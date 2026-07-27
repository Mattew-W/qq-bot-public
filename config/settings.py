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
    # 机器人在群里的显示名（@xxx 触发用）。留空则自动从 OneBot 接口获取。
    BOT_NICKNAME: str = ""

    # === OneBot 适配器配置 ===
    ONEBOT_WS_URL: str = "ws://127.0.0.1:8080"
    ONEBOT_ACCESS_TOKEN: str = ""

    # === LLM 配置 ===
    LLM_API_BASE: str = "https://api.openai.com/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048

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
    # 是否跳过管理员/群主消息不做反垃圾检查。
    ANTISPAM_SKIP_ADMIN: bool = True
    # 用户短窗口消息聚合（C 方案：复合消息合并检测）。
    # 同用户在 N 秒内连发的多条消息（text/video/image/file）合并成一段文本
    # 走规则引擎，解决"纯视频/文档不携带话术、但同批文字含伪装话术"导致的漏检。
    # 默认 30 秒；设 0 关闭聚合（每条消息独立检测，回退到旧行为）。
    ANTISPAM_AGGREGATE_WINDOW: int = 30

    # === 数据分析配置 ===
    DATA_ANALYSIS_DIR: str = "./data/analysis"

    # === 调试模式 ===
    DEBUG: bool = False

    @field_validator("LLM_TEMPERATURE")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """验证温度参数."""
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature 必须在 0.0 ~ 2.0 之间")
        return v

    @field_validator("LLM_MAX_TOKENS")
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
