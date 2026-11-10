"""校园问答能力函数（知识库检索 + 大模型回答 + 拒答）。

本轮为骨架批次：仅固定模块边界与函数签名，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from app.services import ServiceNotImplemented


def answer_campus_question(
    conn: sqlite3.Connection,
    user_id: int,
    question: str,
    session_id: int | None = None,
) -> dict:
    """回答校园问题。

    后续批次需实现：知识库向量 top-k 与 FTS5 关键词混合检索；命中 E3 条目时置顶固定
    免责声明并返回 ``verified: false``；未命中走 ``general_fallback``；越界问题走 ``refusal``。
    """
    raise ServiceNotImplemented("校园问答模块将在后续批次实现")


def list_qa_sessions(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的问答会话。"""
    raise ServiceNotImplemented("校园问答模块将在后续批次实现")
