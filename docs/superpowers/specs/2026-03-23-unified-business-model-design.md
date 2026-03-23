# 사업/계약단위 통합 모델 설계

> **Status:** Reviewed
> **Date:** 2026-03-23
> **Scope:** contracts/contract_periods를 common 모듈로 이동하여 영업·인프라 공통 기본정보로 통합하고, infra의 projects 테이블을 제거한다.

---

## 1. 배경 및 목적

### 현재 문제

- `contracts`(영업)와 `projects`(인프라)가 **별도 테이블**로 존재하며, `project_contract_links` N:N 테이블로 연결.
- 하나의 사업("티머니 보안시스템 유지보수")이 양쪽에 각각 등록되어야 하고, 이름/기간/고객사 등 기본정보가 중복된다.
- 인프라에서 사업을 등록하면 영업에서 안 보이고, 그 반대도 마찬가지.
- 모듈 간 import 규칙(`accounting ↔ infra 절대 금지`)으로 인해 직접 참조 불가.

### 목표

- **사업(Contract)**과 **계약단위(ContractPeriod)**를 common 모듈의 공통 기본정보로 승격한다.
- infra의 `projects` 테이블을 제거하고, `contract_periods`를 인프라 작업 단위로 사용한다.
- 영업/인프라 어디서든 사업을 등록할 수 있되, 공통 필드만 필수로 한다.
- `project_contract_links` 테이블을 삭제한다.

---

## 2. 데이터 모델 변경

### 2.1 테이블 이동 및 분리

#### contracts → common (공통 기본정보만 유지)

| 필드 | 타입 | 구분 | 비고 |
|------|------|------|------|
| `id` | int PK | 공통 | |
| `contract_code` | str(50) unique | 공통 | 자동생성 사업코드 |
| `contract_name` | str(300) NOT NULL | 공통 | 사업명 |
| `contract_type` | str(30) NOT NULL | 공통 | MA/SI/HW/ETC |
| `end_customer_id` | FK→customers.id | 공통 | 고객사 |
| `status` | str(30) default='active' | 공통 | active/closed/cancelled |
| `notes` | str(500) nullable | 공통 | |
| `owner_user_id` | FK→users.id nullable | 공통 | 담당자 |
| `created_at`, `updated_at` | datetime | 공통 | TimestampMixin |

#### contract_periods → common (공통 기본정보만 유지)

| 필드 | 타입 | 구분 | 비고 |
|------|------|------|------|
| `id` | int PK | 공통 | |
| `contract_id` | FK→contracts.id NOT NULL | 공통 | |
| `period_year` | int NOT NULL | 공통 | 2025, 2026 |
| `period_label` | str(20) NOT NULL | 공통 | Y25, Y26 |
| `start_month` | str(10) nullable | 공통 | YYYY-MM-01 |
| `end_month` | str(10) nullable | 공통 | YYYY-MM-01 |
| `description` | Text nullable | 공통 | 기간별 설명 (기존 Project.description 수용) |
| `stage` | str(50) NOT NULL | 공통 | 진행 단계 |
| `owner_user_id` | FK→users.id nullable | 공통 | 기간별 담당자 |
| `customer_id` | FK→customers.id nullable | 공통 | 매출처 (미지정 시 사업 고객사) |
| `is_completed` | bool default=False | 공통 | |
| `is_planned` | bool default=True | 공통 | |
| `notes` | str(500) nullable | 공통 | |
| `created_at`, `updated_at` | datetime | 공통 | TimestampMixin |

#### contract_type_configs → common (함께 이동)

`ContractTypeConfig`는 `contract_type` 값을 검증하는 설정 테이블. Contract가 common으로 이동하므로 함께 이동해야 import 규칙을 위반하지 않는다.

| 필드 | 타입 | 비고 |
|------|------|------|
| 기존 필드 전체 | — | 변경 없음, 모듈만 이동 |

#### 영업 확장 테이블 (신규: `contract_sales_details`)

contract_periods의 영업 전용 필드를 분리한다. **1:1 관계** (contract_period_id UNIQUE FK).

| 필드 | 타입 | 비고 |
|------|------|------|
| `id` | int PK | |
| `contract_period_id` | FK→contract_periods.id UNIQUE NOT NULL | |
| `expected_revenue_amount` | int default=0 | 예상 매출 (기존 `_total` → `_amount` 정규화) |
| `expected_gp_amount` | int default=0 | 예상 GP (기존 `_total` → `_amount` 정규화) |
| `inspection_day` | int nullable | MA: 검수일 (월 N일, 0=말일) |
| `inspection_date` | date nullable | 비MA: 특정 검수일 |
| `invoice_month_offset` | int nullable | 계산서 기준월 (0=당월, 1=익월) |
| `invoice_day_type` | str(20) nullable | 계산서 발행일 유형 |
| `invoice_day` | int nullable | 특정일 |
| `invoice_holiday_adjust` | str(10) nullable | 휴일 조정 |

> - 현재 Contract 레벨에도 검수/계산서 규칙이 있으나, 실제 사용은 ContractPeriod 레벨이 우선. 통합 시 Contract 레벨 검수/계산서 필드는 **제거**하고, ContractPeriod(→ contract_sales_details) 레벨만 유지한다.
> - `expected_revenue_total` / `expected_gp_total` → `_amount` 접미사로 정규화 (backend.md 명명규칙 준수).
> - 영업 모듈에서 계약단위를 처음 열 때 `contract_sales_details` 행이 없으면 기본값으로 **자동 생성** (lazy-create).

### 2.2 삭제 대상

| 테이블/파일 | 사유 |
|------------|------|
| `projects` 테이블 | contract_periods로 대체 |
| `project_contract_links` 테이블 | 불필요 (직접 FK 전환) |
| `common/models/project_contract_link.py` | 테이블 삭제에 따른 모델 삭제 |
| `common/services/project_contract_link.py` | 서비스 삭제 |
| `common/schemas/project_contract_link.py` | 스키마 삭제 |
| `common/routers/project_contract_links.py` | 라우터 삭제 + `__init__.py`에서 등록 제거 |
| `infra/models/project.py` | 모델 삭제 |
| `infra/services/project_service.py` | 서비스 삭제 |
| `infra/schemas/project.py` | 스키마 삭제 |
| `infra/routers/projects.py` (해당 시) | 라우터 삭제 |

### 2.3 FK 변경 (infra 모듈)

| 모델 | 현재 FK | 변경 후 FK |
|------|---------|-----------|
| `ProjectPhase` | project_id → projects.id | contract_period_id → contract_periods.id |
| `ProjectDeliverable` | phase_id → project_phases.id | 변경 없음 (phase 경유) |
| `ProjectAsset` | project_id → projects.id | contract_period_id → contract_periods.id |
| `ProjectCustomer` | project_id → projects.id | contract_period_id → contract_periods.id |
| `ProjectCustomerContact` | project_customer_id → project_customers.id | 변경 없음 (customer 경유) |

### 2.4 테이블 리네이밍

`project_phases` 등의 이름이 더 이상 "project"를 반영하지 않으므로:

| 현재 | 변경 후 | 비고 |
|------|--------|------|
| `project_phases` | `period_phases` | 계약단위의 단계 |
| `project_deliverables` | `period_deliverables` | 계약단위의 산출물 |
| `project_assets` | `period_assets` | 계약단위의 자산 참조 |
| `project_customers` | `period_customers` | 계약단위의 업체 |
| `project_customer_contacts` | `period_customer_contacts` | 계약단위의 담당자 |

### 2.5 기존 관계 유지 확인

다음 back_populates 관계가 이미 존재하며, Contract를 common으로 이동해도 변경 불필요:

| 모델 | 관계 | 비고 |
|------|------|------|
| `User.contracts` | `relationship(back_populates="owner")` | Contract 이동 후에도 동작 |
| `Customer.contracts` | `relationship(back_populates="end_customer")` | 동일 |

### 2.6 ContractContact 처리

`ContractContact` (accounting)는 계약단위별 영업 담당자(매출/검수/계산서 담당). 인프라의 `ProjectCustomerContact`는 계약단위별 프로젝트 담당자(고객PM/구축엔지니어 등). **역할이 다르므로 통합하지 않는다.**

- `ContractContact`는 accounting에 잔류. FK(`contract_period_id`)는 common의 ContractPeriod를 참조하므로 import 규칙 위반 없음.

---

## 3. 모듈 구조 변경

### 3.1 모델 소유권

```
app/modules/common/models/
  ├── contract.py              ← accounting에서 이동
  ├── contract_period.py       ← accounting에서 이동
  ├── contract_type_config.py  ← accounting에서 이동
  ├── customer.py              (기존)
  └── ...

app/modules/accounting/models/
  ├── contract_sales_detail.py ← 신규 (영업 확장)
  ├── contract_contact.py      (기존, FK 유지: contract_period_id)
  ├── monthly_forecast.py      (기존, FK 유지: contract_period_id)
  ├── transaction_line.py      (기존, FK: contract_id 유지)
  ├── receipt.py               (기존, FK: contract_id 유지)
  └── ...

app/modules/infra/models/
  ├── period_phase.py          ← project_phase.py 리네이밍 + FK 변경
  ├── period_deliverable.py    ← project_deliverable.py 리네이밍
  ├── period_asset.py          ← project_asset.py FK 변경
  ├── period_customer.py       ← project_customer.py FK 변경
  ├── asset.py                 (기존, customer_id FK)
  └── ...
```

### 3.2 import 규칙 준수

```
core ← common(Contract, ContractPeriod, ContractTypeConfig, Customer)
         ← accounting(ContractSalesDetail, ContractContact, Forecast, ...)
         ← infra(PeriodPhase, Asset, ...)
```

accounting과 infra 모두 common의 Contract/ContractPeriod만 참조. **상호 참조 없음**.

### 3.3 API 엔드포인트 변경

#### 공통 (common 모듈)

| 엔드포인트 | 설명 | 비고 |
|-----------|------|------|
| `GET/POST /api/v1/contracts` | 사업 CRUD | 공통 필드만 |
| `GET/POST /api/v1/contract-periods` | 계약단위 CRUD | 공통 필드만 |
| `GET/POST /api/v1/contract-types` | 사업유형 설정 | accounting에서 이동 |

#### 영업 (accounting 모듈)

| 엔드포인트 | 설명 | 비고 |
|-----------|------|------|
| `GET/PATCH /api/v1/contract-periods/{id}/sales-detail` | 영업 확장정보 | 검수/계산서/매출. 조회 시 미존재하면 기본값으로 자동 생성 |
| 기존 forecast, ledger, receipt API | 변경 없음 | contract_period_id FK 유지 |

#### 인프라 (infra 모듈)

| 엔드포인트 | 설명 | 비고 |
|-----------|------|------|
| `GET/POST /api/v1/period-phases` | 단계 CRUD | contract_period_id FK |
| `GET/POST /api/v1/period-deliverables` | 산출물 CRUD | phase_id FK |
| 기존 assets, ip, portmap API | 변경 없음 | customer_id FK 유지 |

> `/api/v1/projects` → 삭제. 인프라에서 "프로젝트 목록"은 `/api/v1/contract-periods?customer_id=X`로 대체.

---

## 4. UI 변경

### 4.1 프로젝트관리 모듈 네비게이션

**상단 바:** 변경 없음 (고객사 셀렉터 + 진행중인 프로젝트 읽기 전용 표시)
- 표시 텍스트: `사업명 (Y26)` 형식

**프로젝트 목록 뷰:** `contract_periods` 기반으로 렌더링
- 표시: `사업명 (Y26)` = `contract.contract_name` + ` (` + `period.period_label` + `)`
- 필터: 선택된 고객사의 계약단위만 표시

**프로젝트 상세 뷰:** contract_period 기반
- 프로젝트 정보 카드 → 사업명, 코드, 고객사, 기간, 상태
- 단계/산출물/업체 탭 → FK가 contract_period_id로 변경될 뿐 동일

### 4.2 영업관리 모듈

**사업 상세:** 기존과 동일하되, 사업 기본정보 수정 시 common API 호출.
- 영업 전용 정보(검수/계산서/매출) → sales-detail API 호출
- Forecast, 원장, 입금 → 기존과 동일

### 4.3 사업 등록 플로우

**영업에서 등록:** 사업명, 유형, 고객사, 기간 + 영업 전용 정보 한 번에 입력
**인프라에서 등록:** 사업명, 유형, 고객사, 기간만 입력 (영업 정보는 비워둠)

→ 같은 `POST /api/v1/contracts` + `POST /api/v1/contract-periods` 호출. 인프라에서는 sales-detail을 생성하지 않음.

### 4.4 localStorage 키 변경

| 현재 | 변경 후 |
|------|--------|
| `infra.last_project_id` | `infra.last_period_id` |

---

## 5. 마이그레이션 전략

### 5.1 Alembic 마이그레이션 순서

**단일 마이그레이션 파일**로 원자적 실행 (중간 상태에서 앱 실행 방지):

1. `contract_sales_details` 테이블 생성
2. `contract_periods`에 `description` 컬럼 추가 (Text, nullable)
3. `contract_periods`의 영업 전용 필드를 `contract_sales_details`로 데이터 복사
4. `contract_periods`에서 영업 전용 컬럼 삭제
5. `contracts`에서 검수/계산서 컬럼 삭제 (period 레벨만 유지)
6. infra 테이블 FK 변경: `project_id` → `contract_period_id` (데이터 매핑 포함)
7. infra 테이블 리네이밍 (project_* → period_*)
8. `projects`, `project_contract_links` 테이블 삭제

### 5.2 데이터 매핑 (projects → contract_periods)

infra FK 변경 시 기존 `project_id` 값을 `contract_period_id`로 매핑해야 한다:

**Case 1: project_contract_links에 is_primary=true 매핑 존재**
→ 해당 contract의 가장 최근 contract_period를 사용

**Case 2: project_contract_links에 매핑 존재하나 is_primary 없음**
→ 첫 번째 링크의 contract_period를 사용

**Case 3: project_contract_links에 매핑 없음 (고아 프로젝트)**
→ 신규 contract 자동 생성:
  - `contract_code`: 기존 `project.project_code`에서 변환 (충돌 시 `-MIG` 접미사)
  - `contract_name`: `project.project_name`
  - `contract_type`: `'ETC'` (기본값)
  - `end_customer_id`: `project.customer_id`
→ 신규 contract_period 자동 생성:
  - `period_year`: `project.start_date`의 연도 (없으면 현재 연도)
  - `description`: `project.description`

**Case 4: 동일 contract_period에 여러 project가 매핑**
→ 각 project의 자식 데이터(phase, deliverable, asset, customer)를 해당 contract_period로 병합. 이름 충돌 시 프로젝트명 접두사 추가.

### 5.3 파일 이동

| 현재 위치 | 이동 후 |
|-----------|--------|
| `accounting/models/contract.py` | `common/models/contract.py` |
| `accounting/models/contract_period.py` | `common/models/contract_period.py` |
| `accounting/models/contract_type_config.py` | `common/models/contract_type_config.py` |
| `accounting/schemas/contract.py` (공통 부분) | `common/schemas/contract.py` |
| `accounting/schemas/contract_period.py` (공통 부분) | `common/schemas/contract_period.py` |
| `accounting/schemas/contract_type_config.py` | `common/schemas/contract_type_config.py` |
| `accounting/services/contract_service.py` (공통 CRUD) | `common/services/contract_service.py` |
| `accounting/services/contract_type_config.py` | `common/services/contract_type_config.py` |
| `accounting/routers/contracts.py` (공통 부분) | `common/routers/contracts.py` |
| `accounting/routers/contract_types.py` | `common/routers/contract_types.py` |
| `accounting/models/__init__.py` | Contract, ContractPeriod, ContractTypeConfig import 제거 |
| `common/models/__init__.py` | Contract, ContractPeriod, ContractTypeConfig import 추가 |

> `core/startup/bootstrap.py`의 `seed_defaults` import 경로도 `accounting` → `common`으로 변경.

---

## 6. 범위 제외 (TBD)

이번 설계에서 **제외**하는 항목:

| 항목 | 사유 |
|------|------|
| 정책 (PolicyDefinition, PolicyAssignment) | 사용자 요청으로 TBD |
| 자산 관계 (AssetRelation) | 자산이 충분히 쌓인 후 필요 |
| 프로젝트 상세의 변경이력 탭 | 공통 감사 로그 페이지로 대체 가능 |

---

## 7. 영향 범위 요약

### 모델 파일

| 변경 유형 | 파일 수 | 상세 |
|-----------|--------|------|
| 이동 | 3 | contract.py, contract_period.py, contract_type_config.py → common |
| 신규 | 1 | contract_sales_detail.py |
| FK 변경 + 리네이밍 | 5 | phase, deliverable, asset, customer, customer_contact |
| 삭제 | 3 | project.py, project_contract_link.py, + schemas/services/routers |
| 수정 (import) | 2 | common/__init__.py, accounting/__init__.py |

### 서비스/라우터

| 변경 유형 | 파일 수 | 상세 |
|-----------|--------|------|
| 이동 | 4 | contract_service, contract router, contract_type_config service/router → common |
| 신규 | 1 | contract_sales_detail service/router |
| FK 변경 | 8+ | phase_service, deliverable_service, asset_service, customer_service, infra_exporter, infra_metrics, _helpers, network_service |
| 삭제 | 4 | project_service, project router, project_contract_link service/router |

### 프론트엔드

| 변경 유형 | 파일 수 | 상세 |
|-----------|--------|------|
| 수정 | 3 | infra_projects.js/html, infra_project_detail.js/html → period 기반 |
| 수정 | 1 | contract_detail.js → sales-detail API 분리 호출 |
| 수정 | 1 | utils.js → localStorage 키 변경, ctx 셀렉터 API 경로 변경 |

### 감사 로그

기존 `entity_type == "project"` 감사 로그 항목은 마이그레이션에서 `"contract_period"`로 변환한다.
