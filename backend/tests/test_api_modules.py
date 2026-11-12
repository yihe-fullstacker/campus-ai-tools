"""骨架模块接口测试。

问答、助手、文档、搜索、知识库五个模块本轮只固定契约与鉴权要求，
业务实现由后续批次填充，因此受保护接口返回 501，未登录返回 401。
"""

from __future__ import annotations

from fastapi.testclient import TestClient

API = "/api/v1"


def test_qa_ask_requires_auth(client: TestClient) -> None:
    response = client.post(f"{API}/qa/ask", json={"question": "缓考怎么申请"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"


def test_qa_ask_returns_answer(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        f"{API}/qa/ask", json={"question": "缓考怎么申请"}, headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] > 0
    assert body["source_type"] in ("kb", "general_fallback", "refusal")
    assert body["answer"]


def test_qa_sessions_returns_list(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/qa/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_chat_sessions_returns_list(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/chat/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_documents_list_returns_ok(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/documents", headers=auth_headers)
    assert response.status_code == 200


def test_search_requires_auth(client: TestClient) -> None:
    response = client.get(f"{API}/search", params={"q": "缓考"})
    assert response.status_code == 401


def test_search_returns_results(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"{API}/search", params={"q": "缓考"}, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert "results" in body
    assert body["scope"] == "all"


def test_kb_items_forbidden_for_student(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"{API}/kb/items", headers=auth_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ADMIN_ONLY"


def test_kb_items_for_admin_returns_page(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get(f"{API}/kb/items", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
