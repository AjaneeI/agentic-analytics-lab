"""Summarize multiple unchanged benchmark runs for repeatability review."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.evals.repeatability import (
    load_benchmark,
    summarize_repeatability,
    write_markdown_summary,
)


DEFAULT_OUTPUT = Path("docs/generated/single-agent-repeatability-summary.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare repeated benchmark JSON runs under fixed conditions."
    )
    parser.add_argument(
        "inputs",
        nargs="+",
        type=Path,
        help="Benchmark JSON files produced by scripts/run_single_agent_eval.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination Markdown path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--title",
        default="Single-Agent Repeatability Summary",
        help="Report title.",
    )
    args = parser.parse_args()
    if len(args.inputs) < 2:
        parser.error("provide at least two benchmark JSON files")
    return args


def main() -> None:
    args = parse_args()
    payloads = [load_benchmark(path) for path in args.inputs]
    summary = summarize_repeatability(payloads)
    destination = write_markdown_summary(
        summary,
        args.output,
        title=args.title,
    )
    print(f"Wrote repeatability summary: {destination}")


if __name__ == "__main__":
    main()
