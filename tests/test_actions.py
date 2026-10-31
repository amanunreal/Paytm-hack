import os
import tempfile
import unittest
from pathlib import Path

from wapsi import guardrails, store
from wapsi.actions import LIVE_CALL_CASE, CaseActions, apply_decision
from wapsi.guardrails import Blocked


class ActionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["WAPSI_DB"] = str(Path(cls.tmp.name) / "test.db")
        os.environ["WAPSI_CLOCK_HOUR"] = "10"
        store.ensure_db()

    @classmethod
    def tearDownClass(cls):
        del os.environ["WAPSI_DB"]
        del os.environ["WAPSI_CLOCK_HOUR"]
        cls.tmp.cleanup()

    def setUp(self):
        self.conn = store.connect()
        store.reset(self.conn)
        self.truth = dict(self.conn.execute("SELECT merchant_id, scenario FROM ground_truth").fetchall())
        self.ai = [r[0] for r in self.conn.execute("SELECT merchant_id FROM cases WHERE cohort = 'ai'")]

    def tearDown(self):
        self.conn.execute("UPDATE merchants SET opted_out = 0")
        self.conn.commit()
        self.conn.close()
        os.environ["WAPSI_CLOCK_HOUR"] = "10"

    def actions(self, merchant_id, diagnosed=True):
        actions = CaseActions(self.conn, f"C-{merchant_id}", merchant_id)
        actions.diagnosed = diagnosed
        return actions

    def merchant(self, scenario):
        return next(m for m in self.ai if self.truth[m] == scenario)

    def repeat_billing(self):
        return self.conn.execute(
            "SELECT merchant_id FROM billing WHERE kind = 'rent_duplicate' "
            "GROUP BY merchant_id HAVING COUNT(*) > 1 AND merchant_id IN "
            "(SELECT merchant_id FROM cases WHERE cohort = 'ai')"
        ).fetchone()[0]

    def test_no_action_before_a_diagnosis(self):
        actions = self.actions(self.merchant("device_fault"), diagnosed=False)
        for attempt in (actions.refresh_sim, lambda: actions.start_call("x"),
                        lambda: actions.close_case("no_action", "x")):
            with self.assertRaises(Blocked):
                attempt()

    def test_waiver_within_the_limit_refunds_the_merchant(self):
        merchant_id = self.merchant("billing_anger")
        rent = self.conn.execute("SELECT amount FROM billing WHERE merchant_id = ? AND kind = 'rent_duplicate'",
                                 (merchant_id,)).fetchone()[0]
        if merchant_id == self.repeat_billing():
            self.skipTest("first billing merchant is the repeat case")
        actions = self.actions(merchant_id)
        self.assertEqual(actions.offer_waiver(rent, "Duplicate rent")["refunded"], rent)
        reversal = self.conn.execute("SELECT amount FROM billing WHERE merchant_id = ? AND kind = 'reversal'",
                                     (merchant_id,)).fetchone()[0]
        self.assertEqual(reversal, -rent)

    def test_over_limit_waiver_is_blocked_and_nothing_is_refunded(self):
        merchant_id = self.repeat_billing()
        actions = self.actions(merchant_id)
        self.assertEqual(actions.disputed_total(), 405)
        with self.assertRaises(Blocked):
            actions.offer_waiver(405, "Three months of duplicate rent")
        refunds = self.conn.execute("SELECT COUNT(*) FROM billing WHERE merchant_id = ? AND kind = 'reversal'",
                                    (merchant_id,)).fetchone()[0]
        self.assertEqual(refunds, 0)

    def test_splitting_a_refund_cannot_beat_the_limit(self):
        actions = self.actions(self.repeat_billing())
        actions.offer_waiver(135, "First month")
        with self.assertRaises(Blocked):
            actions.offer_waiver(135, "Second month")

    def test_manager_approval_refunds_the_full_amount(self):
        merchant_id = self.repeat_billing()
        self.actions(merchant_id).request_approval("waiver", 405, "Three months of duplicates", "")
        approval = self.conn.execute("SELECT * FROM approvals WHERE case_id = ?", (f"C-{merchant_id}",)).fetchone()
        self.assertEqual(apply_decision(self.conn, approval, "approve"), "handled_remote")
        refunded = self.conn.execute("SELECT SUM(amount) FROM billing WHERE merchant_id = ? AND kind = 'reversal'",
                                     (merchant_id,)).fetchone()[0]
        self.assertEqual(refunded, -405)

    def test_rejected_waiver_refunds_nothing_and_books_a_rep_with_a_brief(self):
        merchant_id = self.repeat_billing()
        self.actions(merchant_id).request_approval("waiver", 405, "Three months of duplicates", "")
        approval = self.conn.execute("SELECT * FROM approvals WHERE case_id = ?", (f"C-{merchant_id}",)).fetchone()
        self.assertEqual(apply_decision(self.conn, approval, "reject"), "rep_visit")
        case = self.conn.execute("SELECT rep_brief FROM cases WHERE id = ?", (f"C-{merchant_id}",)).fetchone()
        self.assertTrue(case["rep_brief"])

    def test_waiver_cannot_exceed_what_billing_shows(self):
        with self.assertRaises(Blocked):
            self.actions(self.merchant("device_fault")).offer_waiver(50, "No dispute exists")

    def test_counter_offer_only_for_shops_over_the_volume_bar(self):
        with self.assertRaises(Blocked):
            self.actions("M0202").request_approval("counter_offer", 50, "Competitor", "Brief")
        self.assertTrue(self.actions("M0393").request_approval("counter_offer", 50, "Competitor", "Brief")["requested"])

    def test_no_calls_at_night(self):
        os.environ["WAPSI_CLOCK_HOUR"] = "23"
        with self.assertRaises(Blocked):
            self.actions(self.merchant("device_fault")).start_call("Guide a restart")

    def test_opted_out_merchants_are_left_alone(self):
        merchant_id = self.merchant("device_fault")
        self.conn.execute("UPDATE merchants SET opted_out = 1 WHERE id = ?", (merchant_id,))
        with self.assertRaises(Blocked):
            self.actions(merchant_id).start_call("Guide a restart")
        with self.assertRaises(Blocked):
            self.actions(merchant_id).send_whatsapp("Namaste")

    def test_contact_cap_is_enforced(self):
        actions = self.actions(self.merchant("money_problem"))
        for _ in range(guardrails.MAX_CONTACTS_PER_WEEK):
            actions.send_whatsapp("Namaste")
        with self.assertRaises(Blocked):
            actions.send_whatsapp("Namaste")

    def test_messages_cannot_ask_for_sensitive_details(self):
        actions = self.actions(self.merchant("money_problem"))
        for text in ("Please share your OTP", "Send your IFSC code", "Apna password bhejiye", "ओटीपी बताइए"):
            with self.assertRaises(Blocked):
                actions.send_whatsapp(text)

    def test_a_rep_visit_needs_a_brief(self):
        with self.assertRaises(Blocked):
            self.actions(self.merchant("device_fault")).book_visit("Replace unit", "  ")

    def test_failed_restart_does_not_count_as_a_fix(self):
        actions = self.actions("M0044")
        self.assertFalse(actions.start_call("Guide a restart")["device_back_online"])
        with self.assertRaises(Blocked):
            actions.close_case("handled_remote", "Fixed")

    def test_live_case_queues_the_call_and_stays_open(self):
        merchant_id = LIVE_CALL_CASE.removeprefix("C-")
        actions = self.actions(merchant_id)
        self.assertEqual(actions.start_call("Guide a restart")["status"], "queued")
        actions.close_case("awaiting_call", "Waiting for the call")
        row = self.conn.execute("SELECT status, bucket FROM cases WHERE id = ?", (LIVE_CALL_CASE,)).fetchone()
        self.assertEqual(tuple(row), ("awaiting_call", None))

    def test_outcomes_must_match_what_actually_happened(self):
        actions = self.actions(self.merchant("device_fault"))
        for outcome in ("handled_remote", "rep_visit", "needs_approval", "awaiting_call"):
            with self.assertRaises(Blocked):
                actions.close_case(outcome, "x")

    def test_whatsapp_is_recorded_with_the_merchants_language(self):
        actions = self.actions("M0285")
        actions.send_whatsapp("আপনার টাকা ফেরত দেওয়া হয়েছে")
        event = store.event_rows(self.conn.execute(
            "SELECT * FROM events WHERE case_id = 'C-M0285' AND kind = 'whatsapp'"))[0]
        self.assertEqual(event["detail"]["language"], "bn")


if __name__ == "__main__":
    unittest.main()
