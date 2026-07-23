"""工具函数测试."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from utils.helpers import (
    chunk_text,
    clean_text,
    extract_phone_numbers,
    extract_qq_numbers,
    extract_urls,
    hash_text,
    truncate_text,
)


class TestHashText:
    """测试哈希函数."""

    def test_same_input_same_hash(self):
        """相同输入产生相同哈希."""
        h1 = hash_text("hello")
        h2 = hash_text("hello")
        assert h1 == h2

    def test_different_input_different_hash(self):
        """不同输入产生不同哈希."""
        h1 = hash_text("hello")
        h2 = hash_text("world")
        assert h1 != h2

    def test_hash_length(self):
        """哈希长度为 64 (SHA256 十六进制)."""
        h = hash_text("test")
        assert len(h) == 64


class TestChunkText:
    """测试文本分块."""

    def test_short_text(self):
        """短文本不分割."""
        chunks = chunk_text("hello", chunk_size=100)
        assert len(chunks) == 1
        assert chunks[0] == "hello"

    def test_long_text(self):
        """长文本正确分割."""
        text = "a" * 1000
        chunks = chunk_text(text, chunk_size=300, overlap=50)
        assert len(chunks) > 1

    def test_overlap(self):
        """重叠区域正确."""
        text = "a" * 200
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        # 第一块结尾和第二块开头应该有重叠
        assert chunks[0][-20:] == chunks[1][:20]

    def test_invalid_chunk_size(self):
        """非法 chunk_size."""
        with pytest.raises(ValueError):
            chunk_text("test", chunk_size=0)

    def test_overlap_too_large(self):
        """overlap 大于 chunk_size."""
        with pytest.raises(ValueError):
            chunk_text("test", chunk_size=100, overlap=100)


class TestCleanText:
    """测试文本清理."""

    def test_remove_zero_width(self):
        """移除零宽字符."""
        text = "hello\u200bworld"
        assert clean_text(text) == "hello world"

    def test_merge_whitespace(self):
        """合并连续空白."""
        text = "hello    world"
        assert clean_text(text) == "hello world"

    def test_strip(self):
        """去除首尾空白."""
        text = "  hello  "
        assert clean_text(text) == "hello"


class TestExtractUrls:
    """测试 URL 提取."""

    def test_http_url(self):
        """提取 http URL."""
        text = "访问 http://example.com 查看"
        urls = extract_urls(text)
        assert "http://example.com" in urls

    def test_https_url(self):
        """提取 https URL."""
        text = "访问 https://example.com/path 查看"
        urls = extract_urls(text)
        assert "https://example.com/path" in urls

    def test_multiple_urls(self):
        """提取多个 URL."""
        text = "http://a.com 和 https://b.com"
        urls = extract_urls(text)
        assert len(urls) == 2


class TestExtractQqNumbers:
    """测试 QQ 号提取."""

    def test_valid_qq(self):
        """提取有效 QQ 号."""
        text = "联系我 12345678"
        numbers = extract_qq_numbers(text)
        assert "12345678" in numbers

    def test_ignore_short(self):
        """忽略过短数字."""
        text = "数字 1234"
        numbers = extract_qq_numbers(text)
        assert "1234" not in numbers


class TestExtractPhoneNumbers:
    """测试手机号提取."""

    def test_valid_phone(self):
        """提取有效手机号."""
        text = "电话 13812345678"
        phones = extract_phone_numbers(text)
        assert "13812345678" in phones

    def test_invalid_phone(self):
        """忽略无效手机号."""
        text = "电话 12345678901"
        phones = extract_phone_numbers(text)
        assert "12345678901" not in phones


class TestTruncateText:
    """测试文本截断."""

    def test_no_truncate(self):
        """不需要截断."""
        text = "short"
        assert truncate_text(text, max_length=100) == "short"

    def test_truncate(self):
        """截断长文本."""
        text = "a" * 300
        result = truncate_text(text, max_length=200)
        assert len(result) == 200
        assert result.endswith("...")
