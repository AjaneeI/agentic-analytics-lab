"""ASSERT callable adapter for the bounded Q3 evaluation slice."""

from __future__ import annotations

import os
from typing import Any

from src.agents.ollama_client import OllamaModelClient
from src.agents.single_agent import SingleAgent


DEFAULT_MODEL = "qwen2.5:7b"


def chat(
    message: str,
    history: list[dict[str, Any]] | None = None,
) -> str:
    """Run the existing single-agent baseline behind ASSERT's callable boundary.

    ASSERT supplies generated prompts through `message`. The existing agent owns
    its system prompt, read-only ClickHouse tool, and tool-use policy. `history`
    is accepted for compatibility but intentionally ignored because this smoke
    slice uses prompt-only single-turn cases.
    """

    del history

    model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    agent = SingleAgent(
        OllamaModelClient(model=model),
        max_steps=3,
    )
    return agent.run(message).answer
