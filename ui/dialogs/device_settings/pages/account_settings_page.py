r"""
文件位置: ui/dialogs/device_settings/pages/account_settings_page.py
名称: 设备账号设置页
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-19
版本: V1.0.0
状态: P4 账号设置页第一轮
功能及相关说明:
  DeviceSettingsDialog 的账号设置页。
  当前为单设备游戏账号设置，不是 PC 登录账号，也不是 Verify 用户账号。

边界说明:
  - 当前账号来源只允许：手动输入、客户外部账号数据库。
  - 密码使用 PasswordEditor，默认隐藏，支持显示 / 隐藏 / 复制 / 编辑。
  - 本页不把真实密码写入日志、状态栏、普通诊断包。
  - 当前后端配置保存接口未联调，本页只输出本地草稿摘要。
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ui.styles.colors import BORDER, TEAL, TEXT_MUTE
from ui.widgets.account.password_editor import PasswordEditor


@dataclass(frozen=True)
class AccountSettingsDraft:
    """账号设置页本地草稿摘要。真实密码不进入该结构。"""

    source: str
    account: str
    password_present: bool
    email: str
    region: str


class AccountSettingsPage(QWidget):
    """单设备游戏账号设置页。"""

    status_message = Signal(str, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        self._section(lay, "游戏账号设置")
        lay.addWidget(self._hint("账号设置页里的账号是游戏账号，不是 PC 登录账号。当前 P4 第一轮实现密码显示 / 隐藏 / 复制 / 编辑。"))

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._account_source = QComboBox()
        self._account_source.addItem("手动输入", "manual")
        self._account_source.addItem("客户外部账号数据库", "external_db")
        form.addRow("账号来源", self._account_source)

        self._game_account = QLineEdit()
        self._game_account.setPlaceholderText("游戏账号")
        form.addRow("游戏账号", self._game_account)

        self._game_password = PasswordEditor()
        self._game_password.copied.connect(self._on_password_copied)
        self._game_password.visibility_changed.connect(self._on_password_visibility_changed)
        form.addRow("游戏密码", self._game_password)

        self._game_email = QLineEdit()
        form.addRow("验证邮箱", self._game_email)

        self._game_region = QLineEdit()
        form.addRow("区服", self._game_region)

        lay.addLayout(form)
        lay.addWidget(self._hint("当前只允许两类账号来源：手动输入、客户外部账号数据库。不得加入无证据账号来源。"))
        lay.addWidget(self._hint("真实密码不会写入本地草稿 JSON；草稿只记录 password_present。"))
        lay.addStretch()

    def draft(self) -> AccountSettingsDraft:
        return AccountSettingsDraft(
            source=self._account_source.currentData(),
            account=self._game_account.text().strip(),
            password_present=self._game_password.has_password(),
            email=self._game_email.text().strip(),
            region=self._game_region.text().strip(),
        )

    def real_password(self) -> str:
        """
        返回真实密码。
        当前 P4 第一轮仅供未来受控保存接口使用，不得写入日志、状态栏、普通诊断包。
        """
        return self._game_password.text()

    def _on_password_copied(self) -> None:
        self.status_message.emit("密码已复制到剪贴板。", True)

    def _on_password_visibility_changed(self, visible: bool) -> None:
        self.status_message.emit("密码已显示。" if visible else "密码已隐藏。", True)

    @staticmethod
    def _section(lay: QVBoxLayout, title: str) -> None:
        lbl = QLabel(title.upper())
        lbl.setObjectName("section-head")
        lbl.setStyleSheet(
            f"color:{TEAL}; font-size:9px; font-weight:600; letter-spacing:1px; "
            f"padding:8px 0 4px; border-bottom:0.5px solid {BORDER};"
        )
        lay.addWidget(lbl)

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("hint")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        return lbl
