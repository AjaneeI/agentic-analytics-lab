import json
import tempfile
import unittest
from pathlib import Path

from src.agents.single_agent import AgentResult, ToolCallRecord
from src.evals.runner import run_case, save_results


class FakeAgent:
    def run(self, question):
        return AgentResult(
            answer="Data has the highest blocker rate at 20.9%.",
            tool_calls=[
                ToolCallRecord(
                    name="query_clickhouse",
                    arguments={"sql": "SELECT team, 20.9 AS blocked_pct"},
                    row_count=1,
                    result_rows=[{"team": "Data", "blocked_pct": 20.9}],
                )
            ],
            model_call_count=2,
            tool_call_attempt_count=1,
            input_tokens=100,
            output_tokens=20,
            model_duration_seconds=1.5,
        )


class FailingAgent:
    def run(self, question):
        raise RuntimeError("simulated failure")


class IncorrectAgent:
    def run(self, question):
        return AgentResult(
            answer="AI has the highest blocker rate at 15.0%.",
            tool_calls=[
                ToolCallRecord(
                    name="query_clickhouse",
                    arguments={"sql": "SELECT team, 15.0 AS blocked_pct"},
                    row_count=1,
                    result_rows=[{"team": "AI", "blocked_pct": 15.0}],
                )
            ],
            model_call_count=2,
            tool_call_attempt_count=1,
        )


class TestEvalRunner(unittest.TestCase):
    def setUp(self):
        self.case = {
            "id": "Q1",
            "category": "retrieval",
            "question": "Which team has the highest blocker rate?",
            "expected": {"team": "Data", "blocked_pct": 20.9},
            "requires_tool": True,
            "max_tool_calls": 1,
        }

    def test_successful_case_means_correct_and_grounded(self):
        record = run_case(FakeAgent(), self.case)

        self.assertTrue(record.execution_success)
        self.assertTrue(record.correct)
        self.assertTrue(record.task_success)
        self.assertTrue(record.success)
        self.assertEqual(record.model_call_count, 2)
        self.assertEqual(record.input_tokens, 100)
        self.assertEqual(record.output_tokens, 20)
        self.assertEqual(record.expected["team"], "Data")
        self.assertIsNone(record.error)

    def test_wrong_answer_executes_but_does_not_pass(self):
        record = run_case(IncorrectAgent(), self.case)

        self.assertTrue(record.execution_success)
        self.assertFalse(record.correct)
        self.assertFalse(record.task_success)
        self.assertEqual(record.failure_type, "incorrect_answer")

    def test_failure_is_recorded(self):
        record = run_case(FailingAgent(), self.case)

        self.assertFalse(record.execution_success)
        self.assertFalse(record.task_success)
        self.assertIsNone(record.answer)
        self.assertEqual(record.failure_type, "execution_error")
        self.assertIn("simulated failure", record.error)

    def test_results_can_be_saved_with_separate_success_counts(self):
        records = [
            run_case(FakeAgent(), self.case),
            run_case(IncorrectAgent(), self.case),
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results.json"
            save_results(records, path)
            payload = json.loads(path.read_text())

            self.assertEqual(payload["summary"]["questions"], 2)
            self.assertEqual(payload["summary"]["execution_successful"], 2)
            self.assertEqual(payload["summary"]["task_successful"], 1)
            self.assertEqual(payload["summary"]["correct"], 1)
            self.assertEqual(payload["summary"]["total_model_calls"], 4)
            self.assertEqual(payload["summary"]["total_input_tokens"], 100)
            self.assertEqual(payload["summary"]["total_output_tokens"], 20)

    def test_frozen_suite_loads(self):
        questions = json.loads(Path("evals/questions.json").read_text())
        self.assertEqual(len(questions), 6)
        self.assertTrue(all("max_tool_calls" in case for case in questions))


if __name__ == "__main__":
    unittest.main()
