r"""
文件位置: core/auth/models.py
名称: 认证数据模型
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  认证相关的数据类定义：LoginResult、UserInfo。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class UserInfo:
    """登录成功后服务端返回的用户信息。"""
    username:     str = ""
    user_level:   str = ""    # trial / normal / vip / svip / tester
    display_name: str = ""
    expired_at:   str = ""    # ISO 日期字符串，如 "2026-12-31"
    device_quota: int = 0     # 该级别允许绑定的设备上限
    project_uuid: str = ""
    game_name:    str = ""


@dataclass
class LoginResult:
    """登录操作的完整结果。"""
    success:       bool      = False
    access_token:  str       = ""
    refresh_token: str       = ""
    user_info:     UserInfo  = field(default_factory=UserInfo)
    error_message: str       = ""
    error_code:    str       = ""    # 精准提示用，如 "EXPIRED" / "DEVICE_LIMIT"
