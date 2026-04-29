r"""
文件位置: ui/widgets/log_viewer_widget.py
名称: 日志查看器弹窗
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  实时滚动显示本地运行日志（logs/pccontrol.log）。
  使用 QTimer 每秒轮询文件变化，追加新内容。
  支持过滤级别（DEBUG/INFO/WARNING/ERROR）。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QTextCursor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import (
    BG_DEEP, BG_PANEL, BG_MAIN, BORDER, BORDER2,
    TEAL, TEAL_DK, TEAL_BG,
    AMBER, RED,
    TEXT, TEXT_MID, TEXT_MUTE, TEXT_DARK,
    MONO_FONT,
)

logger = logging.getLogger(__name__)

_LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "pccontrol.log"

# 每级别对应的文字颜色
_LEVEL_COLORS = {
    "DEBUG":   TEXT_DARK,
    "INFO":    TEXT_MID,
    "WARNING": AMBER,
    "ERROR":   RED,
    "CRITICAL": "#FF4444",
}


class LogViewerDialog(QDialog):
    """
    日志查看器，600×460 固定大小。
    实时追加 logs/pccontrol.log 新行，支持按级别过滤。
    """

    def __init__(self, title: str = "运行日志", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title    = title
        self._file_pos = 0     # 上次读取到的文件字节偏移
        self._filter_levels: set[str] = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

        self.setWindowTitle(title)
        self.setFixedSize(700, 460)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"""
            QDialog {{
                background: {BG_MAIN};
                font-family: '{MONO_FONT}', monospace;
                font-size: 11px;
                color: {TEXT};
            }}
            QPushButton {{
                background: transparent; border: 0.5px solid {BORDER2};
                border-radius: 5px; color: {TEXT_MID};
                padding: 4px 12px; font-family: '{MONO_FONT}', monospace; font-size: 10px;
            }}
            QPushButton:hover {{ background: {BG_PANEL}; color: {TEXT}; }}
            QPushButton#clear-btn {{
                border-color: #412402; color: {AMBER};
            }}
            QCheckBox {{ color: {TEXT_MID}; font-size: 10px; spacing: 5px; }}
            QCheckBox::indicator {{
                width: 13px; height: 13px;
                border: 1px solid {BORDER2}; border-radius: 2px; background: transparent;
            }}
            QCheckBox::indicator:checked {{ background: {TEAL_DK}; border-color: {TEAL_DK}; }}
        """)

        self._build()
        self._load_initial()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_new_lines)
        self._timer.start(1000)

    # ── UI ───────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 顶部工具栏 ──
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        toolbar.setFixedHeight(36)
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(12, 0, 12, 0)
        tl.setSpacing(12)

        lbl = QLabel("级别过滤：")
        lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:9px;")
        tl.addWidget(lbl)

        self._chk_boxes: dict[str, QCheckBox] = {}
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            chk = QCheckBox(level)
            chk.setChecked(True)
            chk.toggled.connect(lambda checked, lv=level: self._toggle_level(lv, checked))
            self._chk_boxes[level] = chk
            tl.addWidget(chk)

        tl.addStretch()

        self._auto_scroll_chk = QCheckBox("自动滚动")
        self._auto_scroll_chk.setChecked(True)
        tl.addWidget(self._auto_scroll_chk)

        clear_btn = QPushButton("清屏")
        clear_btn.setObjectName("clear-btn")
        clear_btn.clicked.connect(self._clear)
        tl.addWidget(clear_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        tl.addWidget(close_btn)

        root.addWidget(toolbar)

        # ── 日志文本区 ──
        self._text = QPlainTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {BG_DEEP};
                color: {TEXT_MID};
                border: none;
                font-family: '{MONO_FONT}', monospace;
                font-size: 10px;
                line-height: 1.6;
                padding: 8px;
            }}
        """)
        # 最多保留 5000 行
        self._text.setMaximumBlockCount(5000)
        root.addWidget(self._text)

        # ── 底部状态栏 ──
        status_bar = QWidget()
        status_bar.setStyleSheet(f"background:{BG_PANEL}; border-top:1px solid {BORDER};")
        status_bar.setFixedHeight(22)
        sl = QHBoxLayout(status_bar)
        sl.setContentsMargins(12, 0, 12, 0)
        self._status_lbl = QLabel(f"日志文件：{_LOG_FILE}")
        self._status_lbl.setStyleSheet(f"color:{TEXT_DARK}; font-size:9px;")
        sl.addWidget(self._status_lbl)
        sl.addStretch()
        self._line_lbl = QLabel("0 行")
        self._line_lbl.setStyleSheet(f"color:{TEXT_DARK}; font-size:9px;")
        sl.addWidget(self._line_lbl)
        root.addWidget(status_bar)

    # ── 日志读取 ─────────────────────────────────

    def _load_initial(self) -> None:
        """首次打开时加载最后 500 行。"""
        if not _LOG_FILE.exists():
            self._append_line("(日志文件尚未生成)", TEXT_MUTE)
            return
        try:
            with open(_LOG_FILE, encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                self._file_pos = _LOG_FILE.stat().st_size
            # 只显示最后 500 行
            for line in lines[-500:]:
                self._append_line(line.rstrip())
            self._update_line_count()
        except Exception as e:
            self._append_line(f"读取日志失败: {e}", RED)

    def _poll_new_lines(self) -> None:
        """每秒检查是否有新日志行追加。"""
        if not _LOG_FILE.exists():
            return
        try:
            size = _LOG_FILE.stat().st_size
            if size <= self._file_pos:
                return
            with open(_LOG_FILE, encoding="utf-8", errors="replace") as f:
                f.seek(self._file_pos)
                new_content = f.read()
            self._file_pos = size
            for line in new_content.splitlines():
                self._append_line(line)
            self._update_line_count()
        except Exception:
            pass

    def _append_line(self, line: str, force_color: str | None = None) -> None:
        """将一行日志追加到文本框，根据级别着色。"""
        color = force_color or self._detect_color(line)
        # 级别过滤
        level = self._detect_level(line)
        if level and level not in self._filter_levels:
            return

        # 插入带颜色的文本
        cursor = self._text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = cursor.charFormat()
        fmt.setForeground(QColor(color))
        cursor.setCharFormat(fmt)
        cursor.insertText(line + "\n")

        if self._auto_scroll_chk.isChecked():
            self._text.setTextCursor(cursor)
            self._text.ensureCursorVisible()

    def _detect_level(self, line: str) -> str | None:
        for lv in ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]:
            if f"[{lv}]" in line:
                return lv
        return None

    def _detect_color(self, line: str) -> str:
        level = self._detect_level(line)
        return _LEVEL_COLORS.get(level, TEXT_MID)

    # ── 交互 ─────────────────────────────────────

    def _toggle_level(self, level: str, checked: bool) -> None:
        if checked:
            self._filter_levels.add(level)
        else:
            self._filter_levels.discard(level)

    def _clear(self) -> None:
        self._text.clear()
        self._update_line_count()

    def _update_line_count(self) -> None:
        n = self._text.document().blockCount()
        self._line_lbl.setText(f"{n} 行")

    def closeEvent(self, event) -> None:
        self._timer.stop()
        super().closeEvent(event)
