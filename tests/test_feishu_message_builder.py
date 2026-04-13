"""飞书消息构建测试。"""

from __future__ import annotations

from src.models.agent_models import AgentOutput
from src.services.feishu_message_builder import FeishuMessageBuilder


def test_build_success_payload_returns_stable_post_message() -> None:
    builder = FeishuMessageBuilder()
    output = AgentOutput(
        title="今日 Github 热门仓库：owner/repo",
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        stars=4321,
        language="Python",
        content_markdown="一段中文介绍。",
        risk_notes="适合有 Python 基础的读者。",
    )

    payload = builder.build_success_payload(output)
    content = payload["content"]["post"]["zh_cn"]["content"]

    assert payload["msg_type"] == "post"
    assert payload["content"]["post"]["zh_cn"]["title"] == output.title
    assert content[0][1]["href"] == output.repo_url
    assert content[1][0]["text"] == "Stars：4321 | 语言：Python"
    assert content[2][0]["text"] == "一段中文介绍。"
    assert content[3][0]["text"] == "风险提示：适合有 Python 基础的读者。"


def test_build_error_payload_returns_stable_error_message() -> None:
    builder = FeishuMessageBuilder()

    payload = builder.build_error_payload(
        title="今日 Github 热门仓库推送失败",
        error_message="Trendshift 抓取失败",
    )
    content = payload["content"]["post"]["zh_cn"]["content"]

    assert payload["msg_type"] == "post"
    assert payload["content"]["post"]["zh_cn"]["title"] == "今日 Github 热门仓库推送失败"
    assert content[0][0]["text"] == "任务执行失败"
    assert content[1][0]["text"] == "Trendshift 抓取失败"
