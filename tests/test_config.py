"""配置模块测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config import Settings, get_settings


class TestSettings:
    """测试配置读取."""

    def test_default_values(self):
        """测试默认值."""
        settings = Settings(_env_file=None)
        assert settings.ONEBOT_WS_URL == "ws://127.0.0.1:8080"
        assert settings.LLM_MODEL == "gpt-4o-mini"
        assert settings.LLM_TEMPERATURE == 0.7
        assert settings.LOG_LEVEL == "INFO"
        assert settings.DEBUG is False

    def test_temperature_validation(self):
        """测试温度参数校验."""
        settings = Settings(LLM_TEMPERATURE=1.5, _env_file=None)
        assert settings.LLM_TEMPERATURE == 1.5

    def test_temperature_too_high(self):
        """测试温度超出范围."""
        with pytest.raises(Exception):
            Settings(LLM_TEMPERATURE=3.0, _env_file=None)

    def test_singleton(self):
        """测试配置单例."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2
