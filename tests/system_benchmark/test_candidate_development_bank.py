"""Candidate-only reference authoring checks; no model or external database."""

from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import unittest

from src.evals.system_benchmark.contracts import ResponseDisposition, SystemBenchmarkResponse
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references, validate_task_reference
from src.evals.system_benchmark.scoring import ScoringObservation, score_response


ROOT = Path(__file__).resolve().parents[2]
BANK = ROOT / "proposals/phase5-development-bank-v1"


def response(payload):
    return SystemBenchmarkResponse(**dict(payload, disposition=ResponseDisposition(payload["disposition"])))


class TestCandidateDevelopmentBank(unittest.TestCase):
    def test_inactive_bank_has_three_per_family_and_original_seven_are_unchanged(self):
        tasks = load_tasks(BANK / "candidate_tasks.json")
        references = load_references(BANK / "candidate_references.json")
        active_tasks = ROOT / "evals/system_benchmark/development_tasks.json"
        active_references = ROOT / "evals/system_benchmark/development_references.json"
        self.assertEqual(len(tasks), 24)
        self.assertEqual(Counter(task.family.value for task in tasks), {family: 3 for family in "ABCDEFGH"})
        self.assertEqual(tasks[:7], load_tasks(active_tasks))
        self.assertEqual(references[:7], load_references(active_references))
        self.assertEqual(len(load_tasks(active_tasks)), 7)
        for original, candidate in ((active_tasks, BANK / "candidate_tasks.json"),
                                    (active_references, BANK / "candidate_references.json")):
            self.assertTrue(candidate.read_bytes().startswith(original.read_bytes().rstrip()[:-1].rstrip() + b","))

    def test_all_controls_recompute_with_existing_scorer_and_intended_negative_reason(self):
        tasks = {task.case_id: task for task in load_tasks(BANK / "candidate_tasks.json")}
        references = {ref.reference_solution_id: ref for ref in load_references(BANK / "candidate_references.json")}
        controls = json.loads((BANK / "reference_controls.json").read_text())
        self.assertEqual(set(tasks), {control["case_id"] for control in controls})
        for control in controls:
            with self.subTest(case_id=control["case_id"]):
                task = tasks[control["case_id"]]
                reference = references[task.reference_solution_id]
                validate_task_reference(task, reference)
                for label in ("positive", "negative"):
                    item = control[label]
                    score = score_response(task, reference, response(item["response"]), ScoringObservation(**item["observation"]))
                    self.assertEqual(score.to_dict(), item["score"])
                    self.assertEqual(score.passed, label == "positive")
                    if label == "negative":
                        self.assertIn(item["expected_reason"], score.reason_codes)

    def test_numeric_truth_has_independent_cross_checks_and_no_zero_denominators(self):
        truth = json.loads((BANK / "numeric_truth.json").read_text())
        self.assertEqual(truth["row_count"], 500)
        self.assertEqual(truth["seed"], 42)
        self.assertEqual(truth["csv_sha256"], "cb3e85f970aa640624444ffc9dd13ffe7f3cbee9e97ab78050c34c35ab9d33ef")
        self.assertEqual(len(truth["operations"]), 5)
        for operation in truth["operations"].values():
            self.assertTrue(operation["cross_check_passed"])
            for name, observed in operation["observed_values"].items():
                self.assertAlmostEqual(observed, operation["independent_python_values"][name], places=9)
        self.assertEqual(truth["operations"]["active_counts"]["observed_values"], {
            "ai_active_items": 40, "data_active_items": 45,
            "platform_active_items": 32, "product_active_items": 53,
        })

    def test_semantic_invalid_probes_are_preserved_as_blockers_not_accepted_trials(self):
        report = json.loads((BANK / "validation.json").read_text())
        self.assertFalse(report["bank_accepted"])
        self.assertFalse(report["phase5_entry_accepted"])
        self.assertFalse(report["interface_freeze_approved"])
        self.assertEqual(report["semantic_validity_unapproved_ids"], ["SB-B01", "SB-B02", "SB-B03", "SB-F01", "SB-F02", "SB-F03"])
        self.assertEqual(len(report["semantic_invalid_probes"]), 6)
        for item in report["semantic_invalid_probes"]:
            self.assertFalse(item["expected_valid"])
            self.assertTrue(item["score"]["passed"])
            self.assertTrue(item["known_gap_preserved"])
        self.assertEqual(report["active_task_count"], 7)
        self.assertEqual(report["live_model_calls"], 0)
        self.assertEqual(report["external_database_calls"], 0)

    def test_reproduction_blocks_network_and_heldout_access_without_writing_active_files(self):
        probe = r'''
import hashlib, importlib.util, json, pathlib, sys
root = pathlib.Path.cwd()
def guard(event, args):
    if event.startswith("socket."):
        raise AssertionError("network forbidden")
    if event == "open" and "heldout" in str(args[0]).casefold():
        raise AssertionError("held-out access forbidden")
sys.addaudithook(guard)
active = [root / "evals/system_benchmark/development_tasks.json", root / "evals/system_benchmark/development_references.json", root / "evals/questions.json"]
before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in active]
spec = importlib.util.spec_from_file_location("candidate_prepare", root / "scripts/prepare_phase5_candidate_bank.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
files = module.prepare()
for name, text in files.items():
    assert (module.DESTINATION / name).read_text() == text, name
assert before == [hashlib.sha256(path.read_bytes()).hexdigest() for path in active]
assert not (root / "data/delivery_work_items.csv").exists()
print("reproduced offline; active inputs unchanged")
'''
        result = subprocess.run([sys.executable, "-I", "-c", probe], cwd=ROOT,
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("reproduced offline", result.stdout)


if __name__ == "__main__":
    unittest.main()
