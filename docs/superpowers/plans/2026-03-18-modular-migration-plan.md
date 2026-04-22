# pjtmgr 모듈화 마이그레이션 구현 계획

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** pjtmgr를 공통/회계/인프라 3개 모듈로 재구성하고, inframgr 코드를 인프라모듈로 이식하며, RBAC와 PostgreSQL로 전환한다.

**Architecture:** 단일 코드베이스에서 `ENABLED_MODULES` 환경변수로 모듈을 선택적 활성화. `app/core/`에 모듈 독립 인프라, `app/modules/{common,accounting,infra}/`에 도메인별 코드 배치. 모듈 간 의존성은 `core ← common ← {accounting, infra}` 단방향만 허용.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Alembic, Jinja2, HTMX, AG Grid, bcrypt, pytest

**Spec:** `docs/superpowers/specs/2026-03-18-modular-migration-design.md`

**inframgr 참조:** `docs/inframgr-reference/` (모든 원본 소스코드 보관)

---

## 사전 준비

- [ ] **Pre-1: git tag 생성**

```bash
git tag pre-migration
```

- [ ] **Pre-2: 현재 테스트 상태 확인**

```bash
pytest tests/ -v --tb=short
```

모든 테스트가 통과하는 상태에서 시작해야 한다. 실패하는 테스트가 있으면 먼저 해결한다.

---

## Task 1: 지침 및 문서 재편

**Files:**

- Modify: `CLAUDE.md`
- Modify: `README.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/guidelines/backend.md`
- Modify: `docs/guidelines/auth.md`
- Modify: `docs/guidelines/frontend.md`
- Modify: `docs/PROJECT_STRUCTURE.md`
- Modify: `docs/KNOWN_ISSUES.md`

### Task 1.1: CLAUDE.md 재작성

- [ ] **Step 1: CLAUDE.md를 통합 프로젝트 목적에 맞게 재작성**

주요 변경:

1. **마이그레이션 기간 예외 조항 추가**: §8 완료 조건 뒤에 "마이그레이션 기간 예외" 섹션을 추가한다. 지침이 목표 구조를 선행 반영하므로 코드 불일치를 근거로 지침을 되돌리지 않도록 명시. 마이그레이션 완료 후 삭제.
2. **프로젝트 소개**: "영업부서 매입매출 관리" → "사업 관리 통합 플랫폼 (공통 + 회계 + 인프라 모듈)"
2. **도메인 용어**: inframgr 도메인 용어 추가 (프로젝트, 자산, IP대역, 포트맵, 정책 등)
3. **코드 규칙 §2**: 파일 경로 업데이트
   - `app/exceptions.py` → `app/core/exceptions.py`
   - `app/app_factory.py` → `app/core/app_factory.py`
   - `app/schemas/` → `app/modules/{module}/schemas/`
   - 모듈 간 import 규칙 추가 (core ← common ← {accounting, infra}, accounting ↔ infra 금지)
   - `ENABLED_MODULES` 환경변수 설명 추가
4. **예외 처리 §4**: `app/core/exceptions.py`로 경로 업데이트
5. **데이터 원칙 §6**: 인프라 도메인 원칙 추가 (Asset 중심 탐색, 정책 분리, IP 중복 검증 등)
6. **테스트 §7**: 모듈별 테스트 디렉토리 구조, PostgreSQL 테스트 fixture
7. **DB**: SQLite 관련 내용 제거, PostgreSQL 명시

- [ ] **Step 2: 커밋**

```bash
git add CLAUDE.md
git commit -m "docs: rewrite CLAUDE.md for modular architecture"
```

### Task 1.2: README.md 재작성

- [ ] **Step 1: README.md를 통합 프로젝트로 재작성**

주요 변경:

1. 프로젝트 소개를 통합 플랫폼으로 변경
2. 기술 스택: SQLite → PostgreSQL, bcrypt 추가
3. 핵심 흐름: 모듈별 흐름도 (공통, 회계, 인프라)
4. 실행 방법: PostgreSQL + Docker Compose 기반, 포트 9000
5. `ENABLED_MODULES` 환경변수 설명
6. 구현 완료 기능에 인프라 모듈 영역 추가 (이식 예정 표시)
7. 아키텍처 다이어그램에 모듈 구조 반영

- [ ] **Step 2: 커밋**

```bash
git add README.md
git commit -m "docs: rewrite README.md for modular architecture"
```

### Task 1.3: docs 업데이트

- [ ] **Step 1: DECISIONS.md에 통합 결정 추가**

아래 결정들을 추가:

- 단일 코드베이스 + 배포 프로필 선택 (마이크로서비스 대신)
- 모듈 구조 (core/common/accounting/infra)
- RBAC 도입 (실용적 RBAC, 풀 RBAC 확장 대비)
- Partner → Customer 통합
- SQLite → PostgreSQL 전환
- bcrypt 전환
- 단일 Alembic migration 체인

- [ ] **Step 2: guidelines 경로 업데이트**

`docs/guidelines/backend.md`:
- `app/schemas/` → `app/modules/{module}/schemas/`
- `app/services/` → `app/modules/{module}/services/`
- `app/routers/` → `app/modules/{module}/routers/`
- 모듈 간 import 규칙 추가

`docs/guidelines/auth.md`:
- `app/auth/` → `app/core/auth/`
- RBAC 역할 모델 설명 추가
- `require_module_access()` 패턴 추가
- bcrypt 명시

`docs/guidelines/frontend.md`:
- 모듈별 템플릿/JS/CSS 네이밍 규칙 추가 (접두사: `acct_*`, `infra_*`)
- 동적 네비게이션 설명

- [ ] **Step 3: PROJECT_STRUCTURE.md 업데이트**

계획된 새 디렉토리 구조로 업데이트. 아직 이동 전이므로 "계획" 표시.

- [ ] **Step 4: KNOWN_ISSUES.md 업데이트**

- SQLite 관련 이슈 제거 (PostgreSQL 전환 예정)
- "모듈화 마이그레이션 진행 중" 항목 추가

- [ ] **Step 5: 커밋**

```bash
git add docs/
git commit -m "docs: update all documentation for modular migration"
```

### Task 1 검증

- [ ] **검증: 문서 내 경로 참조가 계획된 구조와 일치하는지 확인**

문서에서 `app/exceptions.py`, `app/auth/`, `app/schemas/` 같은 구 경로가 남아있지 않은지 grep으로 확인:

```bash
grep -rn "app/exceptions\.py\|app/auth/\|app/schemas/" docs/ CLAUDE.md README.md | grep -v "app/core/\|app/modules/"
```

---

## Task 2: 프로젝트 인프라 전환 (SQLite → PostgreSQL)

**Files:**

- Modify: `app/database.py`
- Modify: `app/config.py`
- Modify: `requirements.txt`
- Modify: `docker-compose.yml`
- Modify: `Dockerfile`
- Modify: `.env.example`
- Delete: `alembic/versions/0001_initial_baseline.py`
- Delete: `alembic/versions/0002_add_login_failures.py`
- Modify: `alembic/env.py`
- Modify: `alembic.ini`

### Task 2.1: requirements.txt 업데이트

- [ ] **Step 1: 의존성 변경**

추가:
- `psycopg[binary]>=3.2.0` (PostgreSQL 드라이버)
- `bcrypt>=4.0.0` (패스워드 해싱)

제거 가능:
- `aiosqlite` (있다면)

기존 유지:
- `fastapi`, `sqlalchemy`, `alembic`, `pydantic`, `jinja2`, `uvicorn`, `openpyxl`, `pandas`, `pytest`, `httpx`, `python-multipart`, `starlette`

- [ ] **Step 2: 커밋**

```bash
git add requirements.txt
git commit -m "build: add psycopg and bcrypt dependencies"
```

### Task 2.2: database.py 수정

- [ ] **Step 1: SQLite 전용 코드 제거, PostgreSQL 단일 설정**

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`check_same_thread`, WAL PRAGMA, busy_timeout 등 SQLite 전용 코드를 모두 제거한다.

- [ ] **Step 2: 커밋**

```bash
git add app/database.py
git commit -m "refactor: switch database.py to PostgreSQL-only"
```

### Task 2.3: config.py 수정

- [ ] **Step 1: 환경변수 업데이트**

```python
# 변경 사항:
DATABASE_URL: str = "postgresql://pjtmgr:pjtmgr@localhost:5432/pjtmgr"  # 기본값 변경
APP_PORT: int = 9000  # 추가
ENABLED_MODULES: str = "common,accounting,infra"  # 추가
```

`ENABLED_MODULES`를 파싱하는 property 추가:

```python
@property
def enabled_modules(self) -> list[str]:
    return [m.strip() for m in self.ENABLED_MODULES.split(",") if m.strip()]
```

- [ ] **Step 2: 커밋**

```bash
git add app/config.py
git commit -m "refactor: update config for PostgreSQL and module settings"
```

### Task 2.4: Docker 설정 업데이트

- [ ] **Step 1: docker-compose.yml 재작성**

inframgr의 `docs/inframgr-reference/docker-compose.yml`을 참고하여 작성. 핵심:

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: pjtmgr
      POSTGRES_USER: pjtmgr
      POSTGRES_PASSWORD: ${DB_PASSWORD:-pjtmgr}
    ports:
      - "5432:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pjtmgr"]
      interval: 5s
      timeout: 3s
      retries: 5

  app:
    build: .
    ports:
      - "${APP_PORT:-9000}:9000"
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  db-data:
```

- [ ] **Step 2: Dockerfile 업데이트**

PostgreSQL 클라이언트 추가, 포트 9000, entrypoint에서 `alembic upgrade head` 실행:

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9000

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 9000"]
```

- [ ] **Step 3: .env.example 업데이트**

```
APP_ENV=development
DATABASE_URL=postgresql://pjtmgr:pjtmgr@db:5432/pjtmgr
SESSION_SECRET_KEY=change-me-in-production
BOOTSTRAP_ADMIN_LOGIN_ID=admin
BOOTSTRAP_ADMIN_PASSWORD=change-me
BOOTSTRAP_ADMIN_NAME=관리자
APP_PORT=9000
ENABLED_MODULES=common,accounting,infra
DB_PASSWORD=pjtmgr
```

- [ ] **Step 4: 커밋**

```bash
git add docker-compose.yml Dockerfile .env.example
git commit -m "infra: configure Docker for PostgreSQL and port 9000"
```

### Task 2.5: Alembic 리셋

- [ ] **Step 1: 기존 migration 삭제**

```bash
rm alembic/versions/0001_initial_baseline.py alembic/versions/0002_add_login_failures.py
```

- [ ] **Step 2: alembic.ini의 sqlalchemy.url 확인**

`alembic.ini`에서 `sqlalchemy.url`이 없거나 `env.py`에서 config로 오버라이드되는지 확인. `env.py`에서 `settings.DATABASE_URL`을 사용하도록 한다.

- [ ] **Step 3: 커밋**

```bash
git add -A alembic/
git commit -m "refactor: remove old SQLite migrations, prepare for fresh baseline"
```

### Task 2.6: conftest.py를 PostgreSQL 기반으로 수정

Task 3 이후 테스트가 통과하려면 conftest.py가 PostgreSQL을 사용해야 한다. 이 시점에서 미리 전환한다.

- [ ] **Step 1: conftest.py의 DB fixture를 PostgreSQL로 변경**

기존 SQLite in-memory 세션을 PostgreSQL 테스트 DB로 변경. 테스트용 DB URL은 환경변수 `TEST_DATABASE_URL`로 주입하거나, 기본값으로 `postgresql://pjtmgr:pjtmgr@localhost:5432/pjtmgr_test`를 사용.

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://pjtmgr:pjtmgr@localhost:5432/pjtmgr_test",
)

engine = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine)
```

테스트 DB 생성은 docker compose에서 초기화 스크립트로 처리하거나, conftest에서 `create_all()`로 처리.

- [ ] **Step 2: docker-compose.yml에 테스트 DB 추가 (선택)**

기존 db 서비스의 init 스크립트로 `pjtmgr_test` DB를 함께 생성하도록 설정.

- [ ] **Step 3: 테스트 실행 확인**

```bash
pytest tests/ -v --tb=short
```

- [ ] **Step 4: 커밋**

```bash
git add tests/conftest.py docker-compose.yml
git commit -m "test: switch conftest to PostgreSQL test database"
```

### Task 2 검증

- [ ] **검증: docker compose up으로 PostgreSQL 연결, 앱 기동 성공**

```bash
docker compose up -d db
# DB 준비 대기 후
docker compose up app
```

앱이 기동되고 `/api/v1/health`에 접근 가능한지 확인. (아직 테이블은 없으므로 DB 체크는 실패할 수 있음 — 연결만 확인)

```bash
git commit --allow-empty -m "milestone: Task 2 complete - PostgreSQL infrastructure ready"
```

---

## Task 3: 디렉토리 구조 재편

이 단계가 가장 크고, point of no return이다. 모든 파일을 새 위치로 이동하고 import 경로를 수정한다.

**Files:**

- Create: `app/core/` 디렉토리 및 하위 파일들
- Create: `app/modules/common/` 디렉토리 및 하위 파일들
- Create: `app/modules/accounting/` 디렉토리 및 하위 파일들
- Create: `app/modules/infra/` 디렉토리 (빈 scaffolding)
- Modify: 거의 모든 Python 파일의 import 경로
- Move: 기존 `app/` 하위 파일들

### Task 3.1: core/ 디렉토리 생성 및 이동

- [ ] **Step 1: core 디렉토리 구조 생성**

```bash
mkdir -p app/core/auth app/core/startup
```

- [ ] **Step 2: 파일 이동**

```bash
# core 직접 파일
git mv app/app_factory.py app/core/app_factory.py
git mv app/config.py app/core/config.py
git mv app/database.py app/core/database.py
git mv app/exceptions.py app/core/exceptions.py

# base_model (models/base.py → core/base_model.py)
cp app/models/base.py app/core/base_model.py
# base.py는 나중에 models/__init__.py에서 re-export 정리 시 삭제

# _normalize.py (schemas/ → core/)
git mv app/schemas/_normalize.py app/core/_normalize.py

# auth
git mv app/auth/middleware.py app/core/auth/middleware.py
git mv app/auth/dependencies.py app/core/auth/dependencies.py
git mv app/auth/password.py app/core/auth/password.py
git mv app/auth/router.py app/core/auth/router.py
git mv app/auth/service.py app/core/auth/service.py
git mv app/auth/constants.py app/core/auth/constants.py
git mv app/auth/authorization.py app/core/auth/authorization.py
touch app/core/__init__.py app/core/auth/__init__.py

# startup
git mv app/startup/lifespan.py app/core/startup/lifespan.py
git mv app/startup/database_init.py app/core/startup/database_init.py
git mv app/startup/bootstrap.py app/core/startup/bootstrap.py
touch app/core/startup/__init__.py
```

- [ ] **Step 3: 빈 디렉토리 정리, __init__.py 생성**

```bash
# 구 디렉토리에서 남은 __init__.py 등 정리
rm -rf app/auth app/startup
touch app/core/__init__.py
```

- [ ] **Step 4: 커밋 (import 수정 전 — 깨진 상태)**

```bash
git add -A
git commit -m "refactor: move core files to app/core/ (imports broken)"
```

### Task 3.2: modules/common/ 디렉토리 생성 및 이동

- [ ] **Step 1: common 디렉토리 구조 생성**

```bash
mkdir -p app/modules/common/{models,schemas,services,routers,templates}
touch app/modules/__init__.py app/modules/common/__init__.py
touch app/modules/common/models/__init__.py
touch app/modules/common/schemas/__init__.py
touch app/modules/common/services/__init__.py
touch app/modules/common/routers/__init__.py
```

- [ ] **Step 2: common 모델 이동**

```bash
git mv app/models/user.py app/modules/common/models/user.py
git mv app/models/login_failure.py app/modules/common/models/login_failure.py
git mv app/models/user_preference.py app/modules/common/models/user_preference.py
git mv app/models/customer.py app/modules/common/models/customer.py
git mv app/models/customer_contact.py app/modules/common/models/customer_contact.py
git mv app/models/customer_contact_role.py app/modules/common/models/customer_contact_role.py
git mv app/models/setting.py app/modules/common/models/setting.py
git mv app/models/term_config.py app/modules/common/models/term_config.py
git mv app/models/audit_log.py app/modules/common/models/audit_log.py
```

- [ ] **Step 3: common 스키마 이동**

```bash
git mv app/schemas/user.py app/modules/common/schemas/user.py
git mv app/schemas/customer.py app/modules/common/schemas/customer.py
git mv app/schemas/customer_contact.py app/modules/common/schemas/customer_contact.py
git mv app/schemas/customer_contact_role.py app/modules/common/schemas/customer_contact_role.py
git mv app/schemas/setting.py app/modules/common/schemas/setting.py
git mv app/schemas/term_config.py app/modules/common/schemas/term_config.py
git mv app/schemas/auth.py app/modules/common/schemas/auth.py
```

- [ ] **Step 4: common 서비스 이동**

```bash
git mv app/services/user.py app/modules/common/services/user.py
git mv app/services/customer.py app/modules/common/services/customer.py
git mv app/services/_customer_helpers.py app/modules/common/services/_customer_helpers.py
git mv app/services/setting.py app/modules/common/services/setting.py
git mv app/services/term_config.py app/modules/common/services/term_config.py
git mv app/services/audit.py app/modules/common/services/audit.py
git mv app/services/user_preference.py app/modules/common/services/user_preference.py
git mv app/services/health.py app/modules/common/services/health.py
```

- [ ] **Step 5: common 라우터 이동**

```bash
git mv app/routers/users.py app/modules/common/routers/users.py
git mv app/routers/customers.py app/modules/common/routers/customers.py
git mv app/routers/settings.py app/modules/common/routers/settings.py
git mv app/routers/term_configs.py app/modules/common/routers/term_configs.py
git mv app/routers/health.py app/modules/common/routers/health.py
git mv app/routers/user_preferences.py app/modules/common/routers/user_preferences.py
```

- [ ] **Step 6: 커밋**

```bash
git add -A
git commit -m "refactor: move common module files (imports broken)"
```

### Task 3.3: modules/accounting/ 디렉토리 생성 및 이동

- [ ] **Step 1: accounting 디렉토리 구조 생성**

```bash
mkdir -p app/modules/accounting/{models,schemas,services,routers,templates}
touch app/modules/accounting/__init__.py
touch app/modules/accounting/models/__init__.py
touch app/modules/accounting/schemas/__init__.py
touch app/modules/accounting/services/__init__.py
touch app/modules/accounting/routers/__init__.py
```

- [ ] **Step 2: accounting 모델 이동**

```bash
git mv app/models/contract.py app/modules/accounting/models/contract.py
git mv app/models/contract_period.py app/modules/accounting/models/contract_period.py
git mv app/models/contract_contact.py app/modules/accounting/models/contract_contact.py
git mv app/models/contract_type_config.py app/modules/accounting/models/contract_type_config.py
git mv app/models/monthly_forecast.py app/modules/accounting/models/monthly_forecast.py
git mv app/models/transaction_line.py app/modules/accounting/models/transaction_line.py
git mv app/models/receipt.py app/modules/accounting/models/receipt.py
git mv app/models/receipt_match.py app/modules/accounting/models/receipt_match.py
```

- [ ] **Step 3: accounting 스키마 이동**

```bash
git mv app/schemas/contract.py app/modules/accounting/schemas/contract.py
git mv app/schemas/contract_contact.py app/modules/accounting/schemas/contract_contact.py
git mv app/schemas/contract_type_config.py app/modules/accounting/schemas/contract_type_config.py
git mv app/schemas/monthly_forecast.py app/modules/accounting/schemas/monthly_forecast.py
git mv app/schemas/transaction_line.py app/modules/accounting/schemas/transaction_line.py
git mv app/schemas/receipt.py app/modules/accounting/schemas/receipt.py
git mv app/schemas/receipt_match.py app/modules/accounting/schemas/receipt_match.py
git mv app/schemas/report.py app/modules/accounting/schemas/report.py
```

- [ ] **Step 4: accounting 서비스 이동**

```bash
git mv app/services/contract.py app/modules/accounting/services/contract.py
git mv app/services/_contract_helpers.py app/modules/accounting/services/_contract_helpers.py
git mv app/services/contract_contact.py app/modules/accounting/services/contract_contact.py
git mv app/services/contract_type_config.py app/modules/accounting/services/contract_type_config.py
git mv app/services/monthly_forecast.py app/modules/accounting/services/monthly_forecast.py
git mv app/services/transaction_line.py app/modules/accounting/services/transaction_line.py
git mv app/services/receipt.py app/modules/accounting/services/receipt.py
git mv app/services/receipt_match.py app/modules/accounting/services/receipt_match.py
git mv app/services/forecast_sync.py app/modules/accounting/services/forecast_sync.py
git mv app/services/ledger.py app/modules/accounting/services/ledger.py
git mv app/services/metrics.py app/modules/accounting/services/metrics.py
git mv app/services/dashboard.py app/modules/accounting/services/dashboard.py
git mv app/services/report.py app/modules/accounting/services/report.py
git mv app/services/_report_export.py app/modules/accounting/services/_report_export.py
git mv app/services/importer.py app/modules/accounting/services/importer.py
git mv app/services/exporter.py app/modules/accounting/services/exporter.py
git mv app/services/monthly_forecast.py app/modules/accounting/services/monthly_forecast.py
```

- [ ] **Step 5: accounting 라우터 이동**

```bash
git mv app/routers/contracts.py app/modules/accounting/routers/contracts.py
git mv app/routers/contract_contacts.py app/modules/accounting/routers/contract_contacts.py
git mv app/routers/contract_types.py app/modules/accounting/routers/contract_types.py
git mv app/routers/forecasts.py app/modules/accounting/routers/forecasts.py
git mv app/routers/transaction_lines.py app/modules/accounting/routers/transaction_lines.py
git mv app/routers/receipts.py app/modules/accounting/routers/receipts.py
git mv app/routers/receipt_matches.py app/modules/accounting/routers/receipt_matches.py
git mv app/routers/dashboard.py app/modules/accounting/routers/dashboard.py
git mv app/routers/reports.py app/modules/accounting/routers/reports.py
git mv app/routers/excel.py app/modules/accounting/routers/excel.py
```

- [ ] **Step 6: 커밋**

```bash
git add -A
git commit -m "refactor: move accounting module files (imports broken)"
```

### Task 3.4: modules/infra/ scaffolding

- [ ] **Step 1: infra 디렉토리 구조 생성 (빈 상태)**

```bash
mkdir -p app/modules/infra/{models,schemas,services,routers,templates}
touch app/modules/infra/__init__.py
touch app/modules/infra/models/__init__.py
touch app/modules/infra/schemas/__init__.py
touch app/modules/infra/services/__init__.py
touch app/modules/infra/routers/__init__.py
```

- [ ] **Step 2: 커밋**

```bash
git add -A
git commit -m "scaffold: create empty infra module structure"
```

### Task 3.5: 구 디렉토리 정리

- [ ] **Step 1: 남은 빈 디렉토리와 __init__.py 정리**

`app/models/`, `app/schemas/`, `app/services/`, `app/routers/`에 남은 파일 확인:

```bash
find app/models app/schemas app/services app/routers -type f 2>/dev/null
```

`__init__.py`와 pages 라우터만 남아있어야 한다. pages.py는 모듈별로 분리해야 하지만, 이 단계에서는 일단 `app/routers/pages.py` → `app/core/pages.py`로 임시 이동한다 (Task 4에서 모듈별 분리).

```bash
git mv app/routers/pages.py app/core/pages.py
rm -rf app/models app/schemas app/services app/routers app/auth app/startup
```

- [ ] **Step 2: 커밋**

```bash
git add -A
git commit -m "refactor: clean up old directory structure"
```

### Task 3.6: import 경로 전체 수정

이것이 가장 노동 집약적인 부분이다. 모든 Python 파일에서 import 경로를 새 위치에 맞게 수정해야 한다.

- [ ] **Step 1: 모든 Python 파일의 import 수정**

패턴별 치환 목록:

| 구 경로 | 신 경로 |
|---------|---------|
| `from app.config` | `from app.core.config` |
| `from app.database` | `from app.core.database` |
| `from app.exceptions` | `from app.core.exceptions` |
| `from app.app_factory` | `from app.core.app_factory` |
| `from app.auth.` | `from app.core.auth.` |
| `from app.startup.` | `from app.core.startup.` |
| `from app.models.base` | `from app.core.base_model` |
| `from app.schemas._normalize` | `from app.core._normalize` |
| `from app.models.user` | `from app.modules.common.models.user` |
| `from app.models.customer` | `from app.modules.common.models.customer` |
| `from app.models.setting` | `from app.modules.common.models.setting` |
| (등등 — 각 모델/스키마/서비스/라우터에 대해) |  |
| `from app.services.contract` | `from app.modules.accounting.services.contract` |
| `from app.schemas.contract` | `from app.modules.accounting.schemas.contract` |
| (등등) |  |

각 파일을 열어 import 문을 수정한다. 파일 수가 많으므로 IDE의 전역 검색/치환 또는 `sed` 스크립트를 활용한다.

주의: 모듈 간 import 방향 규칙을 준수한다.

- `accounting/services/contract.py`에서 `from app.modules.common.models.user import User` → ✅
- `accounting/services/contract.py`에서 `from app.modules.infra.` → ❌ (이런 경우는 없어야 함)

- [ ] **Step 2: main.py 수정**

`app/main.py`는 현재 `from app.app_factory import create_app`을 참조한다. 수정:

```python
from app.core.app_factory import create_app

app = create_app()
```

- [ ] **Step 3: 각 모듈의 models/__init__.py에 모델 import 추가**

예시 — `app/modules/common/models/__init__.py`:

```python
from app.modules.common.models.user import User
from app.modules.common.models.login_failure import LoginFailure
from app.modules.common.models.user_preference import UserPreference
from app.modules.common.models.customer import Customer
from app.modules.common.models.customer_contact import CustomerContact
from app.modules.common.models.customer_contact_role import CustomerContactRole
from app.modules.common.models.setting import Setting
from app.modules.common.models.term_config import TermConfig
from app.modules.common.models.audit_log import AuditLog

__all__ = [
    "User", "LoginFailure", "UserPreference",
    "Customer", "CustomerContact", "CustomerContactRole",
    "Setting", "TermConfig", "AuditLog",
]
```

`app/modules/accounting/models/__init__.py`도 동일 패턴으로 작성.

- [ ] **Step 4: 테스트 파일의 import도 수정**

`tests/` 하위 모든 테스트 파일에서 동일한 import 경로 치환 적용.

- [ ] **Step 5: alembic/env.py에 모든 모듈 모델 import 추가**

`alembic/env.py`에서 Alembic autogenerate가 모든 모델을 인식할 수 있도록:

```python
# alembic/env.py 상단에 추가
import app.modules.common.models  # noqa: F401
import app.modules.accounting.models  # noqa: F401
import app.modules.infra.models  # noqa: F401
```

- [ ] **Step 6: test_module_isolation.py를 이 시점에 생성 (개발 가드)**

Task 8까지 기다리지 않고, 구조 재편 직후에 모듈 격리 테스트를 생성하여 이후 단계에서 위반을 조기 발견한다.

`tests/test_module_isolation.py` 작성 (Task 8.4에 있는 코드와 동일):

```python
import ast
from pathlib import Path

def _get_imports(filepath: Path) -> list[str]:
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports

def test_accounting_does_not_import_infra():
    accounting_dir = Path("app/modules/accounting")
    for py_file in accounting_dir.rglob("*.py"):
        for imp in _get_imports(py_file):
            assert "app.modules.infra" not in imp, f"{py_file} imports {imp}"

def test_infra_does_not_import_accounting():
    infra_dir = Path("app/modules/infra")
    for py_file in infra_dir.rglob("*.py"):
        for imp in _get_imports(py_file):
            assert "app.modules.accounting" not in imp, f"{py_file} imports {imp}"
```

- [ ] **Step 7: import 오류 확인**

```bash
python -c "from app.core.app_factory import create_app; print('OK')"
python -c "from app.modules.common.models import User; print('OK')"
python -c "from app.modules.accounting.models import Contract; print('OK')"
```

- [ ] **Step 8: 커밋**

```bash
git add -A
git commit -m "refactor: fix all import paths for modular structure"
```

### Task 3 검증

- [ ] **검증: 앱 기동 및 기존 테스트 통과**

```bash
python -c "from app.main import app; print('App created:', type(app))"
pytest tests/ -v --tb=short
```

모든 테스트가 통과해야 한다. DB 연결이 필요한 테스트는 PostgreSQL이 실행 중이어야 한다.

```bash
git commit --allow-empty -m "milestone: Task 3 complete - modular directory structure"
```

---

## Task 4: 모듈 등록 메커니즘

**Files:**

- Modify: `app/core/app_factory.py`
- Modify: `app/core/config.py`
- Modify: `app/main.py`
- Create: `app/modules/common/routers/__init__.py` (라우터 집합)
- Create: `app/modules/accounting/routers/__init__.py` (라우터 집합)
- Modify: `app/templates/base.html`
- Create: `tests/test_module_registration.py`

### Task 4.1: 모듈별 라우터 집합 정의

- [ ] **Step 1: common 라우터 패키지 구성**

`app/modules/common/routers/__init__.py`:

```python
from fastapi import APIRouter

from app.modules.common.routers.users import router as users_router
from app.modules.common.routers.customers import router as customers_router
from app.modules.common.routers.settings import router as settings_router
from app.modules.common.routers.term_configs import router as term_configs_router
from app.modules.common.routers.health import router as health_router
from app.modules.common.routers.user_preferences import router as preferences_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(customers_router)
api_router.include_router(settings_router)
api_router.include_router(term_configs_router)
api_router.include_router(health_router)
api_router.include_router(preferences_router)
```

- [ ] **Step 2: accounting 라우터 패키지 구성**

`app/modules/accounting/routers/__init__.py` — 동일 패턴으로 10개 라우터 등록.

- [ ] **Step 3: 커밋**

```bash
git add app/modules/common/routers/__init__.py app/modules/accounting/routers/__init__.py
git commit -m "feat: define module router packages"
```

### Task 4.2: app_factory.py에 동적 모듈 등록

- [ ] **Step 1: app_factory.py 수정**

```python
from app.core.config import settings

def create_app() -> FastAPI:
    # ... (기존 app 생성, 미들웨어 설정)

    enabled = settings.enabled_modules

    # 모든 모델 import (Alembic 정합성)
    import app.modules.common.models  # noqa: F401
    import app.modules.accounting.models  # noqa: F401
    import app.modules.infra.models  # noqa: F401

    # auth 라우터 (항상)
    from app.core.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/api/v1")

    # 모듈별 라우터 등록
    if "common" in enabled:
        from app.modules.common.routers import api_router as common_router
        app.include_router(common_router, prefix="/api/v1")

    if "accounting" in enabled:
        from app.modules.accounting.routers import api_router as accounting_router
        app.include_router(accounting_router, prefix="/api/v1")

    if "infra" in enabled:
        from app.modules.infra.routers import api_router as infra_router
        app.include_router(infra_router, prefix="/api/v1")

    # Jinja2 템플릿 로더
    _configure_templates(app, enabled)

    # enabled_modules를 Jinja2 global로 주입
    app.state.enabled_modules = enabled

    return app
```

- [ ] **Step 2: 템플릿 ChoiceLoader 구현**

```python
from jinja2 import ChoiceLoader, FileSystemLoader

def _configure_templates(app: FastAPI, enabled: list[str]) -> None:
    loaders = [FileSystemLoader("app/templates")]  # 공통 (base.html, login)

    if "common" in enabled:
        loaders.append(FileSystemLoader("app/modules/common/templates"))
    if "accounting" in enabled:
        loaders.append(FileSystemLoader("app/modules/accounting/templates"))
    if "infra" in enabled:
        loaders.append(FileSystemLoader("app/modules/infra/templates"))

    app.jinja_env = app.jinja_env  # 기존 Jinja2 env 유지
    # templates 객체의 loader를 교체
    from starlette.templating import Jinja2Templates
    templates = Jinja2Templates(directory="app/templates")
    templates.env.loader = ChoiceLoader(loaders)
    # Jinja2 global에 enabled_modules 추가
    templates.env.globals["enabled_modules"] = enabled
```

실제 구현은 기존 `app_factory.py`의 Jinja2 설정 패턴을 따라 조정한다.

- [ ] **Step 3: 커밋**

```bash
git add app/core/app_factory.py
git commit -m "feat: implement dynamic module registration in app_factory"
```

### Task 4.3: base.html 동적 네비게이션

- [ ] **Step 1: base.html 수정**

네비게이션에서 모듈별 조건부 렌더링:

```html
<nav>
  <!-- 공통: 항상 -->
  <a href="/customers">거래처</a>

  <!-- 회계모듈 -->
  {% if "accounting" in enabled_modules %}
  <a href="/my-contracts">내 사업</a>
  <a href="/contracts">사업관리</a>
  <a href="/dashboard">대시보드</a>
  <a href="/reports">보고서</a>
  {% endif %}

  <!-- 인프라모듈 -->
  {% if "infra" in enabled_modules %}
  <a href="/projects">프로젝트</a>
  <a href="/assets">자산</a>
  <a href="/ip-inventory">IP인벤토리</a>
  <a href="/port-maps">포트맵</a>
  <a href="/policies">정책</a>
  {% endif %}

  <!-- 관리자 메뉴 -->
  <a href="/users">사용자</a>
  <a href="/system">시스템설정</a>
</nav>
```

- [ ] **Step 2: 커밋**

```bash
git add app/templates/base.html
git commit -m "feat: dynamic navigation based on enabled modules"
```

### Task 4.4: pages 라우터 분리

- [ ] **Step 1: 기존 pages.py를 모듈별로 분리**

현재 `app/core/pages.py`에 모든 페이지 라우트가 있다. 이를 분리:

- 공통 페이지 (login, change_password, index) → `app/core/pages.py` 유지
- 회계 페이지 (contracts, contract_detail, my_contracts, dashboard, reports) → `app/modules/accounting/routers/pages.py`
- 공통 엔티티 페이지 (customers, users, system, audit_logs) → `app/modules/common/routers/pages.py`

각 모듈의 pages 라우터를 해당 모듈의 `routers/__init__.py`에 등록.

- [ ] **Step 2: 홈 페이지 조건부 라우팅 구현**

`app/core/pages.py`의 index 라우트에서 사용자의 가시 모듈에 따라 리다이렉트:

```python
from fastapi.responses import RedirectResponse

@router.get("/")
async def index(request: Request):
    user = request.state.user  # 또는 get_current_user
    if not user:
        return RedirectResponse("/login")
    # 가시 모듈 우선순위: accounting > infra
    visible = get_visible_modules(user, request.app.state.enabled_modules)
    if "accounting" in visible:
        return RedirectResponse("/my-contracts")
    elif "infra" in visible:
        return RedirectResponse("/projects")
    return RedirectResponse("/login")
```

- [ ] **Step 3: 커밋**

```bash
git add -A
git commit -m "refactor: split pages router by module"
```

### Task 4.5: 모듈 등록 테스트

- [ ] **Step 1: 테스트 작성**

`tests/test_module_registration.py`:

```python
import os
from unittest.mock import patch
from fastapi.testclient import TestClient


def test_accounting_only():
    """ENABLED_MODULES=common,accounting일 때 인프라 라우트는 404."""
    with patch.dict(os.environ, {"ENABLED_MODULES": "common,accounting"}):
        from app.core.app_factory import create_app
        app = create_app()
        client = TestClient(app)
        # 회계 라우트 존재 확인
        assert client.get("/api/v1/health").status_code != 404
        # 인프라 라우트 미존재 확인 (아직 인프라 라우터가 비어있으므로 스킵 가능)


def test_all_modules():
    """ENABLED_MODULES=common,accounting,infra일 때 전체 라우트 등록."""
    with patch.dict(os.environ, {"ENABLED_MODULES": "common,accounting,infra"}):
        from app.core.app_factory import create_app
        app = create_app()
        routes = [r.path for r in app.routes]
        assert "/api/v1/health" in routes
```

- [ ] **Step 2: 테스트 실행**

```bash
pytest tests/test_module_registration.py -v
```

- [ ] **Step 3: 커밋**

```bash
git add tests/test_module_registration.py
git commit -m "test: add module registration tests"
```

### Task 4 검증

- [ ] **검증: ENABLED_MODULES=common,accounting으로 기존 기능 정상 동작**

```bash
ENABLED_MODULES=common,accounting python -c "from app.main import app; print('Routes:', len(app.routes))"
pytest tests/ -v --tb=short
```

```bash
git commit --allow-empty -m "milestone: Task 4 complete - module registration working"
```

---

## Task 5: RBAC 전환

**Files:**

- Create: `app/modules/common/models/role.py`
- Modify: `app/modules/common/models/user.py`
- Modify: `app/modules/common/models/__init__.py`
- Create: `app/modules/common/schemas/role.py`
- Create: `app/modules/common/services/role.py`
- Create: `app/modules/common/routers/roles.py`
- Modify: `app/core/auth/authorization.py`
- Modify: `app/core/auth/dependencies.py`
- Modify: `app/core/auth/password.py`
- Modify: `app/core/startup/bootstrap.py`
- Create: `tests/common/test_role_permissions.py`

### Task 5.1: Role 모델 생성

- [ ] **Step 1: 테스트 작성**

`tests/common/test_role_permissions.py`:

```python
def test_create_role(db_session):
    """역할을 생성하고 permissions JSON이 올바르게 저장되는지 확인."""
    from app.modules.common.models.role import Role
    role = Role(
        name="테스트역할",
        is_system=False,
        permissions={"admin": False, "modules": {"accounting": "full"}},
    )
    db_session.add(role)
    db_session.commit()
    assert role.id is not None
    assert role.permissions["modules"]["accounting"] == "full"
```

- [ ] **Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/common/test_role_permissions.py::test_create_role -v
```

- [ ] **Step 3: Role 모델 구현**

`app/modules/common/models/role.py`:

```python
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import Base, TimestampMixin


class Role(TimestampMixin, Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permissions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # permissions 구조:
    # {
    #   "admin": bool,
    #   "modules": {"accounting": "full"|"read"|null, "infra": "full"|"read"|null}
    #   // 향후 풀 RBAC 확장:
    #   // "resources": {"contract": ["create","read","update","delete"], ...}
    # }
```

- [ ] **Step 4: __init__.py에 추가, 테스트 실행**

```bash
pytest tests/common/test_role_permissions.py -v
```

- [ ] **Step 5: 커밋**

```bash
git add -A
git commit -m "feat: add Role model with JSON permissions"
```

### Task 5.2: User 모델 변경

- [ ] **Step 1: User 모델에 role_id FK 추가, role 문자열 제거, password_hash 컬럼명 통일**

`app/modules/common/models/user.py`에서:

- `role: Mapped[str]` → `role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))`
- `hashed_password` → `password_hash`
- `role_obj` relationship 추가

- [ ] **Step 2: 모든 `user.role` 참조를 `user.role_obj.permissions` 기반으로 변경**

- [ ] **Step 3: 커밋**

```bash
git add -A
git commit -m "feat: switch User model to role_id FK and password_hash"
```

### Task 5.3: bcrypt 전환

- [ ] **Step 1: password.py를 bcrypt 기반으로 변경**

`app/core/auth/password.py`:

```python
import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
```

- [ ] **Step 2: 기존 PBKDF2 관련 코드 제거**

- [ ] **Step 3: 커밋**

```bash
git add app/core/auth/password.py
git commit -m "feat: switch password hashing to bcrypt"
```

### Task 5.4: authorization.py 리팩터링

- [ ] **Step 1: 모듈 접근 권한 함수 추가**

`app/core/auth/authorization.py`에 추가:

```python
def can_access_module(user, module_name: str) -> bool:
    """사용자가 해당 모듈에 접근 가능한지 확인."""
    perms = user.role_obj.permissions
    if perms.get("admin"):
        return True
    modules = perms.get("modules", {})
    return modules.get(module_name) is not None


def get_module_access_level(user, module_name: str) -> str | None:
    """사용자의 모듈 권한 수준 반환. None/read/full"""
    perms = user.role_obj.permissions
    if perms.get("admin"):
        return "full"
    return perms.get("modules", {}).get(module_name)


# TODO: 풀 RBAC 확장 시 아래 함수 구현
# def check_resource_permission(user, resource: str, action: str) -> bool:
#     """리소스 단위 권한 검사. 현재는 미구현."""
#     raise NotImplementedError("Full RBAC not yet implemented")
```

- [ ] **Step 2: dependencies.py에 require_module_access 추가**

```python
def require_module_access(module: str, min_level: str = "read"):
    def checker(current_user=Depends(get_current_user)):
        level = get_module_access_level(current_user, module)
        if level is None:
            raise PermissionDeniedError(f"{module} 모듈 접근 권한이 없습니다")
        if min_level == "full" and level == "read":
            raise PermissionDeniedError(f"{module} 모듈 읽기 전용 권한입니다")
        return current_user
    return Depends(checker)
```

- [ ] **Step 3: 기존 can_* 함수들을 admin 플래그 기반으로 수정**

`core/auth/authorization.py`에 남아있는 공통 함수들을 `permissions["admin"]` 기반으로 변경:
- `can_manage_users(user)` → `user.role_obj.permissions.get("admin", False)`
- `can_manage_settings(user)` → 동일
- `require_admin(user)` → 동일

회계 모듈 전용 권한 함수(`can_delete_contract` 등)는 이미 Task 3에서 `app/modules/accounting/services/`로 이동됨.

- [ ] **Step 4: 모든 회계 라우터에 require_module_access 적용**

`app/modules/accounting/routers/` 하위 모든 라우터 파일(10개)에 대해:
- GET 엔드포인트: `require_module_access("accounting", "read")` 적용
- POST/PATCH/DELETE 엔드포인트: `require_module_access("accounting", "full")` 적용

예시 — `contracts.py`:

```python
from app.core.auth.dependencies import require_module_access

@router.get("/contracts", dependencies=[require_module_access("accounting", "read")])
async def list_contracts(...): ...

@router.post("/contracts", dependencies=[require_module_access("accounting", "full")])
async def create_contract(...): ...

@router.delete("/contracts/{id}", dependencies=[require_module_access("accounting", "full")])
async def delete_contract(...): ...
```

동일 패턴을 `forecasts.py`, `transaction_lines.py`, `receipts.py`, `receipt_matches.py`, `dashboard.py`, `reports.py`, `excel.py`, `contract_types.py`, `contract_contacts.py`에 적용.

- [ ] **Step 5: 커밋**

```bash
git add -A
git commit -m "feat: implement module-level RBAC authorization"
```

### Task 5.5: 기본 역할 시드 및 bootstrap 수정

- [ ] **Step 1: bootstrap.py에 기본 역할 시드 추가**

```python
SYSTEM_ROLES = [
    {"name": "관리자", "is_system": True, "permissions": {"admin": True, "modules": {"accounting": "full", "infra": "full"}}},
    {"name": "영업담당자", "is_system": True, "permissions": {"admin": False, "modules": {"accounting": "full"}}},
    {"name": "기술담당자", "is_system": True, "permissions": {"admin": False, "modules": {"infra": "full"}}},
    {"name": "PM", "is_system": True, "permissions": {"admin": False, "modules": {"accounting": "full", "infra": "full"}}},
]
```

bootstrap admin 생성 시 "관리자" 역할을 할당하도록 수정.

- [ ] **Step 2: 역할 관리 API 구현**

`app/modules/common/routers/roles.py` — 역할 CRUD (admin 전용)
`app/modules/common/services/role.py` — 역할 비즈니스 로직
`app/modules/common/schemas/role.py` — 역할 스키마

- [ ] **Step 3: roles 라우터를 common routers/__init__.py에 등록**

`app/modules/common/routers/__init__.py`에 추가:

```python
from app.modules.common.routers.roles import router as roles_router
api_router.include_router(roles_router)
```

- [ ] **Step 4: 사용자 관리 UI에 역할 선택 드롭다운 추가**

기존 `users.html` + `users.js`에서 role 문자열 대신 역할 선택 UI.

- [ ] **Step 5: 테스트**

```bash
pytest tests/common/test_role_permissions.py -v
pytest tests/ -v --tb=short
```

- [ ] **Step 6: 커밋**

```bash
git add -A
git commit -m "feat: seed system roles, role management API, user role assignment"
```

### Task 5 검증

- [ ] **검증: 역할별 모듈 접근/차단, read 권한 사용자의 POST/DELETE 차단**

```bash
pytest tests/ -v --tb=short
```

```bash
git commit --allow-empty -m "milestone: Task 5 complete - RBAC system"
```

---

## Task 6: Partner → Customer 통합

**Files:**

- Modify: `app/modules/common/models/customer.py`
- Modify: `app/modules/common/models/customer_contact.py`
- Modify: `app/modules/common/schemas/customer.py`
- Modify: `app/modules/common/schemas/customer_contact.py`
- Modify: `app/modules/common/services/customer.py`
- Modify: `app/modules/common/routers/customers.py`

### Task 6.1: Customer 모델 확장

- [ ] **Step 1: Customer 모델에 신규 필드 추가**

```python
# 추가 필드
customer_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 고객사/공급사/유지보수사/통신사
phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
address: Mapped[str | None] = mapped_column(String(500), nullable=True)
note: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 2: CustomerContact 모델에 신규 필드 추가**

```python
# 추가 필드
department: Mapped[str | None] = mapped_column(String(100), nullable=True)
title: Mapped[str | None] = mapped_column(String(100), nullable=True)
emergency_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
note: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 3: 스키마 업데이트**

`CustomerCreate`, `CustomerUpdate`, `CustomerRead`에 신규 필드 추가.
`CustomerContactCreate`, `CustomerContactUpdate`, `CustomerContactRead`에 신규 필드 추가.

- [ ] **Step 4: 서비스/라우터에 customer_type 필터링 지원**

customers 라우터의 list 엔드포인트에 `customer_type` 쿼리 파라미터 추가.

- [ ] **Step 5: 테스트**

```bash
pytest tests/common/test_customer_service.py -v
```

- [ ] **Step 6: 커밋**

```bash
git add -A
git commit -m "feat: extend Customer/CustomerContact with Partner fields"
```

### Task 6 검증

- [ ] **검증: 기존 거래처 CRUD + 신규 필드 동작**

```bash
pytest tests/ -v --tb=short
```

```bash
git commit --allow-empty -m "milestone: Task 6 complete - Customer model extended"
```

---

## Task 7: 인프라모듈 이식

**Files:**

- Create: `app/modules/infra/models/*.py` (10+ 모델)
- Create: `app/modules/infra/schemas/*.py`
- Create: `app/modules/infra/services/*.py`
- Create: `app/modules/infra/routers/*.py`
- Create: `app/modules/infra/routers/pages.py`
- Create: `app/modules/infra/templates/*.html`
- Create: `app/static/js/infra_*.js`
- Create: `app/static/css/infra_*.css`

**참조:** `docs/inframgr-reference/` 전체 소스

### Task 7.1: 인프라 모델 이식

- [ ] **Step 1: inframgr-reference/models.py에서 모델 코드 이식**

각 모델을 `app/modules/infra/models/` 하위에 개별 파일로 생성.

변경 사항:
- `from app.models.base import Base, TimestampMixin` → `from app.core.base_model import Base, TimestampMixin`
- `Partner` 모델 제거 (Customer로 통합됨)
- `Contact` 모델 제거 (CustomerContact로 통합됨)
- `User` 모델 제거 (common에 이미 존재)
- `AssetContact.contact_id` FK: `ForeignKey("contacts.id")` → `ForeignKey("customer_contacts.id")`
- `Partner.project_id` FK 제거 → 필요 시 `ProjectCustomer` 매핑 테이블 생성
- `Project.client_name` → `Project.customer_id = ForeignKey("customers.id")`
- 모든 모델에서 `external_id`, `external_source` 필드 제거

이식 대상 모델:
1. `Project`
2. `ProjectPhase`
3. `ProjectDeliverable`
4. `Asset`
5. `IpSubnet`
6. `AssetIP`
7. `PortMap`
8. `PolicyDefinition`
9. `PolicyAssignment`
10. `AssetContact`

- [ ] **Step 2: models/__init__.py 구성**

```python
from app.modules.infra.models.project import Project
from app.modules.infra.models.project_phase import ProjectPhase
# ... 모든 모델 import
```

- [ ] **Step 3: 커밋**

```bash
git add app/modules/infra/models/
git commit -m "feat: port infra models from inframgr"
```

### Task 7.2: 인프라 스키마 이식

- [ ] **Step 1: inframgr-reference/schemas.py에서 스키마 이식**

각 스키마를 `app/modules/infra/schemas/` 하위에 개별 파일로 생성.

변경 사항:
- Partner/Contact 관련 스키마 제거 (common의 Customer 스키마 사용)
- User 스키마 제거 (common에 이미 존재)
- `ProjectCreate`에 `customer_id` 필드 추가 (`client_name` 대체)

- [ ] **Step 2: 커밋**

```bash
git add app/modules/infra/schemas/
git commit -m "feat: port infra schemas from inframgr"
```

### Task 7.3: 인프라 서비스 이식

- [ ] **Step 1: inframgr-reference/services.py에서 서비스 이식**

변경 사항:
- `partner_service.py` → 제거 (common의 customer 서비스 사용)
- `user_service.py` → 제거 (common에 이미 존재)
- `sync_service.py` → 제거
- 나머지 서비스의 Partner/Contact 참조를 Customer/CustomerContact로 변경
- import 경로 변경: `from app.models.` → `from app.modules.infra.models.` 또는 `from app.modules.common.models.`
- 예외: `from app.exceptions` → `from app.core.exceptions`
- 권한: `from app.auth.authorization` → `from app.core.auth.authorization`

이식 대상 서비스:
1. `project_service.py`
2. `phase_service.py`
3. `asset_service.py`
4. `network_service.py`
5. `policy_service.py`

- [ ] **Step 2: 커밋**

```bash
git add app/modules/infra/services/
git commit -m "feat: port infra services from inframgr"
```

### Task 7.4: 인프라 라우터 이식

- [ ] **Step 1: inframgr-reference/routers.py에서 라우터 이식**

변경 사항:
- `sync.py` → 제거
- `partners.py`, `contacts.py` → 제거
- `users.py` → 제거
- 나머지 라우터의 import 경로 변경
- `pages.py`에서 인프라 관련 페이지만 포함

이식 대상 라우터:
1. `projects.py`
2. `project_phases.py`
3. `project_deliverables.py`
4. `assets.py`
5. `asset_ips.py`
6. `ip_subnets.py`
7. `port_maps.py`
8. `policies.py`
9. `policy_assignments.py`
10. `asset_contacts.py`
11. `pages.py` (인프라 페이지 전용)

- [ ] **Step 2: infra routers/__init__.py 구성**

```python
from fastapi import APIRouter

api_router = APIRouter()
# ... 모든 인프라 라우터 등록
```

- [ ] **Step 3: 커밋**

```bash
git add app/modules/infra/routers/
git commit -m "feat: port infra routers from inframgr"
```

### Task 7.5: 프론트엔드 이식

- [ ] **Step 1: 템플릿 이식**

`docs/inframgr-reference/templates.html`에서 각 템플릿을 개별 파일로 분리하여 `app/modules/infra/templates/`에 저장.

파일명 규칙: `infra_projects.html`, `infra_project_detail.html`, `infra_assets.html`, `infra_ip_inventory.html`, `infra_port_maps.html`, `infra_policies.html`, `infra_partners.html` (→ `infra_contacts.html`로 변경 또는 제거)

각 템플릿에서 `{% extends "base.html" %}`를 유지하되, 인프라 전용 블록만 포함.

- [ ] **Step 2: JS 이식**

`docs/inframgr-reference/static-js.js`에서 각 JS 파일을 분리하여 `app/static/js/`에 저장.

파일명: `infra_projects.js`, `infra_project_detail.js`, `infra_assets.js`, `infra_ip_inventory.js`, `infra_port_maps.js`, `infra_policies.js`, `infra_partners.js` (→ Customer 기반으로 수정)

각 JS 파일에서 API 호출 경로가 `/api/v1/`으로 동일한지 확인.

- [ ] **Step 3: CSS 이식**

`docs/inframgr-reference/static-css.css`에서 inframgr 전용 컴포넌트 스타일 추출.

기존 `base.css`, `components.css`와 중복되는 부분 제거. 인프라 전용 스타일만 `infra_*.css`로 분리.

공통 CSS 변수/컴포넌트가 누락된 것이 있으면 `base.css`/`components.css`에 병합.

- [ ] **Step 4: utils.js 병합**

두 프로젝트의 `utils.js` 비교. 공통 유틸(`apiFetch`, `fmtNumber`, `fmtDate`, `showToast`, `confirmDelete`)은 이미 pjtmgr의 utils.js에 존재할 가능성 높음. inframgr 전용 유틸이 있으면 추가.

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/templates/ app/static/js/infra_* app/static/css/infra_*
git commit -m "feat: port infra frontend from inframgr"
```

### Task 7 검증

- [ ] **검증: ENABLED_MODULES=common,accounting,infra로 전체 동작**

```bash
ENABLED_MODULES=common,accounting,infra python -c "from app.main import app; print('Routes:', len(app.routes))"
```

브라우저에서 인프라 페이지 접근 확인.

```bash
git commit --allow-empty -m "milestone: Task 7 complete - infra module ported"
```

---

## Task 8: Alembic 재구성 및 테스트

**Files:**

- Create: `alembic/versions/0001_initial_modular_baseline.py`
- Move/Create: `tests/common/`, `tests/accounting/`, `tests/infra/`
- Create: `tests/test_module_isolation.py`
- Modify: `tests/conftest.py`

### Task 8.1: 새 initial migration 생성

- [ ] **Step 1: Alembic autogenerate로 새 baseline 생성**

```bash
alembic revision --autogenerate -m "initial modular baseline"
```

생성된 migration 파일을 확인하고, 모든 테이블(common + accounting + infra)이 포함되어 있는지 확인.

- [ ] **Step 2: migration 적용 테스트**

```bash
alembic upgrade head
```

- [ ] **Step 3: 커밋**

```bash
git add alembic/
git commit -m "migration: create initial modular baseline"
```

### Task 8.2: 테스트 구조 재편

- [ ] **Step 1: 테스트 디렉토리 생성 및 이동**

```bash
mkdir -p tests/common tests/accounting tests/infra

# common 테스트
git mv tests/test_auth_service.py tests/common/
git mv tests/test_customer_service.py tests/common/
git mv tests/test_database.py tests/
git mv tests/test_startup.py tests/

# accounting 테스트
git mv tests/test_contract_service.py tests/accounting/
git mv tests/test_contract_schema.py tests/accounting/
git mv tests/test_receipt_match_service.py tests/accounting/
git mv tests/test_transaction_safety.py tests/accounting/
git mv tests/test_metrics.py tests/accounting/
git mv tests/test_dashboard_service.py tests/accounting/
git mv tests/test_report_service.py tests/accounting/
git mv tests/test_importer.py tests/accounting/

touch tests/common/__init__.py tests/accounting/__init__.py tests/infra/__init__.py
```

- [ ] **Step 2: conftest.py를 PostgreSQL 기반으로 수정**

기존 SQLite in-memory fixture를 PostgreSQL 테스트 DB로 변경. `testcontainers` 또는 테스트 전용 DB URL 환경변수 사용.

- [ ] **Step 3: 테스트 파일의 import 경로 수정**

모든 테스트 파일에서 import 경로를 새 모듈 구조에 맞게 수정.

- [ ] **Step 4: 커밋**

```bash
git add -A
git commit -m "test: restructure tests by module, switch to PostgreSQL fixtures"
```

### Task 8.3: 인프라 테스트 이식

- [ ] **Step 1: inframgr-reference/tests.py에서 테스트 이식**

변경 사항:
- import 경로 수정
- Partner 관련 테스트 → Customer 기반으로 재작성
- fixture를 pjtmgr의 conftest 패턴에 맞춤

이식 대상:
1. `test_project_service.py`
2. `test_asset_service.py`
3. `test_network_service.py`
4. `test_port_map_service.py`
5. `test_policy_service.py`
6. `test_asset_contact_service.py`

- [ ] **Step 2: 커밋**

```bash
git add tests/infra/
git commit -m "test: port infra tests from inframgr"
```

### Task 8.4: 모듈 격리 테스트 확인

`test_module_isolation.py`는 이미 Task 3.6에서 생성됨. 인프라 모듈 이식 후 다시 실행하여 격리가 유지되는지 확인.

- [ ] **Step 1: 모듈 격리 테스트 실행**

```bash
pytest tests/test_module_isolation.py -v
```

위반이 있으면 해당 import를 수정한다.

### Task 8 검증

- [ ] **검증: 전체 테스트 통과**

```bash
pytest tests/ -v --tb=short
```

```bash
git commit --allow-empty -m "milestone: Task 8 complete - all tests passing"
```

---

## Task 9: Standalone 배포 준비

**Files:**

- Modify: `docker-compose.yml` (확인)
- Create: `.env.standalone.example`

### Task 9.1: Standalone 환경 설정 파일

- [ ] **Step 1: .env.standalone.example 생성**

```
APP_ENV=production
DATABASE_URL=postgresql://pjtmgr:pjtmgr@db:5432/pjtmgr
SESSION_SECRET_KEY=change-me-in-production
BOOTSTRAP_ADMIN_LOGIN_ID=admin
BOOTSTRAP_ADMIN_PASSWORD=change-me
BOOTSTRAP_ADMIN_NAME=현장관리자
APP_PORT=9000
ENABLED_MODULES=common,infra
DB_PASSWORD=pjtmgr
```

- [ ] **Step 2: 커밋**

```bash
git add .env.standalone.example
git commit -m "infra: add standalone deployment example config"
```

### Task 9.2: Standalone 동작 검증

- [ ] **Step 1: ENABLED_MODULES=common,infra로 앱 기동**

```bash
ENABLED_MODULES=common,infra python -c "
from app.main import app
routes = [r.path for r in app.routes if hasattr(r, 'path')]
# 인프라 라우트 존재
assert any('/projects' in r for r in routes), 'projects route missing'
# 회계 라우트 미존재
assert not any('/contracts' in r for r in routes), 'contracts route should not exist'
print('Standalone verification passed')
"
```

- [ ] **Step 2: export/import CLI 플레이스홀더 생성**

```bash
mkdir -p app/cli
```

`app/cli/export_standalone.py`:

```python
"""
Standalone 배포용 데이터 내보내기 CLI.

TODO: MVP 이후 구현
- User, Role 내보내기
- Customer + Contact 내보내기
- Setting, TermConfig 내보내기
- 지정 Project + 하위 엔티티 내보내기
- JSON 포맷 출력

Usage:
    python -m app.cli.export_standalone --modules common,infra --project-id 42 --output data.json
"""

def main():
    raise NotImplementedError("Export CLI is planned for post-MVP")


if __name__ == "__main__":
    main()
```

`app/cli/import_standalone.py` — 동일 패턴의 플레이스홀더.

- [ ] **Step 3: 커밋**

```bash
git add -A
git commit -m "feat: standalone deployment config and CLI placeholders"
```

### Task 9 검증

- [ ] **검증: 전체 테스트 + standalone 모드 동작**

```bash
pytest tests/ -v --tb=short
```

```bash
git commit --allow-empty -m "milestone: Task 9 complete - migration finished"
```

---

## 최종 정리

- [ ] **Step 1: PROJECT_STRUCTURE.md를 실제 구조로 업데이트**

실제 파일 구조를 반영하여 `docs/PROJECT_STRUCTURE.md` 재작성.

- [ ] **Step 2: KNOWN_ISSUES.md 업데이트**

- "모듈화 마이그레이션 진행 중" → 삭제
- 남아있는 이슈 정리 (export/import CLI 미구현, 감사 로그 미연동 등)

- [ ] **Step 3: docs/inframgr-reference/ 정리 여부 결정**

마이그레이션 완료 후 참조 자료가 더 이상 필요없으면 삭제. 필요하면 유지.

- [ ] **Step 4: 최종 커밋**

```bash
git add -A
git commit -m "docs: finalize documentation after modular migration"
git tag post-migration
```
