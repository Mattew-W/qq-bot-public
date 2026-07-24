"""反垃圾插件.

监听群消息，执行反垃圾检查。
采用规则引擎 + 风险评分 + LLM 二次确认的三层架构。
"""

from __future__ import annotations

import json as _json
import re as _re

from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, GroupMessageEvent
from nonebot.params import EventPlainText

from config import get_settings
from core.logger import get_logger
from services import get_action_service, get_anti_spam_service
from services.anti_spam.message_tracker import get_message_tracker
from utils.helpers import clean_text

logger = get_logger("plugin.antispam")

# 响应器 - 监听所有群消息 (低优先级)
antispam_checker = on_message(priority=1, block=False)

# 服务
anti_spam_service = get_anti_spam_service()
action_service = get_action_service()


def _msg_type(event: GroupMessageEvent) -> str:
    """粗略归类消息类型，仅用于追踪日志。"""
    types = {seg.type for seg in event.message}
    if "shortvideo" in types or "video" in types:
        return "video"
    if "image" in types:
        return "image"
    if "json" in types or "xml" in types:
        return "card"
    return "text"


async def _ocr_images(bot: Bot, event: GroupMessageEvent) -> str:
    """对消息里的图片做 OCR（NapCat ocr_image），返回识别到的文字。失败/不支持返回空。"""
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


async def _extract_card_signals(event: GroupMessageEvent, group_id: str) -> tuple[str, str]:
    """从卡片消息（xml/json）提取反垃圾检测信号。

    QQ 群邀请卡片在 OneBot v11 里是 ``json`` 类型消息段，结构示例::

        {"app":"com.tencent.contact.lua",
         "prompt":"群名片: 26新生事宜通知6群",
         "meta":{"contact":{"uin":<群号>,"from":1,...}}}

    纯文本为空，只用 EventPlainText 会完全漏检。这里做两件事：
    1) 把卡片原始 JSON 也送进规则引擎（让已有规则能扫到里面的号码/链接）；
    2) 结构化解析出目标群号 ``meta.contact.uin``，若 ≠ 当前群则注入
       ``群号:<外部群号>`` 信号，复用 GroupInviteRule(score=90) 直接踢+撤回。

    返回 (检测文本, 调试信息)。
    """
    detection: list[str] = []
    debug: list[str] = []
    for seg in event.message:
        if seg.type not in ("json", "xml", "markdown"):
            continue
        # 取卡片原文：OneBot 里 json 段 data 通常是 {"data": "<json字符串>"}
        raw = seg.data.get("data") if isinstance(seg.data, dict) else seg.data
        if not raw and isinstance(seg.data, dict) and "data" not in seg.data:
            raw = _json.dumps(seg.data, ensure_ascii=False)
        if not raw:
            continue
        raw_str = _json.dumps(raw, ensure_ascii=False) if isinstance(raw, dict) else str(raw)

        # 原始 JSON 一并送检测
        detection.append(raw_str)

        # 结构化解析，找目标群号
        try:
            obj = _json.loads(raw_str) if isinstance(raw_str, str) else raw_str
        except Exception:
            obj = None
        uin = None
        if isinstance(obj, dict):
            app = obj.get("app", "")
            prompt = obj.get("prompt", "")
            contact = (obj.get("meta") or {}).get("contact") or {}
            uin = contact.get("uin")
            frm = contact.get("from")
            debug.append(f"app={app} prompt={prompt[:30]} uin={uin} from={frm}")
            # 是否为“群”名片：from==1 或 prompt 含“群”
            is_group = (frm == 1) or ("群" in prompt)
            if uin and str(uin) != str(group_id) and is_group:
                # 注入“群号:<外部群号>”→ GroupInviteRule 命中 score=90 直接踢
                detection.append(f"群号:{uin}")
                debug.append("=> 注入外部群邀请信号(高优先级踢)")
        else:
            debug.append("parse_failed")

    return "\n".join(detection), " | ".join(debug)


@antispam_checker.handle()
async def check_message(
    bot: Bot,
    event: GroupMessageEvent,
    text: str = EventPlainText(),
) -> None:
    """检查群消息是否为垃圾信息."""
    message_text = clean_text(text or "")
    has_image = any(seg.type == "image" for seg in event.message)
    # 提取卡片消息（群邀请/分享等 xml/json 卡片，纯文本为空）信号
    group_id_raw = str(event.group_id)
    card_text, card_debug = await _extract_card_signals(event, group_id_raw)
    # 纯空消息（无文字、无图片、无卡片）不处理
    if not message_text and not has_image and not card_text:
        return

    # 跳过管理员/群主消息（可由 ANTISPAM_SKIP_ADMIN 关闭，用于拿管理员号自测撤回）
    if get_settings().ANTISPAM_SKIP_ADMIN and event.sender.role in ("admin", "owner"):
        logger.info(f"反垃圾：跳过管理员/群主消息 user={event.user_id} role={event.sender.role}")
        return

    user_id = str(event.user_id)
    group_id = str(event.group_id)
    message_id = str(event.message_id)

    # 追踪该用户本群的 message_id（含图片/视频/卡片），供判定垃圾后批量撤回
    get_message_tracker().record(group_id, user_id, message_id, _msg_type(event))

    # 组合检测文本：纯文本 + 卡片原文/信号 + 图片 OCR
    combined = message_text
    if card_text:
        combined = (combined + "\n" + card_text).strip() if combined else card_text
        logger.info(f"反垃圾：提取到卡片内容 user={user_id} card={card_text[:200]}")
        if card_debug:
            logger.info(f"反垃圾：卡片结构解析 user={user_id} {card_debug}")
    if has_image:
        ocr_text = await _ocr_images(bot, event)
        if ocr_text:
            combined = (combined + "\n" + ocr_text).strip() if combined else ocr_text
            logger.info(f"反垃圾：图片 OCR 识别 user={user_id} text={ocr_text[:60]}")

    # 执行反垃圾检查（传入 message_id 供重复规则追踪，has_image 供群邀请规则判断）
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

    # 如果风险分太低，不处理
    if risk_score < 10:
        return

    # 记录垃圾消息
    reason = "; ".join(r["reason"] for r in rule_hits) if rule_hits else "无规则命中"
    rule_names = ", ".join(r["rule_name"] for r in rule_hits) if rule_hits else None

    # 判定为撤回/禁言/踢人时：把该账号最近发过的所有消息 ID 一并撤回
    # （文字/图片/视频/卡片都含 message_id，实现"整账号清场"）
    if action in ("withdraw", "ban", "kick"):
        recent_ids = get_message_tracker().get_recent_ids(group_id, user_id)
        for mid in recent_ids:
            if mid not in withdraw_ids:
                withdraw_ids.append(mid)

    # 执行动作
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

    # 撤回动作给出可见反馈，便于确认机器人是否真的“反应”了
    if action in ("withdraw", "ban", "kick"):
        withdrawn = result.get("withdrawn_count", 0)
        logger.info(f"反垃圾：{action}，已尝试撤回 {withdrawn} 条消息 user={user_id} group={group_id}")

    # 如果动作是 log，只记录不通知
    if action == "log":
        logger.spam(f"低风险消息记录: {user_id}@{group_id} score={risk_score}")
        return

    # 高风险动作通知管理员
    if action in ("ban", "kick"):
        # TODO: 发送管理员通知
        logger.warning(
            f"⚠️ 高风险动作: {action} user={user_id} group={group_id} "
            f"score={risk_score} reason={reason}"
        )
