import tempfile
import unittest
from pathlib import Path

from src.evals.reporting import (
    build_markdown_report,
    load_benchmark,
    write_markdown_report,
)


class TestBenchmarkReporting(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "summary": {
                "questions": 2,
                "execution_successful": 2,
                "task_successful": 1,
                "correct": 1,
                "failed": 1,
                "total_tool_calls": 2,
                "total_model_calls": 4,
                "total_input_tokens": 1000,
                "total_output_tokens": 200,
                "total_latency_seconds": 12.5,
            },
            "metadata": {
                "benchmark_schema_version": 2,
                "architecture": "single_agent",
                "model": "qwen2.5:7b",
                "provider": "ollama_local",
                "dataset": "synthetic_delivery_seed_42",
                "api_cost_usd": 0,
                "local_compute_cost_usd": None,
            },
            "results": [
                {
                    "question_id": "Q1",
                    "category": "retrieval",
                    "execution_success": True,
                    "correct": True,
                    "task_success": True,
                    "tool_call_count": 1,
                    "model_call_count": 2,
                    "latency_seconds": 5.0,
                    "failure_type": None,
                    "error": None,
                },
                {
                    "question_id": "Q2",
                    "category": "comparison",
                    "execution_success": True,
                    "correct": False,
                    "task_success": False,
                    "tool_call_count": 1,
                    "model_call_count": 2,
                    "latency_seconds": 7.5,
                    "failure_type": "incorrect_answer",
                    "error": None,
                },
            ],
        }

    def test_report_includes_rates_and_case_rows(self):
        report = build_markdown_report(self.payload)

        self.assertIn("Task success | 1/2 (50.0%)", report)
        self.assertIn("Execution success | 2/2 (100.0%)", report)
        self.assertIn("| Q1 | retrieval | PASS | PASS | PASS | 1 | 2 | 5.000 |", report)
        self.assertIn("| Q2 | comparison | PASS | FAIL | FAIL | 1 | 2 | 7.500 |", report)
        self.assertIn("Q2:** incorrect_answer", report)

    def test_write_and_load_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            import json

            source = Path(tmp) / "benchmark.json"
            output = Path(tmp) / "report.md"
            source.write_text(json.dumps(self.payload))

            loaded = load_benchmark(source)
            written = write_markdown_report(loaded, output)

            self.assertEqual(written, output)
            self.assertTrue(output.exists())
            self.assertIn("# Single-Agent Benchmark Report", output.read_text())

    def test_load_rejects_missing_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            import json

            source = Path(tmp) / "benchmark.json"
            source.write_text(json.dumps({"summary": {}}))

            with self.assertRaises(ValueError):
                load_benchmark(source)


if __name__ == "__main__":
    unittest.main()
