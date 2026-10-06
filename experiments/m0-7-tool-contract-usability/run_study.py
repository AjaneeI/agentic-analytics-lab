#!/usr/bin/env python3
"""Run the preregistered M0.7 SQL-qualification study exactly once."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any

from src.agents.ollama_client import OllamaModelClient
from src.evals.capability_reliability import evaluate_sql_attempt
from src.evals.system_benchmark.local_worker import _QUERY_TOOL
from src.tools.clickhouse_readonly import query_clickhouse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


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
            f"refusing to reuse {output_dir}; M0.7 retries are forbidden"
        )
    output_dir.mkdir(parents=True)


def verify_frozen_state(
    root: Path, manifest: dict[str, Any]
) -> dict[str, Any]:
    expected_ref = manifest["repository"]["freeze_ref"]
    head = _git(root, "rev-parse", "HEAD")
    frozen = _git(root, "rev-parse", f"{expected_ref}^{{}}")
    if head != frozen:
        raise RuntimeError(
            f"HEAD {head} does not match {expected_ref} ({frozen})"
        )
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"], cwd=root, check=True
    )
    subprocess.run(
        ["git", "diff", "--cached", "--quiet", "HEAD", "--"],
        cwd=root,
        check=True,
    )

    hashes = {}
    for relative, expected in manifest["contract_sha256"].items():
        actual = _sha256(root / relative)
        if actual != expected:
            raise RuntimeError(f"contract hash mismatch: {relative}")
        hashes[relative] = actual

    model = manifest["runtime"]["model"]
    actual_model_hash = _sha256(Path(model["manifest_path"]))
    if actual_model_hash != model["manifest_sha256"]:
        raise RuntimeError("Ollama model manifest hash mismatch")

    return {
        "passed": True,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "head": head,
        "freeze_ref": expected_ref,
        "contract_sha256": hashes,
        "model_manifest_sha256": actual_model_hash,
    }


def build_evidence_index(output_dir: Path) -> dict[str, Any]:
    return {
        "files": {
            str(path.relative_to(output_dir)): _sha256(path)
            for path in sorted(output_dir.rglob("*"))
            if path.is_file() and path.name != "evidence-index.json"
        }
    }


def run_cases(
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


def run_once(root: Path, output_dir: Path, manifest_path: Path) -> int:
    prepare_output_directory(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _json_write(output_dir / "frozen-state.json", manifest)
    _json_write(
        output_dir / "preflight.json", verify_frozen_state(root, manifest)
    )

    study = manifest["study"]
    attempts = run_cases(
        model=OllamaModelClient(model=manifest["runtime"]["model"]["name"]),
        cases=study["cases"],
        system_prompt=study["system_prompt"],
        tool_spec=_QUERY_TOOL,
        query_fn=query_clickhouse,
    )
    accepted = sum(1 for attempt in attempts if attempt["accepted"])
    report = {
        "study_id": study["study_id"],
        "sample_size": study["sample_size"],
        "pass_threshold": study["pass_threshold"],
        "accepted_attempts": accepted,
        "passed": accepted >= study["pass_threshold"],
        "retries": 0,
        "incremental_paid_spend_usd": 0,
        "attempts": attempts,
    }
    _json_write(output_dir / "study-report.json", report)
    _json_write(
        output_dir / "decision.json",
        {
            "m0_8_authorized_by_evidence": report["passed"],
            "decision": (
                "proceed_to_m0_8"
                if report["passed"]
                else "stop_and_define_smallest_supported_intervention"
            ),
            "same_study_rerun_authorized": False,
        },
    )
    _json_write(
        output_dir / "postflight.json", verify_frozen_state(root, manifest)
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
        print(json.dumps(verify_frozen_state(root, manifest), sort_keys=True))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required unless --verify-only is used")
    return run_once(root, args.output_dir.resolve(), manifest_path)


if __name__ == "__main__":
    raise SystemExit(main())
