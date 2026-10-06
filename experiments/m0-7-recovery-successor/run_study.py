#!/usr/bin/env python3
"""Run the preregistered M0.7 bounded recovery successor once."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
from typing import Any

from src.agents.ollama_client import OllamaModelClient
from src.evals.system_benchmark.local_worker import _QUERY_TOOL
from src.tools.clickhouse_readonly import query_clickhouse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST = Path(__file__).with_name("frozen-state.json")
PREVIOUS_RUNNER = (
    ROOT / "experiments" / "m0-7-tool-contract-usability" / "run_study.py"
)


def _load_previous():
    spec = importlib.util.spec_from_file_location("m0_7_original_runner", PREVIOUS_RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


previous = _load_previous()


def verify_environment() -> dict[str, Any]:
    required = ["CLICKHOUSE_URL", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD"]
    missing = [name for name in required if name not in os.environ]
    if missing:
        raise RuntimeError(
            "missing required ClickHouse environment variables: "
            + ", ".join(missing)
        )
    rows = query_clickhouse(
        "SELECT count() AS row_count "
        "FROM agentic_analytics.delivery_work_items"
    )
    if rows != [{"row_count": 500}]:
        raise RuntimeError(f"unexpected ClickHouse preflight rows: {rows!r}")
    return {
        "passed": True,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "required_environment_present": required,
        "query": (
            "SELECT count() AS row_count "
            "FROM agentic_analytics.delivery_work_items"
        ),
        "rows": rows,
    }


def run_once(root: Path, output_dir: Path, manifest_path: Path) -> int:
    previous.prepare_output_directory(output_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    previous._json_write(output_dir / "frozen-state.json", manifest)
    previous._json_write(
        output_dir / "preflight-frozen-state.json",
        previous.verify_frozen_state(root, manifest),
    )
    try:
        environment = verify_environment()
    except Exception as exc:
        previous._json_write(
            output_dir / "preflight-environment.json",
            {
                "passed": False,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "error": f"{type(exc).__name__}: {exc}",
                "model_invocations": 0,
            },
        )
        previous._json_write(
            output_dir / "evidence-index.json",
            previous.build_evidence_index(output_dir),
        )
        return 2
    previous._json_write(output_dir / "preflight-environment.json", environment)

    study = manifest["study"]
    attempts = previous.run_cases(
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
    previous._json_write(output_dir / "study-report.json", report)
    previous._json_write(
        output_dir / "decision.json",
        {
            "m0_8_authorized_by_evidence": report["passed"],
            "decision": (
                "proceed_to_m0_8"
                if report["passed"]
                else "stop_m0_model_intervention_loop"
            ),
            "same_study_rerun_authorized": False,
        },
    )
    previous._json_write(
        output_dir / "postflight.json",
        previous.verify_frozen_state(root, manifest),
    )
    previous._json_write(
        output_dir / "evidence-index.json",
        previous.build_evidence_index(output_dir),
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if args.verify_only:
        print(
            json.dumps(
                previous.verify_frozen_state(root, manifest), sort_keys=True
            )
        )
        return 0
    if args.preflight_only:
        print(json.dumps(verify_environment(), sort_keys=True))
        return 0
    if args.output_dir is None:
        parser.error(
            "--output-dir is required unless --verify-only or "
            "--preflight-only is used"
        )
    return run_once(root, args.output_dir.resolve(), manifest_path)


if __name__ == "__main__":
    raise SystemExit(main())
