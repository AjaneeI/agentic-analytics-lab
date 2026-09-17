"""Verify frozen evaluation expectations against the deterministic seed-42 CSV."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path


DATA_PATH = Path("data/delivery_work_items.csv")
QUESTIONS_PATH = Path("evals/questions.json")


def compute_team_metrics(rows: list[dict[str, str]]) -> dict[str, dict[str, float | int]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["team"]].append(row)

    metrics: dict[str, dict[str, float | int]] = {}
    for team, team_rows in grouped.items():
        work_items = len(team_rows)
        blocked_items = sum(int(row["blocked"]) for row in team_rows)
        metrics[team] = {
            "work_items": work_items,
            "blocked_items": blocked_items,
            "blocked_pct": round(100 * blocked_items / work_items, 1),
            "avg_effort_ratio": round(
                sum(
                    float(row["actual_hours"]) / float(row["planned_hours"])
                    for row in team_rows
                )
                / work_items,
                2,
            ),
        }
    return metrics


def verify(metrics: dict[str, dict[str, float | int]], cases: list[dict]) -> list[str]:
    failures: list[str] = []
    by_id = {case["id"]: case for case in cases}

    q1 = by_id["Q1"]["expected"]
    highest_blocker = max(metrics, key=lambda team: metrics[team]["blocked_pct"])
    if highest_blocker != q1["team"] or metrics[highest_blocker]["blocked_pct"] != q1["blocked_pct"]:
        failures.append("Q1 expected answer does not match generated data.")

    q2 = by_id["Q2"]["expected"]
    highest_effort = max(metrics, key=lambda team: metrics[team]["avg_effort_ratio"])
    if highest_effort != q2["team"] or metrics[highest_effort]["avg_effort_ratio"] != q2["avg_effort_ratio"]:
        failures.append("Q2 expected answer does not match generated data.")

    q3 = by_id["Q3"]["expected"]
    most_blocked = max(metrics, key=lambda team: metrics[team]["blocked_items"])
    if (
        most_blocked != q3["team"]
        or metrics[most_blocked]["blocked_items"] != q3["blocked_items"]
        or metrics[most_blocked]["blocked_pct"] != q3["blocked_pct"]
        or (most_blocked == highest_blocker) is not q3["answer"]
    ):
        failures.append("Q3 expected answer does not match generated data.")

    q4 = by_id["Q4"]["expected"]["ranking"]
    ranking = sorted(
        ([team, values["blocked_pct"]] for team, values in metrics.items()),
        key=lambda pair: pair[1],
        reverse=True,
    )
    if ranking != q4:
        failures.append("Q4 expected ranking does not match generated data.")

    q5 = by_id["Q5"]["expected"]
    lowest_blocker = min(metrics, key=lambda team: metrics[team]["blocked_pct"])
    lowest_effort = min(metrics, key=lambda team: metrics[team]["avg_effort_ratio"])
    if not (
        lowest_blocker == lowest_effort == q5["team"]
        and metrics[q5["team"]]["blocked_pct"] == q5["blocked_pct"]
        and metrics[q5["team"]]["avg_effort_ratio"] == q5["avg_effort_ratio"]
    ):
        failures.append("Q5 expected answer does not match generated data.")

    return failures


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(
            "Missing data/delivery_work_items.csv. Run "
            "`python3 scripts/generate_delivery_data.py` first."
        )

    with DATA_PATH.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    cases = json.loads(QUESTIONS_PATH.read_text())
    metrics = compute_team_metrics(rows)
    failures = verify(metrics, cases)

    print(json.dumps(metrics, indent=2, sort_keys=True))
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(1)

    print("Ground truth verified against deterministic seed-42 data.")


if __name__ == "__main__":
    main()
