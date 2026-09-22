"""Deterministic validation and escalation contracts for routed execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ValidationDisposition(str, Enum):
    ACCEPT = "accept"
    RETRY = "retry"
    ESCALATE = "escalate"
    FAIL_CLOSED = "fail_closed"


class ValidationReason(str, Enum):
    VALIDATED = "VALIDATED"
    SECURITY_BOUNDARY_VIOLATION = "SECURITY_BOUNDARY_VIOLATION"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    OUTPUT_INVALID = "OUTPUT_INVALID"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"


@dataclass(frozen=True)
class ValidationContext:
    """Explicit validator facts collected after worker execution."""

    output_valid: bool
    evidence_satisfied: bool
    evidence_required: bool = True
    security_boundary_violated: bool = False
    retryable_failure: bool = False
    retry_count: int = 0
    max_retries: int = 1

    def __post_init__(self) -> None:
        if self.retry_count < 0:
            raise ValueError("retry_count must be non-negative.")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative.")


@dataclass(frozen=True)
class ValidationResult:
    disposition: ValidationDisposition
    reason: ValidationReason


def validate_execution(context: ValidationContext) -> ValidationResult:
    """Choose accept/retry/escalate/fail-closed using deterministic precedence."""

    if context.security_boundary_violated:
        return ValidationResult(
            disposition=ValidationDisposition.FAIL_CLOSED,
            reason=ValidationReason.SECURITY_BOUNDARY_VIOLATION,
        )

    evidence_ok = not context.evidence_required or context.evidence_satisfied
    if context.output_valid and evidence_ok:
        return ValidationResult(
            disposition=ValidationDisposition.ACCEPT,
            reason=ValidationReason.VALIDATED,
        )

    if context.retryable_failure and context.retry_count < context.max_retries:
        return ValidationResult(
            disposition=ValidationDisposition.RETRY,
            reason=ValidationReason.RETRYABLE_FAILURE,
        )

    if not context.output_valid:
        return ValidationResult(
            disposition=ValidationDisposition.ESCALATE,
            reason=ValidationReason.OUTPUT_INVALID,
        )

    return ValidationResult(
        disposition=ValidationDisposition.ESCALATE,
        reason=ValidationReason.EVIDENCE_MISSING,
    )
