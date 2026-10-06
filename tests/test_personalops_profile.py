import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from personalops.install import install_profile
from personalops.validate import validate_profile


ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_plugin(path):
    spec = importlib.util.spec_from_file_location("installed_personalops_plugin", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestPersonalOpsProfile(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.package = base / "package"
        shutil.copytree(ROOT / "personalops", self.package)
        self.profile = base / "profiles" / "personalops"
        self.repo = base / "repo"
        self.repo.mkdir()
        (self.repo / ".git").mkdir()
        self.hermes = base / "hermes-agent"
        (self.hermes / "tools").mkdir(parents=True)
        (self.hermes / "tests" / "tools").mkdir(parents=True)
        self.guard = self.hermes / "tools" / "delegate_tool.py"
        self.guard_test = self.hermes / "tests" / "tools" / "test_delegate_oneshot_retirement.py"
        self.guard.write_text("def retire(): return True\n", encoding="utf-8")
        self.guard_test.write_text("def test_retirement(): assert True\n", encoding="utf-8")
        contract = {
            "contract_version": 1,
            "files": [
                {"path": "tools/delegate_tool.py", "sha256": digest(self.guard)},
                {"path": "tests/tools/test_delegate_oneshot_retirement.py", "sha256": digest(self.guard_test)},
            ],
            "focused_tests": ["tests/tools/test_delegate_oneshot_retirement.py"],
        }
        (self.package / "profile" / "runtime-contract.json").write_text(
            json.dumps(contract), encoding="utf-8"
        )

    def install(self):
        return install_profile(
            package_root=self.package,
            profile_root=self.profile,
            repo_root=self.repo,
            hermes_root=self.hermes,
        )

    def validate(self):
        return validate_profile(
            package_root=self.package,
            profile_root=self.profile,
            repo_root=self.repo,
            hermes_root=self.hermes,
        )

    def test_install_is_isolated_local_only_and_preserves_unrelated_files(self):
        self.profile.mkdir(parents=True)
        unrelated = self.profile / "keep.txt"
        unrelated.write_text("keep\n", encoding="utf-8")

        result = self.install()

        self.assertTrue(result["accepted"])
        self.assertEqual(unrelated.read_text(encoding="utf-8"), "keep\n")
        config = (self.profile / "config.yaml").read_text(encoding="utf-8")
        self.assertIn("default: hermes-local:qwen3.5-9b", config)
        self.assertIn("base_url: http://127.0.0.1:11434/v1", config)
        self.assertIn("context_length: 65536", config)
        self.assertIn("max_concurrent_children: 1", config)
        self.assertIn("oneshot_max_children: 1", config)
        self.assertIn("api_server:", config)
        self.assertNotIn("openai", config.lower())
        self.assertNotIn("fallback", config.lower())
        self.assertEqual(result["profile_root"], str(self.profile.resolve()))

    def test_install_is_idempotent_for_owned_files(self):
        self.install()
        installed_policy = self.profile / "personalops" / "policy.json"
        installed_policy.write_text("corrupt", encoding="utf-8")

        second = self.install()

        self.assertTrue(second["accepted"])
        self.assertEqual(installed_policy.read_bytes(), (self.package / "policy.json").read_bytes())

    def test_valid_guard_hashes_are_accepted(self):
        self.install()

        result = self.validate()

        self.assertTrue(result["accepted"])
        self.assertTrue(result["checks"]["runtime_guard"])

    def test_missing_guard_file_fails_closed(self):
        self.install()
        self.guard.unlink()

        result = self.validate()

        self.assertFalse(result["accepted"])
        self.assertFalse(result["checks"]["runtime_guard"])

    def test_mismatched_guard_hash_fails_closed(self):
        self.install()
        self.guard.write_text("changed\n", encoding="utf-8")

        result = self.validate()

        self.assertFalse(result["accepted"])
        self.assertIn("runtime guard hash mismatch", " ".join(result["errors"]))

    def test_malformed_worker_contract_is_blocked(self):
        self.install()
        plugin = load_plugin(self.profile / "plugins" / "personalops-repository" / "__init__.py")
        env = {
            "PERSONALOPS_REPO_ROOT": str(self.repo),
            "PERSONALOPS_CONTRACT_ROOT": str(self.profile / "personalops"),
            "PERSONALOPS_EVIDENCE_LOG": str(self.profile / "cache" / "events.jsonl"),
            "PERSONALOPS_HERMES_ROOT": str(self.hermes),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            result = plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": "Objective: edit only"}]},
                tool_call_id="one",
            )

        self.assertEqual(result["action"], "block")
        self.assertIn("six-field", result["message"])

    def test_one_valid_delegation_then_second_is_blocked(self):
        self.install()
        plugin = load_plugin(self.profile / "plugins" / "personalops-repository" / "__init__.py")
        goal = "\n".join(
            [
                "Objective: update one file",
                "Inputs: repository evidence",
                "Allowed changes: notes.txt",
                "Acceptance: named tests pass",
                "Evidence: diff and tests",
                "Stop: after one patch",
            ]
        )
        env = {
            "PERSONALOPS_REPO_ROOT": str(self.repo),
            "PERSONALOPS_CONTRACT_ROOT": str(self.profile / "personalops"),
            "PERSONALOPS_EVIDENCE_LOG": str(self.profile / "cache" / "events.jsonl"),
            "PERSONALOPS_HERMES_ROOT": str(self.hermes),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            first = plugin._pre_tool_call(
                tool_name="delegate_task", args={"tasks": [{"goal": goal}]}, tool_call_id="one"
            )
            second = plugin._pre_tool_call(
                tool_name="delegate_task", args={"tasks": [{"goal": goal}]}, tool_call_id="two"
            )

        self.assertIsNone(first)
        self.assertEqual(second["action"], "block")
        self.assertIn("one delegation", second["message"])

    def test_invalid_runtime_guard_blocks_first_delegation(self):
        self.install()
        self.guard.write_text("changed\n", encoding="utf-8")
        plugin = load_plugin(self.profile / "plugins" / "personalops-repository" / "__init__.py")
        env = {
            "PERSONALOPS_REPO_ROOT": str(self.repo),
            "PERSONALOPS_CONTRACT_ROOT": str(self.profile / "personalops"),
            "PERSONALOPS_EVIDENCE_LOG": str(self.profile / "cache" / "events.jsonl"),
            "PERSONALOPS_HERMES_ROOT": str(self.hermes),
        }
        with mock.patch.dict(os.environ, env, clear=False):
            result = plugin._pre_tool_call(
                tool_name="delegate_task",
                args={"tasks": [{"goal": "Objective: x\nInputs: x\nAllowed changes: x\nAcceptance: x\nEvidence: x\nStop: x"}]},
                tool_call_id="one",
            )

        self.assertEqual(result["action"], "block")
        self.assertIn("runtime guard", result["message"])


if __name__ == "__main__":
    unittest.main()
