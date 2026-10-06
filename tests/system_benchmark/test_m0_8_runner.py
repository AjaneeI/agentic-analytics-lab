import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from src.evals.system_benchmark.local_worker import _SYSTEM_PROMPT


ROOT = Path(__file__).resolve().parents[2]
RUNNER = (
    ROOT
    / "experiments"
    / "m0-8-final-bounded-validation"
    / "run_validation.py"
)
RECOVERY_RUNNER = (
    ROOT
    / "experiments"
    / "m0-8-recovery-successor"
    / "run_validation.py"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("m0_8_runner", RUNNER)
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
                    {"function": {"name": name}}
                    for name in tools
                ]
            }
        },
    }


class TestM08Runner(unittest.TestCase):
    def test_recovery_runner_loads_without_invoking_hermes(self):
        import subprocess
        import sys

        completed = subprocess.run(
            [sys.executable, str(RECOVERY_RUNNER), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--verify-only", completed.stdout)

    def test_worker_prompt_requires_one_sequential_call_per_evidence_tool(self):
        normalized = " ".join(_SYSTEM_PROMPT.split())
        self.assertIn(
            "Call retrieve_policy exactly once before query_clickhouse.",
            normalized,
        )
        self.assertIn(
            "Do not batch them in the same assistant response",
            normalized,
        )

    def test_retirement_accepts_every_post_success_parent_request_without_delegate(self):
        runner = load_runner()
        dumps = [
            request("parent", "1", ["delegate_task", "query_clickhouse"]),
            request("child", "2", ["query_clickhouse", "retrieve_policy"]),
            request("parent", "3", ["query_clickhouse", "retrieve_policy"]),
            request("parent", "4", ["query_clickhouse", "retrieve_policy"]),
        ]

        result = runner.evaluate_parent_tool_retirement(dumps)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["parent_request_count"], 3)
        self.assertNotIn("delegate_task", result["parent_tools_by_request"][1])
        self.assertNotIn("delegate_task", result["parent_tools_by_request"][2])

    def test_retirement_rejects_delegate_reappearing_later(self):
        runner = load_runner()
        dumps = [
            request("parent", "1", ["delegate_task", "query_clickhouse"]),
            request("parent", "2", ["query_clickhouse"]),
            request("parent", "3", ["delegate_task", "query_clickhouse"]),
        ]

        result = runner.evaluate_parent_tool_retirement(dumps)

        self.assertFalse(result["accepted"])
        self.assertEqual(result["reason_code"], "delegate_tool_not_retired")

    def test_repository_request_copy_redacts_only_authorization(self):
        runner = load_runner()
        payload = {
            "session_id": "parent",
            "request": {
                "headers": {
                    "Authorization": "Bearer local-secret",
                    "Content-Type": "application/json",
                },
                "body": {"messages": [{"role": "user", "content": "task"}]},
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.json"
            destination = Path(directory) / "copy.json"
            source.write_text(json.dumps(payload), encoding="utf-8")

            original, record = runner._sanitize_request_copy(source, destination)
            sanitized = json.loads(destination.read_text(encoding="utf-8"))

        self.assertEqual(original, payload)
        self.assertEqual(
            sanitized["request"]["headers"]["Authorization"],
            "<redacted-local-loopback-credential>",
        )
        self.assertEqual(
            sanitized["request"]["headers"]["Content-Type"],
            "application/json",
        )
        self.assertEqual(sanitized["request"]["body"], payload["request"]["body"])
        self.assertEqual(
            record["redacted_fields"], ["request.headers.Authorization"]
        )


if __name__ == "__main__":
    unittest.main()
