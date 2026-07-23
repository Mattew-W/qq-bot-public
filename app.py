"""应用入口 - FastAPI 应用实例.

提供后台管理接口、配置 UI 和健康检查。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from config import get_settings
from core.logger import get_logger, setup_logging
from database.base import close_db, init_db
from routers import api_router

logger = get_logger("app")

# 静态文件目录
STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    settings = get_settings()
    setup_logging(settings)
    await init_db()
    logger.info("应用启动完成")
    yield
    await close_db()
    logger.info("应用已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用实例.

    Returns:
        FastAPI 实例.
    """
    app = FastAPI(
        title="AI 管家 QQ 机器人",
        description="基于 NoneBot2 + OneBot v11 + LongCat 2.0 的智能 QQ 群机器人",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 注册 API 路由
    app.include_router(api_router, prefix="/api")

    # 挂载静态文件
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/health")
    async def health_check():
        """健康检查接口."""
        return JSONResponse({"status": "ok", "service": "qq-bot"})

    @app.get("/")
    async def root():
        """根路径 - 返回配置 UI."""
        index_file = STATIC_DIR / "config" / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse({
            "name": "AI 管家 QQ 机器人",
            "version": "0.1.0",
            "docs": "/docs",
            "api": "/api",
            "ui": "/static/config/index.html",
        })

    return app


app = create_app()
