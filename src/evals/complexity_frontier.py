"""Pareto-frontier analysis for architecture quality/cost tradeoffs.

This module intentionally avoids a weighted composite score. An architecture is
Pareto-dominated only when another architecture is at least as good on every
declared metric and strictly better on at least one.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping


@dataclass(frozen=True)
class ArchitecturePoint:
    name: str
    metrics: Mapping[str, float]


def _validated_value(point: ArchitecturePoint, metric: str) -> float:
    if metric not in point.metrics:
        raise ValueError(f"{point.name!r} is missing metric {metric!r}")
    value = point.metrics[metric]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(
            f"{point.name!r} metric {metric!r} must be numeric"
        )
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(
            f"{point.name!r} metric {metric!r} must be finite"
        )
    return numeric


def dominates(
    challenger: ArchitecturePoint,
    incumbent: ArchitecturePoint,
    directions: Mapping[str, str],
) -> bool:
    """Return whether challenger Pareto-dominates incumbent."""

    if not directions:
        raise ValueError("At least one comparison metric is required.")

    at_least_as_good = True
    strictly_better = False

    for metric, direction in directions.items():
        challenger_value = _validated_value(challenger, metric)
        incumbent_value = _validated_value(incumbent, metric)

        if direction == "maximize":
            if challenger_value < incumbent_value:
                at_least_as_good = False
                break
            if challenger_value > incumbent_value:
                strictly_better = True
        elif direction == "minimize":
            if challenger_value > incumbent_value:
                at_least_as_good = False
                break
            if challenger_value < incumbent_value:
                strictly_better = True
        else:
            raise ValueError(
                f"Direction for {metric!r} must be 'maximize' or 'minimize'."
            )

    return at_least_as_good and strictly_better


def analyze_frontier(
    points: list[ArchitecturePoint],
    directions: Mapping[str, str],
) -> dict[str, Any]:
    """Return frontier membership and explicit dominance relationships."""

    if len(points) < 2:
        raise ValueError("Frontier analysis requires at least two architectures.")

    names = [point.name for point in points]
    if len(set(names)) != len(names):
        raise ValueError("Architecture names must be unique.")

    dominated_by: dict[str, list[str]] = {point.name: [] for point in points}

    for incumbent in points:
        for challenger in points:
            if challenger.name == incumbent.name:
                continue
            if dominates(challenger, incumbent, directions):
                dominated_by[incumbent.name].append(challenger.name)

    frontier = [
        point.name
        for point in points
        if not dominated_by[point.name]
    ]

    return {
        "method": "pareto_frontier",
        "directions": dict(directions),
        "frontier": frontier,
        "dominated": {
            name: dominators
            for name, dominators in dominated_by.items()
            if dominators
        },
        "points": {
            point.name: dict(point.metrics)
            for point in points
        },
        "claim_boundary": (
            "No weighted winner score is computed. Frontier membership depends "
            "only on the declared metric directions and observed benchmark "
            "measurements."
        ),
    }
