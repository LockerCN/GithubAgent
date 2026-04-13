# -*- coding: utf-8 -*-
# 文件说明：构建阶段四 Agent 的系统提示词与用户提示词。

"""Agent 提示词工厂实现。"""

from __future__ import annotations


class PromptFactory:
    """负责生成稳定的 Agent 提示词。"""

    def build_system_prompt(self) -> str:
        """构建系统提示词。"""

        return "\n".join(
            [
                "你是一个负责分析 Github 热门仓库的高自主 Agent。",
                "你必须遵守以下规则：",
                "1. 榜单来源只能以 trendshift.io 的 Daily Explore 为准。",
                "2. 你必须先调用 get_trendshift_top_repositories 获取前 10 个候选仓库。",
                "3. 排名靠前候选不可用时，必须按顺序回退到下一个候选。",
                "4. 你必须调用 get_delivery_records 判断历史推送情况，自主决定当前候选是否合适。",
                "5. 你必须至少读取目标仓库的 README.md。",
                "6. 你可以按需继续读取其他文件，但应保持读取规模克制。",
                "7. Github 仓库信息必须优先通过自建工具读取，web_search 只能作为补充。",
                "8. 最终回答必须是单个 JSON 对象，不能包含 Markdown 代码块、解释性文字或额外前后缀。",
                "9. 最终 JSON 必须包含字段：title、repo_full_name、repo_url、stars、language、content_markdown、risk_notes。",
                "10. content_markdown 必须为中文且不能为空。",
            ]
        )

    def build_user_prompt(self, current_date: str, user_prompt: str) -> str:
        """构建用户提示词。"""

        normalized_user_prompt = user_prompt.strip() or "请介绍今天最值得推送的 Github 热门仓库。"
        return "\n".join(
            [
                f"今天的日期是 {current_date}。",
                normalized_user_prompt,
                "请自主完成候选获取、候选回退、历史记录检查、README 阅读、必要文件补充阅读和最终中文介绍生成。",
                "如果某个候选仓库不可用，请继续尝试下一个候选，直到得到可输出结果或确认全部失败。",
            ]
        )
