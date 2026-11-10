"""学习助手接口。

本轮为骨架批次：接口路径与鉴权要求按技术方案 §3.3 固定，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db, module_not_implemented
from app.schemas.modules import ChatSendRequest
from app.services import ServiceNotImplemented, chat_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", summary="我的助手会话列表")
def list_sessions(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """列出当前用户的助手会话（mode=chat）。"""
    try:
        return chat_service.list_chat_sessions(conn, user["id"])
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.post("/sessions", status_code=201, summary="新建助手会话")
def create_session(
    title: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """新建一个助手会话。"""
    try:
        return chat_service.create_chat_session(conn, user["id"], title)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.get("/sessions/{session_id}/messages", summary="助手会话历史消息")
def list_messages(
    session_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """读取指定助手会话的历史消息（可回放）。"""
    try:
        return chat_service.get_chat_messages(conn, user["id"], session_id)
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.post("/sessions/{session_id}/messages", status_code=201, summary="发送助手消息")
def send_message(
    session_id: int,
    payload: ChatSendRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """发送一条消息；``template`` 取 free/plan/concept/hint。"""
    try:
        return chat_service.send_chat_message(
            conn, user["id"], session_id, payload.content, payload.template
        )
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc
