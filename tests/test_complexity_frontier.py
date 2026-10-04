import unittest

from src.evals.complexity_frontier import (
    ArchitecturePoint,
    analyze_frontier,
    dominates,
)


DIRECTIONS = {
    "task_success_rate": "maximize",
    "latency_seconds": "minimize",
    "tool_calls": "minimize",
}


class TestComplexityFrontier(unittest.TestCase):
    def test_detects_dominated_architecture(self):
        baseline = ArchitecturePoint(
            "baseline",
            {
                "task_success_rate": 0.70,
                "latency_seconds": 10.0,
                "tool_calls": 6,
            },
        )
        candidate = ArchitecturePoint(
            "candidate",
            {
                "task_success_rate": 0.80,
                "latency_seconds": 9.0,
                "tool_calls": 5,
            },
        )

        self.assertTrue(dominates(candidate, baseline, DIRECTIONS))
        report = analyze_frontier([baseline, candidate], DIRECTIONS)

        self.assertEqual(report["frontier"], ["candidate"])
        self.assertEqual(report["dominated"]["baseline"], ["candidate"])

    def test_preserves_quality_cost_tradeoff_on_frontier(self):
        simple = ArchitecturePoint(
            "simple",
            {
                "task_success_rate": 0.75,
                "latency_seconds": 5.0,
                "tool_calls": 3,
            },
        )
        routed = ArchitecturePoint(
            "routed",
            {
                "task_success_rate": 0.90,
                "latency_seconds": 12.0,
                "tool_calls": 8,
            },
        )

        report = analyze_frontier([simple, routed], DIRECTIONS)

        self.assertEqual(report["frontier"], ["simple", "routed"])
        self.assertEqual(report["dominated"], {})
        self.assertIn("No weighted winner score", report["claim_boundary"])

    def test_rejects_missing_metrics(self):
        first = ArchitecturePoint("a", {"task_success_rate": 0.5})
        second = ArchitecturePoint("b", {"task_success_rate": 0.6})

        with self.assertRaisesRegex(ValueError, "missing metric"):
            analyze_frontier([first, second], DIRECTIONS)


if __name__ == "__main__":
    unittest.main()
