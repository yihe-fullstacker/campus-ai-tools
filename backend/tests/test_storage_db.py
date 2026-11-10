"""存储层测试：迁移、约束与 FTS 同步。"""

from __future__ import annotations

import sqlite3

import pytest

from app.storage.db import migrate, utc_now_iso

EXPECTED_TABLES = (
    "users",
    "sessions",
    "messages",
    "documents",
    "chunks",
    "kb_items",
    "usage_daily",
    "schema_migrations",
)


def test_migrate_creates_expected_tables(db_conn: sqlite3.Connection) -> None:
    rows = db_conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    names = {row["name"] for row in rows}
    for table in EXPECTED_TABLES:
        assert table in names, f"缺少数据表：{table}"


def test_migrate_is_idempotent(db_conn: sqlite3.Connection) -> None:
    assert migrate(db_conn) == []


def test_wal_mode_and_foreign_keys_enabled(db_conn: sqlite3.Connection) -> None:
    assert db_conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
    assert db_conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_users_identity_is_unique(db_conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    db_conn.execute(
        "INSERT INTO users (identity, password_hash, role, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("20240101", "hash", "student", now, now),
    )
    db_conn.commit()
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(
            "INSERT INTO users (identity, password_hash, role, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            ("20240101", "hash", "student", now, now),
        )


def test_kb_items_legacy_id_is_unique_when_not_null(db_conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    insert_sql = (
        "INSERT INTO kb_items (question, aliases, answer, category, priority, evidence, "
        "status, legacy_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    params = ("缓考怎么申请", "[]", "通用建议", "S3", "P0", "E3", "candidate", "Q-S3-001", now, now)
    db_conn.execute(insert_sql, params)
    with pytest.raises(sqlite3.IntegrityError):
        db_conn.execute(insert_sql, params)


def test_kb_fts_index_follows_base_table(db_conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    db_conn.execute(
        "INSERT INTO kb_items (question, aliases, answer, category, priority, evidence, "
        "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "缓考怎么申请",
            '["缓考申请流程"]',
            "通用建议正文",
            "S3",
            "P0",
            "E3",
            "candidate",
            now,
            now,
        ),
    )
    db_conn.commit()
    hits = db_conn.execute(
        "SELECT rowid FROM kb_fts WHERE kb_fts MATCH ?", ("缓考怎么申请",)
    ).fetchall()
    assert len(hits) == 1


def test_kb_fts_row_removed_after_delete(db_conn: sqlite3.Connection) -> None:
    now = utc_now_iso()
    cursor = db_conn.execute(
        "INSERT INTO kb_items (question, aliases, answer, category, priority, evidence, "
        "status, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("补考怎么报名", "[]", "通用建议正文", "S3", "P1", "E3", "candidate", now, now),
    )
    db_conn.commit()
    db_conn.execute("DELETE FROM kb_items WHERE id = ?", (cursor.lastrowid,))
    db_conn.commit()
    hits = db_conn.execute(
        "SELECT rowid FROM kb_fts WHERE kb_fts MATCH ?", ("补考怎么报名",)
    ).fetchall()
    assert hits == []
