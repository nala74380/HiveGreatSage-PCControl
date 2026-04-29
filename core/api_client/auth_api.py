r"""
文件位置: core/api_client/auth_api.py
名称: 认证相关 API
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  封装与网络验证系统 auth 端点的通信。
  对应接入契约中的登录、Token 刷新、登出接口。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

from core.api_client.base_client import BaseClient


class AuthApi(BaseClient):
    """认证 API 客户端。"""

    def login(self, payload: dict) -> dict:
        """
        POST /api/auth/login

        Args:
            payload: 符合接入契约的登录请求体（含 device_identity）

        Returns:
            服务端返回的 JSON 字典（access_token, refresh_token, user 等）

        Raises:
            ApiError: 登录失败（401/403/422 等）
            httpx.TimeoutException / httpx.RequestError: 网络问题
        """
        return self.post("/api/auth/login", json=payload)

    def refresh_token(self, refresh_token: str) -> dict:
        """
        POST /api/auth/refresh
        无需 Authorization 头，用 refresh_token 换新 access_token。
        """
        return self.post("/api/auth/refresh", json={"refresh_token": refresh_token})

    def logout(self) -> dict:
        """POST /api/auth/logout（需要 Authorization 头）。"""
        return self.post("/api/auth/logout")

    def me(self) -> dict:
        """GET /api/auth/me — 获取当前用户信息。"""
        return self.get("/api/auth/me")
