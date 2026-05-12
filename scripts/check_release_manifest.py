#!/usr/bin/env python3
r"""
文件位置: scripts/check_release_manifest.py
名称: 发布包清单检查脚本
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-12
版本: V1.0.0
功能及相关说明:
  检查 PyInstaller 发布目录是否误带本机态、运行态、测试态或敏感文件。

  设计目标:
    1. 让发布边界可自动验证，而不是依赖人工肉眼确认。
    2. 阻断 config/local.yaml、device_id.txt、logs、tests 等脏文件进入交付包。
    3. 保持规则集中，后续新增运行态文件时只维护本脚本。

  运行方式:
    python scripts/check_release_manifest.py dist/HiveGreatSage-yeya

  返回码:
    0 = 检查通过
    1 = 检查失败，发现禁止发布文件
"""

from __future__ import annotations

import argparse
import fnmatch
import sys
from pathlib import Path


# 禁止进入发布包的相对路径或通配符。
# 规则统一使用 POSIX 风格路径，便于跨平台匹配。
DENY_PATTERNS: tuple[str, ...] = (
    "config/local.yaml",
    "config/device_id.txt",
    "config/last_login.json",
    "config/device_meta.json",
    "logs",
    "logs/*",
    "tests",
    "tests/*",
    "__pycache__",
    "*/__pycache__",
    "*/__pycache__/*",
    ".pytest_cache",
    ".pytest_cache/*",
    "*.pyc",
    "*.pyo",
    "*.log",
    "*.spec",
)


# 允许出现在发布包中的模板文件。
ALLOW_EXACT: tuple[str, ...] = (
    "config/local.yaml.example",
)


def _to_posix_relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_denied(relative_path: str) -> bool:
    if relative_path in ALLOW_EXACT:
        return False
    return any(fnmatch.fnmatch(relative_path, pattern) for pattern in DENY_PATTERNS)


def find_denied_entries(release_dir: Path) -> list[str]:
    """返回发布目录中命中禁止规则的相对路径列表。"""
    denied: list[str] = []

    for path in release_dir.rglob("*"):
        rel = _to_posix_relative(path, release_dir)
        if _is_denied(rel):
            denied.append(rel + ("/" if path.is_dir() else ""))

    return sorted(set(denied))


def check_release_dir(release_dir: Path) -> int:
    if not release_dir.exists():
        print(f"❌ 发布目录不存在: {release_dir}")
        return 1

    if not release_dir.is_dir():
        print(f"❌ 发布路径不是目录: {release_dir}")
        return 1

    denied = find_denied_entries(release_dir)
    if denied:
        print("❌ 发布包清单检查失败，发现禁止发布内容:")
        for item in denied:
            print(f"  - {item}")
        print("\n请先清理上述内容，再重新打包。")
        return 1

    print(f"✅ 发布包清单检查通过: {release_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="蜂巢·大圣 PC 中控发布包清单检查")
    parser.add_argument("release_dir", help="PyInstaller 输出目录，例如 dist/HiveGreatSage-yeya")
    args = parser.parse_args(argv)

    return check_release_dir(Path(args.release_dir).resolve())


if __name__ == "__main__":
    sys.exit(main())
