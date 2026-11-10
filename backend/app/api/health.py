"""健康检查接口。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.api.deps import get_db
from app.config import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse, summary="健康探针")
def healthz(conn: sqlite3.Connection = Depends(get_db)) -> HealthResponse:
    """无需认证；部署验收与容器健康检查使用。"""
    settings = get_settings()
    database = "ok"
    try:
        conn.execute("SELECT 1").fetchone()
    except sqlite3.Error:
        database = "error"
    return HealthResponse(
        status="ok" if database == "ok" else "degraded",
        version=settings.app_version,
        database=database,
    )
