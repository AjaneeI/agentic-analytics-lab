"""Statistical evidence helpers for matched architecture comparisons.

Architecture comparisons preserve task identity and repeated-run uncertainty.
The bootstrap resamples matched tasks and, within each selected task, resamples
observed repeated outcomes for each architecture. This avoids treating repeats
as independent benchmark items while still reflecting run-level variability.

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
    "dataset",
    "questions",
)


def _case_ids(payload: dict[str, Any]) -> list[str]:
    return [str(item.get("question_id")) for item in payload.get("results", [])]


def _benchmark_contract_sha(payload: dict[str, Any]) -> str:
    value = (
        payload.get("metadata", {})
        .get("provenance", {})
        .get("benchmark_contract_sha256")
    )
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "Architecture comparison requires metadata.provenance."
            "benchmark_contract_sha256 on every run."
        )
    return value.strip()


def _validate_provenance(payloads: list[dict[str, Any]], label: str) -> str:
    fingerprints = {_benchmark_contract_sha(payload) for payload in payloads}
    if len(fingerprints) != 1:
        raise ValueError(
            f"{label} repeated runs have mismatched benchmark contract provenance."
        )
    return next(iter(fingerprints))


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

    baseline_contract = _validate_provenance(baseline_runs, "Baseline")
    candidate_contract = _validate_provenance(candidate_runs, "Candidate")
    if baseline_contract != candidate_contract:
        raise ValueError(
            "Architecture comparison is incompatible: benchmark contract "
            "provenance differs across architectures."
        )
    matched["benchmark_contract_sha256"] = baseline_contract

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


def _success_matrix(
    payloads: list[dict[str, Any]],
) -> tuple[list[str], list[list[bool]]]:
    case_ids = _case_ids(payloads[0])
    matrix: list[list[bool]] = []
    for position, case_id in enumerate(case_ids):
        outcomes: list[bool] = []
        for run_index, payload in enumerate(payloads, start=1):
            value = payload["results"][position].get("task_success")
            if type(value) is not bool:
                raise ValueError(
                    f"Run {run_index} case {case_id}: task_success must be Boolean."
                )
            outcomes.append(value)
        matrix.append(outcomes)
    return case_ids, matrix


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


def paired_hierarchical_bootstrap(
    baseline_outcomes: list[list[bool]],
    candidate_outcomes: list[list[bool]],
    *,
    samples: int = 10_000,
    seed: int = 42,
) -> dict[str, float]:
    """Resample tasks, then observed runs within each selected task."""

    if len(baseline_outcomes) < 2:
        raise ValueError("Paired bootstrap requires at least two benchmark tasks.")
    if len(baseline_outcomes) != len(candidate_outcomes):
        raise ValueError("Baseline and candidate task matrices must align.")
    if samples < 100:
        raise ValueError("Bootstrap requires at least 100 samples.")

    rng = random.Random(seed)
    task_count = len(baseline_outcomes)
    estimates: list[float] = []

    for _ in range(samples):
        task_deltas: list[float] = []
        for _ in range(task_count):
            task_index = rng.randrange(task_count)
            baseline_task = baseline_outcomes[task_index]
            candidate_task = candidate_outcomes[task_index]
            if not baseline_task or not candidate_task:
                raise ValueError("Every benchmark task must contain repeated outcomes.")

            baseline_rate = mean(
                1.0 if baseline_task[rng.randrange(len(baseline_task))] else 0.0
                for _ in range(len(baseline_task))
            )
            candidate_rate = mean(
                1.0 if candidate_task[rng.randrange(len(candidate_task))] else 0.0
                for _ in range(len(candidate_task))
            )
            task_deltas.append(candidate_rate - baseline_rate)
        estimates.append(mean(task_deltas))

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
    """Compare matched repeated benchmark runs with hierarchical resampling."""

    validate_compatible_runs(baseline_runs)
    validate_compatible_runs(candidate_runs)
    matched_metadata = _cross_architecture_compatibility(
        baseline_runs, candidate_runs
    )

    case_ids, baseline_matrix = _success_matrix(baseline_runs)
    _, candidate_matrix = _success_matrix(candidate_runs)
    runs = len(baseline_runs)

    baseline_counts = [sum(outcomes) for outcomes in baseline_matrix]
    candidate_counts = [sum(outcomes) for outcomes in candidate_matrix]
    baseline_rates = [count / runs for count in baseline_counts]
    candidate_rates = [count / runs for count in candidate_counts]
    deltas = [
        candidate - baseline
        for baseline, candidate in zip(baseline_rates, candidate_rates)
    ]

    bootstrap = paired_hierarchical_bootstrap(
        baseline_matrix,
        candidate_matrix,
        samples=bootstrap_samples,
        seed=seed,
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
        "method": "paired_hierarchical_task_run_bootstrap",
        "bootstrap_samples": bootstrap_samples,
        "seed": seed,
        "run_count_per_architecture": runs,
        "task_count": len(case_ids),
        "matched_metadata": matched_metadata,
        "architectures": {
            "baseline": baseline_runs[0]["metadata"].get("architecture"),
            "candidate": candidate_runs[0]["metadata"].get("architecture"),
        },
        "providers": {
            "baseline": baseline_runs[0]["metadata"].get("provider"),
            "candidate": candidate_runs[0]["metadata"].get("provider"),
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
            "This is a descriptive hierarchical bootstrap over the frozen "
            "benchmark task set and observed repeated runs. It resamples tasks "
            "and observed within-task outcomes. It does not establish "
            "generalization to unseen tasks."
        ),
    }
