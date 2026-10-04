"""Statistical evidence helpers for matched architecture comparisons.

The benchmark is stochastic, but repeated runs of the same task are not
independent benchmark items. This module therefore summarizes repeats within
each task first, then bootstraps across matched task IDs. That avoids treating
every repeated observation as a new independent task.

The resulting interval is descriptive for the frozen benchmark task set. It is
not evidence that performance will generalize to unseen tasks.
"""

from __future__ import annotations

import math
import random
from statistics import mean
from typing import Any

from src.evals.repeatability import validate_compatible_runs


_MATCHED_METADATA_FIELDS = (
    "benchmark_schema_version",
    "model",
    "provider",
    "dataset",
    "questions",
)


def _case_ids(payload: dict[str, Any]) -> list[str]:
    return [str(item.get("question_id")) for item in payload.get("results", [])]


def _cross_architecture_compatibility(
    baseline_runs: list[dict[str, Any]],
    candidate_runs: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_metadata = baseline_runs[0]["metadata"]
    candidate_metadata = candidate_runs[0]["metadata"]

    matched: dict[str, Any] = {}
    for field in _MATCHED_METADATA_FIELDS:
        baseline_value = baseline_metadata.get(field)
        candidate_value = candidate_metadata.get(field)
        if baseline_value != candidate_value:
            raise ValueError(
                f"Architecture comparison is incompatible: metadata field "
                f"{field!r} differs ({baseline_value!r} != {candidate_value!r})."
            )
        matched[field] = baseline_value

    baseline_ids = _case_ids(baseline_runs[0])
    candidate_ids = _case_ids(candidate_runs[0])
    if baseline_ids != candidate_ids:
        raise ValueError(
            "Architecture comparison is incompatible: question IDs/order differ."
        )

    if len(baseline_runs) != len(candidate_runs):
        raise ValueError(
            "Architecture comparison requires the same number of repeated runs "
            "for baseline and candidate."
        )

    return matched


def _success_counts(
    payloads: list[dict[str, Any]],
) -> tuple[list[str], list[int]]:
    case_ids = _case_ids(payloads[0])
    counts: list[int] = []
    for position in range(len(case_ids)):
        counts.append(
            sum(
                payload["results"][position].get("task_success") is True
                for payload in payloads
            )
        )
    return case_ids, counts


def _quantile(sorted_values: list[float], probability: float) -> float:
    if not sorted_values:
        raise ValueError("Cannot compute a quantile from an empty sample.")
    if probability <= 0:
        return sorted_values[0]
    if probability >= 1:
        return sorted_values[-1]

    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def paired_task_bootstrap(
    deltas: list[float],
    *,
    samples: int = 10_000,
    seed: int = 42,
) -> dict[str, float]:
    """Bootstrap a mean delta by resampling matched task-level deltas."""

    if len(deltas) < 2:
        raise ValueError("Paired bootstrap requires at least two benchmark tasks.")
    if samples < 100:
        raise ValueError("Bootstrap requires at least 100 samples.")

    rng = random.Random(seed)
    n = len(deltas)
    estimates = [
        mean(deltas[rng.randrange(n)] for _ in range(n))
        for _ in range(samples)
    ]
    estimates.sort()

    return {
        "lower_95": _quantile(estimates, 0.025),
        "upper_95": _quantile(estimates, 0.975),
        "fraction_positive": sum(value > 0 for value in estimates) / samples,
    }


def compare_architectures(
    baseline_runs: list[dict[str, Any]],
    candidate_runs: list[dict[str, Any]],
    *,
    bootstrap_samples: int = 10_000,
    seed: int = 42,
) -> dict[str, Any]:
    """Compare matched repeated benchmark runs without pseudoreplication.

    Repeats are summarized within each task. The bootstrap then resamples task
    IDs, not individual repeated observations.
    """

    validate_compatible_runs(baseline_runs)
    validate_compatible_runs(candidate_runs)
    matched_metadata = _cross_architecture_compatibility(
        baseline_runs, candidate_runs
    )

    case_ids, baseline_counts = _success_counts(baseline_runs)
    _, candidate_counts = _success_counts(candidate_runs)
    runs = len(baseline_runs)

    baseline_rates = [count / runs for count in baseline_counts]
    candidate_rates = [count / runs for count in candidate_counts]
    deltas = [
        candidate - baseline
        for baseline, candidate in zip(baseline_rates, candidate_rates)
    ]

    bootstrap = paired_task_bootstrap(
        deltas, samples=bootstrap_samples, seed=seed
    )

    per_case = []
    for case_id, baseline_count, candidate_count, delta in zip(
        case_ids, baseline_counts, candidate_counts, deltas
    ):
        per_case.append(
            {
                "question_id": case_id,
                "runs": runs,
                "baseline_successes": baseline_count,
                "candidate_successes": candidate_count,
                "baseline_success_rate_pct": round(
                    (baseline_count / runs) * 100, 1
                ),
                "candidate_success_rate_pct": round(
                    (candidate_count / runs) * 100, 1
                ),
                "delta_percentage_points": round(delta * 100, 1),
                "baseline_variable": 0 < baseline_count < runs,
                "candidate_variable": 0 < candidate_count < runs,
            }
        )

    return {
        "method": "paired_task_level_bootstrap",
        "bootstrap_samples": bootstrap_samples,
        "seed": seed,
        "run_count_per_architecture": runs,
        "task_count": len(case_ids),
        "matched_metadata": matched_metadata,
        "architectures": {
            "baseline": baseline_runs[0]["metadata"].get("architecture"),
            "candidate": candidate_runs[0]["metadata"].get("architecture"),
        },
        "aggregate": {
            "baseline_mean_task_success_rate_pct": round(
                mean(baseline_rates) * 100, 1
            ),
            "candidate_mean_task_success_rate_pct": round(
                mean(candidate_rates) * 100, 1
            ),
            "mean_delta_percentage_points": round(mean(deltas) * 100, 1),
            "bootstrap_95_interval_percentage_points": [
                round(bootstrap["lower_95"] * 100, 1),
                round(bootstrap["upper_95"] * 100, 1),
            ],
            "bootstrap_fraction_positive": round(
                bootstrap["fraction_positive"], 4
            ),
            "candidate_better_tasks": sum(delta > 0 for delta in deltas),
            "tied_tasks": sum(delta == 0 for delta in deltas),
            "candidate_worse_tasks": sum(delta < 0 for delta in deltas),
        },
        "per_case": per_case,
        "claim_boundary": (
            "This is a descriptive paired bootstrap over the frozen benchmark "
            "task set. It preserves repeated-run dependence by summarizing "
            "within task before resampling tasks. It does not establish "
            "generalization to unseen tasks."
        ),
    }
