#!/usr/bin/env python3
"""Execute the preregistered M0.5 capability studies exactly once."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
from typing import Any

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import TOOL_SPEC
from src.evals.capability_reliability import (
    build_delegation_prompt,
    evaluate_delegation_attempt,
    evaluate_sql_attempt,
    summarize_studies,
)
from src.tools.clickhouse_readonly import query_clickhouse


PROFILE = "localbenchmark"
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def prepare_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        raise FileExistsError(
            f"refusing to reuse {output_dir}; M0.5 retries are forbidden"
        )
    output_dir.mkdir(parents=True)


def verify_frozen_state(root: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    expected_ref = manifest["repository"]["freeze_ref"]
    head = _git(root, "rev-parse", "HEAD")
    frozen = _git(root, "rev-parse", f"{expected_ref}^{{}}")
    if head != frozen:
        raise RuntimeError(f"HEAD {head} does not match {expected_ref} ({frozen})")
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--"], cwd=root, check=True)
    subprocess.run(
        ["git", "diff", "--cached", "--quiet", "HEAD", "--"],
        cwd=root,
        check=True,
    )

    for relative, expected in manifest["contract_sha256"].items():
        if _sha256(root / relative) != expected:
            raise RuntimeError(f"contract hash mismatch: {relative}")

    pinned = [
        *manifest["installed_state"]["files"],
        *manifest["one_worker_enforcement"]["assets"],
    ]
    for row in pinned:
        if _sha256(Path(row["path"])) != row["sha256"]:
            raise RuntimeError(f"installed file hash mismatch: {row['path']}")

    model = manifest["runtime"]["model"]
    if _sha256(Path(model["manifest_path"])) != model["manifest_sha256"]:
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
    expected_count = len(manifest["installed_state"]["visible_tools"])
    if prompt_size["tools"]["count"] != expected_count:
        raise RuntimeError("isolated profile tool count changed")

    return {
        "passed": True,
        "head": head,
        "freeze_ref": expected_ref,
        "profile": PROFILE,
        "tool_count": expected_count,
        "contract_sha256": manifest["contract_sha256"],
    }


def run_study_a_cases(
    *,
    model: Any,
    cases: list[dict[str, Any]],
    system_prompt: str,
    tool_spec: dict[str, Any],
    query_fn,
) -> list[dict[str, Any]]:
    attempts = []
    for case in cases:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": case["user_prompt"]},
        ]
        started_at = datetime.now(timezone.utc)
        monotonic_started = time.perf_counter()
        try:
            raw_response = model.respond(messages, [tool_spec])
            outcome = evaluate_sql_attempt(
                raw_response,
                expected_rows=case["expected_rows"],
                query_fn=query_fn,
            )
        except Exception as exc:
            outcome = {
                "accepted": False,
                "reason_code": "model_error",
                "failure_categories": ["infrastructure_runtime"],
                "raw_response": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        attempts.append(
            {
                "case_id": case["case_id"],
                "request": {"messages": messages, "tools": [tool_spec]},
                "expected_rows": case["expected_rows"],
                "started_at": started_at.isoformat(),
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_seconds": time.perf_counter() - monotonic_started,
                **outcome,
            }
        )
    return attempts


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_study_b_case(
    *,
    root: Path,
    output_dir: Path,
    case: dict[str, Any],
) -> dict[str, Any]:
    case_dir = output_dir / "study-b" / case["case_id"]
    case_dir.mkdir(parents=True)
    events_path = case_dir / "events.jsonl"
    usage_path = case_dir / "usage.json"
    prompt = build_delegation_prompt(case)
    (case_dir / "prompt.txt").write_text(prompt + "\n", encoding="utf-8")
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
    _json_write(case_dir / "command.json", {"argv": command})
    env = {
        **os.environ,
        "AAL_REPO_ROOT": str(root),
        "AAL_EVIDENCE_LOG": str(events_path),
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
    (case_dir / "stdout.txt").write_text(stdout, encoding="utf-8")
    (case_dir / "stderr.txt").write_text(stderr, encoding="utf-8")
    process = {
        "returncode": returncode,
        "started_at": started_at.isoformat(),
        "ended_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "error": process_error,
    }
    _json_write(case_dir / "process.json", process)
    events = _read_jsonl(events_path)
    outcome = evaluate_delegation_attempt(
        events,
        stdout=stdout,
        returncode=returncode,
        expected_marker=case["expected_marker"],
    )
    result = {
        "case_id": case["case_id"],
        "expected_marker": case["expected_marker"],
        "elapsed_seconds": elapsed,
        "events": events,
        **outcome,
    }
    _json_write(case_dir / "evaluation.json", result)
    return result


def define_next_experiment(summary: dict[str, Any]) -> dict[str, Any]:
    passed_a = summary["study_a"]["passed"]
    passed_b = summary["study_b"]["passed"]
    categories = summary.get("observed_failure_categories", [])
    if passed_a and passed_b:
        return {
            "target": "m0_6",
            "intervention": None,
            "status": "readiness_recommended_not_executed",
            "same_study_rerun_authorized": False,
        }
    if not passed_a and passed_b:
        intervention = (
            "qualified-table instruction visibility"
            if "tool_contract_understanding" in categories
            else "SQL task-to-tool contract representation"
        )
        target = "study_a_sql_contract"
    elif passed_a and not passed_b:
        intervention = "single-task delegation instruction representation"
        target = "study_b_delegation_contract"
    else:
        intervention = "separate one-variable SQL and delegation interventions"
        target = "study_a_and_study_b_separate_successors"
    return {
        "target": target,
        "intervention": intervention,
        "status": "defined_not_executed",
        "same_study_rerun_authorized": False,
    }


def run_once(root: Path, output_dir: Path, manifest_path: Path) -> int:
    prepare_output_directory(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _json_write(output_dir / "frozen-state.json", manifest)

    _json_write(output_dir / "preflight-study-a.json", verify_frozen_state(root, manifest))
    study_a_config = manifest["studies"]["study_a"]
    study_a = run_study_a_cases(
        model=OllamaModelClient(model=manifest["runtime"]["model"]["name"]),
        cases=study_a_config["cases"],
        system_prompt=study_a_config["system_prompt"],
        tool_spec=TOOL_SPEC,
        query_fn=query_clickhouse,
    )
    _json_write(
        output_dir / "study-a-report.json",
        {
            "study_id": study_a_config["study_id"],
            "sample_size": study_a_config["sample_size"],
            "pass_threshold": study_a_config["pass_threshold"],
            "attempts": study_a,
        },
    )

    _json_write(output_dir / "preflight-study-b.json", verify_frozen_state(root, manifest))
    study_b_config = manifest["studies"]["study_b"]
    study_b = [
        run_study_b_case(root=root, output_dir=output_dir, case=case)
        for case in study_b_config["cases"]
    ]
    _json_write(
        output_dir / "study-b-report.json",
        {
            "study_id": study_b_config["study_id"],
            "sample_size": study_b_config["sample_size"],
            "pass_threshold": study_b_config["pass_threshold"],
            "attempts": study_b,
        },
    )

    summary = summarize_studies(
        study_a=study_a,
        study_b=study_b,
        threshold_a=study_a_config["pass_threshold"],
        threshold_b=study_b_config["pass_threshold"],
    )
    _json_write(output_dir / "summary.json", summary)
    _json_write(output_dir / "next-experiment.json", define_next_experiment(summary))
    _json_write(
        output_dir / "evidence-index.json",
        {
            "files": {
                str(path.relative_to(output_dir)): _sha256(path)
                for path in sorted(output_dir.rglob("*"))
                if path.is_file()
            }
        },
    )
    return 0


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
