r"""
文件位置: ui/main_window.py
名称: 主窗口
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.2.0
功能及相关说明:
  登录成功后显示的主操作窗口（1800×1200，最小 1280×800）。
  V1.2.0：
    · 全局字体放大（13px 正文 / 12px 辅助 / 11px 标注）
    · SideBar 替换为横向 TabBar（贴在 TopBar 正下方，40px）
    · 开发模式自动注入 10 台模拟设备（含订单/价格）

改进内容:
  V1.2.0 - 字体放大；垂直侧边栏 → 横向标签栏；Mock 数据支持
  V1.1.0 - 接入真实数据、右键菜单、ADB 激活线程
  V1.0.0 - 初始版本（骨架）

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QSize, QThread, Signal
from PySide6.QtGui import QColor, QPainter, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.device.models import DeviceInfo

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
#  颜色常量
# ─────────────────────────────────────────
C_BG_DEEP   = "#080806"
C_BG_MAIN   = "#0e0e0c"
C_BG_PANEL  = "#111110"
C_BG_ITEM   = "#1a1a18"
C_BG_HOVER  = "#141412"
C_BG_SEL    = "#071f16"
C_BORDER    = "#1e1e1c"
C_BORDER2   = "#2a2a28"
C_BORDER3   = "#333331"
C_TEAL      = "#5DCAA5"
C_TEAL_DK   = "#1D9E75"
C_TEAL_BG   = "#0A3828"
C_TEAL_BG2  = "#04342C"
C_GREEN     = "#97C459"
C_GREEN_BG  = "#173404"
C_AMBER     = "#EF9F27"
C_AMBER_BG  = "#412402"
C_RED       = "#F7C1C1"
C_RED_BG    = "#501313"
C_TEXT      = "#c8c7c0"
C_TEXT2     = "#B4B2A9"
C_TEXT_MID  = "#888780"
C_TEXT_DIM  = "#5F5E5A"
C_TEXT_MUTE = "#444441"
C_TEXT_DARK = "#333331"
MONO_FONT   = "Consolas"

# ─────────────────────────────────────────
#  全局 QSS  — 字体全面放大
# ─────────────────────────────────────────
MAIN_QSS = f"""
QMainWindow, QWidget {{
    background: {C_BG_MAIN};
    font-family: '{MONO_FONT}', 'Consolas', monospace;
    font-size: 13px;
    color: {C_TEXT};
}}
#topbar  {{ background: {C_BG_PANEL}; border-bottom: 1px solid {C_BORDER}; }}
#tabbar  {{ background: {C_BG_PANEL}; border-bottom: 2px solid {C_BORDER}; }}
#statusbar {{ background: {C_BG_DEEP}; border-top: 1px solid {C_BG_PANEL}; }}
#toolbar, #filterbar {{ background: {C_BG_PANEL}; border-bottom: 1px solid {C_BORDER}; }}

/* ── 横向标签按钮 ── */
QPushButton#tab-btn {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {C_TEXT_MID};
    padding: 0 18px;
    font-size: 13px;
    font-family: '{MONO_FONT}', monospace;
}}
QPushButton#tab-btn:hover {{
    color: {C_TEXT};
    background: {C_BG_ITEM};
}}
QPushButton#tab-btn[active="true"] {{
    color: {C_TEAL};
    border-bottom: 2px solid {C_TEAL_DK};
    background: transparent;
}}

/* ── 普通按钮 ── */
QPushButton {{
    background: transparent; border: 0.5px solid {C_BORDER2}; border-radius: 5px;
    color: {C_TEXT_MID}; padding: 4px 11px;
    font-family: '{MONO_FONT}', monospace; font-size: 12px;
}}
QPushButton:hover {{ background: {C_BG_ITEM}; color: {C_TEXT}; }}
QPushButton:disabled {{ color: {C_TEXT_MUTE}; }}

/* ── 输入框 ── */
QLineEdit {{
    background: {C_BG_PANEL}; border: 0.5px solid {C_BORDER}; border-radius: 4px;
    color: {C_TEXT}; padding: 4px 9px;
    font-family: '{MONO_FONT}', monospace; font-size: 12px;
    selection-background-color: {C_TEAL_DK};
}}
QLineEdit:focus {{ border-color: {C_TEAL_DK}; }}

/* ── 下拉框 ── */
QComboBox {{
    background: {C_BG_PANEL}; border: 0.5px solid {C_BORDER}; border-radius: 4px;
    color: {C_TEXT}; padding: 4px 9px;
    font-family: '{MONO_FONT}', monospace; font-size: 12px;
}}
QComboBox:focus {{ border-color: {C_TEAL_DK}; }}
QComboBox::drop-down {{ border: none; width: 16px; }}
QComboBox QAbstractItemView {{
    background: {C_BG_ITEM}; border: 0.5px solid {C_BORDER3};
    selection-background-color: {C_TEAL_BG}; color: {C_TEXT}; font-size: 12px;
}}

/* ── 表格 ── */
QTableWidget {{
    background: {C_BG_MAIN}; border: none; gridline-color: {C_BG_MAIN};
    color: {C_TEXT}; font-size: 13px; selection-background-color: {C_BG_SEL};
}}
QTableWidget::item {{ padding: 8px 12px; border-bottom: 1px solid {C_BG_MAIN}; }}
QTableWidget::item:hover {{ background: {C_BG_HOVER}; }}
QTableWidget::item:selected {{ background: {C_BG_SEL}; color: {C_TEXT}; }}
QHeaderView::section {{
    background: {C_BG_PANEL}; color: {C_TEXT_MUTE}; font-size: 12px; font-weight: 400;
    padding: 8px 12px; border: none; border-bottom: 1px solid {C_BORDER}; border-right: none;
}}
QHeaderView::section:hover {{ color: {C_TEXT_MID}; }}

/* ── 滚动条 ── */
QScrollBar:vertical {{ background: {C_BG_MAIN}; width: 6px; border: none; }}
QScrollBar::handle:vertical {{ background: {C_BORDER2}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {C_TEXT_MUTE}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: {C_BG_MAIN}; height: 6px; border: none; }}
QScrollBar::handle:horizontal {{ background: {C_BORDER2}; border-radius: 3px; min-width: 24px; }}
QScrollBar::handle:horizontal:hover {{ background: {C_TEXT_MUTE}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── 复选框 ── */
QCheckBox {{ spacing: 0; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border: 1px solid {C_BORDER2};
    border-radius: 3px; background: transparent;
}}
QCheckBox::indicator:checked {{ background: {C_TEAL_DK}; border-color: {C_TEAL_DK}; }}

/* ── 右键菜单 ── */
QMenu {{
    background: {C_BG_ITEM}; border: 0.5px solid {C_BORDER3};
    border-radius: 7px; padding: 4px 0; font-size: 13px; color: {C_TEXT};
}}
QMenu::item {{ padding: 8px 16px 8px 28px; }}
QMenu::item:selected {{ background: {C_TEAL_BG}; color: {C_TEAL}; }}
QMenu::separator {{ height: 1px; background: {C_BORDER2}; margin: 3px 0; }}
"""


# ─────────────────────────────────────────
#  工具函数
# ─────────────────────────────────────────

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


def _btn(text: str, style: str = "") -> QPushButton:
    b = QPushButton(text)
    if style == "prim":
        b.setStyleSheet(
            f"background:{C_TEAL_BG}; border:0.5px solid {C_TEAL_DK}; color:{C_TEAL};"
            f" border-radius:5px; padding:4px 11px; font-size:12px; font-family:'{MONO_FONT}',monospace;"
        )
    elif style == "warn":
        b.setStyleSheet(
            f"background:transparent; border:0.5px solid {C_AMBER_BG}; color:{C_AMBER};"
            f" border-radius:5px; padding:4px 11px; font-size:12px; font-family:'{MONO_FONT}',monospace;"
        )
    elif style == "danger":
        b.setStyleSheet(
            f"background:transparent; border:0.5px solid {C_RED_BG}; color:{C_RED};"
            f" border-radius:5px; padding:4px 11px; font-size:12px; font-family:'{MONO_FONT}',monospace;"
        )
    return b


# ─────────────────────────────────────────
#  ADB 激活线程
# ─────────────────────────────────────────

class ActivateWorker(QThread):
    finished = Signal(str, bool, str)

    def __init__(self, adb, serial: str) -> None:
        super().__init__()
        self._adb    = adb
        self._serial = serial

    def run(self) -> None:
        ok, msg = self._adb.activate_device(self._serial)
        self.finished.emit(self._serial, ok, msg)


# ─────────────────────────────────────────
#  TopBar
# ─────────────────────────────────────────

class TopBar(QWidget):
    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app
        self.setObjectName("topbar")
        self.setFixedHeight(48)
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(0)

        # Logo
        logo = QLabel()
        logo.setText(
            f'<span style="color:{C_TEXT2}; font-size:15px;">'
            f'蜂巢<span style="color:{C_TEAL}">·</span>大圣</span>'
            f'<span style="color:{C_TEXT_DARK}; font-size:10px;"> v1.0.0</span>'
        )
        logo.setStyleSheet("margin-right:20px;")
        lay.addWidget(logo)

        lay.addWidget(_sep_v())

        # 账号
        acct = QWidget()
        acct.setFixedHeight(48)
        al = QHBoxLayout(acct)
        al.setContentsMargins(14, 0, 14, 0)
        al.setSpacing(8)
        user = self._app.auth.user_info
        al.addWidget(_label(user.display_name or user.username, C_TEXT, 14))
        level_colors = {
            "vip":    (C_AMBER_BG, C_AMBER),
            "svip":   ("#26215C", "#AFA9EC"),
            "tester": (C_TEAL_BG2, C_TEAL),
            "normal": (C_BG_ITEM, C_TEXT_MID),
            "trial":  (C_BG_ITEM, C_TEXT_DIM),
        }
        bg, fg = level_colors.get(user.user_level, (C_BG_ITEM, C_TEXT_MID))
        al.addWidget(_badge(user.user_level.upper(), bg, fg, 10))
        lay.addWidget(acct)
        lay.addWidget(_sep_v())

        # 设备统计
        stat = QWidget()
        stat.setFixedHeight(48)
        sl = QHBoxLayout(stat)
        sl.setContentsMargins(14, 0, 14, 0)
        sl.setSpacing(5)
        self._lbl_avail  = _label("—", C_GREEN,    14)
        self._lbl_active = _label("—", C_TEAL,     14)
        self._lbl_inact  = _label("—", C_TEXT_MID, 14)
        for txt, val_lbl in [("可激活", self._lbl_avail),
                              ("已激活", self._lbl_active),
                              ("未激活", self._lbl_inact)]:
            sl.addWidget(_label(txt, C_TEXT_MUTE, 10))
            sl.addWidget(_label("/", C_BORDER2, 11))
            sl.addWidget(val_lbl)
            sl.addSpacing(8)
        lay.addWidget(stat)
        lay.addWidget(_sep_v())

        # 到期
        exp = QWidget()
        exp.setFixedHeight(48)
        el = QHBoxLayout(exp)
        el.setContentsMargins(14, 0, 14, 0)
        el.setSpacing(5)
        el.addWidget(_label("到期：", C_TEXT_DIM, 11))
        el.addWidget(_label(user.expired_at or "—", C_AMBER, 12))
        lay.addWidget(exp)
        lay.addWidget(_sep_v())

        # 连接状态
        conn = QWidget()
        conn.setFixedHeight(48)
        cl = QHBoxLayout(conn)
        cl.setContentsMargins(14, 0, 0, 0)
        cl.setSpacing(6)
        cl.addWidget(_label("●", C_TEAL_DK, 9))
        api_host = (self._app.config.get("server.api_base_url", "")
                    .replace("http://", "").replace("https://", ""))
        cl.addWidget(_label(f"已连接 · {api_host}", C_TEAL, 12))
        lay.addWidget(conn)

        lay.addStretch()

        self._sync_lbl = _label("等待同步...", C_TEXT_MUTE, 11)
        lay.addWidget(self._sync_lbl)
        lay.addSpacing(10)

        _S = (
            f"padding:4px 11px; background:transparent; border:0.5px solid {C_BORDER2};"
            f" border-radius:5px; color:{C_TEXT_MID}; font-size:12px;"
        )
        s_btn = QPushButton("⚙ 全局设置")
        s_btn.setStyleSheet(_S)
        s_btn.clicked.connect(self._open_settings)
        lay.addWidget(s_btn)
        lay.addSpacing(6)

        lo_btn = QPushButton("退出登录")
        lo_btn.setStyleSheet(_S)
        lo_btn.clicked.connect(self._on_logout)
        lay.addWidget(lo_btn)

    def update_stats(self, total: int, online: int) -> None:
        self._lbl_avail.setText(str(total))
        self._lbl_active.setText(str(online))
        self._lbl_inact.setText(str(total - online))
        self._sync_lbl.setText("已同步")
        self._sync_lbl.setStyleSheet(f"color:{C_TEAL}; font-size:11px;")

    def _open_settings(self) -> None:
        win = self.window()
        if hasattr(win, "open_settings"):
            win.open_settings()

    def _on_logout(self) -> None:
        self._app.auth.logout()
        QApplication.quit()


# ─────────────────────────────────────────
#  TabBar（横向标签，替代 SideBar）
# ─────────────────────────────────────────

_TAB_DEFS = [
    ("dev",      "📱 设备管理"),
    ("team",     "👥 组队管理"),
    ("order",    "📋 同服订单"),
    ("price",    "📈 跨服价格"),
]


class TabBar(QWidget):
    """横向标签栏，贴在 TopBar 正下方。"""

    def __init__(self, on_navigate) -> None:
        super().__init__()
        self.setObjectName("tabbar")
        self.setFixedHeight(40)
        self._on_navigate = on_navigate
        self._btns: dict[str, QPushButton] = {}
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(0)

        for pid, label in _TAB_DEFS:
            btn = QPushButton(label)
            btn.setObjectName("tab-btn")
            btn.setFixedHeight(40)
            btn.setMinimumWidth(120)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, p=pid: self._click(p))
            self._btns[pid] = btn
            lay.addWidget(btn)

        # 设置按钮（右侧靠右）
        lay.addStretch()
        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("tab-btn")
        settings_btn.setFixedSize(40, 40)
        settings_btn.setToolTip("全局设置")
        settings_btn.clicked.connect(lambda: self._click("settings"))
        self._btns["settings"] = settings_btn
        lay.addWidget(settings_btn)

        self.set_active("dev")

    def _click(self, pid: str) -> None:
        if pid != "settings":
            self.set_active(pid)
        self._on_navigate(pid)

    def set_active(self, pid: str) -> None:
        for p, btn in self._btns.items():
            active = (p == pid)
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)


# ─────────────────────────────────────────
#  设备管理页
# ─────────────────────────────────────────

_DEV_COLS   = ["", "编号", "序列号", "角色", "状态", "激活", "当前任务", "等级", "战力", "区服", "心跳", "备注"]
_STATUS_MAP = {
    "running": (C_TEAL_BG2, C_TEAL,    "运行中"),
    "idle":    (C_BG_ITEM,  C_TEXT_MID, "在线"),
    "error":   (C_RED_BG,   C_RED,      "异常"),
    "offline": (C_BG_ITEM,  C_TEXT_DIM, "离线"),
}
_ROLE_MAP   = {
    "captain": ("#26215C", "#AFA9EC", "队长"),
    "power":   (C_TEAL_BG2, C_TEAL,   "战力"),
    "farmer":  (C_GREEN_BG, C_GREEN,  "打工"),
    "newbie":  (C_BG_ITEM, C_TEXT_MID,"新号"),
}


class DevicePage(QWidget):
    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app      = app
        self._devices: list[DeviceInfo] = []
        self._activate_workers: list[ActivateWorker] = []
        self._build()

    def _build(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── 工具栏 ──
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(44)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(12, 0, 12, 0)
        tl.setSpacing(8)
        self._chk_all = QCheckBox()
        self._chk_all.stateChanged.connect(self._toggle_all)
        tl.addWidget(self._chk_all)
        tl.addWidget(_sep_v())
        bb = _btn("批量设置", "prim")
        bb.clicked.connect(self._open_batch_dialog)
        tl.addWidget(bb)
        tl.addWidget(_btn("▶ 批量启动"))
        tl.addWidget(_btn("■ 批量停止"))
        tl.addWidget(_btn("⚡ 批量激活", "warn"))
        tl.addWidget(_sep_v())
        tl.addWidget(_btn("导出"))
        tl.addWidget(_btn("解绑", "danger"))
        tl.addWidget(_sep_v())
        tl.addStretch()
        self._sel_lbl = _label("已选 0 台", C_TEXT_MUTE, 12)
        tl.addWidget(self._sel_lbl)
        lay.addWidget(toolbar)

        # ── 筛选栏 ──
        fb = QWidget()
        fb.setObjectName("filterbar")
        fb.setFixedHeight(36)
        fl = QHBoxLayout(fb)
        fl.setContentsMargins(12, 0, 12, 0)
        fl.setSpacing(10)
        fl.addWidget(_label("筛选：", C_TEXT_MUTE, 11))
        self._f_search = QLineEdit()
        self._f_search.setPlaceholderText("编号 / 序列号 / 区服...")
        self._f_search.setFixedWidth(200)
        self._f_search.setFixedHeight(26)
        self._f_search.textChanged.connect(self._apply_filters)
        fl.addWidget(self._f_search)
        self._f_status = QComboBox()
        self._f_status.setFixedHeight(26)
        for t in ["全部状态", "运行中", "在线", "离线", "异常"]:
            self._f_status.addItem(t)
        self._f_status.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self._f_status)
        self._f_role = QComboBox()
        self._f_role.setFixedHeight(26)
        for t in ["全部角色", "队长", "战力号", "打工号", "新号"]:
            self._f_role.addItem(t)
        self._f_role.currentIndexChanged.connect(self._apply_filters)
        fl.addWidget(self._f_role)
        fl.addStretch()
        self._row_lbl = _label("0 台设备", C_TEXT_DARK, 11)
        fl.addWidget(self._row_lbl)
        lay.addWidget(fb)

        # ── 表格 ──
        self._table = QTableWidget()
        self._table.setColumnCount(len(_DEV_COLS))
        self._table.setHorizontalHeaderLabels(_DEV_COLS)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setHighlightSections(False)
        self._table.setShowGrid(False)
        self._table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._table.customContextMenuRequested.connect(self._show_context_menu)
        self._table.cellDoubleClicked.connect(self._on_double_click)
        self._table.itemSelectionChanged.connect(self._update_sel_label)

        hdr = self._table.horizontalHeader()
        col_widths = [36, 80, 140, 70, 80, 65, 0, 65, 90, 55, 90, 110]
        for i, w in enumerate(col_widths):
            if w == 0:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
            else:
                hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self._table.setColumnWidth(i, w)
        lay.addWidget(self._table)

    # ── 数据 ──────────────────────────────────────

    def refresh_devices(self, devices: list) -> None:
        self._devices = devices
        self._apply_filters()

    def _apply_filters(self) -> None:
        search     = self._f_search.text().strip().lower()
        status_txt = self._f_status.currentText()
        role_txt   = self._f_role.currentText()
        status_map = {"运行中": "running", "在线": "idle", "离线": "offline", "异常": "error"}
        role_map   = {"队长": "captain", "战力号": "power", "打工号": "farmer", "新号": "newbie"}

        filtered = [
            d for d in self._devices
            if (not search or search in d.display_id.lower()
                or search in d.fingerprint.lower()
                or search in d.server.lower())
            and (status_txt == "全部状态" or d.api_status == status_map.get(status_txt, ""))
            and (role_txt   == "全部角色" or d.role       == role_map.get(role_txt, ""))
        ]
        self._populate_table(filtered)
        self._row_lbl.setText(f"{len(filtered)} 台设备")

    def _populate_table(self, devices: list[DeviceInfo]) -> None:
        self._table.setRowCount(len(devices))
        for row, dev in enumerate(devices):
            self._table.setRowHeight(row, 40)

            # 复选框
            chk_w = QWidget()
            chk   = QCheckBox()
            cl    = QHBoxLayout(chk_w)
            cl.addWidget(chk)
            cl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cl.setContentsMargins(0, 0, 0, 0)
            self._table.setCellWidget(row, 0, chk_w)

            self._table.setItem(row, 1, self._item(dev.display_id, C_TEXT))
            self._table.setItem(row, 2, self._item(dev.fingerprint[:20], C_TEXT_MID))

            if dev.role in _ROLE_MAP:
                bg, fg, txt = _ROLE_MAP[dev.role]
                self._set_badge_cell(row, 3, txt, bg, fg)
            else:
                self._table.setItem(row, 3, self._item("—", C_TEXT_MUTE))

            st = dev.api_status or "offline"
            if st in _STATUS_MAP:
                bg, fg, txt = _STATUS_MAP[st]
                self._set_badge_cell(row, 4, txt, bg, fg)

            act_text = "已激活" if dev.activated else "未激活"
            self._set_badge_cell(
                row, 5, act_text,
                C_TEAL_BG2 if dev.activated else C_BG_ITEM,
                C_TEAL     if dev.activated else C_TEXT_DIM,
            )

            self._table.setItem(row, 6,  self._item(dev.task or "—", C_TEXT_MID))
            self._table.setItem(row, 7,  self._item(f"Lv.{dev.level}" if dev.level else "—", C_TEXT, Qt.AlignmentFlag.AlignCenter))
            self._table.setItem(row, 8,  self._item(f"{dev.combat_power:,}" if dev.combat_power else "—", C_TEXT2, Qt.AlignmentFlag.AlignCenter))
            self._table.setItem(row, 9,  self._item(dev.server or "—", C_TEXT_MID, Qt.AlignmentFlag.AlignCenter))
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
        menu.setStyleSheet(MAIN_QSS)
        menu.addSection("脚本控制")
        act_start   = menu.addAction("▶  启动脚本")
        act_stop    = menu.addAction("■  停止脚本")
        act_restart = menu.addAction("↺  重启脚本")
        menu.addSeparator()
        menu.addSection("设备操作")
        act_activate = menu.addAction("⚡ 激活设备 (ROOT)")
        act_edit     = menu.addAction("✎  编辑 / 设置")
        act_log      = menu.addAction("≡  查看日志")
        menu.addSeparator()
        act_unbind   = menu.addAction("✕  解绑设备")

        chosen = menu.exec(self._table.viewport().mapToGlobal(pos))
        if chosen == act_activate:
            self._do_activate(dev)
        elif chosen == act_edit:
            self._open_edit_dialog(dev)
        elif chosen == act_log:
            win = self.window()
            if hasattr(win, "open_log_viewer"):
                win.open_log_viewer()
        elif chosen == act_unbind:
            self._confirm_unbind(dev)

    def _do_activate(self, dev: DeviceInfo) -> None:
        if not dev.adb_serial:
            QMessageBox.warning(self, "激活失败",
                f"设备 {dev.display_id} 未通过 ADB 连接。")
            return
        w = ActivateWorker(self._app.adb, dev.adb_serial)
        w.finished.connect(self._on_activate_done)
        self._activate_workers.append(w)
        w.start()

    def _on_activate_done(self, serial: str, ok: bool, msg: str) -> None:
        if ok:
            QMessageBox.information(self, "激活成功", f"{serial}\n{msg}")
            fp = next((d.fingerprint for d in self._devices if d.adb_serial == serial), "")
            if fp:
                self._app.device_manager.update_meta(fp, activated=True)
        else:
            QMessageBox.warning(self, "激活失败", f"{serial}\n{msg}")
        self._activate_workers = [w for w in self._activate_workers if w.isRunning()]

    def _open_batch_dialog(self) -> None:
        selected = self._get_selected_devices()
        if not selected:
            QMessageBox.information(self, "提示", "请先勾选要批量操作的设备")
            return
        from ui.widgets.batch_dialog import BatchDialog
        dlg = BatchDialog(selected, self._app.device_manager, self)
        dlg.batch_apply.connect(lambda _: self._apply_filters())
        dlg.exec()

    def _get_selected_devices(self) -> list:
        result = []
        for row in range(self._table.rowCount()):
            w = self._table.cellWidget(row, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk and chk.isChecked():
                    dev = self._get_device_at_row(row)
                    if dev:
                        result.append(dev)
        return result

    def _open_edit_dialog(self, dev: DeviceInfo) -> None:
        from ui.widgets.device_edit_dialog import DeviceEditDialog
        dlg = DeviceEditDialog(dev, self._app.device_manager, self)
        dlg.meta_saved.connect(lambda _: self._apply_filters())
        dlg.exec()

    def _confirm_unbind(self, dev: DeviceInfo) -> None:
        ret = QMessageBox.warning(
            self, "解绑确认",
            f"确定要解绑设备 {dev.display_id}？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
        )
        if ret == QMessageBox.StandardButton.Yes:
            logger.info("解绑设备: %s（Phase 2 实现）", dev.fingerprint[:12])

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
        return next(
            (d for d in self._devices
             if d.fingerprint.startswith(fp_partial.replace("...", ""))),
            None,
        )

    def _toggle_all(self, state) -> None:
        # PySide6 新版传入 Qt.CheckState 枚举，旧版传入 int，兼容两种
        if isinstance(state, Qt.CheckState):
            checked = (state == Qt.CheckState.Checked)
        else:
            checked = bool(state)
        for row in range(self._table.rowCount()):
            w = self._table.cellWidget(row, 0)
            if w:
                chk = w.findChild(QCheckBox)
                if chk:
                    chk.setChecked(checked)

    def _update_sel_label(self) -> None:
        n = len(set(idx.row() for idx in self._table.selectedIndexes()))
        self._sel_lbl.setText(f"已选 {n} 台")

    @staticmethod
    def _item(
        text: str,
        color: str = C_TEXT,
        align: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
    ) -> QTableWidgetItem:
        it = QTableWidgetItem(text)
        it.setForeground(QColor(color))
        it.setTextAlignment(align)
        return it

    def _set_badge_cell(self, row: int, col: int, text: str, bg: str, fg: str) -> None:
        lbl = _badge(text, bg, fg, 11)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        w   = QWidget()
        lay = QHBoxLayout(w)
        lay.addWidget(lbl)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setContentsMargins(4, 0, 4, 0)
        self._table.setCellWidget(row, col, w)


# ─────────────────────────────────────────
#  占位页
# ─────────────────────────────────────────

def _placeholder_page(title: str) -> QWidget:
    w   = QWidget()
    lay = QVBoxLayout(w)
    lbl = QLabel(title)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setStyleSheet(f"color:{C_TEXT_MUTE}; font-size:14px;")
    lay.addWidget(lbl)
    return w


# ─────────────────────────────────────────
#  MainWindow
# ─────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app
        self.setStyleSheet(MAIN_QSS)
        self._setup_window()
        self._build_ui()
        self._connect_sync()
        logger.debug("MainWindow 初始化完成")

    def _setup_window(self) -> None:
        from game.game_config import WINDOW_TITLE
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1800, 1200)
        self.setMinimumSize(1280, 800)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        rl   = QVBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)

        # TopBar
        self._topbar = TopBar(self._app)
        rl.addWidget(self._topbar)

        # TabBar（横向）
        self._tabbar = TabBar(self._on_navigate)
        rl.addWidget(self._tabbar)

        # 内容区（无侧边栏）
        self._stack = QStackedWidget()
        rl.addWidget(self._stack)

        # 各页面
        self._dev_page = DevicePage(self._app)
        self._stack.addWidget(self._dev_page)         # 0

        from ui.widgets.team_widget import TeamWidget
        self._team_page = TeamWidget(self._app)
        self._stack.addWidget(self._team_page)         # 1

        from ui.widgets.order_widget import OrderWidget
        self._order_page = OrderWidget()
        self._stack.addWidget(self._order_page)        # 2

        from ui.widgets.price_monitor_widget import PriceMonitorWidget
        self._price_page = PriceMonitorWidget()
        self._stack.addWidget(self._price_page)        # 3

        self._page_index = {"dev": 0, "team": 1, "order": 2, "price": 3}

        # StatusBar
        from ui.widgets.status_bar_widget import StatusBarWidget
        self._statusbar = StatusBarWidget(self._app)
        rl.addWidget(self._statusbar)

    def _connect_sync(self) -> None:
        worker = self._app.sync_manager.worker
        worker.devices_updated.connect(self._dev_page.refresh_devices)
        worker.devices_updated.connect(self._order_page.refresh_from_devices)
        worker.devices_updated.connect(self._price_page.refresh_from_devices)
        worker.sync_error.connect(self._on_sync_error)
        # token_expired 已在 app.py 中连接到 _on_token_expired（主线程重新登录流程）
        # 主窗口不再重复连接，避免 Signal 触发两次。
        # worker.token_expired.connect(self._on_token_expired)  # 移除重复连接

    # ── 导航 ──────────────────────────────────────

    def _on_navigate(self, pid: str) -> None:
        if pid == "settings":
            self.open_settings()
        else:
            self._stack.setCurrentIndex(self._page_index.get(pid, 0))

    def open_settings(self) -> None:
        from ui.widgets.settings_dialog import SettingsDialog
        SettingsDialog(self._app, self).exec()

    def open_log_viewer(self) -> None:
        from ui.widgets.log_viewer_widget import LogViewerDialog
        LogViewerDialog(parent=self).show()

    # ── 同步事件 ──────────────────────────────────

    def _on_sync_error(self, msg: str) -> None:
        logger.warning("同步错误: %s", msg)

    def _on_token_expired(self) -> None:
        """
        保留此方法作备用入口，但不再直接处理 token_expired。
        实际处理已由 app.py 的 Application._on_token_expired() 负责。
        """
        pass

    # ── 外部调用 ──────────────────────────────────

    def update_stats(self, total: int, online: int) -> None:
        self._topbar.update_stats(total, online)

    def closeEvent(self, event) -> None:
        self._app.sync_manager.stop()
        super().closeEvent(event)
