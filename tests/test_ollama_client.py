import io
import json
import unittest
from unittest.mock import patch

from src.agents.ollama_client import OllamaModelClient


class FakeResponse:
    def __init__(self, payload):
        self.buffer = io.BytesIO(json.dumps(payload).encode())

    def __enter__(self):
        return self.buffer

    def __exit__(self, exc_type, exc, tb):
        self.buffer.close()


class TestOllamaModelClient(unittest.TestCase):
    @patch("src.agents.ollama_client.urllib.request.urlopen")
    def test_tool_call_response_includes_usage_metrics(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(
            {
                "message": {
                    "content": "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "query_clickhouse",
                                "arguments": {"sql": "SELECT 1"},
                            }
                        }
                    ],
                },
                "prompt_eval_count": 42,
                "eval_count": 7,
                "total_duration": 1_500_000_000,
            }
        )

        result = OllamaModelClient().respond(
            [{"role": "user", "content": "Query it."}],
            [
                {
                    "name": "query_clickhouse",
                    "description": "Read ClickHouse",
                    "input_schema": {
                        "type": "object",
                        "properties": {"sql": {"type": "string"}},
                        "required": ["sql"],
                    },
                }
            ],
        )

        self.assertEqual(result["type"], "tool_call")
        self.assertEqual(result["name"], "query_clickhouse")
        self.assertEqual(result["arguments"]["sql"], "SELECT 1")
        self.assertEqual(result["_metrics"]["input_tokens"], 42)
        self.assertEqual(result["_metrics"]["output_tokens"], 7)
        self.assertEqual(result["_metrics"]["total_duration_seconds"], 1.5)

    @patch("src.agents.ollama_client.urllib.request.urlopen")
    def test_final_response(self, mock_urlopen):
        mock_urlopen.return_value = FakeResponse(
            {"message": {"content": "Data has the highest blocker rate."}}
        )

        result = OllamaModelClient().respond(
            [{"role": "user", "content": "Which team?"}],
            [],
        )

        self.assertEqual(result["type"], "final")
        self.assertIn("Data", result["content"])

    def test_tool_schema_conversion(self):
        converted = OllamaModelClient._convert_tools(
            [
                {
                    "name": "query_clickhouse",
                    "description": "Read ClickHouse",
                    "input_schema": {"type": "object"},
                }
            ]
        )

        self.assertEqual(converted[0]["function"]["name"], "query_clickhouse")
        self.assertEqual(
            converted[0]["function"]["parameters"],
            {"type": "object"},
        )

    def test_internal_tool_message_conversion(self):
        converted = OllamaModelClient._convert_messages(
            [
                {
                    "role": "assistant",
                    "content": json.dumps(
                        {
                            "type": "tool_call",
                            "name": "query_clickhouse",
                            "arguments": {"sql": "SELECT 1"},
                        }
                    ),
                }
            ]
        )

        self.assertEqual(
            converted[0]["tool_calls"][0]["function"]["name"],
            "query_clickhouse",
        )


if __name__ == "__main__":
    unittest.main()
