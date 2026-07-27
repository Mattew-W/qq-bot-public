"""动作执行服务.

根据反垃圾结果执行相应动作：记录日志、撤回消息、禁言、踢人。
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from config import get_settings
from core.exceptions import BotException
from core.logger import get_logger
from database.base import get_session
from database.models import SpamRecord, User, WarningRecord

logger = get_logger("service.action")


class ActionService:
    """动作执行服务.

    根据反垃圾结果执行相应动作。
    """

    # 已尝试撤回的消息ID -> 最近尝试时间戳(单调时钟), 防同一条消息在
    # 连发触发中被反复撤回(雪崩)。冷却期内再次遇到同一条直接跳过。
    _withdraw_dedup: dict[str, float] = {}
    _DEDUP_TTL = 120.0  # 同一条消息 120s 内不再重复发起撤回

    async def execute(
        self,
        action: str,
        user_id: str,
        group_id: str,
        message_id: str,
        reason: str,
        bot: Any = None,
        risk_score: int = 0,
        rule_matched: str | None = None,
        original_message: str = "",
        extra_message_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """执行反垃圾动作.

        Args:
            action: 动作类型 (log/withdraw/ban/kick).
            user_id: 用户 QQ.
            group_id: 群 ID.
            message_id: 消息 ID.
            reason: 原因.
            bot: NoneBot Bot 实例 (需要调用 OneBot API).
            extra_message_ids: 需要一并撤回的其它消息 ID（如连发重复的第一条）.

        Returns:
            执行结果.
        """
        result: dict[str, Any] = {
            "action": action,
            "success": True,
            "message": "",
        }

        try:
            if action == "log":
                result["message"] = "已记录日志"
                await self._record_spam(user_id, group_id, reason, action, risk_score, rule_matched, original_message)

            elif action == "withdraw":
                result["message"] = "已撤回消息"
                await self._record_spam(user_id, group_id, reason, action, risk_score, rule_matched, original_message)
                if bot:
                    await self._withdraw_extra(bot, group_id, message_id, extra_message_ids, result)

            elif action == "ban":
                result["message"] = "已禁言用户"
                await self._record_spam(user_id, group_id, reason, action, risk_score, rule_matched, original_message)
                await self._add_warning(user_id, group_id, reason)
                if bot:
                    await self._withdraw_extra(bot, group_id, message_id, extra_message_ids, result)
                    await self._ban_user(bot, group_id, user_id)

            elif action == "kick":
                result["message"] = "已踢出用户"
                await self._record_spam(user_id, group_id, reason, action, risk_score, rule_matched, original_message)
                await self._add_warning(user_id, group_id, reason)
                if bot:
                    await self._withdraw_extra(bot, group_id, message_id, extra_message_ids, result)
                    await self._kick_user(bot, group_id, user_id)

            else:
                result["success"] = False
                result["message"] = f"未知动作: {action}"

            logger.action(f"执行动作: {action} user={user_id} group={group_id} reason={reason}")

        except Exception as e:
            result["success"] = False
            result["message"] = str(e)
            logger.error(f"执行动作失败: {action} error={e}")

        return result

    async def _record_spam(
        self,
        user_id: str,
        group_id: str,
        reason: str,
        action: str,
        risk_score: int = 0,
        rule_matched: str | None = None,
        original_message: str = "",
    ) -> None:
        """记录垃圾消息到数据库."""
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

                record = SpamRecord(
                    user_id=user.id,
                    group_id=group_id,
                    message=original_message or reason,
                    risk_score=risk_score,
                    action_taken=action,
                    rule_matched=rule_matched,
                )
                session.add(record)
        except Exception as e:
            logger.warning(f"垃圾消息记录失败: {e}")

    async def _add_warning(
        self,
        user_id: str,
        group_id: str,
        reason: str,
    ) -> None:
        """添加警告记录."""
        try:
            async with get_session() as session:
                stmt = select(User).where(User.qq_id == user_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user is None:
                    user = User(qq_id=user_id, group_id=group_id)
                    session.add(user)
                    await session.flush()

                user.warning_count += 1

                warning = WarningRecord(
                    user_id=user.id,
                    group_id=group_id,
                    reason=reason,
                )
                session.add(warning)
        except Exception as e:
            logger.warning(f"警告记录失败: {e}")

    async def _withdraw_message(self, bot: Any, group_id: str, message_id: str) -> bool:
        """撤回消息.

        Args:
            bot: Bot 实例.
            group_id: 群 ID.
            message_id: 消息 ID.

        Returns:
            是否成功撤回。NapCat 偶发 retcode=1200 超时但 QQ 内核实际已撤回
            (EventRet.result=0) 时判定为成功(假失败), 避免误报失败。
        """
        try:
            await bot.call_api(
                "delete_msg",
                message_id=int(message_id),
            )
            return True
        except Exception as e:
            # 识别"假失败": NapCat 偶发超时(retcode=1200)但 QQ 内核实际已处理
            retcode = getattr(e, "retcode", None)
            data = getattr(e, "data", None) or {}
            result_code = data.get("result") if isinstance(data, dict) else None
            if retcode == 1200 and result_code == 0:
                logger.info(
                    f"撤回消息 {message_id} 实际已成功(假失败 retcode=1200 result=0)"
                )
                return True
            logger.warning(f"撤回消息 {message_id} 失败: {e}")
            return False

    async def _withdraw_extra(
        self,
        bot: Any,
        group_id: str,
        message_id: str,
        extra_message_ids: list[str] | None,
        result: dict[str, Any],
    ) -> None:
        """撤回当前消息 + 所有 extra 消息。

        去重(防连发触发雪崩) + 每条间限流(降 QQ 侧召回超时概率) + 假失败识别,
        并把撤回/失败/跳过计数写入 result。
        """
        all_ids = list(dict.fromkeys([message_id, *(extra_message_ids or [])]))
        now = time.monotonic()
        withdrawn = 0
        failed = 0
        skipped = 0
        for mid in all_ids:
            # 去重: 冷却期内已尝试过 → 跳过, 不重复发起撤回(防雪崩)
            if mid in self._withdraw_dedup and (now - self._withdraw_dedup[mid]) < self._DEDUP_TTL:
                skipped += 1
                continue
            self._withdraw_dedup[mid] = now
            if await self._withdraw_message(bot, group_id, mid):
                withdrawn += 1
            else:
                failed += 1
            # 每条之间限流, 降低 QQ 侧召回超时概率
            await asyncio.sleep(0.3)
        # 定期清理过期条目, 避免字典无限增长
        if len(self._withdraw_dedup) > 1000:
            self._withdraw_dedup = {
                k: v for k, v in self._withdraw_dedup.items() if now - v < self._DEDUP_TTL
            }
        result["withdrawn_count"] = withdrawn
        result["withdraw_failed_count"] = failed
        result["withdraw_skipped_count"] = skipped

    async def _ban_user(
        self,
        bot: Any,
        group_id: str,
        user_id: str,
        duration: int = 300,
    ) -> None:
        """禁言用户.

        Args:
            bot: Bot 实例.
            group_id: 群 ID.
            user_id: 用户 ID.
            duration: 禁言时长 (秒).
        """
        try:
            await bot.call_api(
                "set_group_ban",
                group_id=int(group_id),
                user_id=int(user_id),
                duration=duration,
            )
        except Exception as e:
            logger.warning(f"禁言失败: {e}")

    async def _kick_user(self, bot: Any, group_id: str, user_id: str) -> None:
        """踢出用户.

        Args:
            bot: Bot 实例.
            group_id: 群 ID.
            user_id: 用户 ID.
        """
        try:
            await bot.call_api(
                "set_group_kick",
                group_id=int(group_id),
                user_id=int(user_id),
            )
        except Exception as e:
            logger.warning(f"踢人失败: {e}")


_action_service: ActionService | None = None


def get_action_service() -> ActionService:
    """获取动作执行服务实例."""
    global _action_service
    if _action_service is None:
        _action_service = ActionService()
    return _action_service
