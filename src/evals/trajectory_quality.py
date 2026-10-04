"""Model-free trajectory diagnostics for agent tool use.

This module evaluates observable tool-call behavior without inspecting hidden
reasoning or using an LLM judge. It is deliberately generic so both the frozen
Q1-Q6 benchmark and System Benchmark v1 can reuse it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from typing import Any


@dataclass(frozen=True)
class TrajectoryExpectation:
    required_tools: tuple[str, ...] = ()
    allowed_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    ordered_dependencies: tuple[tuple[str, str], ...] = ()
    max_tool_calls: int | None = None


@dataclass(frozen=True)
class TrajectoryResult:
    passed: bool
    total_calls: int
    tool_selection_correct: bool
    dependency_order_correct: bool
    efficiency_ok: bool
    malformed_calls: int
    repeated_calls: int
    unnecessary_calls: int
    missing_required_tools: tuple[str, ...]
    unexpected_tools: tuple[str, ...]
    forbidden_tools_used: tuple[str, ...]
    dependency_violations: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "total_calls": self.total_calls,
            "tool_selection_correct": self.tool_selection_correct,
            "dependency_order_correct": self.dependency_order_correct,
            "efficiency_ok": self.efficiency_ok,
            "malformed_calls": self.malformed_calls,
            "repeated_calls": self.repeated_calls,
            "unnecessary_calls": self.unnecessary_calls,
            "missing_required_tools": list(self.missing_required_tools),
            "unexpected_tools": list(self.unexpected_tools),
            "forbidden_tools_used": list(self.forbidden_tools_used),
            "dependency_violations": list(self.dependency_violations),
        }


def _canonical_call_signature(name: str, arguments: Mapping[str, Any]) -> str:
    return f"{name}:{json.dumps(arguments, sort_keys=True, separators=(',', ':'), default=str)}"


def evaluate_trajectory(
    tool_calls: Sequence[Mapping[str, Any]],
    expectation: TrajectoryExpectation,
) -> TrajectoryResult:
    """Evaluate tool selection, order, repetition, and call-budget behavior."""

    names: list[str] = []
    signatures: list[str] = []
    malformed_calls = 0

    for call in tool_calls:
        if not isinstance(call, Mapping):
            malformed_calls += 1
            continue
        name = call.get("name")
        arguments = call.get("arguments", {})
        if not isinstance(name, str) or not name.strip():
            malformed_calls += 1
            continue
        if not isinstance(arguments, Mapping):
            malformed_calls += 1
            continue
        clean_name = name.strip()
        names.append(clean_name)
        signatures.append(_canonical_call_signature(clean_name, arguments))

    required = tuple(expectation.required_tools)
    allowed = set(expectation.allowed_tools)
    forbidden = set(expectation.forbidden_tools)

    missing_required = tuple(
        tool for tool in required if tool not in names
    )
    forbidden_used = tuple(
        tool for tool in names if tool in forbidden
    )
    unexpected = tuple(
        tool
        for tool in names
        if tool not in allowed and tool not in forbidden
    )

    dependency_violations: list[str] = []
    for before, after in expectation.ordered_dependencies:
        if after not in names:
            continue
        if before not in names:
            dependency_violations.append(f"{before}->{after}:missing_dependency")
            continue
        if names.index(before) > names.index(after):
            dependency_violations.append(f"{before}->{after}:wrong_order")

    repeated_calls = len(signatures) - len(set(signatures))
    unnecessary_calls = 0
    if expectation.max_tool_calls is not None:
        if expectation.max_tool_calls < 0:
            raise ValueError("max_tool_calls must be non-negative or None")
        unnecessary_calls = max(
            len(tool_calls) - expectation.max_tool_calls, 0
        )

    tool_selection_correct = not (
        missing_required or forbidden_used or unexpected or malformed_calls
    )
    dependency_order_correct = not dependency_violations
    efficiency_ok = repeated_calls == 0 and unnecessary_calls == 0

    passed = (
        tool_selection_correct
        and dependency_order_correct
        and efficiency_ok
    )

    return TrajectoryResult(
        passed=passed,
        total_calls=len(tool_calls),
        tool_selection_correct=tool_selection_correct,
        dependency_order_correct=dependency_order_correct,
        efficiency_ok=efficiency_ok,
        malformed_calls=malformed_calls,
        repeated_calls=repeated_calls,
        unnecessary_calls=unnecessary_calls,
        missing_required_tools=missing_required,
        unexpected_tools=unexpected,
        forbidden_tools_used=forbidden_used,
        dependency_violations=tuple(dependency_violations),
    )
