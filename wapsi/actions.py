"""What the agent can do. Each action checks its guardrails, then changes simulated systems.

A blocked action raises guardrails.Blocked, which the agent sees as a tool error. Everything
the agent does is written to the case events, so the audit log is complete.
"""
from datetime import datetime, timedelta

from wapsi import guardrails, sim, store
from wapsi.guardrails import Blocked

# This merchant is called live on stage, so the agent queues the call instead of simulating it.
LIVE_CALL_CASE = "C-M0418"


class CaseActions:
    """Actions for one case. Tracks what has happened so close_case can check the outcome."""

    def __init__(self, conn, case_id, merchant_id, today=sim.TODAY):
        self.conn = conn
        self.case_id = case_id
        self.merchant_id = merchant_id
        self.today = today
        self.diagnosed = False
        self.fixed_remotely = False
        self.visit_booked = False
        self.approval_requested = False
        self.call_queued = False
        self.closed = False

    def require_diagnosis(self):
        if not self.diagnosed:
            raise Blocked("Call record_diagnosis before taking any action.")

    def contact(self, channel):
        self.require_diagnosis()
        guardrails.check_contact(self.conn, self.merchant_id)
        self.conn.execute("INSERT INTO contacts VALUES (?, ?, ?)",
                          (self.merchant_id, channel, datetime.now().isoformat(timespec="seconds")))
        self.conn.commit()

    def record_diagnosis(self, cause, confidence, evidence, summary):
        diagnosis = {"cause": cause, "confidence": confidence, "evidence": evidence, "summary": summary}
        # The contract's cause values do not include unclear: those cases show no cause yet.
        store.update_case(self.conn, self.case_id, cause=None if cause == "unclear" else cause, summary=summary)
        store.add_event(self.conn, self.case_id, "status", f"Diagnosis: {cause}", diagnosis)
        self.diagnosed = True
        return {"recorded": True}

    def refresh_sim(self):
        self.require_diagnosis()
        return {"refreshed": True, "next_step": "The merchant must power cycle the device for it to reconnect."}

    def start_call(self, goal):
        self.contact("call")
        store.add_event(self.conn, self.case_id, "call", "Calling merchant", {"goal": goal})
        if self.case_id == LIVE_CALL_CASE:
            self.call_queued = True
            return {"status": "queued", "next_step": "This call happens live. Close the case as awaiting_call."}
        fixes = self.conn.execute(
            "SELECT restart_fixes FROM world WHERE merchant_id = ?", (self.merchant_id,)
        ).fetchone()["restart_fixes"]
        result = {"answered": True, "device_back_online": bool(fixes)}
        if fixes:
            self.fixed_remotely = True
        store.add_event(self.conn, self.case_id, "call", "Call finished", result)
        return result

    def order_replacement(self, reason):
        self.require_diagnosis()
        return {"ordered": True, "unit": "Replacement Soundbox", "reason": reason}

    def book_visit(self, reason, rep_brief):
        self.require_diagnosis()
        if not rep_brief.strip():
            raise Blocked("A visit needs a rep brief.")
        store.update_case(self.conn, self.case_id, rep_brief=rep_brief)
        self.visit_booked = True
        return {"booked": True, "reason": reason}

    def create_ticket(self, title, evidence):
        self.require_diagnosis()
        self.conn.execute(
            "INSERT INTO tickets VALUES (?, ?, 'wapsi', 'open', ?)",
            (self.merchant_id, self.today.isoformat(), f"{title}: {evidence}"),
        )
        self.conn.commit()
        self.fixed_remotely = True
        return {"created": True}

    def disputed_total(self):
        return self.conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM billing WHERE merchant_id = ? AND kind = 'rent_duplicate'",
            (self.merchant_id,),
        ).fetchone()[0]

    def offer_waiver(self, amount, reason):
        self.require_diagnosis()
        if amount > self.disputed_total():
            raise Blocked(f"Billing only shows Rs {self.disputed_total()} of duplicate charges to refund.")
        guardrails.check_waiver(amount)
        self.conn.execute(
            "INSERT INTO billing VALUES (?, ?, 'reversal', ?, ?)",
            (self.merchant_id, self.today.isoformat(), -amount, reason),
        )
        self.conn.commit()
        self.fixed_remotely = True
        return {"refunded": amount}

    def monthly_gmv(self):
        start = (self.today - timedelta(days=60)).isoformat()
        end = (self.today - timedelta(days=30)).isoformat()
        return self.conn.execute(
            "SELECT COALESCE(SUM(gmv), 0) FROM daily WHERE merchant_id = ? AND day >= ? AND day < ?",
            (self.merchant_id, start, end),
        ).fetchone()[0]

    def request_approval(self, kind, amount, reason, rep_brief):
        self.require_diagnosis()
        if kind == "counter_offer":
            guardrails.check_counter_offer(self.monthly_gmv())
            store.update_case(self.conn, self.case_id, rep_brief=rep_brief)
        next_bucket = "rep_visit" if kind == "counter_offer" else "handled_remote"
        store.add_approval(self.conn, self.case_id, kind, amount, reason, next_bucket)
        self.approval_requested = True
        return {"requested": True, "next_step": "Close the case as needs_approval."}

    def send_whatsapp(self, text):
        guardrails.check_message(text)
        self.contact("whatsapp")
        language = self.conn.execute(
            "SELECT language FROM merchants WHERE id = ?", (self.merchant_id,)
        ).fetchone()["language"]
        store.add_event(self.conn, self.case_id, "whatsapp", "WhatsApp to merchant",
                        {"text": text, "language": language})
        return {"sent": True}

    def close_case(self, outcome, summary):
        self.require_diagnosis()
        missing = {
            "handled_remote": not self.fixed_remotely and "a fix that worked: a call, ticket or refund",
            "rep_visit": not self.visit_booked and "a booked visit",
            "needs_approval": not self.approval_requested and "a request_approval",
            "awaiting_call": not self.call_queued and "a queued call",
            "no_action": False,
        }[outcome]
        if missing:
            raise Blocked(f"You cannot close this case as {outcome} without {missing}.")
        waiting = {"needs_approval": "awaiting_approval", "awaiting_call": "awaiting_call"}
        if outcome in waiting:
            store.update_case(self.conn, self.case_id, status=waiting[outcome], summary=summary)
        else:
            store.update_case(self.conn, self.case_id, status="done", bucket=outcome, summary=summary)
        store.add_event(self.conn, self.case_id, "status", f"Case closed: {outcome}", {"text": summary})
        self.closed = True
        return {"closed": True}
