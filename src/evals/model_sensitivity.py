"""Helpers for model-sensitivity experiments.

This module compares repeated runs per model without changing the frozen
qwen2.5:7b baseline or the benchmark contract.
"""

from __future__ import annotations

import re
from typing import Any

from src.evals.repeatability import summarize_repeatability


def safe_model_slug(model: str) -> str:
    value = model.strip()
    if not value:
        raise ValueError("model must be a non-empty string.")
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return slug.strip("._-") or "model"


def summarize_model_groups(
    model_payloads: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if not model_payloads:
        raise ValueError("At least one model group is required.")

    models: dict[str, Any] = {}
    for model, payloads in model_payloads.items():
        summary = summarize_repeatability(payloads)
        models[model] = {
            "run_count": summary["run_count"],
            "aggregate": summary["aggregate"],
            "per_case": summary["per_case"],
        }

    return {
        "models": models,
        "claim_boundary": (
            "Descriptive model-sensitivity study only. qwen2.5:7b remains the "
            "frozen architecture-comparison anchor unless a separate benchmark "
            "version change is explicitly approved."
        ),
    }
