"""NoneBot2 机器人入口.

运行方式：python bot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保项目根目录在 sys.path 中
ROOT_DIR = str(Path(__file__).parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import nonebot
from nonebot.adapters.onebot.v11 import Adapter as OneBotAdapter
from nonebot.drivers.fastapi import Driver as FastAPIDriver

from config import get_settings
from core.logger import get_logger, setup_logging
from database.base import init_db, close_db


def main() -> None:
    """启动机器人."""
    settings = get_settings()
    setup_logging(settings)

    logger = get_logger("bot")
    logger.info("正在启动 NoneBot2 机器人...")

    # 初始化 NoneBot
    nonebot.init(
        _env_file=".env",
        log_level=settings.LOG_LEVEL,
    )

    # 注册 OneBot v11 适配器
    driver = nonebot.get_driver()
    driver.register_adapter(OneBotAdapter)

    # 数据库初始化/关闭 hook
    @driver.on_startup
    async def _init_db():
        await init_db()

    @driver.on_shutdown
    async def _close_db():
        await close_db()

    # 加载 apscheduler 插件
    try:
        nonebot.load_plugin("nonebot_plugin_apscheduler")
    except Exception as e:
        logger.warning(f"加载 apscheduler 失败: {e}")

    # 加载项目插件
    plugins_dir = Path(__file__).parent / "plugins"
    nonebot.load_plugins(str(plugins_dir))

    # 挂载 FastAPI 管理后台到 NoneBot2 的 ASGI app
    if isinstance(driver, FastAPIDriver):
        _mount_admin_app(driver)

    logger.info("机器人启动成功！正在运行...")
    nonebot.run()


def _mount_admin_app(driver: FastAPIDriver) -> None:
    """将管理后台 API 挂载到 NoneBot2 的 FastAPI 实例."""
    from fastapi.staticfiles import StaticFiles

    from routers import api_router

    server_app = driver.server_app

    # 注册 API 路由
    server_app.include_router(api_router, prefix="/api")

    # 挂载静态文件
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        server_app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # 配置 UI 入口
    from fastapi.responses import FileResponse, JSONResponse

    @server_app.get("/")
    async def config_ui():
        """配置 UI."""
        index_file = static_dir / "config" / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse({"message": "配置 UI 文件不存在"})

    @server_app.get("/health")
    async def health():
        """健康检查."""
        return JSONResponse({"status": "ok", "service": "qq-bot"})

    get_logger("bot").info("FastAPI 管理后台已挂载到 /api, 配置 UI 在 /")


if __name__ == "__main__":
    main()
