r"""
文件位置: core/api_client/device_api.py
名称: 设备管理 API
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  封装与 Verify 系统设备端点的通信。
  GET /api/device/list  — 拉取当前用户所有设备状态
  GET /api/device/data  — 拉取单台设备详情

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

from core.api_client.base_client import BaseClient


class DeviceApi(BaseClient):
    """设备 API 客户端。"""

    def get_device_list(self) -> dict:
        """
        GET /api/device/list
        需要 Authorization 头（Bearer AT）。

        Returns:
            DeviceListResponse dict:
                devices: list[DeviceStatus]
                total: int
                online_count: int
        """
        return self.get("/api/device/list")

    def get_device_data(self, device_fingerprint: str) -> dict:
        """
        GET /api/device/data?device_fingerprint=...
        拉取单台设备运行数据详情。

        Returns:
            DeviceDataResponse dict:
                device_id, user_id, status, last_seen, game_data,
                is_online, source(redis/database/not_found)
        """
        return self.get("/api/device/data", params={"device_fingerprint": device_fingerprint})
