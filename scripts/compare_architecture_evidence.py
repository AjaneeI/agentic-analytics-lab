#!/usr/bin/env python3
"""Compare matched repeated benchmark artifacts across two architectures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.repeatability import load_benchmark
from src.evals.statistical_evidence import compare_architectures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare repeated baseline and candidate benchmark runs with a "
            "paired task-level bootstrap."
        )
    )
    parser.add_argument(
        "--baseline",
        nargs="+",
        type=Path,
        required=True,
        help="Repeated benchmark JSON files for the baseline architecture.",
    )
    parser.add_argument(
        "--candidate",
        nargs="+",
        type=Path,
        required=True,
        help="Repeated benchmark JSON files for the candidate architecture.",
    )
    parser.add_argument(
        "--bootstrap-samples",
        type=int,
        default=10_000,
        help="Number of task-level bootstrap resamples (default: 10000).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic bootstrap seed (default: 42).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional destination for the JSON comparison artifact.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = compare_architectures(
        [load_benchmark(path) for path in args.baseline],
        [load_benchmark(path) for path in args.candidate],
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
        print(args.output)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
