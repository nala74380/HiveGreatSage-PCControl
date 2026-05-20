r"""
文件位置: ui/main_window.py
名称: 主窗口
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.4.0
状态: P2 UI 边界重构执行中
功能及相关说明:
  登录成功后显示的主操作窗口。
  V1.3.0：主窗口收敛为装配层；设备管理页迁移到 ui/pages/device_page.py。
  V1.4.0：全局设置入口切换到 ui/dialogs/global_settings_dialog.py。

边界说明:
  - 本文件只负责 TopBar、TabBar、页面装配、同步信号连接。
  - 设备管理页布局由 ui/pages/device_page.py 承担。
  - 全局设置由 ui/dialogs/global_settings_dialog.py 承担。
  - 本文件不实现远控、投屏、scrcpy、公网远控、Relay 远控。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from core.utils.constants import APP_VERSION
from ui.pages.device_page import DevicePage
from ui.styles.colors import (
    BG_DEEP,
    BG_MAIN,
    BG_PANEL,
    BG_ITEM,
    BORDER,
    BORDER2,
    TEAL,
    TEAL_DK,
    TEAL_BG,
    TEAL_BG2,
    GREEN,
    AMBER,
    AMBER_BG,
    TEXT,
    TEXT_MID,
    TEXT_DIM,
    TEXT_MUTE,
    TEXT_DARK,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)

MAIN_QSS = f"""
QMainWindow, QWidget {{
    background: {BG_MAIN};
    font-family: 'Microsoft YaHei UI', 'HarmonyOS Sans SC', 'Segoe UI', sans-serif;
    font-size: 13px;
    color: {TEXT};
}}
#topbar  {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffffff, stop:0.42 #eef7ff, stop:0.72 #fff7df, stop:1 #eefcf5);
    border-bottom: none;
}}
#tabbar  {{ background: #ffffff; border-bottom: 1px solid {BORDER}; }}
#statusbar {{ background: #f8fbff; border-top: 1px solid {BORDER}; }}
#filterbar {{ background: #ffffff; border-bottom: 1px solid {BORDER}; }}
QPushButton#tab-btn {{
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    border-radius: 0;
    color: {TEXT_MID};
    padding: 0 20px;
    font-size: 14px;
    font-weight: 600;
}}
QPushButton#tab-btn:hover {{ color: {TEAL_DK}; background: #eef7ff; }}
QPushButton#tab-btn[active="true"] {{
    color: {TEAL_DK};
    border-bottom: 3px solid {TEAL};
    background: #e9f8ff;
}}
QPushButton#window-control {{
    background: transparent;
    border: none;
    border-radius: 9px;
    color: {TEXT_MID};
    padding: 0;
    font-size: 17px;
    font-weight: 700;
}}
QPushButton#window-control:hover {{ background: #e7f1ff; color: {TEXT}; }}
QPushButton#window-control[danger="true"]:hover {{ background: #ffe8eb; color: #d92d20; }}
QPushButton {{
    background: #ffffff;
    border: 1px solid {BORDER2};
    border-radius: 9px;
    color: {TEXT};
    padding: 5px 13px;
    font-size: 12px;
    font-weight: 600;
}}
QPushButton:hover {{ background: #eef7ff; border-color: {TEAL}; color: {TEAL_DK}; }}
QPushButton:disabled {{ color: {TEXT_MUTE}; background: #f3f6fb; }}
QLineEdit, QComboBox {{
    background: #ffffff;
    border: 1px solid {BORDER2};
    border-radius: 8px;
    color: {TEXT};
    padding: 4px 8px;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {TEAL}; background: #fbfeff; }}
QTableWidget {{
    background: #ffffff;
    alternate-background-color: #f6fbff;
    border: none;
    gridline-color: {BORDER};
    color: {TEXT};
    selection-background-color: #dff7ee;
    selection-color: {TEXT};
}}
QTableWidget::item {{ padding: 7px 9px; border-bottom: 1px solid #edf3fb; }}
QTableWidget::item:hover {{ background: #eef7ff; }}
QHeaderView::section {{
    background: #2f80ed;
    color: #ffffff;
    border: none;
    padding: 8px 10px;
    font-weight: 700;
}}
QMenu {{
    background: #ffffff;
    border: 1px solid {BORDER2};
    border-radius: 10px;
    padding: 5px 0;
    font-size: 13px;
    color: {TEXT};
}}
QMenu::item {{ padding: 8px 16px 8px 28px; }}
QMenu::item:selected {{ background: #e9f8ff; color: {TEAL_DK}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 0; }}
"""


def _badge(text: str, bg: str, fg: str, font_size: int = 11) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; border-radius:8px;"
        f" padding:3px 10px; font-size:{font_size}px; font-weight:800;"
    )
    return lbl


def _sep_v() -> QFrame:
    frame = QFrame()
    frame.setFrameShape(QFrame.Shape.VLine)
    frame.setFixedWidth(1)
    frame.setStyleSheet(f"background:{BORDER}; border:none;")
    return frame


def _label(text: str, color: str = TEXT_MUTE, size: int = 12) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color}; font-size:{size}px;")
    return lbl


def _metric_label(text: str, color: str = TEXT_MID, size: int = 13) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{color}; font-size:{size}px; font-weight:800;")
    return lbl


def _level_display(level: str) -> str:
    mapping = {
        "trial": "试用",
        "normal": "普通",
        "vip": "VIP",
        "svip": "SVIP",
        "tester": "测试",
    }
    key = (level or "normal").strip().lower()
    return mapping.get(key, level or "普通")


def _is_tester_level(level: str) -> bool:
    return (level or "").strip().lower() == "tester"


def _level_colors(level: str) -> tuple[str, str]:
    mapping = {
        "trial": ("#FFF3BF", "#B7791F"),
        "normal": ("#EAF4FF", "#2F80ED"),
        "vip": ("#FFE8CC", "#D9480F"),
        "svip": ("#EDEBFF", "#6C5CE7"),
        "tester": ("#E6FCF5", "#087F5B"),
    }
    return mapping.get((level or "normal").strip().lower(), ("#EEF6FF", TEXT_MID))


class TopBar(QWidget):
    """顶部状态栏。"""

    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app
        self._drag_offset = None
        self.setObjectName("topbar")
        self.setFixedHeight(48)
        self._build()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 12, 0)
        lay.setSpacing(0)

        logo = QLabel()
        logo.setText(
            f'<span style="color:{TEXT}; font-size:15px;">蜂巢<span style="color:{TEAL}">·</span>大圣</span>'
            f'<span style="color:{TEXT_DARK}; font-size:10px;"> v{APP_VERSION}</span>'
        )
        logo.setStyleSheet("margin-right:20px;")
        lay.addWidget(logo)
        lay.addWidget(_sep_v())

        user = self._app.auth.user_info
        acct = QWidget()
        acct.setFixedHeight(48)
        acct_lay = QHBoxLayout(acct)
        acct_lay.setContentsMargins(14, 0, 14, 0)
        acct_lay.setSpacing(8)
        acct_lay.addWidget(_label(user.display_name or user.username, TEXT, 14))
        bg, fg = _level_colors(user.user_level)
        self._level_badge = _badge(_level_display(user.user_level), bg, fg, 13)
        acct_lay.addWidget(self._level_badge)
        lay.addWidget(acct)
        lay.addWidget(_sep_v())

        stat = QWidget()
        stat.setFixedHeight(48)
        stat_lay = QHBoxLayout(stat)
        stat_lay.setContentsMargins(14, 0, 14, 0)
        stat_lay.setSpacing(5)
        self._lbl_ava_auth = _metric_label(str(user.device_quota) if user.device_quota > 0 else "无限", GREEN, 16)
        self._lbl_act_auth = _metric_label(str(user.activated_devices), TEAL, 16)
        self._lbl_inact_auth = _metric_label(str(user.inactive_devices) if user.inactive_devices is not None else "—", TEXT_MID, 16)
        for txt, value_label in [
            ("可激活", self._lbl_ava_auth),
            ("已激活", self._lbl_act_auth),
            ("未激活", self._lbl_inact_auth),
        ]:
            stat_lay.addWidget(_metric_label(txt, TEXT_MID, 13))
            stat_lay.addWidget(_metric_label("/", BORDER2, 13))
            stat_lay.addWidget(value_label)
            stat_lay.addSpacing(8)
        lay.addWidget(stat)
        lay.addWidget(_sep_v())

        exp = QWidget()
        exp.setFixedHeight(48)
        exp_lay = QHBoxLayout(exp)
        exp_lay.setContentsMargins(14, 0, 14, 0)
        exp_lay.setSpacing(5)
        exp_lay.addWidget(_metric_label("到期：", TEXT_MID, 13))
        expiry = user.expired_at[:10] if user.expired_at and len(user.expired_at) >= 10 else (user.expired_at or "—")
        self._lbl_expiry_auth = _metric_label(expiry, AMBER, 16)
        exp_lay.addWidget(self._lbl_expiry_auth)
        lay.addWidget(exp)
        self._conn_sep = _sep_v()
        lay.addWidget(self._conn_sep)

        conn = QWidget()
        conn.setFixedHeight(48)
        conn_lay = QHBoxLayout(conn)
        conn_lay.setContentsMargins(14, 0, 0, 0)
        conn_lay.setSpacing(6)
        conn_lay.addWidget(_label("●", TEAL_DK, 9))
        api_host = (self._app.config.get("server.api_base_url", "")
                    .replace("http://", "").replace("https://", ""))
        conn_lay.addWidget(_label(f"已连接 · {api_host}", TEAL, 12))
        self._conn_widget = conn
        lay.addWidget(self._conn_widget)
        self._set_connection_visibility(user.user_level)
        lay.addStretch()

        self._sync_lbl = _label("等待同步...", TEXT_MUTE, 11)
        lay.addWidget(self._sync_lbl)
        lay.addSpacing(10)

        settings_btn = QPushButton("⚙ 全局设置")
        settings_btn.clicked.connect(self._open_settings)
        lay.addWidget(settings_btn)
        lay.addSpacing(6)

        logout_btn = QPushButton("退出登录")
        logout_btn.clicked.connect(self._on_logout)
        lay.addWidget(logout_btn)
        lay.addSpacing(10)

        for text, tooltip, handler, danger in [
            ("—", "最小化", self._minimize_window, False),
            ("□", "最大化/还原", self._toggle_maximize, False),
            ("×", "关闭", self._close_window, True),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("window-control")
            btn.setProperty("danger", "true" if danger else "false")
            btn.setToolTip(tooltip)
            btn.setFixedSize(34, 30)
            btn.clicked.connect(handler)
            lay.addWidget(btn)

    def update_auth_stats(self) -> None:
        user = self._app.auth.user_info
        self._lbl_ava_auth.setText(str(user.device_quota) if user.device_quota > 0 else "无限")
        self._lbl_act_auth.setText(str(user.activated_devices))
        self._lbl_inact_auth.setText(str(user.inactive_devices) if user.inactive_devices is not None else "—")
        expiry = user.expired_at[:10] if user.expired_at and len(user.expired_at) >= 10 else (user.expired_at or "—")
        self._lbl_expiry_auth.setText(expiry)

        bg, fg = _level_colors(user.user_level)
        self._level_badge.setText(_level_display(user.user_level))
        self._level_badge.setStyleSheet(
            f"background:{bg}; color:{fg}; border-radius:8px;"
            " padding:3px 10px; font-size:13px; font-weight:800;"
        )
        self._set_connection_visibility(user.user_level)

    def _set_connection_visibility(self, user_level: str) -> None:
        visible = _is_tester_level(user_level)
        self._conn_sep.setVisible(visible)
        self._conn_widget.setVisible(visible)

    def update_stats(self, total: int, online: int) -> None:
        self._sync_lbl.setText("已同步")
        self._sync_lbl.setStyleSheet(f"color:{TEAL}; font-size:11px;")

    def _open_settings(self) -> None:
        win = self.window()
        if hasattr(win, "open_settings"):
            win.open_settings()

    def _on_logout(self) -> None:
        self._app.auth.logout()
        QApplication.quit()

    def _minimize_window(self) -> None:
        self.window().showMinimized()

    def _toggle_maximize(self) -> None:
        win = self.window()
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()

    def _close_window(self) -> None:
        self.window().close()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


_TAB_DEFS = [
    ("dev", "📱 设备管理"),
    ("team", "👥 组队管理"),
    ("order", "📋 同服订单"),
    ("price", "📈 跨服价格"),
]


class TabBar(QWidget):
    """横向标签栏。"""

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
        for page_id, label in _TAB_DEFS:
            btn = QPushButton(label)
            btn.setObjectName("tab-btn")
            btn.setFixedHeight(40)
            btn.setMinimumWidth(120)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, p=page_id: self._click(p))
            self._btns[page_id] = btn
            lay.addWidget(btn)
        lay.addStretch()
        settings_btn = QPushButton("⚙")
        settings_btn.setObjectName("tab-btn")
        settings_btn.setFixedSize(40, 40)
        settings_btn.setToolTip("全局设置")
        settings_btn.clicked.connect(lambda: self._click("settings"))
        self._btns["settings"] = settings_btn
        lay.addWidget(settings_btn)
        self.set_active("dev")

    def _click(self, page_id: str) -> None:
        if page_id != "settings":
            self.set_active(page_id)
        self._on_navigate(page_id)

    def set_active(self, page_id: str) -> None:
        for pid, btn in self._btns.items():
            active = pid == page_id
            btn.setProperty("active", "true" if active else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)


class MainWindow(QMainWindow):
    """PCControl 主窗口装配层。"""

    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app
        self._sync_connected = False
        self._last_devices = []
        self._team_page = None
        self._order_page = None
        self._price_page = None
        self.setStyleSheet(MAIN_QSS)
        self._setup_window()
        self._build_ui()
        self._connect_sync()
        logger.debug("MainWindow 初始化完成")

    def _setup_window(self) -> None:
        from game.game_config import WINDOW_TITLE
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.resize(1800, 1200)
        self.setMinimumSize(1280, 800)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._topbar = TopBar(self._app)
        root_layout.addWidget(self._topbar)

        self._tabbar = TabBar(self._on_navigate)
        root_layout.addWidget(self._tabbar)

        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack)

        self._dev_page = DevicePage(self._app)
        self._stack.addWidget(self._dev_page)

        self._stack.addWidget(self._make_placeholder("组队管理", "运行服务启动后加载组队面板"))
        self._stack.addWidget(self._make_placeholder("同服订单", "收到设备上报后加载订单面板"))
        self._stack.addWidget(self._make_placeholder("跨服价格", "收到设备上报后加载价格面板"))

        self._page_index = {"dev": 0, "team": 1, "order": 2, "price": 3}

        from ui.widgets.status_bar_widget import StatusBarWidget
        self._statusbar = StatusBarWidget(self._app)
        root_layout.addWidget(self._statusbar)

    def _make_placeholder(self, title: str, desc: str) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(10)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{TEXT}; font-size:22px; font-weight:700;")
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color:{TEXT_MID}; font-size:13px;")
        lay.addWidget(title_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(desc_lbl, alignment=Qt.AlignmentFlag.AlignCenter)
        return page

    def _replace_stack_widget(self, index: int, widget: QWidget) -> None:
        old = self._stack.widget(index)
        self._stack.removeWidget(old)
        old.deleteLater()
        self._stack.insertWidget(index, widget)

    def _connect_sync(self) -> None:
        if self._sync_connected:
            return
        sync_manager = getattr(self._app, "sync_manager", None)
        if sync_manager is None:
            return
        worker = sync_manager.worker
        worker.devices_updated.connect(self._on_devices_updated)
        worker.sync_error.connect(self._on_sync_error)
        self._sync_connected = True

    def attach_runtime_services(self) -> None:
        if hasattr(self._dev_page, "attach_runtime_services"):
            self._dev_page.attach_runtime_services()
        if hasattr(self._statusbar, "attach_runtime_services"):
            self._statusbar.attach_runtime_services()
        self._connect_sync()

    def _on_devices_updated(self, devices: list) -> None:
        self._last_devices = list(devices)
        self._dev_page.refresh_devices(devices)
        if self._order_page is not None:
            self._order_page.refresh_from_devices(devices)
        if self._price_page is not None:
            self._price_page.refresh_from_devices(devices)

    def _ensure_page(self, page_id: str) -> None:
        if page_id == "team" and self._team_page is None:
            if getattr(self._app, "team_manager", None) is None:
                return
            from ui.widgets.team_widget import TeamWidget
            self._team_page = TeamWidget(self._app)
            self._replace_stack_widget(1, self._team_page)
        elif page_id == "order" and self._order_page is None:
            from ui.widgets.order_widget import OrderWidget
            self._order_page = OrderWidget()
            self._replace_stack_widget(2, self._order_page)
            if self._last_devices:
                self._order_page.refresh_from_devices(self._last_devices)
        elif page_id == "price" and self._price_page is None:
            from ui.widgets.price_monitor_widget import PriceMonitorWidget
            self._price_page = PriceMonitorWidget()
            self._replace_stack_widget(3, self._price_page)
            if self._last_devices:
                self._price_page.refresh_from_devices(self._last_devices)

    def _on_navigate(self, page_id: str) -> None:
        if page_id == "settings":
            self.open_settings()
        else:
            self._ensure_page(page_id)
            self._stack.setCurrentIndex(self._page_index.get(page_id, 0))

    def open_settings(self) -> None:
        from ui.dialogs.global_settings_dialog import GlobalSettingsDialog
        GlobalSettingsDialog(self._app, self).exec()

    def open_log_viewer(self) -> None:
        from ui.widgets.log_viewer_widget import LogViewerDialog
        LogViewerDialog(parent=self).show()

    def _on_sync_error(self, msg: str) -> None:
        logger.warning("同步错误: %s", msg)

    def _on_token_expired(self) -> None:
        """备用入口；实际处理由 Application._on_token_expired() 负责。"""
        pass

    def update_stats(self, total: int, online: int) -> None:
        self._topbar.update_stats(total, online)

    def update_auth_stats(self) -> None:
        self._topbar.update_auth_stats()

    def closeEvent(self, event) -> None:
        if hasattr(self._app, "_stop_runtime_services"):
            self._app._stop_runtime_services()
        if getattr(self._app, "_main_window", None) is self:
            self._app._main_window = None
        super().closeEvent(event)
