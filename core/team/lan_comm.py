r"""
文件位置: core/team/lan_comm.py
名称: 局域网通信（内网IP检测 + WebSocket 服务端）
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  PC 中控局域网通信模块，Phase 3 核心。
  包含两个类：
    LanInfo   — 本机内网 IP 检测
    WSServer  — PySide6 QWebSocketServer，监听 8889 端口
                接受安卓脚本 WebSocket 连接，处理认证和消息

  消息协议（JSON）：
    安卓→PC: type=auth / type=heartbeat / type=task_completed / type=error
    PC→安卓: type=auth_ok / type=auth_failed / type=start_task / type=stop_task / type=params_update

改进内容:
  V1.0.0 - 初始版本

调试信息:
  ⚠️ PySide6.QtWebSockets 需要 PySide6-Addons：pip install PySide6-Addons
  已知问题: 无
"""

from __future__ import annotations

import ipaddress
import json
import logging
import socket
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QHostAddress

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
#  内网 IP 检测
# ─────────────────────────────────────────────────────────────

class LanInfo:
    """检测本机所有可用的内网 IPv4 地址。"""

    @staticmethod
    def get_lan_ips() -> list[str]:
        """
        返回本机内网 IPv4 地址列表，按 192.168 > 10.x > 172.x 优先级排序。
        排除回环地址（127.x）。
        """
        try:
            hostname = socket.gethostname()
            raw_ips  = socket.gethostbyname_ex(hostname)[2]
        except Exception:
            return []

        lan_ips: list[str] = []
        for ip in raw_ips:
            try:
                addr = ipaddress.IPv4Address(ip)
                if addr.is_private and not addr.is_loopback:
                    lan_ips.append(ip)
            except ValueError:
                continue

        def _priority(ip: str) -> int:
            if ip.startswith("192.168."):
                return 0
            if ip.startswith("10."):
                return 1
            return 2

        lan_ips.sort(key=_priority)
        return lan_ips

    @staticmethod
    def get_primary_ip() -> str:
        """返回优先级最高的内网 IP，无可用则返回 '127.0.0.1'。"""
        ips = LanInfo.get_lan_ips()
        return ips[0] if ips else "127.0.0.1"


# ─────────────────────────────────────────────────────────────
#  WebSocket 服务端
# ─────────────────────────────────────────────────────────────

class WSServer(QObject):
    """
    PC 中控 WebSocket 服务端，监听 8889 端口。

    Signals:
        device_connected(str, dict):     设备认证成功，传递 device_id 和 info
        device_disconnected(str):        设备断开，传递 device_id
        device_message(str, dict):       收到业务消息，传递 device_id 和消息 dict
        server_error(str):               服务端错误描述
        started(int):                    服务启动成功，传递实际监听端口
    """

    device_connected    = Signal(str, dict)
    device_disconnected = Signal(str)
    device_message      = Signal(str, dict)
    server_error        = Signal(str)
    started             = Signal(int)

    def __init__(self, port: int = 8889, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.port = port
        self._server  = None
        self._connections: dict[str, object]  = {}   # device_id → QWebSocket
        self._sock_to_id: dict[object, str]   = {}   # QWebSocket → device_id

    def start(self) -> bool:
        """启动监听，端口冲突时自动尝试 fallback_port（+1）。"""
        try:
            from PySide6.QtWebSockets import QWebSocketServer
        except ImportError:
            logger.error("PySide6.QtWebSockets 不可用，请执行: pip install PySide6-Addons")
            self.server_error.emit("QtWebSockets 模块未安装")
            return False

        self._server = QWebSocketServer(
            "Hive-GreatSage-PCControl",
            QWebSocketServer.SslMode.NonSecureMode,
            self,
        )
        self._server.newConnection.connect(self._on_new_connection)

        for try_port in (self.port, self.port + 1):
            if self._server.listen(QHostAddress.SpecialAddress.AnyIPv4, try_port):
                self.port = try_port
                logger.info("WSServer 启动，监听 0.0.0.0:%d", try_port)
                self.started.emit(try_port)
                return True

        msg = f"端口 {self.port} 和 {self.port + 1} 均被占用"
        logger.error("WSServer 启动失败: %s", msg)
        self.server_error.emit(msg)
        return False

    def stop(self) -> None:
        if self._server:
            self._server.close()
        self._connections.clear()
        self._sock_to_id.clear()

    # ── 内部处理 ─────────────────────────────────

    def _on_new_connection(self) -> None:
        sock = self._server.nextPendingConnection()
        sock.textMessageReceived.connect(lambda msg, s=sock: self._on_message(s, msg))
        sock.disconnected.connect(lambda s=sock: self._on_disconnected(s))
        logger.debug("WSServer: 新连接 %s", sock.peerAddress().toString())

    def _on_message(self, sock, raw: str) -> None:
        try:
            data: dict = json.loads(raw)
        except Exception:
            return

        msg_type = data.get("type")

        if msg_type == "auth":
            device_id = str(data.get("device_id", ""))
            if not device_id:
                self._send(sock, {"type": "auth_failed", "reason": "missing_device_id"})
                sock.close()
                return
            self._connections[device_id] = sock
            self._sock_to_id[sock]       = device_id
            self._send(sock, {"type": "auth_ok"})
            logger.info("WSServer: 设备已认证 device_id=%s", device_id[:16])
            self.device_connected.emit(device_id, data.get("info", {}))
        else:
            device_id = self._sock_to_id.get(sock)
            if device_id:
                self.device_message.emit(device_id, data)

    def _on_disconnected(self, sock) -> None:
        device_id = self._sock_to_id.pop(sock, None)
        if device_id:
            self._connections.pop(device_id, None)
            logger.info("WSServer: 设备断开 device_id=%s", device_id[:16])
            self.device_disconnected.emit(device_id)
        sock.deleteLater()

    # ── 发送 ─────────────────────────────────────

    def _send(self, sock, data: dict) -> None:
        try:
            sock.sendTextMessage(json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.warning("WSServer: 发送失败 %s", e)

    def send_to(self, device_id: str, data: dict) -> bool:
        """向指定设备发送消息。"""
        sock = self._connections.get(device_id)
        if sock and sock.isValid():
            self._send(sock, data)
            return True
        return False

    def broadcast(self, data: dict) -> int:
        """广播给所有已认证设备，返回发送数量。"""
        count = 0
        for sock in list(self._connections.values()):
            if sock.isValid():
                self._send(sock, data)
                count += 1
        return count

    @property
    def connected_count(self) -> int:
        return len(self._connections)

    @property
    def connected_ids(self) -> list[str]:
        return list(self._connections.keys())
