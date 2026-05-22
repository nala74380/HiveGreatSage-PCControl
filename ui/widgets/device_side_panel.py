r"""
文件位置: ui/widgets/device_side_panel.py
名称: 设备管理页右侧中控侧栏
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-18
版本: V1.2.0
状态: P3.4-c LAN IP 自动匹配
功能及相关说明:
  设备管理页右侧中控侧栏。
  承载设备统计、分组摘要、列显示说明、自动刷新说明和人工操作提示。
  设备绑定主键统一为 device_id，不使用隐藏设备唯一标识。
  不承载远控/投屏入口。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from core.device.models import DeviceInfo
from ui.styles.colors import (
    BG_PANEL,
    BG_DEEP,
    BG_ITEM,
    BORDER,
    BORDER2,
    TEXT,
    TEXT_MID,
    TEXT_MUTE,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.device.adb_link_manager import AdbConnectionLink
    from core.team.team_manager import TeamMember


@dataclass(frozen=True)
class DeviceStats:
    total: int = 0
    online: int = 0
    offline: int = 0
    error: int = 0
    activated: int = 0
    inactive: int = 0
    heartbeat_timeout: int = 0


class DeviceSidePanel(QWidget):
    """设备页右侧中控侧栏。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("device-side-panel")
        self.setFixedWidth(250)
        self.setStyleSheet(
            f"QWidget#device-side-panel {{ background:{BG_PANEL}; border-left:1px solid {BORDER}; }}"
            f"QLabel {{ font-family:'{MONO_FONT}',monospace; }}"
        )
        self._stat_labels: dict[str, QLabel] = {}
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        stats_box, stats_lay = self._group("数据统计")
        for key, title in [
            ("total", "设备总数"),
            ("online", "在线设备"),
            ("offline", "离线设备"),
            ("error", "异常设备"),
            ("activated", "已激活"),
            ("inactive", "未激活"),
            ("heartbeat_timeout", "心跳超时"),
        ]:
            lbl = self._kv(stats_lay, title, "0")
            self._stat_labels[key] = lbl
        root.addWidget(stats_box)

        group_box, group_lay = self._group("分组信息")
        group_lay.addWidget(self._hint("设备分组只用于 PC 中控本地管理，不等同于游戏内组队，也不改变 Verify 绑定关系。"))
        group_lay.addWidget(self._hint("建议分组方式：主线号、刷野号、材料号、测试号。后续批量设置会优先按分组下发。"))
        btn_row = QWidget()
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        btn_lay.setSpacing(6)
        btn_lay.addWidget(self._small_button("保存分组（待接入）"))
        btn_lay.addWidget(self._small_button("删除分组（待接入）"))
        group_lay.addWidget(btn_row)
        root.addWidget(group_box)

        column_box, column_lay = self._group("列显示 / 隐藏")
        column_lay.addWidget(self._hint("在设备表表头右键，可以切换列显示、选择列组预设、保存当前列宽。"))
        column_lay.addWidget(self._hint("基础视图：编号 + 状态 + 心跳。"))
        column_lay.addWidget(self._hint("运行视图：编号 + 角色 + 任务 + 区服 + 心跳 + 备注。"))
        column_lay.addWidget(self._hint("完整视图：显示全部列，适合排查设备数据。"))
        root.addWidget(column_box)

        refresh_box, refresh_lay = self._group("自动刷新")
        refresh_lay.addWidget(self._hint("设备主表由 SyncWorker 从 Verify API 周期刷新，刷新间隔读取全局配置。"))
        refresh_lay.addWidget(self._hint("安卓端心跳正常且 PC 中控能检查到 ADB 设备时显示在线；心跳异常或 ADB 不可控会进入离线/异常判断。"))
        refresh_lay.addWidget(self._hint("手动刷新用于立即拉取 Verify 设备列表，不改变设备绑定数量。"))
        root.addWidget(refresh_box)

        action_box, action_lay = self._group("操作提示")
        action_lay.addWidget(self._hint("激活：仅在安卓端离线/异常且本机能找到 ADB 设备时下发 ROOT 激活命令。"))
        action_lay.addWidget(self._hint("设置：进入单设备配置页，当前保存为本地草稿，后端配置接口仍需后续联调。"))
        action_lay.addWidget(self._hint("解绑：后续应走 Verify 设备解绑接口，不能只删除 PC 本地显示。"))
        root.addWidget(action_box)

        root.addStretch()

    def update_devices(self, devices: list[DeviceInfo], visible_devices: list[DeviceInfo] | None = None) -> None:
        """根据当前 Verify 设备列表更新统计。"""
        source = visible_devices if visible_devices is not None else devices
        total = len(source)
        online = sum(1 for d in source if d.display_status_key == "online")
        error = sum(1 for d in source if d.display_status_key == "error")
        activated = sum(1 for d in source if d.activated)
        stats = DeviceStats(
            total=total,
            online=online,
            offline=sum(1 for d in source if d.display_status_key == "offline"),
            error=error,
            activated=activated,
            inactive=max(total - activated, 0),
            heartbeat_timeout=sum(1 for d in source if d.display_status_key == "offline"),
        )
        self._apply_stats(stats)

    def update_lan_members(
        self,
        members: list["TeamMember"],
        verify_devices: list[DeviceInfo] | None = None,
        adb_links: dict[str, "AdbConnectionLink"] | None = None,
    ) -> None:
        """兼容 DevicePage 调用；该实时连接摘要不再放到右侧文本区。"""
        return

    def update_selection(self, selected: list[DeviceInfo]) -> None:
        """兼容 DevicePage 调用；勾选汇总交给底部工具栏承载。"""
        return

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
    def _group(title: str) -> tuple[QGroupBox, QVBoxLayout]:
        group = QGroupBox(title)
        group.setStyleSheet(
            "QGroupBox {"
            f"background:{BG_PANEL};"
            "border:2px solid #0B84FF;"
            "border-radius:6px;"
            "margin-top:8px;"
            f"color:{TEXT};"
            "font-size:12px;"
            "font-weight:600;"
            "}"
            "QGroupBox::title {"
            "subcontrol-origin: margin;"
            "left:8px;"
            "padding:0 5px;"
            f"background:{BG_PANEL};"
            f"color:{TEXT_MID};"
            "}"
        )
        lay = QVBoxLayout(group)
        lay.setContentsMargins(8, 12, 8, 8)
        lay.setSpacing(6)
        return group, lay

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px; line-height:1.4;")
        return lbl

    @staticmethod
    def _mini_text(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:9px;")
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
