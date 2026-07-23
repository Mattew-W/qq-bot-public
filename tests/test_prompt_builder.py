"""Prompt Builder 测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.prompt_builder import (
    PromptBuilder,
    build_ai_qa_prompt,
    build_antispam_prompt,
    build_analysis_prompt,
)


class TestPromptBuilder:
    """测试 Prompt 构造器."""

    def test_builder_basic(self):
        """测试基本构造."""
        builder = PromptBuilder()
        builder.set_system("系统提示")
        builder.set_user("用户问题")
        messages = builder.build()
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    def test_builder_with_context(self):
        """测试带上下文的构造."""
        builder = PromptBuilder()
        builder.set_system("系统提示")
        builder.add_context("上下文1")
        builder.add_context("上下文2")
        builder.set_user("问题")
        messages = builder.build()
        assert len(messages) == 2
        assert "上下文1" in messages[0]["content"]
        assert "上下文2" in messages[0]["content"]

    def test_builder_with_history(self):
        """测试带历史对话的构造."""
        builder = PromptBuilder()
        builder.set_system("系统提示")
        builder.add_history("user", "你好")
        builder.add_history("assistant", "你好！")
        builder.set_user("今天天气怎样？")
        messages = builder.build()
        assert len(messages) == 4

    def test_builder_with_constraints(self):
        """测试带约束的构造."""
        builder = PromptBuilder()
        builder.set_system("系统提示")
        builder.add_constraint("约束1")
        builder.set_user("问题")
        messages = builder.build()
        assert "约束1" in messages[0]["content"]

    def test_builder_reset(self):
        """测试重置."""
        builder = PromptBuilder()
        builder.set_system("系统提示")
        builder.reset()
        builder.set_user("新问题")
        messages = builder.build()
        assert len(messages) == 1


class TestPromptTemplates:
    """测试预定义 Prompt 模板."""

    def test_ai_qa_prompt(self):
        """测试 AI QA Prompt."""
        msgs = build_ai_qa_prompt("问题", ["知识1", "知识2"], [{"role": "user", "content": "历史"}])
        assert len(msgs) >= 2

    def test_antispam_prompt(self):
        """测试反垃圾 Prompt."""
        msgs = build_antispam_prompt("消息", [{"rule_name": "规则1", "score": 30}])
        assert len(msgs) == 2

    def test_build_analysis_prompt(self):
        """测试数据分析 Prompt."""
        messages = build_analysis_prompt("问题", "数据摘要")
        assert len(messages) == 2
