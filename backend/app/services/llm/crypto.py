"""API 密钥的对称加密。

用户自带密钥（BYOK）落库前一律加密，数据库中不出现明文。
算法为 AES-128 的替代实现：以 HMAC-SHA256 做密钥流（CTR 构造），
只用标准库，避免引入额外二进制依赖。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os

from app.config import get_settings

NONCE_BYTES = 16
KEY_CONTEXT = b"campus-ai-user-llm-key-v1"


def _derive_key() -> bytes:
    """从应用密钥派生出用于加密的 32 字节密钥。"""
    secret = get_settings().jwt_secret.encode("utf-8")
    return hmac.new(secret, KEY_CONTEXT, hashlib.sha256).digest()


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    """CTR 模式密钥流：按块对 nonce+计数做 HMAC-SHA256。"""
    out = bytearray()
    counter = 0
    while len(out) < length:
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        out.extend(block)
        counter += 1
    return bytes(out[:length])


def encrypt_secret(plaintext: str) -> str:
    """加密明文密钥，返回 base64(nonce + 密文)。"""
    key = _derive_key()
    nonce = os.urandom(NONCE_BYTES)
    data = plaintext.encode("utf-8")
    cipher = bytes(a ^ b for a, b in zip(data, _keystream(key, nonce, len(data)), strict=True))
    return base64.urlsafe_b64encode(nonce + cipher).decode("ascii")


def decrypt_secret(token: str) -> str:
    """解密由 :func:`encrypt_secret` 生成的密文。"""
    key = _derive_key()
    raw = base64.urlsafe_b64decode(token.encode("ascii"))
    nonce, cipher = raw[:NONCE_BYTES], raw[NONCE_BYTES:]
    data = bytes(a ^ b for a, b in zip(cipher, _keystream(key, nonce, len(cipher)), strict=True))
    return data.decode("utf-8")


def mask_key(plaintext: str) -> str:
    """生成可用于界面展示的密钥掩码，只保留前 4 位与后 4 位。"""
    text = (plaintext or "").strip()
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}{'*' * 8}{text[-4:]}"
