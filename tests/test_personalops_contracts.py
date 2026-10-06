import json
from pathlib import Path
import tempfile
import unittest

from personalops.contracts import load_policy, load_workflow, validate_contracts


POLICY = {
    "package_version": "0.1.0",
    "levels": {
        "green": ["read_repository", "run_named_check"],
        "yellow": ["bounded_local_edit", "one_worker"],
        "red": ["external_write", "push", "merge", "paid_provider"],
    },
    "consultation": {
        "required_sections": [
            "Decision needed",
            "Why it matters",
            "Options/tradeoffs",
            "Hermes recommendation",
        ]
    },
}

WORKFLOW = {
    "package_version": "0.1.0",
    "model": {
        "name": "hermes-local:qwen3.5-9b",
        "provider": "custom",
        "base_url": "http://127.0.0.1:11434/v1",
        "context_length": 65536,
        "fallbacks": [],
    },
    "tools": ["clarify", "delegate_task", "personalops_repository"],
    "worker": {
        "max_workers": 1,
        "max_concurrency": 1,
        "required_fields": [
            "Objective",
            "Inputs",
            "Allowed changes",
            "Acceptance",
            "Evidence",
            "Stop",
        ],
    },
    "checks": {
        "context": {"command": ["python3", "scripts/check_project_context.py"]},
        "diff": {"command": ["git", "diff", "--check"]},
        "full": {"command": ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"]},
    },
    "final_status_fields": [
        "current_state",
        "recommended_action",
        "action_taken",
        "verification",
        "decision_needed",
    ],
}


class TestPersonalOpsContracts(unittest.TestCase):
    def make_root(self, *, policy=None, workflow=None, version="0.1.0"):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "VERSION").write_text(version + "\n", encoding="utf-8")
        (root / "policy.json").write_text(
            json.dumps(policy if policy is not None else POLICY), encoding="utf-8"
        )
        (root / "workflow.json").write_text(
            json.dumps(workflow if workflow is not None else WORKFLOW), encoding="utf-8"
        )
        self.addCleanup(temp.cleanup)
        return root

    def test_valid_contracts_load_and_validate(self):
        root = self.make_root()

        self.assertEqual(load_policy(root)["levels"]["green"][0], "read_repository")
        self.assertEqual(load_workflow(root)["worker"]["max_workers"], 1)
        self.assertEqual(validate_contracts(root), [])

    def test_missing_required_policy_category_is_rejected(self):
        policy = json.loads(json.dumps(POLICY))
        del policy["levels"]["red"]

        errors = validate_contracts(self.make_root(policy=policy))

        self.assertIn("policy.levels must contain exactly green, yellow, red", errors)

    def test_arbitrary_shell_command_is_rejected(self):
        workflow = json.loads(json.dumps(WORKFLOW))
        workflow["checks"]["full"]["command"] = "python3 -m unittest"

        errors = validate_contracts(self.make_root(workflow=workflow))

        self.assertIn("workflow.checks.full.command must be a non-empty string list", errors)

    def test_paid_or_remote_fallback_is_rejected(self):
        workflow = json.loads(json.dumps(WORKFLOW))
        workflow["model"]["fallbacks"] = ["openai/gpt-5"]
        workflow["model"]["base_url"] = "https://api.example.com/v1"

        errors = validate_contracts(self.make_root(workflow=workflow))

        self.assertIn("workflow.model.base_url must be loopback Ollama", errors)
        self.assertIn("workflow.model.fallbacks must be empty", errors)

    def test_missing_worker_contract_fields_is_rejected(self):
        workflow = json.loads(json.dumps(WORKFLOW))
        workflow["worker"]["required_fields"].remove("Stop")

        errors = validate_contracts(self.make_root(workflow=workflow))

        self.assertIn("workflow.worker.required_fields must match the six-field contract", errors)

    def test_mismatched_package_version_is_rejected(self):
        workflow = json.loads(json.dumps(WORKFLOW))
        workflow["package_version"] = "0.2.0"

        errors = validate_contracts(self.make_root(workflow=workflow))

        self.assertIn("workflow.package_version must match VERSION", errors)


if __name__ == "__main__":
    unittest.main()
