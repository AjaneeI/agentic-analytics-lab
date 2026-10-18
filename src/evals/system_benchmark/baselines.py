"""Explicit opt-in System Benchmark baselines; importing activates no execution.

The strong single adapter reuses the bounded runtime and both safe tool schemas.
Tool affordances do not grant execution permissions: the task boundary remains
an independent, fail-closed gate. The simple baseline covers only the one
approved all-item blocker-rate operation and never consumes reference answers.
"""

from __future__ import annotations

import math
from pathlib import Path
import time

from src.evals.system_benchmark.contracts import (
    BenchmarkExecutionRoute, BenchmarkFamily, CapabilityProfile,
    ResponseDisposition, SystemBenchmarkResponse, SystemBenchmarkTask,
)
from src.evals.system_benchmark.local_worker import (
    BoundedLocalExecutor, ModelLike, PolicyFn, QueryFn,
)
from src.evals.system_benchmark.routing import RoutingDecision
from src.evals.system_benchmark.runner import TrialExecution
from src.evals.system_benchmark.scoring import ScoringObservation
from src.evals.system_benchmark.workers import (
    WorkerInvocation, build_strong_single_invocation, execute_worker,
)
from src.routing.deterministic_handlers import (
    DeterministicHandlerDeclined, GROUPED_TEAM_METRICS_SQL, HandlerKey,
    execute_deterministic_handler,
)
from src.tools.clickhouse_readonly import query_clickhouse
from src.tools.policy_retrieval import retrieve_policy


def _strong_route(_task: SystemBenchmarkTask) -> RoutingDecision:
    return RoutingDecision(
        route=BenchmarkExecutionRoute.LOCAL,
        capability_profile=CapabilityProfile.MULTI_SOURCE,
        reason_code="strong_single_no_routing",
    )


def _strong_invocation(task: SystemBenchmarkTask, _decision: RoutingDecision) -> WorkerInvocation:
    return build_strong_single_invocation(task)


def _task_permits_tool(task: SystemBenchmarkTask, name: str) -> bool:
    return (
        task.family is not BenchmarkFamily.UNSUPPORTED_SOURCE_HANDLING
        and name in task.allowed_tools
        and name not in task.forbidden_tools
    )


class StrongSingleExecutor:
    """One explicitly configured model, no route inference, shared safe tools.

    A model instance and its identifier are mandatory. No model is constructed
    or substituted here; callers retain responsibility for recording runtime
    settings and the accepted comparison anchor in the run manifest.
    """

    def __init__(
        self,
        *,
        model: ModelLike,
        model_id: str,
        query_fn: QueryFn = query_clickhouse,
        policy_fn: PolicyFn = retrieve_policy,
        max_model_steps: int = 6,
    ):
        if model is None or not callable(getattr(model, "respond", None)) or not model:
            raise ValueError("an explicit model instance is required")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("an explicit non-empty model_id is required")
        if getattr(model, "model", model_id) != model_id:
            raise ValueError("model_id does not match the supplied model client")
        self.model_id = model_id
        self._executor = BoundedLocalExecutor(
            model=model,
            query_fn=query_fn,
            policy_fn=policy_fn,
            route_fn=_strong_route,
            max_model_steps=max_model_steps,
            invocation_fn=_strong_invocation,
            tool_permission_fn=_task_permits_tool,
        )

    def __call__(
        self, task: SystemBenchmarkTask, trial_number: int, temp_dir: Path | None,
    ) -> TrialExecution:
        execution = self._executor(task, trial_number, temp_dir)
        # Reuse the existing hard G/H response boundary without changing the
        # model's invocation or injecting oracle routing into its input.
        execute_worker(task, execution.route_decision, lambda _invocation: execution.response)
        return execution


class DeterministicBaselineDeclined(DeterministicHandlerDeclined):
    """No approved exact operation or sufficient observed evidence is available."""


_ALL_ITEM_BLOCKER_LEADER_REQUEST = (
    "which team has the highest blocker rate in the structured delivery dataset?"
)


class DeterministicSimpleExecutor:
    """Runner-compatible fixed-query baseline for the approved all-item request.

    Selection uses normalized request text, never case IDs, family labels,
    expected values or reference IDs. Any other operation declines before tools;
    callers must record non-applicability rather than count it as task success.
    """

    def __init__(self, *, query_fn: QueryFn = query_clickhouse):
        self.query_fn = query_fn

    @staticmethod
    def supports(request: str) -> bool:
        return " ".join(request.split()).casefold() == _ALL_ITEM_BLOCKER_LEADER_REQUEST

    def __call__(
        self, task: SystemBenchmarkTask, trial_number: int, temp_dir: Path | None,
    ) -> TrialExecution:
        del trial_number, temp_dir
        started = time.monotonic()
        if not self.supports(task.request):
            raise DeterministicBaselineDeclined("no approved deterministic operation for request")
        if (task.family is BenchmarkFamily.HUMAN_HANDOFF_AUTHORITY_BOUNDARY
                or ResponseDisposition.ANSWER not in task.allowed_dispositions
                or ResponseDisposition.ANSWER in task.forbidden_dispositions):
            raise DeterministicBaselineDeclined("task boundary does not permit a deterministic answer")
        if not _task_permits_tool(task, "query_clickhouse"):
            raise DeterministicBaselineDeclined("query_clickhouse is not permitted for this task")
        if task.trajectory.max_tool_calls is not None and task.trajectory.max_tool_calls < 1:
            raise DeterministicBaselineDeclined("task tool-call budget does not permit a query")

        try:
            result = execute_deterministic_handler(
                HandlerKey.BLOCKER_RATE_LEADER, query_fn=self.query_fn,
            )
        except DeterministicHandlerDeclined as exc:
            raise DeterministicBaselineDeclined(str(exc)) from exc
        for row in result.evidence_rows:
            if not all(math.isfinite(row[name]) for name in (
                "total_items", "blocked_items", "blocker_rate", "avg_effort_ratio",
            )):
                raise DeterministicBaselineDeclined("query returned non-finite metric values")
            if not (0 <= row["blocked_items"] <= row["total_items"] and row["total_items"] > 0
                    and 0 <= row["blocker_rate"] <= 100):
                raise DeterministicBaselineDeclined("query returned invalid count/rate bounds")
        leader = max(result.evidence_rows, key=lambda row: row["blocker_rate"])
        return TrialExecution(
            response=SystemBenchmarkResponse(
                disposition=ResponseDisposition.ANSWER,
                answer_text=result.answer,
                evidence_refs=("structured:delivery_work_items",),
            ),
            observation=ScoringObservation(
                tool_calls=("query_clickhouse",),
                tool_call_records=({
                    "name": "query_clickhouse",
                    "arguments": {"sql": GROUPED_TEAM_METRICS_SQL},
                },),
                structured_values={"team": leader["team"], "blocked_pct": leader["blocker_rate"]},
            ),
            route_decision=RoutingDecision(
                route=BenchmarkExecutionRoute.DETERMINISTIC,
                capability_profile=CapabilityProfile.STRUCTURED,
                reason_code="simple_fixed_blocker_rate_leader",
            ),
            latency_seconds=time.monotonic() - started,
        )
