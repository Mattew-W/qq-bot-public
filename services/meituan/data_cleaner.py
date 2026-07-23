"""数据清洗器 - 数据预处理."""

from __future__ import annotations

import re
from typing import Any

from core.logger import get_logger

logger = get_logger("meituan.cleaner")


class DataCleaner:
    """数据清洗器.

    处理缺失值、格式转换、异常值检测。
    """

    @staticmethod
    def clean(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """清洗数据记录.

        Args:
            records: 原始记录.

        Returns:
            清洗后的记录.
        """
        if not records:
            return []

        cleaned = []
        for record in records:
            cleaned_record = {}
            for key, value in record.items():
                # 清洗键名
                clean_key = DataCleaner._clean_key(key)
                # 清洗值
                clean_value = DataCleaner._clean_value(value)
                cleaned_record[clean_key] = clean_value
            cleaned.append(cleaned_record)

        # 去除完全重复的记录
        unique = []
        seen = set()
        for record in cleaned:
            # 用 frozenset 做 hashable 的表示
            try:
                record_hash = hash(frozenset(
                    (k, str(v)) for k, v in record.items()
                ))
                if record_hash not in seen:
                    seen.add(record_hash)
                    unique.append(record)
            except TypeError:
                unique.append(record)

        logger.info(f"数据清洗: {len(records)} → {len(unique)} 条")
        return unique

    @staticmethod
    def _clean_key(key: str) -> str:
        """清洗键名."""
        # 去除空格、转小写
        key = str(key).strip()
        key = re.sub(r"\s+", "_", key)
        key = re.sub(r"[^\w\u4e00-\u9fff]", "", key)
        return key.lower() if key.isascii() else key

    @staticmethod
    def _clean_value(value: Any) -> Any:
        """清洗值."""
        if value is None:
            return None

        if isinstance(value, str):
            value = value.strip()
            # 尝试转换为数字
            if value == "":
                return None
            # 去除千分位逗号
            if "," in value and value.replace(",", "").replace(".", "").isdigit():
                value = value.replace(",", "")
            # 尝试转 float
            try:
                num = float(value)
                # 如果是整数则返回 int
                if num == int(num):
                    return int(num)
                return num
            except (ValueError, OverflowError):
                pass

            return value

        return value

    @staticmethod
    def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
        """生成数据摘要.

        Args:
            records: 数据记录.

        Returns:
            数据摘要.
        """
        if not records:
            return {"total_records": 0, "field_count": 0, "fields": {}}

        # 收集所有字段
        all_fields: dict[str, dict[str, Any]] = {}
        for record in records:
            for key, value in record.items():
                if key not in all_fields:
                    all_fields[key] = {
                        "type": set(),
                        "non_null": 0,
                        "sample_values": [],
                    }
                all_fields[key]["type"].add(type(value).__name__)
                if value is not None:
                    all_fields[key]["non_null"] += 1
                    if len(all_fields[key]["sample_values"]) < 5:
                        all_fields[key]["sample_values"].append(value)

        # 格式化
        fields_summary = {}
        for key, info in all_fields.items():
            fields_summary[key] = {
                "types": list(info["type"]),
                "non_null_count": info["non_null"],
                "sample_values": info["sample_values"],
            }

        return {
            "total_records": len(records),
            "field_count": len(all_fields),
            "fields": fields_summary,
        }
