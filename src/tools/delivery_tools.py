# -*- coding: utf-8 -*-
# 文件说明：封装推送状态读取工具。

"""推送状态相关工具实现。"""

from __future__ import annotations

from src.services.delivery_state_service import DeliveryStateService
from src.tools.base_tool import BaseTool


class GetDeliveryRecordsTool(BaseTool):
    """读取历史推送记录供 Agent 判断候选可用性。"""

    def __init__(self, delivery_state_service: DeliveryStateService) -> None:
        self._delivery_state_service = delivery_state_service

    @property
    def name(self) -> str:
        return "get_delivery_records"

    @property
    def description(self) -> str:
        return "读取历史推送记录，可按日期过滤并限制返回条数。"

    @property
    def json_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "可选，按 YYYY-MM-DD 过滤指定日期的推送记录。",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回记录上限。",
                    "minimum": 1,
                },
            },
            "required": [],
            "additionalProperties": False,
        }

    def execute(self, arguments: dict) -> dict:
        arguments = self._require_object(arguments)
        date = self._get_optional_str(arguments, "date")
        limit = self._get_int(arguments, "limit", required=False, default=30, minimum=1)
        records = self._delivery_state_service.get_records(date=date, limit=limit)
        return {"records": [record.to_dict() for record in records]}
