"""审查修复项的回归测试。

覆盖：上传大小/类型校验、新建助手会话调用正确的 service、生产环境密钥 fail-fast
搜索枚举校验、知识库 evidence 与 status 的跨字段约束。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import DEFAULT_JWT_SECRET, get_settings
from app.main import create_app
from app.services import ServiceNotImplemented, chat_service, doc_service

API = "/api/v1"


def test_upload_rejects_oversized_file(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    monkeypatch.setattr(doc_service, "MAX_UPLOAD_BYTES", 10)
    response = client.post(
        f"{API}/documents",
        files={"file": ("report.pdf", b"x" * 4096, "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 413
    assert response.json()["code"] == "DOCUMENT_TOO_LARGE"


def test_upload_rejects_unsupported_mime_type(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/documents",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "DOCUMENT_TYPE_UNSUPPORTED"


def test_upload_rejects_mismatched_extension(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/documents",
        files={"file": ("payload.exe", b"hello", "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "DOCUMENT_TYPE_UNSUPPORTED"


def test_upload_empty_pdf_is_marked_failed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # 一个没有文本层的 PDF 无法解析出内容，应如实标记 failed（扫描版/空文档）
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [] /Count 0 >>
endobj
xref
0 3
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
end-xref
trailer
<< /Size 3 /Root 1 0 R >>
startxref
55
%%EOF"""
    response = client.post(
        f"{API}/documents",
        files={"file": ("report.pdf", pdf_content, "application/pdf")},
        headers=auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert "document_id" in body
    assert body["filename"] == "report.pdf"
    assert body["status"] == "failed"
    assert body["status_message"]


def test_upload_requires_auth(client: TestClient) -> None:
    response = client.post(
        f"{API}/documents",
        files={"file": ("report.pdf", b"%PDF-1.4", "application/pdf")},
    )
    assert response.status_code == 401


def test_create_chat_session_calls_create_function(
    client: TestClient, auth_headers: dict[str, str], monkeypatch
) -> None:
    calls: dict[str, object] = {}

    def fake_create(conn, user_id: int, title: str | None = None) -> dict:
        calls["user_id"] = user_id
        calls["title"] = title
        raise ServiceNotImplemented("学习助手模块将在后续批次实现")

    monkeypatch.setattr(chat_service, "create_chat_session", fake_create)
    response = client.post(f"{API}/chat/sessions", headers=auth_headers)

    assert response.status_code == 501
    assert calls["user_id"] == 1
    assert calls["title"] is None


def test_production_refuses_default_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "app.db"))
    get_settings.cache_clear()
    try:
        app = create_app()
        with pytest.raises(RuntimeError) as excinfo:
            with TestClient(app):
                pass
        assert "JWT_SECRET" in str(excinfo.value)
    finally:
        get_settings.cache_clear()


def test_production_refuses_empty_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "app.db"))
    get_settings.cache_clear()
    try:
        app = create_app()
        with pytest.raises(RuntimeError):
            with TestClient(app):
                pass
    finally:
        get_settings.cache_clear()


def test_production_starts_with_strong_secret(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "f" * 64)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "app.db"))
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            assert client.get("/healthz").status_code == 200
    finally:
        get_settings.cache_clear()


def test_search_rejects_invalid_scope(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{API}/search", params={"q": "缓考", "scope": "bogus"}, headers=auth_headers
    )
    assert response.status_code == 400
    assert response.json()["code"] == "REQUEST_INVALID"
    assert "scope" in response.json()["message"]


def test_search_rejects_invalid_type(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{API}/search", params={"q": "缓考", "type": "bogus"}, headers=auth_headers
    )
    assert response.status_code == 400
    assert "type" in response.json()["message"]


def test_search_accepts_valid_enum_values(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{API}/search", params={"q": "缓考", "scope": "kb", "type": "faq"}, headers=auth_headers
    )
    assert response.status_code == 200


def test_kb_item_rejects_verified_with_e3_evidence(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/kb/items",
        json={
            "question": "缓考怎么申请",
            "category": "S3",
            "priority": "P0",
            "evidence": "E3",
            "status": "verified",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "REQUEST_INVALID"
    assert "E3 候选条目不得标记为已核实" in body["message"]


def test_kb_item_update_rejects_verified_with_e3_evidence(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.put(
        f"{API}/kb/items/1",
        json={"evidence": "E3", "status": "verified"},
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "E3 候选条目不得标记为已核实" in response.json()["message"]


def test_kb_item_accepts_verified_with_official_evidence(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/kb/items",
        json={
            "question": "缓考怎么申请",
            "category": "S3",
            "priority": "P0",
            "evidence": "E2",
            "status": "verified",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["evidence"] == "E2"
    assert body["status"] == "verified"


def test_kb_item_default_is_candidate_and_e3(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/kb/items",
        json={"question": "缓考怎么申请", "category": "S3"},
        headers=admin_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "candidate"
    assert body["evidence"] == "E3"