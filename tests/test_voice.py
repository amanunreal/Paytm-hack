import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from wapsi import store, voice

CASE = "C-M0418"
TALK = "assistant: नमस्ते\nuser: हाँ\nassistant: धन्यवाद"


def execution(status="completed", transcript=TALK, outcome=None):
    data = {"Wapsi": {"Call Outcome": {"objective": outcome}}} if outcome else None
    return {"status": status, "transcript": transcript, "extracted_data": data}


class BolnaCallTest(unittest.TestCase):
    """Every way a real call can end, against a fake Bolna."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        env = {
            "WAPSI_DB": str(Path(self.tmp.name) / "test.db"),
            "VOICE_MODE": "bolna",
            "BOLNA_API_KEY": "test",
            "BOLNA_AGENT_ID": "agent",
            "DEMO_MERCHANT_PHONE": "+910000000000",
        }
        patches = [
            mock.patch.dict(os.environ, env),
            mock.patch.object(voice, "POLL_SECONDS", 0),
            mock.patch.object(voice, "bolna_client", self.fake_client),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.addCleanup(self.tmp.cleanup)

        store.ensure_db()
        self.calls = []
        self.polls = []
        self.call_status = 200
        self.on_poll = None
        with store.connect() as conn:
            store.update_case(conn, CASE, status="awaiting_call")

    def fake_client(self):
        def respond(request):
            if request.method == "POST":
                self.calls.append(request)
                if self.call_status != 200:
                    return httpx.Response(self.call_status, text="refused")
                return httpx.Response(200, json={"execution_id": "e1", "status": "queued"})
            if self.on_poll:
                self.on_poll()
            return httpx.Response(200, json=self.polls.pop(0))
        return httpx.Client(base_url=voice.BOLNA_URL, transport=httpx.MockTransport(respond))

    def case(self):
        with store.connect() as conn:
            return dict(conn.execute("SELECT * FROM cases WHERE id = ?", (CASE,)).fetchone())

    def event_titles(self):
        with store.connect() as conn:
            return [row["title"] for row in conn.execute("SELECT title FROM events ORDER BY id")]

    def call_with(self, *polls):
        self.polls = list(polls)
        voice.start_call(CASE)
        return self.case()

    def test_fixed_closes_the_case(self):
        case = self.call_with(
            {"status": "ringing"}, {"status": "in-progress"}, {"status": "call-disconnected"},
            execution(outcome="fixed"),
        )
        self.assertEqual((case["status"], case["bucket"]), ("done", "handled_remote"))
        self.assertEqual(self.event_titles(), [
            voice.CALLING, "Phone ringing", "Merchant picked up", "Call ended, reading the transcript",
            "Wapsi", "Merchant", "Wapsi", "Call finished",
        ])

    def test_not_fixed_books_a_rep(self):
        case = self.call_with(execution(outcome="not_fixed"))
        self.assertEqual((case["status"], case["bucket"]), ("done", "rep_visit"))
        self.assertIn("Restart already tried", case["rep_brief"])

    def test_merchant_details_go_to_bolna(self):
        self.call_with(execution(outcome="fixed"))
        body = self.calls[0].content.decode()
        self.assertIn("+910000000000", body)
        self.assertIn('"offline_days":"3"', body.replace(" ", ""))

    def test_call_back_and_unclear_offer_another_call(self):
        for outcome in ("call_back", "NA", None):
            with self.subTest(outcome=outcome):
                case = self.call_with(execution(outcome=outcome))
                self.assertEqual((case["status"], case["bucket"]), ("awaiting_call", None))
                with store.connect() as conn:
                    conn.execute("DELETE FROM events")
                    conn.commit()

    def test_no_answer_offers_another_call_and_shows_no_transcript(self):
        case = self.call_with(execution("no-answer", transcript=None))
        self.assertEqual(case["status"], "awaiting_call")
        self.assertIn("did not pick up", case["summary"])
        self.assertNotIn("Merchant", self.event_titles())

    def test_rejected_call_marked_completed_does_not_count_as_a_talk(self):
        case = self.call_with(execution(transcript="assistant: नमस्ते", outcome="fixed"))
        self.assertEqual((case["status"], case["bucket"]), ("awaiting_call", None))

    def test_third_call_without_an_answer_books_a_rep(self):
        for attempt in range(voice.MAX_CALLS):
            case = self.call_with(execution("busy", transcript=None))
        self.assertEqual(len(self.calls), voice.MAX_CALLS)
        self.assertEqual((case["status"], case["bucket"]), ("done", "rep_visit"))

    def test_bolna_refusing_the_call_offers_another_and_says_why(self):
        self.call_status = 400
        case = self.call_with()
        self.assertEqual(case["status"], "awaiting_call")
        self.assertIn("Call failed", self.event_titles())

    def test_missing_phone_is_reported_and_rings_nothing(self):
        with mock.patch.dict(os.environ, {"DEMO_MERCHANT_PHONE": ""}):
            case = self.call_with()
        self.assertEqual(self.calls, [])
        self.assertEqual(case["status"], "awaiting_call")

    def test_second_click_does_not_ring_twice(self):
        self.call_with(execution(outcome="fixed"))
        voice.start_call(CASE)
        self.assertEqual(len(self.calls), 1)

    def test_reset_during_a_call_writes_nothing_more(self):
        def reset():
            with store.connect() as conn:
                store.reset(conn)
        self.on_poll = reset
        self.call_with({"status": "ringing"}, {"status": "ringing"})
        self.assertEqual(self.case()["status"], "new")
        self.assertEqual(self.event_titles(), [])


class TranscriptTest(unittest.TestCase):
    def test_wrapped_text_stays_with_its_speaker(self):
        self.assertEqual(
            voice.transcript_lines("assistant:  एक\nदो\nuser: तीन\nassistant:   \n"),
            [("Wapsi", "एक दो"), ("Merchant", "तीन")],
        )

    def test_empty_transcript(self):
        self.assertEqual(voice.transcript_lines(None), [])


if __name__ == "__main__":
    unittest.main()
