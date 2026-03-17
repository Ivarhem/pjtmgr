# 프로젝트 구조

> 파일 단위 프로젝트 구조와 모듈별 역할.
> 디렉토리/파일 추가·삭제 시 이 문서도 함께 갱신한다.

---

## 앱 엔트리포인트

```text
app/
├── main.py                  # uvicorn 엔트리포인트
├── app_factory.py           # FastAPI 앱 생성, 전역 예외 핸들러 등록
├── config.py                # 환경변수·설정값 로드
├── database.py              # SQLAlchemy 엔진·세션 설정
└── exceptions.py            # 커스텀 예외 클래스 (401~422)
```

## 인증·인가

```text
app/auth/
├── authorization.py         # can_*() 권한 함수, apply_contract_scope()
├── constants.py             # 역할 상수 (ROLE_ADMIN 등)
├── dependencies.py          # get_current_user, require_admin
├── middleware.py            # 세션 인증 미들웨어
├── password.py              # 비밀번호 해싱 (PBKDF2-SHA256)
├── router.py                # /api/v1/auth 라우터 (로그인/로그아웃)
└── service.py               # 인증 서비스 (사용자 검증, 비밀번호 정책)
```

## 모델 (ORM)

```text
app/models/
├── base.py                  # TimestampMixin, Base 클래스
├── contract.py              # Contract (사업 원장)
├── contract_period.py       # ContractPeriod (사업 기간/연도)
├── contract_contact.py      # ContractContact (Period별 담당자)
├── contract_type_config.py  # ContractTypeConfig (사업유형 설정)
├── customer.py              # Customer (거래처)
├── customer_contact.py      # CustomerContact (거래처 담당자)
├── customer_contact_role.py # CustomerContactRole (담당자 역할)
├── monthly_forecast.py      # MonthlyForecast (월별 예상 매출/GP)
├── transaction_line.py      # TransactionLine (매출/매입 실적)
├── receipt.py               # Receipt (입금)
├── receipt_match.py         # ReceiptMatch (입금 배분)
├── user.py                  # User (사용자)
├── user_preference.py       # UserPreference (사용자 설정)
├── login_failure.py         # LoginFailure (로그인 실패 기록)
├── audit_log.py             # AuditLog (감사 로그)
├── setting.py               # Setting (시스템 설정)
└── term_config.py           # TermConfig (UI 용어 설정)
```

## 스키마 (Pydantic)

```text
app/schemas/
├── _normalize.py            # 날짜/월 정규화 (normalize_month, normalize_date)
├── auth.py                  # LoginRequest, ChangePasswordRequest
├── contract.py              # Contract/Period Create, Update, Read
├── contract_contact.py      # ContractContact 스키마
├── contract_type_config.py  # ContractType 스키마
├── customer.py              # Customer 스키마
├── customer_contact.py      # CustomerContact 스키마
├── customer_contact_role.py # CustomerContactRole 스키마
├── monthly_forecast.py      # MonthlyForecast 스키마
├── receipt.py               # Receipt 스키마
├── receipt_match.py         # ReceiptMatch 스키마
├── report.py                # ReportFilter, 보고서 응답 스키마
├── setting.py               # SettingRead, SettingUpdate
├── term_config.py           # TermConfig 스키마
├── transaction_line.py      # TransactionLine 스키마
└── user.py                  # User 스키마
```

## 라우터 (API)

```text
app/routers/
├── pages.py                 # HTML 페이지 렌더링 (Jinja2)
├── contracts.py             # /api/v1/contracts — 사업 CRUD, Period 관리
├── customers.py             # /api/v1/customers — 거래처 CRUD, 관련 조회
├── contract_contacts.py     # /api/v1/contract-contacts — 사업 담당자
├── contract_types.py        # /api/v1/contract-types — 사업유형 설정
├── forecasts.py             # /api/v1/.../forecasts — Forecast CRUD
├── transaction_lines.py     # /api/v1/.../transaction-lines — 매출/매입 실적
├── receipts.py              # /api/v1/.../receipts — 입금 CRUD
├── receipt_matches.py       # /api/v1/.../receipt-matches — 입금 배분
├── dashboard.py             # /api/v1/dashboard — 대시보드 KPI/차트
├── reports.py               # /api/v1/reports — 보고서 조회/Excel Export
├── excel.py                 # /api/v1/excel — Excel Import (3단계)
├── users.py                 # /api/v1/users — 사용자 관리 (admin)
├── settings.py              # /api/v1/settings — 시스템 설정
├── term_configs.py          # /api/v1/term-configs — 용어 설정
└── user_preferences.py      # /api/v1/preferences — 사용자 환경설정
```

## 서비스 (비즈니스 로직)

```text
app/services/
├── contract.py              # 사업/Period CRUD, 소프트 삭제·복구
├── _contract_helpers.py     # 사업 관련 교차 도메인 헬퍼
├── customer.py              # 거래처/담당자 CRUD + re-export
├── _customer_helpers.py     # 거래처 관련 사업·재무·입금 조회
├── contract_contact.py      # 사업 담당자 매핑, 피벗 뷰
├── contract_type_config.py  # 사업유형 CRUD, 시드 데이터
├── monthly_forecast.py      # Forecast CRUD
├── transaction_line.py      # 매출/매입 실적 CRUD, 일괄 처리
├── receipt.py               # 입금 CRUD
├── receipt_match.py         # FIFO 자동 배분, 수동 배분
├── forecast_sync.py         # Forecast → 실적 동기화
├── ledger.py                # 원장 뷰 (매출/매입/입금 통합 조회)
├── metrics.py               # 공통 집계 엔진 (필터, 데이터 로더, KPI)
├── dashboard.py             # 대시보드 집계 (목표 vs 실적, 추이)
├── report.py                # 보고서 데이터 생성 (4종) + re-export
├── _report_export.py        # 보고서 Excel Export (4종)
├── importer.py              # Excel Import (검증, 파싱, 저장)
├── exporter.py              # Excel Export (영업관리 원장)
├── user.py                  # 사용자 CRUD, CSV 일괄 등록
├── user_preference.py       # 사용자 환경설정
├── setting.py               # 시스템 설정 CRUD
├── term_config.py           # 용어 설정 CRUD, 시드 데이터
└── audit.py                 # 감사 로그 유틸
```

## 초기화

```text
app/startup/
├── lifespan.py              # FastAPI lifespan (startup/shutdown)
├── database_init.py         # DB 스키마 준비, Alembic 실행
└── bootstrap.py             # 초기 관리자 계정 생성
```

## 프론트엔드

```text
app/static/
├── js/
│   ├── utils.js             # 공통 유틸 (fmt, fmtNumber, fmtPct 등)
│   ├── contract_detail.js   # 사업 상세 (Forecast, 원장, 입금, 배분)
│   ├── contracts.js         # 사업 관리 목록
│   ├── my_contracts.js      # 내 사업
│   ├── customers.js         # 거래처 관리
│   ├── dashboard.js         # 대시보드 차트
│   ├── reports.js           # 보고서
│   ├── users.js             # 사용자 관리
│   ├── system.js            # 시스템 설정
│   └── lucide.js            # 아이콘 라이브러리
├── css/
│   ├── base.css             # 전역 스타일, CSS 변수 (light/dark)
│   ├── components.css       # 재사용 컴포넌트 (필터, 드롭다운, pill-tab)
│   ├── contract_detail.css  # 사업 상세 전용
│   ├── customers.css        # 거래처 전용
│   ├── dashboard.css        # 대시보드 전용
│   ├── reports.css          # 보고서 전용
│   ├── system.css           # 시스템 설정 전용
│   ├── login.css            # 로그인 전용
│   └── change_password.css  # 비밀번호 변경 전용
└── img/                     # 이미지 리소스

app/templates/
├── base.html                # 공통 레이아웃 (네비, 스크립트 로드)
├── index.html               # 메인 (→ 내 사업으로 리다이렉트)
├── login.html               # 로그인
├── change_password.html     # 비밀번호 변경
├── my_contracts.html         # 내 사업
├── contracts.html           # 사업 관리
├── contract_detail.html     # 사업 상세
├── customers.html           # 거래처 관리
├── dashboard.html           # 대시보드
├── reports.html             # 보고서
├── users.html               # 사용자 관리
├── system.html              # 시스템 설정
├── audit_logs.html          # 감사 로그 (placeholder)
└── {components}/
    └── _modal_add_contract.html  # 사업 등록 모달 (공유 컴포넌트)
```

## 테스트

```text
tests/
├── conftest.py              # 테스트 DB, 세션, 픽스처
├── test_contract_service.py # 사업/Period CRUD 테스트
├── test_contract_schema.py  # 스키마 정규화 테스트
├── test_receipt_match_service.py # FIFO 배분, 수동 배분 테스트
├── test_transaction_safety.py   # 트랜잭션 원자성, 기간 격리 테스트
├── test_report_service.py   # 보고서 집계, GP/AR 계산 테스트
├── test_dashboard_service.py # 대시보드 집계 테스트
├── test_importer.py         # Excel Import 검증 테스트
├── test_metrics.py          # 필터, 집계 유틸 테스트
├── test_auth_service.py     # 인증 서비스 테스트
├── test_database.py         # DB 스키마 테스트
└── test_startup.py          # bootstrap, lifespan 테스트
```

## DB 마이그레이션

```text
alembic/
├── env.py                   # Alembic 환경 설정
└── versions/
    ├── 0001_initial_baseline.py  # 초기 스키마 베이스라인
    └── 0002_add_login_failures.py # 로그인 실패 기록 테이블
```

## 루트 파일

```text
├── alembic.ini              # Alembic 설정
├── requirements.txt         # Python 의존성
├── .env                     # 환경변수 (git 미추적)
├── CLAUDE.md                # 상위 개발 지침
└── README.md                # 프로젝트 소개
```
