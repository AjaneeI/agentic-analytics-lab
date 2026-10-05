import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = (
    ROOT / "experiments" / "hermes-successor-ab-v1" / "run_benchmark.py"
)


def load_runner():
    spec = importlib.util.spec_from_file_location(
        "hermes_successor_runner", RUNNER
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def successful_events():
    return [
        {
            "event": "delegate_pre",
            "tool": "delegate_task",
            "ok": True,
            "delegate_sequence": 1,
        },
        {
            "tool": "query_clickhouse",
            "ok": True,
            "delegated_child": True,
            "arguments": {"sql": "SELECT fully qualified"},
            "rows": [{"team": "Data", "blocked_pct": 20.9}],
            "evidence_refs": ["structured:delivery_work_items"],
        },
        {
            "tool": "retrieve_policy",
            "ok": True,
            "delegated_child": True,
            "arguments": {"query": "kpi-dictionary"},
            "rows": [],
            "evidence_refs": [
                "policy:kpi-dictionary@1.0#blocker-rate"
            ],
        },
        {
            "event": "delegate_post",
            "tool": "delegate_task",
            "ok": True,
            "status": "ok",
        },
    ]


class TestHermesSuccessorRunner(unittest.TestCase):
    def test_scores_hermes_from_raw_final_and_observed_tool_events(self):
        module = load_runner()
        raw_final = json.dumps(
            {
                "disposition": "answer",
                "answer_text": (
                    "Data has the highest blocker rate at 20.9%. The KPI is "
                    "blocked items divided by active items; this is descriptive "
                    "and does not establish causality."
                ),
                "uncertainty": None,
                "clarification": None,
                "handoff": None,
            }
        )

        result = module.score_hermes_execution(
            ROOT, raw_final, successful_events(), latency_seconds=12.5
        )

        self.assertTrue(result["task_success"])
        self.assertTrue(result["score"]["passed"])
        self.assertEqual(
            result["evidence_refs"],
            [
                "structured:delivery_work_items",
                "policy:kpi-dictionary@1.0#blocker-rate",
            ],
        )
        self.assertEqual(
            result["tool_calls"],
            ["query_clickhouse", "retrieve_policy"],
        )
        self.assertEqual(result["structured_values"]["team"], "Data")
        self.assertEqual(result["structured_values"]["blocked_pct"], 20.9)
        self.assertEqual(result["worker_count"], 1)
        self.assertEqual(result["human_interventions"], 0)
        self.assertEqual(result["retries"], 0)

    def test_rejects_evidence_call_outside_delegated_child(self):
        module = load_runner()
        events = successful_events()
        events[1]["delegated_child"] = False

        with self.assertRaisesRegex(
            ValueError, "delegated child"
        ):
            module.validate_hermes_events(events)

    def test_rejects_missing_or_repeated_delegate(self):
        module = load_runner()
        events = successful_events()
        events.insert(1, dict(events[0]))

        with self.assertRaisesRegex(
            ValueError, "exactly one successful delegate"
        ):
            module.validate_hermes_events(events)

    def test_final_response_is_strict_json_without_fence_cleanup(self):
        module = load_runner()

        with self.assertRaisesRegex(ValueError, "valid JSON"):
            module.score_hermes_execution(
                ROOT,
                '```json\n{"disposition":"answer"}\n```',
                successful_events(),
                latency_seconds=1.0,
            )

    def test_prompt_freezes_one_worker_and_no_retry_contract(self):
        module = load_runner()
        prompt = module.build_hermes_prompt(
            "Identify the highest blocker-rate team."
        )

        self.assertIn("delegate_task exactly once", prompt)
        self.assertIn("exactly one task", prompt)
        self.assertIn("Do not retry", prompt)
        self.assertIn("query_clickhouse", prompt)
        self.assertIn("retrieve_policy", prompt)
        self.assertIn("JSON object only", prompt)


if __name__ == "__main__":
    unittest.main()
