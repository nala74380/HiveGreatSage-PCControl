r"""
文件位置: main.py
名称: 应用入口
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  PC 中控应用的启动入口。
  ⚠️ os.environ 的 DPI 设置必须在任何 Qt 相关导入之前完成，
     因此 Application 的 import 放在 main() 函数内部（延迟导入）。

改进内容:
  V1.0.0 - 初始版本（修正 DPI 设置顺序）

调试信息:
  已知问题: 无
  启动命令: python main.py
"""

import os

# ── 必须在任何 Qt 导入之前设置 ──────────────────────────────
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

import sys


def main() -> None:
    # 延迟导入确保 DPI 环境变量已生效
    from core.app import Application

    application = Application(sys.argv)
    sys.exit(application.run())


if __name__ == "__main__":
    main()
