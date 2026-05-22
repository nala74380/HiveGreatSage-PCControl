r"""
文件位置: ui/dialogs/global_settings_dialog.py
名称: 全局设置弹窗
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.0.0
状态: P2 UI 边界重构执行中
功能及相关说明:
  真正的全局设置弹窗，只承载平台附加能力、客户环境、本地运行环境、日志、更新等。
  不承载游戏账号表、游戏任务参数、物品、交易、制造、铸币等游戏运行配置。

边界说明:
  - 账号设置页里的游戏账号不属于本弹窗。
  - 客户外部账号数据库页只配置连接、字段映射、拉取策略与测试入口。
  - 当前不实现平台托管游戏账号库，不引入无证据账号来源。
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import (
    BG_MAIN,
    BG_PANEL,
    BG_DEEP,
    BG_ITEM,
    BORDER,
    BORDER2,
    BORDER3,
    TEAL,
    TEAL_DK,
    TEAL_BG,
    AMBER,
    AMBER_BG,
    RED,
    TEXT,
    TEXT_MID,
    TEXT_DIM,
    TEXT_MUTE,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)

_QSS = f"""
QDialog {{
    background: {BG_MAIN};
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
    color: {TEXT};
}}
QListWidget {{
    background: {BG_PANEL};
    border: none;
    border-right: 1px solid {BORDER};
    outline: none;
}}
QListWidget::item {{
    padding: 9px 16px;
    color: {TEXT_DIM};
    border-left: 2px solid transparent;
}}
QListWidget::item:hover {{ background: {BG_ITEM}; color: {TEXT_MID}; }}
QListWidget::item:selected {{
    background: #0a1e17;
    color: {TEAL};
    border-left-color: {TEAL_DK};
}}
QLineEdit, QSpinBox, QComboBox {{
    background: {BG_DEEP};
    border: 0.5px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 5px 8px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {TEAL_DK}; }}
QComboBox QAbstractItemView {{
    background: {BG_ITEM};
    border: 0.5px solid {BORDER3};
    selection-background-color: {TEAL_BG};
    color: {TEXT};
    font-size: 10px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; }}
QCheckBox {{ color: {TEXT}; font-size: 11px; spacing: 6px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {BORDER2}; border-radius: 3px; background: transparent;
}}
QCheckBox::indicator:checked {{ background: {TEAL_DK}; border-color: {TEAL_DK}; }}
QPushButton {{
    background: transparent; border: 0.5px solid {BORDER2};
    border-radius: 5px; color: {TEXT_MID};
    padding: 5px 16px; font-family: '{MONO_FONT}', monospace; font-size: 11px;
}}
QPushButton:hover {{ background: {BG_ITEM}; color: {TEXT}; }}
QPushButton#save-btn {{
    background: {TEAL_BG}; border-color: {TEAL_DK}; color: {TEAL};
}}
QPushButton#test-btn {{ border-color: {AMBER_BG}; color: {AMBER}; }}
QPushButton#danger-btn {{ border-color: {RED}; color: {RED}; }}
QLabel#section-head {{
    color: {TEAL};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 8px 0 4px;
    border-bottom: 0.5px solid {BORDER};
}}
QLabel#hint {{ color: {TEXT_MUTE}; font-size: 9px; }}
"""


class GlobalSettingsDialog(QDialog):
    """真正的全局设置弹窗。"""

    def __init__(self, app: "Application", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self.setStyleSheet(_QSS)
        self.setWindowTitle("⚙ 全局设置")
        self.setFixedSize(1200, 820)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        header.setFixedHeight(38)
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(14, 0, 14, 0)
        header_lay.addWidget(QLabel("⚙ 全局设置"))
        header_lay.addStretch()
        close_btn = QPushButton("×")
        close_btn.setStyleSheet(
            f"border:none; background:transparent; color:{TEXT_MUTE}; font-size:18px; padding:0;"
        )
        close_btn.clicked.connect(self.reject)
        header_lay.addWidget(close_btn)
        root.addWidget(header)

        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        self._nav = QListWidget()
        self._nav.setFixedWidth(190)
        self._stack = QStackedWidget()

        tabs = [
            ("服务器连接", self._build_server_page),
            ("网络配置", self._build_network_page),
            ("运行守护", self._build_runtime_page),
            ("客户外部账号数据库", self._build_external_account_db_page),
            ("接码平台", self._build_sms_provider_page),
            ("邮箱服务", self._build_mail_service_page),
            ("ADB 设置", self._build_adb_page),
            ("日志与诊断", self._build_log_page),
            ("更新设置", self._build_update_page),
            ("本地缓存", self._build_cache_page),
        ]
        for name, builder in tabs:
            self._nav.addItem(QListWidgetItem(name))
            self._stack.addWidget(builder())

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav.setCurrentRow(0)
        body_lay.addWidget(self._nav)
        body_lay.addWidget(self._stack)
        root.addWidget(body)

        footer = QWidget()
        footer.setStyleSheet(f"background:{BG_PANEL}; border-top:1px solid {BORDER};")
        footer.setFixedHeight(46)
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(14, 0, 14, 0)
        footer_lay.setSpacing(8)
        self._status_label = QLabel("全局设置只保存平台附加能力与本地运行环境配置。")
        self._status_label.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        footer_lay.addWidget(self._status_label)
        footer_lay.addStretch()
        close_footer_btn = QPushButton("关闭")
        close_footer_btn.clicked.connect(self.reject)
        footer_lay.addWidget(close_footer_btn)
        save_btn = QPushButton("保存全局设置")
        save_btn.setObjectName("save-btn")
        save_btn.clicked.connect(self._save)
        footer_lay.addWidget(save_btn)
        root.addWidget(footer)

    # ── 页面构建 ──────────────────────────────────

    def _build_server_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "服务器连接")
        form = self._form()
        self._api_url_edit = QLineEdit(self._app.config.get("server.api_base_url", ""))
        self._api_url_edit.setPlaceholderText("http://127.0.0.1:8000")
        form.addRow("API 地址", self._api_url_edit)
        self._project_uuid_edit = QLineEdit(self._app.config.get("server.project_uuid", ""))
        form.addRow("项目 UUID", self._project_uuid_edit)
        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(3, 120)
        self._timeout_spin.setValue(int(float(self._app.config.get("server.timeout", 15))))
        self._timeout_spin.setSuffix(" 秒")
        form.addRow("请求超时", self._timeout_spin)
        lay.addLayout(form)
        lay.addWidget(self._hint("这里只配置 PC 客户端连接后端所需信息，不配置游戏账号。"))
        lay.addStretch()
        return page

    def _build_network_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "网络配置")
        self._network_refresh_startup = QCheckBox("启动时刷新网络配置")
        self._network_refresh_startup.setChecked(bool(self._app.config.get("network.refresh_on_startup", True)))
        lay.addWidget(self._network_refresh_startup)
        self._network_refresh_login = QCheckBox("登录后刷新网络配置")
        self._network_refresh_login.setChecked(bool(self._app.config.get("network.refresh_after_login", True)))
        lay.addWidget(self._network_refresh_login)
        self._network_failover = QCheckBox("允许 API 故障切换")
        self._network_failover.setChecked(bool(self._app.config.get("network.allow_failover", True)))
        lay.addWidget(self._network_failover)
        lay.addWidget(self._hint("P2 阶段先迁移已有配置；候选 API 地址编辑器后续单独实现。"))
        lay.addStretch()
        return page

    def _build_runtime_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "自动登录")
        self._auth_auto_login = QCheckBox("启动时使用已保存账号密码自动登录")
        self._auth_auto_login.setChecked(bool(self._app.config.get("auth.auto_login_enabled", False)))
        lay.addWidget(self._auth_auto_login)
        lay.addWidget(self._hint("仅在用户已勾选“记住密码”且系统凭据可读取时生效；切换账号会自动关闭本项。"))

        self._section(lay, "运行守护")
        self._runtime_restart_on_crash = QCheckBox("主程序异常退出后由守护进程自动重启")
        self._runtime_restart_on_crash.setChecked(bool(self._app.config.get("runtime.restart_on_crash", False)))
        lay.addWidget(self._runtime_restart_on_crash)
        form = self._form()
        self._runtime_restart_delay = QSpinBox()
        self._runtime_restart_delay.setRange(3, 300)
        self._runtime_restart_delay.setValue(int(self._app.config.get("runtime.restart_delay_seconds", 5) or 5))
        self._runtime_restart_delay.setSuffix(" 秒")
        form.addRow("重启等待", self._runtime_restart_delay)
        lay.addLayout(form)
        lay.addWidget(self._hint("安装守护任务后，Windows 登录时由 watchdog 启动 PC 中控；直接运行 main.py 时无法在崩溃后自我拉起。"))

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        preview_btn = QPushButton("预演安装")
        preview_btn.setObjectName("test-btn")
        preview_btn.clicked.connect(self._preview_watchdog_task_install)
        action_row.addWidget(preview_btn)

        install_btn = QPushButton("安装/更新守护任务")
        install_btn.setObjectName("save-btn")
        install_btn.clicked.connect(self._install_watchdog_task)
        action_row.addWidget(install_btn)

        uninstall_btn = QPushButton("卸载守护任务")
        uninstall_btn.setObjectName("danger-btn")
        uninstall_btn.clicked.connect(self._uninstall_watchdog_task)
        action_row.addWidget(uninstall_btn)
        action_row.addStretch()
        lay.addLayout(action_row)
        lay.addWidget(self._hint("安装/更新不会立即启动 watchdog，避免当前主平台已运行时双开；卸载只删除计划任务，不删除账号凭据。"))
        lay.addStretch()
        return page

    def _build_external_account_db_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "客户外部账号数据库")
        self._external_db_enabled = QCheckBox("启用客户外部账号数据库")
        self._external_db_enabled.setChecked(bool(self._app.config.get("external_account_db.enabled", False)))
        lay.addWidget(self._external_db_enabled)
        form = self._form()
        self._external_db_driver = QComboBox()
        for label, value in [("HTTP API", "http_api"), ("MySQL", "mysql"), ("PostgreSQL", "postgresql")]:
            self._external_db_driver.addItem(label, value)
        self._set_combo_data(self._external_db_driver, self._app.config.get("external_account_db.driver", "http_api"))
        form.addRow("连接类型", self._external_db_driver)
        self._external_db_host = QLineEdit(self._app.config.get("external_account_db.host", ""))
        form.addRow("主机 / API 地址", self._external_db_host)
        self._external_db_port = QSpinBox()
        self._external_db_port.setRange(0, 65535)
        self._external_db_port.setValue(int(self._app.config.get("external_account_db.port", 0) or 0))
        form.addRow("端口", self._external_db_port)
        self._external_db_name = QLineEdit(self._app.config.get("external_account_db.database", ""))
        form.addRow("数据库名", self._external_db_name)
        self._external_db_username = QLineEdit(self._app.config.get("external_account_db.username", ""))
        form.addRow("用户名", self._external_db_username)
        self._external_db_password_ref = QLineEdit(self._app.config.get("external_account_db.password_ref", ""))
        self._external_db_password_ref.setPlaceholderText("secret ref / keyring ref，不建议明文密码")
        form.addRow("密码引用", self._external_db_password_ref)
        self._external_db_table = QLineEdit(self._app.config.get("external_account_db.table", ""))
        form.addRow("账号表名", self._external_db_table)
        lay.addLayout(form)

        self._section(lay, "字段映射")
        mapping_form = self._form()
        self._map_account = QLineEdit(self._app.config.get("external_account_db.field_mapping.account", ""))
        mapping_form.addRow("游戏账号字段", self._map_account)
        self._map_password = QLineEdit(self._app.config.get("external_account_db.field_mapping.password", ""))
        mapping_form.addRow("游戏密码字段", self._map_password)
        self._map_email = QLineEdit(self._app.config.get("external_account_db.field_mapping.email", ""))
        mapping_form.addRow("验证邮箱字段", self._map_email)
        self._map_email_password = QLineEdit(self._app.config.get("external_account_db.field_mapping.email_password", ""))
        mapping_form.addRow("邮箱密码字段", self._map_email_password)
        self._map_status = QLineEdit(self._app.config.get("external_account_db.field_mapping.status", ""))
        mapping_form.addRow("账号状态字段", self._map_status)
        lay.addLayout(mapping_form)
        lay.addWidget(self._hint("本页只配置客户数据库连接和字段映射，不编辑具体游戏账号。"))
        test_btn = QPushButton("测试连接（待实现）")
        test_btn.setObjectName("test-btn")
        test_btn.clicked.connect(lambda: self._set_status("客户外部账号数据库连接测试属于 P6，本阶段仅保存配置。", warn=True))
        lay.addWidget(test_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addStretch()
        return page

    def _build_sms_provider_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "接码平台")
        self._sms_enabled = QCheckBox("启用接码平台")
        self._sms_enabled.setChecked(bool(self._app.config.get("sms_provider.enabled", False)))
        lay.addWidget(self._sms_enabled)
        form = self._form()
        self._sms_provider = QLineEdit(self._app.config.get("sms_provider.provider", ""))
        form.addRow("平台类型", self._sms_provider)
        self._sms_api_key_ref = QLineEdit(self._app.config.get("sms_provider.api_key_ref", ""))
        form.addRow("API Key 引用", self._sms_api_key_ref)
        self._sms_project_id = QLineEdit(self._app.config.get("sms_provider.project_id", ""))
        form.addRow("项目 ID", self._sms_project_id)
        lay.addLayout(form)
        lay.addWidget(self._hint("接码平台属于附加功能配置，不属于游戏账号表。"))
        lay.addStretch()
        return page

    def _build_mail_service_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "邮箱服务")
        self._mail_enabled = QCheckBox("启用邮箱服务")
        self._mail_enabled.setChecked(bool(self._app.config.get("mail_service.enabled", False)))
        lay.addWidget(self._mail_enabled)
        form = self._form()
        self._imap_host = QLineEdit(self._app.config.get("mail_service.imap_host", ""))
        form.addRow("IMAP 主机", self._imap_host)
        self._imap_port = QSpinBox()
        self._imap_port.setRange(0, 65535)
        self._imap_port.setValue(int(self._app.config.get("mail_service.imap_port", 993) or 993))
        form.addRow("IMAP 端口", self._imap_port)
        self._smtp_host = QLineEdit(self._app.config.get("mail_service.smtp_host", ""))
        form.addRow("SMTP 主机", self._smtp_host)
        self._smtp_port = QSpinBox()
        self._smtp_port.setRange(0, 65535)
        self._smtp_port.setValue(int(self._app.config.get("mail_service.smtp_port", 465) or 465))
        form.addRow("SMTP 端口", self._smtp_port)
        self._mail_credential_ref = QLineEdit(self._app.config.get("mail_service.credential_ref", ""))
        form.addRow("凭据引用", self._mail_credential_ref)
        lay.addLayout(form)
        lay.addStretch()
        return page

    def _build_adb_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "ADB 设置")
        form = self._form()
        self._adb_path = QLineEdit(self._app.config.get("adb.path", ""))
        form.addRow("ADB 路径", self._adb_path)
        self._adb_port = QSpinBox()
        self._adb_port.setRange(1024, 65535)
        self._adb_port.setValue(int(self._app.config.get("adb.default_tcpip_port", 5555) or 5555))
        form.addRow("默认 TCP/IP 端口", self._adb_port)
        self._adb_timeout = QSpinBox()
        self._adb_timeout.setRange(3, 300)
        self._adb_timeout.setValue(int(self._app.config.get("adb.timeout", 15) or 15))
        self._adb_timeout.setSuffix(" 秒")
        form.addRow("命令超时", self._adb_timeout)
        lay.addLayout(form)
        lay.addStretch()
        return page

    def _build_log_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "日志与诊断")
        form = self._form()
        self._log_level = QComboBox()
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            self._log_level.addItem(level, level)
        self._set_combo_data(self._log_level, str(self._app.config.get("log.level", "INFO")).upper())
        form.addRow("日志级别", self._log_level)
        self._log_retention = QSpinBox()
        self._log_retention.setRange(1, 365)
        self._log_retention.setValue(int(self._app.config.get("log.retention_days", 14) or 14))
        self._log_retention.setSuffix(" 天")
        form.addRow("日志保留", self._log_retention)
        lay.addLayout(form)
        self._diagnostic_mask = QCheckBox("导出诊断包时默认脱敏敏感信息")
        self._diagnostic_mask.setChecked(bool(self._app.config.get("log.mask_sensitive_in_diagnostics", True)))
        lay.addWidget(self._diagnostic_mask)
        lay.addStretch()
        return page

    def _build_update_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "更新设置")
        self._update_on_startup = QCheckBox("启动时自动检查更新")
        self._update_on_startup.setChecked(bool(self._app.config.get("update.check_on_startup", True)))
        lay.addWidget(self._update_on_startup)
        form = self._form()
        self._update_channel = QComboBox()
        for label, value in [("稳定版", "stable"), ("测试版", "beta"), ("开发版", "dev")]:
            self._update_channel.addItem(label, value)
        self._set_combo_data(self._update_channel, self._app.config.get("update.channel", "stable"))
        form.addRow("更新通道", self._update_channel)
        self._update_download_dir = QLineEdit(self._app.config.get("update.download_dir", ""))
        form.addRow("下载目录", self._update_download_dir)
        lay.addLayout(form)
        lay.addStretch()
        return page

    def _build_cache_page(self) -> QWidget:
        page, lay = self._scrollable_page()
        self._section(lay, "本地缓存")
        lay.addWidget(self._hint("P2 阶段仅建立入口。清理缓存、临时文件、重建索引等操作后续单独实现。"))
        clear_btn = QPushButton("清理缓存（待实现）")
        clear_btn.setObjectName("danger-btn")
        clear_btn.clicked.connect(lambda: self._set_status("本地缓存清理属于后续阶段，本阶段不执行删除操作。", warn=True))
        lay.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addStretch()
        return page

    # ── 保存 ──────────────────────────────────────

    def _save_runtime_settings(self) -> None:
        cfg = self._app.config
        cfg.set_local("auth.auto_login_enabled", self._auth_auto_login.isChecked())
        cfg.set_local("runtime.restart_on_crash", self._runtime_restart_on_crash.isChecked())
        cfg.set_local("runtime.restart_delay_seconds", self._runtime_restart_delay.value())

    def _save(self) -> None:
        cfg = self._app.config
        cfg.set_local("server.api_base_url", self._api_url_edit.text().strip())
        cfg.set_local("server.project_uuid", self._project_uuid_edit.text().strip())
        cfg.set_local("server.timeout", self._timeout_spin.value())

        cfg.set_local("network.refresh_on_startup", self._network_refresh_startup.isChecked())
        cfg.set_local("network.refresh_after_login", self._network_refresh_login.isChecked())
        cfg.set_local("network.allow_failover", self._network_failover.isChecked())

        self._save_runtime_settings()

        cfg.set_local("external_account_db.enabled", self._external_db_enabled.isChecked())
        cfg.set_local("external_account_db.driver", self._external_db_driver.currentData())
        cfg.set_local("external_account_db.host", self._external_db_host.text().strip())
        cfg.set_local("external_account_db.port", self._external_db_port.value())
        cfg.set_local("external_account_db.database", self._external_db_name.text().strip())
        cfg.set_local("external_account_db.username", self._external_db_username.text().strip())
        cfg.set_local("external_account_db.password_ref", self._external_db_password_ref.text().strip())
        cfg.set_local("external_account_db.table", self._external_db_table.text().strip())
        cfg.set_local("external_account_db.field_mapping.account", self._map_account.text().strip())
        cfg.set_local("external_account_db.field_mapping.password", self._map_password.text().strip())
        cfg.set_local("external_account_db.field_mapping.email", self._map_email.text().strip())
        cfg.set_local("external_account_db.field_mapping.email_password", self._map_email_password.text().strip())
        cfg.set_local("external_account_db.field_mapping.status", self._map_status.text().strip())

        cfg.set_local("sms_provider.enabled", self._sms_enabled.isChecked())
        cfg.set_local("sms_provider.provider", self._sms_provider.text().strip())
        cfg.set_local("sms_provider.api_key_ref", self._sms_api_key_ref.text().strip())
        cfg.set_local("sms_provider.project_id", self._sms_project_id.text().strip())

        cfg.set_local("mail_service.enabled", self._mail_enabled.isChecked())
        cfg.set_local("mail_service.imap_host", self._imap_host.text().strip())
        cfg.set_local("mail_service.imap_port", self._imap_port.value())
        cfg.set_local("mail_service.smtp_host", self._smtp_host.text().strip())
        cfg.set_local("mail_service.smtp_port", self._smtp_port.value())
        cfg.set_local("mail_service.credential_ref", self._mail_credential_ref.text().strip())

        cfg.set_local("adb.path", self._adb_path.text().strip())
        cfg.set_local("adb.default_tcpip_port", self._adb_port.value())
        cfg.set_local("adb.timeout", self._adb_timeout.value())

        cfg.set_local("log.level", self._log_level.currentData())
        cfg.set_local("log.retention_days", self._log_retention.value())
        cfg.set_local("log.mask_sensitive_in_diagnostics", self._diagnostic_mask.isChecked())

        cfg.set_local("update.check_on_startup", self._update_on_startup.isChecked())
        cfg.set_local("update.channel", self._update_channel.currentData())
        cfg.set_local("update.download_dir", self._update_download_dir.text().strip())

        logger.info("全局设置已保存到 config/local.yaml")
        self._set_status("全局设置已保存。部分设置可能需要重启后生效。")

    # ── 运行守护脚本 ──────────────────────────────

    def _preview_watchdog_task_install(self) -> None:
        self._save_runtime_settings()
        self._run_watchdog_task_script("install_watchdog_task.ps1", ["-WhatIf"], "守护任务预演安装完成")

    def _install_watchdog_task(self) -> None:
        reply = QMessageBox.question(
            self,
            "安装/更新守护任务",
            "将注册 Windows 计划任务：用户登录 Windows 后自动启动 PC 中控 watchdog。\n\n"
            "当前不会立即启动 watchdog，避免主平台双开。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._save_runtime_settings()
        self._run_watchdog_task_script("install_watchdog_task.ps1", [], "守护任务已安装/更新")

    def _uninstall_watchdog_task(self) -> None:
        reply = QMessageBox.question(
            self,
            "卸载守护任务",
            "将删除 Windows 计划任务 HiveGreatSage-PCControl-Watchdog。\n\n"
            "这不会删除已保存账号密码，也不会关闭当前正在运行的 PC 中控。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._run_watchdog_task_script("uninstall_watchdog_task.ps1", [], "守护任务卸载检查完成")

    def _run_watchdog_task_script(self, script_name: str, args: list[str], success_text: str) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        script_path = repo_root / "scripts" / script_name
        if not script_path.exists():
            msg = f"守护脚本不存在：{script_path}"
            self._set_status(msg, warn=True)
            QMessageBox.warning(self, "守护脚本不存在", msg)
            return

        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
            *args,
        ]
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                cmd,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
                timeout=30,
            )
        except Exception as exc:
            logger.exception("执行守护脚本失败: %s", script_path)
            msg = f"执行守护脚本失败：{exc}"
            self._set_status(msg, warn=True)
            QMessageBox.warning(self, "守护脚本执行失败", msg)
            return

        output = "\n".join(
            part.strip()
            for part in (result.stdout, result.stderr)
            if part and part.strip()
        )
        if not output:
            output = "脚本未返回输出。"

        if result.returncode != 0:
            msg = f"守护脚本执行失败，退出码：{result.returncode}"
            self._set_status(msg, warn=True)
            QMessageBox.warning(self, "守护脚本执行失败", f"{msg}\n\n{output[:2000]}")
            return

        self._set_status(success_text)
        QMessageBox.information(self, success_text, output[:2000])

    # ── 工具方法 ──────────────────────────────────

    def _scrollable_page(self) -> tuple[QWidget, QVBoxLayout]:
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        inner = QWidget()
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(18, 14, 18, 14)
        inner_lay.setSpacing(8)
        scroll.setWidget(inner)
        outer_lay.addWidget(scroll)
        return outer, inner_lay

    @staticmethod
    def _form() -> QFormLayout:
        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return form

    @staticmethod
    def _section(lay: QVBoxLayout, title: str) -> None:
        lbl = QLabel(title.upper())
        lbl.setObjectName("section-head")
        lay.addWidget(lbl)

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("hint")
        lbl.setWordWrap(True)
        return lbl

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    def _set_status(self, text: str, warn: bool = False) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(
            f"color:{AMBER if warn else TEAL}; font-size:10px;"
        )
        if hasattr(self._app, "post_status"):
            self._app.post_status(text, level="warn" if warn else "ok")
