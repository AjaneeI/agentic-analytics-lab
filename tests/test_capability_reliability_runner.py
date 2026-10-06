import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "m0-5-capability-reliability"
RUNNER = EXPERIMENT / "run_studies.py"
MANIFEST = EXPERIMENT / "frozen-state.json"


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "m0_5_capability_reliability_runner", RUNNER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScriptedModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.model = "hermes-local:qwen3.5-9b"

    def respond(self, messages, tools):
        self.calls.append({"messages": messages, "tools": tools})
        response = self.responses[len(self.calls) - 1]
        if isinstance(response, Exception):
            raise response
        return response


class TestCapabilityReliabilityManifest(unittest.TestCase):
    def test_manifest_freezes_small_strict_studies(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "m0-5-capability-reliability-v1")
        self.assertEqual(payload["repository"]["freeze_ref"], "refs/tags/m0-5-capability-reliability-v1")
        self.assertEqual(payload["runtime"]["model"]["name"], "hermes-local:qwen3.5-9b")
        self.assertEqual(payload["runtime"]["context_length"], 65536)
        self.assertEqual(payload["runtime"]["model"]["worker_temperature"], 0)
        self.assertEqual(payload["retry_policy"], "one scheduled attempt per case; zero retries")
        self.assertEqual(payload["incremental_paid_spend_usd"], 0)

        study_a = payload["studies"]["study_a"]
        self.assertEqual(study_a["sample_size"], 4)
        self.assertEqual(study_a["pass_threshold"], 4)
        self.assertEqual(len(study_a["cases"]), 4)
        self.assertEqual(
            {case["case_id"] for case in study_a["cases"]},
            {"A1_TOTAL_COUNT", "A2_LARGEST_TEAM", "A3_CRITICAL_COUNT", "A4_STATUS_COUNTS"},
        )
        for case in study_a["cases"]:
            self.assertNotIn("SELECT", case["user_prompt"].upper())
            self.assertTrue(case["expected_rows"])

        study_b = payload["studies"]["study_b"]
        self.assertEqual(study_b["sample_size"], 3)
        self.assertEqual(study_b["pass_threshold"], 3)
        self.assertEqual(len(study_b["cases"]), 3)
        self.assertEqual(payload["installed_state"]["visible_tools"], ["delegate_task", "query_clickhouse", "retrieve_policy"])
        self.assertEqual(payload["one_worker_enforcement"]["max_concurrent_children"], 1)
        self.assertEqual(
            set(payload["contract_sha256"]),
            {
                "experiments/m0-5-capability-reliability/README.md",
                "experiments/m0-5-capability-reliability/run_studies.py",
                "src/evals/capability_reliability.py",
                "src/agents/ollama_client.py",
                "src/agents/single_agent.py",
                "src/tools/clickhouse_readonly.py",
                "experiments/hermes-successor-ab-v1/profile/config.yaml",
                "experiments/hermes-successor-ab-v1/plugin/system-benchmark-tools/__init__.py",
                "experiments/hermes-successor-ab-v1/plugin/system-benchmark-tools/plugin.yaml",
            },
        )


class TestCapabilityReliabilityRunner(unittest.TestCase):
    def test_study_a_schedules_each_case_once_and_preserves_model_error(self):
        runner = load_runner()
        cases = [
            {"case_id": "A1", "user_prompt": "one", "expected_rows": [{"row_count": 500}]},
            {"case_id": "A2", "user_prompt": "two", "expected_rows": [{"row_count": 500}]},
        ]
        valid = {
            "type": "tool_call",
            "name": "query_clickhouse",
            "arguments": {"sql": "SELECT count() AS row_count FROM agentic_analytics.delivery_work_items"},
        }
        model = ScriptedModel([valid, RuntimeError("model unavailable")])

        attempts = runner.run_study_a_cases(
            model=model,
            cases=cases,
            system_prompt="frozen",
            tool_spec={"name": "query_clickhouse"},
            query_fn=lambda _sql: [{"row_count": 500}],
        )

        self.assertEqual(len(model.calls), 2)
        self.assertEqual([item["case_id"] for item in attempts], ["A1", "A2"])
        self.assertTrue(attempts[0]["accepted"])
        self.assertFalse(attempts[1]["accepted"])
        self.assertEqual(attempts[1]["reason_code"], "model_error")
        self.assertEqual(attempts[1]["failure_categories"], ["infrastructure_runtime"])
        self.assertEqual(attempts[1]["raw_response"], None)

    def test_runner_refuses_existing_evidence_directory(self):
        runner = load_runner()
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "evidence"
            existing.mkdir()

            with self.assertRaises(FileExistsError):
                runner.prepare_output_directory(existing)

    def test_next_experiment_targets_only_observed_failed_gate(self):
        runner = load_runner()
        summary = {
            "study_a": {"passed": False},
            "study_b": {"passed": True},
            "observed_failure_categories": ["tool_contract_understanding"],
        }

        decision = runner.define_next_experiment(summary)

        self.assertEqual(decision["target"], "study_a_sql_contract")
        self.assertEqual(decision["intervention"], "qualified-table instruction visibility")
        self.assertEqual(decision["status"], "defined_not_executed")
        self.assertFalse(decision["same_study_rerun_authorized"])


if __name__ == "__main__":
    unittest.main()
