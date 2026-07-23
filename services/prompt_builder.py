"""Prompt Builder - 统一管理所有 AI Prompt.

禁止在业务代码中拼接 prompt 字符串，必须通过 PromptBuilder 构造。
"""

from __future__ import annotations

from typing import Any


class PromptBuilder:
    """Prompt 构造器.

    使用 Builder 模式，支持链式调用。
    """

    def __init__(self) -> None:
        self._system: str = ""
        self._context: list[str] = []
        self._history: list[dict[str, str]] = []
        self._user: str = ""
        self._constraints: list[str] = []
        self._output_format: str = ""

    def set_system(self, system: str) -> "PromptBuilder":
        """设置系统提示词.

        Args:
            system: 系统提示词.

        Returns:
            self.
        """
        self._system = system
        return self

    def add_context(self, context: str) -> "PromptBuilder":
        """添加上下文信息.

        Args:
            context: 上下文文本.

        Returns:
            self.
        """
        self._context.append(context)
        return self

    def add_history(self, role: str, content: str) -> "PromptBuilder":
        """添加历史对话.

        Args:
            role: 角色 (user/assistant).
            content: 内容.

        Returns:
            self.
        """
        self._history.append({"role": role, "content": content})
        return self

    def set_user(self, user: str) -> "PromptBuilder":
        """设置用户问题.

        Args:
            user: 用户输入.

        Returns:
            self.
        """
        self._user = user
        return self

    def add_constraint(self, constraint: str) -> "PromptBuilder":
        """添加约束条件.

        Args:
            constraint: 约束描述.

        Returns:
            self.
        """
        self._constraints.append(constraint)
        return self

    def set_output_format(self, fmt: str) -> "PromptBuilder":
        """设置输出格式.

        Args:
            fmt: 格式描述.

        Returns:
            self.
        """
        self._output_format = fmt
        return self

    def build(self) -> list[dict[str, str]]:
        """构造消息列表.

        Returns:
            OpenAI 格式的消息列表.
        """
        messages: list[dict[str, str]] = []

        # System prompt
        system_parts: list[str] = []
        if self._system:
            system_parts.append(self._system)
        if self._context:
            system_parts.append("# 上下文信息\n" + "\n".join(f"- {c}" for c in self._context))
        if self._constraints:
            system_parts.append("# 约束条件\n" + "\n".join(f"- {c}" for c in self._constraints))
        if self._output_format:
            system_parts.append(f"# 输出格式\n{self._output_format}")

        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        # History
        messages.extend(self._history)

        # User question
        if self._user:
            messages.append({"role": "user", "content": self._user})

        return messages

    def reset(self) -> "PromptBuilder":
        """重置构造器.

        Returns:
            self.
        """
        self._system = ""
        self._context = []
        self._history = []
        self._user = ""
        self._constraints = []
        self._output_format = ""
        return self


# === 预定义 Prompt 模板 ===

AI_QA_SYSTEM = """你是宁波工程学院招新群里的机器人，扮演一个在校学长/学姐，给 26 届新生答疑。

## 人设与语气
- 话少、直接、不啰嗦，像在 QQ 上闲聊，别端着也别像客服，更别像 AI 写小作文
- 口语化、自然，偶尔用「……」「。」收尾，少用感叹号和客套话
- 用中文

## 怎么用上下文
- 「对话历史」是你和对方刚才聊的：遇到「那个」「它」「前面说的」这类指代，先从对话历史搞清楚指什么，再回答
- 「上下文信息」是学校资料库，用来查具体事实（校区、宿舍、转专业等）
- 两者都推不出来的，才说"这个我不太清楚，看录取通知书或打 0574-87616666 问下"，别编

## 回答风格
- 简洁，一般一两句话；要把事说清楚时可多说一句，但别啰嗦
- 禁止"根据资料""温馨提示""总之"这类开头，直接给答案
- 不分段、不列点"""

ANTISPAM_SYSTEM = """你是一个反垃圾消息分析助手。你需要判断一条 QQ 群消息是否属于垃圾信息。

## 垃圾类型
- 广告推广（产品、服务、公众号）
- 诈骗信息（中奖、刷单、贷款）
- 恶意链接（钓鱼、病毒、色情）
- 骚扰内容（人身攻击、恶意刷屏）
- 引流信息（微信号、QQ号、手机号）

## 判断标准
- 正常聊天：日常交流、提问、分享
- 疑似垃圾：包含联系方式、链接、广告词
- 明确垃圾：明显的广告、诈骗、恶意内容"""

MEITUAN_SYSTEM = """你是一个美团业务数据分析助手。你需要根据提供的数据回答分析问题。

## 分析原则
- 基于数据说话，不编造数字
- 给出清晰的数据支撑
- 提供可操作的建议
- 使用中文回复"""


def build_ai_qa_prompt(
    question: str,
    knowledge: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """构造 AI 问答 Prompt.

    Args:
        question: 用户问题.
        knowledge: 知识库检索结果.
        history: 历史对话.

    Returns:
        消息列表.
    """
    builder = PromptBuilder()
    builder.set_system(AI_QA_SYSTEM)

    if knowledge:
        for k in knowledge:
            builder.add_context(k)

    if history:
        for h in history:
            builder.add_history(h["role"], h["content"])

    builder.set_user(question)
    builder.add_constraint("简洁为主，一两句话，别啰嗦也别像 AI 写小作文")
    builder.add_constraint("语气像 QQ 上闲聊的在校学长/学姐，口语、自然")
    builder.add_constraint("先用对话历史理解指代，再用资料库查事实；都没有就说不知道，绝不编造")

    return builder.build()


def build_antispam_prompt(message: str, rule_hits: list[dict[str, Any]]) -> list[dict[str, str]]:
    """构造反垃圾确认 Prompt.

    Args:
        message: 消息内容.
        rule_hits: 命中的规则列表.

    Returns:
        消息列表.
    """
    builder = PromptBuilder()
    builder.set_system(ANTISPAM_SYSTEM)

    rule_desc = "\n".join(
        f"- 规则 {i+1}: {r.get('rule_name', 'unknown')} (风险分: {r.get('score', 0)})"
        for i, r in enumerate(rule_hits)
    )

    builder.set_user(
        f"请分析以下消息是否为垃圾信息。\n\n"
        f"消息内容: {message}\n\n"
        f"命中的规则:\n{rule_desc}\n\n"
        f"请给出你的判断：是垃圾/不是垃圾/不确定，并简要说明理由。"
    )
    builder.set_output_format("请按以下格式回复：\n判断: [是垃圾/不是垃圾/不确定]\n理由: [简要说明]")

    return builder.build()


def build_meituan_prompt(question: str, data_summary: str) -> list[dict[str, str]]:
    """构造美团分析 Prompt.

    Args:
        question: 分析问题.
        data_summary: 数据摘要.

    Returns:
        消息列表.
    """
    builder = PromptBuilder()
    builder.set_system(MEITUAN_SYSTEM)
    builder.add_context(f"数据摘要:\n{data_summary}")
    builder.set_user(question)
    builder.add_constraint("回答必须基于提供的数据")
    builder.add_constraint("给出具体数字支撑")

    return builder.build()
