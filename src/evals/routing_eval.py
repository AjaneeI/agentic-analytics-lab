"""Evaluation utilities for deterministic router contract conformance.\n\nThe synthetic fixtures exercise routing behavior and failure metrics. They are not\na statistical generalization benchmark and remain separate from frozen Q1-Q6.\n"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.routing.control_plane import (
    ExecutionRoute,
    TaskContext,
    parse_execution_route,
    route_task,
)


@dataclass(frozen=True)
class RoutingFixture:
    fixture_id: str
    description: str
    context: TaskContext
    expected_route: ExecutionRoute


@dataclass(frozen=True)
class RoutingMismatch:
    fixture_id: str
    expected_route: ExecutionRoute
    actual_route: ExecutionRoute


@dataclass(frozen=True)
class RoutingEvaluation:
    total: int
    correct: int
    accuracy: float
    confusion_matrix: dict[str, dict[str, int]]
    false_cheap_routes: int
    unnecessary_escalations: int
    mismatches: tuple[RoutingMismatch, ...]


def load_routing_fixtures(path: str | Path) -> list[RoutingFixture]:
    raw = json.loads(Path(path).read_text())
    if not isinstance(raw, list) or not raw:
        raise ValueError("Routing fixture file must contain a non-empty JSON list.")

    fixtures: list[RoutingFixture] = []
    seen_ids: set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("Each routing fixture must be a JSON object.")

        fixture_id = _required_string(item, "id")
        if fixture_id in seen_ids:
            raise ValueError(f"Duplicate routing fixture id: {fixture_id}")
        seen_ids.add(fixture_id)

        context = TaskContext(
            task_type=_required_string(item, "task_type"),
            requires_tool=_required_bool(item, "requires_tool"),
            evidence_required=_required_bool(item, "evidence_required"),
            deterministic_handler_available=_optional_bool(
                item, "deterministic_handler_available", False
            ),
            ambiguity_detected=_optional_bool(item, "ambiguity_detected", False),
            prior_validation_failed=_optional_bool(
                item, "prior_validation_failed", False
            ),
            tool_supported=_optional_bool(item, "tool_supported", True),
            known_failure_category=_optional_string(
                item, "known_failure_category"
            ),
        )

        fixtures.append(
            RoutingFixture(
                fixture_id=fixture_id,
                description=_required_string(item, "description"),
                context=context,
                expected_route=parse_execution_route(
                    _required_string(item, "expected_route")
                ),
            )
        )

    return fixtures


def evaluate_routing(fixtures: list[RoutingFixture]) -> RoutingEvaluation:
    if not fixtures:
        raise ValueError("At least one routing fixture is required.")

    labels = [route.value for route in ExecutionRoute]
    confusion = {
        expected: {actual: 0 for actual in labels}
        for expected in labels
    }
    mismatches: list[RoutingMismatch] = []
    false_cheap = 0
    unnecessary_escalations = 0
    correct = 0

    for fixture in fixtures:
        actual = route_task(fixture.context).route
        expected = fixture.expected_route
        confusion[expected.value][actual.value] += 1

        if actual == expected:
            correct += 1
            continue

        mismatches.append(
            RoutingMismatch(
                fixture_id=fixture.fixture_id,
                expected_route=expected,
                actual_route=actual,
            )
        )

        if expected == ExecutionRoute.ESCALATE and actual != ExecutionRoute.ESCALATE:
            false_cheap += 1
        elif expected != ExecutionRoute.ESCALATE and actual == ExecutionRoute.ESCALATE:
            unnecessary_escalations += 1

    total = len(fixtures)
    return RoutingEvaluation(
        total=total,
        correct=correct,
        accuracy=correct / total,
        confusion_matrix=confusion,
        false_cheap_routes=false_cheap,
        unnecessary_escalations=unnecessary_escalations,
        mismatches=tuple(mismatches),
    )


def _required_string(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()


def _optional_string(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string when provided.")
    return value.strip() or None


def _required_bool(item: dict[str, Any], key: str) -> bool:
    if key not in item or not isinstance(item[key], bool):
        raise ValueError(f"{key} must be a boolean.")
    return item[key]


def _optional_bool(item: dict[str, Any], key: str, default: bool) -> bool:
    value = item.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean.")
    return value
