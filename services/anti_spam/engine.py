"""反垃圾引擎 - 规则引擎 + 风险评分 + LLM 二次确认."""

from __future__ import annotations

import re
from typing import Any

from config import get_settings
from core.exceptions import AntiSpamException
from core.logger import get_logger
from services.prompt_builder import build_antispam_prompt
from services.anti_spam.rules import RuleResult, get_default_rules

logger = get_logger("service.antispam")


class AntiSpamService:
    """反垃圾服务.

    规则引擎 + 风险评分 + LLM 二次确认。
    """

    def __init__(self) -> None:
        self._rules = get_default_rules()
        self._settings = get_settings()

    def add_rule(self, rule) -> None:
        """添加规则."""
        self._rules.append(rule)

    def clear_rules(self) -> None:
        """清空规则."""
        self._rules.clear()

    async def check(
        self,
        message: str,
        user_id: str,
        group_id: str,
        **context: Any,
    ) -> dict[str, Any]:
        """检查消息.

        Args:
            message: 消息内容.
            user_id: 用户 ID.
            group_id: 群 ID.
            **context: 额外上下文.

        Returns:
            检查结果.
        """
        ctx = {"user_id": user_id, "group_id": group_id, **context}

        # 1. 运行规则引擎
        rule_results = await self._run_rules(message, ctx)

        # 2. 计算风险分
        risk_score = sum(r.score for r in rule_results if r.hit)

        # 3. 确定动作
        action = self._decide_action(risk_score)

        # 汇总所有规则要求撤回的消息 ID（从第一条开始删除）。
        # 连带撤回闸门: 仅当命中规则允许连带撤回(chain_delete=True)时,
        # 才把该规则声索的 withdraw_ids 纳入撤回。规则可设 chain_delete=False
        # 退出(如纯媒体引流只踢不撤, 守"识别到二维码才撤"铁律)。
        withdraw_ids: list[str] = []
        for r in rule_results:
            if r.hit and r.chain_delete and r.withdraw_ids:
                for mid in r.withdraw_ids:
                    if mid not in withdraw_ids:
                        withdraw_ids.append(mid)

        result: dict[str, Any] = {
            "risk_score": risk_score,
            "action": action,
            "withdraw_ids": withdraw_ids,
            "rule_hits": [
                {
                    "rule_name": r.rule_name,
                    "reason": r.reason,
                    "score": r.score,
                }
                for r in rule_results
                if r.hit
            ],
        }

        # 4. 中等风险 → LLM 二次确认
        if action == "llm_confirm":
            llm_verdict = await self._llm_confirm(message, rule_results)
            result["llm_verdict"] = llm_verdict
            if llm_verdict.get("is_spam") is True:
                result["action"] = "withdraw"
                result["risk_score"] = max(risk_score, 60)
            elif llm_verdict.get("is_spam") is False:
                result["action"] = "log"
                result["risk_score"] = min(risk_score, 30)
            else:
                # LLM 不可用，保持原始风险分数，降级为 log
                result["action"] = "log"

        logger.spam(
            f"反垃圾检查: user={user_id} group={group_id} "
            f"risk={risk_score} action={result['action']}"
        )

        return result

    async def _run_rules(
        self,
        message: str,
        context: dict[str, Any],
    ) -> list[RuleResult]:
        """运行所有规则."""
        results: list[RuleResult] = []
        for rule in self._rules:
            try:
                result = await rule.check(message, context)
                results.append(result)
            except Exception as e:
                logger.warning(f"规则 {rule.name} 执行失败: {e}")
                results.append(RuleResult(rule_name=rule.name, hit=False))
        return results

    def _decide_action(self, risk_score: int) -> str:
        """根据风险分决定动作."""
        if risk_score >= self._settings.ANTISPAM_THRESHOLD_KICK:
            return "kick"
        elif risk_score >= self._settings.ANTISPAM_THRESHOLD_BAN:
            return "ban"
        elif risk_score >= self._settings.ANTISPAM_THRESHOLD_WITHDRAW:
            return "withdraw"
        elif risk_score >= self._settings.ANTISPAM_THRESHOLD_LLM:
            return "llm_confirm"
        else:
            return "log"

    async def _llm_confirm(
        self,
        message: str,
        rule_results: list[RuleResult],
    ) -> dict[str, Any]:
        """LLM 二次确认."""
        try:
            from services.llm_service import get_llm_service

            llm = get_llm_service()
            hits = [
                {"rule_name": r.rule_name, "score": r.score}
                for r in rule_results
                if r.hit
            ]

            messages = build_antispam_prompt(message, hits)
            reply = await llm.ask(messages=messages)

            is_spam = ("是垃圾" in reply and "不是垃圾" not in reply) or "确认是" in reply
            return {
                "is_spam": is_spam,
                "raw_reply": reply,
            }
        except Exception as e:
            logger.error(f"LLM 反垃圾确认失败: {e}")
            return {"is_spam": None, "raw_reply": "", "error": str(e)}


_anti_spam_service: AntiSpamService | None = None


def get_anti_spam_service() -> AntiSpamService:
    """获取反垃圾服务实例."""
    global _anti_spam_service
    if _anti_spam_service is None:
        _anti_spam_service = AntiSpamService()
    return _anti_spam_service
