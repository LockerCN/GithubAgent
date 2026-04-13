# -*- coding: utf-8 -*-
# 文件说明：实现阶段四 Agent 运行时与工具调用循环。

"""Github 热门仓库 Agent 运行时实现。"""

from __future__ import annotations

import json
from typing import Any

from src.agent.prompt_factory import PromptFactory
from src.agent.tool_registry import ToolRegistry
from src.clients.llm_provider_client import LlmProviderClient
from src.common.exceptions import AgentOutputParseError, LlmInvocationError, ToolExecutionError
from src.models.agent_models import AgentOutput, AgentRunRequest


class GithubHotRepoAgentRuntime:
    """驱动大模型与工具调用循环，并解析最终结构化输出。"""

    def __init__(
        self,
        llm_client: LlmProviderClient,
        tool_registry: ToolRegistry,
        prompt_factory: PromptFactory,
        enable_web_search: bool,
        max_rounds: int,
    ) -> None:
        self._llm_client = llm_client
        self._tool_registry = tool_registry
        self._prompt_factory = prompt_factory
        self._enable_web_search = enable_web_search
        self._max_rounds = max_rounds

    def run(self, request: AgentRunRequest) -> AgentOutput:
        """执行一次完整 Agent 会话。"""

        messages = self._build_initial_messages(request)
        output_text = self._run_loop(messages)
        return self._parse_output(output_text)

    def _build_initial_messages(self, request: AgentRunRequest) -> list[dict]:
        return [
            {"role": "system", "content": self._prompt_factory.build_system_prompt()},
            {
                "role": "user",
                "content": self._prompt_factory.build_user_prompt(
                    current_date=request.current_date,
                    user_prompt=request.user_prompt,
                ),
            },
        ]

    def _run_loop(self, messages: list[dict]) -> str:
        tool_schemas = self._tool_registry.get_tool_schemas()

        for _ in range(self._max_rounds):
            response = self._llm_client.create_agent_response(
                messages=messages,
                tools=tool_schemas,
                enable_web_search=self._enable_web_search,
            )
            text_content = str(response.get("text_content") or "")
            tool_calls = response.get("tool_calls") or []

            assistant_message = self._build_assistant_message(
                text_content=text_content,
                tool_calls=tool_calls,
            )
            if assistant_message is not None:
                messages.append(assistant_message)

            if tool_calls:
                messages.extend(self._handle_tool_calls(tool_calls))
                continue

            if not text_content.strip():
                raise AgentOutputParseError("大模型未返回最终 JSON 文本。")
            return text_content

        raise LlmInvocationError(f"Agent 推理轮数超过上限: {self._max_rounds}")

    def _handle_tool_calls(self, tool_calls: list[dict]) -> list[dict]:
        tool_messages: list[dict] = []

        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                raise ToolExecutionError("工具调用格式非法。")

            tool_call_id = str(tool_call.get("id") or "").strip()
            tool_name = str(tool_call.get("name") or "").strip()
            if not tool_call_id or not tool_name:
                raise ToolExecutionError("工具调用缺少 id 或名称。")

            arguments = self._parse_tool_arguments(tool_name, tool_call.get("arguments"))
            result = self._tool_registry.execute(tool_name=tool_name, arguments=arguments)
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "name": tool_name,
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )

        return tool_messages

    def _parse_output(self, text: str) -> AgentOutput:
        normalized_text = self._normalize_output_text(text)

        try:
            payload = json.loads(normalized_text)
        except json.JSONDecodeError as error:
            raise AgentOutputParseError("Agent 最终输出不是合法 JSON 对象。") from error

        if not isinstance(payload, dict):
            raise AgentOutputParseError("Agent 最终输出必须为 JSON 对象。")

        required_fields = (
            "title",
            "repo_full_name",
            "repo_url",
            "stars",
            "language",
            "content_markdown",
            "risk_notes",
        )
        missing_fields = [field_name for field_name in required_fields if field_name not in payload]
        if missing_fields:
            raise AgentOutputParseError(f"Agent 最终输出缺少字段: {', '.join(missing_fields)}")

        title = self._require_non_empty_str(payload, "title")
        repo_full_name = self._require_non_empty_str(payload, "repo_full_name")
        repo_url = self._require_non_empty_str(payload, "repo_url")
        content_markdown = self._require_non_empty_str(payload, "content_markdown")
        risk_notes = str(payload["risk_notes"]).strip()
        language = payload["language"]
        normalized_language = None if language is None else str(language).strip() or None

        return AgentOutput(
            title=title,
            repo_full_name=repo_full_name,
            repo_url=repo_url,
            stars=self._parse_stars(payload["stars"]),
            language=normalized_language,
            content_markdown=content_markdown,
            risk_notes=risk_notes,
        )

    def _build_assistant_message(self, text_content: str, tool_calls: list[dict]) -> dict | None:
        if not text_content.strip() and not tool_calls:
            return None

        message: dict[str, Any] = {"role": "assistant", "content": text_content}
        if tool_calls:
            message["tool_calls"] = [
                {
                    "id": str(tool_call.get("id") or ""),
                    "type": "function",
                    "function": {
                        "name": str(tool_call.get("name") or ""),
                        "arguments": str(tool_call.get("arguments") or "{}"),
                    },
                }
                for tool_call in tool_calls
            ]
        return message

    def _parse_tool_arguments(self, tool_name: str, raw_arguments: Any) -> dict[str, Any]:
        if raw_arguments in (None, ""):
            return {}
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if not isinstance(raw_arguments, str):
            raise ToolExecutionError(f"工具 {tool_name} 的 arguments 必须为 JSON 字符串。")

        try:
            parsed_arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as error:
            raise ToolExecutionError(f"工具 {tool_name} 的 arguments 不是合法 JSON。") from error

        if not isinstance(parsed_arguments, dict):
            raise ToolExecutionError(f"工具 {tool_name} 的 arguments 必须解析为对象。")
        return parsed_arguments

    def _normalize_output_text(self, text: str) -> str:
        normalized = text.strip()
        if normalized.startswith("```") and normalized.endswith("```"):
            lines = normalized.splitlines()
            if lines:
                lines = lines[1:-1]
            normalized = "\n".join(lines).strip()
            if normalized.lower().startswith("json"):
                normalized = normalized[4:].strip()
        return normalized

    def _require_non_empty_str(self, payload: dict[str, Any], field_name: str) -> str:
        value = str(payload[field_name]).strip()
        if not value:
            raise AgentOutputParseError(f"Agent 最终输出字段 {field_name} 不能为空。")
        return value

    def _parse_stars(self, value: Any) -> int:
        if isinstance(value, bool):
            raise AgentOutputParseError("Agent 最终输出字段 stars 必须为整数。")
        try:
            return int(value)
        except (TypeError, ValueError) as error:
            raise AgentOutputParseError("Agent 最终输出字段 stars 必须为整数。") from error
