#!/usr/bin/env python3
"""QQ Bot 实时监控窗口 —— 仿 NapCat 控制台风格。

只依赖标准库（tkinter + subprocess + threading），无第三方依赖。
用 venv 内置的 pythonw.exe 启动，无控制台窗口。
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, scrolledtext

# ----- 配置 -----
ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
SERVICE_NAME = "QQBot"
BUF_MAX = 1500               # 界面里最多保留多少行
TAIL_INITIAL = 80            # 启动后先显示最近多少行
STATUS_INTERVAL_MS = 3000    # 服务状态轮询周期

# loguru / 项目自定义级别的配色（与 NapCat 控制台类似的暗色风格）
LEVEL_COLORS = {
    "INFO": "#7ce38b",
    "WARNING": "#ffb86c",
    "WARN": "#ffb86c",
    "ERROR": "#ff6b6b",
    "ACTION": "#7aa2f7",
    "SPAM": "#bb9af7",
    "LLM": "#f7768e",
    "DEBUG": "#888888",
    "TRACE": "#666666",
}

# sc.exe 是控制台程序，从 GUI(pythonw) 调它时 Windows 会给它弹一个一闪而过的黑框。
# 加这个标志后所有 subprocess 调用都不会再弹黑框。
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _sc(args, **kwargs):
    """运行 sc 命令且不弹控制台窗口。"""
    kwargs.setdefault("creationflags", _NO_WINDOW)
    return subprocess.run(args, **kwargs)


class BotMonitor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"QQ Bot 实时监控 - {SERVICE_NAME}")
        self.geometry("1280x720")
        self.configure(bg="#1a1b26")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # ===== 顶部状态条 + 按钮 =====
        self.status_var = tk.StringVar(value="状态: 加载中...")
        top = tk.Frame(self, bg="#1a1b26")
        top.pack(fill=tk.X, padx=8, pady=6)

        self.status_label = tk.Label(
            top, textvariable=self.status_var,
            fg="#7ce38b", bg="#1a1b26",
            font=("Microsoft YaHei", 10, "bold"),
        )
        self.status_label.pack(side=tk.LEFT)

        btns = tk.Frame(top, bg="#1a1b26")
        btns.pack(side=tk.RIGHT)
        for text, cmd, color in (
            ("暂停/继续", self.toggle_pause, "#3b4261"),
            ("打开日志文件夹", self.open_log_dir, "#3b4261"),
            ("停止 bot", self.stop_bot, "#7a2a2a"),
            ("重启 bot", self.restart_bot, "#2a4a7a"),
        ):
            tk.Button(
                btns, text=text, command=cmd,
                bg=color, fg="#c0caf5", relief="flat",
                activebackground="#414868", activeforeground="#c0caf5",
                font=("Microsoft YaHei", 9), padx=10, pady=2,
            ).pack(side=tk.LEFT, padx=2)

        # ===== 日志显示区 =====
        self.text = scrolledtext.ScrolledText(
            self, bg="#0f1018", fg="#c0caf5", insertbackground="#c0caf5",
            font=("Consolas", 9), wrap="none",
        )
        self.text.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.text.tag_configure("NORM", foreground="#c0caf5")
        for level, color in LEVEL_COLORS.items():
            self.text.tag_configure(level, foreground=color)
        self.text.tag_configure("SYS", foreground="#bb9af7")

        self.paused = False
        self._closing = False
        self.tail_thread: threading.Thread | None = None

        self.after(300, self.update_status)
        self.after(300, self.start_tail)

    # ---------------- 日志跟踪线程 ----------------
    def start_tail(self) -> None:
        if self.tail_thread and self.tail_thread.is_alive():
            return
        self.tail_thread = threading.Thread(target=self.tail_loop, daemon=True)
        self.tail_thread.start()

    def tail_loop(self) -> None:
        last_path: Path | None = None
        f = None
        while not self._closing:
            try:
                if not LOG_DIR.exists():
                    self._append("SYS", f"日志目录不存在: {LOG_DIR}（bot 还没启动？）")
                    time.sleep(3)
                    continue
                logs = sorted(
                    LOG_DIR.glob("bot_*.log"),
                    key=lambda p: p.stat().st_mtime,
                    reverse=True,
                )
                if not logs:
                    self._append("SYS", f"未找到 {LOG_DIR}\\bot_*.log")
                    time.sleep(3)
                    continue
                cur = logs[0]
                if cur != last_path:
                    if f is not None:
                        try:
                            f.close()
                        except Exception:
                            pass
                    last_path = cur
                    f = open(cur, "r", encoding="utf-8", errors="replace")
                    # 先回看最近 TAIL_INITIAL 行作为上下文
                    try:
                        f.seek(0, os.SEEK_END)
                        size = f.tell()
                        f.seek(max(0, size - 12 * 1024), os.SEEK_SET)
                        buf = f.read()
                        lines = buf.splitlines()[-TAIL_INITIAL:]
                        self._append(
                            "SYS",
                            f"── 跟踪 {cur.name} ── (回看最近 {len(lines)} 行)",
                        )
                        for line in lines:
                            self._append(self._guess_level(line), line)
                    except Exception:
                        pass
                if f is not None:
                    line = f.readline()
                    if line:
                        self._append(self._guess_level(line), line.rstrip("\n"))
                    else:
                        time.sleep(0.2)
            except Exception as e:
                self._append("SYS", f"读取异常: {e}")
                time.sleep(2)

    @staticmethod
    def _guess_level(line: str) -> str:
        # loguru 行格式: "2026-07-24 08:33:21 | WARNING  | core:warning:43 | ..."
        for lv in LEVEL_COLORS:
            if f"| {lv}" in line:
                return lv
        return "NORM"

    # ---------------- UI 线程调度 ----------------
    def _append(self, level: str, msg: str) -> None:
        self.after(0, lambda: self._do_append(level, msg))

    def _do_append(self, level: str, msg: str) -> None:
        if self.paused:
            return
        self.text.insert(tk.END, msg + "\n", level)
        end = self.text.index(tk.END)
        total = int(end.split(".")[0])
        if total > BUF_MAX:
            self.text.delete("1.0", f"{total - BUF_MAX + 200}.0")
        self.text.see(tk.END)

    # ---------------- 按钮动作 ----------------
    def toggle_pause(self) -> None:
        self.paused = not self.paused
        self._append("SYS", f"监控 {'已暂停' if self.paused else '已继续'}")

    def open_log_dir(self) -> None:
        try:
            os.startfile(str(LOG_DIR))
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def stop_bot(self) -> None:
        if not messagebox.askyesno(
            "确认停止 bot",
            f"将停止 Windows 服务 [{SERVICE_NAME}](NapCat 不受影响，QQ 登录态保留)",
        ):
            return
        try:
            _sc(["sc", "stop", SERVICE_NAME], check=False)
            self._append("SYS", f"已请求停止 {SERVICE_NAME}")
        except Exception as e:
            messagebox.showerror("失败", str(e))

    def restart_bot(self) -> None:
        if not messagebox.askyesno(
            "确认重启 bot",
            f"将重启 [{SERVICE_NAME}](NapCat 不受影响，QQ 登录态保留)",
        ):
            return
        try:
            _sc(["sc", "stop", SERVICE_NAME], check=False)
            self.after(
                5000,
                lambda: _sc(["sc", "start", SERVICE_NAME], check=False),
            )
            self._append(
                "SYS",
                f"{SERVICE_NAME} 正在重启……NapCat 与 QQ 登录保留，无需重新扫码",
            )
        except Exception as e:
            messagebox.showerror("失败", str(e))

    # ---------------- 状态轮询 ----------------
    def update_status(self) -> None:
        try:
            out = _sc(
                ["sc", "query", SERVICE_NAME],
                capture_output=True, text=True,
                encoding="gbk", errors="replace",
            ).stdout
            if "RUNNING" in out:
                state, color = "● 运行中", "#7ce38b"
            elif "STOP_PENDING" in out:
                state, color = "◐ 停止中", "#ffb86c"
            elif "START_PENDING" in out:
                state, color = "◑ 启动中", "#7aa2f7"
            elif "STOPPED" in out:
                state, color = "○ 已停止", "#ff6b6b"
            elif "PAUSED" in out:
                state, color = "⏸ 已暂停", "#888888"
            else:
                state, color = "? 未安装或未知", "#888888"
        except Exception as e:
            state, color = f"查询失败: {e}", "#ff6b6b"
        self.status_var.set(
            f"服务 {SERVICE_NAME}: {state}    |    日志: {LOG_DIR}\\bot_*.log    |    NapCat 与 bot 独立,可单独重启"
        )
        self.status_label.configure(fg=color)
        if not self._closing:
            self.after(STATUS_INTERVAL_MS, self.update_status)

    # ---------------- 窗口关闭 ----------------
    def on_close(self) -> None:
        self._closing = True
        self.destroy()


if __name__ == "__main__":
    BotMonitor().mainloop()
