"""用户自助模型配置（BYOK）测试：密钥加密、掩码、生效切换、权限隔离。"""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.services.llm.crypto import decrypt_secret, mask_key

API = "/api/v1"
SAMPLE_KEY = "sk-campus-test-key-0123456789"


def _payload(**overrides: object) -> dict:
    """构造一份模型配置载荷。"""
    payload = {
        "provider": "deepseek",
        "model": "deepseek-chat",
        "api_key": SAMPLE_KEY,
    }
    payload.update(overrides)
    return payload


def test_presets_listed(client: TestClient) -> None:
    response = client.get(f"{API}/llm-configs/presets")
    assert response.status_code == 200
    providers = {item["provider"] for item in response.json()}
    assert {"deepseek", "qwen", "zhipu", "moonshot", "doubao", "openai-compatible"} <= providers


def test_create_config_hides_api_key(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post(f"{API}/llm-configs", json=_payload(), headers=auth_headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["is_active"] is True
    assert body["base_url"] == "https://api.deepseek.com/v1"
    assert SAMPLE_KEY not in str(body)
    assert set(body["api_key_hint"]) != set(SAMPLE_KEY)
    assert "api_key" not in body


def test_api_key_encrypted_at_rest(
    client: TestClient, auth_headers: dict[str, str], db_conn: sqlite3.Connection
) -> None:
    client.post(f"{API}/llm-configs", json=_payload(), headers=auth_headers)
    row = db_conn.execute("SELECT api_key_cipher, api_key_hint FROM user_llm_configs").fetchone()
    assert SAMPLE_KEY not in row["api_key_cipher"]
    assert decrypt_secret(row["api_key_cipher"]) == SAMPLE_KEY
    assert row["api_key_hint"] == mask_key(SAMPLE_KEY)


def test_only_first_config_is_active(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = client.post(f"{API}/llm-configs", json=_payload(), headers=auth_headers).json()
    second = client.post(
        f"{API}/llm-configs", json=_payload(model="deepseek-reasoner"), headers=auth_headers
    ).json()
    assert first["is_active"] is True
    assert second["is_active"] is False

    activated = client.post(f"{API}/llm-configs/{second['id']}/activate", headers=auth_headers)
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True

    configs = client.get(f"{API}/llm-configs", headers=auth_headers).json()
    active = [c for c in configs if c["is_active"]]
    assert len(active) == 1
    assert active[0]["id"] == second["id"]


def test_update_keeps_key_when_omitted(
    client: TestClient, auth_headers: dict[str, str], db_conn: sqlite3.Connection
) -> None:
    created = client.post(f"{API}/llm-configs", json=_payload(), headers=auth_headers).json()
    before = db_conn.execute("SELECT api_key_cipher FROM user_llm_configs").fetchone()[0]

    updated = client.put(
        f"{API}/llm-configs/{created['id']}",
        json={"model": "deepseek-reasoner"},
        headers=auth_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["model"] == "deepseek-reasoner"
    after = db_conn.execute("SELECT api_key_cipher FROM user_llm_configs").fetchone()[0]
    assert before == after, "未提供新密钥时应沿用原密钥"


def test_update_with_new_key_reencrypts(
    client: TestClient, auth_headers: dict[str, str], db_conn: sqlite3.Connection
) -> None:
    created = client.post(f"{API}/llm-configs", json=_payload(), headers=auth_headers).json()
    new_key = "sk-brand-new-key-9876543210"
    client.put(
        f"{API}/llm-configs/{created['id']}",
        json={"api_key": new_key},
        headers=auth_headers,
    )
    cipher = db_conn.execute("SELECT api_key_cipher FROM user_llm_configs").fetchone()[0]
    assert decrypt_secret(cipher) == new_key


def test_custom_provider_requires_base_url(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/llm-configs",
        json={"provider": "openai-compatible", "model": "llama3", "api_key": SAMPLE_KEY},
        headers=auth_headers,
    )
    assert response.status_code == 400
    assert response.json()["code"] == "LLM_BASE_URL_REQUIRED"


def test_unknown_provider_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{API}/llm-configs", json=_payload(provider="unknown-vendor"), headers=auth_headers
    )
    assert response.status_code == 400
    assert response.json()["code"] == "LLM_PROVIDER_UNKNOWN"


def test_short_key_rejected(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(f"{API}/llm-configs", json=_payload(api_key="abc"), headers=auth_headers)
    assert response.status_code == 400
    assert response.json()["code"] == "LLM_API_KEY_INVALID"


def test_delete_active_promotes_latest(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    first = client.post(f"{API}/llm-configs", json=_payload(), headers=auth_headers).json()
    second = client.post(
        f"{API}/llm-configs", json=_payload(model="deepseek-reasoner"), headers=auth_headers
    ).json()

    deleted = client.delete(f"{API}/llm-configs/{first['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert deleted.json()["active_config_id"] == second["id"]

    remaining = client.get(f"{API}/llm-configs", headers=auth_headers).json()
    assert len(remaining) == 1
    assert remaining[0]["is_active"] is True


def test_config_isolated_between_users(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post(f"{API}/llm-configs", json=_payload(), headers=auth_headers).json()

    other = client.post(
        f"{API}/auth/register", json={"identity": "20240102", "password": "campus2024"}
    ).json()
    other_headers = {"Authorization": f"Bearer {other['token']}"}

    assert client.get(f"{API}/llm-configs", headers=other_headers).json() == []
    stolen = client.put(
        f"{API}/llm-configs/{created['id']}", json={"model": "x"}, headers=other_headers
    )
    assert stolen.status_code == 404


def test_config_requires_auth(client: TestClient) -> None:
    assert client.get(f"{API}/llm-configs").status_code == 401
