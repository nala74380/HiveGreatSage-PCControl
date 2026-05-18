r"""
文件位置: core/device/models.py
名称: 设备数据模型
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-17
版本: V1.1.0
功能及相关说明:
  PC 中控本地的设备数据模型。
  数据来源三元合并：
    1. Verify API 响应（device_id / connection_type / connection_label / status / last_seen / game_data / is_online）
    2. 本地元数据文件 config/device_meta.json（role / note，用户可编辑）
    3. ADB 本地扫描（adb_serial / adb_connected）

改进内容:
  V1.1.0 - 对齐 Verify 设备编号绑定口径。
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeviceInfo:
    """
    PC 中控本地设备信息，合并 API + 元数据 + ADB 三路来源。

    · device_id         : 用户填写的设备编号
    · connection_label  : USB 显示 SN；TCP 显示 IP:端口
    """

    device_id: str
    connection_type: str = ""
    connection_label: str = ""
    user_id: int = 0
    api_status: str = "offline"
    last_seen: datetime | None = None
    game_data: dict = field(default_factory=dict)
    is_online: bool = False

    task: str = ""
    level: int = 0
    combat_power: int = 0
    server: str = ""

    role: str = ""
    note: str = ""

    adb_serial: str = ""
    adb_connected: bool = False
    activated: bool = False

    @property
    def display_id(self) -> str:
        return self.device_id or self.connection_label or "—"

    @property
    def heartbeat_str(self) -> str:
        if self.last_seen is None:
            return "—"
        from datetime import timezone
        now = datetime.now(timezone.utc)
        ls = self.last_seen
        if ls.tzinfo is None:
            ls = ls.replace(tzinfo=timezone.utc)
        delta = int((now - ls).total_seconds())
        if delta < 10:
            return "刚才"
        if delta < 60:
            return f"{delta}s前"
        if delta < 3600:
            return f"{delta // 60}m前"
        return f"{delta // 3600}h前"

    @classmethod
    def from_api(cls, api_data: dict, meta: dict | None = None) -> "DeviceInfo":
        game_data: dict = api_data.get("game_data") or {}
        meta = meta or {}

        last_seen_raw = api_data.get("last_seen")
        last_seen: datetime | None = None
        if isinstance(last_seen_raw, datetime):
            last_seen = last_seen_raw
        elif isinstance(last_seen_raw, str):
            try:
                last_seen = datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00"))
            except ValueError:
                last_seen = None

        return cls(
            device_id=api_data.get("device_id", "") or "",
            connection_type=api_data.get("connection_type", "") or "",
            connection_label=api_data.get("connection_label", "") or "",
            user_id=api_data.get("user_id", 0),
            api_status=api_data.get("status") or "offline",
            last_seen=last_seen,
            game_data=game_data,
            is_online=api_data.get("is_online", False),
            task=str(game_data.get("task", "")),
            level=int(game_data.get("level", 0) or 0),
            combat_power=int(game_data.get("combat_power", 0) or 0),
            server=str(game_data.get("server", "")),
            role=meta.get("role", ""),
            note=meta.get("note", ""),
            adb_serial="",
            adb_connected=False,
            activated=meta.get("activated", False),
        )
