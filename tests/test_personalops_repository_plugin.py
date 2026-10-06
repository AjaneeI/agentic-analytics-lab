import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
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

    def test_child_compare_and_swap_patch_succeeds(self):
        path = self.repo / "notes.txt"
        expected = hashlib.sha256(path.read_bytes()).hexdigest()

        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            result = self.result(
                self.plugin._apply_patch(
                    {"path": "notes.txt", "expected_sha256": expected, "old_text": "alpha", "new_text": "gamma"}
                )
            )

        self.assertTrue(result["ok"])
        self.assertEqual(path.read_text(encoding="utf-8"), "gamma\nbeta\n")
        self.assertEqual(result["path"], "notes.txt")

    def test_child_patch_rejects_changed_file(self):
        with mock.patch.object(self.plugin, "_is_delegated_child_context", return_value=True):
            result = self.result(
                self.plugin._apply_patch(
                    {"path": "notes.txt", "expected_sha256": "0" * 64, "old_text": "alpha", "new_text": "gamma"}
                )
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "file_changed")

    def test_verifier_reports_diff_and_check_results(self):
        (self.repo / "notes.txt").write_text("gamma\nbeta\n", encoding="utf-8")

        result = self.result(self.plugin._verify_change({"check_ids": ["diff", "context"]}))

        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_paths"], ["notes.txt"])
        self.assertEqual([row["check_id"] for row in result["checks"]], ["diff", "context"])
        self.assertTrue(all(row["ok"] for row in result["checks"]))


if __name__ == "__main__":
    unittest.main()
