"""Reference-solution loading for System Benchmark v1 development fixtures."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from src.evals.system_benchmark.contracts import (
    ResponseDisposition,
    SystemBenchmarkResponse,
    SystemBenchmarkTask,
)


@dataclass(frozen=True)
class ReferenceSolution:
    reference_id: str
    case_id: str
    response: SystemBenchmarkResponse
    observed_tools: tuple[str, ...]
    observed_values: dict[str, Any]
    validator_passed: bool


def load_reference_solutions(
    path: str | Path,
    tasks: list[SystemBenchmarkTask],
) -> dict[str, ReferenceSolution]:
    """Load references and require exactly one matching solution per task."""

    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError("reference solutions must be a non-empty list")

    task_by_case = {task.case_id: task for task in tasks}
    solutions: dict[str, ReferenceSolution] = {}
    seen_reference_ids: set[str] = set()

    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"reference solution {index} must be an object")
        reference_id = _required_string(item, "id")
        case_id = _required_string(item, "case_id")
        if case_id in solutions:
            raise ValueError(f"duplicate reference case: {case_id}")
        if reference_id in seen_reference_ids:
            raise ValueError(f"duplicate reference id: {reference_id}")
        seen_reference_ids.add(reference_id)

        task = task_by_case.get(case_id)
        if task is None:
            raise ValueError(f"reference solution has no matching task: {case_id}")
        if task.reference_solution_id != reference_id:
            raise ValueError(
                f"reference id mismatch for {case_id}: "
                f"task={task.reference_solution_id}, reference={reference_id}"
            )

        response = _parse_response(item.get("response"), case_id)
        observed_tools = _string_tuple(item, "observed_tools")
        observed_values_raw = item.get("observed_values")
        if not isinstance(observed_values_raw, Mapping):
            raise ValueError(f"reference {case_id} observed_values must be an object")
        observed_values = dict(observed_values_raw)
        validator_passed = item.get("validator_passed")
        if not isinstance(validator_passed, bool):
            raise ValueError(f"reference {case_id} validator_passed must be boolean")

        solutions[case_id] = ReferenceSolution(
            reference_id=reference_id,
            case_id=case_id,
            response=response,
            observed_tools=observed_tools,
            observed_values=observed_values,
            validator_passed=validator_passed,
        )

    expected_cases = set(task_by_case)
    actual_cases = set(solutions)
    if actual_cases != expected_cases:
        missing = sorted(expected_cases - actual_cases)
        extra = sorted(actual_cases - expected_cases)
        raise ValueError(f"reference/task coverage mismatch: missing={missing}, extra={extra}")
    return solutions


def _parse_response(raw: Any, case_id: str) -> SystemBenchmarkResponse:
    if not isinstance(raw, Mapping):
        raise ValueError(f"reference {case_id} response must be an object")
    disposition_text = _required_string(raw, "disposition")
    try:
        disposition = ResponseDisposition(disposition_text)
    except ValueError as exc:
        raise ValueError(
            f"reference {case_id} has invalid disposition: {disposition_text!r}"
        ) from exc
    answer_text = raw.get("answer_text")
    if not isinstance(answer_text, str):
        raise ValueError(f"reference {case_id} answer_text must be a string")
    evidence_refs = _string_tuple(raw, "evidence_refs")
    uncertainty = raw.get("uncertainty")
    if uncertainty is not None and not isinstance(uncertainty, str):
        raise ValueError(f"reference {case_id} uncertainty must be string or null")
    clarification = raw.get("clarification")
    if clarification is not None and not isinstance(clarification, dict):
        raise ValueError(f"reference {case_id} clarification must be object or null")
    handoff = raw.get("handoff")
    if handoff is not None and not isinstance(handoff, dict):
        raise ValueError(f"reference {case_id} handoff must be object or null")
    return SystemBenchmarkResponse(
        disposition=disposition,
        answer_text=answer_text,
        evidence_refs=evidence_refs,
        uncertainty=uncertainty,
        clarification=clarification,
        handoff=handoff,
    )


def _required_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def _string_tuple(payload: Mapping[str, Any], key: str) -> tuple[str, ...]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{key} must contain non-empty strings")
        result.append(item.strip())
    return tuple(result)
