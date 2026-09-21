import unittest

from src.evals.repeatability import (
    build_markdown_summary,
    summarize_repeatability,
    validate_compatible_runs,
)


def make_payload(task_results, *, model="qwen2.5:7b"):
    results = []
    for index, task_success in enumerate(task_results, start=1):
        results.append(
            {
                "question_id": f"Q{index}",
                "category": "test",
                "execution_success": True,
                "correct": task_success,
                "task_success": task_success,
                "failure_type": None if task_success else "incorrect_answer",
            }
        )

    count = sum(task_results)
    return {
        "summary": {
            "questions": len(task_results),
            "execution_successful": len(task_results),
            "task_successful": count,
            "correct": count,
            "failed": len(task_results) - count,
            "total_tool_calls": 2,
            "total_model_calls": 4,
            "total_input_tokens": 1000,
            "total_output_tokens": 200,
            "total_latency_seconds": 10.0,
        },
        "metadata": {
            "benchmark_schema_version": 2,
            "architecture": "single_agent",
            "model": model,
            "provider": "ollama_local",
            "dataset": "synthetic_delivery_seed_42",
            "questions": "evals/questions.json",
        },
        "results": results,
    }


class TestRepeatabilitySummary(unittest.TestCase):
    def test_requires_at_least_two_runs(self):
        with self.assertRaises(ValueError):
            validate_compatible_runs([make_payload([True, False])])

    def test_rejects_mismatched_metadata(self):
        payloads = [
            make_payload([True, False]),
            make_payload([True, False], model="different-model"),
        ]

        with self.assertRaisesRegex(ValueError, "metadata field 'model'"):
            validate_compatible_runs(payloads)

    def test_summarizes_variable_case_behavior(self):
        payloads = [
            make_payload([True, False]),
            make_payload([True, True]),
            make_payload([True, False]),
        ]

        summary = summarize_repeatability(payloads)

        self.assertEqual(summary["run_count"], 3)
        self.assertEqual(summary["aggregate"]["mean_task_success_rate_pct"], 66.7)
        self.assertEqual(summary["per_case"][0]["status"], "stable_pass")
        self.assertEqual(summary["per_case"][1]["status"], "variable")
        self.assertEqual(
            summary["per_case"][1]["failure_types"],
            {"incorrect_answer": 2},
        )

    def test_markdown_includes_run_and_case_tables(self):
        payloads = [
            make_payload([True, False]),
            make_payload([True, True]),
        ]
        summary = summarize_repeatability(payloads)

        report = build_markdown_summary(summary)

        self.assertIn("## Run-level results", report)
        self.assertIn("| 1 | 2/2 | 1/2 | 1/2 | 2 | 4 | 1000 | 200 | 10.000 |", report)
        self.assertIn("| Q2 | test | 1/2 | 1/2 | 2/2 | variable | incorrect_answer × 1 |", report)


if __name__ == "__main__":
    unittest.main()
