import json
import tempfile
import unittest
from pathlib import Path

from src.evals.natural_language_routing import (
    evaluate_natural_language_routing,
    load_natural_language_fixtures,
)
from src.routing.control_plane import ExecutionRoute
from src.routing.natural_language_baseline import classify_natural_language


class TestNaturalLanguageRouting(unittest.TestCase):
    def test_repository_dev_set_matches_lexical_baseline(self):
        fixtures = load_natural_language_fixtures(
            "evals/natural_language_routing_dev.json"
        )
        result = evaluate_natural_language_routing(
            fixtures,
            classify_natural_language,
        )

        self.assertEqual(result.total, 15)
        self.assertEqual(result.correct, result.total)
        self.assertEqual(result.false_cheap_routes, 0)
        self.assertEqual(result.unnecessary_escalations, 0)

    def test_classifier_uses_free_text_only(self):
        decision = classify_natural_language(
            "Rank the delivery teams by blocker percentage."
        )

        self.assertEqual(decision.route, ExecutionRoute.DETERMINISTIC)
        self.assertEqual(decision.reason, "bounded_structured_analytics")

    def test_unsupported_source_escalates(self):
        decision = classify_natural_language(
            "Compare this with our Jira project data."
        )

        self.assertEqual(decision.route, ExecutionRoute.ESCALATE)
        self.assertEqual(decision.reason, "unsupported_external_source")

    def test_causal_question_stays_local(self):
        decision = classify_natural_language(
            "Can this dataset prove blockers cause lateness?"
        )

        self.assertEqual(decision.route, ExecutionRoute.LOCAL)

    def test_duplicate_ids_are_rejected(self):
        payload = [
            {
                "id": "N1",
                "prompt": "First",
                "expected_route": "local",
                "rationale": "first"
            },
            {
                "id": "N1",
                "prompt": "Second",
                "expected_route": "local",
                "rationale": "second"
            }
        ]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixtures.json"
            path.write_text(json.dumps(payload))

            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_natural_language_fixtures(path)

    def test_empty_prompt_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            classify_natural_language("  ")


if __name__ == "__main__":
    unittest.main()
