# -*- coding: utf-8 -*-
"""方块染色解谜 · 无控制台一键启动(双击本文件即可开始游戏)。

替代旧 启动游戏.bat:.pyw 通过 pythonw 运行,启动时不再弹出黑色
命令框。启动逻辑:把项目虚拟环境 .venv(内含 pygame-ce)和 src 目录
加入模块路径后运行游戏;若出错,把错误写入同目录"启动错误.log",
便于排查(双击没反应时先看这个日志)。
"""
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
VENV_SP = os.path.normpath(os.path.join(BASE, "..", ".venv",
                                        "Lib", "site-packages"))
SRC = os.path.join(BASE, "src")

for p in (VENV_SP, SRC):
    if p not in sys.path:
        sys.path.insert(0, p)
os.chdir(BASE)

import main  # noqa: E402,F401  导入游戏主模块


def _log_error():
    import traceback
    log = os.path.join(BASE, "启动错误.log")
    try:
        with open(log, "a", encoding="utf-8") as f:
            f.write("=" * 40 + "\n")
            traceback.print_exc(file=f)
    except OSError:
        pass


try:
    main.main()
except SystemExit:
    raise
except Exception:
    _log_error()
    raise SystemExit(1)
