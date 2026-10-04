"""Model-free worker invocation boundaries for System Benchmark v1."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from src.evals.system_benchmark.contracts import (
    BenchmarkFamily,
    CapabilityProfile,
    ResponseDisposition,
    SystemBenchmarkResponse,
    SystemBenchmarkTask,
)
from src.evals.system_benchmark.routing import RoutingDecision


class WorkerBoundaryError(RuntimeError):
    """Raised when a worker response violates the benchmark execution boundary."""


@dataclass(frozen=True)
class WorkerInvocation:
    case_id: str
    request: str
    route: str
    capability_profile: CapabilityProfile
    allowed_tools: tuple[str, ...]
    escalation_mode: str | None = None


Worker = Callable[[WorkerInvocation], SystemBenchmarkResponse]


_TOOLSETS = {
    CapabilityProfile.NONE: (),
    CapabilityProfile.STRUCTURED: ("query_clickhouse",),
    CapabilityProfile.DOCUMENTS: ("retrieve_policy",),
    CapabilityProfile.MULTI_SOURCE: ("query_clickhouse", "retrieve_policy"),
}
_STRONG_SINGLE_TOOLS = ("query_clickhouse", "retrieve_policy")


def build_worker_invocation(
    task: SystemBenchmarkTask,
    decision: RoutingDecision,
) -> WorkerInvocation:
    """Build an execution request from an already-made route decision."""

    capability_tools = _TOOLSETS[decision.capability_profile]
    allowed = tuple(tool for tool in capability_tools if tool in task.allowed_tools)
    return WorkerInvocation(
        case_id=task.case_id,
        request=task.request,
        route=decision.route.value,
        capability_profile=decision.capability_profile,
        allowed_tools=allowed,
        escalation_mode=decision.escalation_mode,
    )


def build_strong_single_invocation(task: SystemBenchmarkTask) -> WorkerInvocation:
    """Expose both safe evidence tools to the strong single-agent baseline."""

    return WorkerInvocation(
        case_id=task.case_id,
        request=task.request,
        route="local",
        capability_profile=CapabilityProfile.MULTI_SOURCE,
        allowed_tools=_STRONG_SINGLE_TOOLS,
        escalation_mode=None,
    )


def execute_worker(
    task: SystemBenchmarkTask,
    decision: RoutingDecision,
    worker: Worker,
) -> SystemBenchmarkResponse:
    """Execute a worker under a supplied route decision and enforce hard bounds."""

    invocation = build_worker_invocation(task, decision)
    response = worker(invocation)
    if not isinstance(response, SystemBenchmarkResponse):
        raise WorkerBoundaryError("worker must return SystemBenchmarkResponse")

    if task.family is BenchmarkFamily.HUMAN_HANDOFF_AUTHORITY_BOUNDARY:
        if response.disposition is not ResponseDisposition.HANDOFF:
            raise WorkerBoundaryError("Family H worker must return handoff")

    if task.family is BenchmarkFamily.UNSUPPORTED_SOURCE_HANDLING:
        if response.disposition is not ResponseDisposition.UNSUPPORTED:
            raise WorkerBoundaryError("unsupported-source worker must return unsupported")
        if response.evidence_refs:
            raise WorkerBoundaryError("unsupported-source worker cannot fabricate evidence")

    if decision.capability_profile is CapabilityProfile.NONE and response.evidence_refs:
        raise WorkerBoundaryError("none capability cannot emit evidence refs")

    return response
