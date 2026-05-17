r"""
文件位置: ui/pages/device_page.py
名称: 设备管理页
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.0.0
状态: P1 UI 边界重构执行中
功能及相关说明:
  从历史 main_window.py 中拆出的设备管理页。
  P1 目标：筛选栏在上，设备表格在中，右侧中控侧栏，底部主操作工具栏。
  本文件不包含远控、投屏、scrcpy、公网远控、Relay 远控等能力。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.device.models import DeviceInfo
from ui.widgets.device_bottom_toolbar import DeviceBottomToolbar
from ui.widgets.device_side_panel import DeviceSidePanel

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)

# P1 低风险拆分：暂在本页保留设备页专用颜色与辅助函数，后续再统一迁移到 ui.styles。
C_BG_MAIN = "#0e0e0c"
C_BG_PANEL = "#111110"
C_BG_ITEM = "#1a1a18"
C_BG_HOVER = "#141412"
C_BG_SEL = "#071f16"
C_BORDER = "#1e1e1c"
C_BORDER2 = "#2a2a28"
C_TEAL = "#5DCAA5"
C_TEAL_BG2 = "#04342C"
C_GREEN = "#97C459"
C_GREEN_BG = "#173404"
C_AMBER = "#EF9F27"
C_RED = "#F7C1C1"
C_RED_BG = "#501313"
C_TEXT = "#c8c7c0"
C_TEXT2 = "#B4B2A9"
C_TEXT_MID = "#888780"
C_TEXT_DIM = "#5F5E5A"
C_TEXT_MUTE = "#444441"
MONO_FONT = "Consolas"

_DEV_COLS = ["", "编号", "序列号", "角色", "状态", "激活", "当前任务", "等级", "战力", "区服", "心跳", "备注"]
_STATUS_MAP = {
    "running": (C_TEAL_BG2, C_TEAL, "运行中"),
    "idle": (C_BG_ITEM, C_TEXT_MID, "在线"),
    "error": (C_RED_BG, C_RED, "异常"),
    "offline": (C_BG_ITEM, C_TEXT_DIM, "离线"),
}
_ROLE_MAP = {
    "captain": ("#26215C", "#AFA9EC", "队长"),
    "power": (C_TEAL_BG2, C_TEAL, "战力"),
    "farmer": (C_GREEN_BG, C_GREEN, "打工"),
    "newbie": (C_BG_ITEM, C_TEXT_MID, "新号"),
}


def _badge(text: str, bg: str, fg: str, font_size: int = 11) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; border-radius:8px;"
        f" padding:2px 8px; font-size:{font_size}px;"
    )
    return lbl


def _sep_v() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background:{C_BORDER}; border:none;")
    return f


def _label(text: str, color: str = C_TEXT_MUTE, size: int = 12) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color}; font-size:{size}px;")
    return lbl


class ActivateWorker(QThread):
    """ADB 激活线程。"""

    finished = Signal(str, bool, str)

    def __init__(self, adb, serial: str) -> None:
        super().__init__()
        self._adb = adb
        self._serial = serial

    def run(self) -> None:
        ok, msg = self._adb.activate_device(self._serial)
        self.finished.emit(self._serial, ok, msg)


class DevicePage(QWidget):
    """设备管理页：筛选栏 + 表格/右侧栏 + 底部主操作工具栏。"""

    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app
        self._devices: list[DeviceInfo] = []
        self._visible_devices: list[DeviceInfo] = []
        self._activate_workers: list[ActivateWorker] = []
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_filter_bar())

        center = QWidget()
        center_lay = QHBoxLayout(center)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(0)
        self._table = self._build_table()
        center_lay.addWidget(self._table)
        self._side_panel = DeviceSidePanel()
        center_lay.addWidget(self._side_panel)
        root.addWidget(center)

        self._bottom_toolbar = DeviceBottomToolbar()
        self._connect_bottom_toolbar()
        root.addWidget(self._bottom_toolbar)

    def _build_filter_bar(self) -> QWidget:
        fb = QWidget()
        fb.setObjectName("filterbar")
        fb.setFixedHeight(38)
        fb.setStyleSheet(f"background:{C_BG_PANEL}; border-bottom:1px solid {C_BORDER};")
        fl = QHBoxLayout(fb)
        fl.setContentsMargins(12, 0, 12, 0)
        fl.setSpacing(10)
        fl.addWidget(_label("筛选：", C_TEXT_MUTE, 11))

        self._f_search = QLineEdit()
        self._f_search.setPlaceholderText("编号 / 序列号 / 区服...")
        self._f_search.setFixedWidth(220)
        self._f_search.setFixedHeight(26)
        self._f_search.textChanged.connect(self._apply_filters)
        fl.addWidget(self._f_search)

        self._f_status = QComboBox()
        self._f_status.setFixedHeight(26)
        for text in ["全部状态", "运行中", "在线", "离线", "异常"]:
            self._f_status.addItem(text)
        self._f_status.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self._f_status)

        self._f_role = QComboBox()
        self._f_role.setFixedHeight(26)
        for text in ["全部角色", "队长", "战力号", "打工号", "新号"]:
            self._f_role.addItem(text)
        self._f_role.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self._f_role)

        fl.addStretch()
        self._row_lbl = _label("0 台设备", C_TEXT_DIM, 11)
        fl.addWidget(self._row_lbl)
        return fb

    def _build_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(_DEV_COLS))
        table.setHorizontalHeaderLabels(_DEV_COLS)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setHighlightSections(False)
        table.setShowGrid(False)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)
        table.cellDoubleClicked.connect(self._on_double_click)
        table.itemSelectionChanged.connect(self._update_selection_summary)

        hdr = table.horizontalHeader()
        col_widths = [36, 80, 140, 70, 80, 65, 0, 65, 90, 55, 90, 110]
        for i, width in enumerate(col_widths):
            if width == 0:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                table.setColumnWidth(i, width)
        return table

    def _connect_bottom_toolbar(self) -> None:
        tb = self._bottom_toolbar
        tb.toggle_all_requested.connect(self._set_all_checked)
        tb.invert_selection_requested.connect(self._invert_selection)
        tb.clear_selection_requested.connect(self._clear_selection)
        tb.select_online_requested.connect(lambda: self._select_by_predicate(lambda d: d.is_online))
        tb.select_error_requested.connect(lambda: self._select_by_predicate(lambda d: d.api_status == "error"))
        tb.batch_settings_requested.connect(self._open_batch_dialog)
        tb.batch_start_requested.connect(lambda: self._phase_hint("批量启动"))
        tb.batch_stop_requested.connect(lambda: self._phase_hint("批量停止"))
        tb.batch_restart_requested.connect(lambda: self._phase_hint("批量重启"))
        tb.batch_activate_requested.connect(self._batch_activate_selected)
        tb.batch_unbind_requested.connect(lambda: self._phase_hint("批量解绑"))
        tb.refresh_requested.connect(self._request_refresh)
        tb.export_csv_requested.connect(lambda: self._phase_hint("导出CSV"))
        tb.export_diagnostics_requested.connect(lambda: self._phase_hint("导出诊断"))
        tb.open_logs_requested.connect(self._open_log_viewer)

    # ── 数据 ──────────────────────────────────────

    def refresh_devices(self, devices: list[DeviceInfo]) -> None:
        self._devices = devices
        self._apply_filters()

    def _apply_filters(self) -> None:
        search = self._f_search.text().strip().lower()
        status_text = self._f_status.currentText()
        role_text = self._f_role.currentText()
        status_map = {"运行中": "running", "在线": "idle", "离线": "offline", "异常": "error"}
        role_map = {"队长": "captain", "战力号": "power", "打工号": "farmer", "新号": "newbie"}

        filtered = [
            d for d in self._devices
            if (not search or search in d.display_id.lower()
                or search in d.fingerprint.lower()
                or search in d.server.lower())
            and (status_text == "全部状态" or d.api_status == status_map.get(status_text, ""))
            and (role_text == "全部角色" or d.role == role_map.get(role_text, ""))
        ]
        self._visible_devices = filtered
        self._populate_table(filtered)
        self._row_lbl.setText(f"{len(filtered)} 台设备")
        self._side_panel.update_devices(self._devices, filtered)
        self._update_selection_summary()

    def _populate_table(self, devices: list[DeviceInfo]) -> None:
        self._table.setRowCount(len(devices))
        for row, dev in enumerate(devices):
            self._table.setRowHeight(row, 40)

            chk_w = QWidget()
            chk = QCheckBox()
            chk.stateChanged.connect(lambda _=None: self._update_selection_summary())
            cl = QHBoxLayout(chk_w)
            cl.addWidget(chk)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, 0, chk_w)

            self._table.setItem(row, 1, self._item(dev.display_id, C_TEXT))
            self._table.setItem(row, 2, self._item(dev.fingerprint[:20], C_TEXT_MID))

            if dev.role in _ROLE_MAP:
                bg, fg, text = _ROLE_MAP[dev.role]
                self._set_badge_cell(row, 3, text, bg, fg)
            else:
                self._table.setItem(row, 3, self._item("—", C_TEXT_MUTE))

            st = dev.api_status or "offline"
            if st in _STATUS_MAP:
                bg, fg, text = _STATUS_MAP[st]
                self._set_badge_cell(row, 4, text, bg, fg)

            act_text = "已激活" if dev.activated else "未激活"
            self._set_badge_cell(
                row, 5, act_text,
                C_TEAL_BG2 if dev.activated else C_BG_ITEM,
                C_TEAL if dev.activated else C_TEXT_DIM,
            )

            self._table.setItem(row, 6, self._item(dev.task or "—", C_TEXT_MID))
            self._table.setItem(row, 7, self._item(f"Lv.{dev.level}" if dev.level else "—", C_TEXT, Qt.AlignmentFlag.AlignCenter))
            self._table.setItem(row, 8, self._item(f"{dev.combat_power:,}" if dev.combat_power else "—", C_TEXT2, Qt.AlignmentFlag.AlignCenter))
            self._table.setItem(row, 9, self._item(dev.server or "—", C_TEXT_MID, Qt.AlignmentFlag.AlignCenter))
            self._table.setItem(row, 10, self._item(dev.heartbeat_str, C_TEXT_MID))
            self._table.setItem(row, 11, self._item(dev.note, C_TEXT_DIM))

        online = sum(1 for d in self._devices if d.is_online)
        win = self.window()
        if hasattr(win, "update_stats"):
            win.update_stats(len(self._devices), online)

    # ── 右键菜单 ──────────────────────────────────

    def _show_context_menu(self, pos) -> None:
        idx = self._table.indexAt(pos)
        if not idx.isValid():
            return
        dev = self._get_device_at_row(idx.row())
        if dev is None:
            return

        menu = QMenu(self)
        menu.addSection("脚本控制")
        act_start = menu.addAction("▶  启动脚本")
        act_stop = menu.addAction("■  停止脚本")
        act_restart = menu.addAction("↺  重启脚本")
        menu.addSeparator()
        menu.addSection("设备操作")
        act_activate = menu.addAction("⚡ 激活设备 (ROOT)")
        act_edit = menu.addAction("✎  编辑 / 设置")
        act_log = menu.addAction("≡  查看日志")
        menu.addSeparator()
        act_unbind = menu.addAction("✕  解绑设备")

        chosen = menu.exec(self._table.viewport().mapToGlobal(pos))
        if chosen == act_activate:
            self._do_activate(dev)
        elif chosen == act_edit:
            self._open_edit_dialog(dev)
        elif chosen == act_log:
            self._open_log_viewer()
        elif chosen == act_unbind:
            self._confirm_unbind(dev)
        elif chosen in (act_start, act_stop, act_restart):
            self._phase_hint(chosen.text().strip())

    def _open_batch_dialog(self) -> None:
        selected = self._get_selected_devices()
        if not selected:
            QMessageBox.information(self, "提示", "请先勾选要批量操作的设备")
            return
        from ui.widgets.batch_dialog import BatchDialog
        dlg = BatchDialog(selected, self._app.device_manager, self)
        dlg.batch_apply.connect(lambda _: self._apply_filters())
        dlg.exec()

    def _open_edit_dialog(self, dev: DeviceInfo) -> None:
        from ui.widgets.device_edit_dialog import DeviceEditDialog
        dlg = DeviceEditDialog(dev, self._app.device_manager, self)
        dlg.meta_saved.connect(lambda _: self._apply_filters())
        dlg.exec()

    def _open_log_viewer(self) -> None:
        win = self.window()
        if hasattr(win, "open_log_viewer"):
            win.open_log_viewer()

    def _confirm_unbind(self, dev: DeviceInfo) -> None:
        ret = QMessageBox.warning(
            self, "解绑确认",
            f"确定要解绑设备 {dev.display_id}？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if ret == QMessageBox.StandardButton.Yes:
            logger.info("解绑设备: %s（Phase 2 实现）", dev.fingerprint[:12])

    def _do_activate(self, dev: DeviceInfo) -> None:
        if not dev.adb_serial:
            QMessageBox.warning(self, "激活失败", f"设备 {dev.display_id} 未通过 ADB 连接。")
            return
        worker = ActivateWorker(self._app.adb, dev.adb_serial)
        worker.finished.connect(self._on_activate_done)
        self._activate_workers.append(worker)
        worker.start()

    def _batch_activate_selected(self) -> None:
        selected = self._get_selected_devices()
        if not selected:
            QMessageBox.information(self, "提示", "请先勾选要批量激活的设备")
            return
        for dev in selected:
            self._do_activate(dev)

    def _on_activate_done(self, serial: str, ok: bool, msg: str) -> None:
        if ok:
            QMessageBox.information(self, "激活成功", f"{serial}\n{msg}")
            fp = next((d.fingerprint for d in self._devices if d.adb_serial == serial), "")
            if fp:
                self._app.device_manager.update_meta(fp, activated=True)
        else:
            QMessageBox.warning(self, "激活失败", f"{serial}\n{msg}")
        self._activate_workers = [w for w in self._activate_workers if w.isRunning()]

    def _request_refresh(self) -> None:
        if hasattr(self._app, "sync_manager") and hasattr(self._app.sync_manager, "worker"):
            # 当前同步线程负责周期刷新；P1 阶段保留刷新按钮为提示，避免假装已实现立即拉取。
            QMessageBox.information(self, "刷新", "当前由同步线程自动刷新；立即刷新将在后续同步接口中实现。")
        else:
            self._apply_filters()

    def _phase_hint(self, action_name: str) -> None:
        QMessageBox.information(self, "待实现", f"{action_name} 属于后续批量操作实现范围，P1 仅完成布局重构。")

    # ── 选择操作 ──────────────────────────────────

    def _set_all_checked(self, checked: bool) -> None:
        for row in range(self._table.rowCount()):
            chk = self._checkbox_at(row)
            if chk:
                chk.setChecked(checked)
        self._update_selection_summary()

    def _invert_selection(self) -> None:
        for row in range(self._table.rowCount()):
            chk = self._checkbox_at(row)
            if chk:
                chk.setChecked(not chk.isChecked())
        self._update_selection_summary()

    def _clear_selection(self) -> None:
        self._set_all_checked(False)

    def _select_by_predicate(self, predicate) -> None:
        for row in range(self._table.rowCount()):
            chk = self._checkbox_at(row)
            dev = self._get_device_at_row(row)
            if chk and dev:
                chk.setChecked(bool(predicate(dev)))
        self._update_selection_summary()

    def _checkbox_at(self, row: int) -> QCheckBox | None:
        widget = self._table.cellWidget(row, 0)
        if not widget:
            return None
        return widget.findChild(QCheckBox)

    def _get_selected_devices(self) -> list[DeviceInfo]:
        result: list[DeviceInfo] = []
        for row in range(self._table.rowCount()):
            chk = self._checkbox_at(row)
            if chk and chk.isChecked():
                dev = self._get_device_at_row(row)
                if dev:
                    result.append(dev)
        return result

    def _update_selection_summary(self) -> None:
        selected = self._get_selected_devices()
        self._bottom_toolbar.set_selected_count(len(selected))
        self._side_panel.update_selection(selected)
        all_checked = bool(self._table.rowCount()) and len(selected) == self._table.rowCount()
        self._bottom_toolbar.set_all_checked(all_checked)

    def _on_double_click(self, row: int, _: int) -> None:
        dev = self._get_device_at_row(row)
        if dev:
            self._open_edit_dialog(dev)

    # ── 辅助 ──────────────────────────────────────

    def _get_device_at_row(self, row: int) -> DeviceInfo | None:
        item = self._table.item(row, 2)
        if item is None:
            return None
        fp_partial = item.text()
        return next((d for d in self._visible_devices if d.fingerprint.startswith(fp_partial.replace("...", ""))), None)

    @staticmethod
    def _item(
        text: str,
        color: str = C_TEXT,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    ) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setForeground(QColor(color))
        item.setTextAlignment(align)
        return item

    def _set_badge_cell(self, row: int, col: int, text: str, bg: str, fg: str) -> None:
        lbl = _badge(text, bg, fg, 11)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.addWidget(lbl)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(4, 0, 4, 0)
        self._table.setCellWidget(row, col, widget)
