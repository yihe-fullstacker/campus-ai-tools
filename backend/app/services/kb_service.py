"""知识库管理能力函数（唯一写入入口）。

一切知识库写入都必须经过本模块，便于后续挂载"自动从教务通知更新知识库"的 Agent。

证据等级策略（已由用户确认）：
- E3 为未核实通用建议，命中时问答层置顶免责声明并返回 verified=false；
- E1/E2 为已核对本校官方资料，才有资格进入 verified/published 状态；
- 升级只允许人工触发（E3→E2→E1）。
"""

from __future__ import annotations

import json
import sqlite3

from app.errors import ApiError

KB_STATUSES = ("candidate", "verified", "published", "retired")
KB_EVIDENCE = ("E1", "E2", "E3")
VERIFIED_EVIDENCE = ("E1", "E2")
EDITABLE_FIELDS = (
    "question",
    "aliases",
    "answer",
    "answer_missing",
    "category",
    "subcategory",
    "priority",
    "evidence",
    "evidence_source",
    "status",
    "legacy_id",
    "source_doc",
)
JSON_FIELDS = ("aliases",)
MAX_PAGE_SIZE = 100


def _utc_now() -> str:
    """当前 UTC 时间的 ISO8601 字符串。"""
    from app.storage.db import utc_now_iso

    return utc_now_iso()


def _load_json(raw: str | None) -> list:
    """把库里的 JSON 文本还原为列表；异常文本按空列表处理。"""
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return value if isinstance(value, list) else []


def _dump_json(value: object) -> str:
    """把列表序列化为紧凑 JSON 文本。"""
    return json.dumps(value if isinstance(value, list) else [], ensure_ascii=False)


def _row_to_item(row: sqlite3.Row) -> dict:
    """把 kb_items 的一行转换为对外字典。"""
    item = dict(row)
    item["aliases"] = _load_json(item.get("aliases"))
    return item


def _get_row(conn: sqlite3.Connection, item_id: int) -> sqlite3.Row:
    """取出条目；不存在时抛 404。"""
    row = conn.execute("SELECT * FROM kb_items WHERE id = ?", (item_id,)).fetchone()
    if row is None:
        raise ApiError(404, "KB_ITEM_NOT_FOUND", "知识库条目不存在或已删除。")
    return row


def _validate_evidence_status(evidence: str, status: str) -> None:
    """已核实/已发布状态必须搭配 E1/E2 证据。"""
    if status in ("verified", "published") and evidence not in VERIFIED_EVIDENCE:
        raise ApiError(
            400,
            "KB_EVIDENCE_CONFLICT",
            "已核实或已发布的条目必须使用 E1/E2 官方证据；E3 只能停留在候选状态。",
        )


def _check_unique_legacy_id(
    conn: sqlite3.Connection, legacy_id: str | None, exclude_id: int | None = None
) -> None:
    """legacy_id 全局唯一。"""
    if not legacy_id:
        return
    sql = "SELECT id FROM kb_items WHERE legacy_id = ?"
    params: list[object] = [legacy_id]
    if exclude_id is not None:
        sql += " AND id <> ?"
        params.append(exclude_id)
    if conn.execute(sql, params).fetchone() is not None:
        raise ApiError(
            400,
            "KB_LEGACY_ID_DUPLICATED",
            f"语料编号 {legacy_id} 已存在，请勿重复导入。",
        )


def ingest_items(conn: sqlite3.Connection, items: list[dict]) -> dict:
    """批量写入知识库条目（唯一写入入口）。

    导入时统一按候选条目处理：缺省 status=candidate、evidence=E3，
    并写入 legacy_id 便于与语料库原 id 对应。已存在的 legacy_id 将被跳过而非报错，
    使导入动作可重复执行。
    """
    created: list[dict] = []
    skipped: list[str] = []
    now = _utc_now()

    for payload in items:
        legacy_id = payload.get("legacy_id")
        evidence = payload.get("evidence") or "E3"
        status = payload.get("status") or "candidate"
        if evidence not in KB_EVIDENCE or status not in KB_STATUSES:
            raise ApiError(400, "KB_FIELD_INVALID", "证据等级或状态取值不合法。")
        _validate_evidence_status(evidence, status)

        if legacy_id:
            existing = conn.execute(
                "SELECT id FROM kb_items WHERE legacy_id = ?", (legacy_id,)
            ).fetchone()
            if existing is not None:
                skipped.append(str(legacy_id))
                continue

        conn.execute(
            """INSERT INTO kb_items
               (question, aliases, answer, answer_missing, category, subcategory,
                priority, evidence, evidence_source, status, legacy_id, source_doc,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload["question"],
                _dump_json(payload.get("aliases") or []),
                payload.get("answer") or "",
                payload.get("answer_missing"),
                payload["category"],
                payload.get("subcategory"),
                payload.get("priority") or "P2",
                evidence,
                payload.get("evidence_source"),
                status,
                legacy_id,
                payload.get("source_doc"),
                now,
                now,
            ),
        )
        item_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        created.append({"id": item_id, "legacy_id": legacy_id, "question": payload["question"]})

    conn.commit()
    return {
        "created_count": len(created),
        "skipped_count": len(skipped),
        "skipped_legacy_ids": skipped,
        "created": created,
    }


def list_items(
    conn: sqlite3.Connection,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """列出知识库条目，可按状态筛选（分页）。"""
    if status is not None and status not in KB_STATUSES:
        raise ApiError(
            400,
            "KB_STATUS_INVALID",
            f"status 取值不合法，可选值：{'、'.join(KB_STATUSES)}。",
        )
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)

    where = ""
    params: list[object] = []
    if status is not None:
        where = " WHERE status = ?"
        params.append(status)

    total = int(
        conn.execute(f"SELECT COUNT(*) FROM kb_items{where}", params).fetchone()[0]
    )
    rows = conn.execute(
        f"SELECT * FROM kb_items{where} ORDER BY priority, id LIMIT ? OFFSET ?",
        [*params, page_size, (page - 1) * page_size],
    ).fetchall()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [_row_to_item(row) for row in rows],
    }


def create_item(conn: sqlite3.Connection, payload: dict) -> dict:
    """录入一条知识库条目。"""
    evidence = payload.get("evidence") or "E3"
    status = payload.get("status") or "candidate"
    _validate_evidence_status(evidence, status)
    _check_unique_legacy_id(conn, payload.get("legacy_id"))

    now = _utc_now()
    conn.execute(
        """INSERT INTO kb_items
           (question, aliases, answer, answer_missing, category, subcategory,
            priority, evidence, evidence_source, status, legacy_id, source_doc,
            created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            payload["question"],
            _dump_json(payload.get("aliases") or []),
            payload.get("answer") or "",
            payload.get("answer_missing"),
            payload["category"],
            payload.get("subcategory"),
            payload.get("priority") or "P2",
            evidence,
            payload.get("evidence_source"),
            status,
            payload.get("legacy_id"),
            payload.get("source_doc"),
            now,
            now,
        ),
    )
    item_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    return _row_to_item(_get_row(conn, item_id))


def update_item(conn: sqlite3.Connection, item_id: int, payload: dict) -> dict:
    """修改条目内容，或升级证据等级与状态（E3→E2→E1 人工触发）。"""
    row = _get_row(conn, item_id)

    updates = {k: v for k, v in payload.items() if k in EDITABLE_FIELDS and v is not None}
    if not updates:
        return _row_to_item(row)

    merged_evidence = updates.get("evidence", row["evidence"])
    merged_status = updates.get("status", row["status"])
    _validate_evidence_status(merged_evidence, merged_status)
    if "legacy_id" in updates:
        _check_unique_legacy_id(conn, updates["legacy_id"], exclude_id=item_id)

    if "aliases" in updates:
        updates["aliases"] = _dump_json(updates["aliases"])
    updates["updated_at"] = _utc_now()

    assignments = ", ".join(f"{field} = ?" for field in updates)
    conn.execute(
        f"UPDATE kb_items SET {assignments} WHERE id = ?",
        [*updates.values(), item_id],
    )
    conn.commit()
    return _row_to_item(_get_row(conn, item_id))


def retire_item(conn: sqlite3.Connection, item_id: int) -> dict:
    """下架条目（幻觉或文件失效时）。"""
    _get_row(conn, item_id)
    conn.execute(
        "UPDATE kb_items SET status = 'retired', updated_at = ? WHERE id = ?",
        (_utc_now(), item_id),
    )
    conn.commit()
    return _row_to_item(_get_row(conn, item_id))


def search_keywords(
    conn: sqlite3.Connection, query: str, limit: int = 10, published_only: bool = False
) -> list[dict]:
    """FTS5 关键词检索，返回按相关度排序的条目。

    中文语料使用 trigram 分词器，因此查询串需至少 3 个字符才能命中；
    不足 3 字符或 FTS 不可用时退化为 LIKE 匹配，保证结果不空。
    """
    text = (query or "").strip()
    if not text:
        return []

    rows: list[sqlite3.Row] = []
    if len(text) >= 3:
        try:
            rows = conn.execute(
                """SELECT k.*, bm25(kb_fts) AS score
                   FROM kb_fts
                   JOIN kb_items AS k ON k.id = kb_fts.rowid
                   WHERE kb_fts MATCH ?
                   ORDER BY score
                   LIMIT ?""",
                (_fts_query(text), limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []

    if not rows:
        like = f"%{text}%"
        rows = conn.execute(
            """SELECT * FROM kb_items
               WHERE question LIKE ? OR aliases LIKE ? OR answer LIKE ?
               ORDER BY priority, id
               LIMIT ?""",
            (like, like, like, limit),
        ).fetchall()

    items = [_row_to_item(row) for row in rows]
    if published_only:
        items = [i for i in items if i["status"] in ("verified", "published")]
    return items


def _fts_query(text: str) -> str:
    """把用户输入转成安全的 FTS5 查询串（按空白拆词并加引号）。"""
    parts = [p for p in text.replace('"', " ").split() if p]
    if not parts:
        return f'"{text}"'
    return " AND ".join(f'"{p}"' for p in parts)


def get_item(conn: sqlite3.Connection, item_id: int) -> dict:
    """读取单条知识库条目。"""
    return _row_to_item(_get_row(conn, item_id))
