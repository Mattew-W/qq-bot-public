"""AI 问答插件.

监听 @bot 消息，调用 Knowledge + LLM 生成回复。
"""

from __future__ import annotations

from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    Event,
    GroupMessageEvent,
    Message,
)
from nonebot.params import CommandArg
from nonebot.rule import Rule

try:
    from nonebot_plugin_apscheduler import scheduler
    _HAS_SCHEDULER = True
except ImportError:
    scheduler = None
    _HAS_SCHEDULER = False

from config import get_settings
from core.logger import get_logger
from services import (
    get_conversation_service,
    get_knowledge_service,
    get_llm_service,
)
from services.prompt_builder import build_ai_qa_prompt

logger = get_logger("plugin.ai_qa")

# 创建 AI 服务实例
llm_service = get_llm_service()
knowledge_service = get_knowledge_service()
conv_service = get_conversation_service()


# === 规则：只有 @机器人 时才匹配 ===
# 缓存机器人在各群的候选显示名，避免每条消息都查 API
_bot_name_cache: dict[str, list[str]] = {}


async def _get_bot_names(bot: Bot, group_id: str, self_id: str) -> list[str]:
    """获取机器人在群里的候选显示名（用于纯文本 '@昵称' 形式的 @ 检测）。"""
    cache_key = f"{group_id}:{self_id}"
    if cache_key in _bot_name_cache:
        return _bot_name_cache[cache_key]

    names: list[str] = []
    # 1) 优先用配置文件里的昵称
    try:
        env_name = get_settings().BOT_NICKNAME.strip()
        if env_name:
            names.append(env_name)
    except Exception:
        pass
    # 2) 从 QQ 接口获取群名片 / 昵称
    try:
        info = await bot.get_group_member_info(group_id=int(group_id), user_id=int(self_id))
        card = (info.get("card") or "").strip()
        nick = (info.get("nickname") or "").strip()
        for n in (card, nick):
            if n and n not in names:
                names.append(n)
    except Exception:
        pass

    if names:
        _bot_name_cache[cache_key] = names
    return names


async def is_at_me(bot: Bot, event: Event) -> bool:
    """检查事件是否 @ 了机器人.

    兼容三种 NapCat 上报格式：
    1) 解析后的消息段含 at 段
    2) 原始消息含 CQ 码 [CQ:at,qq=...] / [at:qq=...]
    3) 纯文本 '@昵称 ...'（NapCat 文本模式，无 CQ 码，如改名后）
    """
    if not isinstance(event, GroupMessageEvent):
        return False

    self_id = str(bot.self_id)

    # 方式1：解析后的消息段里有 at
    for seg in event.message:
        if seg.type == "at" and str(seg.data.get("qq")) == self_id:
            return True

    # 方式2：原始消息字符串里包含 @机器人 的 CQ 码
    raw = getattr(event, "raw_message", "")
    if f"[CQ:at,qq={self_id}]" in raw or f"[at:qq={self_id}]" in raw:
        return True

    # 方式3：NapCat 以纯文本 '@昵称' 上报 @（无 CQ 码）
    text = event.message.extract_plain_text().lstrip()
    if text.startswith("@"):
        for name in await _get_bot_names(bot, str(event.group_id), self_id):
            if name and text.startswith(f"@{name}"):
                return True

    return False


# === 事件响应器 ===
# 方式1: @机器人 直接对话
ai_chat = on_message(rule=Rule(is_at_me), priority=5, block=False)

# 方式2: 显式命令
ai_ask = on_command("ask", priority=5, block=False)
ai_clear = on_command("clear", priority=5, block=False)


# === 定时任务：每天凌晨3点自动重新加载知识库 ===
async def _reload_knowledge() -> None:
    """每天凌晨3点自动重新加载知识库."""
    logger.info("定时任务: 重新加载知识库")
    try:
        await knowledge_service.reload()
        logger.info("知识库重新加载完成")
    except Exception as e:
        logger.error(f"知识库重新加载失败: {e}")

if _HAS_SCHEDULER:
    scheduler.add_job(_reload_knowledge, "cron", hour=3, minute=0, id="reload_knowledge")


@ai_chat.handle()
async def handle_ai_chat(bot: Bot, event: GroupMessageEvent) -> None:
    """处理群聊中 @bot 的消息."""
    # 提取纯文本
    text = _extract_text(event.message).strip()
    if not text:
        return

    logger.info(f"AI 问答 [{event.user_id}@{event.group_id}]: {text[:50]}")

    # 调用 RAG 处理
    reply = await _process_qa(
        question=text,
        user_id=str(event.user_id),
        group_id=str(event.group_id),
    )

    if reply:
        await ai_chat.send(reply)


@ai_ask.handle()
async def handle_ask(event: GroupMessageEvent, args: Message = CommandArg()) -> None:
    """处理 /ask 命令."""
    text = args.extract_plain_text().strip()
    if not text:
        await ai_ask.send("请输入问题，例如: /ask 什么是 Python？")
        return

    reply = await _process_qa(
        question=text,
        user_id=str(event.user_id),
        group_id=str(event.group_id),
    )

    if reply:
        await ai_ask.send(reply)


@ai_clear.handle()
async def handle_clear(event: GroupMessageEvent) -> None:
    """处理 /clear 命令 - 清除对话历史."""
    count = await conv_service.clear_history(
        user_id=str(event.user_id),
        group_id=str(event.group_id),
    )
    await ai_clear.send(f"已清除 {count} 条对话历史。")


async def _process_qa(
    question: str,
    user_id: str,
    group_id: str,
) -> str:
    """RAG 处理流程.

    Args:
        question: 用户问题.
        user_id: 用户 QQ.
        group_id: 群 ID.

    Returns:
        回复文本.
    """
    try:
        # 1. 获取对话历史
        history = await conv_service.get_history(user_id, group_id)

        # 2. 知识库搜索
        knowledge_results = await knowledge_service.search(question, top_k=3)
        knowledge_texts = [r["content"] for r in knowledge_results]

        # 3. 构造 Prompt
        messages = build_ai_qa_prompt(
            question=question,
            knowledge=knowledge_texts if knowledge_texts else None,
            history=history[-6:] if history else None,
        )

        # 4. 调用 LLM
        reply = await llm_service.ask(
            messages=messages,
            user_id=user_id,
            group_id=group_id,
            max_tokens=256,
        )

        # 5. 记录对话
        await conv_service.add_message(user_id, group_id, "user", question)
        await conv_service.add_message(user_id, group_id, "assistant", reply)

        return reply

    except Exception as e:
        logger.error(f"处理问答失败: {e}")
        return "抱歉，处理您的请求时出错了，请稍后再试。"


def _extract_text(message: Message) -> str:
    """从消息中提取纯文本，跳过 @ 部分.

    Args:
        message: 消息对象.

    Returns:
        纯文本.
    """
    parts: list[str] = []
    for seg in message:
        if seg.type == "text":
            parts.append(seg.data.get("text", ""))
    return " ".join(parts).strip()
