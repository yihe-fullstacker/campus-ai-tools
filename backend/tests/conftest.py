"""pytest 公共夹具。

测试统一使用临时目录作为数据目录，避免污染仓库内的 ``data/``。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_db
from app.config import get_settings
from app.main import create_app
from app.storage.db import connect, migrate

API = "/api/v1"


@pytest.fixture()
def settings(tmp_path, monkeypatch) -> Iterator[object]:
    """把配置指向临时目录并注入测试用密钥。"""
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "data" / "app.db"))
    monkeypatch.setenv("JWT_SECRET", "test-secret-value-for-unit-tests-0123456789")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


@pytest.fixture()
def db_conn(settings) -> Iterator[sqlite3.Connection]:
    """已执行迁移的数据库连接。"""
    conn = connect()
    migrate(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def client(settings, db_conn) -> Iterator[TestClient]:
    """测试客户端；数据库依赖被替换为测试连接。"""
    app = create_app()

    def override_get_db() -> Iterator[sqlite3.Connection]:
        yield db_conn

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client: TestClient) -> dict:
    """注册一个普通学生账号，返回注册响应体。"""
    response = client.post(
        f"{API}/auth/register", json={"identity": "20240101", "password": "campus2024"}
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def auth_headers(registered_user: dict) -> dict[str, str]:
    """已登录学生的请求头。"""
    return {"Authorization": f"Bearer {registered_user['token']}"}
