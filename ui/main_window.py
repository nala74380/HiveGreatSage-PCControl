r"""
文件位置: ui/main_window.py
名称: 主窗口
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.3.0
状态: P1 UI 边界重构执行中
功能及相关说明:
  登录成功后显示的主操作窗口。
  V1.3.0：主窗口收敛为装配层；设备管理页迁移到 ui/pages/device_page.py。

边界说明:
  - 本文件只负责 TopBar、TabBar、页面装配、同步信号连接。
  - 设备管理页布局由 ui/pages/device_page.py 承担。
  - 本文件不实现远控、投屏、scrcpy、公网远控、Relay 远控。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QVBoxLayout, QWidget

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
    GREEN_BG,
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
    font-family: '{MONO_FONT}', 'Consolas', monospace;
    font-size: 13px;
    color: {TEXT};
}}
#topbar  {{ background: {BG_PANEL}; border-bottom: 1px solid {BORDER}; }}
#tabbar  {{ background: {BG_PANEL}; border-bottom: 2px solid {BORDER}; }}
#statusbar {{ background: {BG_DEEP}; border-top: 1px solid {BG_PANEL}; }}
#filterbar {{ background: {BG_PANEL}; border-bottom: 1px solid {BORDER}; }}
QPushButton#tab-btn {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    color: {TEXT_MID};
    padding: 0 18px;
    font-size: 13px;
    font-family: '{MONO_FONT}', monospace;
}}
QPushButton#tab-btn:hover {{ color: {TEXT}; background: {BG_ITEM}; }}
QPushButton#tab-btn[active="true"] {{
    color: {TEAL};
    border-bottom: 2px solid {TEAL_DK};
    background: transparent;
}}
QPushButton {{
    background: transparent;
    border: 0.5px solid {BORDER2};
    border-radius: 5px;
    color: {TEXT_MID};
    padding: 4px 11px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 12px;
}}
QPushButton:hover {{ background: {BG_ITEM}; color: {TEXT}; }}
QPushButton:disabled {{ color: {TEXT_MUTE}; }}
QMenu {{
    background: {BG_ITEM};
    border: 0.5px solid {BORDER2};
    border-radius: 7px;
    padding: 4px 0;
    font-size: 13px;
    color: {TEXT};
}}
QMenu::item {{ padding: 8px 16px 8px 28px; }}
QMenu::item:selected {{ background: {TEAL_BG}; color: {TEAL}; }}
QMenu::separator {{ height: 1px; background: {BORDER2}; margin: 3px 0; }}
"""


def _badge(text: str, bg: str, fg: str, font_size: int = 11) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background:{bg}; color:{fg}; border-radius:8px;"
        f" padding:2px 8px; font-size:{font_size}px;"
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


class TopBar(QWidget):
    """顶部状态栏。"""

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

        logo = QLabel()
        logo.setText(
            f'<span style="color:{TEXT}; font-size:15px;">蜂巢<span style="color:{TEAL}">·</span>大圣</span>'
            f'<span style="color:{TEXT_DARK}; font-size:10px;"> v1.0.0</span>'
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
        level_colors = {
            "vip": (AMBER_BG, AMBER),
            "svip": ("#26215C", "#AFA9EC"),
            "tester": (TEAL_BG2, TEAL),
            "normal": (BG_ITEM, TEXT_MID),
            "trial": (BG_ITEM, TEXT_DIM),
        }
        bg, fg = level_colors.get(user.user_level, (BG_ITEM, TEXT_MID))
        acct_lay.addWidget(_badge(user.user_level.upper(), bg, fg, 10))
        lay.addWidget(acct)
        lay.addWidget(_sep_v())

        stat = QWidget()
        stat.setFixedHeight(48)
        stat_lay = QHBoxLayout(stat)
        stat_lay.setContentsMargins(14, 0, 14, 0)
        stat_lay.setSpacing(5)
        self._lbl_ava_auth = _label(str(user.device_quota) if user.device_quota > 0 else "无限", GREEN, 14)
        self._lbl_act_auth = _label(str(user.activated_devices), TEAL, 14)
        self._lbl_inact_auth = _label(str(user.inactive_devices) if user.inactive_devices is not None else "—", TEXT_MID, 14)
        for txt, value_label in [
            ("可激活", self._lbl_ava_auth),
            ("已激活", self._lbl_act_auth),
            ("未激活", self._lbl_inact_auth),
        ]:
            stat_lay.addWidget(_label(txt, TEXT_MUTE, 10))
            stat_lay.addWidget(_label("/", BORDER2, 11))
            stat_lay.addWidget(value_label)
            stat_lay.addSpacing(8)
        lay.addWidget(stat)
        lay.addWidget(_sep_v())

        exp = QWidget()
        exp.setFixedHeight(48)
        exp_lay = QHBoxLayout(exp)
        exp_lay.setContentsMargins(14, 0, 14, 0)
        exp_lay.setSpacing(5)
        exp_lay.addWidget(_label("到期：", TEXT_DIM, 11))
        expiry = user.expired_at[:10] if user.expired_at and len(user.expired_at) >= 10 else (user.expired_at or "—")
        exp_lay.addWidget(_label(expiry, AMBER, 12))
        lay.addWidget(exp)
        lay.addWidget(_sep_v())

        conn = QWidget()
        conn.setFixedHeight(48)
        conn_lay = QHBoxLayout(conn)
        conn_lay.setContentsMargins(14, 0, 0, 0)
        conn_lay.setSpacing(6)
        conn_lay.addWidget(_label("●", TEAL_DK, 9))
        api_host = (self._app.config.get("server.api_base_url", "")
                    .replace("http://", "").replace("https://", ""))
        conn_lay.addWidget(_label(f"已连接 · {api_host}", TEAL, 12))
        lay.addWidget(conn)
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

    def update_auth_stats(self) -> None:
        user = self._app.auth.user_info
        self._lbl_ava_auth.setText(str(user.device_quota) if user.device_quota > 0 else "无限")
        self._lbl_act_auth.setText(str(user.activated_devices))
        self._lbl_inact_auth.setText(str(user.inactive_devices) if user.inactive_devices is not None else "—")

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

        from ui.widgets.team_widget import TeamWidget
        self._team_page = TeamWidget(self._app)
        self._stack.addWidget(self._team_page)

        from ui.widgets.order_widget import OrderWidget
        self._order_page = OrderWidget()
        self._stack.addWidget(self._order_page)

        from ui.widgets.price_monitor_widget import PriceMonitorWidget
        self._price_page = PriceMonitorWidget()
        self._stack.addWidget(self._price_page)

        self._page_index = {"dev": 0, "team": 1, "order": 2, "price": 3}

        from ui.widgets.status_bar_widget import StatusBarWidget
        self._statusbar = StatusBarWidget(self._app)
        root_layout.addWidget(self._statusbar)

    def _connect_sync(self) -> None:
        worker = self._app.sync_manager.worker
        worker.devices_updated.connect(self._dev_page.refresh_devices)
        worker.devices_updated.connect(self._order_page.refresh_from_devices)
        worker.devices_updated.connect(self._price_page.refresh_from_devices)
        worker.sync_error.connect(self._on_sync_error)

    def _on_navigate(self, page_id: str) -> None:
        if page_id == "settings":
            self.open_settings()
        else:
            self._stack.setCurrentIndex(self._page_index.get(page_id, 0))

    def open_settings(self) -> None:
        from ui.widgets.settings_dialog import SettingsDialog
        SettingsDialog(self._app, self).exec()

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

    def closeEvent(self, event) -> None:
        self._app.sync_manager.stop()
        super().closeEvent(event)
