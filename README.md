# 영업부서 매입매출 관리 앱

영업부서의 사업(Contract)을 원장으로 관리하고, 사업별 매입/매출 내역을 월별로 입력·조회하며
필요한 형태의 Excel 파일로 Export하는 사내 전용 웹 애플리케이션.

> **현재 상태**: 파일럿 테스트 진행 (v0.3)

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
pip install -r requirements.txt

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
│   ├── config.py             # 환경 설정
│   ├── database.py           # DB 연결
│   ├── exceptions.py         # 커스텀 예외 (NotFoundError 등)
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
│   │   └── term_config.py    # TermConfig (용어 설정)
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
│   │   ├── contract.py       # 사업/기간/Forecast/TransactionLine/Receipt 서비스
│   │   ├── customer.py       # 거래처 서비스
│   │   ├── user.py           # 사용자 서비스
│   │   ├── contract_contact.py # 사업별 담당자 서비스
│   │   ├── dashboard.py      # 대시보드 데이터 집계
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
│   │   ├── contracts.py      # 사업/기간/Forecast/TransactionLine/Receipt/Ledger
│   │   ├── customers.py      # 거래처/거래처 담당자
│   │   ├── users.py          # 사용자 관리
│   │   ├── contract_contacts.py # 사업별 담당자
│   │   ├── excel.py          # Excel Import/Export
│   │   ├── dashboard.py      # 대시보드 API
│   │   ├── reports.py        # 보고서 API
│   │   ├── settings.py       # 앱 설정
│   │   ├── user_preferences.py # 사용자 설정
│   │   ├── contract_types.py # 사업유형 관리
│   │   └── term_configs.py   # 용어 설정
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
│   └── test_importer.py      # Excel Import 검증 테스트
├── requirements.txt          # Python 의존성
├── CLAUDE.md                 # 개발 지침/규칙
├── PILOT_TEST.md             # 파일럿 테스트 계획
└── README.md                 # 프로젝트 설명 (이 파일)
```

---

## 데이터 모델

### 테이블 구조

```text
users (사용자/담당자)
  id, login_id, name, department
  role (user/admin), is_active, hashed_password, must_change_password
  created_at, updated_at

customers (거래처 - 매출처/매입처 공용)
  id, name, business_no, notes
  created_at, updated_at

customer_contacts (거래처 담당자 - N명, 인물 중심)
  id, customer_id → customers
  name, phone, email
  created_at, updated_at

customer_contact_roles (담당자 역할 - 1인 다역할 가능)
  id, customer_contact_id → customer_contacts (CASCADE)
  role_type (영업/세금계산서/업무), is_default
  UNIQUE(customer_contact_id, role_type)
  created_at, updated_at

contract_type_configs (사업유형 설정)
  code (PK), label, sort_order, is_active
  default_gp_pct, default_inspection_day
  default_invoice_month_offset, default_invoice_day_type
  default_invoice_day, default_invoice_holiday_adjust

contracts (사업)
  id, contract_code, contract_name, contract_type → contract_type_configs.code
  end_customer_id → customers (END 고객)
  owner_user_id → users (영업 담당)
  status (active/closed/cancelled)
  inspection_day, inspection_date          # 검수일 규칙
  invoice_month_offset, invoice_day_type   # 발행일 규칙
  invoice_day, invoice_holiday_adjust      # 발행일 세부
  notes
  created_at, updated_at

contract_periods (사업 기간 - 연도 단위 버전)
  id, contract_id → contracts
  period_year, period_label (Y25, Y26)
  stage (10%/50%/70%/90%/계약완료)
  expected_revenue_total, expected_gp_total
  start_month, end_month (YYYY-MM-01)
  owner_user_id → users (Period별 담당 영업)
  customer_id → customers (매출처, 미지정 시 Contract.end_customer)
  inspection_day, inspection_date              # 검수일 규칙
  invoice_month_offset, invoice_day_type       # 발행일 규칙
  invoice_day, invoice_holiday_adjust          # 발행일 세부
  notes
  UNIQUE(contract_id, period_year)
  created_at, updated_at

contract_contacts (사업별 담당자 - ContractPeriod·거래처 단위)
  id, contract_period_id → contract_periods
  customer_id → customers
  customer_contact_id → customer_contacts (기본 담당자 참조)
  contact_type (영업/세금계산서/업무)
  rank (정/부), notes
  created_at, updated_at

monthly_forecasts (월별 Forecast - contract_period 단위)
  id, contract_period_id → contract_periods
  forecast_month (YYYY-MM-01)
  revenue_amount, gp_amount
  version_no, is_current, created_by → users
  UNIQUE(contract_period_id, forecast_month, version_no)
  created_at, updated_at

transaction_lines (월별 실적 - contract 단위)
  id, contract_id → contracts
  revenue_month (YYYY-MM-01), line_type (revenue/cost)
  customer_id → customers (매출처/매입처)
  supply_amount, invoice_issue_date, status (예정/확정)
  description, created_by → users
  created_at, updated_at

receipts (입금 - contract 단위)
  id, contract_id → contracts
  customer_id → customers
  receipt_date (YYYY-MM-DD), revenue_month (YYYY-MM-01)
  amount, description, created_by → users
  created_at, updated_at

receipt_matches (입금 배분 - Receipt↔매출 라인 매핑)
  id, receipt_id → receipts, transaction_line_id → transaction_lines
  matched_amount (원)
  match_type (auto/manual)
  created_by → users
  UNIQUE(receipt_id, transaction_line_id)
  created_at, updated_at

term_configs (용어 설정)
  term_key (PK), default_label, custom_label
  category, sort_order
  created_at, updated_at

user_preferences (사용자별 설정)
  id, user_id → users, pref_key, pref_value
  UNIQUE(user_id, pref_key)

settings (앱 설정 - key-value)
  key (PK), value

audit_logs (감사 로그)
  id, user_id → users
  action (create/update/delete)
  entity_type (contract/transaction_line/receipt/...), entity_id
  summary, detail (JSON)
  created_at
```

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

### 사업 관리

- 사업 CRUD (목록/등록/수정/삭제) — 삭제 시 소프트 삭제(status→cancelled), 관리자 복구 가능
- 사업 등록 시 END 고객 입력 지원
- 내 사업 (로그인 사용자 기준 자동 필터) + **요약 바** (진행 사업/매출/GP/미수금)
- 사업 기간(ContractPeriod) 관리 — Period 탭 버튼 UI
- ContractPeriod별 매출처 관리 (미지정 시 Contract의 END 고객 사용)
- 사업별 담당자 매핑 (ContractContact) — **사업 상세에서 담당자 정보 표시**
- 검수일/발행일 규칙 설정 (Contract 기본정보, Period 상속)

### Forecast

- 월별 예상 매출/GP 입력/조회
- Forecast → TransactionLine 동기화 (Forecast 가져오기)
- 동기화 시 발행일 자동 계산 (Period 발행일 규칙 기반) + Period 매출처 자동 입력 (미지정 시 END 고객)

### 매출/매입 원장 (Actual)

- 매출/매입 실적 입력/조회
- 반복행 생성
- 행 복제 (월 단위)
- 체크박스 선택 후 일괄 삭제 (관리자 전용)
- 체크박스 선택 후 일괄 확정 (체크박스 우선, 미선택 시 발행일 기준 자동 탐색)
- 구분(매출/매입)/거래처/귀속월/발행상태 필터 + 미래 숨김 필터
- 저장 시 필수 필드 검증 (구분/거래처/금액) + 매출 거래처 미입력 시 END 고객 자동 입력 제안
- TransactionLine+Receipt 단일 원장 그리드 (Ledger 뷰)
- 입금 상태 컬럼 (완료/미수 배지 표시)
- 매입 행 추가 시 기본값 자동설정 (구분=매입, 귀속월=빈 월, 금액=Forecast 매출-GP)
- 반복행 생성 시 Forecast 매입 기준 옵션 (매출-GP 자동 계산)
- 완료된 귀속기간 읽기 전용 보호 (프론트+백엔드)
- 입금 배분된 매출 행 삭제 방지

### 입금 (Receipt)

- 입금 내역 입력/조회 (등록 시 END 고객 거래처 기본값 자동 입력)
- 입금 추가 시 가장 오래된 미수 매출 기반 기본값 (미저장 행 반영)
- 체크박스 선택 후 일괄 삭제 (관리자 전용)
- 거래처/귀속월 필터

### 입금 배분 (ReceiptMatch)

- FIFO 자동 배분 (귀속기간 내 매출만 대상, 귀속월 오름차순)
- 수동 배분 생성/수정/삭제
- 배분 현황 그리드 (사업 상세 화면, 귀속기간 필터 적용)
- 자동 재배분 기능
- 미수금 = 매출확정 - 배분완료 (단일 공식)
- 선수금 표시 (입금 > 매출확정 시 AR 음수 → "선수금" 라벨)

### 거래처

- 거래처 CRUD
- 거래처 기본 담당자 N명 관리 (1인 다역할: 영업/세금계산서/업무 체크박스)
- 역할별 기본 담당자 지정 (is_default)
- 사업별 담당자: 기본 담당자에서 선택하여 배정 (정/부 구분)
- 탭 기반 대시보드 (사업현황/담당자/매출·매입/입금)
- 거래처별 사업 현황 조회 (역할 배지, 요약 카드, 진행중 필터)
- 거래처별 매출·매입 월별 집계 및 미수금 조회
- 거래처별 입금 내역 조회
- 사업별 담당자 매트릭스 (피벗 뷰, 폴백 표시, 정 담당자 기준)
- 거래처 목록 서브텍스트 (진행중 건수, 매출 금액)

### 사용자/인증

- 세션 기반 인증 (쿠키)
- 역할 기반 권한 관리 (admin/user)
- 데이터 가시 범위 (admin: 전체, user: 본인 담당)
- 활성 관리자 부재 시 초기 관리자 bootstrap 지원
- 사용자 CRUD (관리자 전용)
- 비밀번호 변경/초기화
- CSV 사용자 일괄 등록

### Excel Import/Export

- 3단계 Import: 사업 → Forecast → TransactionLine
- 값 정규화 (진행단계 소수→%, 사업유형 대소문자)
- 유효성 검사 및 오류 행 표시
- 보고서 Excel Export (요약 현황, Forecast vs Actual, 미수 현황, 매입매출관리)

### 보고서/대시보드

- 대시보드: KPI 요약, 사업유형별 매출, 월별 매출 추이, 미수금 현황
- 요약 현황: 월별 Forecast/Actual 매출·매입·GP·입금·미수금 집계
- Forecast vs Actual: 사업별 비교
- 미수 현황: 사업별 미수금 조회
- 매입매출관리: 개별 사업 월별 상세

### 시스템

- 커스텀 예외 + 전역 핸들러 (통일된 에러 응답)
- 런타임 마이그레이션 식별자 검증 (`app/main.py`) — legacy 테이블/컬럼 이관 시 화이트리스트 기반 raw SQL 제한
- 감사 로그 인프라 (테이블/유틸 준비, 연동 예정) + 로그 메뉴/placeholder 화면
- 컬럼 순서·너비 저장/복원 (localStorage) — 사업관리, 내사업, 사업상세, 보고서, 사용자관리
- 필터 상태 저장/복원 (localStorage) — 사업관리, 내사업, 보고서
- 사용자별 설정 저장
- 사업유형 관리 (ContractTypeConfig) — 관리자가 사업유형 추가/수정/삭제, 유형별 기본값 설정
- 용어 설정 (TermConfig) — 관리자가 UI 표시 용어 커스터마이징

---

## 현재 제한사항

- **감사 로그**: 테이블/유틸 준비 완료, 서비스 연동 미완료
- **감사 로그 조회**: `/audit-logs` 화면은 준비 중 placeholder이며, 실제 로그 목록/API는 미구현
- **DB**: 기본값은 SQLite 단일 파일 (`DATABASE_URL`로 변경 가능)
- **초기 관리자 생성**: bootstrap 환경변수를 설정하지 않으면 첫 관리자 계정을 만들 수 없음
- **테스트**: 집계/Contract 서비스/Excel 검증과 완료기간/FIFO 핵심 회귀는 작성됨 — API 통합, 권한, 보고서 회귀 테스트는 추가 필요
- **발행일 휴일 조정**: 공휴일 달력 미적용 (invoice_holiday_adjust 필드 존재)
- **권한**: admin/user 2단계만 구현 (manager/viewer 미구현)

---

## 향후 개발 예정

| 우선순위 | 기능 | 설명 |
| --- | --- | --- |
| 높음 | 복사/붙여넣기 개선 | AG Grid 행 복사·붙여넣기, 다중 행 선택 복사 |
| 중간 | 알림 기능 | 세금계산서 발행 임박, 미수금 지연, Forecast vs Actual 괴리, 계약 갱신 필요 |
| 중간 | 감사 로그 연동 | 주요 CRUD에 audit.log() 호출 + 조회 UI |
| 중간 | 권한 확장 | manager/viewer 역할, 부서 단위 접근 범위 |
| 중간 | 전역 검색 | 사업명·거래처명·코드 통합 검색 |
| 낮음 | 낙관적 잠금 | 동시 편집 충돌 방지 (version 필드 기반) |
| 낮음 | DB 마이그레이션 | Alembic 도입, SQLite → PostgreSQL |
| 낮음 | 발행일 휴일 조정 | 공휴일 달력 연동 (전/후 영업일 계산) |
| 낮음 | 테스트 확장 | API 통합, 권한, ReceiptMatch, 보고서 회귀 테스트 추가 |
| 낮음 | 국세청 API 연동 | 세금계산서 발행·조회 자동화 |
| 낮음 | Undo/History | 변경 이력 추적 및 되돌리기 |

---

## API 엔드포인트 요약

| 메서드 | 경로 | 설명 | 권한 |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/login` | 로그인 | 공개 |
| POST | `/api/v1/auth/logout` | 로그아웃 | 인증 |
| GET | `/api/v1/auth/me` | 현재 사용자 + permissions | 인증 |
| POST | `/api/v1/auth/change-password` | 비밀번호 변경 | 인증 |
| GET | `/api/v1/contract-periods` | 원장 목록 (필터 + scope) | 인증 |
| GET/POST | `/api/v1/contracts` | 사업 목록/생성 | 인증 |
| GET/PATCH | `/api/v1/contracts/{id}` | 사업 조회/수정 | 인증 |
| DELETE | `/api/v1/contracts/{id}` | 사업 삭제 (소프트 삭제) | admin |
| POST | `/api/v1/contracts/{id}/restore` | 삭제된 사업 복구 | admin |
| GET/POST | `/api/v1/contracts/{id}/periods` | 기간 목록/생성 | 인증 |
| GET/PATCH/DELETE | `/api/v1/contract-periods/{id}` | 기간 단건 CRUD | 인증 |
| GET/PATCH | `/api/v1/contract-periods/{id}/forecasts` | Forecast 조회/upsert | 인증 |
| GET | `/api/v1/contracts/{id}/all-forecasts` | 전체 기간 Forecast | 인증 |
| GET/POST | `/api/v1/contracts/{id}/transaction-lines` | 실적 조회/생성 | 인증 |
| PATCH | `/api/v1/transaction-lines/{id}` | 실적 수정 | 인증 |
| DELETE | `/api/v1/transaction-lines/{id}` | 실적 삭제 | admin |
| GET/POST | `/api/v1/contracts/{id}/receipts` | 입금 조회/생성 | 인증 |
| PATCH | `/api/v1/receipts/{id}` | 입금 수정 | 인증 |
| DELETE | `/api/v1/receipts/{id}` | 입금 삭제 | admin |
| GET/POST | `/api/v1/contracts/{id}/receipt-matches` | 배분 목록/수동 생성 | 인증 |
| PATCH | `/api/v1/receipt-matches/{id}` | 배분 수정 | 인증 |
| DELETE | `/api/v1/receipt-matches/{id}` | 배분 삭제 | 인증 |
| POST | `/api/v1/contracts/{id}/receipt-matches/auto` | FIFO 자동 재배분 | 인증 |
| GET | `/api/v1/contracts/{id}/forecast-sync-preview` | Forecast→TransactionLine 미리보기 | 인증 |
| POST | `/api/v1/contracts/{id}/forecast-sync` | Forecast→TransactionLine 동기화 | 인증 |
| GET | `/api/v1/contracts/{id}/ledger` | TransactionLine+Receipt 병합 뷰 | 인증 |
| GET/POST | `/api/v1/customers` | 거래처 목록/생성 | 인증 |
| PATCH/DELETE | `/api/v1/customers/{id}` | 거래처 수정/삭제 | 인증/admin(삭제) |
| GET/POST | `/api/v1/customers/{id}/contacts` | 거래처 담당자 목록/생성 | 인증 |
| PATCH/DELETE | `/api/v1/customers/contacts/{id}` | 거래처 담당자 수정/삭제 | 인증 |
| GET/POST | `/api/v1/contracts/{id}/contacts` | 사업별 담당자 목록/생성 | 인증 |
| GET/POST | `/api/v1/contract-periods/{id}/contacts` | Period별 담당자 목록/생성 | 인증 |
| PATCH | `/api/v1/contract-contacts/{id}` | 사업별 담당자 수정 | 인증 |
| DELETE | `/api/v1/contract-contacts/{id}` | 사업별 담당자 삭제 | 인증 |
| GET | `/api/v1/customers/{id}/contract-contacts` | 거래처별 사업 담당자 목록 | 인증 |
| GET | `/api/v1/customers/{id}/contract-contacts-pivoted` | 거래처별 사업 담당자 (피벗) | 인증 |
| GET/POST | `/api/v1/users` | 사용자 목록/생성 | admin |
| PATCH/DELETE | `/api/v1/users/{id}` | 사용자 수정/삭제 | admin |
| POST | `/api/v1/users/{id}/reset-password` | 비밀번호 초기화 | admin |
| POST | `/api/v1/users/import-csv` | 아웃룩 연락처 CSV 임포트 | admin |
| GET/PATCH | `/api/v1/settings` | 앱 설정 조회/수정 | 인증 |
| GET/PATCH | `/api/v1/preferences/{key}` | 사용자 설정 조회/수정 | 인증 |
| GET | `/api/v1/excel/template` | 통합 Import 템플릿 다운로드 | admin |
| GET | `/api/v1/excel/template/contracts` | 영업기회 템플릿 다운로드 | admin |
| GET | `/api/v1/excel/template/forecast` | 월별계획 템플릿 다운로드 | admin |
| GET | `/api/v1/excel/template/transaction-lines` | 실적 템플릿 다운로드 | admin |
| POST | `/api/v1/excel/validate` | 파일 유효성 검사 (미리보기) | admin |
| POST | `/api/v1/excel/import` | Excel Import (사업) | admin |
| POST | `/api/v1/excel/import/forecast` | Excel Import (Forecast) | admin |
| POST | `/api/v1/excel/import/transaction-lines` | Excel Import (TransactionLine) | admin |
| POST | `/api/v1/contracts/bulk-assign-owner` | 담당자 일괄 변경 | 인증 |
| POST | `/api/v1/contracts/{id}/transaction-lines/bulk-confirm` | 실적 일괄 확정 | 인증 |
| GET | `/api/v1/customers/{id}/contracts` | 거래처 관련 사업 조회 | 인증 |
| GET | `/api/v1/customers/{id}/financials` | 거래처 매출·매입 월별 집계 | 인증 |
| GET | `/api/v1/customers/{id}/receipts` | 거래처 입금 내역 | 인증 |
| GET | `/api/v1/dashboard/summary` | 대시보드 전체 데이터 | 인증 |
| GET | `/api/v1/reports/summary` | 요약 현황 | 인증 |
| GET | `/api/v1/reports/summary/export` | 요약 현황 Excel | 인증 |
| GET | `/api/v1/reports/forecast-vs-actual` | Forecast vs Actual | 인증 |
| GET | `/api/v1/reports/forecast-vs-actual/export` | Forecast vs Actual Excel | 인증 |
| GET | `/api/v1/reports/receivables` | 미수 현황 | 인증 |
| GET | `/api/v1/reports/receivables/export` | 미수 현황 Excel | 인증 |
| GET | `/api/v1/reports/contract-pnl/{contract_id}` | 매입매출관리 | 인증 |
| GET | `/api/v1/reports/contract-pnl/{contract_id}/export` | 매입매출관리 Excel | 인증 |
| GET | `/api/v1/contract-types` | 사업유형 목록 | 인증 |
| POST | `/api/v1/contract-types` | 사업유형 생성 | admin |
| PATCH | `/api/v1/contract-types/{code}` | 사업유형 수정 | admin |
| DELETE | `/api/v1/contract-types/{code}` | 사업유형 삭제 | admin |
| GET | `/api/v1/my-contracts/summary` | 내 사업 요약 통계 | 인증 |
| GET | `/api/v1/term-configs` | 용어 설정 목록 | 인증 |
| POST | `/api/v1/term-configs` | 용어 설정 생성 | admin |
| GET | `/api/v1/term-configs/labels` | 용어 라벨 조회 | 인증 |
| GET | `/api/v1/term-configs/{term_key}` | 용어 설정 단건 조회 | 인증 |
| PATCH | `/api/v1/term-configs/{term_key}` | 용어 설정 수정 | admin |
| DELETE | `/api/v1/term-configs/{term_key}` | 용어 설정 삭제 | admin |
| POST | `/api/v1/term-configs/{term_key}/reset` | 용어 설정 초기화 | admin |

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
