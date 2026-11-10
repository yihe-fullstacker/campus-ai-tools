"""健康检查与路由契约测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

API = "/api/v1"

EXPECTED_PATHS = (
    "/healthz",
    f"{API}/healthz",
    f"{API}/auth/register",
    f"{API}/auth/login",
    f"{API}/auth/logout",
    f"{API}/users/me",
    f"{API}/qa/sessions",
    f"{API}/qa/ask",
    f"{API}/chat/sessions",
    f"{API}/documents",
    f"{API}/search",
    f"{API}/kb/items",
    f"{API}/kb/import",
)


def test_healthz_needs_no_auth(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"


def test_healthz_also_under_api_prefix(client: TestClient) -> None:
    response = client.get(f"{API}/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_openapi_exposes_documented_paths(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    for path in EXPECTED_PATHS:
        assert path in paths, f"缺少接口：{path}"
