r"""
文件位置: core/app.py
名称: 应用生命周期管理
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-18
版本: V1.4.0
功能及相关说明:
  Application 类，管理 QApplication 创建、配置加载、模块初始化和主流程调度。

改进内容:
  V1.4.0 (2026-05-23)
    - 信号连接改为走 SyncManager 代理信号，不再直接引用 worker。
    - _fetch_user_info_async 移入 QThread，避免主线程阻塞 HTTP。
  V1.3.0 (2026-05-18)
    - 初始化 AdbLinkManager。
    - DeviceManager 改为注入 AdbLinkManager，不再直接接收 AdbManager。
  V1.2.1 (2026-05-18)
    - DeviceManager 构造时注入 AdbManager，用于设备页连接类型/连接标识本地展示。
  V1.2.0 (2026-05-12)
    - 连接 SyncWorker.mock_fallback_used 信号。
    - 当设备列表来自模拟数据时，主线程明确弹窗提示，避免误判为真实 Verify 数据。
  V1.1.0 (2026-05-01)
    - 接入 NetworkConfigManager。
    - 启动时拉取 /api/client/network-config。
    - 支持 last_good_api_url / backup_api_urls 回退。
    - 登录成功后轻量刷新远程网络配置。
    - 远程配置变更后重载 AuthManager / DeviceManager 网络配置。
  V1.0.3 (2026-04-27)
    - SyncManager 构造传入 auth_manager；连接 token_expired Signal。
  V1.0.2 - 注入 TeamManager + 热更新检查流程
  V1.0.1 - 注入 DeviceManager + SyncManager，登录后启动同步
  V1.0.0 - 初始版本
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from core.utils.config import Config
from core.utils.logger import setup_logger
from core.utils.adb_manager import AdbManager
from core.auth.auth_manager import AuthManager
from core.device.adb_link_manager import AdbLinkManager
from core.device.device_manager import DeviceManager
from core.sync.sync_manager import SyncManager
from core.team.team_manager import TeamManager
from core.network.network_config_manager import NetworkConfigManager

logger = logging.getLogger(__name__)


class Application:
    """PC 中控应用入口。"""

    def __init__(self, argv: list[str]) -> None:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        self._qt_app = QApplication(argv)

        from core.utils.constants import APP_VERSION
        from game.game_config import WINDOW_TITLE

        self._qt_app.setApplicationName(WINDOW_TITLE)
        self._qt_app.setApplicationVersion(APP_VERSION)

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

        # ── 网络配置 ───────────────────────────────────────────
        self.network = NetworkConfigManager(self.config)
        network_result = self.network.bootstrap()

        logger.info(
            "网络配置启动检查完成: api=%s source=%s changed=%s msg=%s",
            self.config.get("server.api_base_url"),
            network_result.source,
            network_result.changed,
            network_result.message,
        )

        logger.debug(
            "API: %s  uuid: %s",
            self.config.get("server.api_base_url"),
            self.config.get("server.project_uuid", "")[:8] + "...",
        )

        # -- Auth and lazy runtime placeholders ---------------------------
        # Runtime managers are initialized after login and the update gate.
        self.auth = AuthManager(self.config)
        self.adb = None
        self.adb_links = None
        self.device_manager = None
        self.sync_manager = None
        self.team_manager = None

        # ── 主窗口（延迟创建）────────────────────────────────
        self._main_window = None
        self._switch_old_window = None
        self._pending_mock_fallback_message: str | None = None
        self._runtime_started = False

    # ─────────────────────────────────────────────────────
    def run(self) -> int:
        # 1. 登录
        if not self._try_auto_login() and not self._do_login():
            logger.info("用户取消登录，退出")
            return 0

        # 2. 热更新检查作为登录后的启动门禁；通过后才进入主界面和运行服务。
        if self.config.get("update.check_on_startup", True):
            self._start_update_check()
        else:
            self._enter_main_runtime()

        result = self._qt_app.exec()

        # 退出时停止后台服务
        self._stop_runtime_services()
        return result

    def _enter_main_runtime(self, *args) -> None:
        """Enter the main UI and start services after the update gate passes."""
        if self._main_window is None:
            self._show_main_window()

            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, self._fetch_user_info_async)
            QTimer.singleShot(160, self._show_pending_mock_fallback_notice)
            QTimer.singleShot(200, self._bootstrap_runtime_after_main)
            return

        self._bootstrap_runtime_after_main()

    def _bootstrap_runtime_after_main(self) -> None:
        """Initialize runtime managers after the main shell is already visible."""
        if self._runtime_started:
            return
        if self._main_window is None:
            return
        self._ensure_runtime_managers()
        if self._main_window is not None and hasattr(self._main_window, "attach_runtime_services"):
            self._main_window.attach_runtime_services()
        self._start_runtime_services()

    def _ensure_runtime_managers(self) -> None:
        """Initialize ADB/device/sync/team managers after login and update gate."""
        if self.device_manager is not None:
            return

        self.adb = AdbManager()
        if not self.adb.start_server():
            logger.warning(
                "ADB server 启动失败，设备管理功能不可用。"
                "请下载真实的 platform-tools 并解压到 tools/adb/"
            )

        self.adb_links = AdbLinkManager(self.adb)
        self.device_manager = DeviceManager(self.config, self.auth, self.adb_links)
        self.sync_manager = SyncManager(self.device_manager, self.auth, self.config)
        self.team_manager = TeamManager(self.config)

    def _start_runtime_services(self, *args) -> None:
        """Start post-login runtime services once the update gate has passed."""
        if self._runtime_started:
            return

        self._ensure_runtime_managers()
        if self.sync_manager is None or self.team_manager is None:
            logger.error("运行期管理器初始化失败，无法启动同步服务")
            return

        self.sync_manager.token_expired.connect(self._on_token_expired)
        self.sync_manager.mock_fallback_used.connect(self._on_mock_fallback_used)
        self.sync_manager.start()
        ws_started = self.team_manager.start()
        if not ws_started:
            self.post_status("WS 服务启动失败，请检查 PySide6-Addons 或端口占用。", level="error", timeout_ms=8000)
            logger.error("WS 服务启动失败，运行期未标记为完全启动")
            return

        self._runtime_started = True
        self.post_status(f"WS 服务已启动：{self.team_manager.listen_address}", level="ok", timeout_ms=5000)

    def _stop_runtime_services(self) -> None:
        if self.sync_manager is not None:
            self.sync_manager.stop()
        if self.team_manager is not None:
            self.team_manager.stop()
        self._runtime_started = False

    # ─────────────────────────────────────────────────────
    def _try_auto_login(self) -> bool:
        if not bool(self.config.get("auth.auto_login_enabled", False)):
            return False

        username = self.auth.get_saved_username()
        password = self.auth.get_saved_password(username)
        if not username or not password:
            logger.info("自动登录未执行：未找到已保存账号或系统凭据")
            return False

        logger.info("尝试自动登录: %s", username)
        result = self.auth.login(username, password, remember=True)
        if not result.success:
            logger.warning("自动登录失败: %s", result.error_message)
            return False

        self._refresh_network_config_after_login()
        logger.info("自动登录成功: %s", username)
        return True

    def _do_login(self) -> bool:
        from ui.login_window import LoginWindow

        win = LoginWindow(self.auth)
        result = win.exec()

        if result != QDialog.Accepted:
            return False

        self._refresh_network_config_after_login()
        return True

    def switch_account(self) -> None:
        """切换账号：关闭自动登录并清除已保存凭据，再重新进入登录流程。"""
        logger.info("用户请求切换账号")
        self.config.set_local("auth.auto_login_enabled", False)
        self.auth.forget_saved_credentials()
        self.auth.logout()
        self._stop_runtime_services()

        old_window = self._main_window
        if old_window is not None:
            old_window.hide()
        self._switch_old_window = old_window
        self._main_window = None

        if self._do_login():
            if self.config.get("update.check_on_startup", True):
                self._start_update_check()
            else:
                self._enter_main_runtime()
        else:
            self._qt_app.quit()

    def _refresh_network_config_after_login(self) -> None:
        """
        登录成功后轻量刷新远程 network-config。

        说明:
          - 远程配置接口本身不需要 Token。
          - 这里放在登录成功后再跑一次，是为了让管理员刚保存的网络配置能尽快落到 PC 中控。
          - 如果推荐地址不可用，NetworkConfigManager 会保留旧地址。
        """
        if not bool(self.config.get("network.refresh_after_login", True)):
            return

        try:
            result = self.network.refresh_remote_config()

            if result.changed:
                self.auth.reload_network_config()
                if self.device_manager is not None:
                    self.device_manager.reload_network_config()
                logger.info("登录后网络配置已刷新并应用: %s", result.base_url)
            else:
                logger.debug("登录后网络配置检查完成: %s", result.message)

        except Exception as exc:
            logger.warning("登录后刷新 network-config 失败，继续使用当前地址: %s", exc)

    def _start_update_check(self) -> None:
        """启动后台热更新检查，结果在主窗口显示后通过信号处理。"""
        from core.updater.update_checker import UpdateCheckWorker

        self._update_worker = UpdateCheckWorker(self)
        self._update_worker.update_available.connect(self._on_update_available)
        self._update_worker.no_update.connect(self._enter_main_runtime)
        self._update_worker.check_failed.connect(self._enter_main_runtime)
        self._update_worker.start()

    def _on_update_available(self, info) -> None:
        """热更新结果回调（在主线程执行）。"""
        from ui.widgets.update_dialog import UpdateDialog
        from core.updater.update_downloader import UpdateDownloadWorker
        from core.updater.update_installer import install_and_restart
        from PySide6.QtWidgets import QProgressDialog
        from PySide6.QtCore import Qt

        parent = self._main_window
        dlg = UpdateDialog(
            new_version=info.new_version,
            current_version=info.current_version,
            release_notes=info.release_notes,
            force_update=info.force_update,
            parent=parent,
        )
        if dlg.exec() != QDialog.Accepted:
            if info.force_update:
                logger.warning("强制热更新被取消，退出当前客户端")
                self._qt_app.quit()
                return
            self._enter_main_runtime()
            return

        progress = QProgressDialog("正在下载更新...", "取消", 0, 100, parent)
        progress.setWindowModality(
            Qt.WindowModality.WindowModal if parent else Qt.WindowModality.ApplicationModal
        )
        progress.show()

        def on_download_failed(msg: str) -> None:
            progress.close()
            logger.error("下载失败: %s", msg)
            if info.force_update:
                self._qt_app.quit()
            else:
                self._enter_main_runtime()

        downloader = UpdateDownloadWorker(self, info)
        progress.canceled.connect(downloader.requestInterruption)
        downloader.progress.connect(progress.setValue)
        downloader.finished.connect(lambda path: (progress.close(), install_and_restart(path)))
        downloader.failed.connect(on_download_failed)
        downloader.start()
        self._download_worker = downloader

    def _fetch_user_info_async(self) -> None:
        """后台线程拉取 /api/auth/me，完成后在主线程更新顶部授权统计。"""
        if not self._main_window:
            return

        from PySide6.QtCore import QThread, Signal

        class _FetchWorker(QThread):
            done = Signal()

            def __init__(self, auth):
                super().__init__()
                self._auth = auth

            def run(self):
                try:
                    self._auth.fetch_user_info()
                except Exception as e:
                    logger.warning("后台拉取用户信息失败: %s", e)
                self.done.emit()

        self._fetch_worker = _FetchWorker(self.auth)
        self._fetch_worker.done.connect(self._on_user_info_fetched)
        self._fetch_worker.start()

    def _on_user_info_fetched(self) -> None:
        if self._main_window and hasattr(self._main_window, "update_auth_stats"):
            self._main_window.update_auth_stats()

    def _show_main_window(self) -> None:
        from ui.main_window import MainWindow

        self._main_window = MainWindow(self)
        self._main_window.show()
        if self._switch_old_window is not None:
            self._switch_old_window.close()
            self._switch_old_window = None
        logger.info("主窗口已显示")

    def post_status(self, text: str, level: str = "info", timeout_ms: int = 3500) -> None:
        if self._main_window is not None and hasattr(self._main_window, "post_status"):
            self._main_window.post_status(text, level=level, timeout_ms=timeout_ms)
        else:
            logger.info("状态消息[%s]: %s", level, text)

    def _on_token_expired(self) -> None:
        """
        Token 过期且刷新失败的回调（在主线程执行）。

        处理逻辑：
          1. 停止同步，避免持续频繁的 401。
          2. 弹出提示对话框。
          3. 用户确认后重新执行登录流程。
          4. 登录成功则重启同步，登录失败或取消则退出应用。
        """
        logger.warning("收到 token_expired 信号，停止同步并弹出重新登录")

        if self.sync_manager is not None:
            self.sync_manager.stop()

        from PySide6.QtWidgets import QMessageBox

        QMessageBox.warning(
            self._main_window,
            "登录已过期",
            "登录状态已过期，请重新登录。",
        )

        if self._try_auto_login() or self._do_login():
            if self.sync_manager is not None:
                self.sync_manager.start()
        else:
            self._qt_app.quit()

    def _on_mock_fallback_used(self, msg: str) -> None:
        """SyncWorker 使用模拟设备列表时，在主线程提示用户。"""
        logger.warning("设备列表使用模拟数据: %s", msg)
        self._pending_mock_fallback_message = msg
        self._show_pending_mock_fallback_notice()

    def _show_pending_mock_fallback_notice(self) -> None:
        if not self._main_window or not self._pending_mock_fallback_message:
            return

        from PySide6.QtWidgets import QMessageBox

        msg = self._pending_mock_fallback_message
        self._pending_mock_fallback_message = None
        QMessageBox.warning(
            self._main_window,
            "设备列表数据异常",
            "当前设备列表来自本地模拟数据，不是真实 Verify 数据。\n\n"
            f"原因：{msg}\n\n"
            "请检查 Verify API 地址、Token、设备接口和网络配置。",
        )
