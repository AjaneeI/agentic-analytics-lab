"""Aggregate repeated benchmark runs without changing benchmark behavior."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Iterable


COMPATIBILITY_FIELDS = (
    "benchmark_schema_version",
    "architecture",
    "model",
    "provider",
    "dataset",
    "questions",
)


def load_benchmark(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if "summary" not in payload:
        raise ValueError(f"{path}: missing summary section.")
    if "results" not in payload:
        raise ValueError(f"{path}: missing case results.")
    if "metadata" not in payload:
        raise ValueError(f"{path}: missing metadata section.")
    return payload


def _compatibility_signature(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload["metadata"]
    return {field: metadata.get(field) for field in COMPATIBILITY_FIELDS}


def validate_compatible_runs(payloads: list[dict[str, Any]]) -> None:
    if len(payloads) < 2:
        raise ValueError("Repeatability analysis requires at least two benchmark runs.")

    expected_signature = _compatibility_signature(payloads[0])
    expected_case_ids = [
        result.get("question_id") for result in payloads[0]["results"]
    ]

    for index, payload in enumerate(payloads[1:], start=2):
        signature = _compatibility_signature(payload)
        for field, expected in expected_signature.items():
            actual = signature[field]
            if actual != expected:
                raise ValueError(
                    f"Run {index} is incompatible: metadata field {field!r} "
                    f"is {actual!r}, expected {expected!r}."
                )

        case_ids = [result.get("question_id") for result in payload["results"]]
        if case_ids != expected_case_ids:
            raise ValueError(
                f"Run {index} is incompatible: question IDs/order differ "
                "from the first run."
            )


def _metric_values(
    payloads: Iterable[dict[str, Any]],
    key: str,
) -> list[float]:
    return [float(payload["summary"].get(key, 0) or 0) for payload in payloads]


def _sample_stdev(values: list[float]) -> float:
    return round(stdev(values), 4) if len(values) > 1 else 0.0


def _case_status(successes: int, runs: int) -> str:
    if successes == runs:
        return "stable_pass"
    if successes == 0:
        return "stable_fail"
    return "variable"


def summarize_repeatability(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    validate_compatible_runs(payloads)

    runs = len(payloads)
    questions = int(payloads[0]["summary"].get("questions", 0) or 0)
    task_success_counts = _metric_values(payloads, "task_successful")
    correct_counts = _metric_values(payloads, "correct")
    execution_counts = _metric_values(payloads, "execution_successful")
    tool_calls = _metric_values(payloads, "total_tool_calls")
    model_calls = _metric_values(payloads, "total_model_calls")
    input_tokens = _metric_values(payloads, "total_input_tokens")
    output_tokens = _metric_values(payloads, "total_output_tokens")
    latency_seconds = _metric_values(payloads, "total_latency_seconds")

    task_success_rates = [
        (count / questions) * 100 if questions else 0.0
        for count in task_success_counts
    ]

    case_ids = [
        result.get("question_id") for result in payloads[0]["results"]
    ]
    per_case = []

    for position, question_id in enumerate(case_ids):
        records = [payload["results"][position] for payload in payloads]
        task_successes = sum(record.get("task_success") is True for record in records)
        correct = sum(record.get("correct") is True for record in records)
        execution_successes = sum(
            record.get("execution_success") is True for record in records
        )
        failure_types = Counter(
            record.get("failure_type")
            for record in records
            if record.get("failure_type")
        )

        per_case.append(
            {
                "question_id": question_id,
                "category": records[0].get("category", ""),
                "task_successes": task_successes,
                "correct": correct,
                "execution_successes": execution_successes,
                "runs": runs,
                "status": _case_status(task_successes, runs),
                "failure_types": dict(sorted(failure_types.items())),
            }
        )

    return {
        "run_count": runs,
        "questions_per_run": questions,
        "compatibility": _compatibility_signature(payloads[0]),
        "run_metrics": {
            "task_successful": [int(value) for value in task_success_counts],
            "correct": [int(value) for value in correct_counts],
            "execution_successful": [int(value) for value in execution_counts],
            "total_tool_calls": [int(value) for value in tool_calls],
            "total_model_calls": [int(value) for value in model_calls],
            "total_input_tokens": [int(value) for value in input_tokens],
            "total_output_tokens": [int(value) for value in output_tokens],
            "total_latency_seconds": latency_seconds,
        },
        "aggregate": {
            "mean_task_successful": round(mean(task_success_counts), 3),
            "mean_task_success_rate_pct": round(mean(task_success_rates), 1),
            "task_success_rate_stdev_pct": _sample_stdev(task_success_rates),
            "min_task_success_rate_pct": round(min(task_success_rates), 1),
            "max_task_success_rate_pct": round(max(task_success_rates), 1),
            "mean_tool_calls": round(mean(tool_calls), 3),
            "mean_model_calls": round(mean(model_calls), 3),
            "mean_input_tokens": round(mean(input_tokens), 1),
            "mean_output_tokens": round(mean(output_tokens), 1),
            "mean_latency_seconds": round(mean(latency_seconds), 3),
            "min_latency_seconds": round(min(latency_seconds), 3),
            "max_latency_seconds": round(max(latency_seconds), 3),
        },
        "per_case": per_case,
    }


def build_markdown_summary(
    summary: dict[str, Any],
    *,
    title: str = "Single-Agent Repeatability Summary",
) -> str:
    runs = summary["run_count"]
    questions = summary["questions_per_run"]
    metrics = summary["run_metrics"]
    aggregate = summary["aggregate"]

    lines = [
        f"# {title}",
        "",
        "> Descriptive summary of repeated benchmark runs under a fixed configuration. "
        "Review the underlying JSON before publishing conclusions.",
        "",
        "## Compatibility gate",
        "",
        "| Field | Value |",
        "|---|---|",
    ]

    for field, value in summary["compatibility"].items():
        lines.append(f"| {field} | {value} |")

    lines.extend(
        [
            "",
            "## Run-level results",
            "",
            "| Run | Execution | Correct | Task success | Tool calls | Model calls | Input tokens | Output tokens | Latency (s) |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )

    for index in range(runs):
        lines.append(
            "| {run} | {execution}/{questions} | {correct}/{questions} | "
            "{task}/{questions} | {tools} | {models} | {input_tokens} | "
            "{output_tokens} | {latency:.3f} |".format(
                run=index + 1,
                execution=metrics["execution_successful"][index],
                correct=metrics["correct"][index],
                task=metrics["task_successful"][index],
                questions=questions,
                tools=metrics["total_tool_calls"][index],
                models=metrics["total_model_calls"][index],
                input_tokens=metrics["total_input_tokens"][index],
                output_tokens=metrics["total_output_tokens"][index],
                latency=metrics["total_latency_seconds"][index],
            )
        )

    lines.extend(
        [
            "",
            "## Variability snapshot",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Mean task success | {aggregate['mean_task_successful']}/{questions} ({aggregate['mean_task_success_rate_pct']}%) |",
            f"| Task-success rate stdev | {aggregate['task_success_rate_stdev_pct']} percentage points |",
            f"| Task-success range | {aggregate['min_task_success_rate_pct']}%–{aggregate['max_task_success_rate_pct']}% |",
            f"| Mean tool calls | {aggregate['mean_tool_calls']} |",
            f"| Mean model calls | {aggregate['mean_model_calls']} |",
            f"| Mean input tokens | {aggregate['mean_input_tokens']} |",
            f"| Mean output tokens | {aggregate['mean_output_tokens']} |",
            f"| Mean latency | {aggregate['mean_latency_seconds']} s |",
            f"| Latency range | {aggregate['min_latency_seconds']}–{aggregate['max_latency_seconds']} s |",
            "",
            "## Per-case recurrence",
            "",
            "| Case | Category | Task success | Correct | Execution | Classification | Failure types |",
            "|---|---|---:|---:|---:|---|---|",
        ]
    )

    for case in summary["per_case"]:
        failures = ", ".join(
            f"{name} × {count}" for name, count in case["failure_types"].items()
        ) or "none"
        lines.append(
            "| {qid} | {category} | {task}/{runs} | {correct}/{runs} | "
            "{execution}/{runs} | {status} | {failures} |".format(
                qid=case["question_id"],
                category=case["category"],
                task=case["task_successes"],
                correct=case["correct"],
                execution=case["execution_successes"],
                runs=case["runs"],
                status=case["status"],
                failures=failures,
            )
        )

    lines.extend(
        [
            "",
            "## Interpretation guardrail",
            "",
            "This summary characterizes observed repeatability only. It does not establish "
            "statistical significance, and it should not be used to compare architectures "
            "unless the benchmark configuration remains matched.",
            "",
        ]
    )

    return "\n".join(lines)


def write_markdown_summary(
    summary: dict[str, Any],
    destination: str | Path,
    *,
    title: str = "Single-Agent Repeatability Summary",
) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown_summary(summary, title=title))
    return path
