"""项目公共异常定义。"""


class ApplicationError(Exception):
    """应用层统一异常基类。"""


class ConfigurationError(ApplicationError):
    """配置加载或校验失败。"""


class TrendshiftFetchError(ApplicationError):
    """Trendshift 抓取失败。"""


class GithubApiError(ApplicationError):
    """Github API 调用失败。"""


class LlmInvocationError(ApplicationError):
    """大模型调用失败。"""


class ToolExecutionError(ApplicationError):
    """工具执行失败。"""


class AgentOutputParseError(ApplicationError):
    """Agent 输出解析失败。"""


class FeishuPublishError(ApplicationError):
    """飞书消息发送失败。"""


class PersistenceError(ApplicationError):
    """持久化失败。"""
