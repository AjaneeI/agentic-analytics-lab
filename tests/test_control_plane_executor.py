import unittest

from src.agents.single_agent import AgentResult
from src.routing.control_plane import ExecutionRoute, TaskContext
from src.routing.deterministic_handlers import HandlerKey
from src.routing.executor import (
    ExecutionRequest,
    basic_validation_context,
    execute_control_plane_request,
)
from src.routing.validation import ValidationContext, ValidationDisposition


ROWS = [
    {
        "team": "AI",
        "total_items": 120,
        "blocked_items": 18,
        "blocker_rate": 15.0,
        "avg_effort_ratio": 1.1666802146,
    },
    {
        "team": "Data",
        "total_items": 139,
        "blocked_items": 29,
        "blocker_rate": 20.9,
        "avg_effort_ratio": 1.1387180739,
    },
    {
        "team": "Platform",
        "total_items": 105,
        "blocked_items": 12,
        "blocker_rate": 11.4,
        "avg_effort_ratio": 1.0982895688,
    },
    {
        "team": "Product",
        "total_items": 136,
        "blocked_items": 20,
        "blocker_rate": 14.7,
        "avg_effort_ratio": 1.1113253012,
    },
]


class StubWorker:
    def __init__(self):
        self.calls = []

    def run(self, question):
        self.calls.append(question)
        return AgentResult(
            answer="A valid local answer.",
            model_call_count=2,
            input_tokens=25,
            output_tokens=8,
            model_duration_seconds=0.3,
        )


class TestControlPlaneExecutor(unittest.TestCase):
    def test_deterministic_route_uses_handler_without_model_calls(self):
        queries = []

        def query_fn(sql):
            queries.append(sql)
            return ROWS

        request = ExecutionRequest(
            task_id="Q1",
            question="Which team has the highest blocker rate?",
            context=TaskContext(
                task_type="retrieval",
                requires_tool=True,
                evidence_required=True,
                deterministic_handler_available=True,
            ),
            deterministic_handler=HandlerKey.BLOCKER_RATE_LEADER,
        )

        outcome = execute_control_plane_request(request, query_fn=query_fn)

        self.assertEqual(outcome.decision.route, ExecutionRoute.DETERMINISTIC)
        self.assertEqual(outcome.validation.disposition, ValidationDisposition.ACCEPT)
        self.assertFalse(outcome.requires_escalation)
        self.assertEqual(outcome.result.model_call_count, 0)
        self.assertEqual(outcome.result.tool_call_attempt_count, 1)
        self.assertEqual(len(outcome.result.tool_calls), 1)
        self.assertEqual(len(queries), 1)
        self.assertEqual(outcome.telemetry.worker, "blocker_rate_leader")

    def test_local_route_reuses_existing_worker_contract(self):
        worker = StubWorker()
        request = ExecutionRequest(
            task_id="Q6",
            question="Can this dataset establish causality?",
            context=TaskContext(
                task_type="epistemic",
                requires_tool=False,
                evidence_required=False,
            ),
        )

        outcome = execute_control_plane_request(
            request,
            local_worker=worker,
        )

        self.assertEqual(outcome.decision.route, ExecutionRoute.LOCAL)
        self.assertEqual(worker.calls, [request.question])
        self.assertEqual(outcome.result.model_call_count, 2)
        self.assertEqual(outcome.validation.disposition, ValidationDisposition.ACCEPT)
        self.assertEqual(outcome.telemetry.worker, "StubWorker")

    def test_initial_escalation_executes_no_worker(self):
        worker = StubWorker()
        request = ExecutionRequest(
            task_id="ambiguous",
            question="Compare these ambiguous metrics.",
            context=TaskContext(
                task_type="comparison",
                requires_tool=True,
                evidence_required=True,
                ambiguity_detected=True,
            ),
        )

        outcome = execute_control_plane_request(
            request,
            local_worker=worker,
        )

        self.assertEqual(outcome.decision.route, ExecutionRoute.ESCALATE)
        self.assertTrue(outcome.requires_escalation)
        self.assertIsNone(outcome.result)
        self.assertEqual(worker.calls, [])
        self.assertEqual(outcome.telemetry.escalation_reason, "AMBIGUOUS_TASK")

    def test_deterministic_decline_becomes_explicit_escalation(self):
        rows = [dict(row) for row in ROWS]
        rows[3]["avg_effort_ratio"] = 1.02

        request = ExecutionRequest(
            task_id="Q5",
            question="Which team is strongest on both metrics?",
            context=TaskContext(
                task_type="multi_metric",
                requires_tool=True,
                evidence_required=True,
                deterministic_handler_available=True,
            ),
            deterministic_handler=HandlerKey.DUAL_METRIC_LEADER,
        )

        outcome = execute_control_plane_request(
            request,
            query_fn=lambda _sql: rows,
        )

        self.assertTrue(outcome.requires_escalation)
        self.assertIsNone(outcome.result)
        self.assertEqual(
            outcome.telemetry.escalation_reason,
            "DETERMINISTIC_HANDLER_DECLINED",
        )

    def test_security_validation_fails_closed(self):
        worker = StubWorker()
        request = ExecutionRequest(
            task_id="security",
            question="Explain this.",
            context=TaskContext(
                task_type="explain",
                requires_tool=False,
                evidence_required=False,
            ),
        )

        def validator(_request, _result):
            return ValidationContext(
                output_valid=True,
                evidence_satisfied=True,
                evidence_required=False,
                security_boundary_violated=True,
            )

        outcome = execute_control_plane_request(
            request,
            local_worker=worker,
            validator=validator,
        )

        self.assertTrue(outcome.failed_closed)
        self.assertEqual(
            outcome.validation.disposition,
            ValidationDisposition.FAIL_CLOSED,
        )

    def test_retry_disposition_is_exposed_without_automatic_retry(self):
        worker = StubWorker()
        request = ExecutionRequest(
            task_id="retry",
            question="Try this task.",
            context=TaskContext(
                task_type="reasoning",
                requires_tool=False,
                evidence_required=False,
            ),
        )

        def validator(_request, _result):
            return ValidationContext(
                output_valid=False,
                evidence_satisfied=False,
                evidence_required=False,
                retryable_failure=True,
                retry_count=0,
                max_retries=1,
            )

        outcome = execute_control_plane_request(
            request,
            local_worker=worker,
            validator=validator,
        )

        self.assertTrue(outcome.requires_retry)
        self.assertFalse(outcome.requires_escalation)
        self.assertEqual(
            outcome.validation.disposition,
            ValidationDisposition.RETRY,
        )
        self.assertEqual(len(worker.calls), 1)

    def test_missing_deterministic_handler_is_configuration_error(self):
        request = ExecutionRequest(
            task_id="bad-config",
            question="Aggregate this.",
            context=TaskContext(
                task_type="aggregate",
                requires_tool=True,
                evidence_required=True,
                deterministic_handler_available=True,
            ),
        )

        with self.assertRaisesRegex(RuntimeError, "without a deterministic handler"):
            execute_control_plane_request(request, query_fn=lambda _sql: ROWS)

    def test_missing_local_worker_is_configuration_error(self):
        request = ExecutionRequest(
            task_id="bad-local",
            question="Explain this.",
            context=TaskContext(
                task_type="explain",
                requires_tool=False,
                evidence_required=False,
            ),
        )

        with self.assertRaisesRegex(RuntimeError, "without a local worker"):
            execute_control_plane_request(request)

    def test_basic_validator_requires_evidence_only_when_requested(self):
        result = AgentResult(answer="valid")
        no_evidence = ExecutionRequest(
            task_id="Q6",
            question="Epistemic question",
            context=TaskContext(
                task_type="epistemic",
                requires_tool=False,
                evidence_required=False,
            ),
        )
        requires_evidence = ExecutionRequest(
            task_id="Q1",
            question="Dataset question",
            context=TaskContext(
                task_type="retrieval",
                requires_tool=True,
                evidence_required=True,
            ),
        )

        self.assertFalse(
            basic_validation_context(no_evidence, result).evidence_required
        )
        self.assertTrue(
            basic_validation_context(requires_evidence, result).evidence_required
        )


if __name__ == "__main__":
    unittest.main()
