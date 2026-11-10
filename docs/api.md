# API 契约

维护副本：对应《校园综合 AI 平台 · 第二阶段技术方案文档 v0.2》§三。
本文件记录**实际实现**的接口；标记为「占位」的模块仅固定路径与鉴权要求，
业务实现由后续批次填充，受保护接口当前返回 `501 MODULE_NOT_IMPLEMENTED`。

## 通用约定

- 业务接口前缀 `/api/v1`；`/healthz` 同时在根路径与 `/api/v1` 下暴露。
- 认证：除注册、登录、健康检查外，均需 `Authorization: Bearer <JWT>`；非法即 401。
- 错误统一体：`{"code": "<机器码>", "message": "<面向用户的中文提示>"}`。
- 状态码：400 参数不合法、401 未认证、403 无权限、404 不存在、405 方法不支持、
  413 请求体过大、429 限流、500 服务端异常、501 模块尚未实现。
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

## 占位模块（路径已固定，实现待后续批次）

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/qa/sessions` | 我的问答会话列表 |
| POST | `/api/v1/qa/ask` | body `{question, session_id?}`；响应见下 |
| GET | `/api/v1/chat/sessions` | 我的助手会话列表 |
| POST | `/api/v1/chat/sessions` | 新建助手会话（body 可选 `title`） |
| GET | `/api/v1/chat/sessions/{id}/messages` | 助手会话历史消息 |
| POST | `/api/v1/chat/sessions/{id}/messages` | body `{content, template?}` |
| GET | `/api/v1/documents` | 我的文档列表 |
| POST | `/api/v1/documents` | multipart 上传（pdf/docx/pptx，≤30MB） |
| GET | `/api/v1/documents/{id}` | 文档详情（含状态与失败原因） |
| GET | `/api/v1/documents/{id}/summary` | `{summary, outline, progress}` |
| GET | `/api/v1/documents/{id}/summary/export` | 导出 Markdown 摘要 |
| POST | `/api/v1/documents/{id}/ask` | 文档问答，body `{question}` |
| GET | `/api/v1/search` | `q` + `scope`（all/kb/shared/mine）+ `type`（faq/doc/slide）+ 分页 |
| GET | `/api/v1/kb/items` | 列出条目（仅管理员，`status` 可筛选） |
| POST | `/api/v1/kb/items` | 录入条目（仅管理员） |
| PUT | `/api/v1/kb/items/{id}` | 修改条目 / 升级证据等级（仅管理员） |
| POST | `/api/v1/kb/items/{id}/retire` | 下架条目（仅管理员） |
| POST | `/api/v1/kb/import` | 批量导入语料表（仅管理员） |

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
