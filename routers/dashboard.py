"""仪表盘路由."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from database.base import get_session
from database.models import (
    ConversationHistory,
    LLMUsage,
    SpamRecord,
    User,
    WarningRecord,
)
from models.schemas import DashboardStats, DailyStats, Response

router = APIRouter()


@router.get("/stats", response_model=Response)
async def get_stats():
    """获取仪表盘统计."""
    async with get_session() as session:
        # 总用户数
        stmt = select(func.count()).select_from(User)
        total_users = (await session.execute(stmt)).scalar_one()

        # 总警告数
        stmt = select(func.count()).select_from(WarningRecord)
        total_warnings = (await session.execute(stmt)).scalar_one()

        # 总垃圾消息拦截数
        stmt = select(func.count()).select_from(SpamRecord)
        total_spam = (await session.execute(stmt)).scalar_one()

        # LLM 调用统计
        stmt = select(func.count()).select_from(LLMUsage)
        total_llm = (await session.execute(stmt)).scalar_one()

        stmt = select(func.sum(LLMUsage.total_tokens)).select_from(LLMUsage)
        total_tokens = (await session.execute(stmt)).scalar_one() or 0

        stmt = select(func.avg(LLMUsage.latency_ms)).select_from(LLMUsage)
        avg_latency = (await session.execute(stmt)).scalar_one() or 0.0

        # 总群数 (去重)
        stmt = select(func.count(func.distinct(User.group_id))).select_from(User)
        total_groups = (await session.execute(stmt)).scalar_one()

    data = DashboardStats(
        total_users=total_users,
        total_groups=total_groups,
        total_warnings=total_warnings,
        total_spam_blocked=total_spam,
        total_llm_calls=total_llm,
        total_tokens_used=total_tokens,
        avg_latency_ms=round(avg_latency, 2),
    )

    return Response(data=data)


@router.get("/daily", response_model=Response)
async def get_daily_stats(days: int = Query(default=7, ge=1, le=90)):
    """获取每日统计.

    Args:
        days: 天数.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    result = []

    async with get_session() as session:
        # 每日垃圾消息数
        for i in range(days):
            day_start = cutoff + timedelta(days=i)
            day_end = day_start + timedelta(days=1)

            stmt = (
                select(func.count())
                .select_from(SpamRecord)
                .where(SpamRecord.created_at >= day_start, SpamRecord.created_at < day_end)
            )
            spam_count = (await session.execute(stmt)).scalar_one()

            stmt = (
                select(func.count())
                .select_from(LLMUsage)
                .where(LLMUsage.created_at >= day_start, LLMUsage.created_at < day_end)
            )
            llm_calls = (await session.execute(stmt)).scalar_one()

            stmt = (
                select(func.sum(LLMUsage.total_tokens))
                .select_from(LLMUsage)
                .where(LLMUsage.created_at >= day_start, LLMUsage.created_at < day_end)
            )
            tokens = (await session.execute(stmt)).scalar_one() or 0

            result.append(
                DailyStats(
                    date=day_start.strftime("%Y-%m-%d"),
                    spam_count=spam_count,
                    llm_calls=llm_calls,
                    tokens_used=tokens,
                )
            )

    return Response(data=result)
