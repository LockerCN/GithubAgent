# -*- coding: utf-8 -*-
# 文件说明：验证阶段五 Workflow 的成功与失败闭环行为。

"""DailyHotRepoWorkflow 测试。"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.common.exceptions import LlmInvocationError, PersistenceError
from src.models.agent_models import AgentOutput, AgentRunRequest
from src.models.config_models import (
    AppConfig,
    FeishuConfig,
    GithubConfig,
    LlmConfig,
    RuntimeConfig,
    SchedulerConfig,
    TrendshiftConfig,
)
from src.workflows.daily_hot_repo_workflow import (
    DailyHotRepoWorkflow,
    ERROR_ALERT_TITLE,
)


class _FakeAgentRuntime:
    def __init__(self, output: AgentOutput | None = None, error: Exception | None = None) -> None:
        self._output = output
        self._error = error
        self.requests: list[AgentRunRequest] = []

    def run(self, request: AgentRunRequest) -> AgentOutput:
        self.requests.append(request)
        if self._error is not None:
            raise self._error
        assert self._output is not None
        return self._output


class _FakeMessageBuilder:
    def __init__(self) -> None:
        self.success_outputs: list[AgentOutput] = []
        self.error_calls: list[tuple[str, str]] = []

    def build_success_payload(self, output: AgentOutput) -> dict:
        self.success_outputs.append(output)
        return {"kind": "success", "title": output.title}

    def build_error_payload(self, title: str, error_message: str) -> dict:
        self.error_calls.append((title, error_message))
        return {"kind": "error", "title": title, "message": error_message}


class _FakeFeishuClient:
    def __init__(self) -> None:
        self.payloads: list[dict] = []

    def send_post_message(self, payload: dict) -> None:
        self.payloads.append(payload)


class _FakeArchiveService:
    def __init__(self, archive_path: str = "runtime/archive/2026-04-13.md") -> None:
        self.archive_path = archive_path
        self.calls: list[tuple[str, AgentOutput]] = []
        self.error: Exception | None = None

    def save(self, date: str, output: AgentOutput) -> str:
        self.calls.append((date, output))
        if self.error is not None:
            raise self.error
        return self.archive_path


class _FakeDeliveryStateService:
    def __init__(self) -> None:
        self.records: list[object] = []

    def append_record(self, record) -> None:
        self.records.append(record)


def test_workflow_completes_success_chain() -> None:
    output = _build_agent_output()
    agent_runtime = _FakeAgentRuntime(output=output)
    message_builder = _FakeMessageBuilder()
    feishu_client = _FakeFeishuClient()
    archive_service = _FakeArchiveService()
    state_service = _FakeDeliveryStateService()
    workflow = DailyHotRepoWorkflow(
        agent_runtime=agent_runtime,  # type: ignore[arg-type]
        message_builder=message_builder,  # type: ignore[arg-type]
        feishu_client=feishu_client,  # type: ignore[arg-type]
        archive_service=archive_service,  # type: ignore[arg-type]
        delivery_state_service=state_service,  # type: ignore[arg-type]
        app_config=_build_app_config(),
    )
    workflow._get_now = lambda: datetime.fromisoformat("2026-04-13T12:34:56+08:00")  # type: ignore[method-assign]

    workflow.run()

    assert agent_runtime.requests == [
        AgentRunRequest(
            current_date="2026-04-13",
            user_prompt="请介绍今天最值得推送的 Github 热门仓库。",
        )
    ]
    assert feishu_client.payloads == [{"kind": "success", "title": output.title}]
    assert archive_service.calls == [("2026-04-13", output)]
    assert len(state_service.records) == 1
    appended_record = state_service.records[0]
    assert appended_record.date == "2026-04-13"
    assert appended_record.repo_full_name == output.repo_full_name
    assert appended_record.title == output.title
    assert appended_record.archive_path == "runtime/archive/2026-04-13.md"
    assert appended_record.delivered_at == "2026-04-13T12:34:56+08:00"
    assert message_builder.error_calls == []


def test_workflow_sends_error_alert_when_agent_runtime_fails() -> None:
    agent_runtime = _FakeAgentRuntime(error=LlmInvocationError("模型调用失败"))
    message_builder = _FakeMessageBuilder()
    feishu_client = _FakeFeishuClient()
    archive_service = _FakeArchiveService()
    state_service = _FakeDeliveryStateService()
    workflow = DailyHotRepoWorkflow(
        agent_runtime=agent_runtime,  # type: ignore[arg-type]
        message_builder=message_builder,  # type: ignore[arg-type]
        feishu_client=feishu_client,  # type: ignore[arg-type]
        archive_service=archive_service,  # type: ignore[arg-type]
        delivery_state_service=state_service,  # type: ignore[arg-type]
        app_config=_build_app_config(),
    )
    workflow._get_now = lambda: datetime.fromisoformat("2026-04-13T12:34:56+08:00")  # type: ignore[method-assign]

    with pytest.raises(LlmInvocationError, match="模型调用失败"):
        workflow.run()

    assert message_builder.error_calls == [
        (ERROR_ALERT_TITLE, "日期：2026-04-13\n错误：模型调用失败")
    ]
    assert feishu_client.payloads == [
        {
            "kind": "error",
            "title": ERROR_ALERT_TITLE,
            "message": "日期：2026-04-13\n错误：模型调用失败",
        }
    ]
    assert archive_service.calls == []
    assert state_service.records == []


def test_workflow_does_not_send_error_alert_after_success_message_sent() -> None:
    output = _build_agent_output()
    agent_runtime = _FakeAgentRuntime(output=output)
    message_builder = _FakeMessageBuilder()
    feishu_client = _FakeFeishuClient()
    archive_service = _FakeArchiveService()
    archive_service.error = PersistenceError("归档失败")
    state_service = _FakeDeliveryStateService()
    workflow = DailyHotRepoWorkflow(
        agent_runtime=agent_runtime,  # type: ignore[arg-type]
        message_builder=message_builder,  # type: ignore[arg-type]
        feishu_client=feishu_client,  # type: ignore[arg-type]
        archive_service=archive_service,  # type: ignore[arg-type]
        delivery_state_service=state_service,  # type: ignore[arg-type]
        app_config=_build_app_config(),
    )
    workflow._get_now = lambda: datetime.fromisoformat("2026-04-13T12:34:56+08:00")  # type: ignore[method-assign]

    with pytest.raises(PersistenceError, match="归档失败"):
        workflow.run()

    assert feishu_client.payloads == [{"kind": "success", "title": output.title}]
    assert message_builder.error_calls == []
    assert state_service.records == []


def _build_agent_output() -> AgentOutput:
    return AgentOutput(
        title="今日 Github 热门仓库：owner/repo",
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        stars=1234,
        language="Python",
        content_markdown="这是正文。",
        risk_notes="适合继续观察。",
    )


def _build_app_config() -> AppConfig:
    return AppConfig(
        scheduler=SchedulerConfig(timezone="Asia/Shanghai"),
        trendshift=TrendshiftConfig(
            daily_explore_url="https://trendshift.io/",
            top_n=10,
            browser_timeout_ms=30000,
        ),
        github=GithubConfig(
            api_base_url="https://api.github.com",
            token="github-token-placeholder",
            request_timeout_seconds=30,
            tree_max_entries=300,
            file_max_chars=20000,
        ),
        llm=LlmConfig(
            base_url="https://api.example.com/v1",
            api_key="llm-api-key-placeholder",
            model="model-placeholder",
            enable_web_search=True,
            max_rounds=12,
        ),
        feishu=FeishuConfig(
            webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/placeholder",
        ),
        runtime=RuntimeConfig(
            archive_dir="runtime/archive",
            state_file="runtime/state/delivery_state.json",
        ),
    )
