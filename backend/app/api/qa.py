"""校园问答接口。

本轮为骨架批次：接口路径与鉴权要求按技术方案 §3.2 固定，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db, module_not_implemented
from app.schemas.modules import QaAskRequest
from app.services import ServiceNotImplemented, qa_service

router = APIRouter(prefix="/qa", tags=["qa"])


@router.get("/sessions", summary="我的问答会话列表")
def list_sessions(
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    """列出当前用户的问答会话（mode=qa）。"""
    try:
        return qa_service.list_qa_sessions(conn, user["id"])
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc


@router.post("/ask", summary="提问")
def ask(
    payload: QaAskRequest,
    conn: sqlite3.Connection = Depends(get_db),
    user: dict = Depends(get_current_user),
) -> dict:
    """提出校园问题；``session_id`` 为空时新建会话。

    响应契约见技术方案 §3.2：``source_type``、``verified``、``sources``、``refusal``。
    """
    try:
        return qa_service.answer_campus_question(
            conn, user["id"], payload.question, payload.session_id
        )
    except ServiceNotImplemented as exc:
        raise module_not_implemented(exc) from exc
