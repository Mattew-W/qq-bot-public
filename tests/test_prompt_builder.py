"""Prompt Builder 测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.prompt_builder import (
    PromptBuilder,
    build_ai_qa_prompt,
    build_antispam_prompt,
    build_meituan_prompt,
)


class TestPromptBuilder:
    """测试 Prompt 构造器."""

    def test_basic_build(self):
        """测试基本构造."""
        builder = PromptBuilder()
        messages = (
            builder.set_system("你是助手")
            .set_user("你好")
            .build()
        )
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "你是助手"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "你好"

    def test_with_context(self):
        """测试带上下文的构造."""
        builder = PromptBuilder()
        messages = (
            builder.set_system("你是助手")
            .add_context("知识1")
            .add_context("知识2")
            .set_user("问题")
            .build()
        )
        assert len(messages) == 2
        assert "知识1" in messages[0]["content"]
        assert "知识2" in messages[0]["content"]

    def test_with_history(self):
        """测试带历史对话的构造."""
        builder = PromptBuilder()
        messages = (
            builder.set_system("你是助手")
            .add_history("user", "你好")
            .add_history("assistant", "你好！")
            .set_user("再见")
            .build()
        )
        assert len(messages) == 4  # system + 2 history + user

    def test_with_constraints(self):
        """测试带约束的构造."""
        builder = PromptBuilder()
        messages = (
            builder.set_system("你是助手")
            .add_constraint("简短回复")
            .add_constraint("使用中文")
            .set_user("你好")
            .build()
        )
        assert "简短回复" in messages[0]["content"]
        assert "使用中文" in messages[0]["content"]

    def test_with_output_format(self):
        """测试带输出格式的构造."""
        builder = PromptBuilder()
        messages = (
            builder.set_system("你是助手")
            .set_output_format("JSON 格式")
            .set_user("你好")
            .build()
        )
        assert "JSON 格式" in messages[0]["content"]

    def test_reset(self):
        """测试重置."""
        builder = PromptBuilder()
        builder.set_system("系统").set_user("用户")
        builder.reset()
        messages = builder.build()
        assert messages == []

    def test_empty_build(self):
        """测试空构造."""
        builder = PromptBuilder()
        messages = builder.build()
        assert messages == []


class TestPredefinedPrompts:
    """测试预定义 Prompt 模板."""

    def test_build_ai_qa_prompt(self):
        """测试 AI 问答 Prompt."""
        messages = build_ai_qa_prompt(
            question="什么是 Python？",
            knowledge=["Python 是一种编程语言"],
            history=[{"role": "user", "content": "你好"}],
        )
        assert len(messages) >= 2
        assert messages[-1]["content"] == "什么是 Python？"

    def test_build_ai_qa_prompt_no_knowledge(self):
        """测试无知识库的 AI 问答 Prompt."""
        messages = build_ai_qa_prompt(question="你好")
        assert len(messages) == 2
        assert messages[-1]["content"] == "你好"

    def test_build_antispam_prompt(self):
        """测试反垃圾 Prompt."""
        rule_hits = [
            {"rule_name": "手机号", "score": 40},
            {"rule_name": "微信号", "score": 35},
        ]
        messages = build_antispam_prompt("加我微信 13812345678", rule_hits)
        assert len(messages) == 2
        assert "13812345678" in messages[1]["content"]
        assert "手机号" in messages[1]["content"]

    def test_build_meituan_prompt(self):
        """测试美团分析 Prompt."""
        messages = build_meituan_prompt(
            question="本月销售额是多少？",
            data_summary="总销售额: 100万",
        )
        assert len(messages) == 2
        assert "100万" in messages[0]["content"]
        assert "本月销售额" in messages[1]["content"]
