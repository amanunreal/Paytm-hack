"""PLACEHOLDER so A2 can build the UI today. A1 replaces this with wapsi/agent.py.

It writes canned events in the agreed shape and is the only code allowed to read
ground_truth. Delete this file when the real agent lands, and set AGENT_MODE to live.
"""
import os
import time

from wapsi import store

AGENT_MODE = "stub"
HERO_CALL = "C-M0418"  # Stays open until the live call on stage.

# (bucket, count) per cause, matching Target numbers in PLAN.md.
PLAYBOOK = {
    "device_fault": [("rep_visit", 5), ("handled_remote", 2)],
    "sim_network": [("handled_remote", 8), ("rep_visit", 2)],
    "money_problem": [("handled_remote", 6)],
    "billing_anger": [("handled_remote", 6), ("needs_approval", 1)],
    "competitor_switch": [("needs_approval", 1), ("rep_visit", 2)],
    "closed_seasonal": [("no_action", 4)],
}
# Heroes sort first, so they land in the bucket the demo needs.
HEROES = ["M0044", "M0418", "M0285", "M0393"]


def assignments(conn):
    """Map each AI case to its planned cause and bucket."""
    truth = dict(conn.execute("SELECT merchant_id, scenario FROM ground_truth").fetchall())
    ai = [r["merchant_id"] for r in conn.execute("SELECT merchant_id FROM cases WHERE cohort = 'ai'")]
    ai.sort(key=lambda m: (m not in HEROES, m))
    planned = {}
    for cause, slots in PLAYBOOK.items():
        members = [m for m in ai if truth.get(m) == cause]
        buckets = [bucket for bucket, count in slots for _ in range(count)]
        planned.update({f"C-{m}": (cause, bucket) for m, bucket in zip(members, buckets)})
    return planned


def run_case(conn, case_id, planned):
    cause, bucket = planned[case_id]
    delay = float(os.environ.get("WAPSI_STUB_DELAY", "0.2"))
    store.update_case(conn, case_id, status="working")
    store.add_event(conn, case_id, "tool_call", "get_device_status", {"case": case_id})
    time.sleep(delay)
    store.add_event(conn, case_id, "tool_result", "get_device_status", {"note": "stub data"})
    store.add_event(conn, case_id, "thought", f"[stub] Likely cause: {cause}")
    time.sleep(delay)
    summary = f"[stub] {cause} handled as {bucket}"
    if case_id == HERO_CALL:
        store.update_case(conn, case_id, status="awaiting_call", cause=cause, summary="[stub] Call needed")
        return
    if bucket == "needs_approval":
        kind, amount, next_bucket = ("waiver", 405, "handled_remote") if cause == "billing_anger" else (
            "counter_offer", 50, "rep_visit")
        if kind == "waiver":
            store.add_event(conn, case_id, "guardrail", "Blocked: waiver over the agent limit", {"amount": amount})
        store.add_approval(conn, case_id, kind, amount, summary, next_bucket)
        store.update_case(conn, case_id, status="awaiting_approval", cause=cause, summary=summary)
        return
    brief = "[stub] Carry a replacement unit." if bucket == "rep_visit" else None
    store.update_case(conn, case_id, status="done", cause=cause, bucket=bucket, summary=summary, rep_brief=brief)
    store.add_event(conn, case_id, "status", f"Case closed: {bucket}")


def run_all():
    with store.connect() as conn:
        planned = assignments(conn)
        pending = conn.execute("SELECT id FROM cases WHERE status = 'new'").fetchall()
        for row in pending:
            run_case(conn, row["id"], planned)


def run_one(case_id):
    with store.connect() as conn:
        run_case(conn, case_id, assignments(conn))


def on_call_finished(conn, case_id, resolved, summary):
    """Called by wapsi/voice.py when a call ends."""
    if resolved:
        store.update_case(conn, case_id, status="done", bucket="handled_remote", summary=summary)
    else:
        store.update_case(conn, case_id, status="done", bucket="rep_visit", summary=summary,
                          rep_brief="Call did not fix it. Restart already tried.")
    store.add_event(conn, case_id, "status", "Call finished", {"resolved": resolved})
