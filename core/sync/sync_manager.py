r"""
文件位置: core/sync/sync_manager.py
名称: 数据同步管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V2.0.0
功能及相关说明:
  管理 SyncWorker 的生命周期（启动/停止/暂停/恢复）。

  V2.0.0 设计变更：
    - SyncManager 改为 QObject 子类，自持代理 Signal。
    - 外部代码（app.py / main_window.py）统一连接 SyncManager 的信号，
      不直接持有 worker 引用，避免 worker 重建后信号连接失效。
    - start() 在 worker 已终止时安全重建新 worker 实例。
    - 提供 request_immediate_sync()，供 UI 主动触发一次同步。

  典型用法：
    app.sync_manager.start()                               # 登录成功后启动
    app.sync_manager.devices_updated.connect(...)          # 主窗口连接
    app.sync_manager.token_expired.connect(...)            # app.py 连接，处理重新登录
    app.sync_manager.stop()                                # 退出时停止
    app.sync_manager.request_immediate_sync()              # UI 刷新按钮触发

改进内容:
  V2.0.0 (2026-05-23) - 改为 QObject 代理信号；start() 安全重建 worker；
                        新增 request_immediate_sync()。
  V1.0.1 (2026-04-27) - 构造函数新增 auth_manager 参数，传递给 SyncWorker。
  V1.0.0 - 初始版本
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from core.sync.sync_worker import SyncWorker

if TYPE_CHECKING:
    from core.auth.auth_manager import AuthManager
    from core.device.device_manager import DeviceManager
    from core.utils.config import Config

logger = logging.getLogger(__name__)


class SyncManager(QObject):
    """
    管理 SyncWorker 生命周期，对外暴露代理 Signal。

    外部代码始终连接本类的 Signal，不直接引用 worker，
    因此 worker 重建后外部连接自动保持有效。
    """

    # 代理 SyncWorker 的全部信号
    devices_updated    = Signal(object)   # list[DeviceInfo]
    sync_error         = Signal(str)
    token_expired      = Signal()
    mock_fallback_used = Signal(str)

    def __init__(
        self,
        device_manager: "DeviceManager",
        auth_manager: "AuthManager",
        config: "Config",
        parent: "QObject | None" = None,
    ) -> None:
        super().__init__(parent)
        self._device_manager = device_manager
        self._auth_manager   = auth_manager
        self._interval       = int(config.get("sync.interval", 10))
        self._running        = False
        self.worker          = self._make_worker()

    # ── 内部 worker 工厂 ─────────────────────────────────────────

    def _make_worker(self) -> SyncWorker:
        worker = SyncWorker(
            device_manager=self._device_manager,
            auth_manager=self._auth_manager,
            interval_sec=self._interval,
        )
        self._connect_worker(worker)
        return worker

    def _connect_worker(self, worker: SyncWorker) -> None:
        worker.devices_updated.connect(self.devices_updated)
        worker.sync_error.connect(self.sync_error)
        worker.token_expired.connect(self.token_expired)
        worker.mock_fallback_used.connect(self.mock_fallback_used)

    def _disconnect_worker(self, worker: SyncWorker) -> None:
        """断开 worker 到本 manager 的中继连接，忽略已销毁的情况。"""
        try:
            worker.devices_updated.disconnect(self.devices_updated)
            worker.sync_error.disconnect(self.sync_error)
            worker.token_expired.disconnect(self.token_expired)
            worker.mock_fallback_used.disconnect(self.mock_fallback_used)
        except RuntimeError:
            pass

    # ── 生命周期 ─────────────────────────────────────────────────

    def start(self) -> None:
        """
        启动后台同步线程。

        幂等：已在运行时直接返回。
        安全重建：worker 已终止（terminate 或正常退出）时，重建新 worker 再启动，
        避免对已终止的 QThread 调用 start() 导致 undefined behavior。
        """
        if self._running and self.worker.isRunning():
            return

        if not self.worker.isRunning():
            self._disconnect_worker(self.worker)
            self.worker = self._make_worker()
            logger.debug("SyncWorker 已重建（上一个实例已终止）")

        self.worker.start()
        self._running = True
        logger.info("SyncManager 已启动")

    def stop(self) -> None:
        """停止后台同步线程，最多等待 5 秒，超时后强制终止。"""
        if not self._running:
            return
        self.worker.requestInterruption()
        if not self.worker.wait(5000):
            logger.warning("SyncWorker 未在 5s 内退出，强制终止")
            self.worker.terminate()
            self.worker.wait(1000)
        self._running = False
        logger.info("SyncManager 已停止")

    def pause(self) -> None:
        self.stop()

    def resume(self) -> None:
        self.start()

    def request_immediate_sync(self) -> None:
        """通知 worker 跳出当前等待，在下个 100ms 检查点立即触发一次同步。"""
        if self.worker.isRunning():
            self.worker.request_immediate_sync()
            logger.debug("SyncManager: 已请求立即同步")

    @property
    def is_running(self) -> bool:
        return self._running and self.worker.isRunning()
