# 校园综合 AI 平台（campus-ai-tools）

面向高校学生的校园综合 AI 平台，覆盖四大能力：校园智能问答、AI 学习助手、PDF/Word/PPT 等学习资料的智能解析与总结、校园信息与学习资源智能搜索。

- 后端：FastAPI + SQLite（含 FTS5 全文索引）+ 本地文件存储
- 前端：Vue 3 + Vue Router + Pinia + Vite
- 部署：Docker Compose 单机（backend + web 两容器）
- 文档解析：pypdf / python-docx / python-pptx
- LLM：统一 Provider 抽象接口（`provider.chat` / `provider.embed`），用户可自带任意 OpenAI 兼容模型的密钥

## 目录结构

```
campus-ai-tools/
├── AGENTS.md                     # Agent 开发规范
├── README.md
├── docker-compose.yml
├── .env.example                  # 环境变量样例（复制为 .env 使用）
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt          # 运行时依赖
│   ├── requirements-dev.txt      # 测试与检查依赖
│   ├── pyproject.toml            # pytest / ruff 配置
│   ├── app/
│   │   ├── main.py               # FastAPI 入口、路由装配
│   │   ├── config.py             # 环境变量配置
│   │   ├── errors.py             # 统一错误体
│   │   ├── api/                  # auth / qa / chat / documents / search / kb / health
│   │   ├── services/             # 各模块业务层（能力函数）
│   │   │   └── llm/              # Provider 抽象 + providers/
│   │   ├── schemas/              # Pydantic 请求/响应模型
│   │   └── storage/              # SQLite 连接与迁移
│   └── tests/
├── web/                          # Vue 3 前端（Halden 风格统一视觉）
│   ├── package.json
│   └── src/{api,components,halden,router,state,stores,styles,utils,views}
├── data/                         # 运行期数据（git 忽略）
├── docs/
│   ├── api.md                    # API 契约
│   └── schema.md                 # 数据表设计
```

## 本地开发

### 后端

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

首次启动会自动创建 `data/app.db` 并执行 schema 迁移。探活：`curl http://127.0.0.1:8000/healthz`。

### 前端

```bash
cd web
npm install
npm run dev     # http://localhost:5173，开发服务器把 /api 代理到 127.0.0.1:8000
```

### 测试与检查

```bash
cd backend && pytest            # 后端单元与接口测试
cd backend && ruff check .      # 后端静态检查
cd web && npm run test          # 前端单元测试
cd web && npm run build         # 前端构建
```

## 部署（Docker Compose 单机）

生产模式（`APP_ENV=production`）要求提供强随机 JWT 密钥，否则后端会**拒绝启动**，
避免用仓库内的兜底密钥对外服务。

```bash
cp .env.example .env
# 生成随机密钥写入 .env（也可手动编辑该文件）
echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env

docker compose up --build -d
curl http://127.0.0.1:8000/healthz   # 后端探针
# 浏览器访问 http://127.0.0.1:8080/   前端（Nginx 同时反代 /api）
```

`data/` 通过 bind mount 挂载，容器重建后数据不丢。Nginx 的上传上限已设为 30MB，
与后端一致；超限返回统一的 JSON 错误体。

## 当前进度

- 已完成：项目骨架、账户体系（注册/登录/JWT）、SQLite 初始化与 schema 迁移、`/healthz`、Docker Compose 部署配置。
- 校园问答：知识库关键词检索（FTS5 + LIKE 兜底）、带出处回答、E3 未核实条目免责声明、拒答与会话回放。
- 学习助手：自由问答 / 复习计划 / 概念解释 / 思路点拨四种模式，多轮对话与会话回放；未配置模型时明确给出离线建议。
- 资料解析：PDF / Word / PPT 解析、原始文件按用户隔离保存、文本切片入库、摘要与提纲、Markdown 导出、针对文档提问。
- 统一搜索：知识库、共享资料、我的资料三源检索，E3 候选不进入搜索结果。
- 知识库管理：管理员录入、修改、证据等级升级、下架与批量导入。
- 模型接入：用户可保存多份 OpenAI 兼容配置（DeepSeek / 通义 / 智谱 / Kimi / 豆包 / Ollama 等），支持「测试连接」并用一次极短对话验证密钥、接口地址与模型是否可用；密钥加密存储，页面只显示掩码。
- 前端：Halden 碗状光效落地页，以及问答、助手、资料解析、搜索、知识库、模型接入六个可用页面；登录与注册统一为模态框，未登录访问功能模块会弹出登录框。
- 校园问答命中的 E3 语料按已确认口径处理：置顶固定免责声明、返回 `verified: false`、搜索结果不展示 E3 条目。
- 文档摘要与问答在用户配置模型后由模型生成；未配置或调用失败时退化为抽取式摘要 / 原文片段，功能不因缺少模型而不可用。
