"""LLM 服务 - 统一封装所有大模型调用.

支持所有兼容 OpenAI Chat Completions 接口的模型服务：
- OpenAI (GPT-4o / GPT-4o-mini / o1 等)
- DeepSeek
- Claude (via Anthropic-compatible API)
- Google Gemini
- 通义千问 (Qwen)
- 智谱 GLM
- Moonshot
- 任何兼容 OpenAI 格式的自部署模型

业务代码只依赖 LLMService，不直接接触具体模型 API。
"""

from __future__ import annotations

import time
from typing import Any, AsyncGenerator

from adapters.llm_adapter import LLMAdapter, get_llm_adapter
from config import get_settings
from core.exceptions import LLMException
from core.logger import get_logger
from database.base import get_session
from database.models import LLMUsage

logger = get_logger("service.llm")


class LLMService:
    """大语言模型服务.

    封装所有 LLM 调用，支持多模型切换。
    """

    def __init__(self, adapter: LLMAdapter | None = None) -> None:
        self._adapter = adapter or get_llm_adapter()
        self._settings = get_settings()

    async def ask(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        user_id: str | None = None,
        group_id: str | None = None,
    ) -> str:
        """发送消息并获取回复.

        Args:
            messages: 消息列表.
            temperature: 温度 (None 则使用配置默认值).
            max_tokens: 最大 token 数 (None 则使用配置默认值).
            stream: 是否流式.
            user_id: 用户 ID (用于记录).
            group_id: 群 ID (用于记录).

        Returns:
            模型回复文本.

        Raises:
            LLMException: 调用失败时抛出.
        """
        temp = temperature if temperature is not None else self._settings.LLM_TEMPERATURE
        tokens = max_tokens if max_tokens is not None else self._settings.LLM_MAX_TOKENS

        start_time = time.monotonic()
        success = True
        error_msg = None
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        try:
            if stream:
                # 流式调用：收集所有片段
                chunks = []
                async for chunk in self._adapter.stream_chat(
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                ):
                    chunks.append(chunk)
                reply = "".join(chunks)
            else:
                # 非流式调用
                result = await self._adapter.chat(
                    messages=messages,
                    temperature=temp,
                    max_tokens=tokens,
                    stream=False,
                )
                reply = self._extract_content(result)
                usage = result.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

            return reply

        except LLMException:
            success = False
            error_msg = "LLM 调用失败"
            raise
        except Exception as e:
            success = False
            error_msg = str(e)
            logger.error(f"LLM 调用异常: {type(e).__name__}: {e}")
            raise LLMException(f"LLM 调用失败: {type(e).__name__}", details={"error": str(e)}) from e
        finally:
            # 记录调用日志
            elapsed = (time.monotonic() - start_time) * 1000
            await self._record_usage(
                user_id=user_id,
                group_id=group_id,
                model=self._settings.LLM_MODEL,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=elapsed,
                success=success,
                error_message=error_msg,
            )

    async def stream(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式获取回复.

        Args:
            messages: 消息列表.
            temperature: 温度.
            max_tokens: 最大 token 数.

        Yields:
            回复内容片段.
        """
        temp = temperature if temperature is not None else self._settings.LLM_TEMPERATURE
        tokens = max_tokens if max_tokens is not None else self._settings.LLM_MAX_TOKENS

        async for chunk in self._adapter.stream_chat(
            messages=messages,
            temperature=temp,
            max_tokens=tokens,
        ):
            yield chunk

    async def _record_usage(
        self,
        user_id: str | None,
        group_id: str | None,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        latency_ms: float,
        success: bool,
        error_message: str | None,
    ) -> None:
        """记录 LLM 调用到数据库.

        Args:
            user_id: 用户 ID.
            group_id: 群 ID.
            model: 模型名称.
            prompt_tokens: 输入 token 数.
            completion_tokens: 输出 token 数.
            total_tokens: 总 token 数.
            latency_ms: 延迟 (毫秒).
            success: 是否成功.
            error_message: 错误信息.
        """
        try:
            async with get_session() as session:
                record = LLMUsage(
                    user_id=user_id,
                    group_id=group_id,
                    model=model,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    success=success,
                    error_message=error_message,
                )
                session.add(record)
        except Exception as e:
            # 记录失败不影响主流程
            logger.warning(f"LLM 使用记录写入失败: {e}")

    @staticmethod
    def _extract_content(result: dict[str, Any]) -> str:
        """从 API 响应中提取文本内容.

        Args:
            result: API 响应 dict.

        Returns:
            提取的文本.
        """
        try:
            choices = result.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content", "")
            return ""
        except (IndexError, AttributeError, TypeError) as e:
            logger.error(f"解析 LLM 响应失败: {e}, result={result}")
            return ""


_llm_service: LLMService | None = None


def get_llm_service() -> LLMService:
    """获取 LLM 服务实例."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
