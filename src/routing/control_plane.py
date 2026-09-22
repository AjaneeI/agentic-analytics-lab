"""Deterministic control-plane routing primitives.

This module is intentionally model-free. It defines the typed routing contract,
normalizes explicit task facts, and applies deterministic precedence rules.
Semantic/learned routing can be layered on later without changing the execution
contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionRoute(str, Enum):
    DETERMINISTIC = "deterministic"
    LOCAL = "local"
    ESCALATE = "escalate"


class ReasonCode(str, Enum):
    DETERMINISTIC_HANDLER = "DETERMINISTIC_HANDLER"
    PRIOR_VALIDATION_FAILURE = "PRIOR_VALIDATION_FAILURE"
    AMBIGUOUS_TASK = "AMBIGUOUS_TASK"
    UNSUPPORTED_TOOL = "UNSUPPORTED_TOOL"
    LOCAL_ROUTINE_REASONING = "LOCAL_ROUTINE_REASONING"


@dataclass(frozen=True)
class TaskContext:
    """Explicit facts available to the control plane before execution."""

    task_type: str
    requires_tool: bool
    evidence_required: bool
    deterministic_handler_available: bool = False
    ambiguity_detected: bool = False
    prior_validation_failed: bool = False
    tool_supported: bool = True
    known_failure_category: str | None = None


@dataclass(frozen=True)
class RouteFeatures:
    """Normalized, inspectable features consumed by the v0 router."""

    task_type: str
    requires_tool: bool
    evidence_required: bool
    deterministic_handler_available: bool
    ambiguity_detected: bool
    prior_validation_failed: bool
    tool_supported: bool
    known_failure_category: str | None


@dataclass(frozen=True)
class RouteDecision:
    """Machine-readable decision produced by the control plane."""

    route: ExecutionRoute
    task_type: str
    requires_tool: bool
    evidence_required: bool
    reason_code: ReasonCode
    confidence: float | None = None


def extract_route_features(context: TaskContext) -> RouteFeatures:
    """Normalize explicit task facts without inferring intent from free text."""

    task_type = context.task_type.strip().lower()
    if not task_type:
        raise ValueError("task_type must be a non-empty string.")

    failure_category = context.known_failure_category
    if failure_category is not None:
        failure_category = failure_category.strip().lower() or None

    return RouteFeatures(
        task_type=task_type,
        requires_tool=context.requires_tool,
        evidence_required=context.evidence_required,
        deterministic_handler_available=context.deterministic_handler_available,
        ambiguity_detected=context.ambiguity_detected,
        prior_validation_failed=context.prior_validation_failed,
        tool_supported=context.tool_supported,
        known_failure_category=failure_category,
    )


def classify_route(features: RouteFeatures) -> RouteDecision:
    """Choose the cheapest safe route using deterministic precedence rules."""

    if features.prior_validation_failed:
        return _decision(
            features,
            ExecutionRoute.ESCALATE,
            ReasonCode.PRIOR_VALIDATION_FAILURE,
        )

    if features.ambiguity_detected:
        return _decision(
            features,
            ExecutionRoute.ESCALATE,
            ReasonCode.AMBIGUOUS_TASK,
        )

    if features.requires_tool and not features.tool_supported:
        return _decision(
            features,
            ExecutionRoute.ESCALATE,
            ReasonCode.UNSUPPORTED_TOOL,
        )

    if features.deterministic_handler_available:
        return _decision(
            features,
            ExecutionRoute.DETERMINISTIC,
            ReasonCode.DETERMINISTIC_HANDLER,
        )

    return _decision(
        features,
        ExecutionRoute.LOCAL,
        ReasonCode.LOCAL_ROUTINE_REASONING,
    )


def route_task(context: TaskContext) -> RouteDecision:
    """Convenience entry point for feature extraction + deterministic routing."""

    return classify_route(extract_route_features(context))


def parse_execution_route(value: str) -> ExecutionRoute:
    """Validate an externally supplied route label.

    Unknown labels raise instead of silently falling through to a permissive
    execution path.
    """

    try:
        return ExecutionRoute(value)
    except ValueError as exc:
        raise ValueError(f"Unsupported execution route: {value!r}") from exc


def _decision(
    features: RouteFeatures,
    route: ExecutionRoute,
    reason_code: ReasonCode,
) -> RouteDecision:
    return RouteDecision(
        route=route,
        task_type=features.task_type,
        requires_tool=features.requires_tool,
        evidence_required=features.evidence_required,
        reason_code=reason_code,
    )
