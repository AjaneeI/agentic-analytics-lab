"""Model-free routing treatments for System Benchmark v1.

This module keeps route inference separate from worker execution.  Oracle
routing may consume benchmark metadata; natural-language and heuristic routing
receive only the user request text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from src.evals.system_benchmark.contracts import (
    BenchmarkExecutionRoute,
    CapabilityProfile,
    SystemBenchmarkTask,
)
from src.routing.control_plane import ExecutionRoute
from src.routing.natural_language_baseline import classify_natural_language


@dataclass(frozen=True)
class RoutingDecision:
    route: BenchmarkExecutionRoute
    capability_profile: CapabilityProfile
    reason_code: str
    escalation_mode: str | None = None


@dataclass(frozen=True)
class RoutingMetrics:
    total: int
    route_correct: int
    capability_profile_correct: int
    route_accuracy: float
    capability_profile_accuracy: float
    confusion_matrix: dict[str, dict[str, int]]
    false_cheap_routes: int
    unnecessary_escalations: int
    unsupported_source_misses: int


Classifier = Callable[[str], Any]


_UNSUPPORTED_SOURCE_CUES = (
    "jira",
    "salesforce",
    "crm",
    "slack",
    "gmail",
    "email",
    "notion",
    "asana",
    "sharepoint",
)
_DOCUMENT_CUES = (
    "policy",
    "definition",
    "dictionary",
    "guideline",
    "procedure",
    "service-level",
    "service level",
    "according to",
    "as of",
)
_STRUCTURED_CUES = (
    "dataset",
    "blocker rate",
    "blocker-rate",
    "blocked items",
    "effort ratio",
    "actual",
    "planned",
    "team",
    "percentage",
    "percent",
    "count",
)
_MULTI_SOURCE_CUES = (
    "interpret",
    "using the",
    "according to",
    "policy",
    "definition",
    "dictionary",
)


def oracle_route(task: SystemBenchmarkTask) -> RoutingDecision:
    """Return the benchmark-supplied upper-bound route/capability decision."""

    return RoutingDecision(
        route=task.expected_route,
        capability_profile=task.expected_capability_profile,
        reason_code="oracle_metadata",
        escalation_mode=_oracle_escalation_mode(task),
    )


def natural_language_route(
    request: str,
    *,
    classifier: Classifier = classify_natural_language,
) -> RoutingDecision:
    """Adapt the existing free-text route baseline without benchmark metadata."""

    text = _normalized_request(request)
    raw = classifier(text)
    route = _coerce_route(getattr(raw, "route", raw))
    reason = str(getattr(raw, "reason", "natural_language_route"))
    capability = infer_capability_profile(text, route=route)

    return RoutingDecision(
        route=route,
        capability_profile=capability,
        reason_code=reason,
        escalation_mode=_infer_escalation_mode(text, route),
    )


def simple_heuristic_route(request: str) -> RoutingDecision:
    """Inspectable lexical route + capability baseline."""

    text = _normalized_request(request)
    lowered = text.casefold()
    if any(cue in lowered for cue in _UNSUPPORTED_SOURCE_CUES):
        route = BenchmarkExecutionRoute.ESCALATE
        reason = "unsupported_external_source"
    else:
        route_result = classify_natural_language(text)
        route = _coerce_route(route_result.route)
        reason = route_result.reason
    capability = infer_capability_profile(text, route=route)

    return RoutingDecision(
        route=route,
        capability_profile=capability,
        reason_code=f"heuristic:{reason}",
        escalation_mode=_infer_escalation_mode(text, route),
    )


def infer_capability_profile(
    request: str,
    *,
    route: BenchmarkExecutionRoute | None = None,
) -> CapabilityProfile:
    """Infer only the evidence capability implied by realistic request text."""

    text = _normalized_request(request)
    lowered = text.casefold()
    if any(cue in lowered for cue in _UNSUPPORTED_SOURCE_CUES):
        return CapabilityProfile.NONE

    causal_or_epistemic = any(
        cue in lowered
        for cue in ("cause", "causal", "prove", "generalize", "generalise")
    )
    if causal_or_epistemic:
        return CapabilityProfile.NONE

    has_documents = any(cue in lowered for cue in _DOCUMENT_CUES)
    has_structured = any(cue in lowered for cue in _STRUCTURED_CUES)
    document_definition_only = (
        has_documents
        and any(cue in lowered for cue in ("definition", "dictionary", "according to", "as of"))
        and not any(cue in lowered for cue in ("identify", "which team", "highest", "lowest", "rank", "compare"))
    )
    explicitly_combines = (
        has_structured
        and has_documents
        and not document_definition_only
        and any(cue in lowered for cue in _MULTI_SOURCE_CUES)
    )

    if explicitly_combines:
        return CapabilityProfile.MULTI_SOURCE
    if has_documents:
        return CapabilityProfile.DOCUMENTS
    if has_structured:
        return CapabilityProfile.STRUCTURED

    if route is BenchmarkExecutionRoute.DETERMINISTIC:
        return CapabilityProfile.STRUCTURED
    return CapabilityProfile.NONE


def evaluate_route_decisions(
    cases: Iterable[tuple[SystemBenchmarkTask, RoutingDecision]],
) -> RoutingMetrics:
    """Evaluate route quality independently from worker/task outcome."""

    labels = [route.value for route in BenchmarkExecutionRoute]
    confusion = {
        expected: {actual: 0 for actual in labels}
        for expected in labels
    }
    total = route_correct = capability_correct = 0
    false_cheap = unnecessary_escalations = unsupported_misses = 0

    for task, decision in cases:
        total += 1
        expected_route = task.expected_route
        expected_capability = task.expected_capability_profile
        confusion[expected_route.value][decision.route.value] += 1

        if decision.route is expected_route:
            route_correct += 1
        elif (
            expected_route is BenchmarkExecutionRoute.ESCALATE
            and decision.route is not BenchmarkExecutionRoute.ESCALATE
        ):
            false_cheap += 1
        elif (
            expected_route is not BenchmarkExecutionRoute.ESCALATE
            and decision.route is BenchmarkExecutionRoute.ESCALATE
        ):
            unnecessary_escalations += 1

        if decision.capability_profile is expected_capability:
            capability_correct += 1

        if (
            _task_is_unsupported(task)
            and (
                decision.route is not BenchmarkExecutionRoute.ESCALATE
                or decision.capability_profile is not CapabilityProfile.NONE
            )
        ):
            unsupported_misses += 1

    if total == 0:
        raise ValueError("at least one routing case is required")

    return RoutingMetrics(
        total=total,
        route_correct=route_correct,
        capability_profile_correct=capability_correct,
        route_accuracy=route_correct / total,
        capability_profile_accuracy=capability_correct / total,
        confusion_matrix=confusion,
        false_cheap_routes=false_cheap,
        unnecessary_escalations=unnecessary_escalations,
        unsupported_source_misses=unsupported_misses,
    )


def _normalized_request(request: str) -> str:
    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be a non-empty string")
    return " ".join(request.strip().split())


def _coerce_route(value: Any) -> BenchmarkExecutionRoute:
    if isinstance(value, BenchmarkExecutionRoute):
        return value
    if isinstance(value, ExecutionRoute):
        return BenchmarkExecutionRoute(value.value)
    if isinstance(value, str):
        try:
            return BenchmarkExecutionRoute(value)
        except ValueError as exc:
            raise ValueError(f"unsupported route: {value!r}") from exc
    raise TypeError("router must return a route string, enum, or object with .route")


def _task_is_unsupported(task: SystemBenchmarkTask) -> bool:
    return task.family.value == "G"


def _oracle_escalation_mode(task: SystemBenchmarkTask) -> str | None:
    if task.expected_route is not BenchmarkExecutionRoute.ESCALATE:
        return None
    if task.family.value == "G":
        return "unsupported_source"
    if task.family.value == "H":
        return "human_authority"
    if task.required_clarification_concept is not None:
        return "clarify"
    return "escalate"


def _infer_escalation_mode(
    text: str,
    route: BenchmarkExecutionRoute,
) -> str | None:
    if route is not BenchmarkExecutionRoute.ESCALATE:
        return None
    lowered = text.casefold()
    if any(cue in lowered for cue in _UNSUPPORTED_SOURCE_CUES):
        return "unsupported_source"
    if "approve" in lowered or "authorize" in lowered or "authority" in lowered:
        return "human_authority"
    return "clarify"
