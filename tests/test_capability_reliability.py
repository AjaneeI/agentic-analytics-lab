import unittest

from src.evals.capability_reliability import (
    build_delegation_prompt,
    evaluate_delegation_attempt,
    evaluate_sql_attempt,
    summarize_studies,
)


VALID_SQL = (
    "SELECT count() AS row_count "
    "FROM agentic_analytics.delivery_work_items"
)


def sql_tool_call(sql=VALID_SQL):
    return {
        "type": "tool_call",
        "name": "query_clickhouse",
        "arguments": {"sql": sql},
        "_metrics": {"input_tokens": 10, "output_tokens": 12},
    }


def successful_delegation_events():
    return [
        {
            "event": "delegate_pre",
            "tool": "delegate_task",
            "ok": True,
            "arguments": {"tasks": [{"goal": "Return M05_ALPHA_OK"}]},
        },
        {
            "event": "delegate_post",
            "tool": "delegate_task",
            "ok": True,
            "status": "ok",
        },
    ]


class TestSqlCapabilityStudy(unittest.TestCase):
    def test_accepts_one_validator_compliant_call_with_exact_rows(self):
        calls = []

        outcome = evaluate_sql_attempt(
            sql_tool_call(),
            expected_rows=[{"row_count": 500}],
            query_fn=lambda sql: calls.append(sql) or [{"row_count": 500}],
        )

        self.assertTrue(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "accepted")
        self.assertEqual(calls, [VALID_SQL])
        self.assertEqual(outcome["raw_response"], sql_tool_call())

    def test_unqualified_table_is_contract_failure_without_repair(self):
        calls = []

        outcome = evaluate_sql_attempt(
            sql_tool_call("SELECT count() AS row_count FROM delivery_work_items"),
            expected_rows=[{"row_count": 500}],
            query_fn=lambda sql: calls.append(sql),
        )

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "validator_rejected")
        self.assertEqual(
            outcome["failure_categories"], ["tool_contract_understanding"]
        )
        self.assertEqual(calls, [])

    def test_wrong_result_is_instruction_following_failure(self):
        outcome = evaluate_sql_attempt(
            sql_tool_call(),
            expected_rows=[{"row_count": 500}],
            query_fn=lambda _sql: [{"row_count": 499}],
        )

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "unexpected_result")
        self.assertEqual(
            outcome["failure_categories"], ["model_instruction_following"]
        )


class TestDelegationCapabilityStudy(unittest.TestCase):
    def test_accepts_exactly_one_successful_child_and_exact_marker(self):
        outcome = evaluate_delegation_attempt(
            successful_delegation_events(),
            stdout="M05_ALPHA_OK\n",
            returncode=0,
            expected_marker="M05_ALPHA_OK",
        )

        self.assertTrue(outcome["accepted"])
        self.assertEqual(outcome["attempted_delegations"], 1)
        self.assertEqual(outcome["successful_worker_launches"], 1)
        self.assertEqual(outcome["attempted_extra_delegations"], 0)
        self.assertEqual(outcome["parent_level_work_attempts"], 0)
        self.assertEqual(outcome["enforcement_interventions"], 0)
        self.assertTrue(outcome["final_completion"])

    def test_records_malformed_retry_parent_work_and_enforcement(self):
        events = [
            {
                "event": "delegate_pre",
                "tool": "delegate_task",
                "ok": False,
                "reason_code": "single_task_spawn_required",
            },
            {
                "event": "delegate_pre",
                "tool": "delegate_task",
                "ok": False,
                "reason_code": "delegate_budget_exceeded",
            },
            {
                "tool": "query_clickhouse",
                "delegated_child": False,
                "ok": False,
                "reason_code": "parent_evidence_call_forbidden",
            },
        ]

        outcome = evaluate_delegation_attempt(
            events,
            stdout="I could not delegate.",
            returncode=0,
            expected_marker="M05_ALPHA_OK",
        )

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["attempted_delegations"], 2)
        self.assertEqual(outcome["attempted_extra_delegations"], 1)
        self.assertEqual(outcome["parent_level_work_attempts"], 1)
        self.assertEqual(outcome["successful_worker_launches"], 0)
        self.assertEqual(outcome["enforcement_interventions"], 3)
        self.assertEqual(
            outcome["failure_categories"],
            ["orchestration_decomposition", "enforcement_intervention"],
        )

    def test_successful_child_with_wrong_final_marker_is_model_failure(self):
        outcome = evaluate_delegation_attempt(
            successful_delegation_events(),
            stdout="extra M05_ALPHA_OK",
            returncode=0,
            expected_marker="M05_ALPHA_OK",
        )

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "final_output_mismatch")
        self.assertIn(
            "model_instruction_following", outcome["failure_categories"]
        )

    def test_prompt_freezes_one_delegation_and_child_goal(self):
        case = {
            "case_id": "B1_LITERAL",
            "child_goal": "Return exactly M05_ALPHA_OK. No other text.",
            "expected_marker": "M05_ALPHA_OK",
        }

        prompt = build_delegation_prompt(case)

        self.assertIn("delegate_task exactly once", prompt)
        self.assertIn("exactly one task", prompt)
        self.assertIn(case["child_goal"], prompt)
        self.assertIn("Do not retry", prompt)
        self.assertIn("M05_ALPHA_OK", prompt)


class TestCapabilityStudySummary(unittest.TestCase):
    def test_both_strict_thresholds_are_required_for_m0_6_readiness(self):
        summary = summarize_studies(
            study_a=[{"accepted": True}] * 4,
            study_b=[{"accepted": True}] * 3,
            threshold_a=4,
            threshold_b=3,
        )

        self.assertTrue(summary["study_a"]["passed"])
        self.assertTrue(summary["study_b"]["passed"])
        self.assertEqual(summary["decision"], "recommend_m0_6_readiness")

    def test_failed_gate_defines_intervention_experiment_without_rerun(self):
        summary = summarize_studies(
            study_a=[
                {
                    "accepted": False,
                    "failure_categories": ["tool_contract_understanding"],
                },
                *[{"accepted": True}] * 3,
            ],
            study_b=[{"accepted": True}] * 3,
            threshold_a=4,
            threshold_b=3,
        )

        self.assertFalse(summary["study_a"]["passed"])
        self.assertEqual(summary["decision"], "define_next_experiment")
        self.assertEqual(
            summary["observed_failure_categories"],
            ["tool_contract_understanding"],
        )
        self.assertFalse(summary["rerun_authorized"])


if __name__ == "__main__":
    unittest.main()
