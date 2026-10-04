"""Deterministic scoring for System Benchmark v1 development cases."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import math
import re
from typing import Any

from src.evals.system_benchmark.contracts import (
    BenchmarkExecutionRoute,
    BenchmarkFamily,
    ResponseDisposition,
    StructuredExpectation,
    SystemBenchmarkResponse,
    SystemBenchmarkTask,
)


_SOURCE_TOOL = {
    "structured": "query_clickhouse",
    "policy": "retrieve_policy",
}
_POLICY_REF_RE = re.compile(r"^policy:([^@]+)@([^#]+)#(.+)$")


@dataclass(frozen=True)
class DimensionResult:
    name: str
    passed: bool
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class ScoreResult:
    passed: bool
    dimensions: tuple[DimensionResult, ...]
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "dimensions": [item.to_dict() for item in self.dimensions],
            "reason_codes": list(self.reason_codes),
        }


def score_response(
    task: SystemBenchmarkTask,
    response: SystemBenchmarkResponse,
    *,
    observed_tools: Sequence[str] = (),
    observed_values: Mapping[str, Any] | None = None,
    validator_passed: bool = True,
) -> ScoreResult:
    """Score observable behavior without model inference or hidden reasoning."""

    tools = _validate_tools(observed_tools)
    values = _validate_values(observed_values)
    if not isinstance(validator_passed, bool):
        raise ValueError("validator_passed must be a boolean")

    dimensions = (
        _score_disposition(task, response),
        _score_tools(task, tools),
        _score_evidence(task, response),
        _score_values(task.expected_values, values),
        _score_claims(task, response),
        _score_clarification(task, response),
        _score_handoff(task, response),
        _score_validator(validator_passed),
    )
    reasons: list[str] = []
    for dimension in dimensions:
        for code in dimension.reason_codes:
            if code not in reasons:
                reasons.append(code)
    return ScoreResult(
        passed=all(item.passed for item in dimensions),
        dimensions=dimensions,
        reason_codes=tuple(reasons),
    )


def _validate_tools(observed_tools: Sequence[str]) -> tuple[str, ...]:
    if isinstance(observed_tools, (str, bytes)) or not isinstance(observed_tools, Sequence):
        raise ValueError("observed_tools must be a sequence of tool names")
    tools: list[str] = []
    for item in observed_tools:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("observed_tools must contain only non-empty strings")
        tools.append(item.strip())
    return tuple(tools)


def _validate_values(observed_values: Mapping[str, Any] | None) -> dict[str, Any]:
    if observed_values is None:
        return {}
    if not isinstance(observed_values, Mapping):
        raise ValueError("observed_values must be a mapping")
    values: dict[str, Any] = {}
    for key, value in observed_values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("observed_values keys must be non-empty strings")
        values[key.strip()] = value
    return values


def _dimension(name: str, codes: list[str]) -> DimensionResult:
    return DimensionResult(name=name, passed=not codes, reason_codes=tuple(codes))


def _score_disposition(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    codes: list[str] = []
    if response.disposition not in task.allowed_dispositions:
        codes.append(f"disposition_not_allowed:{response.disposition.value}")
    if response.disposition in task.forbidden_dispositions:
        codes.append(f"forbidden_disposition:{response.disposition.value}")

    escalation_dispositions = {
        ResponseDisposition.CLARIFY,
        ResponseDisposition.UNSUPPORTED,
        ResponseDisposition.HANDOFF,
    }
    if (
        task.expected_route is BenchmarkExecutionRoute.ESCALATE
        and response.disposition not in escalation_dispositions
    ):
        codes.append("required_escalation_missing")
    if (
        task.expected_route is not BenchmarkExecutionRoute.ESCALATE
        and response.disposition in {ResponseDisposition.CLARIFY, ResponseDisposition.HANDOFF}
    ):
        codes.append("unnecessary_escalation")

    if (
        task.family is BenchmarkFamily.AMBIGUITY_CLARIFICATION_ESCALATION
        and task.expected_route is BenchmarkExecutionRoute.ESCALATE
        and Counter(task.required_evidence_source_types)["policy"] >= 2
        and response.disposition is ResponseDisposition.ANSWER
    ):
        codes.append("policy_conflict_silently_resolved")
    if (
        task.family is BenchmarkFamily.UNSUPPORTED_SOURCE_HANDLING
        and response.disposition is not ResponseDisposition.UNSUPPORTED
    ):
        codes.append("unsupported_source_not_acknowledged")
    return _dimension("disposition", codes)


def _score_tools(task: SystemBenchmarkTask, tools: tuple[str, ...]) -> DimensionResult:
    codes: list[str] = []
    allowed = set(task.allowed_tools)
    forbidden = set(task.forbidden_tools)
    for tool in tools:
        if tool in forbidden:
            codes.append(f"forbidden_tool_used:{tool}")
        elif tool not in allowed:
            codes.append(f"tool_not_allowed:{tool}")

    required_types = set(task.required_evidence_source_types)
    for source_type in sorted(required_types):
        required_tool = _SOURCE_TOOL.get(source_type)
        if required_tool and required_tool not in tools:
            codes.append(f"required_tool_missing:{required_tool}")
    return _dimension("tools", codes)


def _score_evidence(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    codes: list[str] = []
    refs = tuple(response.evidence_refs)
    if task.family is BenchmarkFamily.UNSUPPORTED_SOURCE_HANDLING and refs:
        codes.append("fabricated_source")

    acceptable = set(task.acceptable_source_ids)
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            codes.append("malformed_evidence_ref")
            continue
        if ref not in acceptable:
            if acceptable and _is_wrong_policy_version(ref, acceptable):
                codes.append("wrong_policy_version")
            else:
                codes.append(f"unacceptable_source:{ref}")

    required_counts = Counter(task.required_evidence_source_types)
    unique_refs = set(refs)
    observed_counts = Counter(_source_type(ref) for ref in unique_refs)
    for source_type, required_count in sorted(required_counts.items()):
        if observed_counts[source_type] < required_count:
            codes.append(f"required_evidence_missing:{source_type}")
    return _dimension("evidence", codes)


def _source_type(ref: str) -> str:
    if not isinstance(ref, str) or ":" not in ref:
        return ""
    return ref.split(":", 1)[0]


def _is_wrong_policy_version(ref: str, acceptable: set[str]) -> bool:
    match = _POLICY_REF_RE.match(ref)
    if not match:
        return False
    document_id, version, section = match.groups()
    for expected in acceptable:
        expected_match = _POLICY_REF_RE.match(expected)
        if not expected_match:
            continue
        exp_doc, exp_version, exp_section = expected_match.groups()
        if document_id == exp_doc and section == exp_section and version != exp_version:
            return True
    return False


def _score_values(
    expectations: tuple[StructuredExpectation, ...],
    observed: Mapping[str, Any],
) -> DimensionResult:
    codes: list[str] = []
    for expectation in expectations:
        if expectation.name not in observed:
            codes.append(f"expected_value_missing:{expectation.name}")
            continue
        actual = observed[expectation.name]
        if not _value_matches(expectation, actual):
            codes.append(f"expected_value_mismatch:{expectation.name}")
    return _dimension("structured_values", codes)


def _value_matches(expectation: StructuredExpectation, actual: Any) -> bool:
    if expectation.tolerance is None:
        return actual == expectation.value
    if isinstance(actual, bool) or not isinstance(actual, (int, float)):
        return False
    if isinstance(expectation.value, bool) or not isinstance(
        expectation.value, (int, float)
    ):
        return False
    try:
        actual_number = float(actual)
        expected_number = float(expectation.value)
    except (TypeError, ValueError, OverflowError):
        return False
    if not math.isfinite(actual_number) or not math.isfinite(expected_number):
        return False
    return abs(actual_number - expected_number) <= expectation.tolerance


def _normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def _score_claims(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    codes: list[str] = []
    text = _normalized(response.answer_text)
    for claim in task.required_claims:
        if _normalized(claim) not in text:
            codes.append(f"required_claim_missing:{claim}")
    for claim in task.forbidden_claims:
        if _normalized(claim) in text:
            codes.append(f"forbidden_claim_present:{claim}")
    return _dimension("claims", codes)


def _score_clarification(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    codes: list[str] = []
    concept = task.required_clarification_concept
    if concept is not None:
        if response.disposition is not ResponseDisposition.CLARIFY:
            codes.append("clarification_missing")
        else:
            payload = response.clarification
            if not isinstance(payload, Mapping):
                codes.append("clarification_missing")
            else:
                rendered = _normalized(str(dict(payload)))
                if _normalized(concept) not in rendered:
                    codes.append("clarification_concept_missing")
    return _dimension("clarification", codes)


def _score_handoff(
    task: SystemBenchmarkTask, response: SystemBenchmarkResponse
) -> DimensionResult:
    codes: list[str] = []
    if task.required_handoff_fields:
        if response.disposition is not ResponseDisposition.HANDOFF:
            codes.append("handoff_missing")
        elif not isinstance(response.handoff, Mapping):
            codes.append("handoff_missing")
        else:
            for field in task.required_handoff_fields:
                value = response.handoff.get(field)
                if value is None or value == "" or value == [] or value == ():
                    codes.append(f"handoff_incomplete:{field}")
    return _dimension("handoff", codes)


def _score_validator(validator_passed: bool) -> DimensionResult:
    return _dimension("validator", [] if validator_passed else ["validator_rejected"])
