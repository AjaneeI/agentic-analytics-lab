#!/usr/bin/env python3
"""Run the frozen SB-D01 direct-vs-Hermes successor comparison once."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from src.agents.ollama_client import OllamaModelClient
from src.evals.system_benchmark.contracts import SystemBenchmarkTask
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.local_worker import (
    BoundedLocalExecutor,
    _SYSTEM_PROMPT,
    _extract_structured_values,
    _parse_final_response,
)
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.routing import oracle_route
from src.evals.system_benchmark.runner import run_trial
from src.evals.system_benchmark.scoring import ScoringObservation, score_response


CASE_ID = "SB-D01"
PROFILE = "localbenchmark"
EXPERIMENT = "hermes-successor-ab-v1"
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def load_case(root: Path):
    tasks = load_tasks(root / "evals/system_benchmark/development_tasks.json")
    references = load_references(
        root / "evals/system_benchmark/development_references.json"
    )
    task = next(item for item in tasks if item.case_id == CASE_ID)
    reference = next(
        item
        for item in references
        if item.reference_solution_id == task.reference_solution_id
    )
    return task, reference


def build_hermes_prompt(request: str) -> str:
    child_goal = f"{_SYSTEM_PROMPT}\n\nTask: {request}"
    return (
        "This is frozen Treatment B for SB-D01. Call delegate_task exactly once "
        "with exactly one task. Do not call query_clickhouse or retrieve_policy "
        "from the parent. Do not provide output_schema. Do not retry. Give the "
        "child the following complete goal verbatim:\n\n"
        f"{child_goal}\n\n"
        "After the child returns, emit the child's final response as one JSON "
        "object only. Do not add prose, Markdown fences, evidence references, or "
        "manual corrections."
    )


def validate_hermes_events(events: list[dict[str, Any]]) -> None:
    delegate_pre = [
        event
        for event in events
        if event.get("event") == "delegate_pre"
        and event.get("tool") == "delegate_task"
        and event.get("ok") is True
    ]
    if len(delegate_pre) != 1:
        raise ValueError("Treatment B requires exactly one successful delegate")

    delegate_post = [
        event
        for event in events
        if event.get("event") == "delegate_post"
        and event.get("tool") == "delegate_task"
        and event.get("ok") is True
    ]
    if len(delegate_post) != 1:
        raise ValueError("Treatment B requires one successful delegate completion")

    evidence = [
        event
        for event in events
        if event.get("tool") in {"query_clickhouse", "retrieve_policy"}
    ]
    if len(evidence) != 2:
        raise ValueError("Treatment B requires exactly two evidence-tool calls")
    if any(event.get("delegated_child") is not True for event in evidence):
        raise ValueError("Every evidence call must execute in the delegated child")
    if any(event.get("ok") is not True for event in evidence):
        raise ValueError("Every evidence call must succeed on its first attempt")
    if {event.get("tool") for event in evidence} != {
        "query_clickhouse",
        "retrieve_policy",
    }:
        raise ValueError("Treatment B must call each allowed evidence tool once")

    failed_events = [event for event in events if event.get("ok") is False]
    if failed_events:
        raise ValueError("Treatment B contains a blocked or failed tool event")


def score_hermes_execution(
    root: Path,
    raw_final: str,
    events: list[dict[str, Any]],
    *,
    latency_seconds: float,
    usage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_hermes_events(events)
    task, reference = load_case(root)

    evidence_events = [
        event
        for event in events
        if event.get("tool") in {"query_clickhouse", "retrieve_policy"}
    ]
    evidence_refs: list[str] = []
    structured_values: dict[str, Any] = {}
    tool_calls: list[str] = []
    tool_records: list[dict[str, Any]] = []
    for event in evidence_events:
        name = str(event["tool"])
        tool_calls.append(name)
        tool_records.append(
            {"name": name, "arguments": dict(event.get("arguments") or {})}
        )
        for ref in event.get("evidence_refs") or []:
            if ref not in evidence_refs:
                evidence_refs.append(ref)
        if name == "query_clickhouse":
            rows = event.get("rows") or []
            if isinstance(rows, list) and all(isinstance(row, dict) for row in rows):
                _extract_structured_values(task, rows, structured_values)

    try:
        response = _parse_final_response(
            raw_final,
            evidence_refs=tuple(evidence_refs),
        )
    except Exception as exc:
        raise ValueError(str(exc)) from exc

    observation = ScoringObservation(
        tool_calls=tuple(tool_calls),
        tool_call_records=tuple(tool_records),
        structured_values=structured_values,
    )
    score = score_response(task, reference, response, observation)
    usage = usage or {}
    route = oracle_route(task)
    return {
        "case_id": task.case_id,
        "family": task.family.value,
        "split": task.split.value,
        "benchmark_version": task.benchmark_version,
        "trial_number": 1,
        "treatment": "hermes_one_worker",
        "route": route.route.value,
        "route_reason": route.reason_code,
        "capability_profile": route.capability_profile.value,
        "disposition": response.disposition.value,
        "answer_text": response.answer_text,
        "evidence_refs": evidence_refs,
        "tool_calls": tool_calls,
        "structured_values": structured_values,
        "score": score.to_dict(),
        "task_success": score.passed,
        "latency_seconds": latency_seconds,
        "model_calls": int(usage.get("api_calls") or 0),
        "tool_call_count": len(tool_calls),
        "input_tokens": int(usage.get("input_tokens") or 0),
        "output_tokens": int(usage.get("output_tokens") or 0),
        "worker_count": 1,
        "human_interventions": 0,
        "retries": 0,
        "incremental_paid_spend_usd": 0,
    }


class RecordingModel:
    def __init__(self, delegate: OllamaModelClient, path: Path):
        self.delegate = delegate
        self.path = path
        self.call_number = 0

    def respond(self, messages, tools):
        self.call_number += 1
        request = {
            "call_number": self.call_number,
            "messages": messages,
            "tools": tools,
        }
        response = self.delegate.respond(messages, tools)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {"request": request, "response": response},
                    sort_keys=True,
                )
                + "\n"
            )
            handle.flush()
            os.fsync(handle.fileno())
        return response


def verify_frozen_state(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    expected_ref = manifest["repository"]["freeze_ref"]
    head = _run_git(root, "rev-parse", "HEAD")
    frozen = _run_git(root, "rev-parse", expected_ref)
    if head != frozen:
        raise RuntimeError(f"HEAD {head} does not match {expected_ref} ({frozen})")
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "diff", "--cached", "--quiet", "HEAD", "--"],
        cwd=root,
        check=True,
    )

    for relative, expected in manifest["contract_sha256"].items():
        observed = _sha256(root / relative)
        if observed != expected:
            raise RuntimeError(f"contract hash mismatch: {relative}")

    installed = manifest["installed_state"]
    installed_files = [
        *installed["files"],
        *manifest["one_worker_enforcement"]["assets"],
    ]
    for row in installed_files:
        observed = _sha256(Path(row["path"]))
        if observed != row["sha256"]:
            raise RuntimeError(f"installed file hash mismatch: {row['path']}")
    model_manifest = Path(manifest["runtime"]["model"]["manifest_path"])
    if _sha256(model_manifest) != manifest["runtime"]["model"]["manifest_sha256"]:
        raise RuntimeError("Ollama model manifest hash mismatch")

    fallback = subprocess.run(
        ["hermes", "-p", PROFILE, "fallback", "list"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    if "No fallback providers configured" not in fallback.stdout:
        raise RuntimeError("isolated profile has a configured fallback provider")

    tool_audit = subprocess.run(
        ["hermes", "-p", PROFILE, "prompt-size", "--json"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    prompt_size = json.loads(tool_audit.stdout)
    if prompt_size["tools"]["count"] != 3:
        raise RuntimeError("isolated profile must expose exactly three tools")

    return {
        "passed": True,
        "head": head,
        "freeze_ref": expected_ref,
        "profile": PROFILE,
        "tool_count": 3,
        "contract_sha256": manifest["contract_sha256"],
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _dimension_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {"passed": 0, "total": 0, "reason_codes": ["unscored"]}
    dimensions = result["score"]["dimensions"]
    return {
        "passed": sum(item["passed"] is True for item in dimensions),
        "total": len(dimensions),
        "reason_codes": result["score"]["reason_codes"],
    }


def _comparison(
    direct: dict[str, Any] | None,
    hermes: dict[str, Any] | None,
    errors: dict[str, str],
) -> dict[str, Any]:
    return {
        "task_id": CASE_ID,
        "direct": {
            "deterministic_acceptance": bool(direct and direct["task_success"]),
            "answer_quality": _dimension_summary(direct),
            "human_interventions": 0,
            "retries": 0,
            "recovery_actions": 0,
            "latency_seconds": direct.get("latency_seconds") if direct else None,
            "model_calls": direct.get("model_calls") if direct else None,
            "tool_calls": direct.get("tool_call_count") if direct else None,
            "error": errors.get("direct"),
        },
        "hermes": {
            "deterministic_acceptance": bool(hermes and hermes["task_success"]),
            "answer_quality": _dimension_summary(hermes),
            "human_interventions": 0,
            "retries": 0,
            "recovery_actions": 0,
            "latency_seconds": hermes.get("latency_seconds") if hermes else None,
            "model_calls": hermes.get("model_calls") if hermes else None,
            "tool_calls": hermes.get("tool_call_count") if hermes else None,
            "worker_count": 1,
            "error": errors.get("hermes"),
        },
        "incremental_paid_spend_usd": 0,
        "scope_note": (
            "One SB-D01 comparison does not establish general superiority of "
            "either architecture."
        ),
    }


def run_once(root: Path, output_dir: Path, manifest_path: Path) -> int:
    if output_dir.exists():
        raise FileExistsError(
            f"refusing to reuse {output_dir}; retrying a failed treatment is forbidden"
        )
    output_dir.mkdir(parents=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _json_write(output_dir / "frozen-state.json", manifest)

    first_check = verify_frozen_state(root, manifest)
    _json_write(output_dir / "preflight-a.json", first_check)

    task, reference = load_case(root)
    direct_result = None
    hermes_result = None
    errors: dict[str, str] = {}

    direct_model = RecordingModel(
        OllamaModelClient(model=manifest["runtime"]["model"]["name"]),
        output_dir / "treatment-a-model.jsonl",
    )
    try:
        direct_result = run_trial(
            task,
            reference,
            trial_number=1,
            executor=BoundedLocalExecutor(model=direct_model),
        )
        direct_result.update(
            treatment="direct_bounded_local",
            human_interventions=0,
            retries=0,
            incremental_paid_spend_usd=0,
        )
        _json_write(output_dir / "treatment-a-score.json", direct_result)
    except Exception as exc:
        errors["direct"] = f"{type(exc).__name__}: {exc}"
        _json_write(
            output_dir / "treatment-a-error.json",
            {"error": errors["direct"], "scored": False},
        )

    second_check = verify_frozen_state(root, manifest)
    _json_write(output_dir / "preflight-b.json", second_check)

    evidence_log = output_dir / "treatment-b-events.jsonl"
    usage_path = output_dir / "treatment-b-usage.json"
    prompt = build_hermes_prompt(task.request)
    (output_dir / "treatment-b-prompt.txt").write_text(
        prompt + "\n", encoding="utf-8"
    )
    command = [
        "hermes",
        "-p",
        PROFILE,
        "--ignore-rules",
        "--usage-file",
        str(usage_path),
        "--in",
        str(root),
        "-z",
        prompt,
    ]
    _json_write(output_dir / "treatment-b-command.json", {"argv": command})
    env = {
        **os.environ,
        "AAL_REPO_ROOT": str(root),
        "AAL_EVIDENCE_LOG": str(evidence_log),
    }
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    hermes_latency = time.monotonic() - started
    (output_dir / "treatment-b-stdout.txt").write_text(
        completed.stdout, encoding="utf-8"
    )
    (output_dir / "treatment-b-stderr.txt").write_text(
        completed.stderr, encoding="utf-8"
    )
    _json_write(
        output_dir / "treatment-b-process.json",
        {"returncode": completed.returncode, "latency_seconds": hermes_latency},
    )

    try:
        if completed.returncode != 0:
            raise RuntimeError(f"Hermes exited {completed.returncode}")
        events = _read_jsonl(evidence_log)
        usage = (
            json.loads(usage_path.read_text(encoding="utf-8"))
            if usage_path.is_file()
            else {}
        )
        hermes_result = score_hermes_execution(
            root,
            completed.stdout.strip(),
            events,
            latency_seconds=hermes_latency,
            usage=usage,
        )
        _json_write(output_dir / "treatment-b-score.json", hermes_result)
    except Exception as exc:
        errors["hermes"] = f"{type(exc).__name__}: {exc}"
        _json_write(
            output_dir / "treatment-b-error.json",
            {"error": errors["hermes"], "scored": False},
        )

    comparison = _comparison(direct_result, hermes_result, errors)
    _json_write(output_dir / "comparison.json", comparison)
    _json_write(
        output_dir / "evidence-index.json",
        {
            "files": {
                path.name: _sha256(path)
                for path in sorted(output_dir.iterdir())
                if path.is_file()
            }
        },
    )
    return 0 if direct_result is not None and hermes_result is not None else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    return run_once(
        args.root.resolve(),
        args.output_dir.resolve(),
        args.manifest.resolve(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
