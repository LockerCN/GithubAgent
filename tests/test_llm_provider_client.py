"""大模型提供商客户端测试。"""

from __future__ import annotations

import io
from urllib import error as urllib_error

import pytest

from src.common.exceptions import LlmInvocationError
from src.clients import llm_provider_client as llm_provider_client_module
from src.clients.llm_provider_client import LlmProviderClient


def test_create_agent_response_accepts_standardized_payload() -> None:
    client = LlmProviderClient(
        base_url="https://api.example.com/v1/responses",
        api_key="llm-api-key-placeholder",
        model="model-placeholder",
        request_sender=lambda *_: {
            "tool_calls": [{"id": "call-1", "name": "get_repo", "arguments": "{}"}],
            "text_content": "",
            "finish_reason": "tool_calls",
        },
    )

    response = client.create_agent_response(messages=[], tools=[], enable_web_search=True)

    assert response["finish_reason"] == "tool_calls"
    assert response["tool_calls"][0]["name"] == "get_repo"


def test_create_agent_response_normalizes_chat_completion_style_payload() -> None:
    client = LlmProviderClient(
        base_url="https://api.example.com/v1/chat/completions",
        api_key="llm-api-key-placeholder",
        model="model-placeholder",
        request_sender=lambda *_: {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "content": [{"type": "text", "text": '{"title":"demo"}'}],
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "function": {"name": "get_repo", "arguments": '{"x":1}'},
                            }
                        ],
                    },
                }
            ]
        },
    )

    response = client.create_agent_response(messages=[], tools=[], enable_web_search=False)

    assert response["finish_reason"] == "stop"
    assert response["text_content"] == '{"title":"demo"}'
    assert response["tool_calls"][0]["arguments"] == '{"x":1}'


def test_create_agent_response_surfaces_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(*_args, **_kwargs):
        raise urllib_error.HTTPError(
            url="https://api.example.com/v1/responses",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"Not Found"}'),
        )

    monkeypatch.setattr(llm_provider_client_module.request, "urlopen", fake_urlopen)

    client = LlmProviderClient(
        base_url="https://api.example.com/v1/responses",
        api_key="llm-api-key-placeholder",
        model="model-placeholder",
    )

    with pytest.raises(LlmInvocationError, match="HTTP 状态码: 404"):
        client.create_agent_response(messages=[], tools=[], enable_web_search=False)
