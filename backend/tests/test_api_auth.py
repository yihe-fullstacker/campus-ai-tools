"""账户与认证接口测试。"""

from __future__ import annotations

from fastapi.testclient import TestClient

API = "/api/v1"


def test_register_returns_token_and_user(client: TestClient) -> None:
    response = client.post(
        f"{API}/auth/register", json={"identity": "20240101", "password": "campus2024"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["token"]
    assert body["token_type"] == "bearer"
    assert body["expires_at"].endswith("Z")
    assert body["user"]["identity"] == "20240101"
    assert body["user"]["role"] == "student"


def test_register_rejects_duplicate_identity(client: TestClient) -> None:
    payload = {"identity": "20240101", "password": "campus2024"}
    assert client.post(f"{API}/auth/register", json=payload).status_code == 201
    response = client.post(f"{API}/auth/register", json=payload)
    assert response.status_code == 400
    assert response.json()["code"] == "AUTH_IDENTITY_EXISTS"
    assert "已注册" in response.json()["message"]


def test_register_rejects_invalid_identity(client: TestClient) -> None:
    response = client.post(
        f"{API}/auth/register", json={"identity": "不是邮箱", "password": "campus2024"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "AUTH_IDENTITY_INVALID"


def test_register_rejects_weak_password(client: TestClient) -> None:
    response = client.post(
        f"{API}/auth/register", json={"identity": "20240101", "password": "abcdefgh"}
    )
    assert response.status_code == 400
    assert response.json()["code"] == "AUTH_PASSWORD_WEAK"


def test_register_rejects_too_short_password(client: TestClient) -> None:
    response = client.post(f"{API}/auth/register", json={"identity": "20240101", "password": "a1"})
    assert response.status_code == 400
    assert response.json()["code"] == "REQUEST_INVALID"


def test_identity_is_normalized_to_lowercase(client: TestClient) -> None:
    response = client.post(
        f"{API}/auth/register",
        json={"identity": "Student@Example.com", "password": "campus2024"},
    )
    assert response.status_code == 201
    assert response.json()["user"]["identity"] == "student@example.com"
    again = client.post(
        f"{API}/auth/register",
        json={"identity": "student@example.com", "password": "campus2024"},
    )
    assert again.status_code == 400
    assert again.json()["code"] == "AUTH_IDENTITY_EXISTS"


def test_login_returns_token(client: TestClient) -> None:
    client.post(f"{API}/auth/register", json={"identity": "20240101", "password": "campus2024"})
    response = client.post(
        f"{API}/auth/login", json={"identity": "20240101", "password": "campus2024"}
    )
    assert response.status_code == 200
    assert response.json()["token"]


def test_login_rejects_wrong_password(client: TestClient) -> None:
    client.post(f"{API}/auth/register", json={"identity": "20240101", "password": "campus2024"})
    response = client.post(
        f"{API}/auth/login", json={"identity": "20240101", "password": "wrong2024"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_CREDENTIALS_INVALID"


def test_login_rejects_unknown_identity(client: TestClient) -> None:
    response = client.post(
        f"{API}/auth/login", json={"identity": "20249999", "password": "campus2024"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_CREDENTIALS_INVALID"


def test_users_me_requires_token(client: TestClient) -> None:
    response = client.get(f"{API}/users/me")
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_MISSING"


def test_users_me_rejects_malformed_authorization(client: TestClient) -> None:
    response = client.get(f"{API}/users/me", headers={"Authorization": "Token abc"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_INVALID"


def test_users_me_returns_current_user(
    client: TestClient, auth_headers: dict[str, str], registered_user: dict
) -> None:
    response = client.get(f"{API}/users/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == registered_user["user"]["id"]
    assert response.json()["identity"] == "20240101"


def test_users_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get(f"{API}/users/me", headers={"Authorization": "Bearer not-a-token"})
    assert response.status_code == 401
    assert response.json()["code"] == "AUTH_TOKEN_INVALID"


def test_logout_returns_no_content(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(f"{API}/auth/logout", headers=auth_headers)
    assert response.status_code == 204
    assert response.content == b""
