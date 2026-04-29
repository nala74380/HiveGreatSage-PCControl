r"""
文件位置: core/sync/sync_manager.py
名称: 数据同步管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.1
功能及相关说明:
  管理 SyncWorker 的生命周期（启动/停止/暂停/恢复）。
  由 Application 持有，主窗口连接 worker 的信号来刷新 UI。

  典型用法：
    app.sync_manager.start()                              # 登录成功后启动
    app.sync_manager.worker.devices_updated.connect(...)  # 主窗口连接
    app.sync_manager.worker.token_expired.connect(...)    # app.py 连接，处理重新登录
    app.sync_manager.stop()                               # 退出时停止

改进内容:
  V1.0.1 (2026-04-27) - 构造函数新增 auth_manager 参数，传递给 SyncWorker
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.sync.sync_worker import SyncWorker

if TYPE_CHECKING:
    from core.auth.auth_manager import AuthManager
    from core.device.device_manager import DeviceManager
    from core.utils.config import Config

logger = logging.getLogger(__name__)


class SyncManager:
    """管理 SyncWorker 生命周期。"""

    def __init__(
        self,
        device_manager: "DeviceManager",
        auth_manager: "AuthManager",
        config: "Config",
    ) -> None:
        interval = int(config.get("sync.interval", 10))
        self.worker = SyncWorker(
            device_manager=device_manager,
            auth_manager=auth_manager,
            interval_sec=interval,
        )
        self._running = False

    # ── 生命周期 ─────────────────────────────────────────────────

    def start(self) -> None:
        """启动后台同步线程（幂等，重复调用无副作用）。"""
        if self._running and self.worker.isRunning():
            return
        self.worker.start()
        self._running = True
        logger.info("SyncManager 已启动")

    def stop(self) -> None:
        """停止后台同步线程，最多等待 5 秒。"""
        if not self._running:
            return
        self.worker.requestInterruption()
        if not self.worker.wait(5000):
            logger.warning("SyncWorker 未在 5s 内退出，强制终止")
            self.worker.terminate()
        self._running = False
        logger.info("SyncManager 已停止")

    def pause(self) -> None:
        """暂停：停止线程，下次 start() 时重新创建（简单实现，适合低频需求）。"""
        self.stop()

    def resume(self) -> None:
        """恢复同步。"""
        self.start()

    @property
    def is_running(self) -> bool:
        return self._running and self.worker.isRunning()
