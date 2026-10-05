"""Bounded local System Benchmark worker with truthful runtime observations."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Mapping, Protocol

from src.agents.ollama_client import OllamaModelClient
from src.evals.system_benchmark.contracts import (
    ResponseDisposition,
    SystemBenchmarkResponse,
    SystemBenchmarkTask,
)
from src.evals.system_benchmark.routing import RoutingDecision, oracle_route
from src.evals.system_benchmark.runner import TrialExecution
from src.evals.system_benchmark.scoring import ScoringObservation
from src.evals.system_benchmark.workers import build_worker_invocation
from src.tools.clickhouse_readonly import query_clickhouse
from src.tools.policy_retrieval import PolicyEvidence, retrieve_policy


DEFAULT_LOCAL_MODEL = "hermes-local:qwen3.5-9b"


class LocalWorkerError(RuntimeError):
    """Raised when the bounded worker contract is violated."""


class ModelLike(Protocol):
    def respond(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...


QueryFn = Callable[[str], list[dict[str, Any]]]
PolicyFn = Callable[..., list[PolicyEvidence]]
RouteFn = Callable[[SystemBenchmarkTask], RoutingDecision]


_QUERY_TOOL = {
    "name": "query_clickhouse",
    "description": (
        "Run one read-only SQL query against "
        "agentic_analytics.delivery_work_items. For blocker percentage, "
        "return the percentage from ClickHouse and alias it as blocked_pct."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string"},
        },
        "required": ["sql"],
    },
}

_POLICY_TOOL = {
    "name": "retrieve_policy",
    "description": (
        "Retrieve read-only repository-local policy sections. Use this for "
        "definitions, current policy, and historical as-of policy evidence."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "as_of": {"type": ["string", "null"]},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 5},
        },
        "required": ["query"],
    },
}

_TOOL_SPECS = {
    "query_clickhouse": _QUERY_TOOL,
    "retrieve_policy": _POLICY_TOOL,
}

_DELIVERY_TABLE_REF = re.compile(
    r"\b(?:from|join)\s+agentic_analytics\s*\.\s*delivery_work_items\b",
    re.IGNORECASE,
)

_SYSTEM_PROMPT = """
You are a bounded local worker for System Benchmark v1.

You have only the explicitly provided evidence tools. Do not claim to have
used a tool unless the runtime actually invoked it. You have no filesystem,
shell, glob, generic execute, benchmark-fixture, web, or external-service
capability.

For factual claims about the structured delivery dataset, call
query_clickhouse. For policy definitions or policy interpretation, call
retrieve_policy. If the request requires both structured and policy evidence,
call both tools before answering. Do not infer causality from observational
data.

When querying blocker percentage, compute it in SQL as
100 * SUM(blocked) / COUNT(*) (or equivalent) and alias the percentage as
blocked_pct.

After evidence gathering, return one JSON object only with these keys:
disposition, answer_text, uncertainty, clarification, handoff.
Do not include evidence_refs, observed_tools, or observed_values; the runtime
constructs those from actual tool execution.
""".strip()


class BoundedLocalExecutor:
    """Runner-compatible local executor restricted to approved evidence tools."""

    def __init__(
        self,
        *,
        model: ModelLike | None = None,
        query_fn: QueryFn = query_clickhouse,
        policy_fn: PolicyFn = retrieve_policy,
        route_fn: RouteFn = oracle_route,
        max_model_steps: int = 6,
    ):
        if max_model_steps < 1:
            raise ValueError("max_model_steps must be >= 1")
        self.model = model or OllamaModelClient(model=DEFAULT_LOCAL_MODEL)
        self.query_fn = query_fn
        self.policy_fn = policy_fn
        self.route_fn = route_fn
        self.max_model_steps = max_model_steps

    def __call__(
        self,
        task: SystemBenchmarkTask,
        trial_number: int,
        temp_dir: Path | None,
    ) -> TrialExecution:
        del trial_number, temp_dir
        started = time.monotonic()
        decision = self.route_fn(task)
        invocation = build_worker_invocation(task, decision)
        tools = [_TOOL_SPECS[name] for name in invocation.allowed_tools]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": task.request},
        ]
        tool_names: list[str] = []
        tool_records: list[Mapping[str, Any]] = []
        structured_values: dict[str, Any] = {}
        evidence_refs: list[str] = []
        model_calls = input_tokens = output_tokens = 0
        model_duration = 0.0
        tool_attempts = 0
        max_tool_calls = task.trajectory.max_tool_calls

        for _ in range(self.max_model_steps):
            raw = self.model.respond(messages, tools)
            model_calls += 1
            metrics = raw.get("_metrics") or {}
            input_tokens += int(metrics.get("input_tokens") or 0)
            output_tokens += int(metrics.get("output_tokens") or 0)
            model_duration += float(metrics.get("total_duration_seconds") or 0.0)

            response_type = raw.get("type")
            if response_type == "final":
                response = _parse_final_response(
                    raw.get("content"),
                    evidence_refs=tuple(evidence_refs),
                )
                return TrialExecution(
                    response=response,
                    observation=ScoringObservation(
                        tool_calls=tuple(tool_names),
                        tool_call_records=tuple(tool_records),
                        structured_values=structured_values,
                    ),
                    route_decision=decision,
                    latency_seconds=time.monotonic() - started,
                    model_calls=model_calls,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    model_duration_seconds=model_duration,
                )

            if response_type != "tool_call":
                raise LocalWorkerError(
                    f"unsupported model response type: {response_type!r}"
                )

            name = raw.get("name")
            arguments = raw.get("arguments")
            if name not in invocation.allowed_tools:
                raise LocalWorkerError(
                    f"tool {name!r} is not exposed for this task"
                )
            if not isinstance(arguments, Mapping):
                raise LocalWorkerError("tool arguments must be an object")

            tool_attempts += 1
            if max_tool_calls is not None and tool_attempts > max_tool_calls:
                raise LocalWorkerError(
                    f"tool-call budget exceeded: {max_tool_calls}"
                )

            if name == "query_clickhouse":
                result_payload = self._run_query_tool(
                    task,
                    arguments,
                    structured_values,
                    evidence_refs,
                )
            elif name == "retrieve_policy":
                result_payload = self._run_policy_tool(arguments, evidence_refs)
            else:
                raise LocalWorkerError(f"unsupported tool: {name!r}")

            normalized_args = dict(arguments)
            tool_names.append(name)
            tool_records.append({"name": name, "arguments": normalized_args})
            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "tool_call",
                            "name": name,
                            "arguments": normalized_args,
                        }
                    ),
                }
            )
            messages.append(
                {
                    "role": "tool",
                    "name": name,
                    "content": json.dumps(result_payload, sort_keys=True),
                }
            )

        raise LocalWorkerError(
            f"model exceeded maximum of {self.max_model_steps} steps"
        )

    def _run_query_tool(
        self,
        task: SystemBenchmarkTask,
        arguments: Mapping[str, Any],
        structured_values: dict[str, Any],
        evidence_refs: list[str],
    ) -> list[dict[str, Any]]:
        sql = arguments.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            raise LocalWorkerError("query_clickhouse requires non-empty sql")

        rows = self.query_fn(sql)
        if not isinstance(rows, list) or not all(
            isinstance(row, dict) for row in rows
        ):
            raise LocalWorkerError("query_clickhouse returned invalid rows")

        if rows and _query_references_delivery_table(sql):
            _append_unique(evidence_refs, "structured:delivery_work_items")
            _extract_structured_values(task, rows, structured_values)
        return rows

    def _run_policy_tool(
        self,
        arguments: Mapping[str, Any],
        evidence_refs: list[str],
    ) -> list[dict[str, Any]]:
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            raise LocalWorkerError("retrieve_policy requires non-empty query")

        kwargs: dict[str, Any] = {"query": query}
        if "as_of" in arguments and arguments["as_of"] is not None:
            kwargs["as_of"] = arguments["as_of"]
        if "top_k" in arguments:
            kwargs["top_k"] = arguments["top_k"]

        evidence = self.policy_fn(**kwargs)
        if not isinstance(evidence, list) or not all(
            isinstance(item, PolicyEvidence) for item in evidence
        ):
            raise LocalWorkerError("retrieve_policy returned invalid evidence")

        payload = []
        for item in evidence:
            ref = (
                f"policy:{item.document_id}@{item.document_version}"
                f"#{item.section_id}"
            )
            _append_unique(evidence_refs, ref)
            payload.append(asdict(item))
        return payload


def _extract_structured_values(
    task: SystemBenchmarkTask,
    rows: list[dict[str, Any]],
    output: dict[str, Any],
) -> None:
    aliases = {"blocked_pct": ("blocked_pct", "blocker_rate")}
    for expectation in task.expected_values:
        keys = aliases.get(expectation.name, (expectation.name,))
        values: list[Any] = []
        for row in rows:
            for key in keys:
                if key in row and row[key] is not None:
                    values.append(row[key])
                    break
        if not values:
            continue
        first = values[0]
        if not all(value == first for value in values):
            output.pop(expectation.name, None)
            continue
        previous = output.get(expectation.name, first)
        if previous != first:
            output.pop(expectation.name, None)
            continue
        output[expectation.name] = first


def _query_references_delivery_table(sql: str) -> bool:
    normalized = sql.replace(chr(96), "").replace(chr(34), "")
    return _DELIVERY_TABLE_REF.search(normalized) is not None


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _parse_final_response(
    content: Any,
    *,
    evidence_refs: tuple[str, ...],
) -> SystemBenchmarkResponse:
    if not isinstance(content, str) or not content.strip():
        raise LocalWorkerError("model returned empty final content")
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LocalWorkerError("model final response must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise LocalWorkerError("model final response must be a JSON object")

    try:
        disposition = ResponseDisposition(payload.get("disposition"))
    except ValueError as exc:
        raise LocalWorkerError("invalid response disposition") from exc

    answer_text = payload.get("answer_text")
    if not isinstance(answer_text, str) or not answer_text.strip():
        raise LocalWorkerError("answer_text must be a non-empty string")

    uncertainty = payload.get("uncertainty")
    if uncertainty is not None and not isinstance(uncertainty, str):
        raise LocalWorkerError("uncertainty must be a string or null")

    clarification = payload.get("clarification")
    if clarification is not None and not isinstance(clarification, dict):
        raise LocalWorkerError("clarification must be an object or null")

    handoff = payload.get("handoff")
    if handoff is not None and not isinstance(handoff, dict):
        raise LocalWorkerError("handoff must be an object or null")

    return SystemBenchmarkResponse(
        disposition=disposition,
        answer_text=answer_text.strip(),
        evidence_refs=evidence_refs,
        uncertainty=uncertainty,
        clarification=clarification,
        handoff=handoff,
    )
