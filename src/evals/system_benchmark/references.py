"""Deterministic reference expectations for System Benchmark v1 development cases."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from src.evals.system_benchmark.contracts import SystemBenchmarkTask


_REFERENCE_FIELDS = {
    "reference_solution_id",
    "required_evidence_refs",
    "allowed_evidence_refs",
    "required_tools",
    "forbidden_tools",
    "required_answer_terms",
    "forbidden_answer_terms",
}
_POLICY_REF_RE = re.compile(
    r"^policy:(?P<document_id>[^@:#]+)@(?P<version>[^#:@]+)#(?P<section_id>[^#:@]+)$"
)
_STRUCTURED_REF_RE = re.compile(r"^structured:(?P<source_id>[^:]+)$")


@dataclass(frozen=True)
class ReferenceExpectation:
    """Machine-checkable reference constraints for one development task."""

    reference_solution_id: str
    required_evidence_refs: tuple[str, ...]
    allowed_evidence_refs: tuple[str, ...]
    required_tools: tuple[str, ...]
    forbidden_tools: tuple[str, ...]
    required_answer_terms: tuple[str, ...]
    forbidden_answer_terms: tuple[str, ...]


def parse_reference_expectation(payload: Mapping[str, Any]) -> ReferenceExpectation:
    """Validate one reference expectation without importing runtime/model code."""

    if not isinstance(payload, Mapping):
        raise ValueError("reference expectation must be an object")
    unknown = set(payload) - _REFERENCE_FIELDS
    if unknown:
        raise ValueError("unknown reference expectation fields: " + ", ".join(sorted(unknown)))

    reference_solution_id = _required_string(payload, "reference_solution_id")
    required_evidence_refs = _string_tuple(payload, "required_evidence_refs")
    allowed_evidence_refs = _string_tuple(payload, "allowed_evidence_refs")
    required_tools = _string_tuple(payload, "required_tools")
    forbidden_tools = _string_tuple(payload, "forbidden_tools")
    required_answer_terms = _string_tuple(payload, "required_answer_terms")
    forbidden_answer_terms = _string_tuple(payload, "forbidden_answer_terms")

    if not set(required_evidence_refs).issubset(allowed_evidence_refs):
        raise ValueError("required evidence refs must be included in allowed evidence refs")
    if set(required_tools) & set(forbidden_tools):
        raise ValueError("required and forbidden tool sets must be disjoint")
    if set(required_answer_terms) & set(forbidden_answer_terms):
        raise ValueError("required and forbidden answer terms must be disjoint")

    for evidence_ref in allowed_evidence_refs:
        _parse_evidence_ref(evidence_ref)

    return ReferenceExpectation(
        reference_solution_id=reference_solution_id,
        required_evidence_refs=required_evidence_refs,
        allowed_evidence_refs=allowed_evidence_refs,
        required_tools=required_tools,
        forbidden_tools=forbidden_tools,
        required_answer_terms=required_answer_terms,
        forbidden_answer_terms=forbidden_answer_terms,
    )


def load_references(path: str | Path) -> list[ReferenceExpectation]:
    """Load a non-empty list of unique deterministic reference expectations."""

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("System Benchmark references must contain a list")
    if not raw:
        raise ValueError("System Benchmark references must contain a non-empty list")

    references: list[ReferenceExpectation] = []
    seen: set[str] = set()
    for item in raw:
        reference = parse_reference_expectation(item)
        if reference.reference_solution_id in seen:
            raise ValueError(
                "Duplicate System Benchmark reference id: "
                + reference.reference_solution_id
            )
        seen.add(reference.reference_solution_id)
        references.append(reference)
    return references


def validate_task_reference(
    task: SystemBenchmarkTask, reference: ReferenceExpectation
) -> None:
    """Validate task/reference compatibility before any response is scored."""

    if task.reference_solution_id != reference.reference_solution_id:
        raise ValueError("task/reference reference_solution_id mismatch")

    required_tools = set(reference.required_tools)
    if not required_tools.issubset(task.allowed_tools):
        raise ValueError("reference required_tools must be permitted by task allowed_tools")
    if not set(reference.forbidden_tools).issubset(task.forbidden_tools):
        raise ValueError("reference forbidden_tools must be declared by task forbidden_tools")

    acceptable_sources = set(task.acceptable_source_ids)
    required_source_types = set(task.required_evidence_source_types)
    required_ref_types = {
        evidence_source_type(evidence_ref)
        for evidence_ref in reference.required_evidence_refs
    }
    if not required_source_types.issubset(required_ref_types):
        raise ValueError(
            "reference required evidence must cover every task required source type"
        )

    for evidence_ref in reference.allowed_evidence_refs:
        source_type = evidence_source_type(evidence_ref)
        if source_type not in required_source_types:
            raise ValueError(
                f"reference evidence source type {source_type!r} is not required by task"
            )
        source_id = evidence_source_id(evidence_ref)
        if source_id not in acceptable_sources:
            raise ValueError(
                f"reference evidence source {source_id!r} is not in task acceptable_source_ids"
            )


def evidence_source_id(evidence_ref: str) -> str:
    """Return the source identifier encoded by a validated evidence reference."""

    kind, data = _parse_evidence_ref(evidence_ref)
    if kind == "policy":
        return data["document_id"]
    return data["source_id"]


def evidence_source_type(evidence_ref: str) -> str:
    """Return the evidence source type encoded by a validated reference."""

    kind, _ = _parse_evidence_ref(evidence_ref)
    return kind


def parse_policy_evidence_ref(evidence_ref: str) -> tuple[str, str, str] | None:
    """Return policy document/version/section identity, or None for non-policy refs."""

    match = _POLICY_REF_RE.fullmatch(evidence_ref)
    if not match:
        return None
    return (
        match.group("document_id"),
        match.group("version"),
        match.group("section_id"),
    )


def _parse_evidence_ref(evidence_ref: str) -> tuple[str, dict[str, str]]:
    if not isinstance(evidence_ref, str) or not evidence_ref.strip():
        raise ValueError("evidence refs must be non-empty strings")
    value = evidence_ref.strip()
    policy = _POLICY_REF_RE.fullmatch(value)
    if policy:
        return "policy", policy.groupdict()
    structured = _STRUCTURED_REF_RE.fullmatch(value)
    if structured:
        return "structured", structured.groupdict()
    raise ValueError(f"unsupported evidence ref format: {evidence_ref!r}")


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _string_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    raw = payload.get(key)
    if not isinstance(raw, list):
        raise ValueError(f"{key} must be a list")
    values: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key} must contain only non-empty strings")
        value = item.strip()
        if value in values:
            raise ValueError(f"{key} must not contain duplicates")
        values.append(value)
    return tuple(values)
