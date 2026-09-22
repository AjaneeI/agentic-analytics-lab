import unittest

from src.routing.control_plane import (
    ExecutionRoute,
    ReasonCode,
    RouteFeatures,
    TaskContext,
    classify_route,
    extract_route_features,
    parse_execution_route,
    route_task,
)


class TestControlPlaneClassifier(unittest.TestCase):
    def test_feature_extraction_normalizes_explicit_fields(self):
        features = extract_route_features(
            TaskContext(
                task_type="  Aggregate  ",
                requires_tool=True,
                evidence_required=True,
                known_failure_category="  Missing Evidence ",
            )
        )

        self.assertEqual(features.task_type, "aggregate")
        self.assertEqual(features.known_failure_category, "missing evidence")

    def test_empty_task_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "task_type"):
            extract_route_features(
                TaskContext(
                    task_type="   ",
                    requires_tool=False,
                    evidence_required=False,
                )
            )

    def test_deterministic_handler_is_cheapest_route_when_safe(self):
        decision = route_task(
            TaskContext(
                task_type="aggregate",
                requires_tool=True,
                evidence_required=True,
                deterministic_handler_available=True,
            )
        )

        self.assertEqual(decision.route, ExecutionRoute.DETERMINISTIC)
        self.assertEqual(decision.reason_code, ReasonCode.DETERMINISTIC_HANDLER)
        self.assertIsNone(decision.confidence)

    def test_routine_reasoning_defaults_to_local_worker(self):
        decision = route_task(
            TaskContext(
                task_type="explain",
                requires_tool=False,
                evidence_required=False,
            )
        )

        self.assertEqual(decision.route, ExecutionRoute.LOCAL)
        self.assertEqual(decision.reason_code, ReasonCode.LOCAL_ROUTINE_REASONING)

    def test_ambiguity_escalates_before_deterministic_handler(self):
        decision = route_task(
            TaskContext(
                task_type="compare",
                requires_tool=True,
                evidence_required=True,
                deterministic_handler_available=True,
                ambiguity_detected=True,
            )
        )

        self.assertEqual(decision.route, ExecutionRoute.ESCALATE)
        self.assertEqual(decision.reason_code, ReasonCode.AMBIGUOUS_TASK)

    def test_prior_validation_failure_has_highest_precedence(self):
        decision = route_task(
            TaskContext(
                task_type="aggregate",
                requires_tool=True,
                evidence_required=True,
                deterministic_handler_available=True,
                ambiguity_detected=True,
                prior_validation_failed=True,
            )
        )

        self.assertEqual(decision.route, ExecutionRoute.ESCALATE)
        self.assertEqual(decision.reason_code, ReasonCode.PRIOR_VALIDATION_FAILURE)

    def test_required_unsupported_tool_escalates(self):
        decision = route_task(
            TaskContext(
                task_type="lookup",
                requires_tool=True,
                evidence_required=True,
                tool_supported=False,
            )
        )

        self.assertEqual(decision.route, ExecutionRoute.ESCALATE)
        self.assertEqual(decision.reason_code, ReasonCode.UNSUPPORTED_TOOL)

    def test_unsupported_tool_does_not_matter_when_no_tool_is_required(self):
        decision = route_task(
            TaskContext(
                task_type="explain",
                requires_tool=False,
                evidence_required=False,
                tool_supported=False,
            )
        )

        self.assertEqual(decision.route, ExecutionRoute.LOCAL)

    def test_classifier_can_be_called_with_precomputed_features(self):
        decision = classify_route(
            RouteFeatures(
                task_type="lookup",
                requires_tool=True,
                evidence_required=True,
                deterministic_handler_available=True,
                ambiguity_detected=False,
                prior_validation_failed=False,
                tool_supported=True,
                known_failure_category=None,
            )
        )

        self.assertEqual(decision.route, ExecutionRoute.DETERMINISTIC)

    def test_unknown_external_route_label_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "Unsupported execution route"):
            parse_execution_route("admin-bypass")


if __name__ == "__main__":
    unittest.main()
