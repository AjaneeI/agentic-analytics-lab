#!/usr/bin/env python3
"""Diagnose observable failure stages in an existing benchmark JSON artifact."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evals.diagnostics import diagnose_payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Classify observable failure stages from an existing Agentic "
            "Analytics benchmark artifact without rerunning the model."
        )
    )
    parser.add_argument("benchmark", type=Path, help="Existing benchmark JSON")
    parser.add_argument(
        "--questions",
        type=Path,
        default=Path("evals/questions.json"),
        help="Frozen question definition JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional JSON destination. If omitted, print to stdout only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(args.benchmark.read_text())
    questions = json.loads(args.questions.read_text())
    diagnostics = diagnose_payload(payload, questions)
    diagnostics["source_artifact"] = str(args.benchmark)
    diagnostics["question_set"] = str(args.questions)
    rendered = json.dumps(diagnostics, indent=2, sort_keys=True) + "\n"

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)

    print(rendered, end="")


if __name__ == "__main__":
    main()
