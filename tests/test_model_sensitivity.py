import unittest

from src.evals.model_sensitivity import (
    safe_model_slug,
    summarize_model_groups,
)


def payload(model, task_successful):
    return {
        "summary": {
            "questions": 2,
            "execution_successful": 2,
            "task_successful": task_successful,
            "correct": task_successful,
            "total_tool_calls": 2,
            "total_model_calls": 4,
            "total_input_tokens": 100,
            "total_output_tokens": 20,
            "total_latency_seconds": 10.0,
        },
        "metadata": {
            "benchmark_schema_version": 2,
            "architecture": "single_agent_model_sensitivity",
            "model": model,
            "provider": "ollama_local",
            "dataset": "synthetic_delivery_seed_42",
            "questions": "evals/questions.json",
        },
        "results": [
            {
                "question_id": "T1",
                "category": "retrieval",
                "task_success": True,
                "correct": True,
                "execution_success": True,
                "failure_type": None,
            },
            {
                "question_id": "T2",
                "category": "comparison",
                "task_success": task_successful == 2,
                "correct": task_successful == 2,
                "execution_success": True,
                "failure_type": None if task_successful == 2 else "incorrect_answer",
            },
        ],
    }


class TestModelSensitivity(unittest.TestCase):
    def test_safe_model_slug(self):
        self.assertEqual(safe_model_slug("qwen2.5:7b"), "qwen2.5_7b")
        self.assertEqual(safe_model_slug("org/model name"), "org_model_name")

    def test_empty_model_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            safe_model_slug("  ")

    def test_groups_are_summarized_independently(self):
        groups = {
            "model-a": [payload("model-a", 2), payload("model-a", 2)],
            "model-b": [payload("model-b", 1), payload("model-b", 1)],
        }

        summary = summarize_model_groups(groups)

        self.assertEqual(summary["models"]["model-a"]["run_count"], 2)
        self.assertEqual(
            summary["models"]["model-a"]["aggregate"]["mean_task_success_rate_pct"],
            100.0,
        )
        self.assertEqual(
            summary["models"]["model-b"]["aggregate"]["mean_task_success_rate_pct"],
            50.0,
        )


if __name__ == "__main__":
    unittest.main()
