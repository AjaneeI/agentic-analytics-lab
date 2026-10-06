#!/usr/bin/env python3
"""Run the preregistered M0.6 direct-vs-repaired-Hermes A/B exactly once."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROFILE = "localbenchmark"
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")
PREVIOUS_RUNNER = ROOT / "experiments/hermes-successor-ab-v1/run_benchmark.py"
RETIREMENT_RUNNER = ROOT / "experiments/m0-5b-delegation-retirement/run_study.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = _load_module("m0_6_previous_runner", PREVIOUS_RUNNER)
retirement = _load_module("m0_6_retirement_runner", RETIREMENT_RUNNER)
evaluate_parent_tool_retirement = retirement.evaluate_parent_tool_retirement


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def prepare_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(
            f"refusing to reuse {output_dir}; M0.6 retries are forbidden"
        )
    output_dir.mkdir(parents=True)


def build_evidence_index(output_dir: Path) -> dict[str, Any]:
    return {
        "files": {
            str(path.relative_to(output_dir)): _sha256(path)
            for path in sorted(output_dir.rglob("*"))
            if path.is_file() and path.name != "evidence-index.json"
        }
    }


def _process_snapshot() -> str:
    completed = subprocess.run(
        ["ps", "-Ao", "pid,ppid,stat,etime,command"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def _copy_new_request_dumps(
    dump_dir: Path, before: set[Path], destination: Path
) -> list[dict[str, Any]]:
    destination.mkdir()
    payloads = []
    for source in sorted(set(dump_dir.glob("request_dump_*.json")) - before):
        target = destination / source.name
        shutil.copy2(source, target)
        payloads.append(json.loads(target.read_text(encoding="utf-8")))
    return payloads


def _orchestration_observation(
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
    intervention_ids = {
        str(event.get("tool_call_id") or f"event-{index}")
        for index, event in enumerate(interventions)
    }
    parent_evidence = [
        event for event in evidence if event.get("delegated_child") is not True
    ]

    if successful_posts:
        tool_retirement = evaluate_parent_tool_retirement(request_dumps)
    else:
        tool_retirement = {
            "accepted": False,
            "reason_code": "not_reached_no_successful_child",
        }

    valid_delegations = sum(event.get("ok") is True for event in delegate_pre)
    observation = {
        "delegation_attempts": len(delegate_pre),
        "delegation_count": valid_delegations,
        "child_count": len(successful_posts),
        "attempted_extra_delegations": max(0, len(delegate_pre) - 1),
        "enforcement_interventions": len(intervention_ids),
        "parent_evidence_tool_calls": len(parent_evidence),
        "successful_worker_launches": len(successful_posts),
        "tool_retirement": tool_retirement,
        "post_success_delegate_task_retired": tool_retirement["accepted"],
    }
    observation["orchestration_accepted"] = bool(
        observation["delegation_attempts"] == 1
        and observation["delegation_count"] == 1
        and observation["child_count"] == 1
        and observation["attempted_extra_delegations"] == 0
        and observation["enforcement_interventions"] == 0
        and observation["parent_evidence_tool_calls"] == 0
        and observation["post_success_delegate_task_retired"]
    )
    return observation


def _dimension_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if not result:
        return {"passed": 0, "total": 0, "reason_codes": ["unscored"]}
    dimensions = result["score"]["dimensions"]
    return {
        "passed": sum(item["passed"] is True for item in dimensions),
        "total": len(dimensions),
        "reason_codes": result["score"]["reason_codes"],
    }


def build_comparison(
    direct: dict[str, Any] | None,
    hermes: dict[str, Any] | None,
    errors: dict[str, str],
) -> dict[str, Any]:
    return {
        "task_id": "SB-D01",
        "primary_metric": "Ajanee hands-on intervention per accepted result",
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
            "deterministic_acceptance": bool(
                hermes
                and hermes["task_success"]
                and hermes.get("orchestration_accepted")
            ),
            "answer_score_passed": bool(hermes and hermes["score"]["passed"]),
            "answer_quality": _dimension_summary(hermes),
            "orchestration_accepted": bool(
                hermes and hermes.get("orchestration_accepted")
            ),
            "human_interventions": 0,
            "retries": 0,
            "recovery_actions": 0,
            "latency_seconds": hermes.get("latency_seconds") if hermes else None,
            "model_calls": hermes.get("model_calls") if hermes else None,
            "tool_calls": hermes.get("tool_call_count") if hermes else None,
            "delegation_count": hermes.get("delegation_count") if hermes else None,
            "child_count": hermes.get("child_count") if hermes else None,
            "attempted_extra_delegations": hermes.get(
                "attempted_extra_delegations"
            ) if hermes else None,
            "enforcement_interventions": hermes.get(
                "enforcement_interventions"
            ) if hermes else None,
            "parent_evidence_tool_calls": hermes.get(
                "parent_evidence_tool_calls"
            ) if hermes else None,
            "post_success_delegate_task_retired": hermes.get(
                "post_success_delegate_task_retired"
            ) if hermes else None,
            "error": errors.get("hermes"),
        },
        "incremental_paid_spend_usd": 0,
        "scope_note": (
            "One SB-D01 comparison does not establish general superiority of "
            "either architecture."
        ),
    }


def determine_m1_readiness(
    hermes: dict[str, Any] | None, errors: dict[str, str]
) -> dict[str, Any]:
    checks = {
        "hermes_scored": hermes is not None,
        "deterministic_acceptance": bool(hermes and hermes.get("task_success")),
        "orchestration_accepted": bool(
            hermes and hermes.get("orchestration_accepted")
        ),
        "delegation_count": bool(hermes and hermes.get("delegation_count") == 1),
        "child_count": bool(hermes and hermes.get("child_count") == 1),
        "enforcement_interventions": bool(
            hermes and hermes.get("enforcement_interventions") == 0
        ),
        "parent_evidence_tool_calls": bool(
            hermes and hermes.get("parent_evidence_tool_calls") == 0
        ),
        "post_success_delegate_task_retired": bool(
            hermes and hermes.get("post_success_delegate_task_retired")
        ),
        "retries": bool(hermes and hermes.get("retries") == 0),
        "incremental_paid_spend_usd": bool(
            hermes and hermes.get("incremental_paid_spend_usd") == 0
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    ready = not failed
    return {
        "ready": ready,
        "verdict": (
            "M0 complete — M1 bounded Personal Ops recommended"
            if ready
            else "M0.6 does not support transition to M1"
        ),
        "checks": checks,
        "failed_checks": failed,
        "errors": errors,
        "m1_scope_if_ready": (
            [
                "read-only project-state recovery",
                "highest-value safe next-action identification",
                "bounded local engineering work",
                "independent verification",
                "Green/Yellow/Red permission boundaries",
            ]
            if ready
            else []
        ),
        "m1_executed": False,
    }


def run_once(root: Path, output_dir: Path, manifest_path: Path) -> int:
    prepare_output_directory(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _json_write(output_dir / "frozen-state.json", manifest)

    preflight_a = previous.verify_frozen_state(root, manifest)
    _json_write(output_dir / "preflight-a.json", preflight_a)
    (output_dir / "process-state-before-a.txt").write_text(
        _process_snapshot(), encoding="utf-8"
    )

    task, reference = previous.load_case(root)
    direct_result = None
    hermes_result = None
    errors: dict[str, str] = {}

    direct_model = previous.RecordingModel(
        previous.OllamaModelClient(model=manifest["runtime"]["model"]["name"]),
        output_dir / "treatment-a-model.jsonl",
    )
    direct_started = datetime.now(timezone.utc)
    try:
        direct_result = previous.run_trial(
            task,
            reference,
            trial_number=1,
            executor=previous.BoundedLocalExecutor(model=direct_model),
        )
        direct_result.update(
            treatment="direct_bounded_local",
            started_at=direct_started.isoformat(),
            ended_at=datetime.now(timezone.utc).isoformat(),
            human_interventions=0,
            retries=0,
            incremental_paid_spend_usd=0,
        )
        _json_write(output_dir / "treatment-a-score.json", direct_result)
    except Exception as exc:
        errors["direct"] = f"{type(exc).__name__}: {exc}"
        _json_write(
            output_dir / "treatment-a-error.json",
            {
                "error": errors["direct"],
                "scored": False,
                "started_at": direct_started.isoformat(),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "retries": 0,
                "human_interventions": 0,
                "incremental_paid_spend_usd": 0,
            },
        )

    preflight_b = previous.verify_frozen_state(root, manifest)
    _json_write(output_dir / "preflight-b.json", preflight_b)
    (output_dir / "process-state-before-b.txt").write_text(
        _process_snapshot(), encoding="utf-8"
    )

    evidence_log = output_dir / "treatment-b-events.jsonl"
    usage_path = output_dir / "treatment-b-usage.json"
    prompt = previous.build_hermes_prompt(task.request)
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
    dump_dir = Path(manifest["installed_state"]["request_dump_directory"])
    dumps_before = set(dump_dir.glob("request_dump_*.json"))
    env = {
        **os.environ,
        "AAL_REPO_ROOT": str(root),
        "AAL_EVIDENCE_LOG": str(evidence_log),
        "HERMES_DUMP_REQUESTS": "1",
    }
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
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
    elapsed = time.perf_counter() - started
    (output_dir / "treatment-b-stdout.txt").write_text(stdout, encoding="utf-8")
    (output_dir / "treatment-b-stderr.txt").write_text(stderr, encoding="utf-8")
    _json_write(
        output_dir / "treatment-b-process.json",
        {
            "returncode": returncode,
            "started_at": started_at.isoformat(),
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "error": process_error,
        },
    )
    request_dumps = _copy_new_request_dumps(
        dump_dir, dumps_before, output_dir / "treatment-b-raw-requests"
    )
    events = _read_jsonl(evidence_log)
    orchestration = _orchestration_observation(events, request_dumps)
    _json_write(output_dir / "treatment-b-orchestration.json", orchestration)
    (output_dir / "process-state-after-b.txt").write_text(
        _process_snapshot(), encoding="utf-8"
    )

    try:
        if returncode != 0:
            raise RuntimeError(f"Hermes exited {returncode}")
        usage = (
            json.loads(usage_path.read_text(encoding="utf-8"))
            if usage_path.is_file()
            else {}
        )
        hermes_result = previous.score_hermes_execution(
            root,
            stdout.strip(),
            events,
            latency_seconds=elapsed,
            usage=usage,
        )
        hermes_result.update(orchestration)
        hermes_result["answer_score_passed"] = hermes_result["score"]["passed"]
        hermes_result["task_success"] = bool(
            hermes_result["answer_score_passed"]
            and hermes_result["orchestration_accepted"]
        )
        _json_write(output_dir / "treatment-b-score.json", hermes_result)
    except Exception as exc:
        errors["hermes"] = f"{type(exc).__name__}: {exc}"
        _json_write(
            output_dir / "treatment-b-error.json",
            {
                "error": errors["hermes"],
                "scored": False,
                "orchestration": orchestration,
                "retries": 0,
                "human_interventions": 0,
                "incremental_paid_spend_usd": 0,
            },
        )

    comparison = build_comparison(direct_result, hermes_result, errors)
    _json_write(output_dir / "comparison.json", comparison)
    _json_write(
        output_dir / "m1-readiness.json",
        determine_m1_readiness(hermes_result, errors),
    )
    _json_write(output_dir / "postflight.json", previous.verify_frozen_state(root, manifest))
    _json_write(output_dir / "evidence-index.json", build_evidence_index(output_dir))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    return run_once(
        args.root.resolve(), args.output_dir.resolve(), args.manifest.resolve()
    )


if __name__ == "__main__":
    raise SystemExit(main())
