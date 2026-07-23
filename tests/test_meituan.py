"""美团分析模块测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from services.meituan.data_cleaner import DataCleaner
from services.meituan.data_loader import DataLoader


class TestDataCleaner:
    """测试数据清洗器."""

    def test_clean_basic(self):
        """测试基本清洗."""
        records = [
            {" 姓名 ": " 张三 ", "年龄": "25", "工资": "10,000"},
            {"姓名": "李四", "年龄": "30", "工资": "15000"},
        ]
        cleaned = DataCleaner.clean(records)
        assert len(cleaned) == 2

    def test_clean_value_conversion(self):
        """测试值转换."""
        records = [{"value": "100"}]
        cleaned = DataCleaner.clean(records)
        assert cleaned[0]["value"] == 100

    def test_clean_float_conversion(self):
        """测试浮点数转换."""
        records = [{"value": "3.14"}]
        cleaned = DataCleaner.clean(records)
        assert cleaned[0]["value"] == 3.14

    def test_clean_empty_string(self):
        """测试空字符串."""
        records = [{"value": ""}]
        cleaned = DataCleaner.clean(records)
        assert cleaned[0]["value"] is None

    def test_summarize(self):
        """测试摘要生成."""
        records = [
            {"name": "A", "value": 100},
            {"name": "B", "value": 200},
            {"name": "C", "value": 300},
        ]
        summary = DataCleaner.summarize(records)
        assert summary["total_records"] == 3
        assert "name" in summary["fields"]

    def test_summarize_empty(self):
        """测试空记录摘要."""
        summary = DataCleaner.summarize([])
        assert summary["total_records"] == 0

    def test_clean_key_normalization(self):
        """测试键名标准化."""
        records = [{"User Name": "test"}]
        cleaned = DataCleaner.clean(records)
        assert "user_name" in cleaned[0]


class TestDataLoader:
    """测试数据加载器."""

    def test_unsupported_format(self):
        """测试不支持的格式."""
        with pytest.raises(Exception):
            DataLoader._load_csv(os.path.dirname(os.path.abspath(__file__)) + "/test.txt")

    def test_json_load(self, tmp_path):
        """测试 JSON 加载."""
        import json
        data = [{"a": 1}, {"b": 2}]
        file_path = tmp_path / "test.json"
        file_path.write_text(json.dumps(data))

        result = DataLoader._load_json(file_path)
        assert len(result) == 2

    def test_json_dict_format(self, tmp_path):
        """测试 JSON 对象格式."""
        import json
        data = {"items": [{"a": 1}, {"b": 2}]}
        file_path = tmp_path / "test.json"
        file_path.write_text(json.dumps(data))

        result = DataLoader._load_json(file_path)
        assert len(result) == 2
