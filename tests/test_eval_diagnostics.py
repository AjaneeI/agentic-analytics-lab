import unittest

from src.evals.diagnostics import diagnose_payload, diagnose_record


class TestFailureStageDiagnostics(unittest.TestCase):
    def setUp(self):
        self.tool_case = {
            "id": "Q1",
            "category": "retrieval",
            "question": "Which team has the highest blocker rate?",
            "expected": {"team": "Data", "blocked_pct": 20.9},
            "requires_tool": True,
            "max_tool_calls": 1,
        }
        self.no_tool_case = {
            "id": "Q6",
            "category": "epistemic",
            "question": "Can this dataset establish causality?",
            "expected_behavior": ["does_not_claim_causality"],
            "requires_tool": False,
            "max_tool_calls": 0,
        }

    def _record(self, **overrides):
        record = {
            "question_id": "Q1",
            "execution_success": True,
            "correct": True,
            "task_success": True,
            "factual_consistency": True,
            "tool_grounded": True,
            "tool_evidence": [
                {
                    "name": "query_clickhouse",
                    "arguments": {
                        "sql": (
                            "SELECT team, 20.9 AS blocked_pct "
                            "FROM agentic_analytics.delivery_work_items"
                        )
                    },
                    "row_count": 1,
                    "result_rows": [{"team": "Data", "blocked_pct": 20.9}],
                }
            ],
            "tool_call_count": 1,
            "tool_call_attempt_count": 1,
            "failure_type": None,
            "error": None,
            "unsupported_claims": [],
        }
        record.update(overrides)
        return record

    def test_required_tool_missing_is_tool_selection_failure(self):
        record = self._record(
            correct=False,
            task_success=False,
            factual_consistency=False,
            tool_grounded=False,
            tool_evidence=[],
            tool_call_count=0,
            tool_call_attempt_count=0,
        )
        result = diagnose_record(record, self.tool_case)

        self.assertEqual(result.primary_failure_stage, "tool_selection")
        self.assertEqual(result.primary_reason_code, "tool_not_called")
        self.assertEqual(
            result.stage_outcomes["query_validation"].state,
            "not_reached",
        )

    def test_no_tool_case_passes_without_tool_invocation(self):
        record = self._record(
            question_id="Q6",
            correct=True,
            task_success=True,
            factual_consistency=None,
            tool_grounded=None,
            tool_evidence=[],
            tool_call_count=0,
            tool_call_attempt_count=0,
        )
        result = diagnose_record(record, self.no_tool_case)

        self.assertEqual(result.primary_failure_stage, "none")
        self.assertEqual(result.stage_outcomes["tool_selection"].state, "passed")
        self.assertEqual(
            result.stage_outcomes["query_execution"].state,
            "not_applicable",
        )

    def test_rejected_query_is_query_validation_failure(self):
        record = self._record(
            execution_success=False,
            correct=None,
            task_success=False,
            factual_consistency=None,
            tool_grounded=None,
            tool_evidence=[],
            tool_call_count=0,
            tool_call_attempt_count=1,
            failure_type="execution_error",
            error="QueryRejected: Mutation or administrative keyword detected.",
        )
        result = diagnose_record(record, self.tool_case)

        self.assertEqual(result.primary_failure_stage, "query_validation")
        self.assertEqual(result.primary_reason_code, "query_rejected")
        self.assertEqual(
            result.stage_outcomes["query_execution"].state,
            "not_reached",
        )

    def test_clickhouse_failure_is_query_execution_failure(self):
        record = self._record(
            execution_success=False,
            correct=None,
            task_success=False,
            factual_consistency=None,
            tool_grounded=None,
            tool_evidence=[],
            tool_call_count=0,
            tool_call_attempt_count=1,
            failure_type="execution_error",
            error="RuntimeError: ClickHouse query failed: connection refused",
        )
        result = diagnose_record(record, self.tool_case)

        self.assertEqual(result.stage_outcomes["query_validation"].state, "passed")
        self.assertEqual(result.primary_failure_stage, "query_execution")
        self.assertEqual(result.primary_reason_code, "query_execution_error")

    def test_incomplete_evidence_is_evidence_coverage_failure(self):
        record = self._record(
            correct=False,
            task_success=False,
            factual_consistency=False,
            unsupported_claims=[
                "Required answer values were not found together in captured tool evidence."
            ],
        )
        result = diagnose_record(record, self.tool_case)

        self.assertEqual(result.primary_failure_stage, "evidence_coverage")
        self.assertEqual(result.primary_reason_code, "required_rows_missing")
        self.assertEqual(
            result.stage_outcomes["answer_synthesis"].state,
            "not_reached",
        )

    def test_correct_evidence_wrong_answer_is_answer_synthesis_failure(self):
        record = self._record(correct=False, task_success=False)
        result = diagnose_record(record, self.tool_case)

        self.assertEqual(result.primary_failure_stage, "answer_synthesis")
        self.assertEqual(result.primary_reason_code, "answer_value_incorrect")
        self.assertEqual(result.stage_outcomes["evidence_coverage"].state, "passed")

    def test_successful_record_has_no_failure_stage(self):
        result = diagnose_record(self._record(), self.tool_case)

        self.assertTrue(result.diagnosis_complete)
        self.assertEqual(result.primary_failure_stage, "none")
        self.assertEqual(result.stage_outcomes["validation"].state, "passed")

    def test_validator_rejection_is_only_used_without_earlier_failure(self):
        record = self._record(task_success=False)
        result = diagnose_record(record, self.tool_case)

        self.assertEqual(result.primary_failure_stage, "validation")
        self.assertEqual(result.primary_reason_code, "validator_rejected")

    def test_payload_keeps_existing_result_schema_read_only(self):
        payload = {
            "summary": {"questions": 1},
            "results": [self._record()],
        }
        result = diagnose_payload(payload, [self.tool_case])

        self.assertEqual(result["diagnostics_version"], "1")
        self.assertEqual(result["source_summary"], {"questions": 1})
        self.assertEqual(result["summary"]["records"], 1)
        self.assertEqual(
            result["summary"]["primary_failure_stage_counts"],
            {"none": 1},
        )
        self.assertEqual(result["results"][0]["question_id"], "Q1")


if __name__ == "__main__":
    unittest.main()
