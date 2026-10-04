import unittest

from src.evals.statistical_evidence import compare_architectures


def make_payload(task_results, *, architecture, provider="ollama_local", contract_sha="contract-v1"):
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
            "provider": provider,
            "dataset": "synthetic_delivery_seed_42",
            "questions": "evals/questions.json",
            "provenance": {"benchmark_contract_sha256": contract_sha},
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

        self.assertEqual(result["method"], "paired_hierarchical_task_run_bootstrap")
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

    def test_provider_may_differ_across_architectures(self):
        baseline = [
            make_payload([True, False], architecture="single", provider="ollama_local"),
            make_payload([True, False], architecture="single", provider="ollama_local"),
        ]
        candidate = [
            make_payload([True, True], architecture="routed", provider="deterministic_plus_ollama_local"),
            make_payload([True, False], architecture="routed", provider="deterministic_plus_ollama_local"),
        ]

        result = compare_architectures(baseline, candidate, bootstrap_samples=500)

        self.assertEqual(result["providers"]["baseline"], "ollama_local")
        self.assertEqual(
            result["providers"]["candidate"], "deterministic_plus_ollama_local"
        )

    def test_rejects_mismatched_contract_provenance(self):
        baseline = [
            make_payload([True, False], architecture="single", contract_sha="contract-a"),
            make_payload([True, False], architecture="single", contract_sha="contract-a"),
        ]
        candidate = [
            make_payload([True, True], architecture="routed", contract_sha="contract-b"),
            make_payload([True, False], architecture="routed", contract_sha="contract-b"),
        ]

        with self.assertRaisesRegex(ValueError, "provenance"):
            compare_architectures(baseline, candidate, bootstrap_samples=500)

    def test_rejects_non_boolean_task_success(self):
        baseline = [
            make_payload([True, False], architecture="single"),
            make_payload([True, False], architecture="single"),
        ]
        candidate = [
            make_payload([True, True], architecture="routed"),
            make_payload([True, False], architecture="routed"),
        ]
        candidate[0]["results"][0]["task_success"] = None

        with self.assertRaisesRegex(ValueError, "Boolean"):
            compare_architectures(baseline, candidate, bootstrap_samples=500)

    def test_bootstrap_reflects_run_level_variability(self):
        baseline = [
            make_payload([True, False], architecture="single"),
            make_payload([False, True], architecture="single"),
        ]
        candidate = [
            make_payload([True, False], architecture="routed"),
            make_payload([False, True], architecture="routed"),
        ]

        result = compare_architectures(
            baseline, candidate, bootstrap_samples=2000, seed=11
        )
        lower, upper = result["aggregate"]["bootstrap_95_interval_percentage_points"]

        self.assertLess(lower, 0)
        self.assertGreater(upper, 0)

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
