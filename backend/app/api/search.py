"""统一搜索接口。

本轮为骨架批次：接口路径与参数按技术方案 §3.5 固定，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_user, get_db, module_not_implemented
from app.services import ServiceNotImplemented, search_service

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", summary="三源统一搜索")
def search(
    q: str = Query(min_length=1, max_length=200, description="检索关键词"),
    scope: str = Query(default="all", description="all/kb/shared/mine"),
    type: str | None = Query(default=None, description="faq/doc/slide"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """并行检索知识库、共享资料与我的资料三源。"""
    try:
        return search_service.unified_search(
            conn, user["id"], q, scope, type, page, page_size
        )
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc
