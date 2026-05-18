---
文件位置: docs/pc_control/UI_BOUNDARY_EXECUTION_LOG.md
名称: PCControl_UI边界重构执行记录
项目: 蜂巢·大圣 HiveGreatSage
模块: HiveGreatSage-PCControl
状态: 执行记录 / 事实台账
生成时间: 2026-05-18
关联文档:
  - docs/pc_control/UI_BOUNDARY.md
  - HiveGreatSage-Knowledge/02-PC中控框架/UI边界重构方案.md
  - HiveGreatSage-Knowledge/02-PC中控框架/UI边界重构执行方案.md
---

# PCControl UI 边界重构执行记录

## 1. 记录原则

本文件只记录已经执行或已经验证的事实。

禁止：

```text
把未运行验证写成已通过。
把未实现功能写成已完成。
把推断写成事实。
把无证据账号来源写入执行记录。
```

---

## 2. P0：冻结边界

### 2.1 已执行

已新增：

```text
docs/pc_control/UI_BOUNDARY.md
```

已修改：

```text
ui/widgets/settings_dialog.py
```

### 2.2 已确认

```text
旧 settings_dialog.py 已标记为历史混合设置弹窗。
旧 settings_dialog.py 已声明 P0 起冻结。
旧 settings_dialog.py 不再作为新增游戏配置入口。
```

### 2.3 相关提交

```text
c29bd6dd66c721a3e5a674aa28cd186087d6b20e  docs(pccontrol): freeze UI boundary rules
d68af17e2e832f5e34903512d5fb65f853c23951  docs(ui): mark legacy settings dialog as frozen
```

---

## 3. P1：设备页布局重构

### 3.1 已执行

已新增：

```text
ui/pages/__init__.py
ui/pages/device_page.py
ui/widgets/device_bottom_toolbar.py
ui/widgets/device_side_panel.py
```

已修改：

```text
ui/main_window.py
```

### 3.2 已完成内容

```text
设备页已从 main_window.py 拆出到 ui/pages/device_page.py。
main_window.py 已收敛为主窗口装配层。
设备页主操作工具栏已放到底部。
设备页已新增右侧中控侧栏骨架。
保留原有设备表字段。
保留原有筛选逻辑。
保留原有右键菜单入口。
保留原有设备激活逻辑。
保留原有批量设置入口。
未加入远控 / 投屏 / scrcpy 入口。
未加入无证据账号来源。
```

### 3.3 相关提交

```text
4bd49b889df9b7625d197ca4643659e416c401dc  refactor(ui): add pages package for device page
a7d30531fe195ce49d4905e1f80e919e317287c9  refactor(ui): add device bottom toolbar widget
ec422092638c13b8a3e74e1473a116f89374075b  fix(ui): wire invert selection toolbar action
13be193489ee3754f7e6c08787a3f07326a9660a  refactor(ui): add device side panel skeleton
06c84612a9ee34b4d0e76fbbd1f00f32bf71c085  refactor(ui): extract device page with bottom toolbar
3579a095565de0683afa78582550d50427772b54  refactor(ui): use extracted device page in main window
0cdfba26301deb1f0821d8dadca79c2667341fa0  fix(ui): normalize toolbar checkbox state
8af0c81590ce895d2d6d0bfdfc1f245a34f19f67  fix(ui): make select all action explicit
```

### 3.4 本地验证记录

验证环境：

```text
用户本地环境：TZYMIR
路径：E:\Hive-GreatSage\蜂巢·大圣（Hive-GreatSage）项目\HiveGreatSage\HiveGreatSage-PCControl
```

用户本地执行：

```powershell
python -m compileall -q .
pytest -q
```

用户提供结果：

```text
compileall：无错误输出
pytest：32 passed in 0.57s
```

### 3.5 已确认结论

```text
P1 当前代码可通过 Python 编译检查。
P1 当前代码可通过现有 pytest 测试集。
现有测试结果为 32 passed。
```

### 3.6 P1.1 手工交互验收记录

用户反馈：

```text
除“全选按钮仅显示为一个勾选框、不够清晰”外，其他手工验证都没有问题。
```

已修正：

```text
全选入口已从裸露勾选框改为明确文字按钮“全选”。
当当前列表已全选时，按钮文案切换为“取消全选”。
```

修正提交：

```text
8af0c81590ce895d2d6d0bfdfc1f245a34f19f67  fix(ui): make select all action explicit
```

---

## 4. P2：全局设置拆分

### 4.1 已执行

已新增：

```text
ui/dialogs/__init__.py
ui/dialogs/global_settings_dialog.py
```

已修改：

```text
ui/main_window.py
```

### 4.2 已完成内容

```text
新增真正的 GlobalSettingsDialog。
主窗口“全局设置”入口已切换到 ui/dialogs/global_settings_dialog.py。
旧 ui/widgets/settings_dialog.py 继续保留，但不再作为主入口。
GlobalSettingsDialog 只包含平台附加能力、客户环境、本地运行环境、日志、更新等配置。
未把游戏账号表放入全局设置。
未把游戏任务参数放入全局设置。
未把物品、交易、制造、铸币放入全局设置。
未引入无证据账号来源。
```

### 4.3 当前 GlobalSettingsDialog 页面

```text
服务器连接
网络配置
客户外部账号数据库
接码平台
邮箱服务
ADB 设置
日志与诊断
更新设置
本地缓存
```

### 4.4 相关提交

```text
e0d8f45ae9119965146388e44609cf528b27ea02  refactor(ui): add dialogs package
0dcd21894cbfca8fa2c120a04932f754bcfb3709  feat(ui): add global settings dialog skeleton
d64f881115eadacb0cbcb47b198b35bfa2602513  refactor(ui): route global settings to new dialog
```

### 4.5 验证记录

用户反馈：

```text
P2 已验证。
```

说明：用户未提供本次验证的完整命令输出文本，因此这里只记录用户反馈，不补写具体测试输出。

### 4.6 已确认结论

```text
P2 全局设置入口已完成用户侧验证。
GlobalSettingsDialog 没有发现需要立即回滚的问题。
```

### 4.7 仍需保留的事实边界

```text
客户外部账号数据库连接测试仍为待实现提示，不代表连接能力已完成。
本地缓存清理仍为待实现提示，不代表删除能力已完成。
旧 settings_dialog.py 尚未删除，仅冻结保留。
```

---

## 5. P3：设备设置对话框

### 5.1 已执行

已新增：

```text
ui/dialogs/device_settings_dialog.py
```

已修改：

```text
ui/pages/device_page.py
```

### 5.2 已完成内容

```text
新增 DeviceSettingsDialog 骨架。
新增主要设置、账号设置、任务设置、物品处理、购买设置、交易设置、制造设置、铸币设置、本地元数据、其他游戏参数等页签骨架。
单设备“编辑 / 设置”入口已切换到 DeviceSettingsDialog。
设备表双击入口已沿用同一 DeviceSettingsDialog。
旧 DeviceEditDialog 未删除，但不再作为设备页主入口。
本地元数据兼容页保留 alias / role / note 保存能力。
本地 profile 草稿保存到用户目录下 .hive_greatsage/pccontrol/profiles/device。
本地草稿明确标记 synced=false，不作为最终真相源。
账号来源只保留手动输入和客户外部账号数据库。
未加入无证据账号来源。
未声称后端配置保存闭环已完成。
```

### 5.3 当前 DeviceSettingsDialog 页签

```text
主要设置
账号设置
任务设置
物品处理
购买设置
交易设置
制造设置
铸币设置
本地元数据
其他
```

### 5.4 相关提交

```text
301c37229e3196b28890965c5c052d2367e377bb  feat(ui): add device settings dialog skeleton
c8f89b8db8ac2d1a37234ba0adca8b60474f54f3  refactor(ui): route device edit action to device settings dialog
```

### 5.5 P3.0 兼容性问题记录

用户反馈运行异常：

```text
AttributeError: 'DeviceInfo' object has no attribute legacy identifier
```

已确认根因：

```text
core/device/models.py 中 DeviceInfo 的真实设备键为 device_id。
P1/P3 重构代码错误使用了不存在的旧属性。
DeviceInfo 也没有 alias 直接属性，本地显示编号应来自 meta.alias 或 device_id。
```

已修复：

```text
ui/pages/device_page.py 改为使用 device.device_id。
ui/pages/device_page.py 增加 _row_devices 行号到 DeviceInfo 对象映射，不再用截断字符串反查设备。
ui/dialogs/device_settings_dialog.py 改为使用 device.device_id。
ui/dialogs/device_settings_dialog.py 本地元数据页使用 device_manager.get_meta(device_id) 获取 alias。
本地草稿 draft_id、device_id、保存路径均改为基于 device_id。
```

修复提交：

```text
2ed905c728f5dc4aab74231eb1b9de08bd98f013  fix(ui): align device page with DeviceInfo identifiers
e26da36112203be2f6e4d373517e517566eb0520  fix(ui): align device settings dialog with DeviceInfo identifiers
```

### 5.6 待确认

```text
P3 字段兼容修复后尚未执行 compileall / pytest。
P3 字段兼容修复后尚未执行手工点击验证。
账号设置页密码显示 / 隐藏 / 复制 / 编辑尚未进入 P4。
设备设置保存到后端配置接口尚未联调。
旧 DeviceEditDialog 尚未删除，仅保留为兼容文件。
```

---

## 6. 下一阶段

推荐先执行：

```text
P3.1：设备设置对话框验证
```

验证内容：

```text
python -m compileall -q .
pytest -q
启动 PCControl。
进入设备管理页。
确认设备列表不再报 DeviceInfo 旧属性错误。
双击设备，确认打开 DeviceSettingsDialog。
右键设备 -> 编辑 / 设置，确认打开 DeviceSettingsDialog。
确认页签包含主要设置、账号设置、任务设置、物品处理、购买设置、交易设置、制造设置、铸币设置、本地元数据、其他。
确认账号设置页只出现手动输入、客户外部账号数据库两类来源。
确认本地元数据页可以保存显示编号、角色、备注。
确认保存草稿不会提示云端保存成功。
确认没有远控 / 投屏 / scrcpy 入口。
```

通过 P3.1 后再进入：

```text
P4：账号设置页与密码行为
```
