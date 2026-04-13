"""仓库访问相关数据模型定义。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RepositoryCandidate:
    """Trendshift 候选仓库信息。"""

    rank: int
    owner: str
    name: str
    full_name: str
    repo_url: str


@dataclass(slots=True)
class RepositoryMetadata:
    """仓库基础元信息。"""

    full_name: str
    description: str
    default_branch: str
    stars: int
    language: str | None
    html_url: str


@dataclass(slots=True)
class RepositoryTreeEntry:
    """仓库目录树节点。"""

    path: str
    type: str


@dataclass(slots=True)
class FileContent:
    """仓库文件内容。"""

    path: str
    ref: str
    content: str
    truncated: bool
