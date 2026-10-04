import json
import tempfile
import unittest
from pathlib import Path

from src.evals.system_benchmark.contracts import parse_task_contract
from src.evals.system_benchmark.references import (
    load_references,
    parse_reference_expectation,
    validate_task_reference,
)


def valid_reference(reference_solution_id="REF-A01"):
    return {
        "reference_solution_id": reference_solution_id,
        "required_evidence_refs": ["structured:delivery_work_items"],
        "allowed_evidence_refs": ["structured:delivery_work_items"],
        "required_tools": ["query_clickhouse"],
        "forbidden_tools": ["retrieve_policy"],
        "required_answer_terms": ["Data"],
        "forbidden_answer_terms": ["causes"],
    }


def valid_task():
    return parse_task_contract(
        {
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
            "expected_values": [
                {"name": "team", "value": "Data"},
                {"name": "blocked_pct", "value": 20.9, "tolerance": 0.2},
            ],
            "required_claims": ["identify the team and blocker rate"],
            "forbidden_claims": ["claim blockers cause lateness"],
            "required_clarification_concept": None,
            "required_handoff_fields": [],
            "allowed_tools": ["query_clickhouse"],
            "forbidden_tools": ["retrieve_policy"],
            "reference_solution_id": "REF-A01",
        }
    )


class TestReferenceContracts(unittest.TestCase):
    def test_parse_reference_returns_typed_contract(self):
        ref = parse_reference_expectation(valid_reference())
        self.assertEqual(ref.reference_solution_id, "REF-A01")
        self.assertEqual(ref.required_tools, ("query_clickhouse",))

    def test_required_evidence_must_be_allowed(self):
        payload = valid_reference()
        payload["allowed_evidence_refs"] = []
        with self.assertRaisesRegex(ValueError, "required evidence"):
            parse_reference_expectation(payload)

    def test_required_and_forbidden_tools_must_be_disjoint(self):
        payload = valid_reference()
        payload["forbidden_tools"] = ["query_clickhouse"]
        with self.assertRaisesRegex(ValueError, "tool"):
            parse_reference_expectation(payload)

    def test_unknown_reference_fields_are_rejected(self):
        payload = valid_reference()
        payload["hidden_expected_reasoning"] = "never allowed"
        with self.assertRaisesRegex(ValueError, "unknown"):
            parse_reference_expectation(payload)

    def test_load_references_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "refs.json"
            path.write_text(json.dumps([valid_reference(), valid_reference()]), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_references(path)

    def test_task_and_reference_identity_must_match(self):
        task = valid_task()
        ref = parse_reference_expectation(valid_reference("REF-WRONG"))
        with self.assertRaisesRegex(ValueError, "reference_solution_id"):
            validate_task_reference(task, ref)

    def test_reference_tools_must_respect_task_tool_boundaries(self):
        task = valid_task()
        payload = valid_reference()
        payload["required_tools"] = ["retrieve_policy"]
        payload["forbidden_tools"] = []
        ref = parse_reference_expectation(payload)
        with self.assertRaisesRegex(ValueError, "allowed_tools"):
            validate_task_reference(task, ref)

    def test_reference_evidence_type_must_match_task_requirements(self):
        task = valid_task()
        payload = valid_reference()
        payload["required_evidence_refs"] = [
            "policy:delivery_work_items@1.0#blocker-rate"
        ]
        payload["allowed_evidence_refs"] = list(payload["required_evidence_refs"])
        ref = parse_reference_expectation(payload)
        with self.assertRaisesRegex(ValueError, "source type"):
            validate_task_reference(task, ref)


if __name__ == "__main__":
    unittest.main()
