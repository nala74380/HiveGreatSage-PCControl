r"""
文件位置: core/debug/mock_devices.py
名称: 开发调试模拟数据
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  开发阶段用于 UI 调试的模拟数据生成器。
  生成 10 台设备，每台设备包含完整的 game_data（任务/等级/战力/区服/订单/价格）。
  调用方式：
    from core.debug.mock_devices import generate_mock_devices
    devices = generate_mock_devices()

改进内容:
  V1.0.0 - 初始版本

调试信息:
  仅在开发阶段使用，生产环境不调用此模块。
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone, timedelta

from core.device.models import DeviceInfo


def _rand_fp() -> str:
    return str(uuid.uuid4()).replace("-", "")[:20]


def _rand_last_seen(max_seconds_ago: int = 60) -> datetime:
    return datetime.now(timezone.utc) - timedelta(
        seconds=random.randint(1, max_seconds_ago)
    )


def generate_mock_devices() -> list[DeviceInfo]:
    """生成 10 台模拟设备，包含完整 game_data（订单 + 价格）。"""

    random.seed(42)   # 固定 seed，每次启动数据一致，方便对比 UI

    TASKS    = ["联盟任务", "副本扫荡", "挂机采集", "铸币生产", "跨服集结", "主线剧情", "—"]
    SERVERS  = ["S1", "S2", "S3", "S4"]
    ROLES    = ["captain", "power", "farmer", "farmer", "newbie"]
    STATUSES = ["running", "running", "running", "idle", "idle", "idle", "offline", "offline", "error", "running"]
    ITEMS    = ["精铁矿石", "高纯铁锭", "龙骨原木", "天火晶石", "元气丹", "战争符文", "破魔石"]
    PLAYERS  = [f"玩家{n}" for n in range(100, 150)]

    configs = []
    for i in range(10):
        configs.append({
            "alias":     f"A-{i+1:03d}",
            "role":      ROLES[i % len(ROLES)],
            "server":    SERVERS[i % len(SERVERS)],
            "status":    STATUSES[i % len(STATUSES)],
            "level":     random.randint(25, 75),
            "cp":        random.randint(80_000, 680_000),
            "task":      random.choice(TASKS),
            "activated": i < 7,
        })

    devices: list[DeviceInfo] = []

    for i, cfg in enumerate(configs):
        fp = _rand_fp()
        is_online = cfg["status"] not in ("offline",)

        # 订单数据（每台 1~3 条）
        orders = []
        for _ in range(random.randint(1, 3)):
            orders.append({
                "item":   random.choice(ITEMS),
                "price":  random.randint(800, 5800),
                "status": random.choice(["pend", "sell", "done"]),
                "seller": random.choice(PLAYERS),
                "buyer":  random.choice(PLAYERS),
                "time":   f"{random.randint(1, 59)}分钟前",
            })

        # 价格数据（每台上报 3~5 种物品当前市价）
        prices = []
        for item in random.sample(ITEMS, k=random.randint(3, 5)):
            prices.append({
                "item":  item,
                "price": random.randint(650, 6200),
            })

        raw_api = {
            "device_id": fp,
            "user_id":   i + 1,
            "status":    cfg["status"],
            "is_online": is_online,
            "last_seen": _rand_last_seen(60).isoformat(),
            "game_data": {
                "task":         cfg["task"],
                "level":        cfg["level"],
                "combat_power": cfg["cp"],
                "server":       cfg["server"],
                "orders":       orders,
                "prices":       prices,
            },
        }
        meta = {
            "alias":     cfg["alias"],
            "role":      cfg["role"],
            "note":      f"模拟设备 #{i+1}",
            "activated": cfg["activated"],
        }
        devices.append(DeviceInfo.from_api(raw_api, meta))

    return devices
