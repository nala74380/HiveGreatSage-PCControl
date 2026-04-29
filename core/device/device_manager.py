r"""
文件位置: core/device/device_manager.py
名称: 设备管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  聚合 Verify API 数据、本地元数据、ADB 连接状态，提供统一的设备列表。

  本地元数据存储在 config/device_meta.json：
    {
      "<fingerprint>": {
        "alias": "A-001",
        "role": "captain",
        "note": "",
        "activated": false
      }
    }

  调用关系：
    SyncWorker → DeviceManager.fetch_devices() → DeviceApi.get_device_list()
    UI 层       → DeviceManager.update_meta()   → 写入 device_meta.json

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

import httpx

from core.api_client.device_api import DeviceApi
from core.api_client.base_client import ApiError
from core.device.models import DeviceInfo

if TYPE_CHECKING:
    from core.utils.config import Config
    from core.auth.auth_manager import AuthManager

logger = logging.getLogger(__name__)

_PROJ_ROOT     = Path(__file__).resolve().parents[2]
_META_FILE     = _PROJ_ROOT / "config" / "device_meta.json"


class DeviceManager:
    """
    设备列表管理，负责 API 拉取 + 本地元数据合并 + ADB 状态注入。

    线程安全说明：
        fetch_devices() 由 SyncWorker（工作线程）调用。
        update_meta() 由 UI 线程通过 Signal→Slot 间接触发，
        实际写文件操作在 UI 线程中，不存在并发写问题。
    """

    def __init__(self, config: "Config", auth: "AuthManager") -> None:
        self._config = config
        self._auth   = auth
        self._api    = DeviceApi(
            base_url=config.get("server.api_base_url", ""),
            timeout=float(config.get("server.timeout", 15)),
        )
        self._meta: dict[str, dict] = {}
        self._load_meta()

    # ── 公开接口 ─────────────────────────────────

    def fetch_devices(self) -> list[DeviceInfo]:
        """
        从 Verify API 拉取设备列表，合并本地元数据后返回。
        由 SyncWorker 在工作线程中定时调用。

        Raises:
            ApiError:               HTTP 错误（含 401 Token 过期）
            httpx.RequestError:     网络错误
        """
        # 确保 API 客户端携带最新 AT
        self._api.set_token(self._auth.access_token)

        data = self._api.get_device_list()
        devices_raw: list[dict] = data.get("devices", [])

        devices: list[DeviceInfo] = []
        for raw in devices_raw:
            fp   = raw.get("device_id", "")
            meta = self._meta.get(fp, {})
            dev  = DeviceInfo.from_api(raw, meta)
            devices.append(dev)

        logger.debug(
            "设备列表拉取完成: %d 台 (在线 %d)",
            len(devices),
            sum(1 for d in devices if d.is_online),
        )
        return devices

    def update_meta(
        self,
        fingerprint: str,
        alias: str = "",
        role: str  = "",
        note: str  = "",
        activated: bool | None = None,
    ) -> None:
        """
        更新单台设备的本地元数据并持久化到 device_meta.json。
        由 UI 线程调用（设备编辑弹窗保存时）。
        """
        entry = self._meta.setdefault(fingerprint, {})
        if alias:
            entry["alias"] = alias
        if role:
            entry["role"] = role
        # note 允许清空
        entry["note"] = note
        if activated is not None:
            entry["activated"] = activated
        self._save_meta()
        logger.debug("设备元数据更新: %s → %s", fingerprint[:12], entry)

    def get_meta(self, fingerprint: str) -> dict:
        """返回单台设备的本地元数据字典（不存在时返回空 dict）。"""
        return dict(self._meta.get(fingerprint, {}))

    # ── 内部方法 ─────────────────────────────────

    def _load_meta(self) -> None:
        if _META_FILE.exists():
            try:
                with open(_META_FILE, encoding="utf-8") as f:
                    self._meta = json.load(f)
                logger.debug("已加载设备元数据: %d 条", len(self._meta))
            except Exception as e:
                logger.warning("加载 device_meta.json 失败: %s，使用空数据", e)
                self._meta = {}
        else:
            self._meta = {}

    def _save_meta(self) -> None:
        _META_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(_META_FILE, "w", encoding="utf-8") as f:
                json.dump(self._meta, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存 device_meta.json 失败: %s", e)
