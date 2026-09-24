"""Inspectable natural-language routing baseline.

This is a deliberately small lexical baseline for route-inference experiments.
It is not the production router and it does not use frozen Q1-Q6 metadata.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.routing.control_plane import ExecutionRoute


_UNSUPPORTED_SOURCE_CUES = (
    "jira",
    "salesforce",
    "gmail",
    "email",
    "slack",
    "notion",
    "asana",
    "sharepoint",
)

_AMBIGUITY_CUES = (
    "not sure",
    "whichever",
    "whatever definition",
    "either definition",
    "seems right",
    "ambiguous",
)

_CAUSAL_OR_GENERALIZATION_CUES = (
    "cause",
    "causal",
    "correlation",
    "randomized",
    "randomised",
    "study design",
    "generalize",
    "generalise",
    "production",
)

_ANALYTIC_OPERATION_CUES = (
    "which team",
    "rank",
    "order",
    "compare",
    "find the team",
    "give me",
    "leader",
    "highest",
    "lowest",
    "most",
    "least",
)

_DATA_METRIC_CUES = (
    "blocker",
    "blocked",
    "effort",
    "ratio",
    "percentage",
    "percent",
    "count",
    "planned",
    "actual",
)


@dataclass(frozen=True)
class NaturalLanguageRoute:
    route: ExecutionRoute
    reason: str
    matched_cues: tuple[str, ...] = ()


def classify_natural_language(question: str) -> NaturalLanguageRoute:
    """Infer a coarse route from free text without benchmark metadata."""

    text = question.strip().casefold()
    if not text:
        raise ValueError("question must be a non-empty string.")

    unsupported = tuple(cue for cue in _UNSUPPORTED_SOURCE_CUES if cue in text)
    if unsupported:
        return NaturalLanguageRoute(
            route=ExecutionRoute.ESCALATE,
            reason="unsupported_external_source",
            matched_cues=unsupported,
        )

    ambiguous = tuple(cue for cue in _AMBIGUITY_CUES if cue in text)
    if ambiguous:
        return NaturalLanguageRoute(
            route=ExecutionRoute.ESCALATE,
            reason="explicit_ambiguity",
            matched_cues=ambiguous,
        )

    causal = tuple(cue for cue in _CAUSAL_OR_GENERALIZATION_CUES if cue in text)
    if causal:
        return NaturalLanguageRoute(
            route=ExecutionRoute.LOCAL,
            reason="open_ended_reasoning",
            matched_cues=causal,
        )

    operations = tuple(cue for cue in _ANALYTIC_OPERATION_CUES if cue in text)
    metrics = tuple(cue for cue in _DATA_METRIC_CUES if cue in text)
    if operations and metrics:
        return NaturalLanguageRoute(
            route=ExecutionRoute.DETERMINISTIC,
            reason="bounded_structured_analytics",
            matched_cues=operations + metrics,
        )

    return NaturalLanguageRoute(
        route=ExecutionRoute.LOCAL,
        reason="default_local_reasoning",
    )
