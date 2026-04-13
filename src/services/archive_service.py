"""归档服务实现。"""

from __future__ import annotations

from pathlib import Path

from src.common.exceptions import PersistenceError
from src.models.agent_models import AgentOutput


class ArchiveService:
    """负责保存最终推送归档。"""

    def __init__(self, archive_dir: Path, repo_root: Path) -> None:
        self._archive_dir = archive_dir
        self._repo_root = repo_root

    def save(self, date: str, output: AgentOutput) -> str:
        """将当天推送结果保存为归档 Markdown 文件。"""

        archive_path = self._archive_dir / f"{date}.md"

        try:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            archive_path.write_text(
                self._build_archive_content(date=date, output=output),
                encoding="utf-8",
            )
            return archive_path.relative_to(self._repo_root).as_posix()
        except Exception as error:
            raise PersistenceError(f"归档写入失败: {archive_path}") from error

    def _build_archive_content(self, date: str, output: AgentOutput) -> str:
        language = output.language or "未说明"
        risk_notes = output.risk_notes.strip() or "无"

        lines = [
            f"# {output.title}",
            "",
            f"- 日期：{date}",
            f"- 仓库：{output.repo_full_name}",
            f"- 链接：{output.repo_url}",
            f"- Stars：{output.stars}",
            f"- 语言：{language}",
            "",
            "## 正文",
            "",
            output.content_markdown.strip(),
            "",
            "## 风险提示",
            "",
            risk_notes,
            "",
        ]
        return "\n".join(lines)
