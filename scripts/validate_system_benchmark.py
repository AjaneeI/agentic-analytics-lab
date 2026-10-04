#!/usr/bin/env python3
"""Validate System Benchmark fixtures and optionally emit contract provenance."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references, validate_task_reference
from src.evals.system_benchmark.runner import fingerprint_paths


DEFAULT_CONTRACT_PATHS = (
    "evals/system_benchmark/development_tasks.json",
    "evals/system_benchmark/development_references.json",
    "evals/system_benchmark/corpus/manifest.json",
    "src/evals/system_benchmark/contracts.py",
    "src/evals/system_benchmark/scoring.py",
    "src/evals/system_benchmark/routing.py",
    "src/evals/system_benchmark/workers.py",
    "src/evals/system_benchmark/runner.py",
    "src/tools/policy_retrieval.py",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate System Benchmark v1 fixtures.")
    parser.add_argument(
        "fixture",
        nargs="?",
        type=Path,
        default=Path("evals/system_benchmark/development_tasks.json"),
    )
    parser.add_argument(
        "--references",
        type=Path,
        default=Path("evals/system_benchmark/development_references.json"),
    )
    parser.add_argument("--emit-provenance", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tasks = load_tasks(args.fixture)
    references = load_references(args.references)
    by_id = {item.reference_solution_id: item for item in references}
    for task in tasks:
        reference = by_id.get(task.reference_solution_id)
        if reference is None:
            raise ValueError(f"missing reference: {task.reference_solution_id}")
        validate_task_reference(task, reference)

    if args.emit_provenance:
        root = Path.cwd()
        result = {
            "benchmark_version": "system-benchmark-v1",
            "split": tasks[0].split.value,
            "tasks": len(tasks),
            "references": len(references),
            "reference_contracts_valid": True,
            "provenance": fingerprint_paths(root, DEFAULT_CONTRACT_PATHS),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"PASS: validated {len(tasks)} System Benchmark task(s) and references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
