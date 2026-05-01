r"""
文件位置: core/api_client/base_client.py
名称: 云端 API 基础客户端
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-01
版本: V1.1.0
功能及相关说明:
  封装 httpx.Client，提供统一的请求入口、超时控制、通用错误处理和鉴权头注入。
  所有上层 API 模块（auth_api、device_api、update_api、client_config_api 等）继承此类。

  ⚠️ 本客户端为同步版本，必须在 QThread 中调用，禁止在 UI 主线程执行重网络请求。

改进内容:
  V1.1.0 - 增加 configure()/set_base_url()/set_timeout()，支持运行时重载网络配置。
  V1.0.0 - 初始版本
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ApiError(Exception):
    """API 调用异常，封装了 HTTP 状态码和服务端错误信息。"""

    def __init__(self, status_code: int, detail: str, error_code: str = "") -> None:
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(f"[{status_code}] {detail}")


class BaseClient:
    """
    同步 HTTP 客户端基类。

    子类示例：
        class AuthApi(BaseClient):
            def login(self, payload: dict) -> dict:
                return self.post("/api/auth/login", json=payload)
    """

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._token: str | None = None

    @property
    def base_url(self) -> str:
        """当前 API 基础地址。"""
        return self._base_url

    @property
    def timeout(self) -> float:
        """当前请求超时时间。"""
        return self._timeout

    def configure(
        self,
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> None:
        """
        运行时更新网络配置。

        用途:
          - PC 中控启动后读取 /api/client/network-config。
          - 网络配置可用时更新 AuthApi / DeviceApi / UpdateApi 等客户端。
        """
        if base_url is not None:
            self.set_base_url(base_url)

        if timeout is not None:
            self.set_timeout(timeout)

    def set_base_url(self, base_url: str) -> None:
        """设置 API 基础地址。"""
        new_base_url = (base_url or "").rstrip("/")

        if not new_base_url:
            logger.warning("忽略空 base_url")
            return

        if new_base_url != self._base_url:
            logger.info("API base_url 已更新: %s -> %s", self._base_url, new_base_url)

        self._base_url = new_base_url

    def set_timeout(self, timeout: float) -> None:
        """设置请求超时时间。"""
        try:
            timeout_value = float(timeout)
        except Exception:
            logger.warning("非法 timeout=%s，忽略", timeout)
            return

        if timeout_value <= 0:
            logger.warning("非法 timeout=%s，忽略", timeout)
            return

        self._timeout = timeout_value

    # ── Token 注入 ─────────────────────────
    def set_token(self, token: str | None) -> None:
        """注入 Bearer Token，后续请求自动携带。"""
        self._token = token

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    # ── 核心请求方法 ───────────────────────
    def request(self, method: str, path: str, **kwargs: Any) -> dict:
        """
        发起 HTTP 请求，返回解析后的 JSON 字典。

        Raises:
            ApiError:                HTTP 状态码非 2xx 时抛出
            httpx.TimeoutException:  请求超时
            httpx.RequestError:      网络连接错误
        """
        if not self._base_url:
            raise httpx.RequestError("API base_url 为空")

        url = f"{self._base_url}{path}"
        headers = {**self._build_headers(), **kwargs.pop("headers", {})}

        logger.debug("API %s %s", method, path)
        try:
            resp = httpx.request(
                method,
                url,
                headers=headers,
                timeout=self._timeout,
                **kwargs,
            )
        except httpx.TimeoutException:
            logger.error("API 超时: %s %s", method, path)
            raise
        except httpx.RequestError as e:
            logger.error("API 网络错误: %s %s — %s", method, path, e)
            raise

        if not resp.is_success:
            try:
                body = resp.json()
                detail = body.get("detail", resp.text)
                error_code = body.get("error_code", "")
            except Exception:
                detail = resp.text
                error_code = ""
            logger.warning("API 错误 %d: %s %s — %s", resp.status_code, method, path, detail)
            err = ApiError(resp.status_code, detail, error_code)
            assert hasattr(err, "status_code"), "ApiError 必须有 status_code 属性"
            raise err

        try:
            return resp.json()
        except Exception:
            return {}

    # ── 快捷方法 ───────────────────────────
    def get(self, path: str, **kwargs: Any) -> dict:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> dict:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> dict:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> dict:
        return self.request("DELETE", path, **kwargs)