"""文档接口。

本轮为骨架批次：接口路径与鉴权要求按技术方案 §3.4 固定，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import Response

from app.api.deps import get_current_user, get_db, module_not_implemented
from app.schemas.modules import DocumentAskRequest
from app.services import ServiceNotImplemented, doc_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("", summary="我的文档列表")
def list_documents(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """列出当前用户的文档（仅本人可见）。"""
    try:
        return doc_service.list_documents(conn, user["id"])
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.post("", status_code=status.HTTP_201_CREATED, summary="上传文档")
async def upload_document(
    file: UploadFile = File(..., description="pdf/docx/pptx 文件，单个不超过 30MB"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """上传单个文档；类型与大小由服务端强校验（超限返回 413）。"""
    content = await file.read()
    try:
        return doc_service.upload_document(
            conn,
            user["id"],
            file.filename or "unnamed",
            file.content_type or "application/octet-stream",
            content,
        )
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.get("/{document_id}", summary="文档详情")
def get_document(
    document_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """返回文档状态与失败原因（如扫描版 PDF 暂不支持）。"""
    try:
        return doc_service.get_document(conn, user["id"], document_id)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.get("/{document_id}/summary", summary="文档摘要与提纲")
def get_summary(
    document_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """返回 ``{summary, outline, progress}``，前端进度条使用。"""
    try:
        return doc_service.get_document_summary(conn, user["id"], document_id)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.get("/{document_id}/summary/export", summary="导出摘要")
def export_summary(
    document_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> Response:
    """以 Markdown 文本下载摘要。"""
    try:
        content = doc_service.export_document_summary(conn, user["id"], document_id)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc
    return Response(
        content=content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="summary-{document_id}.md"'},
    )


@router.post("/{document_id}/ask", summary="文档问答")
def ask_document(
    document_id: int,
    payload: DocumentAskRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """针对文档提问；响应契约与 ``/qa/ask`` 一致。"""
    try:
        return doc_service.ask_document(conn, user["id"], document_id, payload.question)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc
