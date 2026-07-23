"""知识库服务 - 向后兼容导出.

实际实现位于 services/knowledge/ 子模块。
"""

from services.knowledge import (
    KnowledgeService,
    KnowledgeSource,
    KnowledgeItem,
    FileKnowledgeSource,
    KnowledgeIndexer,
    get_knowledge_service,
)

__all__ = [
    "KnowledgeService",
    "KnowledgeSource",
    "KnowledgeItem",
    "FileKnowledgeSource",
    "KnowledgeIndexer",
    "get_knowledge_service",
]
