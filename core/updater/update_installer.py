r"""
文件位置: core/updater/update_installer.py
名称: 热更新安装器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  解压下载好的更新包并重启应用。
  安装策略：解压到应用目录，覆盖旧文件，然后 os.execv 重启主进程。
  ⚠️ 打包为 .exe 后此逻辑需要配合外部 launcher（如 bat 脚本）实现覆盖更新。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: .exe 打包后自身文件被占用，无法直接覆盖，需配合 updater.bat
"""

from __future__ import annotations

import logging
import os
import sys
import zipfile
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJ_ROOT = Path(__file__).resolve().parents[2]


def install_and_restart(zip_path: str) -> None:
    """
    解压更新包到应用目录并重启。

    Args:
        zip_path: 下载好的 ZIP 文件路径（由 UpdateDownloadWorker 传入）

    ⚠️ 开发模式（.py）：直接解压覆盖，os.execv 重启解释器。
    ⚠️ 打包模式（.exe）：写出 updater.bat 脚本后退出，由 bat 完成覆盖并重新启动。
    """
    zip_path_obj = Path(zip_path)
    if not zip_path_obj.exists():
        logger.error("更新包不存在: %s", zip_path)
        return

    try:
        logger.info("开始安装更新: %s", zip_path)
        if getattr(sys, "frozen", False):
            # 打包模式：写出辅助批处理脚本，交给它覆盖并重启
            _install_via_bat(zip_path_obj)
        else:
            # 开发模式：直接解压
            _install_direct(zip_path_obj)
    except Exception as e:
        logger.exception("安装更新时发生错误: %s", e)


def _install_direct(zip_path: Path) -> None:
    """开发模式：解压到项目根目录，覆盖旧文件，重启 Python 进程。"""
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(_PROJ_ROOT)
    logger.info("更新解压完成，准备重启...")
    zip_path.unlink(missing_ok=True)
    # 重启当前 Python 进程
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _install_via_bat(zip_path: Path) -> None:
    """
    打包模式：写出 updater.bat 辅助脚本，退出主进程后由 bat 覆盖并重启 exe。
    bat 脚本逻辑：等待主进程退出 → 解压 zip → 启动 exe → 删除自身。
    """
    exe_path = Path(sys.executable)
    bat_path = exe_path.parent / "updater.bat"

    bat_content = f"""@echo off
timeout /t 2 /nobreak > nul
powershell -command "Expand-Archive -Path '{zip_path}' -DestinationPath '{exe_path.parent}' -Force"
del "{zip_path}"
start "" "{exe_path}"
del "%~f0"
"""
    bat_path.write_text(bat_content, encoding="gbk")
    logger.info("已生成 updater.bat，即将退出主进程...")

    import subprocess
    subprocess.Popen(["cmd", "/c", str(bat_path)], creationflags=0x08000008)
    from PySide6.QtWidgets import QApplication
    QApplication.quit()
