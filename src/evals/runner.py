"""Evaluation runner for Agentic Analytics Lab."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol


class AgentLike(Protocol):
    def run(self, question: str) -> Any:
        ...


@dataclass
class EvalRecord:
    question_id: str
    category: str
    question: str
    answer: str | None
    success: bool
    tool_call_count: int
    latency_seconds: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    model_cost_usd: float | None = None
    error: str | None = None


def load_questions(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text())


def run_case(agent: AgentLike, case: dict[str, Any]) -> EvalRecord:
    started = time.perf_counter()

    try:
        result = agent.run(case["question"])
        latency = time.perf_counter() - started

        return EvalRecord(
            question_id=case["id"],
            category=case["category"],
            question=case["question"],
            answer=result.answer,
            success=True,
            tool_call_count=len(result.tool_calls),
            latency_seconds=round(latency, 6),
        )

    except Exception as exc:
        latency = time.perf_counter() - started

        return EvalRecord(
            question_id=case["id"],
            category=case["category"],
            question=case["question"],
            answer=None,
            success=False,
            tool_call_count=0,
            latency_seconds=round(latency, 6),
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
            "successful": sum(r.success for r in records),
            "failed": sum(not r.success for r in records),
            "total_tool_calls": sum(r.tool_call_count for r in records),
            "total_latency_seconds": round(
                sum(r.latency_seconds for r in records), 6
            ),
        },
        "results": [asdict(record) for record in records],
    }

    path.write_text(json.dumps(payload, indent=2) + "\n")
