"""反垃圾服务测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.anti_spam import (
    AntiSpamService,
    KeywordRule,
    RegexRule,
    UrlRule,
    ContactRule,
    RepeatRule,
    WechatRule,
    QRCodeRule,
)


class TestKeywordRule:
    """测试关键词规则."""

    @pytest.mark.asyncio
    async def test_hit(self):
        """测试命中."""
        rule = KeywordRule("test", 30, ["刷单", "兼职"])
        result = await rule.check("刷单日赚500", {})
        assert result.hit is True
        assert result.score == 30

    @pytest.mark.asyncio
    async def test_no_hit(self):
        """测试未命中."""
        rule = KeywordRule("test", 30, ["刷单", "兼职"])
        result = await rule.check("今天天气真好", {})
        assert result.hit is False
        assert result.score == 0


class TestUrlRule:
    """测试 URL 规则."""

    @pytest.mark.asyncio
    async def test_hit(self):
        """测试命中 URL."""
        rule = UrlRule(score=20)
        result = await rule.check("点击链接 http://example.com", {})
        assert result.hit is True
        assert result.score == 20

    @pytest.mark.asyncio
    async def test_no_hit(self):
        """测试无 URL."""
        rule = UrlRule(score=20)
        result = await rule.check("普通消息", {})
        assert result.hit is False


class TestContactRule:
    """测试联系方式规则."""

    @pytest.mark.asyncio
    async def test_phone_hit(self):
        """测试手机号命中."""
        rule = ContactRule(score=35)
        result = await rule.check("加我 13812345678", {})
        assert result.hit is True

    @pytest.mark.asyncio
    async def test_qq_hit(self):
        """测试 QQ 号命中."""
        rule = ContactRule(score=35)
        result = await rule.check("联系我 987654321", {})
        assert result.hit is True

    @pytest.mark.asyncio
    async def test_group_id_filter(self):
        """测试群号过滤."""
        rule = ContactRule(score=35)
        result = await rule.check("群号 123456", {"group_id": "123456"})
        assert result.hit is False


class TestRepeatRule:
    """测试重复消息规则."""

    @pytest.mark.asyncio
    async def test_repeat_hit(self):
        """测试重复命中."""
        rule = RepeatRule(score=15, threshold=3)
        ctx = {"user_id": "user1"}

        await rule.check("相同消息", ctx)
        await rule.check("相同消息", ctx)
        result = await rule.check("相同消息", ctx)

        assert result.hit is True
        assert result.score == 15

    @pytest.mark.asyncio
    async def test_no_repeat(self):
        """测试不重复."""
        rule = RepeatRule(score=15, threshold=3)
        ctx = {"user_id": "user1"}

        result = await rule.check("不同消息1", ctx)
        assert result.hit is False


class TestWechatRule:
    """测试微信规则."""

    @pytest.mark.asyncio
    async def test_hit(self):
        """测试命中微信."""
        rule = WechatRule(score=35)
        result = await rule.check("加微信 abc123", {})
        assert result.hit is True

    @pytest.mark.asyncio
    async def test_no_hit(self):
        """测试未命中."""
        rule = WechatRule(score=35)
        result = await rule.check("普通聊天", {})
        assert result.hit is False


class TestAntiSpamService:
    """测试反垃圾服务."""

    @pytest.mark.asyncio
    async def test_low_risk(self):
        """测试低风险."""
        service = AntiSpamService()
        result = await service.check("今天天气真好", "user1", "group1")
        assert result["action"] == "log"

    @pytest.mark.asyncio
    async def test_high_risk(self):
        """测试高风险."""
        service = AntiSpamService()
        result = await service.check(
            "刷单日赚500 加微信 abc123 点击 http://spam.com 13812345678",
            "user1",
            "group1",
        )
        assert result["risk_score"] >= 40

    @pytest.mark.asyncio
    async def test_url_detection(self):
        """测试 URL 检测."""
        service = AntiSpamService()
        result = await service.check("访问 http://example.com 查看", "user1", "group1")
        assert any(r["rule_name"] == "url_detector" for r in result["rule_hits"])
