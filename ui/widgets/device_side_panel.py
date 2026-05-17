r"""
文件位置: ui/widgets/device_side_panel.py
名称: 设备管理页右侧中控侧栏
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.0.0
状态: P1 UI 边界重构执行中
功能及相关说明:
  设备管理页右侧中控侧栏骨架。
  当前只承载设备统计、分组摘要、列显示说明、自动刷新说明、当前选中摘要。
  不承载游戏组队逻辑；不承载远控/投屏入口。
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.device.models import DeviceInfo
from ui.styles.colors import (
    BG_PANEL,
    BG_DEEP,
    BG_ITEM,
    BORDER,
    BORDER2,
    TEAL,
    TEXT,
    TEXT_MID,
    TEXT_MUTE,
    MONO_FONT,
)


@dataclass(frozen=True)
class DeviceStats:
    total: int = 0
    online: int = 0
    offline: int = 0
    error: int = 0
    activated: int = 0
    inactive: int = 0
    heartbeat_timeout: int = 0
    selected: int = 0
    selected_online: int = 0
    selected_error: int = 0


class DeviceSidePanel(QWidget):
    """设备页右侧中控侧栏。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("device-side-panel")
        self.setFixedWidth(230)
        self.setStyleSheet(
            f"QWidget#device-side-panel {{ background:{BG_PANEL}; border-left:1px solid {BORDER}; }}"
            f"QLabel {{ font-family:'{MONO_FONT}',monospace; }}"
        )
        self._stat_labels: dict[str, QLabel] = {}
        self._selected_labels: dict[str, QLabel] = {}
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        root.addWidget(self._section_title("数据统计"))
        for key, title in [
            ("total", "设备总数"),
            ("online", "在线设备"),
            ("offline", "离线设备"),
            ("error", "异常设备"),
            ("activated", "已激活"),
            ("inactive", "未激活"),
            ("heartbeat_timeout", "心跳超时"),
        ]:
            lbl = self._kv(root, title, "0")
            self._stat_labels[key] = lbl

        root.addWidget(self._section_title("分组信息"))
        root.addWidget(self._hint("P1 骨架：设备分组属于中控管理能力，不等同于游戏组队。"))
        root.addWidget(self._small_button("保存分组（待实现）"))
        root.addWidget(self._small_button("删除分组（待实现）"))

        root.addWidget(self._section_title("列显示/隐藏"))
        root.addWidget(self._hint("P1 骨架：后续迁移为列注册表与列显隐面板。"))

        root.addWidget(self._section_title("自动刷新"))
        root.addWidget(self._hint("P1 骨架：当前刷新仍由同步线程驱动。后续提供会话级临时刷新间隔。"))

        root.addWidget(self._section_title("当前选中"))
        for key, title in [
            ("selected", "已选设备"),
            ("selected_online", "选中在线"),
            ("selected_error", "选中异常"),
        ]:
            lbl = self._kv(root, title, "0")
            self._selected_labels[key] = lbl

        root.addStretch()

    def update_devices(self, devices: list[DeviceInfo], visible_devices: list[DeviceInfo] | None = None) -> None:
        """根据当前设备列表更新统计。"""
        source = visible_devices if visible_devices is not None else devices
        total = len(source)
        online = sum(1 for d in source if d.is_online)
        error = sum(1 for d in source if d.api_status == "error")
        activated = sum(1 for d in source if d.activated)
        stats = DeviceStats(
            total=total,
            online=online,
            offline=max(total - online, 0),
            error=error,
            activated=activated,
            inactive=max(total - activated, 0),
            heartbeat_timeout=sum(1 for d in source if d.api_status == "offline"),
        )
        self._apply_stats(stats)

    def update_selection(self, selected: list[DeviceInfo]) -> None:
        """更新当前选中摘要。"""
        values = {
            "selected": len(selected),
            "selected_online": sum(1 for d in selected if d.is_online),
            "selected_error": sum(1 for d in selected if d.api_status == "error"),
        }
        for key, value in values.items():
            if key in self._selected_labels:
                self._selected_labels[key].setText(str(value))

    def _apply_stats(self, stats: DeviceStats) -> None:
        values = {
            "total": stats.total,
            "online": stats.online,
            "offline": stats.offline,
            "error": stats.error,
            "activated": stats.activated,
            "inactive": stats.inactive,
            "heartbeat_timeout": stats.heartbeat_timeout,
        }
        for key, value in values.items():
            if key in self._stat_labels:
                self._stat_labels[key].setText(str(value))

    @staticmethod
    def _section_title(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color:{TEAL}; font-size:11px; font-weight:600; padding-top:4px;"
            f"border-bottom:1px solid {BORDER};"
        )
        return lbl

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px; line-height:1.4;")
        return lbl

    @staticmethod
    def _small_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setEnabled(False)
        btn.setStyleSheet(
            f"background:{BG_DEEP}; border:0.5px solid {BORDER2}; color:{TEXT_MUTE};"
            f"border-radius:5px; padding:4px 6px; font-size:10px;"
        )
        return btn

    @staticmethod
    def _kv(root: QVBoxLayout, key: str, value: str) -> QLabel:
        row = QWidget()
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        k = QLabel(key)
        k.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        v = QLabel(value)
        v.setStyleSheet(f"color:{TEXT}; font-size:12px; font-weight:600;")
        lay.addWidget(k)
        lay.addStretch()
        lay.addWidget(v)
        row.setStyleSheet(f"background:{BG_ITEM}; border-radius:4px; padding:2px;")
        root.addWidget(row)
        return v
