"""最近消息 ID 追踪 - 用于垃圾账号批量撤回.

每条群消息进来时调用 record() 记下 (群, 用户, message_id)，
当某账号被判为 withdraw/ban/kick 时，get_recent_ids() 返回该账号
最近一段时间内发过的所有 message_id（文字/图片/视频/卡片均含 message_id），
交给 action_service 一次性 delete_msg 批量撤回。

只存内存，重启即丢（够用：QQ 撤回只对最近约 2 分钟内的消息有效，
超时的 delete_msg 会被 NapCat 拒绝并由 action_service 静默捕获）。
"""

from __future__ import annotations

import time
from collections import defaultdict
from threading import Lock

from core.logger import get_logger

logger = get_logger("antispam.tracker")

# 默认追踪窗口：QQ 群撤回上限约 2 分钟，留 5 分钟余量，超时由 API 侧拒绝
_DEFAULT_WINDOW = 300
# 每个用户最多保留多少条（防刷屏爆内存）
_DEFAULT_MAX = 30


class MessageTracker:
    """按 (group_id, user_id) 追踪最近的 message_id。"""

    def __init__(
        self,
        window_seconds: int = _DEFAULT_WINDOW,
        max_per_user: int = _DEFAULT_MAX,
    ) -> None:
        self._window = window_seconds
        self._max = max_per_user
        self._lock = Lock()
        # (group_id, user_id) -> [(message_id, ts, msg_type)]
        self._data: dict[tuple[str, str], list[tuple[str, float, str]]] = defaultdict(list)

    def record(
        self,
        group_id: str,
        user_id: str,
        message_id: str,
        msg_type: str = "text",
    ) -> None:
        """记录一条消息 ID。"""
        if not message_id:
            return
        key = (group_id, user_id)
        now = time.time()
        cutoff = now - self._window
        with self._lock:
            buf = self._data[key]
            buf.append((message_id, now, msg_type))
            # 裁剪：丢弃窗口外的，并限制条数
            self._data[key] = [
                (mid, ts, t) for (mid, ts, t) in buf if ts >= cutoff
            ][-self._max:]

    def get_recent_ids(
        self,
        group_id: str,
        user_id: str,
        within_seconds: int | None = None,
    ) -> list[str]:
        """返回该用户在窗口内的所有 message_id（按时间升序，可能含当前消息）。"""
        key = (group_id, user_id)
        now = time.time()
        cutoff = now - (within_seconds if within_seconds is not None else self._window)
        with self._lock:
            buf = self._data.get(key, [])
            return [mid for (mid, ts, _t) in buf if ts >= cutoff]

    def clear(self, group_id: str, user_id: str) -> None:
        """清空某用户在某群的记录（撤回完成后可选调用）。"""
        with self._lock:
            self._data.pop((group_id, user_id), None)


_tracker: MessageTracker | None = None


def get_message_tracker() -> MessageTracker:
    """获取全局 MessageTracker 单例。"""
    global _tracker
    if _tracker is None:
        _tracker = MessageTracker()
    return _tracker
