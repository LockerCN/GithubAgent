"""大模型提供商客户端测试。"""

from __future__ import annotations

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
