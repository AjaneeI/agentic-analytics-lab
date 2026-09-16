"""Provider-agnostic single-agent baseline for Agentic Analytics Lab."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol

from src.tools.clickhouse_readonly import query_clickhouse


SYSTEM_PROMPT = """
You are a delivery analytics agent.

You answer questions about:
`agentic_analytics.delivery_work_items`

Schema semantics:
- work_item_id: unique work-item identifier
- team: owning team
- priority: low, medium, high, or critical
- status: done, in_progress, or blocked
- created_at: creation timestamp
- due_at: planned due timestamp
- completed_at: completion timestamp when finished
- for completed work, schedule lateness can be derived by comparing
  completed_at with due_at; completed_at > due_at means the item finished late
- planned_hours: planned effort
- actual_hours: observed effort
- blocked: 1 if the work item experienced a blocker, otherwise 0
- canonical blocker-rate formula:
  blocker_rate = SUM(blocked) / COUNT(*)
  or equivalently AVG(blocked)
- when reporting blocker percentage, use 100 * AVG(blocked)
- COUNT(*) - SUM(blocked) measures NON-BLOCKED work items and must never be
  labeled or interpreted as blocker rate
- blocker_type: blocker category, or none
- rework_count: number of rework cycles
- customer_impact: synthetic impact score from 1 to 5

Rules:
1. Use query_clickhouse for factual claims about the dataset.
2. The database tool is read-only. Never attempt to modify data.
3. Translate business metrics carefully. A rate requires the appropriate
   numerator and denominator, not merely a count. For blocker rate, the
   denominator is all work items in the group; do not filter to only blocked
   rows before calculating the rate.
4. Prefer one database query when one query can answer the question correctly.
   Re-query only when the first result is insufficient.
5. Compute derived numerical metrics such as rates, percentages, ratios, and
   averages in SQL. Return the calculated metric from ClickHouse and quote that
   value in the final answer rather than recomputing it mentally.
6. Prefer the smallest query that answers the question.
7. Cite the numerical evidence used in your answer.
8. Do not infer causality from observational data.
9. If the available data cannot support a conclusion, state what additional
   evidence would be needed.
""".strip()


TOOL_SPEC = {
    "name": "query_clickhouse",
    "description": (
        "Run a read-only analytical SQL query against the local ClickHouse "
        "database. Only SELECT/WITH/SHOW/DESCRIBE/EXPLAIN queries are allowed."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A single read-only ClickHouse SQL statement.",
            }
        },
        "required": ["sql"],
    },
}


class ModelClient(Protocol):
    def respond(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return either a tool_call or final response."""
        ...


@dataclass
class ToolCallRecord:
    name: str
    arguments: dict[str, Any]
    row_count: int


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    transcript: list[dict[str, Any]] = field(default_factory=list)


class SingleAgent:
    def __init__(self, model: ModelClient, max_steps: int = 6):
        self.model = model
        self.max_steps = max_steps

    def run(self, question: str) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        tool_calls: list[ToolCallRecord] = []

        for _ in range(self.max_steps):
            response = self.model.respond(messages, [TOOL_SPEC])

            response_type = response.get("type")

            if response_type == "final":
                answer = response.get("content", "").strip()

                if not answer:
                    raise RuntimeError("Model returned an empty final answer.")

                return AgentResult(
                    answer=answer,
                    tool_calls=tool_calls,
                    transcript=messages + [
                        {"role": "assistant", "content": answer}
                    ],
                )

            if response_type != "tool_call":
                raise RuntimeError(
                    f"Unsupported model response type: {response_type!r}"
                )

            tool_name = response.get("name")
            arguments = response.get("arguments", {})

            if tool_name != "query_clickhouse":
                raise RuntimeError(f"Unknown tool requested: {tool_name!r}")

            sql = arguments.get("sql")

            if not isinstance(sql, str) or not sql.strip():
                raise RuntimeError("query_clickhouse requires a non-empty SQL string.")

            rows = query_clickhouse(sql)

            tool_calls.append(
                ToolCallRecord(
                    name=tool_name,
                    arguments={"sql": sql},
                    row_count=len(rows),
                )
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "tool_call",
                            "name": tool_name,
                            "arguments": {"sql": sql},
                        }
                    ),
                }
            )

            messages.append(
                {
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps(rows),
                }
            )

        raise RuntimeError(
            f"Agent exceeded maximum of {self.max_steps} model steps."
        )
