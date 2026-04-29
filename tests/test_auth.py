r"""
文件位置: tests/test_auth.py
名称: 认证模块单元测试
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  测试 AuthManager 和相关数据模型。
  使用 unittest.mock 模拟 API 调用，不依赖真实服务器。

改进内容:
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
    cfg = MagicMock()
    cfg.get = lambda key, default=None: {
        "server.api_base_url": "http://127.0.0.1:8000",
        "server.timeout":      15,
        "server.project_uuid": "07238db5-129a-4408-b82a-e025be4652a1",
    }.get(key, default)
    return cfg


@pytest.fixture
def auth_manager(mock_config, tmp_path, monkeypatch):
    """创建 AuthManager，并将文件路径重定向到临时目录。"""
    from core.auth.auth_manager import AuthManager

    monkeypatch.setattr(
        "core.auth.auth_manager._PROJ_ROOT", tmp_path
    )
    (tmp_path / "config").mkdir(exist_ok=True)

    with patch("keyring.get_password", return_value=None), \
         patch("keyring.set_password"):
        mgr = AuthManager(mock_config)
    return mgr, tmp_path


# ── 测试：LoginResult 数据模型 ───────────────────────────────

def test_login_result_defaults():
    from core.auth.models import LoginResult, UserInfo
    result = LoginResult()
    assert result.success is False
    assert result.access_token == ""
    assert result.error_code   == ""


def test_user_info_defaults():
    from core.auth.models import UserInfo
    u = UserInfo()
    assert u.username    == ""
    assert u.user_level  == ""
    assert u.device_quota == 0


# ── 测试：AuthManager 本地方法 ───────────────────────────────

def test_get_saved_username_empty(auth_manager):
    mgr, tmp = auth_manager
    assert mgr.get_saved_username() == ""


def test_save_and_get_username(auth_manager):
    mgr, tmp = auth_manager
    mgr._save_last_login("test_user")
    assert mgr.get_saved_username() == "test_user"


def test_hardware_serial_created(auth_manager):
    mgr, tmp = auth_manager
    serial = mgr._get_or_create_hardware_serial()
    assert len(serial) == 36                          # UUID4 格式
    assert (tmp / "config" / "device_id.txt").exists()


def test_hardware_serial_stable(auth_manager):
    mgr, tmp = auth_manager
    s1 = mgr._get_or_create_hardware_serial()
    s2 = mgr._get_or_create_hardware_serial()
    assert s1 == s2


# ── 测试：登录 payload 构造 ──────────────────────────────────

def test_build_login_payload(auth_manager):
    mgr, _ = auth_manager
    payload = mgr._build_login_payload("admin", "pass")
    assert payload["username"]           == "admin"
    assert payload["password"]           == "pass"
    assert payload["project_uuid"]       == "07238db5-129a-4408-b82a-e025be4652a1"
    assert payload["client_type"]        == "pc"
    assert "device_fingerprint" in payload


# ── 测试：API 错误映射 ───────────────────────────────────────

def test_map_api_error_401(auth_manager):
    from core.api_client.base_client import ApiError
    mgr, _ = auth_manager
    e      = ApiError(401, "用户名或密码错误", "")
    result = mgr._map_api_error(e)
    assert result.success is False
    assert result.error_message == "用户名或密码错误"
    assert result.error_code    == "INVALID_CREDENTIALS"


def test_map_api_error_403_with_detail(auth_manager):
    from core.api_client.base_client import ApiError
    mgr, _ = auth_manager
    e      = ApiError(403, "游戏授权已过期", "")
    result = mgr._map_api_error(e)
    assert result.success is False
    assert result.error_message == "游戏授权已过期"


def test_map_api_error_network(auth_manager):
    import httpx
    mgr, _ = auth_manager
    with patch.object(mgr._api, "login", side_effect=httpx.RequestError("conn")):
        result = mgr.login("u", "p")
    assert result.success    is False
    assert result.error_code == "NETWORK_ERROR"


# ── 测试：登录成功流程 ───────────────────────────────────────

def test_login_success(auth_manager):
    mgr, _ = auth_manager
    fake_response = {
        "access_token":  "fake_at_token",
        "refresh_token": "fake_rt_token",
        "username":      "admin",
        "user_level":    "tester",
        "game_project_code": "game_002",
    }
    with patch.object(mgr._api, "login", return_value=fake_response), \
         patch("keyring.set_password"):
        result = mgr.login("admin", "pass")

    assert result.success        is True
    assert result.access_token   == "fake_at_token"
    assert mgr.is_logged_in      is True
    assert mgr.user_info.username == "admin"
    assert mgr.user_info.user_level == "tester"
