r"""
文件位置: core/api_client/client_config_api.py
名称: 客户端配置 API
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-01
版本: V1.0.0
功能及相关说明:
  封装 Verify 客户端公开配置接口。

当前接口:
  GET /api/client/network-config
  GET /health

设计边界:
  1. 该接口不需要用户 Token。
  2. 只返回客户端安全字段。
  3. 不返回家庭服务器内网地址、数据库、Redis、密钥等敏感信息。
"""

from __future__ import annotations

from core.api_client.base_client import BaseClient


class ClientConfigApi(BaseClient):
    """客户端配置 API。"""

    def get_network_config(self) -> dict:
        """
        GET /api/client/network-config

        Returns:
            {
              config_version,
              deployment_mode,
              primary_api_url,
              pc_client_api_url,
              android_client_api_url,
              backup_api_urls,
              timeout_seconds,
              retry_count,
              heartbeat_interval_seconds,
              relay_enabled,
              relay_mode,
              relay_url
            }
        """
        return self.get("/api/client/network-config")

    def health(self) -> dict:
        """
        GET /health

        用于测试当前 base_url 是否为可用 Verify 服务。
        """
        return self.get("/health")