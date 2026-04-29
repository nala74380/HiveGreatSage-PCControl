r"""
文件位置: ui/login_window.py
名称: 登录窗口
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.3
功能及相关说明:
  用户登录界面（420×540 逻辑像素，固定大小）。
  深色主题，蜂巢品牌风格。
  密码显示/隐藏按钮内嵌在输入框右侧（PasswordLineEdit 子类实现）。
  登录 API 调用在 LoginWorker（QThread）中执行，不阻塞 UI。

改进内容:
  V1.0.3 - 修复 _eye_icon 双 QPainter bug；修复 field-label QSS 选择器；清理未使用 import
  V1.0.2 - 全新暗色设计，密码眼睛按钮内嵌
  V1.0.1 - 密码框新增显示/隐藏切换按钮
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
import math

from PySide6.QtCore import Qt, QThread, Signal, QSize, QPointF, QRectF
from PySide6.QtGui import (
    QColor, QIcon, QPainter, QPainterPath,
    QPixmap, QLinearGradient, QPen,
)
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from core.auth.auth_manager import AuthManager
from core.auth.models import LoginResult

logger = logging.getLogger(__name__)

# ── 调色板 ────────────────────────────────────────────────────
_BG_WINDOW     = "#0d1117"
_BG_INPUT      = "#111827"
_BORDER_BASE   = "#1e2d45"
_BORDER_FOCUS  = "#0ea5e9"
_ACCENT_BLUE   = "#0ea5e9"
_ACCENT_INDIGO = "#6366f1"
_TEXT_PRIMARY  = "#e8edf5"
_TEXT_LABEL    = "#6b7fa3"
_TEXT_HINT     = "#3a4a62"
_TEXT_ERROR    = "#f87171"
_TEXT_INFO     = "#38bdf8"

# ── field-label 样式（直接内联，不走 QSS 类选择器）────────────
_FIELD_LABEL_STYLE = (
    f"color: {_TEXT_LABEL}; font-size: 11px; font-weight: 600; letter-spacing: 1px;"
)

_STYLE = f"""
QDialog {{
    background-color: {_BG_WINDOW};
}}

QLabel#title {{
    color: {_TEXT_PRIMARY};
    font-size: 20px;
    font-weight: 600;
}}

QLabel#subtitle {{
    color: {_TEXT_LABEL};
    font-size: 12px;
    letter-spacing: 1px;
}}

QLineEdit {{
    background-color: {_BG_INPUT};
    border: 1.5px solid {_BORDER_BASE};
    border-radius: 10px;
    color: {_TEXT_PRIMARY};
    font-size: 14px;
    padding: 0px 12px;
    selection-background-color: {_ACCENT_BLUE};
}}

QLineEdit:focus {{
    border: 1.5px solid {_BORDER_FOCUS};
    background-color: #0f1623;
}}

QCheckBox {{
    color: {_TEXT_LABEL};
    font-size: 13px;
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1.5px solid {_BORDER_BASE};
    background: {_BG_INPUT};
}}

QCheckBox::indicator:checked {{
    background: {_ACCENT_BLUE};
    border-color: {_ACCENT_BLUE};
    image: none;
}}

QPushButton#login-btn {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {_ACCENT_BLUE}, stop:1 {_ACCENT_INDIGO});
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 1px;
}}

QPushButton#login-btn:hover {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #38bdf8, stop:1 #818cf8);
}}

QPushButton#login-btn:pressed {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 #0284c7, stop:1 #4f46e5);
}}

QPushButton#login-btn:disabled {{
    background: #1e2d45;
    color: {_TEXT_HINT};
}}

QLabel#version-label {{
    color: {_TEXT_HINT};
    font-size: 11px;
}}
"""


# ──────────────────────────────────────────────
#  密码输入框（眼睛按钮内嵌）
# ──────────────────────────────────────────────

class PasswordLineEdit(QLineEdit):
    """内嵌显示/隐藏密码按钮的 QLineEdit。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setEchoMode(QLineEdit.EchoMode.Password)

        self._eye_btn = QToolButton(self)
        self._eye_btn.setCheckable(True)
        self._eye_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._eye_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._eye_btn.setStyleSheet(
            "QToolButton { border: none; background: transparent; padding: 0; }"
        )
        self._eye_btn.setIcon(self._eye_icon(visible=False))
        self._eye_btn.setIconSize(QSize(18, 18))
        self._eye_btn.toggled.connect(self._on_toggle)
        self.setTextMargins(0, 0, 32, 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._eye_btn.setGeometry(self.width() - 34, 0, 32, self.height())

    def _on_toggle(self, checked: bool) -> None:
        self.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        self._eye_btn.setIcon(self._eye_icon(visible=checked))

    @staticmethod
    def _eye_icon(visible: bool) -> QIcon:
        """
        用单个 QPainter 绘制眼睛图标。
        visible=True  → 明亮眼睛（密码可见状态）
        visible=False → 暗淡眼睛+斜线（密码隐藏状态）
        """
        size = 18
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)

        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        eye_color = QColor("#8ba0be") if visible else QColor("#4b6080")

        # ── 眼睛轮廓 ──
        pen = QPen(eye_color, 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)

        path = QPainterPath()
        path.moveTo(2, 9)
        path.cubicTo(2, 9, 6, 4, 9, 4)
        path.cubicTo(12, 4, 16, 9, 16, 9)
        path.cubicTo(16, 9, 12, 14, 9, 14)
        path.cubicTo(6, 14, 2, 9, 2, 9)
        p.drawPath(path)

        # ── 瞳孔 ──
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(eye_color)
        p.drawEllipse(QRectF(6.5, 6.5, 5.0, 5.0))

        # ── 隐藏状态：斜线划掉 ──
        if not visible:
            slash_pen = QPen(QColor("#4b6080"), 1.5, Qt.PenStyle.SolidLine,
                             Qt.PenCapStyle.RoundCap)
            p.setPen(slash_pen)
            p.drawLine(QPointF(3.5, 3.5), QPointF(14.5, 14.5))

        p.end()
        return QIcon(px)


# ──────────────────────────────────────────────
#  后台登录线程
# ──────────────────────────────────────────────

class LoginWorker(QThread):
    finished = Signal(object)   # LoginResult

    def __init__(self, auth: AuthManager, username: str, password: str, remember: bool) -> None:
        super().__init__()
        self._auth     = auth
        self._username = username
        self._password = password
        self._remember = remember

    def run(self) -> None:
        result = self._auth.login(self._username, self._password, self._remember)
        self.finished.emit(result)


# ──────────────────────────────────────────────
#  登录窗口
# ──────────────────────────────────────────────

class LoginWindow(QDialog):
    """登录窗口，420×540 固定大小，深色蜂巢主题。"""

    def __init__(self, auth: AuthManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._auth   = auth
        self._worker: LoginWorker | None = None

        self.setStyleSheet(_STYLE)
        self._setup_window()
        self._build_ui()
        self._load_saved_credentials()

    # ── 窗口基础配置 ──────────────────────
    def _setup_window(self) -> None:
        from game.game_config import GAME_NAME
        self.setWindowTitle(f"蜂巢·大圣 — {GAME_NAME} 登录")
        self.setFixedSize(420, 540)
        # 完全无边框，去掉系统标题栏
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

    # ── UI 构建 ───────────────────────────
    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 16, 40, 32)
        root.setSpacing(0)

        # ── 自定义关闭按鈕（无标题栏，右上角）──
        close_row = QHBoxLayout()
        close_row.setContentsMargins(0, 0, 0, 0)
        close_row.addStretch()
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { border: none; background: transparent;"
            f" color: {_TEXT_HINT}; font-size: 18px; font-weight: 300; }}"
            f"QPushButton:hover {{ color: {_TEXT_PRIMARY}; }}"
        )
        close_btn.clicked.connect(self.reject)
        close_row.addWidget(close_btn)
        root.addLayout(close_row)
        root.addSpacing(4)

        # ── Logo + 标题区 ──
        root.addLayout(self._build_header())
        root.addSpacing(32)

        # ── 用户名 ──
        lbl_user = QLabel("用户名")
        lbl_user.setStyleSheet(_FIELD_LABEL_STYLE)
        root.addWidget(lbl_user)
        root.addSpacing(8)
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("请输入用户名")
        self._username_input.setFixedHeight(46)
        root.addWidget(self._username_input)
        root.addSpacing(16)

        # ── 密码 ──
        lbl_pwd = QLabel("密码")
        lbl_pwd.setStyleSheet(_FIELD_LABEL_STYLE)
        root.addWidget(lbl_pwd)
        root.addSpacing(8)
        self._password_input = PasswordLineEdit()
        self._password_input.setPlaceholderText("请输入密码")
        self._password_input.setFixedHeight(46)
        self._password_input.returnPressed.connect(self._on_login_clicked)
        root.addWidget(self._password_input)
        root.addSpacing(16)

        # ── 记住密码 ──
        self._remember_cb = QCheckBox("记住密码")
        root.addWidget(self._remember_cb)
        root.addSpacing(10)

        # ── 状态提示 ──
        self._status_label = QLabel("")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setWordWrap(True)
        self._status_label.setFixedHeight(32)
        self._status_label.setStyleSheet("color: transparent; font-size: 12px;")
        root.addWidget(self._status_label)
        root.addSpacing(8)

        # ── 登录按钮 ──
        self._login_btn = QPushButton("登  录")
        self._login_btn.setObjectName("login-btn")
        self._login_btn.setFixedHeight(50)
        self._login_btn.setDefault(True)
        self._login_btn.clicked.connect(self._on_login_clicked)
        root.addWidget(self._login_btn)

        root.addStretch()

        # ── 版本号 ──
        ver = QLabel("v1.0.0 · 椰芽专用版")
        ver.setObjectName("version-label")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(ver)

    def _build_header(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        logo_label = QLabel()
        logo_label.setFixedSize(60, 60)
        logo_label.setPixmap(self._make_logo_pixmap(60))
        logo_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        title = QLabel("蜂巢·大圣")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        subtitle = QLabel("PC 中控  ·  椰芽")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(14)
        layout.addWidget(title)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        return layout

    # ── 已保存凭据 ────────────────────────
    def _load_saved_credentials(self) -> None:
        username = self._auth.get_saved_username()
        if username:
            self._username_input.setText(username)
            password = self._auth.get_saved_password(username)
            if password:
                self._password_input.setText(password)
                self._remember_cb.setChecked(True)
                self._login_btn.setFocus()
            else:
                self._password_input.setFocus()
        else:
            self._username_input.setFocus()

    # ── 登录点击 ──────────────────────────
    def _on_login_clicked(self) -> None:
        username = self._username_input.text().strip()
        password = self._password_input.text()

        if not username:
            self._show_status("请输入用户名", error=True)
            self._username_input.setFocus()
            return
        if not password:
            self._show_status("请输入密码", error=True)
            self._password_input.setFocus()
            return

        self._set_loading(True)
        self._show_status("正在连接服务器...", error=False)

        self._worker = LoginWorker(
            self._auth, username, password, self._remember_cb.isChecked()
        )
        self._worker.finished.connect(self._on_login_done)
        self._worker.start()

    # ── 登录结果回调 ──────────────────────
    def _on_login_done(self, result: LoginResult) -> None:
        self._set_loading(False)

        if result.success:
            logger.info("登录窗口：登录成功")
            self.accept()
        else:
            self._show_status(result.error_message or "登录失败，请重试", error=True)
            if result.error_code in ("INVALID_CREDENTIALS", "USER_NOT_FOUND"):
                self._password_input.clear()
                self._password_input.setFocus()

    # ── 辅助方法 ──────────────────────────
    def _set_loading(self, loading: bool) -> None:
        self._login_btn.setEnabled(not loading)
        self._username_input.setEnabled(not loading)
        self._password_input.setEnabled(not loading)
        self._remember_cb.setEnabled(not loading)
        self._login_btn.setText("登录中..." if loading else "登  录")

    def _show_status(self, message: str, error: bool = True) -> None:
        color = _TEXT_ERROR if error else _TEXT_INFO
        self._status_label.setText(message)
        self._status_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    @staticmethod
    def _make_logo_pixmap(size: int) -> QPixmap:
        """绘制六边形蜂巢 Logo。"""
        px = QPixmap(size, size)
        px.fill(Qt.GlobalColor.transparent)
        p = QPainter(px)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0, QColor(_ACCENT_BLUE))
        grad.setColorAt(1, QColor(_ACCENT_INDIGO))

        cx, cy = size / 2, size / 2
        r = size / 2 - 2
        outer = QPainterPath()
        for i in range(6):
            angle = math.radians(i * 60 - 30)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            outer.moveTo(x, y) if i == 0 else outer.lineTo(x, y)
        outer.closeSubpath()
        p.fillPath(outer, grad)

        r2 = r * 0.44
        inner = QPainterPath()
        for i in range(6):
            angle = math.radians(i * 60 - 30)
            x = cx + r2 * math.cos(angle)
            y = cy + r2 * math.sin(angle)
            inner.moveTo(x, y) if i == 0 else inner.lineTo(x, y)
        inner.closeSubpath()
        p.fillPath(inner, QColor(255, 255, 255, 220))

        p.end()
        return px

    # ── 关闭时停止线程 ────────────────────
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if hasattr(self, "_drag_pos"):
            del self._drag_pos
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(3000)
        super().closeEvent(event)
