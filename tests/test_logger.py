"""日志模块测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Settings
from core.logger import LoggerWrap, get_logger, setup_logging


class TestLogger:
    """测试日志模块."""

    def test_get_logger(self):
        """测试获取 logger."""
        logger = get_logger("test")
        assert isinstance(logger, LoggerWrap)
        assert logger._name == "test"

    def test_logger_singleton(self):
        """测试 logger 单例."""
        logger1 = get_logger("test_singleton")
        logger2 = get_logger("test_singleton")
        assert logger1 is logger2

    def test_setup_logging(self):
        """测试日志初始化."""
        settings = Settings(LOG_LEVEL="DEBUG", LOG_DIR="./test_logs", _env_file=None)
        setup_logging(settings)
        # 验证不抛出异常
        assert True

    def test_logger_methods(self):
        """测试日志方法."""
        logger = get_logger("test_methods")
        # 验证方法存在
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "llm")
        assert hasattr(logger, "spam")
        assert hasattr(logger, "action")
