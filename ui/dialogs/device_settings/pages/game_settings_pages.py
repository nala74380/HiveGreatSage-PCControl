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
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import BG_DEEP, BG_ITEM, BORDER, BORDER2, TEAL, TEXT, TEXT_MID, TEXT_MUTE, MONO_FONT


class _BaseSettingsPage(QWidget):
    """设备设置页基础组件。"""

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
        self._section(lay, "运行基础")
        form = self._form()
        self.run_mode = self._combo([("普通运行", "normal"), ("仅登录", "login_only"), ("仅维护", "maintenance")])
        self.mainline_mode = self._combo([("保持当前", "keep"), ("启用主线", "enabled"), ("暂停主线", "paused")])
        self.dungeon_mode = self._combo([("保持当前", "keep"), ("启用副本", "enabled"), ("暂停副本", "paused")])
        self.consumable_mode = self._combo([("保持当前", "keep"), ("允许使用", "enabled"), ("禁止使用", "disabled")])
        self.auto_recover = self._check("异常后自动恢复", True)
        self.daily_reset = self._check("每日重置后自动继续", True)
        self.max_runtime_minutes = self._spin(0, 1440, 0, " 分钟")
        form.addRow("运行模式", self.run_mode)
        form.addRow("主线任务", self.mainline_mode)
        form.addRow("副本设置", self.dungeon_mode)
        form.addRow("消耗品设置", self.consumable_mode)
        form.addRow("自动恢复", self.auto_recover)
        form.addRow("每日继续", self.daily_reset)
        form.addRow("最长运行", self.max_runtime_minutes)
        lay.addLayout(form)
        lay.addWidget(self._hint("主要设置属于单设备游戏运行配置，不属于全局设置。当前保存为本地草稿，后端配置接口待联调。"))
        lay.addStretch()

    def draft(self) -> dict:
        return {
            "run_mode": self.run_mode.currentData(),
            "mainline_mode": self.mainline_mode.currentData(),
            "dungeon_mode": self.dungeon_mode.currentData(),
            "consumable_mode": self.consumable_mode.currentData(),
            "auto_recover": self.auto_recover.isChecked(),
            "daily_reset_continue": self.daily_reset.isChecked(),
            "max_runtime_minutes": self.max_runtime_minutes.value(),
        }


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
