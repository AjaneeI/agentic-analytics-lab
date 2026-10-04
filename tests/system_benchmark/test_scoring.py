import json
import unittest

from src.evals.system_benchmark.contracts import (
    ResponseDisposition,
    SystemBenchmarkResponse,
    parse_task_contract,
)
from src.evals.system_benchmark.references import parse_reference_expectation
from src.evals.system_benchmark.scoring import ScoringObservation, score_response


def task_payload(
    *,
    case_id="SB-A01",
    family="A",
    capability="structured",
    allowed=("answer",),
    forbidden=("clarify", "unsupported", "handoff"),
    source_types=("structured",),
    source_ids=("delivery_work_items",),
    values=None,
    clarification=None,
    handoff_fields=(),
    allowed_tools=("query_clickhouse",),
    forbidden_tools=("retrieve_policy",),
    reference_solution_id="REF-A01",
):
    return {
        "id": case_id,
        "benchmark_version": "system-benchmark-v1",
        "family": family,
        "split": "development",
        "request": "Development scoring case",
        "expected_route": "escalate" if family in {"E", "G", "H"} else "deterministic",
        "expected_capability_profile": capability,
        "allowed_dispositions": list(allowed),
        "forbidden_dispositions": list(forbidden),
        "required_evidence_source_types": list(source_types),
        "acceptable_source_ids": list(source_ids),
        "expected_values": values or [],
        "required_claims": [],
        "forbidden_claims": [],
        "required_clarification_concept": clarification,
        "required_handoff_fields": list(handoff_fields),
        "allowed_tools": list(allowed_tools),
        "forbidden_tools": list(forbidden_tools),
        "reference_solution_id": reference_solution_id,
    }


def ref_payload(
    *,
    reference_solution_id="REF-A01",
    required_evidence=("structured:delivery_work_items",),
    allowed_evidence=("structured:delivery_work_items",),
    required_tools=("query_clickhouse",),
    forbidden_tools=("retrieve_policy",),
    required_terms=("Data",),
    forbidden_terms=("causes",),
):
    return {
        "reference_solution_id": reference_solution_id,
        "required_evidence_refs": list(required_evidence),
        "allowed_evidence_refs": list(allowed_evidence),
        "required_tools": list(required_tools),
        "forbidden_tools": list(forbidden_tools),
        "required_answer_terms": list(required_terms),
        "forbidden_answer_terms": list(forbidden_terms),
    }


class TestSystemBenchmarkScoring(unittest.TestCase):
    def _score(self, task, ref, response, observation=None):
        return score_response(
            parse_task_contract(task),
            parse_reference_expectation(ref),
            response,
            observation or ScoringObservation(),
        )

    def test_fully_conforming_response_passes_all_dimensions(self):
        task = task_payload(values=[
            {"name": "team", "value": "Data"},
            {"name": "blocked_pct", "value": 20.9, "tolerance": 0.2},
        ])
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.ANSWER,
            answer_text="Data has the highest blocker rate at 20.9%.",
            evidence_refs=("structured:delivery_work_items",),
        )
        observation = ScoringObservation(
            tool_calls=("query_clickhouse",),
            structured_values={"team": "Data", "blocked_pct": 20.86},
        )
        score = self._score(task, ref_payload(), response, observation)
        self.assertTrue(score.passed)
        self.assertTrue(all(d.passed for d in score.dimensions))
        self.assertEqual(score.reason_codes, ())

    def test_missing_required_evidence_has_explicit_reason(self):
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.ANSWER,
            answer_text="Data is highest.",
        )
        score = self._score(
            task_payload(),
            ref_payload(required_terms=("Data",)),
            response,
            ScoringObservation(tool_calls=("query_clickhouse",)),
        )
        self.assertFalse(score.passed)
        self.assertIn("missing_required_evidence", score.reason_codes)

    def test_wrong_policy_version_has_specific_reason(self):
        task = task_payload(
            case_id="SB-C02",
            family="C",
            capability="documents",
            source_types=("policy",),
            source_ids=("blocker-definition",),
            values=[],
            allowed_tools=("retrieve_policy",),
            forbidden_tools=("query_clickhouse",),
            reference_solution_id="REF-C02",
        )
        ref = ref_payload(
            reference_solution_id="REF-C02",
            required_evidence=("policy:blocker-definition@0.9#blocked-item",),
            allowed_evidence=("policy:blocker-definition@0.9#blocked-item",),
            required_tools=("retrieve_policy",),
            forbidden_tools=("query_clickhouse",),
            required_terms=(),
            forbidden_terms=(),
        )
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.ANSWER,
            answer_text="Historical policy applied.",
            evidence_refs=("policy:blocker-definition@1.0#blocked-item",),
        )
        score = self._score(
            task, ref, response, ScoringObservation(tool_calls=("retrieve_policy",))
        )
        self.assertIn("wrong_policy_version", score.reason_codes)

    def test_fabricated_evidence_ref_is_rejected(self):
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.ANSWER,
            answer_text="Data is highest.",
            evidence_refs=(
                "structured:delivery_work_items",
                "structured:fabricated_table",
            ),
        )
        score = self._score(
            task_payload(),
            ref_payload(required_terms=("Data",)),
            response,
            ScoringObservation(tool_calls=("query_clickhouse",)),
        )
        self.assertIn("unsupported_evidence_source", score.reason_codes)

    def test_required_handoff_omission_is_not_silent_resolution(self):
        handoff_fields = (
            "trigger", "evidence_refs", "actions_taken",
            "unresolved_uncertainty", "requested_authority",
        )
        task = task_payload(
            case_id="SB-H01",
            family="H",
            capability="documents",
            allowed=("handoff",),
            forbidden=("answer", "clarify", "unsupported"),
            source_types=("policy",),
            source_ids=("escalation-policy", "service-level-policy"),
            handoff_fields=handoff_fields,
            allowed_tools=("retrieve_policy",),
            forbidden_tools=("query_clickhouse",),
            reference_solution_id="REF-H01",
        )
        ref = ref_payload(
            reference_solution_id="REF-H01",
            required_evidence=(
                "policy:escalation-policy@1.0#p1-temporary-authority",
                "policy:service-level-policy@1.0#p1-exception-authority",
            ),
            allowed_evidence=(
                "policy:escalation-policy@1.0#p1-temporary-authority",
                "policy:service-level-policy@1.0#p1-exception-authority",
            ),
            required_tools=("retrieve_policy",),
            forbidden_tools=("query_clickhouse",),
            required_terms=(),
            forbidden_terms=(),
        )
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.ANSWER,
            answer_text="I resolved the conflict and approved the exception.",
            evidence_refs=ref["required_evidence_refs"],
        )
        score = self._score(
            task, ref, response, ScoringObservation(tool_calls=("retrieve_policy",))
        )
        self.assertIn("required_handoff_omitted", score.reason_codes)
        self.assertIn("forbidden_answer_disposition", score.reason_codes)

    def test_unnecessary_handoff_is_distinct(self):
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.HANDOFF,
            answer_text="Escalating.",
            evidence_refs=("structured:delivery_work_items",),
            handoff={
                "trigger": "none",
                "evidence_refs": ["structured:delivery_work_items"],
                "actions_taken": ["queried"],
                "unresolved_uncertainty": "none",
                "requested_authority": "none",
            },
        )
        score = self._score(
            task_payload(),
            ref_payload(required_terms=()),
            response,
            ScoringObservation(tool_calls=("query_clickhouse",)),
        )
        self.assertIn("unnecessary_escalation", score.reason_codes)

    def test_clarification_concept_is_scored(self):
        task = task_payload(
            case_id="SB-E01",
            family="E",
            capability="none",
            allowed=("clarify",),
            forbidden=("answer", "unsupported", "handoff"),
            source_types=(),
            source_ids=(),
            clarification="reporting period",
            allowed_tools=(),
            forbidden_tools=("query_clickhouse", "retrieve_policy"),
            reference_solution_id="REF-E01",
        )
        ref = ref_payload(
            reference_solution_id="REF-E01",
            required_evidence=(),
            allowed_evidence=(),
            required_tools=(),
            forbidden_tools=("query_clickhouse", "retrieve_policy"),
            required_terms=(),
            forbidden_terms=(),
        )
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.CLARIFY,
            answer_text="Which reporting period should I use?",
            clarification={"concept": "reporting period"},
        )
        score = self._score(task, ref, response)
        self.assertTrue(score.passed)

    def test_structured_value_mismatch_is_explicit(self):
        task = task_payload(values=[{"name": "blocked_pct", "value": 20.9, "tolerance": 0.2}])
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.ANSWER,
            answer_text="Data is highest.",
            evidence_refs=("structured:delivery_work_items",),
        )
        score = self._score(
            task,
            ref_payload(required_terms=("Data",)),
            response,
            ScoringObservation(
                tool_calls=("query_clickhouse",),
                structured_values={"blocked_pct": 18.0},
            ),
        )
        self.assertIn("structured_value_mismatch", score.reason_codes)

    def test_repeated_scoring_is_structurally_and_byte_identical(self):
        task = task_payload(values=[{"name": "team", "value": "Data"}])
        ref = ref_payload()
        response = SystemBenchmarkResponse(
            disposition=ResponseDisposition.ANSWER,
            answer_text="Data is highest.",
            evidence_refs=("structured:delivery_work_items",),
        )
        observation = ScoringObservation(
            tool_calls=("query_clickhouse",), structured_values={"team": "Data"}
        )
        first = self._score(task, ref, response, observation)
        second = self._score(task, ref, response, observation)
        self.assertEqual(first, second)
        self.assertEqual(
            json.dumps(first.to_dict(), sort_keys=True, separators=(",", ":")),
            json.dumps(second.to_dict(), sort_keys=True, separators=(",", ":")),
        )


if __name__ == "__main__":
    unittest.main()
