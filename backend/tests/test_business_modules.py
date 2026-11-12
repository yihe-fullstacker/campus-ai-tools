"""第二/三批次业务模块测试：知识库、问答、学习助手、统一搜索。"""

from __future__ import annotations

from fastapi.testclient import TestClient

API = "/api/v1"


# --- 知识库管理 -------------------------------------------------------

def _kb_payload(**overrides: object) -> dict:
    """构造一条知识库录入请求。"""
    payload = {
        "question": "缓考怎么申请",
        "aliases": ["怎么办理缓考"],
        "answer": "在教务系统提交缓考申请，并附医院证明。",
        "category": "S3",
        "priority": "P0",
        "evidence": "E3",
        "status": "candidate",
        "legacy_id": "Q-S3-001",
    }
    payload.update(overrides)
    return payload


def test_kb_create_then_list_and_detail(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(f"{API}/kb/items", json=_kb_payload(), headers=admin_headers)
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["status"] == "candidate"
    assert item["evidence"] == "E3"
    assert item["aliases"] == ["怎么办理缓考"]

    listed = client.get(f"{API}/kb/items", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_kb_duplicate_legacy_id_rejected(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(f"{API}/kb/items", json=_kb_payload(), headers=admin_headers)
    assert created.status_code == 201
    duplicated = client.post(f"{API}/kb/items", json=_kb_payload(), headers=admin_headers)
    assert duplicated.status_code == 400
    assert duplicated.json()["code"] == "KB_LEGACY_ID_DUPLICATED"


def test_kb_cannot_verify_e3_item(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(f"{API}/kb/items", json=_kb_payload(), headers=admin_headers)
    item_id = created.json()["id"]

    rejected = client.put(
        f"{API}/kb/items/{item_id}",
        json={"status": "verified"},
        headers=admin_headers,
    )
    assert rejected.status_code == 400
    assert rejected.json()["code"] == "KB_EVIDENCE_CONFLICT"

    upgraded = client.put(
        f"{API}/kb/items/{item_id}",
        json={"evidence": "E2", "status": "verified"},
        headers=admin_headers,
    )
    assert upgraded.status_code == 200
    assert upgraded.json()["evidence"] == "E2"
    assert upgraded.json()["status"] == "verified"


def test_kb_retire_item(client: TestClient, admin_headers: dict[str, str]) -> None:
    created = client.post(f"{API}/kb/items", json=_kb_payload(), headers=admin_headers)
    item_id = created.json()["id"]
    retired = client.post(f"{API}/kb/items/{item_id}/retire", headers=admin_headers)
    assert retired.status_code == 200
    assert retired.json()["status"] == "retired"


def test_kb_import_skips_existing_legacy_ids(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    first = client.post(f"{API}/kb/import", json=[_kb_payload()], headers=admin_headers)
    assert first.status_code == 200, first.text
    assert first.json()["created_count"] == 1

    again = client.post(f"{API}/kb/import", json=[_kb_payload()], headers=admin_headers)
    assert again.status_code == 200
    assert again.json()["created_count"] == 0
    assert again.json()["skipped_count"] == 1
    assert again.json()["skipped_legacy_ids"] == ["Q-S3-001"]


def test_kb_missing_item_returns_404(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.put(
        f"{API}/kb/items/99999", json={"answer": "x"}, headers=admin_headers
    )
    assert response.status_code == 404
    assert response.json()["code"] == "KB_ITEM_NOT_FOUND"


# --- 校园问答 ---------------------------------------------------------

def test_qa_hit_e3_returns_disclaimer_and_not_verified(
    client: TestClient, auth_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    client.post(f"{API}/kb/items", json=_kb_payload(), headers=admin_headers)

    response = client.post(
        f"{API}/qa/ask", json={"question": "缓考怎么申请"}, headers=auth_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_type"] == "kb"
    assert body["verified"] is False
    assert body["disclaimer"]
    assert body["answer"].startswith(body["disclaimer"])
    assert body["sources"][0]["evidence"] == "E3"


def test_qa_hit_verified_item_has_no_disclaimer(
    client: TestClient, auth_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    client.post(
        f"{API}/kb/items",
        json=_kb_payload(evidence="E2", status="verified", answer="缓考须在考试前 3 天提交。"),
        headers=admin_headers,
    )
    response = client.post(
        f"{API}/qa/ask", json={"question": "缓考怎么申请"}, headers=auth_headers
    )
    body = response.json()
    assert body["verified"] is True
    assert body["disclaimer"] is None
    assert "3 天" in body["answer"]


def test_qa_unmatched_question_falls_back(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/qa/ask", json={"question": "请问图书馆几点关门"}, headers=auth_headers
    )
    body = response.json()
    assert body["source_type"] == "general_fallback"
    assert body["verified"] is False
    assert body["sources"] == []


def test_qa_out_of_scope_question_is_refused(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/qa/ask", json={"question": "帮我破解同学院长账号密码"}, headers=auth_headers
    )
    body = response.json()
    assert body["source_type"] == "refusal"
    assert body["refusal"]
    assert body["sources"] == []


def test_qa_session_persists_and_replays(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = client.post(
        f"{API}/qa/ask", json={"question": "缓考怎么申请"}, headers=auth_headers
    )
    session_id = first.json()["session_id"]

    second = client.post(
        f"{API}/qa/ask",
        json={"question": "那补考呢", "session_id": session_id},
        headers=auth_headers,
    )
    assert second.json()["session_id"] == session_id

    sessions = client.get(f"{API}/qa/sessions", headers=auth_headers).json()
    assert [s["id"] for s in sessions] == [session_id]

    messages = client.get(
        f"{API}/qa/messages/{session_id}", headers=auth_headers
    )
    assert messages.status_code == 200
    roles = [m["role"] for m in messages.json()]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_qa_rejects_foreign_session(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/qa/ask",
        json={"question": "缓考怎么申请", "session_id": 99999},
        headers=auth_headers,
    )
    assert response.status_code == 404
    assert response.json()["code"] == "QA_SESSION_NOT_FOUND"


# --- 学习助手 ---------------------------------------------------------

def test_chat_session_lifecycle(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        f"{API}/chat/sessions", params={"title": "高数复习"}, headers=auth_headers
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]

    sent = client.post(
        f"{API}/chat/sessions/{session_id}/messages",
        json={"content": "帮我排一个高数复习计划", "template": "plan"},
        headers=auth_headers,
    )
    assert sent.status_code == 201, sent.text
    body = sent.json()
    assert body["template"] == "plan"
    assert body["engine"] in ("llm", "offline")
    assert body["reply"]

    messages = client.get(
        f"{API}/chat/sessions/{session_id}/messages", headers=auth_headers
    ).json()
    assert [m["role"] for m in messages] == ["user", "assistant"]

    sessions = client.get(f"{API}/chat/sessions", headers=auth_headers).json()
    assert [s["id"] for s in sessions] == [session_id]


def test_chat_rejects_invalid_template(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    session_id = client.post(f"{API}/chat/sessions", headers=auth_headers).json()["id"]
    response = client.post(
        f"{API}/chat/sessions/{session_id}/messages",
        json={"content": "你好", "template": "unknown"},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "CHAT_TEMPLATE_INVALID"


def test_chat_rejects_empty_content(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    session_id = client.post(f"{API}/chat/sessions", headers=auth_headers).json()["id"]
    response = client.post(
        f"{API}/chat/sessions/{session_id}/messages",
        json={"content": "   "},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "CHAT_CONTENT_EMPTY"


# --- 统一搜索 ---------------------------------------------------------

def test_search_hides_e3_candidates(
    client: TestClient, auth_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    client.post(f"{API}/kb/items", json=_kb_payload(), headers=admin_headers)

    body = client.get(
        f"{API}/search", params={"q": "缓考"}, headers=auth_headers
    ).json()
    assert body["counts"]["kb"] == 0
    assert body["total"] == 0


def test_search_returns_verified_kb_items(
    client: TestClient, auth_headers: dict[str, str], admin_headers: dict[str, str]
) -> None:
    client.post(
        f"{API}/kb/items",
        json=_kb_payload(evidence="E1", status="verified"),
        headers=admin_headers,
    )
    body = client.get(
        f"{API}/search", params={"q": "缓考", "scope": "kb"}, headers=auth_headers
    ).json()
    assert body["counts"]["kb"] == 1
    hit = body["results"][0]
    assert hit["type"] == "faq"
    assert hit["evidence"] == "E1"


def test_search_shared_source_is_empty_placeholder(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    body = client.get(
        f"{API}/search", params={"q": "缓考", "scope": "shared"}, headers=auth_headers
    ).json()
    assert body["counts"]["shared"] == 0
    assert body["total"] == 0


def test_search_requires_keyword(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(f"{API}/search", params={"q": " "}, headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "SEARCH_QUERY_EMPTY"
