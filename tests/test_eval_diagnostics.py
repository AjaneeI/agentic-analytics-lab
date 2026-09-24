import unittest

from src.evals.diagnostics import diagnose_payload, diagnose_result


class TestFailureDiagnostics(unittest.TestCase):
    def test_no_tool_attempt_is_tool_selection_failure(self):
        result = {
            "question_id": "Q3",
            "execution_success": True,
            "task_success": False,
            "correct": False,
            "tool_grounded": False,
            "factual_consistency": False,
            "tool_call_attempt_count": 0,
            "tool_call_count": 0,
            "failure_type": "incorrect_answer",
        }

        diagnostic = diagnose_result(result)

        self.assertIsNotNone(diagnostic)
        self.assertEqual(diagnostic.stage, "tool_selection")

    def test_inconsistent_tool_evidence_is_evidence_generation_failure(self):
        result = {
            "question_id": "Q5",
            "execution_success": True,
            "task_success": False,
            "correct": False,
            "tool_grounded": True,
            "factual_consistency": False,
            "tool_call_attempt_count": 1,
            "tool_call_count": 1,
        }

        diagnostic = diagnose_result(result)

        self.assertEqual(diagnostic.stage, "evidence_generation")

    def test_available_evidence_with_wrong_answer_is_answer_reasoning_failure(self):
        result = {
            "question_id": "QX",
            "execution_success": True,
            "task_success": False,
            "correct": False,
            "tool_grounded": True,
            "factual_consistency": True,
            "tool_call_attempt_count": 1,
            "tool_call_count": 1,
        }

        diagnostic = diagnose_result(result)

        self.assertEqual(diagnostic.stage, "answer_reasoning")

    def test_success_is_not_diagnosed(self):
        self.assertIsNone(diagnose_result({"task_success": True}))

    def test_payload_counts_stages(self):
        payload = {
            "results": [
                {
                    "question_id": "Q3",
                    "execution_success": True,
                    "task_success": False,
                    "correct": False,
                    "tool_grounded": False,
                    "factual_consistency": False,
                    "tool_call_attempt_count": 0,
                    "tool_call_count": 0,
                },
                {
                    "question_id": "Q5",
                    "execution_success": True,
                    "task_success": False,
                    "correct": False,
                    "tool_grounded": True,
                    "factual_consistency": False,
                    "tool_call_attempt_count": 1,
                    "tool_call_count": 1,
                },
            ]
        }

        diagnosed = diagnose_payload(payload)

        self.assertEqual(diagnosed["summary"]["failed_cases"], 2)
        self.assertEqual(
            diagnosed["summary"]["stage_counts"],
            {"tool_selection": 1, "evidence_generation": 1},
        )


if __name__ == "__main__":
    unittest.main()
