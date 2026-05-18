r"""
文件位置: core/device/adb_link_manager.py
名称: ADB 连接映射管理器
作者: 蜂巢·大圣 (HiveGreatSage)
时间: 2026-05-18
版本: V1.2.0
状态: P3.4-d ADB identity 文件读取
功能及相关说明:
  管理 device_id 与 PC 本地 ADB serial 的映射关系。
  该映射仅用于 PC 中控本地连接展示与本地操作，不参与 Verify 设备绑定主键。

边界说明:
  - Verify 设备绑定主键仍是 device_id。
  - adb_serial / connection_label 不上传 Verify 作为绑定依据。
  - 不使用隐藏设备唯一标识。
  - 不把 USB SN / TCP 地址猜测为 device_id。
  - manual 人工绑定最高优先级，不被自动匹配覆盖。
  - adb_identity 高可信，但不覆盖 manual_locked=true。
  - lan_ip 中可信，不覆盖 manual / adb_identity。
  - strict_equal 仅作为最低优先级临时兜底，不写入映射文件。

后续阶段:
  - P3.4-e：设备设置页增加人工绑定 UI。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from core.team.team_manager import TeamMember
    from core.utils.adb_manager import AdbManager, DeviceInfo as AdbDeviceInfo

logger = logging.getLogger(__name__)

_PROJ_ROOT = Path(__file__).resolve().parents[2]
_LINK_FILE = _PROJ_ROOT / "config" / "device_adb_links.json"
IDENTITY_PATH = "/sdcard/HiveGreatSage/device_identity.json"


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

        当前支持：
          1. 本地已保存映射：manual / adb_identity / lan_ip。
          2. strict_equal 兜底：device_id 与 adb serial 完全相等时临时生成连接展示。

        注意：strict_equal 不持久化，不覆盖已保存映射。
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

    # ── ADB identity 自动确认 ──────────────────────

    def refresh_identity_links(
        self,
        known_device_ids: Iterable[str],
        project_uuid: str = "",
    ) -> dict[str, AdbConnectionLink]:
        """
        通过 ADB 读取安卓端公开身份文件，刷新 adb_identity 映射。

        读取路径：/sdcard/HiveGreatSage/device_identity.json

        文件示例：
            {
              "device_id": "A118",
              "project_uuid": "...",
              "client": "HiveGreatSage-AndroidScript"
            }

        规则：
          - 只接受 known_device_ids 中存在的 device_id。
          - project_uuid 非空时必须一致。
          - 不覆盖 manual_locked=true。
          - 可覆盖 lan_ip / strict_equal / 旧 adb_identity。
          - 同一 adb_serial 读取不到或 JSON 异常时跳过。
        """
        known = {device_id for device_id in known_device_ids if device_id}
        if not known:
            return {}

        changed = False
        refreshed: dict[str, AdbConnectionLink] = {}
        seen_serial_by_device_id: dict[str, str] = {}

        for adb_device in self.list_adb_devices():
            serial = getattr(adb_device, "serial", "")
            if not serial:
                continue
            payload = self._read_identity_payload(serial)
            if payload is None:
                continue
            device_id = str(payload.get("device_id", "")).strip()
            if not device_id or device_id not in known:
                logger.debug("ADB identity 跳过未知 device_id: serial=%s device_id=%s", serial, device_id)
                continue

            payload_project_uuid = str(payload.get("project_uuid", "")).strip()
            if project_uuid and payload_project_uuid and payload_project_uuid != project_uuid:
                logger.warning(
                    "ADB identity project_uuid 不一致，跳过: serial=%s device_id=%s payload=%s expected=%s",
                    serial,
                    device_id,
                    payload_project_uuid,
                    project_uuid,
                )
                continue

            if device_id in seen_serial_by_device_id and seen_serial_by_device_id[device_id] != serial:
                self._mark_identity_conflict(device_id, [seen_serial_by_device_id[device_id], serial])
                changed = True
                continue
            seen_serial_by_device_id[device_id] = serial

            existing = self._links.get(device_id)
            if existing is not None and existing.manual_locked:
                continue

            link = AdbConnectionLink(
                device_id=device_id,
                adb_serial=serial,
                connection_type=self._connection_type_from_adb_device(adb_device),
                connection_label=serial,
                match_method="adb_identity",
                match_confidence="high",
                source="android_identity_file",
                verified_at=self._now(),
                manual_locked=False,
                conflict=False,
                note=f"Read {IDENTITY_PATH} via ADB; client={payload.get('client', '')}",
            )
            self._links[device_id] = link
            refreshed[device_id] = link
            changed = True

        if changed:
            self._save_links()
        return refreshed

    def _read_identity_payload(self, adb_serial: str) -> dict | None:
        if self._adb is None:
            return None
        result = self._adb.shell(adb_serial, f"cat {IDENTITY_PATH}")
        if not result.success or not result.stdout:
            return None
        text = result.stdout.strip()
        if not text.startswith("{"):
            logger.debug("ADB identity 输出不是 JSON: serial=%s output=%s", adb_serial, text[:80])
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning("ADB identity JSON 解析失败: serial=%s err=%s", adb_serial, exc)
            return None
        if not isinstance(payload, dict):
            return None
        return payload

    def _mark_identity_conflict(self, device_id: str, adb_serials: list[str]) -> None:
        existing = self._links.get(device_id)
        if existing is not None and existing.manual_locked:
            return
        note = f"ADB identity conflict: device_id={device_id}, adb_serials={adb_serials}"
        self._links[device_id] = AdbConnectionLink(
            device_id=device_id,
            adb_serial=adb_serials[0] if adb_serials else "",
            connection_type=self._infer_connection_type(adb_serials[0]) if adb_serials else "",
            connection_label=adb_serials[0] if adb_serials else "",
            match_method="adb_identity",
            match_confidence="conflict",
            source="android_identity_file",
            verified_at=self._now(),
            manual_locked=False,
            conflict=True,
            note=note,
        )
        logger.warning("ADB identity 映射冲突: %s", note)

    # ── LAN IP 自动匹配 ─────────────────────────────

    def refresh_lan_ip_links(self, members: Iterable["TeamMember"]) -> dict[str, AdbConnectionLink]:
        """
        根据 LAN WebSocket peer_ip 与 TCP ADB serial(ip:port) 刷新 lan_ip 映射。

        规则：
          - 只处理带 peer_ip 的 TeamMember。
          - 只匹配 TCP ADB serial，例如 192.168.2.28:5555。
          - 同一 IP 对应多个 device_id 或多个 adb_serial 时标记冲突，不自动写入。
          - 不覆盖 manual_locked=true 的人工绑定。
          - 不覆盖 adb_identity 高可信映射。
          - 可覆盖旧的 lan_ip 映射。
        """
        member_by_ip: dict[str, list["TeamMember"]] = {}
        for member in members:
            ip = self._normalize_ip(getattr(member, "peer_ip", ""))
            device_id = getattr(member, "device_id", "")
            if not ip or not device_id:
                continue
            member_by_ip.setdefault(ip, []).append(member)

        adb_by_ip: dict[str, list["AdbDeviceInfo"]] = {}
        for adb_device in self.list_adb_devices():
            serial = getattr(adb_device, "serial", "")
            ip = self._adb_serial_ip(serial)
            if not ip:
                continue
            adb_by_ip.setdefault(ip, []).append(adb_device)

        changed = False
        refreshed: dict[str, AdbConnectionLink] = {}
        for ip, ip_members in member_by_ip.items():
            adb_devices = adb_by_ip.get(ip, [])
            if len(ip_members) != 1 or len(adb_devices) != 1:
                self._mark_ip_conflicts(ip_members, adb_devices, ip)
                changed = True
                continue

            member = ip_members[0]
            adb_device = adb_devices[0]
            device_id = member.device_id
            existing = self._links.get(device_id)
            if existing is not None and (existing.manual_locked or existing.match_method == "adb_identity"):
                continue

            serial = getattr(adb_device, "serial", "")
            link = AdbConnectionLink(
                device_id=device_id,
                adb_serial=serial,
                connection_type="tcp",
                connection_label=serial,
                match_method="lan_ip",
                match_confidence="medium",
                source="pccontrol_lan",
                verified_at=self._now(),
                manual_locked=False,
                conflict=False,
                note=f"LAN peer_ip {ip} matched TCP ADB serial {serial}",
            )
            self._links[device_id] = link
            refreshed[device_id] = link
            changed = True

        if changed:
            self._save_links()
        return refreshed

    def _mark_ip_conflicts(
        self,
        members: list["TeamMember"],
        adb_devices: list["AdbDeviceInfo"],
        ip: str,
    ) -> None:
        """记录 LAN IP 匹配冲突，不自动绑定。"""
        if not members or not adb_devices:
            return
        device_ids = [m.device_id for m in members if m.device_id]
        adb_serials = [getattr(d, "serial", "") for d in adb_devices if getattr(d, "serial", "")]
        note = f"LAN IP {ip} conflict: device_ids={device_ids}, adb_serials={adb_serials}"
        for device_id in device_ids:
            existing = self._links.get(device_id)
            if existing is not None and (existing.manual_locked or existing.match_method == "adb_identity"):
                continue
            self._links[device_id] = AdbConnectionLink(
                device_id=device_id,
                adb_serial=adb_serials[0] if len(adb_serials) == 1 else "",
                connection_type="tcp",
                connection_label=adb_serials[0] if len(adb_serials) == 1 else "",
                match_method="lan_ip",
                match_confidence="conflict",
                source="pccontrol_lan",
                verified_at=self._now(),
                manual_locked=False,
                conflict=True,
                note=note,
            )
        logger.warning("ADB LAN IP 映射冲突: %s", note)

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
    def _normalize_ip(ip: str) -> str:
        ip = (ip or "").strip()
        if ip.startswith("::ffff:"):
            ip = ip.removeprefix("::ffff:")
        return ip

    @classmethod
    def _adb_serial_ip(cls, adb_serial: str) -> str:
        if not adb_serial or ":" not in adb_serial:
            return ""
        host = adb_serial.rsplit(":", 1)[0]
        return cls._normalize_ip(host)

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
