import dataclasses
import json
from pathlib import Path
import subprocess
import sys
import unittest

from src.evals.system_benchmark.contracts import BenchmarkSplit
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references


ROOT = Path(__file__).resolve().parents[2]


class TestReadinessReport(unittest.TestCase):
    def report(self, tasks=None, references=None):
        from scripts.audit_system_benchmark_readiness import build_readiness_report
        return build_readiness_report(
            tasks if tasks is not None else load_tasks(ROOT / "evals/system_benchmark/development_tasks.json"),
            references if references is not None else load_references(ROOT / "evals/system_benchmark/development_references.json"),
        )

    def test_seven_valid_contracts_do_not_imply_phase_entry_or_freeze(self):
        report = self.report()
        self.assertFalse(report["phase5_ready"])
        self.assertFalse(report["freeze_audit"]["ready"])
        self.assertEqual(report["missing_tasks_by_family"], {
            "A": 2, "B": 3, "C": 1, "D": 2, "E": 2, "F": 3, "G": 2, "H": 2,
        })
        self.assertEqual(report["additional_tasks_required"], 17)
        self.assertEqual(report["reference_contracts_valid"], 7)
        self.assertEqual(report["policy_reference_failures"], [])
        self.assertEqual(report["phase2_to_4_acceptance"], "not_verified_by_this_audit")
        self.assertEqual(report["known_good_response_validation"], "not_performed")

    def test_unknown_policy_identity_is_a_separate_blocker(self):
        refs = load_references(ROOT / "evals/system_benchmark/development_references.json")
        refs[1] = dataclasses.replace(refs[1],
            required_evidence_refs=("policy:kpi-dictionary@99#blocker-rate",),
            allowed_evidence_refs=("policy:kpi-dictionary@99#blocker-rate",))
        report = self.report(references=refs)
        self.assertEqual(report["reference_contracts_valid"], 7)
        self.assertEqual(report["policy_reference_failures"], ["policy:kpi-dictionary@99#blocker-rate"])
        self.assertIn("policy_reference_not_retrievable", report["blockers"])

    def test_non_development_task_is_rejected_before_probing(self):
        tasks = load_tasks(ROOT / "evals/system_benchmark/development_tasks.json")
        tasks[0] = dataclasses.replace(tasks[0], split=BenchmarkSplit.HELDOUT)
        with self.assertRaisesRegex(ValueError, "development-only"):
            self.report(tasks=tasks)

    def test_baseline_contract_checks_do_not_claim_worker_execution(self):
        report = self.report()
        self.assertEqual(report["worker_contract_failures"], [])
        self.assertEqual(set(report["route_diagnostics"]), {"oracle", "natural_language", "simple_heuristic"})
        self.assertEqual(report["route_diagnostics"]["oracle"]["route_correct"], 7)
        self.assertEqual(report["route_diagnostics"]["simple_heuristic"]["route_correct"], 2)
        self.assertEqual(report["baseline_execution"], "not_performed")

    def test_cli_returns_blocked_without_model_client_or_network(self):
        probe = '''
import runpy, sys
def block_network(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "urllib.Request"):
        raise AssertionError("network attempted: " + event)
sys.addaudithook(block_network)
try:
    runpy.run_path("scripts/audit_system_benchmark_readiness.py", run_name="__main__")
except SystemExit as exc:
    assert exc.code == 2, exc.code
for prefix in ("src.agents.ollama_client", "src.evals.system_benchmark.local_worker", "ollama", "openai", "clickhouse_connect"):
    assert not any(name == prefix or name.startswith(prefix + ".") for name in sys.modules), prefix
'''
        result = subprocess.run([sys.executable, "-c", probe], cwd=ROOT,
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["phase5_ready"])


if __name__ == "__main__":
    unittest.main()
