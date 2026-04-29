r"""
文件位置: core/api_client/update_api.py
名称: 热更新 API
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  封装与 Verify 系统热更新端点的通信。
  GET /api/update/check    — 检查是否有新版本
  GET /api/update/download — 获取签名限时下载 URL

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

from core.api_client.base_client import BaseClient


class UpdateApi(BaseClient):
    """热更新 API 客户端。"""

    def check(self, current_version: str, client_type: str = "pc") -> dict:
        """
        GET /api/update/check?client_type=pc&current_version=1.0.0
        Returns:
            UpdateCheckResponse dict:
              need_update, current_version, client_type,
              game_project_code, force_update, release_notes, checksum_sha256
        """
        return self.get(
            "/api/update/check",
            params={"client_type": client_type, "current_version": current_version},
        )

    def get_download_url(self, client_type: str = "pc") -> dict:
        """
        GET /api/update/download?client_type=pc
        Returns:
            UpdateDownloadResponse dict:
              download_url, expires_at, version, checksum_sha256
        """
        return self.get("/api/update/download", params={"client_type": client_type})
