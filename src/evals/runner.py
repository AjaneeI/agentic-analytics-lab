"""Evaluation runner for Agentic Analytics Lab."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from src.evals.scoring import score_case


class AgentLike(Protocol):
    def run(self, question: str) -> Any:
        ...


@dataclass
class EvalRecord:
    question_id: str
    category: str
    question: str
    expected: Any
    answer: str | None
    execution_success: bool
    correct: bool | None
    task_success: bool
    factual_consistency: bool | None
    tool_grounded: bool | None
    evidence_quality: str | None
    unsupported_claims: list[str] = field(default_factory=list)
    tool_evidence: list[dict[str, Any]] = field(default_factory=list)
    tool_call_count: int = 0
    tool_call_attempt_count: int = 0
    repeated_tool_calls: int = 0
    extra_tool_calls: int = 0
    model_call_count: int = 0
    latency_seconds: float = 0.0
    model_duration_seconds: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    model_cost_usd: float | None = None
    failure_type: str | None = None
    error: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Backward-compatible alias for task_success."""
        return self.task_success


def load_questions(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text())


def _expected_for_record(case: dict[str, Any]) -> Any:
    if "expected" in case:
        return case["expected"]
    return {"expected_behavior": case.get("expected_behavior", [])}


def _repeated_tool_calls(tool_calls: list[Any]) -> int:
    sql_calls = [
        (getattr(call, "arguments", {}) or {}).get("sql", "").strip()
        for call in tool_calls
    ]
    return len(sql_calls) - len(set(sql_calls))


def _partial_metrics(agent: AgentLike) -> Any:
    return getattr(agent, "last_run_metrics", None)


def _tool_evidence(tool_calls: list[Any]) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for call in tool_calls:
        evidence.append(
            {
                "name": getattr(call, "name", None),
                "arguments": getattr(call, "arguments", {}) or {},
                "row_count": getattr(call, "row_count", 0),
                "result_rows": getattr(call, "result_rows", []) or [],
            }
        )
    return evidence


def run_case(agent: AgentLike, case: dict[str, Any]) -> EvalRecord:
    started = time.perf_counter()
    expected = _expected_for_record(case)

    try:
        result = agent.run(case["question"])
        latency = time.perf_counter() - started
        score = score_case(case, result.answer, result.tool_calls)
        max_tool_calls = int(case.get("max_tool_calls", 1))
        tool_call_count = len(result.tool_calls)
        extra_tool_calls = max(tool_call_count - max_tool_calls, 0)
        repeated_tool_calls = _repeated_tool_calls(result.tool_calls)
        task_success = bool(
            score.correct
            and score.factual_consistency is not False
            and score.tool_grounded is not False
        )

        failure_type = None
        if not score.correct:
            failure_type = "incorrect_answer"
        elif score.factual_consistency is False or score.tool_grounded is False:
            failure_type = "ungrounded_or_inconsistent_answer"

        notes = list(score.notes)
        if extra_tool_calls:
            notes.append(
                f"Used {extra_tool_calls} tool call(s) above the case limit."
            )
        if repeated_tool_calls:
            notes.append(
                f"Repeated {repeated_tool_calls} identical SQL tool call(s)."
            )

        return EvalRecord(
            question_id=case["id"],
            category=case["category"],
            question=case["question"],
            expected=expected,
            answer=result.answer,
            execution_success=True,
            correct=score.correct,
            task_success=task_success,
            factual_consistency=score.factual_consistency,
            tool_grounded=score.tool_grounded,
            evidence_quality=score.evidence_quality,
            unsupported_claims=score.unsupported_claims,
            tool_evidence=_tool_evidence(result.tool_calls),
            tool_call_count=tool_call_count,
            tool_call_attempt_count=getattr(
                result, "tool_call_attempt_count", tool_call_count
            ),
            repeated_tool_calls=repeated_tool_calls,
            extra_tool_calls=extra_tool_calls,
            model_call_count=getattr(result, "model_call_count", 0),
            latency_seconds=round(latency, 6),
            model_duration_seconds=getattr(
                result, "model_duration_seconds", None
            ),
            input_tokens=getattr(result, "input_tokens", None),
            output_tokens=getattr(result, "output_tokens", None),
            failure_type=failure_type,
            notes=notes,
        )

    except Exception as exc:
        latency = time.perf_counter() - started
        metrics = _partial_metrics(agent)

        return EvalRecord(
            question_id=case["id"],
            category=case["category"],
            question=case["question"],
            expected=expected,
            answer=None,
            execution_success=False,
            correct=None,
            task_success=False,
            factual_consistency=None,
            tool_grounded=None,
            evidence_quality=None,
            tool_call_attempt_count=getattr(
                metrics, "tool_call_attempt_count", 0
            ),
            model_call_count=getattr(metrics, "model_call_count", 0),
            latency_seconds=round(latency, 6),
            model_duration_seconds=round(
                getattr(metrics, "model_duration_seconds", 0.0), 6
            ),
            input_tokens=getattr(metrics, "input_tokens", None),
            output_tokens=getattr(metrics, "output_tokens", None),
            failure_type="execution_error",
            error=f"{type(exc).__name__}: {exc}",
        )


def run_suite(
    agent: AgentLike,
    questions_path: str | Path = "evals/questions.json",
) -> list[EvalRecord]:
    questions = load_questions(questions_path)
    return [run_case(agent, case) for case in questions]


def save_results(
    records: list[EvalRecord],
    destination: str | Path,
) -> None:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "summary": {
            "questions": len(records),
            "execution_successful": sum(r.execution_success for r in records),
            "task_successful": sum(r.task_success for r in records),
            "correct": sum(r.correct is True for r in records),
            "failed": sum(not r.task_success for r in records),
            "total_tool_calls": sum(r.tool_call_count for r in records),
            "total_model_calls": sum(r.model_call_count for r in records),
            "total_input_tokens": sum(r.input_tokens or 0 for r in records),
            "total_output_tokens": sum(r.output_tokens or 0 for r in records),
            "total_latency_seconds": round(
                sum(r.latency_seconds for r in records), 6
            ),
        },
        "results": [asdict(record) for record in records],
    }

    path.write_text(json.dumps(payload, indent=2) + "\n")
