"""Frozen local-model probe for the existing ClickHouse tool contract."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any

from src.agents.single_agent import TOOL_SPEC
from src.tools.clickhouse_readonly import QueryRejected, validate_read_only


PROBE_ID = "clickhouse-tool-contract-v1"
ATTEMPT_COUNT = 3
EXPECTED_ROW_COUNT = 500
PROBE_MESSAGES = [
    {
        "role": "system",
        "content": (
            "This is a frozen tool-contract probe. Use exactly one provided "
            "tool call and do not answer directly. You have no other tools."
        ),
    },
    {
        "role": "user",
        "content": (
            "Call query_clickhouse exactly once with one read-only SQL "
            "statement that returns count() AS row_count from "
            "agentic_analytics.delivery_work_items."
        ),
    },
]


QueryFn = Callable[[str], list[dict[str, Any]]]


def _error_text(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def evaluate_attempt(
    raw_response: Any,
    *,
    query_fn: QueryFn,
) -> dict[str, Any]:
    """Apply deterministic acceptance to one unedited model response."""

    outcome: dict[str, Any] = {
        "accepted": False,
        "reason_code": "not_tool_call",
        "raw_response": deepcopy(raw_response),
    }

    if not isinstance(raw_response, Mapping):
        return outcome
    if raw_response.get("type") != "tool_call":
        return outcome
    if raw_response.get("name") != "query_clickhouse":
        outcome["reason_code"] = "wrong_tool"
        return outcome

    arguments = raw_response.get("arguments")
    sql = arguments.get("sql") if isinstance(arguments, Mapping) else None
    if not isinstance(sql, str) or not sql.strip():
        outcome["reason_code"] = "invalid_arguments"
        return outcome

    try:
        validated_sql = validate_read_only(sql)
    except QueryRejected as exc:
        outcome["reason_code"] = "validator_rejected"
        outcome["error"] = str(exc)
        return outcome

    outcome["validated_sql"] = validated_sql
    try:
        rows = query_fn(validated_sql)
    except Exception as exc:
        outcome["reason_code"] = "execution_error"
        outcome["error"] = _error_text(exc)
        return outcome

    outcome["result_rows"] = deepcopy(rows)
    if rows != [{"row_count": EXPECTED_ROW_COUNT}]:
        outcome["reason_code"] = "unexpected_result"
        return outcome

    outcome["accepted"] = True
    outcome["reason_code"] = "accepted"
    return outcome


def run_probe(*, model: Any, query_fn: QueryFn) -> dict[str, Any]:
    """Run the three frozen attempts exactly once each, without retries."""

    attempts = []
    report_started = datetime.now(timezone.utc)

    for attempt_number in range(1, ATTEMPT_COUNT + 1):
        started = datetime.now(timezone.utc)
        monotonic_started = time.perf_counter()
        try:
            raw_response = model.respond(PROBE_MESSAGES, [TOOL_SPEC])
            outcome = evaluate_attempt(raw_response, query_fn=query_fn)
        except Exception as exc:
            outcome = {
                "accepted": False,
                "reason_code": "model_error",
                "raw_response": None,
                "error": _error_text(exc),
            }
        ended = datetime.now(timezone.utc)
        attempts.append(
            {
                "attempt_number": attempt_number,
                "started_at": started.isoformat(),
                "ended_at": ended.isoformat(),
                "elapsed_seconds": time.perf_counter() - monotonic_started,
                **outcome,
            }
        )

    accepted_attempts = sum(
        1 for attempt in attempts if attempt["accepted"]
    )
    report_ended = datetime.now(timezone.utc)
    return {
        "probe_id": PROBE_ID,
        "model": getattr(model, "model", None),
        "attempt_count": ATTEMPT_COUNT,
        "accepted_attempts": accepted_attempts,
        "passed": accepted_attempts == ATTEMPT_COUNT,
        "retries": 0,
        "incremental_paid_spend_usd": 0,
        "started_at": report_started.isoformat(),
        "ended_at": report_ended.isoformat(),
        "acceptance_criteria": (
            "3/3 attempts must call query_clickhouse exactly once, pass the "
            "unchanged validator, and return one row with row_count=500."
        ),
        "messages": deepcopy(PROBE_MESSAGES),
        "tool_spec": deepcopy(TOOL_SPEC),
        "attempts": attempts,
    }


def write_report(report: Mapping[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, sort_keys=True)
        handle.write("\n")
