#!/usr/bin/env python3
"""Validate a System Benchmark v1 task fixture without executing a model."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.system_benchmark.loader import load_tasks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a System Benchmark v1 task fixture."
    )
    parser.add_argument(
        "fixture",
        type=Path,
        help="Path to a System Benchmark task JSON file.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tasks = load_tasks(args.fixture)
    print(f"PASS: validated {len(tasks)} System Benchmark task(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
