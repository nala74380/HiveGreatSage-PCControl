r"""
文件位置: core/updater/update_checker.py
名称: 热更新检查器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  启动时检查是否有新版本。
  在 QThread 中调用 UpdateApi.check()，结果通过 Signal 返回主线程。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    """版本检查结果。"""
    need_update:     bool  = False
    force_update:    bool  = False
    new_version:     str   = ""
    current_version: str   = ""
    release_notes:   str   = ""
    checksum_sha256: str   = ""


class UpdateCheckWorker(QThread):
    """
    在后台线程检查是否有新版本。

    Signals:
        update_available(UpdateInfo): 有新版本时触发
        no_update():                  已是最新版本
        check_failed(str):            检查失败（网络错误等）
    """

    update_available = Signal(object)   # UpdateInfo
    no_update        = Signal()
    check_failed     = Signal(str)

    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app

    def run(self) -> None:
        from core.api_client.update_api import UpdateApi
        from core.utils.constants import APP_VERSION

        api = UpdateApi(
            base_url=self._app.config.get("server.api_base_url", ""),
            timeout=float(self._app.config.get("server.timeout", 15)),
        )
        api.set_token(self._app.auth.access_token)

        try:
            data = api.check(current_version=APP_VERSION, client_type="pc")
        except Exception as e:
            logger.warning("热更新检查失败: %s（跳过）", e)
            self.check_failed.emit(str(e))
            return

        if not data.get("need_update"):
            logger.info("热更新: 已是最新版本 %s", APP_VERSION)
            self.no_update.emit()
            return

        info = UpdateInfo(
            need_update     = True,
            force_update    = data.get("force_update", False),
            new_version     = str(data.get("current_version", "")),
            current_version = APP_VERSION,
            release_notes   = data.get("release_notes") or "",
            checksum_sha256 = data.get("checksum_sha256") or "",
        )
        logger.info(
            "热更新: 发现新版本 %s（force=%s）",
            info.new_version, info.force_update,
        )
        self.update_available.emit(info)
