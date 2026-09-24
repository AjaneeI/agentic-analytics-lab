"""Failure-stage diagnostics derived from existing benchmark artifacts.

This module is intentionally post-hoc. It does not change benchmark prompts,
scoring, routing, or model behavior. It classifies only evidence already
captured by the deterministic evaluation runner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FailureDiagnostic:
    question_id: str
    stage: str
    reason: str
    evidence: dict[str, Any]


def diagnose_result(result: dict[str, Any]) -> FailureDiagnostic | None:
    """Classify a failed result using only observable benchmark fields."""

    if result.get("task_success") is True:
        return None

    question_id = str(result.get("question_id", "unknown"))
    execution_success = result.get("execution_success")
    tool_grounded = result.get("tool_grounded")
    factual_consistency = result.get("factual_consistency")
    correct = result.get("correct")
    attempts = int(result.get("tool_call_attempt_count", 0) or 0)
    completed_calls = int(result.get("tool_call_count", 0) or 0)

    evidence = {
        "execution_success": execution_success,
        "correct": correct,
        "tool_grounded": tool_grounded,
        "factual_consistency": factual_consistency,
        "tool_call_attempt_count": attempts,
        "tool_call_count": completed_calls,
        "failure_type": result.get("failure_type"),
        "error": result.get("error"),
    }

    if execution_success is False:
        if attempts > completed_calls:
            return FailureDiagnostic(
                question_id,
                "tool_execution",
                "A tool call was attempted but did not complete successfully.",
                evidence,
            )
        return FailureDiagnostic(
            question_id,
            "execution",
            "The agent run failed before a complete scored answer was produced.",
            evidence,
        )

    if tool_grounded is False and attempts == 0:
        return FailureDiagnostic(
            question_id,
            "tool_selection",
            "The task required dataset grounding but no tool call was attempted.",
            evidence,
        )

    if tool_grounded is False:
        return FailureDiagnostic(
            question_id,
            "tool_grounding",
            "The answer was not grounded in a completed tool call.",
            evidence,
        )

    if factual_consistency is False:
        return FailureDiagnostic(
            question_id,
            "evidence_generation",
            "Tool evidence did not contain the values required by the frozen answer contract.",
            evidence,
        )

    if correct is False and factual_consistency is True:
        return FailureDiagnostic(
            question_id,
            "answer_reasoning",
            "The required evidence was available, but the final answer did not satisfy the frozen contract.",
            evidence,
        )

    return FailureDiagnostic(
        question_id,
        "unclassified",
        "The captured fields do not support a narrower failure-stage claim.",
        evidence,
    )


def diagnose_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return reviewable diagnostics for every failed case in a benchmark payload."""

    diagnostics = [
        diagnostic
        for result in payload.get("results", [])
        if (diagnostic := diagnose_result(result)) is not None
    ]

    stage_counts: dict[str, int] = {}
    for diagnostic in diagnostics:
        stage_counts[diagnostic.stage] = stage_counts.get(diagnostic.stage, 0) + 1

    return {
        "summary": {
            "failed_cases": len(diagnostics),
            "stage_counts": stage_counts,
        },
        "diagnostics": [
            {
                "question_id": item.question_id,
                "stage": item.stage,
                "reason": item.reason,
                "evidence": item.evidence,
            }
            for item in diagnostics
        ],
    }
