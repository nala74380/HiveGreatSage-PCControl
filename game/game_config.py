r"""
文件位置: game/game_config.py
名称: 游戏定制配置 — yeya（椰芽）
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.1
功能及相关说明:
  本文件是 game/ 定制区的入口配置，fork 后第一个修改的文件。
  project_uuid 与 config/local.yaml 中的值保持一致，
  local.yaml 是运行时读取来源，本文件仅作为代码层面的游戏元信息声明。

  ⚠️ 修改说明：
    GAME_CODE 是游戏在 Verify 系统中注册的 code_name。
    PROJECT_UUID 必须与 Verify 管理后台创建项目时返回的 project_uuid 一致。
    两处需同步：1）此处 PROJECT_UUID 常量  2）config/local.yaml server.project_uuid

改进历史:
  V1.0.1 (2026-04-28) - 修正 GAME_DB_NAME 双前缀 bug（hive_game_game_002 → hive_yeya）
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

# ── 游戏元信息（fork 后修改） ──────────────────────────────────

GAME_NAME     = "椰芽"
GAME_CODE     = "yeya"          # Verify 系统中的 code_name，需与 Verify 后台一致
GAME_VERSION  = "1.0.0"

# ── 项目 UUID（与 config/local.yaml → server.project_uuid 保持一致）──
# 运行时实际从 Config.get("server.project_uuid") 读取，此处作为代码可读性声明。
# ⚠️ 必须与 Verify 管理后台创建游戏项目时返回的 project_uuid 完全一致。
PROJECT_UUID  = "07238db5-129a-4408-b82a-e025be4652a1"   # ← fork 后填入真实 UUID

# ── 游戏数据库（仅供参考，PCControl 不直连 DB）──────────────
# 规则：hive_{code_name}，在 Verify 后台创建时由 setup_game_db.py 生成
GAME_DB_NAME  = "hive_yeya"

# ── 窗口标题 ─────────────────────────────────────────────────
WINDOW_TITLE  = f"蜂巢·大圣 PC 中控 — {GAME_NAME}"
WINDOW_ICON   = "ui/resources/logo.svg"
