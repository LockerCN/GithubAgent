"""推送状态相关数据模型。"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class DeliveryRecord:
    """单条推送记录。"""

    date: str
    repo_full_name: str
    title: str
    archive_path: str
    delivered_at: str

    def to_dict(self) -> dict[str, str]:
        """转换为可序列化字典。"""

        return asdict(self)


@dataclass(slots=True)
class DeliveryState:
    """推送状态聚合根。"""

    records: list[DeliveryRecord]
