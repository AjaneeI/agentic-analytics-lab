"""Offline adapter behavior: scripted models and injected query results only."""

from dataclasses import replace
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from src.evals.system_benchmark.contracts import (
    ResponseDisposition, StructuredExpectation, TrajectoryContract,
)
from src.evals.system_benchmark.loader import load_tasks
from src.evals.system_benchmark.references import load_references
from src.evals.system_benchmark.runner import run_trial
from tests.system_benchmark.test_local_worker import ScriptedModel, final_payload


ROOT = Path(__file__).resolve().parents[2]


def development_cases():
    return {task.case_id: task for task in load_tasks(
        ROOT / "evals/system_benchmark/development_tasks.json"
    )}


def tool_call(name, **arguments):
    return {"type": "tool_call", "name": name, "arguments": arguments}


def final(**extra):
    return {"type": "final", "content": final_payload(**extra)}


class TestStrongSingleExecutor(unittest.TestCase):
    def setUp(self):
        self.tasks = development_cases()

    def make_executor(self, model, **kwargs):
        from src.evals.system_benchmark.baselines import StrongSingleExecutor
        return StrongSingleExecutor(model=model, model_id="offline-script", **kwargs)

    def test_model_configuration_is_required_and_does_not_replace_default(self):
        from src.evals.system_benchmark.baselines import StrongSingleExecutor
        from src.evals.system_benchmark.local_worker import DEFAULT_LOCAL_MODEL
        with self.assertRaises(TypeError):
            StrongSingleExecutor(model=ScriptedModel([]))
        for model_id in ("", " ", None):
            with self.subTest(model_id=model_id), self.assertRaises(ValueError):
                StrongSingleExecutor(model=ScriptedModel([]), model_id=model_id)
        with self.assertRaises(ValueError):
            StrongSingleExecutor(model=None, model_id="offline-script")
        self.assertEqual(DEFAULT_LOCAL_MODEL, "hermes-local:qwen3.5-9b")

    def test_declared_model_must_match_client_identifier_when_available(self):
        model = ScriptedModel([])
        model.model = "client-model"
        with self.assertRaises(ValueError):
            self.make_executor(model)

    def test_falsey_model_cannot_trigger_implicit_runtime_fallback(self):
        class FalseyModel(ScriptedModel):
            def __bool__(self):
                return False
        with patch("src.evals.system_benchmark.local_worker.OllamaModelClient") as constructor:
            with self.assertRaises(ValueError):
                self.make_executor(FalseyModel([]))
        constructor.assert_not_called()

    def test_handoff_retrieves_real_policy_evidence_without_query_permission(self):
        from src.tools.policy_retrieval import retrieve_policy
        task = self.tasks["SB-H01"]
        query = Mock(side_effect=AssertionError("must not execute"))
        model = ScriptedModel([
            tool_call("retrieve_policy", query="escalation-policy", top_k=5),
            final(disposition="handoff", answer_text="Applicable policy authority conflicts; request service-owner resolution.", handoff={
                "trigger": "P1 authority conflict", "evidence_refs": ["runtime supplied evidence"],
                "actions_taken": "Retrieved applicable escalation policy.",
                "unresolved_uncertainty": "Service-owner approval conflicts with temporary authority.",
                "requested_authority": "service owner",
            }),
        ])
        execution = self.make_executor(model, query_fn=query, policy_fn=retrieve_policy)(task, 1, None)
        self.assertEqual(execution.response.disposition, ResponseDisposition.HANDOFF)
        self.assertIn("policy:escalation-policy@1.0#p1-temporary-authority", execution.response.evidence_refs)
        self.assertEqual(execution.observation.tool_calls, ("retrieve_policy",))
        query.assert_not_called()

    def test_both_tool_schemas_match_routed_runtime_without_oracle_routing(self):
        from src.evals.system_benchmark.local_worker import BoundedLocalExecutor
        from src.evals.system_benchmark.routing import oracle_route
        task = self.tasks["SB-D01"]
        routed = ScriptedModel([final()])
        with patch.object(routed, "respond", wraps=routed.respond) as routed_call:
            BoundedLocalExecutor(model=routed)(task, 1, None)
        routed_tools = routed_call.call_args.args[1]
        strong = ScriptedModel([final()])
        with patch("src.evals.system_benchmark.routing.oracle_route", side_effect=AssertionError("oracle used")), \
             patch("src.evals.system_benchmark.routing.natural_language_route", side_effect=AssertionError("router used")), \
             patch.object(strong, "respond", wraps=strong.respond) as strong_call:
            execution = self.make_executor(strong)(task, 1, None)
        self.assertEqual(strong_call.call_args.args[1], routed_tools)
        self.assertEqual(strong.tool_surfaces, [("query_clickhouse", "retrieve_policy")])
        self.assertEqual(strong.message_batches, routed.message_batches)
        self.assertEqual(execution.route_decision.route.value, "local")
        self.assertEqual(execution.route_decision.reason_code, "strong_single_no_routing")
        self.assertNotEqual(execution.route_decision, oracle_route(task))

    def test_model_sees_request_and_shared_prompt_without_reference_metadata(self):
        task = replace(self.tasks["SB-A01"], case_id="SECRET-CASE",
                       reference_solution_id="SECRET-REF",
                       expected_values=(StructuredExpectation("team", "SECRET-TRUTH"),))
        model = ScriptedModel([final()])
        self.make_executor(model)(task, 1, None)
        rendered = json.dumps(model.message_batches)
        self.assertIn(task.request, rendered)
        for secret in ("SECRET-CASE", "SECRET-REF", "SECRET-TRUTH", "expected_route", "family"):
            self.assertNotIn(secret, rendered)

    def test_both_tool_affordances_do_not_permit_task_forbidden_execution(self):
        query = Mock(side_effect=AssertionError("must not execute"))
        policy = Mock(side_effect=AssertionError("must not execute"))
        model = ScriptedModel([tool_call("retrieve_policy", query="definition")])
        from src.evals.system_benchmark.local_worker import LocalWorkerError
        with self.assertRaises(LocalWorkerError):
            self.make_executor(model, query_fn=query, policy_fn=policy)(self.tasks["SB-A01"], 1, None)
        self.assertEqual(model.tool_surfaces, [("query_clickhouse", "retrieve_policy")])
        query.assert_not_called()
        policy.assert_not_called()

    def test_unsupported_source_has_no_executable_tools(self):
        query = Mock(side_effect=AssertionError("must not execute"))
        model = ScriptedModel([tool_call("query_clickhouse", sql="SELECT 1")])
        from src.evals.system_benchmark.local_worker import LocalWorkerError
        with self.assertRaises(LocalWorkerError):
            # Even an incorrectly widened task object cannot grant G access.
            task = replace(self.tasks["SB-G01"], allowed_tools=("query_clickhouse",), forbidden_tools=())
            self.make_executor(model, query_fn=query)(task, 1, None)
        query.assert_not_called()

    def test_unsupported_and_handoff_hard_bounds_are_preserved(self):
        from src.evals.system_benchmark.workers import WorkerBoundaryError
        for case_id in ("SB-G01", "SB-H01"):
            with self.subTest(case_id=case_id), self.assertRaises(WorkerBoundaryError):
                self.make_executor(ScriptedModel([final()]))(self.tasks[case_id], 1, None)
        result = self.make_executor(ScriptedModel([final(
            disposition="unsupported", answer_text="Private CRM is unavailable.",
            evidence_refs=["fabricated:CRM"],
        )]))(self.tasks["SB-G01"], 1, None)
        self.assertEqual(result.response.evidence_refs, ())

    def test_document_task_cannot_execute_query(self):
        from src.evals.system_benchmark.local_worker import LocalWorkerError
        query = Mock()
        with self.assertRaises(LocalWorkerError):
            self.make_executor(ScriptedModel([
                tool_call("query_clickhouse", sql="SELECT 1"),
            ]), query_fn=query)(self.tasks["SB-H01"], 1, None)
        query.assert_not_called()

    def test_tool_budget_and_real_observations_survive_adapter(self):
        from src.evals.system_benchmark.local_worker import LocalWorkerError
        sql = "SELECT team, blocked_pct FROM agentic_analytics.delivery_work_items"
        task = replace(self.tasks["SB-A01"], trajectory=TrajectoryContract(max_tool_calls=1))
        query = Mock(return_value=[{"team": "ObservedTeam", "blocked_pct": 31.2}])
        with self.assertRaises(LocalWorkerError):
            self.make_executor(ScriptedModel([
                tool_call("query_clickhouse", sql=sql), tool_call("query_clickhouse", sql=sql),
            ]), query_fn=query)(task, 1, None)
        self.assertEqual(query.call_count, 1)
        result = self.make_executor(ScriptedModel([
            tool_call("query_clickhouse", sql=sql), final(observed_values={"team": "invented"}),
        ]), query_fn=query)(task, 1, None)
        self.assertEqual(dict(result.observation.structured_values), {"team": "ObservedTeam", "blocked_pct": 31.2})
        self.assertEqual(result.observation.tool_call_records, ({"name": "query_clickhouse", "arguments": {"sql": sql}},))
        self.assertEqual(result.model_calls, 2)


class TestDeterministicSimpleExecutor(unittest.TestCase):
    def setUp(self):
        self.tasks = development_cases()

    @staticmethod
    def rows():
        return [
            {"team": "ObservedTeam", "total_items": 10, "blocked_items": 3,
             "blocker_rate": 30.0, "avg_effort_ratio": 1.2},
            {"team": "OtherTeam", "total_items": 10, "blocked_items": 1,
             "blocker_rate": 10.0, "avg_effort_ratio": 1.0},
        ]

    def test_approved_operation_reuses_handler_and_observed_values(self):
        from src.evals.system_benchmark.baselines import DeterministicSimpleExecutor
        from src.routing.deterministic_handlers import GROUPED_TEAM_METRICS_SQL
        query = Mock(return_value=self.rows())
        result = DeterministicSimpleExecutor(query_fn=query)(self.tasks["SB-A01"], 1, None)
        query.assert_called_once_with(GROUPED_TEAM_METRICS_SQL)
        self.assertEqual(result.response.disposition, ResponseDisposition.ANSWER)
        self.assertIn("ObservedTeam", result.response.answer_text)
        self.assertEqual(dict(result.observation.structured_values), {"team": "ObservedTeam", "blocked_pct": 30.0})
        self.assertEqual(result.response.evidence_refs, ("structured:delivery_work_items",))
        self.assertEqual(result.model_calls, 0)
        self.assertEqual(result.observation.tool_calls, ("query_clickhouse",))
        self.assertEqual(result.observation.tool_call_records[0]["arguments"], {"sql": GROUPED_TEAM_METRICS_SQL})

    def test_active_or_multi_source_or_unknown_requests_decline_before_tools(self):
        from src.evals.system_benchmark.baselines import DeterministicSimpleExecutor, DeterministicBaselineDeclined
        query = Mock()
        executor = DeterministicSimpleExecutor(query_fn=query)
        for task in self.tasks.values():
            if task.case_id == "SB-A01":
                continue
            with self.subTest(case_id=task.case_id), self.assertRaises(DeterministicBaselineDeclined):
                executor(task, 1, None)
        query.assert_not_called()

    def test_selection_and_answer_ignore_case_id_reference_and_expected_values(self):
        from src.evals.system_benchmark.baselines import DeterministicSimpleExecutor
        task = replace(self.tasks["SB-A01"], case_id="not-a-fixture-id",
                       request="  WHICH team has the highest blocker rate in the structured delivery dataset? ",
                       reference_solution_id="do-not-read",
                       expected_values=(StructuredExpectation("team", "invented"),))
        result = DeterministicSimpleExecutor(query_fn=lambda _sql: self.rows())(task, 1, None)
        self.assertEqual(result.observation.structured_values["team"], "ObservedTeam")

    def test_task_tool_boundary_and_zero_budget_reject_before_query(self):
        from src.evals.system_benchmark.baselines import DeterministicSimpleExecutor, DeterministicBaselineDeclined
        query = Mock()
        for task in (
            replace(self.tasks["SB-A01"], allowed_tools=()),
            replace(self.tasks["SB-A01"], forbidden_tools=("query_clickhouse",)),
            replace(self.tasks["SB-A01"], trajectory=TrajectoryContract(max_tool_calls=0)),
        ):
            with self.subTest(task=task), self.assertRaises(DeterministicBaselineDeclined):
                DeterministicSimpleExecutor(query_fn=query)(task, 1, None)
        query.assert_not_called()

    def test_no_unique_or_valid_result_declines_without_fabrication(self):
        from src.evals.system_benchmark.baselines import DeterministicSimpleExecutor, DeterministicBaselineDeclined
        cases = [[], [{"team": "x"}], [dict(self.rows()[0]), dict(self.rows()[0], team="Tie")],
                 [dict(self.rows()[0], blocker_rate=float("nan"))]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(DeterministicBaselineDeclined):
                DeterministicSimpleExecutor(query_fn=lambda _sql: rows)(self.tasks["SB-A01"], 1, None)

    def test_runner_scores_actual_output_and_does_not_substitute_reference_truth(self):
        from src.evals.system_benchmark.baselines import DeterministicSimpleExecutor
        references = {ref.reference_solution_id: ref for ref in load_references(
            ROOT / "evals/system_benchmark/development_references.json"
        )}
        task = self.tasks["SB-A01"]
        result = run_trial(task, references[task.reference_solution_id], trial_number=1,
                           executor=DeterministicSimpleExecutor(query_fn=lambda _sql: self.rows()))
        self.assertFalse(result["task_success"])
        self.assertEqual(result["structured_values"]["team"], "ObservedTeam")
        self.assertEqual(result["tool_call_count"], 1)
        self.assertEqual(result["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
