#!/usr/bin/env python3
r"""
文件位置: scripts/build.py
名称: PyInstaller 打包脚本
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  将 PC 中控框架打包为单个 .exe 文件。
  打包策略：
    · --onedir 模式（比 --onefile 启动更快，且方便增量更新）
    · tools/adb/ 目录整体打包进 _internal/tools/adb/
    · config/default.yaml 打包进去
    · game/ 目录整体打包进去
  打包后目录结构：
    dist/HiveGreatSage-PCControl/
      ├── HiveGreatSage-PCControl.exe   ← 主程序
      ├── _internal/                    ← PyInstaller 运行时
      ├── tools/adb/platform-tools/     ← ADB 工具包
      └── config/default.yaml           ← 默认配置

  运行方式：
    conda activate TZYMIR
    cd HiveGreatSage-PCControl
    python scripts/build.py [--game yeya]

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题:
    · 首次打包需要 pip install pyinstaller
    · tools/adb/platform-tools/ 必须有真实的 adb.exe 才能打包
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ── 项目根目录 ──────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

def build(game_code: str = "yeya") -> None:
    print(f"=" * 60)
    print(f" 蜂巢·大圣 PC 中控 — 打包脚本 (game={game_code})")
    print(f"=" * 60)

    # 检查 adb.exe 是否存在且非空
    adb_exe = ROOT / "tools" / "adb" / "platform-tools" / "adb.exe"
    if not adb_exe.exists() or adb_exe.stat().st_size == 0:
        print(f"⚠️  警告：{adb_exe} 不存在或为空文件")
        print("     请先下载 platform-tools 并解压到 tools/adb/")
        print("     打包将继续，但打包后的程序无法使用 ADB 功能")

    app_name = f"HiveGreatSage-{game_code}"

    # PyInstaller 参数
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        f"--name={app_name}",
        "--windowed",          # 不显示控制台窗口（生产版）
        # "--console",         # 调试时改用这行

        # 数据文件
        f"--add-data={ROOT / 'config' / 'default.yaml'};config",
        f"--add-data={ROOT / 'game'};game",
        f"--add-data={ROOT / 'tools' / 'adb'};tools/adb",
        f"--add-data={ROOT / 'ui' / 'resources'};ui/resources",
        f"--add-data={ROOT / 'ui' / 'styles'};ui/styles",

        # 隐式导入
        "--hidden-import=keyring.backends.Windows",
        "--hidden-import=PySide6.QtWebSockets",
        "--hidden-import=PySide6.QtSvg",

        # 图标（如果存在）
        *([f"--icon={ROOT / 'ui' / 'resources' / 'logo.ico'}"]
          if (ROOT / "ui" / "resources" / "logo.ico").exists()
          else []),

        str(ROOT / "main.py"),
    ]

    print("\n[1/3] 运行 PyInstaller...")
    print("命令：" + " ".join(cmd[2:]))
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("\n❌ 打包失败，请检查上方错误信息")
        sys.exit(1)

    print("\n[2/3] 复制 config/local.yaml 模板...")
    dist_dir = ROOT / "dist" / app_name
    (dist_dir / "config").mkdir(exist_ok=True)
    local_example = dist_dir / "config" / "local.yaml.example"
    shutil.copy(ROOT / "config" / "default.yaml", local_example)
    local_example.write_text(
        "# 重命名此文件为 local.yaml 并填写以下字段：\n"
        "server:\n"
        "  api_base_url: \"https://你的服务器地址\"\n"
        "  project_uuid: \"填写游戏项目UUID\"\n",
        encoding="utf-8",
    )

    print("\n[3/3] 打包完成！")
    print(f"\n输出目录：{dist_dir}")
    print(f"主程序：  {dist_dir / (app_name + '.exe')}")
    print("\n发布前请确认：")
    print("  □ config/local.yaml.example 已正确")
    print("  □ tools/adb/platform-tools/adb.exe 存在且完整")
    print("  □ ui/resources/ 中有 logo 文件")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="蜂巢·大圣 PC 中控打包脚本")
    parser.add_argument("--game", default="yeya", help="游戏代号，用于命名输出文件")
    args = parser.parse_args()
    build(args.game)
