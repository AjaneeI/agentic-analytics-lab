"""Deterministic failure-stage diagnostics for benchmark artifacts.

This module classifies only observable execution evidence. It never infers
private chain-of-thought and does not introduce an LLM judge.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

from src.tools.clickhouse_readonly import QueryRejected, validate_read_only


DIAGNOSTICS_VERSION = "1"
STAGES = (
    "preflight",
    "routing",
    "tool_selection",
    "query_validation",
    "query_execution",
    "evidence_coverage",
    "answer_synthesis",
    "validation",
)


@dataclass(frozen=True)
class StageOutcome:
    state: str
    reason_code: str | None = None
    detail: str | None = None

    def __post_init__(self) -> None:
        if self.state not in {
            "passed",
            "failed",
            "not_reached",
            "not_applicable",
            "unknown",
        }:
            raise ValueError(f"Unsupported diagnostic state: {self.state}")


@dataclass(frozen=True)
class DiagnosticRecord:
    diagnostics_version: str
    question_id: str
    stage_outcomes: dict[str, StageOutcome]
    primary_failure_stage: str
    primary_reason_code: str | None
    diagnosis_complete: bool
    observable_evidence: dict[str, Any]
    limitations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tool_evidence(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = record.get("tool_evidence") or []
    return [item for item in raw if isinstance(item, dict)]


def _tool_names(record: Mapping[str, Any]) -> list[str]:
    return [
        str(item.get("name"))
        for item in _tool_evidence(record)
        if item.get("name") is not None
    ]


def _query_clickhouse_evidence(
    record: Mapping[str, Any],
) -> list[dict[str, Any]]:
    return [
        item
        for item in _tool_evidence(record)
        if item.get("name") == "query_clickhouse"
    ]


def _error_text(record: Mapping[str, Any]) -> str:
    return str(record.get("error") or "")


def _attempt_count(record: Mapping[str, Any]) -> int:
    value = record.get("tool_call_attempt_count", 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _stage(
    state: str,
    reason_code: str | None = None,
    detail: str | None = None,
) -> StageOutcome:
    return StageOutcome(
        state=state,
        reason_code=reason_code,
        detail=detail,
    )


def _query_validation_outcome(
    record: Mapping[str, Any],
    requires_tool: bool,
    tool_selection: StageOutcome,
) -> StageOutcome:
    if not requires_tool:
        return _stage("not_applicable", detail="No database tool is required.")

    if tool_selection.state == "failed":
        return _stage("not_reached", detail="Required tool was not selected.")

    evidence = _query_clickhouse_evidence(record)
    error = _error_text(record)

    if not evidence:
        if "QueryRejected" in error:
            return _stage(
                "failed",
                "query_rejected",
                "The read-only SQL validator rejected the attempted query.",
            )
        if "ClickHouse query failed" in error:
            return _stage(
                "passed",
                detail=(
                    "Execution reached ClickHouse, so the existing read-only "
                    "validator had already accepted the query."
                ),
            )
        return _stage(
            "unknown",
            detail="Attempted SQL was not serialized in this artifact.",
        )

    for call in evidence:
        arguments = call.get("arguments") or {}
        sql = arguments.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            return _stage(
                "unknown",
                "insufficient_artifact_evidence",
                "Executed tool evidence does not include a non-empty SQL string.",
            )
        try:
            validate_read_only(sql)
        except QueryRejected as exc:
            return _stage("failed", "query_rejected", str(exc))

    return _stage(
        "passed",
        detail="Captured SQL passes the existing read-only validator.",
    )


def _query_execution_outcome(
    record: Mapping[str, Any],
    requires_tool: bool,
    query_validation: StageOutcome,
) -> StageOutcome:
    if not requires_tool:
        return _stage("not_applicable", detail="No database execution is required.")

    if query_validation.state == "failed":
        return _stage("not_reached", detail="Query validation failed first.")
    if query_validation.state == "not_reached":
        return _stage("not_reached", detail="Query execution was never reached.")

    if _query_clickhouse_evidence(record):
        return _stage(
            "passed",
            detail="Captured query_clickhouse evidence proves execution returned.",
        )

    error = _error_text(record)
    if "ClickHouse query failed" in error:
        return _stage("failed", "query_execution_error", error)

    if _attempt_count(record) > 0 and record.get("execution_success") is False:
        return _stage(
            "failed",
            "query_execution_error",
            error or "A tool call was attempted but did not return evidence.",
        )

    return _stage(
        "unknown",
        detail="This artifact does not preserve enough execution evidence.",
    )


def _numeric_matches(observed: float, target: float) -> bool:
    if abs(observed - target) <= 0.2:
        return True
    if abs(target) > 1 and -1 <= observed <= 1:
        return abs((observed * 100) - target) <= 0.2
    return False


def _row_matches_value(row: Mapping[str, Any], value: Any) -> bool:
    import json
    import re

    serialized = json.dumps(row, sort_keys=True).casefold()
    if isinstance(value, bool):
        return True
    if isinstance(value, str):
        return value.casefold() in serialized
    if isinstance(value, (int, float)):
        candidates = [
            float(match.group(0))
            for match in re.finditer(r"-?\d+(?:\.\d+)?", serialized)
        ]
        return any(_numeric_matches(candidate, float(value)) for candidate in candidates)
    return False


def _captured_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for call in _query_clickhouse_evidence(record):
        for row in call.get("result_rows") or []:
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _expected_evidence_is_captured(
    record: Mapping[str, Any],
    case: Mapping[str, Any],
) -> bool | None:
    expected = case.get("expected")
    if not isinstance(expected, Mapping):
        return None

    rows = _captured_rows(record)
    if not rows:
        return False

    if case.get("id") == "Q4":
        ranking = expected.get("ranking")
        if not isinstance(ranking, list):
            return None
        return all(
            any(
                _row_matches_value(row, team) and _row_matches_value(row, pct)
                for row in rows
            )
            for team, pct in ranking
        )

    values = [
        value
        for key, value in expected.items()
        if key != "answer" and not isinstance(value, bool)
    ]

    anchor = expected.get("team")
    if isinstance(anchor, str):
        anchored_rows = [row for row in rows if _row_matches_value(row, anchor)]
        if not anchored_rows:
            return False
        return all(
            any(_row_matches_value(row, value) for row in anchored_rows)
            for value in values
        )

    return all(
        any(_row_matches_value(row, value) for row in rows)
        for value in values
    )


def _evidence_coverage_outcome(
    record: Mapping[str, Any],
    case: Mapping[str, Any],
    requires_tool: bool,
    query_execution: StageOutcome,
) -> StageOutcome:
    if not requires_tool:
        return _stage(
            "not_applicable",
            detail="The epistemic case does not require dataset evidence.",
        )

    if query_execution.state == "failed":
        return _stage("not_reached", detail="Query execution failed first.")
    if query_execution.state == "not_reached":
        return _stage("not_reached", detail="Query execution was not reached.")
    if query_execution.state == "unknown":
        return _stage(
            "unknown",
            detail="Evidence coverage cannot be assessed without execution evidence.",
        )

    captured = _expected_evidence_is_captured(record, case)
    if captured is True:
        if record.get("factual_consistency") is False:
            return _stage(
                "passed",
                detail=(
                    "Captured rows contain the frozen expected evidence across "
                    "the executed tool results even though the legacy scorer's "
                    "row-co-location check reported factual_consistency=false."
                ),
            )
        return _stage(
            "passed",
            detail="Captured rows contain the frozen expected evidence.",
        )
    if captured is False:
        return _stage(
            "failed",
            "required_rows_missing",
            "Captured tool rows do not contain the frozen expected evidence.",
        )

    factual_consistency = record.get("factual_consistency")
    if factual_consistency is True:
        return _stage(
            "passed",
            detail="Legacy deterministic factual-consistency evidence passed.",
        )
    if factual_consistency is False:
        return _stage(
            "failed",
            "required_rows_missing",
            "Required answer values were not found in captured tool evidence.",
        )
    return _stage(
        "unknown",
        detail="The artifact does not contain enough evidence for coverage analysis.",
    )


def _answer_synthesis_outcome(
    record: Mapping[str, Any],
    requires_tool: bool,
    evidence_coverage: StageOutcome,
) -> StageOutcome:
    if requires_tool:
        if evidence_coverage.state == "failed":
            return _stage(
                "not_reached",
                detail=(
                    "Incomplete evidence prevents attribution to final answer "
                    "synthesis."
                ),
            )
        if evidence_coverage.state == "not_reached":
            return _stage(
                "not_reached",
                detail="Required evidence was never available.",
            )
        if evidence_coverage.state == "unknown":
            return _stage(
                "unknown",
                detail=(
                    "Artifact evidence is insufficient to separate retrieval "
                    "from answer synthesis."
                ),
            )

    correct = record.get("correct")
    if correct is True:
        return _stage(
            "passed",
            detail="The final answer matches the deterministic expected result.",
        )
    if correct is False:
        return _stage(
            "failed",
            "answer_value_incorrect",
            "The final answer does not match the deterministic expected result.",
        )
    return _stage(
        "unknown",
        detail="The artifact does not contain a deterministic correctness result.",
    )


def diagnose_record(
    record: Mapping[str, Any],
    case: Mapping[str, Any],
) -> DiagnosticRecord:
    """Classify one saved benchmark record from observable evidence only."""

    question_id = str(record.get("question_id") or case.get("id") or "")
    if not question_id:
        raise ValueError("A diagnostic record requires a question id.")

    requires_tool = bool(case.get("requires_tool", "expected" in case))
    limitations: list[str] = []

    outcomes: dict[str, StageOutcome] = {}
    outcomes["preflight"] = _stage(
        "unknown",
        detail="Frozen benchmark JSON does not independently record preflight state.",
    )
    limitations.append("preflight_not_independently_recorded")

    outcomes["routing"] = _stage(
        "not_applicable",
        detail=(
            "Routing is outside the frozen single-agent record. Routed-system "
            "telemetry should be analyzed separately."
        ),
    )

    names = _tool_names(record)
    attempts = _attempt_count(record)

    if requires_tool:
        if "query_clickhouse" in names or attempts > 0:
            outcomes["tool_selection"] = _stage(
                "passed",
                detail="The required query_clickhouse path was invoked or attempted.",
            )
        elif names:
            outcomes["tool_selection"] = _stage(
                "failed",
                "unexpected_tool",
                f"Observed tools: {', '.join(names)}",
            )
        else:
            outcomes["tool_selection"] = _stage(
                "failed",
                "tool_not_called",
                "The case required query_clickhouse but no tool attempt was recorded.",
            )
    else:
        if names or attempts > 0:
            outcomes["tool_selection"] = _stage(
                "failed",
                "unexpected_tool",
                "The case does not require a database tool.",
            )
        else:
            outcomes["tool_selection"] = _stage(
                "passed",
                detail="No tool was required and none was called.",
            )

    outcomes["query_validation"] = _query_validation_outcome(
        record,
        requires_tool,
        outcomes["tool_selection"],
    )
    outcomes["query_execution"] = _query_execution_outcome(
        record,
        requires_tool,
        outcomes["query_validation"],
    )
    outcomes["evidence_coverage"] = _evidence_coverage_outcome(
        record,
        case,
        requires_tool,
        outcomes["query_execution"],
    )
    outcomes["answer_synthesis"] = _answer_synthesis_outcome(
        record,
        requires_tool,
        outcomes["evidence_coverage"],
    )

    first_failed = next(
        (stage for stage in STAGES[:-1] if outcomes[stage].state == "failed"),
        None,
    )

    if first_failed is not None:
        outcomes["validation"] = _stage(
            "not_reached",
            detail=(
                "A prior observable stage already failed; validation is not "
                "used as a second failure attribution."
            ),
        )
    elif any(
        outcomes[stage].state == "unknown"
        for stage in (
            "tool_selection",
            "query_validation",
            "query_execution",
            "evidence_coverage",
            "answer_synthesis",
        )
        if outcomes[stage].state != "not_applicable"
    ):
        outcomes["validation"] = _stage(
            "unknown",
            detail="Upstream artifact evidence is incomplete.",
        )
    elif record.get("task_success") is True:
        outcomes["validation"] = _stage(
            "passed",
            detail="Existing deterministic task-success gate passed.",
        )
    elif record.get("task_success") is False:
        outcomes["validation"] = _stage(
            "failed",
            "validator_rejected",
            "No earlier stage failed, but the deterministic task-success gate did.",
        )
    else:
        outcomes["validation"] = _stage(
            "unknown",
            detail="The artifact does not contain task_success.",
        )

    first_failed = next(
        (stage for stage in STAGES if outcomes[stage].state == "failed"),
        None,
    )

    if first_failed is None and record.get("task_success") is True:
        primary_failure_stage = "none"
        primary_reason_code = None
        diagnosis_complete = True
    elif first_failed is not None:
        primary_failure_stage = first_failed
        primary_reason_code = outcomes[first_failed].reason_code
        diagnosis_complete = True
    else:
        primary_failure_stage = "unknown"
        primary_reason_code = "insufficient_artifact_evidence"
        diagnosis_complete = False
        limitations.append("primary_failure_stage_not_determinable")

    return DiagnosticRecord(
        diagnostics_version=DIAGNOSTICS_VERSION,
        question_id=question_id,
        stage_outcomes=outcomes,
        primary_failure_stage=primary_failure_stage,
        primary_reason_code=primary_reason_code,
        diagnosis_complete=diagnosis_complete,
        observable_evidence={
            "execution_success": record.get("execution_success"),
            "correct": record.get("correct"),
            "task_success": record.get("task_success"),
            "factual_consistency": record.get("factual_consistency"),
            "tool_grounded": record.get("tool_grounded"),
            "tool_names": names,
            "tool_call_count": record.get("tool_call_count", len(names)),
            "tool_call_attempt_count": attempts,
            "failure_type": record.get("failure_type"),
            "error": record.get("error"),
            "unsupported_claims": list(record.get("unsupported_claims") or []),
        },
        limitations=tuple(limitations),
    )


def diagnose_payload(
    payload: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    questions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Diagnose every record in an existing benchmark JSON payload."""

    if isinstance(payload, Mapping):
        raw_results = payload.get("results")
        if not isinstance(raw_results, list):
            raise ValueError("Benchmark payload must contain a results list.")
        source_summary = payload.get("summary")
    else:
        raw_results = list(payload)
        source_summary = None

    cases = {str(case.get("id")): case for case in questions}
    if not cases:
        raise ValueError("Question set must not be empty.")

    diagnostics: list[dict[str, Any]] = []
    counts: dict[str, int] = {}

    for raw in raw_results:
        if not isinstance(raw, Mapping):
            raise ValueError("Every benchmark result must be a JSON object.")
        question_id = str(raw.get("question_id") or "")
        case = cases.get(question_id)
        if case is None:
            raise ValueError(
                f"No frozen question definition found for {question_id!r}."
            )

        diagnosed = diagnose_record(raw, case).to_dict()
        diagnostics.append(diagnosed)
        stage = diagnosed["primary_failure_stage"]
        counts[stage] = counts.get(stage, 0) + 1

    return {
        "diagnostics_version": DIAGNOSTICS_VERSION,
        "source_summary": source_summary,
        "summary": {
            "records": len(diagnostics),
            "primary_failure_stage_counts": counts,
            "complete_diagnoses": sum(
                bool(item["diagnosis_complete"]) for item in diagnostics
            ),
        },
        "results": diagnostics,
    }
