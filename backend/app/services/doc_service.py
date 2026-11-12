"""文档能力函数（上传、解析、摘要、文档问答）。

实现流程：
1. 解析 PDF / Word / PPT，提取文本、页码与章节标题；
2. 原始文件按用户隔离落盘，文本切成片段写入 ``chunks``（供搜索与文档问答）；
3. 摘要优先调用用户当前生效的大模型生成，未配置或调用失败时退化为抽取式摘要；
4. 文档问答先在本文档切片中检索，再把命中片段交给大模型组织回答。

扫描版或加密文件提取不到文本时，文档状态标记为 ``failed`` 并给出可直接展示的失败原因，
不做"看起来成功、实际不可用"的静默降级。
"""

from __future__ import annotations

import io
import json
import re
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

# --- 切片与摘要参数 ---
CHUNK_MAX_CHARS = 1200
OUTLINE_MAX_ITEMS = 50
SUMMARY_FALLBACK_CHARS = 500
SUMMARY_INPUT_CHARS = 8000
ASK_CONTEXT_CHARS = 6000
ASK_CHUNK_LIMIT = 5
SNIPPET_CHARS = 180
KEYWORD_TERM_LIMIT = 40
CJK_STOPWORDS = frozenset(
    {
        "怎么",
        "如何",
        "什么",
        "请问",
        "是否",
        "可以",
        "需要",
        "我要",
        "我想",
        "一下",
        "这个",
        "那个",
        "哪些",
        "为什么",
        "多少",
        "以及",
        "还有",
    }
)

SCANNED_DOCUMENT_MESSAGE = (
    "未能从文件中提取到文本，可能是扫描版或加密文件，暂不支持全文解析。"
)
EMPTY_ANSWER_TEXT = "在本文档中没有检索到与该问题相关的内容，请换一种问法再试。"


def format_size(limit: int) -> str:
    """把字节上限格式化为用户可读文案。"""
    if limit >= 1024 * 1024:
        return f"{limit // (1024 * 1024)}MB"
    return f"{limit}B"


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_text(text: str) -> str:
    """压缩空白，便于摘要与检索。"""
    return re.sub(r"\s+", " ", text or "").strip()


# --- 解析器 -------------------------------------------------------


def parse_pdf_bytes(content: bytes) -> dict:
    """用 pypdf 解析 PDF 字节流，按页返回文本。"""
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(content))
    except Exception as exc:  # pypdf 对损坏文件抛出多种异常
        raise ApiError(400, "DOCUMENT_PARSE_ERROR", f"PDF 解析失败：{exc}") from exc

    texts: list[str] = []
    segments: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            page_text = page.extract_text()
        except Exception:
            page_text = None
        text = page_text or ""
        texts.append(text)
        if text.strip():
            segments.append({"page": index, "section_title": None, "text": text})

    return {
        "pages": len(reader.pages),
        "texts": texts,
        "segments": segments,
        "has_images": not segments,
    }


def parse_docx_bytes(content: bytes) -> dict:
    """用 python-docx 解析 Word 字节流，保留标题层级与段落顺序。"""
    from docx import Document

    try:
        doc = Document(io.BytesIO(content))
    except Exception as exc:
        raise ApiError(400, "DOCUMENT_PARSE_ERROR", f"Word 解析失败：{exc}") from exc

    texts: list[str] = []
    segments: list[dict] = []
    current_heading: str | None = None
    for paragraph in doc.paragraphs:
        text = paragraph.text or ""
        texts.append(text)
        if not text.strip():
            continue
        style_name = (getattr(paragraph.style, "name", "") or "").lower()
        if style_name.startswith("heading") or style_name.startswith("标题"):
            current_heading = text.strip()
        segments.append(
            {"page": None, "section_title": current_heading, "text": text}
        )

    return {
        "pages": len(doc.paragraphs) or 1,
        "texts": texts,
        "segments": segments,
        "has_images": False,
    }


def parse_pptx_bytes(content: bytes) -> dict:
    """用 python-pptx 解析 PPT 字节流，按幻灯片返回文本。"""
    from pptx import Presentation

    try:
        prs = Presentation(io.BytesIO(content))
    except Exception as exc:
        raise ApiError(400, "DOCUMENT_PARSE_ERROR", f"PPT 解析失败：{exc}") from exc

    texts: list[str] = []
    segments: list[dict] = []
    for index, slide in enumerate(prs.slides, start=1):
        slide_parts: list[str] = []
        for shape in slide.shapes:
            if not getattr(shape, "has_text_frame", False):
                continue
            for paragraph in shape.text_frame.paragraphs:
                line = "".join(run.text for run in paragraph.runs).strip()
                if line:
                    slide_parts.append(line)
        slide_text = "\n".join(slide_parts)
        texts.append(slide_text)
        if slide_text.strip():
            segments.append(
                {
                    "page": index,
                    "section_title": slide_parts[0] if slide_parts else None,
                    "text": slide_text,
                }
            )

    return {
        "pages": len(prs.slides),
        "texts": texts,
        "segments": segments,
        "has_images": not segments,
    }


def _parse_by_suffix(filename: str, content: bytes) -> dict:
    """按扩展名选择解析器。"""
    suffix = Path(filename.lower()).suffix
    if suffix == ".pdf":
        return parse_pdf_bytes(content)
    if suffix == ".docx":
        return parse_docx_bytes(content)
    if suffix == ".pptx":
        return parse_pptx_bytes(content)
    raise ApiError(400, "DOCUMENT_TYPE_UNSUPPORTED", "仅支持 PDF/Word/PPT 文件。")


# --- 切片 / 提纲 ----------------------------------------------------


def _build_chunks(segments: list[dict]) -> list[dict]:
    """把解析片段合并成适合检索的文本块。"""
    chunks: list[dict] = []
    buffer: list[str] = []
    buffer_chars = 0
    page: int | None = None
    section_title: str | None = None

    def flush() -> None:
        nonlocal buffer, buffer_chars, page, section_title
        text = "\n".join(part for part in buffer if part.strip()).strip()
        if text:
            chunks.append(
                {
                    "seq": len(chunks),
                    "page": page,
                    "section_title": section_title,
                    "text": text,
                }
            )
        buffer = []
        buffer_chars = 0
        page = None
        section_title = None

    for segment in segments:
        text = (segment.get("text") or "").strip()
        if not text:
            continue
        if not buffer:
            page = segment.get("page")
            section_title = segment.get("section_title")
        if buffer_chars and buffer_chars + len(text) > CHUNK_MAX_CHARS:
            flush()
            page = segment.get("page")
            section_title = segment.get("section_title")
        buffer.append(text)
        buffer_chars += len(text)
        if buffer_chars >= CHUNK_MAX_CHARS:
            flush()
    if buffer:
        flush()
    return chunks


def _build_outline(segments: list[dict], chunks: list[dict]) -> list[dict]:
    """从章节标题或每页首行生成提纲。"""
    outline: list[dict] = []
    seen: set[tuple[str, int | None]] = set()
    for segment in segments:
        title = (segment.get("section_title") or "").strip()
        if not title:
            first_line = (segment.get("text") or "").strip().splitlines()
            title = first_line[0].strip() if first_line else ""
        if not title:
            continue
        title = title[:80]
        key = (title, segment.get("page"))
        if key in seen:
            continue
        seen.add(key)
        outline.append({"title": title, "level": 1, "page": segment.get("page")})
        if len(outline) >= OUTLINE_MAX_ITEMS:
            break

    if outline:
        return outline
    return [
        {"title": chunk["text"].splitlines()[0][:80], "level": 1, "page": chunk["page"]}
        for chunk in chunks[:OUTLINE_MAX_ITEMS]
        if chunk["text"].strip()
    ]


# --- 摘要 -----------------------------------------------------------


def _fallback_summary(text: str) -> str:
    """抽取式摘要：保留开头要点，避免直接把整篇原文塞给用户。"""
    body = _normalize_text(text)
    if len(body) <= SUMMARY_FALLBACK_CHARS:
        return body
    return f"{body[:SUMMARY_FALLBACK_CHARS]}…"


def _summarize(
    conn: sqlite3.Connection,
    user_id: int,
    filename: str,
    text: str,
    outline: list[dict],
) -> str:
    """优先用大模型生成摘要；未配置模型或调用失败时退回抽取式摘要。"""
    fallback = _fallback_summary(text)
    if not fallback:
        return ""

    from app.services import llm_config_service
    from app.services.llm import ChatMessage, LLMError

    provider = llm_config_service.get_active_provider(conn, user_id)
    if provider is None:
        return fallback

    outline_text = "\n".join(
        f"- {item['title']}" + (f"（第 {item['page']} 页）" if item.get("page") else "")
        for item in outline[:30]
    )
    system = (
        "你是学习资料整理助手。请用简体中文为给定文档写一段 150 字以内的摘要，"
        "并根据文档结构列出 3–8 条提纲。只依据文档内容，不要编造。"
    )
    user = (
        f"文件名：{filename}\n"
        f"文档提纲（供参考）：\n{outline_text or '（无）'}\n\n"
        f"文档正文（可能被截断）：\n{text[:SUMMARY_INPUT_CHARS]}"
    )
    try:
        result = provider.chat(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            {"temperature": 0.2, "max_tokens": 700},
        )
    except LLMError:
        return fallback
    generated = (result.text or "").strip()
    return generated or fallback


# --- 内部：写入 DB ---------------------------------------------------


def _write_document_meta(
    conn: sqlite3.Connection,
    user_id: int,
    filename: str,
    mime: str,
    status: str,
    size: int,
    summary: str | None = None,
    outline: list | None = None,
    status_message: str | None = None,
    storage_path: str | None = None,
) -> int:
    """把文档元数据写入 sqlite，返回 document_id。"""
    now = _utc_now()
    outline_json = json.dumps(outline or [], ensure_ascii=False)
    cursor = conn.execute(
        """INSERT INTO documents
           (user_id, filename, mime, size, status, status_message, storage_path,
            summary, outline, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            filename,
            mime,
            size,
            status,
            status_message,
            storage_path,
            summary,
            outline_json,
            now,
            now,
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def _update_document(
    conn: sqlite3.Connection,
    document_id: int,
    *,
    status: str,
    status_message: str | None = None,
    summary: str | None = None,
    outline: list | None = None,
    storage_path: str | None = None,
) -> None:
    """更新文档解析结果。"""
    conn.execute(
        """UPDATE documents
           SET status = ?, status_message = ?, summary = ?, outline = ?,
               storage_path = COALESCE(?, storage_path), updated_at = ?
           WHERE id = ?""",
        (
            status,
            status_message,
            summary,
            json.dumps(outline or [], ensure_ascii=False),
            storage_path,
            _utc_now(),
            document_id,
        ),
    )
    conn.commit()


def _save_original(user_id: int, document_id: int, filename: str, content: bytes) -> str:
    """按用户隔离保存原始文件，返回相对数据目录的路径。"""
    from app.config import get_settings

    settings = get_settings()
    safe_name = Path(filename).name or "document"
    directory = settings.files_dir / str(user_id) / str(document_id)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / safe_name
    path.write_bytes(content)
    try:
        return path.relative_to(settings.data_dir).as_posix()
    except ValueError:
        return path.as_posix()


def _store_chunks(conn: sqlite3.Connection, document_id: int, chunks: list[dict]) -> None:
    """写入文本切片（FTS 触发器会自动同步）。"""
    if not chunks:
        return
    now = _utc_now()
    conn.executemany(
        """INSERT INTO chunks
           (document_id, seq, page, section_title, text, doc_vec_id, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                document_id,
                chunk["seq"],
                chunk["page"],
                chunk["section_title"],
                chunk["text"],
                f"d{document_id}_{chunk['seq']}",
                now,
                now,
            )
            for chunk in chunks
        ],
    )
    conn.commit()


# --- 公开函数 -------------------------------------------------------


def list_documents(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的文档（仅本人可见）。"""
    rows = conn.execute(
        """SELECT id, filename, mime, size, status, status_message, created_at, summary
           FROM documents WHERE user_id = ?
           ORDER BY id DESC""",
        (user_id,),
    ).fetchall()
    return [
        {
            "document_id": row["id"],
            "filename": row["filename"],
            "mime": row["mime"],
            "size": row["size"],
            "status": row["status"],
            "status_message": row["status_message"],
            "created_at": row["created_at"],
            "summary": row["summary"],
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
    """上传并解析一个文档。

    类型与大小由 API 层先行校验；解析失败（损坏、扫描版）时文档以 ``failed`` 状态入库，
    并返回可直接展示的失败原因。
    """
    try:
        parsed = _parse_by_suffix(filename, content)
        parse_error = None
    except ApiError as exc:
        parsed = {"pages": 0, "texts": [], "segments": [], "has_images": True}
        parse_error = exc.message

    document_id = _write_document_meta(
        conn, user_id, filename, mime, "parsing", size=len(content)
    )
    storage_path = _save_original(user_id, document_id, filename, content)

    if parse_error:
        _update_document(
            conn,
            document_id,
            status="failed",
            status_message=parse_error,
            storage_path=storage_path,
        )
        return {
            "document_id": document_id,
            "filename": filename,
            "mime": mime,
            "status": "failed",
            "status_message": parse_error,
            "pages": 0,
            "summary": None,
        }

    text = "\n".join(parsed["texts"])
    if not _normalize_text(text):
        _update_document(
            conn,
            document_id,
            status="failed",
            status_message=SCANNED_DOCUMENT_MESSAGE,
            storage_path=storage_path,
        )
        return {
            "document_id": document_id,
            "filename": filename,
            "mime": mime,
            "status": "failed",
            "status_message": SCANNED_DOCUMENT_MESSAGE,
            "pages": parsed["pages"],
            "summary": None,
        }

    chunks = _build_chunks(parsed["segments"])
    outline = _build_outline(parsed["segments"], chunks)
    summary = _summarize(conn, user_id, filename, text, outline)
    _store_chunks(conn, document_id, chunks)
    _update_document(
        conn,
        document_id,
        status="ready",
        summary=summary,
        outline=outline,
        storage_path=storage_path,
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
    row = conn.execute(
        """SELECT id, filename, mime, size, status, status_message, summary, outline,
                  storage_path, created_at, updated_at
           FROM documents WHERE id = ? AND user_id = ?""",
        (document_id, user_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "DOCUMENT_NOT_FOUND", "文档不存在或无权访问")
    try:
        outline = json.loads(row["outline"] or "[]")
    except (TypeError, ValueError):
        outline = []
    return {
        "document_id": row["id"],
        "filename": row["filename"],
        "mime": row["mime"],
        "size": row["size"],
        "status": row["status"],
        "status_message": row["status_message"],
        "summary": row["summary"],
        "outline": outline,
        "storage_path": row["storage_path"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_document_summary(conn: sqlite3.Connection, user_id: int, document_id: int) -> dict:
    """读取文档摘要、提纲与解析进度。"""
    doc = get_document(conn, user_id, document_id)
    progress = {"ready": 100, "failed": 0, "parsing": 50, "uploaded": 10}.get(
        doc["status"], 0
    )
    return {
        "document_id": doc["document_id"],
        "filename": doc["filename"],
        "status": doc["status"],
        "status_message": doc["status_message"],
        "summary": doc["summary"] or "",
        "outline": doc["outline"] or [],
        "progress": progress,
    }


def export_document_summary(conn: sqlite3.Connection, user_id: int, document_id: int) -> str:
    """导出 Markdown 格式的摘要与提纲。"""
    data = get_document_summary(conn, user_id, document_id)
    lines = [f"# {data['filename']}", ""]
    if data["status"] != "ready":
        lines.append(f"> 文档状态：{data['status']}")
        if data["status_message"]:
            lines.append(f"> {data['status_message']}")
        lines.append("")
    lines.extend(["## 摘要", "", data["summary"] or "该文档尚无摘要内容。", ""])
    if data["outline"]:
        lines.extend(["## 提纲", ""])
        for item in data["outline"]:
            page = f"（第 {item['page']} 页）" if item.get("page") else ""
            lines.append(f"- {item['title']}{page}")
    return "\n".join(lines)


# --- 文档问答 -------------------------------------------------------


def _snippet(text: str) -> str:
    """截取用于来源展示的片段。"""
    body = _normalize_text(text)
    return body[:SNIPPET_CHARS] + ("…" if len(body) > SNIPPET_CHARS else "")


def _fts_query(text: str) -> str:
    """把输入转成安全的 FTS5 查询串。"""
    parts = [part for part in text.replace('"', " ").split() if part]
    if not parts:
        return f'"{text}"'
    return " AND ".join(f'"{part}"' for part in parts)


def _keywords(question: str) -> list[str]:
    """从中文自然问句中抽取用于 LIKE 检索的关键词。

    FTS5 的 trigram 分词要求查询串至少 3 个字符，而中文问句里真正有区分度的
    往往是「缓考」「提前」这类两字词，因此在 FTS 未命中时用 2–3 字滑动窗口兜底。
    """
    cleaned = re.sub(r"[^\w一-鿿]+", " ", question)
    terms: set[str] = set()
    for piece in cleaned.split():
        if re.search(r"[一-鿿]", piece):
            if len(piece) <= 6:
                terms.add(piece)
            for size in (2, 3):
                for index in range(len(piece) - size + 1):
                    term = piece[index : index + size]
                    if term not in CJK_STOPWORDS:
                        terms.add(term)
        elif len(piece) >= 2:
            terms.add(piece.lower())
    ordered = sorted(terms, key=len, reverse=True)
    return ordered[:KEYWORD_TERM_LIMIT]


def _search_chunks(
    conn: sqlite3.Connection, document_id: int, question: str
) -> list[sqlite3.Row]:
    """在指定文档的切片中检索，FTS 未命中时用关键词 LIKE 兜底。"""
    text = question.strip()
    rows: list[sqlite3.Row] = []
    if len(text) >= 3:
        try:
            rows = conn.execute(
                """SELECT c.*, bm25(chunks_fts) AS score
                   FROM chunks_fts
                   JOIN chunks AS c ON c.id = chunks_fts.rowid
                   WHERE c.document_id = ? AND chunks_fts MATCH ?
                   ORDER BY score
                   LIMIT ?""",
                (document_id, _fts_query(text), ASK_CHUNK_LIMIT),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []
    if rows:
        return rows

    keywords = _keywords(text)
    if not keywords:
        return []
    where = " OR ".join("text LIKE ?" for _ in keywords)
    candidates = conn.execute(
        f"""SELECT * FROM chunks
            WHERE document_id = ? AND ({where})
            LIMIT 50""",
        [document_id, *[f"%{term}%" for term in keywords]],
    ).fetchall()
    if not candidates:
        return []

    scored = [
        (sum(1 for term in keywords if term in row["text"]), -int(row["seq"]), row)
        for row in candidates
    ]
    scored.sort(reverse=True)
    return [row for _, _, row in scored[:ASK_CHUNK_LIMIT]]



def _source_of(row: sqlite3.Row, filename: str) -> dict:
    """把切片转换为来源标注。"""
    return {
        "kind": "chunk",
        "doc_id": row["document_id"],
        "chunk_id": row["id"],
        "page": row["page"],
        "section_title": row["section_title"],
        "title": filename,
        "snippet": _snippet(row["text"]),
    }


def _answer_with_chunks(
    conn: sqlite3.Connection,
    user_id: int,
    filename: str,
    question: str,
    rows: list[sqlite3.Row],
) -> tuple[str, str]:
    """用检索到的切片回答，返回 (正文, 引擎)。"""
    context_parts: list[str] = []
    used = 0
    for row in rows:
        page = f"第 {row['page']} 页" if row["page"] else "正文"
        piece = f"[{page}] {row['text'].strip()}"
        if used + len(piece) > ASK_CONTEXT_CHARS:
            break
        context_parts.append(piece)
        used += len(piece)
    context = "\n\n".join(context_parts)

    from app.services import llm_config_service
    from app.services.llm import ChatMessage, LLMError

    provider = llm_config_service.get_active_provider(conn, user_id)
    if provider is not None:
        system = (
            "你是文档阅读助手。只能依据给出的文档片段回答，不得补充片段以外的信息；"
            "片段不足以回答时明确说明文档中没有相关内容。用简体中文回答，"
            "引用内容时标注页码，回答保持简洁。"
        )
        user = f"文档《{filename}》的相关片段：\n{context}\n\n学生问题：{question}"
        try:
            result = provider.chat(
                [
                    ChatMessage(role="system", content=system),
                    ChatMessage(role="user", content=user),
                ],
                {"temperature": 0.2, "max_tokens": 900},
            )
            answer = (result.text or "").strip()
            if answer:
                return answer, "llm"
        except LLMError:
            pass

    # 未配置模型或调用失败：直接给出命中的原文片段，保证功能可用
    lines = [
        f"以下是《{filename}》中与问题最相关的内容"
        + (f"（第 {row['page']} 页）" if row["page"] else "")
        + f"：\n{_snippet(row['text'])}"
        for row in rows[:3]
    ]
    return "\n\n".join(lines), "offline"


def ask_document(
    conn: sqlite3.Connection,
    user_id: int,
    document_id: int,
    question: str,
) -> dict:
    """针对文档提问；来源强制包含命中的切片。"""
    text = (question or "").strip()
    if not text:
        raise ApiError(400, "DOCUMENT_QUESTION_EMPTY", "请输入要针对文档提出的问题。")

    doc = get_document(conn, user_id, document_id)
    if doc["status"] != "ready":
        reason = doc["status_message"] or "文档尚未解析完成，暂时无法问答。"
        return {
            "answer": reason,
            "sources": [],
            "refusal": reason,
            "engine": "offline",
            "status": doc["status"],
        }

    rows = _search_chunks(conn, document_id, text)
    if not rows:
        return {
            "answer": EMPTY_ANSWER_TEXT,
            "sources": [],
            "refusal": EMPTY_ANSWER_TEXT,
            "engine": "offline",
            "status": "ready",
        }

    answer, engine = _answer_with_chunks(
        conn, user_id, doc["filename"], text, rows
    )
    return {
        "answer": answer,
        "sources": [_source_of(row, doc["filename"]) for row in rows],
        "refusal": None,
        "engine": engine,
        "status": "ready",
    }
