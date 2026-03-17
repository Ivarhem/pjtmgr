# 모듈 재구성 계획: 공통모듈 + 회계모듈

## 1. 현재 구조 분석

현재 `app/` 하위에 모든 코드가 플랫하게 존재:
```
app/
├── models/          # 18개 모델 (혼재)
├── schemas/         # 15개 스키마 (혼재)
├── routers/         # 17개 라우터 (혼재)
├── services/        # 21개 서비스 (혼재)
├── auth/            # 인증 (이미 분리됨)
├── startup/         # 초기화
├── templates/       # HTML
├── static/          # JS/CSS/img
├── app_factory.py
├── config.py
├── database.py
└── exceptions.py
```

## 2. 모듈 분류

### 공통모듈 (`app/common/`) — 프로젝트, 거래처, 사용자, 시스템 설정

| 레이어 | 포함 대상 |
|--------|----------|
| **models** | User, UserPreference, LoginFailure, Customer, CustomerContact, CustomerContactRole, Contract, ContractPeriod, ContractContact, ContractTypeConfig, Setting, TermConfig, AuditLog |
| **schemas** | user, auth, customer, customer_contact, customer_contact_role, contract, contract_contact, contract_type_config, setting, term_config, _normalize |
| **routers** | users, customers, contracts, contract_contacts, contract_types, settings, term_configs, user_preferences, health, pages |
| **services** | user, customer, _customer_helpers, contract, contract_contact, _contract_helpers, contract_type_config, user_preference, setting, term_config, audit |

### 회계모듈 (`app/accounting/`) — 매출/매입, 입금, 배분, 예측, 보고

| 레이어 | 포함 대상 |
|--------|----------|
| **models** | TransactionLine, Receipt, ReceiptMatch, MonthlyForecast |
| **schemas** | transaction_line, receipt, receipt_match, monthly_forecast, report |
| **routers** | transaction_lines, receipts, receipt_matches, forecasts, dashboard, reports, excel |
| **services** | transaction_line, receipt, receipt_match, monthly_forecast, forecast_sync, ledger, metrics, dashboard, report, _report_export, importer, exporter |

### 앱 루트 (`app/`) — 공유 인프라 (변경 없음)

| 파일 | 역할 |
|------|------|
| `app_factory.py` | 앱 생성, 모듈 라우터 통합 등록 |
| `config.py` | 환경변수/설정 |
| `database.py` | DB 엔진/세션 |
| `exceptions.py` | 커스텀 예외 |
| `auth/` | 인증/인가 (이미 분리, 위치 유지) |
| `startup/` | 초기화 |
| `templates/` | HTML (1차에서는 이동하지 않음) |
| `static/` | JS/CSS (1차에서는 이동하지 않음) |

## 3. 목표 디렉토리 구조

```
app/
├── main.py
├── app_factory.py          # 모듈별 라우터 등록 통합
├── config.py
├── database.py
├── exceptions.py
│
├── auth/                   # 그대로 유지
│   └── ...
│
├── startup/                # 그대로 유지
│   └── ...
│
├── common/                 # ← 공통모듈
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py     # 모든 공통 모델 re-export
│   │   ├── base.py         # TimestampMixin, Base
│   │   ├── user.py
│   │   ├── user_preference.py
│   │   ├── login_failure.py
│   │   ├── customer.py
│   │   ├── customer_contact.py
│   │   ├── customer_contact_role.py
│   │   ├── contract.py
│   │   ├── contract_period.py
│   │   ├── contract_contact.py
│   │   ├── contract_type_config.py
│   │   ├── setting.py
│   │   ├── term_config.py
│   │   └── audit_log.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── _normalize.py
│   │   ├── user.py
│   │   ├── auth.py
│   │   ├── customer.py
│   │   ├── customer_contact.py
│   │   ├── customer_contact_role.py
│   │   ├── contract.py
│   │   ├── contract_contact.py
│   │   ├── contract_type_config.py
│   │   ├── setting.py
│   │   └── term_config.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── users.py
│   │   ├── customers.py
│   │   ├── contracts.py
│   │   ├── contract_contacts.py
│   │   ├── contract_types.py
│   │   ├── settings.py
│   │   ├── term_configs.py
│   │   ├── user_preferences.py
│   │   ├── health.py
│   │   └── pages.py
│   └── services/
│       ├── __init__.py
│       ├── user.py
│       ├── customer.py
│       ├── _customer_helpers.py
│       ├── contract.py
│       ├── contract_contact.py
│       ├── _contract_helpers.py
│       ├── contract_type_config.py
│       ├── user_preference.py
│       ├── setting.py
│       ├── term_config.py
│       └── audit.py
│
├── accounting/             # ← 회계모듈
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py     # 모든 회계 모델 re-export
│   │   ├── transaction_line.py
│   │   ├── receipt.py
│   │   ├── receipt_match.py
│   │   └── monthly_forecast.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── transaction_line.py
│   │   ├── receipt.py
│   │   ├── receipt_match.py
│   │   ├── monthly_forecast.py
│   │   └── report.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── transaction_lines.py
│   │   ├── receipts.py
│   │   ├── receipt_matches.py
│   │   ├── forecasts.py
│   │   ├── dashboard.py
│   │   ├── reports.py
│   │   └── excel.py
│   └── services/
│       ├── __init__.py
│       ├── transaction_line.py
│       ├── receipt.py
│       ├── receipt_match.py
│       ├── monthly_forecast.py
│       ├── forecast_sync.py
│       ├── ledger.py
│       ├── metrics.py
│       ├── dashboard.py
│       ├── report.py
│       ├── _report_export.py
│       ├── importer.py
│       └── exporter.py
│
├── models/                 # ← 호환 re-export (기존 import 경로 유지용)
│   └── __init__.py         # from app.common.models import * ; from app.accounting.models import *
├── schemas/                # ← 호환 re-export
│   └── __init__.py
├── services/               # ← 호환 re-export
│   └── __init__.py
├── routers/                # ← 호환 re-export
│   └── __init__.py
│
├── templates/              # 그대로 유지 (1차)
└── static/                 # 그대로 유지 (1차)
```

## 4. 모듈 간 의존성 규칙

```
accounting → common   ✅ (회계모듈은 공통모듈 참조 가능)
common → accounting   ❌ (공통모듈은 회계모듈을 참조하면 안 됨)
common → app/         ✅ (config, database, exceptions, auth)
accounting → app/     ✅ (config, database, exceptions, auth)
```

### 교차 의존성 해결이 필요한 현재 지점

| 공통모듈 파일 | 회계모듈 참조 | 해결 방법 |
|--------------|-------------|----------|
| `services/customer.py` | TransactionLine, Receipt, ReceiptMatch import | 회계 관련 조회 로직을 `_customer_helpers.py`로 분리 → 이 헬퍼를 accounting 쪽으로 이동하거나, 회계모듈이 제공하는 인터페이스 함수를 호출 |
| `services/_customer_helpers.py` | Receipt, ReceiptMatch, TransactionLine import | 이 파일 자체를 `accounting/services/` 쪽으로 이동 (고객 재무 정보 조회는 회계 도메인) |
| `services/contract_contact.py` | `_related_contract_ids` (from customer service) | 공통모듈 내부 의존이므로 문제 없음 |
| `models/customer.py` | relationship → TransactionLine, Receipt, ContractContact | relationship은 문자열 참조로 유지 가능 (lazy import) |

### 해결 전략

1. **`_customer_helpers.py`를 `accounting/services/`로 이동**: 거래처의 재무 데이터(매출/매입/입금/미수금) 조회는 회계 도메인의 책임
2. **`customer.py` 서비스에서 회계 관련 함수 분리**: `customer.py`는 공통모듈에 남되, 재무 조회 함수는 `accounting/services/customer_finance.py`로 추출
3. **ORM relationship**: 문자열 기반 `relationship("TransactionLine", ...)`으로 선언하면 import 없이 모듈 간 참조 가능. 단, 모든 모델이 같은 `Base`를 공유해야 함 → `base.py`는 `app/common/models/base.py`에 두고 양쪽에서 import

## 5. 실행 단계

### Phase 1: 디렉토리 생성 + 파일 이동 (물리적 재배치)
1. `app/common/`, `app/accounting/` 디렉토리 트리 생성
2. 각 파일을 새 위치로 이동 (git mv)
3. 기존 `app/models/`, `app/schemas/`, `app/services/`, `app/routers/`에 호환 re-export `__init__.py` 작성

### Phase 2: import 경로 갱신
1. 모듈 내부 import를 새 경로로 전환 (`app.models.contract` → `app.common.models.contract`)
2. 교차 의존성 파일 리팩터링 (customer ↔ 회계 분리)
3. `app_factory.py` 수정 (모듈별 라우터 등록)
4. `app/models/__init__.py` 호환 레이어 (Alembic + 테스트 기존 import 유지)

### Phase 3: 검증
1. 전체 테스트 실행 (`pytest`)
2. Alembic migration이 모델을 정상 감지하는지 확인
3. 앱 기동 확인

### Phase 4: 정리
1. 호환 re-export 레이어에서 deprecation 주석 추가 (향후 제거 예정)
2. 문서 갱신 (CLAUDE.md, PROJECT_STRUCTURE.md, DECISIONS.md)

## 6. 향후 인프라 모듈 추가 시

```
app/infra/                  # ← 미래 인프라 모듈
├── models/                 # 물품, 구성현황 모델
├── schemas/
├── routers/
└── services/
```

의존성: `infra → common ✅`, `infra → accounting ❌` (필요 시 재검토)

## 7. 주의사항

- **Alembic**: `alembic/env.py`의 `target_metadata`가 모든 모델을 인식하도록 `app.common.models`와 `app.accounting.models` 모두 import 필요
- **Base 공유**: `Base = declarative_base()`는 `app.common.models.base`에 단일 정의, 회계모듈도 동일 Base 사용
- **templates/static**: 1차에서는 이동하지 않음. 향후 모듈별 프론트엔드 분리 시 검토
- **호환 레이어**: 기존 `from app.models.contract import Contract` 경로가 깨지지 않도록 re-export. 테스트/Alembic/외부 스크립트 호환 보장
- **`_customer_helpers.py` 이동**: 공통 → 회계 방향 의존을 제거하는 핵심 리팩터링. customer 서비스의 `get_customer_financial_summary()` 등 재무 조회 함수를 `accounting/services/customer_finance.py`로 이동하고, 라우터에서 직접 호출하도록 변경
