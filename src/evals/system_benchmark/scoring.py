"""Model-free deterministic scoring for System Benchmark v1 development cases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from typing import Any

from src.evals.system_benchmark.contracts import (
    ResponseDisposition,
    StructuredExpectation,
    SystemBenchmarkResponse,
    SystemBenchmarkTask,
)
from src.evals.system_benchmark.references import (
    ReferenceExpectation,
    evidence_source_id,
    parse_policy_evidence_ref,
    validate_task_reference,
)


@dataclass(frozen=True)
class ScoringObservation:
    """Observable execution facts supplied to deterministic scoring."""

    tool_calls: tuple[str, ...] = ()
    structured_values: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DimensionResult:
    """One inspectable scoring dimension."""

    name: str
    passed: bool
    reason_codes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class ScoreResult:
    """Deterministic aggregate score with stable dimension ordering."""

    passed: bool
    dimensions: tuple[DimensionResult, ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "dimensions": [dimension.to_dict() for dimension in self.dimensions],
            "reason_codes": list(self.reason_codes),
        }


def score_response(
    task: SystemBenchmarkTask,
    reference: ReferenceExpectation,
    response: SystemBenchmarkResponse,
    observation: ScoringObservation,
) -> ScoreResult:
    """Score only observable response/evidence/tool behavior, without model inference."""

    validate_task_reference(task, reference)
    dimensions = (
        _score_disposition(task, response),
        _score_evidence(task, reference, response),
        _score_tools(task, reference, observation),
        _score_structured_values(task, observation),
        _score_clarification(task, response),
        _score_handoff(task, response),
        _score_answer_bounds(reference, response),
    )
    reason_codes = _stable_unique(
        reason
        for dimension in dimensions
        for reason in dimension.reason_codes
    )
    return ScoreResult(
        passed=all(dimension.passed for dimension in dimensions),
        dimensions=dimensions,
        reason_codes=reason_codes,
    )


def _score_disposition(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    reasons: list[str] = []
    disposition = response.disposition

    if disposition is ResponseDisposition.ANSWER and disposition in task.forbidden_dispositions:
        reasons.append("forbidden_answer_disposition")
    elif disposition in task.forbidden_dispositions:
        reasons.append("forbidden_disposition")

    if disposition not in task.allowed_dispositions:
        if (
            ResponseDisposition.HANDOFF in task.allowed_dispositions
            and disposition is not ResponseDisposition.HANDOFF
        ):
            reasons.append("required_handoff_omitted")
        elif (
            ResponseDisposition.CLARIFY in task.allowed_dispositions
            and disposition is not ResponseDisposition.CLARIFY
        ):
            reasons.append("required_clarification_omitted")
        elif (
            ResponseDisposition.UNSUPPORTED in task.allowed_dispositions
            and disposition is not ResponseDisposition.UNSUPPORTED
        ):
            reasons.append("required_unsupported_disposition")
        elif disposition is ResponseDisposition.HANDOFF:
            reasons.append("unnecessary_escalation")
        else:
            reasons.append("unexpected_disposition")

    return _dimension("disposition", reasons)


def _score_evidence(
    task: SystemBenchmarkTask,
    reference: ReferenceExpectation,
    response: SystemBenchmarkResponse,
) -> DimensionResult:
    reasons: list[str] = []
    observed = tuple(response.evidence_refs)
    required = reference.required_evidence_refs
    allowed = set(reference.allowed_evidence_refs)

    for required_ref in required:
        if required_ref in observed:
            continue
        required_policy = parse_policy_evidence_ref(required_ref)
        wrong_version = False
        if required_policy is not None:
            req_doc, req_version, req_section = required_policy
            for observed_ref in observed:
                observed_policy = parse_policy_evidence_ref(observed_ref)
                if observed_policy is None:
                    continue
                obs_doc, obs_version, obs_section = observed_policy
                if obs_doc == req_doc and obs_section == req_section and obs_version != req_version:
                    wrong_version = True
                    break
        reasons.append("wrong_policy_version" if wrong_version else "missing_required_evidence")

    for observed_ref in observed:
        if observed_ref in allowed:
            continue
        observed_policy = parse_policy_evidence_ref(observed_ref)
        is_wrong_version = False
        if observed_policy is not None:
            obs_doc, obs_version, obs_section = observed_policy
            for required_ref in required:
                required_policy = parse_policy_evidence_ref(required_ref)
                if required_policy is None:
                    continue
                req_doc, req_version, req_section = required_policy
                if obs_doc == req_doc and obs_section == req_section and obs_version != req_version:
                    is_wrong_version = True
                    break
        if not is_wrong_version:
            reasons.append("unsupported_evidence_source")
            continue
        try:
            source_id = evidence_source_id(observed_ref)
        except ValueError:
            reasons.append("unsupported_evidence_source")
            continue
        if source_id not in task.acceptable_source_ids:
            reasons.append("unsupported_evidence_source")

    return _dimension("evidence", reasons)


def _score_tools(
    task: SystemBenchmarkTask,
    reference: ReferenceExpectation,
    observation: ScoringObservation,
) -> DimensionResult:
    reasons: list[str] = []
    observed = tuple(observation.tool_calls)
    for required_tool in reference.required_tools:
        if required_tool not in observed:
            reasons.append("missing_required_tool")
    forbidden = set(reference.forbidden_tools) | set(task.forbidden_tools)
    for tool in observed:
        if tool in forbidden:
            reasons.append("forbidden_tool_used")
        elif tool not in task.allowed_tools:
            reasons.append("unexpected_tool")
    return _dimension("tools", reasons)


def _score_structured_values(
    task: SystemBenchmarkTask, observation: ScoringObservation
) -> DimensionResult:
    reasons: list[str] = []
    for expectation in task.expected_values:
        if expectation.name not in observation.structured_values:
            reasons.append("missing_expected_value")
            continue
        observed = observation.structured_values[expectation.name]
        if not _matches_expectation(observed, expectation):
            reasons.append("structured_value_mismatch")
    return _dimension("structured_values", reasons)


def _score_clarification(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    reasons: list[str] = []
    if response.disposition is ResponseDisposition.CLARIFY:
        expected = task.required_clarification_concept
        clarification = response.clarification
        if expected is None:
            reasons.append("unexpected_clarification")
        elif not isinstance(clarification, Mapping):
            reasons.append("clarification_payload_missing")
        else:
            concept = clarification.get("concept")
            if (
                not isinstance(concept, str)
                or concept.strip().casefold() != expected.casefold()
            ):
                reasons.append("clarification_concept_mismatch")
    return _dimension("clarification", reasons)


def _score_handoff(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    reasons: list[str] = []
    if response.disposition is ResponseDisposition.HANDOFF:
        if not isinstance(response.handoff, Mapping):
            reasons.append("handoff_payload_missing")
        else:
            for field_name in task.required_handoff_fields:
                value = response.handoff.get(field_name)
                if value is None or value == "" or value == [] or value == ():
                    reasons.append(f"missing_handoff_field:{field_name}")
    return _dimension("handoff", reasons)


def _score_answer_bounds(
    reference: ReferenceExpectation, response: SystemBenchmarkResponse
) -> DimensionResult:
    reasons: list[str] = []
    answer = response.answer_text.casefold()
    for term in reference.required_answer_terms:
        if term.casefold() not in answer:
            reasons.append("required_answer_term_missing")
    for term in reference.forbidden_answer_terms:
        if term.casefold() in answer:
            reasons.append("forbidden_answer_term_present")
    return _dimension("answer_bounds", reasons)


def _matches_expectation(observed: Any, expectation: StructuredExpectation) -> bool:
    expected = expectation.value
    if (
        isinstance(expected, (int, float))
        and not isinstance(expected, bool)
        and isinstance(observed, (int, float))
        and not isinstance(observed, bool)
    ):
        expected_float = float(expected)
        observed_float = float(observed)
        if not math.isfinite(expected_float) or not math.isfinite(observed_float):
            return False
        tolerance = expectation.tolerance or 0.0
        return abs(observed_float - expected_float) <= tolerance
    if isinstance(expected, str) and isinstance(observed, str):
        return expected.casefold() == observed.casefold()
    return observed == expected


def _dimension(name: str, reasons: list[str]) -> DimensionResult:
    reason_codes = _stable_unique(reasons)
    return DimensionResult(name=name, passed=not reason_codes, reason_codes=reason_codes)


def _stable_unique(values) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)
