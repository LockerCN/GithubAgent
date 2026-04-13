# -*- coding: utf-8 -*-
# 文件说明：提供 Agent 工具注册与分发能力。

"""工具注册器实现。"""

from __future__ import annotations

from typing import Iterable

from src.common.exceptions import ToolExecutionError
from src.tools.base_tool import BaseTool


class ToolRegistry:
    """聚合全部工具并按名称分发执行。"""

    def __init__(self, tools: Iterable[BaseTool]) -> None:
        self._tools: dict[str, BaseTool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"重复的工具名称: {tool.name}")
            self._tools[tool.name] = tool

    def get_tool_schemas(self) -> list[dict]:
        """返回全部工具定义。"""

        return [tool.to_tool_schema() for tool in self._tools.values()]

    def execute(self, tool_name: str, arguments: dict) -> dict:
        """按名称执行指定工具。"""

        tool = self._tools.get(tool_name)
        if tool is None:
            raise ToolExecutionError(f"未注册的工具: {tool_name}")

        try:
            return tool.execute(arguments)
        except ToolExecutionError:
            raise
        except Exception as error:
            raise ToolExecutionError(f"工具执行失败: {tool_name}") from error
