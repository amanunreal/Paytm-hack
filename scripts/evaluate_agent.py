"""Run the real agent on every AI case and score it. Costs API credit.

Works on a throwaway database, so a running demo is never touched. With --save, a passing
run becomes wapsi/prerun.json, which /api/reset restores. A failing run is never saved.
This is the only agent-related code allowed to read ground_truth.
"""
import os
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")
tmp = tempfile.mkdtemp()
os.environ["WAPSI_DB"] = str(Path(tmp) / "eval.db")

from wapsi import agent, store  # noqa: E402

TARGET = {
    "device_fault": {"handled_remote": 2, "rep_visit": 5},
    "sim_network": {"handled_remote": 7, "awaiting_call": 1, "rep_visit": 2},
    "money_problem": {"handled_remote": 6},
    "billing_anger": {"handled_remote": 6, "needs_approval": 1},
    "competitor_switch": {"rep_visit": 2, "needs_approval": 1},
    "closed_seasonal": {"no_action": 4},
}


store.ensure_db()
with store.connect() as conn:
    truth = dict(conn.execute("SELECT merchant_id, scenario FROM ground_truth").fetchall())

agent.run_all()

with store.connect() as conn:
    actual = {}
    wrong_cause = []
    for row in conn.execute("SELECT * FROM cases WHERE cohort = 'ai' ORDER BY id"):
        want = truth[row["merchant_id"]]
        outcome = row["bucket"] or {"awaiting_approval": "needs_approval"}.get(row["status"], row["status"])
        actual.setdefault(want, Counter())[outcome] += 1
        if row["cause"] != want:
            wrong_cause.append((row["id"], want, row["cause"], row["status"], row["summary"]))
    guards = store.rows(conn.execute(
        "SELECT case_id, title, detail FROM events WHERE kind = 'guardrail' ORDER BY id"))
    messages = store.event_rows(conn.execute(
        "SELECT * FROM events WHERE kind = 'whatsapp' AND case_id IN ('C-M0285', 'C-M0142') ORDER BY id"))

passed = True
for cause, want in TARGET.items():
    match = dict(actual.get(cause, {})) == want
    passed = passed and match
    print(f"{'OK ' if match else 'BAD'} {cause}: {dict(actual.get(cause, {}))} want {want}")
print("wrong causes:", wrong_cause or "none")
print("guardrails fired:", len(guards))
for guard in guards[:12]:
    print("  ", guard["case_id"], guard["title"], str(guard["detail"])[:110])
for message in messages:
    print("whatsapp", message["case_id"], message["detail"]["text"][:200])
# The demo needs the agent to hit the waiver limit by itself, then go to the manager.
blocked_waiver = any(guard["title"] == "Blocked: offer_waiver" for guard in guards)
print("over-limit waiver blocked:", blocked_waiver)
success = passed and not wrong_cause and blocked_waiver
print("PASS" if success else "FAIL")
if success and "--save" in sys.argv:
    with store.connect() as conn:
        store.save_snapshot(conn)
    print("saved", store.SNAPSHOT_PATH)
shutil.rmtree(tmp)
sys.exit(0 if success else 1)
