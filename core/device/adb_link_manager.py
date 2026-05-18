r"""
文件位置: core/device/adb_link_manager.py
名称: ADB 连接映射管理器
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.0.0
状态: P3.4-b ADB 映射层骨架
功能及相关说明:
  管理 device_id 与 PC 本地 ADB serial 的映射关系。
  该映射仅用于 PC 中控本地连接展示与本地操作，不参与 Verify 设备绑定主键。

边界说明:
  - Verify 设备绑定主键仍是 device_id。
  - adb_serial / connection_label 不上传 Verify 作为绑定依据。
  - 不使用隐藏设备唯一标识。
  - 不把 USB SN / TCP 地址猜测为 device_id。
  - strict_equal 仅作为最低优先级临时兜底，不写入映射文件。

后续阶段:
  - P3.4-c：接入 LAN WebSocket peer_ip 与 TCP ADB IP 匹配。
  - P3.4-d：通过 ADB 读取安卓端 /sdcard/HiveGreatSage/device_identity.json。
  - P3.4-e：设备设置页增加人工绑定 UI。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from core.utils.adb_manager import AdbManager, DeviceInfo as AdbDeviceInfo

logger = logging.getLogger(__name__)

_PROJ_ROOT = Path(__file__).resolve().parents[2]
_LINK_FILE = _PROJ_ROOT / "config" / "device_adb_links.json"


@dataclass(frozen=True)
class AdbConnectionLink:
    """device_id 与本机 ADB 连接的确认结果。"""

    device_id: str
    adb_serial: str
    connection_type: str
    connection_label: str
    match_method: str
    match_confidence: str
    source: str
    verified_at: str
    manual_locked: bool = False
    conflict: bool = False
    note: str = ""


class AdbLinkManager:
    """ADB 本地连接映射管理器。"""

    def __init__(self, adb: "AdbManager | None" = None, link_file: Path | None = None) -> None:
        self._adb = adb
        self._link_file = link_file or _LINK_FILE
        self._links: dict[str, AdbConnectionLink] = {}
        self._load_links()

    # ── 公开查询 ──────────────────────────────────

    def build_connection_index(self, device_ids: Iterable[str]) -> dict[str, AdbConnectionLink]:
        """
        返回 device_id -> AdbConnectionLink。

        当前 P3.4-b 支持：
          1. 本地已保存人工映射 manual。
          2. strict_equal 兜底：device_id 与 adb serial 完全相等时临时生成连接展示。

        注意：strict_equal 不持久化，不覆盖 manual。
        """
        requested = [device_id for device_id in device_ids if device_id]
        result: dict[str, AdbConnectionLink] = {}

        for device_id in requested:
            saved = self._links.get(device_id)
            if saved is not None:
                result[device_id] = saved

        unresolved = [device_id for device_id in requested if device_id not in result]
        if unresolved:
            result.update(self._build_strict_equal_links(unresolved))

        return result

    def list_adb_devices(self) -> list["AdbDeviceInfo"]:
        """返回 PC 本机当前 ADB 设备列表。"""
        if self._adb is None:
            return []
        try:
            return self._adb.list_devices()
        except Exception as exc:
            logger.warning("ADB 设备列表查询失败: %s", exc)
            return []

    # ── 人工绑定 ──────────────────────────────────

    def bind_manual(self, device_id: str, adb_serial: str, connection_type: str = "", note: str = "") -> AdbConnectionLink:
        """人工显式绑定 device_id 与 adb_serial。"""
        device_id = device_id.strip()
        adb_serial = adb_serial.strip()
        if not device_id:
            raise ValueError("device_id 不能为空")
        if not adb_serial:
            raise ValueError("adb_serial 不能为空")

        link = AdbConnectionLink(
            device_id=device_id,
            adb_serial=adb_serial,
            connection_type=connection_type or self._infer_connection_type(adb_serial),
            connection_label=adb_serial,
            match_method="manual",
            match_confidence="high",
            source="operator",
            verified_at=self._now(),
            manual_locked=True,
            note=note,
        )
        self._links[device_id] = link
        self._save_links()
        logger.info("ADB 人工绑定已保存: %s -> %s", device_id, adb_serial)
        return link

    def unbind(self, device_id: str) -> None:
        """解除本地 ADB 映射。"""
        self._links.pop(device_id, None)
        self._save_links()
        logger.info("ADB 本地绑定已解除: %s", device_id)

    def get_saved_link(self, device_id: str) -> AdbConnectionLink | None:
        return self._links.get(device_id)

    # ── 兜底匹配 ──────────────────────────────────

    def _build_strict_equal_links(self, device_ids: Iterable[str]) -> dict[str, AdbConnectionLink]:
        """最低优先级：device_id 与 adb serial 完全相等。"""
        device_id_set = set(device_ids)
        if not device_id_set:
            return {}
        links: dict[str, AdbConnectionLink] = {}
        for adb_device in self.list_adb_devices():
            serial = getattr(adb_device, "serial", "")
            if not serial or serial not in device_id_set:
                continue
            links[serial] = AdbConnectionLink(
                device_id=serial,
                adb_serial=serial,
                connection_type=self._connection_type_from_adb_device(adb_device),
                connection_label=serial,
                match_method="strict_equal",
                match_confidence="low_to_medium",
                source="pccontrol_runtime",
                verified_at=self._now(),
                manual_locked=False,
                note="临时兜底匹配；未写入 device_adb_links.json。",
            )
        return links

    # ── 读写 ──────────────────────────────────────

    def _load_links(self) -> None:
        if not self._link_file.exists():
            self._links = {}
            return
        try:
            with open(self._link_file, encoding="utf-8") as f:
                raw = json.load(f)
            self._links = {
                device_id: AdbConnectionLink(**payload)
                for device_id, payload in raw.items()
                if isinstance(payload, dict)
            }
            logger.debug("已加载 ADB 本地映射: %d 条", len(self._links))
        except Exception as exc:
            logger.warning("加载 device_adb_links.json 失败，使用空映射: %s", exc)
            self._links = {}

    def _save_links(self) -> None:
        self._link_file.parent.mkdir(parents=True, exist_ok=True)
        raw = {device_id: asdict(link) for device_id, link in self._links.items()}
        with open(self._link_file, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)

    # ── 辅助 ──────────────────────────────────────

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _infer_connection_type(adb_serial: str) -> str:
        return "tcp" if ":" in adb_serial else "usb"

    @classmethod
    def _connection_type_from_adb_device(cls, adb_device: "AdbDeviceInfo") -> str:
        mode_name = getattr(getattr(adb_device, "mode", None), "name", "").lower()
        if mode_name == "usb":
            return "usb"
        if mode_name == "tcpip":
            return "tcp"
        serial = getattr(adb_device, "serial", "")
        return cls._infer_connection_type(serial) if serial else "unknown"
