"""数据分析插件.

提供 /analyze 命令，支持上传数据文件并进行 AI 分析。
"""

from __future__ import annotations

from pathlib import Path

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from config import get_settings
from core.exceptions import AnalysisException
from core.logger import get_logger
from services.analysis import DataAnalyzer

logger = get_logger("plugin.analysis")

analyze_cmd = on_command("analyze", priority=5, block=False)

analyzer = DataAnalyzer()


@analyze_cmd.handle()
async def handle_analyze(event: GroupMessageEvent, args: Message = CommandArg()) -> None:
    """处理 /analyze 命令 - 数据分析."""
    text = args.extract_plain_text().strip()
    if not text:
        await analyze_cmd.send("用法: /analyze <文件名> <分析问题>")
        return

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await analyze_cmd.send("请提供文件名和问题，例如: /analyze data.csv 本月销售趋势")
        return

    file_name, question = parts
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        await analyze_cmd.send("文件名不合法")
        return

    settings = get_settings()
    file_path = Path(settings.DATA_ANALYSIS_DIR) / file_name

    if not file_path.exists():
        await analyze_cmd.send(f"文件不存在: {file_name}")
        return

    await analyze_cmd.send("⏳ 正在分析中，请稍候...")

    try:
        result = await analyzer.load_and_analyze(str(file_path), question)
        await analyze_cmd.send(f"📊 分析结果:\n{result}")
    except AnalysisException as e:
        await analyze_cmd.send(f"分析失败: {e.message}")
    except Exception as e:
        logger.error(f"分析失败: {e}")
        await analyze_cmd.send(f"分析失败: {e}")
