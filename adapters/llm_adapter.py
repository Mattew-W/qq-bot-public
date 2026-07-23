"""LLM API 适配器.

封装 HTTP 调用细节，统一错误处理。
兼容 OpenAI Chat Completions 接口（OpenAI / DeepSeek / Claude / Gemini / 通义千问 / 智谱 / Moonshot 等均可接入）。
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator

import httpx

from config import get_settings
from core.exceptions import LLMException
from core.logger import get_logger
from utils.decorators import retry

logger = get_logger("adapter.llm")


class LLMAdapter:
    """LLM API 适配器.

    封装 HTTP 调用细节，统一错误处理。
    兼容 OpenAI Chat Completions 接口。
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.LLM_API_BASE.rstrip("/")
        self._api_key = settings.LLM_API_KEY
        self._model = settings.LLM_MODEL
        self._timeout = httpx.Timeout(
            connect=10.0,
            read=60.0,
            write=10.0,
            pool=10.0,
        )

    def _get_headers(self) -> dict[str, str]:
        """构造请求头."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _get_url(self) -> str:
        """构造 Chat Completions URL."""
        return f"{self._base_url}/chat/completions"

    @retry(max_attempts=3, wait_min=1.0, wait_max=10.0, exceptions=(httpx.ConnectError, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout))
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """调用 Chat API.

        Args:
            messages: 消息列表.
            temperature: 温度.
            max_tokens: 最大 token 数.
            stream: 是否流式.
            **kwargs: 额外参数.

        Returns:
            API 响应 dict.

        Raises:
            LLMException: API 调用失败时抛出.
        """
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs,
        }

        logger.llm(f"请求: model={self._model} messages={len(messages)} stream={stream}")
        start_time = time.monotonic()

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    self._get_url(),
                    headers=self._get_headers(),
                    json=payload,
                )
                response.raise_for_status()

            elapsed = (time.monotonic() - start_time) * 1000
            result = response.json()

            usage = result.get("usage", {})
            logger.llm(
                f"响应: prompt_tokens={usage.get('prompt_tokens', 0)} "
                f"completion_tokens={usage.get('completion_tokens', 0)} "
                f"latency={elapsed:.0f}ms"
            )

            return result

        except httpx.HTTPStatusError as e:
            elapsed = (time.monotonic() - start_time) * 1000
            error_body = e.response.text if e.response is not None else "unknown"
            logger.error(f"LLM API HTTP 错误: {e.response.status_code if e.response else '?'} body={error_body} latency={elapsed:.0f}ms")
            raise LLMException(
                f"LLM API HTTP {e.response.status_code if e.response else '?'} 错误",
                details={"status_code": e.response.status_code if e.response else None, "body": error_body},
            ) from e
        except httpx.HTTPError as e:
            elapsed = (time.monotonic() - start_time) * 1000
            logger.error(f"LLM API 网络错误: {type(e).__name__}: {e} latency={elapsed:.0f}ms")
            raise LLMException(
                f"LLM API 网络错误: {type(e).__name__}",
                details={"error": str(e)},
            ) from e

    async def stream_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs: Any,
    ) -> AsyncGenerator[str, None]:
        """流式调用 Chat API.

        Args:
            messages: 消息列表.
            temperature: 温度.
            max_tokens: 最大 token 数.
            **kwargs: 额外参数.

        Yields:
            流式内容片段.
        """
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }

        logger.llm(f"流式请求: model={self._model} messages={len(messages)}")

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    self._get_url(),
                    headers=self._get_headers(),
                    json=payload,
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except Exception:
                                continue

        except httpx.HTTPError as e:
            logger.error(f"LLM 流式错误: {type(e).__name__}: {e}")
            raise LLMException(
                f"LLM 流式调用失败: {type(e).__name__}",
                details={"error": str(e)},
            ) from e


_llm_adapter: LLMAdapter | None = None


def get_llm_adapter() -> LLMAdapter:
    """获取 LLM 适配器实例."""
    global _llm_adapter
    if _llm_adapter is None:
        _llm_adapter = LLMAdapter()
    return _llm_adapter
