# -*- coding: utf-8 -*-
# 文件说明：验证阶段四 Agent 运行时的工具循环与输出解析。

"""Agent 运行时测试。"""

from __future__ import annotations

import json

import pytest

from src.agent import GithubHotRepoAgentRuntime, PromptFactory, ToolRegistry
from src.common.exceptions import AgentOutputParseError, LlmInvocationError
from src.models.agent_models import AgentRunRequest
from src.tools.base_tool import BaseTool


class _FakeLlmClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    def create_agent_response(
        self,
        messages: list[dict],
        tools: list[dict],
        enable_web_search: bool,
    ) -> dict:
        self.calls.append(
            {
                "messages": [message.copy() for message in messages],
                "tools": tools,
                "enable_web_search": enable_web_search,
            }
        )
        return self._responses.pop(0)


class _EchoTool(BaseTool):
    @property
    def name(self) -> str:
        return "echo_tool"

    @property
    def description(self) -> str:
        return "返回传入的文本。"

    @property
    def json_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict) -> dict:
        arguments = self._require_object(arguments)
        return {"echo": self._get_str(arguments, "value")}


def test_runtime_executes_tool_call_then_parses_final_output() -> None:
    llm_client = _FakeLlmClient(
        responses=[
            {
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "echo_tool",
                        "arguments": json.dumps({"value": "hello"}, ensure_ascii=False),
                        "type": "function",
                        "function": {
                            "name": "echo_tool",
                            "arguments": json.dumps({"value": "hello"}, ensure_ascii=False),
                            "thought_signature": "sig-123",
                        },
                    }
                ],
                "text_content": "",
                "finish_reason": "tool_calls",
            },
            {
                "tool_calls": [],
                "text_content": json.dumps(
                    {
                        "title": "今日 Github 热门仓库：owner/repo",
                        "repo_full_name": "owner/repo",
                        "repo_url": "https://github.com/owner/repo",
                        "stars": 123,
                        "language": "Python",
                        "content_markdown": "这是正文。",
                        "risk_notes": "适合继续观察。",
                    },
                    ensure_ascii=False,
                ),
                "finish_reason": "stop",
            },
        ]
    )
    runtime = GithubHotRepoAgentRuntime(
        llm_client=llm_client,  # type: ignore[arg-type]
        tool_registry=ToolRegistry([_EchoTool()]),
        prompt_factory=PromptFactory(),
        enable_web_search=True,
        max_rounds=3,
    )

    output = runtime.run(
        AgentRunRequest(
            current_date="2026-04-13",
            user_prompt="请介绍今天最值得推送的 Github 热门仓库。",
        )
    )

    assert output.repo_full_name == "owner/repo"
    assert llm_client.calls[1]["messages"][-1]["role"] == "tool"
    assert llm_client.calls[1]["messages"][-1]["content"] == '{"echo": "hello"}'
    assistant_tool_call = llm_client.calls[1]["messages"][-2]["tool_calls"][0]
    assert assistant_tool_call["function"]["thought_signature"] == "sig-123"


def test_runtime_raises_parse_error_when_required_field_missing() -> None:
    llm_client = _FakeLlmClient(
        responses=[
            {
                "tool_calls": [],
                "text_content": json.dumps(
                    {
                        "title": "title",
                        "repo_full_name": "owner/repo",
                        "repo_url": "https://github.com/owner/repo",
                        "stars": 123,
                        "language": "Python",
                        "risk_notes": "risk",
                    },
                    ensure_ascii=False,
                ),
                "finish_reason": "stop",
            }
        ]
    )
    runtime = GithubHotRepoAgentRuntime(
        llm_client=llm_client,  # type: ignore[arg-type]
        tool_registry=ToolRegistry([_EchoTool()]),
        prompt_factory=PromptFactory(),
        enable_web_search=False,
        max_rounds=2,
    )

    with pytest.raises(AgentOutputParseError, match="content_markdown"):
        runtime.run(
            AgentRunRequest(
                current_date="2026-04-13",
                user_prompt="请介绍今天的热门仓库。",
            )
        )


def test_runtime_raises_when_rounds_exceed_limit() -> None:
    llm_client = _FakeLlmClient(
        responses=[
            {
                "tool_calls": [
                    {"id": "call-1", "name": "echo_tool", "arguments": '{"value":"a"}'}
                ],
                "text_content": "",
                "finish_reason": "tool_calls",
            },
            {
                "tool_calls": [
                    {"id": "call-2", "name": "echo_tool", "arguments": '{"value":"b"}'}
                ],
                "text_content": "",
                "finish_reason": "tool_calls",
            },
        ]
    )
    runtime = GithubHotRepoAgentRuntime(
        llm_client=llm_client,  # type: ignore[arg-type]
        tool_registry=ToolRegistry([_EchoTool()]),
        prompt_factory=PromptFactory(),
        enable_web_search=False,
        max_rounds=2,
    )

    with pytest.raises(LlmInvocationError, match="轮数超过上限"):
        runtime.run(
            AgentRunRequest(
                current_date="2026-04-13",
                user_prompt="请介绍今天的热门仓库。",
            )
        )
