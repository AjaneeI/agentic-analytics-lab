import json
import tempfile
import unittest
from pathlib import Path

from src.evals.system_benchmark.contracts import (
    ResponseDisposition,
    SystemBenchmarkResponse,
    parse_task_contract,
)
from src.evals.system_benchmark.references import parse_reference_expectation
from src.evals.system_benchmark.routing import oracle_route
from src.evals.system_benchmark.runner import (
    TrialExecution,
    fingerprint_paths,
    run_trial,
    write_artifact_bundle,
)
from src.evals.system_benchmark.scoring import ScoringObservation


def task():
    return parse_task_contract({
        "id": "SB-A01",
        "benchmark_version": "system-benchmark-v1",
        "family": "A",
        "split": "development",
        "request": "Which team is highest?",
        "expected_route": "deterministic",
        "expected_capability_profile": "structured",
        "allowed_dispositions": ["answer"],
        "forbidden_dispositions": ["clarify", "unsupported", "handoff"],
        "required_evidence_source_types": ["structured"],
        "acceptable_source_ids": ["delivery_work_items"],
        "expected_values": [{"name": "team", "value": "Data"}],
        "required_claims": [],
        "forbidden_claims": [],
        "required_clarification_concept": None,
        "required_handoff_fields": [],
        "allowed_tools": ["query_clickhouse"],
        "forbidden_tools": ["retrieve_policy"],
        "reference_solution_id": "REF-A01",
    })


def reference():
    return parse_reference_expectation({
        "reference_solution_id": "REF-A01",
        "required_evidence_refs": ["structured:delivery_work_items"],
        "allowed_evidence_refs": ["structured:delivery_work_items"],
        "required_tools": ["query_clickhouse"],
        "forbidden_tools": ["retrieve_policy"],
        "required_answer_terms": ["Data"],
        "forbidden_answer_terms": [],
    })


class TestSystemBenchmarkRunner(unittest.TestCase):
    def test_trial_is_scored_from_observable_execution(self):
        current = task()

        def executor(received, trial_number, temp_dir):
            self.assertEqual(received, current)
            self.assertEqual(trial_number, 1)
            self.assertTrue(temp_dir.is_dir())
            return TrialExecution(
                response=SystemBenchmarkResponse(
                    disposition=ResponseDisposition.ANSWER,
                    answer_text="Data is highest.",
                    evidence_refs=("structured:delivery_work_items",),
                ),
                observation=ScoringObservation(
                    tool_calls=("query_clickhouse",),
                    structured_values={"team": "Data"},
                ),
                route_decision=oracle_route(received),
                latency_seconds=0.25,
                model_calls=1,
                input_tokens=10,
                output_tokens=5,
            )

        result = run_trial(current, reference(), trial_number=1, executor=executor)

        self.assertTrue(result["task_success"])
        self.assertEqual(result["tool_call_count"], 1)
        self.assertEqual(result["model_calls"], 1)
        self.assertEqual(result["capability_profile"], "structured")

    def test_each_trial_receives_fresh_temporary_directory(self):
        seen = []

        def executor(received, trial_number, temp_dir):
            seen.append(str(temp_dir))
            return TrialExecution(
                response=SystemBenchmarkResponse(
                    disposition=ResponseDisposition.ANSWER,
                    answer_text="Data is highest.",
                    evidence_refs=("structured:delivery_work_items",),
                ),
                observation=ScoringObservation(
                    tool_calls=("query_clickhouse",),
                    structured_values={"team": "Data"},
                ),
                route_decision=oracle_route(received),
                latency_seconds=0.1,
            )

        run_trial(task(), reference(), trial_number=1, executor=executor)
        run_trial(task(), reference(), trial_number=2, executor=executor)

        self.assertEqual(len(set(seen)), 2)
        self.assertTrue(all(not Path(path).exists() for path in seen))

    def test_artifact_bundle_has_fixed_six_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_artifact_bundle(
                tmp,
                manifest={"benchmark_version": "system-benchmark-v1"},
                reference_validation={"passed": True},
                results=[{"task_success": True, "latency_seconds": 1.0}],
                routing_metrics={"route_accuracy": 1.0},
                diagnostics={"failed_cases": 0},
            )

            self.assertEqual(
                {path.name for path in paths},
                {
                    "manifest.json",
                    "reference_validation.json",
                    "results.jsonl",
                    "routing_metrics.json",
                    "diagnostics.json",
                    "summary.json",
                },
            )
            self.assertEqual(json.loads((Path(tmp) / "summary.json").read_text())["successful"], 1)

    def test_fingerprint_changes_when_contract_file_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "a.txt").write_text("one")
            first = fingerprint_paths(root, ["a.txt"])
            (root / "a.txt").write_text("two")
            second = fingerprint_paths(root, ["a.txt"])

            self.assertNotEqual(
                first["benchmark_contract_sha256"],
                second["benchmark_contract_sha256"],
            )


if __name__ == "__main__":
    unittest.main()
