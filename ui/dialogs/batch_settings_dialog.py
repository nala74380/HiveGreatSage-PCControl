r"""
文件位置: ui/dialogs/batch_settings_dialog.py
名称: 批量设置对话框
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.0.0
状态: P5-a 批量设置边界重构第一轮
功能及相关说明:
  多设备批量应用配置入口。
  本对话框替代历史 ui/widgets/batch_dialog.py。

边界说明:
  - 批量设置只处理多设备批量应用配置。
  - 不承载全局设置。
  - 不承载远控 / 投屏 / scrcpy / 公网远控 / Relay 远控。
  - 账号来源只允许：保持不变、手动批量导入、客户外部账号数据库。
  - 未勾选字段不得覆盖。
  - 密码字段默认不批量覆盖；后续实现批量覆盖时必须二次确认。
  - 后端接口未联调前，只做本地预览和草稿，不声称云端应用成功。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
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
    from core.device.models import DeviceInfo
    from core.device.device_manager import DeviceManager

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
QTextEdit, QComboBox {{
    background: {BG_DEEP};
    border: 0.5px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 5px 8px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
}}
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
QTableWidget {{
    background: {BG_DEEP};
    border: 1px solid {BORDER};
    color: {TEXT};
    gridline-color: {BORDER};
}}
QHeaderView::section {{
    background: {BG_PANEL};
    color: {TEXT_MID};
    border: 0.5px solid {BORDER};
    padding: 4px;
}}
"""


class BatchSettingsDialog(QDialog):
    """多设备批量设置对话框。"""

    batch_apply = Signal(list)

    def __init__(self, devices: list["DeviceInfo"], device_manager: "DeviceManager", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._devices = list(devices)
        self._device_manager = device_manager
        self.setStyleSheet(_QSS)
        self.setWindowTitle(f"批量设置 — {len(self._devices)} 台设备")
        self.setFixedSize(1280, 760)
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
        title = QLabel(f"批量设置 · {len(self._devices)} 台设备")
        title.setStyleSheet(f"color:{TEXT}; font-size:13px; font-weight:600;")
        header_lay.addWidget(title)
        header_lay.addSpacing(12)
        scope = QLabel("多设备批量应用配置 / 本地预览阶段")
        scope.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        header_lay.addWidget(scope)
        header_lay.addStretch()
        close_btn = QPushButton("×")
        close_btn.setStyleSheet(f"border:none; background:transparent; color:{TEXT_MUTE}; font-size:18px;")
        close_btn.clicked.connect(self.reject)
        header_lay.addWidget(close_btn)
        root.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_target_page(), "目标设备摘要")
        self._tabs.addTab(self._build_account_page(), "批量账号")
        self._tabs.addTab(self._build_task_page(), "批量任务")
        self._tabs.addTab(self._build_param_page(), "批量参数")
        self._tabs.addTab(self._build_diff_page(), "差异预览")
        self._tabs.addTab(self._build_result_page(), "应用结果")
        root.addWidget(self._tabs)

        footer = QWidget()
        footer.setFixedHeight(52)
        footer.setStyleSheet(f"background:{BG_PANEL}; border-top:1px solid {BORDER};")
        footer_lay = QHBoxLayout(footer)
        footer_lay.setContentsMargins(14, 0, 14, 0)
        footer_lay.setSpacing(8)
        self._status_label = QLabel("P5 第一轮：只生成本地预览与草稿；后端批量应用接口待联调。")
        self._status_label.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        footer_lay.addWidget(self._status_label)
        footer_lay.addStretch()
        preview_btn = QPushButton("生成差异预览")
        preview_btn.clicked.connect(self._generate_preview)
        footer_lay.addWidget(preview_btn)
        draft_btn = QPushButton("保存批量草稿")
        draft_btn.setObjectName("warn-btn")
        draft_btn.clicked.connect(self._save_draft)
        footer_lay.addWidget(draft_btn)
        apply_btn = QPushButton("应用到设备（待联调）")
        apply_btn.setObjectName("save-btn")
        apply_btn.setEnabled(False)
        footer_lay.addWidget(apply_btn)
        close_btn2 = QPushButton("关闭")
        close_btn2.clicked.connect(self.accept)
        footer_lay.addWidget(close_btn2)
        root.addWidget(footer)

    def _build_target_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "目标设备摘要")
        total = len(self._devices)
        online = sum(1 for d in self._devices if d.is_online)
        error = sum(1 for d in self._devices if d.api_status == "error")
        offline = max(total - online, 0)
        form = self._form()
        form.addRow("目标设备数", self._readonly_label(str(total)))
        form.addRow("在线设备", self._readonly_label(str(online)))
        form.addRow("离线设备", self._readonly_label(str(offline)))
        form.addRow("异常设备", self._readonly_label(str(error)))
        lay.addLayout(form)
        lay.addWidget(self._hint("批量设置只作用于当前已勾选设备。每台设备后续必须有成功 / 失败 / 跳过结果。"))
        self._device_table = QTableWidget()
        self._device_table.setColumnCount(5)
        self._device_table.setHorizontalHeaderLabels(["设备编号", "状态", "角色", "区服", "连接标识"])
        self._device_table.setRowCount(total)
        self._device_table.verticalHeader().setVisible(False)
        self._device_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for row, dev in enumerate(self._devices):
            values = [dev.display_id, dev.api_status or "offline", dev.role or "—", dev.server or "—", dev.connection_label or "—"]
            for col, value in enumerate(values):
                self._device_table.setItem(row, col, QTableWidgetItem(str(value)))
        lay.addWidget(self._device_table)
        return page

    def _build_account_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "批量账号")
        lay.addWidget(self._hint("账号是游戏账号，不是 PC 登录账号，也不是 Verify 用户账号。当前只允许：保持不变、手动批量导入、客户外部账号数据库。"))
        form = self._form()
        self._account_enabled = QCheckBox("修改账号来源")
        self._account_source = QComboBox()
        self._account_source.addItem("保持不变", "keep")
        self._account_source.addItem("手动批量导入", "manual_import")
        self._account_source.addItem("客户外部账号数据库", "external_db")
        form.addRow("启用", self._account_enabled)
        form.addRow("账号来源", self._account_source)
        lay.addLayout(form)
        self._account_import_text = QTextEdit()
        self._account_import_text.setPlaceholderText("手动批量导入草稿区。格式后续确认；不得默认记录真实密码到日志。")
        lay.addWidget(self._account_import_text)
        lay.addWidget(self._hint("密码批量覆盖后续必须二次确认；本轮不实现真实覆盖。"))
        lay.addStretch()
        return page

    def _build_task_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "批量任务")
        form = self._form()
        self._task_enabled = QCheckBox("修改任务动作")
        self._task_action = QComboBox()
        self._task_action.addItem("保持不变", "keep")
        self._task_action.addItem("启动任务", "start")
        self._task_action.addItem("停止任务", "stop")
        self._task_action.addItem("重启任务", "restart")
        self._task_action.addItem("切换任务配置", "switch_profile")
        form.addRow("启用", self._task_enabled)
        form.addRow("任务动作", self._task_action)
        lay.addLayout(form)
        lay.addWidget(self._hint("本页只建立批量任务配置入口；真实脚本下发接口待联调。"))
        lay.addStretch()
        return page

    def _build_param_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "批量参数")
        lay.addWidget(self._hint("硬规则：未勾选字段不得覆盖。敏感字段如密码，必须明确勾选且二次确认后才可覆盖。"))
        form = self._form()
        self._role_enabled = QCheckBox("修改账号角色")
        self._role_value = QComboBox()
        for value, label in [("", "保持不变"), ("captain", "队长"), ("power", "战力号"), ("farmer", "打工号"), ("newbie", "新号")]:
            self._role_value.addItem(label, value)
        self._server_enabled = QCheckBox("修改区服")
        self._server_note = QTextEdit()
        self._server_note.setFixedHeight(70)
        self._server_note.setPlaceholderText("区服批量设置草稿；具体字段模型待后续设备配置模型确认。")
        form.addRow("角色字段", self._role_enabled)
        form.addRow("角色新值", self._role_value)
        form.addRow("区服字段", self._server_enabled)
        lay.addLayout(form)
        lay.addWidget(self._server_note)
        lay.addStretch()
        return page

    def _build_diff_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "差异预览")
        lay.addWidget(self._hint("当前为本地预览。未勾选字段不出现在差异表中。"))
        self._diff_table = QTableWidget()
        self._diff_table.setColumnCount(5)
        self._diff_table.setHorizontalHeaderLabels(["设备", "参数", "原值", "新值", "风险提示"])
        self._diff_table.verticalHeader().setVisible(False)
        self._diff_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self._diff_table)
        return page

    def _build_result_page(self) -> QWidget:
        page, lay = self._page()
        self._section(lay, "应用结果")
        lay.addWidget(self._hint("后端接口未联调前，不生成成功结果。当前只显示待联调状态。"))
        self._result_table = QTableWidget()
        self._result_table.setColumnCount(4)
        self._result_table.setHorizontalHeaderLabels(["设备", "结果", "阶段", "说明"])
        self._result_table.setRowCount(len(self._devices))
        self._result_table.verticalHeader().setVisible(False)
        self._result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for row, dev in enumerate(self._devices):
            values = [dev.display_id, "未应用", "待联调", "当前只完成本地预览与草稿"]
            for col, value in enumerate(values):
                self._result_table.setItem(row, col, QTableWidgetItem(value))
        lay.addWidget(self._result_table)
        return page

    def _generate_preview(self) -> None:
        rows: list[tuple[str, str, str, str, str]] = []
        for dev in self._devices:
            if self._account_enabled.isChecked():
                rows.append((dev.display_id, "账号来源", "保持原值", self._account_source.currentText(), "账号字段涉及敏感信息，真实覆盖需二次确认"))
            if self._task_enabled.isChecked():
                rows.append((dev.display_id, "任务动作", "保持原值", self._task_action.currentText(), "真实脚本下发接口待联调"))
            if self._role_enabled.isChecked() and self._role_value.currentData():
                rows.append((dev.display_id, "账号角色", dev.role or "—", self._role_value.currentText(), "本地元数据字段"))
            if self._server_enabled.isChecked():
                rows.append((dev.display_id, "区服", dev.server or "—", "草稿输入", "具体字段模型待确认"))

        self._diff_table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for col, value in enumerate(values):
                self._diff_table.setItem(row, col, QTableWidgetItem(value))
        self._tabs.setCurrentWidget(self._diff_table.parentWidget())
        self._status(f"已生成本地差异预览：{len(rows)} 条。", ok=True)

    def _save_draft(self) -> None:
        draft = {
            "draft_id": f"batch-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "type": "batch_settings_draft",
            "synced": False,
            "synced_at": None,
            "remote_version": None,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "device_ids": [d.device_id for d in self._devices],
            "account": {
                "enabled": self._account_enabled.isChecked(),
                "source": self._account_source.currentData(),
                "import_text_present": bool(self._account_import_text.toPlainText().strip()),
            },
            "task": {
                "enabled": self._task_enabled.isChecked(),
                "action": self._task_action.currentData(),
            },
            "params": {
                "role_enabled": self._role_enabled.isChecked(),
                "role_value": self._role_value.currentData(),
                "server_enabled": self._server_enabled.isChecked(),
            },
            "note": "P5 本地批量草稿；不是最终真相源；后端批量配置接口待联调。",
        }
        path = self._draft_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(draft, f, ensure_ascii=False, indent=2)
        logger.info("批量设置草稿已保存: %s", path)
        self._status(f"本地批量草稿已保存：{path}", ok=True)
        self.batch_apply.emit(self._devices)

    def _draft_path(self) -> Path:
        return Path.home() / ".hive_greatsage" / "pccontrol" / "profiles" / "batch" / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

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

    @staticmethod
    def _readonly_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"background:{BG_ITEM}; color:{TEXT}; border-radius:4px; padding:5px 8px;")
        return lbl

    def _status(self, text: str, ok: bool = False) -> None:
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"color:{TEAL if ok else TEXT_MUTE}; font-size:10px;")
