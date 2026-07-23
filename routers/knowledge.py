"""知识库管理路由."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from core.logger import get_logger
from database.base import get_session
from database.models import KnowledgeVersion
from models.schemas import KnowledgeReloadResponse, Response
from services import get_knowledge_service

logger = get_logger("api.knowledge")
router = APIRouter()


@router.get("/info", response_model=Response)
async def get_knowledge_info():
    """获取知识库信息."""
    service = get_knowledge_service()
    return Response(data={
        "loaded": service.is_loaded,
        "size": service.size,
    })


@router.get("/versions", response_model=Response)
async def get_versions():
    """获取知识库版本历史."""
    async with get_session() as session:
        from sqlalchemy import select, desc
        stmt = select(KnowledgeVersion).order_by(desc(KnowledgeVersion.created_at)).limit(20)
        result = await session.execute(stmt)
        versions = result.scalars().all()

    return Response(data=[
        {
            "version": v.version,
            "file_name": v.file_name,
            "file_hash": v.file_hash,
            "chunk_count": v.chunk_count,
            "created_at": v.created_at.isoformat(),
        }
        for v in versions
    ])


@router.post("/reload", response_model=Response)
async def reload_knowledge():
    """重新加载知识库."""
    try:
        service = get_knowledge_service()
        await service.reload()
        return Response(data=KnowledgeReloadResponse(
            success=True,
            message="知识库重载成功",
            chunk_count=service.size,
        ))
    except Exception as e:
        logger.error(f"知识库重载失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"重载失败: {e}"},
        )
