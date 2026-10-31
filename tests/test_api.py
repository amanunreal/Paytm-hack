import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ["WAPSI_CALL_DELAY"] = "0"
os.environ["VOICE_MODE"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from wapsi import agent  # noqa: E402
from wapsi.api import app  # noqa: E402

CALL_CASE = "C-M0418"


class DemoFlowTest(unittest.TestCase):
    """The demo path from PLAN.md, end to end, on the saved agent run."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        os.environ["WAPSI_DB"] = str(Path(cls.tmp.name) / "test.db")
        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)
        del os.environ["WAPSI_DB"]
        cls.tmp.cleanup()

    def setUp(self):
        self.client.post("/api/reset")

    def board(self):
        return self.client.get("/api/board").json()

    def test_board_opens_on_the_cover_slide_numbers_with_the_real_agent(self):
        board = self.board()
        self.assertEqual(board["agent_mode"], "live")
        self.assertEqual(board["headline"], {
            "flagged": 37, "handled_remote": 21, "rep_visit": 9,
            "needs_approval": 2, "no_action": 4, "awaiting_call": 1,
        })
        self.assertEqual(board["watched"], {"merchants": 500, "places": 20, "languages": 11})
        self.assertEqual(board["area_dips"][0]["area"], "Guwahati")
        self.assertGreater(len({case["state"] for case in board["cases"]}), 8)

    def test_full_demo_can_run_twice_from_reset(self):
        for _ in range(2):
            self.assertEqual(self.client.post(f"/api/cases/{CALL_CASE}/call").status_code, 202)
            self.assertEqual(self.board()["headline"]["handled_remote"], 22)
            approvals = self.client.get("/api/approvals").json()
            self.assertEqual({a["kind"] for a in approvals}, {"waiver", "counter_offer"})
            for approval in approvals:
                self.client.post(f"/api/approvals/{approval['id']}/decide", json={"decision": "approve"})
            headline = self.board()["headline"]
            self.assertEqual(headline["needs_approval"], 0)
            self.assertEqual(headline["awaiting_call"], 0)
            self.assertEqual(headline["handled_remote"] + headline["rep_visit"] + headline["no_action"], 37)
            self.client.post("/api/reset")
            self.assertEqual(self.board()["headline"]["handled_remote"], 21)

    def test_hero_cases_land_where_the_demo_needs_them(self):
        cases = {c["id"]: c for c in self.board()["cases"]}
        self.assertEqual(cases["C-M0044"]["bucket"], "rep_visit")
        self.assertTrue(cases["C-M0044"]["rep_brief"])
        self.assertEqual(cases[CALL_CASE]["status"], "awaiting_call")
        self.assertEqual(cases["C-M0285"]["bucket"], "handled_remote")
        self.assertEqual(cases["C-M0393"]["status"], "awaiting_approval")
        self.assertEqual(cases["C-M0235"]["status"], "awaiting_approval")

    def test_demo_moments_exist_in_the_saved_run(self):
        def kinds(case_id):
            return {e["kind"]: e for e in self.client.get(f"/api/cases/{case_id}").json()["events"]}

        self.assertIn("whatsapp", kinds("C-M0285"))
        self.assertEqual(kinds("C-M0285")["whatsapp"]["detail"]["language"], "bn")
        self.assertIn("guardrail", kinds("C-M0235"))
        evidence = [e for e in self.client.get("/api/cases/C-M0044").json()["events"]
                    if e["title"].startswith("Diagnosis")]
        self.assertTrue(evidence[0]["detail"]["evidence"])

    def test_fresh_reset_gives_new_cases_and_clears_agent_writes(self):
        self.client.post("/api/reset?fresh=true")
        board = self.board()
        self.assertEqual({case["status"] for case in board["cases"]}, {"new"})
        self.assertEqual(self.client.get("/api/events").json(), [])
        detail = self.client.get("/api/cases/C-M0285").json()
        self.assertIsNone(detail["case"]["cause"])

    def test_run_starts_the_real_agent(self):
        self.client.post("/api/reset?fresh=true")
        with mock.patch.object(agent, "run_case") as run_case:
            self.assertEqual(self.client.post("/api/run").status_code, 202)
        self.assertEqual(run_case.call_count, 37)

    def test_an_api_failure_hands_the_case_to_a_person(self):
        self.client.post("/api/reset?fresh=true")
        failure = agent.anthropic.APIConnectionError(request=mock.Mock())
        with mock.patch.object(agent, "run_case", side_effect=failure):
            self.client.post("/api/cases/C-M0044/run")
        case = self.client.get("/api/cases/C-M0044").json()["case"]
        self.assertEqual(case["status"], "awaiting_approval")

    def test_events_can_be_polled_incrementally(self):
        seen = []
        page = self.client.get("/api/events?after=0").json()
        while page:
            seen.extend(event["id"] for event in page)
            page = self.client.get(f"/api/events?after={seen[-1]}").json()
        self.assertGreater(len(seen), 500)
        self.assertEqual(len(seen), len(set(seen)))

    def test_call_is_refused_unless_case_is_waiting(self):
        self.assertEqual(self.client.post("/api/cases/C-M0044/call").status_code, 409)

    def test_results_are_labelled_simulated(self):
        results = self.client.get("/api/results").json()
        self.assertTrue(results["simulated"])
        self.assertEqual(results["ai"]["visits"], 9)
        self.assertGreater(results["incremental_won_back"], 0)
        self.assertEqual(results["revenue_kept"], round(14.75 * 3000))

    def test_unknown_case_is_404(self):
        self.assertEqual(self.client.get("/api/cases/C-NOPE").status_code, 404)


if __name__ == "__main__":
    unittest.main()
