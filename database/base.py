"""数据库引擎和会话管理."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from config import get_settings
from core.logger import get_logger

logger = get_logger("database")


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类."""
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """获取数据库引擎 (单例)."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.DATABASE_URL
        # 确保 SQLite 使用 aiosqlite
        if db_url.startswith("sqlite:///"):
            db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        _engine = create_async_engine(
            db_url,
            echo=settings.DEBUG,
            pool_pre_ping=True,
        )
        # 脱敏日志
        safe_url = db_url
        if "@" in db_url and "://" in db_url:
            # 非 SQLite URL 可能含密码，脱敏
            import re
            safe_url = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", db_url)
        logger.info(f"数据库引擎已创建: {safe_url}")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂 (单例)."""
    global _session_factory
    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def init_db() -> None:
    """初始化数据库 - 创建所有表."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表初始化完成")


async def close_db() -> None:
    """关闭数据库连接."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("数据库连接已关闭")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的异步上下文管理器.

    Yields:
        AsyncSession 实例.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
