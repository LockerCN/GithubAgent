"""推送状态服务实现。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.common.exceptions import PersistenceError
from src.models.delivery_models import DeliveryRecord, DeliveryState


class DeliveryStateService:
    """负责读取和写入推送状态文件。"""

    def __init__(self, state_file: Path) -> None:
        self._state_file = state_file

    def get_records(self, date: str | None = None, limit: int = 30) -> list[DeliveryRecord]:
        """读取推送记录并按时间倒序返回。"""

        state = self._read_state()
        records = sorted(state.records, key=lambda record: record.delivered_at, reverse=True)

        if date is not None:
            records = [record for record in records if record.date == date]

        if limit <= 0:
            return []

        return records[:limit]

    def append_record(self, record: DeliveryRecord) -> None:
        """追加一条成功推送记录并覆盖写回状态文件。"""

        state = self._read_state()
        state.records.append(record)
        ordered_records = sorted(state.records, key=lambda item: item.delivered_at, reverse=True)
        payload = {"records": [item.to_dict() for item in ordered_records]}

        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            self._state_file.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except Exception as error:
            raise PersistenceError(f"状态文件写入失败: {self._state_file}") from error

    def _read_state(self) -> DeliveryState:
        if not self._state_file.exists():
            return DeliveryState(records=[])

        try:
            raw_text = self._state_file.read_text(encoding="utf-8").strip()
            if not raw_text:
                return DeliveryState(records=[])

            payload = json.loads(raw_text)
        except json.JSONDecodeError as error:
            raise PersistenceError(f"状态文件 JSON 解析失败: {self._state_file}") from error
        except OSError as error:
            raise PersistenceError(f"状态文件读取失败: {self._state_file}") from error

        records_raw = self._extract_records(payload)
        records = [self._build_record(item) for item in records_raw]
        return DeliveryState(records=records)

    def _extract_records(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, dict):
            raise PersistenceError("状态文件格式非法: 根节点必须为对象。")

        records = payload.get("records", [])
        if not isinstance(records, list):
            raise PersistenceError("状态文件格式非法: records 必须为数组。")

        return records

    def _build_record(self, item: Any) -> DeliveryRecord:
        if not isinstance(item, dict):
            raise PersistenceError("状态文件格式非法: 记录项必须为对象。")

        required_fields = (
            "date",
            "repo_full_name",
            "title",
            "archive_path",
            "delivered_at",
        )
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            missing_text = ", ".join(missing_fields)
            raise PersistenceError(f"状态文件格式非法: 缺少字段 {missing_text}。")

        return DeliveryRecord(
            date=str(item["date"]),
            repo_full_name=str(item["repo_full_name"]),
            title=str(item["title"]),
            archive_path=str(item["archive_path"]),
            delivered_at=str(item["delivered_at"]),
        )
