"""Run the non-evidentiary bounded throughput experiment."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent
from src.evals.throughput import run_throughput_sweep


MODEL = "qwen2.5:7b"
QUESTIONS_PATH = Path("evals/questions.json")
DESTINATION = Path("experiments/results/throughput_qwen2.5_7b.json")
DEFAULT_LEVELS = (1, 2, 4, 6)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Measure validated tasks per minute under bounded concurrency. "
            "This is a systems/load experiment, not an official Q1-Q6 benchmark run."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing local throughput artifact.",
    )
    return parser.parse_args()


def build_agent() -> SingleAgent:
    return SingleAgent(
        OllamaModelClient(model=MODEL),
        max_steps=3,
    )


def main() -> None:
    args = parse_args()

    if DESTINATION.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite {DESTINATION}. Use --force intentionally."
        )

    questions = json.loads(QUESTIONS_PATH.read_text())
    payload = run_throughput_sweep(
        agent_factory=build_agent,
        cases=questions,
        concurrency_levels=DEFAULT_LEVELS,
    )
    payload["metadata"] = {
        "experiment_type": "bounded_throughput_non_evidentiary",
        "model": MODEL,
        "provider": "ollama_local",
        "dataset": "synthetic_delivery_seed_42",
        "questions": str(QUESTIONS_PATH),
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "claim_boundary": (
            "This load experiment reuses the frozen cases for validated-work "
            "measurement but is not one of the official three evidentiary runs."
        ),
    }

    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    DESTINATION.write_text(json.dumps(payload, indent=2) + "\n")

    print(json.dumps(payload["sweep_summary"], indent=2))
    print(f"Saved local throughput artifact: {DESTINATION}")


if __name__ == "__main__":
    main()
