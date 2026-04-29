r"""
文件位置: ui/widgets/status_bar_widget.py
名称: 底部状态栏组件
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  独立抽取的底部状态栏，统一管理：
    · API 连接状态
    · Access Token 剩余时间（每秒倒计时）
    · 同步间隔
    · 局域网 IP 和 WS 连接数
    · 版本信息 / 分辨率

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget

from ui.styles.colors import (
    BG_DEEP, BG_PANEL, BORDER,
    TEAL, TEAL_DK,
    AMBER,
    TEXT_MID, TEXT_MUTE, TEXT_DARK,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)


class StatusBarWidget(QWidget):
    """底部状态栏，22px 高。"""

    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app
        self.setObjectName("statusbar")
        self.setFixedHeight(22)
        self.setStyleSheet(
            f"background:{BG_DEEP}; border-top:1px solid {BG_PANEL};"
            f" font-family:'{MONO_FONT}',monospace; font-size:9px; color:{TEXT_DARK};"
        )
        self._build()
        self._start_token_timer()

    def _build(self) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 12, 0)
        lay.setSpacing(14)

        # API 连接
        api = self._app.config.get("server.api_base_url", "").replace("http://", "")
        self._conn_lbl = self._lbl(f"● {api}", "#0F6E56")
        lay.addWidget(self._conn_lbl)

        # Token 倒计时
        self._token_lbl = self._lbl("Token —", TEXT_DARK)
        lay.addWidget(self._token_lbl)

        # 同步间隔
        interval = self._app.config.get("sync.interval", 10)
        lay.addWidget(self._lbl(f"同步 {interval}s", TEXT_DARK))

        # 局域网（如果 team_manager 存在）
        try:
            ip   = self._app.team_manager.lan_ip
            port = self._app.team_manager.ws_server.port
            self._lan_lbl = self._lbl(f"LAN {ip}:{port}", TEXT_DARK)
            lay.addWidget(self._lan_lbl)
            # 连接计数
            self._ws_count_lbl = self._lbl("WS 0", TEXT_DARK)
            lay.addWidget(self._ws_count_lbl)
            self._app.team_manager.ws_server.device_connected.connect(self._update_ws_count)
            self._app.team_manager.ws_server.device_disconnected.connect(self._update_ws_count)
        except Exception:
            pass

        lay.addStretch()

        from game.game_config import WINDOW_TITLE, GAME_VERSION
        scr  = QApplication.primaryScreen()
        geom = scr.geometry() if scr else None
        res  = f"{geom.width()}×{geom.height()}" if geom else "—"
        lay.addWidget(self._lbl(
            f"{WINDOW_TITLE} v{GAME_VERSION} · Windows · {res}", TEXT_DARK
        ))

    def _lbl(self, text: str, color: str) -> QLabel:
        l = QLabel(text)
        l.setStyleSheet(f"color:{color}; font-size:9px;")
        return l

    # ── Token 倒计时 ──────────────────────────────

    def _start_token_timer(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_token_time)
        self._timer.start(1000)

    def _update_token_time(self) -> None:
        """尝试从 JWT 解析剩余时间（不依赖 PyJWT，手动 base64 解码）。"""
        token = self._app.auth.access_token
        if not token:
            self._token_lbl.setText("Token —")
            self._token_lbl.setStyleSheet(f"color:{TEXT_DARK}; font-size:9px;")
            return

        try:
            import base64, json as _json, time
            payload_b64 = token.split(".")[1]
            # 补齐 padding
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload     = _json.loads(base64.urlsafe_b64decode(payload_b64))
            exp         = int(payload.get("exp", 0))
            remaining   = exp - int(time.time())

            if remaining <= 0:
                self._token_lbl.setText("Token 已过期")
                self._token_lbl.setStyleSheet(f"color:{AMBER}; font-size:9px;")
            elif remaining < 120:
                m, s = divmod(remaining, 60)
                self._token_lbl.setText(f"Token {m:02d}:{s:02d}")
                self._token_lbl.setStyleSheet(f"color:{AMBER}; font-size:9px;")
            else:
                m, s = divmod(remaining, 60)
                h, m = divmod(m, 60)
                self._token_lbl.setText(f"Token {h:02d}:{m:02d}:{s:02d}")
                self._token_lbl.setStyleSheet(f"color:{TEXT_DARK}; font-size:9px;")
        except Exception:
            self._token_lbl.setText("Token —")

    def _update_ws_count(self, *_) -> None:
        count = self._app.team_manager.connected_count
        if hasattr(self, "_ws_count_lbl"):
            self._ws_count_lbl.setText(f"WS {count}")
            color = TEAL if count > 0 else TEXT_DARK
            self._ws_count_lbl.setStyleSheet(f"color:{color}; font-size:9px;")
