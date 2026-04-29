r"""
文件位置: core/team/team_manager.py
名称: 组队管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  管理 WSServer 生命周期 + 维护已连接设备的队伍状态。
  由 Application 持有，Phase 3 使用。

改进内容:
  V1.0.0 - 初始版本（Phase 3 预留接口）

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from core.team.lan_comm import WSServer, LanInfo

if TYPE_CHECKING:
    from core.utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class TeamMember:
    """通过 WebSocket 连接的安卓设备成员信息。"""
    device_id:   str
    device_name: str  = ""
    role:        str  = ""    # captain / power / farmer / newbie
    status:      str  = "idle"
    current_task: str = ""
    info:        dict = field(default_factory=dict)


class TeamManager:
    """
    管理 WebSocket 服务端和已连接成员列表。
    主窗口通过 ws_server.device_connected / device_disconnected 信号自动维护。
    """

    def __init__(self, config: "Config") -> None:
        port = int(config.get("team.ws_port", 8889))
        self.ws_server = WSServer(port=port)
        self._members: dict[str, TeamMember] = {}

        self.ws_server.device_connected.connect(self._on_connected)
        self.ws_server.device_disconnected.connect(self._on_disconnected)
        self.ws_server.device_message.connect(self._on_message)

    def start(self) -> bool:
        """启动 WS 服务端。登录成功后由 app 调用。"""
        return self.ws_server.start()

    def stop(self) -> None:
        self.ws_server.stop()

    @property
    def members(self) -> list[TeamMember]:
        return list(self._members.values())

    @property
    def connected_count(self) -> int:
        return self.ws_server.connected_count

    @property
    def lan_ip(self) -> str:
        return LanInfo.get_primary_ip()

    @property
    def listen_address(self) -> str:
        return f"{self.lan_ip}:{self.ws_server.port}"

    # ── WS 事件 ──────────────────────────────────

    def _on_connected(self, device_id: str, info: dict) -> None:
        member = TeamMember(
            device_id   = device_id,
            device_name = info.get("device_name", ""),
            info        = info,
        )
        self._members[device_id] = member
        logger.info("TeamManager: 成员加入 %s", device_id[:12])

    def _on_disconnected(self, device_id: str) -> None:
        self._members.pop(device_id, None)
        logger.info("TeamManager: 成员离开 %s", device_id[:12])

    def _on_message(self, device_id: str, data: dict) -> None:
        msg_type = data.get("type")
        member   = self._members.get(device_id)
        if not member:
            return

        if msg_type == "heartbeat":
            member.status       = data.get("status", "idle")
            member.current_task = data.get("current_task", "")

    # ── 指令发送 ──────────────────────────────────

    def start_task(self, device_id: str, task_name: str, params: dict | None = None) -> bool:
        return self.ws_server.send_to(device_id, {
            "type":      "start_task",
            "task_name": task_name,
            "params":    params or {},
        })

    def stop_task(self, device_id: str) -> bool:
        return self.ws_server.send_to(device_id, {"type": "stop_task"})

    def broadcast_params(self, params: dict) -> int:
        return self.ws_server.broadcast({"type": "params_update", "params": params})
