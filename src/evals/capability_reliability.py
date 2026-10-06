"""Deterministic evaluators for the M0.5 capability reliability studies."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from typing import Any

from src.tools.clickhouse_readonly import QueryRejected, validate_read_only


QueryFn = Callable[[str], list[dict[str, Any]]]


def _error_text(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"


def evaluate_sql_attempt(
    raw_response: Any,
    *,
    expected_rows: list[dict[str, Any]],
    query_fn: QueryFn,
) -> dict[str, Any]:
    """Evaluate one unedited Qwen response against the existing SQL contract."""

    outcome: dict[str, Any] = {
        "accepted": False,
        "reason_code": "not_tool_call",
        "failure_categories": ["model_instruction_following"],
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
        outcome.update(
            reason_code="validator_rejected",
            failure_categories=["tool_contract_understanding"],
            error=str(exc),
        )
        return outcome

    outcome["validated_sql"] = validated_sql
    try:
        rows = query_fn(validated_sql)
    except Exception as exc:
        outcome.update(
            reason_code="execution_error",
            failure_categories=["infrastructure_runtime"],
            error=_error_text(exc),
        )
        return outcome

    outcome["result_rows"] = deepcopy(rows)
    if rows != expected_rows:
        outcome["reason_code"] = "unexpected_result"
        return outcome

    outcome.update(
        accepted=True,
        reason_code="accepted",
        failure_categories=[],
    )
    return outcome


def build_delegation_prompt(case: Mapping[str, Any]) -> str:
    """Build the frozen Hermes parent prompt for one Study B case."""

    return (
        "This is frozen M0.5 Study B. Call delegate_task exactly once with "
        "exactly one task. Do not call any other tool. Do not perform the "
        "child task in the parent. Do not provide output_schema. Do not retry. "
        "Give the child this complete goal verbatim:\n\n"
        f"{case['child_goal']}\n\n"
        "After the child returns, output exactly this marker and nothing else: "
        f"{case['expected_marker']}"
    )


def evaluate_delegation_attempt(
    events: Sequence[Mapping[str, Any]],
    *,
    stdout: str,
    returncode: int,
    expected_marker: str,
) -> dict[str, Any]:
    """Evaluate observable one-request/one-child Hermes behavior."""

    delegate_pre = [
        event
        for event in events
        if event.get("event") == "delegate_pre"
        and event.get("tool") == "delegate_task"
    ]
    delegate_post = [
        event
        for event in events
        if event.get("event") == "delegate_post"
        and event.get("tool") == "delegate_task"
    ]
    successful_pre = [event for event in delegate_pre if event.get("ok") is True]
    successful_post = [event for event in delegate_post if event.get("ok") is True]
    parent_work = [
        event
        for event in events
        if event.get("tool") in {"query_clickhouse", "retrieve_policy"}
        and event.get("delegated_child") is False
    ]
    interventions = [event for event in events if event.get("ok") is False]
    final_completion = returncode == 0 and stdout.strip() == expected_marker

    accepted = (
        len(delegate_pre) == 1
        and len(successful_pre) == 1
        and len(successful_post) == 1
        and len(parent_work) == 0
        and len(interventions) == 0
        and final_completion
    )

    categories: list[str] = []
    orchestration_failure = (
        len(delegate_pre) != 1
        or len(successful_pre) != 1
        or len(successful_post) != 1
        or bool(parent_work)
    )
    if orchestration_failure:
        categories.append("orchestration_decomposition")
    if interventions:
        categories.append("enforcement_intervention")
    if returncode != 0:
        categories.append("infrastructure_runtime")
    if not final_completion and returncode == 0 and not orchestration_failure:
        categories.append("model_instruction_following")

    if accepted:
        reason_code = "accepted"
    elif returncode != 0:
        reason_code = "process_error"
    elif orchestration_failure:
        reason_code = "delegation_contract_failed"
    elif interventions:
        reason_code = "enforcement_intervened"
    else:
        reason_code = "final_output_mismatch"

    return {
        "accepted": accepted,
        "reason_code": reason_code,
        "failure_categories": categories,
        "attempted_delegations": len(delegate_pre),
        "successful_delegate_requests": len(successful_pre),
        "successful_worker_launches": len(successful_post),
        "attempted_extra_delegations": max(0, len(delegate_pre) - 1),
        "parent_level_work_attempts": len(parent_work),
        "enforcement_interventions": len(interventions),
        "final_completion": final_completion,
        "returncode": returncode,
        "observed_stdout": stdout,
    }


def summarize_studies(
    *,
    study_a: Sequence[Mapping[str, Any]],
    study_b: Sequence[Mapping[str, Any]],
    threshold_a: int,
    threshold_b: int,
) -> dict[str, Any]:
    """Apply preregistered thresholds and return the next decision."""

    accepted_a = sum(item.get("accepted") is True for item in study_a)
    accepted_b = sum(item.get("accepted") is True for item in study_b)
    passed_a = accepted_a >= threshold_a
    passed_b = accepted_b >= threshold_b
    categories = sorted(
        {
            str(category)
            for item in [*study_a, *study_b]
            for category in item.get("failure_categories", [])
        }
    )
    both_passed = passed_a and passed_b
    return {
        "study_a": {
            "accepted": accepted_a,
            "sample_size": len(study_a),
            "threshold": threshold_a,
            "passed": passed_a,
        },
        "study_b": {
            "accepted": accepted_b,
            "sample_size": len(study_b),
            "threshold": threshold_b,
            "passed": passed_b,
        },
        "observed_failure_categories": categories,
        "decision": (
            "recommend_m0_6_readiness" if both_passed else "define_next_experiment"
        ),
        "rerun_authorized": False,
        "incremental_paid_spend_usd": 0,
        "interpretation_boundary": (
            "These seven frozen cases characterize only the tested SQL shapes "
            "and delegation requests; they do not establish general reliability."
        ),
    }
