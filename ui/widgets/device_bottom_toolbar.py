r"""
文件位置: ui/widgets/device_bottom_toolbar.py
名称: 设备管理页底部主操作工具栏
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.0.0
状态: P1 UI 边界重构执行中
功能及相关说明:
  设备管理页底部主操作工具栏。
  按 UI_BOUNDARY.md 约束：主操作区放置在底部；不包含远控、投屏、scrcpy 等入口。
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QWidget

from ui.styles.colors import (
    BORDER,
    BORDER2,
    TEAL,
    TEAL_BG,
    TEAL_DK,
    AMBER,
    AMBER_BG,
    RED,
    RED_BG,
    TEXT,
    TEXT_MID,
    TEXT_MUTE,
    MONO_FONT,
)


class DeviceBottomToolbar(QWidget):
    """设备页底部主操作工具栏。"""

    toggle_all_requested = Signal(bool)
    clear_selection_requested = Signal()
    select_online_requested = Signal()
    select_error_requested = Signal()
    batch_settings_requested = Signal()
    batch_start_requested = Signal()
    batch_stop_requested = Signal()
    batch_restart_requested = Signal()
    batch_activate_requested = Signal()
    batch_unbind_requested = Signal()
    refresh_requested = Signal()
    export_csv_requested = Signal()
    export_diagnostics_requested = Signal()
    open_logs_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("device-bottom-toolbar")
        self.setFixedHeight(48)
        self.setStyleSheet(
            f"QWidget#device-bottom-toolbar {{ background:#111110; border-top:1px solid {BORDER}; }}"
        )
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(8)

        self._chk_all = QCheckBox()
        self._chk_all.setToolTip("全选 / 取消全选")
        self._chk_all.stateChanged.connect(lambda state: self.toggle_all_requested.emit(bool(state)))
        lay.addWidget(self._chk_all)

        lay.addWidget(self._button("反选", self.clear_selection_requested.emit, tooltip="当前阶段暂用作清空选择；后续补反选逻辑"))
        lay.addWidget(self._button("清空选择", self.clear_selection_requested.emit))
        lay.addWidget(self._button("仅选在线", self.select_online_requested.emit))
        lay.addWidget(self._button("仅选异常", self.select_error_requested.emit))
        lay.addWidget(self._sep())

        lay.addWidget(self._button("批量设置", self.batch_settings_requested.emit, style="prim"))
        lay.addWidget(self._button("▶ 启动", self.batch_start_requested.emit))
        lay.addWidget(self._button("■ 停止", self.batch_stop_requested.emit))
        lay.addWidget(self._button("↺ 重启", self.batch_restart_requested.emit))
        lay.addWidget(self._button("⚡ 激活", self.batch_activate_requested.emit, style="warn"))
        lay.addWidget(self._button("解绑", self.batch_unbind_requested.emit, style="danger"))
        lay.addWidget(self._sep())

        lay.addWidget(self._button("刷新", self.refresh_requested.emit))
        lay.addWidget(self._button("导出CSV", self.export_csv_requested.emit))
        lay.addWidget(self._button("导出诊断", self.export_diagnostics_requested.emit))
        lay.addWidget(self._button("打开日志", self.open_logs_requested.emit))
        lay.addStretch()

        self._selected_label = QLabel("已选 0 台")
        self._selected_label.setStyleSheet(f"color:{TEXT_MUTE}; font-size:12px; font-family:'{MONO_FONT}',monospace;")
        lay.addWidget(self._selected_label)

    def set_selected_count(self, count: int) -> None:
        self._selected_label.setText(f"已选 {count} 台")

    def set_all_checked(self, checked: bool) -> None:
        self._chk_all.blockSignals(True)
        self._chk_all.setChecked(checked)
        self._chk_all.blockSignals(False)

    @staticmethod
    def _sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedWidth(1)
        f.setStyleSheet(f"background:{BORDER}; border:none;")
        return f

    @staticmethod
    def _button(text: str, slot, style: str = "", tooltip: str = "") -> QPushButton:
        b = QPushButton(text)
        if tooltip:
            b.setToolTip(tooltip)
        if style == "prim":
            b.setStyleSheet(
                f"background:{TEAL_BG}; border:0.5px solid {TEAL_DK}; color:{TEAL};"
                f" border-radius:5px; padding:4px 11px; font-size:12px; font-family:'{MONO_FONT}',monospace;"
            )
        elif style == "warn":
            b.setStyleSheet(
                f"background:transparent; border:0.5px solid {AMBER_BG}; color:{AMBER};"
                f" border-radius:5px; padding:4px 11px; font-size:12px; font-family:'{MONO_FONT}',monospace;"
            )
        elif style == "danger":
            b.setStyleSheet(
                f"background:transparent; border:0.5px solid {RED_BG}; color:{RED};"
                f" border-radius:5px; padding:4px 11px; font-size:12px; font-family:'{MONO_FONT}',monospace;"
            )
        else:
            b.setStyleSheet(
                f"background:transparent; border:0.5px solid {BORDER2}; color:{TEXT_MID};"
                f" border-radius:5px; padding:4px 11px; font-size:12px; font-family:'{MONO_FONT}',monospace;"
            )
        b.clicked.connect(slot)
        return b
