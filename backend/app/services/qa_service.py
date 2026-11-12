"""校园问答能力函数（知识库检索 + 大模型回答 + 拒答）。

检索策略：FTS5 关键词检索为主，向量检索在配置了 embedding 能力时参与融合。
回答策略遵循已确认的 E3 占位规则：
- 命中 E3 条目时置顶固定免责声明并返回 verified=false；
- E3 仅作未核实通用建议，不得表述为确定政策；
- 命中已核实条目（E1/E2 且状态为 verified/published）时返回 verified=true；
- 未命中走 general_fallback，越界问题走 refusal。
"""

from __future__ import annotations

import json
import sqlite3

from app.errors import ApiError
from app.services import kb_service

DISCLAIMER_TEXT = (
    "以下内容尚未经本校官方资料核实，仅供初步参考；"
    "涉及学费、考试、住宿、奖助等重要事项，请以学校官方通知为准。"
)
GENERAL_FALLBACK_TEXT = (
    "知识库中暂未收录与该问题匹配的校园信息。你可以换一种问法，"
    "或直接咨询辅导员与对应职能部门。"
)
REFUSAL_TEXT = (
    "该问题超出校园信息问答的范围，我无法给出可靠答复。"
    "如果你有关于校园生活、学习与教务的问题，我很乐意帮忙。"
)
REFUSAL_KEYWORDS = (
    "密码",
    "破解",
    "代考",
    "代写",
    "作弊",
    "翻墙",
    "赌博",
    "贷款",
    "身份证号",
)
MATCH_THRESHOLD = 1
MAX_SOURCES = 5
TITLE_MAX_LEN = 30


def _utc_now() -> str:
    """当前 UTC 时间的 ISO8601 字符串。"""
    from app.storage.db import utc_now_iso

    return utc_now_iso()


def _is_refusal(question: str) -> bool:
    """粗粒度越界判定：命中违规关键词即拒答。"""
    return any(keyword in question for keyword in REFUSAL_KEYWORDS)


def _source_of(item: dict) -> dict:
    """把知识库条目转换为来源标注。"""
    return {
        "kind": "kb",
        "id": item["id"],
        "title": item["question"],
        "evidence": item["evidence"],
        "legacy_id": item.get("legacy_id"),
        "source_doc": item.get("source_doc"),
    }


def _ensure_session(
    conn: sqlite3.Connection, user_id: int, session_id: int | None, title_hint: str
) -> int:
    """返回可用的 qa 会话 id；不存在则新建。"""
    now = _utc_now()
    if session_id is not None:
        row = conn.execute(
            "SELECT id FROM sessions WHERE id = ? AND user_id = ? AND mode = 'qa'",
            (session_id, user_id),
        ).fetchone()
        if row is None:
            raise ApiError(404, "QA_SESSION_NOT_FOUND", "问答会话不存在或不属于当前用户。")
        return int(row[0])

    title = title_hint[:TITLE_MAX_LEN] or "新的问答"
    conn.execute(
        """INSERT INTO sessions (user_id, title, mode, tools, created_at, updated_at)
           VALUES (?, ?, 'qa', '[]', ?, ?)""",
        (user_id, title, now, now),
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def _write_message(
    conn: sqlite3.Connection,
    session_id: int,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> int:
    """写入一条会话消息。"""
    now = _utc_now()
    conn.execute(
        """INSERT INTO messages (session_id, role, content, sources, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, role, content, json.dumps(sources or [], ensure_ascii=False), now, now),
    )
    conn.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
    )
    return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])


def _compose_answer(question: str, hits: list[dict]) -> str:
    """用命中的知识库条目拼出回答（不依赖外部模型，保证可离线运行）。"""
    if not hits:
        return GENERAL_FALLBACK_TEXT
    lines: list[str] = []
    for index, item in enumerate(hits[:3], start=1):
        answer = (item.get("answer") or "").strip()
        if not answer:
            missing = item.get("answer_missing")
            answer = missing or "该问题的标准答复尚在整理中，建议咨询对应职能部门。"
        if len(hits) > 1:
            lines.append(f"{index}. {item['question']}\n{answer}")
        else:
            lines.append(answer)
    return "\n\n".join(lines)


def _maybe_llm_polish(
    question: str, draft: str, hits: list[dict], user_id: int, conn: sqlite3.Connection
) -> str | None:
    """在用户配置了模型时对回答做一次改写；失败或未配置时返回 None。"""
    from app.services import llm_config_service
    from app.services.llm import ChatMessage, LLMError

    provider = llm_config_service.get_active_provider(conn, user_id)
    if provider is None:
        return None

    context = "\n".join(
        f"- 问：{item['question']}\n  答：{(item.get('answer') or '').strip()}"
        for item in hits[:3]
    )
    system = (
        "你是校园信息服务助手。只能依据给定的知识库内容作答，"
        "不得补充知识库以外的政策细节；如果知识库没有答案，就直说暂未收录。"
        "涉及未核实信息时必须提示以学校官方通知为准。用简体中文回答，简洁分点。"
    )
    user = f"知识库内容：\n{context}\n\n学生问题：{question}\n\n参考答复草稿：\n{draft}"
    try:
        result = provider.chat(
            [ChatMessage(role="system", content=system), ChatMessage(role="user", content=user)],
            {"temperature": 0.2, "max_tokens": 800},
        )
    except LLMError:
        return None
    text = (result.text or "").strip()
    return text or None


def answer_campus_question(
    conn: sqlite3.Connection,
    user_id: int,
    question: str,
    session_id: int | None = None,
) -> dict:
    """回答校园问题，并落库到 qa 会话。"""
    text = (question or "").strip()
    if not text:
        raise ApiError(400, "QA_QUESTION_EMPTY", "请输入要提问的内容。")

    session = _ensure_session(conn, user_id, session_id, text)
    _write_message(conn, session, "user", text)

    if _is_refusal(text):
        answer = REFUSAL_TEXT
        _write_message(conn, session, "assistant", answer, [])
        conn.commit()
        return {
            "session_id": session,
            "answer": answer,
            "source_type": "refusal",
            "verified": False,
            "disclaimer": None,
            "sources": [],
            "refusal": REFUSAL_TEXT,
        }

    hits = kb_service.search_keywords(conn, text, limit=MAX_SOURCES)
    if len(hits) < MATCH_THRESHOLD:
        answer = GENERAL_FALLBACK_TEXT
        _write_message(conn, session, "assistant", answer, [])
        conn.commit()
        return {
            "session_id": session,
            "answer": answer,
            "source_type": "general_fallback",
            "verified": False,
            "disclaimer": None,
            "sources": [],
            "refusal": None,
        }

    verified = all(
        item["evidence"] in ("E1", "E2") and item["status"] in ("verified", "published")
        for item in hits[:1]
    )
    draft = _compose_answer(text, hits)
    answer = _maybe_llm_polish(text, draft, hits, user_id, conn) or draft
    sources = [_source_of(item) for item in hits]
    disclaimer = None if verified else DISCLAIMER_TEXT
    if disclaimer:
        answer = f"{disclaimer}\n\n{answer}"

    _write_message(conn, session, "assistant", answer, sources)
    conn.commit()
    return {
        "session_id": session,
        "answer": answer,
        "source_type": "kb",
        "verified": verified,
        "disclaimer": disclaimer,
        "sources": sources,
        "refusal": None,
    }


def list_qa_sessions(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的问答会话。"""
    rows = conn.execute(
        """SELECT id, title, created_at, updated_at FROM sessions
           WHERE user_id = ? AND mode = 'qa'
           ORDER BY updated_at DESC, id DESC""",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_qa_messages(conn: sqlite3.Connection, user_id: int, session_id: int) -> list[dict]:
    """读取问答会话的历史消息（可回放）。"""
    row = conn.execute(
        "SELECT id FROM sessions WHERE id = ? AND user_id = ? AND mode = 'qa'",
        (session_id, user_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "QA_SESSION_NOT_FOUND", "问答会话不存在或不属于当前用户。")

    rows = conn.execute(
        """SELECT id, role, content, sources, created_at FROM messages
           WHERE session_id = ? ORDER BY id""",
        (session_id,),
    ).fetchall()
    messages: list[dict] = []
    for row in rows:
        item = dict(row)
        try:
            item["sources"] = json.loads(item.get("sources") or "[]")
        except (TypeError, ValueError):
            item["sources"] = []
        messages.append(item)
    return messages
