"""通用响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """统一错误响应体。"""

    code: str = Field(description="机器码，供前端分支判断")
    message: str = Field(description="面向用户的中文提示")


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str = Field(description="ok 表示服务与数据库均可用")
    version: str = Field(description="应用版本")
    database: str = Field(description="数据库状态：ok 或 error")
