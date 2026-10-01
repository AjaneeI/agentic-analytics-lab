import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _loader(testcase):
    try:
        return importlib.import_module("src.evals.system_benchmark.loader")
    except ModuleNotFoundError as exc:
        testcase.fail(f"System Benchmark loader module is missing: {exc}")


def valid_task_payload(case_id="SB-A01"):
    return {
        "id": case_id,
        "benchmark_version": "system-benchmark-v1",
        "family": "A",
        "split": "development",
        "request": "Which team has the highest blocker rate?",
        "expected_route": "deterministic",
        "expected_capability_profile": "structured",
        "allowed_dispositions": ["answer"],
        "forbidden_dispositions": ["clarify", "unsupported", "handoff"],
        "required_evidence_source_types": ["structured"],
        "acceptable_source_ids": ["delivery_work_items"],
        "expected_values": [
            {"name": "blocked_pct", "value": 20.9, "tolerance": 0.2}
        ],
        "required_claims": ["identify the team and blocker rate"],
        "forbidden_claims": ["claim that blockers cause lateness"],
        "required_clarification_concept": None,
        "required_handoff_fields": [],
        "allowed_tools": ["query_clickhouse"],
        "forbidden_tools": ["retrieve_policy"],
        "reference_solution_id": "REF-A01",
    }


class TestSystemBenchmarkLoader(unittest.TestCase):
    def _write(self, tmp, payload):
        path = Path(tmp) / "tasks.json"
        path.write_text(json.dumps(payload))
        return path

    def test_load_tasks_returns_typed_contracts(self):
        loader = _loader(self)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [valid_task_payload()])
            tasks = loader.load_tasks(path)

        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].case_id, "SB-A01")
        self.assertEqual(tasks[0].family.value, "A")

    def test_duplicate_case_ids_are_rejected(self):
        loader = _loader(self)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(
                tmp,
                [
                    valid_task_payload("SB-A01"),
                    valid_task_payload("SB-A01"),
                ],
            )
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                loader.load_tasks(path)

    def test_top_level_fixture_must_be_a_list(self):
        loader = _loader(self)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, {"task": valid_task_payload()})
            with self.assertRaisesRegex(ValueError, "list"):
                loader.load_tasks(path)

    def test_fixture_list_must_not_be_empty(self):
        loader = _loader(self)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [])
            with self.assertRaisesRegex(ValueError, "non-empty"):
                loader.load_tasks(path)

    def test_each_fixture_entry_must_be_an_object(self):
        loader = _loader(self)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, ["not-an-object"])
            with self.assertRaisesRegex(ValueError, "object"):
                loader.load_tasks(path)

    def test_fingerprint_inputs_are_deterministic_and_fixture_scoped(self):
        loader = _loader(self)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [valid_task_payload()])
            first = loader.fixture_fingerprint_inputs(path)
            second = loader.fixture_fingerprint_inputs(path)

        self.assertEqual(first, second)
        self.assertEqual(first, (path,))

    def test_loader_reads_fixture_as_utf8(self):
        loader = _loader(self)
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, [valid_task_payload()])
            original_read_text = Path.read_text
            seen_encodings = []

            def recording_read_text(path_obj, *args, **kwargs):
                seen_encodings.append(kwargs.get("encoding"))
                return original_read_text(path_obj, *args, **kwargs)

            with patch.object(Path, "read_text", recording_read_text):
                loader.load_tasks(path)

        self.assertEqual(seen_encodings, ["utf-8"])

    def test_loader_validation_does_not_import_model_or_tool_runtime(self):
        probe = """
import json
import sys
from pathlib import Path
import tempfile

from src.evals.system_benchmark.loader import load_tasks

payload = [{
    "id": "SB-A01",
    "benchmark_version": "system-benchmark-v1",
    "family": "A",
    "split": "development",
    "request": "Which team has the highest blocker rate?",
    "expected_route": "deterministic",
    "expected_capability_profile": "structured",
    "allowed_dispositions": ["answer"],
    "forbidden_dispositions": ["clarify", "unsupported", "handoff"],
    "required_evidence_source_types": ["structured"],
    "acceptable_source_ids": ["delivery_work_items"],
    "expected_values": [{"name": "blocked_pct", "value": 20.9, "tolerance": 0.2}],
    "required_claims": ["identify the team and blocker rate"],
    "forbidden_claims": ["claim that blockers cause lateness"],
    "required_clarification_concept": None,
    "required_handoff_fields": [],
    "allowed_tools": ["query_clickhouse"],
    "forbidden_tools": ["retrieve_policy"],
    "reference_solution_id": "REF-A01",
}]

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "tasks.json"
    path.write_text(json.dumps(payload))
    load_tasks(path)

forbidden = {"src.agents.single_agent", "src.tools.clickhouse_readonly"}
loaded = forbidden.intersection(sys.modules)
if loaded:
    raise SystemExit("forbidden runtime imports loaded: " + ", ".join(sorted(loaded)))
"""
        result = subprocess.run(
            [sys.executable, "-c", probe],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
