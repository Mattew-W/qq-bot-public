"""API 路由模块."""

from fastapi import APIRouter

from . import dashboard, knowledge, users, anti_spam, llm, config

api_router = APIRouter()

api_router.include_router(dashboard.router, prefix="/dashboard", tags=["仪表盘"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
api_router.include_router(users.router, prefix="/users", tags=["用户"])
api_router.include_router(anti_spam.router, prefix="/antispam", tags=["反垃圾"])
api_router.include_router(llm.router, prefix="/llm", tags=["LLM"])
api_router.include_router(config.router, prefix="/config", tags=["配置"])
