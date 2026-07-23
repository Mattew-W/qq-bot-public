"""美团分析插件.

提供 /meituan 命令，支持上传数据文件并进行 AI 分析。
"""

from __future__ import annotations

from pathlib import Path

from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.matcher import Matcher
from nonebot.params import CommandArg

from config import get_settings
from core.exceptions import MeituanException
from core.logger import get_logger
from services.meituan_service import DataAnalyzer

logger = get_logger("plugin.meituan")

meituan_cmd = on_command("meituan", priority=5, block=False)
meituan_analyze = on_command("analyze", priority=5, block=False)

# 服务
analyzer = DataAnalyzer()


@meituan_cmd.handle()
async def handle_meituan(event: GroupMessageEvent, args: Message = CommandArg()) -> None:
    """处理 /meituan 命令 - 数据文件管理."""
    text = args.extract_plain_text().strip()

    if not text:
        await meituan_cmd.send(
            "📊 美团数据分析\n"
            "用法:\n"
            "  /meituan list          - 查看已上传的数据文件\n"
            "  /meituan stats <文件>  - 快速统计\n"
            "  /analyze <文件> <问题> - AI 分析\n\n"
            "请先上传文件再使用命令分析"
        )
        return

    parts = text.split(maxsplit=1)
    subcmd = parts[0].lower()

    if subcmd == "list":
        await _handle_list_files()
    else:
        await meituan_cmd.send(f"未知子命令: {subcmd}")


@meituan_analyze.handle()
async def handle_analyze(event: GroupMessageEvent, args: Message = CommandArg()) -> None:
    """处理 /analyze 命令 - 数据分析."""
    text = args.extract_plain_text().strip()
    if not text:
        await meituan_analyze.send("用法: /analyze <文件名> <分析问题>")
        return

    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await meituan_analyze.send("请提供文件名和问题，例如: /analyze data.csv 本月销售趋势")
        return

    file_name, question = parts
    # 路径安全校验：禁止路径穿越
    if ".." in file_name or "/" in file_name or "\\" in file_name:
        await meituan_analyze.send("文件名不合法")
        return

    settings = get_settings()
    file_path = Path(settings.MEITUAN_DATA_DIR) / file_name

    if not file_path.exists():
        await meituan_analyze.send(f"文件不存在: {file_name}")
        return

    await meituan_analyze.send("⏳ 正在分析中，请稍候...")

    try:
        result = await analyzer.load_and_analyze(str(file_path), question)
        await meituan_analyze.send(f"📊 分析结果:\n{result}")
    except MeituanException as e:
        await meituan_analyze.send(f"分析失败: {e.message}")
    except Exception as e:
        logger.error(f"分析失败: {e}")
        await meituan_analyze.send(f"分析失败: {e}")


async def _handle_list_files() -> None:
    """列出数据文件."""
    settings = get_settings()
    data_dir = Path(settings.MEITUAN_DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)

    files = list(data_dir.glob("*.csv")) + list(data_dir.glob("*.xlsx")) + list(data_dir.glob("*.json"))

    if not files:
        await meituan_cmd.send("暂无数据文件，请上传 CSV/Excel/JSON 文件到 data/meituan/ 目录")
        return

    file_list = "\n".join(f"  📄 {f.name} ({f.stat().st_size / 1024:.1f} KB)" for f in files)
    await meituan_cmd.send(f"数据文件列表:\n{file_list}")
