# -*- coding: utf-8 -*-
# 文件说明：封装 Trendshift 候选仓库查询工具。

"""Trendshift 相关工具实现。"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Callable

from src.clients.trendshift_browser_client import TrendshiftBrowserClient
from src.tools.base_tool import BaseTool


DateProvider = Callable[[], str]


class GetTrendshiftTopRepositoriesTool(BaseTool):
    """获取 Trendshift Daily Explore 候选仓库。"""

    def __init__(
        self,
        client: TrendshiftBrowserClient,
        date_provider: DateProvider | None = None,
    ) -> None:
        self._client = client
        self._date_provider = date_provider or self._get_current_date

    @property
    def name(self) -> str:
        return "get_trendshift_top_repositories"

    @property
    def description(self) -> str:
        return "获取 trendshift.io Daily Explore 的前 N 个 Github 热门仓库候选。"

    @property
    def json_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "候选仓库数量，最大为 10。",
                    "minimum": 1,
                    "maximum": 10,
                }
            },
            "required": ["limit"],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict) -> dict:
        arguments = self._require_object(arguments)
        limit = self._get_int(arguments, "limit", minimum=1, maximum=10)
        repositories = self._client.fetch_daily_top_repositories(limit=limit)
        return {
            "date": self._date_provider(),
            "source": "trendshift_daily_explore",
            "repositories": [asdict(repository) for repository in repositories],
        }

    def _get_current_date(self) -> str:
        return datetime.now().date().isoformat()
