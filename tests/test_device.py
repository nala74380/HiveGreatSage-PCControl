from core.device.models import DeviceInfo


def test_display_status_online_requires_adb_and_heartbeat():
    dev = DeviceInfo(
        device_id="A118",
        api_status="running",
        is_online=True,
        adb_connected=True,
    )

    assert dev.display_status_key == "online"


def test_display_status_offline_when_heartbeat_lost_but_adb_exists():
    dev = DeviceInfo(
        device_id="A118",
        api_status="offline",
        is_online=False,
        adb_connected=True,
    )

    assert dev.display_status_key == "offline"


def test_display_status_offline_status_wins_over_stale_is_online():
    dev = DeviceInfo(
        device_id="A118",
        api_status="offline",
        is_online=True,
        adb_connected=True,
    )

    assert dev.heartbeat_online is False
    assert dev.display_status_key == "offline"


def test_display_status_offline_when_runtime_status_is_stale_without_online_flag():
    dev = DeviceInfo(
        device_id="A118",
        api_status="running",
        is_online=False,
        adb_connected=True,
    )

    assert dev.heartbeat_online is False
    assert dev.display_status_key == "offline"


def test_display_status_online_when_remote_heartbeat_is_alive_without_adb():
    dev = DeviceInfo(
        device_id="A118",
        api_status="running",
        is_online=True,
        adb_connected=False,
    )

    assert dev.display_status_key == "online"


def test_display_status_error_when_account_blocked():
    dev = DeviceInfo(
        device_id="A118",
        api_status="running",
        is_online=True,
        adb_connected=True,
        game_data={"account_status": "封号"},
    )

    assert dev.display_status_key == "error"


def test_from_api_normalizes_string_is_online():
    dev = DeviceInfo.from_api({
        "device_id": "A118",
        "status": "unknown",
        "is_online": "false",
        "game_data": {},
    })

    assert dev.is_online is False
    assert dev.display_status_key == "offline"
