"""通用装饰器 - 重试、计时、限流."""

from __future__ import annotations

import asyncio
import functools
import time
from collections import defaultdict
from typing import Any, Callable, TypeVar

from tenacity import (
    retry as tenacity_retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.logger import get_logger

logger = get_logger("utils")

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    wait_min: float = 1.0,
    wait_max: float = 10.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """异步重试装饰器.

    Args:
        max_attempts: 最大重试次数.
        wait_min: 最小等待时间 (秒).
        wait_max: 最大等待时间 (秒).
        exceptions: 触发重试的异常类型.

    Returns:
        装饰器.
    """

    def decorator(func: F) -> F:
        @tenacity_retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_min, max=wait_max),
            retry=retry_if_exception_type(exceptions),
            before_sleep=lambda retry_state: logger.warning(
                f"{func.__name__} 重试第 {retry_state.attempt_number} 次"
            ),
        )
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


def timing(func: F) -> F:
    """计时装饰器 - 记录函数执行时间."""

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger.info(f"{func.__name__} 耗时 {elapsed:.2f}ms")

    return wrapper  # type: ignore


class RateLimiter:
    """基于滑动窗口的异步限流器."""

    def __init__(self, rate: int, period: float = 60.0) -> None:
        """
        Args:
            rate: 周期内允许的最大请求数.
            period: 周期长度 (秒).
        """
        self.rate = rate
        self.period = period
        self._timestamps: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> bool:
        """获取限流许可.

        Args:
            key: 限流键 (如用户ID、群ID).

        Returns:
            是否允许通过.
        """
        async with self._lock:
            now = time.monotonic()
            timestamps = self._timestamps[key]

            # 清理过期时间戳
            cutoff = now - self.period
            self._timestamps[key] = [t for t in timestamps if t > cutoff]

            if len(self._timestamps[key]) >= self.rate:
                return False

            self._timestamps[key].append(now)
            return True

    async def __aenter__(self) -> bool:
        return await self.acquire("default")

    async def __aexit__(self, *args: Any) -> None:
        pass


def rate_limit(rate: int, period: float = 60.0, key_func: Callable[..., str] | None = None) -> Callable[[F], F]:
    """限流装饰器.

    Args:
        rate: 周期内允许的最大请求数.
        period: 周期长度 (秒).
        key_func: 提取限流键的函数.

    Returns:
        装饰器.
    """
    limiter = RateLimiter(rate, period)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = "default"
            if key_func is not None:
                key = key_func(*args, **kwargs)

            if not await limiter.acquire(key):
                logger.warning(f"触发限流: {func.__name__} key={key}")
                raise RuntimeError("请求过于频繁，请稍后再试")

            return await func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator
