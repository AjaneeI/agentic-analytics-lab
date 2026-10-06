#!/usr/bin/env python3
"""Execute the preregistered M0.5B delegation-retirement study once."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

from src.evals.capability_reliability import (
    build_delegation_prompt,
    evaluate_delegation_attempt,
)


PROFILE = "localbenchmark"
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def prepare_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(f"refusing to reuse {output_dir}; M0.5B retries are forbidden")
    output_dir.mkdir(parents=True)


def verify_frozen_state(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    expected_ref = manifest["repository"]["freeze_ref"]
    head = _git(root, "rev-parse", "HEAD")
    frozen = _git(root, "rev-parse", f"{expected_ref}^{{}}")
    if head != frozen:
        raise RuntimeError(f"HEAD {head} does not match {expected_ref} ({frozen})")
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=root, check=True)
    subprocess.run(["git", "diff", "--cached", "--quiet", "HEAD", "--"], cwd=root, check=True)

    for relative, expected in manifest["contract_sha256"].items():
        if _sha256(root / relative) != expected:
            raise RuntimeError(f"contract hash mismatch: {relative}")
    for row in manifest["installed_state"]["files"]:
        if _sha256(Path(row["path"])) != row["sha256"]:
            raise RuntimeError(f"installed file hash mismatch: {row['path']}")
    for relative, expected in manifest["prior_evidence_sha256"].items():
        if _sha256(root / relative) != expected:
            raise RuntimeError(f"prior evidence changed: {relative}")

    model = manifest["runtime"]["model"]
    if _sha256(Path(model["manifest_path"])) != model["manifest_sha256"]:
        raise RuntimeError("Ollama model manifest hash mismatch")

    fallback = subprocess.run(
        ["hermes", "-p", PROFILE, "fallback", "list"], cwd=root,
        check=True, capture_output=True, text=True,
    )
    if "No fallback providers configured" not in fallback.stdout:
        raise RuntimeError("isolated profile has a configured fallback provider")

    audit = subprocess.run(
        ["hermes", "-p", PROFILE, "prompt-size", "--json"], cwd=root,
        check=True, capture_output=True, text=True,
    )
    prompt_size = json.loads(audit.stdout)
    expected_tools = manifest["study"]["allowed_parent_visible_tools_before_success"]
    if prompt_size["tools"]["count"] != len(expected_tools):
        raise RuntimeError("isolated profile tool count changed")

    return {
        "passed": True,
        "head": head,
        "freeze_ref": expected_ref,
        "profile": PROFILE,
        "initial_tool_count": len(expected_tools),
        "installed_state_sha256": {
            row["path"]: row["sha256"] for row in manifest["installed_state"]["files"]
        },
    }


def _tool_names(request_dump: dict[str, Any]) -> list[str]:
    tools = request_dump.get("request", {}).get("body", {}).get("tools") or []
    return [
        item.get("function", {}).get("name")
        for item in tools
        if isinstance(item, dict) and item.get("function", {}).get("name")
    ]


def evaluate_parent_tool_retirement(request_dumps: list[dict[str, Any]]) -> dict[str, Any]:
    """Find the parent request stream and prove delegate_task disappears after success."""
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
    accepted = (
        len(tool_sets) == 2
        and "delegate_task" in tool_sets[0]
        and "delegate_task" not in tool_sets[1]
    )
    return {
        "accepted": accepted,
        "reason_code": "accepted" if accepted else "delegate_tool_not_retired",
        "parent_session_id": session_id,
        "parent_request_count": len(tool_sets),
        "parent_tools_by_request": tool_sets,
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_case(*, root: Path, output_dir: Path, case: dict[str, Any], dump_dir: Path) -> dict[str, Any]:
    case_dir = output_dir / "study-b" / case["case_id"]
    case_dir.mkdir(parents=True)
    events_path = case_dir / "events.jsonl"
    usage_path = case_dir / "usage.json"
    prompt = build_delegation_prompt(case)
    if prompt != case["parent_prompt"]:
        raise RuntimeError(f"frozen parent prompt changed: {case['case_id']}")
    (case_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    command = [
        "hermes", "-p", PROFILE, "--ignore-rules", "--usage-file", str(usage_path),
        "--in", str(root), "-z", prompt,
    ]
    _json_write(case_dir / "command.json", {"argv": command})
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
            command, cwd=root, env=env, capture_output=True, text=True,
            timeout=1200, check=False,
        )
        stdout, stderr, returncode = completed.stdout, completed.stderr, completed.returncode
        process_error = None
    except Exception as exc:
        stdout, stderr, returncode = "", "", -1
        process_error = f"{type(exc).__name__}: {exc}"
    elapsed = time.perf_counter() - monotonic_started
    (case_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (case_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    _json_write(case_dir / "process.json", {
        "returncode": returncode,
        "started_at": started_at.isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "error": process_error,
    })

    raw_dir = case_dir / "raw-requests"
    raw_dir.mkdir()
    new_dumps = sorted(set(dump_dir.glob("request_dump_*.json")) - before)
    request_dumps = []
    for source in new_dumps:
        destination = raw_dir / source.name
        shutil.copy2(source, destination)
        request_dumps.append(json.loads(destination.read_text(encoding="utf-8")))

    events = _read_jsonl(events_path)
    delegation = evaluate_delegation_attempt(
        events, stdout=stdout, returncode=returncode,
        expected_marker=case["expected_marker"],
    )
    retirement = evaluate_parent_tool_retirement(request_dumps)
    result = {
        "case_id": case["case_id"],
        "expected_marker": case["expected_marker"],
        "elapsed_seconds": elapsed,
        "events": events,
        **delegation,
        "tool_retirement": retirement,
    }
    result["accepted"] = bool(delegation["accepted"] and retirement["accepted"])
    if not retirement["accepted"]:
        result["reason_code"] = retirement["reason_code"]
        if "orchestration_decomposition" not in result["failure_categories"]:
            result["failure_categories"].append("orchestration_decomposition")
    _json_write(case_dir / "evaluation.json", result)
    return result


def run_once(root: Path, output_dir: Path, manifest_path: Path) -> int:
    prepare_output_directory(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _json_write(output_dir / "frozen-state.json", manifest)
    _json_write(output_dir / "preflight.json", verify_frozen_state(root, manifest))
    dump_dir = Path(manifest["installed_state"]["request_dump_directory"])
    attempts = [
        run_case(root=root, output_dir=output_dir, case=case, dump_dir=dump_dir)
        for case in manifest["study"]["cases"]
    ]
    accepted = sum(item["accepted"] is True for item in attempts)
    passed = accepted >= manifest["study"]["pass_threshold"]
    summary = {
        "study_id": manifest["study"]["study_id"],
        "accepted": accepted,
        "sample_size": len(attempts),
        "pass_threshold": manifest["study"]["pass_threshold"],
        "passed": passed,
        "attempts": attempts,
        "decision": "recommend_next_m0_gate_not_executed" if passed else "define_next_experiment",
        "rerun_authorized": False,
        "incremental_paid_spend_usd": 0,
        "interpretation_boundary": manifest["interpretation_boundary"],
    }
    _json_write(output_dir / "study-b-report.json", summary)
    _json_write(output_dir / "summary.json", {key: value for key, value in summary.items() if key != "attempts"})
    _json_write(output_dir / "evidence-index.json", {
        "files": {
            str(path.relative_to(output_dir)): _sha256(path)
            for path in sorted(output_dir.rglob("*")) if path.is_file()
        }
    })
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    return run_once(args.root.resolve(), args.output_dir.resolve(), args.manifest.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
