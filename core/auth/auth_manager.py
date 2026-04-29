r"""
文件位置: core/auth/auth_manager.py
名称: 验证管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  管理登录流程、Token 存储与刷新、会话状态。
  供登录窗口和 API 客户端层调用。
  ⚠️ login() 为同步阻塞，必须在 QThread 中调用，禁止在 UI 线程直接调用。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

import keyring
import httpx

from core.api_client.auth_api import AuthApi
from core.api_client.base_client import ApiError
from core.auth.models import LoginResult, UserInfo
from core.utils.config import Config
from core.utils.constants import (
    CLIENT_TYPE,
    DEVICE_ID_FILE,
    KEYRING_RT_SUFFIX,
    KEYRING_SERVICE,
    LAST_LOGIN_FILE,
)
from core.utils.crypto import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

_PROJ_ROOT = Path(__file__).resolve().parents[2]


class AuthManager:
    """
    登录 / Token / 会话管理。

    属性：
        is_logged_in  — 当前是否已登录
        access_token  — 内存中的 AT（短命，15分钟）
        user_info     — UserInfo 对象
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._api    = AuthApi(
            base_url=config.get("server.api_base_url", ""),
            timeout=float(config.get("server.timeout", 15)),
        )
        self.access_token: str | None = None
        self.user_info:    UserInfo   = UserInfo()

    # ── 对外接口 ───────────────────────────

    @property
    def is_logged_in(self) -> bool:
        return bool(self.access_token)

    def login(
        self,
        username: str,
        password: str,
        remember_password: bool = False,
    ) -> LoginResult:
        """
        执行登录，完成接入契约中的 10 步验证链。

        Args:
            username:          用户名
            password:          明文密码
            remember_password: True 则把密码存入 keyring

        Returns:
            LoginResult（success=True 表示登录成功）
        """
        payload = self._build_login_payload(username, password)
        logger.info(
            "登录请求: user=%s project=%s",
            username,
            str(payload.get("project_uuid", ""))[:8],
        )

        try:
            data = self._api.login(payload)
        except ApiError as e:
            return self._map_api_error(e)
        except httpx.TimeoutException:
            return LoginResult(
                success=False,
                error_message="连接服务器超时，请检查网络",
                error_code="TIMEOUT",
            )
        except httpx.RequestError:
            return LoginResult(
                success=False,
                error_message="无法连接服务器，请检查网络或 API 地址",
                error_code="NETWORK_ERROR",
            )
        except Exception as e:
            logger.exception("登录时发生未知异常")
            return LoginResult(
                success=False,
                error_message=f"未知错误: {e}",
                error_code="UNKNOWN",
            )

        # ── 登录成功，保存凭据 ─────────────
        at = data.get("access_token", "")
        rt = data.get("refresh_token", "")

        self.access_token = at
        self._api.set_token(at)
        self.user_info = self._parse_user_info(data, username)

        if rt:
            self._save_refresh_token(username, rt)

        if remember_password:
            keyring.set_password(KEYRING_SERVICE, username, password)

        self._save_last_login(username)

        logger.info("登录成功: user=%s level=%s", username, self.user_info.user_level)
        return LoginResult(
            success=True,
            access_token=at,
            refresh_token=rt,
            user_info=self.user_info,
        )

    def refresh_access_token(self) -> bool:
        """用 Refresh Token 换新 Access Token。返回 True 表示刷新成功。"""
        username = self.user_info.username
        rt       = self._load_refresh_token(username)
        if not rt:
            logger.warning("找不到 Refresh Token，需要重新登录")
            return False

        try:
            data   = self._api.refresh_token(rt)
            at     = data.get("access_token", "")
            new_rt = data.get("refresh_token", rt)

            self.access_token = at
            self._api.set_token(at)
            if new_rt != rt:
                self._save_refresh_token(username, new_rt)

            logger.info("Access Token 刷新成功")
            return True
        except Exception as e:
            logger.error("Token 刷新失败: %s", e)
            return False

    def logout(self) -> None:
        """登出：清除内存 Token 并通知服务端。"""
        try:
            if self.access_token:
                self._api.logout()
        except Exception as e:
            logger.warning("登出 API 调用失败（忽略）: %s", e)
        finally:
            self.access_token = None
            self._api.set_token(None)
            self.user_info = UserInfo()
            logger.info("已登出")

    def get_saved_username(self) -> str:
        """读取上次登录的用户名（用于自动填充登录框）。"""
        path = _PROJ_ROOT / LAST_LOGIN_FILE
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f).get("username", "")
            except Exception:
                pass
        return ""

    def get_saved_password(self, username: str) -> str:
        """从 keyring 读取已保存的密码，无则返回空字符串。"""
        if not username:
            return ""
        try:
            return keyring.get_password(KEYRING_SERVICE, username) or ""
        except Exception:
            return ""

    # ── 内部方法 ───────────────────────────

    def _build_login_payload(self, username: str, password: str) -> dict:
        """构造符合 Verify LoginRequest schema 的登录请求体。"""
        hardware_serial = self._get_or_create_hardware_serial()
        return {
            "username":           username,
            "password":           password,
            "project_uuid":       self._config.get("server.project_uuid", ""),
            "device_fingerprint": hardware_serial,   # 顶层字段
            "client_type":        CLIENT_TYPE,        # 顶层字段，值为 "pc"
        }

    def _get_or_create_hardware_serial(self) -> str:
        """
        获取或生成本机唯一标识（UUID4）。
        首次调用时生成并写入 config/device_id.txt。
        """
        id_file = _PROJ_ROOT / DEVICE_ID_FILE
        if id_file.exists():
            try:
                serial = id_file.read_text(encoding="utf-8").strip()
                if serial:
                    return serial
            except Exception:
                pass

        serial = str(uuid.uuid4())
        id_file.parent.mkdir(parents=True, exist_ok=True)
        id_file.write_text(serial, encoding="utf-8")
        logger.info("生成本机唯一标识: %s", serial)
        return serial

    def _save_refresh_token(self, username: str, rt: str) -> None:
        """Fernet 加密后存入 keyring。"""
        try:
            serial    = self._get_or_create_hardware_serial()
            encrypted = encrypt_token(rt, serial)
            service   = f"{KEYRING_SERVICE}{KEYRING_RT_SUFFIX}"
            keyring.set_password(service, username, encrypted)
        except Exception as e:
            logger.warning("Refresh Token 存储失败: %s", e)

    def _load_refresh_token(self, username: str) -> str | None:
        """从 keyring 读取并解密 Refresh Token。"""
        if not username:
            return None
        try:
            service   = f"{KEYRING_SERVICE}{KEYRING_RT_SUFFIX}"
            encrypted = keyring.get_password(service, username)
            if not encrypted:
                return None
            serial = self._get_or_create_hardware_serial()
            return decrypt_token(encrypted, serial)
        except Exception as e:
            logger.warning("Refresh Token 读取失败: %s", e)
            return None

    def _save_last_login(self, username: str) -> None:
        path = _PROJ_ROOT / LAST_LOGIN_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"username": username}, f)
        except Exception as e:
            logger.warning("保存最后登录用户名失败: %s", e)

    def _parse_user_info(self, data: dict, username: str) -> UserInfo:
        """从 LoginResponse 扁平结构中提取并构造 UserInfo。

        LoginResponse 字段: access_token / refresh_token / token_type /
                          expires_in / user_id / username / user_level /
                          game_project_code
        """
        return UserInfo(
            username=data.get("username", username),
            user_level=data.get("user_level", ""),
            display_name=data.get("username", username),
            expired_at="",
            device_quota=0,
            project_uuid=self._config.get("server.project_uuid", ""),
            game_name=data.get("game_project_code", ""),
        )

    def _map_api_error(self, e: ApiError) -> LoginResult:
        """将 ApiError 映射为用户友好的 LoginResult。"""
        # 对于 4xx 错误，优先显示服务端的具体 detail（如果有的话）
        server_detail = e.detail if isinstance(e.detail, str) and e.detail else ""

        CODE_MAP = {
            401: (server_detail or "用户名或密码错误",           "INVALID_CREDENTIALS"),
            403: (server_detail or "账号无权限或已过期",          "FORBIDDEN"),
            404: (server_detail or "用户不存在",                 "USER_NOT_FOUND"),
            422: (server_detail or "请求格式错误，请联系管理员",   "INVALID_PAYLOAD"),
            429: (server_detail or "请求过于频繁，请稍后再试",     "RATE_LIMIT"),
        }
        msg, code = CODE_MAP.get(
            e.status_code,
            (server_detail or f"服务器错误 ({e.status_code})", "SERVER_ERROR"),
        )
        if e.error_code:
            code = e.error_code

        logger.warning("登录失败 [%s] HTTP%s: %s", code, e.status_code, msg)
        return LoginResult(success=False, error_message=msg, error_code=code)
