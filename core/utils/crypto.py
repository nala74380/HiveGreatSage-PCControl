r"""
文件位置: core/utils/crypto.py
名称: 加密工具
作者: 蜂巢·大圣 (Hive-GreatSage)
时间: 2026-04-27
版本: V1.0.0
功能及相关说明:
  基于 Fernet 对称加密，用于 Refresh Token 的本地加密存储。
  密钥由机器唯一标识（hardware_serial）+ 固定盐值派生，
  保证同一台机器跨进程重启后都能解密，换台机器则无法解密。

改进内容:
  V1.0.0 - 初始版本

调试信息:
  已知问题: 无
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_SALT = b"HiveGreatSage-PCControl-v1"   # 固定盐值，不可修改


def _derive_key(hardware_serial: str) -> bytes:
    """从 hardware_serial 派生 Fernet 密钥（32 bytes base64url）。"""
    raw = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=hardware_serial.encode("utf-8"),
        salt=_SALT,
        iterations=100_000,
        dklen=32,
    )
    return base64.urlsafe_b64encode(raw)


def encrypt_token(plaintext: str, hardware_serial: str) -> str:
    """
    加密字符串，返回 base64 密文字符串。

    Args:
        plaintext:       明文（如 Refresh Token）
        hardware_serial: 本机唯一标识，用于密钥派生

    Returns:
        加密后的 base64 字符串
    """
    key    = _derive_key(hardware_serial)
    fernet = Fernet(key)
    token  = fernet.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_token(ciphertext: str, hardware_serial: str) -> str | None:
    """
    解密字符串，解密失败返回 None（不抛异常）。

    Args:
        ciphertext:      密文字符串（由 encrypt_token 生成）
        hardware_serial: 本机唯一标识

    Returns:
        明文字符串，或 None（解密失败 / 密钥不匹配）
    """
    try:
        key    = _derive_key(hardware_serial)
        fernet = Fernet(key)
        result = fernet.decrypt(ciphertext.encode("utf-8"))
        return result.decode("utf-8")
    except (InvalidToken, Exception) as e:
        logger.warning("Refresh Token 解密失败: %s", e)
        return None
