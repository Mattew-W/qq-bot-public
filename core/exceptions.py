"""统一异常定义.

所有自定义异常继承自 BotException，便于统一捕获和处理。
"""


class BotException(Exception):
    """机器人基础异常."""

    def __init__(self, message: str = "机器人内部错误", details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigException(BotException):
    """配置相关异常."""


class DatabaseException(BotException):
    """数据库相关异常."""


class LLMException(BotException):
    """LLM 调用相关异常."""


class KnowledgeException(BotException):
    """知识库相关异常."""


class AntiSpamException(BotException):
    """反垃圾相关异常."""


class MeituanException(BotException):
    """美团分析相关异常."""
