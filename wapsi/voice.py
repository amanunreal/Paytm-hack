"""The live call. A2 owns this file.

VOICE_MODE=mock plays a scripted call, so the UI works before Bolna does.
VOICE_MODE=bolna is for A2 to finish: POST /call with the agent id and number, then
poll GET /executions/{id} until it is completed, so no public tunnel is needed.
Check field names against the Bolna API reference.
"""
import os
import time

from wapsi import store, stub_agent

MOCK_SCRIPT = [
    ("Wapsi", "Namaste Sunita ji, main Paytm se Wapsi bol rahi hoon. Aapka Soundbox teen din se offline hai."),
    ("Merchant", "Haan, awaaz nahi aa rahi. Payment aa raha hai par pata nahi chalta."),
    ("Wapsi", "Aapke paise surakshit hain. Kripya box ko 10 second band karke phir chalu kijiye."),
    ("Merchant", "Theek hai, kar diya. Ab light jal rahi hai."),
    ("Wapsi", "Badhiya, box wapas online aa gaya hai. Dhanyavaad!"),
]


def start_call(case_id):
    with store.connect() as conn:
        store.update_case(conn, case_id, status="on_call")
        store.add_event(conn, case_id, "call", "Calling merchant", {"mode": os.environ.get("VOICE_MODE", "mock")})
        if os.environ.get("VOICE_MODE", "mock") == "bolna":
            raise NotImplementedError("A2: Bolna call goes here")
        delay = float(os.environ.get("WAPSI_CALL_DELAY", "2.5"))
        for speaker, line in MOCK_SCRIPT:
            time.sleep(delay)
            store.add_event(conn, case_id, "call", speaker, {"text": line})
        stub_agent.on_call_finished(conn, case_id, True, "SIM session refreshed; box back online after guided restart")
