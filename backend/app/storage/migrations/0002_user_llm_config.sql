-- 用户自助配置的大模型 API（BYOK：用户自带密钥与额度）
-- 一个用户可保存多份配置，但同一时刻只有一份生效（is_active=1）。
CREATE TABLE IF NOT EXISTS user_llm_configs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider        TEXT    NOT NULL,
    display_name    TEXT    NOT NULL,
    base_url        TEXT    NOT NULL,
    model           TEXT    NOT NULL,
    embedding_model TEXT,
    api_key_cipher  TEXT    NOT NULL,
    api_key_hint    TEXT    NOT NULL,
    is_active       INTEGER NOT NULL DEFAULT 0,
    last_verified_at TEXT,
    last_error      TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_user_llm_configs_user
    ON user_llm_configs (user_id, is_active);
