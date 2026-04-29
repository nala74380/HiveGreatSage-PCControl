r"""
文件位置: ui/widgets/update_dialog.py
名称: 热更新提示弹窗
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  检测到新版本时弹出，显示版本号/更新说明/强制标记。
  非强制更新允许跳过；强制更新只显示"立即更新"按钮。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import (
    BG_MAIN, BG_PANEL, BORDER, BORDER2,
    TEAL, TEAL_DK, TEAL_BG,
    AMBER, AMBER_BG,
    TEXT, TEXT_MID, TEXT_MUTE,
    MONO_FONT,
)

logger = logging.getLogger(__name__)

_QSS = f"""
QDialog {{
    background: {BG_MAIN};
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
    color: {TEXT};
}}
QLabel#version-badge {{
    background: {TEAL_BG}; color: {TEAL};
    border: 0.5px solid {TEAL_DK};
    border-radius: 4px; padding: 3px 10px; font-size: 11px;
}}
QLabel#force-badge {{
    background: {AMBER_BG}; color: {AMBER};
    border: 0.5px solid #633806;
    border-radius: 4px; padding: 3px 10px; font-size: 11px;
}}
QLabel#notes {{
    background: {BG_PANEL}; color: {TEXT_MID};
    border: 0.5px solid {BORDER};
    border-radius: 5px; padding: 10px; font-size: 11px; line-height: 1.7;
}}
QPushButton {{
    background: transparent; border: 0.5px solid {BORDER2};
    border-radius: 5px; color: {TEXT_MID};
    padding: 6px 18px; font-family: '{MONO_FONT}', monospace; font-size: 11px;
}}
QPushButton:hover {{ background: {BG_PANEL}; color: {TEXT}; }}
QPushButton#update-btn {{
    background: {TEAL_BG}; border-color: {TEAL_DK}; color: {TEAL};
}}
QPushButton#update-btn:hover {{ background: #0F6E56; }}
"""


class UpdateDialog(QDialog):
    """热更新提示弹窗，480×320。"""

    def __init__(
        self,
        new_version: str,
        current_version: str,
        release_notes: str = "",
        force_update: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._new_version  = new_version
        self._force_update = force_update

        self.setStyleSheet(_QSS)
        self.setWindowTitle("发现新版本")
        self.setFixedSize(480, 340)
        flags = Qt.WindowType.Dialog
        if force_update:
            flags &= ~Qt.WindowType.WindowCloseButtonHint
        else:
            flags |= Qt.WindowType.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self._build(new_version, current_version, release_notes, force_update)

    def _build(
        self,
        new_ver: str,
        cur_ver: str,
        notes: str,
        force: bool,
    ) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # ── 标题行 ──
        title_row = QHBoxLayout()
        title_lbl = QLabel("发现新版本")
        title_lbl.setStyleSheet(f"color:{TEXT}; font-size:14px; font-weight:600;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        ver_badge = QLabel(f"v{new_ver}")
        ver_badge.setObjectName("version-badge")
        title_row.addWidget(ver_badge)
        if force:
            force_badge = QLabel("强制更新")
            force_badge.setObjectName("force-badge")
            title_row.addWidget(force_badge)
        root.addLayout(title_row)

        # ── 版本说明 ──
        cur_lbl = QLabel(f"当前版本：v{cur_ver}  →  新版本：v{new_ver}")
        cur_lbl.setStyleSheet(f"color:{TEXT_MID}; font-size:11px;")
        root.addWidget(cur_lbl)

        # ── 更新日志 ──
        notes_text = notes or "（暂无更新说明）"
        notes_lbl = QLabel(notes_text)
        notes_lbl.setObjectName("notes")
        notes_lbl.setWordWrap(True)
        root.addWidget(notes_lbl)

        root.addStretch()

        # ── 按钮行 ──
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if not force:
            skip_btn = QPushButton("稍后再说")
            skip_btn.clicked.connect(self.reject)
            btn_row.addWidget(skip_btn)

        update_btn = QPushButton("立即更新")
        update_btn.setObjectName("update-btn")
        update_btn.clicked.connect(self.accept)
        btn_row.addWidget(update_btn)

        root.addLayout(btn_row)

        if force:
            warn = QLabel("⚠ 此版本为强制更新，必须更新后才能继续使用")
            warn.setStyleSheet(f"color:{AMBER}; font-size:10px;")
            warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            root.addWidget(warn)
