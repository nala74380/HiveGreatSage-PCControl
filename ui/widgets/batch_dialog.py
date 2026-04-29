r"""
文件位置: ui/widgets/batch_dialog.py
名称: 批量操作弹窗
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  对多台已勾选设备执行批量设置操作。
  分三个分区：基础设置（角色/区服）/ 任务控制（脚本操作/优先级）/ 激活操作（ADB）。
  参照 main_platform_v2.html 的 ov-batch 弹窗。

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
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import (
    BG_MAIN, BG_PANEL, BG_DEEP, BORDER, BORDER2,
    TEAL, TEAL_DK, TEAL_BG, TEAL_BG2,
    AMBER, AMBER_BG,
    TEXT, TEXT_MID, TEXT_MUTE, TEXT_DARK,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.device.models import DeviceInfo
    from core.device.device_manager import DeviceManager

logger = logging.getLogger(__name__)

_SHELL_CMDS = (
    "adb shell cp /sdcard/Download/proxy /data/local/tmp/proxy\n"
    "adb shell chmod 777 /data/local/tmp/proxy\n"
    "adb shell /data/local/tmp/proxy --daemon"
)

_QSS = f"""
QDialog {{
    background: {BG_MAIN};
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
    color: {TEXT};
}}
QLabel#section-title {{
    color: {TEAL};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
}}
QLabel#shell-block {{
    background: {BG_DEEP};
    color: {TEAL};
    border: 0.5px solid {BORDER};
    border-radius: 5px;
    padding: 8px 10px;
    font-size: 10px;
    line-height: 1.8;
}}
QLabel#warn-note {{ color: {TEXT_MUTE}; font-size: 9px; }}
QWidget#section-card {{
    background: {BG_DEEP};
    border: 0.5px solid {BORDER};
    border-radius: 6px;
}}
QComboBox {{
    background: {BG_DEEP};
    border: 0.5px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 5px 8px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 10px;
}}
QComboBox:focus {{ border-color: {TEAL_DK}; }}
QComboBox QAbstractItemView {{
    background: {BG_PANEL};
    border: 0.5px solid {BORDER2};
    selection-background-color: {TEAL_BG};
    color: {TEXT};
    font-size: 10px;
}}
QPushButton {{
    background: transparent; border: 0.5px solid {BORDER2};
    border-radius: 5px; color: {TEXT_MID};
    padding: 5px 16px; font-family: '{MONO_FONT}', monospace; font-size: 11px;
}}
QPushButton:hover {{ background: {BG_PANEL}; color: {TEXT}; }}
QPushButton#ok-btn {{
    background: {TEAL_BG}; border-color: {TEAL_DK}; color: {TEAL};
}}
QPushButton#ok-btn:hover {{ background: #0F6E56; }}
"""


class BatchDialog(QDialog):
    """
    批量操作弹窗，520×480。

    Signals:
        batch_apply(dict): 用户点击"应用"时触发，传递设置字典
    """

    batch_apply = Signal(dict)

    def __init__(
        self,
        devices: "list[DeviceInfo]",
        device_manager: "DeviceManager",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._devices = devices
        self._manager = device_manager

        self.setStyleSheet(_QSS)
        self.setWindowTitle(f"批量设置 — 已选 {len(devices)} 台设备")
        self.setFixedSize(520, 500)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build()

    # ── UI ───────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 标题栏 ──
        header = QWidget()
        header.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        header.setFixedHeight(38)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 14, 0)
        title_lbl = QLabel(f"批量设置 — 已选 {len(self._devices)} 台设备")
        title_lbl.setStyleSheet(f"color:{TEXT}; font-size:12px;")
        hl.addWidget(title_lbl)
        hl.addStretch()
        close_btn = QPushButton("×")
        close_btn.setStyleSheet(
            f"border:none; background:transparent; color:{TEXT_MUTE}; font-size:16px; padding:0;"
        )
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        root.addWidget(header)

        # ── 内容区 ──
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 12, 14, 12)
        bl.setSpacing(10)

        # 分区1：基础设置
        bl.addWidget(self._section("基础设置", [
            ("账号角色", ["— 不修改 —", "队长", "战力号", "打工号", "新号"], "_role_cb"),
            ("所属区服", ["— 不修改 —", "S1", "S2", "S3", "S4"],          "_server_cb"),
        ]))

        # 分区2：任务控制
        bl.addWidget(self._section("任务控制", [
            ("脚本操作", ["— 不修改 —", "启动脚本", "停止脚本", "重启脚本"], "_script_cb"),
            ("任务优先", ["— 不修改 —", "日常优先", "副本优先", "采集优先"], "_priority_cb"),
        ]))

        # 分区3：激活操作
        act_card = QWidget()
        act_card.setObjectName("section-card")
        al = QVBoxLayout(act_card)
        al.setContentsMargins(12, 10, 12, 10)
        al.setSpacing(8)

        sec_lbl = QLabel("激活操作")
        sec_lbl.setObjectName("section-title")
        al.addWidget(sec_lbl)

        act_mode_row = QHBoxLayout()
        act_mode_row.addWidget(QLabel("激活模式"))
        self._act_mode_cb = QComboBox()
        for t in ["— 不执行 —", "ROOT 激活"]:
            self._act_mode_cb.addItem(t)
        act_mode_row.addWidget(self._act_mode_cb)
        al.addLayout(act_mode_row)

        shell_lbl = QLabel(_SHELL_CMDS)
        shell_lbl.setObjectName("shell-block")
        al.addWidget(shell_lbl)

        warn = QLabel("⚠ 仅对已勾选且通过 ADB 连接的设备执行")
        warn.setObjectName("warn-note")
        al.addWidget(warn)

        bl.addWidget(act_card)
        bl.addStretch()
        root.addWidget(body)

        # ── 底部按钮 ──
        footer = QWidget()
        footer.setStyleSheet(f"background:{BG_PANEL}; border-top:1px solid {BORDER};")
        footer.setFixedHeight(46)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(14, 0, 14, 0)
        fl.setSpacing(8)
        fl.addStretch()
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        fl.addWidget(cancel_btn)
        ok_btn = QPushButton("应用到所选设备")
        ok_btn.setObjectName("ok-btn")
        ok_btn.clicked.connect(self._on_apply)
        fl.addWidget(ok_btn)
        root.addWidget(footer)

    def _section(self, title: str, rows: list) -> QWidget:
        card = QWidget()
        card.setObjectName("section-card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(8)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("section-title")
        cl.addWidget(title_lbl)

        grid = QHBoxLayout()
        grid.setSpacing(12)
        for label_text, items, attr_name in rows:
            col = QVBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:9px; text-transform:uppercase;")
            col.addWidget(lbl)
            cb = QComboBox()
            for t in items:
                cb.addItem(t)
            setattr(self, attr_name, cb)
            col.addWidget(cb)
            grid.addLayout(col)
        cl.addLayout(grid)
        return card

    # ── 应用 ─────────────────────────────────────

    def _on_apply(self) -> None:
        settings: dict = {}

        role = self._role_cb.currentText()
        if role != "— 不修改 —":
            role_map = {"队长": "captain", "战力号": "power",
                        "打工号": "farmer", "新号": "newbie"}
            settings["role"] = role_map.get(role, "")

        server = self._server_cb.currentText()
        if server != "— 不修改 —":
            settings["server"] = server

        script = self._script_cb.currentText()
        if script != "— 不修改 —":
            settings["script_action"] = script

        act_mode = self._act_mode_cb.currentText()
        if act_mode != "— 不执行 —":
            settings["activate"] = True

        if not settings:
            self.reject()
            return

        # 应用元数据变更（role / server）
        for dev in self._devices:
            meta_kwargs = {}
            if "role" in settings:
                meta_kwargs["role"] = settings["role"]
            if meta_kwargs:
                self._manager.update_meta(dev.fingerprint, **meta_kwargs)

        self.batch_apply.emit(settings)
        logger.info("批量设置已应用: %s 台设备 %s", len(self._devices), settings)
        self.accept()
