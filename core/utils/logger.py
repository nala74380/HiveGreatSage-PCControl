r"""
文件位置: core/utils/logger.py
名称: 日志系统
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  初始化全局日志系统。
  同时输出到控制台和 logs/ 目录下的滚动文件。
  日志格式: 2026-04-27 14:30:25 [INFO] [module] 消息

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
  调试开关: 在 config/local.yaml 中设置 log.level: DEBUG
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path


def setup_logger(
    level: str = "INFO",
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """
    初始化根日志器（全局调用一次）。

    Args:
        level:        日志级别字符串，如 "DEBUG" / "INFO" / "WARNING"
        max_bytes:    单个日志文件最大字节数，默认 10MB
        backup_count: 保留的历史日志文件数量
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ── 控制台处理器 ──────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(numeric_level)

    # ── 滚动文件处理器 ────────────────────
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "pccontrol.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(numeric_level)

    # ── 根日志器 ──────────────────────────
    root = logging.getLogger()
    root.setLevel(numeric_level)
    # 防止重复添加（单元测试场景多次实例化时）
    if not root.handlers:
        root.addHandler(console_handler)
        root.addHandler(file_handler)
