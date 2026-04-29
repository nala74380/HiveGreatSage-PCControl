r"""
文件位置: core/app.py
名称: 应用生命周期管理
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.3
功能及相关说明:
  Application 类，管理 QApplication 创建、配置加载、模块初始化和主流程调度。

改进内容:
  V1.0.3 (2026-04-27) - SyncManager 构造传入 auth_manager；连接 token_expired Signal
                        到 _on_token_expired（主线程重新登录流程）
  V1.0.2 - 注入 TeamManager + 热更新检查流程
  V1.0.1 - 注入 DeviceManager + SyncManager，登录后启动同步
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from core.utils.config import Config
from core.utils.logger import setup_logger
from core.utils.adb_manager import AdbManager
from core.auth.auth_manager import AuthManager
from core.device.device_manager import DeviceManager
from core.sync.sync_manager import SyncManager
from core.team.team_manager import TeamManager

logger = logging.getLogger(__name__)


class Application:
    """PC 中控应用入口。"""

    def __init__(self, argv: list[str]) -> None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self._qt_app = QApplication(argv)

        from game.game_config import WINDOW_TITLE, GAME_VERSION
        self._qt_app.setApplicationName(WINDOW_TITLE)
        self._qt_app.setApplicationVersion(GAME_VERSION)

        # ── 配置 ──────────────────────────────────────────────
        self.config = Config.instance()

        # ── 日志 ──────────────────────────────────────────────
        setup_logger(
            level=self.config.get("log.level", "INFO"),
            max_bytes=int(self.config.get("log.max_file_size_mb", 10)) * 1024 * 1024,
            backup_count=int(self.config.get("log.max_files", 5)),
        )
        logger.info("=" * 60)
        logger.info("%s 启动", WINDOW_TITLE)
        logger.info("=" * 60)
        logger.debug(
            "API: %s  uuid: %s",
            self.config.get("server.api_base_url"),
            self.config.get("server.project_uuid", "")[:8] + "...",
        )

        # ── ADB ───────────────────────────────────────────────
        self.adb = AdbManager()
        if not self.adb.start_server():
            logger.warning(
                "ADB server 启动失败，设备管理功能不可用。"
                "请下载真实的 platform-tools 并解压到 tools/adb/"
            )

        # ── 认证管理器 ────────────────────────────────────────
        self.auth = AuthManager(self.config)

        # ── 设备管理器 ─────────────────────────────────────────
        self.device_manager = DeviceManager(self.config, self.auth)

        # ── 同步管理器 ─────────────────────────────────────────
        self.sync_manager = SyncManager(self.device_manager, self.auth, self.config)

        # ── 组队管理器（WS 服务端，Phase 3）────────────────────
        self.team_manager = TeamManager(self.config)

        # ── 主窗口（延迟创建）────────────────────────────────
        self._main_window = None

    # ─────────────────────────────────────────────────────
    def run(self) -> int:
        # 1. 登录
        if not self._do_login():
            logger.info("用户取消登录，退出")
            return 0

        # 2. 热更新检查（异步，不阻塞主窗口显示）
        if self.config.get("update.check_on_startup", True):
            self._start_update_check()

        # 3. 启动设备同步（连接 token_expired 信号）
        self.sync_manager.worker.token_expired.connect(self._on_token_expired)
        self.sync_manager.start()

        # 4. 启动 WS 服务端（Phase 3）
        self.team_manager.start()

        # 5. 显示主窗口
        self._show_main_window()
        result = self._qt_app.exec()

        # 退出时停止后台服务
        self.sync_manager.stop()
        self.team_manager.stop()
        return result

    # ─────────────────────────────────────────────────────
    def _do_login(self) -> bool:
        from ui.login_window import LoginWindow
        win    = LoginWindow(self.auth)
        result = win.exec()
        return result == QDialog.Accepted

    def _start_update_check(self) -> None:
        """启动后台热更新检查，结果在主窗口显示后通过信号处理。"""
        from core.updater.update_checker import UpdateCheckWorker
        self._update_worker = UpdateCheckWorker(self)
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.start()

    def _on_update_available(self, info) -> None:
        """热更新结果回调（在主线程执行）。"""
        if self._main_window is None:
            return
        from ui.widgets.update_dialog import UpdateDialog
        from core.updater.update_downloader import UpdateDownloadWorker
        from core.updater.update_installer import install_and_restart
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt

        dlg = UpdateDialog(
            new_version=info.new_version,
            current_version=info.current_version,
            release_notes=info.release_notes,
            force_update=info.force_update,
            parent=self._main_window,
        )
        if dlg.exec() != QDialog.Accepted:
            return

        # 显示下载进度
        progress = QProgressDialog("正在下载更新...", "取消", 0, 100, self._main_window)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()

        downloader = UpdateDownloadWorker(self, info)
        downloader.progress.connect(progress.setValue)
        downloader.finished.connect(lambda path: (progress.close(), install_and_restart(path)))
        downloader.failed.connect(lambda msg: (progress.close(), logger.error("下载失败: %s", msg)))
        downloader.start()
        self._download_worker = downloader   # 防 GC

    def _show_main_window(self) -> None:
        from ui.main_window import MainWindow
        self._main_window = MainWindow(self)
        self._main_window.show()
        logger.info("主窗口已显示")

    def _on_token_expired(self) -> None:
        """
        Token 过期且刷新失败的回调（在主线程执行）。

        处理逻辑：
          1. 停止同步，避免持续频繁的 401
          2. 弹出提示对话框，告知用户 Token 已过期
          3. 用户确认后重新执行登录流程
          4. 登录成功则重启同步，登录失败或取消则退出应用

        注意：此方法通过 Qt queued connection 在主线程执行，安全。
        """
        logger.warning("收到 token_expired 信号，停止同步并弹出重新登录")

        # 1. 停止同步
        self.sync_manager.stop()

        # 2. 提示用户
        from PySide6.QtWidgets import QMessageBox
        parent = self._main_window
        msg = QMessageBox(parent)
        msg.setWindowTitle("登录状态已失效")
        msg.setText("您的登录已过期，请重新登录继续使用。")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.exec()

        # 3. 重新登录
        logged_in = self._do_login()
        if not logged_in:
            logger.info("用户取消重新登录，退出应用")
            self._qt_app.quit()
            return

        # 4. 重启同步
        self.sync_manager.start()
        logger.info("重新登录成功，同步已重启")
