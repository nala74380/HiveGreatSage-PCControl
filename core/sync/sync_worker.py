r"""
文件位置: core/sync/sync_worker.py
名称: 数据同步工作线程
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-22
版本: V1.2.0
功能及相关说明:
  在独立 QThread 中每 10 秒向 Verify API 拉取设备列表，
  通过 Signal 将结果传回主线程（UI 层）更新设备表格。

  401 处理流程：
    1. fetch_devices() 抛出含 status_code=401 的异常
    2. 在工作线程中调用 auth_manager.refresh_access_token()
    3. 刷新成功 → 立即用新 Token 重试一次 fetch
    4. 刷新失败 → emit token_expired Signal，主线程弹出重新登录

  Mock fallback 边界：
    1. 生产默认禁止 mock fallback。
    2. 只有 config/local.yaml 显式配置 debug.allow_mock_fallback=true 时才允许。
    3. 默认还要求 server.api_base_url 指向 127.0.0.1 或 localhost。
    4. 使用 mock fallback 时会 emit mock_fallback_used，UI/日志必须明确提示。

  立即同步：
    - request_immediate_sync() 设置 _sync_now 标志，主循环在下一个 100ms 检查点
      跳出等待直接触发同步，由 SyncManager 代理调用，不暴露给 UI 层直接访问。

改进内容:
  V1.2.0 (2026-05-23) - 新增 request_immediate_sync() + _sync_now 标志，支持 UI 主动触发同步。
  V1.1.1 (2026-05-22) - 修复：刷新后仍401时清除过期Token，避免下次同步继续使用
  V1.1.0 (2026-05-12) - mock fallback 改为显式配置开关，并增加 mock_fallback_used 信号。
  V1.0.2 (2026-04-28) - _do_sync 改为单一 except + getattr 属性检测，根本解决
                        类身份问题导致的 401 无法捕获；_handle_401 同样修改
  V1.0.1 (2026-04-27) - 注入 auth_manager，修复 Signal 未连接问题
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Signal

if TYPE_CHECKING:
    from core.device.device_manager import DeviceManager
    from core.auth.auth_manager import AuthManager

logger = logging.getLogger(__name__)


class SyncWorker(QThread):
    """
    设备数据同步线程。

    Signals:
        devices_updated(list[DeviceInfo]): 成功拉取后触发，传递设备列表
        sync_error(str):                   拉取失败时触发，传递错误描述
        token_expired():                   AT 过期且刷新失败，通知主线程重新登录
        mock_fallback_used(str):           开发模式启用模拟数据时触发，传递提示说明
    """

    devices_updated    = Signal(object)    # list[DeviceInfo]
    sync_error         = Signal(str)
    token_expired      = Signal()
    mock_fallback_used = Signal(str)

    def __init__(
        self,
        device_manager: "DeviceManager",
        auth_manager: "AuthManager",
        interval_sec: int = 10,
    ) -> None:
        super().__init__()
        self._device_manager = device_manager
        self._auth           = auth_manager
        self._interval_sec   = interval_sec
        self._mock_notice_emitted = False
        self._sync_now       = False

    def request_immediate_sync(self) -> None:
        """由 SyncManager 代理调用，标记下个等待检查点立即触发同步。线程安全。"""
        self._sync_now = True

    # ── 主循环 ──────────────────────────────────────────────────

    def run(self) -> None:
        logger.info("SyncWorker 启动，立即拉取 Verify 设备列表，后续同步间隔 %ds", self._interval_sec)

        while not self.isInterruptionRequested():
            self._sync_now = False
            self._do_sync()
            total_ms = self._interval_sec * 1000
            slept    = 0
            while slept < total_ms and not self.isInterruptionRequested() and not self._sync_now:
                self.msleep(100)
                slept += 100

        logger.info("SyncWorker 已停止")

    # ── 单次同步 ────────────────────────────────────────────────

    def _do_sync(self) -> None:
        """
        执行一次设备列表拉取。

        异常处理策略（V1.0.2）：
          使用单一 except Exception + getattr 属性检测，不依赖类型匹配。
          这样无论 ApiError 被哪条 import 路径创建，都能正确识别 HTTP 错误码。
        """
        try:
            devices = self._device_manager.fetch_devices()
            self.devices_updated.emit(devices)

        except Exception as e:
            status_code = getattr(e, "status_code", None)

            # ── HTTP 401：Token 过期，尝试刷新 ──────────────────
            if status_code == 401:
                self._handle_401()
                return

            # ── 其他 HTTP 错误码 ─────────────────────────────────
            if status_code is not None:
                detail = getattr(e, "detail", str(e))
                self.sync_error.emit(f"设备列表拉取失败 [{status_code}]: {detail}")
                return

            # ── 网络层错误或未知异常 ─────────────────────────────
            if self._is_mock_fallback_allowed():
                self._try_mock_fallback(e)
            else:
                logger.exception("SyncWorker 同步异常，mock fallback 未启用")
                self.sync_error.emit(f"同步异常: {e}")

    # ── 401 处理 ─────────────────────────────────────────────────

    def _handle_401(self) -> None:
        """
        处理 AT 过期（HTTP 401）。

        1. 调用 auth_manager.refresh_access_token()（同步，可在工作线程调用）
        2. 刷新成功 → 立即重试 fetch
        3. 刷新失败 → emit token_expired，由主线程弹出重新登录
        """
        logger.info("AT 过期，尝试刷新 Token...")

        refreshed = self._auth.refresh_access_token()
        if not refreshed:
            logger.warning("Token 刷新失败，通知主线程重新登录")
            self.token_expired.emit()
            return

        logger.info("Token 刷新成功，立即重试 fetch")
        try:
            devices = self._device_manager.fetch_devices()
            self.devices_updated.emit(devices)

        except Exception as retry_e:
            status_code = getattr(retry_e, "status_code", None)
            if status_code == 401:
                # 刷新后仍 401：账号被踢出或服务端异常
                logger.warning("刷新后仍然 401，清除Token并通知主线程重新登录")
                self._auth.clear_tokens()  # 清除过期Token，避免下次同步继续使用
                self.token_expired.emit()
            elif status_code is not None:
                detail = getattr(retry_e, "detail", str(retry_e))
                self.sync_error.emit(f"Token 刷新后 fetch 仍失败 [{status_code}]: {detail}")
            else:
                self.sync_error.emit(f"Token 刷新后 fetch 异常: {retry_e}")

    # ── 辅助 ─────────────────────────────────────────────────────

    def _is_local_api_url(self) -> bool:
        """判断 API 地址是否为本机开发地址。"""
        base_url = self._device_manager._config.get("server.api_base_url", "") or ""
        base_url = base_url.lower()
        return "127.0.0.1" in base_url or "localhost" in base_url

    def _is_mock_fallback_allowed(self) -> bool:
        """
        判断是否允许 mock fallback。

        生产安全边界：
          - 必须显式配置 debug.allow_mock_fallback=true。
          - 默认要求 API 地址为本机开发地址。
        """
        cfg = self._device_manager._config
        allow_mock = bool(cfg.get("debug.allow_mock_fallback", False))
        require_local = bool(cfg.get("debug.require_local_api_for_mock", True))

        if not allow_mock:
            return False
        if require_local and not self._is_local_api_url():
            logger.warning(
                "已配置 allow_mock_fallback=true，但 API 地址不是本机地址，拒绝启用 mock fallback"
            )
            return False
        return True

    def _try_mock_fallback(self, cause: Exception) -> None:
        """开发模式连接失败时降级为模拟数据，并显式通知 UI/日志。"""
        try:
            from core.debug.mock_devices import generate_mock_devices
            devices = generate_mock_devices()
            message = (
                "开发模式：Verify API 不可用，当前设备列表来自模拟数据，"
                "不得用于生产验收或真实联调。"
            )
            logger.warning("SyncWorker 启用 mock fallback: cause=%s devices=%d", cause, len(devices))
            if not self._mock_notice_emitted:
                self.mock_fallback_used.emit(message)
                self._mock_notice_emitted = True
            self.devices_updated.emit(devices)
        except Exception as mock_err:
            logger.warning("SyncWorker: 模拟数据生成失败: %s", mock_err)
            self.sync_error.emit("开发模式：无法连接服务器，模拟数据也加载失败")
