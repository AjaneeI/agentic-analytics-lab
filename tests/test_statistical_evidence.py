import unittest

from src.evals.statistical_evidence import compare_architectures


def make_payload(task_results, *, architecture):
    results = [
        {
            "question_id": f"Q{index}",
            "category": "test",
            "execution_success": True,
            "correct": success,
            "task_success": success,
        }
        for index, success in enumerate(task_results, start=1)
    ]
    return {
        "summary": {
            "questions": len(results),
            "execution_successful": len(results),
            "task_successful": sum(task_results),
            "correct": sum(task_results),
        },
        "metadata": {
            "benchmark_schema_version": 2,
            "architecture": architecture,
            "model": "qwen2.5:7b",
            "provider": "ollama_local",
            "dataset": "synthetic_delivery_seed_42",
            "questions": "evals/questions.json",
        },
        "results": results,
    }


class TestStatisticalEvidence(unittest.TestCase):
    def test_compares_repeats_at_task_level(self):
        baseline = [
            make_payload([True, False, True], architecture="single"),
            make_payload([True, False, False], architecture="single"),
            make_payload([True, True, False], architecture="single"),
        ]
        candidate = [
            make_payload([True, True, True], architecture="routed"),
            make_payload([True, True, True], architecture="routed"),
            make_payload([True, True, False], architecture="routed"),
        ]

        result = compare_architectures(
            baseline, candidate, bootstrap_samples=1000, seed=7
        )

        self.assertEqual(result["method"], "paired_task_level_bootstrap")
        self.assertEqual(result["task_count"], 3)
        self.assertEqual(result["run_count_per_architecture"], 3)
        self.assertEqual(result["aggregate"]["candidate_better_tasks"], 2)
        self.assertEqual(result["aggregate"]["tied_tasks"], 1)
        self.assertGreater(
            result["aggregate"]["mean_delta_percentage_points"], 0
        )
        self.assertIn("frozen benchmark task set", result["claim_boundary"])

    def test_bootstrap_is_deterministic_for_fixed_seed(self):
        baseline = [
            make_payload([True, False], architecture="single"),
            make_payload([True, False], architecture="single"),
        ]
        candidate = [
            make_payload([True, True], architecture="routed"),
            make_payload([True, False], architecture="routed"),
        ]

        first = compare_architectures(
            baseline, candidate, bootstrap_samples=500, seed=42
        )
        second = compare_architectures(
            baseline, candidate, bootstrap_samples=500, seed=42
        )

        self.assertEqual(first["aggregate"], second["aggregate"])

    def test_rejects_unmatched_run_counts(self):
        baseline = [
            make_payload([True, False], architecture="single"),
            make_payload([True, False], architecture="single"),
        ]
        candidate = [
            make_payload([True, True], architecture="routed"),
            make_payload([True, False], architecture="routed"),
            make_payload([True, True], architecture="routed"),
        ]

        with self.assertRaisesRegex(ValueError, "same number"):
            compare_architectures(baseline, candidate, bootstrap_samples=500)


if __name__ == "__main__":
    unittest.main()
