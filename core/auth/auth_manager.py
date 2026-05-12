"""
文件位置: core/auth/auth_manager.py
名称: 认证管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-03
版本: V2.1.0
功能及相关说明:
    PC 中控认证管理器。

    核心职责:
      1. 登录 / 登出 / Token 刷新。
      2. 管理 access_token、refresh_token。
      3. 提供同步接口（可在 QThread 中安全调用）。
      4. 通过系统凭据管理器保存“记住密码”，禁止明文密码写入 local.yaml。

    与 Verify 交互:
      - POST /api/auth/login      — 用户登录
      - POST /api/auth/refresh    — 刷新 Access Token
      - POST /api/auth/logout     — 登出

改进历史:
    V2.1.0 (2026-05-12): 使用 keyring 保存记住密码，并清理历史 saved_password 字段。
    V2.0.0 (2026-05-03): 重建被覆盖的文件。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import keyring

from core.api_client.auth_api import AuthApi
from core.auth.models import LoginResult, UserInfo
from core.utils.config import Config

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "HiveGreatSage-PCControl"


class AuthManager:
    """PC 中控认证管理器（同步，可在 QThread 中调用）。"""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._user_info: UserInfo = UserInfo()
        self._auth_info: dict[str, Any] = {}
        self._api: AuthApi | None = None
        self._saved_username: str = ""
        self._saved_password: str = ""
        self._cleanup_legacy_saved_password()

    @property
    def is_logged_in(self) -> bool:
        return bool(self._access_token)

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def user_info(self) -> UserInfo:
        return self._user_info

    @property
    def auth_info(self) -> dict[str, Any]:
        return self._auth_info

    # ── API 客户端 ──────────────────────────────────────────

    def _get_api(self) -> AuthApi:
        if self._api is None:
            base_url = self._config.get("server.api_base_url", "")
            timeout = float(self._config.get("server.timeout", 15))
            self._api = AuthApi(base_url=base_url, timeout=timeout)
        return self._api

    def _sync_api_token(self) -> None:
        if self._api and self._access_token:
            self._api.set_token(self._access_token)

    # ── 凭据存储 ───────────────────────────────────────────

    def get_saved_username(self) -> str:
        return self._config.get("auth.saved_username", "") or ""

    def get_saved_password(self, username: str) -> str:
        """从系统凭据管理器读取记住密码；不再读取 local.yaml 明文字段。"""
        if not username or username != self.get_saved_username():
            return ""
        try:
            return keyring.get_password(_KEYRING_SERVICE, username) or ""
        except Exception as e:
            logger.warning("读取系统凭据失败: %s", e)
            return ""

    def _save_credentials(self, username: str, password: str) -> None:
        """保存用户名到 local.yaml，保存密码到系统凭据管理器。"""
        self._config.set_local("auth.saved_username", username)
        self._cleanup_legacy_saved_password()
        try:
            keyring.set_password(_KEYRING_SERVICE, username, password)
        except Exception as e:
            logger.warning("保存系统凭据失败: %s", e)

    def _clear_saved_credentials(self) -> None:
        """清理记住登录信息，包括系统凭据与历史明文字段。"""
        username = self.get_saved_username()
        self._config.set_local("auth.saved_username", "")
        self._cleanup_legacy_saved_password()

        if username:
            try:
                keyring.delete_password(_KEYRING_SERVICE, username)
            except Exception as e:
                logger.debug("删除系统凭据失败或凭据不存在: %s", e)

    def _cleanup_legacy_saved_password(self) -> None:
        """清理历史版本曾写入 local.yaml 的 auth.saved_password 明文字段。"""
        if self._config.get("auth.saved_password", None) is None:
            return

        remove_local = getattr(self._config, "remove_local", None)
        if callable(remove_local):
            remove_local("auth.saved_password")
        else:
            logger.warning("当前 Config 不支持 remove_local，无法自动清理 auth.saved_password")

    # ── 登录 ───────────────────────────────────────────────

    def login(self, username: str, password: str,
              remember: bool = False) -> LoginResult:
        """
        同步登录。project_uuid 和 device_fingerprint 从 Config 读取。

        Returns:
            LoginResult with success=True + tokens, or error_message.
        """
        api = self._get_api()

        project_uuid = self._config.get("server.project_uuid", "")
        device_fingerprint = self._read_device_id()

        payload = {
            "username": username,
            "password": password,
            "project_uuid": project_uuid,
            "device_fingerprint": device_fingerprint,
            "client_type": "pc",
        }

        try:
            data = api.login(payload)
        except Exception as e:
            status_code = getattr(e, "status_code", None)
            detail = getattr(e, "detail", str(e))
            logger.warning("登录失败 [%s]: %s", status_code, detail)
            return LoginResult(
                success=False,
                error_message=f"{detail}",
                error_code=str(status_code or ""),
            )

        self._access_token = data.get("access_token", "")
        self._refresh_token = data.get("refresh_token", "")
        self._user_info = UserInfo(
            username=data.get("username", username),
            display_name=data.get("username", username),
            project_uuid=project_uuid,
        )
        self._sync_api_token()

        if remember:
            self._save_credentials(username, password)
        else:
            self._clear_saved_credentials()

        return LoginResult(
            success=True,
            access_token=self._access_token,
            refresh_token=self._refresh_token,
            user_info=self._user_info,
        )

    # ── 用户信息 ──────────────────────────────────────────

    def fetch_user_info(self) -> None:
        """
        从 /api/auth/me 拉取完整授权信息（异步友好，可在 QThread 调用）。
        填充 _user_info 和 _auth_info。
        """
        api = self._get_api()
        try:
            me_data = api.me()
            self._user_info = UserInfo(
                username=self._user_info.username,
                display_name=self._user_info.display_name,
                project_uuid=self._user_info.project_uuid,
                user_level=me_data.get("authorization_level", ""),
                device_quota=int(me_data.get("authorized_devices") or 0),
                expired_at=me_data.get("valid_until") or "",
                activated_devices=int(me_data.get("activated_devices") or 0),
                inactive_devices=me_data.get("inactive_devices"),
            )
            self._auth_info = me_data
        except Exception as e:
            logger.warning("获取 /me 失败: %s", e)

    # ── Token 刷新 ──────────────────────────────────────────

    def refresh_access_token(self) -> bool:
        """刷新 Access Token。成功返回 True，失败返回 False。"""
        if not self._refresh_token:
            logger.warning("refresh_token 为空")
            return False

        api = self._get_api()

        try:
            data = api.refresh_token(self._refresh_token)
        except Exception as e:
            logger.warning("Token 刷新失败: %s", e)
            return False

        new_at = data.get("access_token", "")
        new_rt = data.get("refresh_token", "")

        if not new_at:
            return False

        self._access_token = new_at
        if new_rt:
            self._refresh_token = new_rt
        self._sync_api_token()
        logger.info("Token 刷新成功")
        return True

    # ── 登出 ───────────────────────────────────────────────

    def logout(self) -> None:
        """登出：调用服务端 + 清空本地。"""
        if self._api and self._refresh_token:
            try:
                self._api.logout()
            except Exception as e:
                logger.debug("登出 API 异常（不影响本地清理）: %s", e)

        self._access_token = None
        self._refresh_token = None
        self._user_info = UserInfo()
        self._auth_info = {}
        if self._api:
            self._api.set_token(None)

    # ── 配置更新 ───────────────────────────────────────────

    def reload_network_config(self) -> None:
        """重载 API 客户端（app.py 在网络配置变更后调用）。"""
        base_url = self._config.get("server.api_base_url", "")
        timeout = float(self._config.get("server.timeout", 15))
        self.update_network_config(base_url, timeout)

    def update_network_config(self, base_url: str, timeout: float) -> None:
        """运行时更新 API 客户端配置。"""
        new_api = AuthApi(base_url=base_url, timeout=timeout)
        if self._access_token:
            new_api.set_token(self._access_token)
        self._api = new_api

    # ── 内部 ───────────────────────────────────────────────

    @staticmethod
    def _read_device_id() -> str:
        """从 config/device_id.txt 读取设备指纹。"""
        from core.utils.constants import DEVICE_ID_FILE
        path = Path(__file__).resolve().parents[2] / DEVICE_ID_FILE
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return ""
