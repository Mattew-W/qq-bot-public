"""数据分析测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.analysis.data_cleaner import DataCleaner
from services.analysis.data_loader import DataLoader


class TestDataCleaner:
    """测试数据清洗器."""

    def test_clean_removes_duplicates(self):
        """测试去重."""
        records = [
            {"name": "Alice", "age": "25"},
            {"name": "Alice", "age": "25"},
            {"name": "Bob", "age": "30"},
        ]
        cleaned = DataCleaner.clean(records)
        assert len(cleaned) == 2

    def test_clean_converts_types(self):
        """测试类型转换."""
        records = [{"value": "42"}]
        cleaned = DataCleaner.clean(records)
        assert cleaned[0]["value"] == 42

    def test_summarize(self):
        """测试摘要."""
        records = [
            {"name": "Alice", "score": "85"},
            {"name": "Bob", "score": "92"},
        ]
        summary = DataCleaner.summarize(records)
        assert summary["total_records"] == 2
        assert "name" in summary["fields"]
