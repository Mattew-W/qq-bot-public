"""知识库索引器 - 基于倒排检索 + BM25.

当前使用内存索引，以后可无缝替换为 FAISS/Chroma/Milvus。
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from core.logger import get_logger
from services.knowledge.base import KnowledgeItem, KnowledgeSource

logger = get_logger("knowledge.indexer")


class KnowledgeIndexer:
    """知识库索引器.

    使用 BM25 算法进行检索。
    后续可替换为向量检索而不影响业务代码。
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self._k1 = k1  # BM25 参数
        self._b = b    # BM25 参数
        self._items: list[KnowledgeItem] = []
        self._inverted_index: dict[str, set[int]] = defaultdict(set)
        self._idf: dict[str, float] = {}
        self._doc_lengths: list[int] = []
        self._avg_doc_length: float = 0.0
        self._is_built: bool = False

    @property
    def size(self) -> int:
        """返回索引中的文档数."""
        return len(self._items)

    def build(self, items: list[KnowledgeItem]) -> None:
        """构建索引.

        Args:
            items: 知识条目列表.
        """
        self._items = items
        self._build_index()
        self._is_built = True
        logger.info(f"知识库索引构建完成: {len(items)} 个条目")

    def _tokenize(self, text: str) -> list[str]:
        """分词 - 简单字符级 + 单词级.

        Args:
            text: 输入文本.

        Returns:
            token 列表.
        """
        # 转小写
        text = text.lower()
        # 提取中文字符和英文单词
        tokens = re.findall(r"[\u4e00-\u9fff]|[a-z]+", text)
        return tokens

    def _build_index(self) -> None:
        """构建倒排索引和 IDF."""
        self._inverted_index.clear()
        self._doc_lengths = []
        total_length = 0

        # 构建倒排索引
        for idx, item in enumerate(self._items):
            tokens = self._tokenize(item.content)
            self._doc_lengths.append(len(tokens))
            total_length += len(tokens)

            # 记录每个词出现在哪些文档中
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self._inverted_index[token].add(idx)

        # 计算 IDF
        n = len(self._items)
        self._idf = {}
        for token, doc_set in self._inverted_index.items():
            df = len(doc_set)
            # 使用平滑 IDF
            self._idf[token] = math.log((n - df + 0.5) / (df + 0.5) + 1.0)

        self._avg_doc_length = total_length / n if n > 0 else 1.0

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """搜索相关知识.

        Args:
            query: 查询文本.
            top_k: 返回结果数.

        Returns:
            相关片段列表，按相关性降序排列.
        """
        if not self._is_built:
            logger.warning("索引未构建，返回空结果")
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # 找到包含任一查询词的文档
        candidate_docs: set[int] = set()
        for token in query_tokens:
            candidate_docs.update(self._inverted_index.get(token, set()))

        # 计算 BM25 分数
        scores: list[tuple[int, float]] = []
        for doc_id in candidate_docs:
            score = self._bm25_score(doc_id, query_tokens)
            scores.append((doc_id, score))

        # 按分数降序排列
        scores.sort(key=lambda x: x[1], reverse=True)

        # 返回 top_k 结果
        results = []
        for doc_id, score in scores[:top_k]:
            item = self._items[doc_id]
            results.append({
                "content": item.content,
                "source": item.source,
                "chunk_index": item.chunk_index,
                "score": round(score, 4),
                "metadata": item.metadata,
            })

        logger.debug(f"搜索: '{query[:30]}...' 命中 {len(results)} 条")
        return results

    def _bm25_score(self, doc_id: int, query_tokens: list[str]) -> float:
        """计算 BM25 分数.

        Args:
            doc_id: 文档 ID.
            query_tokens: 查询 token 列表.

        Returns:
            BM25 分数.
        """
        score = 0.0
        doc_length = self._doc_lengths[doc_id]

        # 统计文档中每个词的频率
        item = self._items[doc_id]
        doc_tokens = self._tokenize(item.content)
        tf_map: dict[str, int] = defaultdict(int)
        for token in doc_tokens:
            tf_map[token] += 1

        for token in query_tokens:
            if token not in self._idf:
                continue
            tf = tf_map.get(token, 0)
            if tf == 0:
                continue

            idf = self._idf[token]
            numerator = tf * (self._k1 + 1)
            denominator = tf + self._k1 * (1 - self._b + self._b * doc_length / self._avg_doc_length)
            score += idf * numerator / denominator

        return score

    def add_item(self, item: KnowledgeItem) -> None:
        """动态添加条目 (需要重新构建索引).

        Args:
            item: 知识条目.
        """
        self._items.append(item)
        self._is_built = False
