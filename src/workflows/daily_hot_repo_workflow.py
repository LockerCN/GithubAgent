# -*- coding: utf-8 -*-
# 文件说明：实现每日热门仓库推送的业务闭环入口。
# 核心职责：
# 1. 生成本次运行日期与默认任务提示。
# 2. 调用 Agent 获取结构化仓库介绍。
# 3. 发送飞书成功消息。
# 4. 保存归档文件与推送状态。
# 5. 在失败时发送飞书错误告警。
# 调用关系：
# 1. `src/main.py` 完成依赖装配后调用本类的 `run()`。
# 2. 本类内部依赖 Agent 运行时、飞书客户端、归档服务、状态服务。
# 3. 这是最靠近“每日任务主流程”的业务文件。
# 直接影响：
# 1. `DEFAULT_USER_PROMPT` 会直接进入提示词，影响模型任务理解。
# 2. 成功链路的发送顺序会影响失败后的可恢复性与日志表现。
# 3. 错误告警文案会直接出现在飞书中。
# 上手建议：
# 1. 想改“默认让模型怎么写”，先看 `DEFAULT_USER_PROMPT`。
# 2. 想改“成功后做什么”，看 `run()` 中 Agent、飞书、归档、状态写入顺序。
# 3. 想改“失败时通知什么”，看 `_try_send_error_alert()`。

"""每日热门仓库 Workflow 实现。"""

from __future__ import annotations

from datetime import datetime
import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from src.agent.github_hot_repo_agent_runtime import GithubHotRepoAgentRuntime
from src.clients.feishu_webhook_client import FeishuWebhookClient
from src.common.exceptions import ConfigurationError
from src.models.agent_models import AgentRunRequest
from src.models.config_models import AppConfig
from src.models.delivery_models import DeliveryRecord
from src.services.archive_service import ArchiveService
from src.services.delivery_state_service import DeliveryStateService
from src.services.feishu_message_builder import FeishuMessageBuilder


LOGGER = logging.getLogger(__name__)
DEFAULT_USER_PROMPT = "请介绍今天最值得推送的 Github 热门仓库。"
ERROR_ALERT_TITLE = "今日 Github 热门仓库推送失败"


class DailyHotRepoWorkflow:
    """负责执行每日热门仓库推送闭环。"""

    def __init__(
        self,
        agent_runtime: GithubHotRepoAgentRuntime,
        message_builder: FeishuMessageBuilder,
        feishu_client: FeishuWebhookClient,
        archive_service: ArchiveService,
        delivery_state_service: DeliveryStateService,
        app_config: AppConfig,
    ) -> None:
        self._agent_runtime = agent_runtime
        self._message_builder = message_builder
        self._feishu_client = feishu_client
        self._archive_service = archive_service
        self._delivery_state_service = delivery_state_service
        self._app_config = app_config

    def run(self) -> None:
        """执行完整的每日热门仓库推送流程。"""

        success_message_sent = False
        current_date = "unknown"

        try:
            now = self._get_now()
            current_date = now.date().isoformat()
            delivered_at = now.isoformat(timespec="seconds")

            LOGGER.info("开始执行每日热门仓库 Workflow，日期: %s", current_date)

            output = self._agent_runtime.run(
                AgentRunRequest(
                    current_date=current_date,
                    user_prompt=DEFAULT_USER_PROMPT,
                )
            )
            success_payload = self._message_builder.build_success_payload(output)
            self._feishu_client.send_post_message(success_payload)
            success_message_sent = True

            archive_path = self._archive_service.save(current_date, output)
            self._delivery_state_service.append_record(
                DeliveryRecord(
                    date=current_date,
                    repo_full_name=output.repo_full_name,
                    title=output.title,
                    archive_path=archive_path,
                    delivered_at=delivered_at,
                )
            )

            LOGGER.info(
                "每日热门仓库 Workflow 执行成功，仓库: %s",
                output.repo_full_name,
            )
        except Exception as error:
            LOGGER.exception("每日热门仓库 Workflow 执行失败。")
            if not success_message_sent:
                self._try_send_error_alert(current_date=current_date, error=error)
            raise

    def _get_now(self) -> datetime:
        timezone_name = self._app_config.scheduler.timezone

        try:
            timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise ConfigurationError(f"无效的时区配置: {timezone_name}") from error

        return datetime.now(timezone)

    def _try_send_error_alert(self, current_date: str, error: Exception) -> None:
        error_payload = self._message_builder.build_error_payload(
            title=ERROR_ALERT_TITLE,
            error_message=f"日期：{current_date}\n错误：{error}",
        )

        try:
            self._feishu_client.send_post_message(error_payload)
        except Exception:
            LOGGER.exception("飞书错误告警发送失败。")
