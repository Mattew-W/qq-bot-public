"""端到端测试 - 集成测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.llm_service import LLMService
from services.knowledge_service import KnowledgeService
from services.anti_spam_service import AntiSpamService
from services.action_service import ActionService
from services.prompt_builder import (
    PromptBuilder,
    build_ai_qa_prompt,
    build_antispam_prompt,
    build_meituan_prompt,
)
from services.anti_spam import get_default_rules


class TestPromptBuilderE2E:
    """Prompt Builder 端到端测试."""

    def test_full_qa_prompt_flow(self):
        """完整 QA prompt 流程."""
        messages = build_ai_qa_prompt(
            question="什么是 Python？",
            knowledge=[
                "Python 是一种解释型、面向对象、动态数据类型的高级程序设计语言。",
                "Python 由 Guido van Rossum 于 1989 年底发明。",
            ],
            history=[
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！有什么可以帮你的？"},
            ],
        )

        # 验证结构
        assert len(messages) == 4  # system + 2 history + user
        assert messages[0]["role"] == "system"
        assert "Python" in messages[0]["content"]
        assert messages[-1]["role"] == "user"
        assert messages[-1]["content"] == "什么是 Python？"

    def test_antispam_prompt_flow(self):
        """完整反垃圾 prompt 流程."""
        rule_hits = [
            {"rule_name": "手机号", "score": 40},
            {"rule_name": "微信号", "score": 35},
        ]

        messages = build_antispam_prompt("加我微信 13812345678", rule_hits)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "13812345678" in messages[1]["content"]

    def test_meituan_prompt_flow(self):
        """完整美团分析 prompt 流程."""
        messages = build_meituan_prompt(
            question="本月销售额趋势如何？",
            data_summary="总销售额: 100万\n订单数: 5000",
        )

        assert len(messages) == 2
        assert "100万" in messages[0]["content"]
        assert "销售额趋势" in messages[1]["content"]


class TestRulesE2E:
    """规则引擎端到端测试."""

    @pytest.mark.asyncio
    async def test_normal_message(self):
        """正常消息不触发规则."""
        rules = get_default_rules()
        from services.anti_spam.rules import KeywordRule

        # 只使用关键词规则测试
        rule = KeywordRule("ad", 30, ["刷单", "兼职"])
        result = await rule.check("今天天气真好", {})
        assert result.hit is False

    @pytest.mark.asyncio
    async def test_spam_message(self):
        """垃圾消息触发规则."""
        from services.anti_spam.rules import KeywordRule

        rule = KeywordRule("ad", 30, ["刷单", "兼职"])
        result = await rule.check("刷单日赚500，轻松月入过万", {})
        assert result.hit is True
        assert result.score == 30

    @pytest.mark.asyncio
    async def test_all_default_rules(self):
        """测试所有默认规则."""
        rules = get_default_rules()
        assert len(rules) >= 5


class TestCacheE2E:
    """缓存端到端测试."""

    def test_lru_cache_basic(self):
        """LRU 缓存基本功能."""
        from core.cache import LRUCache

        cache = LRUCache[str, str](max_size=3)

        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")

        assert cache.get("a") == "1"
        assert cache.get("b") == "2"
        assert cache.size() == 3

        # 添加第 4 个，最早的被驱逐
        cache.put("d", "4")
        assert cache.size() == 3

    def test_lru_cache_eviction(self):
        """LRU 缓存淘汰."""
        from core.cache import LRUCache

        cache = LRUCache[str, str](max_size=2)

        cache.put("a", "1")
        cache.put("b", "2")
        cache.get("a")  # 访问 a，使其更新
        cache.put("c", "3")  # b 应该被淘汰

        assert cache.get("a") == "1"
        assert cache.get("c") == "3"


class TestHelpersE2E:
    """工具函数端到端测试."""

    def test_text_processing_pipeline(self):
        """文本处理流水线."""
        from utils.helpers import clean_text, chunk_text, hash_text

        raw = "  Hello\u200b   World  \n\n  Test  "
        cleaned = clean_text(raw)
        assert cleaned == "Hello World Test"

        chunks = chunk_text(cleaned, chunk_size=10, overlap=2)
        assert len(chunks) > 0

        h = hash_text(cleaned)
        assert len(h) == 64

    def test_extract_pipeline(self):
        """提取工具流水线."""
        from utils.helpers import extract_urls, extract_phone_numbers, extract_qq_numbers

        text = "访问 https://example.com 联系我 13812345678 或 QQ 987654321"

        urls = extract_urls(text)
        phones = extract_phone_numbers(text)
        qqs = extract_qq_numbers(text)

        assert len(urls) == 1
        assert len(phones) == 1
        assert len(qqs) >= 1


class TestConfigE2E:
    """配置端到端测试."""

    def test_config_loads(self):
        """配置正确加载."""
        from config import Settings

        settings = Settings(_env_file=None)
        assert settings.BOT_APP_ID == ""
        assert settings.LONGCAT_MODEL == "longcat-chat"
        assert settings.DEBUG is False
        assert settings.LOG_LEVEL == "INFO"
