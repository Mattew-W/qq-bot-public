"""反垃圾自定义规则 · 参考示例（非默认加载）.

本文件收录了某个真实部署中使用的「场景化自定义规则」，**仅作参考**。
它们不会被 `get_default_rules()` 默认加载；如需启用，请复制你需要的规则类到
自己的规则模块，并通过以下任一种方式注册：

    from services.anti_spam.rules import get_default_rules, RuleResult, SpamRule
    from services.anti_spam.rules_reference import CampusWallRule, ClickAvatarRule

    # 方式 A: 直接扩展默认规则集
    def my_rules():
        return [*get_default_rules(), CampusWallRule(), ClickAvatarRule()]

    # 方式 B: 运行时动态添加
    service = get_anti_spam_service()
    service.add_rule(CampusWallRule())
    service.add_rule(ClickAvatarRule())

⚠️ 上下文字段依赖：下列规则用到 `has_media` / `is_new_user` / `is_pure_media` /
`has_image` / `message_id` 等字段，需你的 bot 插件在调用 `anti_spam_service.check`
时通过 `**context` 传入（可参考真实部署的 `plugins/anti_spam/__init__.py`）。
缺省时这些字段取 `False`/空，规则会表现得「更保守」，不会误触发。

⚠️ 二维码解码规则（`QRContentRule`）未收入本参考文件：它依赖可选模块
`qr_decode.py`（基于 opencv 本地解码），属于可选增强。若需要，自行在部署中
启用 `ANTISPAM_QR_DECODE_ENABLED` 并安装 `opencv-python-headless` 即可。

铁律（务必遵守）：撤回的唯一硬触发应是「解码出二维码内容」，无二维码的纯媒体
消息不应被自动撤回 —— 只踢人，媒体由人工/管理员后续清理。对应地，纯媒体引流
规则应设 `chain_delete=False`。
"""

from __future__ import annotations

import re
from typing import Any

from .rules import RuleResult, SpamRule


class CampusWallRule(SpamRule):
    """伪校园墙/新生墙广告识别 - 专门对付"装作官方校园墙"的新型引流.

    特征: 自称"校园墙/新生墙/墙墙", 用"免费领取新生资料"吸引扫码加好友,
    列举一堆学校话题(学生会/转专业/社团纳新/宿舍)伪装权威,
    末尾附二维码图/资料文件 + "@全体成员"催促.

    与 GroupInviteRule 互补:
    - GroupInviteRule 监"加群/扫码"等通用关键词
    - CampusWallRule 监"校园墙/新生须知/免费领取"等校园场景特有话术
    """

    # 高风险关键词(单独命中即告警)
    HIGH_KEYWORDS = [
        "校园墙", "新生墙", "墙墙", "墙主", "墙君",
        "大一新生须知", "新生须知", "新生资料", "新生群",
    ]
    # 中风险关键词(需配合其他信号)
    MID_KEYWORDS = [
        "免费领取", "免费领", "微信扫码", "扫码添加",
        "别错过", "抓紧加", "务必全部", "全部加上",
        "今日必", "今天必", "都看下",
    ]
    # 学校话题(用于识别伪装权威的长文案)
    SCHOOL_TOPICS = [
        "学生会", "转专业", "社团纳新", "入团入党", "竞选班委",
        "宿舍安排", "军训", "录取通知书", "奖助学金", "学籍",
        "入党", "转团", "专业调剂",
    ]

    def __init__(self, score: int = 70) -> None:
        super().__init__("campus_wall", score)

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        msg_id = str(context.get("message_id", ""))
        has_image = bool(context.get("has_image", False))
        at_all = (
            "@全体成员" in message
            or "[CQ:at,qq=all]" in message
            or "[CQ:at,qq=anonymous]" in message
        )

        has_high = sum(1 for kw in self.HIGH_KEYWORDS if kw in message)
        has_mid = sum(1 for kw in self.MID_KEYWORDS if kw in message)
        has_topics = sum(1 for kw in self.SCHOOL_TOPICS if kw in message)

        # 情形 A: 命中高风险关键词(校园墙/新生须知/墙墙...)
        if has_high >= 1:
            boost = 0
            if has_mid >= 1:
                boost += 15  # 配合"免费领取/扫码添加"等引流话术
            if has_topics >= 2:
                boost += 10  # 列举多个学校话题 = 伪装权威
            if at_all:
                boost += 10  # @全体成员 = 强引导
            if has_image:
                boost += 15  # 配图(可能二维码)
            reason = f"伪校园墙: 命中高风险词×{has_high}"
            if has_mid:
                reason += f"+引流信号×{has_mid}"
            if has_topics:
                reason += f"+学校话题×{has_topics}"
            return RuleResult(
                rule_name=self.name,
                hit=True,
                reason=reason,
                # 单规则封顶 90: 叠加信号不应把总分推到远超阈值量纲之外
                score=min(self.score + boost, 90),
                withdraw_ids=[msg_id] if msg_id else [],
            )

        # 情形 B: @全体成员 + 多个引流关键词(无校园墙词也触发)
        if at_all and has_mid >= 2:
            return RuleResult(
                rule_name=self.name,
                hit=True,
                reason=f"@全体成员+引流信号×{has_mid}",
                score=50,  # 中高分, 走撤回或AI确认
                withdraw_ids=[msg_id] if msg_id else [],
            )

        # 情形 C: 多个学校话题 + 引流关键词(伪装学校通知的引流)
        if has_topics >= 3 and has_mid >= 1:
            return RuleResult(
                rule_name=self.name,
                hit=True,
                reason=f"伪装学校话题×{has_topics}+引流×{has_mid}",
                score=45,  # 中分, 走AI确认
                withdraw_ids=[msg_id] if msg_id else [],
            )

        return RuleResult(rule_name=self.name, hit=False)


class MediaSpamRule(SpamRule):
    """纯媒体引流信号 - 新账号发送无任何文字/卡片/解码内容的图片或视频.

    ⚠️ 已降级：本规则**不再单独触发撤回**（曾导致"新账号发个表情包就被撤"误伤）。
    按"识别到二维码才撤，否则不撤"铁律：撤回的唯一硬触发由二维码解码规则
    （解出二维码内容）决定；本规则仅作弱信号/日志记录，供观察与多信号叠加参考。

    仅对"新账号"生效（老成员发梗图不命中）；命中分数为 0，不影响最终 action。
    """

    def __init__(self, score: int = 0) -> None:
        super().__init__("media_spam", score)

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        is_pure_media = context.get("is_pure_media", False)
        is_new_user = context.get("is_new_user", False)
        if not is_pure_media or not is_new_user:
            return RuleResult(rule_name=self.name, hit=False)
        # 分数固定为 0：只记录"新账号发纯媒体"这一可疑信号，不触发撤回
        return RuleResult(
            rule_name=self.name,
            hit=True,
            reason="新账号发送纯图片/视频(无文字/无二维码内容，仅记录不撤回)",
            score=self.score,
        )


class ClickAvatarRule(SpamRule):
    """'点我头像/戳我头像' + 媒体/新账号 引流话术.

    典型诈骗开场: 发视频/图片 + '点我头像' 引导私聊(色情/赌博/刷单等)。
    '点我头像' 这类话术在日常聊天里几乎只出现在引流场景, 但为降低误伤,
    要求命中话术 **且** (消息含媒体 或 发送者是新账号) 才判垃圾。

    ⚠️ 不触发连带撤回(chain_delete=False): 按铁律'识别到二维码才撤',
    这类纯媒体消息不应被自动撤回 —— 只踢人, 媒体由人工/管理员后续清理。
    """

    PATTERNS = [
        r"点我头像",
        r"戳我头像",
        r"点击头像",
        r"点头像",
        r"点下头像",
        r"看我头像",
    ]

    def __init__(self, score: int = 90) -> None:
        super().__init__("click_avatar", score)
        self._pats = [re.compile(p) for p in self.PATTERNS]

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检查'点我头像'引流话术."""
        if not any(p.search(message) for p in self._pats):
            return RuleResult(rule_name=self.name, hit=False)

        has_media = bool(context.get("has_media", False))
        is_new_user = bool(context.get("is_new_user", False))
        # 纯文本说"点我头像"(无媒体、老账号)大概率是正常聊天, 不判垃圾
        if not (has_media or is_new_user):
            return RuleResult(rule_name=self.name, hit=False)

        return RuleResult(
            rule_name=self.name,
            hit=True,
            reason="点我头像引流话术+媒体/新账号",
            score=self.score,
            chain_delete=False,  # 铁律: 不自动撤无二维码的媒体
        )
