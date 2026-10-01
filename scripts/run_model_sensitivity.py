"""Run a separate repeated model-sensitivity study.

This script never changes the project's frozen qwen2.5:7b baseline. Models must
be supplied explicitly so an expensive sweep cannot start accidentally.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent
from src.evals.benchmark_preflight import run_preflight
from src.evals.model_sensitivity import safe_model_slug, summarize_model_groups
from src.evals.runner import run_case, save_results


QUESTIONS_PATH = Path("evals/questions.json")
SUMMARY_DESTINATION = Path(
    "experiments/results/model_sensitivity_summary.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run repeated frozen-contract evaluations for explicitly selected "
            "models without replacing the qwen2.5:7b baseline."
        )
    )
    parser.add_argument(
        "--models",
        nargs="+",
        required=True,
        help="Exact local Ollama model identifiers to evaluate.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Repeat count per model (default: 3; minimum: 2).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing model-sensitivity artifacts.",
    )
    return parser.parse_args()


def _run_one_model(model: str) -> dict[str, object]:
    questions = json.loads(QUESTIONS_PATH.read_text())
    agent = SingleAgent(
        OllamaModelClient(model=model),
        max_steps=3,
    )
    records = [run_case(agent, case) for case in questions]

    return {
        "records": records,
        "metadata": {
            "benchmark_schema_version": 2,
            "architecture": "single_agent_model_sensitivity",
            "model": model,
            "provider": "ollama_local",
            "dataset": "synthetic_delivery_seed_42",
            "questions": str(QUESTIONS_PATH),
            "run_at_utc": datetime.now(timezone.utc).isoformat(),
            "claim_boundary": (
                "Model-sensitivity study only; this does not replace the "
                "frozen qwen2.5:7b baseline."
            ),
        },
    }


def main() -> None:
    args = parse_args()
    if args.runs < 2:
        raise SystemExit("--runs must be at least 2 for repeatability analysis.")

    models = list(dict.fromkeys(model.strip() for model in args.models if model.strip()))
    if not models:
        raise SystemExit("At least one non-empty model identifier is required.")

    exit_code, message = run_preflight()
    print(message)
    if exit_code:
        raise SystemExit(exit_code)

    model_payloads: dict[str, list[dict[str, object]]] = {}

    for model in models:
        slug = safe_model_slug(model)
        payloads: list[dict[str, object]] = []

        for run_index in range(1, args.runs + 1):
            destination = Path(
                f"experiments/results/model_sensitivity_{slug}_run{run_index}.json"
            )
            if destination.exists() and not args.force:
                raise SystemExit(
                    f"Refusing to overwrite {destination}. Use --force intentionally."
                )

            result = _run_one_model(model)
            save_results(result["records"], destination)
            payload = json.loads(destination.read_text())
            payload["metadata"] = result["metadata"]
            destination.write_text(json.dumps(payload, indent=2) + "\n")
            payloads.append(payload)

            print(
                f"{model} run {run_index}/{args.runs}: "
                f"task_success={payload['summary']['task_successful']}/"
                f"{payload['summary']['questions']}"
            )

        model_payloads[model] = payloads

    summary = summarize_model_groups(model_payloads)
    summary["metadata"] = {
        "experiment_type": "model_sensitivity_non_baseline",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "models": models,
        "runs_per_model": args.runs,
        "questions": str(QUESTIONS_PATH),
    }

    if SUMMARY_DESTINATION.exists() and not args.force:
        raise SystemExit(
            f"Refusing to overwrite {SUMMARY_DESTINATION}. Use --force intentionally."
        )

    SUMMARY_DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_DESTINATION.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Saved model-sensitivity summary: {SUMMARY_DESTINATION}")


if __name__ == "__main__":
    main()
