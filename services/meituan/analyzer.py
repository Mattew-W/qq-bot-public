"""数据分析器 - LLM 驱动的数据分析."""

from __future__ import annotations

from typing import Any

from config import get_settings
from core.exceptions import MeituanException
from core.logger import get_logger
from services.prompt_builder import build_meituan_prompt
from services.llm_service import get_llm_service
from services.meituan.data_cleaner import DataCleaner
from services.meituan.data_loader import DataLoader

logger = get_logger("meituan.analyzer")


class DataAnalyzer:
    """数据分析器.

    数据加载 → 清洗 → LLM 分析 → 格式化输出。
    """

    def __init__(self) -> None:
        self._loader = DataLoader()
        self._cleaner = DataCleaner()
        self._llm = get_llm_service()

    async def load_and_analyze(
        self,
        file_path: str,
        question: str,
    ) -> str:
        """加载文件并分析.

        Args:
            file_path: 数据文件路径.
            question: 分析问题.

        Returns:
            分析结果.
        """
        try:
            # 1. 加载数据
            records = await self._loader.load(file_path)

            # 2. 清洗数据
            cleaned = self._cleaner.clean(records)

            # 3. 生成摘要
            summary = self._cleaner.summarize(cleaned)

            # 4. 构造 prompt
            summary_text = (
                f"总记录数: {summary['total_records']}\n"
                f"字段数: {summary['field_count']}\n"
                f"字段列表: {list(summary['fields'].keys())}\n"
                f"样本数据 (前5条):\n"
            )
            for i, record in enumerate(cleaned[:5]):
                summary_text += f"  记录{i+1}: {record}\n"

            # 5. 调用 LLM
            messages = build_meituan_prompt(
                question=question,
                data_summary=summary_text,
            )

            reply = await self._llm.ask(messages=messages)
            return reply

        except MeituanException:
            raise
        except Exception as e:
            logger.error(f"分析失败: {e}")
            raise MeituanException(f"分析失败: {e}")

    async def quick_stats(self, file_path: str) -> dict[str, Any]:
        """快速统计 - 不调用 LLM.

        Args:
            file_path: 数据文件路径.

        Returns:
            统计结果.
        """
        records = await self._loader.load(file_path)
        cleaned = self._cleaner.clean(records)
        return self._cleaner.summarize(cleaned)
