import json
import tempfile
import unittest
from pathlib import Path

from src.agents.single_agent import AgentResult, ToolCallRecord
from src.evals.runner import run_case, run_suite, save_results


class FakeAgent:
    def run(self, question):
        return AgentResult(
            answer=f"Answer to: {question}",
            tool_calls=[
                ToolCallRecord(
                    name="query_clickhouse",
                    arguments={"sql": "SELECT 1"},
                    row_count=1,
                )
            ],
        )


class FailingAgent:
    def run(self, question):
        raise RuntimeError("simulated failure")


class TestEvalRunner(unittest.TestCase):
    def test_successful_case(self):
        case = {
            "id": "Q1",
            "category": "retrieval",
            "question": "Which team?",
        }

        record = run_case(FakeAgent(), case)

        self.assertTrue(record.success)
        self.assertEqual(record.question_id, "Q1")
        self.assertEqual(record.tool_call_count, 1)
        self.assertIsNone(record.error)

    def test_failure_is_recorded(self):
        case = {
            "id": "QX",
            "category": "failure",
            "question": "Break please.",
        }

        record = run_case(FailingAgent(), case)

        self.assertFalse(record.success)
        self.assertIsNone(record.answer)
        self.assertIn("simulated failure", record.error)

    def test_full_question_suite_loads(self):
        records = run_suite(FakeAgent(), "evals/questions.json")

        self.assertEqual(len(records), 6)
        self.assertTrue(all(record.success for record in records))

    def test_results_can_be_saved(self):
        records = run_suite(FakeAgent(), "evals/questions.json")

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.json"
            save_results(records, path)

            payload = json.loads(path.read_text())

            self.assertEqual(payload["summary"]["questions"], 6)
            self.assertEqual(payload["summary"]["successful"], 6)
            self.assertEqual(payload["summary"]["total_tool_calls"], 6)
            self.assertEqual(len(payload["results"]), 6)


if __name__ == "__main__":
    unittest.main()
