#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""thesis-retrieval 初始化启动器。

用途：当 skill 首次运行（无 resources/config/sources.env）而当前环境是非交互
（AI agent / 管道 / 计划任务）时，在**真实终端**里弹出新窗口运行主脚本的三问式
初始化（选库 → 摘要筛选 → SCI 分区），让真人确认并落盘配置。等该窗口里初始化
完成后，AI 再重试检索即可。

用法：
    python scripts/init_config.py            # 弹新终端窗口初始化并等待
    python scripts/init_config.py --no-wait  # 只弹窗口，不等待（用于后台）

实现：Windows 用 `start cmd /k`，macOS 用 Terminal.app，Linux 尝试常见终端模拟器。
窗口内脚本退出后，本脚本打印下一步提示。
"""

import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
MAIN = SKILL_DIR / "scripts" / "thesis_retrieval.py"
SOURCES_ENV = SKILL_DIR / "resources" / "config" / "sources.env"


def _print_next_steps() -> None:
    print(
        "\n已在新终端窗口中启动初始化。请在该窗口走完三问式（选库 → 摘要筛选 → SCI 分区）。\n"
        "完成后回来告诉我，我会用保存的配置继续检索。",
        flush=True,
    )


def launch(wait: bool = True) -> int:
    """Open a real terminal and run the interactive init there."""
    if not MAIN.exists():
        print(f"主脚本不存在: {MAIN}", file=sys.stderr)
        return 1

    cmd_py = shlex.quote(sys.executable)
    cmd_main = shlex.quote(str(MAIN))

    if os.name == "nt":  # Windows
        # Git-Bash 下 `cmd //c start ...` 会吞引号导致命令不执行；改用 PowerShell
        # Start-Process 启动，引号处理可靠。/k 保持窗口开着，让用户看到结果。
        inner = f'{cmd_py} {cmd_main} test'
        subprocess.Popen(
            [
                "powershell", "-NoProfile", "-Command",
                "Start-Process", "cmd",
                "-ArgumentList", f"'/k','{inner}'",
            ],
            cwd=str(SKILL_DIR),
        )
    elif sys.platform == "darwin":  # macOS
        script = f'tell application "Terminal" to do script "{cmd_py} {cmd_main} test"'
        subprocess.Popen(["osascript", "-e", script], cwd=str(SKILL_DIR))
    else:  # Linux/Unix
        term = None
        for t in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
            if shutil.which(t):
                term = t
                break
        if term is None:
            print(
                "未找到可用终端模拟器（x-terminal-emulator/gnome-terminal/konsole/xterm）。\n"
                f"请在你的终端手动运行：\n    {cmd_py} {cmd_main} test",
                file=sys.stderr,
            )
            return 1
        subprocess.Popen(
            [term, "-e", f"{cmd_py} {shlex.quote(str(MAIN))} test"],
            cwd=str(SKILL_DIR),
        )

    _print_next_steps()

    if not wait:
        return 0

    # 轮询等待配置生成（用户在新窗口完成初始化后写盘）。
    print("等待初始化完成（检测 sources.env 生成）…", flush=True)
    deadline = time.time() + 300  # 最多等 5 分钟
    while time.time() < deadline:
        if SOURCES_ENV.exists():
            print(f"检测到配置已生成：{SOURCES_ENV}", flush=True)
            return 0
        time.sleep(1.5)
    print("超时（5 分钟）未检测到 sources.env。请确认已在弹出的终端窗口完成三问式。",
          file=sys.stderr)
    return 2


def main() -> int:
    no_wait = "--no-wait" in sys.argv[1:]
    return launch(wait=not no_wait)


if __name__ == "__main__":
    sys.exit(main())
