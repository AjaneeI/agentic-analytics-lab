import json
from pathlib import Path
import tempfile
import unittest

from src.agents.single_agent import TOOL_SPEC
from src.evals.tool_contract_probe import (
    ATTEMPT_COUNT,
    PROBE_ID,
    PROBE_MESSAGES,
    evaluate_attempt,
    run_probe,
    write_report,
)


VALID_SQL = (
    "SELECT count() AS row_count "
    "FROM agentic_analytics.delivery_work_items"
)


def tool_call(sql=VALID_SQL):
    return {
        "type": "tool_call",
        "name": "query_clickhouse",
        "arguments": {"sql": sql},
        "_metrics": {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_duration_seconds": 1.5,
        },
    }


class ScriptedModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.model = "hermes-local:qwen3.5-9b"

    def respond(self, messages, tools):
        self.calls.append(
            {
                "messages": json.loads(json.dumps(messages)),
                "tools": json.loads(json.dumps(tools)),
            }
        )
        response = self.responses[len(self.calls) - 1]
        if isinstance(response, Exception):
            raise response
        return response


class TestToolContractProbe(unittest.TestCase):
    def test_frozen_probe_contract_is_small_and_not_sb_d01(self):
        self.assertEqual(PROBE_ID, "clickhouse-tool-contract-v1")
        self.assertEqual(ATTEMPT_COUNT, 3)
        serialized = json.dumps(PROBE_MESSAGES)
        self.assertIn("agentic_analytics.delivery_work_items", serialized)
        self.assertNotIn("SB-D01", serialized)
        self.assertNotIn("blocker", serialized.lower())

    def test_valid_existing_tool_call_is_accepted(self):
        outcome = evaluate_attempt(
            tool_call(),
            query_fn=lambda _sql: [{"row_count": 500}],
        )

        self.assertTrue(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "accepted")
        self.assertEqual(outcome["validated_sql"], VALID_SQL)
        self.assertEqual(outcome["result_rows"], [{"row_count": 500}])
        self.assertEqual(outcome["raw_response"], tool_call())

    def test_unqualified_table_fails_closed_without_execution(self):
        calls = []
        outcome = evaluate_attempt(
            tool_call(
                "SELECT count() AS row_count FROM delivery_work_items"
            ),
            query_fn=lambda sql: calls.append(sql),
        )

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "validator_rejected")
        self.assertEqual(calls, [])
        self.assertIn(
            "Only agentic_analytics.delivery_work_items may be queried",
            outcome["error"],
        )

    def test_three_scheduled_attempts_are_not_retried_until_success(self):
        model = ScriptedModel(
            [
                tool_call(),
                {"type": "final", "content": "I will answer directly."},
                tool_call(),
            ]
        )

        report = run_probe(
            model=model,
            query_fn=lambda _sql: [{"row_count": 500}],
        )

        self.assertEqual(len(model.calls), 3)
        self.assertEqual(len(report["attempts"]), 3)
        self.assertEqual(report["accepted_attempts"], 2)
        self.assertFalse(report["passed"])
        self.assertEqual(
            [attempt["reason_code"] for attempt in report["attempts"]],
            ["accepted", "not_tool_call", "accepted"],
        )
        for call in model.calls:
            self.assertEqual(call["messages"], PROBE_MESSAGES)
            self.assertEqual(call["tools"], [TOOL_SPEC])

    def test_exception_is_preserved_as_one_failed_attempt(self):
        model = ScriptedModel(
            [RuntimeError("local model failure"), tool_call(), tool_call()]
        )

        report = run_probe(
            model=model,
            query_fn=lambda _sql: [{"row_count": 500}],
        )

        self.assertEqual(len(model.calls), 3)
        self.assertEqual(report["attempts"][0]["reason_code"], "model_error")
        self.assertEqual(
            report["attempts"][0]["error"],
            "RuntimeError: local model failure",
        )
        self.assertFalse(report["passed"])

    def test_pass_requires_all_three_attempts(self):
        model = ScriptedModel([tool_call(), tool_call(), tool_call()])

        report = run_probe(
            model=model,
            query_fn=lambda _sql: [{"row_count": 500}],
        )

        self.assertEqual(report["accepted_attempts"], 3)
        self.assertTrue(report["passed"])
        self.assertEqual(report["incremental_paid_spend_usd"], 0)
        self.assertEqual(report["retries"], 0)
        self.assertEqual(
            report["model"],
            "hermes-local:qwen3.5-9b",
        )

    def test_raw_report_is_preserved_without_overwrite(self):
        report = {"probe_id": PROBE_ID, "attempts": [{"accepted": False}]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "probe.json"

            write_report(report, output)

            self.assertEqual(json.loads(output.read_text()), report)
            with self.assertRaises(FileExistsError):
                write_report(report, output)


class TestToolContractProbeResultValidation(unittest.TestCase):
    def test_wrong_row_count_is_rejected_deterministically(self):
        outcome = evaluate_attempt(
            tool_call(),
            query_fn=lambda _sql: [{"row_count": 499}],
        )

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "unexpected_result")

    def test_wrong_tool_name_is_rejected_without_execution(self):
        raw = tool_call()
        raw["name"] = "shell"
        calls = []

        outcome = evaluate_attempt(raw, query_fn=lambda sql: calls.append(sql))

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "wrong_tool")
        self.assertEqual(calls, [])

    def test_missing_sql_is_rejected_without_execution(self):
        raw = tool_call()
        raw["arguments"] = {}
        calls = []

        outcome = evaluate_attempt(raw, query_fn=lambda sql: calls.append(sql))

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "invalid_arguments")
        self.assertEqual(calls, [])

    def test_query_execution_error_is_preserved(self):
        def fail(_sql):
            raise RuntimeError("ClickHouse unavailable")

        outcome = evaluate_attempt(tool_call(), query_fn=fail)

        self.assertFalse(outcome["accepted"])
        self.assertEqual(outcome["reason_code"], "execution_error")
        self.assertEqual(
            outcome["error"],
            "RuntimeError: ClickHouse unavailable",
        )


if __name__ == "__main__":
    unittest.main()
