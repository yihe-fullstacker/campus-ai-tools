"""认证服务层测试。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.errors import ApiError
from app.services.auth_service import (
    decode_access_token,
    hash_password,
    validate_identity,
    validate_password,
    verify_password,
)

API = "/api/v1"


def test_password_hash_is_salted_and_verifiable() -> None:
    hashed = hash_password("campus2024")
    assert hashed != "campus2024"
    assert verify_password("campus2024", hashed)
    assert not verify_password("wrong2024", hashed)


def test_two_hashes_of_same_password_differ() -> None:
    assert hash_password("campus2024") != hash_password("campus2024")


def test_verify_password_returns_false_for_invalid_hash() -> None:
    assert verify_password("campus2024", "not-a-hash") is False


def test_validate_identity_accepts_email_and_student_id() -> None:
    assert validate_identity(" Student@Example.com ") == "student@example.com"
    assert validate_identity("20240101") == "20240101"


@pytest.mark.parametrize("identity", ["", "不是邮箱", "a" * 65, "ab"])
def test_validate_identity_rejects_invalid_values(identity: str) -> None:
    with pytest.raises(ApiError) as excinfo:
        validate_identity(identity)
    assert excinfo.value.code == "AUTH_IDENTITY_INVALID"


def test_validate_password_enforces_rules() -> None:
    validate_password("campus2024")
    with pytest.raises(ApiError) as excinfo:
        validate_password("a1")
    assert excinfo.value.code == "AUTH_PASSWORD_WEAK"
    with pytest.raises(ApiError):
        validate_password("abcdefgh")
    with pytest.raises(ApiError):
        validate_password("a1" * 40)


def test_access_token_round_trip(client: TestClient) -> None:
    response = client.post(
        f"{API}/auth/register", json={"identity": "20240101", "password": "campus2024"}
    )
    body = response.json()
    payload = decode_access_token(body["token"])
    assert int(payload["sub"]) == body["user"]["id"]
    assert payload["role"] == "student"


def test_expired_token_is_rejected(settings) -> None:
    expired = jwt.encode(
        {
            "sub": "1",
            "exp": int((datetime.now(UTC) - timedelta(minutes=1)).timestamp()),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(ApiError) as excinfo:
        decode_access_token(expired)
    assert excinfo.value.code == "AUTH_TOKEN_EXPIRED"
    assert excinfo.value.status_code == 401
