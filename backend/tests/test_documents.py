"""文档解析、摘要与文档问答测试。"""

from __future__ import annotations

import io
import sqlite3

from fastapi.testclient import TestClient

API = "/api/v1"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _docx_bytes() -> bytes:
    """生成一份带标题与正文的 Word 文档。"""
    from docx import Document

    document = Document()
    document.add_heading("缓考办理说明", level=1)
    document.add_paragraph(
        "学生须在考试前三个工作日向教务系统提交缓考申请，并附医院证明。"
    )
    document.add_heading("补考安排", level=1)
    document.add_paragraph("缓考通过后，补考时间由教务处统一通知。")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _upload(client: TestClient, headers: dict[str, str]) -> dict:
    """上传测试文档并返回响应体。"""
    response = client.post(
        f"{API}/documents",
        files={"file": ("guide.docx", _docx_bytes(), DOCX_MIME)},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_upload_docx_builds_summary_and_chunks(
    client: TestClient, auth_headers: dict[str, str], db_conn: sqlite3.Connection
) -> None:
    body = _upload(client, auth_headers)
    assert body["status"] == "ready"
    assert body["pages"] >= 2
    assert "缓考" in body["summary"]

    chunks = db_conn.execute(
        "SELECT seq, text FROM chunks WHERE document_id = ? ORDER BY seq",
        (body["document_id"],),
    ).fetchall()
    assert chunks, "解析成功后应写入文本切片"
    assert "教务系统" in " ".join(row["text"] for row in chunks)


def test_document_summary_has_outline_and_progress(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = _upload(client, auth_headers)
    response = client.get(
        f"{API}/documents/{created['document_id']}/summary", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["progress"] == 100
    assert body["outline"]
    assert any("缓考" in item["title"] for item in body["outline"])


def test_document_ask_returns_answer_with_sources(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = _upload(client, auth_headers)
    response = client.post(
        f"{API}/documents/{created['document_id']}/ask",
        json={"question": "缓考需要提前几天申请"},
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["refusal"] is None
    assert body["answer"]
    assert body["sources"]
    assert body["sources"][0]["kind"] == "chunk"
    assert body["sources"][0]["title"] == "guide.docx"


def test_document_ask_refuses_unrelated_question(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = _upload(client, auth_headers)
    response = client.post(
        f"{API}/documents/{created['document_id']}/ask",
        json={"question": "量子纠缠的贝尔不等式是什么"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["refusal"]
    assert body["sources"] == []


def test_document_summary_export_markdown(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = _upload(client, auth_headers)
    response = client.get(
        f"{API}/documents/{created['document_id']}/summary/export", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "guide.docx" in response.text
    assert "## 摘要" in response.text


def test_documents_isolated_between_users(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = _upload(client, auth_headers)
    other = client.post(
        f"{API}/auth/register",
        json={"identity": "20240103", "password": "student-pass-2024"},
    ).json()
    other_headers = {"Authorization": f"Bearer {other['token']}"}

    assert client.get(f"{API}/documents", headers=other_headers).json() == []
    denied = client.get(
        f"{API}/documents/{created['document_id']}", headers=other_headers
    )
    assert denied.status_code == 404
