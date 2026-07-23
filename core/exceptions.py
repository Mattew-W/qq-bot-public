"""自定义异常."""

from __future__ import annotations


class BotException(Exception):
    """机器人基础异常."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class LLMException(BotException):
    """LLM 调用异常."""
    pass


class AnalysisException(BotException):
    """数据分析异常."""
    pass
