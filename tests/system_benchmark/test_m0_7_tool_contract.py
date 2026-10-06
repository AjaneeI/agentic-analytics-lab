import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

from src.evals.system_benchmark.local_worker import _QUERY_TOOL


ROOT = Path(__file__).resolve().parents[2]
PLUGIN = (
    ROOT
    / "experiments"
    / "hermes-successor-ab-v1"
    / "plugin"
    / "system-benchmark-tools"
    / "__init__.py"
)
RUNNER = ROOT / "experiments" / "m0-7-tool-contract-usability" / "run_study.py"
REQUIRED_QUALIFICATION = (
    "SQL passed to this tool must reference this exact fully qualified "
    "table name: agentic_analytics.delivery_work_items."
)


def load_plugin():
    spec = importlib.util.spec_from_file_location("m0_7_plugin", PLUGIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestM07ToolContract(unittest.TestCase):
    def test_runner_help_loads_without_model_invocation(self):
        completed = subprocess.run(
            [sys.executable, str(RUNNER), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--verify-only", completed.stdout)

    def test_direct_contract_states_exact_sql_qualification_requirement(self):
        description = _QUERY_TOOL["description"]

        self.assertIn(
            "The only approved table is "
            "agentic_analytics.delivery_work_items.",
            description,
        )
        self.assertIn(REQUIRED_QUALIFICATION, description)

    def test_hermes_contract_matches_validated_direct_contract(self):
        plugin = load_plugin()

        self.assertEqual(plugin._QUERY_SPEC, _QUERY_TOOL)
        self.assertIn(
            REQUIRED_QUALIFICATION,
            plugin._QUERY_SPEC["description"],
        )


if __name__ == "__main__":
    unittest.main()
