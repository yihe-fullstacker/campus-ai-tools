"""骨架模块接口测试。

问答、助手、文档、搜索、知识库五个模块本轮只固定契约与鉴权要求，
业务实现由后续批次填充，因此受保护接口返回 501，未登录返回 401。
"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.services.auth_service import hash_password
from app.storage.db import utc_now_iso

API = "/api/v1"


def test_qa_ask_requires_auth(client: TestClient) -> None:
    response = client.post(f"{API}/qa/ask", json={"question": "缓考怎么申请"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"


def test_qa_ask_returns_not_implemented(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        f"{API}/qa/ask", json={"question": "缓考怎么申请"}, headers=auth_headers
    )
    assert response.status_code == 501
    body = response.json()
    assert body["code"] == "MODULE_NOT_IMPLEMENTED"
    assert body["message"]


def test_qa_sessions_returns_not_implemented(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/qa/sessions", headers=auth_headers)
    assert response.status_code == 501


def test_chat_sessions_returns_not_implemented(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/chat/sessions", headers=auth_headers)
    assert response.status_code == 501


def test_documents_list_returns_not_implemented(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/documents", headers=auth_headers)
    assert response.status_code == 501


def test_search_requires_auth(client: TestClient) -> None:
    response = client.get(f"{API}/search", params={"q": "缓考"})
    assert response.status_code == 401


def test_search_returns_not_implemented(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"{API}/search", params={"q": "缓考"}, headers=auth_headers)
    assert response.status_code == 501


def test_kb_items_forbidden_for_student(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"{API}/kb/items", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ADMIN_ONLY"


def test_kb_items_for_admin_returns_not_implemented(
    client: TestClient, db_conn: sqlite3.Connection
) -> None:
    now = utc_now_iso()
    db_conn.execute(
        "INSERT INTO users (identity, password_hash, role, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        ("admin", hash_password("admin2024"), "admin", now, now),
    )
    db_conn.commit()
    login = client.post(f"{API}/auth/login", json={"identity": "admin", "password": "admin2024"})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    response = client.get(f"{API}/kb/items", headers=headers)
    assert response.status_code == 501
