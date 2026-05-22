r"""
文件位置: ui/dialogs/device_settings/pages/account_settings_page.py
名称: 设备账号设置页
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-19
版本: V1.3.0
状态: P4 账号设置页可用性重排
功能及相关说明:
  DeviceSettingsDialog 的账号设置页。
  当前为单设备游戏账号设置，不是 PC 登录账号，也不是 Verify 用户账号。

边界说明:
  - 账号设置页整体结构按 Ymir-CC 风格组织为：顶部操作区 + 主账号表 + 账号详情区 + 安全提示。
  - 当前账号来源只允许：手动输入、客户外部账号数据库。
  - 当前 P4 第一轮只保留一行账号草稿，不声称账号池 / 客户数据库闭环完成。
  - 密码使用 PasswordEditor，默认隐藏，支持显示 / 隐藏 / 复制 / 编辑 / 右键菜单。
  - 本页不把真实密码写入日志、状态栏、普通诊断包。
  - 当前后端配置保存接口未联调，本页只输出本地草稿摘要。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
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

    enabled: bool
    source: str
    account_type: str
    account: str
    password_present: bool
    email: str
    email_password_present: bool
    region_big: str
    region_small: str
    main_role: str
    profession: str
    last_login_at: str
    last_email_verify_at: str
    account_status: str
    remark: str

    def to_dict(self) -> dict:
        return asdict(self)


class AccountSettingsPage(QWidget):
    """单设备游戏账号设置页。"""

    status_message = Signal(str, bool)

    _COLS = [
        "序号",
        "启用",
        "账号来源",
        "账号类型",
        "游戏账号",
        "游戏密码",
        "验证邮箱",
        "邮箱密码",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._password_editors: list[PasswordEditor] = []
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(9)

        self._section(lay, "游戏账号设置")
        lay.addWidget(self._hint("账号设置页里的账号是游戏账号，不是 PC 登录账号。主账号表只保留高频字段，低频字段放入下方详情区，避免横向挤压。"))
        lay.addWidget(self._build_toolbar())
        self._account_table = self._build_account_table()
        lay.addWidget(self._account_table)
        lay.addWidget(self._build_detail_panel())
        lay.addWidget(self._hint("当前 P4 第一轮只保留一行账号草稿；后续是否支持多账号 / 客户数据库字段映射，必须在 P6 或后续阶段确认。"))
        lay.addWidget(self._hint("真实密码和邮箱密码不会写入本地普通草稿 JSON；草稿只记录 password_present / email_password_present。"))
        lay.addStretch()

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(42)
        bar.setStyleSheet(f"background:{BG_ITEM}; border:0.5px solid {BORDER}; border-radius:5px;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(8, 6, 8, 6)
        lay.setSpacing(8)

        add_btn = self._small_button("新增账号")
        add_btn.setEnabled(False)
        add_btn.setToolTip("P4 第一轮暂不启用多账号，后续基于账号模型确认。")
        remove_btn = self._small_button("删除账号")
        remove_btn.setEnabled(False)
        import_btn = self._small_button("导入账号")
        import_btn.setEnabled(False)
        db_btn = self._small_button("客户数据库")
        db_btn.setEnabled(False)
        db_btn.setToolTip("客户外部账号数据库连接与字段映射属于 P6。")

        show_all_btn = self._small_button("显示全部密码")
        show_all_btn.clicked.connect(self._show_all_passwords)
        hide_all_btn = self._small_button("隐藏全部密码")
        hide_all_btn.clicked.connect(self._hide_all_passwords)
        copy_game_btn = self._small_button("复制游戏密码")
        copy_game_btn.clicked.connect(self._copy_game_password)
        copy_email_btn = self._small_button("复制邮箱密码")
        copy_email_btn.clicked.connect(self._copy_email_password)

        lay.addWidget(add_btn)
        lay.addWidget(remove_btn)
        lay.addWidget(import_btn)
        lay.addWidget(db_btn)
        lay.addStretch()
        lay.addWidget(show_all_btn)
        lay.addWidget(hide_all_btn)
        lay.addWidget(copy_game_btn)
        lay.addWidget(copy_email_btn)
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
        table.setMinimumHeight(122)
        table.setMaximumHeight(136)
        table.setStyleSheet(
            f"QTableWidget {{ background:{BG_DEEP}; color:{TEXT}; border:1px solid {BORDER}; gridline-color:{BORDER}; }}"
            f"QHeaderView::section {{ background:{BG_ITEM}; color:{TEXT_MID}; border:0.5px solid {BORDER}; padding:5px; }}"
            f"QTableWidget::item:selected {{ background:#0a1e17; color:{TEAL}; }}"
        )

        hdr = table.horizontalHeader()
        widths = [48, 58, 150, 110, 170, 310, 170, 300]
        for col, width in enumerate(widths):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)
            table.setColumnWidth(col, width)
        hdr.setStretchLastSection(True)
        table.setRowHeight(0, 52)

        seq = QTableWidgetItem("1")
        seq.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        table.setItem(0, 0, seq)

        self._enabled_combo = QComboBox()
        self._enabled_combo.addItem("启用", True)
        self._enabled_combo.addItem("禁用", False)
        table.setCellWidget(0, 1, self._enabled_combo)

        self._account_source = QComboBox()
        self._account_source.addItem("手动输入", "manual")
        self._account_source.addItem("客户外部账号数据库", "external_db")
        table.setCellWidget(0, 2, self._account_source)

        self._account_type = QComboBox()
        self._account_type.addItem("普通账号", "normal")
        self._account_type.addItem("主号", "main")
        self._account_type.addItem("小号", "alt")
        self._account_type.addItem("工具号", "utility")
        table.setCellWidget(0, 3, self._account_type)

        self._game_account = self._line_edit("游戏账号")
        table.setCellWidget(0, 4, self._game_account)

        self._game_password = PasswordEditor("游戏密码")
        self._game_password.copied.connect(self._on_password_copied)
        self._game_password.visibility_changed.connect(self._on_password_visibility_changed)
        self._password_editors.append(self._game_password)
        table.setCellWidget(0, 5, self._game_password)

        self._game_email = self._line_edit("验证邮箱")
        table.setCellWidget(0, 6, self._game_email)

        self._email_password = PasswordEditor("邮箱密码")
        self._email_password.copied.connect(self._on_password_copied)
        self._email_password.visibility_changed.connect(self._on_password_visibility_changed)
        self._password_editors.append(self._email_password)
        table.setCellWidget(0, 7, self._email_password)

        table.selectRow(0)
        return table

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet(f"background:{BG_ITEM}; border:0.5px solid {BORDER}; border-radius:5px;")
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        self._game_region = self._line_edit("大区")
        self._game_sub_region = self._line_edit("小区")
        self._main_role = self._line_edit("主角色")
        self._profession = self._line_edit("职业")
        self._last_login_at = self._line_edit("上次登录")
        self._last_email_verify_at = self._line_edit("邮件验证")
        self._account_status = QComboBox()
        self._account_status.addItem("未验证", "unknown")
        self._account_status.addItem("可用", "available")
        self._account_status.addItem("异常", "error")
        self._account_status.addItem("停用", "disabled")
        self._remark = self._line_edit("备注")

        self._add_detail_row(grid, 0, 0, "大区", self._game_region)
        self._add_detail_row(grid, 0, 2, "小区", self._game_sub_region)
        self._add_detail_row(grid, 1, 0, "主角色", self._main_role)
        self._add_detail_row(grid, 1, 2, "职业", self._profession)
        self._add_detail_row(grid, 2, 0, "上次登录", self._last_login_at)
        self._add_detail_row(grid, 2, 2, "邮件验证", self._last_email_verify_at)
        self._add_detail_row(grid, 3, 0, "账号状态", self._account_status)
        self._add_detail_row(grid, 3, 2, "备注", self._remark)

        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        return panel

    def draft(self) -> AccountSettingsDraft:
        return AccountSettingsDraft(
            enabled=bool(self._enabled_combo.currentData()),
            source=str(self._account_source.currentData()),
            account_type=str(self._account_type.currentData()),
            account=self._game_account.text().strip(),
            password_present=self._game_password.has_password(),
            email=self._game_email.text().strip(),
            email_password_present=self._email_password.has_password(),
            region_big=self._game_region.text().strip(),
            region_small=self._game_sub_region.text().strip(),
            main_role=self._main_role.text().strip(),
            profession=self._profession.text().strip(),
            last_login_at=self._last_login_at.text().strip(),
            last_email_verify_at=self._last_email_verify_at.text().strip(),
            account_status=str(self._account_status.currentData()),
            remark=self._remark.text().strip(),
        )

    def to_dict(self) -> dict:
        return self.draft().to_dict()

    def from_dict(self, data: dict | None) -> None:
        if not data:
            return
        self._set_combo_data(self._enabled_combo, data.get("enabled"))
        self._set_combo_data(self._account_source, data.get("source"))
        self._set_combo_data(self._account_type, data.get("account_type"))
        self._game_account.setText(str(data.get("account") or ""))
        self._game_email.setText(str(data.get("email") or ""))
        self._game_region.setText(str(data.get("region_big") or ""))
        self._game_sub_region.setText(str(data.get("region_small") or ""))
        self._main_role.setText(str(data.get("main_role") or ""))
        self._profession.setText(str(data.get("profession") or ""))
        self._last_login_at.setText(str(data.get("last_login_at") or ""))
        self._last_email_verify_at.setText(str(data.get("last_email_verify_at") or ""))
        self._set_combo_data(self._account_status, data.get("account_status"))
        self._remark.setText(str(data.get("remark") or ""))

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def real_password(self) -> str:
        """
        返回游戏真实密码。
        当前 P4 第一轮仅供未来受控保存接口使用，不得写入日志、状态栏、普通诊断包。
        """
        return self._game_password.text()

    def real_email_password(self) -> str:
        """
        返回邮箱真实密码。
        当前 P4 第一轮仅供未来受控保存接口使用，不得写入日志、状态栏、普通诊断包。
        """
        return self._email_password.text()

    def _show_all_passwords(self) -> None:
        for editor in self._password_editors:
            editor.show_password()
        self.status_message.emit("密码已显示。", True)

    def _hide_all_passwords(self) -> None:
        for editor in self._password_editors:
            editor.hide_password()
        self.status_message.emit("密码已隐藏。", True)

    def _copy_game_password(self) -> None:
        self._game_password.copy_password()

    def _copy_email_password(self) -> None:
        self._email_password.copy_password()

    def _on_password_copied(self) -> None:
        self.status_message.emit("密码已复制到剪贴板。", True)

    def _on_password_visibility_changed(self, visible: bool) -> None:
        self.status_message.emit("密码已显示。" if visible else "密码已隐藏。", True)

    @staticmethod
    def _add_detail_row(grid: QGridLayout, row: int, col: int, label_text: str, widget: QWidget) -> None:
        label = QLabel(label_text)
        label.setStyleSheet(f"color:{TEXT_MID}; font-size:11px;")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        grid.addWidget(label, row, col)
        grid.addWidget(widget, row, col + 1)

    @staticmethod
    def _line_edit(placeholder: str) -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(28)
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
