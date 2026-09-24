"""Typed contracts for System Benchmark v1.

This module is intentionally runtime-light. It validates benchmark metadata
without importing an agent, model runtime, or evidence tool.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from src.routing.control_plane import ExecutionRoute, parse_execution_route


class BenchmarkFamily(str, Enum):
    STRUCTURED_DETERMINISTIC_ANALYTICS = "A"
    TOOL_GROUNDED_ANALYTICAL_REASONING = "B"
    DOCUMENT_POLICY_RETRIEVAL = "C"
    MULTI_SOURCE_SYNTHESIS = "D"
    AMBIGUITY_CLARIFICATION_ESCALATION = "E"
    EPISTEMIC_CAUSAL_REASONING = "F"
    UNSUPPORTED_SOURCE_HANDLING = "G"
    HUMAN_HANDOFF_AUTHORITY_BOUNDARY = "H"


class BenchmarkSplit(str, Enum):
    DEVELOPMENT = "development"
    HELDOUT = "heldout"


class CapabilityProfile(str, Enum):
    NONE = "none"
    STRUCTURED = "structured"
    DOCUMENTS = "documents"
    MULTI_SOURCE = "multi_source"


class ResponseDisposition(str, Enum):
    ANSWER = "answer"
    CLARIFY = "clarify"
    UNSUPPORTED = "unsupported"
    HANDOFF = "handoff"


REQUIRED_HANDOFF_FIELDS = (
    "trigger",
    "evidence_refs",
    "actions_taken",
    "unresolved_uncertainty",
    "requested_authority",
)


@dataclass(frozen=True)
class StructuredExpectation:
    name: str
    value: Any
    tolerance: float | None = None


@dataclass(frozen=True)
class SystemBenchmarkTask:
    case_id: str
    benchmark_version: str
    family: BenchmarkFamily
    split: BenchmarkSplit
    request: str
    expected_route: ExecutionRoute
    expected_capability_profile: CapabilityProfile
    allowed_dispositions: tuple[ResponseDisposition, ...]
    forbidden_dispositions: tuple[ResponseDisposition, ...]
    required_evidence_source_types: tuple[str, ...]
    acceptable_source_ids: tuple[str, ...]
    expected_values: tuple[StructuredExpectation, ...]
    required_claims: tuple[str, ...]
    forbidden_claims: tuple[str, ...]
    required_clarification_concept: str | None
    required_handoff_fields: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    reference_solution_id: str


@dataclass(frozen=True)
class SystemBenchmarkResponse:
    disposition: ResponseDisposition
    answer_text: str
    evidence_refs: tuple[str, ...] = ()
    uncertainty: str | None = None
    clarification: dict[str, Any] | None = None
    handoff: dict[str, Any] | None = None


def parse_task_contract(payload: Mapping[str, Any]) -> SystemBenchmarkTask:
    """Validate one machine-readable task contract and return typed metadata."""

    if not isinstance(payload, Mapping):
        raise ValueError("task contract must be an object")

    case_id = _required_string(payload, "id")
    benchmark_version = _required_string(payload, "benchmark_version")
    family = _enum_value(
        BenchmarkFamily,
        _required_string(payload, "family"),
        label="family",
    )
    split = _enum_value(
        BenchmarkSplit,
        _required_string(payload, "split"),
        label="split",
    )
    request = _required_string(payload, "request")

    route_text = _required_string(payload, "expected_route")
    try:
        expected_route = parse_execution_route(route_text)
    except ValueError as exc:
        raise ValueError(f"invalid route: {route_text!r}") from exc

    expected_capability_profile = _enum_value(
        CapabilityProfile,
        _required_string(payload, "expected_capability_profile"),
        label="capability profile",
    )

    allowed_dispositions = _disposition_tuple(
        payload,
        "allowed_dispositions",
        require_nonempty=True,
    )
    forbidden_dispositions = _disposition_tuple(
        payload,
        "forbidden_dispositions",
    )
    if set(allowed_dispositions) & set(forbidden_dispositions):
        raise ValueError("allowed and forbidden disposition sets must be disjoint")

    required_evidence_source_types = _string_tuple(
        payload,
        "required_evidence_source_types",
    )
    if (
        expected_capability_profile is not CapabilityProfile.NONE
        and not required_evidence_source_types
    ):
        raise ValueError(
            "an evidence source type is required for non-none capability profiles"
        )

    acceptable_source_ids = _string_tuple(payload, "acceptable_source_ids")
    expected_values = _expectation_tuple(payload)
    required_claims = _string_tuple(payload, "required_claims")
    forbidden_claims = _string_tuple(payload, "forbidden_claims")

    clarification = payload.get("required_clarification_concept")
    if clarification is not None:
        if not isinstance(clarification, str) or not clarification.strip():
            raise ValueError(
                "required clarification concept must be a non-empty string or null"
            )
        clarification = clarification.strip()

    if (
        ResponseDisposition.CLARIFY in allowed_dispositions
        and clarification is None
    ):
        raise ValueError(
            "clarification disposition requires a clarification concept"
        )

    required_handoff_fields = _string_tuple(
        payload,
        "required_handoff_fields",
    )
    if ResponseDisposition.HANDOFF in allowed_dispositions:
        missing = set(REQUIRED_HANDOFF_FIELDS) - set(required_handoff_fields)
        if missing:
            raise ValueError(
                "handoff disposition requires canonical handoff fields: "
                + ", ".join(sorted(missing))
            )

    allowed_tools = _string_tuple(payload, "allowed_tools")
    forbidden_tools = _string_tuple(payload, "forbidden_tools")
    if set(allowed_tools) & set(forbidden_tools):
        raise ValueError("allowed and forbidden tool sets must be disjoint")

    reference_solution_id = _required_string(payload, "reference_solution_id")

    return SystemBenchmarkTask(
        case_id=case_id,
        benchmark_version=benchmark_version,
        family=family,
        split=split,
        request=request,
        expected_route=expected_route,
        expected_capability_profile=expected_capability_profile,
        allowed_dispositions=allowed_dispositions,
        forbidden_dispositions=forbidden_dispositions,
        required_evidence_source_types=required_evidence_source_types,
        acceptable_source_ids=acceptable_source_ids,
        expected_values=expected_values,
        required_claims=required_claims,
        forbidden_claims=forbidden_claims,
        required_clarification_concept=clarification,
        required_handoff_fields=required_handoff_fields,
        allowed_tools=allowed_tools,
        forbidden_tools=forbidden_tools,
        reference_solution_id=reference_solution_id,
    )


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _enum_value(enum_type: type[Enum], value: str, *, label: str):
    try:
        return enum_type(value)
    except ValueError as exc:
        raise ValueError(f"invalid {label}: {value!r}") from exc


def _string_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        raise ValueError(f"{key} must be a list")

    values: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key} must contain only non-empty strings")
        values.append(item.strip())
    return tuple(values)


def _disposition_tuple(
    payload: Mapping[str, Any],
    key: str,
    *,
    require_nonempty: bool = False,
) -> tuple[ResponseDisposition, ...]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        raise ValueError(f"{key} disposition list is required")
    if require_nonempty and not raw:
        raise ValueError(f"{key} disposition list must be non-empty")

    values: list[ResponseDisposition] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(f"invalid disposition in {key}")
        try:
            values.append(ResponseDisposition(item.strip()))
        except ValueError as exc:
            raise ValueError(f"invalid disposition: {item!r}") from exc
    return tuple(values)


def _expectation_tuple(
    payload: Mapping[str, Any],
) -> tuple[StructuredExpectation, ...]:
    raw = payload.get("expected_values")
    if not isinstance(raw, list):
        raise ValueError("expected_values must be a list")

    expectations: list[StructuredExpectation] = []
    for item in raw:
        if not isinstance(item, Mapping):
            raise ValueError("each expected value must be an object")
        name = _required_string(item, "name")
        if "value" not in item:
            raise ValueError(f"expected value {name!r} is missing value")

        tolerance = item.get("tolerance")
        if tolerance is not None:
            if (
                isinstance(tolerance, bool)
                or not isinstance(tolerance, (int, float))
                or tolerance < 0
            ):
                raise ValueError(
                    f"tolerance for expected value {name!r} must be a non-negative number"
                )
            tolerance = float(tolerance)

        expectations.append(
            StructuredExpectation(
                name=name,
                value=item["value"],
                tolerance=tolerance,
            )
        )
    return tuple(expectations)
