"""统一搜索能力函数（知识库 / 共享资料 / 我的资料三源）。

三源策略（按已确认的 E3 规则）：
- kb：只返回已核实（status=verified/published 且 evidence 为 E1/E2）的条目，
      E3 候选不出现在搜索结果中；
- shared：MVP 阶段留空占位，保留后续扩展接口；
- mine：当前用户的上传文档切片。
结果统一按相关度降序返回，并附分源计数。
"""

from __future__ import annotations

import sqlite3

from app.errors import ApiError
from app.services import kb_service

SCOPES = ("all", "kb", "shared", "mine")
ITEM_TYPES = ("faq", "doc", "slide")
MAX_PAGE_SIZE = 100
KB_SCAN_LIMIT = 50
CHUNK_SCAN_LIMIT = 50
SNIPPET_LEN = 120


def _snippet(text: str, query: str) -> str:
    """截取包含关键词的摘要片段。"""
    body = " ".join((text or "").split())
    if not body:
        return ""
    pos = body.find(query)
    if pos < 0:
        return body[:SNIPPET_LEN]
    start = max(0, pos - SNIPPET_LEN // 3)
    return body[start : start + SNIPPET_LEN]


def _search_kb(conn: sqlite3.Connection, query: str) -> list[dict]:
    """检索已核实知识库条目，按相关度降序。"""
    hits = kb_service.search_keywords(conn, query, limit=KB_SCAN_LIMIT)
    results: list[dict] = []
    for rank, item in enumerate(hits):
        if item["evidence"] not in ("E1", "E2"):
            continue
        if item["status"] not in ("verified", "published"):
            continue
        results.append(
            {
                "type": "faq",
                "source": "kb",
                "id": item["id"],
                "title": item["question"],
                "snippet": _snippet(item.get("answer") or "", query),
                "evidence": item["evidence"],
                "legacy_id": item.get("legacy_id"),
                "_score": KB_SCAN_LIMIT - rank,
            }
        )
    return results


def _search_shared(conn: sqlite3.Connection, query: str) -> list[dict]:
    """共享资料源在 MVP 阶段留空占位。"""
    return []


def _search_mine(conn: sqlite3.Connection, user_id: int, query: str) -> list[dict]:
    """在当前用户自己的文档切片中检索。"""
    text = query.strip()
    if not text:
        return []
    like = f"%{text}%"
    rows = conn.execute(
        """SELECT c.id, c.document_id, c.page, c.section_title, c.text, d.filename
           FROM chunks AS c
           JOIN documents AS d ON d.id = c.document_id
           WHERE d.user_id = ? AND (c.text LIKE ? OR d.filename LIKE ?)
           ORDER BY c.document_id, c.seq
           LIMIT ?""",
        (user_id, like, like, CHUNK_SCAN_LIMIT),
    ).fetchall()

    results: list[dict] = []
    for rank, row in enumerate(rows):
        results.append(
            {
                "type": "doc",
                "source": "mine",
                "id": row["document_id"],
                "chunk_id": row["id"],
                "title": row["filename"],
                "page": row["page"],
                "section_title": row["section_title"],
                "snippet": _snippet(row["text"], text),
                "_score": CHUNK_SCAN_LIMIT - rank,
            }
        )
    return results


def unified_search(
    conn: sqlite3.Connection,
    user_id: int,
    query: str,
    scope: str = "all",
    item_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """三源统一检索。"""
    text = (query or "").strip()
    if not text:
        raise ApiError(400, "SEARCH_QUERY_EMPTY", "请输入检索关键词。")
    if scope not in SCOPES:
        raise ApiError(
            400, "SEARCH_SCOPE_INVALID", f"scope 取值不合法，可选值：{'、'.join(SCOPES)}。"
        )
    if item_type is not None and item_type not in ITEM_TYPES:
        raise ApiError(
            400,
            "SEARCH_TYPE_INVALID",
            f"type 取值不合法，可选值：{'、'.join(ITEM_TYPES)}。",
        )

    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)

    groups: dict[str, list[dict]] = {"kb": [], "shared": [], "mine": []}
    if scope in ("all", "kb"):
        groups["kb"] = _search_kb(conn, text)
    if scope in ("all", "shared"):
        groups["shared"] = _search_shared(conn, text)
    if scope in ("all", "mine"):
        groups["mine"] = _search_mine(conn, user_id, text)

    counts = {name: len(items) for name, items in groups.items()}

    merged: list[dict] = []
    for name in ("kb", "mine", "shared"):
        merged.extend(groups[name])
    if item_type is not None:
        merged = [item for item in merged if item["type"] == item_type]
    merged.sort(key=lambda item: item.get("_score", 0), reverse=True)

    total = len(merged)
    start = (page - 1) * page_size
    window = merged[start : start + page_size]
    for item in window:
        item.pop("_score", None)

    return {
        "query": text,
        "scope": scope,
        "type": item_type,
        "total": total,
        "counts": counts,
        "page": page,
        "page_size": page_size,
        "results": window,
    }
