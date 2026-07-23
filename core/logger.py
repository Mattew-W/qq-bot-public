"""统一日志模块.

提供结构化的日志输出，支持按天自动切分。
使用 loguru 作为底层日志库。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from config.settings import Settings

# 日志格式
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 已注册的 logger 实例缓存
_LOGGERS: dict[str, "LoggerWrap"] = {}


class LoggerWrap:
    """Logger 包装类，提供语义化日志方法."""

    def __init__(self, name: str) -> None:
        self._name = name
        self._logger = logger.bind(name=name)

    def info(self, message: str, **kwargs) -> None:
        """记录 INFO 级别日志."""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """记录 WARNING 级别日志."""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """记录 ERROR 级别日志."""
        self._logger.error(message, **kwargs)

    def debug(self, message: str, **kwargs) -> None:
        """记录 DEBUG 级别日志."""
        self._logger.debug(message, **kwargs)

    def llm(self, message: str, **kwargs) -> None:
        """记录 LLM 调用相关日志."""
        self._logger.log("LLM", message, **kwargs)

    def spam(self, message: str, **kwargs) -> None:
        """记录反垃圾相关日志."""
        self._logger.log("SPAM", message, **kwargs)

    def action(self, message: str, **kwargs) -> None:
        """记录动作执行相关日志."""
        self._logger.log("ACTION", message, **kwargs)


def setup_logging(settings: "Settings") -> None:
    """初始化全局日志配置.

    Args:
        settings: 应用配置实例.
    """
    # 移除默认 handler
    logger.remove()

    # 控制台输出
    logger.add(
        sys.stdout,
        format=LOG_FORMAT,
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # 文件输出 - 按天切分
    log_dir = Path(settings.LOG_DIR)
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_dir / "bot_{time:YYYY-MM-DD}.log"),
        format=LOG_FORMAT,
        level=settings.LOG_LEVEL,
        rotation="00:00",  # 每天 0 点切分
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,  # 异步写入
    )

    # 错误日志单独文件
    logger.add(
        str(log_dir / "error_{time:YYYY-MM-DD}.log"),
        format=LOG_FORMAT,
        level="ERROR",
        rotation="00:00",
        retention=settings.LOG_RETENTION,
        encoding="utf-8",
        enqueue=True,
    )

    # 注册自定义级别
    logger.level("LLM", no=25, color="<magenta>", icon="🤖")
    logger.level("SPAM", no=26, color="<yellow>", icon="🛡️")
    logger.level("ACTION", no=27, color="<blue>", icon="⚡")


def get_logger(name: str) -> LoggerWrap:
    """获取命名 Logger.

    Args:
        name: 模块名称.

    Returns:
        LoggerWrap 实例.
    """
    if name not in _LOGGERS:
        _LOGGERS[name] = LoggerWrap(name)
    return _LOGGERS[name]
