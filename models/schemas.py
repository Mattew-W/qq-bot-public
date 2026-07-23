"""Pydantic 数据模型 - API 请求/响应."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# === 通用响应 ===

class Response(BaseModel):
    """通用响应."""

    code: int = 0
    message: str = "ok"
    data: Any = None


class PaginatedResponse(Response):
    """分页响应."""

    total: int = 0
    page: int = 1
    page_size: int = 20


# === 用户模型 ===

class UserOut(BaseModel):
    """用户输出."""

    id: int
    qq_id: str
    nickname: str | None
    group_id: str | None
    role: str
    warning_count: int
    created_at: datetime


# === 警告记录 ===

class WarningOut(BaseModel):
    """警告记录输出."""

    id: int
    user_id: int
    group_id: str
    reason: str
    risk_score: int
    created_at: datetime


# === 垃圾消息记录 ===

class SpamRecordOut(BaseModel):
    """垃圾消息记录输出."""

    id: int
    user_id: int
    group_id: str
    message: str
    risk_score: int
    action_taken: str
    rule_matched: str | None
    llm_confirmed: bool | None
    created_at: datetime


# === LLM 使用记录 ===

class LLMUsageOut(BaseModel):
    """LLM 使用记录输出."""

    id: int
    user_id: str | None
    group_id: str | None
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    success: bool
    error_message: str | None
    created_at: datetime


# === 对话历史 ===

class ConversationOut(BaseModel):
    """对话历史输出."""

    id: int
    user_id: int
    group_id: str | None
    role: str
    content: str
    created_at: datetime


# === 统计模型 ===

class DashboardStats(BaseModel):
    """仪表盘统计."""

    total_users: int
    total_groups: int
    total_warnings: int
    total_spam_blocked: int
    total_llm_calls: int
    total_tokens_used: int
    avg_latency_ms: float


class DailyStats(BaseModel):
    """每日统计."""

    date: str
    spam_count: int
    llm_calls: int
    tokens_used: int


# === 知识库管理 ===

class KnowledgeInfo(BaseModel):
    """知识库信息."""

    file_name: str
    file_hash: str
    chunk_count: int
    created_at: datetime


class KnowledgeReloadResponse(BaseModel):
    """知识库重载响应."""

    success: bool
    message: str
    chunk_count: int = 0
