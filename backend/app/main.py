"""FastAPI 入口与路由装配。

约定：
- 业务接口统一挂载在 ``/api/v1`` 前缀下；``/healthz`` 同时在根路径与前缀下暴露，便于探针使用。
- 错误统一体为 ``{"code": "<机器码>", "message": "<面向用户的中文提示>"}``。
- 首次启动自动创建数据目录并执行 SQLite schema 迁移。
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import auth, chat, documents, health, kb, qa, search
from app.config import get_settings
from app.errors import ApiError
from app.storage.db import connect, migrate

logger = logging.getLogger(__name__)

DEFAULT_STATUS_MESSAGES = {
    400: "请求参数不合法，请检查后重试。",
    401: "请先登录后再访问该资源。",
    403: "没有权限执行该操作。",
    404: "请求的资源不存在。",
    405: "请求方法不被支持。",
    413: "上传内容超过限制。",
    429: "请求过于频繁，请稍后重试。",
}
STARLETTE_DEFAULT_DETAILS = {"Not Found", "Method Not Allowed"}


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """启动时准备数据目录并执行数据库迁移。"""
    settings = get_settings()
    settings.ensure_dirs()
    conn = connect()
    try:
        applied = migrate(conn)
    finally:
        conn.close()
    if applied:
        logger.info("已应用数据库迁移：%s", ", ".join(applied))
    if settings.uses_default_jwt_secret:
        logger.warning("正在使用开发兜底 JWT 密钥，生产环境请通过环境变量 JWT_SECRET 覆盖。")
    yield


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        logger.debug("请求参数校验失败：%s", exc.errors())
        return JSONResponse(
            status_code=400,
            content={"code": "REQUEST_INVALID", "message": "请求参数不合法，请检查后重试。"},
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else None
        message = DEFAULT_STATUS_MESSAGES.get(exc.status_code)
        if detail and detail not in STARLETTE_DEFAULT_DETAILS:
            message = detail
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": f"HTTP_{exc.status_code}",
                "message": message or "请求处理失败，请稍后重试。",
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("未预期的服务端异常", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"code": "INTERNAL_ERROR", "message": "服务出现异常，请稍后重试。"},
        )


def create_app() -> FastAPI:
    """组装 FastAPI 应用。"""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="校园综合 AI 平台后端：校园问答、学习助手、文档解析与统一搜索。",
        lifespan=lifespan,
    )
    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    prefix = settings.api_prefix
    app.include_router(health.router)
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(auth.users_router, prefix=prefix)
    app.include_router(qa.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(kb.router, prefix=prefix)

    _register_exception_handlers(app)
    return app


app = create_app()
