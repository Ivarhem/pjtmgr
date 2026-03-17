# 모듈 재구성 계획: 모노레포 + 독립 앱

## 1. 아키텍처 방향

- **모노레포 1개**에 공통모듈, 회계모듈 (향후 인프라모듈) 배치
- 각 모듈은 **독립 FastAPI 앱**으로 실행
- 프론트엔드(templates/static)도 **모듈별 분리**
- 공유 DB (동일 데이터베이스, 별도 프로세스)
- 공유 코드는 `shared/` 패키지로 추출

---

## 2. 현재 구조 → 목표 구조

### 현재 (단일 앱)
```
sales/
└── app/
    ├── models/      # 18개 모델 혼재
    ├── schemas/     # 15개 스키마 혼재
    ├── routers/     # 17개 라우터 혼재
    ├── services/    # 21개 서비스 혼재
    ├── auth/        # 인증
    ├── startup/     # 초기화
    ├── templates/   # HTML 14개 혼재
    ├── static/      # JS/CSS 혼재
    ├── app_factory.py
    ├── config.py
    ├── database.py
    └── exceptions.py
```

### 목표 (모노레포, 독립 앱)
```
sales-platform/                     # 새 모노레포
│
├── shared/                         # ── 공유 패키지 ──
│   ├── __init__.py
│   ├── database.py                 # Base, engine, get_db
│   ├── config.py                   # 환경변수 (DB URL, 세션 등)
│   ├── exceptions.py               # 커스텀 예외
│   ├── auth/                       # 인증/인가 공통 로직
│   │   ├── __init__.py
│   │   ├── authorization.py        # can_*(), apply_contract_scope()
│   │   ├── constants.py            # ROLE_ADMIN 등
│   │   ├── dependencies.py         # get_current_user, require_admin
│   │   ├── middleware.py           # 세션 인증 미들웨어
│   │   ├── password.py             # PBKDF2-SHA256
│   │   └── service.py              # 인증 서비스
│   └── models/                     # 공유 Base + Mixin
│       ├── __init__.py
│       └── base.py                 # DeclarativeBase, TimestampMixin
│
├── common/                         # ── 공통모듈 (독립 앱) ──
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # uvicorn 엔트리포인트
│   │   ├── app_factory.py          # FastAPI 앱 생성
│   │   ├── startup/
│   │   │   ├── __init__.py
│   │   │   ├── lifespan.py
│   │   │   ├── database_init.py    # Alembic 실행
│   │   │   └── bootstrap.py        # 초기 데이터 시드
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── user_preference.py
│   │   │   ├── login_failure.py
│   │   │   ├── customer.py
│   │   │   ├── customer_contact.py
│   │   │   ├── customer_contact_role.py
│   │   │   ├── contract.py
│   │   │   ├── contract_period.py
│   │   │   ├── contract_contact.py
│   │   │   ├── contract_type_config.py
│   │   │   ├── setting.py
│   │   │   ├── term_config.py
│   │   │   └── audit_log.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── _normalize.py
│   │   │   ├── auth.py
│   │   │   ├── user.py
│   │   │   ├── customer.py
│   │   │   ├── customer_contact.py
│   │   │   ├── customer_contact_role.py
│   │   │   ├── contract.py
│   │   │   ├── contract_contact.py
│   │   │   ├── contract_type_config.py
│   │   │   ├── setting.py
│   │   │   └── term_config.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py             # /api/v1/auth (로그인/로그아웃)
│   │   │   ├── health.py
│   │   │   ├── pages.py            # 공통모듈 HTML 페이지
│   │   │   ├── users.py
│   │   │   ├── customers.py
│   │   │   ├── contracts.py
│   │   │   ├── contract_contacts.py
│   │   │   ├── contract_types.py
│   │   │   ├── settings.py
│   │   │   ├── term_configs.py
│   │   │   └── user_preferences.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── customer.py         # 거래처 CRUD (재무 조회 제외)
│   │   │   ├── contract.py
│   │   │   ├── contract_contact.py
│   │   │   ├── _contract_helpers.py
│   │   │   ├── contract_type_config.py
│   │   │   ├── user_preference.py
│   │   │   ├── setting.py
│   │   │   ├── term_config.py
│   │   │   └── audit.py
│   │   ├── templates/
│   │   │   ├── base.html           # 공통 레이아웃
│   │   │   ├── index.html
│   │   │   ├── login.html
│   │   │   ├── change_password.html
│   │   │   ├── my_contracts.html
│   │   │   ├── contracts.html
│   │   │   ├── contract_detail.html
│   │   │   ├── customers.html
│   │   │   ├── users.html
│   │   │   ├── system.html
│   │   │   ├── audit_logs.html
│   │   │   └── {components}/
│   │   │       └── _modal_add_contract.html
│   │   └── static/
│   │       ├── js/
│   │       │   ├── utils.js
│   │       │   ├── contracts.js
│   │       │   ├── my_contracts.js
│   │       │   ├── contract_detail.js  # 원장/입금/배분 탭은 회계 API 호출
│   │       │   ├── customers.js
│   │       │   ├── users.js
│   │       │   ├── system.js
│   │       │   └── lucide.js
│   │       ├── css/
│   │       │   ├── base.css
│   │       │   ├── components.css
│   │       │   ├── contract_detail.css
│   │       │   ├── customers.css
│   │       │   ├── login.css
│   │       │   ├── change_password.css
│   │       │   └── system.css
│   │       └── img/
│   │           └── logo.svg
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_contract_service.py
│   │   ├── test_contract_schema.py
│   │   ├── test_auth_service.py
│   │   ├── test_database.py
│   │   └── test_startup.py
│   ├── alembic/                    # 공통모듈 전용 마이그레이션
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── accounting/                     # ── 회계모듈 (독립 앱) ──
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── app_factory.py
│   │   ├── startup/
│   │   │   ├── __init__.py
│   │   │   ├── lifespan.py
│   │   │   └── database_init.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── transaction_line.py
│   │   │   ├── receipt.py
│   │   │   ├── receipt_match.py
│   │   │   └── monthly_forecast.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── transaction_line.py
│   │   │   ├── receipt.py
│   │   │   ├── receipt_match.py
│   │   │   ├── monthly_forecast.py
│   │   │   └── report.py
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   ├── pages.py            # 회계모듈 HTML 페이지
│   │   │   ├── transaction_lines.py
│   │   │   ├── receipts.py
│   │   │   ├── receipt_matches.py
│   │   │   ├── forecasts.py
│   │   │   ├── dashboard.py
│   │   │   ├── reports.py
│   │   │   └── excel.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── transaction_line.py
│   │   │   ├── receipt.py
│   │   │   ├── receipt_match.py
│   │   │   ├── monthly_forecast.py
│   │   │   ├── forecast_sync.py
│   │   │   ├── ledger.py
│   │   │   ├── metrics.py          # 집계 엔진
│   │   │   ├── dashboard.py
│   │   │   ├── report.py
│   │   │   ├── _report_export.py
│   │   │   ├── _customer_helpers.py # 거래처 재무 조회 (공통→회계 이전)
│   │   │   ├── importer.py
│   │   │   └── exporter.py
│   │   ├── templates/
│   │   │   ├── base.html           # 회계 레이아웃 (공통 base 상속 or 독립)
│   │   │   ├── dashboard.html
│   │   │   └── reports.html
│   │   └── static/
│   │       ├── js/
│   │       │   ├── dashboard.js
│   │       │   └── reports.js
│   │       └── css/
│   │           ├── dashboard.css
│   │           └── reports.css
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_receipt_match_service.py
│   │   ├── test_transaction_safety.py
│   │   ├── test_report_service.py
│   │   ├── test_dashboard_service.py
│   │   ├── test_importer.py
│   │   └── test_metrics.py
│   ├── alembic/                    # 회계모듈 전용 마이그레이션
│   │   ├── env.py
│   │   └── versions/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── Dockerfile
│
├── docker-compose.yml              # 전체 서비스 오케스트레이션
├── .env                            # 공유 환경변수
├── .env.example
├── README.md
├── CLAUDE.md
└── docs/
    ├── DECISIONS.md
    ├── KNOWN_ISSUES.md
    ├── PROJECT_CONTEXT.md
    ├── PROJECT_STRUCTURE.md
    └── guidelines/
        ├── backend.md
        ├── frontend.md
        ├── auth.md
        └── excel.md
```

---

## 3. 모듈 분류 상세

### 공통모듈 (`common/`)

프로젝트(계약), 거래처, 사용자, 인증, 시스템 설정을 관리하는 독립 앱.

| 레이어 | 파일 | 비고 |
|--------|------|------|
| **models** | User, UserPreference, LoginFailure, Customer, CustomerContact, CustomerContactRole, Contract, ContractPeriod, ContractContact, ContractTypeConfig, Setting, TermConfig, AuditLog | 13개 |
| **schemas** | user, auth, customer, customer_contact, customer_contact_role, contract, contract_contact, contract_type_config, setting, term_config, _normalize | 11개 |
| **routers** | auth, health, pages, users, customers, contracts, contract_contacts, contract_types, settings, term_configs, user_preferences | 11개 |
| **services** | user, customer, contract, contract_contact, _contract_helpers, contract_type_config, user_preference, setting, term_config, audit | 10개 |
| **templates** | base, index, login, change_password, my_contracts, contracts, contract_detail, customers, users, system, audit_logs, _modal_add_contract | 12개 |
| **static/js** | utils, contracts, my_contracts, contract_detail, customers, users, system, lucide | 8개 |
| **static/css** | base, components, contract_detail, customers, login, change_password, system | 7개 |

### 회계모듈 (`accounting/`)

매출/매입, 입금, 배분, 예측, 대시보드, 보고서를 관리하는 독립 앱.

| 레이어 | 파일 | 비고 |
|--------|------|------|
| **models** | TransactionLine, Receipt, ReceiptMatch, MonthlyForecast | 4개 |
| **schemas** | transaction_line, receipt, receipt_match, monthly_forecast, report | 5개 |
| **routers** | health, pages, transaction_lines, receipts, receipt_matches, forecasts, dashboard, reports, excel | 9개 |
| **services** | transaction_line, receipt, receipt_match, monthly_forecast, forecast_sync, ledger, metrics, dashboard, report, _report_export, _customer_helpers, importer, exporter | 13개 |
| **templates** | base (회계용), dashboard, reports | 3개 |
| **static/js** | dashboard, reports | 2개 |
| **static/css** | dashboard, reports | 2개 |

### 공유 패키지 (`shared/`)

두 모듈이 공통으로 사용하는 인프라 코드. pip install 가능한 내부 패키지.

| 파일 | 역할 |
|------|------|
| `database.py` | DeclarativeBase, engine 생성, get_db |
| `config.py` | DATABASE_URL, 세션, 보안 설정 |
| `exceptions.py` | UnauthorizedError~ValidationError |
| `auth/` | 세션 인증, 권한 검사, 미들웨어 |
| `models/base.py` | TimestampMixin |

---

## 4. 모듈 간 의존성 규칙

```
┌─────────────┐       ┌─────────────┐
│   common    │       │ accounting  │
│  (독립 앱)   │       │  (독립 앱)   │
└──────┬──────┘       └──────┬──────┘
       │                     │
       │  ┌──────────────┐   │
       └─►│   shared     │◄──┘
          │  (패키지)     │
          └──────────────┘
```

| 방향 | 허용 | 비고 |
|------|------|------|
| `common → shared` | ✅ | config, database, auth, exceptions |
| `accounting → shared` | ✅ | config, database, auth, exceptions |
| `accounting → common` | ✅ (모델만) | 공통모듈의 ORM 모델 import (같은 DB) |
| `common → accounting` | ❌ | 역방향 금지 |

### 회계모듈의 공통모델 참조 방식

회계모듈은 공통모듈의 **ORM 모델만** 직접 import합니다 (같은 DB를 공유하므로):

```python
# accounting/app/services/transaction_line.py
from common.app.models.contract import Contract           # 공통모듈 모델
from common.app.models.contract_period import ContractPeriod
from accounting.app.models.transaction_line import TransactionLine  # 자체 모델
```

서비스/라우터/스키마는 참조하지 않습니다. 필요 시 **HTTP API 호출**로 통신합니다.

---

## 5. 교차 의존성 해결

### 5.1 `_customer_helpers.py` → 회계모듈로 이전

현재 `app/services/_customer_helpers.py`는 거래처의 재무 데이터(매출/매입/입금/미수금)를 조회합니다.
- TransactionLine, Receipt, ReceiptMatch를 직접 import
- 이는 **회계 도메인의 책임**이므로 `accounting/app/services/_customer_helpers.py`로 이전

공통모듈의 `customer.py` 서비스에서 재무 조회 관련 함수를 제거하고,
프론트엔드(contract_detail.js 등)가 회계모듈 API를 직접 호출하도록 변경합니다.

### 5.2 `customer.py` 서비스 분리

현재 `app/services/customer.py`가 import하는 회계 모델들:
- `TransactionLine`, `Receipt`, `ReceiptMatch` — 거래처 삭제 가능 여부 확인용

**해결**: 거래처 삭제 시 회계모듈에 HTTP API로 "이 거래처에 연결된 거래가 있는지" 확인 요청.
또는 DB 직접 조회(공유 DB이므로)하되, accounting 모델을 import.

### 5.3 `importer.py`의 거래처/계약유형 참조

현재 importer가 `customer.get_or_create_by_name`, `contract_type_config.get_valid_codes`를 호출.
- **공유 DB**이므로 공통모듈의 모델을 직접 import하여 조회 가능
- 또는 공통모듈 API 호출 (`POST /api/v1/customers/get-or-create`)

### 5.4 ORM relationship 크로스 모듈 참조

`Customer` 모델의 `transaction_lines`, `receipts` relationship:
- **문자열 참조**로 유지: `relationship("TransactionLine", back_populates="customer")`
- 같은 `Base`를 공유하고, 앱 시작 시 양쪽 모델을 모두 import하면 동작

### 5.5 `metrics.py`의 공통모델 참조

`metrics.py`는 Contract, ContractPeriod, Customer, User를 직접 import:
- 회계모듈에 위치하되, 공통모듈의 **ORM 모델만** import (허용된 방향)

---

## 6. 프론트엔드 분리 전략

### contract_detail 페이지 (경계에 걸치는 페이지)

`contract_detail.html`은 공통모듈에 위치하되, 원장/입금/배분 탭은 회계모듈 API를 호출합니다:

```
contract_detail.js
├── 계약 기본 정보 탭 → 공통모듈 API (GET /api/v1/contracts/{id})
├── Forecast 탭     → 회계모듈 API (GET /api/v1/forecasts/...)
├── 원장 탭         → 회계모듈 API (GET /api/v1/transaction-lines/...)
├── 입금 탭         → 회계모듈 API (GET /api/v1/receipts/...)
└── 배분 탭         → 회계모듈 API (GET /api/v1/receipt-matches/...)
```

### 공통 레이아웃

- `base.html`은 공통모듈이 소유 (네비게이션 바, 글로벌 스타일)
- 회계모듈은 자체 `base.html`을 가지되, 같은 디자인 시스템 사용
- 또는 공통모듈의 `base.html`을 심볼릭 링크/복사로 공유

### API 포트 분리

```
공통모듈: http://localhost:8000  (또는 /common prefix)
회계모듈: http://localhost:8001  (또는 /accounting prefix)
```

프론트엔드 JS에서 API 호출 시 대상 모듈의 base URL을 구분합니다.

---

## 7. Docker Compose 구성

```yaml
services:
  common:
    build: ./common
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [db]

  accounting:
    build: ./accounting
    ports: ["8001:8001"]
    env_file: .env
    depends_on: [db, common]

  db:
    image: postgres:16
    volumes: [pgdata:/var/lib/postgresql/data]

  # 향후
  # infra:
  #   build: ./infra
  #   ports: ["8002:8002"]

volumes:
  pgdata:
```

---

## 8. Alembic 전략

### 옵션 A: 모듈별 독립 Alembic (권장)

각 모듈이 자신의 모델에 대한 마이그레이션만 관리:
- `common/alembic/` → User, Customer, Contract 등 테이블
- `accounting/alembic/` → TransactionLine, Receipt 등 테이블

**장점**: 모듈별 독립 배포 가능
**주의**: FK 참조 테이블이 상대 모듈에 있으므로 실행 순서 보장 필요 (common → accounting)

### 옵션 B: 루트 레벨 통합 Alembic

`sales-platform/alembic/`에서 양쪽 모델을 모두 import하여 단일 마이그레이션 관리.

**장점**: FK 의존성 자동 해결
**단점**: 모듈 독립성 저하

---

## 9. 실행 단계

### Phase 1: 모노레포 스캐폴딩
1. 새 리포지토리 `sales-platform/` 생성
2. `shared/`, `common/`, `accounting/` 디렉토리 트리 생성
3. `shared/` 패키지 작성 (database, config, exceptions, auth)

### Phase 2: 공통모듈 구축
1. 공통 모델/스키마/서비스/라우터 이전
2. 공통 프론트엔드 이전 (templates/static)
3. `app_factory.py` + `main.py` 작성
4. 공통모듈 단독 실행 확인

### Phase 3: 회계모듈 구축
1. 회계 모델/스키마/서비스/라우터 이전
2. 회계 프론트엔드 이전
3. 교차 의존성 해결 (_customer_helpers 이전, import 경로 갱신)
4. 회계모듈 단독 실행 확인

### Phase 4: 통합 검증
1. Docker Compose로 전체 기동
2. 전체 테스트 실행
3. Alembic 마이그레이션 검증
4. 프론트엔드 크로스 모듈 API 호출 검증

### Phase 5: 문서 갱신
1. CLAUDE.md 갱신 (새 구조 반영)
2. PROJECT_STRUCTURE.md 갱신
3. DECISIONS.md에 모듈 분리 결정 기록
4. README.md 갱신 (실행 방법)

---

## 10. 향후 인프라 모듈

```
sales-platform/
├── infra/                          # ← 미래 인프라 모듈
│   ├── app/
│   │   ├── models/                 # 물품, 구성현황, 자산
│   │   ├── schemas/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── templates/
│   │   └── static/
│   ├── tests/
│   ├── alembic/
│   ├── requirements.txt
│   └── Dockerfile
```

의존성: `infra → shared ✅`, `infra → common (모델) ✅`, `infra → accounting ❌`

---

## 11. 리스크 및 주의사항

| 항목 | 리스크 | 대응 |
|------|--------|------|
| **공유 DB FK** | 회계 테이블이 공통 테이블 FK 참조 | Alembic 실행 순서 보장 (common 먼저) |
| **ORM Base 공유** | 두 앱이 같은 Base를 써야 relationship 동작 | `shared/models/base.py`에 단일 정의 |
| **세션 공유** | 두 앱 간 로그인 세션 공유 필요 | 같은 SESSION_SECRET_KEY + 쿠키 도메인 설정, 또는 공통모듈이 JWT 발급 |
| **CORS** | 프론트엔드가 다른 포트의 API 호출 | 리버스 프록시(nginx) 또는 CORS 설정 |
| **프론트엔드 UX** | 페이지 전환 시 다른 앱으로 이동 | 리버스 프록시로 단일 도메인 유지, path prefix로 라우팅 |
| **배포 복잡도** | 서비스 수 증가 | Docker Compose로 로컬 관리, 프로덕션은 K8s 고려 |
| **contract_detail 경계** | 한 페이지에서 두 모듈 API 사용 | JS에서 모듈별 base URL 구분, 리버스 프록시 권장 |
