"""端到端测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from config import Settings


class TestE2E:
    """端到端测试."""

    def test_settings_load_without_env(self):
        """测试无 .env 时加载默认配置."""
        settings = Settings(_env_file=None)
        assert settings.LLM_MODEL == "gpt-4o-mini"
        assert settings.LOG_LEVEL == "INFO"
        assert settings.DEBUG is False
