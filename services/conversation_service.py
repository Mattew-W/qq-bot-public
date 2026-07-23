"""对话历史服务 - 管理用户与机器人的对话上下文."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select

from config import get_settings
from core.logger import get_logger
from database.base import get_session
from database.models import ConversationHistory, User

logger = get_logger("service.conversation")


class ConversationService:
    """对话历史服务.

    管理对话上下文，支持滑动窗口。
    """

    def __init__(self, max_history: int = 10, ttl_hours: int = 2) -> None:
        self._max_history = max_history
        self._ttl = timedelta(hours=ttl_hours)

    async def add_message(
        self,
        user_id: str,
        group_id: str,
        role: str,
        content: str,
    ) -> None:
        """添加对话记录.

        Args:
            user_id: 用户 QQ 号.
            group_id: 群 ID.
            role: 角色 (user/assistant/system).
            content: 内容.
        """
        try:
            async with get_session() as session:
                # 获取或创建用户
                stmt = select(User).where(User.qq_id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user is None:
                    user = User(qq_id=user_id, group_id=group_id)
                    session.add(user)
                    await session.flush()

                record = ConversationHistory(
                    user_id=user.id,
                    group_id=group_id,
                    role=role,
                    content=content,
                )
                session.add(record)

        except Exception as e:
            logger.warning(f"对话记录写入失败: {e}")

    async def get_history(
        self,
        user_id: str,
        group_id: str,
    ) -> list[dict[str, str]]:
        """获取用户对话历史.

        Args:
            user_id: 用户 QQ 号.
            group_id: 群 ID.

        Returns:
            消息列表.
        """
        try:
            async with get_session() as session:
                # 获取用户
                stmt = select(User).where(User.qq_id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user is None:
                    return []

                # 查询最近的历史
                cutoff = datetime.now(timezone.utc) - self._ttl
                stmt = (
                    select(ConversationHistory)
                    .where(
                        ConversationHistory.user_id == user.id,
                        ConversationHistory.group_id == group_id,
                        ConversationHistory.created_at > cutoff,
                    )
                    .order_by(ConversationHistory.created_at.desc())
                    .limit(self._max_history)
                )
                result = await session.execute(stmt)
                records = result.scalars().all()

                # 反转顺序 (从旧到新)
                return [
                    {"role": r.role, "content": r.content}
                    for r in reversed(records)
                ]

        except Exception as e:
            logger.warning(f"获取对话历史失败: {e}")
            return []

    async def clear_history(self, user_id: str, group_id: str) -> int:
        """清除用户对话历史.

        Args:
            user_id: 用户 QQ 号.
            group_id: 群 ID.

        Returns:
            删除的记录数.
        """
        try:
            async with get_session() as session:
                stmt = select(User).where(User.qq_id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user is None:
                    return 0

                stmt = (
                    delete(ConversationHistory)
                    .where(
                        ConversationHistory.user_id == user.id,
                        ConversationHistory.group_id == group_id,
                    )
                )
                result = await session.execute(stmt)
                return result.rowcount or 0

        except Exception as e:
            logger.warning(f"清除对话历史失败: {e}")
            return 0


_conversation_service: ConversationService | None = None


def get_conversation_service() -> ConversationService:
    """获取对话历史服务实例."""
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service
