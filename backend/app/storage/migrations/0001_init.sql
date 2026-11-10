-- 校园综合 AI 平台 · 初始 schema
-- 对应技术方案 §二 T1–T7 与索引物理设计；执行后记录在 schema_migrations 表。

-- T1 users —— 用户（identity 为学号或邮箱，MVP 单绑定）
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    identity      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'student' CHECK (role IN ('student', 'admin')),
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

-- T2 sessions —— 会话（问答与助手共用，mode 区分；tools 为未来 Agent 工具链预留字段）
CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title      TEXT,
    mode       TEXT    NOT NULL CHECK (mode IN ('qa', 'chat', 'doc')),
    tools      TEXT    NOT NULL DEFAULT '[]',
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_mode ON sessions (user_id, mode);

-- T3 messages —— 消息（sources 为来源标注数组的 JSON 文本）
CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    role       TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT    NOT NULL,
    sources    TEXT    NOT NULL DEFAULT '[]',
    created_at TEXT    NOT NULL,
    updated_at TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages (session_id, id);

-- T4 documents —— 用户文档（原始文件与他人完全隔离）
CREATE TABLE IF NOT EXISTS documents (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    filename       TEXT    NOT NULL,
    mime           TEXT    NOT NULL,
    size           INTEGER NOT NULL,
    status         TEXT    NOT NULL DEFAULT 'uploaded'
                   CHECK (status IN ('uploaded', 'parsing', 'ready', 'failed')),
    status_message TEXT,
    storage_path   TEXT,
    summary        TEXT,
    outline        TEXT    NOT NULL DEFAULT '[]',
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_documents_user ON documents (user_id, id);

-- T5 chunks —— 文档切片（doc_vec_id 为本地向量索引中的 ID）
CREATE TABLE IF NOT EXISTS chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER NOT NULL REFERENCES documents (id) ON DELETE CASCADE,
    seq           INTEGER NOT NULL,
    page          INTEGER,
    section_title TEXT,
    text          TEXT    NOT NULL,
    doc_vec_id    TEXT    NOT NULL,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL,
    UNIQUE (document_id, seq)
);

-- T6 kb_items —— 本校知识库条目（唯一业务数据源；evidence 为 E1/E2/E3）
CREATE TABLE IF NOT EXISTS kb_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    question        TEXT    NOT NULL,
    aliases         TEXT    NOT NULL DEFAULT '[]',
    answer          TEXT    NOT NULL DEFAULT '',
    answer_missing  TEXT,
    category        TEXT    NOT NULL,
    subcategory     TEXT,
    priority        TEXT    NOT NULL DEFAULT 'P2' CHECK (priority IN ('P0', 'P1', 'P2')),
    evidence        TEXT    NOT NULL DEFAULT 'E3' CHECK (evidence IN ('E1', 'E2', 'E3')),
    evidence_source TEXT,
    status          TEXT    NOT NULL DEFAULT 'candidate'
                    CHECK (status IN ('candidate', 'verified', 'published', 'retired')),
    legacy_id       TEXT,
    kb_vec_id       TEXT,
    source_doc      TEXT,
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_kb_items_legacy_id
    ON kb_items (legacy_id) WHERE legacy_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_kb_items_status ON kb_items (status);

-- T7 usage_daily —— 每日配额计数（user_id + date 复合主键）
CREATE TABLE IF NOT EXISTS usage_daily (
    user_id     INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    date        TEXT    NOT NULL,
    qa_count    INTEGER NOT NULL DEFAULT 0,
    chat_count  INTEGER NOT NULL DEFAULT 0,
    embed_units INTEGER NOT NULL DEFAULT 0,
    updated_at  TEXT    NOT NULL,
    PRIMARY KEY (user_id, date)
);

-- 关键词检索：SQLite FTS5 虚表。语料为中文，采用 trigram 分词器以支持中文子串匹配。
-- 触发器保证虚表与基表自动同步。
CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5 (
    question,
    aliases,
    answer,
    content = 'kb_items',
    content_rowid = 'id',
    tokenize = 'trigram'
);

CREATE TRIGGER IF NOT EXISTS kb_fts_ai AFTER INSERT ON kb_items BEGIN
    INSERT INTO kb_fts (rowid, question, aliases, answer)
    VALUES (new.id, new.question, new.aliases, new.answer);
END;

CREATE TRIGGER IF NOT EXISTS kb_fts_ad AFTER DELETE ON kb_items BEGIN
    INSERT INTO kb_fts (kb_fts, rowid, question, aliases, answer)
    VALUES ('delete', old.id, old.question, old.aliases, old.answer);
END;

CREATE TRIGGER IF NOT EXISTS kb_fts_au AFTER UPDATE ON kb_items BEGIN
    INSERT INTO kb_fts (kb_fts, rowid, question, aliases, answer)
    VALUES ('delete', old.id, old.question, old.aliases, old.answer);
    INSERT INTO kb_fts (rowid, question, aliases, answer)
    VALUES (new.id, new.question, new.aliases, new.answer);
END;

CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5 (
    text,
    content = 'chunks',
    content_rowid = 'id',
    tokenize = 'trigram'
);

CREATE TRIGGER IF NOT EXISTS chunks_fts_ai AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts (rowid, text) VALUES (new.id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_fts_ad AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts (chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;

CREATE TRIGGER IF NOT EXISTS chunks_fts_au AFTER UPDATE ON chunks BEGIN
    INSERT INTO chunks_fts (chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO chunks_fts (rowid, text) VALUES (new.id, new.text);
END;
