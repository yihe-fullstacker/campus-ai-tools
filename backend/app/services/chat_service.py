"""学习助手能力函数（多轮对话 + 模板）。

本轮为骨架批次：仅固定模块边界与函数签名，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from app.services import ServiceNotImplemented

TEMPLATES = ("free", "plan", "concept", "hint")


def send_chat_message(
    conn: sqlite3.Connection,
    user_id: int,
    session_id: int,
    content: str,
    template: str | None = None,
) -> dict:
    """发送一条助手消息。

    后续批次需实现：``template`` 取值为 free/plan/concept/hint，分别对应自由问答、
    复习计划、概念解释与思路点拨；历史消息需可回放。
    """
    raise ServiceNotImplemented("学习助手模块将在后续批次实现")


def list_chat_sessions(conn: sqlite3.Connection, user_id: int) -> list[dict]:
    """列出当前用户的助手会话（mode=chat）。"""
    raise ServiceNotImplemented("学习助手模块将在后续批次实现")


def get_chat_messages(conn: sqlite3.Connection, user_id: int, session_id: int) -> list[dict]:
    """读取指定助手会话的历史消息。"""
    raise ServiceNotImplemented("学习助手模块将在后续批次实现")
