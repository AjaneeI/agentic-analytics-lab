"""Experiment-scoped Hermes adapters for the frozen System Benchmark tools."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import threading
from typing import Any


_QUERY_SPEC = {
    "name": "query_clickhouse",
    "description": (
        "Run one read-only SQL query against "
        "agentic_analytics.delivery_work_items. For blocker percentage, "
        "return the percentage from ClickHouse and alias it as blocked_pct."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"sql": {"type": "string"}},
        "required": ["sql"],
    },
}

_POLICY_SPEC = {
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

_MAX_TOOL_CALLS = 2
_state_lock = threading.Lock()
_call_count = 0
_delegate_count = 0


def _repo_root() -> Path:
    raw = os.environ.get("AAL_REPO_ROOT", "")
    if not raw:
        raise RuntimeError("AAL_REPO_ROOT is required")
    root = Path(raw)
    if not root.is_absolute():
        raise RuntimeError("AAL_REPO_ROOT must be absolute")
    root = root.resolve(strict=True)
    required = root / "src" / "evals" / "system_benchmark" / "local_worker.py"
    if not required.is_file():
        raise RuntimeError("AAL_REPO_ROOT is not an Agentic Analytics Lab checkout")
    return root


def _load_runtime():
    root = _repo_root()
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    from src.tools.clickhouse_readonly import QueryRejected, query_clickhouse
    from src.tools.policy_retrieval import retrieve_policy

    return QueryRejected, query_clickhouse, retrieve_policy


def _consume_call() -> int | None:
    global _call_count
    with _state_lock:
        _call_count += 1
        return _call_count if _call_count <= _MAX_TOOL_CALLS else None


def _write_event(event: dict[str, Any]) -> None:
    raw = os.environ.get("AAL_EVIDENCE_LOG", "")
    if not raw:
        raise RuntimeError("AAL_EVIDENCE_LOG is required")
    path = Path(raw)
    if not path.is_absolute():
        raise RuntimeError("AAL_EVIDENCE_LOG must be absolute")
    path.parent.mkdir(parents=True, exist_ok=True)
    with _state_lock:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _is_delegated_child_context() -> bool:
    try:
        from agent.delegation_context import is_delegated_child_context
    except ImportError:
        return False
    return bool(is_delegated_child_context())


def _reject_parent_evidence_call(
    tool: str, args: dict[str, Any]
) -> str | None:
    if _is_delegated_child_context():
        return None
    event = {
        "arguments": args,
        "delegated_child": False,
        "ok": False,
        "reason_code": "parent_evidence_call_forbidden",
        "tool": tool,
    }
    _write_event(event)
    return json.dumps(event, sort_keys=True)


def _blocked(tool: str, args: dict[str, Any]) -> str:
    event = {
        "arguments": args,
        "ok": False,
        "reason_code": "tool_budget_exceeded",
        "tool": tool,
    }
    _write_event(event)
    return json.dumps(event, sort_keys=True)


def _query(args, **_) -> str:
    arguments = dict(args or {})
    if blocked := _reject_parent_evidence_call("query_clickhouse", arguments):
        return blocked
    sequence = _consume_call()
    if sequence is None:
        return _blocked("query_clickhouse", arguments)
    QueryRejected, query_clickhouse, _ = _load_runtime()
    try:
        rows = query_clickhouse(arguments.get("sql"))
    except QueryRejected as exc:
        result = {
            "arguments": arguments,
            "delegated_child": True,
            "error": str(exc),
            "ok": False,
            "reason_code": "query_rejected",
            "sequence": sequence,
            "tool": "query_clickhouse",
        }
    except Exception as exc:
        result = {
            "arguments": arguments,
            "delegated_child": True,
            "error": f"{type(exc).__name__}: {exc}",
            "ok": False,
            "reason_code": "tool_error",
            "sequence": sequence,
            "tool": "query_clickhouse",
        }
    else:
        result = {
            "arguments": arguments,
            "delegated_child": True,
            "evidence_refs": ["structured:delivery_work_items"],
            "ok": True,
            "rows": rows,
            "sequence": sequence,
            "tool": "query_clickhouse",
        }
    _write_event(result)
    return json.dumps(result, sort_keys=True)


def _policy(args, **_) -> str:
    arguments = dict(args or {})
    if blocked := _reject_parent_evidence_call("retrieve_policy", arguments):
        return blocked
    sequence = _consume_call()
    if sequence is None:
        return _blocked("retrieve_policy", arguments)
    _, _, retrieve_policy = _load_runtime()
    kwargs = {"query": arguments.get("query")}
    if "as_of" in arguments and arguments["as_of"] is not None:
        kwargs["as_of"] = arguments["as_of"]
    if "top_k" in arguments:
        kwargs["top_k"] = arguments["top_k"]
    try:
        evidence = retrieve_policy(**kwargs)
    except Exception as exc:
        result = {
            "arguments": arguments,
            "delegated_child": True,
            "error": f"{type(exc).__name__}: {exc}",
            "ok": False,
            "reason_code": "tool_error",
            "sequence": sequence,
            "tool": "retrieve_policy",
        }
    else:
        rows = [asdict(item) for item in evidence]
        result = {
            "arguments": arguments,
            "delegated_child": True,
            "evidence_refs": [
                f"policy:{item.document_id}@{item.document_version}#{item.section_id}"
                for item in evidence
            ],
            "ok": True,
            "rows": rows,
            "sequence": sequence,
            "tool": "retrieve_policy",
        }
    _write_event(result)
    return json.dumps(result, sort_keys=True)


def _schema(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": spec["name"],
        "description": spec["description"],
        "parameters": spec["input_schema"],
    }


def _pre_tool_call(
    tool_name: str = "",
    args: dict[str, Any] | None = None,
    tool_call_id: str = "",
    **_: Any,
):
    if tool_name != "delegate_task":
        return None

    arguments = dict(args or {})
    tasks = arguments.get("tasks")
    action = str(arguments.get("action") or "spawn").strip().lower()
    valid_single_spawn = (
        action == "spawn"
        and isinstance(tasks, list)
        and len(tasks) == 1
        and isinstance(tasks[0], dict)
        and isinstance(tasks[0].get("goal"), str)
        and bool(tasks[0]["goal"].strip())
    )

    global _delegate_count
    with _state_lock:
        _delegate_count += 1
        delegate_sequence = _delegate_count

    event = {
        "arguments": arguments,
        "delegate_sequence": delegate_sequence,
        "event": "delegate_pre",
        "ok": valid_single_spawn and delegate_sequence == 1,
        "tool": "delegate_task",
        "tool_call_id": tool_call_id,
    }
    if not valid_single_spawn:
        event["reason_code"] = "single_task_spawn_required"
        _write_event(event)
        return {
            "action": "block",
            "message": "Treatment B requires one delegate_task spawn with exactly one task.",
        }
    if delegate_sequence != 1:
        event["reason_code"] = "delegate_budget_exceeded"
        _write_event(event)
        return {
            "action": "block",
            "message": "Treatment B allows exactly one delegate_task call.",
        }
    _write_event(event)
    return None


def _post_tool_call(
    tool_name: str = "",
    args: dict[str, Any] | None = None,
    tool_call_id: str = "",
    status: str | None = None,
    error_type: str | None = None,
    **_: Any,
) -> None:
    if tool_name != "delegate_task":
        return None
    _write_event(
        {
            "arguments": dict(args or {}),
            "error_type": error_type,
            "event": "delegate_post",
            "ok": status not in {"blocked", "error"},
            "status": status,
            "tool": "delegate_task",
            "tool_call_id": tool_call_id,
        }
    )
    return None


def register(ctx) -> None:
    ctx.register_tool(
        name="query_clickhouse",
        toolset="system_benchmark",
        schema=_schema(_QUERY_SPEC),
        handler=_query,
    )
    ctx.register_tool(
        name="retrieve_policy",
        toolset="system_benchmark",
        schema=_schema(_POLICY_SPEC),
        handler=_policy,
    )
    ctx.register_hook("pre_tool_call", _pre_tool_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
