"""反垃圾子模块."""

from services.anti_spam.rules import (
    SpamRule,
    RuleResult,
    KeywordRule,
    RegexRule,
    UrlRule,
    ContactRule,
    RepeatRule,
    WechatRule,
    QRCodeRule,
    get_default_rules,
)
from services.anti_spam.engine import AntiSpamService, get_anti_spam_service

__all__ = [
    "AntiSpamService",
    "get_anti_spam_service",
    "SpamRule",
    "RuleResult",
    "KeywordRule",
    "RegexRule",
    "UrlRule",
    "ContactRule",
    "RepeatRule",
    "WechatRule",
    "QRCodeRule",
    "get_default_rules",
]
