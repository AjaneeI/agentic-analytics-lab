import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from personalops.install import install_profile
from personalops.smoke import run_smoke, score_attempt


ROOT = Path(__file__).resolve().parents[1]


class TestPersonalOpsSmokeScoring(unittest.TestCase):
    def setUp(self):
        self.repo = {
            "repository_root": "/tmp/repo",
            "branch": "feat/hermes-desktop-lite",
            "head": "abc123",
        }
        self.validation = {"accepted": True, "checks": {"runtime_guard": True}, "errors": []}
        self.usage = {
            "completed": True,
            "failed": False,
            "model": "hermes-local:qwen3.5-9b",
            "provider": "custom",
            "estimated_cost_usd": 0.0,
            "total_including_auxiliary": {"estimated_cost_usd": 0.0, "api_calls": 2},
        }
        self.events = [
            {
                "tool": "personalops_inspect_repository",
                "ok": True,
                "repository_root": "/tmp/repo",
                "branch": "feat/hermes-desktop-lite",
                "head": "abc123",
                "recommended_action": "run_context_and_full_checks",
            },
            {"tool": "personalops_run_check", "ok": True, "check_id": "full"},
            {
                "tool": "personalops_record_outcome",
                "ok": True,
                "outcome": {
                    "current_state": "clean",
                    "recommended_action": "run checks",
                    "action_taken": "ran full check",
                    "verification": "passed",
                    "decision_needed": "none",
                },
            },
        ]
        self.requests = [
            {
                "request": {
                    "url": "http://127.0.0.1:11434/v1/chat/completions",
                    "body": {
                        "messages": [{"role": "user", "content": "check the repository"}],
                        "tools": [
                            {"type": "function", "function": {"name": "clarify"}},
                            {"type": "function", "function": {"name": "delegate_task"}},
                            {
                                "type": "function",
                                "function": {"name": "personalops_inspect_repository"},
                            },
                            {
                                "type": "function",
                                "function": {"name": "personalops_run_check"},
                            },
                            {
                                "type": "function",
                                "function": {"name": "personalops_record_outcome"},
                            },
                        ],
                    },
                }
            }
        ]

    def score(self, **changes):
        values = {
            "repository_state": self.repo,
            "profile_validation": self.validation,
            "returncode": 0,
            "stdout": "The full check passed.",
            "stderr": "",
            "usage": self.usage,
            "events": self.events,
            "requests": self.requests,
        }
        values.update(changes)
        return score_attempt(**values)

    def test_accepts_complete_green_workflow(self):
        result = self.score()

        self.assertTrue(result["accepted"])
        self.assertTrue(all(result["checks"].values()))

    def test_rejects_clickhouse_tool_use(self):
        result = self.score(events=self.events + [{"tool": "query_clickhouse", "ok": True}])

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["no_clickhouse"])

    def test_rejects_more_than_one_delegation(self):
        delegated = [
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
        ]
        result = self.score(events=self.events + delegated)

        self.assertFalse(result["checks"]["one_worker"])

    def test_rejects_unverified_yellow_work(self):
        result = self.score(
            events=self.events
            + [
                {"tool": "delegate_task", "phase": "pre", "action": "allow"},
                {"tool": "delegate_task", "phase": "post", "completed": True},
            ],
            requests=[self.retired_request()],
        )

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["yellow_independently_verified"])

    def test_rejects_red_execution_instead_of_approval(self):
        result = self.score(events=self.events + [{"tool": "send_message", "phase": "pre", "action": "allow"}])

        self.assertFalse(result["checks"]["no_red_execution"])

    def test_rejects_nonzero_paid_usage(self):
        usage = dict(self.usage)
        usage["total_including_auxiliary"] = {"estimated_cost_usd": 0.01, "api_calls": 2}

        result = self.score(usage=usage)

        self.assertFalse(result["checks"]["zero_paid_spend"])

    def test_rejects_missing_structured_outcome(self):
        result = self.score(events=self.events[:-1])

        self.assertFalse(result["checks"]["structured_outcome"])

    def test_rejects_wrong_live_repository_identity(self):
        events = [dict(row) for row in self.events]
        events[0]["head"] = "wrong"

        result = self.score(events=events)

        self.assertFalse(result["checks"]["repository_identity"])

    def test_accepts_one_verified_child_with_observable_retirement(self):
        events = self.events + [
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
            {"tool": "delegate_task", "phase": "post", "completed": True},
            {"tool": "personalops_apply_patch", "ok": True, "path": "notes.txt"},
            {"tool": "personalops_verify_change", "ok": True, "changed_paths": ["notes.txt"]},
        ]

        result = self.score(events=events, requests=[self.retired_request()])

        self.assertTrue(result["accepted"])
        self.assertTrue(result["checks"]["post_child_retirement"])

    def test_rejects_child_without_observable_retirement(self):
        events = self.events + [
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
            {"tool": "delegate_task", "phase": "post", "completed": True},
            {"tool": "personalops_verify_change", "ok": True, "changed_paths": []},
        ]
        request = self.retired_request()
        request["request"]["body"]["tools"].append(
            {"type": "function", "function": {"name": "delegate_task"}}
        )

        result = self.score(events=events, requests=[request])

        self.assertFalse(result["checks"]["post_child_retirement"])

    def test_red_decision_requires_clarify_observation(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["decision_needed"] = "approve push"

        missing = self.score(events=events)
        present = self.score(
            events=events + [{"tool": "clarify", "phase": "pre", "action": "allow"}]
        )

        self.assertFalse(missing["checks"]["red_uses_approval"])
        self.assertTrue(present["checks"]["red_uses_approval"])

    @staticmethod
    def retired_request():
        return {
            "request": {
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "body": {
                    "messages": [
                        {
                            "role": "assistant",
                            "tool_calls": [
                                {"type": "function", "function": {"name": "delegate_task"}}
                            ],
                        },
                        {"role": "tool", "content": "child completed"},
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {"name": "personalops_verify_change"},
                        }
                    ],
                }
            }
        }


class TestPersonalOpsSmokeRunner(unittest.TestCase):
    def test_runner_invokes_hermes_once_and_preserves_raw_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            package = root / "package"
            shutil.copytree(ROOT / "personalops", package)
            profile = root / "profiles" / "personalops"
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-b", "feat/test"], cwd=repo, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
            (repo / "README.md").write_text("test\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, capture_output=True)
            hermes = root / "hermes"
            guard = hermes / "tools" / "delegate_tool.py"
            guard_test = hermes / "tests" / "tools" / "test_delegate_oneshot_retirement.py"
            guard.parent.mkdir(parents=True)
            guard_test.parent.mkdir(parents=True)
            guard.write_text("guard\n", encoding="utf-8")
            guard_test.write_text("test\n", encoding="utf-8")
            contract = {
                "contract_version": 1,
                "files": [
                    {"path": "tools/delegate_tool.py", "sha256": hashlib.sha256(guard.read_bytes()).hexdigest()},
                    {
                        "path": "tests/tools/test_delegate_oneshot_retirement.py",
                        "sha256": hashlib.sha256(guard_test.read_bytes()).hexdigest(),
                    },
                ],
                "focused_tests": ["tests/tools/test_delegate_oneshot_retirement.py"],
            }
            (package / "profile" / "runtime-contract.json").write_text(
                json.dumps(contract), encoding="utf-8"
            )
            install_profile(
                package_root=package,
                profile_root=profile,
                repo_root=repo,
                hermes_root=hermes,
            )
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True, text=True, capture_output=True
            ).stdout.strip()
            calls = []

            def fake_launcher(argv, **kwargs):
                calls.append((argv, kwargs))
                usage_path = Path(argv[argv.index("--usage-file") + 1])
                usage_path.write_text(
                    json.dumps(
                        {
                            "completed": True,
                            "failed": False,
                            "model": "hermes-local:qwen3.5-9b",
                            "provider": "custom",
                            "estimated_cost_usd": 0,
                            "total_including_auxiliary": {"estimated_cost_usd": 0},
                        }
                    ),
                    encoding="utf-8",
                )
                events = [
                    {
                        "tool": "personalops_inspect_repository",
                        "ok": True,
                        "repository_root": str(repo.resolve()),
                        "branch": "feat/test",
                        "head": head,
                        "recommended_action": "run_context_and_full_checks",
                    },
                    {"tool": "personalops_run_check", "ok": True},
                    {
                        "tool": "personalops_record_outcome",
                        "ok": True,
                        "outcome": {
                            "current_state": "clean",
                            "recommended_action": "run checks",
                            "action_taken": "ran check",
                            "verification": "passed",
                            "decision_needed": "none",
                        },
                    },
                ]
                event_path = profile / "cache" / "events.jsonl"
                event_path.write_text(
                    "".join(json.dumps(row) + "\n" for row in events), encoding="utf-8"
                )
                dump_dir = profile / "logs"
                dump_dir.mkdir()
                (dump_dir / "request_dump_test_001.json").write_text(
                    json.dumps(
                        {
                            "request": {
                                "url": "http://127.0.0.1:11434/v1/chat/completions",
                                "headers": {"Authorization": "Bearer masked"},
                                "body": {
                                    "messages": [],
                                    "tools": [
                                        {"type": "function", "function": {"name": "personalops_inspect_repository"}},
                                        {"type": "function", "function": {"name": "personalops_run_check"}},
                                        {"type": "function", "function": {"name": "personalops_record_outcome"}},
                                    ],
                                },
                            }
                        }
                    ),
                    encoding="utf-8",
                )
                return subprocess.CompletedProcess(argv, 0, stdout="passed\n", stderr="")

            result = run_smoke(
                package_root=package,
                profile_root=profile,
                repo_root=repo,
                hermes_root=hermes,
                evidence_root=repo / "personalops" / "evidence",
                hermes_bin="fake-hermes",
                launcher=fake_launcher,
            )

            self.assertTrue(result["accepted"])
            self.assertEqual(len(calls), 1)
            self.assertIn("-p", calls[0][0])
            self.assertEqual(calls[0][1]["env"]["HERMES_DUMP_REQUESTS"], "1")
            evidence = Path(result["evidence_directory"])
            self.assertTrue((evidence / "acceptance.json").is_file())
            saved_request = json.loads((evidence / "requests" / "request-001.json").read_text())
            self.assertEqual(saved_request["request"]["headers"]["Authorization"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
