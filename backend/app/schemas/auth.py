"""账户与认证相关的请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """注册请求。"""

    identity: str = Field(min_length=3, max_length=64, description="学号或邮箱，注册时绑定一种")
    password: str = Field(min_length=8, max_length=72, description="密码，长度 8–72 字节")


class LoginRequest(BaseModel):
    """登录请求。"""

    identity: str = Field(min_length=1, max_length=64, description="学号或邮箱")
    password: str = Field(min_length=1, max_length=72, description="密码")


class UserResponse(BaseModel):
    """用户信息。"""

    id: int
    identity: str = Field(description="学号或邮箱")
    role: str = Field(description="student 或 admin")
    created_at: str


class TokenResponse(BaseModel):
    """登录/注册成功后的令牌响应。"""

    token: str = Field(description="JWT 访问令牌")
    token_type: str = Field(default="bearer")
    expires_at: str = Field(description="令牌过期时间（UTC ISO8601）")
    user: UserResponse
