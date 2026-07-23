"""Pydantic Settings - 统一配置管理.

所有配置从 .env 文件读取，不允许硬编码。
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用级统一配置."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # === 机器人基础配置 ===
    BOT_APP_ID: str = ""
    BOT_SECRET: str = ""
    BOT_TOKEN: str = ""
    # 机器人在群里的显示名（@xxx 触发用）。留空则自动从 QQ 接口获取。
    # 当 NapCat 以纯文本 '@昵称' 上报 @（无 CQ 码）时必须能匹配到此名。
    BOT_NICKNAME: str = ""

    # === OneBot 适配器配置 ===
    ONEBOT_WS_URL: str = "ws://127.0.0.1:8080"
    ONEBOT_ACCESS_TOKEN: str = ""

    # === LongCat LLM 配置 ===
    LONGCAT_API_BASE: str = "https://api.longcat.ai/v1"
    LONGCAT_API_KEY: str = ""
    LONGCAT_MODEL: str = "longcat-chat"
    LONGCAT_TEMPERATURE: float = 0.7
    LONGCAT_MAX_TOKENS: int = 2048

    # === 数据库配置 ===
    DATABASE_URL: str = "sqlite:///./data/qqbot.db"

    # === 日志配置 ===
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "./logs"
    LOG_RETENTION: int = 30

    # === 知识库配置 ===
    KNOWLEDGE_DIR: str = "./data/knowledge"
    KNOWLEDGE_CHUNK_SIZE: int = 500
    KNOWLEDGE_CHUNK_OVERLAP: int = 50

    # === 反垃圾配置 ===
    ANTISPAM_RULES_DIR: str = "./data/rules"
    ANTISPAM_THRESHOLD_LLM: int = 40
    ANTISPAM_THRESHOLD_WITHDRAW: int = 50
    ANTISPAM_THRESHOLD_BAN: int = 70
    ANTISPAM_THRESHOLD_KICK: int = 90
    # 是否跳过管理员/群主消息不做反垃圾检查。生产环境建议 True；想自己拿管理员号测试撤回可设 False。
    ANTISPAM_SKIP_ADMIN: bool = True

    # === 美团分析配置 ===
    MEITUAN_DATA_DIR: str = "./data/meituan"

    # === 调试模式 ===
    DEBUG: bool = False

    @field_validator("LONGCAT_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """验证温度参数."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature 必须在 0.0 ~ 2.0 之间")
        return v

    @field_validator("LONGCAT_MAX_TOKENS")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """验证最大 token 数."""
        if v <= 0 or v > 128000:
            raise ValueError("max_tokens 必须在 1 ~ 128000 之间")
        return v


@lru_cache
def get_settings() -> Settings:
    """获取全局唯一配置实例 (单例模式)."""
    return Settings()
