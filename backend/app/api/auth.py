"""账户与认证接口。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_current_user, get_db
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


def _token_response(user: dict) -> TokenResponse:
    token, expires_at = auth_service.create_access_token(user)
    return TokenResponse(token=token, expires_at=expires_at, user=UserResponse(**user))


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册账号",
)
def register(
    payload: RegisterRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> TokenResponse:
    """注册并直接返回访问令牌。"""
    user = auth_service.create_user(conn, payload.identity, payload.password)
    return _token_response(user)


@router.post("/login", response_model=TokenResponse, summary="登录")
def login(
    payload: LoginRequest,
    conn: sqlite3.Connection = Depends(get_db),
) -> TokenResponse:
    """校验账号密码并签发访问令牌。"""
    user = auth_service.authenticate(conn, payload.identity, payload.password)
    return _token_response(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="登出",
)
def logout() -> Response:
    """服务端无状态，登出由前端丢弃令牌完成。"""
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@users_router.get("/me", response_model=UserResponse, summary="当前用户信息")
def me(user: dict = Depends(get_current_user)) -> UserResponse:
    """返回当前登录用户的信息。"""
    return UserResponse(**user)
