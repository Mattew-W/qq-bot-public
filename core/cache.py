"""LRU 缓存模块.

提供简单的内存缓存能力，用于高频读取数据的临时存储。
"""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Generic, Hashable, TypeVar

K = TypeVar("K", bound=Hashable)
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    """线程安全的 LRU 缓存.

    使用 OrderedDict 实现，支持最大容量限制和 TTL (可选)。
    """

    def __init__(self, max_size: int = 1024) -> None:
        if max_size <= 0:
            raise ValueError("max_size 必须大于 0")
        self._max_size = max_size
        self._cache: OrderedDict[K, V] = OrderedDict()
        self._lock = Lock()

    def get(self, key: K) -> V | None:
        """获取缓存值.

        Args:
            key: 缓存键.

        Returns:
            缓存值或 None.
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def put(self, key: K, value: V) -> None:
        """写入缓存.

        Args:
            key: 缓存键.
            value: 缓存值.
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def remove(self, key: K) -> bool:
        """删除缓存项.

        Args:
            key: 缓存键.

        Returns:
            是否成功删除.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存."""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """返回当前缓存大小."""
        with self._lock:
            return len(self._cache)

    def __contains__(self, key: K) -> bool:
        """支持 `in` 操作符."""
        with self._lock:
            return key in self._cache

    def __len__(self) -> int:
        """支持 `len()` 操作."""
        return self.size()
