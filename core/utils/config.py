r"""
文件位置: core/utils/config.py
名称: 配置管理
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  加载 default.yaml 和 local.yaml，提供全局唯一的 Config 单例。
  local.yaml 的值覆盖 default.yaml。
  通过 dotted key（如 "server.api_base_url"）访问嵌套值。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

from core.utils.constants import DEFAULT_YAML, LOCAL_YAML

logger = logging.getLogger(__name__)

# 项目根目录（通过本文件路径推断，不依赖工作目录）
_PROJ_ROOT = Path(__file__).resolve().parents[2]


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典，override 的叶子节点优先。"""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


class Config:
    """
    全局配置单例。

    用法：
        from core.utils.config import Config
        cfg = Config.instance()
        url  = cfg.get("server.api_base_url")
        port = cfg.get("team.ws_port", 8889)
    """

    _instance: "Config | None" = None

    def __init__(self) -> None:
        self._data: dict = {}
        self._load()

    # ── 单例访问 ──────────────────────────
    @classmethod
    def instance(cls) -> "Config":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── 加载 ──────────────────────────────
    def _load(self) -> None:
        default_path = _PROJ_ROOT / DEFAULT_YAML
        local_path   = _PROJ_ROOT / LOCAL_YAML

        if not default_path.exists():
            logger.warning("默认配置文件不存在: %s", default_path)
            self._data = {}
            return

        with open(default_path, encoding="utf-8") as f:
            self._data = yaml.safe_load(f) or {}

        if local_path.exists():
            with open(local_path, encoding="utf-8") as f:
                local_data = yaml.safe_load(f) or {}
            self._data = _deep_merge(self._data, local_data)
            logger.debug("已加载本地覆盖配置: %s", local_path)
        else:
            logger.debug("local.yaml 不存在，使用默认配置")

    # ── 读取 ──────────────────────────────
    def get(self, key: str, default: Any = None) -> Any:
        """
        通过 dotted key 读取配置值。

        Args:
            key:     点分路径，如 "server.api_base_url"
            default: key 不存在时的返回值
        """
        parts = key.split(".")
        node = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    # ── 写入 local.yaml（运行时持久化用户设置）──
    def set_local(self, key: str, value: Any) -> None:
        """
        将 key=value 写入 config/local.yaml 并立即生效。
        用于首次运行时持久化生成的 hardware_serial 等。
        """
        local_path = _PROJ_ROOT / LOCAL_YAML

        if local_path.exists():
            with open(local_path, encoding="utf-8") as f:
                local_data = yaml.safe_load(f) or {}
        else:
            local_data = {}

        parts = key.split(".")
        node = local_data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(local_data, f, allow_unicode=True, default_flow_style=False)

        self._data = _deep_merge(self._data, local_data)
        logger.debug("config/local.yaml 已更新: %s = %s", key, value)
