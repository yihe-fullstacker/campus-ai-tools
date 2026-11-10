"""文档接口。

本轮为骨架批次：接口路径与鉴权要求按技术方案 §3.4 固定，业务实现由后续批次填充。

上传在读取内容**之前**先做类型与大小校验：类型不支持返回 400，超限返回 413；
读取时按块进行并累计字节数，避免把超大文件整体读进内存。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from fastapi.responses import Response

from app.api.deps import get_current_user, get_db, module_not_implemented
from app.errors import ApiError
from app.schemas.modules import DocumentAskRequest
from app.services import ServiceNotImplemented, doc_service

router = APIRouter(prefix="/documents", tags=["documents"])

READ_CHUNK_BYTES = 1024 * 1024


def _check_declared_size(request: Request) -> None:
    """按 Content-Length 提前拦截超大请求。"""
    declared = request.headers.get("content-length")
    if not declared:
        return
    try:
        size = int(declared)
    except ValueError:
        return
    if size > doc_service.MAX_UPLOAD_BYTES:
        raise ApiError(
            413,
            "DOCUMENT_TOO_LARGE",
            "上传内容超过 "
            f"{doc_service.format_size(doc_service.MAX_UPLOAD_BYTES)} 上限，请压缩后重试。",
        )


def _check_file_type(content_type: str | None, filename: str | None) -> None:
    """只接受 pdf / docx / pptx。"""
    mime = (content_type or "").split(";")[0].strip().lower()
    suffix = Path(filename or "").suffix.lower()
    if mime not in doc_service.ALLOWED_MIME_TYPES:
        raise ApiError(
            400,
            "DOCUMENT_TYPE_UNSUPPORTED",
            "仅支持 PDF、Word（docx）、PPT（pptx）文件。",
        )
    if suffix and suffix not in doc_service.ALLOWED_SUFFIXES:
        raise ApiError(
            400,
            "DOCUMENT_TYPE_UNSUPPORTED",
            "仅支持 PDF、Word（docx）、PPT（pptx）文件。",
        )


async def _read_limited(file: UploadFile, limit: int) -> bytes:
    """分块读取文件，超过上限立即中断。"""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise ApiError(
                413,
                "DOCUMENT_TOO_LARGE",
                f"上传内容超过 {doc_service.format_size(limit)} 上限，请压缩后重试。",
            )
        chunks.append(chunk)
    return b"".join(chunks)


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
    request: Request,
    file: UploadFile = File(..., description="pdf/docx/pptx 文件，单个不超过 30MB"),
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """上传单个文档；类型与大小由服务端强校验（超限返回 413）。"""
    _check_declared_size(request)
    _check_file_type(file.content_type, file.filename)
    content = await _read_limited(file, doc_service.MAX_UPLOAD_BYTES)
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
