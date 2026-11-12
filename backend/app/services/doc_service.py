"""文档能力函数（上传、解析、摘要、文档问答）。

本轮为骨架批次：实现PDF/Word/PPT的基础切片与状态写入，后续批次补充向量库、LLM问答与高级特性。
"""

from __future__ import annotations

import io
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.errors import ApiError

# --- 允许的文件类型 ---
ALLOWED_MIME_TYPES = (
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
)
ALLOWED_SUFFIXES = (".pdf", ".docx", ".pptx")
MAX_UPLOAD_BYTES = 30 * 1024 * 1024  # 30MB

def format_size(limit: int) -> str:
    """把字节上限格式化为用户可读文案。"""
    if limit >= 1024 * 1024:
        return f"{limit // (1024 * 1024)}MB"
    return f"{limit}B"

# --- 解析器 -------------------------------------------------------

def parse_pdf_bytes(content: bytes) -> dict:
    """用 pypdf 解析 PDF 字节流。

    返回：
        {
            "pages": int,                         页数
            "texts": list[str],                   每页提取的原文本（可能为空）
            "has_images": bool,   是否检测到非空文本页（有文本即视为无图片问题）
        }
    """

    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as e:
        raise ApiError(400, "DOCUMENT_PARSE_ERROR", f"PDF 解析失败：{e}") from e

    texts: list[str] = []
    has_content = False
    for page in reader.pages:
        try:
            t = page.extract_text()
        except Exception:
            t = None
        texts.append(t if t else "")
        if t and t.strip():
            has_content = True

    return {
        "pages": len(reader.pages),
        "texts": texts,
        "has_images": not has_content,
    }

def parse_docx_bytes(content: bytes) -> dict:
    """用 python-docx 解析 Word 字节流。

    返回：
        {
            "pages": int,                         粗略等同为段落节数
            "texts": list[str],                   每段/标题的文本
            "has_images": bool,                   Word 文档通常无此概念，始为 False
        }
    """

    from docx import Document

    try:
        doc = Document(io.BytesIO(content))
    except Exception as e:
        raise ApiError(400, "DOCUMENT_PARSE_ERROR", f"Word 解析失败：{e}") from e

    texts: list[str] = []
    for p in doc.paragraphs:
        texts.append(p.text)

    return {
        "pages": len(doc.paragraphs),
        "texts": texts,
        "has_images": False,
    }

def parse_pptx_bytes(content: bytes) -> dict:
    """用 python-pptx 解析 PPT 字节流。

    返回：
        {
            "pages": int,                         slide 页数
            "texts": list[str],                 每页对应的首行提取文本
            "has_images": bool                    是否检测到图形/多媒体
        }
    """

    from pptx import Presentation

    try:
        prs = Presentation(io.BytesIO(content))
    except Exception as e:
        raise ApiError(400, "DOCUMENT_PARSE_ERROR", f"PPT 解析失败：{e}") from e

    texts: list[str] = []
    has_images = False
    for slide in prs.slides:
        slide_text_parts = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    for run in para.runs:
                        if run.text.strip():
                            slide_text_parts.append(run.text)
                            break
            if shape.shape_type.name in ("PICTURE", "GROUP"):
                has_images = True
        if slide_text_parts:
            texts.append(" ".join(slide_text_parts[:3]))
        else:
            texts.append("")

    return {
        "pages": len(prs.slides),
        "texts": texts,
        "has_images": has_images,
    }

# --- 内部：写入 DB -------------------------------------------------------


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def _write_document_meta(
    conn: sqlite3.Connection,
    user_id: int,
    filename: str,
    mime: str,
    status: str,
    size: int,
    summary: str | None = None,
    outline: list | None = None,
) -> int:
    """把文档元数据写入 sqlite，返回 document_id。"""
    now = _utc_now()
    outline_json = json.dumps(outline or [], ensure_ascii=False)
    conn.execute(
        """INSERT INTO documents
           (user_id, filename, mime, size, status, summary, outline, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, filename, mime, size, status, summary, outline_json, now, now),
    )
    cursor = conn.execute("SELECT last_insert_rowid()")
    return int(cursor.fetchone()[0])

# --- 公开函数 -------------------------------------------------------

def list_documents(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的文档（仅本人可见）。"""
    cursor = conn.execute(
        "SELECT id, filename, mime, status, created_at, summary FROM documents WHERE user_id = ?",
        (user_id,),
    )
    rows = cursor.fetchall()
    return [
        {
            "document_id": row[0],
            "filename": row[1],
            "mime": row[2],
            "status": row[3],
            "created_at": row[4],
            "summary": row[5],
        }
        for row in rows
    ]

def upload_document(
    conn: sqlite3.Connection,
    user_id: int,
    filename: str,
    mime: str,
    content: bytes,
) -> dict:
    """上传单个文档。

    后续批次实现：
    - 类型与大小强校验（已在 api/documents.py 的 _check_file_type/_read_limited 中完成）
    - 解析成功后写入 status=ready 与 summary/outline
    - 解析失败写入 status=failed 与用户可懂的失败原因（如扫描版/加密文件暂不支持）
    """
    # 1. 类型/大小在 API 层已校验（413 / 400），此处假符合条件

    # 2. 解析内容
    suffix = Path(filename.lower()).suffix
    if suffix == ".pdf":
        parsed = parse_pdf_bytes(content)
    elif suffix == ".docx":
        parsed = parse_docx_bytes(content)
    elif suffix == ".pptx":
        parsed = parse_pptx_bytes(content)
    else:
        raise ApiError(400, "DOCUMENT_TYPE_UNSUPPORTED", "仅支持 PDF/Word/PPT 文件。")

    # 3. 生成基础摘要（仅首页前 200 字符，作占位）
    first_text = " ".join([t for t in parsed["texts"] if t])
    summary = (first_text[:200] + "...") if first_text else None

    # 4. 写入 DB
    # Get size from content
    size = len(content)
    document_id = _write_document_meta(
        conn, user_id, filename, mime, "ready", size=size, summary=summary, outline=[]
    )

    return {
        "document_id": document_id,
        "filename": filename,
        "mime": mime,
        "status": "ready",
        "pages": parsed["pages"],
        "summary": summary,
    }

def get_document(conn: sqlite3.Connection, user_id: int, document_id: int) -> dict:
    """读取文档详情（含状态与失败原因）。"""
    cursor = conn.execute(
        "SELECT id, filename, mime, status, summary, outline, created_at"
        " FROM documents WHERE id = ? AND user_id = ?",
        (document_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        raise ApiError(404, "DOCUMENT_NOT_FOUND", "文档不存在或无权访问")
    return {
        "document_id": row[0],
        "filename": row[1],
        "mime": row[2],
        "status": row[3],
        "summary": row[4],
        "outline": row[5],
        "created_at": row[6],
    }

def get_document_summary(conn: sqlite3.Connection, user_id: int, document_id: int) -> dict:
    """读取文档摘要与提纲。"""
    doc = get_document(conn, user_id, document_id)  # 复用 get_document 校验权限
    return {
        "document_id": doc["document_id"],
        "summary": doc["summary"] or "",
        "outline": doc["outline"] or [],
    }

def export_document_summary(conn: sqlite3.Connection, user_id: int, document_id: int) -> str:
    """导出 Markdown 格式的摘要文本。"""
    summary = get_document_summary(conn, user_id, document_id)["summary"]
    if not summary:
        return "该文档尚无摘要内容。"
    lines = ["# 摘要", "", summary]
    return "\n".join(lines)

def ask_document(
    conn: sqlite3.Connection,
    user_id: int,
    document_id: int,
    question: str,
) -> dict:
    """针对文档提问。

    后续批次实现：
    - 响应契约与 ``/qa/ask`` 一致，sources 强制包含
      {kind: 'chunk', page, section_title}
    - 超出文档内容的问题走 refusal
    """
    # --- 占位：当前仅返回提示，后续批次接入向量检索 + LLM ---
    return {
        "answer": "文档问答功能尚未实现，请等待后续批次开发。",
        "sources": [],
        "refusal": None,
    }