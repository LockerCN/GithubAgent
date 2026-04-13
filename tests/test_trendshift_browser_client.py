"""Trendshift 浏览器客户端测试。"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.clients.trendshift_browser_client import TrendshiftBrowserClient
from src.common.exceptions import TrendshiftFetchError


def test_fetch_daily_top_repositories_extracts_ranked_candidates_from_fixture() -> None:
    fixture_path = Path("tests/fixtures/trendshift_daily_explore.html")
    html = fixture_path.read_text(encoding="utf-8")
    client = TrendshiftBrowserClient(
        daily_explore_url="https://trendshift.io/",
        browser_timeout_ms=30000,
        page_content_loader=lambda *_: html,
    )

    repositories = client.fetch_daily_top_repositories(limit=2)

    assert [repository.full_name for repository in repositories] == [
        "astral-sh/uv",
        "pydantic/pydantic-ai",
    ]
    assert [repository.rank for repository in repositories] == [1, 2]


def test_fetch_daily_top_repositories_raises_when_daily_explore_structure_is_missing() -> None:
    client = TrendshiftBrowserClient(
        daily_explore_url="https://trendshift.io/",
        browser_timeout_ms=30000,
        page_content_loader=lambda *_: "<html><body><div>No daily section</div></body></html>",
    )

    with pytest.raises(TrendshiftFetchError, match="Daily Explore"):
        client.fetch_daily_top_repositories(limit=3)
