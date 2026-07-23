"""反垃圾管理路由."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select, desc

from database.base import get_session
from database.models import SpamRecord, WarningRecord
from models.schemas import (
    PaginatedResponse,
    Response,
    SpamRecordOut,
    WarningOut,
)

router = APIRouter()


@router.get("/records", response_model=PaginatedResponse)
async def list_spam_records(page: int = 1, page_size: int = 20):
    """获取垃圾消息记录.

    Args:
        page: 页码.
        page_size: 每页大小.
    """
    offset = (page - 1) * page_size

    async with get_session() as session:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(SpamRecord)
        total = (await session.execute(stmt)).scalar_one()

        stmt = select(SpamRecord).order_by(desc(SpamRecord.created_at)).offset(offset).limit(page_size)
        result = await session.execute(stmt)
        records = result.scalars().all()

    data = [
        SpamRecordOut(
            id=r.id,
            user_id=r.user_id,
            group_id=r.group_id,
            message=r.message,
            risk_score=r.risk_score,
            action_taken=r.action_taken,
            rule_matched=r.rule_matched,
            llm_confirmed=r.llm_confirmed,
            created_at=r.created_at,
        )
        for r in records
    ]

    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)


@router.get("/warnings", response_model=PaginatedResponse)
async def list_warnings(page: int = 1, page_size: int = 20):
    """获取警告记录.

    Args:
        page: 页码.
        page_size: 每页大小.
    """
    offset = (page - 1) * page_size

    async with get_session() as session:
        from sqlalchemy import func
        stmt = select(func.count()).select_from(WarningRecord)
        total = (await session.execute(stmt)).scalar_one()

        stmt = select(WarningRecord).order_by(desc(WarningRecord.created_at)).offset(offset).limit(page_size)
        result = await session.execute(stmt)
        warnings = result.scalars().all()

    data = [
        WarningOut(
            id=w.id,
            user_id=w.user_id,
            group_id=w.group_id,
            reason=w.reason,
            risk_score=w.risk_score,
            created_at=w.created_at,
        )
        for w in warnings
    ]

    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)
