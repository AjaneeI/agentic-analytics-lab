"""Evaluation harness for free-text route inference.

This remains separate from the frozen Q1-Q6 benchmark. It measures only whether
a classifier maps a request to the expected execution route.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from src.routing.control_plane import ExecutionRoute, parse_execution_route


@dataclass(frozen=True)
class NaturalLanguageRoutingFixture:
    fixture_id: str
    prompt: str
    expected_route: ExecutionRoute
    rationale: str


@dataclass(frozen=True)
class NaturalLanguageRoutingMismatch:
    fixture_id: str
    prompt: str
    expected_route: ExecutionRoute
    actual_route: ExecutionRoute


@dataclass(frozen=True)
class NaturalLanguageRoutingEvaluation:
    total: int
    correct: int
    accuracy: float
    confusion_matrix: dict[str, dict[str, int]]
    false_cheap_routes: int
    unnecessary_escalations: int
    mismatches: tuple[NaturalLanguageRoutingMismatch, ...]


Classifier = Callable[[str], Any]


def load_natural_language_fixtures(
    path: str | Path,
) -> list[NaturalLanguageRoutingFixture]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list) or not raw:
        raise ValueError("Natural-language fixture file must contain a non-empty list.")

    fixtures: list[NaturalLanguageRoutingFixture] = []
    seen_ids: set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each natural-language routing fixture must be an object.")

        fixture_id = _required_string(item, "id")
        if fixture_id in seen_ids:
            raise ValueError(f"Duplicate natural-language fixture id: {fixture_id}")
        seen_ids.add(fixture_id)

        fixtures.append(
            NaturalLanguageRoutingFixture(
                fixture_id=fixture_id,
                prompt=_required_string(item, "prompt"),
                expected_route=parse_execution_route(
                    _required_string(item, "expected_route")
                ),
                rationale=_required_string(item, "rationale"),
            )
        )

    return fixtures


def evaluate_natural_language_routing(
    fixtures: list[NaturalLanguageRoutingFixture],
    classifier: Classifier,
) -> NaturalLanguageRoutingEvaluation:
    if not fixtures:
        raise ValueError("At least one natural-language fixture is required.")

    labels = [route.value for route in ExecutionRoute]
    confusion = {
        expected: {actual: 0 for actual in labels}
        for expected in labels
    }
    mismatches: list[NaturalLanguageRoutingMismatch] = []
    correct = 0
    false_cheap = 0
    unnecessary_escalations = 0

    for fixture in fixtures:
        raw = classifier(fixture.prompt)
        actual = _route_from_classifier_result(raw)
        expected = fixture.expected_route
        confusion[expected.value][actual.value] += 1

        if actual == expected:
            correct += 1
            continue

        mismatches.append(
            NaturalLanguageRoutingMismatch(
                fixture_id=fixture.fixture_id,
                prompt=fixture.prompt,
                expected_route=expected,
                actual_route=actual,
            )
        )

        if expected == ExecutionRoute.ESCALATE and actual != ExecutionRoute.ESCALATE:
            false_cheap += 1
        elif expected != ExecutionRoute.ESCALATE and actual == ExecutionRoute.ESCALATE:
            unnecessary_escalations += 1

    total = len(fixtures)
    return NaturalLanguageRoutingEvaluation(
        total=total,
        correct=correct,
        accuracy=correct / total,
        confusion_matrix=confusion,
        false_cheap_routes=false_cheap,
        unnecessary_escalations=unnecessary_escalations,
        mismatches=tuple(mismatches),
    )


def _route_from_classifier_result(value: Any) -> ExecutionRoute:
    route = getattr(value, "route", value)
    if isinstance(route, ExecutionRoute):
        return route
    if isinstance(route, str):
        return parse_execution_route(route)
    raise TypeError("Classifier must return an ExecutionRoute, route string, or object with .route.")


def _required_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()
