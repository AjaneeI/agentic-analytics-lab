"""Ollama adapter for the provider-agnostic agent interface."""

from __future__ import annotations

import json
import urllib.request
from typing import Any


class OllamaModelClient:
    def __init__(
        self,
        model: str = "qwen2.5:7b",
        base_url: str = "http://127.0.0.1:11434",
        timeout: int = 120,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @staticmethod
    def _convert_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in tools
        ]

    @staticmethod
    def _convert_messages(
        messages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        converted = []

        for message in messages:
            role = message["role"]

            if role in {"system", "user"}:
                converted.append(
                    {"role": role, "content": message["content"]}
                )

            elif role == "tool":
                converted.append(
                    {"role": "tool", "content": message["content"]}
                )

            elif role == "assistant":
                content = message.get("content", "")

                try:
                    parsed = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    converted.append(
                        {"role": "assistant", "content": content}
                    )
                    continue

                if parsed.get("type") == "tool_call":
                    converted.append(
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "function": {
                                        "name": parsed["name"],
                                        "arguments": parsed["arguments"],
                                    }
                                }
                            ],
                        }
                    )
                else:
                    converted.append(
                        {"role": "assistant", "content": content}
                    )

        return converted

    def respond(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "temperature": 0,
                "num_predict": 192,
                "num_ctx": 4096,
            },
            "messages": self._convert_messages(messages),
            "tools": self._convert_tools(tools),
        }

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(
            request,
            timeout=self.timeout,
        ) as response:
            result = json.load(response)

        message = result.get("message", {})
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            function = tool_calls[0].get("function", {})
            arguments = function.get("arguments", {})

            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            return {
                "type": "tool_call",
                "name": function.get("name"),
                "arguments": arguments,
            }

        return {
            "type": "final",
            "content": message.get("content", ""),
        }
