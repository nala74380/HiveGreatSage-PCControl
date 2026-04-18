r"""
文件位置: core/utils/adb_manager.py
文件名称: adb_manager.py
作者: Hailin
时间: 2026-04-19
版本: v1.0.0
功能及相关说明:
    ADB 设备管理封装层。
    支持 USB 连接（serial = 设备序列号）和 TCP/IP 连接（serial = ip:port）两种模式。
    所有操作通过本地 platform-tools/adb.exe 调用，无第三方 Python 依赖。
改进内容: 初版
调试信息: 需确认 tools/adb/platform-tools/adb.exe 路径存在
"""

from __future__ import annotations

import subprocess
import logging
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  常量
# ──────────────────────────────────────────────

# platform-tools 目录：相对于本文件向上两级到项目根，再进 tools/adb/
_PROJ_ROOT = Path(__file__).resolve().parents[2]
ADB_EXE    = _PROJ_ROOT / "tools" / "adb" / "platform-tools" / "adb.exe"

# 激活命令序列（依次执行，任一失败即中止）
ACTIVATE_CMDS = [
    "cp /sdcard/Download/proxy /data/local/tmp/proxy",
    "chmod 777 /data/local/tmp/proxy",
    "/data/local/tmp/proxy --daemon",
]

DEFAULT_TCP_PORT = 5555
ADB_TIMEOUT      = 10   # 秒，单条命令超时


# ──────────────────────────────────────────────
#  数据类型
# ──────────────────────────────────────────────

class ConnMode(Enum):
    USB   = auto()
    TCPIP = auto()


@dataclass
class AdbResult:
    success:   bool
    returncode: int
    stdout:    str
    stderr:    str

    @property
    def output(self) -> str:
        return self.stdout or self.stderr


@dataclass
class DeviceInfo:
    serial:   str                      # USB 序列号 或 ip:port
    mode:     ConnMode
    state:    str = "unknown"          # device / offline / unauthorized
    model:    str = ""
    product:  str = ""
    extra:    dict = field(default_factory=dict)

    @property
    def is_ready(self) -> bool:
        return self.state == "device"

    @property
    def display(self) -> str:
        tag = "USB" if self.mode == ConnMode.USB else "TCP"
        return f"[{tag}] {self.serial}  {self.model or '—'}  ({self.state})"


# ──────────────────────────────────────────────
#  AdbManager
# ──────────────────────────────────────────────

class AdbManager:
    """
    封装 adb.exe 调用，对上层屏蔽 USB/TCP 差异。

    用法示例：
        mgr = AdbManager()
        mgr.start_server()

        # USB 模式
        devices = mgr.list_devices()

        # TCP/IP 连接
        ok = mgr.connect_tcpip("192.168.1.101")

        # 执行 shell
        result = mgr.shell("SN·4F2A·8C1E", "echo hello")

        # 激活设备
        ok = mgr.activate_device("SN·4F2A·8C1E")
    """

    def __init__(self, adb_path: Optional[Path] = None):
        self._adb = str(adb_path or ADB_EXE)
        if not Path(self._adb).exists():
            logger.warning(
                "adb.exe 不存在: %s\n"
                "请从 https://developer.android.com/tools/releases/platform-tools "
                "下载 Windows platform-tools 并解压到 tools/adb/",
                self._adb,
            )

    # ────────── 内部执行 ──────────

    def _run(self, *args: str, timeout: int = ADB_TIMEOUT) -> AdbResult:
        """执行任意 adb 命令，返回结构化结果。"""
        cmd = [self._adb, *args]
        logger.debug("ADB ▶ %s", " ".join(cmd))
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            ok = r.returncode == 0
            if not ok:
                logger.warning("ADB 返回 %d: %s", r.returncode, r.stderr.strip())
            return AdbResult(ok, r.returncode, r.stdout.strip(), r.stderr.strip())
        except subprocess.TimeoutExpired:
            logger.error("ADB 命令超时 (%ds): %s", timeout, " ".join(cmd))
            return AdbResult(False, -1, "", "timeout")
        except FileNotFoundError:
            logger.error("找不到 adb.exe: %s", self._adb)
            return AdbResult(False, -1, "", "adb not found")

    def _device_args(self, serial: str) -> list[str]:
        """生成 -s <serial> 参数，serial 为空时省略（操作唯一已连接设备）。"""
        return ["-s", serial] if serial else []

    # ────────── Server 管理 ──────────

    def start_server(self) -> bool:
        """启动 adb server（程序启动时调用一次即可）。"""
        r = self._run("start-server")
        logger.info("ADB server 启动: %s", "成功" if r.success else "失败")
        return r.success

    def kill_server(self) -> bool:
        return self._run("kill-server").success

    # ────────── 设备枚举 ──────────

    def list_devices(self) -> list[DeviceInfo]:
        """
        返回当前所有已连接设备（USB + TCP 混合）。
        解析 `adb devices -l` 输出。
        """
        r = self._run("devices", "-l")
        devices: list[DeviceInfo] = []
        for line in r.stdout.splitlines()[1:]:   # 跳过第一行 "List of devices attached"
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state  = parts[1]
            # 解析附加字段 key:value
            extra: dict[str, str] = {}
            for token in parts[2:]:
                if ":" in token:
                    k, _, v = token.partition(":")
                    extra[k] = v
            mode  = ConnMode.TCPIP if ":" in serial else ConnMode.USB
            model = extra.get("model", "")
            devices.append(DeviceInfo(serial, mode, state, model, extra.get("product",""), extra))
        return devices

    def get_device(self, serial: str) -> Optional[DeviceInfo]:
        """按 serial 查找单个设备信息。"""
        return next((d for d in self.list_devices() if d.serial == serial), None)

    # ────────── TCP/IP 连接管理 ──────────

    def enable_tcpip(self, serial: str, port: int = DEFAULT_TCP_PORT) -> bool:
        """
        将 USB 连接的设备切换为 TCP/IP 监听模式。
        切换后可拔 USB，用 connect_tcpip() 通过 WiFi 连接。
        """
        r = self._run(*self._device_args(serial), "tcpip", str(port))
        if r.success:
            logger.info("[%s] 已切换为 TCP/IP 模式，端口 %d", serial, port)
        return r.success

    def connect_tcpip(self, ip: str, port: int = DEFAULT_TCP_PORT) -> bool:
        """
        通过 IP 连接 TCP/IP 模式设备。
        返回 True 表示 connected 或 already connected。
        """
        target = f"{ip}:{port}"
        r = self._run("connect", target)
        ok = r.success and ("connected" in r.stdout or "already" in r.stdout)
        logger.info("TCP/IP 连接 %s: %s", target, "成功" if ok else f"失败 ({r.output})")
        return ok

    def disconnect_tcpip(self, ip: str, port: int = DEFAULT_TCP_PORT) -> bool:
        """断开 TCP/IP 连接。"""
        r = self._run("disconnect", f"{ip}:{port}")
        return r.success

    def disconnect_all(self) -> bool:
        """断开所有 TCP/IP 连接（USB 设备不受影响）。"""
        return self._run("disconnect").success

    # ────────── Shell 命令 ──────────

    def shell(self, serial: str, command: str, timeout: int = ADB_TIMEOUT) -> AdbResult:
        """
        在指定设备上执行 shell 命令。

        Args:
            serial:  设备序列号（USB）或 ip:port（TCP）
            command: shell 命令字符串
            timeout: 超时秒数
        """
        return self._run(*self._device_args(serial), "shell", command, timeout=timeout)

    def shell_batch(self, serial: str, commands: list[str], stop_on_error: bool = True) -> list[AdbResult]:
        """
        顺序执行多条 shell 命令。
        stop_on_error=True 时，遇到失败立即中止后续命令。
        """
        results: list[AdbResult] = []
        for cmd in commands:
            r = self.shell(serial, cmd)
            results.append(r)
            if stop_on_error and not r.success:
                logger.warning("批量 shell 在第 %d 条命令失败，中止。命令: %s", len(results), cmd)
                break
        return results

    # ────────── 文件传输 ──────────

    def push(self, serial: str, local: str, remote: str) -> bool:
        """推送本地文件到设备。"""
        r = self._run(*self._device_args(serial), "push", local, remote)
        return r.success

    def pull(self, serial: str, remote: str, local: str) -> bool:
        """从设备拉取文件到本地。"""
        r = self._run(*self._device_args(serial), "pull", remote, local)
        return r.success

    # ────────── 激活设备 ──────────

    def activate_device(self, serial: str) -> tuple[bool, str]:
        """
        向目标设备部署并启动代理守护进程（ROOT 激活模式）。

        执行顺序:
            1. cp /sdcard/Download/proxy /data/local/tmp/proxy
            2. chmod 777 /data/local/tmp/proxy
            3. /data/local/tmp/proxy --daemon

        Returns:
            (success: bool, message: str)
        """
        logger.info("[%s] 开始激活设备...", serial)
        dev = self.get_device(serial)
        if not dev:
            msg = f"设备 {serial} 未连接"
            logger.error(msg)
            return False, msg
        if not dev.is_ready:
            msg = f"设备 {serial} 状态异常: {dev.state}（需要 authorized device）"
            logger.error(msg)
            return False, msg

        results = self.shell_batch(serial, ACTIVATE_CMDS, stop_on_error=True)

        # 检查最后一条是否是 daemon 启动
        if len(results) == len(ACTIVATE_CMDS) and all(r.success for r in results):
            logger.info("[%s] 激活成功，代理守护进程已启动", serial)
            return True, "激活成功"

        failed_idx = next((i for i, r in enumerate(results) if not r.success), -1)
        failed_cmd = ACTIVATE_CMDS[failed_idx] if failed_idx >= 0 else "unknown"
        msg = f"激活失败，第 {failed_idx + 1} 步出错: {failed_cmd}\n输出: {results[failed_idx].output}"
        logger.error("[%s] %s", serial, msg)
        return False, msg

    def batch_activate(self, serials: list[str]) -> dict[str, tuple[bool, str]]:
        """批量激活多台设备，返回每台的结果字典。"""
        return {s: self.activate_device(s) for s in serials}

    # ────────── 设备基础信息 ──────────

    def get_serial_no(self, serial: str) -> str:
        """读取设备硬件序列号（与 ADB serial 可能不同）。"""
        r = self.shell(serial, "getprop ro.serialno")
        return r.stdout if r.success else ""

    def get_model(self, serial: str) -> str:
        r = self.shell(serial, "getprop ro.product.model")
        return r.stdout if r.success else ""

    def get_android_version(self, serial: str) -> str:
        r = self.shell(serial, "getprop ro.build.version.release")
        return r.stdout if r.success else ""

    def get_ip_address(self, serial: str) -> str:
        """获取设备 wlan0 IP 地址（用于切换 TCP/IP 连接）。"""
        r = self.shell(serial, "ip -f inet addr show wlan0")
        if not r.success:
            return ""
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                # inet 192.168.1.101/24 ...
                return line.split()[1].split("/")[0]
        return ""