import os
import tempfile
import unittest
from pathlib import Path

os.environ["WAPSI_STUB_DELAY"] = "0"
os.environ["WAPSI_CALL_DELAY"] = "0"
os.environ["VOICE_MODE"] = "mock"

from fastapi.testclient import TestClient  # noqa: E402

from wapsi.api import app  # noqa: E402


class DemoFlowTest(unittest.TestCase):
    """The demo path from PLAN.md, end to end."""

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

    def headline(self):
        return self.client.get("/api/board").json()["headline"]

    def test_board_opens_with_37_new_cases(self):
        board = self.client.get("/api/board").json()
        self.assertEqual(len(board["cases"]), 37)
        self.assertEqual(board["headline"]["flagged"], 37)
        self.assertEqual(board["area_dips"][0]["area"], "Guwahati")
        self.assertGreater(len({case["state"] for case in board["cases"]}), 8)

    def test_full_demo_reaches_cover_slide_numbers(self):
        self.client.post("/api/run")
        self.assertEqual(self.headline(), {
            "flagged": 37, "handled_remote": 21, "rep_visit": 9,
            "needs_approval": 2, "no_action": 4, "awaiting_call": 1,
        })

        self.assertEqual(self.client.post("/api/cases/C-M0418/call").status_code, 202)
        self.assertEqual(self.headline()["handled_remote"], 22)

        for approval in self.client.get("/api/approvals").json():
            self.client.post(f"/api/approvals/{approval['id']}/decide", json={"decision": "approve"})
        headline = self.headline()
        self.assertEqual(headline["needs_approval"], 0)
        self.assertEqual(headline["awaiting_call"], 0)

    def test_hero_cases_land_where_the_demo_needs_them(self):
        self.client.post("/api/run")
        cases = {c["id"]: c for c in self.client.get("/api/board").json()["cases"]}
        self.assertEqual(cases["C-M0044"]["bucket"], "rep_visit")
        self.assertEqual(cases["C-M0418"]["status"], "awaiting_call")
        self.assertEqual(cases["C-M0285"]["bucket"], "handled_remote")
        self.assertEqual(cases["C-M0393"]["status"], "awaiting_approval")

    def test_events_can_be_polled_incrementally(self):
        self.client.post("/api/run")
        first = self.client.get("/api/events?after=0").json()
        self.assertTrue(first)
        after = first[-1]["id"]
        self.assertEqual(self.client.get(f"/api/events?after={after}").json()[:0], [])

    def test_call_is_refused_unless_case_is_waiting(self):
        self.assertEqual(self.client.post("/api/cases/C-M0418/call").status_code, 409)

    def test_reset_restores_the_morning(self):
        self.client.post("/api/run")
        self.client.post("/api/reset")
        self.assertEqual(self.headline()["handled_remote"], 0)
        self.assertEqual(self.client.get("/api/events").json(), [])

    def test_results_are_labelled_simulated(self):
        self.client.post("/api/run")
        results = self.client.get("/api/results").json()
        self.assertTrue(results["simulated"])
        self.assertEqual(results["ai"]["visits"], 9)
        self.assertGreater(results["incremental_won_back"], 0)

    def test_unknown_case_is_404(self):
        self.assertEqual(self.client.get("/api/cases/C-NOPE").status_code, 404)


if __name__ == "__main__":
    unittest.main()
