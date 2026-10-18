"""Characterize the real frozen D01 contract without a model or database service."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/characterize_system_benchmark_runtime.py"


class TestRuntimeCharacterization(unittest.TestCase):
    def run_characterization(self, *arguments):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), *arguments], cwd=ROOT,
            capture_output=True, text=True, check=False,
        )
        self.assertTrue(result.stdout.startswith("{"), result.stderr)
        return result, json.loads(result.stdout)

    def test_real_d01_contract_exposes_missing_scope_without_row_overrides(self):
        result, report = self.run_characterization()
        self.assertEqual(result.returncode, 2)
        self.assertFalse(report["phase3_accepted"])
        self.assertTrue(report["freeze_unchanged"])
        self.assertEqual(report["dataset"]["row_count"], 500)
        active_data = report["dataset"]["active_team_counts"]["Data"]
        self.assertEqual(active_data, {"blocked": 8, "total": 45})
        winner = max(report["dataset"]["active_team_counts"].items(),
                     key=lambda item: item[1]["blocked"] / item[1]["total"])
        self.assertEqual(winner[0], "Data")
        case = next(row for row in report["cases"] if row["id"] == "D01-active-unlabelled")
        self.assertTrue(case["expected_pass"])
        self.assertEqual(case["rows"], [{"team": "Data", "blocked_pct": 100 * 8 / 45}])
        self.assertEqual(case["observation"]["structured_values"], case["rows"][0])
        self.assertEqual(case["score"]["reason_codes"], ["missing_expected_value"])
        self.assertFalse(case["matches_expectation"])
        self.assertEqual(case["observation"]["tool_calls"], ["query_clickhouse", "retrieve_policy"])
        self.assertEqual(case["response"]["evidence_refs"], [
            "structured:delivery_work_items", "policy:kpi-dictionary@1.0#blocker-rate",
        ])

    def test_sql_alternatives_and_invalid_labels_retain_actual_frozen_outcomes(self):
        _, report = self.run_characterization()
        cases = {row["id"]: row for row in report["cases"]}
        for case_id in ("D01-active-negated-equality", "D01-active-cte"):
            self.assertTrue(cases[case_id]["expected_pass"])
            self.assertEqual(cases[case_id]["score"]["reason_codes"], ["missing_expected_value"])
        self.assertTrue(cases["D01-active-labelled"]["matches_expectation"])
        self.assertTrue(cases["D01-all-items-labelled"]["matches_expectation"])
        self.assertIn("structured_value_mismatch", cases["D01-all-items-labelled"]["score"]["reason_codes"])
        self.assertTrue(cases["D01-or-bypass"]["matches_expectation"])
        self.assertFalse(cases["D01-fabricated-rate-and-scope"]["expected_pass"])
        self.assertTrue(cases["D01-fabricated-rate-and-scope"]["score"]["passed"])
        self.assertFalse(cases["D01-fabricated-rate-and-scope"]["matches_expectation"])
        self.assertEqual(cases["D01-empty-active-result"]["rows"], [])
        self.assertIn("missing_required_evidence", cases["D01-empty-active-result"]["score"]["reason_codes"])
        self.assertFalse(report["audit_checks_pass"])

    def test_report_is_reproducible_and_hashes_integration_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "runtime.json"
            first, report = self.run_characterization("--output", str(output))
            second, _ = self.run_characterization()
            self.assertEqual(first.stdout, second.stdout)
            self.assertEqual(output.read_text(), first.stdout)
            for relative in ("src/evals/system_benchmark/local_worker.py",
                             "scripts/generate_delivery_data.py",
                             "scripts/characterize_system_benchmark_runtime.py"):
                self.assertEqual(report["sha256"][relative], hashlib.sha256((ROOT / relative).read_bytes()).hexdigest())
        self.assertEqual(report["live_model_calls"], 0)
        self.assertEqual(report["external_database_calls"], 0)

    def test_execution_cannot_reach_network_or_instantiate_live_model(self):
        probe = """
import runpy, socket, sys
from unittest.mock import patch
def denied(*args, **kwargs):
    raise AssertionError('live network or model access is forbidden')
with patch.object(socket.socket, 'connect', denied), \\
     patch.object(socket.socket, 'connect_ex', denied), \\
     patch('socket.create_connection', denied), \\
     patch('src.agents.ollama_client.OllamaModelClient.__init__', denied), \\
     patch('src.agents.ollama_client.OllamaModelClient.respond', denied), \\
     patch('src.tools.clickhouse_readonly.query_clickhouse', denied):
    sys.argv = ['characterize_system_benchmark_runtime.py']
    try:
        runpy.run_path('scripts/characterize_system_benchmark_runtime.py', run_name='__main__')
    except SystemExit as result:
        assert result.code == 2, result.code
"""
        result = subprocess.run([sys.executable, "-c", probe], cwd=ROOT,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
