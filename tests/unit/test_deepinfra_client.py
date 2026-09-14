"""Tests for the DeepInfra client."""

import respx

from llm_bench_data.clients.deepinfra import DeepInfraClient
from llm_bench_data.core.models import ChatRequest, Message


def test_chat_uses_deepinfra_endpoint(settings, monkeypatch) -> None:
    """DeepInfra uses its own base URL and bearer token."""
    monkeypatch.setenv("DEEPINFRA_API_KEY", "di-test-key")
    with respx.mock:
        route = respx.post("https://api.deepinfra.com/v1/openai/chat/completions").respond(
            200,
            json={
                "model": "deepseek-ai/DeepSeek-V4-Flash-0731",
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            },
        )
        client = DeepInfraClient()
        response = client.chat(
            ChatRequest(
                model_id="deepseek-ai/DeepSeek-V4-Flash-0731",
                messages=[Message(role="user", content="hi")],
                max_tokens=20,
            )
        )
        assert response.prompt_tokens == 2
        assert route.calls[0].request.headers["authorization"] == "Bearer di-test-key"
