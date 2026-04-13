# -*- coding: utf-8 -*-
# 文件说明：定义 Agent 工具抽象与通用参数校验逻辑。

"""Agent 工具抽象基类。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.common.exceptions import ToolExecutionError


class BaseTool(ABC):
    """所有 Agent 工具的统一抽象。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """返回工具名称。"""

    @property
    @abstractmethod
    def description(self) -> str:
        """返回工具用途描述。"""

    @property
    @abstractmethod
    def json_schema(self) -> dict[str, Any]:
        """返回工具参数 JSON Schema。"""

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """执行工具调用。"""

    def to_tool_schema(self) -> dict[str, Any]:
        """转换为 LLM 可消费的函数工具定义。"""

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.json_schema,
            },
        }

    def _require_object(self, arguments: Any) -> dict[str, Any]:
        if not isinstance(arguments, dict):
            raise ToolExecutionError(f"工具 {self.name} 的参数必须为对象。")
        return arguments

    def _get_str(
        self,
        arguments: dict[str, Any],
        field_name: str,
        *,
        required: bool = True,
        allow_empty: bool = False,
        default: str | None = None,
    ) -> str:
        if field_name not in arguments:
            if required:
                raise ToolExecutionError(f"工具 {self.name} 缺少参数: {field_name}")
            return default or ""

        value = arguments[field_name]
        if value is None:
            if required:
                raise ToolExecutionError(f"工具 {self.name} 的参数 {field_name} 不能为空。")
            return default or ""

        text = str(value).strip()
        if not allow_empty and not text:
            raise ToolExecutionError(f"工具 {self.name} 的参数 {field_name} 不能为空字符串。")
        return text

    def _get_optional_str(
        self,
        arguments: dict[str, Any],
        field_name: str,
        *,
        default: str | None = None,
    ) -> str | None:
        if field_name not in arguments or arguments[field_name] is None:
            return default

        text = str(arguments[field_name]).strip()
        return text or default

    def _get_int(
        self,
        arguments: dict[str, Any],
        field_name: str,
        *,
        required: bool = True,
        default: int | None = None,
        minimum: int | None = None,
        maximum: int | None = None,
    ) -> int:
        if field_name not in arguments:
            if required:
                raise ToolExecutionError(f"工具 {self.name} 缺少参数: {field_name}")
            if default is None:
                raise ToolExecutionError(f"工具 {self.name} 缺少默认整数参数: {field_name}")
            value = default
        else:
            raw_value = arguments[field_name]
            if isinstance(raw_value, bool):
                raise ToolExecutionError(f"工具 {self.name} 的参数 {field_name} 必须为整数。")
            try:
                value = int(raw_value)
            except (TypeError, ValueError) as error:
                raise ToolExecutionError(
                    f"工具 {self.name} 的参数 {field_name} 必须为整数。"
                ) from error

        if minimum is not None and value < minimum:
            raise ToolExecutionError(
                f"工具 {self.name} 的参数 {field_name} 必须大于等于 {minimum}。"
            )
        if maximum is not None and value > maximum:
            raise ToolExecutionError(
                f"工具 {self.name} 的参数 {field_name} 必须小于等于 {maximum}。"
            )

        return value

    def _get_bool(
        self,
        arguments: dict[str, Any],
        field_name: str,
        *,
        required: bool = True,
        default: bool | None = None,
    ) -> bool:
        if field_name not in arguments:
            if required:
                raise ToolExecutionError(f"工具 {self.name} 缺少参数: {field_name}")
            if default is None:
                raise ToolExecutionError(f"工具 {self.name} 缺少默认布尔参数: {field_name}")
            return default

        value = arguments[field_name]
        if not isinstance(value, bool):
            raise ToolExecutionError(f"工具 {self.name} 的参数 {field_name} 必须为布尔值。")
        return value
