r"""
文件位置: core/api_client/params_api.py
名称: 参数配置 API
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  封装与 Verify 系统脚本参数端点的通信。
  GET  /api/params/get  — 拉取当前用户所有参数（定义+用户值合并）
  POST /api/params/set  — 保存参数修改

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

from core.api_client.base_client import BaseClient


class ParamsApi(BaseClient):
    """脚本参数 API 客户端。"""

    def get_params(self) -> dict:
        """
        GET /api/params/get
        返回 ParamsGetResponse dict:
          game_project_code, params: list[ParamItem], total
        """
        return self.get("/api/params/get")

    def set_params(self, params: list[dict]) -> dict:
        """
        POST /api/params/set
        Args:
            params: list of {"param_key": str, "param_value": str}
        Returns:
            ParamsSetResponse dict:
              game_project_code, updated_count, failed_count, results
        """
        return self.post("/api/params/set", json={"params": params})
