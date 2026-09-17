"""Generate a reviewable Markdown report from a benchmark JSON file."""

from __future__ import annotations

import argparse
from pathlib import Path

from src.evals.reporting import load_benchmark, write_markdown_report


DEFAULT_OUTPUT = Path("docs/generated/single-agent-benchmark-report.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a deterministic Markdown benchmark report."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to benchmark JSON produced by scripts/run_single_agent_eval.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination Markdown path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--title",
        default="Single-Agent Benchmark Report",
        help="Report title.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = load_benchmark(args.input)
    destination = write_markdown_report(
        payload,
        args.output,
        title=args.title,
    )
    print(f"Wrote benchmark report: {destination}")


if __name__ == "__main__":
    main()
