"""SQLite 连接与 schema 迁移。

表结构见 ``docs/schema.md``（对应技术方案 §二）。迁移脚本位于 ``migrations/`` 目录，
文件名形如 ``0001_init.sql``，按文件名排序执行；已执行版本记录在 ``schema_migrations`` 表，
因此迁移可重复调用且不会重复建表。
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def utc_now_iso() -> str:
    """当前 UTC 时间的 ISO8601 字符串（秒级精度，Z 后缀）。"""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """打开 SQLite 连接。

    统一开启 WAL 模式与外键约束，并设置 busy_timeout，降低单机并发写冲突概率。
    """
    settings = get_settings()
    path = Path(db_path) if db_path is not None else settings.resolved_db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def migrate(conn: sqlite3.Connection, migrations_dir: Path | None = None) -> list[str]:
    """执行尚未应用的迁移脚本。

    Returns:
        本次实际应用的迁移版本列表（按执行顺序）。
    """
    directory = migrations_dir or MIGRATIONS_DIR
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
    )
    conn.commit()

    applied = {row["version"] for row in conn.execute("SELECT version FROM schema_migrations")}
    newly_applied: list[str] = []
    for script in sorted(directory.glob("*.sql")):
        version = script.stem
        if version in applied:
            continue
        conn.executescript(script.read_text(encoding="utf-8"))
        conn.execute(
            "INSERT INTO schema_migrations (version, applied_at) VALUES (?, ?)",
            (version, utc_now_iso()),
        )
        conn.commit()
        newly_applied.append(version)
    return newly_applied
