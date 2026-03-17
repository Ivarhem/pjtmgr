# 영업부서 매입매출 관리 앱

영업부서의 사업(Contract)을 원장으로 관리하고, 사업별 매입/매출 내역을 월별로 입력·조회하며
필요한 형태의 Excel 파일로 Export하는 사내 전용 웹 애플리케이션.

> **현재 상태**: 파일럿 테스트 진행 (v0.3)
>
> **정보 소재 (Source of Truth)** — 모델 필드·API 상세는 소스 코드(`app/models/`, `app/routers/`) 참조.
> 코딩 규칙은 `CLAUDE.md`, 작업 지침은 `docs/guidelines/`, 아키텍처 결정은 `docs/DECISIONS.md`,
> 알려진 제약은 `docs/KNOWN_ISSUES.md`, 프로젝트 배경은 `docs/PROJECT_CONTEXT.md` 참조.

---

## 핵심 흐름

```text
[앱에서 데이터 입력/관리]
       ↓
  사업 원장 (마스터)
  ├── 사업 기본정보 (사업유형, 담당, 거래처, 진행단계 등)
  ├── 사업기간 (ContractPeriod: Y25, Y26 등 연도 단위)
  ├── Forecast (ContractPeriod별 월별 예상 매출/GP)
  ├── TransactionLine (매출/매입 실적 라인)
  └── Receipt (입금 내역)
       ↓
  [Export]
  ├── [매입매출관리] Excel - 사업 단위
  └── [영업관리] Excel - 전체 원장 (월별 집계)
```

---

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| 백엔드 | Python 3.11+, FastAPI |
| ORM | SQLAlchemy 2.0 (Mapped 방식) |
| DB | SQLite (향후 PostgreSQL 마이그레이션 예정) |
| 프론트엔드 | Jinja2 + HTMX + AG Grid Community |
| Excel 처리 | openpyxl, pandas |
| 인증 | 세션 기반 (쿠키) |
| 포매터/린터 | black, ruff |
| 테스트 | pytest |

---

## 실행 방법

### 사전 요구사항

- Python 3.11 이상
- pip

### 설치 및 실행

```bash
# 1. 의존성 설치
python -m pip install -r requirements.txt

# 2. 환경변수 설정 (.env 파일 생성)
# SESSION_SECRET_KEY=<운영 환경 필수, 충분히 긴 랜덤 세션 비밀키>
# DATABASE_URL=sqlite:///./sales.db  (기본값, 환경별 DB 교체 가능)
# BOOTSTRAP_ADMIN_LOGIN_ID=admin
# BOOTSTRAP_ADMIN_PASSWORD=<초기 관리자 비밀번호>
# BOOTSTRAP_ADMIN_NAME=관리자

# 3. 서버 실행
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. 브라우저 접속
# http://localhost:8000
```

- 비개발 환경에서는 `SESSION_SECRET_KEY`가 없으면 앱이 시작되지 않는다.
- `DATABASE_URL`을 PostgreSQL 등으로 변경할 경우 해당 드라이버 설치와 backend별 연결 설정이 추가로 필요하다.

### 초기 설정

- 최초 실행 시 DB 테이블이 자동 생성됨
- 활성 관리자 계정이 없으면 bootstrap 환경변수(`BOOTSTRAP_ADMIN_LOGIN_ID`, `BOOTSTRAP_ADMIN_PASSWORD`, `BOOTSTRAP_ADMIN_NAME`)로 첫 관리자 계정을 생성
- Excel Import를 통해 기존 데이터 일괄 등록 가능 (관리자 전용)

---

## 아키텍처

```text
[브라우저]
  └─ HTML (Jinja2) + HTMX + AG Grid
       │  HTTP / JSON
[FastAPI 서버] ── [사내 네트워크 전용, 외부 차단]
  ├─ API 라우터 (/api/v1/...)
  ├─ 템플릿 렌더러
  ├─ 서비스 레이어 (비즈니스 로직)
  └─ DB 레이어 (ORM)
       │
    [SQLite / PostgreSQL]
```

- API와 템플릿 렌더링을 같은 FastAPI 인스턴스에서 처리
- LLM은 개발(코드 생성) 단계에서만 사용, 런타임에는 포함하지 않음

---

## 프로젝트 구조

```text
sales/
├── app/
│   ├── main.py               # FastAPI 앱 진입점
│   ├── app_factory.py        # FastAPI 앱 팩토리 (미들웨어·라우터·예외 핸들러 등록)
│   ├── migrations_legacy.py  # 경량 마이그레이션 (Alembic 도입 전 레거시)
│   ├── config.py             # 환경 설정
│   ├── database.py           # DB 연결
│   ├── exceptions.py         # 커스텀 예외 (NotFoundError 등)
│   ├── startup/              # 앱 초기화
│   │   ├── database_init.py  # DB 스키마 준비 + Alembic 연동
│   │   ├── bootstrap.py      # 초기 데이터 시드 (사업유형, 용어, 관리자)
│   │   └── lifespan.py       # FastAPI lifespan 컨텍스트 관리
│   ├── auth/                 # 인증/권한
│   │   ├── constants.py      # Role 타입, 역할 상수
│   │   ├── authorization.py  # 권한 판단 헬퍼 (can_*, apply_contract_scope)
│   │   ├── dependencies.py   # FastAPI 의존성 (get_current_user, require_admin)
│   │   ├── middleware.py     # 인증 미들웨어
│   │   ├── router.py         # 인증 API (login, logout, me)
│   │   ├── service.py        # 인증 서비스
│   │   └── password.py       # 비밀번호 해싱
│   ├── models/               # ORM 모델
│   │   ├── base.py           # TimestampMixin
│   │   ├── contract.py       # Contract (사업)
│   │   ├── contract_period.py # ContractPeriod (사업기간)
│   │   ├── contract_contact.py # ContractContact (사업별 담당자)
│   │   ├── monthly_forecast.py # MonthlyForecast (월별 Forecast)
│   │   ├── transaction_line.py # TransactionLine (매출/매입 실적)
│   │   ├── receipt.py        # Receipt (입금)
│   │   ├── receipt_match.py  # ReceiptMatch (입금 배분)
│   │   ├── customer.py       # Customer (거래처)
│   │   ├── customer_contact.py # CustomerContact (거래처 담당자)
│   │   ├── customer_contact_role.py # CustomerContactRole (담당자 역할)
│   │   ├── user.py           # User (사용자)
│   │   ├── user_preference.py # UserPreference (사용자 설정)
│   │   ├── setting.py        # Setting (앱 설정 key-value)
│   │   ├── audit_log.py      # AuditLog (감사 로그)
│   │   ├── contract_type_config.py # ContractTypeConfig (사업유형 설정)
│   │   ├── term_config.py    # TermConfig (용어 설정)
│   │   └── login_failure.py  # LoginFailure (로그인 실패 추적)
│   ├── schemas/              # Pydantic 스키마
│   │   ├── _normalize.py     # 날짜/월 정규화 유틸
│   │   ├── auth.py           # Login/ChangePassword 스키마
│   │   ├── contract.py       # Contract/ContractPeriod 스키마
│   │   ├── customer.py       # Customer 스키마
│   │   ├── customer_contact.py # CustomerContact 스키마
│   │   ├── customer_contact_role.py # CustomerContactRole 스키마
│   │   ├── contract_contact.py # ContractContact 스키마
│   │   ├── monthly_forecast.py # MonthlyForecast 스키마
│   │   ├── transaction_line.py # TransactionLine 스키마
│   │   ├── receipt.py        # Receipt 스키마
│   │   ├── receipt_match.py  # ReceiptMatch 스키마
│   │   ├── report.py         # 보고서 응답 스키마
│   │   ├── user.py           # User 스키마
│   │   ├── contract_type_config.py # ContractTypeConfig 스키마
│   │   ├── term_config.py    # TermConfig 스키마
│   │   └── setting.py        # Settings 스키마
│   ├── services/             # 비즈니스 로직
│   │   ├── _contract_helpers.py # 완료 기간 검사 등 공유 헬퍼
│   │   ├── contract.py       # 사업/기간 CRUD 서비스
│   │   ├── transaction_line.py # 매출/매입 실적 서비스
│   │   ├── receipt.py        # 입금 서비스
│   │   ├── monthly_forecast.py # 월별 Forecast 서비스
│   │   ├── forecast_sync.py  # Forecast → TransactionLine 동기화
│   │   ├── ledger.py         # 매출/매입 원장 뷰 서비스
│   │   ├── customer.py       # 거래처 서비스
│   │   ├── user.py           # 사용자 서비스
│   │   ├── contract_contact.py # 사업별 담당자 서비스
│   │   ├── dashboard.py      # 대시보드 데이터 집계 + 내 사업 요약
│   │   ├── report.py         # 보고서 데이터 및 Excel Export
│   │   ├── metrics.py        # 공통 집계 함수 (dashboard/report 공용)
│   │   ├── importer.py       # Excel Import 서비스
│   │   ├── exporter.py       # Excel Export 서비스
│   │   ├── receipt_match.py  # 입금 배분 서비스 (FIFO 자동 배분)
│   │   ├── audit.py          # 감사 로그 유틸
│   │   ├── setting.py        # 앱 설정 서비스
│   │   ├── user_preference.py # 사용자 설정 서비스
│   │   ├── contract_type_config.py # 사업유형 설정 서비스
│   │   └── term_config.py    # 용어 설정 서비스
│   ├── routers/              # API 라우터
│   │   ├── contracts.py      # 사업/기간/Ledger/내사업요약
│   │   ├── transaction_lines.py # 매출/매입 실적
│   │   ├── receipts.py       # 입금
│   │   ├── receipt_matches.py # 입금 배분
│   │   ├── forecasts.py      # Forecast/Forecast Sync
│   │   ├── customers.py      # 거래처/거래처 담당자
│   │   ├── users.py          # 사용자 관리
│   │   ├── contract_contacts.py # 사업별 담당자
│   │   ├── excel.py          # Excel Import/Export
│   │   ├── dashboard.py      # 대시보드 API
│   │   ├── reports.py        # 보고서 API
│   │   ├── settings.py       # 앱 설정
│   │   ├── user_preferences.py # 사용자 설정
│   │   ├── contract_types.py # 사업유형 관리
│   │   ├── term_configs.py   # 용어 설정
│   │   └── pages.py          # HTML 페이지 라우트 (템플릿 렌더링)
│   ├── templates/            # Jinja2 HTML 템플릿
│   │   ├── base.html         # 공통 레이아웃 (topbar, subnav)
│   │   ├── login.html        # 로그인
│   │   ├── change_password.html # 비밀번호 변경
│   │   ├── contracts.html    # 사업원장 목록
│   │   ├── my_contracts.html # 내 사업 목록
│   │   ├── contract_detail.html # 사업 상세
│   │   ├── customers.html    # 거래처 관리
│   │   ├── users.html        # 사용자 관리
│   │   ├── system.html       # 시스템 설정
│   │   ├── dashboard.html    # 대시보드
│   │   ├── reports.html      # 보고서
│   │   ├── audit_logs.html   # 감사 로그/변경 이력 화면 (현재 placeholder)
│   │   ├── index.html        # 리다이렉트 (→ /my-contracts)
│   │   └── {components}/     # 재사용 HTML 컴포넌트
│   │       └── _modal_add_contract.html
│   └── static/
│       ├── css/
│       │   ├── base.css        # 전역: reset, nav, 버튼, 모달, 유틸리티
│       │   ├── change_password.css # 비밀번호 변경 페이지 전용 스타일
│       │   ├── components.css  # 재사용 컴포넌트: filter-bar, chk-drop, grid
│       │   ├── contract_detail.css # 사업 상세 전용 스타일
│       │   ├── customers.css   # 거래처 관리 전용 스타일
│       │   ├── dashboard.css   # 대시보드 전용 스타일
│       │   ├── reports.css     # 보고서 전용 스타일
│       │   ├── system.css     # 시스템 관리 전용 스타일
│       │   └── login.css       # 로그인 페이지 전용 스타일
│       └── js/
│           ├── utils.js        # 공통 유틸 (fmt, fmtNumber 등)
│           ├── contracts.js    # 사업원장 페이지
│           ├── my_contracts.js # 내 사업 페이지
│           ├── contract_detail.js # 사업 상세 페이지
│           ├── customers.js    # 거래처 관리 페이지
│           ├── users.js        # 사용자 관리 페이지
│           ├── system.js       # 시스템 설정 페이지
│           ├── dashboard.js    # 대시보드 페이지
│           ├── reports.js      # 보고서 페이지
│           └── lucide.js       # 아이콘 라이브러리 (Lucide Icons)
├── docs/
│   ├── PROJECT_CONTEXT.md   # 프로젝트 배경/목적
│   ├── DECISIONS.md         # 아키텍처 결정 기록
│   ├── KNOWN_ISSUES.md      # 인지된 이슈/피드백
│   └── guidelines/          # 작업별 상세 지침
│       ├── frontend.md      # 프론트엔드(JS/CSS/HTML) 지침
│       ├── auth.md          # 인증/권한/보안 지침
│       └── excel.md         # Excel Import/Export 지침
├── scripts/
│   └── migrate_contacts.py   # DB 마이그레이션 헬퍼
├── tests/                    # pytest 테스트
│   ├── conftest.py           # 인메모리 SQLite 픽스처
│   ├── test_metrics.py       # 공통 집계 함수 테스트
│   ├── test_contract_service.py # Contract/Period 서비스 테스트
│   ├── test_contract_schema.py # Contract 스키마 정규화 테스트
│   ├── test_importer.py      # Excel Import 검증 테스트
│   ├── test_dashboard_service.py # 대시보드 목표 vs 실적/재집계 테스트
│   ├── test_report_service.py # 보고서 서비스/Export 회귀 테스트
│   ├── test_auth_service.py  # 로그인 잠금/비밀번호 정책 테스트
│   ├── test_receipt_match_service.py # ReceiptMatch 권한/FIFO 배분 테스트
│   ├── test_database.py      # DB 연결/기본 설정 테스트
│   ├── test_startup.py       # 앱 startup 분리/초기화 테스트
│   └── test_transaction_safety.py # 복합 서비스 rollback 테스트
├── alembic/                   # Alembic 마이그레이션
│   ├── env.py                # 마이그레이션 환경 설정
│   ├── script.py.mako        # 리비전 템플릿
│   └── versions/             # 마이그레이션 리비전 파일
├── alembic.ini                # Alembic 설정
├── requirements.txt          # Python 의존성
├── CLAUDE.md                 # 개발 지침/규칙
├── PILOT_TEST.md             # 파일럿 테스트 계획
└── README.md                 # 프로젝트 설명 (이 파일)
```

---

## 데이터 모델

> 각 테이블의 상세 필드는 `app/models/` 참조. 아래는 핵심 테이블과 관계만 표시한다.

### 핵심 테이블

| 테이블 | 설명 | 모델 파일 |
| ------ | ---- | --------- |
| users | 사용자/담당자 | `app/models/user.py` |
| customers | 거래처 (매출처/매입처 공용) | `app/models/customer.py` |
| customer_contacts | 거래처 담당자 (인물 중심) | `app/models/customer_contact.py` |
| customer_contact_roles | 담당자 역할 (1인 다역할) | `app/models/customer_contact_role.py` |
| contract_type_configs | 사업유형 설정 (동적 관리) | `app/models/contract_type_config.py` |
| contracts | 사업 (원장의 1행) | `app/models/contract.py` |
| contract_periods | 사업 기간 (연도 단위 버전) | `app/models/contract_period.py` |
| contract_contacts | 사업별 담당자 (Period·거래처 단위) | `app/models/contract_contact.py` |
| monthly_forecasts | 월별 Forecast (예상 매출/GP) | `app/models/monthly_forecast.py` |
| transaction_lines | 매출/매입 실적 (귀속월 기준) | `app/models/transaction_line.py` |
| receipts | 입금 내역 | `app/models/receipt.py` |
| receipt_matches | 입금 배분 (Receipt↔매출 매핑) | `app/models/receipt_match.py` |
| term_configs | UI 용어 설정 | `app/models/term_config.py` |
| user_preferences | 사용자별 설정 (KV) | `app/models/user_preference.py` |
| settings | 앱 설정 (KV) | `app/models/setting.py` |
| audit_logs | 감사 로그 | `app/models/audit_log.py` |
| login_failures | 로그인 실패 추적 | `app/models/login_failure.py` |

### 계산값 (조회 시 계산, DB 저장 안 함)

- GP = 매출 합계(line_type=revenue) - 매입 합계(line_type=cost)
- GP% = GP ÷ 매출 × 100
- 미수금 = 매출 확정 합계 - 배분완료(ReceiptMatch) 합계
- 미배분 입금 = 입금 합계 - 배분완료 합계
- 월별/분기별/연간/누적 집계

### 관계도

```text
User ──1:N──→ Contract (owner)
User ──1:N──→ ContractPeriod (Period별 owner)
Customer ──1:N──→ Contract (end_customer)
Customer ──1:N──→ ContractPeriod (Period별 매출처)
Customer ──1:N──→ CustomerContact ──1:N──→ CustomerContactRole
CustomerContact ──1:N──→ ContractContact (참조)
Customer ──1:N──→ ContractContact
Customer ──1:N──→ TransactionLine
Customer ──1:N──→ Receipt

Contract ──1:N──→ ContractPeriod ──1:N──→ MonthlyForecast
                                 ──1:N──→ ContractContact
Contract ──1:N──→ TransactionLine
Contract ──1:N──→ Receipt

Receipt ──1:N──→ ReceiptMatch ──N:1──→ TransactionLine(revenue)
```

---

## 구현 완료 기능

| 영역 | 주요 기능 |
| ---- | -------- |
| **사업 관리** | CRUD (소프트 삭제·복구), 내 사업 필터 + 요약 바, Period 관리 (계획/수시·실주), 담당자 매핑, 검수일/발행일 규칙 |
| **Forecast** | 월별 예상 매출/GP, Forecast→실적 동기화 (발행일·매출처 자동 계산) |
| **매출/매입 원장** | 실적 CRUD, 반복행·행복제, 일괄 삭제·확정, Ledger 뷰, 완료 기간 읽기전용 보호, 입금 배분 매출 삭제 방지 |
| **입금** | 입금 CRUD, 미수 매출 기반 기본값 자동설정 |
| **입금 배분** | FIFO 자동 배분 (귀속기간 격리), 수동 배분, 자동 재배분, 미수금/선수금 계산 |
| **거래처** | CRUD, 담당자 N명 (다역할), 탭 대시보드 (사업현황/담당자/매출·매입/입금), 담당자 피벗 뷰 |
| **인증/사용자** | 세션 기반 인증, admin/user 권한, 데이터 가시 범위, bootstrap 관리자, 로그인 잠금, CSV 일괄 등록 |
| **Excel** | 3단계 Import (검증→사업→Forecast→실적), 값 정규화, 4종 보고서 Excel Export |
| **대시보드** | KPI 요약, 사업유형별 매출, 추이 차트 (막대/선형/영역), 목표 vs 실적, 집계 단위 전환 |
| **보고서** | 요약 현황, Forecast vs Actual, 미수 현황, 매입매출관리 + Excel Export |
| **시스템** | 전역 예외 핸들러, 감사 로그 인프라, 컬럼/필터 상태 localStorage 저장, 사업유형·용어 설정 관리 |

---

## 현재 제한사항 / 알려진 이슈

> 상세 내용은 [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md) 참조.

- 감사 로그 서비스 연동 미완료, 조회 UI placeholder
- admin/user 2단계 권한만 구현 (manager/viewer 미구현)
- 동시 편집 충돌 방지(낙관적 잠금) 미구현
- 발행일 휴일 조정 미적용

---

## API 엔드포인트 요약

> 전체 엔드포인트 상세는 `app/routers/` 소스 코드 참조. 아래는 리소스별 요약.

| 라우터 | 프리픽스 | 주요 기능 | 권한 |
| ------ | ------- | -------- | ---- |
| auth | `/api/v1/auth` | 로그인, 로그아웃, 비밀번호 변경, 현재 사용자 | 공개/인증 |
| contracts | `/api/v1/contracts`, `/api/v1/contract-periods` | 사업/기간 CRUD, 원장 뷰, 내사업 요약, 담당자 일괄 변경 | 인증/admin(삭제·복구·일괄변경) |
| transaction_lines | `/api/v1/.../transaction-lines` | 매출/매입 실적 CRUD, 일괄 확정 | 인증/admin(삭제) |
| receipts | `/api/v1/.../receipts` | 입금 CRUD | 인증/admin(삭제) |
| receipt_matches | `/api/v1/.../receipt-matches` | 입금 배분 CRUD, FIFO 자동 재배분 | 인증 |
| forecasts | `/api/v1/.../forecasts` | Forecast 조회/upsert, Forecast→실적 동기화 | 인증 |
| customers | `/api/v1/customers` | 거래처 CRUD, 담당자, 사업현황, 매출·매입·입금 조회 | 인증/admin(삭제) |
| contract_contacts | `/api/v1/.../contacts` | 사업별/Period별 담당자, 거래처별 담당자 피벗 | 인증 |
| users | `/api/v1/users` | 사용자 CRUD, 비밀번호 초기화, CSV 임포트 | admin |
| excel | `/api/v1/excel` | 템플릿 다운로드, 검증, 3단계 Import | admin |
| dashboard | `/api/v1/dashboard` | 대시보드 요약, 목표 vs 실적 | 인증 |
| reports | `/api/v1/reports` | 요약/Forecast vs Actual/미수/매입매출관리 + Excel Export | 인증 |
| settings | `/api/v1/settings`, `/api/v1/preferences` | 시스템 설정, 사용자 설정 | 인증 |
| contract_types | `/api/v1/contract-types` | 사업유형 CRUD | 인증/admin(CUD) |
| term_configs | `/api/v1/term-configs` | 용어 설정 CRUD, 라벨 조회, 초기화 | 인증/admin(CUD) |

---

## 화면 구조

### 네비게이션

내 사업 / 사업 관리 / 거래처 관리 / 대시보드 / 보고서 / 로그(준비 중) / 설정

### 사업 상세 화면

```text
사업 기본정보 (수정 가능)
├── 검수일/발행일 규칙 설정
└── Period 탭 버튼 [ Y25 ] [ Y26 ] [ Y27 ]
    ├── Forecast 그리드 (월별 예상 매출/GP)
    ├── 매출/매입 원장 그리드 (TransactionLine, 필터, 행추가/삭제/복제/확정/저장)
    ├── 입금 내역 그리드 (Receipt, 행추가/삭제/저장)
    ├── 배분 현황 그리드 (ReceiptMatch, 자동/수동 배분 조회)
    └── GP 요약 (매출/매입/GP/GP%/입금/미수)
```
