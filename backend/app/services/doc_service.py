"""文档能力函数（上传、解析、摘要、文档问答）。

本轮为骨架批次：仅固定模块边界与函数签名，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from app.services import ServiceNotImplemented

ALLOWED_MIME_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
)
MAX_UPLOAD_BYTES = 30 * 1024 * 1024


def list_documents(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的文档（仅本人可见）。"""
    raise ServiceNotImplemented("文档模块将在后续批次实现")


def upload_document(
    conn: sqlite3.Connection,
    user_id: int,
    filename: str,
    mime: str,
    content: bytes,
) -> dict:
    """上传单个文档。

    后续批次需实现：类型与大小强校验（限 pdf/docx/pptx、≤30MB，超限返回 413）、
    解析成功后写入 status=ready 与 summary/outline，解析失败写入 status=failed 与
    用户可懂的失败原因（如扫描版/加密文件暂不支持）。
    """
    raise ServiceNotImplemented("文档模块将在后续批次实现")


def get_document(conn: sqlite3.Connection, user_id: int, document_id: int) -> dict:
    """读取文档详情（含状态与失败原因）。"""
    raise ServiceNotImplemented("文档模块将在后续批次实现")


def get_document_summary(conn: sqlite3.Connection, user_id: int, document_id: int) -> dict:
    """读取文档摘要与提纲。"""
    raise ServiceNotImplemented("文档模块将在后续批次实现")


def export_document_summary(conn: sqlite3.Connection, user_id: int, document_id: int) -> str:
    """导出 Markdown 格式的摘要文本。"""
    raise ServiceNotImplemented("文档模块将在后续批次实现")


def ask_document(
    conn: sqlite3.Connection,
    user_id: int,
    document_id: int,
    question: str,
) -> dict:
    """针对文档提问。

    后续批次需实现：响应契约与 ``/qa/ask`` 一致，sources 强制包含
    ``{kind: 'chunk', page, section_title}``；超出文档内容的问题走 refusal。
    """
    raise ServiceNotImplemented("文档模块将在后续批次实现")
