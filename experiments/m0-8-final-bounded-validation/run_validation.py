#!/usr/bin/env python3
"""Run one final bounded Hermes workflow for the M0 exit decision."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROFILE = "localbenchmark"
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")
M0_6_RUNNER = ROOT / "experiments" / "m0-6-fresh-sb-d01-ab" / "run_benchmark.py"
RECOVERY_RUNNER = ROOT / "experiments" / "m0-7-recovery-successor" / "run_study.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m0_6 = _load_module("m0_8_m0_6", M0_6_RUNNER)
recovery = _load_module("m0_8_recovery", RECOVERY_RUNNER)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _tool_names(request_dump: dict[str, Any]) -> list[str]:
    tools = request_dump.get("request", {}).get("body", {}).get("tools") or []
    return [
        item.get("function", {}).get("name")
        for item in tools
        if isinstance(item, dict) and item.get("function", {}).get("name")
    ]


def evaluate_parent_tool_retirement(
    request_dumps: list[dict[str, Any]],
) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for payload in request_dumps:
        grouped[str(payload.get("session_id", ""))].append(payload)
    parent_streams = []
    for session_id, rows in grouped.items():
        ordered = sorted(rows, key=lambda row: str(row.get("timestamp", "")))
        if any("delegate_task" in _tool_names(row) for row in ordered):
            parent_streams.append((session_id, ordered))
    if len(parent_streams) != 1:
        return {
            "accepted": False,
            "reason_code": "parent_request_stream_ambiguous",
            "parent_stream_count": len(parent_streams),
        }
    session_id, rows = parent_streams[0]
    tool_sets = [_tool_names(row) for row in rows]
    accepted = bool(
        len(tool_sets) >= 2
        and "delegate_task" in tool_sets[0]
        and all("delegate_task" not in names for names in tool_sets[1:])
    )
    return {
        "accepted": accepted,
        "reason_code": "accepted" if accepted else "delegate_tool_not_retired",
        "parent_session_id": session_id,
        "parent_request_count": len(tool_sets),
        "parent_tools_by_request": tool_sets,
    }


def _sanitize_request_copy(source: Path, destination: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    original_bytes = source.read_bytes()
    payload = json.loads(original_bytes)
    copy_payload = json.loads(json.dumps(payload))
    headers = copy_payload.get("request", {}).get("headers")
    redacted_fields = []
    if isinstance(headers, dict) and "Authorization" in headers:
        headers["Authorization"] = "<redacted-local-loopback-credential>"
        redacted_fields.append("request.headers.Authorization")
    destination.write_text(
        json.dumps(copy_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload, {
        "source_path": str(source),
        "repository_copy": destination.name,
        "original_sha256": hashlib.sha256(original_bytes).hexdigest(),
        "sanitized_sha256": _sha256(destination),
        "redacted_fields": redacted_fields,
    }


def _copy_new_request_dumps(
    dump_dir: Path, before: set[Path], destination: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    destination.mkdir()
    payloads = []
    records = []
    for source in sorted(set(dump_dir.glob("request_dump_*.json")) - before):
        payload, record = _sanitize_request_copy(source, destination / source.name)
        payloads.append(payload)
        records.append(record)
    return payloads, {
        "schema_version": "m0-8-request-redaction-v1",
        "policy": (
            "Repository copies replace only request.headers.Authorization. "
            "Local originals remain untouched."
        ),
        "files": records,
    }


def orchestration_observation(
    events: list[dict[str, Any]], request_dumps: list[dict[str, Any]]
) -> dict[str, Any]:
    delegate_pre = [
        event
        for event in events
        if event.get("event") == "delegate_pre"
        and event.get("tool") == "delegate_task"
    ]
    successful_posts = [
        event
        for event in events
        if event.get("event") == "delegate_post"
        and event.get("tool") == "delegate_task"
        and event.get("ok") is True
    ]
    evidence = [
        event
        for event in events
        if event.get("tool") in {"query_clickhouse", "retrieve_policy"}
    ]
    interventions = [event for event in events if event.get("ok") is False]
    parent_evidence = [
        event for event in evidence if event.get("delegated_child") is not True
    ]
    retirement = evaluate_parent_tool_retirement(request_dumps)
    observation = {
        "delegation_attempts": len(delegate_pre),
        "delegation_count": sum(event.get("ok") is True for event in delegate_pre),
        "child_count": len(successful_posts),
        "attempted_extra_delegations": max(0, len(delegate_pre) - 1),
        "successful_worker_launches": len(successful_posts),
        "evidence_tool_calls": len(evidence),
        "successful_evidence_tool_calls": sum(
            event.get("ok") is True for event in evidence
        ),
        "enforcement_interventions": len(interventions),
        "parent_evidence_tool_calls": len(parent_evidence),
        "tool_retirement": retirement,
        "post_success_delegate_task_retired": retirement["accepted"],
    }
    observation["orchestration_accepted"] = bool(
        observation["delegation_attempts"] == 1
        and observation["delegation_count"] == 1
        and observation["child_count"] == 1
        and observation["attempted_extra_delegations"] == 0
        and observation["evidence_tool_calls"] == 2
        and observation["successful_evidence_tool_calls"] == 2
        and observation["enforcement_interventions"] == 0
        and observation["parent_evidence_tool_calls"] == 0
        and observation["post_success_delegate_task_retired"]
    )
    return observation


def build_evidence_index(output_dir: Path) -> dict[str, Any]:
    return {
        "files": {
            str(path.relative_to(output_dir)): _sha256(path)
            for path in sorted(output_dir.rglob("*"))
            if path.is_file() and path.name != "evidence-index.json"
        }
    }


def run_once(root: Path, output_dir: Path, manifest_path: Path) -> int:
    m0_6.prepare_output_directory(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _json_write(output_dir / "frozen-state.json", manifest)
    _json_write(
        output_dir / "preflight-frozen-state.json",
        m0_6.previous.verify_frozen_state(root, manifest),
    )
    _json_write(
        output_dir / "preflight-environment.json",
        recovery.verify_environment(),
    )

    task, _ = m0_6.previous.load_case(root)
    prompt = m0_6.previous.build_hermes_prompt(task.request)
    (output_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    usage_path = output_dir / "usage.json"
    events_path = output_dir / "events.jsonl"
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
    _json_write(output_dir / "command.json", {"argv": command})
    dump_dir = Path(manifest["installed_state"]["request_dump_directory"])
    before = set(dump_dir.glob("request_dump_*.json"))
    env = {
        **os.environ,
        "AAL_REPO_ROOT": str(root),
        "AAL_EVIDENCE_LOG": str(events_path),
        "HERMES_DUMP_REQUESTS": "1",
    }
    started_at = datetime.now(timezone.utc)
    monotonic_started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=1200,
            check=False,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
        process_error = None
    except Exception as exc:
        stdout = ""
        stderr = ""
        returncode = -1
        process_error = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - monotonic_started
    (output_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (output_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    _json_write(
        output_dir / "process.json",
        {
            "returncode": returncode,
            "started_at": started_at.isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "error": process_error,
        },
    )

    request_dumps, redaction = _copy_new_request_dumps(
        dump_dir, before, output_dir / "raw-requests"
    )
    _json_write(output_dir / "redaction-manifest.json", redaction)
    events = _read_jsonl(events_path)
    orchestration = orchestration_observation(events, request_dumps)
    _json_write(output_dir / "orchestration.json", orchestration)

    error = None
    scored = None
    try:
        if returncode != 0:
            raise RuntimeError(f"Hermes exited {returncode}")
        usage = (
            json.loads(usage_path.read_text(encoding="utf-8"))
            if usage_path.is_file()
            else {}
        )
        scored = m0_6.previous.score_hermes_execution(
            root,
            stdout.strip(),
            events,
            latency_seconds=elapsed,
            usage=usage,
        )
        scored.update(orchestration)
        scored["answer_score_passed"] = scored["score"]["passed"]
        scored["task_success"] = bool(
            scored["answer_score_passed"]
            and scored["orchestration_accepted"]
        )
        _json_write(output_dir / "score.json", scored)
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        _json_write(
            output_dir / "score-error.json",
            {
                "error": error,
                "scored": False,
                "orchestration": orchestration,
            },
        )

    accepted = bool(scored and scored.get("task_success"))
    _json_write(
        output_dir / "independent-verification.json",
        {
            "accepted": accepted,
            "existing_deterministic_scorer_passed": bool(
                scored and scored["score"]["passed"]
            ),
            "raw_event_orchestration_passed": orchestration[
                "orchestration_accepted"
            ],
            "tool_events_reconstructed": len(events),
            "error": error,
        },
    )
    _json_write(
        output_dir / "m0-decision.json",
        {
            "foundation_sufficient_for_bounded_use": accepted,
            "verdict": (
                "M0 foundation sufficient for bounded use"
                if accepted
                else "M0 exit criterion not met"
            ),
            "m1_authorized_by_evidence": accepted,
            "retries": 0,
            "human_interventions": 0,
            "incremental_paid_spend_usd": 0,
        },
    )
    _json_write(
        output_dir / "postflight.json",
        m0_6.previous.verify_frozen_state(root, manifest),
    )
    _json_write(output_dir / "evidence-index.json", build_evidence_index(output_dir))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.verify_only:
        print(
            json.dumps(
                m0_6.previous.verify_frozen_state(root, manifest),
                sort_keys=True,
            )
        )
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required unless --verify-only is used")
    return run_once(root, args.output_dir.resolve(), manifest_path)


if __name__ == "__main__":
    raise SystemExit(main())
