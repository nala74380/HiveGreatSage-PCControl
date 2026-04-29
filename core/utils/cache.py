r"""
文件位置: core/utils/cache.py
名称: 内存缓存工具
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  简单的线程安全 TTL 内存缓存。
  用于 SyncWorker 的设备快照缓存：
    当 API 请求失败时，返回上一次成功的结果，避免 UI 清空设备列表。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import threading
import time
from typing import Any


class TTLCache:
    """
    线程安全的 TTL 内存缓存。

    用法：
        cache = TTLCache(default_ttl=30)
        cache.set("devices", device_list)
        result = cache.get("devices")          # None if expired
        result = cache.get("devices", [])      # 带 default
    """

    def __init__(self, default_ttl: float = 60.0) -> None:
        self._store:   dict[str, tuple[Any, float]] = {}  # key → (value, expire_at)
        self._ttl      = default_ttl
        self._lock     = threading.Lock()

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """写入缓存。"""
        expire_at = time.monotonic() + (ttl if ttl is not None else self._ttl)
        with self._lock:
            self._store[key] = (value, expire_at)

    def get(self, key: str, default: Any = None) -> Any:
        """读取缓存；过期或不存在时返回 default。"""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return default
            value, expire_at = entry
            if time.monotonic() > expire_at:
                del self._store[key]
                return default
            return value

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def has(self, key: str) -> bool:
        return self.get(key) is not None
