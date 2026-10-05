import json
import unittest

from src.evals.system_benchmark.contracts import parse_task_contract
from src.evals.system_benchmark.routing import oracle_route
from src.tools.policy_retrieval import PolicyEvidence


def sb_d01():
    return parse_task_contract({
        "id": "SB-D01",
        "benchmark_version": "system-benchmark-v1",
        "family": "D",
        "split": "development",
        "request": "Identify the highest blocker-rate team and interpret it using the KPI definition without claiming causality.",
        "expected_route": "deterministic",
        "expected_capability_profile": "multi_source",
        "allowed_dispositions": ["answer"],
        "forbidden_dispositions": ["clarify", "unsupported", "handoff"],
        "required_evidence_source_types": ["structured", "policy"],
        "acceptable_source_ids": ["delivery_work_items", "kpi-dictionary"],
        "expected_values": [
            {"name": "team", "value": "Data"},
            {"name": "blocked_pct", "value": 20.9, "tolerance": 0.2},
        ],
        "required_claims": ["identify the team and blocker rate"],
        "forbidden_claims": ["claim blockers cause lateness"],
        "required_clarification_concept": None,
        "required_handoff_fields": [],
        "allowed_tools": ["query_clickhouse", "retrieve_policy"],
        "forbidden_tools": [],
        "trajectory": {"ordered_dependencies": [], "max_tool_calls": 2},
        "reference_solution_id": "REF-D01",
    })


class ScriptedModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.tool_surfaces = []
        self.message_batches = []

    def respond(self, messages, tools):
        self.tool_surfaces.append(tuple(tool["name"] for tool in tools))
        self.message_batches.append(tuple(dict(message) for message in messages))
        if not self.responses:
            raise AssertionError("model script exhausted")
        return self.responses.pop(0)


def final_payload(**extra):
    payload = {
        "disposition": "answer",
        "answer_text": (
            "Data has the highest blocker rate at 20.9%. "
            "The KPI dictionary defines blocker rate as blocked items divided by active items; "
            "this is descriptive and does not establish causality."
        ),
        "uncertainty": None,
        "clarification": None,
        "handoff": None,
    }
    payload.update(extra)
    return json.dumps(payload)


class TestBoundedLocalWorker(unittest.TestCase):
    def test_runtime_trace_overrides_spoofed_model_observations(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor

        model = ScriptedModel([
            {
                "type": "tool_call",
                "name": "query_clickhouse",
                "arguments": {
                    "sql": (
                        "SELECT team, round(100.0 * avg(blocked), 1) AS blocked_pct "
                        "FROM agentic_analytics.delivery_work_items "
                        "GROUP BY team ORDER BY blocked_pct DESC LIMIT 1"
                    )
                },
            },
            {
                "type": "tool_call",
                "name": "retrieve_policy",
                "arguments": {"query": "KPI dictionary blocker rate"},
            },
            {
                "type": "final",
                "content": final_payload(
                    evidence_refs=["structured:fake", "policy:fake@9#fake"],
                    observed_tools=["shell", "read"],
                    observed_values={"team": "Fake", "blocked_pct": 999},
                ),
            },
        ])
        executor = BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [{"team": "Data", "blocked_pct": 20.9}],
            policy_fn=lambda **_kwargs: [
                PolicyEvidence(
                    document_id="kpi-dictionary",
                    document_version="1.0",
                    section_id="blocker-rate",
                    excerpt="Blocker Rate: blocked items divided by active items.",
                    effective_date="2026-01-01",
                    status="current",
                )
            ],
        )

        execution = executor(sb_d01(), 1, None)

        self.assertEqual(
            execution.observation.tool_calls,
            ("query_clickhouse", "retrieve_policy"),
        )
        self.assertEqual(
            dict(execution.observation.structured_values),
            {"team": "Data", "blocked_pct": 20.9},
        )
        self.assertEqual(
            execution.response.evidence_refs,
            (
                "structured:delivery_work_items",
                "policy:kpi-dictionary@1.0#blocker-rate",
            ),
        )

    def test_model_surface_contains_only_task_allowed_evidence_tools(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor

        model = ScriptedModel([{"type": "final", "content": final_payload()}])
        executor = BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [],
            policy_fn=lambda **_kwargs: [],
        )

        executor(sb_d01(), 1, None)

        self.assertEqual(
            model.tool_surfaces,
            [("query_clickhouse", "retrieve_policy")],
        )
        self.assertNotIn("read", model.tool_surfaces[0])
        self.assertNotIn("shell", model.tool_surfaces[0])
        self.assertNotIn("glob", model.tool_surfaces[0])
        self.assertNotIn("execute", model.tool_surfaces[0])

    def test_model_input_excludes_hidden_benchmark_ground_truth(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor

        model = ScriptedModel([{"type": "final", "content": final_payload()}])
        BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [],
            policy_fn=lambda **_kwargs: [],
        )(sb_d01(), 1, None)

        serialized = json.dumps(model.message_batches)
        self.assertIn(sb_d01().request, serialized)
        self.assertNotIn("REF-D01", serialized)
        self.assertNotIn('"value": "Data"', serialized)
        self.assertNotIn('"value": 20.9', serialized)
        self.assertNotIn("development_references", serialized)
        self.assertNotIn("development_tasks", serialized)

    def test_documents_only_task_exposes_only_policy_tool(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor

        task = parse_task_contract({
            "id": "SB-C01",
            "benchmark_version": "system-benchmark-v1",
            "family": "C",
            "split": "development",
            "request": "According to the current KPI dictionary, how is blocker rate defined?",
            "expected_route": "local",
            "expected_capability_profile": "documents",
            "allowed_dispositions": ["answer"],
            "forbidden_dispositions": ["clarify", "unsupported", "handoff"],
            "required_evidence_source_types": ["policy"],
            "acceptable_source_ids": ["kpi-dictionary"],
            "expected_values": [],
            "required_claims": ["state the blocker-rate definition"],
            "forbidden_claims": [],
            "required_clarification_concept": None,
            "required_handoff_fields": [],
            "allowed_tools": ["retrieve_policy"],
            "forbidden_tools": ["query_clickhouse"],
            "reference_solution_id": "REF-C01",
        })
        model = ScriptedModel([{"type": "final", "content": final_payload()}])
        BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [],
            policy_fn=lambda **_kwargs: [],
        )(task, 1, None)

        self.assertEqual(model.tool_surfaces, [("retrieve_policy",)])

    def test_unknown_tool_request_fails_closed(self):
        from src.evals.system_benchmark.local_worker import (
            BoundedLocalExecutor,
            LocalWorkerError,
        )

        model = ScriptedModel([
            {"type": "tool_call", "name": "shell", "arguments": {"cmd": "cat evals/system_benchmark/development_tasks.json"}}
        ])
        executor = BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [],
            policy_fn=lambda **_kwargs: [],
        )

        with self.assertRaisesRegex(LocalWorkerError, "not exposed"):
            executor(sb_d01(), 1, None)

    def test_policy_evidence_refs_come_from_actual_retrieval(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor

        model = ScriptedModel([
            {
                "type": "tool_call",
                "name": "retrieve_policy",
                "arguments": {"query": "blocker rate definition"},
            },
            {
                "type": "final",
                "content": final_payload(
                    evidence_refs=["policy:invented@99#answer-key"],
                ),
            },
        ])
        executor = BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [],
            policy_fn=lambda **_kwargs: [
                PolicyEvidence(
                    document_id="kpi-dictionary",
                    document_version="1.0",
                    section_id="blocker-rate",
                    excerpt="Blocker Rate: blocked items divided by active items.",
                    effective_date="2026-01-01",
                    status="current",
                )
            ],
        )

        execution = executor(sb_d01(), 1, None)

        self.assertEqual(
            execution.response.evidence_refs,
            ("policy:kpi-dictionary@1.0#blocker-rate",),
        )

    def test_structured_values_come_only_from_actual_query_rows(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor

        model = ScriptedModel([
            {
                "type": "tool_call",
                "name": "query_clickhouse",
                "arguments": {"sql": "SELECT team, 20.9 AS blocked_pct FROM agentic_analytics.delivery_work_items LIMIT 1"},
            },
            {
                "type": "final",
                "content": final_payload(
                    observed_values={"team": "Fake", "blocked_pct": 0},
                ),
            },
        ])
        executor = BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [{"team": "Data", "blocked_pct": 20.9}],
            policy_fn=lambda **_kwargs: [],
        )

        execution = executor(sb_d01(), 1, None)

        self.assertEqual(
            dict(execution.observation.structured_values),
            {"team": "Data", "blocked_pct": 20.9},
        )

    def test_trial_execution_is_runner_compatible(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
        from src.evals.system_benchmark.runner import TrialExecution

        model = ScriptedModel([{"type": "final", "content": final_payload()}])
        execution = BoundedLocalExecutor(
            model=model,
            query_fn=lambda _sql: [],
            policy_fn=lambda **_kwargs: [],
        )(sb_d01(), 1, None)

        self.assertIsInstance(execution, TrialExecution)
        self.assertEqual(execution.route_decision, oracle_route(sb_d01()))
        self.assertEqual(execution.model_calls, 1)

    def test_default_model_is_local_qwen35(self):
        from src.evals.system_benchmark.local_worker import DEFAULT_LOCAL_MODEL

        self.assertEqual(DEFAULT_LOCAL_MODEL, "hermes-local:qwen3.5-9b")


if __name__ == "__main__":
    unittest.main()
