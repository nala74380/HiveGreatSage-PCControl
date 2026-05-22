"""
PC 中控守护启动器。

用途:
  - 通过本脚本启动 main.py。
  - main.py 正常退出时不重启。
  - main.py 异常退出且 runtime.restart_on_crash=true 时，等待配置秒数后重启。
"""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "watchdog.log"

sys.path.insert(0, str(ROOT))

from core.utils.config import Config  # noqa: E402


def _setup_logger() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("pccontrol_watchdog")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(handler)
    return logger


def _runtime_config() -> tuple[bool, int]:
    Config._instance = None
    cfg = Config.instance()
    enabled = bool(cfg.get("runtime.restart_on_crash", False))
    delay = int(cfg.get("runtime.restart_delay_seconds", 5) or 5)
    return enabled, max(delay, 3)


def main() -> int:
    logger = _setup_logger()
    logger.info("watchdog 启动: %s", MAIN)

    while True:
        restart_on_crash, restart_delay = _runtime_config()
        proc = subprocess.Popen([sys.executable, str(MAIN)], cwd=str(ROOT))
        logger.info("PC 中控进程已启动: pid=%s restart_on_crash=%s", proc.pid, restart_on_crash)

        code = proc.wait()
        logger.info("PC 中控进程退出: pid=%s code=%s", proc.pid, code)

        restart_on_crash, restart_delay = _runtime_config()
        if code == 0:
            logger.info("检测到正常退出，watchdog 结束")
            return 0
        if not restart_on_crash:
            logger.info("检测到异常退出，但自动重启未启用，watchdog 结束")
            return code

        logger.warning("%s 秒后自动重启 PC 中控", restart_delay)
        time.sleep(restart_delay)


if __name__ == "__main__":
    raise SystemExit(main())
