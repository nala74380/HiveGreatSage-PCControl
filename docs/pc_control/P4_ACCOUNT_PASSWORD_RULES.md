---
文件位置: docs/pc_control/P4_ACCOUNT_PASSWORD_RULES.md
名称: P4_账号设置页密码行为规则
项目: 蜂巢·大圣 HiveGreatSage
模块: HiveGreatSage-PCControl
状态: P4 执行规则 / 密码行为边界
创建时间: 2026-05-19
关联文档:
  - docs/pc_control/UI_BOUNDARY.md
  - docs/pc_control/UI_BOUNDARY_DECISION_LOG.md
  - HiveGreatSage-Knowledge/02-PC中控框架/UI边界重构方案.md
  - HiveGreatSage-Knowledge/02-PC中控框架/UI边界重构执行方案.md
---

# P4 账号设置页密码行为规则

## 1. 当前任务理解

P4 的目标不是单纯增加一个密码输入框，而是把设备设置中的账号设置页从 P3 骨架升级为可用、可控、可维护的账号设置能力。

当前阶段先解决单设备账号设置页中的密码行为，后续是否表格化账号设置页、是否支持客户外部账号数据库字段映射，必须在 P6 或后续阶段继续设计。

---

## 2. 已确认边界

```text
账号设置页属于 DeviceSettingsDialog。
账号设置页中的账号是游戏账号，不是 PC 登录账号，也不是 Verify 用户账号。
当前账号来源只允许：手动输入、客户外部账号数据库。
客户外部账号数据库连接配置属于全局设置的附加能力，但具体游戏账号字段仍属于设备设置 / 账号设置页。
```

---

## 3. 密码行为硬规则

P4 实现必须满足：

```text
密码默认隐藏。
必须有显式“显示”按钮或动作。
必须有显式“隐藏”按钮或动作。
必须有显式“复制”按钮或动作。
必须允许编辑真实密码。
编辑完成后默认恢复隐藏。
复制时不得把真实密码写入日志。
复制时不得把真实密码写入状态栏。
复制时不得在普通提示弹窗中显示真实密码。
普通诊断包不得包含真实密码。
```

---

## 4. 当前阶段的保存规则

当前后端配置保存接口尚未联调，因此 P4 第一轮不得声称云端保存闭环完成。

本地草稿规则：

```text
允许保存 password_present。
禁止保存真实 password 明文。
禁止把真实密码写入普通 profile JSON。
禁止把真实密码写入日志。
```

当前草稿中只允许出现：

```json
{
  "password_present": true
}
```

不得出现：

```json
{
  "password": "真实密码"
}
```

---

## 5. 与 Ymir-CC 的关系

Ymir-CC 可参考：

```text
账号设置页结构。
账号字段组织方式。
密码掩码显示思路。
右键显示 / 隐藏 / 复制行为。
编辑完成后恢复掩码的交互。
```

但 HiveGreatSage 不照搬：

```text
不照搬本地 JSON 作为最终真相源。
不绕过后端配置接口设计。
不把账号设置搬入全局设置。
不弱化显示 / 隐藏 / 复制按钮。
不把真实密码写入普通诊断包。
```

---

## 6. 推荐实现路径

P4 第一轮实现顺序：

```text
1. 新增 ui/widgets/account/password_editor.py。
2. 新增 ui/dialogs/device_settings/pages/account_settings_page.py。
3. DeviceSettingsDialog 挂载 AccountSettingsPage。
4. AccountSettingsPage 使用 PasswordEditor 替换当前简单 QLineEdit 密码框。
5. DeviceSettingsDialog 保存草稿时继续只保存 password_present。
6. 手动验证显示 / 隐藏 / 复制 / 编辑 / 草稿保存。
```

---

## 7. 后续扩展点

后续如进入账号表格化，应新增：

```text
ui/widgets/account/account_table_model.py
ui/widgets/account/account_table_view.py
ui/widgets/account/password_delegate.py
```

但表格化不是 P4 第一轮必须完成项。

---

## 8. 验收清单

```text
账号设置页能打开。
密码默认隐藏。
点击显示后能看到真实密码。
点击隐藏后恢复隐藏。
点击复制后剪贴板可用。
复制成功提示不显示真实密码。
编辑密码后仍能隐藏 / 显示 / 复制。
保存草稿不写真实密码，只写 password_present。
日志中不出现真实密码。
状态栏不出现真实密码。
普通诊断包不包含真实密码。
```
