import unittest
from unittest.mock import patch

from src.agents.single_agent import SingleAgent


class FakeModel:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def respond(self, messages, tools):
        self.calls.append({"messages": list(messages), "tools": list(tools)})
        return self.responses.pop(0)


class TestSingleAgent(unittest.TestCase):
    @patch("src.agents.single_agent.query_clickhouse")
    def test_tool_call_then_final_answer_tracks_evidence_and_usage(self, mock_query):
        mock_query.return_value = [
            {"team": "Data", "blocked_pct": 20.9},
            {"team": "AI", "blocked_pct": 15.0},
        ]

        model = FakeModel(
            [
                {
                    "type": "tool_call",
                    "name": "query_clickhouse",
                    "arguments": {
                        "sql": (
                            "SELECT team, "
                            "round(100 * avg(blocked), 1) AS blocked_pct "
                            "FROM agentic_analytics.delivery_work_items "
                            "GROUP BY team "
                            "ORDER BY blocked_pct DESC"
                        )
                    },
                    "_metrics": {
                        "input_tokens": 50,
                        "output_tokens": 10,
                        "total_duration_seconds": 0.5,
                    },
                },
                {
                    "type": "final",
                    "content": (
                        "Data has the highest blocker rate at 20.9%, "
                        "compared with AI at 15.0%."
                    ),
                    "_metrics": {
                        "input_tokens": 80,
                        "output_tokens": 20,
                        "total_duration_seconds": 0.75,
                    },
                },
            ]
        )

        result = SingleAgent(model).run("Which team has the highest blocker rate?")

        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].row_count, 2)
        self.assertEqual(result.tool_calls[0].result_rows[0]["team"], "Data")
        self.assertEqual(result.model_call_count, 2)
        self.assertEqual(result.tool_call_attempt_count, 1)
        self.assertEqual(result.input_tokens, 130)
        self.assertEqual(result.output_tokens, 30)
        self.assertEqual(result.model_duration_seconds, 1.25)
        self.assertIn("Data", result.answer)
        self.assertIn("20.9", result.answer)
        mock_query.assert_called_once()

    def test_unknown_tool_rejected(self):
        model = FakeModel(
            [
                {
                    "type": "tool_call",
                    "name": "delete_everything",
                    "arguments": {},
                }
            ]
        )

        with self.assertRaisesRegex(RuntimeError, "Unknown tool"):
            SingleAgent(model).run("Delete the database.")

    def test_empty_final_answer_rejected(self):
        model = FakeModel([{"type": "final", "content": "   "}])

        with self.assertRaisesRegex(RuntimeError, "empty final answer"):
            SingleAgent(model).run("What happened?")

    def test_step_limit(self):
        model = FakeModel(
            [
                {
                    "type": "tool_call",
                    "name": "query_clickhouse",
                    "arguments": {"sql": "SELECT 1"},
                },
                {
                    "type": "tool_call",
                    "name": "query_clickhouse",
                    "arguments": {"sql": "SELECT 1"},
                },
            ]
        )

        with patch(
            "src.agents.single_agent.query_clickhouse",
            return_value=[{"1": 1}],
        ):
            with self.assertRaisesRegex(RuntimeError, "maximum"):
                SingleAgent(model, max_steps=2).run("Keep going forever.")


if __name__ == "__main__":
    unittest.main()
