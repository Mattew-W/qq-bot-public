"""反垃圾服务 - 向后兼容导出.

实际实现位于 services/anti_spam/ 子模块。
"""

from services.anti_spam.engine import AntiSpamService, get_anti_spam_service
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
