import unittest

from src.routing.control_plane import (
    ExecutionRoute,
    ReasonCode,
    RouteDecision,
)
from src.routing.telemetry import build_route_telemetry
from src.routing.validation import (
    ValidationDisposition,
    ValidationReason,
    ValidationResult,
)


class TestRouteTelemetry(unittest.TestCase):
    def setUp(self):
        self.decision = RouteDecision(
            route=ExecutionRoute.DETERMINISTIC,
            task_type="aggregate",
            requires_tool=True,
            evidence_required=True,
            reason_code=ReasonCode.DETERMINISTIC_HANDLER,
        )

    def test_builds_machine_readable_record(self):
        validation = ValidationResult(
            disposition=ValidationDisposition.ACCEPT,
            reason=ValidationReason.VALIDATED,
        )

        record = build_route_telemetry(
            task_id="Q1",
            router_version="rules-v0",
            decision=self.decision,
            router_latency_seconds=0.002,
            validation=validation,
            worker="deterministic_aggregation",
            tool_calls=1,
            worker_input_tokens=120,
            worker_output_tokens=24,
            total_model_calls=1,
            total_latency_seconds=0.012,
            estimated_cost_usd=0.0,
            task_success=True,
        )

        self.assertEqual(record.route, "deterministic")
        self.assertEqual(record.route_reason_code, "DETERMINISTIC_HANDLER")
        self.assertEqual(record.validator_disposition, "accept")
        self.assertEqual(record.validator_reason, "VALIDATED")
        self.assertEqual(record.worker_input_tokens, 120)
        self.assertEqual(record.worker_output_tokens, 24)
        self.assertEqual(record.total_model_calls, 1)
        self.assertEqual(record.estimated_cost_usd, 0.0)

    def test_validation_can_be_absent_before_worker_finishes(self):
        record = build_route_telemetry(
            task_id="Q2",
            router_version="rules-v0",
            decision=self.decision,
            router_latency_seconds=0.001,
        )

        self.assertIsNone(record.validator_disposition)
        self.assertIsNone(record.validator_reason)
        self.assertIsNone(record.task_success)
        self.assertEqual(record.worker_input_tokens, 0)
        self.assertEqual(record.worker_output_tokens, 0)

    def test_empty_task_id_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "task_id"):
            build_route_telemetry(
                task_id=" ",
                router_version="rules-v0",
                decision=self.decision,
                router_latency_seconds=0.0,
            )

    def test_negative_router_latency_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "router_latency_seconds"):
            build_route_telemetry(
                task_id="Q3",
                router_version="rules-v0",
                decision=self.decision,
                router_latency_seconds=-0.001,
            )

    def test_negative_worker_tokens_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "worker_input_tokens"):
            build_route_telemetry(
                task_id="Q3b",
                router_version="rules-v0",
                decision=self.decision,
                router_latency_seconds=0.001,
                worker_input_tokens=-1,
            )

    def test_negative_cost_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "estimated_cost_usd"):
            build_route_telemetry(
                task_id="Q4",
                router_version="rules-v0",
                decision=self.decision,
                router_latency_seconds=0.001,
                estimated_cost_usd=-0.01,
            )


if __name__ == "__main__":
    unittest.main()
