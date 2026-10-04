import unittest

from src.evals.system_benchmark.contracts import (
    BenchmarkExecutionRoute,
    CapabilityProfile,
    ResponseDisposition,
    SystemBenchmarkResponse,
    parse_task_contract,
)


def task_payload(**updates):
    payload = {
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
        "expected_values": [{"name": "team", "value": "Data"}],
        "required_claims": ["identify the team and blocker rate"],
        "forbidden_claims": ["claim blockers cause lateness"],
        "required_clarification_concept": None,
        "required_handoff_fields": [],
        "allowed_tools": ["query_clickhouse", "retrieve_policy"],
        "forbidden_tools": [],
        "reference_solution_id": "REF-D01",
    }
    payload.update(updates)
    return payload


class TestSystemBenchmarkRouting(unittest.TestCase):
    def test_oracle_route_uses_contract_metadata_exactly(self):
        from src.evals.system_benchmark.routing import oracle_route

        task = parse_task_contract(task_payload())
        decision = oracle_route(task)

        self.assertEqual(decision.route, BenchmarkExecutionRoute.DETERMINISTIC)
        self.assertEqual(decision.capability_profile, CapabilityProfile.MULTI_SOURCE)
        self.assertEqual(decision.reason_code, "oracle_metadata")

    def test_natural_language_router_receives_only_request_text(self):
        from src.evals.system_benchmark.routing import natural_language_route

        seen = []

        class Result:
            route = "local"
            reason = "test"

        def classifier(value):
            seen.append(value)
            return Result()

        task = parse_task_contract(task_payload(
            family="C",
            request="According to the current KPI dictionary, how is blocker rate defined?",
            expected_route="local",
            expected_capability_profile="documents",
            required_evidence_source_types=["policy"],
            acceptable_source_ids=["kpi-dictionary"],
            expected_values=[],
            required_claims=["state the blocker-rate definition"],
            allowed_tools=["retrieve_policy"],
            forbidden_tools=["query_clickhouse"],
            reference_solution_id="REF-C01",
        ))

        decision = natural_language_route(task.request, classifier=classifier)

        self.assertEqual(seen, [task.request])
        self.assertEqual(decision.route, BenchmarkExecutionRoute.LOCAL)
        self.assertEqual(decision.capability_profile, CapabilityProfile.DOCUMENTS)
        self.assertNotIn(task.case_id, repr(seen))
        self.assertNotIn(task.family.value, repr(seen))

    def test_simple_heuristic_detects_multi_source_request(self):
        from src.evals.system_benchmark.routing import simple_heuristic_route

        decision = simple_heuristic_route(
            "Identify the highest blocker-rate team and interpret it using the KPI definition."
        )
        self.assertEqual(decision.capability_profile, CapabilityProfile.MULTI_SOURCE)

    def test_unsupported_source_escalates_without_fabricated_capability(self):
        from src.evals.system_benchmark.routing import simple_heuristic_route

        decision = simple_heuristic_route(
            "Use private CRM notes to explain why the Data team is blocked."
        )
        self.assertEqual(decision.route, BenchmarkExecutionRoute.ESCALATE)
        self.assertEqual(decision.capability_profile, CapabilityProfile.NONE)
        self.assertEqual(decision.escalation_mode, "unsupported_source")

    def test_route_metrics_are_independent_of_worker_outcome(self):
        from src.evals.system_benchmark.routing import (
            RoutingDecision,
            evaluate_route_decisions,
        )

        task = parse_task_contract(task_payload())
        wrong_but_more_expensive = RoutingDecision(
            route=BenchmarkExecutionRoute.LOCAL,
            capability_profile=CapabilityProfile.MULTI_SOURCE,
            reason_code="test_alternate_route",
        )
        metrics = evaluate_route_decisions([(task, wrong_but_more_expensive)])

        self.assertEqual(metrics.total, 1)
        self.assertEqual(metrics.route_accuracy, 0.0)
        self.assertEqual(metrics.capability_profile_accuracy, 1.0)
        self.assertEqual(metrics.false_cheap_routes, 0)

    def test_oracle_route_matches_all_current_development_contracts(self):
        from pathlib import Path
        from src.evals.system_benchmark.loader import load_tasks
        from src.evals.system_benchmark.routing import oracle_route, evaluate_route_decisions

        root = Path(__file__).resolve().parents[2]
        tasks = load_tasks(root / "evals/system_benchmark/development_tasks.json")
        metrics = evaluate_route_decisions((task, oracle_route(task)) for task in tasks)

        self.assertEqual(metrics.total, 7)
        self.assertEqual(metrics.route_accuracy, 1.0)
        self.assertEqual(metrics.capability_profile_accuracy, 1.0)
        self.assertEqual(metrics.false_cheap_routes, 0)
        self.assertEqual(metrics.unsupported_source_misses, 0)

    def test_route_inference_requires_no_worker(self):
        from src.evals.system_benchmark.routing import simple_heuristic_route

        decision = simple_heuristic_route("Can this dataset prove blockers cause lateness?")
        self.assertEqual(decision.route, BenchmarkExecutionRoute.LOCAL)
        self.assertEqual(decision.capability_profile, CapabilityProfile.NONE)


class TestSystemBenchmarkWorkerAdapters(unittest.TestCase):
    def test_strong_single_agent_receives_both_safe_tools(self):
        from src.evals.system_benchmark.workers import build_strong_single_invocation

        task = parse_task_contract(task_payload())
        invocation = build_strong_single_invocation(task)
        self.assertEqual(
            invocation.allowed_tools,
            ("query_clickhouse", "retrieve_policy"),
        )

    def test_oracle_worker_uses_capability_tool_boundary(self):
        from src.evals.system_benchmark.routing import oracle_route
        from src.evals.system_benchmark.workers import build_worker_invocation

        task = parse_task_contract(task_payload(
            family="C",
            expected_route="local",
            expected_capability_profile="documents",
            required_evidence_source_types=["policy"],
            acceptable_source_ids=["kpi-dictionary"],
            expected_values=[],
            required_claims=["state definition"],
            allowed_tools=["retrieve_policy"],
            forbidden_tools=["query_clickhouse"],
            reference_solution_id="REF-C01",
        ))
        invocation = build_worker_invocation(task, oracle_route(task))
        self.assertEqual(invocation.allowed_tools, ("retrieve_policy",))

    def test_misrouted_worker_never_expands_task_tool_boundary(self):
        from src.evals.system_benchmark.routing import RoutingDecision
        from src.evals.system_benchmark.workers import build_worker_invocation

        task = parse_task_contract(task_payload(
            id="SB-C01",
            family="C",
            expected_route="local",
            expected_capability_profile="documents",
            required_evidence_source_types=["policy"],
            acceptable_source_ids=["kpi-dictionary"],
            expected_values=[],
            required_claims=["state definition"],
            allowed_tools=["retrieve_policy"],
            forbidden_tools=["query_clickhouse"],
            reference_solution_id="REF-C01",
        ))
        wrong_route = RoutingDecision(
            route=BenchmarkExecutionRoute.LOCAL,
            capability_profile=CapabilityProfile.MULTI_SOURCE,
            reason_code="wrong_capability",
        )
        invocation = build_worker_invocation(task, wrong_route)
        self.assertEqual(invocation.allowed_tools, ("retrieve_policy",))

    def test_worker_execution_can_run_from_oracle_route_without_router(self):
        from src.evals.system_benchmark.routing import oracle_route
        from src.evals.system_benchmark.workers import execute_worker

        task = parse_task_contract(task_payload())
        seen = []

        def worker(invocation):
            seen.append(invocation)
            return SystemBenchmarkResponse(
                disposition=ResponseDisposition.ANSWER,
                answer_text="Data has the highest blocker rate.",
                evidence_refs=(
                    "structured:delivery_work_items",
                    "policy:kpi-dictionary@1.0#blocker-rate",
                ),
            )

        response = execute_worker(task, oracle_route(task), worker)
        self.assertEqual(response.disposition, ResponseDisposition.ANSWER)
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].case_id, task.case_id)

    def test_family_h_must_return_handoff_after_bounded_evidence(self):
        from src.evals.system_benchmark.routing import oracle_route
        from src.evals.system_benchmark.workers import WorkerBoundaryError, execute_worker

        task = parse_task_contract(task_payload(
            id="SB-H01",
            family="H",
            request="May the incident commander authorize the exception?",
            expected_route="escalate",
            expected_capability_profile="documents",
            allowed_dispositions=["handoff"],
            forbidden_dispositions=["answer", "clarify", "unsupported"],
            required_evidence_source_types=["policy"],
            acceptable_source_ids=["escalation-policy", "service-level-policy"],
            expected_values=[],
            required_claims=[],
            forbidden_claims=["silently choose one conflicting policy"],
            required_handoff_fields=[
                "trigger", "evidence_refs", "actions_taken",
                "unresolved_uncertainty", "requested_authority",
            ],
            allowed_tools=["retrieve_policy"],
            forbidden_tools=["query_clickhouse"],
            reference_solution_id="REF-H01",
        ))

        def bad_worker(_invocation):
            return SystemBenchmarkResponse(
                disposition=ResponseDisposition.ANSWER,
                answer_text="Approved.",
                evidence_refs=("policy:escalation-policy@1.0#p1-temporary-authority",),
            )

        with self.assertRaisesRegex(WorkerBoundaryError, "handoff"):
            execute_worker(task, oracle_route(task), bad_worker)

    def test_unsupported_source_worker_cannot_fabricate_evidence(self):
        from src.evals.system_benchmark.routing import oracle_route
        from src.evals.system_benchmark.workers import WorkerBoundaryError, execute_worker

        task = parse_task_contract(task_payload(
            id="SB-G01",
            family="G",
            request="Use private CRM notes.",
            expected_route="escalate",
            expected_capability_profile="none",
            allowed_dispositions=["unsupported"],
            forbidden_dispositions=["answer", "clarify", "handoff"],
            required_evidence_source_types=[],
            acceptable_source_ids=[],
            expected_values=[],
            required_claims=[],
            forbidden_claims=["invent CRM evidence"],
            allowed_tools=[],
            forbidden_tools=["query_clickhouse", "retrieve_policy"],
            reference_solution_id="REF-G01",
        ))

        def bad_worker(_invocation):
            return SystemBenchmarkResponse(
                disposition=ResponseDisposition.UNSUPPORTED,
                answer_text="CRM is unavailable.",
                evidence_refs=("crm:invented",),
            )

        with self.assertRaisesRegex(WorkerBoundaryError, "evidence"):
            execute_worker(task, oracle_route(task), bad_worker)


if __name__ == "__main__":
    unittest.main()
