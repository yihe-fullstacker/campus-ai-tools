"""账户与认证能力函数。

密码使用 bcrypt 加盐哈希存储；访问令牌为 HS256 签名的 JWT，默认有效期 7 天。
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config import get_settings
from app.errors import ApiError
from app.storage.db import utc_now_iso

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{4,20}$")
MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72  # bcrypt 的输入上限，超出部分会被静默截断


def normalize_identity(identity: str) -> str:
    """规范化账号标识：去除首尾空白并统一转小写，便于唯一性判定。"""
    return identity.strip().lower()


def validate_identity(identity: str) -> str:
    """校验账号标识格式，返回规范化后的结果。"""
    normalized = normalize_identity(identity)
    if not normalized:
        raise ApiError(400, "AUTH_IDENTITY_INVALID", "请填写学号或邮箱。")
    if len(normalized) > 64:
        raise ApiError(400, "AUTH_IDENTITY_INVALID", "学号或邮箱过长，请检查输入。")
    if not (EMAIL_PATTERN.match(normalized) or STUDENT_ID_PATTERN.match(normalized)):
        raise ApiError(
            400,
            "AUTH_IDENTITY_INVALID",
            "账号需为有效邮箱，或 4–20 位字母数字组成的学号。",
        )
    return normalized


def validate_password(password: str) -> None:
    """校验密码强度：8–72 字节，且至少包含字母与数字。"""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ApiError(400, "AUTH_PASSWORD_WEAK", "密码至少 8 位。")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ApiError(400, "AUTH_PASSWORD_WEAK", "密码不能超过 72 字节。")
    has_letter = any(char.isalpha() for char in password)
    has_digit = any(char.isdigit() for char in password)
    if not (has_letter and has_digit):
        raise ApiError(400, "AUTH_PASSWORD_WEAK", "密码需同时包含字母和数字。")


def hash_password(password: str) -> str:
    """生成加盐哈希。"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验密码与哈希是否匹配；哈希非法时返回 False。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _row_to_user(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "identity": row["identity"],
        "role": row["role"],
        "created_at": row["created_at"],
    }


def get_user_by_id(conn: sqlite3.Connection, user_id: int) -> dict | None:
    """按主键查询用户。"""
    row = conn.execute(
        "SELECT id, identity, role, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return _row_to_user(row) if row is not None else None


def get_user_by_identity(conn: sqlite3.Connection, identity: str) -> dict | None:
    """按账号标识查询用户（规范化后匹配）。"""
    row = conn.execute(
        "SELECT id, identity, role, created_at FROM users WHERE identity = ?",
        (normalize_identity(identity),),
    ).fetchone()
    return _row_to_user(row) if row is not None else None


def create_user(
    conn: sqlite3.Connection,
    identity: str,
    password: str,
    role: str = "student",
) -> dict:
    """创建用户；账号标识唯一，重复注册会被拒绝。"""
    normalized = validate_identity(identity)
    validate_password(password)
    if get_user_by_identity(conn, normalized) is not None:
        raise ApiError(400, "AUTH_IDENTITY_EXISTS", "该学号或邮箱已注册，请直接登录。")
    now = utc_now_iso()
    cursor = conn.execute(
        "INSERT INTO users (identity, password_hash, role, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (normalized, hash_password(password), role, now, now),
    )
    conn.commit()
    user = get_user_by_id(conn, cursor.lastrowid)
    if user is None:  # pragma: no cover - 刚写入的记录不可能读不到
        raise ApiError(500, "AUTH_CREATE_FAILED", "用户创建失败，请稍后重试。")
    return user


def authenticate(conn: sqlite3.Connection, identity: str, password: str) -> dict:
    """校验账号与密码，返回用户信息。"""
    user = get_user_by_identity(conn, identity)
    if user is None:
        # 不区分“账号不存在”与“密码错误”，避免账号枚举
        raise ApiError(401, "AUTH_CREDENTIALS_INVALID", "学号/邮箱或密码不正确。")
    row = conn.execute(
        "SELECT password_hash FROM users WHERE id = ?", (user["id"],)
    ).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        raise ApiError(401, "AUTH_CREDENTIALS_INVALID", "学号/邮箱或密码不正确。")
    return user


def create_access_token(user: dict) -> tuple[str, str]:
    """签发访问令牌，返回 ``(token, 过期时间)``。"""
    settings = get_settings()
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(days=settings.jwt_expire_days)
    payload = {
        "sub": str(user["id"]),
        "role": user["role"],
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    expires_at_iso = expires_at.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return token, expires_at_iso


def decode_access_token(token: str) -> dict:
    """校验并解析访问令牌，失败时抛出 401。"""
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise ApiError(401, "AUTH_TOKEN_EXPIRED", "登录已过期，请重新登录。") from exc
    except jwt.InvalidTokenError as exc:
        raise ApiError(401, "AUTH_TOKEN_INVALID", "登录凭证无效，请重新登录。") from exc
