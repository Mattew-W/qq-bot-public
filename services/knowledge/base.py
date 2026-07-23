"""知识库基础抽象类."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class KnowledgeItem:
    """知识条目."""

    content: str
    source: str  # 来源文件
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "content": self.content,
            "source": self.source,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
        }


class KnowledgeSource(ABC):
    """知识源抽象基类.

    所有知识源（Markdown、PDF、Word、向量数据库等）必须实现此接口。
    """

    @abstractmethod
    async def load(self) -> list[KnowledgeItem]:
        """加载知识.

        Returns:
            知识条目列表.
        """
        ...

    @abstractmethod
    def get_source_name(self) -> str:
        """获取源名称.

        Returns:
            源名称.
        """
        ...
