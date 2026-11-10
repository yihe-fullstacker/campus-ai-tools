# 数据表设计

维护副本：对应《校园综合 AI 平台 · 第二阶段技术方案文档 v0.2》§二。
实际建表语句见 `backend/app/storage/migrations/0001_init.sql`，迁移由应用启动时自动执行。

## 通用约定

- SQLite 起步，兼容后续迁移到 PostgreSQL（+pgvector）。
- 主键 `id` 为自增整数；所有表带 `created_at / updated_at`（UTC ISO8601 字符串）。
- 连接统一开启 WAL 模式、外键约束与 `busy_timeout`，降低单机并发写冲突概率。

## T1 users — 用户

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK | |
| identity | TEXT UNIQUE | 学号或邮箱（注册时绑定一种，规范化后唯一） |
| password_hash | TEXT | bcrypt 加盐哈希 |
| role | TEXT | student / admin（admin 用于知识库维护） |
| created_at / updated_at | TEXT | |

## T2 sessions — 会话

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK | |
| user_id | INTEGER FK→users | |
| title | TEXT | 取首条消息前 N 字，可改 |
| mode | TEXT | qa / chat / doc |
| tools | TEXT JSON | 预留字段：未来 Agent 工具链路状态，MVP 恒为空 |
| created_at / updated_at | TEXT | |

索引：`idx_sessions_user_mode (user_id, mode)`。

## T3 messages — 消息

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK | |
| session_id | INTEGER FK→sessions | |
| role | TEXT | user / assistant |
| content | TEXT | 正文 Markdown |
| sources | TEXT JSON | 来源标注数组 |
| created_at / updated_at | TEXT | |

索引：`idx_messages_session (session_id, id)`。

## T4 documents — 用户文档

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK | |
| user_id | INTEGER FK→users | 归属用户，原始文件与他人完全隔离 |
| filename / mime / size | TEXT / TEXT / INTEGER | 原始名、MIME、字节数 |
| status | TEXT | uploaded / parsing / ready / failed |
| status_message | TEXT | 失败原因（如"扫描版 PDF 暂不支持"） |
| storage_path | TEXT | `data/files/{user_id}/{doc_id}/` |
| summary | TEXT | 全文摘要 |
| outline | TEXT JSON | `[{title, level, page}]` |

索引：`idx_documents_user (user_id, id)`。

## T5 chunks — 文档切片

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK | |
| document_id | INTEGER FK→documents | |
| seq | INTEGER | 片段序号 |
| page | INTEGER NULL | 页码（pdf/pptx 有，docx 为章节） |
| section_title | TEXT NULL | 所在章节标题（尽力抽取） |
| text | TEXT | 切片文本 |
| doc_vec_id | TEXT | 本地块向量索引 ID（如 `d{doc_id}_{seq}`） |

约束：`UNIQUE (document_id, seq)`。

## T6 kb_items — 本校知识库条目

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK | |
| question | TEXT | 标准问法 |
| aliases | TEXT JSON | 同义问法数组 |
| answer | TEXT | 预期回答要点（Markdown） |
| answer_missing | TEXT | 暂缺时的占位说明 |
| category / subcategory | TEXT / TEXT | S1–S5 一级 / 二级子类 |
| priority | TEXT | P0 / P1 / P2 |
| evidence / evidence_source | TEXT / TEXT | E1/E2/E3 + 来源 |
| status | TEXT | candidate / verified / published / retired |
| legacy_id | TEXT NULL | 语料库原 id（如 `Q-S3-001`） |
| kb_vec_id | TEXT | 本地块向量索引 ID（如 `kb{i}`） |
| source_doc | TEXT NULL | 核对用的官方文件名称或 URL（E2 升级时填写） |
| created_at / updated_at | TEXT | |

索引：`idx_kb_items_status (status)`；`legacy_id` 非空时唯一
（`idx_kb_items_legacy_id`，用于语料回溯与重复导入去重）。

> 证据等级与状态说明：`verified` 表示已核对本校官方资料；E3 候选命中时问答会置顶免责声明并
> 返回 `verified: false`；`retired` 条目不再命中。E3→E2→E1 的升级为人工触发，不自动执行。

## T7 usage_daily — 配额计数

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| user_id | INTEGER FK→users | 复合主键 |
| date | TEXT | 复合主键 |
| qa_count / chat_count / embed_units | INTEGER | 每人每日计数（阈值配置化，初期 30–50 次/日） |
| updated_at | TEXT | |

## 全文索引（FTS5）

- `kb_fts`：外部内容表，映射 `kb_items` 的 question / aliases / answer。
- `chunks_fts`：外部内容表，映射 `chunks` 的 text。
- 语料为中文，两个虚表均使用 `trigram` 分词器以支持中文子串匹配；
  触发器（`kb_fts_ai/ad/au`、`chunks_fts_ai/ad/au`）保证虚表与基表自动同步。
- 向量检索使用本地文件索引（`data/index/blocks.faiss`、`kb.faiss`），后续批次实现。

## 迁移机制

- 迁移脚本位于 `backend/app/storage/migrations/`，文件名形如 `0001_init.sql`，按文件名排序执行。
- 已执行版本记录在 `schema_migrations (version, applied_at)` 表，迁移可重复调用且幂等。
- 新增迁移时新增一个 `000N_xxx.sql` 文件，不要修改已发布的脚本。
