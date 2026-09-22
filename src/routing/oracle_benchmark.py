"""Benchmark-only oracle-metadata adapter for routed execution.

This adapter isolates execution-layer value. It uses frozen benchmark
category/requires_tool metadata to choose a deterministic handler or the existing
local worker. It does not infer routes from natural language and must not be
reported as an end-to-end classifier.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from src.agents.single_agent import AgentResult, RunMetrics
from src.routing.control_plane import TaskContext
from src.routing.deterministic_handlers import HandlerKey, QueryFn
from src.routing.executor import ExecutionRequest, execute_control_plane_request
from src.routing.telemetry import RouteTelemetry


_CATEGORY_HANDLER: dict[str, HandlerKey] = {
    "retrieval": HandlerKey.BLOCKER_RATE_LEADER,
    "comparison": HandlerKey.EFFORT_RATIO_LEADER,
    "reasoning": HandlerKey.BLOCKER_COUNT_RATE_CONSISTENCY,
    "ranking": HandlerKey.BLOCKER_RATE_RANKING,
    "multi_metric": HandlerKey.DUAL_METRIC_LEADER,
}


@dataclass(frozen=True)
class OracleCaseSpec:
    task_id: str
    question: str
    category: str
    requires_tool: bool
    deterministic_handler: HandlerKey | None


def build_oracle_case_specs(
    questions: Iterable[dict[str, Any]],
) -> dict[str, OracleCaseSpec]:
    """Build question-keyed specs using routing metadata only.

    Ground-truth answer fields are deliberately not read here so answer
    correctness cannot influence route selection.
    """

    specs: dict[str, OracleCaseSpec] = {}

    for case in questions:
        task_id = _required_string(case, "id")
        question = _required_string(case, "question")
        category = _required_string(case, "category")
        requires_tool = _required_bool(case, "requires_tool")

        if question in specs:
            raise ValueError("Frozen benchmark questions must be unique.")

        specs[question] = OracleCaseSpec(
            task_id=task_id,
            question=question,
            category=category,
            requires_tool=requires_tool,
            deterministic_handler=_CATEGORY_HANDLER.get(category),
        )

    if not specs:
        raise ValueError("At least one benchmark case is required.")

    return specs


class OracleMetadataRoutedAgent:
    """AgentLike adapter for the frozen oracle-metadata routed experiment."""

    def __init__(
        self,
        *,
        questions: Iterable[dict[str, Any]],
        local_worker: Any,
        query_fn: QueryFn | None = None,
    ):
        self.specs = build_oracle_case_specs(questions)
        self.local_worker = local_worker
        self.query_fn = query_fn
        self.last_run_metrics = RunMetrics()
        self.last_route_telemetry: RouteTelemetry | None = None
        self.route_telemetry_by_task: dict[str, RouteTelemetry] = {}

    def run(self, question: str) -> AgentResult:
        spec = self.specs.get(question)
        if spec is None:
            raise RuntimeError(
                "Question is not present in the frozen oracle routing metadata."
            )

        handler = spec.deterministic_handler
        request = ExecutionRequest(
            task_id=spec.task_id,
            question=question,
            context=TaskContext(
                task_type=spec.category,
                requires_tool=spec.requires_tool,
                evidence_required=spec.requires_tool,
                deterministic_handler_available=handler is not None,
            ),
            deterministic_handler=handler,
        )

        outcome = execute_control_plane_request(
            request,
            local_worker=self.local_worker,
            query_fn=self.query_fn,
            router_version="oracle-metadata-rules-v0",
        )

        self.last_route_telemetry = outcome.telemetry
        self.route_telemetry_by_task[spec.task_id] = outcome.telemetry
        self.last_run_metrics = RunMetrics(
            model_call_count=outcome.telemetry.total_model_calls,
            input_tokens=outcome.telemetry.worker_input_tokens,
            output_tokens=outcome.telemetry.worker_output_tokens,
        )

        if outcome.result is None:
            reason = outcome.telemetry.escalation_reason or "NO_RESULT"
            raise RuntimeError(
                f"Oracle routed execution produced no result: {reason}"
            )

        return outcome.result


def _required_string(case: dict[str, Any], key: str) -> str:
    value = case.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string.")
    return value.strip()


def _required_bool(case: dict[str, Any], key: str) -> bool:
    value = case.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"{key} must be a boolean.")
    return value
