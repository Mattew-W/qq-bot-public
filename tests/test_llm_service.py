"""LLM Service 测试."""

from __future__ import annotations

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from adapters.llm_adapter import LLMAdapter
from core.exceptions import LLMException
from services.llm_service import LLMService


class TestLLMService:
    """测试 LLM 服务."""

    @pytest.fixture
    def mock_adapter(self):
        """创建 mock 适配器."""
        adapter = AsyncMock(spec=LLMAdapter)
        adapter.chat.return_value = {
            "choices": [
                {"message": {"content": "你好，我是 AI 助手。"}}
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        }
        return adapter

    @pytest.fixture
    def llm_service(self, mock_adapter):
        """创建带 mock 适配器的 LLMService."""
        return LLMService(adapter=mock_adapter)

    @pytest.mark.asyncio
    async def test_ask_returns_content(self, llm_service, mock_adapter):
        """测试 ask 方法返回内容."""
        messages = [{"role": "user", "content": "你好"}]
        result = await llm_service.ask(messages)
        assert result == "你好，我是 AI 助手。"
        mock_adapter.chat.assert_called_once()

    @pytest.mark.asyncio
    async def test_ask_with_custom_params(self, llm_service, mock_adapter):
        """测试自定义参数."""
        messages = [{"role": "user", "content": "你好"}]
        await llm_service.ask(messages, temperature=0.5, max_tokens=1000)
        call_kwargs = mock_adapter.chat.call_args
        assert call_kwargs.kwargs["temperature"] == 0.5
        assert call_kwargs.kwargs["max_tokens"] == 1000

    @pytest.mark.asyncio
    async def test_ask_handles_error(self, mock_adapter):
        """测试错误处理."""
        mock_adapter.chat.side_effect = LLMException("API 错误")
        service = LLMService(adapter=mock_adapter)
        messages = [{"role": "user", "content": "你好"}]
        with pytest.raises(LLMException):
            await service.ask(messages)

    def test_extract_content_valid(self):
        """测试提取有效内容."""
        result = {
            "choices": [
                {"message": {"content": "回复内容"}}
            ]
        }
        assert LLMService._extract_content(result) == "回复内容"

    def test_extract_content_empty_choices(self):
        """测试空 choices."""
        result = {"choices": []}
        assert LLMService._extract_content(result) == ""

    def test_extract_content_no_choices(self):
        """测试无 choices 字段."""
        result = {}
        assert LLMService._extract_content(result) == ""

    def test_extract_content_malformed(self):
        """测试畸形响应."""
        result = {"choices": [{"message": None}]}
        assert LLMService._extract_content(result) == ""
