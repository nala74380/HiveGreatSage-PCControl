r"""
文件位置: ui/dialogs/device_settings/pages/account_settings_page.py
名称: 设备账号设置页
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-19
版本: V1.1.0
状态: P4 账号设置页 Ymir-CC 风格结构调整
功能及相关说明:
  DeviceSettingsDialog 的账号设置页。
  当前为单设备游戏账号设置，不是 PC 登录账号，也不是 Verify 用户账号。

边界说明:
  - 账号设置页整体结构按 Ymir-CC 风格调整为：顶部操作区 + 账号表格 + 安全提示。
  - 当前账号来源只允许：手动输入、客户外部账号数据库。
  - 当前 P4 第一轮只保留一行账号草稿，不声称账号池 / 客户数据库闭环完成。
  - 密码使用 PasswordEditor，默认隐藏，支持显示 / 隐藏 / 复制 / 编辑。
  - 本页不把真实密码写入日志、状态栏、普通诊断包。
  - 当前后端配置保存接口未联调，本页只输出本地草稿摘要。
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import BG_DEEP, BG_ITEM, BORDER, BORDER2, TEAL, TEXT, TEXT_MID, TEXT_MUTE, MONO_FONT
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

    _COLS = ["启用", "账号来源", "游戏账号", "游戏密码", "验证邮箱", "邮箱密码", "大区", "小区", "主角色", "职业", "账号状态", "备注"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._password_editors: list[PasswordEditor] = []
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)

        self._section(lay, "游戏账号设置")
        lay.addWidget(self._hint("账号设置页里的账号是游戏账号，不是 PC 登录账号。当前结构按 Ymir-CC 风格调整为账号表格。"))
        lay.addWidget(self._build_toolbar())
        self._account_table = self._build_account_table()
        lay.addWidget(self._account_table)
        lay.addWidget(self._hint("当前 P4 第一轮只保留一行账号草稿；后续是否支持多账号 / 客户数据库字段映射，必须在 P6 或后续阶段确认。"))
        lay.addWidget(self._hint("真实密码不会写入本地草稿 JSON；草稿只记录 password_present。"))
        lay.addStretch()

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(f"background:{BG_ITEM}; border:0.5px solid {BORDER}; border-radius:5px;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        add_btn = self._small_button("新增账号（待实现）")
        add_btn.setEnabled(False)
        remove_btn = self._small_button("删除账号（待实现）")
        remove_btn.setEnabled(False)
        import_btn = self._small_button("导入账号（待实现）")
        import_btn.setEnabled(False)
        db_btn = self._small_button("客户数据库（待P6）")
        db_btn.setEnabled(False)

        show_all_btn = self._small_button("显示密码")
        show_all_btn.clicked.connect(self._show_all_passwords)
        hide_all_btn = self._small_button("隐藏密码")
        hide_all_btn.clicked.connect(self._hide_all_passwords)
        copy_btn = self._small_button("复制当前密码")
        copy_btn.clicked.connect(self._copy_current_password)

        lay.addWidget(add_btn)
        lay.addWidget(remove_btn)
        lay.addWidget(import_btn)
        lay.addWidget(db_btn)
        lay.addStretch()
        lay.addWidget(show_all_btn)
        lay.addWidget(hide_all_btn)
        lay.addWidget(copy_btn)
        return bar

    def _build_account_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(self._COLS))
        table.setHorizontalHeaderLabels(self._COLS)
        table.setRowCount(1)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(False)
        table.setShowGrid(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setMinimumHeight(132)
        table.setMaximumHeight(170)
        table.setStyleSheet(
            f"QTableWidget {{ background:{BG_DEEP}; color:{TEXT}; border:1px solid {BORDER}; gridline-color:{BORDER}; }}"
            f"QHeaderView::section {{ background:{BG_ITEM}; color:{TEXT_MID}; border:0.5px solid {BORDER}; padding:4px; }}"
            f"QTableWidget::item:selected {{ background:#0a1e17; color:{TEAL}; }}"
        )

        hdr = table.horizontalHeader()
        widths = [54, 150, 150, 260, 160, 220, 90, 90, 110, 90, 100, 180]
        for col, width in enumerate(widths):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(col, width)
        hdr.setStretchLastSection(True)

        self._enabled_combo = QComboBox()
        self._enabled_combo.addItem("启用", True)
        self._enabled_combo.addItem("禁用", False)
        table.setCellWidget(0, 0, self._enabled_combo)

        self._account_source = QComboBox()
        self._account_source.addItem("手动输入", "manual")
        self._account_source.addItem("客户外部账号数据库", "external_db")
        table.setCellWidget(0, 1, self._account_source)

        self._game_account = self._line_edit("游戏账号")
        table.setCellWidget(0, 2, self._game_account)

        self._game_password = PasswordEditor()
        self._game_password.copied.connect(self._on_password_copied)
        self._game_password.visibility_changed.connect(self._on_password_visibility_changed)
        self._password_editors.append(self._game_password)
        table.setCellWidget(0, 3, self._game_password)

        self._game_email = self._line_edit("验证邮箱")
        table.setCellWidget(0, 4, self._game_email)

        self._email_password = PasswordEditor()
        self._email_password.copied.connect(self._on_password_copied)
        self._email_password.visibility_changed.connect(self._on_password_visibility_changed)
        self._password_editors.append(self._email_password)
        table.setCellWidget(0, 5, self._email_password)

        self._game_region = self._line_edit("大区")
        table.setCellWidget(0, 6, self._game_region)

        self._game_sub_region = self._line_edit("小区")
        table.setCellWidget(0, 7, self._game_sub_region)

        self._main_role = self._line_edit("主角色")
        table.setCellWidget(0, 8, self._main_role)

        self._job = self._line_edit("职业")
        table.setCellWidget(0, 9, self._job)

        self._account_status = QComboBox()
        self._account_status.addItem("未验证", "unknown")
        self._account_status.addItem("可用", "available")
        self._account_status.addItem("异常", "error")
        self._account_status.addItem("停用", "disabled")
        table.setCellWidget(0, 10, self._account_status)

        self._note = self._line_edit("备注")
        table.setCellWidget(0, 11, self._note)

        table.selectRow(0)
        return table

    def draft(self) -> AccountSettingsDraft:
        return AccountSettingsDraft(
            source=self._account_source.currentData(),
            account=self._game_account.text().strip(),
            password_present=self._game_password.has_password(),
            email=self._game_email.text().strip(),
            region=self._region_text(),
        )

    def real_password(self) -> str:
        """
        返回游戏真实密码。
        当前 P4 第一轮仅供未来受控保存接口使用，不得写入日志、状态栏、普通诊断包。
        """
        return self._game_password.text()

    def _region_text(self) -> str:
        region = self._game_region.text().strip()
        sub_region = self._game_sub_region.text().strip()
        if region and sub_region:
            return f"{region}/{sub_region}"
        return region or sub_region

    def _show_all_passwords(self) -> None:
        for editor in self._password_editors:
            editor.show_password()
        self.status_message.emit("密码已显示。", True)

    def _hide_all_passwords(self) -> None:
        for editor in self._password_editors:
            editor.hide_password()
        self.status_message.emit("密码已隐藏。", True)

    def _copy_current_password(self) -> None:
        # 当前 P4 第一轮只有一行账号，复制游戏密码；不通过状态栏携带真实密码。
        self._game_password.copy_password()

    def _on_password_copied(self) -> None:
        self.status_message.emit("密码已复制到剪贴板。", True)

    def _on_password_visibility_changed(self, visible: bool) -> None:
        self.status_message.emit("密码已显示。" if visible else "密码已隐藏。", True)

    @staticmethod
    def _line_edit(placeholder: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet(
            f"background:{BG_DEEP}; border:0.5px solid {BORDER}; border-radius:4px; "
            f"color:{TEXT}; padding:5px 8px; font-family:'{MONO_FONT}',monospace; font-size:11px;"
        )
        return edit

    @staticmethod
    def _small_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:0.5px solid {BORDER2}; border-radius:5px; "
            f"color:{TEXT_MID}; padding:5px 10px; font-family:'{MONO_FONT}',monospace; font-size:11px; }}"
            f"QPushButton:hover {{ color:{TEAL}; }}"
            f"QPushButton:disabled {{ color:{TEXT_MUTE}; }}"
        )
        return btn

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
