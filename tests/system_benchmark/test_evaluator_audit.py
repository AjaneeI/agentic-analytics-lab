"""The audit must expose defects without redefining frozen scorer outcomes."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit_system_benchmark_evaluator.py"


class TestEvaluatorAudit(unittest.TestCase):
    def run_audit(self, *arguments):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments], cwd=ROOT,
            capture_output=True, text=True, check=False,
        )
        self.assertTrue(result.stdout.startswith("{"), result.stderr)
        return result, json.loads(result.stdout)

    def test_semantic_defects_are_reported_as_a_failing_gate(self):
        result, report = self.run_audit()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report["phase3_accepted"])
        self.assertEqual(report["known_good"]["passed"], 7)
        self.assertEqual(report["known_good"]["total"], 7)
        controls = {row["id"]: row for row in report["controls"]}
        self.assertEqual(controls["C01-equivalent-definition"]["score"]["reason_codes"],
                         ["required_answer_term_missing"])
        self.assertTrue(controls["G01-fabricated-prose"]["score"]["passed"])
        self.assertEqual(set(report["unresolved_control_ids"]), {
            "C01-equivalent-definition", "C02-equivalent-working-day",
            "C02-negated-later-definition", "A01-negated-causality",
            "C01-reversed-definition", "D01-causal-paraphrase",
            "G01-fabricated-prose", "H01-contradictory-authority",
            "A01-contradictory-prose",
        })
        self.assertEqual(report["controls_matching_expectations"], 22)
        self.assertTrue(report["freeze_unchanged"])

    def test_known_bad_reason_targets_and_valid_tool_order_are_distinct(self):
        _, report = self.run_audit()
        controls = {row["id"]: row for row in report["controls"]}
        for control_id, reason in (
            ("C02-wrong-version", "wrong_policy_version"),
            ("D01-wrong-scope", "structured_value_mismatch"),
            ("E01-omitted-clarification", "required_clarification_omitted"),
            ("H01-omitted-handoff", "required_handoff_omitted"),
        ):
            self.assertIn(reason, controls[control_id]["score"]["reason_codes"])
            self.assertTrue(controls[control_id]["matches_expectation"])
        self.assertTrue(controls["D01-reversed-tool-order"]["matches_expectation"])

    def test_saved_report_is_byte_reproducible_and_hashes_actual_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.json"
            result, report = self.run_audit("--output", str(path))
            second, _ = self.run_audit()
            self.assertEqual(result.stdout, second.stdout)
            self.assertEqual(path.read_text(), result.stdout)
            self.assertEqual(report["sha256"]["src/evals/system_benchmark/scoring.py"],
                             hashlib.sha256((ROOT / "src/evals/system_benchmark/scoring.py").read_bytes()).hexdigest())

    def test_actual_audit_imports_no_model_or_tool_runtime(self):
        probe = """
import runpy, sys
sys.argv = ['audit_system_benchmark_evaluator.py']
try:
    runpy.run_path('scripts/audit_system_benchmark_evaluator.py', run_name='__main__')
except SystemExit as result:
    assert result.code == 2, result.code
for prefix in ('src.agents', 'src.tools', 'openai', 'ollama', 'requests'):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""
        result = subprocess.run([sys.executable, "-c", probe], cwd=ROOT,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
