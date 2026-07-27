"""反垃圾规则引擎.

每条规则返回：是否命中、原因、风险分。
支持动态加载规则，无需修改代码即可扩展。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from core.logger import get_logger
from utils.helpers import extract_phone_numbers, extract_qq_numbers, extract_urls

logger = get_logger("antispam.rules")


@dataclass
class RuleResult:
    """规则命中结果."""

    rule_name: str
    hit: bool
    reason: str = ""
    score: int = 0
    metadata: dict = field(default_factory=dict)
    withdraw_ids: list[str] = field(default_factory=list)
    # 是否允许"连带撤回"(把该规则声索的 withdraw_ids 纳入统一撤回)。
    # 默认 True。纯媒体引流规则(如 click_avatar)设 False: 按铁律
    # "识别到二维码才撤", 这类无二维码的图/视频不应被自动撤回, 只踢人。
    chain_delete: bool = True


class SpamRule:
    """反垃圾规则基类."""

    def __init__(self, name: str, score: int, description: str = "") -> None:
        self.name = name
        self.score = score
        self.description = description

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检查消息.

        Args:
            message: 消息内容.
            context: 上下文信息.

        Returns:
            规则命中结果.
        """
        raise NotImplementedError


class KeywordRule(SpamRule):
    """关键词规则 - 匹配广告词、敏感词."""

    def __init__(self, name: str, score: int, keywords: list[str]) -> None:
        super().__init__(name, score)
        self.keywords = [kw.lower() for kw in keywords]

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检查关键词."""
        msg_lower = message.lower()
        for kw in self.keywords:
            if kw in msg_lower:
                return RuleResult(
                    rule_name=self.name,
                    hit=True,
                    reason=f"命中关键词: {kw}",
                    score=self.score,
                    metadata={"keyword": kw},
                )
        return RuleResult(rule_name=self.name, hit=False)


class RegexRule(SpamRule):
    """正则规则 - 匹配微信号、手机号等."""

    def __init__(self, name: str, score: int, pattern: str, flags: int = 0) -> None:
        super().__init__(name, score)
        self.pattern = re.compile(pattern, flags)

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检查正则匹配."""
        match = self.pattern.search(message)
        if match:
            return RuleResult(
                rule_name=self.name,
                hit=True,
                reason=f"匹配模式: {match.group()[:20]}...",
                score=self.score,
                metadata={"matched": match.group()[:50]},
            )
        return RuleResult(rule_name=self.name, hit=False)


class UrlRule(SpamRule):
    """URL 规则 - 检测链接."""

    def __init__(self, score: int = 20) -> None:
        super().__init__("url_detector", score)

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检测 URL."""
        urls = extract_urls(message)
        if urls:
            return RuleResult(
                rule_name=self.name,
                hit=True,
                reason=f"检测到 {len(urls)} 个链接",
                score=self.score,
                metadata={"urls": urls[:5]},
            )
        return RuleResult(rule_name=self.name, hit=False)


class ContactRule(SpamRule):
    """联系方式规则 - 检测手机号、QQ号."""

    def __init__(self, score: int = 35) -> None:
        super().__init__("contact_detector", score)

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检测联系方式."""
        phones = extract_phone_numbers(message)
        if phones:
            return RuleResult(
                rule_name=self.name,
                hit=True,
                reason=f"检测到手机号: {phones[0]}",
                score=self.score,
                metadata={"phones": phones},
            )

        # 检测独立 QQ 号（排除群号）
        qq_numbers = extract_qq_numbers(message)
        group_id = context.get("group_id", "")
        # 过滤掉当前群号
        other_qqs = [q for q in qq_numbers if q != group_id]
        if other_qqs:
            return RuleResult(
                rule_name=self.name,
                hit=True,
                reason=f"检测到外部 QQ 号: {other_qqs[0]}",
                score=self.score,
                metadata={"qq_numbers": other_qqs},
            )

        return RuleResult(rule_name=self.name, hit=False)


class RepeatRule(SpamRule):
    """重复/刷屏消息规则 - 检测连发重复或拉群广告，撤回所有相关消息."""

    MAX_TRACKED_USERS = 500
    # 拉人加其他 QQ 群 / 引流的关键词
    INVITE_KEYWORDS = [
        "加群", "拉群", "进群", "qq群", "QQ群", "q群", "加我群",
        "群号", "微信群", "创群", "扫码进群", "扫码加群", "拉你进群",
        "邀请进群", "互拉群", "兼职群", "薅羊毛群",
        # 校园墙 / 拉人话术特征
        "校园墙", "已报备", "说三遍", "勿撤", "以备不时之需",
        "重要的事情", "加我qq", "加qq", "加微信", "错过校园",
    ]
    # 相似度判定：两条消息去除空白后重叠比例阈值
    SIMILARITY = 0.6

    def __init__(self, score: int = 55, threshold: int = 4, invite_threshold: int = 3) -> None:
        super().__init__("repeat_detector", score)
        self.threshold = threshold          # 完全相同的连发条数
        self.invite_threshold = invite_threshold  # 拉群消息的连发条数（更敏感）
        # user_id -> [(message_id, content)]
        self._history: dict[str, list[tuple[str, str]]] = {}

    @staticmethod
    def _similar(a: str, b: str) -> float:
        """简单相似度：基于字符集合 Jaccard."""
        sa, sb = set(a), set(b)
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def _is_invite(self, msg: str, group_id: str = "") -> bool:
        if any(kw in msg for kw in self.INVITE_KEYWORDS):
            return True
        # 含外部 QQ 号（拉人加好友 / 加群引流）
        qq_numbers = extract_qq_numbers(msg)
        if qq_numbers:
            other = [q for q in qq_numbers if q != group_id]
            if other:
                return True
        return False

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检测重复或拉群刷屏消息."""
        user_id = context.get("user_id", "")
        msg_id = str(context.get("message_id", ""))
        group_id = context.get("group_id", "")
        if not user_id:
            return RuleResult(rule_name=self.name, hit=False)

        if user_id not in self._history:
            self._history[user_id] = []
            while len(self._history) > self.MAX_TRACKED_USERS:
                oldest = next(iter(self._history))
                del self._history[oldest]

        history = self._history[user_id]
        history.append((msg_id, message))
        if len(history) > 10:
            history.pop(0)

        # —— 情形 A：连续 N 条完全相同（或高度相似）——
        recent = history[-self.threshold:]
        if len(recent) >= self.threshold:
            contents = [c for _, c in recent]
            if len(set(contents)) == 1:
                target = contents[0]
                # 撤回该用户所有相同消息（从第一条开始）
                withdraw_ids = [mid for mid, c in history if c == target]
                return RuleResult(
                    rule_name=self.name,
                    hit=True,
                    reason=f"连续发送 {self.threshold} 条相同消息",
                    score=self.score,
                    withdraw_ids=withdraw_ids,
                )
            # 高度相似（模糊重复）
            if all(self._similar(contents[0], c) >= self.SIMILARITY for c in contents[1:]):
                first = contents[0]
                withdraw_ids = [
                    mid for mid, c in history
                    if self._similar(first, c) >= self.SIMILARITY
                ]
                return RuleResult(
                    rule_name=self.name,
                    hit=True,
                    reason=f"连续发送 {self.threshold} 条相似消息",
                    score=self.score,
                    withdraw_ids=withdraw_ids,
                )

        # —— 情形 B：连续拉群 / 加群 / 外泄 QQ 引流（更敏感）——
        recent_inv = history[-self.invite_threshold:]
        if len(recent_inv) >= self.invite_threshold:
            if all(self._is_invite(c, group_id) for _, c in recent_inv):
                # 撤回该用户本轮所有引流消息（从第一条开始）
                withdraw_ids = [
                    mid for mid, c in history if self._is_invite(c, group_id)
                ]
                return RuleResult(
                    rule_name=self.name,
                    hit=True,
                    reason=f"连续发送 {self.invite_threshold} 条拉群/引流消息",
                    score=self.score,
                    withdraw_ids=withdraw_ids,
                )

        return RuleResult(rule_name=self.name, hit=False)


# 微信引流信号检测（供 GroupInviteRule 复用，与 WechatRule 模式一致）
_WECHAT_SIGNAL_RE = re.compile(
    r"(?:微信|wx|vx)[号:]?\s*[a-zA-Z0-9_-]{6,20}|微[信]?[号]?[：:]",
    re.IGNORECASE,
)


def _has_wechat_signal(message: str) -> bool:
    """是否含微信引流信号（微信号 / wx / vx / 微信: 等）。"""
    return bool(_WECHAT_SIGNAL_RE.search(message))


class WechatRule(SpamRule):
    """微信号规则 - 检测微信相关."""

    WECHAT_PATTERNS = [
        r"微信[号:]?\s*[a-zA-Z0-9_-]{6,20}",
        r"wx[号:]?\s*[a-zA-Z0-9_-]{6,20}",
        r"vx[号:]?\s*[a-zA-Z0-9_-]{6,20}",
        r"加微[信]?",
        r"微[信]?[号]?[：:]",
    ]

    def __init__(self, score: int = 50) -> None:
        super().__init__("wechat_detector", score)
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.WECHAT_PATTERNS]

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检测微信号."""
        for pattern in self.patterns:
            match = pattern.search(message)
            if match:
                return RuleResult(
                    rule_name=self.name,
                    hit=True,
                    reason=f"检测到微信引流: {match.group()[:20]}...",
                    score=self.score,
                    metadata={"matched": match.group()},
                )
        return RuleResult(rule_name=self.name, hit=False)


class QRCodeRule(SpamRule):
    """二维码规则 - 检测二维码相关."""

    def __init__(self, score: int = 25) -> None:
        super().__init__("qrcode_detector", score)
        self.patterns = [
            r"二维码",
            r"扫码",
            r"扫我",
            r"二维码[图片]?",
        ]

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        """检测二维码."""
        for pattern in self.patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return RuleResult(
                    rule_name=self.name,
                    hit=True,
                    reason="检测到二维码相关",
                    score=self.score,
                )
        return RuleResult(rule_name=self.name, hit=False)


class GroupInviteRule(SpamRule):
    """单条群邀请/拉群广告：邀请关键词 + (外部号码 或 图片) → 直接踢+撤回。

    仅关键词、没有号码也没有图片时不踢（可能是新生在问"群号多少"）。
    """

    KEYWORDS = [
        "群号", "加群", "拉群", "qq群", "QQ群", "q群",
        "扫码进群", "扫码加群", "拉你进群", "邀请进群",
        "二维码", "扫码", "校园墙",
    ]

    def __init__(self, score: int = 90) -> None:
        super().__init__("group_invite", score)

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        msg_id = str(context.get("message_id", ""))
        group_id = context.get("group_id", "")

        if not any(kw in message for kw in self.KEYWORDS):
            return RuleResult(rule_name=self.name, hit=False)

        # 外部号码（排除当前群号本身）
        external = [q for q in extract_qq_numbers(message) if q != group_id]
        has_image = bool(context.get("has_image", False))
        has_wechat = _has_wechat_signal(message)
        has_phone = bool(extract_phone_numbers(message))

        # 有关键词但既没 QQ 号/图片，也没微信/手机 → 可能是正常提问，不踢
        if not external and not has_image and not has_wechat and not has_phone:
            return RuleResult(rule_name=self.name, hit=False)

        reason = "群邀请/二维码广告"
        if external:
            reason += f": {external[0]}"
        elif has_wechat:
            reason += ": 含微信引流"
        elif has_phone:
            reason += ": 含手机号"
        elif has_image:
            reason += ": 含图片"

        return RuleResult(
            rule_name=self.name,
            hit=True,
            reason=reason,
            score=self.score,
            withdraw_ids=[msg_id] if msg_id else [],
        )


class SchoolTopicRule(SpamRule):
    """学校话题弱信号 - 多个学校话题词 + 媒体 → 弱分, 交 LLM 确认.

    用于识别"伪装校园通知/新生指南 + 引流材料"组合（C 方案多消息聚合后，
    话术文字与视频/图片合并送审）。单条纯文字多话题词（日常聊学校话题）不触发，
    避免 LLM 调用滥用；仅当消息含媒体(图片/视频)时才视为可疑组合。

    命中只给弱分(不直撤)，交由引擎的 LLM 二次确认看完整上下文(话术+媒体)判断。
    需配合 C 方案的消息聚合，才能把"纯视频/文档 + 同批文字话术"组合送进 LLM。
    """

    # 具体校园场景词(不含"大学/大一"等日常高频泛词，降低误触发)
    SCHOOL_TOPICS = [
        "学生会", "转专业", "社团纳新", "入团入党", "竞选班委",
        "宿舍安排", "军训", "录取通知书", "奖助学金", "学籍",
        "入党", "转团", "专业调剂", "入学定金", "转班",
    ]
    MIN_TOPICS = 3

    def __init__(self, score: int = 15) -> None:
        super().__init__("school_topic", score)

    async def check(self, message: str, context: dict[str, Any]) -> RuleResult:
        has = sum(1 for kw in self.SCHOOL_TOPICS if kw in message)
        if has < self.MIN_TOPICS:
            return RuleResult(rule_name=self.name, hit=False)
        # 仅当消息含媒体(图片/视频)时，话题词组合才可疑(伪装校园通知+引流材料)。
        # 纯文字多话题词(日常聊学校话题)不触发，避免 LLM 调用滥用。
        # 注: C 聚合后 check 的 has_media 是当前消息(视频/图片)的媒体标志，
        #     聚合文本里的话题词由此被纳入 LLM 确认范围。
        has_media = bool(context.get("has_media", False))
        if not has_media:
            return RuleResult(rule_name=self.name, hit=False)
        return RuleResult(
            rule_name=self.name,
            hit=True,
            reason=f"校园话题词×{has}+媒体(疑似伪装校园引流, 交LLM确认)",
            score=self.score,
        )


# === 默认规则集 ===

def get_default_rules() -> list[SpamRule]:
    """获取默认规则集.

    Returns:
        规则列表.
    """
    return [
        # 高危险规则
        KeywordRule("ad_keywords", 30, [
            "刷单", "兼职", "日赚", "月入", "高薪", "诚聘",
            "贷款", "信用卡套现", "代办", "代开",
            "加群", "拉群", "拉你进群",
        ]),
        WechatRule(score=50),
        ContactRule(score=35),
        UrlRule(score=20),
        QRCodeRule(score=25),
        RepeatRule(score=55, threshold=4, invite_threshold=3),
        GroupInviteRule(score=90),
        SchoolTopicRule(score=15),
    ]
