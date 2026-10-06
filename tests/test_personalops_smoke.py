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
            "session_id": "smoke-session",
            "api_calls": 2,
            "completed": True,
            "failed": False,
            "interrupted": False,
            "partial": False,
            "model": "hermes-local:qwen3.5-9b",
            "provider": "custom",
            "estimated_cost_usd": 0.0,
            "total_including_auxiliary": {
                "estimated_cost_usd": 0.0,
                "api_calls": 2,
                "total_tokens": 10,
            },
        }
        self.events = [
            {
                "session_id": "smoke-session",
                "tool": "personalops_inspect_repository",
                "ok": True,
                "repository_root": "/tmp/repo",
                "branch": "feat/hermes-desktop-lite",
                "head": "abc123",
                "recommended_action": "run_context_and_full_checks",
            },
            {"session_id": "smoke-session", "tool": "personalops_run_check", "ok": True, "check_id": "context"},
            {"session_id": "smoke-session", "tool": "personalops_run_check", "ok": True, "check_id": "full"},
            {
                "session_id": "smoke-session",
                "tool": "personalops_record_outcome",
                "ok": True,
                "outcome": {
                    "current_state": "clean",
                    "recommended_action": "none",
                    "action_taken": "ran full check",
                    "verification": "passed",
                    "decision_needed": "none",
                },
            },
        ]
        self.requests = [
            {
                "session_id": "smoke-session",
                "request": {
                    "url": "http://127.0.0.1:11434/v1/chat/completions",
                    "headers": {},
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

    def before_outcome(self, *rows):
        attributed = []
        for original in rows:
            row = dict(original)
            if row.get("phase") == "child_start":
                row.setdefault("parent_session_id", "smoke-session")
                row.setdefault("child_session_id", "child-session")
            elif row.get("tool") == "personalops_apply_patch":
                row.setdefault("session_id", "child-session")
                row.setdefault("parent_session_id", "smoke-session")
            else:
                row.setdefault("session_id", "smoke-session")
            attributed.append(row)
        return self.events[:-1] + attributed + [self.events[-1]]

    def test_accepts_complete_green_workflow(self):
        result = self.score()

        self.assertTrue(result["accepted"])
        self.assertTrue(all(result["checks"].values()))

    def test_accepts_post_hook_observer_after_structured_outcome(self):
        events = self.events + [
            {"session_id": "smoke-session", "tool": "personalops_record_outcome", "phase": "post", "completed": True}
        ]

        result = self.score(events=events)

        self.assertTrue(result["accepted"])

    def test_rejects_clickhouse_tool_use(self):
        result = self.score(events=self.events + [{"tool": "query_clickhouse", "ok": True}])

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["no_clickhouse"])

    def test_rejects_unknown_event_only_tool(self):
        result = self.score(events=self.before_outcome({"tool": "mystery_tool", "ok": True}))

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["approved_tool_surface"])

    def test_rejects_successful_check_that_does_not_match_recommendation(self):
        events = [dict(row) for row in self.events]
        events[0]["recommended_action"] = "run_full_verification_for_draft_pr"
        events = [row for row in events if row.get("check_id") != "full"]

        result = self.score(events=events)

        self.assertFalse(result["checks"]["recommended_checks_succeeded"])

    def test_rejects_green_checks_that_precede_repository_inspection(self):
        events = [self.events[1], self.events[2], self.events[0], self.events[3]]

        result = self.score(events=events)

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["recommended_checks_succeeded"])

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

    def test_rejects_incomplete_usage_evidence(self):
        usage = dict(self.usage)
        usage.pop("failed")

        result = self.score(usage=usage)

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["usage_evidence_complete"])

    def test_rejects_contradictory_completed_usage_flags(self):
        usage = dict(self.usage)
        usage["failed"] = True

        result = self.score(usage=usage)

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["usage_evidence_complete"])
        self.assertFalse(result["checks"]["process_completed"])

    def test_rejects_foreign_session_evidence(self):
        events = self.before_outcome(
            {"session_id": "other-session", "tool": "personalops_run_check", "ok": True, "check_id": "full"}
        )

        result = self.score(events=events)

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["session_attribution"])

    def test_rejects_missing_and_unexpected_request_evidence(self):
        missing = self.score(requests=[])
        unexpected = self.score(requests=[{"request": []}])

        self.assertFalse(missing["checks"]["request_evidence"])
        self.assertFalse(unexpected["checks"]["request_evidence"])

    def test_rejects_missing_structured_outcome(self):
        result = self.score(events=self.events[:-1])

        self.assertFalse(result["checks"]["structured_outcome"])

    def test_rejects_wrong_live_repository_identity(self):
        events = [dict(row) for row in self.events]
        events[0]["head"] = "wrong"

        result = self.score(events=events)

        self.assertFalse(result["checks"]["repository_identity"])

    def test_accepts_one_verified_child_with_observable_retirement(self):
        events = self.before_outcome(
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
            {"tool": "delegate_task", "phase": "child_start", "manifest_bound": True},
            {"tool": "personalops_apply_patch", "ok": True, "path": "notes.txt"},
            {"tool": "delegate_task", "phase": "post", "completed": True},
            {
                "tool": "personalops_verify_change",
                "ok": True,
                "changed_paths": ["notes.txt"],
                "manifest": {"allowed_paths": ["notes.txt"]},
            },
        )

        result = self.score(events=events, requests=[self.retired_request()])

        self.assertTrue(result["accepted"])
        self.assertTrue(result["checks"]["post_child_retirement"])

    def test_accepts_yellow_with_handler_and_post_hook_events(self):
        events = self.before_outcome(
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
            {"tool": "delegate_task", "phase": "child_start", "manifest_bound": True},
            {"tool": "personalops_apply_patch", "ok": True, "path": "notes.txt"},
            {"tool": "personalops_apply_patch", "phase": "post", "completed": True},
            {"tool": "delegate_task", "phase": "post", "completed": True},
            {
                "tool": "personalops_verify_change",
                "ok": True,
                "changed_paths": ["notes.txt"],
                "manifest": {"allowed_paths": ["notes.txt"]},
            },
            {"tool": "personalops_verify_change", "phase": "post", "completed": True},
        )

        result = self.score(events=events, requests=[self.retired_request()])

        self.assertTrue(result["accepted"])

    def test_rejects_child_without_observable_retirement(self):
        events = self.before_outcome(
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
            {"tool": "delegate_task", "phase": "child_start", "manifest_bound": True},
            {"tool": "personalops_apply_patch", "ok": True, "path": "notes.txt"},
            {"tool": "delegate_task", "phase": "post", "completed": True},
            {
                "tool": "personalops_verify_change",
                "ok": True,
                "changed_paths": ["notes.txt"],
                "manifest": {"allowed_paths": ["notes.txt"]},
            },
        )
        request = self.retired_request()
        request["request"]["body"]["tools"].append(
            {"type": "function", "function": {"name": "delegate_task"}}
        )

        result = self.score(events=events, requests=[request])

        self.assertFalse(result["checks"]["post_child_retirement"])

    def test_rejects_yellow_verification_before_delegated_edit(self):
        events = self.before_outcome(
            {"tool": "delegate_task", "phase": "pre", "action": "allow"},
            {
                "tool": "personalops_verify_change",
                "ok": True,
                "changed_paths": ["notes.txt"],
                "manifest": {"allowed_paths": ["notes.txt"]},
            },
            {"tool": "personalops_apply_patch", "ok": True, "path": "notes.txt"},
            {"tool": "delegate_task", "phase": "post", "completed": True},
        )

        result = self.score(events=events, requests=[self.retired_request()])

        self.assertFalse(result["checks"]["yellow_independently_verified"])

    def test_true_red_boundary_with_clarify_is_accepted(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["recommended_action"] = "request_approval_external_write"
        events[-1]["outcome"]["decision_needed"] = "external_write"

        result = self.score(
            events=events[:-1]
            + [
                {
                    "tool": "clarify",
                    "phase": "pre",
                    "action": "allow",
                    "red_boundary": True,
                    "consultation_complete": True,
                    "red_category": "external_write",
                    "session_id": "smoke-session",
                },
                events[-1],
            ]
        )

        self.assertTrue(result["accepted"])
        self.assertTrue(result["checks"]["red_uses_approval"])

    def test_true_red_boundary_with_text_only_question_is_rejected(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["recommended_action"] = "request_approval_external_write"
        events[-1]["outcome"]["decision_needed"] = "external_write"

        result = self.score(events=events)

        self.assertFalse(result["checks"]["red_uses_approval"])

    def test_red_clarify_category_must_match_structured_decision(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["recommended_action"] = "request_approval_external_write"
        events[-1]["outcome"]["decision_needed"] = "external_write"
        events = events[:-1] + [
            {
                "session_id": "smoke-session",
                "tool": "clarify",
                "phase": "pre",
                "action": "allow",
                "red_boundary": True,
                "consultation_complete": True,
                "red_category": "external_communication",
            },
            events[-1],
        ]

        result = self.score(events=events)

        self.assertFalse(result["checks"]["red_uses_approval"])
        self.assertFalse(result["accepted"])

    def test_red_recommendation_cannot_bypass_clarify(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["recommended_action"] = "request_approval_external_write"
        events[-1]["outcome"]["decision_needed"] = "external_write"

        result = self.score(events=events)

        self.assertFalse(result["checks"]["red_uses_approval"])

    def test_external_write_and_communication_phrases_require_clarify(self):
        actions = [
            "Open a pull request",
            "Close issue #91",
            "Email the report",
            "Upload the artifact",
            "Post an update",
            "Reply to issue #91",
            "Approve pull request #93",
            "Reopen issue #91",
            "Respond to the customer",
            "Assign issue #91 to Alice",
            "Add a comment to issue #91",
            "DM the customer",
            "Make the repository public",
            "Enable branch protection",
        ]
        for action in actions:
            with self.subTest(action=action):
                events = [dict(row) for row in self.events]
                events[-1] = dict(events[-1])
                events[-1]["outcome"] = dict(events[-1]["outcome"])
                events[-1]["outcome"]["recommended_action"] = action

                result = self.score(events=events)

                self.assertFalse(result["checks"]["structured_outcome"])
                self.assertFalse(result["accepted"])

    def test_local_remove_word_does_not_justify_unnecessary_approval(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["recommended_action"] = "review_verified_local_change"
        events = events[:-1] + [
            {
                "session_id": "smoke-session",
                "tool": "clarify",
                "phase": "pre",
                "action": "allow",
                "red_boundary": False,
                "consultation_complete": True,
            },
            events[-1],
        ]

        result = self.score(events=events)

        self.assertTrue(result["checks"]["red_uses_approval"])
        self.assertFalse(result["checks"]["no_unnecessary_approval"])
        self.assertFalse(result["accepted"])

    def test_incomplete_red_consultation_is_rejected(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["recommended_action"] = "request_approval_external_write"
        events[-1]["outcome"]["decision_needed"] = "external_write"

        result = self.score(
            events=events[:-1]
            + [
                {
                    "tool": "clarify",
                    "phase": "pre",
                    "action": "allow",
                    "red_boundary": True,
                    "consultation_complete": False,
                    "red_category": "external_write",
                    "session_id": "smoke-session",
                },
                events[-1],
            ]
        )

        self.assertFalse(result["checks"]["red_uses_approval"])

    def test_non_red_approval_request_is_an_orchestration_error(self):
        events = [dict(row) for row in self.events]
        events[-1] = dict(events[-1])
        events[-1]["outcome"] = dict(events[-1]["outcome"])
        events[-1]["outcome"]["decision_needed"] = "did the smoke pass or fail?"
        events = events[:-1] + [
            {"session_id": "smoke-session", "tool": "clarify", "phase": "pre", "action": "allow", "red_boundary": False, "consultation_complete": False},
            events[-1],
        ]

        result = self.score(events=events)

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["no_unnecessary_approval"])

    @staticmethod
    def retired_request():
        return {
            "session_id": "smoke-session",
            "request": {
                "url": "http://127.0.0.1:11434/v1/chat/completions",
                "headers": {},
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
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / "package"
        shutil.copytree(ROOT / "personalops", self.package)
        self.profile = self.root / "profiles" / "personalops"
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-b", "feat/test"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo, check=True)
        (self.repo / "README.md").write_text("test\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=self.repo, check=True, capture_output=True)
        self.hermes = self.root / "hermes"
        self.guard = self.hermes / "tools" / "delegate_tool.py"
        guard_test = self.hermes / "tests" / "tools" / "test_delegate_oneshot_retirement.py"
        self.guard.parent.mkdir(parents=True)
        guard_test.parent.mkdir(parents=True)
        self.guard.write_text("guard\n", encoding="utf-8")
        guard_test.write_text("test\n", encoding="utf-8")
        contract = {
            "contract_version": 1,
            "files": [
                {"path": "tools/delegate_tool.py", "sha256": hashlib.sha256(self.guard.read_bytes()).hexdigest()},
                {"path": "tests/tools/test_delegate_oneshot_retirement.py", "sha256": hashlib.sha256(guard_test.read_bytes()).hexdigest()},
            ],
            "focused_tests": ["tests/tools/test_delegate_oneshot_retirement.py"],
        }
        (self.package / "profile" / "runtime-contract.json").write_text(json.dumps(contract), encoding="utf-8")
        install_profile(package_root=self.package, profile_root=self.profile, repo_root=self.repo, hermes_root=self.hermes)
        self.head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, check=True, text=True, capture_output=True
        ).stdout.strip()
        self.calls = []

    def valid_usage(self):
        return {
            "session_id": "smoke-session",
            "api_calls": 2,
            "completed": True,
            "failed": False,
            "interrupted": False,
            "partial": False,
            "model": "hermes-local:qwen3.5-9b",
            "provider": "custom",
            "estimated_cost_usd": 0,
            "total_including_auxiliary": {"api_calls": 2, "estimated_cost_usd": 0, "total_tokens": 10},
        }

    def write_valid_events(self):
        events = [
            {
                "session_id": "smoke-session",
                "tool": "personalops_inspect_repository", "ok": True,
                "repository_root": str(self.repo.resolve()), "branch": "feat/test", "head": self.head,
                "recommended_action": "run_context_and_full_checks",
            },
            {"session_id": "smoke-session", "tool": "personalops_run_check", "ok": True, "check_id": "context"},
            {"session_id": "smoke-session", "tool": "personalops_run_check", "ok": True, "check_id": "full"},
            {
                "session_id": "smoke-session",
                "tool": "personalops_record_outcome", "ok": True,
                "outcome": {
                    "current_state": "clean", "recommended_action": "none",
                    "action_taken": "ran checks", "verification": "passed", "decision_needed": "none",
                },
            },
        ]
        event_path = self.profile / "cache" / "events.jsonl"
        event_path.write_text("".join(json.dumps(row) + "\n" for row in events), encoding="utf-8")

    def write_request(self, content=None):
        dump_dir = self.profile / "logs"
        dump_dir.mkdir(exist_ok=True)
        if content is None:
            content = json.dumps(
                {
                    "session_id": "smoke-session",
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
            )
        (dump_dir / "request_dump_test_001.json").write_text(content, encoding="utf-8")

    def run_smoke_fixture(self, launcher):
        return run_smoke(
            package_root=self.package, profile_root=self.profile, repo_root=self.repo,
            hermes_root=self.hermes, evidence_root=self.repo / "personalops" / "evidence",
            hermes_bin="fake-hermes", launcher=launcher,
        )

    def valid_launcher(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        Path(argv[argv.index("--usage-file") + 1]).write_text(json.dumps(self.valid_usage()), encoding="utf-8")
        self.write_valid_events()
        self.write_request()
        return subprocess.CompletedProcess(argv, 0, stdout="passed\n", stderr="")

    def test_runner_invokes_hermes_once_and_preserves_raw_evidence(self):
        result = self.run_smoke_fixture(self.valid_launcher)

        self.assertTrue(result["accepted"])
        self.assertEqual(len(self.calls), 1)
        self.assertIn("-p", self.calls[0][0])
        self.assertEqual(self.calls[0][1]["env"]["HERMES_DUMP_REQUESTS"], "1")
        evidence = Path(result["evidence_directory"])
        self.assertTrue((evidence / "acceptance.json").is_file())
        saved_request = json.loads((evidence / "requests" / "request-001.json").read_text())
        self.assertEqual(saved_request["request"]["headers"]["Authorization"], "[REDACTED]")

    def test_runner_scores_only_requests_attributed_to_usage_session(self):
        def launcher(argv, **kwargs):
            self.calls.append((argv, kwargs))
            Path(argv[argv.index("--usage-file") + 1]).write_text(json.dumps(self.valid_usage()), encoding="utf-8")
            self.write_valid_events()
            self.write_request()
            target = self.profile / "logs" / "request_dump_test_001.json"
            foreign = json.loads(target.read_text(encoding="utf-8"))
            foreign["session_id"] = "foreign-session"
            (target.parent / "request_dump_test_002.json").write_text(json.dumps(foreign), encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, stdout="passed\n", stderr="")

        result = self.run_smoke_fixture(launcher)

        self.assertTrue(result["accepted"])
        evidence = Path(result["evidence_directory"])
        self.assertEqual(len(list((evidence / "requests").glob("*.json"))), 1)
        self.assertEqual(len(list((evidence / "requests-foreign").glob("*.json"))), 1)

    def test_invalid_profile_aborts_before_launcher_and_preserves_failure(self):
        self.guard.write_text("changed\n", encoding="utf-8")

        result = self.run_smoke_fixture(self.valid_launcher)

        self.assertFalse(result["accepted"])
        self.assertEqual(self.calls, [])
        self.assertEqual(result["attempt_count"], 0)
        self.assertFalse(result["checks"]["profile_valid"])
        evidence = Path(result["evidence_directory"])
        command = json.loads((evidence / "command.json").read_text())
        self.assertEqual(command["attempt_count"], 0)

    def test_missing_guard_and_config_mismatch_each_abort_before_launcher(self):
        self.guard.unlink()
        missing_guard = self.run_smoke_fixture(self.valid_launcher)

        self.assertFalse(missing_guard["accepted"])
        self.assertEqual(missing_guard["attempt_count"], 0)
        self.assertEqual(self.calls, [])

        self.guard.write_text("guard\n", encoding="utf-8")
        config = self.profile / "config.yaml"
        config.write_text(
            config.read_text(encoding="utf-8").replace(
                "default: hermes-local:qwen3.5-9b", "default: forbidden-paid-model"
            ),
            encoding="utf-8",
        )
        mismatch = self.run_smoke_fixture(self.valid_launcher)

        self.assertFalse(mismatch["accepted"])
        self.assertEqual(mismatch["attempt_count"], 0)
        self.assertEqual(self.calls, [])

    def test_missing_usage_file_is_an_explicit_failure(self):
        def launcher(argv, **kwargs):
            self.calls.append((argv, kwargs))
            self.write_valid_events()
            self.write_request()
            return subprocess.CompletedProcess(argv, 0, stdout="passed\n", stderr="")

        result = self.run_smoke_fixture(launcher)

        self.assertFalse(result["accepted"])
        self.assertIn("usage_missing", result["evidence_errors"])

    def test_malformed_usage_fails_closed_and_preserves_redacted_raw(self):
        def launcher(argv, **kwargs):
            self.calls.append((argv, kwargs))
            Path(argv[argv.index("--usage-file") + 1]).write_text(
                '{"Authorization":"Bearer leaked-token",', encoding="utf-8"
            )
            self.write_valid_events()
            self.write_request()
            return subprocess.CompletedProcess(argv, 0, stdout="passed\n", stderr="")

        result = self.run_smoke_fixture(launcher)

        self.assertFalse(result["accepted"])
        self.assertIn("usage_json_invalid", result["evidence_errors"])
        raw = (Path(result["evidence_directory"]) / "usage.raw.txt").read_text()
        self.assertIn("[REDACTED]", raw)
        self.assertNotIn("leaked-token", raw)

    def test_malformed_request_fails_closed_and_preserves_redacted_raw(self):
        def launcher(argv, **kwargs):
            self.calls.append((argv, kwargs))
            Path(argv[argv.index("--usage-file") + 1]).write_text(json.dumps(self.valid_usage()), encoding="utf-8")
            self.write_valid_events()
            self.write_request('{"Authorization":"Bearer leaked-token",')
            return subprocess.CompletedProcess(argv, 0, stdout="passed\n", stderr="")

        result = self.run_smoke_fixture(launcher)

        self.assertFalse(result["accepted"])
        self.assertIn("request_json_invalid:request_dump_test_001.json", result["evidence_errors"])
        raw_files = list((Path(result["evidence_directory"]) / "requests-malformed").glob("*.txt"))
        self.assertEqual(len(raw_files), 1)
        raw = raw_files[0].read_text()
        self.assertIn("[REDACTED]", raw)
        self.assertNotIn("leaked-token", raw)

    def test_invalid_utf8_event_evidence_fails_closed(self):
        def launcher(argv, **kwargs):
            self.calls.append((argv, kwargs))
            Path(argv[argv.index("--usage-file") + 1]).write_text(json.dumps(self.valid_usage()), encoding="utf-8")
            self.write_valid_events()
            event_path = self.profile / "cache" / "events.jsonl"
            event_path.write_bytes(event_path.read_bytes().replace(b'"context"', b'"cont\xffext"', 1))
            self.write_request()
            return subprocess.CompletedProcess(argv, 0, stdout="passed\n", stderr="")

        result = self.run_smoke_fixture(launcher)

        self.assertFalse(result["accepted"])
        self.assertIn("event_utf8_invalid", result["evidence_errors"])

    def test_invalid_repository_preflight_aborts_before_launcher(self):
        not_a_repo = self.root / "not-a-repo"
        not_a_repo.mkdir()

        result = run_smoke(
            package_root=self.package, profile_root=self.profile, repo_root=not_a_repo,
            hermes_root=self.hermes, evidence_root=self.root / "preflight-evidence",
            hermes_bin="fake-hermes", launcher=self.valid_launcher,
        )

        self.assertFalse(result["accepted"])
        self.assertEqual(result["attempt_count"], 0)
        self.assertEqual(self.calls, [])
        self.assertIn("preflight_failed", result["evidence_errors"])

    def test_malformed_workflow_preflight_aborts_before_launcher(self):
        (self.package / "workflow.json").write_text("{", encoding="utf-8")

        result = self.run_smoke_fixture(self.valid_launcher)

        self.assertFalse(result["accepted"])
        self.assertEqual(result["attempt_count"], 0)
        self.assertEqual(self.calls, [])
        self.assertIn("profile_validation_failed", result["evidence_errors"])

    def test_raw_stdout_stderr_and_events_are_redacted(self):
        def launcher(argv, **kwargs):
            self.calls.append((argv, kwargs))
            usage = self.valid_usage()
            usage["api_key"] = "usage-api-secret"
            usage["private_key"] = "-----BEGIN PRIVATE KEY-----\nUSAGE-PRIVATE-BODY\n-----END PRIVATE KEY-----"
            Path(argv[argv.index("--usage-file") + 1]).write_text(json.dumps(usage), encoding="utf-8")
            self.write_valid_events()
            event_path = self.profile / "cache" / "events.jsonl"
            with event_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"session_id": "smoke-session", "tool": "personalops_run_check", "ok": True, "api_key": "event-secret"}) + "\n")
            self.write_request()
            return subprocess.CompletedProcess(
                argv, 0,
                stdout=(
                    "passed API_KEY=stdout-secret\n"
                    "private_key: |\n  -----BEGIN PRIVATE KEY-----\n"
                    "  YAML-PRIVATE-BODY\n  -----END PRIVATE KEY-----\n"
                ),
                stderr="Authorization: Bearer stderr-secret\n",
            )

        result = self.run_smoke_fixture(launcher)
        evidence = Path(result["evidence_directory"])
        combined = "\n".join(
            (evidence / name).read_text(encoding="utf-8")
            for name in ("stdout.txt", "stderr.txt", "events.jsonl", "usage.json", "usage.raw.txt")
        )

        for secret in (
            "stdout-secret", "stderr-secret", "event-secret",
            "usage-api-secret", "USAGE-PRIVATE-BODY", "BEGIN PRIVATE KEY", "END PRIVATE KEY",
            "YAML-PRIVATE-BODY",
        ):
            self.assertNotIn(secret, combined)


if __name__ == "__main__":
    unittest.main()
