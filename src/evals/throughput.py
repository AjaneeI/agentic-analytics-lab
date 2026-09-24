"""Bounded concurrency evaluation for validated agent throughput.

This module is separate from the official three-run evidentiary benchmark. It
measures systems behavior while preserving the existing deterministic scorer for
every completed request.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import statistics
import time
from typing import Any, Callable, Iterable, Sequence

from src.evals.runner import EvalRecord, run_case


AgentFactory = Callable[[], Any]
LevelRunner = Callable[[AgentFactory, list[dict[str, Any]], int], dict[str, Any]]


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]

    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _per_minute(count: int, wall_clock_seconds: float) -> float:
    if wall_clock_seconds <= 0:
        return 0.0
    return round((count / wall_clock_seconds) * 60.0, 6)


def _run_one(
    agent_factory: AgentFactory,
    case: dict[str, Any],
    submitted_at: float,
) -> dict[str, Any]:
    worker_started = time.perf_counter()
    queue_wait = worker_started - submitted_at
    agent = agent_factory()
    record = run_case(agent, case)

    return {
        "question_id": case["id"],
        "queue_wait_seconds": round(queue_wait, 6),
        "record": record,
    }


def run_load_level(
    agent_factory: AgentFactory,
    cases: list[dict[str, Any]],
    concurrency: int,
) -> dict[str, Any]:
    """Run one bounded-concurrency level with isolated agent instances."""

    if concurrency < 1:
        raise ValueError("concurrency must be at least 1.")
    if not cases:
        raise ValueError("At least one load-test case is required.")

    suite_started = time.perf_counter()
    measurements: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for case in cases:
            submitted_at = time.perf_counter()
            futures.append(
                executor.submit(_run_one, agent_factory, case, submitted_at)
            )

        for future in as_completed(futures):
            measurements.append(future.result())

    wall_clock_seconds = round(time.perf_counter() - suite_started, 6)
    order = {case["id"]: index for index, case in enumerate(cases)}
    measurements.sort(key=lambda item: order.get(item["question_id"], len(order)))

    records: list[EvalRecord] = [item["record"] for item in measurements]
    service_latencies = [record.latency_seconds for record in records]
    queue_waits = [item["queue_wait_seconds"] for item in measurements]
    task_successful = sum(record.task_success for record in records)
    execution_errors = sum(not record.execution_success for record in records)

    return {
        "concurrency": concurrency,
        "summary": {
            "requests": len(records),
            "task_successful": task_successful,
            "execution_errors": execution_errors,
            "task_success_rate": round(task_successful / len(records), 6),
            "wall_clock_seconds": wall_clock_seconds,
            "requests_per_minute": _per_minute(len(records), wall_clock_seconds),
            "validated_tasks_per_minute": _per_minute(
                task_successful, wall_clock_seconds
            ),
            "median_service_latency_seconds": round(
                statistics.median(service_latencies), 6
            ),
            "p95_service_latency_seconds": round(
                _percentile(service_latencies, 0.95), 6
            ),
            "median_queue_wait_seconds": round(statistics.median(queue_waits), 6),
            "p95_queue_wait_seconds": round(_percentile(queue_waits, 0.95), 6),
            "total_tool_calls": sum(record.tool_call_count for record in records),
            "total_model_calls": sum(record.model_call_count for record in records),
            "total_input_tokens": sum(record.input_tokens or 0 for record in records),
            "total_output_tokens": sum(
                record.output_tokens or 0 for record in records
            ),
        },
        "results": [
            {
                "question_id": item["question_id"],
                "queue_wait_seconds": item["queue_wait_seconds"],
                "record": asdict(item["record"]),
            }
            for item in measurements
        ],
    }


def _degradation_reasons(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> list[str]:
    previous_summary = previous["summary"]
    current_summary = current["summary"]
    reasons: list[str] = []

    if (
        current_summary["validated_tasks_per_minute"]
        <= previous_summary["validated_tasks_per_minute"]
    ):
        reasons.append("validated_goodput_did_not_improve")

    if (
        current_summary["task_success_rate"]
        < previous_summary["task_success_rate"]
    ):
        reasons.append("task_success_rate_dropped")

    if (
        current_summary["execution_errors"]
        > previous_summary["execution_errors"]
    ):
        reasons.append("execution_errors_increased")

    return reasons


def summarize_throughput_sweep(
    level_results: Sequence[dict[str, Any]],
    *,
    saturation_reasons: Sequence[str] = (),
) -> dict[str, Any]:
    if not level_results:
        raise ValueError("At least one throughput level result is required.")

    best = max(
        level_results,
        key=lambda item: (
            item["summary"]["validated_tasks_per_minute"],
            -item["concurrency"],
        ),
    )

    return {
        "levels_completed": [item["concurrency"] for item in level_results],
        "best_observed_concurrency": best["concurrency"],
        "best_validated_tasks_per_minute": best["summary"][
            "validated_tasks_per_minute"
        ],
        "saturation_concurrency": (
            level_results[-1]["concurrency"] if saturation_reasons else None
        ),
        "saturation_reasons": list(saturation_reasons),
    }


def run_throughput_sweep(
    *,
    agent_factory: AgentFactory,
    cases: list[dict[str, Any]],
    concurrency_levels: Iterable[int] = (1, 2, 4, 6),
    level_runner: LevelRunner = run_load_level,
) -> dict[str, Any]:
    """Run increasing concurrency until validated goodput or quality degrades."""

    requested = list(concurrency_levels)
    if not requested:
        raise ValueError("At least one concurrency level is required.")
    if any(level < 1 for level in requested):
        raise ValueError("Concurrency levels must all be at least 1.")
    if requested != sorted(set(requested)):
        raise ValueError("Concurrency levels must be unique and increasing.")

    levels: list[dict[str, Any]] = []
    saturation_reasons: list[str] = []

    for concurrency in requested:
        current = level_runner(agent_factory, cases, concurrency)
        levels.append(current)

        if len(levels) > 1:
            saturation_reasons = _degradation_reasons(levels[-2], levels[-1])
            if saturation_reasons:
                break

    return {
        "requested_concurrency_levels": requested,
        "sweep_summary": summarize_throughput_sweep(
            levels,
            saturation_reasons=saturation_reasons,
        ),
        "levels": levels,
    }
