"""通用工具函数."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable


def hash_text(text: str) -> str:
    """计算文本的 SHA256 哈希.

    Args:
        text: 输入文本.

    Returns:
        十六进制哈希字符串.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """将长文本切分为重叠的块.

    Args:
        text: 输入文本.
        chunk_size: 每块最大字符数.
        overlap: 相邻块之间的重叠字符数.

    Returns:
        文本块列表.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start += chunk_size - overlap

    return chunks


def clean_text(text: str) -> str:
    """清理文本 - 去除多余空白、特殊字符.

    Args:
        text: 输入文本.

    Returns:
        清理后的文本.
    """
    # 去除零宽字符
    text = re.sub(r"[\u200b-\u200f\ufeff]", "", text)
    # 合并连续空白
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_urls(text: str) -> list[str]:
    """提取文本中的 URL.

    Args:
        text: 输入文本.

    Returns:
        URL 列表.
    """
    pattern = r"https?://[^\s<>\")\]]+"
    return re.findall(pattern, text)


def extract_qq_numbers(text: str) -> list[str]:
    """提取文本中的 QQ 号码 (5-11位数字).

    Args:
        text: 输入文本.

    Returns:
        QQ 号码列表.
    """
    # 匹配独立的 QQ 号码（前后非数字）
    pattern = r"(?<!\d)(\d{5,11})(?!\d)"
    return re.findall(pattern, text)


def extract_phone_numbers(text: str) -> list[str]:
    """提取文本中的手机号 (11位 1开头).

    Args:
        text: 输入文本.

    Returns:
        手机号列表.
    """
    pattern = r"1[3-9]\d{9}"
    return re.findall(pattern, text)


def truncate_text(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """截断文本到指定长度.

    Args:
        text: 输入文本.
        max_length: 最大长度.
        suffix: 截断后缀.

    Returns:
        截断后的文本.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix
