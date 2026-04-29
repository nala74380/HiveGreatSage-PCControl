r"""
文件位置: ui/widgets/device_edit_dialog.py
名称: 单设备编辑弹窗
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  单台设备详情查看 + 可编辑字段（别名/角色/区服/备注）。
  保存后通过 device_manager.update_meta() 持久化到 device_meta.json。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.device.models import DeviceInfo
    from core.device.device_manager import DeviceManager

logger = logging.getLogger(__name__)

# ── 颜色复用（与 main_window.py 保持一致）────────────────────
_C_BG_MAIN   = "#0e0e0c"
_C_BG_PANEL  = "#111110"
_C_BG_ITEM   = "#1a1a18"
_C_BG_INFO   = "#0e0e0c"
_C_BORDER    = "#1e1e1c"
_C_BORDER2   = "#2a2a28"
_C_TEAL      = "#5DCAA5"
_C_TEAL_DK   = "#1D9E75"
_C_TEAL_BG   = "#0A3828"
_C_AMBER     = "#EF9F27"
_C_TEXT      = "#c8c7c0"
_C_TEXT_MID  = "#888780"
_C_TEXT_MUTE = "#444441"

_EDIT_QSS = f"""
QDialog {{
    background: {_C_BG_MAIN};
    font-family: 'Consolas', monospace;
    font-size: 11px;
    color: {_C_TEXT};
}}
QLabel {{
    color: {_C_TEXT};
    font-size: 11px;
}}
QLabel#section {{
    color: {_C_TEAL};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
}}
QFrame#info-card {{
    background: {_C_BG_INFO};
    border: 0.5px solid {_C_BORDER};
    border-radius: 5px;
}}
QLineEdit, QComboBox {{
    background: {_C_BG_INFO};
    border: 0.5px solid {_C_BORDER};
    border-radius: 5px;
    color: {_C_TEXT};
    padding: 5px 8px;
    font-family: 'Consolas', monospace;
    font-size: 11px;
}}
QLineEdit:focus, QComboBox:focus {{
    border-color: {_C_TEAL_DK};
}}
QComboBox QAbstractItemView {{
    background: {_C_BG_ITEM};
    color: {_C_TEXT};
    border: 0.5px solid {_C_BORDER2};
    selection-background-color: {_C_TEAL_BG};
}}
QPushButton {{
    background: transparent;
    border: 0.5px solid {_C_BORDER2};
    border-radius: 5px;
    color: {_C_TEXT_MID};
    padding: 5px 16px;
    font-family: 'Consolas', monospace;
    font-size: 11px;
}}
QPushButton:hover {{
    background: {_C_BG_ITEM};
    color: {_C_TEXT};
}}
QPushButton#ok-btn {{
    background: {_C_TEAL_BG};
    border-color: {_C_TEAL_DK};
    color: {_C_TEAL};
}}
QPushButton#ok-btn:hover {{
    background: #0F6E56;
}}
"""


class DeviceEditDialog(QDialog):
    """
    单设备编辑弹窗，500×420 固定大小。

    Signals:
        meta_saved(str): 保存成功后触发，传递 fingerprint
    """

    meta_saved = Signal(str)   # fingerprint

    def __init__(
        self,
        device: "DeviceInfo",
        device_manager: "DeviceManager",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._device  = device
        self._manager = device_manager

        self.setStyleSheet(_EDIT_QSS)
        self.setWindowTitle(f"设备详情 — {device.display_id}")
        self.setFixedSize(500, 420)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        self._build()

    # ── UI ───────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 14)
        root.setSpacing(12)

        # ── 信息卡片（只读）──
        root.addWidget(self._build_info_card())

        # ── 可编辑字段 ──
        section_edit = QLabel("可编辑字段")
        section_edit.setObjectName("section")
        root.addWidget(section_edit)

        form = QFormLayout()
        form.setSpacing(8)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._alias_edit = QLineEdit(self._device.alias)
        self._alias_edit.setPlaceholderText("如 A-001")
        form.addRow("显示编号", self._alias_edit)

        self._role_cb = QComboBox()
        for val, label in [
            ("", "— 未设置 —"),
            ("captain", "队长 (Captain)"),
            ("power",   "战力号 (Power)"),
            ("farmer",  "打工号 (Farmer)"),
            ("newbie",  "新号 (Newbie)"),
        ]:
            self._role_cb.addItem(label, val)
        idx = self._role_cb.findData(self._device.role)
        if idx >= 0:
            self._role_cb.setCurrentIndex(idx)
        form.addRow("账号角色", self._role_cb)

        self._note_edit = QLineEdit(self._device.note)
        self._note_edit.setPlaceholderText("可选备注...")
        form.addRow("备注", self._note_edit)

        root.addLayout(form)
        root.addStretch()

        # ── 底部按钮 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("保存")
        ok_btn.setObjectName("ok-btn")
        ok_btn.clicked.connect(self._on_save)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def _build_info_card(self) -> QWidget:
        """只读信息卡片（设备指纹/状态/最后心跳等）。"""
        card = QFrame()
        card.setObjectName("info-card")
        g = QGridLayout(card)
        g.setContentsMargins(12, 10, 12, 10)
        g.setSpacing(8)

        def _kv(row: int, key: str, val: str, val_color: str = _C_TEXT) -> None:
            k = QLabel(key)
            k.setStyleSheet(f"color:{_C_TEXT_MUTE}; font-size:9px; text-transform:uppercase;")
            v = QLabel(val)
            v.setStyleSheet(f"color:{val_color}; font-size:11px;")
            g.addWidget(k, row, 0)
            g.addWidget(v, row, 1)

        dev = self._device
        status_color = {
            "running": _C_TEAL, "idle": "#888780",
            "error": "#F7C1C1", "offline": "#5F5E5A",
        }.get(dev.api_status, _C_TEXT_MID)

        _kv(0, "设备指纹",  dev.fingerprint, _C_TEXT_MID)
        _kv(1, "状态",      dev.api_status or "offline", status_color)
        _kv(2, "在线",      "是" if dev.is_online else "否",
            _C_TEAL if dev.is_online else _C_TEXT_MUTE)
        _kv(3, "最后心跳",  dev.heartbeat_str)
        _kv(4, "等级 / 战力",
            f"Lv.{dev.level}  /  {dev.combat_power:,}" if dev.level else "—")
        _kv(5, "当前任务",  dev.task or "—")

        return card

    # ── 保存 ────────────────────────────────────

    def _on_save(self) -> None:
        alias = self._alias_edit.text().strip()
        role  = self._role_cb.currentData() or ""
        note  = self._note_edit.text().strip()

        self._manager.update_meta(
            fingerprint=self._device.fingerprint,
            alias=alias,
            role=role,
            note=note,
        )
        logger.info("设备元数据已保存: %s alias=%s role=%s", self._device.fingerprint[:12], alias, role)
        self.meta_saved.emit(self._device.fingerprint)
        self.accept()
