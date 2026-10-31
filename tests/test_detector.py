import tempfile
import unittest
from collections import Counter
from datetime import timedelta
from pathlib import Path

from wapsi.detector import detect
from wapsi.sim import SCENARIO_MIX, TODAY, build


class DetectorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.conn = build(Path(cls.tmp.name) / "test.db")
        cls.truth = dict(cls.conn.execute("SELECT merchant_id, scenario FROM ground_truth"))
        cls.flagged = detect(cls.conn, TODAY)
        cls.flagged_ids = {item["merchant_id"] for item in cls.flagged}

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_ai_cohort_matches_cover_slide(self):
        self.assertEqual(sum(SCENARIO_MIX.values()), 37)
        ai = [item for item in self.flagged if item["cohort"] == "ai"]
        self.assertEqual(len(ai), 37)

    def test_every_planted_problem_is_flagged(self):
        planted = {m for m, s in self.truth.items() if s != "area_dip"}
        self.assertEqual(planted - self.flagged_ids, set())

    def test_healthy_merchants_are_not_flagged(self):
        self.assertEqual(self.flagged_ids - set(self.truth), set())

    def test_one_day_off_is_not_flagged(self):
        recent = (TODAY - timedelta(days=3)).isoformat()
        off = {
            row[0] for row in self.conn.execute(
                "SELECT merchant_id FROM daily WHERE day >= ? GROUP BY merchant_id "
                "HAVING SUM(txn_count = 0) = 1", (recent,))
        } - set(self.truth)
        self.assertTrue(off)
        self.assertEqual(off & self.flagged_ids, set())

    def test_merchants_span_india_with_local_languages(self):
        states, languages = zip(*self.conn.execute("SELECT state, language FROM merchants"))
        self.assertGreaterEqual(len(set(states)), 15)
        self.assertGreaterEqual(len(set(languages)), 10)

    def test_area_wide_dip_is_left_alone(self):
        dip = {m for m, s in self.truth.items() if s == "area_dip"}
        self.assertTrue(dip)
        self.assertEqual(dip & self.flagged_ids, set())

    def test_broken_box_with_payments_still_flowing_is_flagged(self):
        by_id = {item["merchant_id"]: item for item in self.flagged}
        faults = [m for m, s in self.truth.items() if s == "device_fault"]
        for merchant_id in faults:
            self.assertGreater(by_id[merchant_id]["volume_ratio"], 0.6)
            self.assertGreaterEqual(by_id[merchant_id]["offline_days"], 2)

    def test_planted_mix_is_paired_across_cohorts(self):
        cohorts = dict(self.conn.execute("SELECT id, cohort FROM merchants"))
        counts = Counter((cohorts[m], s) for m, s in self.truth.items() if s != "area_dip")
        for scenario, count in SCENARIO_MIX.items():
            self.assertEqual(counts["ai", scenario], count)
            self.assertEqual(counts["control", scenario], count)


if __name__ == "__main__":
    unittest.main()
