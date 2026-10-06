import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.evals.system_benchmark.local_worker import _TOOL_SPECS


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = (
    ROOT
    / "experiments"
    / "hermes-successor-ab-v1"
    / "plugin"
    / "system-benchmark-tools"
    / "__init__.py"
)


class FakeContext:
    def __init__(self):
        self.tools = []
        self.hooks = []

    def register_tool(self, **kwargs):
        self.tools.append(kwargs)

    def register_hook(self, name, handler):
        self.hooks.append((name, handler))


def load_plugin():
    spec = importlib.util.spec_from_file_location(
        "hermes_successor_benchmark_plugin", PLUGIN
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestHermesSuccessorPlugin(unittest.TestCase):
    def test_register_exposes_only_the_two_frozen_evidence_tools(self):
        module = load_plugin()
        context = FakeContext()

        module.register(context)

        self.assertEqual(
            [(tool["name"], tool["toolset"]) for tool in context.tools],
            [
                ("query_clickhouse", "system_benchmark"),
                ("retrieve_policy", "system_benchmark"),
            ],
        )
        for tool in context.tools:
            frozen = _TOOL_SPECS[tool["name"]]
            self.assertEqual(tool["schema"]["description"], frozen["description"])
            self.assertEqual(
                tool["schema"]["parameters"], frozen["input_schema"]
            )
        self.assertEqual(
            [name for name, _ in context.hooks],
            ["pre_tool_call", "post_tool_call"],
        )

    def test_policy_handler_uses_real_repository_retrieval_and_logs_evidence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "AAL_REPO_ROOT": str(ROOT),
                "AAL_EVIDENCE_LOG": str(Path(directory) / "calls.jsonl"),
            },
            clear=False,
        ):
            module = load_plugin()
            context = FakeContext()
            module.register(context)
            handler = next(
                tool["handler"]
                for tool in context.tools
                if tool["name"] == "retrieve_policy"
            )

            with patch.object(
                module, "_is_delegated_child_context", return_value=True
            ):
                result = json.loads(
                    handler({"query": "kpi-dictionary", "top_k": 2})
                )

            self.assertTrue(result["ok"])
            self.assertEqual(result["tool"], "retrieve_policy")
            self.assertEqual(len(result["rows"]), 2)
            self.assertIn(
                "policy:kpi-dictionary@1.0#blocker-rate",
                result["evidence_refs"],
            )
            events = [
                json.loads(line)
                for line in (Path(directory) / "calls.jsonl").read_text().splitlines()
            ]
            self.assertEqual(events[0]["tool"], "retrieve_policy")
            self.assertTrue(events[0]["ok"])

    def test_query_rejection_is_fail_closed_and_recorded(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "AAL_REPO_ROOT": str(ROOT),
                "AAL_EVIDENCE_LOG": str(Path(directory) / "calls.jsonl"),
            },
            clear=False,
        ):
            module = load_plugin()
            context = FakeContext()
            module.register(context)
            handler = next(
                tool["handler"]
                for tool in context.tools
                if tool["name"] == "query_clickhouse"
            )

            with patch.object(
                module, "_is_delegated_child_context", return_value=True
            ):
                result = json.loads(
                    handler(
                        {
                            "sql": (
                                "SELECT team FROM delivery_work_items LIMIT 1"
                            )
                        }
                    )
                )

            self.assertFalse(result["ok"])
            self.assertEqual(result["reason_code"], "query_rejected")
            self.assertIn(
                "Only agentic_analytics.delivery_work_items may be queried",
                result["error"],
            )
            event = json.loads(
                (Path(directory) / "calls.jsonl").read_text().strip()
            )
            self.assertFalse(event["ok"])
            self.assertEqual(event["reason_code"], "query_rejected")

    def test_third_evidence_call_is_blocked_by_task_budget(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "AAL_REPO_ROOT": str(ROOT),
                "AAL_EVIDENCE_LOG": str(Path(directory) / "calls.jsonl"),
            },
            clear=False,
        ):
            module = load_plugin()
            context = FakeContext()
            module.register(context)
            policy = next(
                tool["handler"]
                for tool in context.tools
                if tool["name"] == "retrieve_policy"
            )

            with patch.object(
                module, "_is_delegated_child_context", return_value=True
            ):
                self.assertTrue(json.loads(policy({"query": "blocker rate"}))["ok"])
                self.assertTrue(json.loads(policy({"query": "blocker rate"}))["ok"])
                blocked = json.loads(policy({"query": "blocker rate"}))

            self.assertFalse(blocked["ok"])
            self.assertEqual(blocked["reason_code"], "tool_budget_exceeded")

    def test_parent_cannot_call_evidence_tools_directly(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "AAL_REPO_ROOT": str(ROOT),
                "AAL_EVIDENCE_LOG": str(Path(directory) / "calls.jsonl"),
            },
            clear=False,
        ):
            module = load_plugin()
            context = FakeContext()
            module.register(context)
            policy = next(
                tool["handler"]
                for tool in context.tools
                if tool["name"] == "retrieve_policy"
            )

            with patch.object(
                module, "_is_delegated_child_context", return_value=False
            ):
                blocked = json.loads(policy({"query": "blocker rate"}))

            self.assertFalse(blocked["ok"])
            self.assertEqual(
                blocked["reason_code"], "parent_evidence_call_forbidden"
            )

    def test_delegate_hook_allows_exactly_one_single_task_spawn(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "AAL_REPO_ROOT": str(ROOT),
                "AAL_EVIDENCE_LOG": str(Path(directory) / "calls.jsonl"),
            },
            clear=False,
        ):
            module = load_plugin()
            context = FakeContext()
            module.register(context)
            pre = next(handler for name, handler in context.hooks if name == "pre_tool_call")

            allowed = pre(
                tool_name="delegate_task",
                args={"tasks": [{"goal": "bounded task"}]},
                tool_call_id="call-1",
            )
            second = pre(
                tool_name="delegate_task",
                args={"tasks": [{"goal": "bounded task"}]},
                tool_call_id="call-2",
            )

            self.assertIsNone(allowed)
            self.assertEqual(second["action"], "block")
            self.assertIn("exactly one", second["message"])

    def test_delegate_hook_rejects_multi_task_spawn(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {
                "AAL_REPO_ROOT": str(ROOT),
                "AAL_EVIDENCE_LOG": str(Path(directory) / "calls.jsonl"),
            },
            clear=False,
        ):
            module = load_plugin()
            context = FakeContext()
            module.register(context)
            pre = next(handler for name, handler in context.hooks if name == "pre_tool_call")

            blocked = pre(
                tool_name="delegate_task",
                args={"tasks": [{"goal": "one"}, {"goal": "two"}]},
                tool_call_id="call-1",
            )

            self.assertEqual(blocked["action"], "block")
            self.assertIn("one task", blocked["message"])


if __name__ == "__main__":
    unittest.main()
