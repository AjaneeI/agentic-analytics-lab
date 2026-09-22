"""Generic execution layer for the deterministic control plane."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from src.agents.single_agent import AgentResult, ToolCallRecord
from src.routing.control_plane import (
    ExecutionRoute,
    RouteDecision,
    TaskContext,
    route_task,
)
from src.routing.deterministic_handlers import (
    GROUPED_TEAM_METRICS_SQL,
    DeterministicHandlerDeclined,
    HandlerKey,
    QueryFn,
    execute_deterministic_handler,
)
from src.routing.telemetry import RouteTelemetry, build_route_telemetry
from src.routing.validation import (
    ValidationContext,
    ValidationDisposition,
    ValidationResult,
    validate_execution,
)


class WorkerLike(Protocol):
    def run(self, question: str) -> AgentResult:
        ...


class ValidatorLike(Protocol):
    def __call__(
        self,
        request: "ExecutionRequest",
        result: AgentResult,
    ) -> ValidationContext:
        ...


@dataclass(frozen=True)
class ExecutionRequest:
    task_id: str
    question: str
    context: TaskContext
    deterministic_handler: HandlerKey | None = None

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("task_id must be a non-empty string.")
        if not self.question.strip():
            raise ValueError("question must be a non-empty string.")


@dataclass(frozen=True)
class ExecutionOutcome:
    request: ExecutionRequest
    decision: RouteDecision
    result: AgentResult | None
    validation: ValidationResult | None
    telemetry: RouteTelemetry
    requires_retry: bool = False
    requires_escalation: bool = False
    failed_closed: bool = False
    execution_note: str | None = None


def basic_validation_context(
    request: ExecutionRequest,
    result: AgentResult,
) -> ValidationContext:
    """Minimal structural validator used until a domain validator is injected."""

    return ValidationContext(
        output_valid=bool(result.answer.strip()),
        evidence_satisfied=bool(result.tool_calls),
        evidence_required=request.context.evidence_required,
    )


def execute_control_plane_request(
    request: ExecutionRequest,
    *,
    local_worker: WorkerLike | None = None,
    validator: ValidatorLike = basic_validation_context,
    query_fn: QueryFn | None = None,
    router_version: str = "rules-v0",
) -> ExecutionOutcome:
    """Route once, execute one worker tier, validate, and emit telemetry.

    This slice does not automatically retry or invoke a stronger worker.
    Retry/escalation/fail-closed are explicit outcomes for the orchestration
    layer to handle in a later step.
    """

    started = time.perf_counter()
    route_started = time.perf_counter()
    decision = route_task(request.context)
    router_latency = time.perf_counter() - route_started

    if decision.route == ExecutionRoute.ESCALATE:
        return _terminal_without_result(
            request=request,
            decision=decision,
            router_latency=router_latency,
            total_latency=time.perf_counter() - started,
            router_version=router_version,
            escalation_reason=decision.reason_code.value,
            requires_escalation=True,
            execution_note="Control plane selected escalation before worker execution.",
        )

    if decision.route == ExecutionRoute.DETERMINISTIC:
        if request.deterministic_handler is None:
            raise RuntimeError(
                "Deterministic route selected without a deterministic handler."
            )

        try:
            if query_fn is None:
                handler_result = execute_deterministic_handler(
                    request.deterministic_handler
                )
            else:
                handler_result = execute_deterministic_handler(
                    request.deterministic_handler,
                    query_fn=query_fn,
                )
        except DeterministicHandlerDeclined as exc:
            return _terminal_without_result(
                request=request,
                decision=decision,
                router_latency=router_latency,
                total_latency=time.perf_counter() - started,
                router_version=router_version,
                escalation_reason="DETERMINISTIC_HANDLER_DECLINED",
                requires_escalation=True,
                worker=request.deterministic_handler.value,
                execution_note=str(exc),
            )

        result = AgentResult(
            answer=handler_result.answer,
            tool_calls=[
                ToolCallRecord(
                    name="query_clickhouse",
                    arguments={"sql": GROUPED_TEAM_METRICS_SQL},
                    row_count=len(handler_result.evidence_rows),
                    result_rows=list(handler_result.evidence_rows),
                )
            ],
            model_call_count=0,
            tool_call_attempt_count=handler_result.query_count,
            input_tokens=0,
            output_tokens=0,
            model_duration_seconds=0.0,
        )
        worker_name = request.deterministic_handler.value

    else:
        if local_worker is None:
            raise RuntimeError("Local route selected without a local worker.")
        result = local_worker.run(request.question)
        worker_name = type(local_worker).__name__

    validation = validate_execution(validator(request, result))
    total_latency = time.perf_counter() - started

    requires_retry = validation.disposition == ValidationDisposition.RETRY
    requires_escalation = validation.disposition == ValidationDisposition.ESCALATE
    failed_closed = validation.disposition == ValidationDisposition.FAIL_CLOSED
    escalation_reason = (
        validation.reason.value if requires_escalation else None
    )

    telemetry = build_route_telemetry(
        task_id=request.task_id,
        router_version=router_version,
        decision=decision,
        router_latency_seconds=router_latency,
        validation=validation,
        worker=worker_name,
        tool_calls=len(result.tool_calls),
        escalation_reason=escalation_reason,
        total_model_calls=result.model_call_count,
        total_latency_seconds=total_latency,
        estimated_cost_usd=None,
        task_success=None,
        human_intervention=False,
    )

    return ExecutionOutcome(
        request=request,
        decision=decision,
        result=result,
        validation=validation,
        telemetry=telemetry,
        requires_retry=requires_retry,
        requires_escalation=requires_escalation,
        failed_closed=failed_closed,
    )


def _terminal_without_result(
    *,
    request: ExecutionRequest,
    decision: RouteDecision,
    router_latency: float,
    total_latency: float,
    router_version: str,
    escalation_reason: str,
    requires_escalation: bool,
    worker: str | None = None,
    execution_note: str | None = None,
) -> ExecutionOutcome:
    telemetry = build_route_telemetry(
        task_id=request.task_id,
        router_version=router_version,
        decision=decision,
        router_latency_seconds=router_latency,
        worker=worker,
        escalation_reason=escalation_reason,
        total_latency_seconds=total_latency,
    )
    return ExecutionOutcome(
        request=request,
        decision=decision,
        result=None,
        validation=None,
        telemetry=telemetry,
        requires_escalation=requires_escalation,
        execution_note=execution_note,
    )
