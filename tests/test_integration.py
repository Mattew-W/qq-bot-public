"""系统集成测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.knowledge import KnowledgeIndexer, KnowledgeItem
from services.anti_spam import KeywordRule


class TestKnowledgeIntegration:
    """知识库集成测试."""

    @pytest.mark.asyncio
    async def test_full_rag_pipeline(self):
        """完整 RAG 流水线."""
        # 1. 创建知识库
        items = [
            KnowledgeItem(content="Python 是一种编程语言，由 Guido van Rossum 创建。", source="py.md", chunk_index=0),
            KnowledgeItem(content="Python 具有简洁、易读的语法特点。", source="py.md", chunk_index=1),
            KnowledgeItem(content="Java 是一种广泛使用的面向对象编程语言。", source="java.md", chunk_index=0),
            KnowledgeItem(content="Java 具有跨平台、安全性高的特点。", source="java.md", chunk_index=1),
        ]

        # 2. 构建索引
        indexer = KnowledgeIndexer()
        indexer.build(items)
        assert indexer.size == 4

        # 3. 搜索
        results = indexer.search("Python 语言", top_k=2)
        assert len(results) > 0
        assert any("Python" in r["content"] for r in results)

        # 4. 搜索 Java
        results = indexer.search("Java 编程", top_k=2)
        assert any("Java" in r["content"] for r in results)


class TestAntiSpamIntegration:
    """反垃圾集成测试."""

    @pytest.mark.asyncio
    async def test_spam_detection_flow(self):
        """垃圾检测完整流程."""
        from services.anti_spam import get_default_rules

        rules = get_default_rules()

        # 正常消息
        normal_msg = "大家好，今天天气不错"
        hits = []
        for rule in rules:
            result = await rule.check(normal_msg, {"user_id": "u1", "group_id": "g1"})
            if result.hit:
                hits.append(result)

        assert len(hits) == 0

        # 垃圾消息
        spam_msg = "刷单日赚500，加微信 abc123，点击 http://spam.com，电话 13812345678"
        hits = []
        for rule in rules:
            result = await rule.check(spam_msg, {"user_id": "u1", "group_id": "g1"})
            if result.hit:
                hits.append(result)

        # 至少命中多个规则
        assert len(hits) >= 3
        total_score = sum(h["score"] for h in hits)
        assert total_score >= 40


class TestLLMServiceIntegration:
    """LLM 服务集成测试 (使用 Mock)."""

    @pytest.mark.asyncio
    async def test_llm_with_mocked_adapter(self):
        """LLM 服务 + Mock 适配器."""
        from services.llm_service import LLMService
        from unittest.mock import AsyncMock

        from adapters.longcat_adapter import LongCatAdapter

        mock_adapter = AsyncMock(spec=LongCatAdapter)
        mock_adapter.chat.return_value = {
            "choices": [{"message": {"content": "这是 AI 的回复。"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        service = LLMService(adapter=mock_adapter)
        messages = [{"role": "user", "content": "你好"}]
        reply = await service.ask(messages)

        assert reply == "这是 AI 的回复。"
        mock_adapter.chat.assert_called_once()


class TestPromptIntegration:
    """Prompt 集成测试."""

    def test_all_prompt_templates(self):
        """所有 prompt 模板."""
        from services.prompt_builder import (
            build_ai_qa_prompt,
            build_antispam_prompt,
            build_meituan_prompt,
        )

        # AI QA
        msgs = build_ai_qa_prompt("问题", ["知识1"], [{"role": "user", "content": "历史"}])
        assert len(msgs) >= 2

        # AntiSpam
        msgs = build_antispam_prompt("消息", [{"rule_name": "规则1", "score": 30}])
        assert len(msgs) == 2

        # Meituan
        msgs = build_meituan_prompt("问题", "数据摘要")
        assert len(msgs) == 2
