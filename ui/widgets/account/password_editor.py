r"""
文件位置: ui/widgets/account/password_editor.py
名称: 账号密码编辑控件
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-19
版本: V1.1.0
状态: P4 账号设置页密码行为重整
功能及相关说明:
  用于设备设置 / 账号设置页的游戏密码、邮箱密码编辑。
  参考 Ymir-CC 的密码交互：默认掩码，支持显示、隐藏、复制，编辑完成后恢复掩码。

边界说明:
  - 密码默认隐藏。
  - 支持显式显示 / 隐藏按钮。
  - 支持显式复制按钮。
  - 支持右键菜单：显示密码 / 隐藏密码 / 复制密码。
  - 支持编辑真实密码。
  - 编辑完成后恢复隐藏。
  - 不把真实密码写日志。
  - 不把真实密码写状态栏。
  - 不把真实密码写普通诊断包。
  - 本控件不负责持久化真实密码。
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QMenu, QPushButton, QWidget

from ui.styles.colors import BG_DEEP, BORDER, BORDER2, TEAL, TEXT, TEXT_MID, MONO_FONT


class PasswordEditor(QWidget):
    """游戏密码 / 邮箱密码编辑控件。"""

    password_changed = Signal()
    copied = Signal()
    visibility_changed = Signal(bool)

    def __init__(self, placeholder: str = "密码", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._visible = False
        self._placeholder = placeholder
        self._build()
        self.hide_password()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(self._placeholder)
        self._edit.setToolTip("双击/输入可编辑真实密码；离开输入框后自动恢复隐藏。右键可显示、隐藏、复制。")
        self._edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._edit.customContextMenuRequested.connect(self._show_context_menu)
        self._edit.setStyleSheet(
            f"background:{BG_DEEP}; border:0.5px solid {BORDER}; border-radius:4px; "
            f"color:{TEXT}; padding:5px 8px; font-family:'{MONO_FONT}',monospace; font-size:11px;"
        )
        self._edit.textChanged.connect(lambda _: self.password_changed.emit())
        self._edit.editingFinished.connect(self.hide_password)
        lay.addWidget(self._edit, 1)

        self._toggle_btn = QPushButton("显示")
        self._toggle_btn.setFixedWidth(58)
        self._toggle_btn.setToolTip("显示 / 隐藏真实密码。不会写入日志或状态栏。")
        self._toggle_btn.clicked.connect(self.toggle_visibility)
        lay.addWidget(self._toggle_btn)

        self._copy_btn = QPushButton("复制")
        self._copy_btn.setFixedWidth(58)
        self._copy_btn.setToolTip("复制真实密码到剪贴板。提示信息不会包含真实密码。")
        self._copy_btn.clicked.connect(self.copy_password)
        lay.addWidget(self._copy_btn)

        button_qss = (
            f"QPushButton {{ background:transparent; border:0.5px solid {BORDER2}; border-radius:5px; "
            f"color:{TEXT_MID}; padding:5px 8px; font-family:'{MONO_FONT}',monospace; font-size:11px; }}"
            f"QPushButton:hover {{ color:{TEAL}; }}"
        )
        self._toggle_btn.setStyleSheet(button_qss)
        self._copy_btn.setStyleSheet(button_qss)

    def text(self) -> str:
        """返回真实密码。调用方不得写入日志、状态栏、普通诊断包。"""
        return self._edit.text()

    def set_text(self, value: str) -> None:
        self._edit.setText(value or "")
        self.hide_password()

    def has_password(self) -> bool:
        return bool(self._edit.text())

    def clear(self) -> None:
        self._edit.clear()
        self.hide_password()

    def toggle_visibility(self) -> None:
        if self._visible:
            self.hide_password()
        else:
            self.show_password()

    def show_password(self) -> None:
        self._visible = True
        self._edit.setEchoMode(QLineEdit.EchoMode.Normal)
        self._toggle_btn.setText("隐藏")
        self.visibility_changed.emit(True)

    def hide_password(self) -> None:
        self._visible = False
        self._edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._toggle_btn.setText("显示")
        self.visibility_changed.emit(False)

    def copy_password(self) -> None:
        """复制真实密码到剪贴板，但不通过信号携带真实密码。"""
        QGuiApplication.clipboard().setText(self._edit.text())
        self.copied.emit()

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        act_show = menu.addAction("显示密码")
        act_hide = menu.addAction("隐藏密码")
        act_copy = menu.addAction("复制密码")
        chosen = menu.exec(self._edit.mapToGlobal(pos))
        if chosen == act_show:
            self.show_password()
        elif chosen == act_hide:
            self.hide_password()
        elif chosen == act_copy:
            self.copy_password()
