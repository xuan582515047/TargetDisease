# 药物靶点发现 Web 平台 — Phase 0 + Phase 1 增量设计

> 创建日期: 2026-09-14
> 来源文档: `target_discovery_web_v2_design.md`（本文件是对该文档 Phase 0 / Phase 1 的落地细化，不覆盖原文档）
> 目标: 搭建多用户 Web 科研平台的地基（工程基础 + 用户与项目），为后续工作流、权限检查点、结果工作台、TTD 管理打底

---

## 1. 目标与本增量范围

本增量只交付 **Phase 0（工程基础）** 与 **Phase 1（用户与项目）**，产物是一个可一键启动、可注册登录、数据隔离、DeepSeek Key 加密存储的多用户平台骨架。

**本增量完成后，用户能够：**
- 注册 / 登录 / 登出 / 刷新会话；
- 配置并验证自己的 DeepSeek API Key（加密落库，不明文）；
- 创建、查看、修改、删除自己的项目（Project）；
- 创建并查看一次分析（Run）的**数据记录**（本增量只落库，不触发真实工作流）。

**本增量不包含（YAGNI，显式推迟）：**
- Celery 异步任务、SSE、工作流状态机（Phase 3）；
- permission 检查点与人工审批（Phase 4）；
- 结果工作台、Mol* 三维结构（Phase 5）；
- TTD 上传/校验/导入/激活（Phase 6）；
- nginx / HTTPS / 监控 / 备份（Phase 7）；
- `pocket_center` 坐标算法（Phase 2 结构专家前再定，数据模型先留 `pending` 占位）；
- 邮箱验证、密码找回（学校内网系统，第一版不做）。

---

## 2. 关键决策（本增量已拍板）

| 决策点 | 决定 | 理由 |
|---|---|---|
| 增量起点 | Phase 0 + Phase 1 | 文档自身顺序，地基先行、风险低 |
| 运行方式 | 全栈 Docker | 宿主机 Python 3.8 太老；Docker 统一运行环境并复用部署模型 |
| 后端 Python 版本 | 3.12（容器内） | 满足 FastAPI / SQLAlchemy 2 / Pydantic v2 / Celery 要求 |
| 数据库访问 | SQLAlchemy 2.x **同步** + psycopg | 与现有引擎同步代码一致，降低 Phase 2 迁移成本；学校负载下同步足够 |
| 密码哈希 | Argon2id | 文档已定 |
| 认证 | JWT access + refresh，HttpOnly cookie | 文档已定 |
| DeepSeek Key | AES-GCM 信封加密，主密钥 `APP_CREDENTIAL_MASTER_KEY` | 文档已定，禁止明文 |
| `pocket_center` | 先留 `pending` 占位 | 不阻塞本增量；模型已预留，无需重构 |
| 前端代理 | Next.js rewrites 把 `/api/*` 代理到 backend | 前后端同源，cookie 与 CORS 最简单；生产由 nginx 同构代理 |

---

## 3. 目录结构

新建 `targetDiscoveryWeb/`，与现有 `Disease/` 平级，互不覆盖：

```
targetDiscoveryWeb/
├── frontend/                 # Next.js (App Router) + React + TS
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── lib/                  # api client、cookie 处理
│   └── types/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── v1/           # auth.py, settings.py, projects.py, runs.py
│   │   ├── core/             # config.py, security.py, encryption.py
│   │   ├── db/               # base.py, session.py, models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── deps.py           # require_user / require_admin 依赖
│   ├── alembic/
│   ├── seed_admin.py         # 创建初始 admin
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

> `targetDiscoveryWeb/` 是独立目录，现有 `Disease/`（v1 CLI + engine）保持原样，仅作为后续 Phase 2 引擎迁移的源码来源。

---

## 4. Docker Compose 服务

| 服务 | 镜像/基础 | 说明 |
|---|---|---|
| `postgres` | postgres:16 | 数据卷持久化；健康检查 |
| `redis` | redis:7 | 本增量仅起好预留，Phase 3 启用 |
| `backend` | python:3.12-slim | uvicorn，代码 volume 挂载热重载，`depends_on` postgres |
| `frontend` | node:22-alpine | `next dev`，`/api` rewrite 到 backend |

- 数据卷：`postgres_data`（持久化数据库）。
- `nginx`、`worker`（celery）本增量**不引入**，避免骨架过重。

---

## 5. 数据模型（本增量建 4 张表）

统一使用 UUID 主键、`created_at` / `updated_at` 时间戳。由 Alembic 管理迁移。

### 5.1 `users`
- `id` UUID PK
- `email` VARCHAR UNIQUE NOT NULL
- `password_hash` TEXT NOT NULL（Argon2id）
- `role` ENUM('user','admin') 默认 'user'
- `status` ENUM('active','disabled') 默认 'active'
- `created_at` / `updated_at` / `last_login_at`（可空）

### 5.2 `user_llm_credentials`
- `id` UUID PK
- `user_id` FK → users NOT NULL
- `provider` VARCHAR 默认 'deepseek'
- `api_key_ciphertext` BYTEA NOT NULL
- `nonce` BYTEA NOT NULL
- `key_version` INT 默认 1
- `key_last4` VARCHAR(8)
- `is_validated` BOOLEAN 默认 false
- `validated_at` TIMESTAMP 可空
- `created_at` / `updated_at`
- 约束：`UNIQUE(user_id, provider)`（每用户每 provider 一条，替换即更新）

> **硬约束**：数据库与日志中永不出现明文 Key；GET 接口只返回 `key_last4`。

### 5.3 `projects`
- `id` UUID PK
- `user_id` FK → users NOT NULL
- `name` VARCHAR NOT NULL
- `primary_disease` VARCHAR 可空
- `notes` TEXT 可空
- `created_at` / `updated_at`

### 5.4 `analysis_runs`
- `id` UUID PK
- `project_id` FK → projects NOT NULL
- `user_id` FK → users NOT NULL
- `mode` ENUM('auto','permission') NOT NULL
- `status` ENUM('queued','running','waiting_permission','action_required','completed','failed','cancelling','cancelled') 默认 'queued'
- `current_step` VARCHAR 可空
- `input_disease` VARCHAR NOT NULL
- `model_name` VARCHAR 可空
- `prompt_version` VARCHAR 可空
- `workflow_version` VARCHAR 可空
- `ttd_version_id` UUID 可空（**外键到 Phase 6 建 `ttd_versions` 表时再补**）
- `credential_id` FK → user_llm_credentials 可空
- `created_at` / `started_at` / `completed_at` / `failed_at` / `cancelled_at`（均可空）
- `error_code` VARCHAR 可空 / `error_message` TEXT 可空

> 每次 Run 固定保存 `mode / model_name / prompt_version / workflow_version / ttd_version_id / credential_id`，保证历史结果可复现（本增量仅预留字段，写入逻辑在 Phase 3）。

---

## 6. 认证与安全

- **密码**：Argon2id，用 `argon2-cffi` 库实现。
- **会话**：登录发放 access token（短时效，约 15 分钟）与 refresh token（长时效，约 7 天），均存 HttpOnly cookie；`SameSite=Lax`，生产 `Secure`；refresh 通过 `POST /auth/refresh` 换新 access。
- **CSRF**：SameSite=Lax + 对写操作校验 Origin（同源代理下天然收敛）。
- **DeepSeek Key 加密**：AES-256-GCM 信封加密。主密钥 `APP_CREDENTIAL_MASTER_KEY` 从环境变量读取；数据库只存 `ciphertext / nonce / key_version / last4`；解密仅发生在进程内存（本增量即保存/验证时）。
- **RBAC**：FastAPI 依赖 `require_user()` 与 `require_admin()`。
- **数据隔离**：所有用户资源查询强制 `WHERE user_id = current_user.id`（管理员例外）；不依赖前端隐藏按钮。
- **日志脱敏**：任何日志禁止记录 Authorization 头、DeepSeek Key、解密后凭据。

---

## 7. API 设计（前缀 `/api/v1`，前端经 `/api` 同源代理）

### 7.1 Auth
- `POST /auth/register` — `{email, password}` → 201 创建用户
- `POST /auth/login` — `{email, password}` → 设置 cookie，返回当前用户
- `POST /auth/logout` — 清 cookie
- `POST /auth/refresh` — 用 refresh token 换新 access
- `GET  /auth/me` — 返回当前用户

### 7.2 DeepSeek Key（`/settings/deepseek-key`）
- `PUT` — `{api_key}` → AES-GCM 加密保存（替换旧值）
- `POST /validate` — 调 DeepSeek 做最小验证，失败不回显原 Key
- `DELETE` — 删除当前用户的 Key
- `GET /status` — `{configured, validated, last4}`（永不返回完整 Key）

### 7.3 Projects
- `GET /projects` — 当前用户的项目列表
- `POST /projects` — `{name, primary_disease?, notes?}`
- `GET /projects/{id}` — 校验归属
- `PATCH /projects/{id}` — 校验归属
- `DELETE /projects/{id}` — 校验归属

### 7.4 Runs
- `POST /runs` — `{project_id, disease_name, mode}` → 创建 `analysis_runs`（status=queued，**不触发工作流**）
- `GET /runs` — 当前用户的 Run 列表
- `GET /runs/{id}` — 校验归属

> 约定：成功直接返回资源对象；错误统一用 FastAPI `HTTPException`（HTTP 状态码 + `detail` 字段），不额外包裹。

---

## 8. 前端页面（骨架，界面中文）

- `/login`、`/register`
- `/dashboard`（占位：显示欢迎、Key 是否已配置）
- `/projects`、`/projects/new`、`/projects/[id]`（骨架）
- `/settings/api-keys`（配置 / 验证 / 删除 DeepSeek Key）
- 认证守卫（未登录跳 `/login`）+ 顶部导航

技术栈：Next.js（App Router）+ React + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query。

---

## 9. 验收标准（本增量完成即满足）

1. `docker compose up` 一键启动，Alembic 迁移正常跑通。
2. 注册 / 登录 / 登出 / refresh 可用。
3. 不同用户数据隔离：一个用户看不到另一个用户的 Project / Run。
4. DeepSeek Key 加密落库、绝不明文；查询只返回 `last4`。
5. Project CRUD 可用。
6. Run 可创建、可查询（status 初始为 `queued`）。
7. 存在 admin 角色机制 + 一个 seed admin 账号。

---

## 10. 测试策略（本增量）

- **后端单元测试**：密码哈希、JWT 签发/校验、AES-GCM 加解密、Argon2id roundtrip。
- **后端集成测试**：注册/登录/refresh 流程、Project/Run 归属隔离、Key 保存后 DB 无明文。
- **前端**：认证守卫、登录表单、Key 配置页（可选，Phase 3 再加强）。

---

## 11. 明确不做的清单（防止范围蔓延）

- 不引入 Celery / SSE / 工作流（Phase 3）。
- 不做 permission 检查点（Phase 4）。
- 不做 Mol* / 报告导出（Phase 5）。
- 不做 TTD 上传与管理（Phase 6）。
- 不部署 nginx / HTTPS（Phase 7）。
- 不实现 `pocket_center` 算法（先 `pending`）。
- 不做邮箱验证 / 密码找回 / 多租户计费。
