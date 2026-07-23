"""文件知识源 - 支持 Markdown、TXT 等文本文件."""

from __future__ import annotations

import asyncio
from pathlib import Path

from config import get_settings
from core.exceptions import KnowledgeException
from core.logger import get_logger
from utils.helpers import chunk_text
from services.knowledge.base import KnowledgeItem, KnowledgeSource

logger = get_logger("knowledge.text_source")


class FileKnowledgeSource(KnowledgeSource):
    """文件知识源.

    从指定目录加载 Markdown、TXT 等文本文件。
    """

    SUPPORTED_EXTENSIONS = {".md", ".txt", ".markdown"}

    def __init__(self, directory: str | None = None) -> None:
        settings = get_settings()
        self._directory = Path(directory or settings.KNOWLEDGE_DIR)
        self._chunk_size = settings.KNOWLEDGE_CHUNK_SIZE
        self._chunk_overlap = settings.KNOWLEDGE_CHUNK_OVERLAP

    def get_source_name(self) -> str:
        """获取源名称."""
        return f"file:{self._directory}"

    async def load(self) -> list[KnowledgeItem]:
        """加载目录中的所有文本文件.

        Returns:
            知识条目列表.

        Raises:
            KnowledgeException: 目录不存在时抛出.
        """
        if not self._directory.exists():
            raise KnowledgeException(
                f"知识库目录不存在: {self._directory}",
                details={"directory": str(self._directory)},
            )

        items: list[KnowledgeItem] = []

        # 使用 to_thread 避免阻塞事件循环
        files = await asyncio.to_thread(self._scan_files)

        for file_path in files:
            try:
                file_items = await self._load_file(file_path)
                items.extend(file_items)
            except Exception as e:
                logger.warning(f"加载知识文件失败 {file_path}: {e}")

        logger.info(f"知识库加载完成: {len(items)} 个条目，来自 {len(files)} 个文件")
        return items

    def _scan_files(self) -> list[Path]:
        """扫描目录中所有支持的文件.

        Returns:
            文件路径列表.
        """
        files: list[Path] = []
        for ext in self.SUPPORTED_EXTENSIONS:
            files.extend(self._directory.rglob(f"*{ext}"))
        return sorted(files)

    async def _load_file(self, file_path: Path) -> list[KnowledgeItem]:
        """加载单个文件.

        Args:
            file_path: 文件路径.

        Returns:
            知识条目列表.
        """
        items: list[KnowledgeItem] = []

        content = await asyncio.to_thread(self._read_file, file_path)

        if not content.strip():
            return items

        # 分块
        chunks = chunk_text(content, self._chunk_size, self._chunk_overlap)

        for idx, chunk in enumerate(chunks):
            items.append(
                KnowledgeItem(
                    content=chunk,
                    source=str(file_path),
                    chunk_index=idx,
                    metadata={"file_name": file_path.name},
                )
            )

        logger.debug(f"加载知识文件: {file_path.name} ({len(chunks)} 块)")
        return items

    def _read_file(self, file_path: Path) -> str:
        """读取文件内容.

        Args:
            file_path: 文件路径.

        Returns:
            文件内容.
        """
        for encoding in ("utf-8", "gbk", "gb2312"):
            try:
                return file_path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise KnowledgeException(f"无法读取文件 (编码问题): {file_path}")
