"""Tests for the Alibaba Cloud Model Studio client."""

import respx

from llm_bench_data.clients.alibaba import AlibabaClient
from llm_bench_data.core.models import ChatRequest, Message


def test_chat_uses_alibaba_workspace_endpoint(settings, monkeypatch) -> None:
    """Alibaba uses the workspace-scoped compatible-mode endpoint."""
    monkeypatch.setenv("ALIBABA_KEYSUB", "alibaba-test-key")
    monkeypatch.setenv("ALIBABA_ID1", "workspace-test")
    with respx.mock:
        route = respx.post(
            "https://workspace-test.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
        ).respond(
            200,
            json={
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            },
        )
        client = AlibabaClient()
        response = client.chat(
            ChatRequest(
                model_id="deepseek-v4-flash",
                messages=[Message(role="user", content="hi")],
                max_tokens=20,
            )
        )
        assert response.prompt_tokens == 2
        assert route.calls[0].request.headers["authorization"] == "Bearer alibaba-test-key"


def test_chat_accepts_full_alibaba_endpoint(settings, monkeypatch) -> None:
    """A full OpenAI-compatible endpoint can be supplied in ALIBABA_ID1."""
    monkeypatch.setenv("ALIBABA_KEYSUB", "alibaba-test-key")
    monkeypatch.setenv(
        "ALIBABA_ID1",
        "https://ws-test.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/",
    )
    with respx.mock:
        route = respx.post(
            "https://ws-test.cn-beijing.maas.aliyuncs.com/compatible-mode/v1/chat/completions"
        ).respond(
            200,
            json={
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"content": "hello"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            },
        )
        client = AlibabaClient()
        client.chat(
            ChatRequest(
                model_id="deepseek-v4-flash",
                messages=[Message(role="user", content="hi")],
                max_tokens=20,
            )
        )
        assert route.called
