import unittest

from src.agents.single_agent import AgentResult
from src.routing.oracle_benchmark import (
    OracleMetadataRoutedAgent,
    build_oracle_case_specs,
)


QUESTIONS = [
    {
        "id": "Q1",
        "category": "retrieval",
        "question": "Which team has the highest blocker rate?",
        "requires_tool": True,
        "expected": {"team": "DO_NOT_USE_THIS"},
    },
    {
        "id": "Q6",
        "category": "epistemic",
        "question": "Can this dataset establish causality?",
        "requires_tool": False,
        "expected_behavior": ["DO_NOT_USE_THIS_EITHER"],
    },
]

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


class StubLocalWorker:
    def __init__(self):
        self.questions = []

    def run(self, question):
        self.questions.append(question)
        return AgentResult(
            answer=(
                "No. Observational association does not establish causality; "
                "a randomized or stronger study design would be needed."
            ),
            model_call_count=1,
            input_tokens=40,
            output_tokens=20,
        )


class TestOracleMetadataRoutedAgent(unittest.TestCase):
    def test_specs_ignore_expected_answer_fields(self):
        altered = [dict(case) for case in QUESTIONS]
        altered[0]["expected"] = {"team": "Anything", "blocked_pct": -999}
        altered[1]["expected_behavior"] = ["anything"]

        self.assertEqual(
            build_oracle_case_specs(QUESTIONS),
            build_oracle_case_specs(altered),
        )

    def test_retrieval_case_routes_to_deterministic_handler(self):
        worker = StubLocalWorker()
        agent = OracleMetadataRoutedAgent(
            questions=QUESTIONS,
            local_worker=worker,
            query_fn=lambda _sql: ROWS,
        )

        result = agent.run(QUESTIONS[0]["question"])

        self.assertIn("Data", result.answer)
        self.assertEqual(result.model_call_count, 0)
        self.assertEqual(worker.questions, [])
        telemetry = agent.route_telemetry_by_task["Q1"]
        self.assertEqual(telemetry.route, "deterministic")
        self.assertEqual(telemetry.worker_input_tokens, 0)

    def test_epistemic_case_routes_to_existing_local_worker(self):
        worker = StubLocalWorker()
        agent = OracleMetadataRoutedAgent(
            questions=QUESTIONS,
            local_worker=worker,
            query_fn=lambda _sql: ROWS,
        )

        result = agent.run(QUESTIONS[1]["question"])

        self.assertEqual(worker.questions, [QUESTIONS[1]["question"]])
        self.assertEqual(result.model_call_count, 1)
        telemetry = agent.route_telemetry_by_task["Q6"]
        self.assertEqual(telemetry.route, "local")
        self.assertEqual(telemetry.worker_input_tokens, 40)
        self.assertEqual(telemetry.worker_output_tokens, 20)

    def test_unknown_question_fails_instead_of_guessing_metadata(self):
        agent = OracleMetadataRoutedAgent(
            questions=QUESTIONS,
            local_worker=StubLocalWorker(),
            query_fn=lambda _sql: ROWS,
        )

        with self.assertRaisesRegex(RuntimeError, "not present"):
            agent.run("A question outside the frozen suite")

    def test_duplicate_question_text_is_rejected(self):
        duplicate = [dict(QUESTIONS[0]), dict(QUESTIONS[0])]
        duplicate[1]["id"] = "QX"

        with self.assertRaisesRegex(ValueError, "unique"):
            build_oracle_case_specs(duplicate)

    def test_empty_suite_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "At least one"):
            build_oracle_case_specs([])


if __name__ == "__main__":
    unittest.main()
