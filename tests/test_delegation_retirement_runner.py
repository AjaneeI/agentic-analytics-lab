import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from src.evals.capability_reliability import build_delegation_prompt


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "m0-5b-delegation-retirement"
RUNNER = EXPERIMENT / "run_study.py"
MANIFEST = EXPERIMENT / "frozen-state.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("m0_5b_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(session_id, timestamp, tools):
    return {
        "session_id": session_id,
        "timestamp": timestamp,
        "request": {"body": {"tools": [
            {"type": "function", "function": {"name": name}} for name in tools
        ]}},
    }


class TestDelegationRetirementManifest(unittest.TestCase):
    def test_manifest_reuses_exact_m0_5_b_contract_with_strict_threshold(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        prior = json.loads(
            (ROOT / "experiments/m0-5-capability-reliability/frozen-state.json").read_text(encoding="utf-8")
        )["studies"]["study_b"]

        study = payload["study"]
        self.assertEqual(study["sample_size"], 3)
        self.assertEqual(study["pass_threshold"], 3)
        self.assertEqual(
            [(case["case_id"], case["child_goal"], case["expected_marker"]) for case in study["cases"]],
            [(case["case_id"], case["child_goal"], case["expected_marker"]) for case in prior["cases"]],
        )
        for case in study["cases"]:
            self.assertEqual(case["parent_prompt"], build_delegation_prompt(case))
        self.assertEqual(payload["retry_policy"], "one scheduled attempt per frozen case; zero reruns after any observed result")
        self.assertEqual(payload["incremental_paid_spend_usd"], 0)
        self.assertFalse(payload["implementation"]["external_enforcement_changed"])


class TestDelegationRetirementRunner(unittest.TestCase):
    def test_parent_request_visibility_proves_post_success_retirement(self):
        runner = load_runner()
        dumps = [
            request("child", "2", ["query_clickhouse", "retrieve_policy"]),
            request("parent", "1", ["delegate_task", "query_clickhouse", "retrieve_policy"]),
            request("parent", "3", ["query_clickhouse", "retrieve_policy"]),
        ]

        result = runner.evaluate_parent_tool_retirement(dumps)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["parent_request_count"], 2)
        self.assertEqual(result["parent_tools_by_request"][0][0], "delegate_task")
        self.assertNotIn("delegate_task", result["parent_tools_by_request"][1])

    def test_repeated_parent_delegation_fails_retirement_acceptance(self):
        runner = load_runner()
        dumps = [
            request("parent", "1", ["delegate_task", "query_clickhouse", "retrieve_policy"]),
            request("parent", "2", ["delegate_task", "query_clickhouse", "retrieve_policy"]),
        ]

        result = runner.evaluate_parent_tool_retirement(dumps)

        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason_code"], "delegate_tool_not_retired")

    def test_missing_or_ambiguous_parent_stream_fails_closed(self):
        runner = load_runner()
        missing = runner.evaluate_parent_tool_retirement([
            request("child", "1", ["query_clickhouse"])
        ])
        ambiguous = runner.evaluate_parent_tool_retirement([
            request("parent-a", "1", ["delegate_task"]),
            request("parent-b", "1", ["delegate_task"]),
        ])

        self.assertFalse(missing["accepted"])
        self.assertEqual(missing["reason_code"], "parent_request_stream_ambiguous")
        self.assertFalse(ambiguous["accepted"])
        self.assertEqual(ambiguous["parent_stream_count"], 2)

    def test_runner_refuses_existing_evidence_directory(self):
        runner = load_runner()
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "evidence"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                runner.prepare_output_directory(existing)


if __name__ == "__main__":
    unittest.main()
