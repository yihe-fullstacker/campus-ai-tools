"""学习助手能力函数（多轮对话 + 模板）。

模板取值：
- free：自由问答
- plan：复习计划
- concept：概念解释
- hint：思路点拨（只给方向不给答案）

未配置 LLM 时退化为本地模板回答，保证功能可用且不静默失败。
"""

from __future__ import annotations

import json
import sqlite3

from app.errors import ApiError

TEMPLATES = ("free", "plan", "concept", "hint")
HISTORY_LIMIT = 20
TITLE_MAX_LEN = 30

TEMPLATE_PROMPTS = {
    "free": "你是一位耐心的学习助手，用简体中文回答问题，条理清晰、通俗易懂。",
    "plan": (
        "你是复习计划助手。根据学生给出的科目、时间与目标，"
        "输出一份按天或按周排列的复习计划，标注重点与检查点。"
    ),
    "concept": (
        "你是概念讲解助手。先用一句话给出定义，再解释关键要点，最后给一个贴近校园生活的例子。"
    ),
    "hint": (
        "你是思路点拨助手。只给出解题方向与关键提示，不直接给出最终答案，"
        "引导学生自己完成推导。"
    ),
}

OFFLINE_TEMPLATE_TEXTS = {
    "plan": (
        "当前学习助手未接入大模型，无法生成个性化复习计划。"
        "建议按「每天 2 个科目 × 45 分钟 + 15 分钟回顾」的节奏自行排布，"
        "并在每周末留出一次整体自测。"
    ),
    "concept": (
        "当前学习助手未接入大模型，无法生成概念讲解。"
        "可以先在教材或课程资料中定位该概念的定义句，再整理出「是什么、为什么、怎么用」三行笔记。"
    ),
    "hint": (
        "当前学习助手未接入大模型，无法生成个性化提示。"
        "建议先把题目已知条件和自己卡住的那一步分别写下来，通常问题就出在两者之间的连接环节。"
    ),
    "free": "当前学习助手尚未接入大模型服务，暂时无法自由问答。请联系管理员配置模型后重试。",
}


def _utc_now() -> str:
    """当前 UTC 时间的 ISO8601 字符串。"""
    from app.storage.db import utc_now_iso

    return utc_now_iso()


def _normalize_template(template: str | None) -> str:
    """校验并归一化模板取值。"""
    value = (template or "free").strip().lower()
    if value not in TEMPLATES:
        raise ApiError(
            400,
            "CHAT_TEMPLATE_INVALID",
            f"template 取值不合法，可选值：{'、'.join(TEMPLATES)}。",
        )
    return value


def _get_session(conn: sqlite3.Connection, user_id: int, session_id: int) -> sqlite3.Row:
    """取出属于当前用户的 chat 会话；不存在时抛 404。"""
    row = conn.execute(
        "SELECT * FROM sessions WHERE id = ? AND user_id = ? AND mode = 'chat'",
        (session_id, user_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "CHAT_SESSION_NOT_FOUND", "助手会话不存在或不属于当前用户。")
    return row


def create_chat_session(
    conn: sqlite3.Connection,
    user_id: int,
    title: str | None = None,
) -> dict:
    """新建一个助手会话（mode=chat，tools 恒为空）。"""
    now = _utc_now()
    clean_title = (title or "").strip()[:TITLE_MAX_LEN] or "新的学习对话"
    conn.execute(
        """INSERT INTO sessions (user_id, title, mode, tools, created_at, updated_at)
           VALUES (?, ?, 'chat', '[]', ?, ?)""",
        (user_id, clean_title, now, now),
    )
    session_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    conn.commit()
    return {"id": session_id, "title": clean_title, "created_at": now, "updated_at": now}


def _history(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    """读取最近若干条历史消息。"""
    rows = conn.execute(
        """SELECT role, content FROM messages
           WHERE session_id = ? ORDER BY id DESC LIMIT ?""",
        (session_id, HISTORY_LIMIT),
    ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def _reply(
    template: str, history: list[dict], content: str, user_id: int, conn: sqlite3.Connection
) -> tuple[str, str]:
    """生成助手回复，返回 (正文, 使用的引擎：llm/offline)。"""
    from app.services import llm_config_service
    from app.services.llm import ChatMessage, LLMError

    provider = llm_config_service.get_active_provider(conn, user_id)
    if provider is None:
        return OFFLINE_TEMPLATE_TEXTS[template], "offline"

    messages = [ChatMessage(role="system", content=TEMPLATE_PROMPTS[template])]
    for item in history:
        messages.append(ChatMessage(role=item["role"], content=item["content"]))
    messages.append(ChatMessage(role="user", content=content))
    try:
        result = provider.chat(messages, {"temperature": 0.4, "max_tokens": 1200})
    except LLMError:
        return OFFLINE_TEMPLATE_TEXTS[template], "offline"
    text = (result.text or "").strip()
    if not text:
        return OFFLINE_TEMPLATE_TEXTS[template], "offline"
    return text, "llm"


def send_chat_message(
    conn: sqlite3.Connection,
    user_id: int,
    session_id: int,
    content: str,
    template: str | None = None,
) -> dict:
    """发送一条助手消息；历史消息需可回放。"""
    text = (content or "").strip()
    if not text:
        raise ApiError(400, "CHAT_CONTENT_EMPTY", "请输入消息内容。")
    chosen = _normalize_template(template)

    session = _get_session(conn, user_id, session_id)
    history = _history(conn, session_id)
    now = _utc_now()

    conn.execute(
        """INSERT INTO messages (session_id, role, content, sources, created_at, updated_at)
           VALUES (?, 'user', ?, '[]', ?, ?)""",
        (session_id, text, now, now),
    )

    reply, engine = _reply(chosen, history, text, user_id, conn)

    conn.execute(
        """INSERT INTO messages (session_id, role, content, sources, created_at, updated_at)
           VALUES (?, 'assistant', ?, '[]', ?, ?)""",
        (session_id, reply, now, now),
    )

    # 会话标题为空或仍为默认值且这是首条消息时，用首条消息做标题
    count = int(
        conn.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
    )
    if count <= 2 and (not session["title"] or session["title"] in ("新的学习对话", "")):
        conn.execute(
            "UPDATE sessions SET title = ? WHERE id = ?",
            (text[:TITLE_MAX_LEN], session_id),
        )
    conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id))
    conn.commit()

    return {
        "session_id": session_id,
        "template": chosen,
        "engine": engine,
        "reply": reply,
        "created_at": now,
    }


def list_chat_sessions(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的助手会话（mode=chat）。"""
    rows = conn.execute(
        """SELECT id, title, created_at, updated_at FROM sessions
           WHERE user_id = ? AND mode = 'chat'
           ORDER BY updated_at DESC, id DESC""",
        (user_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def get_chat_messages(conn: sqlite3.Connection, user_id: int, session_id: int) -> list[dict]:
    """读取指定助手会话的历史消息。"""
    _get_session(conn, user_id, session_id)
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
