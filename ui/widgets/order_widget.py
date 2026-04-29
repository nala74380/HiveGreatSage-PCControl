r"""
文件位置: ui/widgets/order_widget.py
名称: 同服订单页
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  显示从设备 game_data 聚合的同服交易订单。
  参照 main_platform_v2.html .order-grid 卡片布局。
  数据来源：DeviceManager 最新 devices 列表的 game_data.orders 字段。
  由 SyncWorker 的 devices_updated 信号刷新。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import (
    BG_MAIN, BG_PANEL, BG_ITEM,
    BORDER, BORDER2,
    TEAL, TEAL_BG2,
    GREEN, GREEN_BG,
    AMBER, AMBER_BG,
    TEXT, TEXT2, TEXT_MID, TEXT_MUTE, TEXT_DARK,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.device.models import DeviceInfo

logger = logging.getLogger(__name__)

_STATUS_STYLE = {
    "pend": (AMBER_BG, AMBER, "挂单中"),
    "sell": (TEAL_BG2, TEAL,  "交易中"),
    "done": (GREEN_BG, GREEN, "已完成"),
}


class OrderWidget(QWidget):
    """同服订单页面。"""

    def __init__(self) -> None:
        super().__init__()
        self._all_orders: list[dict] = []
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── 工具栏 ──
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        toolbar.setFixedHeight(38)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(12, 0, 12, 0)
        tl.setSpacing(8)

        tl.addWidget(_lbl("区服：", TEXT_MUTE, 9))
        self._srv_cb = QComboBox()
        self._srv_cb.setFixedHeight(24)
        for t in ["全部", "S1", "S2", "S3", "S4"]:
            self._srv_cb.addItem(t)
        self._srv_cb.currentIndexChanged.connect(self._render)
        tl.addWidget(self._srv_cb)

        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet(_mini_btn())
        refresh_btn.clicked.connect(self._render)
        tl.addWidget(refresh_btn)

        tl.addWidget(_vsep())

        self._search = QLineEdit()
        self._search.setPlaceholderText("物品名筛选...")
        self._search.setFixedHeight(24)
        self._search.setFixedWidth(140)
        self._search.textChanged.connect(self._render)
        tl.addWidget(self._search)

        tl.addStretch()
        self._count_lbl = _lbl("共 0 条", TEXT_DARK, 10)
        tl.addWidget(self._count_lbl)
        lay.addWidget(toolbar)

        # ── 卡片区 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._card_container = QWidget()
        self._card_container.setStyleSheet(f"background:{BG_MAIN};")
        self._card_grid = QGridLayout(self._card_container)
        self._card_grid.setContentsMargins(12, 12, 12, 12)
        self._card_grid.setSpacing(8)
        scroll.setWidget(self._card_container)
        lay.addWidget(scroll)

    def refresh_from_devices(self, devices: list) -> None:
        """从设备列表的 game_data.orders 字段聚合订单。"""
        orders: list[dict] = []
        for dev in devices:
            for order in dev.game_data.get("orders", []):
                order["_server"] = dev.server or dev.game_data.get("server", "")
                orders.append(order)
        self._all_orders = orders
        self._render()

    def _render(self) -> None:
        # 清空
        while self._card_grid.count():
            item = self._card_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        srv    = self._srv_cb.currentText()
        search = self._search.text().strip().lower()

        filtered = [
            o for o in self._all_orders
            if (srv == "全部" or o.get("_server") == srv)
            and (not search or search in str(o.get("item", "")).lower())
        ]

        if not filtered:
            empty = QLabel("暂无订单数据\n（设备上报的 game_data.orders 将显示于此）")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"color:{TEXT_MUTE}; font-size:12px;")
            self._card_grid.addWidget(empty, 0, 0)
            self._count_lbl.setText("共 0 条")
            return

        self._count_lbl.setText(f"共 {len(filtered)} 条")
        cols = 3
        for i, order in enumerate(filtered):
            card = self._make_card(order)
            self._card_grid.addWidget(card, i // cols, i % cols)

    def _make_card(self, order: dict) -> QFrame:
        status = order.get("status", "pend")
        bg, fg, st_text = _STATUS_STYLE.get(status, (BG_ITEM, TEXT_MID, status))

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background:{BG_PANEL}; border:0.5px solid {BORDER};"
            f" border-radius:7px; }}"
        )
        vl = QVBoxLayout(card)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # 头
        head = QWidget()
        head.setStyleSheet(f"background:{BG_ITEM}; border-radius:7px 7px 0 0;")
        hl   = QHBoxLayout(head)
        hl.setContentsMargins(10, 7, 10, 7)
        item_name = _lbl(str(order.get("item", "未知物品")), TEXT2, 12)
        hl.addWidget(item_name)
        hl.addStretch()
        badge = QLabel(st_text)
        badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:8px; padding:2px 7px; font-size:9px;"
        )
        hl.addWidget(badge)
        time_lbl = _lbl(str(order.get("time", "")), TEXT_MUTE, 9)
        hl.addWidget(time_lbl)
        vl.addWidget(head)

        # 体：2 列网格
        body = QWidget()
        gl   = QGridLayout(body)
        gl.setContentsMargins(10, 8, 10, 8)
        gl.setSpacing(6)
        _add_kv(gl, 0, 0, "单价", _price(order.get("price", 0)), TEAL)
        _add_kv(gl, 0, 1, "卖方", str(order.get("seller", "—")))
        _add_kv(gl, 1, 0, "买方", str(order.get("buyer", "—")))
        _add_kv(gl, 1, 1, "区服", str(order.get("_server", "—")))
        vl.addWidget(body)
        return card


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


def _mini_btn() -> str:
    return (
        f"background:transparent; border:0.5px solid {BORDER2}; border-radius:4px;"
        f" color:{TEXT_MID}; padding:3px 8px; font-family:'{MONO_FONT}',monospace; font-size:10px;"
    )


def _price(val) -> str:
    try:
        return f"¥{int(val):,}"
    except Exception:
        return str(val)


def _add_kv(grid: QGridLayout, row: int, col: int, key: str, val: str, val_color: str = TEXT2) -> None:
    cell = QWidget()
    vl   = QVBoxLayout(cell)
    vl.setContentsMargins(0, 0, 0, 0)
    vl.setSpacing(2)
    k = QLabel(key.upper())
    k.setStyleSheet(f"color:{TEXT_MUTE}; font-size:9px; letter-spacing:0.04em;")
    vl.addWidget(k)
    v = QLabel(val)
    v.setStyleSheet(f"color:{val_color}; font-size:11px; font-weight:500;")
    vl.addWidget(v)
    grid.addWidget(cell, row, col)
