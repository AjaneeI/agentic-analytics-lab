"""Model-free execution and artifact contracts for System Benchmark v1."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Any, Callable, Iterable

from src.evals.system_benchmark.contracts import SystemBenchmarkResponse, SystemBenchmarkTask
from src.evals.system_benchmark.references import ReferenceExpectation
from src.evals.system_benchmark.routing import RoutingDecision
from src.evals.system_benchmark.scoring import ScoringObservation, score_response


@dataclass(frozen=True)
class TrialExecution:
    response: SystemBenchmarkResponse
    observation: ScoringObservation
    route_decision: RoutingDecision
    latency_seconds: float
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    model_duration_seconds: float | None = None
    error: str | None = None


Executor = Callable[[SystemBenchmarkTask, int, Path], TrialExecution]


def run_trial(
    task: SystemBenchmarkTask,
    reference: ReferenceExpectation,
    *,
    trial_number: int,
    executor: Executor,
) -> dict[str, Any]:
    """Run one isolated trial and deterministically score its observable result."""

    if trial_number < 1:
        raise ValueError("trial_number must be >= 1")

    with tempfile.TemporaryDirectory(prefix=f"system-benchmark-{task.case_id}-") as tmp:
        started = time.monotonic()
        execution = executor(task, trial_number, Path(tmp))
        wall_seconds = time.monotonic() - started

    if not isinstance(execution, TrialExecution):
        raise TypeError("executor must return TrialExecution")

    score = score_response(task, reference, execution.response, execution.observation)
    return {
        "case_id": task.case_id,
        "family": task.family.value,
        "split": task.split.value,
        "benchmark_version": task.benchmark_version,
        "trial_number": trial_number,
        "route": execution.route_decision.route.value,
        "route_reason": execution.route_decision.reason_code,
        "capability_profile": execution.route_decision.capability_profile.value,
        "disposition": execution.response.disposition.value,
        "answer_text": execution.response.answer_text,
        "evidence_refs": list(execution.response.evidence_refs),
        "tool_calls": list(execution.observation.tool_calls),
        "structured_values": dict(execution.observation.structured_values),
        "score": score.to_dict(),
        "task_success": score.passed and execution.error is None,
        "latency_seconds": execution.latency_seconds,
        "runner_wall_seconds": wall_seconds,
        "model_calls": execution.model_calls,
        "tool_call_count": len(execution.observation.tool_calls),
        "input_tokens": execution.input_tokens,
        "output_tokens": execution.output_tokens,
        "model_duration_seconds": execution.model_duration_seconds,
        "error": execution.error,
    }


def summarize_results(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(results)
    if not rows:
        raise ValueError("at least one result is required")
    successes = sum(row.get("task_success") is True for row in rows)
    latencies = [float(row["latency_seconds"]) for row in rows]
    return {
        "trials": len(rows),
        "successful": successes,
        "task_success_rate": successes / len(rows),
        "total_latency_seconds": sum(latencies),
        "mean_latency_seconds": sum(latencies) / len(latencies),
        "model_calls": sum(int(row.get("model_calls", 0)) for row in rows),
        "tool_calls": sum(int(row.get("tool_call_count", 0)) for row in rows),
        "input_tokens": sum(int(row.get("input_tokens", 0)) for row in rows),
        "output_tokens": sum(int(row.get("output_tokens", 0)) for row in rows),
    }


def write_artifact_bundle(
    output_dir: str | Path,
    *,
    manifest: dict[str, Any],
    reference_validation: dict[str, Any],
    results: list[dict[str, Any]],
    routing_metrics: dict[str, Any],
    diagnostics: dict[str, Any],
) -> tuple[Path, ...]:
    """Write the fixed six-file System Benchmark artifact bundle."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    summary = summarize_results(results)
    payloads = {
        "manifest.json": manifest,
        "reference_validation.json": reference_validation,
        "routing_metrics.json": routing_metrics,
        "diagnostics.json": diagnostics,
        "summary.json": summary,
    }
    written: list[Path] = []
    for name, payload in payloads.items():
        path = root / name
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)

    results_path = root / "results.jsonl"
    results_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )
    written.append(results_path)
    return tuple(sorted(written))


def fingerprint_paths(root: str | Path, paths: Iterable[str]) -> dict[str, Any]:
    """Build a deterministic benchmark-contract fingerprint over explicit files."""

    base = Path(root)
    file_hashes: dict[str, str] = {}
    for relative in sorted(set(paths)):
        path = base / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        file_hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()

    aggregate = hashlib.sha256()
    for relative, digest in sorted(file_hashes.items()):
        aggregate.update(relative.encode())
        aggregate.update(b"\0")
        aggregate.update(digest.encode())
        aggregate.update(b"\n")
    return {
        "benchmark_contract_sha256": aggregate.hexdigest(),
        "contract_files": file_hashes,
    }
