# 프로젝트 구조

> 파일 단위 프로젝트 구조와 모듈별 역할.
> 디렉토리/파일 추가/삭제 시 이 문서도 함께 갱신한다.
>
> **참고**: 아래 구조는 모듈화 마이그레이션 목표 구조이다. 마이그레이션 진행 중에는 코드가 아직 구 구조(`app/models/`, `app/schemas/` 등)에 있을 수 있다. (계획)

---

## 앱 엔트리포인트 및 core

```text
app/
├── main.py                          # uvicorn 엔트리포인트, ENABLED_MODULES 기반 동적 모듈 등록
└── core/                            # 모듈-독립 인프라
    ├── app_factory.py               # FastAPI 앱 생성, 전역 예외 핸들러 등록
    ├── config.py                    # 환경변수/설정값 로드, ENABLED_MODULES 파싱
    ├── database.py                  # SQLAlchemy 엔진/세션 설정 (PostgreSQL)
    ├── exceptions.py                # 커스텀 예외 클래스 (401~422)
    ├── base_model.py                # TimestampMixin, 공통 Base
    ├── _normalize.py                # 날짜/월 정규화 (normalize_month, normalize_date)
    ├── auth/                        # 인증/인가
    │   ├── authorization.py         # can_*() 공통 권한 함수, 모듈 접근 제어
    │   ├── constants.py             # 역할 상수
    │   ├── dependencies.py          # get_current_user, require_admin, require_module_access
    │   ├── middleware.py            # 세션 인증 미들웨어
    │   ├── password.py              # 비밀번호 해싱 (bcrypt)
    │   ├── router.py                # /api/v1/auth 라우터 (로그인/로그아웃)
    │   └── service.py               # 인증 서비스 (사용자 검증, 비밀번호 정책)
    └── startup/                     # 초기화
        ├── lifespan.py              # FastAPI lifespan (startup/shutdown)
        ├── database_init.py         # DB 스키마 준비, Alembic 실행
        └── bootstrap.py             # 초기 관리자 계정 생성, 기본 역할 시드
```

## 공통모듈 (common) — 항상 활성

```text
app/modules/common/
├── models/
│   ├── user.py                  # User (사용자)
│   ├── user_preference.py       # UserPreference (사용자 설정)
│   ├── login_failure.py         # LoginFailure (로그인 실패 기록)
│   ├── role.py                  # Role (RBAC 역할, permissions JSON)
│   ├── customer.py              # Customer (거래처)
│   ├── customer_contact.py      # CustomerContact (거래처 담당자)
│   ├── customer_contact_role.py # CustomerContactRole (담당자 역할)
│   ├── setting.py               # Setting (시스템 설정)
│   ├── term_config.py           # TermConfig (UI 용어 설정)
│   └── audit_log.py             # AuditLog (감사 로그)
├── schemas/
├── services/
│   ├── user.py                  # 사용자 CRUD, CSV 일괄 등록
│   ├── customer.py              # 거래처/담당자 CRUD
│   ├── setting.py               # 시스템 설정 CRUD
│   ├── term_config.py           # 용어 설정 CRUD, 시드 데이터
│   ├── user_preference.py       # 사용자 환경설정
│   ├── health.py                # 헬스체크 (DB 연결 확인)
│   └── audit.py                 # 감사 로그 유틸
├── routers/
│   ├── users.py                 # /api/v1/users
│   ├── customers.py             # /api/v1/customers
│   ├── settings.py              # /api/v1/settings
│   ├── term_configs.py          # /api/v1/term-configs
│   ├── health.py                # /api/v1/health
│   ├── user_preferences.py      # /api/v1/preferences
│   ├── roles.py                 # /api/v1/roles
│   └── pages.py                 # 공통 HTML 페이지 렌더링
└── templates/
```

## 회계모듈 (accounting)

```text
app/modules/accounting/
├── models/
│   ├── contract.py              # Contract (사업 원장)
│   ├── contract_period.py       # ContractPeriod (사업 기간/연도)
│   ├── contract_contact.py      # ContractContact (Period별 담당자)
│   ├── contract_type_config.py  # ContractTypeConfig (사업유형 설정)
│   ├── monthly_forecast.py      # MonthlyForecast (월별 예상 매출/GP)
│   ├── transaction_line.py      # TransactionLine (매출/매입 실적)
│   ├── receipt.py               # Receipt (입금)
│   └── receipt_match.py         # ReceiptMatch (입금 배분)
├── schemas/
├── services/
│   ├── contract.py              # 사업/Period CRUD, 소프트 삭제/복구
│   ├── _contract_helpers.py     # 사업 관련 교차 도메인 헬퍼
│   ├── contract_contact.py      # 사업 담당자 매핑
│   ├── contract_type_config.py  # 사업유형 CRUD, 시드 데이터
│   ├── monthly_forecast.py      # Forecast CRUD
│   ├── transaction_line.py      # 매출/매입 실적 CRUD
│   ├── receipt.py               # 입금 CRUD
│   ├── receipt_match.py         # FIFO 자동 배분, 수동 배분
│   ├── forecast_sync.py         # Forecast -> 실적 동기화
│   ├── ledger.py                # 원장 뷰 (통합 조회)
│   ├── metrics.py               # 공통 집계 엔진
│   ├── dashboard.py             # 대시보드 집계
│   ├── report.py                # 보고서 데이터 생성
│   ├── _report_export.py        # 보고서 Excel Export
│   ├── importer.py              # Excel Import
│   └── exporter.py              # Excel Export (영업관리 원장)
├── routers/
│   ├── contracts.py             # /api/v1/contracts
│   ├── contract_contacts.py     # /api/v1/contract-contacts
│   ├── contract_types.py        # /api/v1/contract-types
│   ├── forecasts.py             # /api/v1/.../forecasts
│   ├── transaction_lines.py     # /api/v1/.../transaction-lines
│   ├── receipts.py              # /api/v1/.../receipts
│   ├── receipt_matches.py       # /api/v1/.../receipt-matches
│   ├── dashboard.py             # /api/v1/dashboard
│   ├── reports.py               # /api/v1/reports
│   └── excel.py                 # /api/v1/excel
└── templates/
```

## 인프라모듈 (infra) — 이식 예정

```text
app/modules/infra/
├── models/
│   ├── project.py               # Project (프로젝트)
│   ├── project_phase.py         # ProjectPhase (프로젝트 단계)
│   ├── project_deliverable.py   # ProjectDeliverable (산출물)
│   ├── asset.py                 # Asset (기술 자산)
│   ├── asset_ip.py              # AssetIP (자산 IP)
│   ├── ip_subnet.py             # IpSubnet (IP 대역)
│   ├── port_map.py              # PortMap (포트맵)
│   ├── policy_definition.py     # PolicyDefinition (정책 정의)
│   ├── policy_assignment.py     # PolicyAssignment (정책 적용 상태)
│   └── asset_contact.py         # AssetContact (자산 담당자 매핑)
├── schemas/
├── services/
├── routers/
└── templates/
```

## 프론트엔드

```text
app/static/
├── js/
│   ├── utils.js                 # 공통 유틸 (fmt, fmtNumber, fmtPct 등)
│   ├── acct_*.js                # 회계모듈 JS (접두사: acct_)
│   ├── infra_*.js               # 인프라모듈 JS (접두사: infra_)
│   └── lucide.js                # 아이콘 라이브러리
├── css/
│   ├── base.css                 # 전역 스타일, CSS 변수 (light/dark)
│   ├── components.css           # 재사용 컴포넌트
│   ├── acct_*.css               # 회계모듈 CSS (접두사: acct_)
│   ├── infra_*.css              # 인프라모듈 CSS (접두사: infra_)
│   ├── login.css                # 로그인 전용
│   └── change_password.css      # 비밀번호 변경 전용
└── img/                         # 이미지 리소스

app/templates/                   # 공통 템플릿
├── base.html                    # 공통 레이아웃 (동적 네비게이션)
├── login.html                   # 로그인
└── change_password.html         # 비밀번호 변경
```

## 테스트

```text
tests/
├── conftest.py                  # DB 세션 (PostgreSQL), 기본 유저/역할 fixture
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
├── test_database.py             # 스키마 정합성
├── test_startup.py              # bootstrap, lifespan
└── test_module_isolation.py     # accounting <-> infra import 금지 검증
```

## DB 마이그레이션

```text
alembic/
├── env.py                       # Alembic 환경 설정
└── versions/                    # 단일 migration 체인 (통합 후 새 initial)
```

## 루트 파일

```text
├── alembic.ini              # Alembic 설정
├── requirements.txt         # Python 의존성
├── .env                     # 환경변수 (git 미추적)
├── .env.example             # 환경변수 템플릿 (배포 시 참조)
├── Dockerfile               # 컨테이너 이미지 빌드
├── docker-compose.yml       # 컨테이너 실행 구성 (앱 + PostgreSQL)
├── .dockerignore            # Docker 빌드 제외 파일
├── CLAUDE.md                # 상위 개발 지침
└── README.md                # 프로젝트 소개
```
