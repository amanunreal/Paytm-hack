"""The live call. A2 owns this file.

VOICE_MODE=mock plays a scripted call, so the UI works without Bolna.
VOICE_MODE=bolna rings DEMO_MERCHANT_PHONE and polls GET /executions/{id}, so no public
tunnel is needed. Bolna only gives the transcript once the call ends, so the trace shows
progress during the call and the conversation after it.

The outcome decides the next step: fixed closes the case, not fixed books a rep, and
anything else goes back to awaiting_call until MAX_CALLS is used.
Set up the agent and its outcome extraction with scripts/bolna_agent.py.
"""
import os
import re
import time

import httpx

from wapsi import store

BOLNA_URL = "https://api.bolna.ai"
POLL_SECONDS = 2
POLL_LIMIT_SECONDS = 300
MAX_CALLS = 3
# Not the agent's "Calling merchant", which only queues a call and must not use up a try.
CALLING = "Dialling merchant"

# call-disconnected is not here: transcript and outcome are not final until completed.
TERMINAL = {"completed", "no-answer", "busy", "canceled", "failed", "stopped", "error", "balance-low"}
PROGRESS = {
    "ringing": "Phone ringing",
    "in-progress": "Merchant picked up",
    "call-disconnected": "Call ended, reading the transcript",
}
SPEAKERS = {"assistant": "Wapsi", "user": "Merchant"}

# Must match the extraction made by scripts/bolna_agent.py.
OUTCOME_CATEGORY = "Wapsi"
OUTCOME_NAME = "Call Outcome"

# Sarvam speaks the script it is given, so the name needs to be in Devanagari.
HINDI_NAMES = {"Sunita": "सुनीता"}

MOCK_SCRIPT = [
    ("Wapsi", "Namaste Sunita ji, main Paytm se Wapsi bol rahi hoon. Aapka Soundbox teen din se offline hai."),
    ("Merchant", "Haan, awaaz nahi aa rahi. Payment aa raha hai par pata nahi chalta."),
    ("Wapsi", "Aapke paise surakshit hain. Kripya box ko 10 second band karke phir chalu kijiye."),
    ("Merchant", "Theek hai, kar diya. Ab light jal rahi hai."),
    ("Wapsi", "Badhiya, box wapas online aa gaya hai. Dhanyavaad!"),
]


def bolna_client():
    key = os.environ.get("BOLNA_API_KEY", "").strip()
    return httpx.Client(base_url=BOLNA_URL, timeout=30, headers={"Authorization": f"Bearer {key}"})


def claim_call(conn, case_id):
    """Take the case in one write, so a double click cannot ring the phone twice."""
    claimed = conn.execute(
        "UPDATE cases SET status = 'on_call' WHERE id = ? AND status = 'awaiting_call'", (case_id,)
    ).rowcount
    conn.commit()
    return claimed == 1


def still_on_call(conn, case_id):
    """False once /api/reset has moved the case on, so this call writes nothing more."""
    row = conn.execute("SELECT status FROM cases WHERE id = ?", (case_id,)).fetchone()
    return row is not None and row["status"] == "on_call"


def finish(conn, case_id, resolved, summary, rep_brief=None):
    bucket = "handled_remote" if resolved else "rep_visit"
    store.update_case(conn, case_id, status="done", bucket=bucket, summary=summary, rep_brief=rep_brief)
    store.add_event(conn, case_id, "status", "Call finished", {"resolved": resolved})


def call_later(conn, case_id, reason):
    """Offer another call, or book a rep once MAX_CALLS is used."""
    calls = conn.execute(
        "SELECT COUNT(*) FROM events WHERE case_id = ? AND kind = 'call' AND title = ?", (case_id, CALLING)
    ).fetchone()[0]
    if calls >= MAX_CALLS:
        finish(conn, case_id, False, f"{reason} Stopped after {calls} calls.",
               "Could not finish this over the phone. Restart may not have been tried.")
        return
    store.update_case(conn, case_id, status="awaiting_call", summary=reason)
    store.add_event(conn, case_id, "status", "Call again", {"reason": reason, "calls_used": f"{calls} of {MAX_CALLS}"})


def merchant_details(conn, case_id):
    row = conn.execute(
        "SELECT m.owner, m.shop_type, m.area, c.offline_days FROM cases c "
        "JOIN merchants m ON m.id = c.merchant_id WHERE c.id = ?", (case_id,)
    ).fetchone()
    first_name = row["owner"].split()[0]
    return {
        "merchant_name": HINDI_NAMES.get(first_name, first_name),
        "shop_type": row["shop_type"],
        "area": row["area"],
        "offline_days": str(row["offline_days"]),
    }


def transcript_lines(transcript):
    """Split Bolna's `speaker: text` lines, keeping any wrapped text with its speaker."""
    lines = []
    for line in (transcript or "").splitlines():
        match = re.match(r"(assistant|user):\s*(.*)", line)
        if match:
            lines.append((SPEAKERS[match[1]], match[2].strip()))
        elif lines and line.strip():
            lines[-1] = (lines[-1][0], f"{lines[-1][1]} {line.strip()}")
    return [(speaker, text) for speaker, text in lines if text]


def call_outcome(execution):
    """fixed, not_fixed or call_back. Anything else means Bolna could not tell."""
    outcome = ((execution.get("extracted_data") or {}).get(OUTCOME_CATEGORY) or {}).get(OUTCOME_NAME) or {}
    return outcome.get("objective")


def settle(conn, case_id, execution):
    status = execution.get("status")
    lines = transcript_lines(execution.get("transcript"))
    # Bolna can say completed for a rejected call, so look for the merchant actually talking.
    if status != "completed" or not any(speaker == "Merchant" for speaker, _ in lines):
        store.add_event(conn, case_id, "call", "Call did not connect", {"status": status})
        call_later(conn, case_id, f"Merchant did not pick up ({status}).")
        return

    for speaker, text in lines:
        store.add_event(conn, case_id, "call", speaker, {"text": text})

    outcome = call_outcome(execution)
    if outcome == "fixed":
        finish(conn, case_id, True, "Box back online after the guided restart on the call.")
    elif outcome == "not_fixed":
        finish(conn, case_id, False, "Restart on the call did not bring the box back.",
               "Call did not fix it. Restart already tried.")
    elif outcome == "call_back":
        call_later(conn, case_id, "Merchant could not finish the restart on this call.")
    else:
        call_later(conn, case_id, "Could not tell from the call if the box is back.")


def bolna_call(conn, case_id):
    agent_id = os.environ.get("BOLNA_AGENT_ID", "").strip()
    phone = os.environ.get("DEMO_MERCHANT_PHONE", "").strip()
    if not agent_id or not phone:
        raise RuntimeError("Set BOLNA_AGENT_ID and DEMO_MERCHANT_PHONE in .env")

    with bolna_client() as bolna:
        response = bolna.post("/call", json={
            "agent_id": agent_id,
            "recipient_phone_number": phone,
            "user_data": merchant_details(conn, case_id),
        })
        if response.status_code >= 400:
            raise RuntimeError(f"Bolna refused the call ({response.status_code}): {response.text}")
        execution_id = response.json()["execution_id"]

        seen = None
        deadline = time.monotonic() + POLL_LIMIT_SECONDS
        while time.monotonic() < deadline:
            time.sleep(POLL_SECONDS)
            response = bolna.get(f"/executions/{execution_id}")
            if not still_on_call(conn, case_id):
                return
            response.raise_for_status()
            execution = response.json()
            status = execution.get("status")
            if status != seen and status in PROGRESS:
                store.add_event(conn, case_id, "call", PROGRESS[status])
            seen = status
            if status in TERMINAL:
                settle(conn, case_id, execution)
                return
    raise RuntimeError(f"No result from Bolna after {POLL_LIMIT_SECONDS}s, last status {seen}")


def mock_call(conn, case_id):
    delay = float(os.environ.get("WAPSI_CALL_DELAY", "2.5"))
    for speaker, line in MOCK_SCRIPT:
        time.sleep(delay)
        if not still_on_call(conn, case_id):
            return
        store.add_event(conn, case_id, "call", speaker, {"text": line})
    finish(conn, case_id, True, "SIM session refreshed; box back online after guided restart")


def start_call(case_id):
    mode = os.environ.get("VOICE_MODE", "mock")
    with store.connect() as conn:
        if not claim_call(conn, case_id):
            return
        store.add_event(conn, case_id, "call", CALLING, {"mode": mode})
        try:
            bolna_call(conn, case_id) if mode == "bolna" else mock_call(conn, case_id)
        except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as failure:
            if still_on_call(conn, case_id):
                store.add_event(conn, case_id, "call", "Call failed", {"error": str(failure)})
                call_later(conn, case_id, "The call failed before it finished.")
