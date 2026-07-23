"""用户管理路由."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select, desc

from database.base import get_session
from database.models import User
from models.schemas import PaginatedResponse, Response, UserOut

router = APIRouter()


@router.get("", response_model=PaginatedResponse)
async def list_users(page: int = 1, page_size: int = 20):
    """获取用户列表.

    Args:
        page: 页码.
        page_size: 每页大小.
    """
    offset = (page - 1) * page_size

    async with get_session() as session:
        # 总数
        from sqlalchemy import func
        stmt = select(func.count()).select_from(User)
        total = (await session.execute(stmt)).scalar_one()

        # 分页
        stmt = select(User).order_by(desc(User.created_at)).offset(offset).limit(page_size)
        result = await session.execute(stmt)
        users = result.scalars().all()

    data = [
        UserOut(
            id=u.id,
            qq_id=u.qq_id,
            nickname=u.nickname,
            group_id=u.group_id,
            role=u.role,
            warning_count=u.warning_count,
            created_at=u.created_at,
        )
        for u in users
    ]

    return PaginatedResponse(data=data, total=total, page=page, page_size=page_size)


@router.get("/{user_id}", response_model=Response)
async def get_user(user_id: int):
    """获取用户详情.

    Args:
        user_id: 用户 ID.
    """
    async with get_session() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if user is None:
        return Response(code=404, message="用户不存在")

    return Response(data=UserOut(
        id=user.id,
        qq_id=user.qq_id,
        nickname=user.nickname,
        group_id=user.group_id,
        role=user.role,
        warning_count=user.warning_count,
        created_at=user.created_at,
    ))
