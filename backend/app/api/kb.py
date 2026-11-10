"""知识库管理接口（仅管理员）。

本轮为骨架批次：接口路径与鉴权要求按技术方案 §3.6 固定，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import get_db, module_not_implemented, require_admin
from app.schemas.modules import KbItemCreateRequest, KbItemUpdateRequest
from app.services import ServiceNotImplemented, kb_service

router = APIRouter(prefix="/kb", tags=["kb"])


@router.get("/items", summary="列出知识库条目")
def list_items(
    status_filter: str | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin),
) -> dict:
    """列出条目，可按 status 筛选。"""
    try:
        return kb_service.list_items(conn, status_filter, page, page_size)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.post("/items", status_code=status.HTTP_201_CREATED, summary="录入知识库条目")
def create_item(
    payload: KbItemCreateRequest,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin),
) -> dict:
    """录入一条条目，走 T6 全字段。"""
    try:
        return kb_service.create_item(conn, payload.model_dump())
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.put("/items/{item_id}", summary="修改知识库条目")
def update_item(
    item_id: int,
    payload: KbItemUpdateRequest,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin),
) -> dict:
    """修改条目内容，或升级证据等级与状态（E3→E2→E1 人工触发）。"""
    try:
        return kb_service.update_item(conn, item_id, payload.model_dump(exclude_unset=True))
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.post("/items/{item_id}/retire", summary="下架知识库条目")
def retire_item(
    item_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin),
) -> dict:
    """下架条目（幻觉或文件失效时）。"""
    try:
        return kb_service.retire_item(conn, item_id)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.post("/import", summary="批量导入语料表")
def import_items(
    items: list[KbItemCreateRequest],
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_admin),
) -> dict:
    """批量导入语料表（v0 30 条直接导入为 status=candidate）。"""
    try:
        return kb_service.ingest_items(conn, [item.model_dump() for item in items])
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc
