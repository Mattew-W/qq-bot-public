"""数据加载器 - 支持 CSV/Excel/JSON."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from core.exceptions import MeituanException
from core.logger import get_logger

logger = get_logger("meituan.loader")


class DataLoader:
    """数据加载器.

    支持 CSV、Excel、JSON 格式。
    """

    @staticmethod
    async def load(file_path: str) -> list[dict[str, Any]]:
        """加载数据文件.

        Args:
            file_path: 文件路径.

        Returns:
            数据记录列表.

        Raises:
            MeituanException: 文件不存在或格式不支持.
        """
        path = Path(file_path)

        if not path.exists():
            raise MeituanException(f"文件不存在: {file_path}")

        suffix = path.suffix.lower()

        if suffix == ".csv":
            return DataLoader._load_csv(path)
        elif suffix in (".xls", ".xlsx"):
            return DataLoader._load_excel(path)
        elif suffix == ".json":
            return DataLoader._load_json(path)
        else:
            raise MeituanException(f"不支持的文件格式: {suffix}")

    @staticmethod
    def _load_csv(path: Path) -> list[dict[str, Any]]:
        """加载 CSV 文件."""
        records = []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(dict(row))
        except UnicodeDecodeError:
            # 尝试 GBK 编码
            with open(path, "r", encoding="gbk") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    records.append(dict(row))

        logger.info(f"CSV 加载完成: {path.name} ({len(records)} 行)")
        return records

    @staticmethod
    def _load_excel(path: Path) -> list[dict[str, Any]]:
        """加载 Excel 文件."""
        try:
            import openpyxl
        except ImportError:
            raise MeituanException("请先安装 openpyxl: pip install openpyxl")

        wb = openpyxl.load_workbook(path, read_only=True)
        try:
            ws = wb.active

            if ws is None:
                raise MeituanException("Excel 文件无有效工作表")

            rows = list(ws.iter_rows(values_only=True))
            if len(rows) < 2:
                return []

            headers = [str(h) if h else f"col_{i}" for i, h in enumerate(rows[0])]
            records = []

            for row in rows[1:]:
                record = {headers[i]: val for i, val in enumerate(row) if i < len(headers)}
                records.append(record)

            logger.info(f"Excel 加载完成: {path.name} ({len(records)} 行)")
            return records
        finally:
            wb.close()

    @staticmethod
    def _load_json(path: Path) -> list[dict[str, Any]]:
        """加载 JSON 文件."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # 尝试提取列表
            for key, val in data.items():
                if isinstance(val, list):
                    return val
            return [data]
        else:
            raise MeituanException("JSON 格式不正确，需要对象列表")
