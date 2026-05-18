r"""
文件位置: ui/dialogs/device_settings_dialog.py
名称: 设备设置弹窗
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-19
版本: V1.2.0
状态: P4 账号设置页密码行为第一轮
功能及相关说明:
  单设备游戏运行配置入口。
  本弹窗承载设备设置，不承载全局设置。
  P3.4-e 新增“本机 ADB 连接”页，用于人工绑定 device_id 与 PC 本机 adb_serial。
  P4 引入 AccountSettingsPage 与 PasswordEditor，账号设置页支持密码默认隐藏、显示、隐藏、复制、编辑。

边界说明:
  - 游戏账号设置属于本弹窗。
  - 本地 profile 只作为草稿/缓存，不是最终真相源。
  - 后端配置保存接口未联调前，不得声称云端配置闭环已完成。
  - ADB 绑定只写入 PC 中控本地 device_adb_links.json，不写 Verify 绑定主键。
  - adb_serial / connection_label 不上传 Verify 作为设备唯一性依据。
  - 真实游戏密码不得写入日志、状态栏、普通诊断包、普通本地草稿 JSON。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.dialogs.device_settings.pages.account_settings_page import AccountSettingsPage
from ui.styles.colors import (
    BG_MAIN,
    BG_PANEL,
    BG_DEEP,
    BG_ITEM,
    BORDER,
    BORDER2,
    TEAL,
    TEAL_DK,
    TEAL_BG,
    AMBER,
    AMBER_BG,
    TEXT,
    TEXT_MID,
    TEXT_MUTE,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.app import Application
    from core.device.models import DeviceInfo

logger = logging.getLogger(__name__)

_QSS = f"""
QDialog {{
    background: {BG_MAIN};
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
    color: {TEXT};
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    background: {BG_MAIN};
}}
QTabBar::tab {{
    background: {BG_PANEL};
    color: {TEXT_MID};
    padding: 8px 14px;
    border: 1px solid {BORDER};
    border-bottom: none;
}}
QTabBar::tab:selected {{
    color: {TEAL};
    background: #0a1e17;
    border-top: 2px solid {TEAL_DK};
}}
QLineEdit, QComboBox, QTextEdit {{
    background: {BG_DEEP};
    border: 0.5px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 5px 8px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
}}
QLineEdit:focus, QComboBox:focus, QTextEdit:focus {{ border-color: {TEAL_DK}; }}
QPushButton {{
    background: transparent;
    border: 0.5px solid {BORDER2};
    border-radius: 5px;
    color: {TEXT_MID};
    padding: 5px 16px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
}}
QPushButton:hover {{ background: {BG_ITEM}; color: {TEXT}; }}
QPushButton#save-btn {{
    background: {TEAL_BG};
    border-color: {TEAL_DK};
    color: {TEAL};
}}
QPushButton#warn-btn {{ border-color: {AMBER_BG}; color: {AMBER}; }}
QLabel#section-head {{
    color: {TEAL};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 8px 0 4px;
    border-bottom: 0.5px solid {BORDER};
}}
QLabel#hint {{ color: {TEXT_MUTE}; font-size: 10px; }}
"""


def _device_key(device: "DeviceInfo") -> str:
    return device.device_id


class DeviceSettingsDialog(QDialog):
    """单设备游戏运行配置弹窗。"""

    meta_saved = Signal(str)
    adb_link_changed = Signal(str)

    def __init__(self, app: "Application", device: "DeviceInfo", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app = app
        self._device = device
        self._meta = self._app.device_manager.get_meta(_device_key(device))
        self.setStyleSheet(_QSS)
        self.setWindowTitle(f"设备设置 — {device.display_id}")
        self.setFixedSize(1400, 850)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(42)
        header.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(14, 0, 14, 0)
        title = QLabel(f"设备设置 · {self._device.display_id}")
        title.setStyleSheet(f"color:{TEXT}; font-size:13px; font-weight:600;")
        header_lay.addWidget(title)
        header_lay.addSpacing(12)
        device_id_label = QLabel(_device_key(self._device))
        device_id_label.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        header_lay.addWidget(device_id_label)
        header_lay.addStretch()
        close_btn = QPushButton("×")
        close_btn.setStyleSheet(f"border:none; background:transparent; color:{TEXT_MUTE}; font-size:18px;")
        close_btn.clicked.connect(self.reject)
        header_lay.addWidget(close_btn)
        root.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_main_page(), "主要设置")
        self._account_page = AccountSettingsPage()
        self._account_page.status_message.connect(self._status)
        self._tabs.addTab(self._account_page, "账号设置")
        self._tabs.addTab(self._build_task_page(), "任务设置")
        self._tabs.addTab(self._placeholder_page("物品处理", "游戏物品处理策略页签骨架，P3 不实现具体字段。"), "物品处理")
        self._tabs.addTab(self._placeholder_page("购买设置", "购买补给策略页签骨架，P3 不实现具体字段。"), "购买设置")
        self._tabs.addTab(self._placeholder_page("交易设置", "交易策略页签骨架，P3 不实现具体字段。"), "交易设置")
        self._tabs.addTab(self._placeholder_page("制造设置", "制造策略页签骨架，P3 不实现具体字段。"), "制造设置")
        self._tabs.addTab(self._placeholder_page("铸币设置", "铸币策略页签骨架，P3 不实现具体字段。"), "铸币设置")
        self._tabs.addTab(self._build_adb_page(), "本机 ADB 连接")
        self._tabs.addTab(self._build_meta_page(), "本地元数据")
        self._tabs.addTab(self._placeholder_page("其他游戏参数", "其他游戏参数页签骨架，P3 不实现具体字段。"), "其他")
        root.addWidget(self._tabs)

        footer = QWidget()
        footer.setFixedHeight(50)
        footer.setStyleSheet(f"background:{BG_PANEL}; border-top:1px solid {BORDER};")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(14, 0, 14, 0)
        footer_lay.setSpacing(8)
        reset_page_btn = QPushButton("重置当前页面（待实现）")
        reset_page_btn.setEnabled(False)
        reset_all_btn = QPushButton("全部重置（待实现）")
        reset_all_btn.setEnabled(False)
        footer_lay.addWidget(reset_page_btn)
        footer_lay.addWidget(reset_all_btn)
        footer_lay.addSpacing(12)
        self._status_label = QLabel("P4：账号设置页密码行为第一轮；后端配置接口待联调。")
        self._status_label.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        footer_lay.addWidget(self._status_label)
        footer_lay.addStretch()
        save_page_btn = QPushButton("保存当前页面草稿")
        save_page_btn.setObjectName("warn-btn")
        save_page_btn.clicked.connect(self._save_current_page_draft)
        footer_lay.addWidget(save_page_btn)
        save_all_btn = QPushButton("全部保存草稿")
        save_all_btn.setObjectName("save-btn")
        save_all_btn.clicked.connect(self._save_all_draft)
        footer_lay.addWidget(save_all_btn)
        close_footer_btn = QPushButton("关闭")
        close_footer_btn.clicked.connect(self.accept)
        footer_lay.addWidget(close_footer_btn)
        root.addWidget(footer)

    # ── Pages ─────────────────────────────────────

    def _build_main_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "运行基础")
        form = self._form()
        self._run_mode = QComboBox()
        for label, value in [("普通运行", "normal"), ("仅登录", "login_only"), ("仅维护", "maintenance")]:
            self._run_mode.addItem(label, value)
        form.addRow("运行模式", self._run_mode)
        self._mainline_mode = QComboBox()
        for label, value in [("保持当前", "keep"), ("启用主线", "enabled"), ("暂停主线", "paused")]:
            self._mainline_mode.addItem(label, value)
        form.addRow("主线任务", self._mainline_mode)
        self._dungeon_mode = QComboBox()
        for label, value in [("保持当前", "keep"), ("启用副本", "enabled"), ("暂停副本", "paused")]:
            self._dungeon_mode.addItem(label, value)
        form.addRow("副本设置", self._dungeon_mode)
        lay.addLayout(form)
        lay.addWidget(self._hint("P3 第一轮只建立字段骨架；具体游戏含义由游戏 fork 后续定义。"))
        lay.addStretch()
        return page

    def _build_task_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "任务设置")
        form = self._form()
        self._task_profile = QLineEdit()
        self._task_profile.setPlaceholderText("任务配置名 / 草稿名")
        form.addRow("任务配置", self._task_profile)
        self._task_note = QTextEdit()
        self._task_note.setPlaceholderText("任务备注，仅作为本地草稿说明。")
        self._task_note.setFixedHeight(120)
        form.addRow("任务备注", self._task_note)
        lay.addLayout(form)
        lay.addWidget(self._hint("任务参数属于设备设置，不属于全局设置。后端保存接口待联调。"))
        lay.addStretch()
        return page

    def _build_adb_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "本机 ADB 连接")
        lay.addWidget(self._hint("本页只维护 PC 中控本地 device_id -> adb_serial 映射。该映射不上传 Verify，不改变设备绑定主键。"))

        form = self._form()
        self._adb_device_id = QLineEdit(_device_key(self._device))
        self._adb_device_id.setReadOnly(True)
        form.addRow("设备编号", self._adb_device_id)

        self._adb_current_label = QLineEdit()
        self._adb_current_label.setReadOnly(True)
        form.addRow("当前绑定", self._adb_current_label)

        self._adb_source_label = QLineEdit()
        self._adb_source_label.setReadOnly(True)
        form.addRow("匹配方式", self._adb_source_label)

        self._adb_combo = QComboBox()
        form.addRow("可选 ADB 设备", self._adb_combo)
        lay.addLayout(form)

        btn_row = QHBoxLayout()
        refresh_btn = QPushButton("刷新 ADB 设备")
        refresh_btn.clicked.connect(self._refresh_adb_devices)
        bind_btn = QPushButton("绑定选中 ADB 设备")
        bind_btn.setObjectName("save-btn")
        bind_btn.clicked.connect(self._bind_selected_adb)
        unbind_btn = QPushButton("解除本机绑定")
        unbind_btn.setObjectName("warn-btn")
        unbind_btn.clicked.connect(self._unbind_adb)
        identity_btn = QPushButton("读取 identity 文件")
        identity_btn.clicked.connect(self._try_read_identity)
        btn_row.addWidget(refresh_btn)
        btn_row.addWidget(bind_btn)
        btn_row.addWidget(unbind_btn)
        btn_row.addWidget(identity_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        lay.addWidget(self._hint("人工绑定优先级最高，会写入 config/device_adb_links.json。identity / LAN IP 自动匹配不会覆盖人工绑定。"))
        lay.addWidget(self._hint("identity 文件路径：/sdcard/HiveGreatSage/device_identity.json；不得包含账号密码、token、游戏密码。"))
        lay.addStretch()

        self._refresh_adb_binding_status()
        self._refresh_adb_devices()
        return page

    def _build_meta_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "本地元数据")
        form = self._form()
        self._alias_edit = QLineEdit(self._meta.get("alias", self._device.device_id))
        form.addRow("显示编号", self._alias_edit)
        self._role_cb = QComboBox()
        for val, label in [
            ("", "— 未设置 —"),
            ("captain", "队长 (Captain)"),
            ("power", "战力号 (Power)"),
            ("farmer", "打工号 (Farmer)"),
            ("newbie", "新号 (Newbie)"),
        ]:
            self._role_cb.addItem(label, val)
        idx = self._role_cb.findData(self._device.role)
        if idx >= 0:
            self._role_cb.setCurrentIndex(idx)
        form.addRow("账号角色", self._role_cb)
        self._note_edit = QLineEdit(self._device.note)
        form.addRow("备注", self._note_edit)
        lay.addLayout(form)
        lay.addWidget(self._hint("本页保存到 device_meta.json，仅为 PC 本地元数据，不是游戏运行参数真相源。"))
        save_meta_btn = QPushButton("保存本地元数据")
        save_meta_btn.setObjectName("save-btn")
        save_meta_btn.clicked.connect(self._save_local_meta)
        lay.addWidget(save_meta_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        lay.addStretch()
        return page

    def _placeholder_page(self, title: str, hint: str) -> QWidget:
        page, lay = self._page()
        self._section(lay, title)
        lay.addWidget(self._hint(hint))
        lay.addWidget(self._hint("该页属于设备设置 / 游戏运行配置，不属于全局设置。"))
        lay.addStretch()
        return page

    # ── ADB Link ──────────────────────────────────

    def _refresh_adb_devices(self) -> None:
        if not hasattr(self, "_adb_combo"):
            return
        self._adb_combo.clear()
        adb_links = getattr(self._app, "adb_links", None)
        if adb_links is None:
            self._adb_combo.addItem("ADB 映射管理器不可用", "")
            return
        devices = adb_links.list_adb_devices()
        if not devices:
            self._adb_combo.addItem("未发现 ADB 设备", "")
            return
        for dev in devices:
            serial = getattr(dev, "serial", "")
            state = getattr(dev, "state", "")
            model = getattr(dev, "model", "") or "—"
            mode = getattr(getattr(dev, "mode", None), "name", "").lower() or ("tcp" if ":" in serial else "usb")
            self._adb_combo.addItem(f"[{mode}] {serial}  {model}  ({state})", serial)

    def _refresh_adb_binding_status(self) -> None:
        if not hasattr(self, "_adb_current_label"):
            return
        adb_links = getattr(self._app, "adb_links", None)
        device_id = _device_key(self._device)
        if adb_links is None:
            self._adb_current_label.setText("ADB 映射管理器不可用")
            self._adb_source_label.setText("—")
            return
        link = adb_links.get_saved_link(device_id)
        if link is None:
            self._adb_current_label.setText("未绑定")
            self._adb_source_label.setText("—")
            return
        status = "冲突" if link.conflict else "已绑定"
        self._adb_current_label.setText(f"{status}: {link.connection_label or link.adb_serial}")
        self._adb_source_label.setText(f"{link.match_method} / {link.match_confidence}")

    def _bind_selected_adb(self) -> None:
        adb_links = getattr(self._app, "adb_links", None)
        if adb_links is None:
            QMessageBox.warning(self, "ADB 绑定失败", "ADB 映射管理器不可用。")
            return
        serial = self._adb_combo.currentData() if hasattr(self, "_adb_combo") else ""
        if not serial:
            QMessageBox.information(self, "提示", "请先选择一个 ADB 设备。")
            return
        device_id = _device_key(self._device)
        adb_links.bind_manual(device_id, serial, note="Manual bind from DeviceSettingsDialog")
        logger.info("设备 ADB 人工绑定: %s -> %s", device_id, serial)
        self._refresh_adb_binding_status()
        self.adb_link_changed.emit(device_id)
        self._status(f"已绑定本机 ADB 设备：{serial}", ok=True)

    def _unbind_adb(self) -> None:
        adb_links = getattr(self._app, "adb_links", None)
        if adb_links is None:
            QMessageBox.warning(self, "ADB 解绑失败", "ADB 映射管理器不可用。")
            return
        device_id = _device_key(self._device)
        adb_links.unbind(device_id)
        logger.info("设备 ADB 本机绑定已解除: %s", device_id)
        self._refresh_adb_binding_status()
        self.adb_link_changed.emit(device_id)
        self._status("本机 ADB 绑定已解除。", ok=True)

    def _try_read_identity(self) -> None:
        adb_links = getattr(self._app, "adb_links", None)
        if adb_links is None:
            QMessageBox.warning(self, "读取失败", "ADB 映射管理器不可用。")
            return
        device_id = _device_key(self._device)
        project_uuid = ""
        config = getattr(self._app, "config", None)
        if config is not None:
            project_uuid = str(config.get("server.project_uuid", "") or "")
        result = adb_links.refresh_identity_links([device_id], project_uuid=project_uuid)
        self._refresh_adb_binding_status()
        self.adb_link_changed.emit(device_id)
        if device_id in result:
            self._status("已通过 ADB identity 文件确认连接映射。", ok=True)
        else:
            self._status("未从已连接 ADB 设备读取到匹配 identity 文件。", ok=False)

    # ── Save ──────────────────────────────────────

    def _save_current_page_draft(self) -> None:
        self._save_draft(scope="current_page")

    def _save_all_draft(self) -> None:
        self._save_draft(scope="all")

    def _save_draft(self, scope: str) -> None:
        device_key = _device_key(self._device)
        account_draft = self._account_page.draft()
        draft = {
            "draft_id": f"device-{device_key[:12]}",
            "device_id": device_key,
            "device_display_id": self._device.display_id,
            "scope": scope,
            "synced": False,
            "synced_at": None,
            "remote_version": None,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "note": "P4 本地草稿；不是最终真相源；后端配置接口待联调；真实密码不写入普通草稿。",
            "main_settings": {
                "run_mode": self._run_mode.currentData(),
                "mainline_mode": self._mainline_mode.currentData(),
                "dungeon_mode": self._dungeon_mode.currentData(),
            },
            "account_settings": {
                "source": account_draft.source,
                "account": account_draft.account,
                "password_present": account_draft.password_present,
                "email": account_draft.email,
                "region": account_draft.region,
            },
            "task_settings": {
                "task_profile": self._task_profile.text().strip(),
                "task_note": self._task_note.toPlainText().strip(),
            },
        }
        path = self._draft_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        logger.info("设备设置草稿已保存: %s", path)
        self._status(f"本地草稿已保存：{path}", ok=True)

    def _save_local_meta(self) -> None:
        device_key = _device_key(self._device)
        self._app.device_manager.update_meta(
            device_key=device_key,
            alias=self._alias_edit.text().strip(),
            role=self._role_cb.currentData() or "",
            note=self._note_edit.text().strip(),
        )
        logger.info("设备本地元数据已保存: %s", device_key[:12])
        self.meta_saved.emit(device_key)
        self._status("本地元数据已保存到 device_meta.json。", ok=True)

    def _draft_path(self) -> Path:
        device_key = _device_key(self._device)
        safe_device_id = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in device_key)
        return Path.home() / ".hive_greatsage" / "pccontrol" / "profiles" / "device" / f"{safe_device_id}.json"

    # ── Helpers ───────────────────────────────────

    @staticmethod
    def _page() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)
        return page, lay

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

    def _status(self, text: str, ok: bool = False) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color:{TEAL if ok else TEXT_MUTE}; font-size:10px;")
