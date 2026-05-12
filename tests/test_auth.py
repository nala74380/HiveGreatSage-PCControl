r"""
文件位置: tests/test_auth.py
名称: 认证模块单元测试
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-12
版本: V2.0.0
功能及相关说明:
  测试 AuthManager 和相关数据模型。
  使用 unittest.mock 模拟 API 调用，不依赖真实服务器。

改进内容:
  V2.0.0 - 对齐 AuthManager V2.1.0；覆盖 keyring 凭据存储，不再测试旧私有方法。
  V1.0.0 - 初始版本

调试信息:
  运行: pytest tests/test_auth.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── 辅助 Fixtures ────────────────────────────────────────────

@pytest.fixture
def mock_config():
    data = {
        "server.api_base_url": "http://127.0.0.1:8000",
        "server.timeout": 15,
        "server.project_uuid": "07238db5-129a-4408-b82a-e025be4652a1",
        "auth.saved_username": "",
        "auth.saved_password": None,
    }

    cfg = MagicMock()
    cfg.get = lambda key, default=None: data.get(key, default)

    def set_local(key, value):
        data[key] = value

    def remove_local(key):
        data.pop(key, None)

    cfg.set_local.side_effect = set_local
    cfg.remove_local.side_effect = remove_local
    cfg._test_data = data
    return cfg


@pytest.fixture
def auth_manager(mock_config):
    """创建 AuthManager，并避免真实访问系统凭据管理器。"""
    from core.auth.auth_manager import AuthManager

    with patch("core.auth.auth_manager.keyring.get_password", return_value=None), \
         patch("core.auth.auth_manager.keyring.set_password"), \
         patch("core.auth.auth_manager.keyring.delete_password"):
        mgr = AuthManager(mock_config)
    return mgr


# ── 测试：LoginResult 数据模型 ───────────────────────────────

def test_login_result_defaults():
    from core.auth.models import LoginResult

    result = LoginResult()
    assert result.success is False
    assert result.access_token == ""
    assert result.refresh_token == ""
    assert result.error_code == ""


def test_user_info_defaults():
    from core.auth.models import UserInfo

    u = UserInfo()
    assert u.username == ""
    assert u.user_level == ""
    assert u.device_quota == 0
    assert u.activated_devices == 0


# ── 测试：凭据存储 ────────────────────────────────────────────

def test_get_saved_username_empty(auth_manager):
    assert auth_manager.get_saved_username() == ""


def test_get_saved_password_uses_keyring_when_username_matches(mock_config):
    from core.auth.auth_manager import AuthManager

    mock_config._test_data["auth.saved_username"] = "admin"
    with patch("core.auth.auth_manager.keyring.get_password", return_value="secret") as get_password:
        mgr = AuthManager(mock_config)
        assert mgr.get_saved_password("admin") == "secret"

    get_password.assert_called_once_with("HiveGreatSage-PCControl", "admin")


def test_get_saved_password_returns_empty_when_username_mismatch(mock_config):
    from core.auth.auth_manager import AuthManager

    mock_config._test_data["auth.saved_username"] = "admin"
    with patch("core.auth.auth_manager.keyring.get_password") as get_password:
        mgr = AuthManager(mock_config)
        assert mgr.get_saved_password("other") == ""

    get_password.assert_not_called()


def test_save_credentials_writes_username_to_local_and_password_to_keyring(mock_config):
    from core.auth.auth_manager import AuthManager

    with patch("core.auth.auth_manager.keyring.set_password") as set_password:
        mgr = AuthManager(mock_config)
        mgr._save_credentials("admin", "secret")

    assert mock_config._test_data["auth.saved_username"] == "admin"
    assert "auth.saved_password" not in mock_config._test_data
    set_password.assert_called_once_with("HiveGreatSage-PCControl", "admin", "secret")


def test_clear_saved_credentials_removes_username_password_and_keyring(mock_config):
    from core.auth.auth_manager import AuthManager

    mock_config._test_data["auth.saved_username"] = "admin"
    mock_config._test_data["auth.saved_password"] = "legacy-secret"

    with patch("core.auth.auth_manager.keyring.delete_password") as delete_password:
        mgr = AuthManager(mock_config)
        mgr._clear_saved_credentials()

    assert mock_config._test_data["auth.saved_username"] == ""
    assert "auth.saved_password" not in mock_config._test_data
    delete_password.assert_called_once_with("HiveGreatSage-PCControl", "admin")


def test_init_cleans_legacy_saved_password(mock_config):
    from core.auth.auth_manager import AuthManager

    mock_config._test_data["auth.saved_password"] = "legacy-secret"
    AuthManager(mock_config)

    assert "auth.saved_password" not in mock_config._test_data
    mock_config.remove_local.assert_called_with("auth.saved_password")


# ── 测试：登录流程 ────────────────────────────────────────────

def test_login_success_remember_false_clears_saved_credentials(auth_manager):
    fake_api = MagicMock()
    fake_api.login.return_value = {
        "access_token": "fake_at_token",
        "refresh_token": "fake_rt_token",
        "username": "admin",
    }
    auth_manager._api = fake_api

    with patch.object(auth_manager, "_read_device_id", return_value="device-001"), \
         patch.object(auth_manager, "_clear_saved_credentials") as clear_credentials:
        result = auth_manager.login("admin", "pass", remember=False)

    assert result.success is True
    assert result.access_token == "fake_at_token"
    assert result.refresh_token == "fake_rt_token"
    assert auth_manager.is_logged_in is True
    assert auth_manager.user_info.username == "admin"
    assert auth_manager.user_info.project_uuid == "07238db5-129a-4408-b82a-e025be4652a1"
    fake_api.login.assert_called_once_with({
        "username": "admin",
        "password": "pass",
        "project_uuid": "07238db5-129a-4408-b82a-e025be4652a1",
        "device_fingerprint": "device-001",
        "client_type": "pc",
    })
    fake_api.set_token.assert_called_once_with("fake_at_token")
    clear_credentials.assert_called_once()


def test_login_success_remember_true_saves_credentials(auth_manager):
    fake_api = MagicMock()
    fake_api.login.return_value = {
        "access_token": "fake_at_token",
        "refresh_token": "fake_rt_token",
        "username": "admin",
    }
    auth_manager._api = fake_api

    with patch.object(auth_manager, "_read_device_id", return_value="device-001"), \
         patch.object(auth_manager, "_save_credentials") as save_credentials:
        result = auth_manager.login("admin", "pass", remember=True)

    assert result.success is True
    save_credentials.assert_called_once_with("admin", "pass")


def test_login_failure_returns_login_result(auth_manager):
    from core.api_client.base_client import ApiError

    fake_api = MagicMock()
    fake_api.login.side_effect = ApiError(401, "用户名或密码错误", "INVALID_CREDENTIALS")
    auth_manager._api = fake_api

    result = auth_manager.login("admin", "bad-pass")

    assert result.success is False
    assert result.error_message == "用户名或密码错误"
    assert result.error_code == "401"
    assert auth_manager.is_logged_in is False


# ── 测试：用户信息 / Token / 登出 ─────────────────────────────

def test_fetch_user_info_updates_auth_info(auth_manager):
    fake_api = MagicMock()
    fake_api.me.return_value = {
        "authorization_level": "tester",
        "authorized_devices": 10,
        "valid_until": "2027-01-01",
        "activated_devices": 3,
        "inactive_devices": 7,
    }
    auth_manager._api = fake_api
    auth_manager._user_info.username = "admin"
    auth_manager._user_info.display_name = "admin"
    auth_manager._user_info.project_uuid = "project-001"

    auth_manager.fetch_user_info()

    assert auth_manager.user_info.user_level == "tester"
    assert auth_manager.user_info.device_quota == 10
    assert auth_manager.user_info.activated_devices == 3
    assert auth_manager.auth_info["authorization_level"] == "tester"


def test_refresh_access_token_success(auth_manager):
    fake_api = MagicMock()
    fake_api.refresh_token.return_value = {
        "access_token": "new_at",
        "refresh_token": "new_rt",
    }
    auth_manager._api = fake_api
    auth_manager._refresh_token = "old_rt"

    assert auth_manager.refresh_access_token() is True
    assert auth_manager.access_token == "new_at"
    assert auth_manager._refresh_token == "new_rt"
    fake_api.refresh_token.assert_called_once_with("old_rt")
    fake_api.set_token.assert_called_once_with("new_at")


def test_refresh_access_token_without_refresh_token_returns_false(auth_manager):
    auth_manager._refresh_token = None
    assert auth_manager.refresh_access_token() is False


def test_logout_clears_local_state(auth_manager):
    fake_api = MagicMock()
    auth_manager._api = fake_api
    auth_manager._access_token = "at"
    auth_manager._refresh_token = "rt"

    auth_manager.logout()

    fake_api.logout.assert_called_once()
    fake_api.set_token.assert_called_once_with(None)
    assert auth_manager.access_token is None
    assert auth_manager._refresh_token is None
    assert auth_manager.is_logged_in is False


def test_update_network_config_preserves_access_token(auth_manager):
    auth_manager._access_token = "at"

    with patch("core.auth.auth_manager.AuthApi") as auth_api_cls:
        fake_api = MagicMock()
        auth_api_cls.return_value = fake_api
        auth_manager.update_network_config("http://new.example", 20)

    auth_api_cls.assert_called_once_with(base_url="http://new.example", timeout=20)
    fake_api.set_token.assert_called_once_with("at")
    assert auth_manager._api is fake_api
