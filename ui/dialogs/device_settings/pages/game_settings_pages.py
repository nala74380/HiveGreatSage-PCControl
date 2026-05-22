r"""
文件位置: ui/dialogs/device_settings/pages/game_settings_pages.py
名称: 设备游戏设置页集合
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-19
版本: V1.0.0
状态: P4 设备设置其他页签补全
功能及相关说明:
  为 DeviceSettingsDialog 提供设备级游戏运行配置页。

边界说明:
  - 本文件只处理单设备游戏运行配置草稿。
  - 不承载全局设置。
  - 不承载远控 / 投屏 / scrcpy / 公网远控。
  - 当前后端配置保存接口未联调，只输出本地草稿摘要。
  - 具体字段语义后续可按游戏 fork 继续扩展，但不能再放回全局设置。
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import BG_DEEP, BG_ITEM, BORDER, BORDER2, TEAL, TEXT, TEXT_MID, TEXT_MUTE, MONO_FONT


class _BaseSettingsPage(QWidget):
    """设备设置页基础组件。"""

    def to_dict(self) -> dict:
        draft = getattr(self, "draft", None)
        return draft() if callable(draft) else {}

    def from_dict(self, data: dict | None) -> None:
        if not data:
            return

    @staticmethod
    def _set_combo_data(combo: QComboBox, value) -> None:
        idx = combo.findData(value)
        if idx >= 0:
            combo.setCurrentIndex(idx)

    @staticmethod
    def _set_combo_text(combo: QComboBox, value) -> None:
        idx = combo.findText(str(value))
        if idx >= 0:
            combo.setCurrentIndex(idx)

    @staticmethod
    def _set_widget_value(widget: QWidget, value) -> None:
        if isinstance(widget, QComboBox):
            _BaseSettingsPage._set_combo_data(widget, value)
        elif isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QGroupBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSpinBox):
            widget.setValue(int(value or 0))
        elif isinstance(widget, QDoubleSpinBox):
            widget.setValue(float(value or 0))
        elif isinstance(widget, QLineEdit):
            widget.setText("" if value is None else str(value))
        elif isinstance(widget, QTextEdit):
            widget.setPlainText("" if value is None else str(value))

    def _load_flat_fields(self, data: dict | None, mapping: dict[str, QWidget]) -> None:
        if not data:
            return
        for key, widget in mapping.items():
            if key in data:
                self._set_widget_value(widget, data[key])

    def _page_layout(self) -> QVBoxLayout:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(10)
        return lay

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
        lbl.setStyleSheet(
            f"color:{TEAL}; font-size:9px; font-weight:600; letter-spacing:1px; "
            f"padding:8px 0 4px; border-bottom:0.5px solid {BORDER};"
        )
        lay.addWidget(lbl)

    @staticmethod
    def _hint(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("hint")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        return lbl

    @staticmethod
    def _line_edit(placeholder: str = "") -> QLineEdit:
        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet(
            f"background:{BG_DEEP}; border:0.5px solid {BORDER}; border-radius:4px; "
            f"color:{TEXT}; padding:5px 8px; font-family:'{MONO_FONT}',monospace; font-size:11px;"
        )
        return edit

    @staticmethod
    def _text_edit(placeholder: str = "", height: int = 100) -> QTextEdit:
        edit = QTextEdit()
        edit.setPlaceholderText(placeholder)
        edit.setFixedHeight(height)
        edit.setStyleSheet(
            f"background:{BG_DEEP}; border:0.5px solid {BORDER}; border-radius:4px; "
            f"color:{TEXT}; padding:5px 8px; font-family:'{MONO_FONT}',monospace; font-size:11px;"
        )
        return edit

    @staticmethod
    def _combo(items: list[tuple[str, str]]) -> QComboBox:
        combo = QComboBox()
        for label, value in items:
            combo.addItem(label, value)
        return combo

    @staticmethod
    def _spin(min_value: int = 0, max_value: int = 999999, value: int = 0, suffix: str = "") -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(min_value, max_value)
        spin.setValue(value)
        if suffix:
            spin.setSuffix(suffix)
        return spin

    @staticmethod
    def _check(text: str, checked: bool = False) -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(checked)
        return box

    @staticmethod
    def _toolbar_button(text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:0.5px solid {BORDER2}; border-radius:5px; "
            f"color:{TEXT_MID}; padding:5px 10px; font-family:'{MONO_FONT}',monospace; font-size:11px; }}"
            f"QPushButton:hover {{ color:{TEAL}; }}"
            f"QPushButton:disabled {{ color:{TEXT_MUTE}; }}"
        )
        return btn


class MainSettingsPage(_BaseSettingsPage):
    """主要设置页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        board = QGridLayout()
        board.setContentsMargins(0, 0, 0, 0)
        board.setHorizontalSpacing(8)
        board.setVerticalSpacing(7)

        left_col = QVBoxLayout()
        left_col.setContentsMargins(0, 0, 0, 0)
        left_col.setSpacing(7)
        left_col.addWidget(self._build_run_mode_group())
        left_col.addWidget(self._build_idle_map_group())
        left_col.addStretch()

        board.addLayout(left_col, 0, 0)
        board.addWidget(self._build_mainline_task_group(), 0, 1)
        board.addWidget(self._build_dungeon_group(), 0, 2)
        board.addWidget(self._build_battlefield_group(), 0, 3)
        board.setColumnStretch(0, 1)
        board.setColumnStretch(1, 1)
        board.setColumnStretch(2, 1)
        board.setColumnStretch(3, 1)

        lay.addLayout(board)
        lay.addWidget(self._hint("主要设置按附件风格收敛为 5 个核心区域：运行模式、野外挂机地图、主线/外传/支线/每日任务、副本、激战地。当前仍只保存本地草稿，后端配置接口待联调。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "run_mode": {
                "account_mode": self.account_mode.currentData(),
                "role_mode": self.role_mode.currentData(),
            },
            "idle_map": {
                "map": self.idle_map.currentData(),
                "map_level": self.idle_map_level.currentData(),
                "use_random_scroll_after_arrival": self.use_random_scroll_after_arrival.isChecked(),
                "target_monster_enabled": self.target_monster_enabled.isChecked(),
            },
            "mainline_tasks": {
                "main_task_mode": self.main_task_mode.currentData(),
                "chapter": self.main_chapter.currentData(),
                "section": self.main_section.value(),
                "death_stop_count": self.main_death_count.currentData(),
                "legend_task": self.legend_task.isChecked(),
                "side_task": self.side_task.isChecked(),
                "daily_task": self.daily_task.isChecked(),
                "daily_mode": self.daily_mode.currentData(),
                "level_start": self.level_start.value(),
                "level_end": self.level_end.value(),
                "continuous_enabled": self.continuous_enabled.isChecked(),
                "continuous_mode": self.continuous_mode.currentData(),
                "team_execute": self.team_execute.isChecked(),
            },
            "dungeon": {
                "temple": {"enabled": self.temple_enabled.isChecked(), "mode": self.temple_mode.currentData()},
                "daily_time_hours": self.daily_dungeon_hours.value(),
                "ruins": {"enabled": self.ruins_enabled.isChecked(), "mode": self.ruins_mode.currentData()},
                "sapperas": {"enabled": self.sapperas_enabled.isChecked(), "mode": self.sapperas_mode.currentData()},
                "special": {"enabled": self.special_dungeon_enabled.isChecked(), "name": self.special_dungeon.currentData(), "map": self.special_map.currentData()},
                "ticket_trade": self.ticket_trade_enabled.isChecked(),
                "ticket_price_limit_diamond": self.ticket_price_limit.value(),
                "world": {"enabled": self.world_dungeon_enabled.isChecked(), "floor": self.world_floor.currentData(), "map": self.world_map.currentData()},
                "epic": {"enabled": self.epic_dungeon_enabled.isChecked(), "map": self.epic_map.currentData()},
                "activity": {"enabled": self.activity_dungeon_enabled.isChecked(), "status": "developing"},
            },
            "battlefield": {
                "enabled": self.battlefield_group.isChecked(),
                "mode": self.battlefield_mode.currentData(),
                "map": self.battlefield_map.currentData(),
                "min_gold_enabled": self.battlefield_min_gold_enabled.isChecked(),
                "min_gold_wan": self.battlefield_min_gold.value(),
                "death_retry_enabled": self.battlefield_death_enabled.isChecked(),
                "death_retry_count": self.battlefield_death_count.value(),
                "return_retry_enabled": self.battlefield_return_enabled.isChecked(),
                "return_retry_count": self.battlefield_return_count.value(),
                "time_limit_enabled": self.battlefield_time_enabled.isChecked(),
                "start_hour": self.battlefield_start_hour.value(),
                "end_hour": self.battlefield_end_hour.value(),
            },
        }

    def from_dict(self, data: dict | None) -> None:
        if not data:
            return
        run_mode = data.get("run_mode") or {}
        self._load_flat_fields(run_mode, {
            "account_mode": self.account_mode,
            "role_mode": self.role_mode,
        })

        idle_map = data.get("idle_map") or {}
        self._load_flat_fields(idle_map, {
            "map": self.idle_map,
            "map_level": self.idle_map_level,
            "use_random_scroll_after_arrival": self.use_random_scroll_after_arrival,
            "target_monster_enabled": self.target_monster_enabled,
        })

        mainline = data.get("mainline_tasks") or {}
        self._load_flat_fields(mainline, {
            "main_task_mode": self.main_task_mode,
            "chapter": self.main_chapter,
            "section": self.main_section,
            "death_stop_count": self.main_death_count,
            "legend_task": self.legend_task,
            "side_task": self.side_task,
            "daily_task": self.daily_task,
            "daily_mode": self.daily_mode,
            "level_start": self.level_start,
            "level_end": self.level_end,
            "continuous_enabled": self.continuous_enabled,
            "continuous_mode": self.continuous_mode,
            "team_execute": self.team_execute,
        })

        dungeon = data.get("dungeon") or {}
        temple = dungeon.get("temple") or {}
        ruins = dungeon.get("ruins") or {}
        sapperas = dungeon.get("sapperas") or {}
        special = dungeon.get("special") or {}
        world = dungeon.get("world") or {}
        epic = dungeon.get("epic") or {}
        self._load_flat_fields({
            "daily_time_hours": dungeon.get("daily_time_hours"),
            "ticket_trade": dungeon.get("ticket_trade"),
            "ticket_price_limit_diamond": dungeon.get("ticket_price_limit_diamond"),
        }, {
            "daily_time_hours": self.daily_dungeon_hours,
            "ticket_trade": self.ticket_trade_enabled,
            "ticket_price_limit_diamond": self.ticket_price_limit,
        })
        self._load_flat_fields(temple, {"enabled": self.temple_enabled, "mode": self.temple_mode})
        self._load_flat_fields(ruins, {"enabled": self.ruins_enabled, "mode": self.ruins_mode})
        self._load_flat_fields(sapperas, {"enabled": self.sapperas_enabled, "mode": self.sapperas_mode})
        self._load_flat_fields(special, {"enabled": self.special_dungeon_enabled, "name": self.special_dungeon, "map": self.special_map})
        self._load_flat_fields(world, {"enabled": self.world_dungeon_enabled, "floor": self.world_floor, "map": self.world_map})
        self._load_flat_fields(epic, {"enabled": self.epic_dungeon_enabled, "map": self.epic_map})

        battlefield = data.get("battlefield") or {}
        self._load_flat_fields(battlefield, {
            "enabled": self.battlefield_group,
            "mode": self.battlefield_mode,
            "map": self.battlefield_map,
            "min_gold_enabled": self.battlefield_min_gold_enabled,
            "min_gold_wan": self.battlefield_min_gold,
            "death_retry_enabled": self.battlefield_death_enabled,
            "death_retry_count": self.battlefield_death_count,
            "return_retry_enabled": self.battlefield_return_enabled,
            "return_retry_count": self.battlefield_return_count,
            "time_limit_enabled": self.battlefield_time_enabled,
            "start_hour": self.battlefield_start_hour,
            "end_hour": self.battlefield_end_hour,
        })

    # ── 附件风格分组 ──────────────────────────────

    def _build_run_mode_group(self) -> QGroupBox:
        group, grid = self._group("运行模式")
        grid.addWidget(self._label("账号模式:"), 0, 0)
        self.account_mode = self._small_combo([
            ("单账号单区", "single_account_single_region"),
            ("多账号轮换", "multi_account_rotate"),
            ("多区轮换", "multi_region_rotate"),
        ], width=112)
        grid.addWidget(self.account_mode, 0, 1)

        grid.addWidget(self._label("角色模式:"), 1, 0)
        self.role_mode = self._small_combo([
            ("单角色", "single_role"),
            ("四角色", "four_roles"),
            ("滚角色", "rolling_roles"),
        ], width=112)
        grid.addWidget(self.role_mode, 1, 1)
        return group

    def _build_idle_map_group(self) -> QGroupBox:
        group, grid = self._group("野外挂机地图")
        grid.addWidget(self._label("挂机地图:"), 0, 0)
        self.idle_map = self._small_combo([
            ("智能挂机", "auto_idle"),
            ("朝圣者峡谷", "pilgrim_canyon"),
            ("繁荣之地", "prosperity_land"),
            ("马萨尔塔冰洞", "frost_cave"),
        ], width=132)
        grid.addWidget(self.idle_map, 0, 1)

        grid.addWidget(self._label("地图等级:"), 1, 0)
        self.idle_map_level = self._small_combo([
            ("智能等级", "auto_level"),
            ("30~40级", "30_40"),
            ("40~50级", "40_50"),
            ("50级以上", "50_plus"),
        ], width=132)
        grid.addWidget(self.idle_map_level, 1, 1)

        self.use_random_scroll_after_arrival = self._check_box("到达地图后使用随机卷")
        self.target_monster_enabled = self._check_box("指定怪物")
        grid.addWidget(self.use_random_scroll_after_arrival, 2, 0, 1, 2)
        grid.addWidget(self.target_monster_enabled, 3, 0, 1, 2)
        return group

    def _build_mainline_task_group(self) -> QGroupBox:
        group, grid = self._group("主线/外传/支线/每日任务")
        grid.addWidget(self._label("主线任务:"), 0, 0)
        self.main_task_mode = self._small_combo([
            ("按章节", "by_chapter"),
            ("按等级", "by_level"),
            ("不执行", "disabled"),
        ], width=92)
        grid.addWidget(self.main_task_mode, 0, 1)
        grid.addWidget(self._help(), 0, 2)

        grid.addWidget(self._label("第"), 1, 0)
        self.main_chapter = self._small_combo([
            ("第1章 夜鸦归来", "chapter_1"),
            ("第2章 暗影追踪", "chapter_2"),
            ("第3章 战火重燃", "chapter_3"),
        ], width=140)
        self.main_section = self._small_spin(1, 99, 1, width=42)
        grid.addWidget(self.main_chapter, 1, 1)
        grid.addWidget(self._label("第"), 1, 2)
        grid.addWidget(self.main_section, 1, 3)
        grid.addWidget(self._label("节"), 1, 4)
        grid.addWidget(self._help(), 1, 5)

        grid.addWidget(self._label("主线死亡:"), 2, 0)
        self.main_death_count = self._small_combo([
            ("1", "1"),
            ("2", "2"),
            ("3", "3"),
            ("不限制", "unlimited"),
        ], width=54)
        grid.addWidget(self.main_death_count, 2, 1)
        grid.addWidget(self._label("次后停止"), 2, 2, 1, 3)

        self.legend_task = self._check_box("外传任务")
        self.side_task = self._check_box("支线任务")
        grid.addWidget(self.legend_task, 3, 0, 1, 2)
        grid.addWidget(self.side_task, 3, 2, 1, 2)

        self.daily_task = self._check_box("每日任务", checked=True)
        self.daily_mode = self._small_combo([
            ("等级模式", "level_mode"),
            ("章节模式", "chapter_mode"),
            ("不执行", "disabled"),
        ], width=94)
        grid.addWidget(self.daily_task, 4, 0)
        grid.addWidget(self._label("模式:"), 4, 1)
        grid.addWidget(self.daily_mode, 4, 2, 1, 2)
        grid.addWidget(self._help(), 4, 4)

        grid.addWidget(self._label("等级"), 5, 0)
        self.level_start = self._small_spin(1, 999, 30, width=48)
        self.level_end = self._small_spin(1, 999, 35, width=48)
        grid.addWidget(self.level_start, 5, 1)
        grid.addWidget(self._label("~"), 5, 2)
        grid.addWidget(self.level_end, 5, 3)

        self.continuous_enabled = self._check_box("连续执行")
        self.continuous_mode = self._small_combo([
            ("不使用", "disabled"),
            ("按顺序", "sequence"),
            ("失败跳过", "skip_failed"),
        ], width=100)
        grid.addWidget(self.continuous_enabled, 6, 0)
        grid.addWidget(self.continuous_mode, 6, 1, 1, 2)
        grid.addWidget(self._help(), 6, 3)

        self.team_execute = self._check_box("以上任务组队执行")
        grid.addWidget(self.team_execute, 7, 0, 1, 4)
        grid.addWidget(self._help(), 7, 4)
        return group

    def _build_dungeon_group(self) -> QGroupBox:
        group, grid = self._group("副本")
        self.temple_enabled = self._check_box("伊莱塔神殿")
        self.temple_mode = self._small_combo([("宠物冒险执行", "pet_adventure"), ("日程执行", "schedule"), ("不执行", "disabled")], width=124)
        grid.addWidget(self.temple_enabled, 0, 0)
        grid.addWidget(self.temple_mode, 0, 1, 1, 2)

        self.daily_dungeon_time_enabled = self._check_box("每日执行时间")
        self.daily_dungeon_hours = self._small_double(0.0, 24.0, 1.0, width=78)
        grid.addWidget(self.daily_dungeon_time_enabled, 1, 0)
        grid.addWidget(self.daily_dungeon_hours, 1, 1)
        grid.addWidget(self._label("h"), 1, 2)

        self.ruins_enabled = self._check_box("圣科纳遗址")
        self.ruins_mode = self._small_combo([("宠物冒险执行", "pet_adventure"), ("日程执行", "schedule"), ("不执行", "disabled")], width=124)
        grid.addWidget(self.ruins_enabled, 2, 0)
        grid.addWidget(self.ruins_mode, 2, 1, 1, 2)

        self.sapperas_enabled = self._check_box("赛佩拉斯遗迹")
        self.sapperas_mode = self._small_combo([("日程执行", "schedule"), ("宠物冒险执行", "pet_adventure"), ("不执行", "disabled")], width=124)
        grid.addWidget(self.sapperas_enabled, 3, 0)
        grid.addWidget(self.sapperas_mode, 3, 1, 1, 2)

        self._add_separator(grid, 4)

        self.special_dungeon_enabled = self._check_box("特殊副本")
        self.special_dungeon = self._small_combo([("马萨尔塔冰洞", "frost_cave"), ("繁荣之地", "prosperity_land")], width=124)
        grid.addWidget(self.special_dungeon_enabled, 5, 0)
        grid.addWidget(self.special_dungeon, 5, 1, 1, 2)
        grid.addWidget(self._label("地图:"), 6, 0)
        self.special_map = self._small_combo([("第1洞穴30~40级", "cave_1_30_40"), ("第3洞穴40~50级", "cave_3_40_50")], width=142)
        grid.addWidget(self.special_map, 6, 1, 1, 2)
        self.ticket_trade_enabled = self._check_box("门票")
        self.ticket_trade_label = self._label("交易所购买")
        grid.addWidget(self.ticket_trade_enabled, 7, 0)
        grid.addWidget(self.ticket_trade_label, 7, 1, 1, 2)
        grid.addWidget(self._label("交易所购买限价(钻):"), 8, 0, 1, 2)
        self.ticket_price_limit = self._small_spin(0, 999999, 10, width=70)
        grid.addWidget(self.ticket_price_limit, 8, 2)

        self._add_separator(grid, 9)

        self.world_dungeon_enabled = self._check_box("世界副本")
        self.world_floor = self._small_combo([("上层", "upper"), ("下层", "lower")], width=82)
        grid.addWidget(self.world_dungeon_enabled, 10, 0)
        grid.addWidget(self.world_floor, 10, 1)
        grid.addWidget(self._label("地图:"), 11, 0)
        self.world_map = self._small_combo([("悲叹沙丘78级", "sigh_dune_78"), ("天空岛80级", "sky_island_80")], width=142)
        grid.addWidget(self.world_map, 11, 1, 1, 2)

        self._add_separator(grid, 12)

        self.epic_dungeon_enabled = self._check_box("史诗副本（哈尔佩伦圣所）")
        grid.addWidget(self.epic_dungeon_enabled, 13, 0, 1, 3)
        grid.addWidget(self._label("地图:"), 14, 0)
        self.epic_map = self._small_combo([("起源神域90级", "origin_domain_90"), ("圣所90级", "sanctuary_90")], width=142)
        grid.addWidget(self.epic_map, 14, 1, 1, 2)

        self._add_separator(grid, 15)

        self.activity_dungeon_enabled = self._check_box("活动副本（待开发）")
        self.activity_dungeon_enabled.setEnabled(False)
        grid.addWidget(self.activity_dungeon_enabled, 16, 0, 1, 2)
        status = self._label("功能开发中")
        status.setStyleSheet("color:#7B8BA0; font-size:11px;")
        grid.addWidget(status, 16, 2)
        return group

    def _build_battlefield_group(self) -> QGroupBox:
        group, grid = self._group("激战地")
        group.setCheckable(True)
        group.setChecked(True)
        self.battlefield_group = group

        grid.addWidget(self._label("激战地:"), 0, 0)
        self.battlefield_mode = self._small_combo([("智能激战地", "auto_battlefield"), ("55级激战地", "level_55"), ("60级激战地", "level_60")], width=130)
        grid.addWidget(self.battlefield_mode, 0, 1, 1, 3)

        grid.addWidget(self._label("地图:"), 1, 0)
        self.battlefield_map = self._small_combo([("智能激战地地图", "auto_map"), ("峡谷", "canyon"), ("高地", "highland")], width=130)
        grid.addWidget(self.battlefield_map, 1, 1, 1, 3)

        self.battlefield_min_gold_enabled = self._check_box("金币低于")
        self.battlefield_min_gold = self._small_spin(0, 999999, 100, width=72)
        self.battlefield_min_gold.setSuffix(" 万")
        grid.addWidget(self.battlefield_min_gold_enabled, 2, 0)
        grid.addWidget(self.battlefield_min_gold, 2, 1)
        grid.addWidget(self._label("不执行"), 2, 2, 1, 2)

        self.battlefield_death_enabled = self._check_box("死亡")
        self.battlefield_death_count = self._small_spin(0, 99, 3, width=46)
        grid.addWidget(self.battlefield_death_enabled, 3, 0)
        grid.addWidget(self.battlefield_death_count, 3, 1)
        grid.addWidget(self._label("次后随机刷野30~60分钟"), 3, 2, 1, 2)

        self.battlefield_return_enabled = self._check_box("回城")
        self.battlefield_return_count = self._small_spin(0, 99, 3, width=46)
        grid.addWidget(self.battlefield_return_enabled, 4, 0)
        grid.addWidget(self.battlefield_return_count, 4, 1)
        grid.addWidget(self._label("次后随机刷野30~60分钟"), 4, 2, 1, 2)

        self.battlefield_time_enabled = self._check_box("限时")
        self.battlefield_start_hour = self._small_spin(0, 23, 0, width=46)
        self.battlefield_end_hour = self._small_spin(0, 23, 23, width=46)
        grid.addWidget(self.battlefield_time_enabled, 5, 0)
        grid.addWidget(self.battlefield_start_hour, 5, 1)
        grid.addWidget(self._label("时 -"), 5, 2)
        grid.addWidget(self.battlefield_end_hour, 5, 3)
        grid.addWidget(self._label("时 执行"), 5, 4)
        return group

    # ── 小控件 ────────────────────────────────────

    def _group(self, title: str) -> tuple[QGroupBox, QGridLayout]:
        group = QGroupBox(title)
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        group.setStyleSheet(
            "QGroupBox {"
            "background:#F5F8FC;"
            "border:2px solid #0B84FF;"
            "border-radius:4px;"
            "margin-top:8px;"
            "font-size:12px;"
            f"color:{TEXT};"
            "}"
            "QGroupBox::title {"
            "subcontrol-origin: margin;"
            "left:8px;"
            "padding:0 4px;"
            "background:#F5F8FC;"
            "}"
        )
        grid = QGridLayout(group)
        grid.setContentsMargins(8, 10, 8, 8)
        grid.setHorizontalSpacing(5)
        grid.setVerticalSpacing(6)
        return group, grid

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color:{TEXT}; font-size:11px;")
        return label

    @staticmethod
    def _help() -> QLabel:
        label = QLabel("?")
        label.setFixedSize(18, 18)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color:#0B84FF; border:1px solid #8EC5FF; border-radius:9px; background:#FFFFFF; font-size:11px;")
        return label

    @staticmethod
    def _check_box(text: str, checked: bool = False) -> QCheckBox:
        box = QCheckBox(text)
        box.setChecked(checked)
        box.setStyleSheet(f"QCheckBox {{ color:{TEXT}; font-size:11px; spacing:5px; }}")
        return box

    def _small_combo(self, items: list[tuple[str, str]], width: int = 96) -> QComboBox:
        combo = self._combo(items)
        combo.setFixedWidth(width)
        combo.setFixedHeight(24)
        return combo

    def _small_spin(self, min_value: int, max_value: int, value: int, width: int = 56) -> QSpinBox:
        spin = self._spin(min_value, max_value, value)
        spin.setFixedWidth(width)
        spin.setFixedHeight(24)
        return spin

    @staticmethod
    def _small_double(min_value: float, max_value: float, value: float, width: int = 64) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(min_value, max_value)
        spin.setDecimals(1)
        spin.setSingleStep(0.5)
        spin.setValue(value)
        spin.setFixedWidth(width)
        spin.setFixedHeight(24)
        return spin

    @staticmethod
    def _add_separator(grid: QGridLayout, row: int) -> None:
        line = QLabel("")
        line.setFixedHeight(1)
        line.setStyleSheet("background:#B8C7D9; margin:2px 0;")
        grid.addWidget(line, row, 0, 1, 5)

class TaskSettingsPage(_BaseSettingsPage):
    """任务设置页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        self._section(lay, "任务设置")
        form = self._form()
        self.task_profile = self._line_edit("任务配置名 / 草稿名")
        self.task_action = self._combo([("保持当前", "keep"), ("启动", "start"), ("停止", "stop"), ("重启", "restart"), ("切换配置", "switch_profile")])
        self.priority = self._combo([("普通", "normal"), ("低优先级", "low"), ("高优先级", "high")])
        self.retry_count = self._spin(0, 20, 3, " 次")
        self.timeout_minutes = self._spin(0, 1440, 0, " 分钟")
        self.task_note = self._text_edit("任务备注，仅作为本地草稿说明。", 120)
        form.addRow("任务配置", self.task_profile)
        form.addRow("任务动作", self.task_action)
        form.addRow("执行优先级", self.priority)
        form.addRow("失败重试", self.retry_count)
        form.addRow("任务超时", self.timeout_minutes)
        form.addRow("任务备注", self.task_note)
        lay.addLayout(form)
        lay.addWidget(self._hint("任务参数属于设备设置，不属于全局设置。真实脚本下发接口待联调。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "task_profile": self.task_profile.text().strip(),
            "task_action": self.task_action.currentData(),
            "priority": self.priority.currentData(),
            "retry_count": self.retry_count.value(),
            "timeout_minutes": self.timeout_minutes.value(),
            "task_note": self.task_note.toPlainText().strip(),
        }

    def from_dict(self, data: dict | None) -> None:
        self._load_flat_fields(data, {
            "task_profile": self.task_profile,
            "task_action": self.task_action,
            "priority": self.priority,
            "retry_count": self.retry_count,
            "timeout_minutes": self.timeout_minutes,
            "task_note": self.task_note,
        })


class ItemProcessingPage(_BaseSettingsPage):
    """物品处理页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        self._section(lay, "物品处理")
        form = self._form()
        self.enabled = self._check("启用物品处理策略", False)
        self.full_bag_action = self._combo([("保持不变", "keep"), ("停止任务", "stop"), ("清理背包", "clean"), ("回城处理", "return_town")])
        self.keep_rules = self._text_edit("保留规则，例如：紫装以上、指定材料、绑定物品。", 90)
        self.sell_rules = self._text_edit("出售规则，例如：白装、低级材料。", 90)
        self.destroy_rules = self._text_edit("丢弃 / 销毁规则。", 90)
        form.addRow("启用", self.enabled)
        form.addRow("背包满处理", self.full_bag_action)
        form.addRow("保留规则", self.keep_rules)
        form.addRow("出售规则", self.sell_rules)
        form.addRow("销毁规则", self.destroy_rules)
        lay.addLayout(form)
        lay.addWidget(self._hint("物品处理是游戏运行策略，只属于设备设置 / 批量设备设置，不属于全局设置。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "enabled": self.enabled.isChecked(),
            "full_bag_action": self.full_bag_action.currentData(),
            "keep_rules": self.keep_rules.toPlainText().strip(),
            "sell_rules": self.sell_rules.toPlainText().strip(),
            "destroy_rules": self.destroy_rules.toPlainText().strip(),
        }

    def from_dict(self, data: dict | None) -> None:
        self._load_flat_fields(data, {
            "enabled": self.enabled,
            "full_bag_action": self.full_bag_action,
            "keep_rules": self.keep_rules,
            "sell_rules": self.sell_rules,
            "destroy_rules": self.destroy_rules,
        })


class PurchaseSettingsPage(_BaseSettingsPage):
    """购买设置页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        self._section(lay, "购买设置")
        form = self._form()
        self.enabled = self._check("启用购买策略", False)
        self.budget = self._spin(0, 999999999, 0)
        self.purchase_mode = self._combo([("保持不变", "keep"), ("缺少时购买", "on_shortage"), ("定时补给", "scheduled"), ("禁止购买", "disabled")])
        self.whitelist = self._text_edit("允许购买的物品，一行一个。", 110)
        self.blacklist = self._text_edit("禁止购买的物品，一行一个。", 90)
        form.addRow("启用", self.enabled)
        form.addRow("预算上限", self.budget)
        form.addRow("购买模式", self.purchase_mode)
        form.addRow("购买白名单", self.whitelist)
        form.addRow("购买黑名单", self.blacklist)
        lay.addLayout(form)
        lay.addWidget(self._hint("购买设置属于游戏运行参数，不能放入全局设置。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "enabled": self.enabled.isChecked(),
            "budget_limit": self.budget.value(),
            "purchase_mode": self.purchase_mode.currentData(),
            "whitelist": self.whitelist.toPlainText().strip(),
            "blacklist": self.blacklist.toPlainText().strip(),
        }

    def from_dict(self, data: dict | None) -> None:
        self._load_flat_fields(data, {
            "enabled": self.enabled,
            "budget_limit": self.budget,
            "purchase_mode": self.purchase_mode,
            "whitelist": self.whitelist,
            "blacklist": self.blacklist,
        })


class TradeSettingsPage(_BaseSettingsPage):
    """交易设置页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        self._section(lay, "交易设置")
        form = self._form()
        self.enabled = self._check("启用交易策略", False)
        self.trade_mode = self._combo([("保持不变", "keep"), ("只卖出", "sell_only"), ("只买入", "buy_only"), ("买卖都允许", "buy_sell"), ("禁止交易", "disabled")])
        self.price_policy = self._combo([("保持不变", "keep"), ("跟随市场", "market"), ("固定价格", "fixed"), ("最低可接受价", "min_price")])
        self.trade_rules = self._text_edit("交易规则、价格规则、物品名单。", 140)
        self.risk_note = self._text_edit("风险备注，例如价格异常、交易频率限制。", 90)
        form.addRow("启用", self.enabled)
        form.addRow("交易模式", self.trade_mode)
        form.addRow("价格策略", self.price_policy)
        form.addRow("交易规则", self.trade_rules)
        form.addRow("风险备注", self.risk_note)
        lay.addLayout(form)
        lay.addWidget(self._hint("交易设置当前只保存草稿，不声称交易执行闭环已完成。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "enabled": self.enabled.isChecked(),
            "trade_mode": self.trade_mode.currentData(),
            "price_policy": self.price_policy.currentData(),
            "trade_rules": self.trade_rules.toPlainText().strip(),
            "risk_note": self.risk_note.toPlainText().strip(),
        }

    def from_dict(self, data: dict | None) -> None:
        self._load_flat_fields(data, {
            "enabled": self.enabled,
            "trade_mode": self.trade_mode,
            "price_policy": self.price_policy,
            "trade_rules": self.trade_rules,
            "risk_note": self.risk_note,
        })


class CraftSettingsPage(_BaseSettingsPage):
    """制造设置页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        self._section(lay, "制造设置")
        form = self._form()
        self.enabled = self._check("启用制造策略", False)
        self.craft_mode = self._combo([("保持不变", "keep"), ("按队列制造", "queue"), ("材料足够才制造", "material_ready"), ("禁止制造", "disabled")])
        self.queue_text = self._text_edit("制造队列，一行一个配方或物品。", 140)
        self.material_policy = self._combo([("保持不变", "keep"), ("缺材料暂停", "pause"), ("缺材料购买", "buy"), ("缺材料跳过", "skip")])
        self.limit_count = self._spin(0, 999999, 0)
        form.addRow("启用", self.enabled)
        form.addRow("制造模式", self.craft_mode)
        form.addRow("制造队列", self.queue_text)
        form.addRow("材料策略", self.material_policy)
        form.addRow("制造上限", self.limit_count)
        lay.addLayout(form)
        lay.addWidget(self._hint("制造设置属于游戏运行配置，当前只写入本地草稿。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "enabled": self.enabled.isChecked(),
            "craft_mode": self.craft_mode.currentData(),
            "queue": self.queue_text.toPlainText().strip(),
            "material_policy": self.material_policy.currentData(),
            "limit_count": self.limit_count.value(),
        }

    def from_dict(self, data: dict | None) -> None:
        self._load_flat_fields(data, {
            "enabled": self.enabled,
            "craft_mode": self.craft_mode,
            "queue": self.queue_text,
            "material_policy": self.material_policy,
            "limit_count": self.limit_count,
        })


class MintSettingsPage(_BaseSettingsPage):
    """铸币设置页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        self._section(lay, "铸币设置")
        form = self._form()
        self.enabled = self._check("启用铸币策略", False)
        self.mint_mode = self._combo([("保持不变", "keep"), ("自动铸币", "auto"), ("达到阈值铸币", "threshold"), ("禁止铸币", "disabled")])
        self.threshold = self._spin(0, 999999999, 0)
        self.reserve = self._spin(0, 999999999, 0)
        self.mint_rules = self._text_edit("铸币规则、材料保留规则、风险限制。", 130)
        form.addRow("启用", self.enabled)
        form.addRow("铸币模式", self.mint_mode)
        form.addRow("触发阈值", self.threshold)
        form.addRow("保留数量", self.reserve)
        form.addRow("铸币规则", self.mint_rules)
        lay.addLayout(form)
        lay.addWidget(self._hint("铸币设置不属于全局设置。当前只保存本地草稿。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "enabled": self.enabled.isChecked(),
            "mint_mode": self.mint_mode.currentData(),
            "threshold": self.threshold.value(),
            "reserve": self.reserve.value(),
            "mint_rules": self.mint_rules.toPlainText().strip(),
        }

    def from_dict(self, data: dict | None) -> None:
        self._load_flat_fields(data, {
            "enabled": self.enabled,
            "mint_mode": self.mint_mode,
            "threshold": self.threshold,
            "reserve": self.reserve,
            "mint_rules": self.mint_rules,
        })


class MiscSettingsPage(_BaseSettingsPage):
    """其他游戏参数页。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = self._page_layout()
        self._section(lay, "其他游戏参数")
        form = self._form()
        self.profile_tag = self._line_edit("配置标签")
        self.custom_flags = self._text_edit("自定义开关或标记，一行一个。", 110)
        self.extra_json = self._text_edit("扩展 JSON 草稿。必须避免写入真实密码、token、客户数据库密钥。", 150)
        self.operator_note = self._text_edit("人工备注。", 90)
        form.addRow("配置标签", self.profile_tag)
        form.addRow("自定义标记", self.custom_flags)
        form.addRow("扩展 JSON", self.extra_json)
        form.addRow("人工备注", self.operator_note)
        lay.addLayout(form)
        lay.addWidget(self._hint("其他参数用于游戏 fork 的低频扩展。不得在此写入真实密码、token、客户数据库密钥。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "profile_tag": self.profile_tag.text().strip(),
            "custom_flags": self.custom_flags.toPlainText().strip(),
            "extra_json_draft": self.extra_json.toPlainText().strip(),
            "operator_note": self.operator_note.toPlainText().strip(),
        }

    def from_dict(self, data: dict | None) -> None:
        self._load_flat_fields(data, {
            "profile_tag": self.profile_tag,
            "custom_flags": self.custom_flags,
            "extra_json_draft": self.extra_json,
            "operator_note": self.operator_note,
        })
