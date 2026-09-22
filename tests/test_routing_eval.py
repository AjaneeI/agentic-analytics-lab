import json
import tempfile
import unittest
from pathlib import Path

from src.evals.routing_eval import (
    RoutingFixture,
    evaluate_routing,
    load_routing_fixtures,
)
from src.routing.control_plane import ExecutionRoute, TaskContext


class TestRoutingEvaluation(unittest.TestCase):
    def test_repository_fixture_set_matches_v0_contract(self):
        fixtures = load_routing_fixtures("evals/routing_fixtures.json")
        result = evaluate_routing(fixtures)

        self.assertGreaterEqual(result.total, 12)
        self.assertEqual(result.correct, result.total)
        self.assertEqual(result.accuracy, 1.0)
        self.assertEqual(result.false_cheap_routes, 0)
        self.assertEqual(result.unnecessary_escalations, 0)
        self.assertEqual(result.mismatches, ())

    def test_confusion_matrix_and_false_cheap_are_reported(self):
        fixtures = [
            RoutingFixture(
                fixture_id="X1",
                description="Expected escalation but router chooses local",
                context=TaskContext(
                    task_type="reasoning",
                    requires_tool=False,
                    evidence_required=False,
                ),
                expected_route=ExecutionRoute.ESCALATE,
            )
        ]

        result = evaluate_routing(fixtures)

        self.assertEqual(result.correct, 0)
        self.assertEqual(result.false_cheap_routes, 1)
        self.assertEqual(result.unnecessary_escalations, 0)
        self.assertEqual(result.confusion_matrix["escalate"]["local"], 1)

    def test_unnecessary_escalation_is_reported(self):
        fixtures = [
            RoutingFixture(
                fixture_id="X2",
                description="Expected local but ambiguity forces escalation",
                context=TaskContext(
                    task_type="reasoning",
                    requires_tool=False,
                    evidence_required=False,
                    ambiguity_detected=True,
                ),
                expected_route=ExecutionRoute.LOCAL,
            )
        ]

        result = evaluate_routing(fixtures)

        self.assertEqual(result.unnecessary_escalations, 1)
        self.assertEqual(result.false_cheap_routes, 0)

    def test_empty_fixture_list_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "At least one"):
            evaluate_routing([])

    def test_duplicate_fixture_ids_are_rejected(self):
        payload = [
            {
                "id": "R1",
                "description": "first",
                "task_type": "lookup",
                "requires_tool": True,
                "evidence_required": True,
                "expected_route": "local"
            },
            {
                "id": "R1",
                "description": "second",
                "task_type": "lookup",
                "requires_tool": True,
                "evidence_required": True,
                "expected_route": "local"
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "fixtures.json"
            path.write_text(json.dumps(payload))

            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_routing_fixtures(path)

    def test_invalid_expected_route_is_rejected(self):
        payload = [
            {
                "id": "R1",
                "description": "bad route",
                "task_type": "lookup",
                "requires_tool": True,
                "evidence_required": True,
                "expected_route": "bypass"
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "fixtures.json"
            path.write_text(json.dumps(payload))

            with self.assertRaisesRegex(ValueError, "Unsupported execution route"):
                load_routing_fixtures(path)


if __name__ == "__main__":
    unittest.main()
