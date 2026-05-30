r"""
文件位置: core/auth/auth_manager.py
名称: 认证管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-17
版本: V2.2.1
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

    当前设备绑定口径:
      - 账号 + 项目 + 设备编号 是唯一绑定身份
      - device_id = PC 端设备编号
      - connection_type = tcp
      - connection_label = Verify 地址

改进历史:
    V2.2.1 (2026-05-23) - 新增 clear_tokens()，修复 SyncWorker 刷新后仍401时的 AttributeError。
    V2.2.0 (2026-05-17) - 对齐 Verify 新设备标识契约与 refresh 请求体。
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

    def _get_api(self) -> AuthApi:
        if self._api is None:
            base_url = self._config.get("server.api_base_url", "")
            timeout = float(self._config.get("server.timeout", 15))
            self._api = AuthApi(base_url=base_url, timeout=timeout)
        return self._api

    def _sync_api_token(self) -> None:
        if self._api and self._access_token:
            self._api.set_token(self._access_token)

    def get_saved_username(self) -> str:
        return self._config.get("auth.saved_username", "") or ""

    def get_saved_password(self, username: str) -> str:
        if not username or username != self.get_saved_username():
            return ""
        try:
            return keyring.get_password(_KEYRING_SERVICE, username) or ""
        except Exception as e:
            logger.warning("读取系统凭据失败: %s", e)
            return ""

    def _save_credentials(self, username: str, password: str) -> None:
        self._config.set_local("auth.saved_username", username)
        self._cleanup_legacy_saved_password()
        try:
            keyring.set_password(_KEYRING_SERVICE, username, password)
        except Exception as e:
            logger.warning("保存系统凭据失败: %s", e)

    def _clear_saved_credentials(self) -> None:
        username = self.get_saved_username()
        self._config.set_local("auth.saved_username", "")
        self._cleanup_legacy_saved_password()

        if username:
            try:
                keyring.delete_password(_KEYRING_SERVICE, username)
            except Exception as e:
                logger.debug("删除系统凭据失败或凭据不存在: %s", e)

    def forget_saved_credentials(self) -> None:
        """清除记住的登录账号密码，用于切换账号。"""
        self._clear_saved_credentials()

    def _cleanup_legacy_saved_password(self) -> None:
        if self._config.get("auth.saved_password", None) is None:
            return

        remove_local = getattr(self._config, "remove_local", None)
        if callable(remove_local):
            remove_local("auth.saved_password")
        else:
            logger.warning("当前 Config 不支持 remove_local，无法自动清理 auth.saved_password")

    def login(self, username: str, password: str, remember: bool = False) -> LoginResult:
        api = self._get_api()

        project_uuid = self._config.get("server.project_uuid", "")
        device_id = self._read_device_id()
        if not device_id:
            return LoginResult(
                success=False,
                error_message="设备编号不能为空，请先配置 config/device_id.txt",
                error_code="DEVICE_ID_REQUIRED",
            )
        connection_label = self._config.get("server.api_base_url", "") or "pc"

        payload = {
            "username": username,
            "password": password,
            "project_uuid": project_uuid,
            "device_id": device_id,
            "connection_type": "tcp",
            "connection_label": connection_label,
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
            user_level=data.get("authorization_level", ""),
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

    def fetch_user_info(self) -> None:
        api = self._get_api()
        try:
            me_data = api.me()
            inactive_devices = me_data.get("inactive_devices")
            self._user_info = UserInfo(
                username=self._user_info.username,
                display_name=self._user_info.display_name,
                project_uuid=self._user_info.project_uuid,
                user_level=me_data.get("authorization_level", ""),
                device_quota=int(me_data.get("authorized_devices") or 0),
                expired_at=me_data.get("valid_until") or "",
                activated_devices=int(me_data.get("activated_devices") or 0),
                inactive_devices=None if inactive_devices is None else int(inactive_devices or 0),
            )
            self._auth_info = me_data
            logger.info(
                "授权摘要已刷新: level=%s quota=%s activated=%s inactive=%s valid_until=%s",
                self._user_info.user_level,
                self._user_info.device_quota,
                self._user_info.activated_devices,
                self._user_info.inactive_devices,
                self._user_info.expired_at,
            )
        except Exception as e:
            logger.warning("获取 /me 失败: %s", e)

    def refresh_access_token(self) -> bool:
        if not self._refresh_token:
            logger.warning("refresh_token 为空")
            return False

        api = self._get_api()
        device_id = self._read_device_id()
        if not device_id:
            logger.warning("Token 刷新失败：设备编号为空")
            return False

        try:
            data = api.refresh_token(self._refresh_token, device_id, "pc")
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

    def clear_tokens(self) -> None:
        """清除内存中的 access_token 和 refresh_token。

        用于刷新后仍 401 的情况，避免下次同步继续使用过期 Token。
        不调用登出 API，不清除 keyring 保存的密码。
        """
        self._access_token = None
        self._refresh_token = None
        if self._api:
            self._api.set_token(None)
        logger.info("Token 已清除（clear_tokens）")

    def logout(self) -> None:
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

    def reload_network_config(self) -> None:
        base_url = self._config.get("server.api_base_url", "")
        timeout = float(self._config.get("server.timeout", 15))
        self.update_network_config(base_url, timeout)

    def update_network_config(self, base_url: str, timeout: float) -> None:
        new_api = AuthApi(base_url=base_url, timeout=timeout)
        if self._access_token:
            new_api.set_token(self._access_token)
        self._api = new_api

    @staticmethod
    def _read_device_id() -> str:
        """从 config/device_id.txt 读取 PC 端设备编号。"""
        from core.utils.constants import DEVICE_ID_FILE
        path = Path(__file__).resolve().parents[2] / DEVICE_ID_FILE
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
        return ""
