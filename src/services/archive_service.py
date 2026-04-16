# -*- coding: utf-8 -*-
# 文件说明：将每日推送结果持久化为仓库内 Markdown 归档文件。
# 核心职责：
# 1. 生成当天归档文件路径。
# 2. 把 `AgentOutput` 渲染为统一格式的 Markdown。
# 3. 返回相对仓库根目录的归档路径，供状态记录使用。
# 调用关系：
# 1. `src/workflows/daily_hot_repo_workflow.py` 在飞书发送成功后调用本类保存归档。
# 2. 归档内容来源于 Agent 的最终结构化输出。
# 3. 归档路径会被写入 `runtime/state/delivery_state.json`。
# 直接影响：
# 1. 仓库中的历史推送存档长什么样。
# 2. 以后回看每日记录时能否快速获取关键信息。
# 3. 如果你希望“飞书展示”和“本地归档”风格一致，这里需要同步调整。
# 上手建议：
# 1. 想改归档标题、正文区块、风险提示区块，优先看 `_build_archive_content()`。
# 2. 想改文件命名或保存位置，先看 `save()`。
# 3. 修改这里不会影响模型输出本身，只影响本地持久化结果。

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
