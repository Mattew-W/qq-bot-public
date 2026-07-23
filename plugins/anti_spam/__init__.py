"""反垃圾插件.

监听群消息，执行反垃圾检查。
采用规则引擎 + 风险评分 + LLM 二次确认的三层架构。
"""

from __future__ import annotations

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.params import EventPlainText

from config import get_settings
from core.logger import get_logger
from services import get_action_service, get_anti_spam_service
from utils.helpers import clean_text

logger = get_logger("plugin.antispam")

# 响应器 - 监听所有群消息 (低优先级)
antispam_checker = on_message(priority=1, block=False)

# 服务
anti_spam_service = get_anti_spam_service()
action_service = get_action_service()


async def _ocr_images(bot: Bot, event: GroupMessageEvent) -> str:
    """对消息里的图片做 OCR，返回识别到的文字。失败/不支持返回空。"""
    texts: list[str] = []
    for seg in event.message:
        if seg.type != "image":
            continue
        file_id = seg.data.get("file") or seg.data.get("file_id") or ""
        if not file_id:
            continue
        try:
            res = await bot.call_api("ocr_image", image_id=file_id)
            items = (res or {}).get("texts") or (res or {}).get("data") or []
            for it in items:
                t = it.get("text") if isinstance(it, dict) else str(it)
                if t:
                    texts.append(t)
        except Exception as e:
            logger.debug(f"图片 OCR 失败: {e}")
    return " ".join(texts)


@antispam_checker.handle()
async def check_message(
    bot: Bot,
    event: GroupMessageEvent,
    text: str = EventPlainText(),
) -> None:
    """检查群消息是否为垃圾信息."""
    message_text = clean_text(text or "")
    has_image = any(seg.type == "image" for seg in event.message)
    if not message_text and not has_image:
        return

    # 跳过管理员/群主消息
    if get_settings().ANTISPAM_SKIP_ADMIN and event.sender.role in ("admin", "owner"):
        logger.info(f"反垃圾：跳过管理员/群主消息 user={event.user_id} role={event.sender.role}")
        return

    user_id = str(event.user_id)
    group_id = str(event.group_id)
    message_id = str(event.message_id)

    combined = message_text
    if has_image:
        ocr_text = await _ocr_images(bot, event)
        if ocr_text:
            combined = (message_text + "\n" + ocr_text).strip() if message_text else ocr_text
            logger.info(f"反垃圾：图片 OCR 识别 user={user_id} text={ocr_text[:60]}")

    result = await anti_spam_service.check(
        message=combined,
        user_id=user_id,
        group_id=group_id,
        message_id=message_id,
        has_image=has_image,
    )

    risk_score = result["risk_score"]
    action = result["action"]
    rule_hits = result["rule_hits"]
    withdraw_ids = result.get("withdraw_ids", [])

    if risk_score < 10:
        return

    reason = "; ".join(r["reason"] for r in rule_hits) if rule_hits else "无规则命中"
    rule_names = ", ".join(r["rule_name"] for r in rule_hits) if rule_hits else None

    result = await action_service.execute(
        action=action,
        user_id=user_id,
        group_id=group_id,
        message_id=message_id,
        reason=reason,
        bot=bot,
        risk_score=risk_score,
        rule_matched=rule_names,
        original_message=message_text,
        extra_message_ids=withdraw_ids,
    )

    if action in ("withdraw", "ban", "kick"):
        withdrawn = result.get("withdrawn_count", 0)
        logger.info(f"反垃圾：{action}，已尝试撤回 {withdrawn} 条消息 user={user_id} group={group_id}")

    if action == "log":
        logger.spam(f"低风险消息记录: {user_id}@{group_id} score={risk_score}")
        return

    if action in ("ban", "kick"):
        logger.warning(
            f"⚠️ 高风险动作: {action} user={user_id} group={group_id} "
            f"score={risk_score} reason={reason}"
        )
