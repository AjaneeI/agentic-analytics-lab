"""Hierarchical failure taxonomy for observable benchmark failures.

The taxonomy adds a stable category/subtype layer without replacing the raw
reason codes or diagnostic stages that remain the primary evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, order=True)
class FailureTag:
    category: str
    subtype: str

    @property
    def code(self) -> str:
        return f"{self.category}.{self.subtype}"


_REASON_CODE_MAP = {
    "missing_required_evidence": FailureTag("grounding", "missing_evidence"),
    "unsupported_evidence_source": FailureTag("grounding", "unsupported_evidence"),
    "wrong_policy_version": FailureTag("grounding", "wrong_version"),
    "missing_required_tool": FailureTag("tool_use", "missing_required_tool"),
    "forbidden_tool_used": FailureTag("tool_use", "forbidden_tool"),
    "unexpected_tool": FailureTag("tool_use", "unexpected_tool"),
    "structured_value_mismatch": FailureTag("reasoning", "structured_value_mismatch"),
    "missing_expected_value": FailureTag("reasoning", "missing_expected_value"),
    "required_clarification_omitted": FailureTag("reasoning", "failed_to_clarify"),
    "clarification_payload_missing": FailureTag("reasoning", "malformed_clarification"),
    "required_handoff_omitted": FailureTag("authority", "failed_to_handoff"),
    "forbidden_answer_disposition": FailureTag("authority", "unauthorized_answer"),
    "unnecessary_escalation": FailureTag("routing", "unnecessary_escalation"),
    "required_unsupported_disposition": FailureTag("grounding", "unsupported_source_not_acknowledged"),
    "unexpected_disposition": FailureTag("reasoning", "unexpected_disposition"),
}

_STAGE_MAP = {
    "tool_selection": FailureTag("tool_use", "no_grounding_action"),
    "tool_execution": FailureTag("execution", "tool_error"),
    "tool_grounding": FailureTag("grounding", "tool_grounding_failure"),
    "evidence_generation": FailureTag("grounding", "evidence_generation_failure"),
    "answer_reasoning": FailureTag("reasoning", "answer_failure"),
    "execution": FailureTag("execution", "runtime_failure"),
    "unclassified": FailureTag("unknown", "unclassified"),
}


def classify_failure(
    *,
    reason_codes: Iterable[str] = (),
    diagnostic_stage: str | None = None,
    recovered: bool | None = None,
) -> tuple[FailureTag, ...]:
    """Return stable taxonomy tags while preserving unknown observations."""

    tags = {
        _REASON_CODE_MAP[code]
        for code in reason_codes
        if code in _REASON_CODE_MAP
    }

    if diagnostic_stage in _STAGE_MAP:
        tags.add(_STAGE_MAP[diagnostic_stage])

    if recovered is True:
        tags.add(FailureTag("recovery", "recovered"))
    elif recovered is False:
        tags.add(FailureTag("recovery", "unrecovered"))

    if not tags:
        tags.add(FailureTag("unknown", "unclassified"))

    return tuple(sorted(tags))


def taxonomy_codes(
    *,
    reason_codes: Iterable[str] = (),
    diagnostic_stage: str | None = None,
    recovered: bool | None = None,
) -> tuple[str, ...]:
    return tuple(
        tag.code
        for tag in classify_failure(
            reason_codes=reason_codes,
            diagnostic_stage=diagnostic_stage,
            recovered=recovered,
        )
    )
