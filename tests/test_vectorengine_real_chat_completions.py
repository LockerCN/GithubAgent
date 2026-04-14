# -*- coding: utf-8 -*-
# 文件说明：针对 VectorEngine chat/completions 的真实工具调用闭环联调测试。

"""VectorEngine 真实工具调用联调测试。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request

import pytest


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"未设置环境变量 {name}，跳过真实联调测试。")
    return value


@dataclass(frozen=True)
class _VariantResult:
    name: str
    success: bool
    detail: str


class _VectorEngineChatCompletionsProbe:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 120,
    ) -> None:
        self._base_url = base_url.rstrip("/") + "/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    @property
    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "echo_tool",
                    "description": "返回调用参数，供模型继续回答。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "value": {
                                "type": "string",
                                "description": "需要回显的值。",
                            }
                        },
                        "required": ["value"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

    @property
    def initial_messages(self) -> list[dict[str, Any]]:
        return [
            {
                "role": "system",
                "content": (
                    "你正在进行工具调用联调。"
                    "你必须先调用 echo_tool，参数 value 固定为 pong。"
                    "拿到工具结果后，只输出 TOOL_OK: pong。"
                ),
            },
            {
                "role": "user",
                "content": "请完成一次最小工具调用闭环测试。",
            },
        ]

    def run_probe(self) -> tuple[dict[str, Any], list[_VariantResult]]:
        first_response = self._post_chat_completion(self.initial_messages)
        first_choice = self._get_first_choice(first_response)
        assistant_message = self._get_assistant_message(first_choice)
        tool_call = self._get_first_tool_call(assistant_message)
        tool_result_message = self._build_tool_result_message(tool_call)

        variants = [
            ("raw_assistant_message", assistant_message),
            (
                "assistant_null_content",
                {
                    **assistant_message,
                    "content": None,
                },
            ),
            (
                "assistant_text_only",
                {
                    "role": "assistant",
                    "content": self._extract_text_content(assistant_message.get("content")),
                    "tool_calls": assistant_message.get("tool_calls"),
                },
            ),
        ]

        results: list[_VariantResult] = []
        for variant_name, variant_assistant_message in variants:
            try:
                second_response = self._post_chat_completion(
                    self.initial_messages
                    + [variant_assistant_message, tool_result_message]
                )
                second_choice = self._get_first_choice(second_response)
                final_text = self._extract_text_content(
                    self._get_assistant_message(second_choice).get("content")
                )
                success = "TOOL_OK: pong" in final_text
                detail = final_text or json.dumps(second_response, ensure_ascii=False)[:400]
                results.append(
                    _VariantResult(
                        name=variant_name,
                        success=success,
                        detail=detail,
                    )
                )
            except Exception as error_info:  # pragma: no cover - 真实联调调试路径
                results.append(
                    _VariantResult(
                        name=variant_name,
                        success=False,
                        detail=str(error_info),
                    )
                )

        return first_response, results

    def _build_tool_result_message(self, tool_call: dict[str, Any]) -> dict[str, Any]:
        function_payload = tool_call.get("function", {})
        arguments_text = "{}"
        if isinstance(function_payload, dict):
            arguments_text = str(function_payload.get("arguments") or "{}")

        arguments = json.loads(arguments_text)
        value = str(arguments.get("value") or "")
        return {
            "role": "tool",
            "tool_call_id": str(tool_call.get("id") or ""),
            "name": "echo_tool",
            "content": json.dumps({"echo": value}, ensure_ascii=False),
        }

    def _post_chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "model": self._model,
            "messages": messages,
            "tools": self.tools,
            "tool_choice": "auto",
            "temperature": 0,
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self._api_key}",
        }
        http_request = request.Request(
            url=self._base_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
                response_body = response.read().decode("utf-8", errors="replace")
        except error.HTTPError as http_error:
            response_body = http_error.read().decode("utf-8", errors="replace")
            raise AssertionError(
                f"HTTP {http_error.code}: {response_body[:600]}"
            ) from http_error

        payload_data = json.loads(response_body)
        if not isinstance(payload_data, dict):
            raise AssertionError("响应 JSON 根节点不是对象。")
        return payload_data

    def _get_first_choice(self, response_payload: dict[str, Any]) -> dict[str, Any]:
        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AssertionError(f"响应缺少 choices: {json.dumps(response_payload, ensure_ascii=False)[:400]}")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise AssertionError("首个 choice 不是对象。")
        return first_choice

    def _get_assistant_message(self, choice: dict[str, Any]) -> dict[str, Any]:
        message = choice.get("message")
        if not isinstance(message, dict):
            raise AssertionError(f"choice.message 非法: {json.dumps(choice, ensure_ascii=False)[:400]}")
        return message

    def _get_first_tool_call(self, assistant_message: dict[str, Any]) -> dict[str, Any]:
        tool_calls = assistant_message.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            raise AssertionError(
                f"第一轮响应未返回 tool_calls: {json.dumps(assistant_message, ensure_ascii=False)[:600]}"
            )
        first_tool_call = tool_calls[0]
        if not isinstance(first_tool_call, dict):
            raise AssertionError("首个 tool_call 不是对象。")
        return first_tool_call

    def _extract_text_content(self, content: Any) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(str(item.get("text") or ""))
            return "".join(text_parts)
        return str(content)


def test_vectorengine_chat_completions_real_tool_loop() -> None:
    probe = _VectorEngineChatCompletionsProbe(
        base_url=_require_env("VECTORENGINE_REAL_BASE_URL"),
        api_key=_require_env("VECTORENGINE_REAL_API_KEY"),
        model=_require_env("VECTORENGINE_REAL_MODEL"),
        timeout_seconds=int(os.getenv("VECTORENGINE_REAL_TIMEOUT_SECONDS", "120")),
    )

    first_response, results = probe.run_probe()

    print("=== First Response ===")
    print(json.dumps(first_response, ensure_ascii=False, indent=2))
    print("=== Variant Results ===")
    for result in results:
        print(f"{result.name}: success={result.success} detail={result.detail}")

    assert any(result.success for result in results), (
        "所有第二轮消息变体均失败。"
        f" 结果: {[{'name': item.name, 'detail': item.detail} for item in results]}"
    )
