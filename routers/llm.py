"""LLM 管理路由."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select, desc

from database.base import get_session
from database.models import LLMUsage
from models.schemas import LLMUsageOut, PaginatedResponse, Response

router = APIRouter()


@router.get("/usage", response_model=PaginatedResponse)
async def list_llm_usage(page: int = 1, page_size: int = 20):
    """获取 LLM 使用记录.

    Args:
        page: 页码.
        page_size: 每页大小.
    """
    offset = (page - 1) * page_size

    async with get_session() as session:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(LLMUsage)
        total = (await session.execute(stmt)).scalar_one()

        stmt = select(LLMUsage).order_by(desc(LLMUsage.created_at)).offset(offset).limit(page_size)
        result = await session.execute(stmt)
        records = result.scalars().all()

    data = [
        LLMUsageOut(
            id=r.id,
            user_id=r.user_id,
            group_id=r.group_id,
            model=r.model,
            prompt_tokens=r.prompt_tokens,
            completion_tokens=r.completion_tokens,
            total_tokens=r.total_tokens,
            latency_ms=r.latency_ms,
            success=r.success,
            error_message=r.error_message,
            created_at=r.created_at,
        )
        for r in records
    ]

    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)


@router.get("/stats", response_model=Response)
async def get_llm_stats():
    """获取 LLM 统计."""
    async with get_session() as session:
        from sqlalchemy import func

        # 总调用次数
        stmt = select(func.count()).select_from(LLMUsage)
        total_calls = (await session.execute(stmt)).scalar_one()

        # 总 token
        stmt = select(func.sum(LLMUsage.total_tokens)).select_from(LLMUsage)
        total_tokens = (await session.execute(stmt)).scalar_one() or 0

        # 平均延迟
        stmt = select(func.avg(LLMUsage.latency_ms)).select_from(LLMUsage)
        avg_latency = (await session.execute(stmt)).scalar_one() or 0.0

        # 成功率
        stmt = select(func.count()).select_from(LLMUsage).where(LLMUsage.success.is_(True))
        success_count = (await session.execute(stmt)).scalar_one()
        success_rate = (success_count / total_calls * 100) if total_calls > 0 else 0

    return Response(data={
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "avg_latency_ms": round(avg_latency, 2),
        "success_rate": round(success_rate, 2),
    })
