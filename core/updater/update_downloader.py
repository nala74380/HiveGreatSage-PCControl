r"""
文件位置: core/updater/update_downloader.py
名称: 热更新下载器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  在 QThread 中下载更新包，通过 Signal 报告进度。
  下载完成后校验 SHA-256，通过后通知安装器。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import hashlib
import logging
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from core.updater.update_checker import UpdateInfo
    from core.app import Application

logger = logging.getLogger(__name__)


class UpdateDownloadWorker(QThread):
    """
    下载更新包到临时目录。

    Signals:
        progress(int):       下载进度 0~100
        finished(str):       下载并校验成功，传递本地文件路径
        failed(str):         下载失败错误描述
    """

    progress = Signal(int)
    finished = Signal(str)    # local file path
    failed   = Signal(str)

    def __init__(self, app: "Application", update_info: "UpdateInfo") -> None:
        super().__init__()
        self._app  = app
        self._info = update_info

    def run(self) -> None:
        from core.api_client.update_api import UpdateApi

        api = UpdateApi(
            base_url=self._app.config.get("server.api_base_url", ""),
            timeout=60.0,   # 下载可能较慢，超时设大
        )
        api.set_token(self._app.auth.access_token)

        # 1. 获取下载链接
        try:
            data         = api.get_download_url(client_type="pc")
            download_url = data.get("download_url", "")
            expected_sha = data.get("checksum_sha256") or self._info.checksum_sha256
        except Exception as e:
            logger.error("获取下载地址失败: %s", e)
            self.failed.emit(f"获取下载地址失败: {e}")
            return

        if not download_url:
            self.failed.emit("服务端未返回下载地址")
            return

        # 2. 下载到临时文件
        tmp_path = Path(tempfile.gettempdir()) / f"hgs_update_{self._info.new_version}.zip"
        try:
            with httpx.stream("GET", download_url, follow_redirects=True) as resp:
                resp.raise_for_status()
                total = int(resp.headers.get("content-length", 0))
                downloaded = 0
                sha256 = hashlib.sha256()

                with open(tmp_path, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        if self.isInterruptionRequested():
                            self.failed.emit("下载已取消")
                            return
                        f.write(chunk)
                        sha256.update(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(int(downloaded * 100 / total))

        except Exception as e:
            logger.error("下载更新包失败: %s", e)
            self.failed.emit(f"下载失败: {e}")
            return

        # 3. 校验 SHA-256
        if expected_sha:
            actual_sha = sha256.hexdigest()
            if actual_sha.lower() != expected_sha.lower():
                tmp_path.unlink(missing_ok=True)
                msg = f"校验失败（期望 {expected_sha[:12]}...，实际 {actual_sha[:12]}...）"
                logger.error("更新包 %s", msg)
                self.failed.emit(msg)
                return

        self.progress.emit(100)
        logger.info("更新包下载完成: %s", tmp_path)
        self.finished.emit(str(tmp_path))
