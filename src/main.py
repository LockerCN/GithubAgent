# -*- coding: utf-8 -*-
# 文件说明：程序入口与每日热门仓库 Workflow 装配。

"""程序入口实现。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from src.agent import GithubHotRepoAgentRuntime, PromptFactory, ToolRegistry
from src.clients import (
    FeishuWebhookClient,
    GithubApiClient,
    LlmProviderClient,
    TrendshiftBrowserClient,
)
from src.common.exceptions import ApplicationError, PersistenceError
from src.common.logging_utils import configure_logging
from src.config.config_loader import ConfigLoader
from src.services import ArchiveService, DeliveryStateService, FeishuMessageBuilder
from src.tools import (
    GetDeliveryRecordsTool,
    GetRepositoryFileContentTool,
    GetRepositoryMetadataTool,
    GetRepositoryTreeTool,
    GetTrendshiftTopRepositoriesTool,
)
from src.workflows import DailyHotRepoWorkflow


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = "config/app.toml"
CONFIG_PATH_ENV_NAME = "GITHUB_AGENT_CONFIG_PATH"


def main() -> int:
    """初始化日志、装配依赖并执行每日热门仓库 Workflow。"""

    configure_logging()

    try:
        config_path = Path(os.getenv(CONFIG_PATH_ENV_NAME, DEFAULT_CONFIG_PATH))
        loader = ConfigLoader()
        app_config = loader.load(config_path)

        repo_root = Path.cwd()
        archive_dir = _resolve_repo_path(repo_root, app_config.runtime.archive_dir)
        state_file = _resolve_repo_path(repo_root, app_config.runtime.state_file)
        archive_dir.mkdir(parents=True, exist_ok=True)
        _ensure_state_file_exists(state_file)

        trendshift_client = TrendshiftBrowserClient(
            daily_explore_url=app_config.trendshift.daily_explore_url,
            browser_timeout_ms=app_config.trendshift.browser_timeout_ms,
        )
        github_client = GithubApiClient(
            api_base_url=app_config.github.api_base_url,
            token=app_config.github.token,
            request_timeout_seconds=app_config.github.request_timeout_seconds,
            tree_max_entries=app_config.github.tree_max_entries,
            file_max_chars=app_config.github.file_max_chars,
        )
        llm_client = LlmProviderClient(
            base_url=app_config.llm.base_url,
            api_key=app_config.llm.api_key,
            model=app_config.llm.model,
            timeout_seconds=app_config.llm.request_timeout_seconds,
        )
        feishu_client = FeishuWebhookClient(webhook_url=app_config.feishu.webhook_url)
        archive_service = ArchiveService(archive_dir=archive_dir, repo_root=repo_root)
        delivery_state_service = DeliveryStateService(state_file=state_file)
        message_builder = FeishuMessageBuilder()

        tool_registry = ToolRegistry(
            [
                GetTrendshiftTopRepositoriesTool(client=trendshift_client),
                GetDeliveryRecordsTool(delivery_state_service=delivery_state_service),
                GetRepositoryMetadataTool(github_client=github_client),
                GetRepositoryTreeTool(github_client=github_client),
                GetRepositoryFileContentTool(github_client=github_client),
            ]
        )
        prompt_factory = PromptFactory()
        agent_runtime = GithubHotRepoAgentRuntime(
            llm_client=llm_client,
            tool_registry=tool_registry,
            prompt_factory=prompt_factory,
            enable_web_search=app_config.llm.enable_web_search,
            max_rounds=app_config.llm.max_rounds,
        )
        workflow = DailyHotRepoWorkflow(
            agent_runtime=agent_runtime,
            message_builder=message_builder,
            feishu_client=feishu_client,
            archive_service=archive_service,
            delivery_state_service=delivery_state_service,
            app_config=app_config,
        )

        LOGGER.info("配置加载完成，配置文件: %s", config_path.resolve())
        LOGGER.info("开始执行每日热门仓库 Workflow。")
        workflow.run()
        LOGGER.info("每日热门仓库 Workflow 执行完成。")
        return 0
    except ApplicationError as error:
        LOGGER.error("启动失败: %s", error)
        return 2
    except Exception:
        LOGGER.exception("发生未预期异常。")
        return 1


def _resolve_repo_path(repo_root: Path, path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (repo_root / candidate).resolve()


def _ensure_state_file_exists(state_file: Path) -> None:
    if state_file.exists():
        return

    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            json.dumps({"records": []}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise PersistenceError(f"初始化状态文件失败: {state_file}") from error


if __name__ == "__main__":
    raise SystemExit(main())
