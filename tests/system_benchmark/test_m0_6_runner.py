import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "experiments" / "m0-6-fresh-sb-d01-ab"
RUNNER = EXPERIMENT / "run_benchmark.py"
MANIFEST = EXPERIMENT / "frozen-state.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("m0_6_runner", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def request(session_id, timestamp, tools):
    return {
        "session_id": session_id,
        "timestamp": timestamp,
        "request": {
            "body": {
                "tools": [
                    {"type": "function", "function": {"name": name}}
                    for name in tools
                ]
            }
        },
    }


class TestM06Manifest(unittest.TestCase):
    def test_manifest_freezes_fresh_m0_6_contract(self):
        payload = json.loads(MANIFEST.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "m0-6-fresh-sb-d01-ab-v1")
        self.assertEqual(
            payload["repository"]["base_commit"],
            "655e5891398e1b8d2be2a3eea13df9251a90b232",
        )
        self.assertEqual(
            payload["repository"]["freeze_ref"],
            "refs/tags/m0-6-fresh-sb-d01-ab-v1",
        )
        self.assertEqual(
            payload["repository"]["branch"], "m0-6-fresh-sb-d01-ab"
        )
        self.assertEqual(
            payload["benchmark"]["task"],
            "Identify the highest blocker-rate team and interpret it using the KPI definition without claiming causality.",
        )
        self.assertEqual(
            payload["benchmark"]["allowed_tools"],
            ["query_clickhouse", "retrieve_policy"],
        )
        self.assertEqual(
            payload["benchmark"]["response_contract"],
            "SystemBenchmarkResponse",
        )
        self.assertEqual(payload["benchmark"]["treatment_order"], ["direct", "hermes"])
        self.assertEqual(payload["benchmark"]["retry_policy"], "one_attempt_per_treatment_no_retries")
        self.assertEqual(payload["benchmark"]["incremental_paid_spend_usd"], 0)
        self.assertEqual(payload["runtime"]["context_length"], 65536)
        self.assertEqual(payload["runtime"]["model"]["worker_temperature"], 0)
        self.assertEqual(
            payload["installed_state"]["visible_tools_before_success"],
            ["delegate_task", "query_clickhouse", "retrieve_policy"],
        )
        self.assertEqual(
            payload["installed_state"]["visible_tools_after_success"],
            ["query_clickhouse", "retrieve_policy"],
        )
        self.assertEqual(
            payload["implementation"]["patched_sha256"],
            "df65f6506c03d8533ee695a1266cc23739b4d0ad43715d0408e79fb8a2e35405",
        )


class TestM06Runner(unittest.TestCase):
    def test_parent_request_stream_proves_post_success_retirement(self):
        module = load_runner()
        result = module.evaluate_parent_tool_retirement(
            [
                request(
                    "parent",
                    "1",
                    ["delegate_task", "query_clickhouse", "retrieve_policy"],
                ),
                request("child", "2", ["query_clickhouse", "retrieve_policy"]),
                request("parent", "3", ["query_clickhouse", "retrieve_policy"]),
            ]
        )

        self.assertTrue(result["accepted"])
        self.assertEqual(result["parent_request_count"], 2)
        self.assertIn("delegate_task", result["parent_tools_by_request"][0])
        self.assertNotIn("delegate_task", result["parent_tools_by_request"][1])

    def test_comparison_keeps_answer_and_orchestration_acceptance_separate(self):
        module = load_runner()
        score = {
            "task_success": True,
            "score": {
                "passed": True,
                "dimensions": [{"passed": True}],
                "reason_codes": [],
            },
            "latency_seconds": 10.0,
            "model_calls": 3,
            "tool_call_count": 2,
        }
        hermes = {
            **score,
            "orchestration_accepted": True,
            "delegation_count": 1,
            "child_count": 1,
            "enforcement_interventions": 0,
            "parent_evidence_tool_calls": 0,
            "post_success_delegate_task_retired": True,
        }

        comparison = module.build_comparison(score, hermes, {})

        self.assertTrue(comparison["direct"]["deterministic_acceptance"])
        self.assertTrue(comparison["hermes"]["deterministic_acceptance"])
        self.assertTrue(comparison["hermes"]["answer_score_passed"])
        self.assertTrue(comparison["hermes"]["orchestration_accepted"])
        self.assertEqual(comparison["hermes"]["delegation_count"], 1)
        self.assertEqual(comparison["hermes"]["child_count"], 1)
        self.assertEqual(comparison["hermes"]["enforcement_interventions"], 0)
        self.assertTrue(comparison["hermes"]["post_success_delegate_task_retired"])
        self.assertEqual(comparison["incremental_paid_spend_usd"], 0)

    def test_enforcement_intervention_counts_one_blocked_tool_call_once(self):
        module = load_runner()
        events = [
            {
                "event": "delegate_pre",
                "tool": "delegate_task",
                "tool_call_id": "blocked-1",
                "ok": False,
            },
            {
                "event": "delegate_post",
                "tool": "delegate_task",
                "tool_call_id": "blocked-1",
                "ok": False,
            },
        ]

        observed = module._orchestration_observation(events, [])

        self.assertEqual(observed["enforcement_interventions"], 1)

    def test_evidence_index_hashes_nested_raw_request_files(self):
        module = load_runner()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "treatment-b-raw-requests" / "request.json"
            nested.parent.mkdir()
            nested.write_text("{}\n", encoding="utf-8")

            payload = module.build_evidence_index(root)

        self.assertIn(
            "treatment-b-raw-requests/request.json", payload["files"]
        )

    def test_m1_readiness_requires_valid_bounded_hermes_result(self):
        module = load_runner()
        hermes = {
            "task_success": True,
            "orchestration_accepted": True,
            "delegation_count": 1,
            "child_count": 1,
            "enforcement_interventions": 0,
            "parent_evidence_tool_calls": 0,
            "post_success_delegate_task_retired": True,
            "retries": 0,
            "incremental_paid_spend_usd": 0,
        }

        decision = module.determine_m1_readiness(hermes, {})

        self.assertTrue(decision["ready"])
        self.assertEqual(
            decision["verdict"],
            "M0 complete — M1 bounded Personal Ops recommended",
        )

        hermes["post_success_delegate_task_retired"] = False
        blocked = module.determine_m1_readiness(hermes, {})
        self.assertFalse(blocked["ready"])
        self.assertIn("post_success_delegate_task_retired", blocked["failed_checks"])

    def test_runner_refuses_existing_evidence_directory(self):
        module = load_runner()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                module.prepare_output_directory(Path(directory))


if __name__ == "__main__":
    unittest.main()
