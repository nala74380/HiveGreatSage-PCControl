r"""
文件位置: core/network/network_config_manager.py
名称: 网络配置管理器
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-05-01
版本: V1.0.0
功能及相关说明:
  PC 中控网络配置管理器。

核心职责:
  1. 启动时选择可用 API 地址。
  2. 拉取 Verify /api/client/network-config。
  3. 根据远程配置选择 PC 中控 API 地址。
  4. 测试新地址可用性。
  5. 可用则写入 config/local.yaml。
  6. 不可用则保留旧地址。
  7. 保存 last_good_api_url、backup_api_urls、config_version。
  8. 避免一次错误配置导致 PC 中控完全断连。

设计边界:
  - 只处理 PC 中控网络入口。
  - 不修改项目 UUID。
  - 不保存敏感配置。
  - 不把家庭服务器内网地址暴露给客户端。
  - 运行中不做频繁热切换，避免同步线程不稳定。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from core.api_client.client_config_api import ClientConfigApi
from core.utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class NetworkApplyResult:
    """网络配置应用结果。"""

    changed: bool = False
    base_url: str = ""
    source: str = ""
    config_version: int = 0
    message: str = ""


class NetworkConfigManager:
    """
    PC 中控网络配置管理器。

    推荐调用顺序:
      1. Application 初始化 Config 后创建 NetworkConfigManager。
      2. 调用 bootstrap()。
      3. 再创建 AuthManager / DeviceManager。
      4. 登录成功后可调用 refresh_remote_config() 再做一次轻量刷新。
    """

    def __init__(self, config: Config) -> None:
        self._config = config

    # ── 启动流程 ──────────────────────────────────────────────

    def bootstrap(self) -> NetworkApplyResult:
        """
        启动时网络自检与远程配置拉取。

        步骤:
          1. 从 local/default 配置中收集候选地址。
          2. 选择第一个可用 Verify API 地址。
          3. 写入 server.api_base_url。
          4. 使用该地址拉取 /api/client/network-config。
          5. 如果远程返回了更合适的地址，则测试后应用。
        """
        if not bool(self._config.get("network.enabled", True)):
            logger.info("远程网络配置已关闭，跳过 bootstrap")
            return NetworkApplyResult(
                changed=False,
                base_url=self._config.get("server.api_base_url", ""),
                source="disabled",
                message="远程网络配置已关闭",
            )

        selected = self._select_reachable_base_url()

        if not selected:
            logger.warning("没有找到可用 API 地址，继续使用当前配置")
            return NetworkApplyResult(
                changed=False,
                base_url=self._config.get("server.api_base_url", ""),
                source="fallback_current",
                message="没有找到可用 API 地址",
            )

        current = self._normalize_url(self._config.get("server.api_base_url", ""))
        changed = selected != current

        if changed:
            self._config.set_local("server.api_base_url", selected)
            logger.info("启动时已切换到可用 API 地址: %s", selected)

        # 能访问基础地址后，尝试拉取远程 network-config。
        remote_result = self.refresh_remote_config(base_url=selected)

        if remote_result.changed or remote_result.base_url:
            return remote_result

        return NetworkApplyResult(
            changed=changed,
            base_url=selected,
            source="bootstrap",
            message="启动网络配置完成",
        )

    # ── 远程配置拉取与应用 ─────────────────────────────────────

    def refresh_remote_config(self, base_url: str | None = None) -> NetworkApplyResult:
        """
        拉取并应用 /api/client/network-config。

        注意:
          - 如果远程推荐地址不可用，不覆盖当前地址。
          - 如果远程 config_version 不高，也允许刷新 last_good_api_url。
          - 若远程配置可用，则写入 local.yaml。
        """
        if not bool(self._config.get("network.refresh_on_startup", True)):
            return NetworkApplyResult(
                changed=False,
                base_url=self._config.get("server.api_base_url", ""),
                source="refresh_disabled",
                message="远程配置刷新已关闭",
            )

        active_base = self._normalize_url(base_url or self._config.get("server.api_base_url", ""))

        if not active_base:
            return NetworkApplyResult(
                changed=False,
                source="empty_base_url",
                message="当前 API 地址为空，无法拉取远程配置",
            )

        timeout = float(self._config.get("server.timeout", 15))

        try:
            api = ClientConfigApi(base_url=active_base, timeout=timeout)
            data = api.get_network_config()
        except Exception as exc:
            logger.warning("拉取远程 network-config 失败: %s", exc)
            return NetworkApplyResult(
                changed=False,
                base_url=active_base,
                source="remote_fetch_failed",
                message=f"拉取远程配置失败: {exc}",
            )

        return self.apply_remote_config(data=data, source_base_url=active_base)

    def apply_remote_config(
        self,
        data: dict[str, Any],
        source_base_url: str,
    ) -> NetworkApplyResult:
        """
        应用远程 network-config。

        只应用 PC 中控需要的安全字段:
          - config_version
          - primary_api_url
          - pc_client_api_url
          - backup_api_urls
          - timeout_seconds
          - retry_count
          - heartbeat_interval_seconds
          - relay_enabled / relay_mode / relay_url
        """
        remote_version = self._safe_int(data.get("config_version"), 0)
        current_version = self._safe_int(self._config.get("network.config_version", 0), 0)

        primary_api_url = self._normalize_url(
            data.get("pc_client_api_url")
            or data.get("primary_api_url")
            or source_base_url
        )

        backup_api_urls = self._normalize_url_list(data.get("backup_api_urls") or [])

        candidate_urls = self._unique_urls([
            primary_api_url,
            *backup_api_urls,
            source_base_url,
            self._config.get("network.last_good_api_url", ""),
            self._config.get("server.api_base_url", ""),
        ])

        selected = self._first_reachable(candidate_urls)

        if not selected:
            if primary_api_url:
                self._config.set_local("network.candidate_api_url", primary_api_url)
            logger.warning("远程 network-config 中没有可用 API 地址，保留当前配置")
            return NetworkApplyResult(
                changed=False,
                base_url=self._config.get("server.api_base_url", ""),
                source="remote_all_unreachable",
                config_version=current_version,
                message="远程配置地址均不可用，已保留当前地址",
            )

        current_base = self._normalize_url(self._config.get("server.api_base_url", ""))
        changed = selected != current_base

        timeout_seconds = self._safe_int(data.get("timeout_seconds"), int(self._config.get("server.timeout", 15)))
        retry_count = self._safe_int(data.get("retry_count"), int(self._config.get("server.max_retries", 3)))
        heartbeat_interval = self._safe_int(
            data.get("heartbeat_interval_seconds"),
            int(self._config.get("sync.interval", 10)),
        )

        self._config.set_local("server.api_base_url", selected)
        self._config.set_local("server.timeout", timeout_seconds)
        self._config.set_local("server.max_retries", retry_count)
        self._config.set_local("sync.interval", heartbeat_interval)

        self._config.set_local("network.config_version", remote_version)
        self._config.set_local("network.deployment_mode", data.get("deployment_mode", ""))
        self._config.set_local("network.last_good_api_url", selected)
        self._config.set_local("network.candidate_api_url", primary_api_url)
        self._config.set_local("network.backup_api_urls", backup_api_urls)
        self._config.set_local("network.relay_enabled", bool(data.get("relay_enabled", False)))
        self._config.set_local("network.relay_mode", data.get("relay_mode", ""))
        self._config.set_local("network.relay_url", self._normalize_url(data.get("relay_url", "")))

        if changed:
            logger.info(
                "远程网络配置已应用: version=%s base_url=%s",
                remote_version,
                selected,
            )
        else:
            logger.info(
                "远程网络配置已刷新: version=%s base_url=%s",
                remote_version,
                selected,
            )

        version_msg = "版本更新" if remote_version > current_version else "版本未增加但配置已校验"

        return NetworkApplyResult(
            changed=changed,
            base_url=selected,
            source="remote_network_config",
            config_version=remote_version,
            message=version_msg,
        )

    # ── 候选地址选择 ───────────────────────────────────────────

    def _select_reachable_base_url(self) -> str:
        candidates = self._collect_candidate_urls()
        return self._first_reachable(candidates)

    def _collect_candidate_urls(self) -> list[str]:
        """
        收集候选 API 地址。

        优先级:
          1. last_good_api_url
          2. candidate_api_url
          3. 当前 server.api_base_url
          4. backup_api_urls
        """
        backup_api_urls = self._config.get("network.backup_api_urls", [])
        if not isinstance(backup_api_urls, list):
            backup_api_urls = []

        candidates = [
            self._config.get("network.last_good_api_url", ""),
            self._config.get("network.candidate_api_url", ""),
            self._config.get("server.api_base_url", ""),
            *backup_api_urls,
        ]

        return self._unique_urls(candidates)

    def _first_reachable(self, urls: list[str]) -> str:
        for url in urls:
            if self._is_reachable_base_url(url):
                return url
        return ""

    def _is_reachable_base_url(self, base_url: str) -> bool:
        """
        判断 base_url 是否为可用 Verify 地址。

        判断顺序:
          1. GET /health 成功。
          2. GET /api/client/network-config 成功。

        任一成功即可认为可用。
        """
        base = self._normalize_url(base_url)

        if not base:
            return False

        timeout = float(self._config.get("server.timeout", 15))

        for path in ("/health", "/api/client/network-config"):
            url = f"{base}{path}"
            try:
                resp = httpx.get(url, timeout=timeout)
                if 200 <= resp.status_code < 500:
                    logger.debug("候选 API 可访问: %s status=%s", url, resp.status_code)
                    return True
            except Exception as exc:
                logger.debug("候选 API 不可访问: %s error=%s", url, exc)

        return False

    # ── 工具方法 ───────────────────────────────────────────────

    def _normalize_url(self, value: Any) -> str:
        url = str(value or "").strip().rstrip("/")

        if not url:
            return ""

        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return ""

        if not parsed.netloc:
            return ""

        return url

    def _normalize_url_list(self, values: list[Any]) -> list[str]:
        return [
            item
            for item in (self._normalize_url(v) for v in values)
            if item
        ]

    def _unique_urls(self, values: list[Any]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for item in values:
            url = self._normalize_url(item)
            if not url or url in seen:
                continue
            seen.add(url)
            result.append(url)

        return result

    def _safe_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except Exception:
            return default