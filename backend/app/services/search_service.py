"""统一搜索能力函数（知识库 / 共享资料 / 我的资料三源）。

本轮为骨架批次：仅固定模块边界与函数签名，业务实现由后续批次填充。
"""

from __future__ import annotations

import sqlite3

from app.services import ServiceNotImplemented

SCOPES = ("all", "kb", "shared", "mine")
ITEM_TYPES = ("faq", "doc", "slide")


def unified_search(
    conn: sqlite3.Connection,
    user_id: int,
    query: str,
    scope: str = "all",
    item_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """三源统一检索。

    后续批次需实现：shared 源 MVP 阶段保持空集占位；kb 分组只返回已 verified 的条目，
    E3 候选不出现在搜索结果中；结果按相关度降序返回。
    """
    raise ServiceNotImplemented("统一搜索模块将在后续批次实现")
