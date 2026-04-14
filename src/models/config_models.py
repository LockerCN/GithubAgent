"""配置数据模型定义。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class SchedulerConfig:
    timezone: str


@dataclass(slots=True)
class TrendshiftConfig:
    daily_explore_url: str
    top_n: int
    browser_timeout_ms: int


@dataclass(slots=True)
class GithubConfig:
    api_base_url: str
    token: str
    request_timeout_seconds: int
    tree_max_entries: int
    file_max_chars: int


@dataclass(slots=True)
class LlmConfig:
    base_url: str
    api_key: str
    model: str
    request_timeout_seconds: int
    enable_web_search: bool
    max_rounds: int


@dataclass(slots=True)
class FeishuConfig:
    webhook_url: str


@dataclass(slots=True)
class RuntimeConfig:
    archive_dir: str
    state_file: str


@dataclass(slots=True)
class AppConfig:
    scheduler: SchedulerConfig
    trendshift: TrendshiftConfig
    github: GithubConfig
    llm: LlmConfig
    feishu: FeishuConfig
    runtime: RuntimeConfig
