"""api 层公共依赖：数据库连接、当前用户与管理员校验。"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from fastapi import Depends, Header

from app.errors import ApiError
from app.services import ServiceNotImplemented, auth_service
from app.storage.db import connect


def get_db() -> Iterator[sqlite3.Connection]:
    """请求级数据库连接；请求结束自动关闭。"""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(
    conn: sqlite3.Connection = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> dict:
    """解析 Bearer 令牌并返回当前用户。"""
    if not authorization:
        raise ApiError(401, "AUTH_TOKEN_MISSING", "请先登录后再访问该资源。")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise ApiError(401, "AUTH_TOKEN_INVALID", "登录凭证格式不正确，请重新登录。")
    payload = auth_service.decode_access_token(token.strip())
    subject = payload.get("sub")
    if subject is None:
        raise ApiError(401, "AUTH_TOKEN_INVALID", "登录凭证无效，请重新登录。")
    user = auth_service.get_user_by_id(conn, int(subject))
    if user is None:
        raise ApiError(401, "AUTH_USER_NOT_FOUND", "账号不存在或已注销，请重新登录。")
    return user


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """仅限管理员访问。"""
    if user["role"] != "admin":
        raise ApiError(403, "FORBIDDEN_ADMIN_ONLY", "该接口仅限管理员使用。")
    return user


def module_not_implemented(exc: ServiceNotImplemented) -> ApiError:
    """把"模块尚未实现"转换为 501 响应。"""
    return ApiError(501, "MODULE_NOT_IMPLEMENTED", str(exc))
