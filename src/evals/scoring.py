"""Deterministic scoring for the frozen single-agent evaluation set."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoreResult:
    correct: bool
    factual_consistency: bool | None
    tool_grounded: bool | None
    evidence_quality: str
    unsupported_claims: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _has_text(answer: str, value: str) -> bool:
    return value.casefold() in answer.casefold()


def _has_number(answer: str, value: float | int) -> bool:
    target = float(value)
    for match in re.finditer(r"(?<![\w.])-?\d+(?:\.\d+)?", answer):
        try:
            observed = float(match.group(0))
        except ValueError:
            continue
        if abs(observed - target) <= 0.011:
            return True
    return False


def _row_contains_values(row: dict[str, Any], values: list[Any]) -> bool:
    serialized = json.dumps(row, sort_keys=True).casefold()
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, str):
            if value.casefold() not in serialized:
                return False
        elif isinstance(value, (int, float)):
            numeric_values = [
                float(match.group(0))
                for match in re.finditer(r"-?\d+(?:\.\d+)?", serialized)
            ]
            if not any(abs(candidate - float(value)) <= 0.011 for candidate in numeric_values):
                return False
    return True


def _tool_rows(tool_calls: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in tool_calls:
        for row in getattr(call, "result_rows", []) or []:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _expected_values(expected: dict[str, Any]) -> list[Any]:
    return [value for key, value in expected.items() if key != "answer"]


def _score_expected_answer(case: dict[str, Any], answer: str) -> bool:
    expected = case["expected"]
    question_id = case["id"]

    if question_id == "Q4":
        ranking = expected["ranking"]
        team_positions = []
        for team, pct in ranking:
            match = re.search(rf"\b{re.escape(team)}\b", answer, re.IGNORECASE)
            if not match or not _has_number(answer, pct):
                return False
            team_positions.append(match.start())
        return team_positions == sorted(team_positions)

    values = _expected_values(expected)
    for value in values:
        if isinstance(value, str) and not _has_text(answer, value):
            return False
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if not _has_number(answer, value):
                return False

    if expected.get("answer") is True:
        lowered = answer.casefold()
        affirmative = bool(
            re.search(r"\b(yes|same team|also the team|it is)\b", lowered)
        )
        contradiction = bool(re.search(r"\b(no|not the same|false)\b", lowered))
        if not affirmative or contradiction:
            return False

    return True


def _score_epistemic(answer: str) -> bool:
    lowered = answer.casefold()

    rejects_causality = any(
        phrase in lowered
        for phrase in (
            "cannot establish",
            "can't establish",
            "does not establish",
            "cannot conclude",
            "can't conclude",
            "cannot determine causality",
            "does not prove",
        )
    )
    distinguishes = (
        ("association" in lowered or "correlation" in lowered)
        and ("caus" in lowered)
    )
    requests_stronger_design = any(
        term in lowered
        for term in (
            "experiment",
            "randomized",
            "randomised",
            "longitudinal",
            "confound",
            "control group",
            "additional evidence",
            "stronger study design",
            "counterfactual",
        )
    )

    return rejects_causality and distinguishes and requests_stronger_design


def _evidence_matches(case: dict[str, Any], rows: list[dict[str, Any]]) -> bool:
    expected = case.get("expected")
    if not expected:
        return True

    if case["id"] == "Q4":
        return all(
            any(_row_contains_values(row, [team, pct]) for row in rows)
            for team, pct in expected["ranking"]
        )

    values = _expected_values(expected)
    return any(_row_contains_values(row, values) for row in rows)


def score_case(
    case: dict[str, Any],
    answer: str,
    tool_calls: list[Any],
) -> ScoreResult:
    """Score a completed run without using an LLM judge."""

    requires_tool = bool(case.get("requires_tool", "expected" in case))
    rows = _tool_rows(tool_calls)

    if "expected" in case:
        correct = _score_expected_answer(case, answer)
    else:
        correct = _score_epistemic(answer)

    if requires_tool:
        tool_grounded = bool(tool_calls)
        factual_consistency = bool(rows) and _evidence_matches(case, rows)
    else:
        tool_grounded = None
        factual_consistency = None

    unsupported_claims: list[str] = []
    notes: list[str] = []

    if requires_tool and not tool_grounded:
        unsupported_claims.append("Dataset claim was not grounded in a tool call.")
    elif requires_tool and not factual_consistency:
        unsupported_claims.append(
            "Required answer values were not found together in captured tool evidence."
        )

    if not requires_tool:
        evidence_quality = "epistemic_no_tool_required"
    elif factual_consistency and len(tool_calls) == 1:
        evidence_quality = "grounded_single_query"
    elif factual_consistency:
        evidence_quality = "grounded_multiple_queries"
        notes.append("Answer is grounded, but used more than one database query.")
    else:
        evidence_quality = "ungrounded_or_inconsistent"

    return ScoreResult(
        correct=correct,
        factual_consistency=factual_consistency,
        tool_grounded=tool_grounded,
        evidence_quality=evidence_quality,
        unsupported_claims=unsupported_claims,
        notes=notes,
    )
