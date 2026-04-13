# -*- coding: utf-8 -*-
# 文件说明：验证阶段四工具层的输出结构与注册行为。

"""工具层测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from src.agent.tool_registry import ToolRegistry
from src.common.exceptions import ToolExecutionError
from src.models.delivery_models import DeliveryRecord
from src.services.delivery_state_service import DeliveryStateService
from src.tools import (
    GetDeliveryRecordsTool,
    GetRepositoryTreeTool,
    GetTrendshiftTopRepositoriesTool,
)


@dataclass(slots=True)
class _FakeCandidate:
    rank: int
    owner: str
    name: str
    full_name: str
    repo_url: str


@dataclass(slots=True)
class _FakeTreeEntry:
    path: str
    type: str


class _FakeTrendshiftClient:
    def fetch_daily_top_repositories(self, limit: int) -> list[_FakeCandidate]:
        return [
            _FakeCandidate(
                rank=1,
                owner="owner",
                name="repo",
                full_name="owner/repo",
                repo_url="https://github.com/owner/repo",
            )
        ][:limit]


class _FakeGithubClient:
    def get_repository_tree(
        self,
        owner: str,
        name: str,
        ref: str,
        path: str,
        recursive: bool,
    ) -> list[_FakeTreeEntry]:
        assert owner == "owner"
        assert name == "repo"
        assert ref == "main"
        assert path == ""
        assert recursive is True
        return [
            _FakeTreeEntry(path="README.md", type="file"),
            _FakeTreeEntry(path="docs", type="dir"),
        ]


def test_get_trendshift_top_repositories_tool_returns_serializable_payload() -> None:
    tool = GetTrendshiftTopRepositoriesTool(
        client=_FakeTrendshiftClient(),  # type: ignore[arg-type]
        date_provider=lambda: "2026-04-13",
    )

    payload = tool.execute({"limit": 1})

    assert payload["date"] == "2026-04-13"
    assert payload["source"] == "trendshift_daily_explore"
    assert payload["repositories"][0]["full_name"] == "owner/repo"


def test_get_delivery_records_tool_returns_filtered_records(tmp_path: Path) -> None:
    service = DeliveryStateService(state_file=tmp_path / "runtime" / "state" / "delivery_state.json")
    service.append_record(
        DeliveryRecord(
            date="2026-04-13",
            repo_full_name="owner/repo",
            title="今日 Github 热门仓库：owner/repo",
            archive_path="runtime/archive/2026-04-13.md",
            delivered_at="2026-04-13T12:00:08+08:00",
        )
    )
    tool = GetDeliveryRecordsTool(delivery_state_service=service)

    payload = tool.execute({"date": "2026-04-13", "limit": 1})

    assert payload["records"][0]["repo_full_name"] == "owner/repo"
    assert payload["records"][0]["archive_path"] == "runtime/archive/2026-04-13.md"


def test_tool_registry_dispatches_repository_tree_tool() -> None:
    registry = ToolRegistry([GetRepositoryTreeTool(github_client=_FakeGithubClient())])  # type: ignore[arg-type]

    payload = registry.execute(
        "get_repository_tree",
        {"owner": "owner", "name": "repo", "ref": "main", "path": "", "recursive": True},
    )

    assert payload["entries"][0]["path"] == "README.md"
    assert registry.get_tool_schemas()[0]["function"]["name"] == "get_repository_tree"


def test_tool_registry_raises_for_unknown_tool() -> None:
    registry = ToolRegistry([])

    with pytest.raises(ToolExecutionError, match="未注册的工具"):
        registry.execute("unknown_tool", {})
