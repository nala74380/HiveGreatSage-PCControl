r"""
文件位置: core/utils/constants.py
名称: 全局常量
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  整个 PC 中控框架使用的全局常量。
  与配置文件的区别：常量是代码层面不可变的值，配置是运行时可调整的值。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

# ── 应用元信息 ──────────────────────────────────────────────
APP_NAME          = "蜂巢·大圣 PC 中控"
APP_VERSION       = "1.0.0"
CLIENT_TYPE       = "pc"          # Verify schema 要求: ^(pc|android)$
RUNTIME_MODE      = "pc"

# ── 路径标识 ────────────────────────────────────────────────
KEYRING_SERVICE   = "HiveGreatSage-PCControl"
KEYRING_RT_SUFFIX = "-RT"       # Refresh Token keyring 服务名后缀
LAST_LOGIN_FILE   = "config/last_login.json"
DEVICE_ID_FILE    = "config/device_id.txt"
LOCAL_YAML        = "config/local.yaml"
DEFAULT_YAML      = "config/default.yaml"

# ── 网络 ───────────────────────────────────────────────────
DEFAULT_WS_PORT          = 8889
DEFAULT_WS_FALLBACK_PORT = 8890
SYNC_INTERVAL_SEC        = 10
