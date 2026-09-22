"""Deterministic analytics handlers for the control-plane execution tier."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from src.tools.clickhouse_readonly import query_clickhouse


class HandlerKey(str, Enum):
    BLOCKER_RATE_LEADER = "blocker_rate_leader"
    EFFORT_RATIO_LEADER = "effort_ratio_leader"
    BLOCKER_COUNT_RATE_CONSISTENCY = "blocker_count_rate_consistency"
    BLOCKER_RATE_RANKING = "blocker_rate_ranking"
    DUAL_METRIC_LEADER = "dual_metric_leader"


class DeterministicHandlerDeclined(RuntimeError):
    """Raised when deterministic evidence cannot support a unique answer."""


@dataclass(frozen=True)
class HandlerResult:
    handler: HandlerKey
    answer: str
    evidence_rows: tuple[dict[str, Any], ...]
    query_count: int = 1


QueryFn = Callable[[str], list[dict[str, Any]]]


GROUPED_TEAM_METRICS_SQL = """
SELECT
    team,
    count() AS total_items,
    sum(blocked) AS blocked_items,
    round(100.0 * sum(blocked) / count(), 1) AS blocker_rate,
    round(avg(actual_hours / planned_hours), 2) AS avg_effort_ratio
FROM agentic_analytics.delivery_work_items
GROUP BY team
ORDER BY team
""".strip()


def execute_deterministic_handler(
    handler: HandlerKey | str,
    *,
    query_fn: QueryFn = query_clickhouse,
) -> HandlerResult:
    """Execute one approved deterministic analytics operation.

    The handler never receives arbitrary SQL. Every operation uses the same fixed
    grouped-metrics query through the existing read-only ClickHouse boundary.
    """

    try:
        key = handler if isinstance(handler, HandlerKey) else HandlerKey(handler)
    except ValueError as exc:
        raise ValueError(f"Unsupported deterministic handler: {handler!r}") from exc

    rows = _normalized_metric_rows(query_fn(GROUPED_TEAM_METRICS_SQL))

    if key == HandlerKey.BLOCKER_RATE_LEADER:
        answer = _blocker_rate_leader(rows)
    elif key == HandlerKey.EFFORT_RATIO_LEADER:
        answer = _effort_ratio_leader(rows)
    elif key == HandlerKey.BLOCKER_COUNT_RATE_CONSISTENCY:
        answer = _blocker_count_rate_consistency(rows)
    elif key == HandlerKey.BLOCKER_RATE_RANKING:
        answer = _blocker_rate_ranking(rows)
    elif key == HandlerKey.DUAL_METRIC_LEADER:
        answer = _dual_metric_leader(rows)
    else:  # pragma: no cover - enum exhaustiveness guard
        raise ValueError(f"Unsupported deterministic handler: {key!r}")

    return HandlerResult(
        handler=key,
        answer=answer,
        evidence_rows=tuple(rows),
    )


def _normalized_metric_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise DeterministicHandlerDeclined("Grouped metric query returned no rows.")

    normalized: list[dict[str, Any]] = []
    seen_teams: set[str] = set()
    required = {
        "team",
        "total_items",
        "blocked_items",
        "blocker_rate",
        "avg_effort_ratio",
    }

    for row in rows:
        if not required.issubset(row):
            missing = sorted(required - set(row))
            raise DeterministicHandlerDeclined(
                f"Grouped metric row is missing required fields: {missing}"
            )

        team = str(row["team"]).strip()
        if not team or team in seen_teams:
            raise DeterministicHandlerDeclined(
                "Grouped metric rows must contain unique non-empty teams."
            )
        seen_teams.add(team)

        try:
            normalized.append(
                {
                    "team": team,
                    "total_items": int(row["total_items"]),
                    "blocked_items": int(row["blocked_items"]),
                    "blocker_rate": float(row["blocker_rate"]),
                    "avg_effort_ratio": float(row["avg_effort_ratio"]),
                }
            )
        except (TypeError, ValueError) as exc:
            raise DeterministicHandlerDeclined(
                f"Grouped metric row for {team!r} contains invalid numeric values."
            ) from exc

    return normalized


def _unique_extreme(
    rows: list[dict[str, Any]],
    field: str,
    *,
    highest: bool,
) -> dict[str, Any]:
    extreme = (max if highest else min)(row[field] for row in rows)
    candidates = [row for row in rows if row[field] == extreme]
    if len(candidates) != 1:
        direction = "highest" if highest else "lowest"
        raise DeterministicHandlerDeclined(
            f"No unique {direction} value for {field}."
        )
    return candidates[0]


def _blocker_rate_leader(rows: list[dict[str, Any]]) -> str:
    leader = _unique_extreme(rows, "blocker_rate", highest=True)
    return (
        f"{leader['team']} has the highest blocker rate at "
        f"{leader['blocker_rate']:.1f}%."
    )


def _effort_ratio_leader(rows: list[dict[str, Any]]) -> str:
    leader = _unique_extreme(rows, "avg_effort_ratio", highest=True)
    return (
        f"{leader['team']} has the highest average actual-to-planned effort "
        f"ratio at {leader['avg_effort_ratio']:.2f}."
    )


def _blocker_count_rate_consistency(rows: list[dict[str, Any]]) -> str:
    count_leader = _unique_extreme(rows, "blocked_items", highest=True)
    rate_leader = _unique_extreme(rows, "blocker_rate", highest=True)

    if count_leader["team"] == rate_leader["team"]:
        return (
            f"Yes. {count_leader['team']} has both the most blocked items "
            f"({count_leader['blocked_items']}) and the highest blocker rate "
            f"({rate_leader['blocker_rate']:.1f}%)."
        )

    return (
        f"No. {count_leader['team']} has the most blocked items "
        f"({count_leader['blocked_items']}), while {rate_leader['team']} has "
        f"the highest blocker rate ({rate_leader['blocker_rate']:.1f}%)."
    )


def _blocker_rate_ranking(rows: list[dict[str, Any]]) -> str:
    ranked = sorted(rows, key=lambda row: (-row["blocker_rate"], row["team"]))
    return " ".join(
        f"{index}. {row['team']} — {row['blocker_rate']:.1f}%"
        for index, row in enumerate(ranked, start=1)
    )


def _dual_metric_leader(rows: list[dict[str, Any]]) -> str:
    blocker_leader = _unique_extreme(rows, "blocker_rate", highest=False)
    effort_leader = _unique_extreme(rows, "avg_effort_ratio", highest=False)

    if blocker_leader["team"] != effort_leader["team"]:
        raise DeterministicHandlerDeclined(
            "No single team is uniquely best on both blocker rate and effort ratio."
        )

    return (
        f"{blocker_leader['team']} appears strongest on both metrics, with a "
        f"{blocker_leader['blocker_rate']:.1f}% blocker rate and an average "
        f"actual-to-planned effort ratio of "
        f"{blocker_leader['avg_effort_ratio']:.2f}."
    )
