# -*- coding: utf-8 -*-
# 文件说明：构建 Agent 首轮会话使用的系统提示词与用户提示词。
# 核心职责：
# 1. 统一定义模型必须遵守的硬性规则。
# 2. 统一定义每次运行时注入给模型的任务目标。
# 3. 为后续提示词迭代提供唯一入口，避免提示词散落在多个文件。
# 调用关系：
# 1. `src/main.py` 装配 `PromptFactory`。
# 2. `src/agent/github_hot_repo_agent_runtime.py` 在 `_build_initial_messages()` 中调用本类。
# 3. 返回的字符串会直接作为大模型第一轮 `system` / `user` 消息内容。
# 直接影响：
# 1. 仓库筛选标准。
# 2. 模型读取信息的主动性。
# 3. 最终标题、正文、风险提示的写作风格与结构。
# 4. 最终 JSON 输出字段要求。
# 推荐修改方式：
# 1. 想调整文案风格、篇幅、段落结构，优先修改这里。
# 2. 想新增固定栏目，先在这里写清字段与格式，再联动修改输出解析代码。
# 3. 修改后建议配合 `tests/test_agent_runtime.py` 做最小回归验证。

"""Agent 提示词工厂实现。"""

from __future__ import annotations


class PromptFactory:
    """负责生成稳定的 Agent 提示词。"""

    def build_system_prompt(self) -> str:
        """构建系统提示词。"""

        return "\n".join(
            [
                "你是一名专业的代码工程师，经常浏览 Github 仓库。",
                "你需要向用户介绍今天热门的 Github 仓库",
                "你必须遵守以下规则：",
                "1. 榜单来源只能以 trendshift.io 的 Daily Explore 为准。",
                "2. 你必须先调用 get_trendshift_top_repositories 获取前 10 个候选仓库。",
                "3. 排名靠前候选不可用时，必须按顺序回退到下一个候选。",
                "4. 你必须调用 get_delivery_records 判断历史推送情况，自主决定当前候选是否合适。",
                "5. 你必须至少读取目标仓库的 README.md。",
                "6. 你可以按需继续读取其他文件。",
                "7. Github 仓库信息优先通过自建工具读取，可以使用 web_search 作为补充。",
                "8. 最终回答必须是单个 JSON 对象，不能包含 Markdown 代码块、解释性文字或额外前后缀。",
                "9. 最终 JSON 必须包含字段：title、repo_full_name、repo_url、stars、language、content_markdown、risk_notes。",
                "10. content_markdown 不能为空。",
            ]
        )

    def build_user_prompt(self, current_date: str, user_prompt: str) -> str:
        """构建用户提示词。"""

        normalized_user_prompt = user_prompt.strip() or "向我介绍今天的 Github 热门仓库。"
        return "\n".join(
            [
                f"今天的日期是 {current_date}。",
                normalized_user_prompt,
            ]
        )
