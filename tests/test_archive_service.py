"""归档服务测试。"""

from __future__ import annotations

from pathlib import Path

from src.models.agent_models import AgentOutput
from src.services.archive_service import ArchiveService


def test_save_writes_markdown_archive_and_returns_relative_path(tmp_path: Path) -> None:
    repo_root = tmp_path
    archive_dir = repo_root / "runtime" / "archive"
    service = ArchiveService(archive_dir=archive_dir, repo_root=repo_root)

    output = AgentOutput(
        title="今日 Github 热门仓库：owner/repo",
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        stars=1234,
        language="Python",
        content_markdown="这是正文。",
        risk_notes="适合快速了解。",
    )

    archive_path = service.save(date="2026-04-13", output=output)

    assert archive_path == "runtime/archive/2026-04-13.md"
    content = (repo_root / archive_path).read_text(encoding="utf-8")
    assert "# 今日 Github 热门仓库：owner/repo" in content
    assert "- 日期：2026-04-13" in content
    assert "## 正文" in content
    assert "这是正文。" in content
    assert "## 风险提示" in content
    assert "适合快速了解。" in content
