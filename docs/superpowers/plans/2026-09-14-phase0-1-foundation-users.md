# Phase 0 + Phase 1（工程基础 + 用户与项目）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建药物靶点发现 Web 平台的地基：全栈 Docker 可一键启动，用户可注册/登录/配置 DeepSeek Key/管理项目/创建 Run 记录，数据隔离、Key 加密。

**Architecture:** 模块化单体。backend 为 FastAPI + SQLAlchemy 2（同步）+ psycopg，frontend 为 Next.js（App Router）。frontend 通过 `/api/*` 同源代理到 backend，认证用 HttpOnly cookie（JWT access + refresh）。数据层 PostgreSQL，Alembic 迁移。

**Tech Stack:** Python 3.12（容器）、FastAPI、SQLAlchemy 2.x、psycopg、Alembic、Pydantic v2、argon2-cffi、PyJWT、cryptography（AES-GCM）、PostgreSQL 16、Redis 7、Next.js + React + TS + Tailwind + shadcn/ui + TanStack Query、Docker Compose。

**说明：** 本计划不含 git commit（项目未初始化 git，用户已确认）。每个 Task 以「验证」作为检查点。

---

## 文件结构总览

```
targetDiscoveryWeb/
├── docker-compose.yml
├── .env.example
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── seed_admin.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── encryption.py
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── session.py
│   │   │   └── models.py
│   │   ├── schemas.py
│   │   ├── deps.py
│   │   └── api/
│   │       ├── __init__.py
│   │       └── v1/
│   │           ├── __init__.py
│   │           ├── auth.py
│   │           ├── settings.py
│   │           ├── projects.py
│   │           └── runs.py
│   └── tests/
│       ├── conftest.py
│       ├── test_security.py
│       ├── test_encryption.py
│       ├── test_auth.py
│       ├── test_settings.py
│       ├── test_projects.py
│       └── test_runs.py
└── frontend/
    ├── Dockerfile
    ├── next.config.mjs
    ├── app/
    │   ├── layout.tsx
    │   ├── page.tsx
    │   ├── login/page.tsx
    │   ├── register/page.tsx
    │   ├── dashboard/page.tsx
    │   ├── settings/api-keys/page.tsx
    │   └── projects/
    │       ├── page.tsx
    │       ├── new/page.tsx
    │       └── [id]/page.tsx
    ├── components/
    │   └── nav.tsx
    ├── lib/
    │   └── api.ts
    └── (create-next-app 生成的文件)
```

> 本增量不建 `repositories/` 与 `services/` 目录（v2 文档为后续预留）。本增量 CRUD 逻辑简单，直接在 router 层用 SQLAlchemy session，避免过度分层；Phase 2+ 逻辑复杂时再引入 service 层。

---

### Task 1: 仓库骨架 + Docker Compose + 环境变量

**Files:**
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `README.md`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@postgres:5432/app
      SECRET_KEY: ${APP_SECRET_KEY}
      CREDENTIAL_MASTER_KEY: ${APP_CREDENTIAL_MASTER_KEY}
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    build: ./frontend
    command: npm run dev
    environment:
      NODE_ENV: development
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
```

- [ ] **Step 2: 创建 .env.example**

```env
# 用 `python -c "import secrets; print(secrets.token_urlsafe(48))"` 生成
APP_SECRET_KEY=change-me
# AES-GCM 主密钥：32 字节 base64，用 `python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"` 生成
APP_CREDENTIAL_MASTER_KEY=change-me
```

- [ ] **Step 3: 创建 README.md**

```markdown
# 药物靶点发现 Web 平台

## 启动

1. 复制 `.env.example` 为 `.env`，填入 `APP_SECRET_KEY` 与 `APP_CREDENTIAL_MASTER_KEY`。
2. `docker compose up --build`

- 前端: http://localhost:3000
- 后端: http://localhost:8000（健康检查 `/healthz`）
```

- [ ] **Step 4: 验证**

Run: `docker compose up -d postgres redis`
Expected: 两个容器启动，`docker compose ps` 显示 postgres healthy、redis running。

---

### Task 2: Backend 可运行骨架（FastAPI + config + healthcheck）

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/app/__init__.py`
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/config.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: 创建 requirements.txt**

```txt
fastapi
uvicorn[standard]
sqlalchemy>=2.0
psycopg[binary]
alembic
pydantic>=2
pydantic-settings
argon2-cffi
PyJWT
cryptography
httpx
email-validator
pytest
```

- [ ] **Step 2: 创建 Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 创建 app/core/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/app"
    secret_key: str = "test-secret"
    credential_master_key: str = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    deepseek_base_url: str = "https://api.deepseek.com"


settings = Settings()
```

- [ ] **Step 4: 创建 app/main.py**

```python
from fastapi import FastAPI

from app.api.v1 import api_router

app = FastAPI(title="Target Discovery API")
app.include_router(api_router, prefix="/api/v1")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
```

- [ ] **Step 5: 创建 app/api/__init__.py 与 app/api/v1/__init__.py**

`app/api/v1/__init__.py` 先写为（后续 Task 会补 router）：

```python
from fastapi import APIRouter

api_router = APIRouter()
```

- [ ] **Step 6: 验证**

Run: `docker compose build backend`
Run: `docker compose up -d backend`
Run: `docker compose run --rm backend python -c "from app.main import app; print(app.title)"`
Expected: 打印 `Target Discovery API`。

---

### Task 3: 数据库模型（4 张表）+ Alembic 迁移

**Files:**
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models.py`

- [ ] **Step 1: 创建 app/db/base.py**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 2: 创建 app/db/session.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 3: 创建 app/db/models.py**

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, LargeBinary, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class UserStatus(str, enum.Enum):
    active = "active"
    disabled = "disabled"


class RunMode(str, enum.Enum):
    auto = "auto"
    permission = "permission"


class RunStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    waiting_permission = "waiting_permission"
    action_required = "action_required"
    completed = "completed"
    failed = "failed"
    cancelling = "cancelling"
    cancelled = "cancelled"


def _enum(cls):
    return Enum(cls, native_enum=False, values_callable=lambda e: [m.value for m in e])


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.user, nullable=False)
    status: Mapped[UserStatus] = mapped_column(_enum(UserStatus), default=UserStatus.active, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class UserLlmCredential(Base):
    __tablename__ = "user_llm_credentials"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    provider: Mapped[str] = mapped_column(String(32), default="deepseek", nullable=False)
    api_key_ciphertext: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    nonce: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    key_version: Mapped[int] = mapped_column(default=1, nullable=False)
    key_last4: Mapped[str] = mapped_column(String(8), nullable=False)
    is_validated: Mapped[bool] = mapped_column(default=False, nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    primary_disease: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    mode: Mapped[RunMode] = mapped_column(_enum(RunMode), nullable=False)
    status: Mapped[RunStatus] = mapped_column(_enum(RunStatus), default=RunStatus.queued, nullable=False)
    current_step: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_disease: Mapped[str] = mapped_column(String(255), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    workflow_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ttd_version_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    credential_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("user_llm_credentials.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 4: 初始化 Alembic**

Run: `docker compose run --rm backend alembic init alembic`

- [ ] **Step 5: 改写 alembic/env.py 与 alembic.ini**

`alembic.ini` 中 `sqlalchemy.url` 一行改为（env.py 会覆盖，但保留占位）：

```ini
sqlalchemy.url = postgresql+psycopg://postgres:postgres@postgres:5432/app
```

`alembic/env.py` 替换为：

```python
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base
from app.db import models  # noqa: F401  确保模型注册

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 6: 生成并应用迁移**

Run: `docker compose run --rm backend alembic revision --autogenerate -m "initial tables"`
Run: `docker compose run --rm backend alembic upgrade head`
Expected: 生成 `alembic/versions/xxx_initial_tables.py`，`upgrade head` 成功，无报错。

- [ ] **Step 7: 验证**

Run: `docker compose run --rm backend python -c "from app.db.models import User, Project, AnalysisRun, UserLlmCredential; print('models ok')"`
Expected: 打印 `models ok`。

---

### Task 4: 安全核心（密码哈希 + JWT + AES-GCM）

**Files:**
- Create: `backend/app/core/security.py`
- Create: `backend/app/core/encryption.py`
- Test: `backend/tests/test_security.py`
- Test: `backend/tests/test_encryption.py`

- [ ] **Step 1: 写失败测试 test_security.py**

```python
from app.core import security


def test_hash_and_verify_password():
    h = security.hash_password("secret123")
    assert h != "secret123"
    assert security.verify_password("secret123", h) is True
    assert security.verify_password("wrong", h) is False


def test_access_token_roundtrip():
    token = security.create_access_token("some-user-id")
    assert security.decode_token(token, "access") == "some-user-id"


def test_refresh_token_rejected_as_access():
    token = security.create_refresh_token("some-user-id")
    try:
        security.decode_token(token, "access")
        assert False, "should have raised"
    except Exception:
        pass
```

- [ ] **Step 2: 写失败测试 test_encryption.py**

```python
from app.core import encryption


def test_encrypt_decrypt_roundtrip():
    ct, nonce = encryption.encrypt("sk-1234567890abcdef")
    assert ct != b"sk-1234567890abcdef"
    assert encryption.decrypt(ct, nonce) == "sk-1234567890abcdef"


def test_encrypt_is_nondeterministic():
    ct1, _ = encryption.encrypt("same")
    ct2, _ = encryption.encrypt("same")
    assert ct1 != ct2
```

- [ ] **Step 3: 运行测试确认失败**

Run: `docker compose run --rm backend pytest tests/test_security.py tests/test_encryption.py -v`
Expected: FAIL（`ModuleNotFoundError: app.core.security` 或 import error）。

- [ ] **Step 4: 实现 app/core/security.py**

```python
import datetime

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import settings

_ph = PasswordHasher()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def _create_token(subject: str, token_type: str, expires_delta: datetime.timedelta) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"sub": subject, "type": token_type, "iat": now, "exp": now + expires_delta}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    return _create_token(user_id, "access", datetime.timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(user_id: str) -> str:
    return _create_token(user_id, "refresh", datetime.timedelta(days=settings.refresh_token_expire_days))


def decode_token(token: str, expected_type: str) -> str:
    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("wrong token type")
    return payload["sub"]
```

- [ ] **Step 5: 实现 app/core/encryption.py**

```python
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings


def _master_key() -> bytes:
    return base64.urlsafe_b64decode(settings.credential_master_key.encode())


def encrypt(plaintext: str) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    aesgcm = AESGCM(_master_key())
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return ciphertext, nonce


def decrypt(ciphertext: bytes, nonce: bytes) -> str:
    aesgcm = AESGCM(_master_key())
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
```

- [ ] **Step 6: 运行测试确认通过**

Run: `docker compose run --rm backend pytest tests/test_security.py tests/test_encryption.py -v`
Expected: PASS（4 个测试全部通过）。

---

### Task 5: 认证 API（register / login / logout / refresh / me）

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/deps.py`
- Create: `backend/app/api/v1/auth.py`
- Modify: `backend/app/api/v1/__init__.py`
- Test: `backend/tests/conftest.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: 创建 app/schemas.py**

```python
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    status: str

    model_config = {"from_attributes": True}


class DeepSeekKeyIn(BaseModel):
    api_key: str = Field(min_length=1)


class DeepSeekKeyStatus(BaseModel):
    configured: bool
    validated: bool
    last4: str | None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    primary_disease: str | None = None
    notes: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    primary_disease: str | None = None
    notes: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    primary_disease: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RunCreate(BaseModel):
    project_id: uuid.UUID
    disease_name: str = Field(min_length=1, max_length=255)
    mode: Literal["auto", "permission"]


class RunOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    mode: str
    status: str
    input_disease: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 创建 app/deps.py**

```python
import uuid

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import User, UserRole, UserStatus
from app.db.session import get_db


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = uuid.UUID(decode_token(token, "access"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if user is None or user.status != UserStatus.active:
        raise HTTPException(status_code=401, detail="User not found or disabled")
    return user


def require_user(user: User = Depends(get_current_user)) -> User:
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user
```

- [ ] **Step 3: 创建 app/api/v1/auth.py**

```python
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.core import security
from app.db.models import User
from app.db.session import get_db
from app.deps import require_user
from app.schemas import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_auth_cookies(response: Response, user_id: uuid.UUID):
    access = security.create_access_token(str(user_id))
    refresh = security.create_refresh_token(str(user_id))
    response.set_cookie("access_token", access, httponly=True, samesite="lax")
    response.set_cookie("refresh_token", refresh, httponly=True, samesite="lax")


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=body.email, password_hash=security.hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    _set_auth_cookies(response, user.id)
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.post("/refresh", response_model=UserOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        user_id = uuid.UUID(security.decode_token(refresh_token, "refresh"))
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    access = security.create_access_token(str(user.id))
    response.set_cookie("access_token", access, httponly=True, samesite="lax")
    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(require_user)):
    return user
```

- [ ] **Step 4: 更新 app/api/v1/__init__.py 注册 router**

```python
from fastapi import APIRouter

from app.api.v1 import auth

api_router = APIRouter()
api_router.include_router(auth.router)
```

- [ ] **Step 5: 创建 tests/conftest.py**

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal
    app.dependency_overrides.clear()


@pytest.fixture
def make_client(db_session):
    return lambda: TestClient(app)
```

- [ ] **Step 6: 写失败测试 test_auth.py**

```python
def register(client, email="a@example.com", password="password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def test_register_and_me(make_client):
    c = make_client()
    r = register(c)
    assert r.status_code == 201
    assert r.json()["email"] == "a@example.com"


def test_register_duplicate_email(make_client):
    c = make_client()
    register(c)
    r = register(c)
    assert r.status_code == 400


def test_login_sets_cookie_and_me(make_client):
    c = make_client()
    register(c)
    r = c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert "access_token" in c.cookies
    me = c.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


def test_login_wrong_password(make_client):
    c = make_client()
    register(c)
    r = c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_me_requires_auth(make_client):
    c = make_client()
    assert c.get("/api/v1/auth/me").status_code == 401


def test_refresh(make_client):
    c = make_client()
    register(c)
    c.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})
    c.cookies.delete("access_token")
    r = c.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert "access_token" in c.cookies
```

- [ ] **Step 7: 运行测试确认失败**

Run: `docker compose run --rm backend pytest tests/test_auth.py -v`
Expected: FAIL（`ModuleNotFoundError: app.api.v1.auth` 或相关 import error）。

- [ ] **Step 8: 运行测试确认通过**

Run: `docker compose run --rm backend pytest tests/test_auth.py -v`
Expected: PASS（6 个测试全部通过）。

- [ ] **Step 9: 验证（回归）**

Run: `docker compose run --rm backend pytest tests/ -v`
Expected: 全部通过（Task 4 的 4 个 + Task 5 的 6 个）。

---

### Task 6: DeepSeek Key 设置 API

**Files:**
- Create: `backend/app/api/v1/settings.py`
- Modify: `backend/app/api/v1/__init__.py`
- Test: `backend/tests/test_settings.py`

- [ ] **Step 1: 创建 app/api/v1/settings.py**

```python
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core import encryption
from app.core.config import settings as app_settings
from app.db.models import User, UserLlmCredential
from app.db.session import get_db
from app.deps import require_user
from app.schemas import DeepSeekKeyIn, DeepSeekKeyStatus

router = APIRouter(prefix="/settings", tags=["settings"])


def _status(db: Session, user_id: uuid.UUID) -> DeepSeekKeyStatus:
    cred = db.query(UserLlmCredential).filter(UserLlmCredential.user_id == user_id).first()
    if cred is None:
        return DeepSeekKeyStatus(configured=False, validated=False, last4=None)
    return DeepSeekKeyStatus(configured=True, validated=cred.is_validated, last4=cred.key_last4)


@router.put("/deepseek-key", response_model=DeepSeekKeyStatus)
def upsert_key(body: DeepSeekKeyIn, user: User = Depends(require_user), db: Session = Depends(get_db)):
    ciphertext, nonce = encryption.encrypt(body.api_key)
    cred = db.query(UserLlmCredential).filter(UserLlmCredential.user_id == user.id).first()
    if cred is None:
        cred = UserLlmCredential(user_id=user.id, provider="deepseek")
        db.add(cred)
    cred.api_key_ciphertext = ciphertext
    cred.nonce = nonce
    cred.key_last4 = body.api_key[-4:]
    cred.is_validated = False
    cred.validated_at = None
    db.commit()
    return _status(db, user.id)


@router.get("/deepseek-key/status", response_model=DeepSeekKeyStatus)
def key_status(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return _status(db, user.id)


@router.post("/deepseek-key/validate", response_model=DeepSeekKeyStatus)
def validate_key(user: User = Depends(require_user), db: Session = Depends(get_db)):
    cred = db.query(UserLlmCredential).filter(UserLlmCredential.user_id == user.id).first()
    if cred is None:
        raise HTTPException(status_code=404, detail="No key configured")
    api_key = encryption.decrypt(cred.api_key_ciphertext, cred.nonce)
    try:
        r = httpx.get(
            f"{app_settings.deepseek_base_url}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        cred.is_validated = r.status_code == 200
    except httpx.HTTPError:
        cred.is_validated = False
    cred.validated_at = datetime.now(timezone.utc)
    db.commit()
    return _status(db, user.id)


@router.delete("/deepseek-key", response_model=DeepSeekKeyStatus)
def delete_key(user: User = Depends(require_user), db: Session = Depends(get_db)):
    cred = db.query(UserLlmCredential).filter(UserLlmCredential.user_id == user.id).first()
    if cred is not None:
        db.delete(cred)
        db.commit()
    return _status(db, user.id)
```

- [ ] **Step 2: 更新 app/api/v1/__init__.py**

```python
from fastapi import APIRouter

from app.api.v1 import auth, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(settings.router)
```

- [ ] **Step 3: 写失败测试 test_settings.py**

```python
def _register_and_login(client):
    client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "password123"})
    client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "password123"})


def test_key_upsert_and_status(make_client):
    c = make_client()
    _register_and_login(c)
    r = c.put("/api/v1/settings/deepseek-key", json={"api_key": "sk-abcdefgh1234"})
    assert r.status_code == 200
    assert r.json()["configured"] is True
    assert r.json()["last4"] == "1234"

    s = c.get("/api/v1/settings/deepseek-key/status")
    assert s.json()["last4"] == "1234"


def test_key_not_plaintext_in_db(make_client, db_session):
    c = make_client()
    _register_and_login(c)
    c.put("/api/v1/settings/deepseek-key", json={"api_key": "sk-abcdefgh1234"})

    from app.db.models import UserLlmCredential

    db = db_session()
    cred = db.query(UserLlmCredential).first()
    db.close()
    assert cred is not None
    assert b"sk-abcdefgh1234" not in cred.api_key_ciphertext


def test_key_delete(make_client):
    c = make_client()
    _register_and_login(c)
    c.put("/api/v1/settings/deepseek-key", json={"api_key": "sk-abcdefgh1234"})
    r = c.delete("/api/v1/settings/deepseek-key")
    assert r.status_code == 200
    assert r.json()["configured"] is False


def test_validate_requires_key(make_client):
    c = make_client()
    _register_and_login(c)
    r = c.post("/api/v1/settings/deepseek-key/validate")
    assert r.status_code == 404
```

- [ ] **Step 4: 运行测试确认失败**

Run: `docker compose run --rm backend pytest tests/test_settings.py -v`
Expected: FAIL（import error）。

- [ ] **Step 5: 运行测试确认通过**

Run: `docker compose run --rm backend pytest tests/test_settings.py -v`
Expected: PASS（4 个测试通过；`test_validate_requires_key` 不触发真实网络）。

---

### Task 7: Projects API

**Files:**
- Create: `backend/app/api/v1/projects.py`
- Modify: `backend/app/api/v1/__init__.py`
- Test: `backend/tests/test_projects.py`

- [ ] **Step 1: 创建 app/api/v1/projects.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Project, User
from app.db.session import get_db
from app.deps import require_user
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


def _get_owned_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == user.id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.user_id == user.id).order_by(Project.created_at.desc()).all()


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(body: ProjectCreate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    project = Project(user_id=user.id, name=body.name, primary_disease=body.primary_disease, notes=body.notes)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: uuid.UUID, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return _get_owned_project(db, project_id, user)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: uuid.UUID, body: ProjectUpdate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    project = _get_owned_project(db, project_id, user)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: uuid.UUID, user: User = Depends(require_user), db: Session = Depends(get_db)):
    project = _get_owned_project(db, project_id, user)
    db.delete(project)
    db.commit()
    return {"ok": True}
```

- [ ] **Step 2: 更新 app/api/v1/__init__.py**

```python
from fastapi import APIRouter

from app.api.v1 import auth, projects, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(projects.router)
```

- [ ] **Step 3: 写失败测试 test_projects.py**

```python
def _user(client, email):
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})


def test_project_crud(make_client):
    c = make_client()
    _user(c, "a@example.com")
    r = c.post("/api/v1/projects", json={"name": "AD Project", "primary_disease": "Alzheimer's disease"})
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["name"] == "AD Project"

    assert c.get("/api/v1/projects").json()[0]["id"] == pid
    p = c.patch(f"/api/v1/projects/{pid}", json={"name": "AD Project v2"})
    assert p.json()["name"] == "AD Project v2"
    assert c.delete(f"/api/v1/projects/{pid}").status_code == 200
    assert c.get("/api/v1/projects").json() == []


def test_project_isolation(make_client):
    a = make_client()
    b = make_client()
    _user(a, "a@example.com")
    _user(b, "b@example.com")
    r = a.post("/api/v1/projects", json={"name": "A's project"})
    pid = r.json()["id"]
    # b 访问 a 的项目应 404
    assert b.get(f"/api/v1/projects/{pid}").status_code == 404
    # b 的列表为空
    assert b.get("/api/v1/projects").json() == []
```

- [ ] **Step 4: 运行测试确认失败**

Run: `docker compose run --rm backend pytest tests/test_projects.py -v`
Expected: FAIL（import error）。

- [ ] **Step 5: 运行测试确认通过**

Run: `docker compose run --rm backend pytest tests/test_projects.py -v`
Expected: PASS（2 个测试通过）。

---

### Task 8: Runs API + RBAC 依赖 + 数据隔离

**Files:**
- Create: `backend/app/api/v1/runs.py`
- Modify: `backend/app/api/v1/__init__.py`
- Test: `backend/tests/test_runs.py`

- [ ] **Step 1: 创建 app/api/v1/runs.py**

```python
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import AnalysisRun, Project, RunMode, User
from app.db.session import get_db
from app.deps import require_user
from app.schemas import RunCreate, RunOut

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=201)
def create_run(body: RunCreate, user: User = Depends(require_user), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == body.project_id, Project.user_id == user.id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    run = AnalysisRun(
        project_id=body.project_id,
        user_id=user.id,
        mode=RunMode(body.mode),
        input_disease=body.disease_name,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("", response_model=list[RunOut])
def list_runs(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return db.query(AnalysisRun).filter(AnalysisRun.user_id == user.id).order_by(AnalysisRun.created_at.desc()).all()


@router.get("/{run_id}", response_model=RunOut)
def get_run(run_id: uuid.UUID, user: User = Depends(require_user), db: Session = Depends(get_db)):
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id, AnalysisRun.user_id == user.id).first()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run
```

- [ ] **Step 2: 更新 app/api/v1/__init__.py**

```python
from fastapi import APIRouter

from app.api.v1 import auth, projects, runs, settings

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(settings.router)
api_router.include_router(projects.router)
api_router.include_router(runs.router)
```

- [ ] **Step 3: 写失败测试 test_runs.py**

```python
def _user(client, email):
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})


def _project(client):
    return client.post("/api/v1/projects", json={"name": "P"}).json()["id"]


def test_create_and_list_run(make_client):
    c = make_client()
    _user(c, "a@example.com")
    pid = _project(c)
    r = c.post("/api/v1/runs", json={"project_id": pid, "disease_name": "Alzheimer's disease", "mode": "auto"})
    assert r.status_code == 201
    assert r.json()["status"] == "queued"
    assert r.json()["mode"] == "auto"
    runs = c.get("/api/v1/runs").json()
    assert len(runs) == 1


def test_create_run_requires_owned_project(make_client):
    a = make_client()
    b = make_client()
    _user(a, "a@example.com")
    _user(b, "b@example.com")
    pid = _project(a)
    r = b.post("/api/v1/runs", json={"project_id": pid, "disease_name": "X", "mode": "auto"})
    assert r.status_code == 404


def test_run_isolation(make_client):
    a = make_client()
    b = make_client()
    _user(a, "a@example.com")
    _user(b, "b@example.com")
    pid = _project(a)
    run_id = a.post("/api/v1/runs", json={"project_id": pid, "disease_name": "X", "mode": "auto"}).json()["id"]
    assert b.get(f"/api/v1/runs/{run_id}").status_code == 404
    assert b.get("/api/v1/runs").json() == []
```

- [ ] **Step 4: 运行测试确认失败 → 通过**

Run: `docker compose run --rm backend pytest tests/test_runs.py -v`
Expected: 先 FAIL（import error），实现后 PASS（3 个测试通过）。

---

### Task 9: Admin seed 脚本

**Files:**
- Create: `backend/seed_admin.py`

- [ ] **Step 1: 创建 backend/seed_admin.py**

```python
import argparse

from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import SessionLocal


def seed(email: str, password: str):
    db = SessionLocal()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        print(f"User {email} already exists, skipping.")
        return
    user = User(email=email, password_hash=hash_password(password), role=UserRole.admin)
    db.add(user)
    db.commit()
    print(f"Created admin {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    seed(args.email, args.password)
```

- [ ] **Step 2: 验证**

Run: `docker compose run --rm backend python seed_admin.py --email admin@example.edu --password change-me-123`
Expected: 打印 `Created admin admin@example.edu`；重复执行打印 `already exists, skipping.`

---

### Task 10: 前端骨架（Next.js + Tailwind + shadcn + 布局 + 守卫 + api client）

**Files:**
- Create: `frontend/`（create-next-app 生成）
- Create: `frontend/Dockerfile`
- Create: `frontend/next.config.mjs`
- Create: `frontend/lib/api.ts`
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/components/nav.tsx`
- Create: `frontend/app/page.tsx`

- [ ] **Step 1: 用 create-next-app 初始化 frontend**

Run: `cd targetDiscoveryWeb && npx create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir=false --import-alias "@/*" --use-npm --yes`
Expected: 生成 `frontend/`，含 `app/`、`components/`、`lib/` 等。

- [ ] **Step 2: 初始化 shadcn/ui**

Run: `cd targetDiscoveryWeb/frontend && npx shadcn@latest init -d`
Run: `cd targetDiscoveryWeb/frontend && npx shadcn@latest add button input card label form`

- [ ] **Step 3: 创建 frontend/Dockerfile**

```dockerfile
FROM node:22-alpine

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .

EXPOSE 3000
CMD ["npm", "run", "dev"]
```

- [ ] **Step 4: 创建 frontend/next.config.mjs（同源代理 /api）**

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://backend:8000/api/:path*" },
    ];
  },
};

export default nextConfig;
```

- [ ] **Step 5: 创建 frontend/lib/api.ts**

```ts
export type User = {
  id: string;
  email: string;
  role: string;
  status: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error((body as any).detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/v1/auth/me"),
  login: (email: string, password: string) =>
    request<User>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string) =>
    request<User>("/api/v1/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  logout: () => request<{ ok: boolean }>("/api/v1/auth/logout", { method: "POST" }),
};
```

- [ ] **Step 6: 改写 frontend/app/layout.tsx**

```tsx
import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/nav";

export const metadata: Metadata = { title: "药物靶点发现平台" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <Nav />
        <main className="max-w-5xl mx-auto p-6">{children}</main>
      </body>
    </html>
  );
}
```

- [ ] **Step 7: 创建 frontend/components/nav.tsx**

```tsx
"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type User } from "@/lib/api";

export default function Nav() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => setUser(null));
  }, []);

  return (
    <nav className="border-b p-4 flex gap-4 items-center text-sm">
      <Link href="/" className="font-semibold">靶点发现平台</Link>
      {user ? (
        <>
          <Link href="/dashboard">工作台</Link>
          <Link href="/projects">项目</Link>
          <Link href="/settings/api-keys">API Key</Link>
          <span className="ml-auto text-muted-foreground">{user.email}</span>
          <button
            onClick={async () => {
              await api.logout();
              window.location.href = "/login";
            }}
            className="text-sm underline"
          >
            退出
          </button>
        </>
      ) : (
        <span className="ml-auto flex gap-4">
          <Link href="/login">登录</Link>
          <Link href="/register">注册</Link>
        </span>
      )}
    </nav>
  );
}
```

- [ ] **Step 8: 改写 frontend/app/page.tsx（首页跳转）**

```tsx
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    api.me().then(() => router.push("/dashboard")).catch(() => router.push("/login"));
  }, [router]);
  return <p>加载中…</p>;
}
```

- [ ] **Step 9: 验证**

Run: `docker compose build frontend`
Run: `docker compose up -d frontend`
Expected: 打开 http://localhost:3000 能显示页面并跳转（未登录跳 /login）。

---

### Task 11: 前端页面（login / register / dashboard / api-keys / projects）

**Files:**
- Create: `frontend/app/login/page.tsx`
- Create: `frontend/app/register/page.tsx`
- Create: `frontend/app/dashboard/page.tsx`
- Create: `frontend/app/settings/api-keys/page.tsx`
- Create: `frontend/app/projects/page.tsx`
- Create: `frontend/app/projects/new/page.tsx`
- Create: `frontend/app/projects/[id]/page.tsx`
- Modify: `frontend/lib/api.ts`（补 projects / key 接口）

- [ ] **Step 1: 扩展 frontend/lib/api.ts**

在 `api` 对象内追加：

```ts
export type Project = {
  id: string;
  name: string;
  primary_disease: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type KeyStatus = { configured: boolean; validated: boolean; last4: string | null };

// 追加到 api 对象：
  projects: {
    list: () => request<Project[]>("/api/v1/projects"),
    create: (data: { name: string; primary_disease?: string; notes?: string }) =>
      request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(data) }),
  },
  deepseekKey: {
    status: () => request<KeyStatus>("/api/v1/settings/deepseek-key/status"),
    upsert: (api_key: string) =>
      request<KeyStatus>("/api/v1/settings/deepseek-key", { method: "PUT", body: JSON.stringify({ api_key }) }),
    remove: () => request<KeyStatus>("/api/v1/settings/deepseek-key", { method: "DELETE" }),
  },
```

- [ ] **Step 2: 创建 login/page.tsx**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  return (
    <div className="max-w-sm mx-auto space-y-4">
      <h1 className="text-xl font-semibold">登录</h1>
      <Input type="email" placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <Button
        onClick={async () => {
          try {
            await api.login(email, password);
            router.push("/dashboard");
          } catch (e: any) {
            setError(e.message);
          }
        }}
      >
        登录
      </Button>
    </div>
  );
}
```

- [ ] **Step 3: 创建 register/page.tsx**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  return (
    <div className="max-w-sm mx-auto space-y-4">
      <h1 className="text-xl font-semibold">注册</h1>
      <Input type="email" placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
      <Input type="password" placeholder="密码（至少 8 位）" value={password} onChange={(e) => setPassword(e.target.value)} />
      {error && <p className="text-red-500 text-sm">{error}</p>}
      <Button
        onClick={async () => {
          try {
            await api.register(email, password);
            router.push("/login");
          } catch (e: any) {
            setError(e.message);
          }
        }}
      >
        注册
      </Button>
    </div>
  );
}
```

- [ ] **Step 4: 创建 dashboard/page.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type KeyStatus, type User } from "@/lib/api";

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);
  const [key, setKey] = useState<KeyStatus | null>(null);

  useEffect(() => {
    api.me().then(setUser).catch(() => {});
    api.deepseekKey.status().then(setKey).catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">工作台</h1>
      {user && <p>你好，{user.email}</p>}
      <p>
        DeepSeek Key：
        {key?.configured ? `已配置 (…${key.last4})` : "未配置"}
      </p>
      {!key?.configured && (
        <Link href="/settings/api-keys" className="underline">去配置 API Key</Link>
      )}
    </div>
  );
}
```

- [ ] **Step 5: 创建 settings/api-keys/page.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import { api, type KeyStatus } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function ApiKeysPage() {
  const [key, setKey] = useState<KeyStatus | null>(null);
  const [value, setValue] = useState("");
  const [msg, setMsg] = useState("");

  const refresh = () => api.deepseekKey.status().then(setKey);
  useEffect(() => {
    refresh().catch(() => {});
  }, []);

  return (
    <div className="space-y-4 max-w-sm">
      <h1 className="text-xl font-semibold">DeepSeek API Key</h1>
      {key?.configured && <p>当前已配置，尾号 …{key.last4}（验证状态：{key.validated ? "已验证" : "未验证"}）</p>}
      <Input type="password" placeholder="粘贴新的 API Key" value={value} onChange={(e) => setValue(e.target.value)} />
      {msg && <p className="text-sm text-muted-foreground">{msg}</p>}
      <Button
        onClick={async () => {
          await api.deepseekKey.upsert(value);
          setValue("");
          setMsg("已保存");
          refresh();
        }}
      >
        保存
      </Button>
      {key?.configured && (
        <Button variant="destructive" onClick={async () => { await api.deepseekKey.remove(); refresh(); }}>
          删除
        </Button>
      )}
    </div>
  );
}
```

- [ ] **Step 6: 创建 projects/page.tsx**

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Project } from "@/lib/api";
import { Button } from "@/components/ui/button";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);

  useEffect(() => {
    api.projects.list().then(setProjects).catch(() => {});
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-semibold">项目</h1>
        <Link href="/projects/new"><Button>新建项目</Button></Link>
      </div>
      {projects.length === 0 ? (
        <p className="text-muted-foreground">还没有项目。</p>
      ) : (
        <ul className="space-y-2">
          {projects.map((p) => (
            <li key={p.id} className="border rounded p-3">
              <Link href={`/projects/${p.id}`} className="font-medium">{p.name}</Link>
              {p.primary_disease && <p className="text-sm text-muted-foreground">{p.primary_disease}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **Step 7: 创建 projects/new/page.tsx**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [disease, setDisease] = useState("");

  return (
    <div className="space-y-4 max-w-sm">
      <h1 className="text-xl font-semibold">新建项目</h1>
      <Input placeholder="项目名称" value={name} onChange={(e) => setName(e.target.value)} />
      <Input placeholder="主要疾病（可选）" value={disease} onChange={(e) => setDisease(e.target.value)} />
      <Button
        onClick={async () => {
          const p = await api.projects.create({ name, primary_disease: disease || undefined });
          router.push(`/projects/${p.id}`);
        }}
      >
        创建
      </Button>
    </div>
  );
}
```

- [ ] **Step 8: 创建 projects/[id]/page.tsx**

```tsx
"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Project } from "@/lib/api";

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);

  useEffect(() => {
    api.projects.list().then((list) => setProject(list.find((p) => p.id === id) ?? null));
  }, [id]);

  if (!project) return <p>加载中…</p>;
  return (
    <div className="space-y-2">
      <h1 className="text-2xl font-semibold">{project.name}</h1>
      {project.primary_disease && <p>主要疾病：{project.primary_disease}</p>}
      {project.notes && <p>{project.notes}</p>}
      <p className="text-muted-foreground text-sm">（本阶段暂不显示 Run 列表，Phase 3 补充）</p>
    </div>
  );
}
```

- [ ] **Step 9: 验证**

Run: `docker compose up -d frontend`
Expected: 依次访问 /login、/register、/dashboard、/settings/api-keys、/projects、/projects/new 均可正常渲染；登录后导航出现用户邮箱与「退出」按钮。

---

### Task 12: 端到端验证（真实 Postgres + 迁移 + 手动流程）

- [ ] **Step 1: 全栈启动**

Run: `docker compose up -d --build`
Expected: postgres healthy，redis / backend / frontend 全部 running。

- [ ] **Step 2: 执行迁移（若未自动执行）**

Run: `docker compose run --rm backend alembic upgrade head`
Expected: 无报错，`alembic_version` 表出现。

- [ ] **Step 3: 创建 admin**

Run: `docker compose run --rm backend python seed_admin.py --email admin@example.edu --password change-me-123`

- [ ] **Step 4: 后端冒烟（curl）**

Run: `docker compose run --rm backend python -c "import httpx; print(httpx.get('http://backend:8000/healthz').json())"`
Expected: `{'status': 'ok'}`。

- [ ] **Step 5: 完整用户流程验证**

在浏览器执行：注册 → 配置 DeepSeek Key → 新建项目 → （Phase 3 才有真实 Run，本增量 Run 创建按钮暂缺，可用 API 验证）→ 退出 → 用另一账号登录确认看不到前者的项目。

- [ ] **Step 6: 运行全部测试**

Run: `docker compose run --rm backend pytest tests/ -v`
Expected: 全部通过。

---

## Self-Review 记录

- **Spec 覆盖**：§3 目录 → Task 1/2/10；§4 Compose → Task 1；§5 数据模型 → Task 3；§6 认证安全 → Task 4/5/6；§7 API → Task 5–8；§8 前端 → Task 10/11；§9 验收 → Task 12；§10 测试 → Task 4–8/12。
- **类型一致性**：`UserLlmCredential.user_id` 为 `unique=True`（spec 的 `UNIQUE(user_id, provider)` 简化为 user 级唯一，本增量单 provider）；`RunStatus.waiting_permission` 等枚举在 models 与 schemas 用字符串值一致；`UserOut.role`/`status` 用 `str`（Python str-enum 自动兼容 `from_attributes`）。
- **测试隔离**：conftest 用 `db_session` fixture 暴露测试 SQLite 会话工厂，密文验证测试直接查测试库、不连真实 Postgres；`make_client` 依赖该 fixture，返回 `TestClient` 签名不变。
