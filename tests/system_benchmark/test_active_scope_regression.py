import unittest
from pathlib import Path

from src.evals.system_benchmark.loader import load_tasks


ROOT = Path(__file__).resolve().parents[2]


class TestSBActiveScopeRegression(unittest.TestCase):
    def test_d01_uses_policy_aligned_active_work_population(self):
        tasks = load_tasks(ROOT / "evals/system_benchmark/development_tasks.json")
        task = next(item for item in tasks if item.case_id == "SB-D01")
        expected = {item.name: item for item in task.expected_values}

        self.assertIn("active work items", task.request.casefold())
        self.assertEqual(expected["team"].value, "Data")
        self.assertAlmostEqual(expected["blocked_pct"].value, 17.8)
        self.assertEqual(expected["scope"].value, "active_work_items")

    def test_a01_historical_all_item_case_is_unchanged(self):
        tasks = load_tasks(ROOT / "evals/system_benchmark/development_tasks.json")
        task = next(item for item in tasks if item.case_id == "SB-A01")
        expected = {item.name: item for item in task.expected_values}

        self.assertAlmostEqual(expected["blocked_pct"].value, 20.9)
        self.assertNotIn("scope", expected)


if __name__ == "__main__":
    unittest.main()
