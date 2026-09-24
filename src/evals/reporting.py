"""Render deterministic, reviewable benchmark summaries from evaluation JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_benchmark(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if "summary" not in payload:
        raise ValueError("Benchmark payload is missing a summary section.")
    if "results" not in payload:
        raise ValueError("Benchmark payload is missing case results.")
    return payload


def _rate(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100, 1)


def _status(value: Any) -> str:
    if value is True:
        return "PASS"
    if value is False:
        return "FAIL"
    return "N/A"


def _optional_number(value: Any, *, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.3f}{suffix}"


def build_markdown_report(
    payload: dict[str, Any],
    *,
    title: str = "Single-Agent Benchmark Report",
) -> str:
    summary = payload["summary"]
    results = payload["results"]
    metadata = payload.get("metadata", {})

    questions = int(summary.get("questions", len(results)))
    execution_successful = int(summary.get("execution_successful", 0))
    task_successful = int(summary.get("task_successful", 0))
    correct = int(summary.get("correct", 0))
    failed = int(summary.get("failed", max(questions - task_successful, 0)))

    lines = [
        f"# {title}",
        "",
        "> Generated from benchmark JSON. Review the underlying run before publishing this report as a current benchmark.",
        "",
        "## Outcome snapshot",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Questions | {questions} |",
        f"| Execution success | {execution_successful}/{questions} ({_rate(execution_successful, questions)}%) |",
        f"| Task success | {task_successful}/{questions} ({_rate(task_successful, questions)}%) |",
        f"| Correct answers | {correct}/{questions} ({_rate(correct, questions)}%) |",
        f"| Failed cases | {failed} |",
        f"| Tool calls | {int(summary.get('total_tool_calls', 0))} |",
        f"| Model calls | {int(summary.get('total_model_calls', 0))} |",
        f"| Input tokens | {int(summary.get('total_input_tokens', 0)):,} |",
        f"| Output tokens | {int(summary.get('total_output_tokens', 0)):,} |",
        f"| Total latency | {float(summary.get('total_latency_seconds', 0.0)):.3f} s |",
        f"| Latency per successful task | {_optional_number(summary.get('latency_seconds_per_task_success'), suffix=' s')} |",
        f"| Model calls per successful task | {_optional_number(summary.get('model_calls_per_task_success'))} |",
        f"| Tool calls per successful task | {_optional_number(summary.get('tool_calls_per_task_success'))} |",
        f"| Tokens per successful task | {_optional_number(summary.get('tokens_per_task_success'))} |",
        "",
    ]

    if metadata:
        lines.extend(
            [
                "## Run metadata",
                "",
                "| Field | Value |",
                "|---|---|",
            ]
        )
        for key in (
            "benchmark_schema_version",
            "architecture",
            "model",
            "provider",
            "dataset",
            "run_at_utc",
            "api_cost_usd",
            "local_compute_cost_usd",
        ):
            if key in metadata:
                value = metadata[key]
                rendered = "not estimated" if value is None else str(value)
                lines.append(f"| {key} | {rendered} |")
        lines.append("")

    lines.extend(
        [
            "## Case results",
            "",
            "| Case | Category | Execution | Correct | Task success | Tool calls | Model calls | Latency (s) |",
            "|---|---|---|---|---|---:|---:|---:|",
        ]
    )

    for result in results:
        lines.append(
            "| {qid} | {category} | {execution} | {correct} | {task} | {tools} | {models} | {latency:.3f} |".format(
                qid=result.get("question_id", ""),
                category=result.get("category", ""),
                execution=_status(result.get("execution_success")),
                correct=_status(result.get("correct")),
                task=_status(result.get("task_success")),
                tools=int(result.get("tool_call_count", 0) or 0),
                models=int(result.get("model_call_count", 0) or 0),
                latency=float(result.get("latency_seconds", 0.0) or 0.0),
            )
        )

    failures = [
        result
        for result in results
        if result.get("task_success") is False
        or result.get("failure_type")
        or result.get("error")
    ]
    if failures:
        lines.extend(["", "## Failure review", ""])
        for result in failures:
            qid = result.get("question_id", "unknown")
            failure_type = result.get("failure_type") or "task_failure"
            error = result.get("error")
            note = f"- **{qid}:** {failure_type}"
            if error:
                note += f" — {error}"
            lines.append(note)

    lines.extend(
        [
            "",
            "## Interpretation guardrail",
            "",
            "This report is descriptive. A routed or specialist-agent architecture should only be compared against this run when the dataset, frozen question set, evaluator, tool layer, metric definitions, and benchmark version are held constant.",
            "",
        ]
    )

    return "\n".join(lines)


def write_markdown_report(
    payload: dict[str, Any],
    destination: str | Path,
    *,
    title: str = "Single-Agent Benchmark Report",
) -> Path:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_markdown_report(payload, title=title))
    return path
