"""知识库服务 - 统一封装知识检索.

支持多数据源（Markdown/TXT/PDF/Word/向量数据库），
插件不关心知识来源，只调用 knowledge.search()。
"""

from __future__ import annotations

from typing import Any

from config import get_settings
from core.exceptions import KnowledgeException
from core.logger import get_logger
from services.knowledge.base import KnowledgeItem, KnowledgeSource
from services.knowledge.indexer import KnowledgeIndexer
from services.knowledge.text_source import FileKnowledgeSource

logger = get_logger("service.knowledge")


class KnowledgeService:
    """知识库服务.

    封装知识库搜索，支持多数据源。
    """

    def __init__(self) -> None:
        self._sources: list[KnowledgeSource] = []
        self._indexer = KnowledgeIndexer()
        self._is_loaded = False

    def register_source(self, source: KnowledgeSource) -> None:
        """注册知识源.

        Args:
            source: 知识源实例.
        """
        self._sources.append(source)
        logger.info(f"注册知识源: {source.get_source_name()}")

    async def load(self) -> None:
        """加载所有知识源并构建索引."""
        if not self._sources:
            # 默认注册文件知识源
            self.register_source(FileKnowledgeSource())

        all_items: list[KnowledgeItem] = []

        for source in self._sources:
            try:
                items = await source.load()
                all_items.extend(items)
                logger.info(f"知识源 {source.get_source_name()} 加载 {len(items)} 条")
            except KnowledgeException as e:
                logger.error(f"知识源 {source.get_source_name()} 加载失败: {e}")
            except Exception as e:
                logger.error(f"知识源 {source.get_source_name()} 未知错误: {e}")

        # 构建索引
        self._indexer.build(all_items)
        self._is_loaded = True
        logger.info(f"知识库加载完成: 共 {len(all_items)} 条")

    async def search(self, question: str, top_k: int = 5) -> list[dict[str, Any]]:
        """搜索相关知识.

        Args:
            question: 问题.
            top_k: 返回结果数.

        Returns:
            相关知识片段列表.
        """
        if not self._is_loaded:
            logger.warning("知识库未加载，尝试加载...")
            await self.load()

        return self._indexer.search(question, top_k)

    async def reload(self) -> None:
        """重新加载知识库."""
        self._is_loaded = False
        await self.load()

    @property
    def is_loaded(self) -> bool:
        """是否已加载."""
        return self._is_loaded

    @property
    def size(self) -> int:
        """索引中的条目数."""
        return self._indexer.size


_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    """获取知识库服务实例."""
    global _knowledge_service
    if _knowledge_service is None:
        _knowledge_service = KnowledgeService()
    return _knowledge_service
