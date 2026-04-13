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
