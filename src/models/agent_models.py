"""Agent 运行相关数据模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AgentOutput:
    """Agent 结构化输出。"""

    title: str
    repo_full_name: str
    repo_url: str
    stars: int
    language: str | None
    content_markdown: str
    risk_notes: str


@dataclass(slots=True)
class AgentRunRequest:
    """Agent 运行请求。"""

    current_date: str
    user_prompt: str
