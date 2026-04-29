r"""
文件位置: ui/widgets/team_widget.py
名称: 组队管理页
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  队伍状态卡片网格 + 内网 IP 显示 + WS 服务端状态。
  参照 main_platform_v2.html .team-grid 设计。
  由 TeamManager 管理的 WSServer 实时推送数据刷新。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import (
    BG_MAIN, BG_PANEL, BG_ITEM, BG_DEEP,
    BORDER, BORDER2,
    TEAL, TEAL_DK, TEAL_BG, TEAL_BG2,
    GREEN, GREEN_BG,
    AMBER, AMBER_BG,
    RED, RED_BG,
    TEXT, TEXT2, TEXT_MID, TEXT_DIM, TEXT_MUTE, TEXT_DARK,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)

# 状态颜色
_STATUS_COLORS = {
    "running": (TEAL_BG2, TEAL, "运行中"),
    "idle":    (BG_ITEM,  TEXT_MID, "待机"),
    "error":   (RED_BG,   RED,   "异常"),
}


class TeamWidget(QWidget):
    """组队管理页面。"""

    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app
        self._build()
        # 每 5 秒刷新一次连接状态
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(5000)

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── 顶部工具栏 ──
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        toolbar.setFixedHeight(40)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(12, 0, 12, 0)
        tl.setSpacing(10)

        # 内网 IP + 端口显示
        tl.addWidget(_lbl("内网 IP：", TEXT_MUTE, 9))
        self._ip_cb = QComboBox()
        self._ip_cb.setFixedHeight(24)
        self._ip_cb.setFixedWidth(150)
        self._reload_ips()
        tl.addWidget(self._ip_cb)

        port = self._app.team_manager.ws_server.port
        self._port_lbl = _lbl(f": {port}", TEXT_MID, 11)
        tl.addWidget(self._port_lbl)

        copy_btn = QPushButton("复制地址")
        copy_btn.setStyleSheet(_mini_btn_style())
        copy_btn.clicked.connect(self._copy_address)
        tl.addWidget(copy_btn)

        tl.addWidget(_vsep())

        # WS 服务状态
        self._ws_status_lbl = _lbl("● 等待连接", TEXT_MUTE, 10)
        tl.addWidget(self._ws_status_lbl)

        self._conn_count_lbl = _lbl("已连接：0 台", TEXT_MID, 10)
        tl.addWidget(self._conn_count_lbl)

        tl.addWidget(_vsep())

        # 筛选
        tl.addWidget(_lbl("筛选：", TEXT_MUTE, 9))
        self._filter_cb = QComboBox()
        self._filter_cb.setFixedHeight(24)
        for t in ["全部", "运行中", "待机", "异常"]:
            self._filter_cb.addItem(t)
        self._filter_cb.currentIndexChanged.connect(self._refresh)
        tl.addWidget(self._filter_cb)

        tl.addStretch()
        lay.addWidget(toolbar)

        # ── 卡片网格区 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet(f"background:{BG_MAIN};")
        self._grid = QGridLayout(self._grid_container)
        self._grid.setContentsMargins(12, 12, 12, 12)
        self._grid.setSpacing(10)
        scroll.setWidget(self._grid_container)
        lay.addWidget(scroll)

        # 初始刷新
        self._refresh()

        # 连接 WS 事件
        self._app.team_manager.ws_server.device_connected.connect(
            lambda *_: self._refresh()
        )
        self._app.team_manager.ws_server.device_disconnected.connect(
            lambda *_: self._refresh()
        )

    def _refresh(self) -> None:
        """清空网格并重新渲染已连接成员卡片。"""
        # 清空
        while self._grid.count():
            item = self._grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        members = self._app.team_manager.members
        filt    = self._filter_cb.currentText()
        filt_map = {"运行中": "running", "待机": "idle", "异常": "error"}
        if filt in filt_map:
            members = [m for m in members if m.status == filt_map[filt]]

        count = self._app.team_manager.connected_count
        self._conn_count_lbl.setText(f"已连接：{count} 台")
        if count > 0:
            self._ws_status_lbl.setText("● 已有设备连接")
            self._ws_status_lbl.setStyleSheet(f"color:{TEAL}; font-size:10px;")
        else:
            self._ws_status_lbl.setText("● 监听中，等待连接")
            self._ws_status_lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")

        if not members:
            empty = QLabel("暂无连接的设备\n请在安卓脚本中填写此 PC 的内网 IP 地址")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{TEXT_MUTE}; font-size:12px; line-height:2;")
            self._grid.addWidget(empty, 0, 0)
            return

        cols = 4
        for i, member in enumerate(members):
            card = self._make_card(member)
            self._grid.addWidget(card, i // cols, i % cols)

    def _make_card(self, member) -> QFrame:
        bg, fg, status_text = _STATUS_COLORS.get(member.status, (BG_ITEM, TEXT_MID, member.status))

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{BG_PANEL}; border:0.5px solid {BORDER};"
            f" border-radius:7px; }}"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # 卡片头
        head = QWidget()
        head.setStyleSheet(f"background:{BG_ITEM}; border-radius:7px 7px 0 0;")
        hl   = QHBoxLayout(head)
        hl.setContentsMargins(10, 7, 10, 7)
        name_lbl = _lbl(member.device_name or member.device_id[:12], TEXT2, 11)
        hl.addWidget(name_lbl)
        hl.addStretch()
        status_badge = QLabel(status_text)
        status_badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:7px; padding:2px 7px; font-size:9px;"
        )
        hl.addWidget(status_badge)
        vl.addWidget(head)

        # 卡片体
        body = QWidget()
        bl   = QVBoxLayout(body)
        bl.setContentsMargins(10, 8, 10, 8)
        bl.setSpacing(4)
        bl.addWidget(_kv_row("设备 ID", member.device_id[:16]))
        bl.addWidget(_kv_row("角色",    member.role or "—"))
        bl.addWidget(_kv_row("当前任务", member.current_task or "—"))
        vl.addWidget(body)

        return card

    def _reload_ips(self) -> None:
        from core.team.lan_comm import LanInfo
        ips = LanInfo.get_lan_ips()
        self._ip_cb.clear()
        if ips:
            self._ip_cb.addItems(ips)
        else:
            self._ip_cb.addItem("未检测到内网 IP")

    def _copy_address(self) -> None:
        ip   = self._ip_cb.currentText()
        port = self._app.team_manager.ws_server.port
        addr = f"{ip}:{port}"
        QGuiApplication.clipboard().setText(addr)
        self._ws_status_lbl.setText(f"已复制 {addr}")
        self._ws_status_lbl.setStyleSheet(f"color:{TEAL}; font-size:10px;")


# ─── 工具函数 ─────────────────────────────────────────────────

def _lbl(text: str, color: str, size: int) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(f"color:{color}; font-size:{size}px;")
    return l


def _vsep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background:{BORDER}; border:none;")
    return f


def _mini_btn_style() -> str:
    return (
        f"background:transparent; border:0.5px solid {BORDER2}; border-radius:4px;"
        f" color:{TEXT_MID}; padding:3px 8px; font-family:'{MONO_FONT}',monospace; font-size:10px;"
    )


def _kv_row(key: str, val: str) -> QWidget:
    w  = QWidget()
    hl = QHBoxLayout(w)
    hl.setContentsMargins(0, 0, 0, 0)
    hl.setSpacing(8)
    k = QLabel(key)
    k.setStyleSheet(f"color:{TEXT_MUTE}; font-size:9px; min-width:60px;")
    hl.addWidget(k)
    v = QLabel(val)
    v.setStyleSheet(f"color:{TEXT2}; font-size:11px;")
    hl.addWidget(v)
    hl.addStretch()
    return w
