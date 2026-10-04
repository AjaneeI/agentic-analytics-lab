import ast
import importlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from src.evals.system_benchmark.loader import load_tasks

ROOT = Path(__file__).resolve().parents[2]
DEV_TASKS = ROOT / "evals" / "system_benchmark" / "dev_tasks.json"
REFERENCES = ROOT / "evals" / "system_benchmark" / "reference_solutions.json"


def _reference(testcase):
    try:
        return importlib.import_module("src.evals.system_benchmark.reference")
    except ModuleNotFoundError as exc:
        testcase.fail(f"System Benchmark reference module is missing: {exc}")


def _scoring(testcase):
    try:
        return importlib.import_module("src.evals.system_benchmark.scoring")
    except ModuleNotFoundError as exc:
        testcase.fail(f"System Benchmark scoring module is missing: {exc}")


class TestSystemBenchmarkReferences(unittest.TestCase):
    def test_development_set_has_exactly_three_cases_per_family(self):
        tasks = load_tasks(DEV_TASKS)
        self.assertEqual(len(tasks), 24)
        self.assertEqual(Counter(task.family.value for task in tasks), Counter({x: 3 for x in "ABCDEFGH"}))
        self.assertEqual({task.split.value for task in tasks}, {"development"})

    def test_reference_solutions_match_every_task_and_pass(self):
        reference = _reference(self)
        scoring = _scoring(self)
        tasks = load_tasks(DEV_TASKS)
        solutions = reference.load_reference_solutions(REFERENCES, tasks)
        self.assertEqual(set(solutions), {task.case_id for task in tasks})
        for task in tasks:
            with self.subTest(case_id=task.case_id):
                solution = solutions[task.case_id]
                result = scoring.score_response(
                    task,
                    solution.response,
                    observed_tools=solution.observed_tools,
                    observed_values=solution.observed_values,
                    validator_passed=solution.validator_passed,
                )
                self.assertTrue(result.passed, result.reason_codes)

    def test_malformed_reference_expectations_fail_validation(self):
        reference = _reference(self)
        tasks = load_tasks(DEV_TASKS)
        raw = json.loads(REFERENCES.read_text(encoding="utf-8"))
        raw[0].pop("observed_tools")
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
            json.dump(raw, handle)
            handle.flush()
            with self.assertRaisesRegex(ValueError, "observed_tools"):
                reference.load_reference_solutions(handle.name, tasks)

    def test_duplicate_reference_case_is_rejected(self):
        reference = _reference(self)
        tasks = load_tasks(DEV_TASKS)
        raw = json.loads(REFERENCES.read_text(encoding="utf-8"))
        raw.append(dict(raw[0]))
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
            json.dump(raw, handle)
            handle.flush()
            with self.assertRaisesRegex(ValueError, "duplicate"):
                reference.load_reference_solutions(handle.name, tasks)

    def test_fixture_and_scorer_modules_are_model_free(self):
        forbidden = ("src.agents", "src.routing", "ollama", "smolagents")
        for relative in (
            "src/evals/system_benchmark/scoring.py",
            "src/evals/system_benchmark/reference.py",
        ):
            path = ROOT / relative
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.append(node.module)
            with self.subTest(path=relative):
                self.assertFalse(any(name.startswith(forbidden) for name in imports), imports)

    def test_frozen_q1_q6_fixture_is_not_replaced_by_system_benchmark(self):
        frozen = ROOT / "evals" / "questions.json"
        self.assertTrue(frozen.is_file())
        ids = [item["id"] for item in json.loads(frozen.read_text(encoding="utf-8"))]
        self.assertEqual(ids, ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6"])


if __name__ == "__main__":
    unittest.main()
