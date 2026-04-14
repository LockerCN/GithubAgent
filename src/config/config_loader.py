"""应用配置加载与校验实现。"""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any

from src.common.exceptions import ConfigurationError
from src.models.config_models import (
    AppConfig,
    FeishuConfig,
    GithubConfig,
    LlmConfig,
    RuntimeConfig,
    SchedulerConfig,
    TrendshiftConfig,
)


DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS = 180


class ConfigLoader:
    """负责读取并校验应用配置。"""

    def load(self, path: Path) -> AppConfig:
        """从给定 TOML 文件加载应用配置。"""

        config_path = path.resolve()
        repo_root = config_path.parent.parent

        try:
            with config_path.open("rb") as file:
                raw_config = tomllib.load(file)
        except FileNotFoundError as error:
            raise ConfigurationError(f"配置文件不存在: {config_path}") from error
        except tomllib.TOMLDecodeError as error:
            raise ConfigurationError(f"TOML 解析失败: {config_path}") from error

        scheduler = self._build_scheduler_config(raw_config)
        trendshift = self._build_trendshift_config(raw_config)
        github = self._build_github_config(raw_config)
        llm = self._build_llm_config(raw_config)
        feishu = self._build_feishu_config(raw_config)
        runtime = self._build_runtime_config(raw_config)

        self._validate_runtime_paths(runtime, repo_root)

        return AppConfig(
            scheduler=scheduler,
            trendshift=trendshift,
            github=github,
            llm=llm,
            feishu=feishu,
            runtime=runtime,
        )

    def _build_scheduler_config(self, raw_config: dict[str, Any]) -> SchedulerConfig:
        section = self._require_section(raw_config, "scheduler")
        timezone = self._require_value(section, "timezone")
        return SchedulerConfig(timezone=str(timezone))

    def _build_trendshift_config(self, raw_config: dict[str, Any]) -> TrendshiftConfig:
        section = self._require_section(raw_config, "trendshift")
        top_n = self._require_int(section, "top_n")
        if top_n > 10:
            raise ConfigurationError("trendshift.top_n 必须小于等于 10。")

        return TrendshiftConfig(
            daily_explore_url=str(self._require_value(section, "daily_explore_url")),
            top_n=top_n,
            browser_timeout_ms=self._require_int(section, "browser_timeout_ms"),
        )

    def _build_github_config(self, raw_config: dict[str, Any]) -> GithubConfig:
        section = self._require_section(raw_config, "github")
        file_max_chars = self._require_int(section, "file_max_chars")
        if file_max_chars <= 1000:
            raise ConfigurationError("github.file_max_chars 必须大于 1000。")

        return GithubConfig(
            api_base_url=str(self._require_value(section, "api_base_url")),
            token=str(self._require_value(section, "token")),
            request_timeout_seconds=self._require_int(section, "request_timeout_seconds"),
            tree_max_entries=self._require_int(section, "tree_max_entries"),
            file_max_chars=file_max_chars,
        )

    def _build_llm_config(self, raw_config: dict[str, Any]) -> LlmConfig:
        section = self._require_section(raw_config, "llm")
        max_rounds = self._require_int(section, "max_rounds")
        request_timeout_seconds = self._optional_int(
            section,
            "request_timeout_seconds",
            DEFAULT_LLM_REQUEST_TIMEOUT_SECONDS,
        )
        if max_rounds <= 0:
            raise ConfigurationError("llm.max_rounds 必须大于 0。")
        if request_timeout_seconds <= 0:
            raise ConfigurationError("llm.request_timeout_seconds 必须大于 0。")

        return LlmConfig(
            base_url=str(self._require_value(section, "base_url")),
            api_key=str(self._require_value(section, "api_key")),
            model=str(self._require_value(section, "model")),
            request_timeout_seconds=request_timeout_seconds,
            enable_web_search=self._require_bool(section, "enable_web_search"),
            max_rounds=max_rounds,
        )

    def _build_feishu_config(self, raw_config: dict[str, Any]) -> FeishuConfig:
        section = self._require_section(raw_config, "feishu")
        webhook_url = str(self._require_value(section, "webhook_url")).strip()
        if not webhook_url:
            raise ConfigurationError("feishu.webhook_url 不能为空。")
        return FeishuConfig(webhook_url=webhook_url)

    def _build_runtime_config(self, raw_config: dict[str, Any]) -> RuntimeConfig:
        section = self._require_section(raw_config, "runtime")
        return RuntimeConfig(
            archive_dir=str(self._require_value(section, "archive_dir")),
            state_file=str(self._require_value(section, "state_file")),
        )

    def _validate_runtime_paths(self, runtime: RuntimeConfig, repo_root: Path) -> None:
        archive_dir = self._resolve_repo_path(repo_root, runtime.archive_dir)
        state_file = self._resolve_repo_path(repo_root, runtime.state_file)

        if not self._is_within_directory(archive_dir, repo_root):
            raise ConfigurationError("runtime.archive_dir 必须位于仓库目录内。")
        if not self._is_within_directory(state_file, repo_root):
            raise ConfigurationError("runtime.state_file 必须位于仓库目录内。")

    def _resolve_repo_path(self, repo_root: Path, path_value: str) -> Path:
        candidate = Path(path_value)
        if candidate.is_absolute():
            return candidate.resolve()
        return (repo_root / candidate).resolve()

    def _is_within_directory(self, target: Path, base_dir: Path) -> bool:
        try:
            target.relative_to(base_dir)
            return True
        except ValueError:
            return False

    def _require_section(self, raw_config: dict[str, Any], section_name: str) -> dict[str, Any]:
        section = raw_config.get(section_name)
        if not isinstance(section, dict):
            raise ConfigurationError(f"缺少配置段: {section_name}")
        return section

    def _require_value(self, section: dict[str, Any], field_name: str) -> Any:
        if field_name not in section:
            raise ConfigurationError(f"缺少配置项: {field_name}")
        return section[field_name]

    def _require_int(self, section: dict[str, Any], field_name: str) -> int:
        value = self._require_value(section, field_name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigurationError(f"配置项 {field_name} 必须为整数。")
        return value

    def _require_bool(self, section: dict[str, Any], field_name: str) -> bool:
        value = self._require_value(section, field_name)
        if not isinstance(value, bool):
            raise ConfigurationError(f"配置项 {field_name} 必须为布尔值。")
        return value

    def _optional_int(
        self,
        section: dict[str, Any],
        field_name: str,
        default_value: int,
    ) -> int:
        if field_name not in section:
            return default_value
        value = section[field_name]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigurationError(f"配置项 {field_name} 必须为整数。")
        return value
