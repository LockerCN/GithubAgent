"""推送状态服务测试。"""

from __future__ import annotations

import json
from pathlib import Path

from src.models.delivery_models import DeliveryRecord
from src.services.delivery_state_service import DeliveryStateService


def test_get_records_returns_empty_list_when_state_file_missing(tmp_path: Path) -> None:
    service = DeliveryStateService(state_file=tmp_path / "runtime" / "state" / "delivery_state.json")

    records = service.get_records()

    assert records == []


def test_append_record_persists_records_in_descending_delivered_at_order(tmp_path: Path) -> None:
    state_file = tmp_path / "runtime" / "state" / "delivery_state.json"
    service = DeliveryStateService(state_file=state_file)

    service.append_record(
        DeliveryRecord(
            date="2026-04-12",
            repo_full_name="owner/older",
            title="旧仓库",
            archive_path="runtime/archive/2026-04-12.md",
            delivered_at="2026-04-12T12:00:08+08:00",
        )
    )
    service.append_record(
        DeliveryRecord(
            date="2026-04-13",
            repo_full_name="owner/newer",
            title="新仓库",
            archive_path="runtime/archive/2026-04-13.md",
            delivered_at="2026-04-13T12:00:08+08:00",
        )
    )

    records = service.get_records()

    assert [record.repo_full_name for record in records] == ["owner/newer", "owner/older"]
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    assert payload["records"][0]["repo_full_name"] == "owner/newer"


def test_get_records_supports_date_filter_and_limit(tmp_path: Path) -> None:
    state_file = tmp_path / "runtime" / "state" / "delivery_state.json"
    service = DeliveryStateService(state_file=state_file)

    for day in ("2026-04-11", "2026-04-12", "2026-04-12"):
        service.append_record(
            DeliveryRecord(
                date=day,
                repo_full_name=f"owner/{day}",
                title=f"title-{day}",
                archive_path=f"runtime/archive/{day}.md",
                delivered_at=f"{day}T12:00:08+08:00",
            )
        )

    filtered_records = service.get_records(date="2026-04-12", limit=1)

    assert len(filtered_records) == 1
    assert filtered_records[0].date == "2026-04-12"
