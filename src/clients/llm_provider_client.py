"""大模型提供商适配客户端实现。"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib import error, request

from src.common.exceptions import LlmInvocationError


RequestSender = Callable[[str, dict[str, str], bytes | None, int], dict[str, Any]]


class LlmProviderClient:
    """负责统一封装大模型会话调用。"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        request_sender: RequestSender | None = None,
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._request_sender = request_sender or self._send_request

    def create_agent_response(
        self,
        messages: list[dict],
        tools: list[dict],
        enable_web_search: bool,
    ) -> dict[str, Any]:
        """发起一次统一模型调用并返回标准化结果。"""

        payload = {
            "model": self._model,
            "messages": messages,
            "tools": tools,
            "enable_web_search": enable_web_search,
        }
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            response_payload = self._request_sender(
                self._base_url,
                headers,
                json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                self._timeout_seconds,
            )
        except LlmInvocationError:
            raise
        except Exception as error:
            raise LlmInvocationError("大模型调用失败。") from error

        return self._normalize_response(response_payload)

    def _normalize_response(self, response_payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(response_payload, dict):
            raise LlmInvocationError("大模型返回格式非法。")

        if {
            "tool_calls",
            "text_content",
            "finish_reason",
        }.issubset(response_payload.keys()):
            tool_calls = response_payload.get("tool_calls")
            text_content = response_payload.get("text_content")
            finish_reason = response_payload.get("finish_reason")
            if not isinstance(tool_calls, list):
                raise LlmInvocationError("大模型返回的 tool_calls 必须为数组。")
            return {
                "tool_calls": tool_calls,
                "text_content": "" if text_content is None else str(text_content),
                "finish_reason": str(finish_reason),
            }

        choices = response_payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise LlmInvocationError("大模型返回缺少 choices。")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise LlmInvocationError("大模型返回的首个 choice 非法。")

        message = first_choice.get("message", {})
        if not isinstance(message, dict):
            raise LlmInvocationError("大模型返回的 message 非法。")

        return {
            "tool_calls": self._extract_tool_calls(message.get("tool_calls")),
            "text_content": self._extract_text_content(message.get("content")),
            "finish_reason": str(first_choice.get("finish_reason") or "stop"),
        }

    def _extract_tool_calls(self, raw_tool_calls: Any) -> list[dict[str, Any]]:
        if raw_tool_calls is None:
            return []
        if not isinstance(raw_tool_calls, list):
            raise LlmInvocationError("大模型返回的 tool_calls 非法。")

        normalized_calls: list[dict[str, Any]] = []
        for item in raw_tool_calls:
            if not isinstance(item, dict):
                raise LlmInvocationError("大模型返回的单个 tool_call 非法。")

            function_payload = item.get("function", {})
            if not isinstance(function_payload, dict):
                raise LlmInvocationError("大模型返回的 tool_call.function 非法。")

            normalized_calls.append(
                {
                    "id": str(item.get("id") or ""),
                    "name": str(function_payload.get("name") or ""),
                    "arguments": str(function_payload.get("arguments") or "{}"),
                }
            )

        return normalized_calls

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
        raise LlmInvocationError("大模型返回的 content 非法。")

    def _send_request(
        self,
        url: str,
        headers: dict[str, str],
        body: bytes | None,
        timeout_seconds: int,
    ) -> dict[str, Any]:
        http_request = request.Request(url=url, data=body, headers=headers, method="POST")

        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                response_body = response.read().decode("utf-8", errors="replace")
        except TimeoutError as timeout_error:
            raise LlmInvocationError(
                f"大模型调用超时，超过 {timeout_seconds} 秒。"
            ) from timeout_error
        except error.HTTPError as http_error:
            response_body = http_error.read().decode("utf-8", errors="replace")
            raise LlmInvocationError(
                f"大模型调用失败，HTTP 状态码: {http_error.code}，响应摘要: {response_body[:200]}"
            ) from http_error
        except error.URLError as url_error:
            raise LlmInvocationError(f"大模型调用失败: {url_error.reason}") from url_error

        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError as json_error:
            raise LlmInvocationError("大模型返回非 JSON 响应。") from json_error

        if not isinstance(payload, dict):
            raise LlmInvocationError("大模型返回的 JSON 根节点非法。")

        return payload
