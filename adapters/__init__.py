"""适配器模块 - 第三方接口封装."""

from adapters.llm_adapter import LLMAdapter, get_llm_adapter

__all__ = ["LLMAdapter", "get_llm_adapter"]
