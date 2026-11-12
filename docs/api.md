# API 契约

维护副本：对应《校园综合 AI 平台 · 第二阶段技术方案文档 v0.2》§三。
本文件记录**实际实现**的接口；问答、助手、文档、搜索与知识库模块均已落地。

## 通用约定

- 业务接口前缀 `/api/v1`；`/healthz` 同时在根路径与 `/api/v1` 下暴露。
- 认证：除注册、登录、健康检查外，均需 `Authorization: Bearer <JWT>`；非法即 401。
- 错误统一体：`{"code": "<机器码>", "message": "<面向用户的中文提示>"}`。
- 状态码：400 参数不合法、401 未认证、403 无权限、404 不存在、405 方法不支持、
  413 请求体过大、429 限流、500 服务端异常。
- 分页：`?page=&page_size=`，默认 `page=1`、`page_size=20`（上限 100）。
- 时间：所有时间字段为 UTC ISO8601 字符串。
- 上传：服务端强校验类型与大小。类型不支持返回 400 `DOCUMENT_TYPE_UNSUPPORTED`；
  超过 30MB 返回 413 `DOCUMENT_TOO_LARGE`（Nginx 侧 `client_max_body_size` 同步为 30m，
  并返回同样的 JSON 错误体）。

## 已实现

### 账户 /auth

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | body `{identity, password}`；注册成功返回 201 + `{token, user}` |
| POST | `/api/v1/auth/login` | body `{identity, password}`；返回 `{token, user}` |
| POST | `/api/v1/auth/logout` | 204；服务端无状态，前端丢弃令牌 |
| GET | `/api/v1/users/me` | 返回当前用户 `{id, identity, role, created_at}` |

注册规则：
- `identity`：学号或邮箱二选一，规范化（去空白、转小写）后唯一；邮箱或 4–20 位字母数字学号。
- `password`：8–72 字节，需同时包含字母与数字；bcrypt 加盐哈希存储。

错误码：`AUTH_IDENTITY_INVALID`、`AUTH_PASSWORD_WEAK`、`AUTH_IDENTITY_EXISTS`、
`AUTH_CREDENTIALS_INVALID`、`AUTH_TOKEN_MISSING`、`AUTH_TOKEN_INVALID`、
`AUTH_TOKEN_EXPIRED`、`AUTH_USER_NOT_FOUND`、`REQUEST_INVALID`。

### 探活 /healthz

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/healthz` | 无需认证，返回 `{status, version, database}`；`status=ok` 表示服务与数据库均可用 |

### 运行期安全要求

- `APP_ENV=production` 时必须提供强随机 `JWT_SECRET`（≥32 字节）；使用仓库内的兜底值、
  文档示例值或空值时，后端**拒绝启动**并给出可执行的修复提示。

## 业务模块（已实现）

### 校园问答 /qa

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/qa/sessions` | 我的问答会话列表 |
| GET | `/api/v1/qa/messages/{session_id}` | 会话历史消息（可回放） |
| POST | `/api/v1/qa/ask` | body `{question, session_id?}`；响应见下 |

### 学习助手 /chat

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/chat/sessions` | 我的助手会话列表 |
| POST | `/api/v1/chat/sessions?title=` | 新建助手会话（title 可选） |
| GET | `/api/v1/chat/sessions/{id}/messages` | 助手会话历史消息 |
| POST | `/api/v1/chat/sessions/{id}/messages` | body `{content, template?}`，template 取 `free/plan/concept/hint` |

响应中的 `engine` 为 `llm` 或 `offline`：未配置模型、调用失败时返回离线通用建议并标记 `offline`。

### 文档解析 /documents

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/documents` | 我的文档列表 |
| POST | `/api/v1/documents` | multipart 上传（pdf/docx/pptx，≤30MB） |
| GET | `/api/v1/documents/{id}` | 文档详情（含状态与失败原因） |
| GET | `/api/v1/documents/{id}/summary` | `{summary, outline, progress, status, status_message}` |
| GET | `/api/v1/documents/{id}/summary/export` | 导出 Markdown 摘要与提纲 |
| POST | `/api/v1/documents/{id}/ask` | 文档问答，body `{question}` |

上传成功后按解析结果返回 `status`：可解析为 `ready`，扫描版/空文档/损坏文件为 `failed`，
并在 `status_message` 给出可直接展示的原因（例如「未能从文件中提取到文本，可能是扫描版或加密文件」）。
解析成功时会写入文本切片，文档问答的 `sources` 形如
`{kind: "chunk", doc_id, chunk_id, page, section_title, title, snippet}`；
未检索到相关内容时 `refusal` 非空。配置了模型时由模型依据切片作答，否则返回命中原文片段。

### 统一搜索 /search

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/search` | `q` + `scope`（all/kb/shared/mine）+ `type`（faq/doc/slide）+ 分页 |

### 知识库管理 /kb（仅管理员）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/kb/items` | 列出条目（`status` 可筛选） |
| POST | `/api/v1/kb/items` | 录入条目 |
| PUT | `/api/v1/kb/items/{id}` | 修改条目 / 升级证据等级 |
| POST | `/api/v1/kb/items/{id}/retire` | 下架条目 |
| POST | `/api/v1/kb/import` | 批量导入语料表（重复 `legacy_id` 自动跳过） |

### 模型接入 /llm-configs（用户自带密钥）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/llm-configs/presets` | 厂商预设（无需登录） |
| GET | `/api/v1/llm-configs` | 我的配置列表（密钥仅返回掩码） |
| POST | `/api/v1/llm-configs` | 新增配置；首个配置自动生效 |
| PUT | `/api/v1/llm-configs/{id}` | 修改配置；`api_key` 留空表示沿用原密钥 |
| POST | `/api/v1/llm-configs/{id}/activate` | 设为当前生效 |
| DELETE | `/api/v1/llm-configs/{id}` | 删除配置；删除生效配置时自动启用最新一份 |
| POST | `/api/v1/llm-configs/test` | 连通性测试 |

连通性测试支持两种入参：
- 未保存的草稿：`{provider, base_url, model, embedding_model?, api_key}`；
- 已保存的配置：`{config_id}`（密钥留空时不回传明文）。

成功返回 `{"ok": true, "reply": "...", "model": "...", "latency_ms": 320}`；
失败返回 `{"ok": false, "error": "面向用户的中文原因", "model": "..."}`，
并记录到配置的 `last_error`。密钥使用服务端密钥派生的对称加密存储，任何响应都不返回明文。

枚举校验：`scope` 与 `type` 非法取值返回 400 `REQUEST_INVALID`，不会进入检索逻辑。

知识库条目跨字段约束：`status=verified` 表示"已核对本校官方资料"，因此 `evidence` 必须为
E1 或 E2；`evidence=E3` + `status=verified` 的组合返回 400
（只修改 `status` 而不传 `evidence` 时，需由服务层与库中现值合并后再校验）。

## 校园问答响应契约（`/api/v1/qa/ask`）

```json
{
  "session_id": 12,
  "answer": "……（Markdown）",
  "source_type": "kb_hit | general_fallback",
  "verified": true,
  "sources": [
    { "kind": "kb_item", "id": "Q-S3-001", "title": "缓考怎么申请", "ref": "kb" },
    { "kind": "chunk", "doc_id": null, "page": null, "title": "教务处考试管理规定", "ref": "公开资料核对页" }
  ],
  "refusal": null
}
```

- `verified` 仅在 `source_type=kb_hit` 时有意义：true 表示该条目已核对本校官方资料，
  false 表示命中 E3 候选条目，正文自动置顶固定免责声明
  「⚠️ 以下为通用建议，尚未核对西昌学院安宁校区官方文件，具体流程与规定以学校官方最新通知为准。」
- `source_type=general_fallback` 表示未命中知识库，回答开头带
  「此回答非本校知识库内容，仅供参考」。
- `refusal` 非 null 时表示拒答，不生成编造内容。
- 搜索接口的 kb 分组只返回已 verified 条目，E3 候选不出现在搜索结果中。

## 通用错误体

```json
{ "code": "AUTH_CREDENTIALS_INVALID", "message": "学号/邮箱或密码不正确。" }
```
