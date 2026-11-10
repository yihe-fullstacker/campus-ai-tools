"""知识库管理能力函数（唯一写入入口）。

一切知识库写入都必须经过本模块的 ``ingest_items``，便于后续挂载
"自动从教务通知更新知识库" 的 Agent。
"""

from __future__ import annotations

import sqlite3

from app.services import ServiceNotImplemented

KB_STATUSES = ("candidate", "verified", "published", "retired")


def ingest_items(conn: sqlite3.Connection, items: list[dict]) -> dict:
    """批量写入知识库条目（唯一写入入口）。

    后续批次需实现：语料表 v0 导入时统一写为 status=candidate、evidence=E3，
    并写入 legacy_id 便于与语料库原 id 对应。
    """
    raise ServiceNotImplemented("知识库模块将在后续批次实现")


def list_items(
    conn: sqlite3.Connection,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """列出知识库条目，可按状态筛选。"""
    raise ServiceNotImplemented("知识库模块将在后续批次实现")


def create_item(conn: sqlite3.Connection, payload: dict) -> dict:
    """录入一条知识库条目。"""
    raise ServiceNotImplemented("知识库模块将在后续批次实现")


def update_item(conn: sqlite3.Connection, item_id: int, payload: dict) -> dict:
    """修改条目内容，或升级证据等级与状态（E3→E2→E1 人工触发）。"""
    raise ServiceNotImplemented("知识库模块将在后续批次实现")


def retire_item(conn: sqlite3.Connection, item_id: int) -> dict:
    """下架条目（幻觉或文件失效时）。"""
    raise ServiceNotImplemented("知识库模块将在后续批次实现")
