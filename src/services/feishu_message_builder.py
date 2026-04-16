# -*- coding: utf-8 -*-
# 文件说明：将 `AgentOutput` 转换为飞书机器人可发送的消息负载。
# 核心职责：
# 1. 构建成功推送消息。
# 2. 构建失败告警消息。
# 3. 统一管理飞书展示结构，避免展示逻辑散落在 Workflow 中。
# 调用关系：
# 1. `src/workflows/daily_hot_repo_workflow.py` 在成功与失败分支中调用本类。
# 2. 本类输入为结构化的 `AgentOutput`，输出为飞书 `post` 消息 JSON。
# 直接影响：
# 1. 飞书标题如何显示。
# 2. 正文、仓库链接、风险提示的排版顺序。
# 3. 用户最终在飞书里看到的视觉结构与阅读体验。
# 上手建议：
# 1. 如果模型写得没问题，但飞书展示不顺手，优先改这里。
# 2. 如果想增加固定展示模块，例如“推荐理由”“适合谁看”，可以从这里下手。
# 3. 修改这里通常不会影响 Agent 推理，只会影响消息展示样式。

"""飞书消息负载构建实现。"""

from __future__ import annotations

from src.models.agent_models import AgentOutput


class FeishuMessageBuilder:
    """负责构建飞书机器人消息负载。"""

    def build_success_payload(self, output: AgentOutput) -> dict:
        """构建成功推送消息。"""

        language = output.language or "未说明"
        risk_notes = output.risk_notes.strip() or "无"

        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": output.title,
                        "content": [
                            [
                                {"tag": "text", "text": "仓库："},
                                {
                                    "tag": "a",
                                    "text": output.repo_full_name,
                                    "href": output.repo_url,
                                },
                            ],
                            [
                                {
                                    "tag": "text",
                                    "text": f"Stars：{output.stars} | 语言：{language}",
                                }
                            ],
                            [{"tag": "text", "text": output.content_markdown.strip()}],
                            [{"tag": "text", "text": f"风险提示：{risk_notes}"}],
                        ],
                    }
                }
            },
        }

    def build_error_payload(self, title: str, error_message: str) -> dict:
        """构建错误告警消息。"""

        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": title,
                        "content": [
                            [{"tag": "text", "text": "任务执行失败"}],
                            [{"tag": "text", "text": error_message.strip()}],
                        ],
                    }
                }
            },
        }
