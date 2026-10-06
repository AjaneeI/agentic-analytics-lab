import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_PATH = (
    ROOT
    / "personalops"
    / "profile"
    / "plugins"
    / "personalops-repository"
    / "__init__.py"
)


def load_plugin():
    spec = importlib.util.spec_from_file_location("personalops_repository_plugin", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestPersonalOpsRepositoryPlugin(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.git("git", "init", "-b", "feat/test")
        self.git("git", "config", "user.email", "test@example.com")
        self.git("git", "config", "user.name", "Test User")
        for name in ("PROJECT.md", "STATUS.md", "DECISIONS.md", "ARCHITECTURE.md"):
            (self.repo / name).write_text(f"# {name}\n", encoding="utf-8")
        (self.repo / "notes.txt").write_text("alpha\nbeta\n", encoding="utf-8")
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts" / "check_project_context.py").write_text(
            "print('context ok')\n", encoding="utf-8"
        )
        self.git("git", "add", ".")
        self.git("git", "commit", "-m", "initial")
        self.git("git", "remote", "add", "origin", "https://github.com/AjaneeI/agentic-analytics-lab.git")
        self.events = Path(self.temp.name) / "events.jsonl"
        env = {
            "PERSONALOPS_REPO_ROOT": str(self.repo),
            "PERSONALOPS_CONTRACT_ROOT": str(ROOT / "personalops"),
            "PERSONALOPS_EVIDENCE_LOG": str(self.events),
            "PERSONALOPS_GH_BIN": str(Path(self.temp.name) / "missing-gh"),
        }
        self.env_patch = mock.patch.dict(os.environ, env, clear=False)
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)
        self.plugin = load_plugin()

    def git(self, *args):
        return subprocess.run(
            list(args),
            cwd=self.repo,
            check=True,
            text=True,
            capture_output=True,
        )

    def result(self, value):
        return json.loads(value)

    def goal(self, allowed="notes.txt", acceptance="diff"):
        return "\n".join(
            [
                "Objective: update one bounded file",
                "Inputs: repository evidence",
                f"Allowed changes: {allowed}",
                f"Acceptance: {acceptance}",
                "Evidence: exact diff and named check results",
                "Stop: after one verified patch",
            ]
        )

    def begin_delegation(self, *, allowed="notes.txt", acceptance="diff", parent="parent-1", child="child-1"):
        goal = self.goal(allowed, acceptance)
        with mock.patch.object(self.plugin, "_runtime_guard_status", return_value=(True, [])):
            result = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": goal}]},
                tool_call_id="delegate-1",
                session_id=parent,
            )
        self.assertIsNone(result)
        self.plugin._subagent_start(
            parent_session_id=parent,
            child_session_id=child,
            child_goal=goal,
        )
        return goal

    def test_inspection_reports_live_git_state_and_safe_recommendation(self):
        result = self.result(self.plugin._inspect_repository({}))

        self.assertTrue(result["ok"])
        self.assertEqual(result["repository_root"], str(self.repo.resolve()))
        self.assertEqual(result["branch"], "feat/test")
        self.assertEqual(result["head"], self.git("git", "rev-parse", "HEAD").stdout.strip())
        self.assertTrue(result["clean"])
        self.assertEqual(result["recommended_action"], "run_context_and_full_checks")
        self.assertEqual(result["github"], {"available": False, "issues": [], "pull_requests": []})
        self.assertEqual(result["context_files_missing"], [])

    def test_dirty_inspection_recommends_verifying_existing_changes(self):
        (self.repo / "notes.txt").write_text("changed\n", encoding="utf-8")

        result = self.result(self.plugin._inspect_repository({}))

        self.assertFalse(result["clean"])
        self.assertEqual(result["recommended_action"], "inspect_and_verify_current_changes")

    def test_missing_github_cli_degrades_without_losing_local_state(self):
        result = self.result(self.plugin._inspect_repository({}))

        self.assertFalse(result["github"]["available"])
        self.assertEqual(result["branch"], "feat/test")
        self.assertTrue(result["head"])

    def test_named_check_runs_without_a_shell(self):
        result = self.result(self.plugin._run_check({"check_id": "context"}))

        self.assertTrue(result["ok"])
        self.assertEqual(result["check_id"], "context")
        self.assertEqual(result["argv"], ["python3", "scripts/check_project_context.py"])
        self.assertIn("context ok", result["output"])

    def test_unapproved_check_is_rejected(self):
        result = self.result(self.plugin._run_check({"check_id": "curl"}))

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "check_not_approved")

    def test_read_rejects_traversal_and_symlink_escape(self):
        outside = Path(self.temp.name) / "outside.txt"
        outside.write_text("secret\n", encoding="utf-8")
        (self.repo / "escape.txt").symlink_to(outside)

        traversal = self.result(self.plugin._read_file({"path": "../outside.txt"}))
        symlink = self.result(self.plugin._read_file({"path": "escape.txt"}))

        self.assertEqual(traversal["reason_code"], "path_outside_repository")
        self.assertEqual(symlink["reason_code"], "path_outside_repository")

    def test_search_is_bounded_to_repository_text(self):
        result = self.result(self.plugin._search_repository({"query": "beta", "paths": ["."]}))

        self.assertTrue(result["ok"])
        self.assertEqual(result["matches"], [{"path": "notes.txt", "line": 2, "text": "beta"}])

    def test_parent_patch_is_rejected(self):
        result = self.result(
            self.plugin._apply_patch(
                {"path": "notes.txt", "expected_sha256": "ignored", "old_text": "alpha", "new_text": "gamma"}
            )
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "delegated_child_required")
        self.assertEqual((self.repo / "notes.txt").read_text(encoding="utf-8"), "alpha\nbeta\n")

    def test_child_compare_and_swap_patch_succeeds_only_for_parent_allowed_path(self):
        path = self.repo / "notes.txt"
        expected = hashlib.sha256(path.read_bytes()).hexdigest()

        self.begin_delegation()

        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            result = self.result(
                self.plugin._apply_patch(
                    {"path": "notes.txt", "expected_sha256": expected, "old_text": "alpha", "new_text": "gamma"},
                    session_id="child-1",
                )
            )

        self.assertTrue(result["ok"])
        self.assertEqual(path.read_text(encoding="utf-8"), "gamma\nbeta\n")
        self.assertEqual(result["path"], "notes.txt")

    def test_child_patch_rejects_changed_file(self):
        self.begin_delegation()

        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            result = self.result(
                self.plugin._apply_patch(
                    {"path": "notes.txt", "expected_sha256": "0" * 64, "old_text": "alpha", "new_text": "gamma"},
                    session_id="child-1",
                )
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "file_changed")

    def test_child_cannot_patch_undeclared_source_or_checker(self):
        (self.repo / "source.py").write_text("old\n", encoding="utf-8")
        self.git("git", "add", "source.py")
        self.git("git", "commit", "-m", "add source")
        self.begin_delegation(allowed="notes.txt")

        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            source = self.result(
                self.plugin._apply_patch(
                    {
                        "path": "source.py",
                        "expected_sha256": hashlib.sha256((self.repo / "source.py").read_bytes()).hexdigest(),
                        "old_text": "old",
                        "new_text": "new",
                    },
                    session_id="child-1",
                )
            )
            checker = self.result(
                self.plugin._apply_patch(
                    {
                        "path": "scripts/check_project_context.py",
                        "expected_sha256": hashlib.sha256(
                            (self.repo / "scripts" / "check_project_context.py").read_bytes()
                        ).hexdigest(),
                        "old_text": "context ok",
                        "new_text": "always pass",
                    },
                    session_id="child-1",
                )
            )

        self.assertEqual(source["reason_code"], "path_not_allowed")
        self.assertEqual(checker["reason_code"], "path_not_allowed")
        self.assertEqual((self.repo / "source.py").read_text(encoding="utf-8"), "old\n")
        self.assertIn("context ok", (self.repo / "scripts" / "check_project_context.py").read_text())

    def test_manifest_rejects_traversal_and_symlink_allowed_paths(self):
        (self.repo / "alias.txt").symlink_to(self.repo / "notes.txt")

        with mock.patch.object(self.plugin, "_runtime_guard_status", return_value=(True, [])):
            traversal = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal("../outside.txt")}]},
                tool_call_id="traversal",
                session_id="parent-traversal",
            )
            symlink = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal("alias.txt")}]},
                tool_call_id="symlink",
                session_id="parent-symlink",
            )

        self.assertEqual(traversal["action"], "block")
        self.assertEqual(traversal["reason_code"], "invalid_allowed_path")
        self.assertEqual(symlink["action"], "block")
        self.assertEqual(symlink["reason_code"], "invalid_allowed_path")

    def test_manifest_rejects_explicitly_allowed_verifier_or_checker(self):
        with mock.patch.object(self.plugin, "_runtime_guard_status", return_value=(True, [])):
            checker = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal("scripts/check_project_context.py")}]},
                tool_call_id="checker",
                session_id="parent-checker",
            )

        self.assertEqual(checker["action"], "block")
        self.assertEqual(checker["reason_code"], "protected_path_forbidden")

    def test_second_delegation_in_same_session_is_blocked(self):
        with mock.patch.object(self.plugin, "_runtime_guard_status", return_value=(True, [])):
            first = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal()}]},
                tool_call_id="one",
                session_id="same-session",
            )
            second = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal()}]},
                tool_call_id="two",
                session_id="same-session",
            )

        self.assertIsNone(first)
        self.assertEqual(second["reason_code"], "one_delegation_limit")

    def test_independent_sessions_have_independent_delegation_budgets(self):
        with mock.patch.object(self.plugin, "_runtime_guard_status", return_value=(True, [])):
            first = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal()}]},
                tool_call_id="one",
                session_id="session-a",
            )
            second = self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal()}]},
                tool_call_id="two",
                session_id="session-b",
            )

        self.assertIsNone(first)
        self.assertIsNone(second)

    def test_concurrent_sessions_are_isolated_deterministically(self):
        def delegate(session_id):
            return self.plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": self.goal()}]},
                tool_call_id=f"delegate-{session_id}",
                session_id=session_id,
            )

        with mock.patch.object(self.plugin, "_runtime_guard_status", return_value=(True, [])):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(delegate, ["session-a", "session-b"]))

        self.assertEqual(results, [None, None])
        events = [json.loads(line) for line in self.events.read_text().splitlines()]
        allowed = [row for row in events if row.get("tool") == "delegate_task" and row.get("action") == "allow"]
        self.assertEqual({row["session_id"] for row in allowed}, {"session-a", "session-b"})
        self.assertEqual([row["delegation_number"] for row in allowed], [1, 1])

    def test_child_turn_end_preserves_binding_until_parent_verifies(self):
        self.begin_delegation()
        path = self.repo / "notes.txt"
        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            patch = self.result(
                self.plugin._apply_patch(
                    {
                        "path": "notes.txt",
                        "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "old_text": "alpha",
                        "new_text": "gamma",
                    },
                    session_id="child-1",
                )
            )
        self.plugin._on_session_end(session_id="child-1")
        self.plugin._post_tool_call(
            tool_name="delegate_task", tool_call_id="delegate-1", result={"status": "completed"},
            status="ok", session_id="parent-1",
        )

        verified = self.result(
            self.plugin._verify_change({"check_ids": ["diff"]}, session_id="parent-1")
        )

        self.assertTrue(patch["ok"])
        self.assertTrue(verified["ok"])

    def test_parent_turn_end_preserves_background_delegation_manifest(self):
        goal = self.goal()
        with mock.patch.object(self.plugin, "_runtime_guard_status", return_value=(True, [])):
            self.assertIsNone(
                self.plugin._pre_tool_call(
                    tool_name="delegate_task", args={"tasks": [{"goal": goal}]},
                    tool_call_id="delegate-1", session_id="parent-1",
                )
            )
        self.plugin._on_session_end(session_id="parent-1")
        self.plugin._subagent_start(
            parent_session_id="parent-1", child_session_id="child-1", child_goal=goal
        )

        self.assertEqual(self.plugin._child_parents.get("child-1"), "parent-1")

        self.plugin._on_session_finalize(session_id="parent-1")

        self.assertNotIn("parent-1", self.plugin._manifests)
        self.assertNotIn("child-1", self.plugin._child_parents)

    def test_one_session_cannot_verify_another_childs_write(self):
        self.begin_delegation(parent="parent-a", child="child-a")
        self.begin_delegation(parent="parent-b", child="child-b")
        path = self.repo / "notes.txt"
        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            changed = self.result(
                self.plugin._apply_patch(
                    {
                        "path": "notes.txt",
                        "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "old_text": "alpha",
                        "new_text": "gamma",
                    },
                    session_id="child-b",
                )
            )
        for parent in ("parent-a", "parent-b"):
            self.plugin._post_tool_call(
                tool_name="delegate_task", tool_call_id="delegate-1", result={"status": "completed"},
                status="ok", session_id=parent,
            )

        a = self.result(self.plugin._verify_change({"check_ids": ["diff"]}, session_id="parent-a"))
        b = self.result(self.plugin._verify_change({"check_ids": ["diff"]}, session_id="parent-b"))

        self.assertTrue(changed["ok"])
        self.assertFalse(a["ok"])
        self.assertEqual(a["reason_code"], "no_child_writes")
        self.assertTrue(b["ok"])

    def test_verifier_rejects_actual_diff_outside_parent_allowlist(self):
        self.begin_delegation()
        (self.repo / "ARCHITECTURE.md").write_text("tampered\n", encoding="utf-8")
        self.plugin._post_tool_call(
            tool_name="delegate_task",
            tool_call_id="delegate-1",
            result={"status": "completed"},
            status="ok",
            session_id="parent-1",
        )

        result = self.result(
            self.plugin._verify_change({"check_ids": ["diff"]}, session_id="parent-1")
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "changed_path_not_allowed")
        self.assertEqual(result["unexpected_paths"], ["ARCHITECTURE.md"])

    def test_verifier_reports_diff_and_check_results_from_trusted_baseline(self):
        self.begin_delegation(acceptance="diff, context")
        path = self.repo / "notes.txt"
        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            patched = self.result(
                self.plugin._apply_patch(
                    {
                        "path": "notes.txt",
                        "expected_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "old_text": "alpha",
                        "new_text": "gamma",
                    },
                    session_id="child-1",
                )
            )
        self.assertTrue(patched["ok"])

        self.plugin._post_tool_call(
            tool_name="delegate_task",
            tool_call_id="delegate-1",
            result={"status": "completed"},
            status="ok",
            session_id="parent-1",
        )

        result = self.result(
            self.plugin._verify_change(
                {"check_ids": ["diff", "context"]}, session_id="parent-1"
            )
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_paths"], ["notes.txt"])
        self.assertEqual([row["check_id"] for row in result["checks"]], ["diff", "context"])
        self.assertTrue(all(row["ok"] for row in result["checks"]))

    def test_sensitive_path_variants_fail_closed(self):
        sensitive = [
            ".env",
            ".env.local",
            ".env.production",
            "nested/.env.test",
            ".netrc",
            "nested/.netrc",
            "credentials.json",
            "nested/credentials.json",
            "secrets.toml",
            "nested/secrets.toml",
            ".npmrc",
            ".pypirc",
            ".envrc",
            ".git-credentials",
            "id_rsa",
            "nested/id_ed25519",
            ".docker/config.json",
            ".kube/config",
            "private.pem",
        ]

        for raw in sensitive:
            with self.subTest(path=raw):
                self.assertTrue(self.plugin._is_sensitive(Path(raw)))

        for raw in ["environment.md", "credentials-guide.md", "secrets-example.md"]:
            with self.subTest(path=raw):
                self.assertFalse(self.plugin._is_sensitive(Path(raw)))

    def test_clarify_events_classify_red_boundary_without_storing_question_text(self):
        self.plugin._pre_tool_call(
            tool_name="clarify",
            args={"questions": [{"question": "Approve git push?"}]},
            tool_call_id="red",
            session_id="session-a",
        )
        self.plugin._pre_tool_call(
            tool_name="clarify",
            args={"questions": [{"question": "Did the smoke pass?"}]},
            tool_call_id="not-red",
            session_id="session-b",
        )
        self.plugin._pre_tool_call(
            tool_name="clarify",
            args={
                "questions": [
                    {
                        "question": (
                            "Decision needed: approve git push? Why it matters: external write. "
                            "Options: approve or stop. Hermes recommendation: stop."
                        )
                    }
                ]
            },
            tool_call_id="complete-red",
            session_id="session-c",
        )

        events = [json.loads(line) for line in self.events.read_text().splitlines()]
        self.assertEqual([row["red_boundary"] for row in events], [True, False, True])
        self.assertEqual([row["consultation_complete"] for row in events], [False, False, True])
        self.assertNotIn("Approve git push?", self.events.read_text())

    def test_event_log_redacts_sensitive_keys_bearer_tokens_and_assignments(self):
        self.plugin._write_event(
            {
                "tool": "personalops_run_check",
                "authorization": "Bearer auth-secret",
                "api_key": "key-secret",
                "output": "API_KEY=output-secret TOKEN:token-secret",
            }
        )

        saved = self.events.read_text(encoding="utf-8")
        for secret in ("auth-secret", "key-secret", "output-secret", "token-secret"):
            self.assertNotIn(secret, saved)
        self.assertIn("[REDACTED]", saved)


if __name__ == "__main__":
    unittest.main()
