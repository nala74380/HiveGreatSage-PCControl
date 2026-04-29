r"""
文件位置: ui/widgets/settings_dialog.py
名称: 全局设置弹窗
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  1200×900 全局设置弹窗，左侧标签导航，右侧内容区。
  标签页：账号设置 / 脚本参数 / 仓库设置 / 物品设置 /
          制造设置 / 活动设置 / 铸币设置 / 其他设置
  - 账号设置：本地 config 字段（API地址/同步间隔等），可直接保存到 local.yaml
  - 脚本参数：从 Verify API /api/params/get 动态加载，动态渲染表单，POST /api/params/set 保存
  - 其他设置：日志级别/ADB 端口等
  - 其余标签：占位提示（Phase 2 游戏层实现）

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ui.styles.colors import (
    BG_MAIN, BG_PANEL, BG_DEEP, BG_ITEM, BORDER, BORDER2, BORDER3,
    TEAL, TEAL_DK, TEAL_BG, TEAL_BG2,
    AMBER, AMBER_BG,
    RED, RED_BG,
    TEXT, TEXT_MID, TEXT_DIM, TEXT_MUTE, TEXT_DARK,
    MONO_FONT,
)

if TYPE_CHECKING:
    from core.app import Application

logger = logging.getLogger(__name__)

_QSS = f"""
QDialog {{
    background: {BG_MAIN};
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
    color: {TEXT};
}}
/* 左侧导航列表 */
QListWidget {{
    background: {BG_PANEL};
    border: none;
    border-right: 1px solid {BORDER};
    outline: none;
}}
QListWidget::item {{
    padding: 9px 16px;
    color: {TEXT_DIM};
    border-left: 2px solid transparent;
}}
QListWidget::item:hover   {{ background: {BG_ITEM}; color: {TEXT_MID}; }}
QListWidget::item:selected {{
    background: #0a1e17;
    color: {TEAL};
    border-left-color: {TEAL_DK};
}}
/* 表单元素 */
QLineEdit, QSpinBox {{
    background: {BG_DEEP};
    border: 0.5px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 5px 8px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
}}
QLineEdit:focus, QSpinBox:focus {{ border-color: {TEAL_DK}; }}
QComboBox {{
    background: {BG_DEEP};
    border: 0.5px solid {BORDER};
    border-radius: 4px;
    color: {TEXT};
    padding: 5px 8px;
    font-family: '{MONO_FONT}', monospace;
    font-size: 11px;
}}
QComboBox:focus {{ border-color: {TEAL_DK}; }}
QComboBox QAbstractItemView {{
    background: {BG_ITEM};
    border: 0.5px solid {BORDER3};
    selection-background-color: {TEAL_BG};
    color: {TEXT};
    font-size: 10px;
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; }}
/* 复选框 */
QCheckBox {{ color: {TEXT}; font-size: 11px; spacing: 6px; }}
QCheckBox::indicator {{
    width: 14px; height: 14px;
    border: 1px solid {BORDER2}; border-radius: 3px; background: transparent;
}}
QCheckBox::indicator:checked {{ background: {TEAL_DK}; border-color: {TEAL_DK}; }}
/* 按钮 */
QPushButton {{
    background: transparent; border: 0.5px solid {BORDER2};
    border-radius: 5px; color: {TEXT_MID};
    padding: 5px 16px; font-family: '{MONO_FONT}', monospace; font-size: 11px;
}}
QPushButton:hover {{ background: {BG_ITEM}; color: {TEXT}; }}
QPushButton#save-btn {{
    background: {TEAL_BG}; border-color: {TEAL_DK}; color: {TEAL};
}}
QPushButton#save-btn:hover {{ background: #0F6E56; }}
QPushButton#load-btn {{
    border-color: {AMBER_BG}; color: {AMBER};
}}
QPushButton#load-btn:hover {{ background: {AMBER_BG}; }}
/* 分节标题 */
QLabel#section-head {{
    color: {TEAL};
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 1px;
    padding: 8px 0 4px;
    border-bottom: 0.5px solid {BORDER};
}}
QLabel#hint {{ color: {TEXT_MUTE}; font-size: 9px; }}
"""


# ─── 参数加载线程 ────────────────────────────────────────────

class ParamsLoadWorker(QThread):
    loaded  = Signal(dict)
    failed  = Signal(str)

    def __init__(self, app: "Application") -> None:
        super().__init__()
        self._app = app

    def run(self) -> None:
        try:
            from core.api_client.params_api import ParamsApi
            api = ParamsApi(
                base_url=self._app.config.get("server.api_base_url", ""),
                timeout=float(self._app.config.get("server.timeout", 15)),
            )
            api.set_token(self._app.auth.access_token)
            data = api.get_params()
            self.loaded.emit(data)
        except Exception as e:
            self.failed.emit(str(e))


class ParamsSaveWorker(QThread):
    done   = Signal(dict)
    failed = Signal(str)

    def __init__(self, app: "Application", params: list[dict]) -> None:
        super().__init__()
        self._app    = app
        self._params = params

    def run(self) -> None:
        try:
            from core.api_client.params_api import ParamsApi
            api = ParamsApi(
                base_url=self._app.config.get("server.api_base_url", ""),
                timeout=float(self._app.config.get("server.timeout", 15)),
            )
            api.set_token(self._app.auth.access_token)
            data = api.set_params(self._params)
            self.done.emit(data)
        except Exception as e:
            self.failed.emit(str(e))


# ─── 主弹窗 ──────────────────────────────────────────────────

class SettingsDialog(QDialog):
    """全局设置弹窗，1200×900。"""

    def __init__(self, app: "Application", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._app   = app
        self._param_widgets: dict[str, QWidget] = {}   # param_key → 编辑控件

        self.setStyleSheet(_QSS)
        self.setWindowTitle("⚙ 全局设置")
        self.setFixedSize(1200, 900)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._build()

    # ── 构建 ──────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── 标题栏 ──
        header = QWidget()
        header.setStyleSheet(f"background:{BG_PANEL}; border-bottom:1px solid {BORDER};")
        header.setFixedHeight(38)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(14, 0, 14, 0)
        hl.addWidget(QLabel("⚙ 全局设置"))
        hl.addStretch()
        close_btn = QPushButton("×")
        close_btn.setStyleSheet(
            f"border:none; background:transparent; color:{TEXT_MUTE}; font-size:18px; padding:0;"
        )
        close_btn.clicked.connect(self.reject)
        hl.addWidget(close_btn)
        root.addWidget(header)

        # ── 主体：左侧导航 + 右侧内容 ──
        body = QWidget()
        bl = QHBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        self._nav   = QListWidget()
        self._nav.setFixedWidth(160)
        self._stack = QStackedWidget()

        tabs = [
            ("账号设置",   self._build_tab_account),
            ("脚本参数",   self._build_tab_params),
            ("仓库设置",   lambda: self._build_placeholder_tab("仓库设置", "游戏层参数，Phase 2 实现")),
            ("物品设置",   lambda: self._build_placeholder_tab("物品设置", "游戏层参数，Phase 2 实现")),
            ("制造设置",   lambda: self._build_placeholder_tab("制造设置", "游戏层参数，Phase 2 实现")),
            ("活动设置",   lambda: self._build_placeholder_tab("活动设置", "游戏层参数，Phase 2 实现")),
            ("铸币设置",   lambda: self._build_placeholder_tab("铸币设置", "游戏层参数，Phase 2 实现")),
            ("其他设置",   self._build_tab_other),
        ]
        for name, builder in tabs:
            item = QListWidgetItem(name)
            self._nav.addItem(item)
            self._stack.addWidget(builder())

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._nav.setCurrentRow(0)

        bl.addWidget(self._nav)
        bl.addWidget(self._stack)
        root.addWidget(body)

        # ── 底部按钮 ──
        footer = QWidget()
        footer.setStyleSheet(f"background:{BG_PANEL}; border-top:1px solid {BORDER};")
        footer.setFixedHeight(46)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(14, 0, 14, 0)
        fl.setSpacing(8)
        fl.addStretch()
        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(self.reject)
        fl.addWidget(cancel_btn)
        self._save_btn = QPushButton("保存设置")
        self._save_btn.setObjectName("save-btn")
        self._save_btn.clicked.connect(self._on_save)
        fl.addWidget(self._save_btn)
        root.addWidget(footer)

    # ── 标签页：账号设置 ──────────────────────────

    def _build_tab_account(self) -> QWidget:
        w = self._scrollable_tab()
        lay = w.layout()

        self._section(lay, "服务器连接")

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._api_url_edit = QLineEdit(self._app.config.get("server.api_base_url", ""))
        self._api_url_edit.setPlaceholderText("http://127.0.0.1:8000")
        form.addRow("API 地址", self._api_url_edit)

        self._proj_uuid_edit = QLineEdit(self._app.config.get("server.project_uuid", ""))
        self._proj_uuid_edit.setPlaceholderText("xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        form.addRow("项目 UUID", self._proj_uuid_edit)

        lay.addLayout(form)

        self._section(lay, "同步设置")
        form2 = QFormLayout()
        form2.setSpacing(10)
        form2.setContentsMargins(0, 0, 0, 0)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._sync_interval_spin = QSpinBox()
        self._sync_interval_spin.setRange(5, 120)
        self._sync_interval_spin.setValue(int(self._app.config.get("sync.interval", 10)))
        self._sync_interval_spin.setSuffix(" 秒")
        form2.addRow("设备刷新间隔", self._sync_interval_spin)
        lay.addLayout(form2)

        hint = QLabel("⚠ 修改后需重启程序生效（同步间隔）；API地址/UUID 立即生效。")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        lay.addStretch()
        return w

    # ── 标签页：脚本参数 ──────────────────────────

    def _build_tab_params(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(18, 14, 18, 14)
        vl.setSpacing(10)

        # 顶部操作栏
        top_row = QHBoxLayout()
        info_lbl = QLabel("参数从云端 Verify 服务实时加载，修改后点击「保存参数」提交。")
        info_lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        top_row.addWidget(info_lbl)
        top_row.addStretch()
        reload_btn = QPushButton("↺ 重新加载")
        reload_btn.setObjectName("load-btn")
        reload_btn.clicked.connect(self._load_params)
        top_row.addWidget(reload_btn)
        self._params_save_btn = QPushButton("保存参数")
        self._params_save_btn.setObjectName("save-btn")
        self._params_save_btn.clicked.connect(self._save_params)
        top_row.addWidget(self._params_save_btn)
        vl.addLayout(top_row)

        # 状态标签
        self._params_status = QLabel("点击「重新加载」从服务器获取参数...")
        self._params_status.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
        vl.addWidget(self._params_status)

        # 参数表单区域（可滚动）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._params_form_widget = QWidget()
        self._params_form_layout = QVBoxLayout(self._params_form_widget)
        self._params_form_layout.setContentsMargins(0, 0, 0, 0)
        self._params_form_layout.setSpacing(8)
        self._params_form_layout.addStretch()
        scroll.setWidget(self._params_form_widget)
        vl.addWidget(scroll)

        return w

    def _load_params(self) -> None:
        self._params_status.setText("正在从服务器加载参数...")
        self._params_status.setStyleSheet(f"color:{TEAL}; font-size:10px;")
        worker = ParamsLoadWorker(self._app)
        worker.loaded.connect(self._on_params_loaded)
        worker.failed.connect(self._on_params_failed)
        worker.start()
        self._params_worker = worker   # 防止被 GC

    def _on_params_loaded(self, data: dict) -> None:
        params = data.get("params", [])
        total  = data.get("total", 0)

        # 清空旧表单
        self._param_widgets.clear()
        lay = self._params_form_layout
        while lay.count() > 1:   # 保留最后的 addStretch
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not params:
            self._params_status.setText("暂无参数（游戏库尚未配置参数定义）")
            self._params_status.setStyleSheet(f"color:{TEXT_MUTE}; font-size:10px;")
            return

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        for param in sorted(params, key=lambda p: p.get("sort_order", 0)):
            key       = param.get("param_key", "")
            ptype     = param.get("param_type", "string")
            value     = param.get("value", "")
            label     = param.get("display_name") or key
            desc      = param.get("description") or ""
            options   = param.get("options") or []

            if ptype == "bool":
                widget = QCheckBox()
                widget.setChecked(value.lower() in ("true", "1", "yes"))
            elif ptype == "enum" and options:
                widget = QComboBox()
                for opt in options:
                    opt_lbl = opt.get("label", str(opt.get("value", "")))
                    opt_val = str(opt.get("value", ""))
                    widget.addItem(opt_lbl, opt_val)
                idx = widget.findData(value)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
            elif ptype == "int":
                widget = QSpinBox()
                widget.setRange(-999999, 999999)
                try:
                    widget.setValue(int(value))
                except (ValueError, TypeError):
                    pass
            else:
                widget = QLineEdit(value)
                if desc:
                    widget.setPlaceholderText(desc)

            self._param_widgets[key] = widget

            row_lbl = f"{label}" + (f"\n({key})" if label != key else "")
            form.addRow(row_lbl, widget)

        lay.insertLayout(0, form)
        self._params_status.setText(f"已加载 {total} 个参数")
        self._params_status.setStyleSheet(f"color:{TEAL}; font-size:10px;")

    def _on_params_failed(self, msg: str) -> None:
        self._params_status.setText(f"加载失败：{msg}")
        self._params_status.setStyleSheet(f"color:{RED}; font-size:10px;")

    def _save_params(self) -> None:
        if not self._param_widgets:
            return
        payload = []
        for key, widget in self._param_widgets.items():
            if isinstance(widget, QCheckBox):
                val = "true" if widget.isChecked() else "false"
            elif isinstance(widget, QComboBox):
                val = widget.currentData() or widget.currentText()
            elif isinstance(widget, QSpinBox):
                val = str(widget.value())
            else:
                val = widget.text()
            payload.append({"param_key": key, "param_value": val})

        self._params_status.setText("正在保存...")
        self._params_status.setStyleSheet(f"color:{TEAL}; font-size:10px;")
        worker = ParamsSaveWorker(self._app, payload)
        worker.done.connect(self._on_params_saved)
        worker.failed.connect(self._on_params_failed)
        worker.start()
        self._params_save_worker = worker

    def _on_params_saved(self, data: dict) -> None:
        updated = data.get("updated_count", 0)
        failed  = data.get("failed_count", 0)
        if failed:
            self._params_status.setText(
                f"部分保存：{updated} 成功，{failed} 失败"
            )
            self._params_status.setStyleSheet(f"color:{AMBER}; font-size:10px;")
        else:
            self._params_status.setText(f"已保存 {updated} 个参数")
            self._params_status.setStyleSheet(f"color:{TEAL}; font-size:10px;")

    # ── 标签页：其他设置 ──────────────────────────

    def _build_tab_other(self) -> QWidget:
        w = self._scrollable_tab()
        lay = w.layout()

        self._section(lay, "日志设置")
        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._log_level_cb = QComboBox()
        for lv in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            self._log_level_cb.addItem(lv)
        cur_level = self._app.config.get("log.level", "INFO")
        idx = self._log_level_cb.findText(cur_level.upper())
        if idx >= 0:
            self._log_level_cb.setCurrentIndex(idx)
        form.addRow("日志级别", self._log_level_cb)
        lay.addLayout(form)

        self._section(lay, "ADB 设置")
        form2 = QFormLayout()
        form2.setSpacing(10)
        form2.setContentsMargins(0, 0, 0, 0)
        form2.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self._adb_port_spin = QSpinBox()
        self._adb_port_spin.setRange(1024, 65535)
        self._adb_port_spin.setValue(int(self._app.config.get("adb.default_tcpip_port", 5555)))
        form2.addRow("默认 TCP/IP 端口", self._adb_port_spin)
        lay.addLayout(form2)

        self._section(lay, "热更新")
        self._update_on_startup_chk = QCheckBox("启动时自动检查更新")
        self._update_on_startup_chk.setChecked(
            bool(self._app.config.get("update.check_on_startup", True))
        )
        lay.addWidget(self._update_on_startup_chk)

        lay.addStretch()
        return w

    # ── 占位标签页 ────────────────────────────────

    def _build_placeholder_tab(self, name: str, hint: str) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"{name}\n\n{hint}")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color:{TEXT_MUTE}; font-size:12px; line-height:2;")
        vl.addWidget(lbl)
        return w

    # ── 保存（账号+其他设置）────────────────────

    def _on_save(self) -> None:
        cur_idx = self._nav.currentRow()

        if cur_idx == 0:   # 账号设置
            self._app.config.set_local("server.api_base_url",  self._api_url_edit.text().strip())
            self._app.config.set_local("server.project_uuid",  self._proj_uuid_edit.text().strip())
            self._app.config.set_local("sync.interval",        self._sync_interval_spin.value())
            logger.info("账号设置已保存到 config/local.yaml")

        elif cur_idx == 7:  # 其他设置
            self._app.config.set_local("log.level",                  self._log_level_cb.currentText())
            self._app.config.set_local("adb.default_tcpip_port",     self._adb_port_spin.value())
            self._app.config.set_local("update.check_on_startup",    self._update_on_startup_chk.isChecked())
            logger.info("其他设置已保存到 config/local.yaml")

        elif cur_idx == 1:  # 脚本参数（走单独的保存流程）
            self._save_params()
            return

    # ── 工具方法 ──────────────────────────────────

    def _scrollable_tab(self) -> QWidget:
        """创建带滚动区域的标签页容器。"""
        outer = QWidget()
        ol = QVBoxLayout(outer)
        ol.setContentsMargins(0, 0, 0, 0)
        ol.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        il = QVBoxLayout(inner)
        il.setContentsMargins(18, 14, 18, 14)
        il.setSpacing(8)
        scroll.setWidget(inner)
        ol.addWidget(scroll)

        # 把布局挂到 outer 上方便外层 addWidget
        outer._inner_layout = il   # noqa: protected-access
        outer.layout = lambda: il   # noqa: method-override  # 让调用方直接 .layout() 拿到
        return outer

    def _section(self, lay: QVBoxLayout, title: str) -> None:
        lbl = QLabel(title.upper())
        lbl.setObjectName("section-head")
        lay.addWidget(lbl)
