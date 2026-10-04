import subprocess
import sys
import unittest
from pathlib import Path

from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references, validate_task_reference


ROOT = Path(__file__).resolve().parents[2]
TASKS = ROOT / "evals" / "system_benchmark" / "development_tasks.json"
REFERENCES = ROOT / "evals" / "system_benchmark" / "development_references.json"


class TestDevelopmentFixtures(unittest.TestCase):
    def test_development_suite_covers_required_evidence_conditions(self):
        tasks = load_tasks(TASKS)
        refs = {r.reference_solution_id: r for r in load_references(REFERENCES)}
        self.assertEqual(len(tasks), 7)
        self.assertEqual({t.reference_solution_id for t in tasks}, set(refs))
        self.assertEqual({t.family.value for t in tasks}, {"A", "C", "D", "E", "G", "H"})
        for task in tasks:
            self.assertEqual(task.split.value, "development")
            validate_task_reference(task, refs[task.reference_solution_id])

        by_id = {t.case_id: t for t in tasks}
        self.assertIn("SB-C02", by_id)  # historical/as-of
        self.assertIn("SB-H01", by_id)  # explicit policy conflict/HITL
        self.assertIn("SB-G01", by_id)  # unsupported source
        self.assertIn("SB-D01", by_id)  # cross-source alignment

    def test_no_heldout_fixture_is_added_in_pr_c(self):
        heldout = list((ROOT / "evals" / "system_benchmark").glob("*heldout*.json"))
        self.assertEqual(heldout, [])

    def test_fixture_and_scorer_imports_are_model_free(self):
        probe = r"""
import sys
from pathlib import Path
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.scoring import ScoringObservation

root = Path.cwd()
load_tasks(root / "evals/system_benchmark/development_tasks.json")
load_references(root / "evals/system_benchmark/development_references.json")
ScoringObservation()

forbidden_prefixes = ("src.agents", "src.tools", "ollama", "openai")
loaded = sorted(
    name for name in sys.modules
    if any(name == p or name.startswith(p + ".") for p in forbidden_prefixes)
)
if loaded:
    raise SystemExit("runtime/model imports loaded: " + ", ".join(loaded))
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_frozen_q1_q6_content_hash_is_unchanged(self):
        import hashlib
        expected = "0dc047fbc378f0cf75f1c488e92fcb18dddcbfe976c79b1f16281e4b428654d1"
        actual = hashlib.sha256((ROOT / "evals/questions.json").read_bytes()).hexdigest()
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
