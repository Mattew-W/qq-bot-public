"""配置管理路由."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse

from config import get_settings
from core.logger import get_logger

logger = get_logger("api.config")
router = APIRouter()

# 允许写入 .env 的键白名单
_ALLOWED_KEYS = {
    "BOT_APP_ID", "BOT_SECRET", "BOT_TOKEN",
    "ONEBOT_WS_URL", "ONEBOT_ACCESS_TOKEN",
    "LLM_API_BASE", "LLM_API_KEY", "LLM_MODEL",
    "LLM_TEMPERATURE", "LLM_MAX_TOKENS",
    "DATABASE_URL", "LOG_LEVEL", "LOG_DIR", "LOG_RETENTION",
    "KNOWLEDGE_DIR", "KNOWLEDGE_CHUNK_SIZE", "KNOWLEDGE_CHUNK_OVERLAP",
    "ANTISPAM_RULES_DIR", "ANTISPAM_THRESHOLD_LLM",
    "ANTISPAM_THRESHOLD_BAN", "ANTISPAM_THRESHOLD_KICK",
    "DATA_ANALYSIS_DIR", "DEBUG",
}


def _mask(value: str) -> str:
    """脱敏处理."""
    if not value:
        return ""
    return "********"


def _sanitize(value: str) -> str:
    """清洗值 - 防止 .env 注入."""
    # 移除换行符和回车符
    value = str(value).replace("\n", "").replace("\r", "")
    # 移除其他控制字符
    value = re.sub(r"[\x00-\x1f\x7f]", "", value)
    return value


async def _check_auth(x_admin_token: str | None = Header(None)) -> bool:
    """简易鉴权 - 通过 Header 中的 admin token."""
    if x_admin_token is None:
        return True  # 开发阶段允许无鉴权访问
    return True


@router.get("")
async def get_config():
    """获取当前配置."""
    settings = get_settings()
    data = {
        "BOT_APP_ID": settings.BOT_APP_ID,
        "BOT_SECRET": _mask(settings.BOT_SECRET),
        "BOT_TOKEN": _mask(settings.BOT_TOKEN),
        "ONEBOT_WS_URL": settings.ONEBOT_WS_URL,
        "ONEBOT_ACCESS_TOKEN": _mask(settings.ONEBOT_ACCESS_TOKEN),
        "LLM_API_BASE": settings.LLM_API_BASE,
        "LLM_API_KEY": _mask(settings.LLM_API_KEY),
        "LLM_MODEL": settings.LLM_MODEL,
        "LLM_TEMPERATURE": settings.LLM_TEMPERATURE,
        "LLM_MAX_TOKENS": settings.LLM_MAX_TOKENS,
        "DATABASE_URL": _mask(settings.DATABASE_URL) if "://" in settings.DATABASE_URL and "@" in settings.DATABASE_URL else settings.DATABASE_URL,
        "LOG_LEVEL": settings.LOG_LEVEL,
        "LOG_DIR": settings.LOG_DIR,
        "LOG_RETENTION": settings.LOG_RETENTION,
        "KNOWLEDGE_DIR": settings.KNOWLEDGE_DIR,
        "KNOWLEDGE_CHUNK_SIZE": settings.KNOWLEDGE_CHUNK_SIZE,
        "KNOWLEDGE_CHUNK_OVERLAP": settings.KNOWLEDGE_CHUNK_OVERLAP,
        "ANTISPAM_RULES_DIR": settings.ANTISPAM_RULES_DIR,
        "ANTISPAM_THRESHOLD_LLM": settings.ANTISPAM_THRESHOLD_LLM,
        "ANTISPAM_THRESHOLD_BAN": settings.ANTISPAM_THRESHOLD_BAN,
        "ANTISPAM_THRESHOLD_KICK": settings.ANTISPAM_THRESHOLD_KICK,
        "DATA_ANALYSIS_DIR": settings.DATA_ANALYSIS_DIR,
        "DEBUG": settings.DEBUG,
    }
    return JSONResponse({"code": 0, "message": "ok", "data": data})


@router.put("")
async def update_config(request: dict):
    """更新配置.

    Args:
        request: 配置字典.
    """
    try:
        # 使用项目根目录的绝对路径
        project_root = Path(__file__).parent.parent
        env_path = project_root / ".env"
        env_lines = []

        if env_path.exists():
            env_lines = env_path.read_text(encoding="utf-8").splitlines()

        # 过滤白名单 + 清洗值
        safe_request = {}
        for key, value in request.items():
            if key not in _ALLOWED_KEYS:
                logger.warning(f"拒绝写入非白名单配置项: {key}")
                continue
            if isinstance(value, bool):
                value = str(value).lower()
            safe_request[key] = _sanitize(str(value))

        existing_keys = set()
        new_lines = []

        for line in env_lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                new_lines.append(line)
                continue

            if "=" not in stripped:
                new_lines.append(line)
                continue

            key = stripped.split("=", 1)[0].strip()
            existing_keys.add(key)

            if key in safe_request:
                new_lines.append(f"{key}={safe_request[key]}")
            else:
                new_lines.append(line)

        # 添加新字段
        for key, value in safe_request.items():
            if key not in existing_keys:
                new_lines.append(f"{key}={value}")

        env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

        logger.info("配置已更新")
        return JSONResponse({"code": 0, "message": "配置已更新，请重启服务生效"})

    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        return JSONResponse(
            status_code=500,
            content={"code": 500, "message": f"更新失败: {e}"},
        )
