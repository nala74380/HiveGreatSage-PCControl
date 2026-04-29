r"""
文件位置: tests/test_api_client.py
名称: API 客户端单元测试
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  测试 BaseClient 和各 API 子类的行为。
  使用 unittest.mock 拦截 httpx.request，不发真实网络请求。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  运行: pytest tests/test_api_client.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ── BaseClient 基础行为 ───────────────────────────────────────

def _make_mock_response(status_code: int, json_data: dict):
    resp = MagicMock()
    resp.status_code   = status_code
    resp.is_success    = (200 <= status_code < 300)
    resp.json.return_value = json_data
    resp.text          = str(json_data)
    return resp


def test_base_client_get_success():
    from core.api_client.base_client import BaseClient
    client = BaseClient("http://test.example.com")
    client.set_token("fake_token")

    with patch("httpx.request", return_value=_make_mock_response(200, {"ok": True})) as mock_req:
        result = client.get("/api/test")

    assert result == {"ok": True}
    call_args = mock_req.call_args
    assert call_args[0][0] == "GET"
    assert "Authorization" in call_args[1]["headers"]
    assert call_args[1]["headers"]["Authorization"] == "Bearer fake_token"


def test_base_client_post_json():
    from core.api_client.base_client import BaseClient
    client = BaseClient("http://test.example.com")

    with patch("httpx.request", return_value=_make_mock_response(200, {"id": 1})):
        result = client.post("/api/create", json={"name": "test"})

    assert result["id"] == 1


def test_base_client_raises_api_error_on_4xx():
    from core.api_client.base_client import BaseClient, ApiError
    client = BaseClient("http://test.example.com")

    mock_resp = _make_mock_response(401, {"detail": "Unauthorized"})
    with patch("httpx.request", return_value=mock_resp):
        with pytest.raises(ApiError) as exc_info:
            client.get("/api/secure")

    assert exc_info.value.status_code == 401
    assert "Unauthorized" in exc_info.value.detail


def test_base_client_raises_on_timeout():
    import httpx
    from core.api_client.base_client import BaseClient
    client = BaseClient("http://test.example.com")

    with patch("httpx.request", side_effect=httpx.TimeoutException("timeout")):
        with pytest.raises(httpx.TimeoutException):
            client.get("/api/slow")


def test_base_client_no_token_no_auth_header():
    from core.api_client.base_client import BaseClient
    client = BaseClient("http://test.example.com")
    # token 为 None

    with patch("httpx.request", return_value=_make_mock_response(200, {})) as mock_req:
        client.get("/api/public")

    headers = mock_req.call_args[1]["headers"]
    assert "Authorization" not in headers


# ── AuthApi ───────────────────────────────────────────────────

def test_auth_api_login():
    from core.api_client.auth_api import AuthApi
    api = AuthApi("http://test.example.com")

    fake_resp = {"access_token": "at", "refresh_token": "rt", "user_level": "tester"}
    with patch("httpx.request", return_value=_make_mock_response(200, fake_resp)):
        result = api.login({
            "username": "u", "password": "p",
            "project_uuid": "xxx", "device_fingerprint": "yyy", "client_type": "pc"
        })

    assert result["access_token"] == "at"


def test_auth_api_refresh():
    from core.api_client.auth_api import AuthApi
    api = AuthApi("http://test.example.com")
    api.set_token("old_at")

    fake_resp = {"access_token": "new_at", "expires_in": 900}
    with patch("httpx.request", return_value=_make_mock_response(200, fake_resp)):
        result = api.refresh_token("old_rt")

    assert result["access_token"] == "new_at"


# ── DeviceApi ─────────────────────────────────────────────────

def test_device_api_get_list():
    from core.api_client.device_api import DeviceApi
    api = DeviceApi("http://test.example.com")
    api.set_token("fake_at")

    fake_resp = {
        "devices": [
            {"device_id": "fp001", "user_id": 1, "status": "running",
             "is_online": True, "last_seen": None, "game_data": {}}
        ],
        "total": 1, "online_count": 1,
    }
    with patch("httpx.request", return_value=_make_mock_response(200, fake_resp)):
        result = api.get_device_list()

    assert result["total"] == 1
    assert result["devices"][0]["device_id"] == "fp001"


# ── DeviceInfo 模型 ───────────────────────────────────────────

def test_device_info_from_api_basic():
    from core.device.models import DeviceInfo
    raw = {
        "device_id": "fp_abc",
        "user_id":   42,
        "status":    "running",
        "is_online": True,
        "last_seen": None,
        "game_data": {"task": "日常任务", "level": 55, "combat_power": 300000, "server": "S2"},
    }
    dev = DeviceInfo.from_api(raw)
    assert dev.fingerprint    == "fp_abc"
    assert dev.api_status     == "running"
    assert dev.task           == "日常任务"
    assert dev.level          == 55
    assert dev.combat_power   == 300000
    assert dev.server         == "S2"


def test_device_info_meta_merge():
    from core.device.models import DeviceInfo
    raw = {"device_id": "fp_xyz", "user_id": 1, "status": "idle",
           "is_online": False, "last_seen": None, "game_data": {}}
    meta = {"alias": "A-007", "role": "captain", "note": "主力号"}
    dev  = DeviceInfo.from_api(raw, meta)
    assert dev.alias      == "A-007"
    assert dev.role       == "captain"
    assert dev.display_id == "A-007"


def test_device_info_heartbeat_str_none():
    from core.device.models import DeviceInfo
    dev = DeviceInfo(fingerprint="fp")
    assert dev.heartbeat_str == "—"


def test_device_info_heartbeat_str_recent():
    from core.device.models import DeviceInfo
    from datetime import datetime, timezone, timedelta
    dev = DeviceInfo(
        fingerprint="fp",
        last_seen=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    assert "刚才" in dev.heartbeat_str or "s前" in dev.heartbeat_str


# ── TTLCache ──────────────────────────────────────────────────

def test_ttl_cache_set_get():
    from core.utils.cache import TTLCache
    cache = TTLCache(default_ttl=60)
    cache.set("k", [1, 2, 3])
    assert cache.get("k") == [1, 2, 3]


def test_ttl_cache_expired():
    import time
    from core.utils.cache import TTLCache
    cache = TTLCache(default_ttl=0.1)
    cache.set("k", "val")
    time.sleep(0.2)
    assert cache.get("k") is None


def test_ttl_cache_default():
    from core.utils.cache import TTLCache
    cache = TTLCache()
    assert cache.get("missing", "default") == "default"
