# pjtmgr 모듈화 마이그레이션 설계

> 작성일: 2026-03-18
> 상태: 승인 대기

---

## 1. 배경 및 목적

### 현재 상황

- **pjtmgr**: 영업부서 매입매출 관리 서비스. 파일럿 운영 중 (v0.3). SQLite, 단일 앱 구조.
- **inframgr**: SI 프로젝트 기술 인벤토리 관리 서비스. MVP 구현 완료. PostgreSQL, 단일 앱 구조.

두 프로젝트는 기술 스택(FastAPI + SQLAlchemy + Jinja2/HTMX + AG Grid), 아키텍처 패턴(서비스 레이어, 커스텀 예외, Alembic, 세션 인증), 코드 규칙이 거의 동일하며 사용자/거래처/인증 등 공통 도메인이 중복된다.

### 통합 목적

1. 공통 도메인(사용자, 거래처, 인증) 중복 제거
2. 영업팀은 회계모듈만, 기술팀은 인프라모듈만 사용 가능하도록 분리
3. 인프라모듈을 오프라인 환경(프로젝트 현장)에 standalone 배포 가능
4. 회계모듈과 인프라모듈 간 의존성 zero

### 핵심 제약

- 인프라모듈 standalone 배포 시 공통 데이터(사용자, 거래처)는 로컬 DB에서 생성/수정 가능 (양방향 동기화 불필요, 외부 반출 불가 가정)
- 프로젝트 이름은 `pjtmgr` 유지 (추후 변경 가능)
- 기존 pjtmgr는 복사본이므로 제자리 리팩터링 진행

### 파일럿 데이터 처리

기존 pjtmgr/inframgr의 파일럿 데이터는 **폐기**한다. 통합 후 PostgreSQL에서 새로 시작한다. 이유:

- SQLite → PostgreSQL 전환으로 데이터 이관 스크립트가 필요하나, 파일럿 수준 데이터에 투자할 가치가 낮음
- 패스워드 해싱 방식 변경 (PBKDF2 → bcrypt)
- 모델 구조 변경 (Role FK, Customer 확장 등)

### 롤백 전략

- 단계 1 시작 전 git tag(`pre-migration`)를 생성한다.
- 각 단계 완료 시 커밋하고, 단계별 검증 기준을 통과한 후 다음 단계로 진행한다.
- 단계 3(디렉토리 구조 재편)이 사실상 돌아오기 어려운 지점(point of no return)이다. 이 단계 이전까지는 `git reset`으로 원복 가능.
- 기존 pjtmgr는 복사본이므로 최악의 경우 원본에서 다시 시작할 수 있다.

---

## 2. 아키텍처: 단일 코드베이스 + 배포 프로필

마이크로서비스 대신 **단일 코드베이스에서 환경변수로 모듈 활성화**하는 구조를 채택한다.

```
하나의 리포, 하나의 Docker 이미지, 환경변수로 모듈 선택
ENABLED_MODULES=common,accounting,infra   → 본사 전체
ENABLED_MODULES=common,infra              → 현장 standalone
ENABLED_MODULES=common,accounting         → 영업 전용
```

**선택 이유:**

- 오프라인 배포 단순성: 이미지 하나 + env 파일 하나
- 개발 효율: 리포 하나, 테스트 한 번, 공통 코드 변경 즉시 반영
- 모듈 격리는 코드 규칙 + lint로 충분
- 규모가 커져서 진짜 분리가 필요해지면, 의존성이 이미 끊어져 있으므로 추출 가능

---

## 3. 디렉토리 구조

```
app/
├── main.py                          # ENABLED_MODULES 기반 동적 모듈 등록
├── core/                            # 모듈-독립 인프라
│   ├── app_factory.py               # FastAPI 앱 생성, 전역 예외 핸들러
│   ├── config.py                    # Settings (.env), ENABLED_MODULES 파싱
│   ├── database.py                  # SQLAlchemy engine, SessionLocal, Base
│   ├── exceptions.py                # 커스텀 예외 6종
│   ├── base_model.py                # TimestampMixin, 공통 Base
│   ├── auth/                        # 인증 미들웨어, 세션, 패스워드
│   │   ├── middleware.py
│   │   ├── dependencies.py          # get_current_user, require_admin
│   │   ├── password.py              # bcrypt 해싱
│   │   ├── router.py                # /api/v1/auth (login, logout, change-pw)
│   │   ├── service.py
│   │   └── constants.py
│   └── startup/                     # lifespan, DB init, bootstrap
│       ├── lifespan.py
│       ├── database_init.py
│       └── bootstrap.py
│
├── modules/
│   ├── common/                      # 항상 활성
│   │   ├── models/                  # User, Customer, CustomerContact, CustomerContactRole
│   │   │                            # Role, Setting, TermConfig, AuditLog,
│   │   │                            # LoginFailure, UserPreference
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── routers/                 # users, customers, settings, term_configs,
│   │   │                            # health, preferences, roles
│   │   └── templates/
│   │
│   ├── accounting/                  # common만 참조 가능
│   │   ├── models/                  # Contract, ContractPeriod, ContractContact
│   │   │                            # ContractTypeConfig, MonthlyForecast
│   │   │                            # TransactionLine, Receipt, ReceiptMatch
│   │   ├── schemas/
│   │   ├── services/                # contract, receipt_match, metrics, dashboard
│   │   │                            # report, importer, exporter, forecast_sync, ledger
│   │   ├── routers/                 # contracts, forecasts, transaction_lines, receipts
│   │   │                            # receipt_matches, dashboard, reports, excel,
│   │   │                            # contract_types, contract_contacts
│   │   └── templates/
│   │
│   └── infra/                       # common만 참조 가능
│       ├── models/                  # Project, ProjectPhase, ProjectDeliverable
│       │                            # Asset, IpSubnet, AssetIP, PortMap
│       │                            # PolicyDefinition, PolicyAssignment
│       │                            # AssetContact
│       ├── schemas/
│       ├── services/
│       ├── routers/
│       └── templates/
│
├── static/
│   ├── js/                          # 공통 utils.js + 모듈별 JS
│   └── css/                         # 공통 base.css, components.css + 모듈별 CSS
│
├── templates/
│   ├── base.html                    # 공통 레이아웃 (동적 네비게이션)
│   └── login.html, change_password.html
│
└── alembic/
```

---

## 4. 모듈 등록 메커니즘

### 환경변수

```
ENABLED_MODULES=common,accounting,infra
APP_PORT=9000
```

### 동적 등록 흐름 (main.py)

1. **모든 모델은 항상 import** — Alembic 정합성을 위해 비활성 모듈 테이블도 DB에 존재
2. **라우터는 활성 모듈만 등록** — `ENABLED_MODULES`에 따라 `app.include_router()` 호출
3. **템플릿 로더에 활성 모듈 경로만 추가** — Jinja2 `ChoiceLoader`로 구성
4. **`enabled_modules`를 Jinja2 global로 주입** — base.html 네비게이션 동적 렌더링

### 모듈 간 import 규칙

```
core/              ← 누구든 import 가능
modules/common/    ← accounting, infra가 import 가능
modules/accounting ← accounting 내부에서만
modules/infra      ← infra 내부에서만
accounting ↔ infra   절대 금지
```

`ruff` 또는 `import-linter` 설정과 `test_module_isolation.py`로 CI에서 강제한다.

### Alembic 전략

- 단일 migration 체인 유지
- 기존 pjtmgr/inframgr migration 모두 폐기, 통합 후 새 initial migration 생성
- 비활성 모듈의 테이블도 스키마에 존재하되 라우터가 없으니 접근되지 않음
- **수용된 제약**: standalone 배포 시에도 모든 테이블(accounting 포함)이 생성됨. 스키마 수준 결합이지만, 운영상 무해하며 단일 migration 체인의 단순성을 우선한다.

---

## 5. DB 전환 (SQLite → PostgreSQL)

| 항목 | 현재 (pjtmgr) | 변경 후 |
|------|----------------|---------|
| DB | SQLite (sales.db) | PostgreSQL 16 |
| 드라이버 | 동기 sqlite | psycopg |
| connect_args | `check_same_thread=False` | 제거 |
| WAL / busy_timeout | SQLite 전용 PRAGMA | 제거 |
| 워커 제한 | 단일 워커 | 제한 해제, Gunicorn 멀티워커 가능 |
| Docker | 앱 컨테이너만 | 앱 + PostgreSQL 컨테이너 |
| 포트 | 8000 | 앱: 9000, DB: 5432 |

---

## 6. 인증/권한 통합

### 패스워드 해싱

bcrypt로 통일한다. 기존 PBKDF2-SHA256 해시는 파일럿 데이터이므로 재생성한다.

### auth 코드 배치

- **`core/auth/`**: 미들웨어, 세션, 패스워드, 공통 권한 함수
- **공통 권한 함수** (`core/auth/authorization.py`): `can_manage_users()`, `can_manage_settings()`, `require_admin()`, `can_access_module()`, `get_module_access_level()`
- **모듈 고유 권한**: 각 모듈 서비스 내부에 배치

### 권한 함수 배치 맵

```
core/auth/authorization.py:
  can_manage_users()
  can_manage_settings()
  require_admin()
  can_access_module(user, module_name)
  get_module_access_level(user, module_name)

modules/accounting/services/:
  can_delete_contract()
  can_delete_transaction_line()
  can_delete_receipt()
  can_import()
  can_view_reports()
  can_export()
  apply_contract_scope()
  check_contract_access()
  check_period_access()

modules/infra/services/:
  can_edit_inventory()
  can_manage_policies()
```

---

## 7. RBAC (역할 기반 접근 제어)

### 설계: 실용적 RBAC

풀 RBAC(resource × action 조합)는 이 규모에 과하다. 모듈 접근 + 모듈별 권한 수준으로 구성한다.

### Role 모델

```python
class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int]
    name: Mapped[str]            # "영업담당자", "기술담당자", "PM", "관리자"
    is_system: Mapped[bool]      # True면 삭제/수정 불가 (기본 역할)
    permissions: Mapped[dict]    # JSON 컬럼
```

### permissions JSON 구조

```json
{
  "admin": false,
  "modules": {
    "accounting": "full",
    "infra": "read"
  }
  // 향후 풀 RBAC 확장 시:
  // "resources": {
  //   "contract": ["create", "read", "update"],
  //   "asset": ["read"]
  // }
}
```

| 권한 수준 | 의미 |
|-----------|------|
| `null` / 키 없음 | 접근 불가 (메뉴 미노출) |
| `"read"` | 조회만 |
| `"full"` | CRUD 전체 |
| `"admin"` 플래그 | 시스템 설정, 사용자 관리, 삭제 등 관리 기능 |

### 기본 역할 (시드 데이터, is_system=True)

| 역할명 | admin | accounting | infra |
|--------|-------|------------|-------|
| 관리자 | true | full | full |
| 영업담당자 | false | full | null |
| 기술담당자 | false | null | full |
| PM | false | full | full |

관리자가 커스텀 역할 생성 가능 (예: "영업+인프라조회" → `{"admin": false, "modules": {"accounting": "full", "infra": "read"}}`).

### User 모델 통합 스키마

두 프로젝트의 User 모델을 통합한다.

| 필드 | pjtmgr | inframgr | 통합 후 |
|------|---------|----------|---------|
| `id` | ✅ | ✅ | 유지 |
| `login_id` | ✅ | ✅ | 유지 |
| `name` | ✅ | ✅ | 유지 |
| `password_hash` | `hashed_password` | `password_hash` | `password_hash`로 통일 (bcrypt) |
| `role` / `role_id` | `role` (문자열) | `role` (문자열) | `role_id` (FK → Role.id)로 전환 |
| `is_active` | ✅ | ✅ | 유지 |
| `department` | ✅ | ❌ | 유지 |
| `position` | ✅ | ❌ | 유지 |
| `must_change_password` | ✅ | ❌ | 유지 |
| `external_id` | ❌ | ✅ | **제거** (sync_service 제거에 따라 불필요) |
| `external_source` | ❌ | ✅ | **제거** |

- `get_current_user()`에서 `user.role_obj.permissions` 참조

### 최종 가시 모듈

```
사용자에게 보이는 모듈 = ENABLED_MODULES ∩ user.role.permissions.modules
홈 화면 = 가시 모듈 중 우선순위 (accounting > infra, 또는 사용자 설정)
```

### `read` 권한 수준 적용 패턴

`read` 권한은 모듈 단위로 라우터 레벨에서 강제한다.

- 각 모듈 라우터에 `Depends(require_module_access("accounting", "full"))` 같은 의존성을 적용
- `read` 수준 사용자가 POST/PATCH/DELETE 엔드포인트에 접근하면 403 반환
- GET 엔드포인트는 `read` 이상이면 허용
- 기존 `can_delete_*()` 등의 함수는 `admin` 플래그 체크를 유지하되, 모듈 접근 수준도 함께 확인

```python
# core/auth/dependencies.py
def require_module_access(module: str, min_level: str = "read"):
    """라우터 Depends로 사용. read/full 수준 검사."""
    def checker(current_user: User = Depends(get_current_user)):
        level = get_module_access_level(current_user, module)
        if level is None:
            raise PermissionDeniedError("모듈 접근 권한 없음")
        if min_level == "full" and level == "read":
            raise PermissionDeniedError("읽기 전용 권한")
        return current_user
    return Depends(checker)

# 사용 예시
@router.get("/contracts")          # require_module_access("accounting", "read")
@router.post("/contracts")         # require_module_access("accounting", "full")
@router.delete("/contracts/{id}")  # require_module_access("accounting", "full") + can_delete_contract()
```

### 풀 RBAC 확장 대비

- Role 모델과 permissions JSON 구조에 `resources` 키 플레이스홀더 + 주석
- `authorization.py`에 `check_resource_permission(user, resource, action)` 스텁 함수 + TODO 주석
- 현 단계에서는 모듈 수준 권한만 구현, resource 수준은 기존 하드코딩(`can_delete_*`)으로 admin 플래그 체크

---

## 8. 엔티티 배치

### 모듈별 엔티티 매핑

| 모듈 | 엔티티 |
|------|--------|
| **core** | (코드만, 모델 없음) — auth, exceptions, config, database, startup |
| **common** | User, UserPreference, LoginFailure, Role |
|  | Customer, CustomerContact, CustomerContactRole |
|  | Setting, TermConfig, AuditLog |
| **accounting** | Contract, ContractPeriod, ContractContact |
|  | ContractTypeConfig |
|  | MonthlyForecast |
|  | TransactionLine, Receipt, ReceiptMatch |
| **infra** | Project, ProjectPhase, ProjectDeliverable |
|  | Asset, AssetIP, IpSubnet, PortMap |
|  | PolicyDefinition, PolicyAssignment |
|  | AssetContact |

### 크로스 모듈 FK 참조

```
accounting.Contract.end_customer_id     → common.Customer.id      ✅
accounting.Contract.owner_user_id       → common.User.id           ✅
accounting.TransactionLine.customer_id  → common.Customer.id       ✅
accounting.TransactionLine.created_by   → common.User.id           ✅

infra.AssetContact.contact_id           → common.CustomerContact.id ✅

accounting ↔ infra 직접 FK 없음  ✅
```

### Contract ↔ Project 연결

직접 FK 없이, 양쪽 모듈 모두 활성일 때만 동작하는 선택적 매핑 테이블을 common에 둘 수 있다. MVP에서는 구현하지 않으며, 필요 시 추가한다.

---

## 9. Partner → Customer 통합

### Customer 모델 확장

inframgr의 Partner 속성을 흡수한다.

| 신규 필드 | 출처 | 설명 |
|-----------|------|------|
| `customer_type` | Partner.partner_type | 고객사/공급사/유지보수사/통신사/null |
| `phone` | Partner.contact_phone | 대표 연락처 |
| `address` | Partner.address | 주소 |
| `note` | Partner.note | 비고 |

**Partner.project_id FK 처리**: inframgr의 Partner는 `project_id` FK를 가지고 있었으나, Customer가 common 모듈로 이동하므로 이 FK는 제거한다 (common → infra 의존성 위반). 프로젝트와 거래처의 연결이 필요하면 인프라모듈에 `ProjectCustomer` 매핑 테이블을 둔다.

### CustomerContact 모델 확장

inframgr의 Contact 속성을 흡수한다.

| 신규 필드 | 출처 | 설명 |
|-----------|------|------|
| `department` | Contact.department | 부서 |
| `title` | Contact.title | 직위 |
| `emergency_phone` | Contact.emergency_phone | 비상연락처 |
| `note` | Contact.note | 비고 |

### 역할 통합

- CustomerContactRole 테이블 유지 (pjtmgr의 역할 모델이 더 성숙)
- inframgr의 `Contact.role` 문자열은 이식 시 CustomerContactRole로 매핑
- AssetContact는 인프라모듈에서 `CustomerContact.id`를 참조 (테이블명 `contacts` → `customer_contacts`로 변경됨에 주의)

### external_id / external_source 필드 처리

inframgr의 Partner, Contact, Project, User에 있던 `external_id`, `external_source` 컬럼은 sync_service 용도였다. sync_service를 제거하므로 이 필드들도 모두 제거한다.

### Project.client_name 처리

inframgr의 `Project.client_name`은 자유 텍스트 필드다. 통합 후에는 `Project.customer_id` FK (→ common.Customer)로 전환하여 데이터 정합성을 확보한다. `client_name`은 제거한다. 이는 허용된 의존 방향(infra → common)이다.

### 영향 범위

- 인프라모듈의 Partner/Contact 관련 코드를 Customer/CustomerContact 기반으로 재작성
- 회계모듈은 기존 Customer 구조 그대로, 신규 필드만 스키마에 추가
- 공통모듈의 customers 라우터에 `customer_type` 필터링 지원

---

## 10. 네비게이션 및 프론트엔드 전략

### base.html 동적 네비게이션

`app_factory.py`에서 Jinja2 global로 `enabled_modules`와 사용자의 가시 모듈을 주입한다.

```
네비게이션 = ENABLED_MODULES ∩ user.role.permissions.modules
```

- 공통 메뉴 (항상): 거래처, 사용자(관리자), 시스템설정(관리자)
- accounting 활성: 사업관리, 대시보드, 보고서
- infra 활성: 프로젝트, 자산, IP인벤토리, 포트맵, 정책

### 템플릿 로더

Jinja2 `ChoiceLoader`로 공통 → 활성 모듈 순서로 경로 추가.

### 페이지 분리 원칙

영업모듈 페이지와 인프라모듈 페이지는 **완전히 분리**한다. 양쪽 모듈을 모두 사용하는 사용자(PM 등)라도 하나의 화면에 두 모듈의 정보가 섞이지 않는다.

- 각 모듈은 자체 페이지 세트를 가짐 (templates 디렉토리 분리)
- 공통 엔티티(거래처 등)의 관리 화면은 공통모듈이 소유하되, 모듈별 확장 정보(회계: 계약 이력 / 인프라: 자산 담당)는 해당 모듈 활성 시에만 탭/섹션으로 노출
- 네비게이션에서 회계/인프라 메뉴 그룹을 시각적으로 구분

### 템플릿 네이밍 규칙

Jinja2 ChoiceLoader 사용 시 모듈 간 파일명 충돌을 방지하기 위해:

- 공통 템플릿: `base.html`, `login.html` 등 (접두사 없음)
- 모듈별 템플릿: 모듈명 접두사 사용 — `acct_contracts.html`, `infra_assets.html`
- 또는 모듈별 하위 디렉토리: `accounting/contracts.html`, `infra/assets.html`

### CSS/JS 전략

- `base.css`, `components.css`, `utils.js`: 두 프로젝트 것을 병합. pjtmgr 기준, inframgr 전용 부분만 추가.
- 모듈별 JS/CSS: 접두사로 구분 — `acct_*.js`, `infra_*.js`, `acct_*.css`, `infra_*.css`
- 각 페이지 템플릿의 `{% block scripts %}`/`{% block styles %}`로 필요한 파일만 개별 로드.

### URL 라우트 충돌 방지

모든 API는 `/api/v1/` prefix를 유지한다. 모듈 간 URL 충돌이 없음을 확인한다:

- accounting: `/contracts`, `/dashboard`, `/reports`, `/excel` 등
- infra: `/projects`, `/assets`, `/ip-subnets`, `/port-maps`, `/policies` 등
- 공통: `/customers`, `/users`, `/settings`, `/health`, `/auth` 등

현재 두 프로젝트의 라우트에 충돌하는 경로는 없다.

### 홈 화면

사용자의 가시 모듈 중 우선순위에 따라 결정:

- accounting 가시 → `/my-contracts`
- infra만 가시 → `/projects`

---

## 11. Standalone 배포 (인프라모듈 오프라인)

### 시나리오

```
본사 서버                          프로젝트 현장 (오프라인)
┌─────────────────────┐           ┌─────────────────────┐
│ ENABLED_MODULES=    │           │ ENABLED_MODULES=    │
│ common,accounting,  │  docker   │ common,infra        │
│ infra               │  save →   │                     │
│ PostgreSQL          │           │ PostgreSQL           │
│ (전체 데이터)        │           │ (초기 데이터)        │
└─────────────────────┘           └─────────────────────┘
```

### 배포 절차

```bash
# 본사: Docker 이미지 내보내기
docker save app:latest > app.tar

# 현장: 이미지 반입 + .env 설정
docker load < app.tar
# .env: ENABLED_MODULES=common,infra
docker compose up -d
```

### 초기 데이터 내보내기/가져오기 (MVP 이후)

관리자가 본사에서 특정 프로젝트 관련 데이터를 JSON으로 익스포트하는 CLI/관리 화면을 향후 구현한다.

**내보내는 데이터 범위:**

| 대상 | 범위 |
|------|------|
| User, Role | 관련 사용자 또는 전체 선택 |
| Customer + Contact | 관련 거래처 또는 전체 선택 |
| Setting, TermConfig | 전체 |
| Project + 하위 엔티티 | 지정 프로젝트만 |

### 설계 원칙

- export/import CLI는 MVP 이후 구현, 마이그레이션 단계에서는 구조만 준비
- 단방향 (본사 → 현장), 역동기화 없음
- 동일 Docker 이미지, `.env`만 다름
- 회계 테이블은 standalone DB에도 존재 (Alembic 정합성), 라우터만 미등록
- 현장 인스턴스에서도 공통 데이터(사용자, 거래처) 생성/수정 가능
- bootstrap admin으로 현장 자체 관리자 생성 가능

---

## 12. 테스트 전략

### DB fixture 변경

SQLite in-memory → PostgreSQL 테스트 컨테이너 (`testcontainers-python` 또는 테스트용 별도 DB).

### 테스트 구조

```
tests/
├── conftest.py                    # DB 세션, 기본 유저/역할 fixture
├── common/
│   ├── test_user_service.py
│   ├── test_customer_service.py
│   └── test_auth_service.py
├── accounting/
│   ├── test_contract_service.py
│   ├── test_receipt_match_service.py
│   ├── test_transaction_safety.py
│   ├── test_metrics.py
│   ├── test_dashboard_service.py
│   ├── test_report_service.py
│   └── test_importer.py
├── infra/
│   ├── test_project_service.py
│   ├── test_asset_service.py
│   ├── test_network_service.py
│   ├── test_port_map_service.py
│   ├── test_policy_service.py
│   └── test_asset_contact_service.py
├── test_database.py               # 스키마 정합성
├── test_startup.py                # bootstrap, lifespan
└── test_module_isolation.py       # accounting ↔ infra import 금지 검증
```

### 신규 테스트

| 테스트 | 목적 |
|--------|------|
| `test_module_isolation.py` | accounting ↔ infra 간 import 금지 검증 (AST 파싱) |
| `test_module_registration.py` | ENABLED_MODULES에 따른 라우터 등록/미등록 검증 |
| `test_role_permissions.py` | 역할별 모듈 접근, read/full 권한 수준 동작 검증 |

---

## 13. 마이그레이션 단계

### 단계 1: 지침 및 문서 재편

- CLAUDE.md를 통합 프로젝트 목적에 맞게 재작성 (모듈 구조, RBAC, 확장된 도메인 용어, 경로 업데이트)
- README.md 재작성 (통합 프로젝트 소개, PostgreSQL 기반 실행 방법)
- docs/guidelines 업데이트 (파일 경로: `app/exceptions.py` → `app/core/exceptions.py` 등)
- docs/DECISIONS.md에 통합 결정 기록
- **검증**: 문서 내 경로 참조가 계획된 구조와 일치

### 단계 2: 프로젝트 인프라 전환

- SQLite → PostgreSQL (database.py, docker-compose.yml, requirements.txt)
- 포트 9000으로 변경
- bcrypt 의존성 추가, PBKDF2 제거
- 기존 Alembic migration 폐기
- **검증**: `docker compose up`으로 PostgreSQL 연결, 앱 기동 성공

### 단계 3: 디렉토리 구조 재편

- `app/core/` 생성 → app_factory, config, database, exceptions, auth, startup 이동
- `app/core/` 하위에 `_normalize.py` 배치 (회계/인프라 모두 사용 가능한 공통 유틸)
- `app/modules/common/` 생성 → User, Customer, Setting 등 이동
- `app/modules/accounting/` 생성 → Contract, Transaction, Receipt 등 이동
- `app/modules/infra/` 생성 → 빈 구조 scaffolding
- import 경로 전체 수정
- **검증**: 모든 import 오류 없이 앱 기동, 기존 테스트 통과

### 단계 4: 모듈 등록 메커니즘

- ENABLED_MODULES 설정 추가
- main.py / app_factory.py 동적 라우터 등록
- Jinja2 ChoiceLoader, base.html 동적 네비게이션
- **검증**: `ENABLED_MODULES=common,accounting`으로 기존 기능 정상 동작. infra 라우트 404 확인.
- 참고: 이 시점에서는 아직 구 admin/user 역할 시스템 사용. 모듈 접근 제어는 단계 5에서 완성.

### 단계 5: RBAC 전환

- Role 모델 생성, 기본 역할 시드
- User.role (문자열) → User.role_id (FK) 전환, 컬럼명 `hashed_password` → `password_hash`
- authorization.py 리팩터링 (모듈 접근 + read/full 권한 수준)
- `require_module_access()` 의존성 구현 및 라우터 적용
- 관리 화면에 역할 관리 추가
- bcrypt 전환 (기존 사용자 전체 `must_change_password=True` 설정)
- 풀 RBAC 확장 플레이스홀더 + 주석
- **검증**: 역할별 모듈 접근/차단, read 권한 사용자의 POST/DELETE 차단 확인

### 단계 6: Partner → Customer 통합

- Customer 모델에 신규 필드 추가 (customer_type, phone, address, note)
- CustomerContact에 신규 필드 추가 (department, title, emergency_phone, note)
- Partner.project_id FK 제거 (인프라모듈에 ProjectCustomer 매핑 테이블 준비)
- external_id/external_source 필드 제거 (Partner, Contact, Project, User)
- 공통모듈 라우터/서비스/스키마에 확장 필드 반영
- **검증**: 기존 거래처 CRUD 정상, 신규 필드 입력/조회 확인

### 단계 7: 인프라모듈 이식

- `docs/inframgr-reference/`에서 모델/스키마/서비스/라우터 이식
- Partner → Customer, Contact → CustomerContact 참조 교체 (테이블명 `contacts` → `customer_contacts`)
- Project.client_name → Project.customer_id FK 전환
- sync_service, sync_router 제거
- 템플릿/JS/CSS 이식 (접두사 규칙 적용: `infra_*.js`, `infra_*.css`)
- base.html 네비게이션에 인프라 메뉴 그룹 추가
- **검증**: `ENABLED_MODULES=common,accounting,infra`로 전체 동작. 양쪽 모듈 페이지 독립 확인.

### 단계 8: Alembic 재구성 및 테스트

- 전체 모델 기반 새 initial migration 생성
- 테스트 구조 재편 (모듈별 디렉토리)
- 모듈 격리, RBAC, 모듈 등록 테스트 추가
- **검증**: 전체 테스트 통과, `test_module_isolation.py` 통과

### 단계 9: Standalone 배포 준비

- Docker 설정 확인 (동일 이미지, env만 다르게)
- **검증**: `ENABLED_MODULES=common,infra`로 기동. 인프라 기능 정상, 회계 라우트 404 확인.
- export/import CLI 플레이스홀더 (MVP 이후 구현)

---

## 14. inframgr 참조 자료

마이그레이션에 필요한 inframgr 전체 소스코드와 문서가 `docs/inframgr-reference/`에 저장되어 있다.

| 파일 | 내용 |
|------|------|
| `models.py` | 전체 ORM 모델 (13개 엔티티) |
| `schemas.py` | Pydantic 스키마 |
| `services.py` | 비즈니스 로직 (8개 서비스) |
| `routers.py` | API 라우터 (16개) |
| `core.py` | main, app_factory, config, auth, startup |
| `tests.py` | 전체 테스트 (11개 모듈) |
| `templates.html` | Jinja2 템플릿 (10개) |
| `static-js.js` | JavaScript (8개 파일) |
| `static-css.css` | CSS (3개 파일) |
| `alembic-versions.py` | DB 마이그레이션 (4개) |
| `ARCHITECTURE.md` 등 | 설계 문서 |
| `guideline-*.md` | 작업 지침 |
| `docker-compose.yml`, `Dockerfile`, `requirements.txt` | 인프라 설정 |
