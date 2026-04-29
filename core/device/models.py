r"""
文件位置: core/device/models.py
名称: 设备数据模型
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  PC 中控本地的设备数据模型。
  数据来源三元合并：
    1. Verify API 响应（device_fingerprint / status / last_seen / game_data / is_online）
    2. 本地元数据文件 config/device_meta.json（alias / role / server / note，用户可编辑）
    3. ADB 本地扫描（adb_serial / adb_connected）

改进内容:
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

    · api_status : Verify API 返回的 status 字段（running/idle/error/offline）
    · is_online  : Redis 中有活跃心跳 → True；仅有 DB 记录 → False
    · game_data  : 游戏原始数据字典，各游戏字段不同，此层不校验
    """

    # ── 来自 API ────────────────────────────────────
    fingerprint:  str              # 设备唯一标识（device_fingerprint）
    user_id:      int   = 0
    api_status:   str   = "offline"  # running / idle / error / offline
    last_seen:    datetime | None = None
    game_data:    dict  = field(default_factory=dict)
    is_online:    bool  = False

    # ── 从 game_data 提取（各游戏通用字段，不存在时为默认值）──
    task:          str  = ""
    level:         int  = 0
    combat_power:  int  = 0
    server:        str  = ""      # 如 "S1" "S2"

    # ── 本地元数据（用户可编辑，存 config/device_meta.json）──
    alias:   str = ""   # 显示编号，如 "A-001"
    role:    str = ""   # captain / power / farmer / newbie
    note:    str = ""   # 用户自定义备注

    # ── ADB 本地状态 ─────────────────────────────────
    adb_serial:    str  = ""
    adb_connected: bool = False
    activated:     bool = False    # 已执行 ROOT 激活命令

    # ── 计算属性 ─────────────────────────────────────
    @property
    def display_id(self) -> str:
        """优先显示 alias，否则显示 fingerprint 前 12 位。"""
        return self.alias or self.fingerprint[:12]

    @property
    def heartbeat_str(self) -> str:
        """将 last_seen 转换为可读的相对时间字符串。"""
        if self.last_seen is None:
            return "—"
        from datetime import timezone
        now = datetime.now(timezone.utc)
        # last_seen 可能是 naive datetime，统一处理
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
        """
        从 API 响应字典和本地元数据字典构造 DeviceInfo。

        Args:
            api_data: DeviceStatus 对应的 dict（来自 /api/device/list）
            meta:     config/device_meta.json 中该 fingerprint 的条目，可为 None
        """
        game_data: dict = api_data.get("game_data") or {}
        meta = meta or {}

        # last_seen 可能是字符串（ISO 格式）或 datetime 或 None
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
            fingerprint  = api_data.get("device_id", ""),
            user_id      = api_data.get("user_id", 0),
            api_status   = api_data.get("status") or "offline",
            last_seen    = last_seen,
            game_data    = game_data,
            is_online    = api_data.get("is_online", False),
            # game_data 字段（安全 get，各游戏自定义）
            task          = str(game_data.get("task", "")),
            level         = int(game_data.get("level", 0) or 0),
            combat_power  = int(game_data.get("combat_power", 0) or 0),
            server        = str(game_data.get("server", "")),
            # 本地元数据
            alias  = meta.get("alias", ""),
            role   = meta.get("role", ""),
            note   = meta.get("note", ""),
            # ADB 默认未连接，由 DeviceManager 后续填充
            adb_serial    = "",
            adb_connected = False,
            activated     = meta.get("activated", False),
        )
