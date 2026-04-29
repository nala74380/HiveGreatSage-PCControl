r"""
文件位置: ui/widgets/price_monitor_widget.py
名称: 跨服价格监控页
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  聚合各区服设备上报的物品价格，找出最低价区服。
  参照 main_platform_v2.html .ptbl 表格布局。
  数据来源：DeviceManager 最新 devices 列表的 game_data.prices 字段。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor

from ui.styles.colors import (
    BG_MAIN, BG_PANEL, BG_ITEM,
    BORDER, BORDER2,
    TEAL, TEAL_BG2,
    GREEN, GREEN_BG,
    TEXT, TEXT2, TEXT_MID, TEXT_MUTE, TEXT_DARK,
    MONO_FONT,
)

logger = logging.getLogger(__name__)

# 最多支持 6 个区服列
_MAX_SERVERS = 6
_SERVERS     = ["S1", "S2", "S3", "S4", "S5", "S6"]


class PriceMonitorWidget(QWidget):
    """跨服价格监控页。"""

    def __init__(self) -> None:
        super().__init__()
        self._price_data: dict[str, dict[str, int]] = {}   # item → {server: price}
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

        add_btn = QPushButton("+ 添加物品")
        add_btn.setStyleSheet(
            f"background:{BG_ITEM}; border:0.5px solid {BORDER2}; border-radius:4px;"
            f" color:{TEXT_MID}; padding:3px 9px; font-size:10px; font-family:'{MONO_FONT}',monospace;"
        )
        tl.addWidget(add_btn)

        tl.addWidget(_vsep())
        tl.addWidget(_lbl("自动刷新：", TEXT_MUTE, 9))
        self._interval_cb = QComboBox()
        self._interval_cb.setFixedHeight(24)
        for t in ["5 分钟", "10 分钟", "手动"]:
            self._interval_cb.addItem(t)
        tl.addWidget(self._interval_cb)

        refresh_btn = QPushButton("立即刷新")
        refresh_btn.setStyleSheet(
            f"background:transparent; border:0.5px solid {BORDER2}; border-radius:4px;"
            f" color:{TEXT_MID}; padding:3px 8px; font-size:10px; font-family:'{MONO_FONT}',monospace;"
        )
        refresh_btn.clicked.connect(self._render)
        tl.addWidget(refresh_btn)

        tl.addStretch()
        self._collect_lbl = _lbl("采集中：0 台设备", TEXT_DARK, 10)
        tl.addWidget(self._collect_lbl)
        lay.addWidget(toolbar)

        # ── 价格表 ──
        body = QWidget()
        body.setStyleSheet(f"background:{BG_MAIN};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(12, 12, 12, 12)

        # 表格容器
        table_frame = QFrame()
        table_frame.setStyleSheet(
            f"QFrame {{ background:{BG_PANEL}; border:0.5px solid {BORDER}; border-radius:7px; }}"
        )
        tfl = QVBoxLayout(table_frame)
        tfl.setContentsMargins(0, 0, 0, 0)

        # 动态列：物品名 + N 个区服 + 最低价区服 + 最后采集
        cols = ["物品名"] + _SERVERS + ["最低价区服", "最后采集"]
        self._table = QTableWidget()
        self._table.setColumnCount(len(cols))
        self._table.setHorizontalHeaderLabels(cols)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.setShowGrid(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {BG_PANEL}; border: none;
                color: {TEXT}; font-size: 11px;
            }}
            QTableWidget::item {{ padding: 8px 12px; border-bottom: 0.5px solid {BG_MAIN}; }}
            QTableWidget::item:hover {{ background: {BG_ITEM}; }}
            QHeaderView::section {{
                background: {BG_ITEM}; color: {TEXT_MUTE}; font-size: 10px;
                padding: 8px 12px; border: none;
                border-bottom: 0.5px solid {BORDER};
            }}
        """)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(cols)):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            self._table.setColumnWidth(i, 100)

        tfl.addWidget(self._table)
        bl.addWidget(table_frame)
        lay.addWidget(body)

        self._render()

    def refresh_from_devices(self, devices: list) -> None:
        """从设备列表的 game_data.prices 字段聚合价格数据。"""
        price_data: dict[str, dict[str, int]] = {}
        active = 0

        for dev in devices:
            prices: list = dev.game_data.get("prices", [])
            if not prices:
                continue
            active += 1
            server = dev.server or dev.game_data.get("server", "")
            for entry in prices:
                item  = str(entry.get("item", ""))
                price = int(entry.get("price", 0) or 0)
                if item:
                    price_data.setdefault(item, {})[server] = price

        self._price_data = price_data
        self._collect_lbl.setText(f"采集中：{active} 台设备")
        self._render()

    def _render(self) -> None:
        items = list(self._price_data.keys())
        self._table.setRowCount(len(items))

        if not items:
            self._table.setRowCount(1)
            self._table.setItem(0, 0, _item("暂无价格数据（设备上报 game_data.prices 后显示）", TEXT_MUTE))
            return

        for row, item_name in enumerate(sorted(items)):
            self._table.setRowHeight(row, 38)
            srv_prices = self._price_data[item_name]

            self._table.setItem(row, 0, _item(item_name, TEXT, bold=True))

            prices_for_min: list[tuple[str, int]] = []
            for col_i, srv in enumerate(_SERVERS, start=1):
                price = srv_prices.get(srv)
                if price:
                    it = _item(f"¥{price:,}", TEXT_MID)
                    prices_for_min.append((srv, price))
                else:
                    it = _item("—", TEXT_MUTE)
                self._table.setItem(row, col_i, it)

            # 最低价区服
            if prices_for_min:
                min_srv, min_price = min(prices_for_min, key=lambda x: x[1])
                # 给最低价格列标绿
                idx = _SERVERS.index(min_srv) + 1
                self._table.item(row, idx).setForeground(QColor(TEAL))
                self._table.item(row, idx).setFont(
                    self._table.item(row, idx).font()
                )
                min_lbl = f"{min_srv}  ¥{min_price:,}"
                self._table.setItem(row, len(_SERVERS) + 1, _item(min_lbl, TEAL))
            else:
                self._table.setItem(row, len(_SERVERS) + 1, _item("—", TEXT_MUTE))

            # 最后采集时间（暂不追踪，预留）
            self._table.setItem(row, len(_SERVERS) + 2, _item("—", TEXT_MUTE))


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


def _item(text: str, color: str = TEXT, bold: bool = False) -> QTableWidgetItem:
    it = QTableWidgetItem(text)
    it.setForeground(QColor(color))
    if bold:
        from PySide6.QtGui import QFont
        font = it.font()
        # PySide6 要求传 QFont.Weight 枚举，不接受裸 int
        font.setWeight(QFont.Weight.DemiBold)   # DemiBold = 600
        it.setFont(font)
    return it
