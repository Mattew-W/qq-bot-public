"""数据清洗器 - 数据预处理."""

from __future__ import annotations

import re
from typing import Any

from core.logger import get_logger

logger = get_logger("analysis.cleaner")


class DataCleaner:
    """数据清洗器.

    处理缺失值、格式转换、异常值检测。
    """

    @staticmethod
    def clean(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """清洗数据记录."""
        if not records:
            return []

        cleaned = []
        for record in records:
            cleaned_record = {}
            for key, value in record.items():
                clean_key = DataCleaner._clean_key(key)
                clean_value = DataCleaner._clean_value(value)
                cleaned_record[clean_key] = clean_value
            cleaned.append(cleaned_record)

        unique = []
        seen = set()
        for record in cleaned:
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
            if value == "":
                return None
            if "," in value and value.replace(",", "").replace(".", "").isdigit():
                value = value.replace(",", "")
            try:
                num = float(value)
                if num == int(num):
                    return int(num)
                return num
            except (ValueError, OverflowError):
                pass

            return value

        return value

    @staticmethod
    def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
        """生成数据摘要."""
        if not records:
            return {"total_records": 0, "field_count": 0, "fields": {}}

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
