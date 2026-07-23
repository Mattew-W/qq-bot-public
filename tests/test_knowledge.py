"""知识库测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.knowledge import KnowledgeIndexer, KnowledgeItem, KnowledgeService
from services.knowledge.base import KnowledgeSource


class MockKnowledgeSource(KnowledgeSource):
    """Mock 知识源."""

    def __init__(self, items: list[KnowledgeItem]) -> None:
        self._items = items

    async def load(self) -> list[KnowledgeItem]:
        return self._items

    def get_source_name(self) -> str:
        return "mock"


class TestKnowledgeIndexer:
    """测试知识库索引器."""

    @pytest.fixture
    def indexer(self):
        """创建索引器."""
        idx = KnowledgeIndexer()
        items = [
            KnowledgeItem(content="Python 是一种编程语言", source="test.md", chunk_index=0),
            KnowledgeItem(content="Java 也是一种编程语言", source="test.md", chunk_index=1),
            KnowledgeItem(content="今天天气很好", source="test2.md", chunk_index=0),
        ]
        idx.build(items)
        return idx

    def test_build(self, indexer):
        """测试构建."""
        assert indexer.size == 3

    def test_search_exact_match(self, indexer):
        """测试精确匹配."""
        results = indexer.search("Python", top_k=5)
        assert len(results) > 0
        assert "Python" in results[0]["content"]

    def test_search_multiple_keywords(self, indexer):
        """测试多关键词."""
        results = indexer.search("编程语言", top_k=5)
        assert len(results) >= 2

    def test_search_no_match(self, indexer):
        """测试无匹配."""
        results = indexer.search("不存在的关键词", top_k=5)
        assert len(results) == 0

    def test_search_top_k(self, indexer):
        """测试 top_k 限制."""
        results = indexer.search("编程语言", top_k=1)
        assert len(results) == 1

    def test_search_sorted_by_score(self, indexer):
        """测试结果按分数排序."""
        results = indexer.search("编程语言", top_k=5)
        scores = [r["score"] for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_add_item(self, indexer):
        """测试动态添加."""
        new_item = KnowledgeItem(content="新条目", source="new.md", chunk_index=0)
        indexer.add_item(new_item)
        assert indexer.size == 4

    def test_search_empty_index(self):
        """测试空索引搜索."""
        idx = KnowledgeIndexer()
        results = idx.search("test", top_k=5)
        assert results == []


class TestKnowledgeService:
    """测试知识库服务."""

    @pytest.fixture
    def service(self):
        """创建服务."""
        return KnowledgeService()

    def test_register_source(self, service):
        """测试注册源."""
        source = MockKnowledgeSource([])
        service.register_source(source)
        assert len(service._sources) == 1

    def test_default_source(self, service):
        """测试默认源."""
        # 不注册任何源时，load 应该注册默认文件源
        pass  # 文件源需要真实文件，不在此测试

    @pytest.mark.asyncio
    async def test_load_with_mock_source(self, service):
        """测试加载 mock 源."""
        items = [
            KnowledgeItem(content="测试内容", source="mock", chunk_index=0),
        ]
        source = MockKnowledgeSource(items)
        service.register_source(source)
        await service.load()
        assert service.is_loaded is True
        assert service.size == 1

    @pytest.mark.asyncio
    async def test_search_before_load(self, service):
        """测试加载前搜索."""
        items = [
            KnowledgeItem(content="测试内容", source="mock", chunk_index=0),
        ]
        source = MockKnowledgeSource(items)
        service.register_source(source)
        # 搜索会自动触发加载
        results = await service.search("测试")
        assert len(results) > 0
