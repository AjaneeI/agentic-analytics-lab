from unittest.mock import Mock, patch

import pytest

from src.evals.assert_q3_target import DEFAULT_MODEL, chat


def test_assert_q3_callable_uses_existing_single_agent(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    tool_call = Mock()
    tool_call.name = "query_clickhouse"
    fake_result = Mock(answer="grounded answer", tool_calls=[tool_call])

    with patch("src.evals.assert_q3_target.OllamaModelClient") as client_cls, patch(
        "src.evals.assert_q3_target.SingleAgent"
    ) as agent_cls:
        agent_cls.return_value.run.return_value = fake_result

        answer = chat("compare blockers", history=[{"role": "user", "content": "ignored"}])

    client_cls.assert_called_once_with(model=DEFAULT_MODEL)
    agent_cls.assert_called_once_with(client_cls.return_value, max_steps=3)
    agent_cls.return_value.run.assert_called_once_with("compare blockers")
    assert answer == "grounded answer"


def test_assert_q3_callable_honors_model_override(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")

    with patch("src.evals.assert_q3_target.OllamaModelClient") as client_cls, patch(
        "src.evals.assert_q3_target.SingleAgent"
    ) as agent_cls:
        tool_call = Mock()
        tool_call.name = "query_clickhouse"
        agent_cls.return_value.run.return_value = Mock(
            answer="ok",
            tool_calls=[tool_call],
        )
        chat("question")

    client_cls.assert_called_once_with(model="qwen2.5:3b")


def test_assert_q3_callable_rejects_answer_without_clickhouse_query(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    with patch("src.evals.assert_q3_target.OllamaModelClient"), patch(
        "src.evals.assert_q3_target.SingleAgent"
    ) as agent_cls:
        agent_cls.return_value.run.return_value = Mock(
            answer="ungrounded answer",
            tool_calls=[],
        )

        with pytest.raises(RuntimeError, match="without a ClickHouse query"):
            chat("compare blockers")
