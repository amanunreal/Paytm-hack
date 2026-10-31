"""The API both of us build against. Contract: PLAN.md. Docs: /docs."""
from collections import Counter
from contextlib import asynccontextmanager
from datetime import timedelta

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

load_dotenv()

from wapsi import actions, agent, detector, results, sim, store, voice  # noqa: E402


@asynccontextmanager
async def lifespan(_app):
    store.ensure_db(prerun=True)
    yield


app = FastAPI(title="Wapsi", lifespan=lifespan)


class Decision(BaseModel):
    decision: str


def get_case(conn, case_id):
    row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Unknown case {case_id}")
    return dict(row)


@app.get("/api/board")
def board():
    with store.connect() as conn:
        cases = store.rows(conn.execute(
            "SELECT c.*, m.owner, m.shop_type, m.area, m.state, m.language, m.device_model FROM cases c "
            "JOIN merchants m ON m.id = c.merchant_id WHERE c.cohort = 'ai' ORDER BY c.cause, c.id"
        ))
        buckets = Counter(case["bucket"] for case in cases)
        statuses = Counter(case["status"] for case in cases)
        return {
            "date": sim.TODAY.isoformat(),
            "agent_mode": agent.AGENT_MODE,
            "watched": dict(conn.execute(
                "SELECT COUNT(*) AS merchants, COUNT(DISTINCT area) AS places, "
                "COUNT(DISTINCT language) AS languages FROM merchants"
            ).fetchone()),
            "headline": {
                "flagged": len(cases),
                "handled_remote": buckets["handled_remote"],
                "rep_visit": buckets["rep_visit"],
                "needs_approval": statuses["awaiting_approval"],
                "no_action": buckets["no_action"],
                "awaiting_call": statuses["awaiting_call"] + statuses["on_call"],
            },
            "area_dips": detector.area_dips(conn, sim.TODAY),
            "cases": cases,
        }


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str):
    with store.connect() as conn:
        case = get_case(conn, case_id)
        since = (sim.TODAY - timedelta(days=14)).isoformat()
        return {
            "case": case,
            "merchant": dict(conn.execute("SELECT * FROM merchants WHERE id = ?", (case["merchant_id"],)).fetchone()),
            "signals": store.rows(conn.execute(
                "SELECT day, txn_count, gmv, heartbeats, signal FROM daily "
                "WHERE merchant_id = ? AND day >= ? ORDER BY day", (case["merchant_id"], since))),
            "events": store.event_rows(conn.execute("SELECT * FROM events WHERE case_id = ? ORDER BY id", (case_id,))),
            "approvals": store.rows(conn.execute("SELECT * FROM approvals WHERE case_id = ?", (case_id,))),
        }


@app.get("/api/events")
def events(after: int = 0):
    with store.connect() as conn:
        return store.event_rows(conn.execute("SELECT * FROM events WHERE id > ? ORDER BY id LIMIT 500", (after,)))


@app.post("/api/run", status_code=202)
def run(tasks: BackgroundTasks):
    tasks.add_task(agent.run_all)
    return {"started": True}


@app.post("/api/cases/{case_id}/run", status_code=202)
def run_case(case_id: str, tasks: BackgroundTasks):
    with store.connect() as conn:
        get_case(conn, case_id)
    tasks.add_task(agent.run_one, case_id)
    return {"started": True}


@app.post("/api/cases/{case_id}/call", status_code=202)
def call(case_id: str, tasks: BackgroundTasks):
    with store.connect() as conn:
        if get_case(conn, case_id)["status"] != "awaiting_call":
            raise HTTPException(409, "Case is not waiting for a call")
    tasks.add_task(voice.start_call, case_id)
    return {"started": True}


@app.get("/api/approvals")
def approvals():
    with store.connect() as conn:
        return store.rows(conn.execute("SELECT * FROM approvals WHERE status = 'pending' ORDER BY id"))


@app.post("/api/approvals/{approval_id}/decide")
def decide(approval_id: int, body: Decision):
    if body.decision not in ("approve", "reject"):
        raise HTTPException(422, "decision must be approve or reject")
    with store.connect() as conn:
        row = conn.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
        if row is None or row["status"] != "pending":
            raise HTTPException(409, "Approval is not pending")
        return {"bucket": actions.apply_decision(conn, row, body.decision)}


@app.get("/api/results")
def get_results():
    with store.connect() as conn:
        return results.results(conn)


@app.post("/api/reset")
def reset(fresh: bool = False):
    """Back to the demo's opening board. With fresh, every case is new for a real agent run."""
    with store.connect() as conn:
        store.reset(conn, prerun=not fresh)
    return {"reset": True}
