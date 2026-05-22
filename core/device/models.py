r"""
文件位置: core/device/models.py
名称: 设备数据模型
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-18
版本: V1.2.0
功能及相关说明:
  PC 中控本地的设备数据模型。
  设备绑定主键统一为 device_id。
  数据来源：
    1. Verify API 响应：device_id / status / last_seen / game_data / is_online
    2. 本地元数据文件 config/device_meta.json：role / note，用户可编辑
    3. PC 中控侧 ADB 查询：connection_type / connection_label / adb_serial / adb_connected

改进内容:
  V1.2.0 - 明确 connection_type / connection_label 为 PC 中控侧 ADB 本地展示信息，不从 Verify API 读取。
  V1.1.0 - 对齐 Verify 设备编号绑定口径。
  V1.0.0 - 初始版本

调试信息:
  已知问题: ADB 扫描结果注入 DeviceInfo 的链路尚待实现。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeviceInfo:
    """
    PC 中控本地设备信息。

    · device_id         : 用户填写的设备编号；账号 + 项目下的设备绑定主键
    · connection_type   : PC 中控侧通过 ADB 查询得到的本地连接类型
    · connection_label  : PC 中控侧通过 ADB 查询得到的本地连接展示标识

    注意：
      connection_type / connection_label 不参与 Verify 设备绑定唯一性。
      安卓端登录 / 心跳不应把 connection_type / connection_label 作为绑定字段上报。
    """

    device_id: str
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
    activated: bool = False

    connection_type: str = ""
    connection_label: str = ""
    adb_serial: str = ""
    adb_connected: bool = False

    @staticmethod
    def is_activated_status(status: str) -> bool:
        return (status or "").strip().lower() in {"idle", "running"}

    @staticmethod
    def _as_bool(value) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "online"}
        return False

    @property
    def heartbeat_online(self) -> bool:
        """安卓端心跳正常才视为在线；列表在线状态以 Verify 的 is_online 为准。"""
        status = (self.api_status or "").strip().lower()
        if status in {"offline", "error", "abnormal"}:
            return False
        return self._as_bool(self.is_online)

    @property
    def account_blocked(self) -> bool:
        """从游戏数据中识别明确封号状态；没有上报该字段时不主动猜测。"""
        data = self.game_data or {}
        block_keys = {
            "account_status",
            "account_state",
            "ban_status",
            "blocked",
            "banned",
            "is_banned",
        }
        block_values = {"ban", "banned", "blocked", "封号", "封禁", "冻结"}
        for key in block_keys:
            value = data.get(key)
            if isinstance(value, bool) and value:
                return True
            text = str(value or "").strip().lower()
            if text in block_values or "封号" in text or "封禁" in text:
                return True
        return False

    @property
    def display_status_key(self) -> str:
        """
        PC 中控前台唯一三态：
        online  = 安卓端正常运行，心跳正常。
        offline = 安卓端未运行，心跳不正常。
        error   = 游戏数据明确上报封号/异常，或后端状态明确为异常。

        注意：ADB/LAN 只代表“这台 PC 能否本地控制设备”，不能决定设备是否在线。
        设备不在本机局域网但心跳正常时，仍然是在线；只是在连接标识中显示为远程心跳。
        """
        status = (self.api_status or "").strip().lower()
        if self.account_blocked or status in {"error", "abnormal"}:
            return "error"
        if self.heartbeat_online:
            return "online"
        return "offline"

    @property
    def display_id(self) -> str:
        return self.device_id or "—"

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

        api_status = api_data.get("status") or "offline"
        return cls(
            device_id=api_data.get("device_id", "") or "",
            user_id=api_data.get("user_id", 0),
            api_status=api_status,
            last_seen=last_seen,
            game_data=game_data,
            is_online=cls._as_bool(api_data.get("is_online", False)),
            task=str(game_data.get("task", "")),
            level=int(game_data.get("level", 0) or 0),
            combat_power=int(game_data.get("combat_power", 0) or 0),
            server=str(game_data.get("server", "")),
            role=meta.get("role", ""),
            note=meta.get("note", ""),
            activated=cls.is_activated_status(api_status),
            connection_type="",
            connection_label="",
            adb_serial="",
            adb_connected=False,
        )
