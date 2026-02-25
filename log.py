#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单日志模块 - 替换 print，输出到 TXT 文件
"""

import sys
from datetime import datetime
from pathlib import Path


# 日志文件路径
LOG_FILE = Path(__file__).parent / "monitor_log.txt"


def log(*args, **kwargs):
    """
    替换 print 的函数，输出到文件
    
    用法：
        log("消息")  # 替代 print("消息")
    """
    # 构建消息
    msg = " ".join(str(arg) for arg in args)
    
    # 添加时间戳
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    
    # 写入文件（追加模式，立即刷新）
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()


def log_init():
    """初始化日志文件，清空旧内容"""
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 日志启动\n")
        f.flush()


# 初始化
log_init()