# Customer → Partner 리네이밍 + 코드 체계 변경

> Customer를 Partner로 리네이밍하고, 코드 체계를 P000-B000-Y26A로 변경한다.

---

## 1. DB 테이블 리네이밍

| 현행 | 변경 |
|------|------|
| `customers` | `partners` |
| `customer_contacts` | `partner_contacts` |
| `customer_contact_roles` | `partner_contact_roles` |
| `period_customers` | `period_partners` |
| `period_customer_contacts` | `period_partner_contacts` |

## 2. FK 컬럼 리네이밍

| 현행 | 변경 | 영향 테이블 |
|------|------|------------|
| `customer_id` | `partner_id` | partner_contacts, contracts(end→), contract_periods, period_partners, transaction_lines, receipts, receipt_matches |
| `end_customer_id` | `end_partner_id` | contracts |
| `customer_contact_id` | `partner_contact_id` | contract_contacts, asset_contacts, period_partner_contacts |
| `period_customer_id` | `period_partner_id` | period_partner_contacts |
| `customer_code` | `partner_code` | partners |

## 3. 코드 체계 변경

```text
P000-B000-Y26A
│     │     └── 기간코드: Y + 연도(2자리) + 순번(A~Z) — 변경 없음
│     └──────── 사업코드: B + base36(3자리), 업체 내 순번 (P→B)
└────────────── 업체코드: P + base36(3자리), 전역 순번 (C→P)
```

| 구분 | 현행 | 변경 |
|------|------|------|
| 업체코드 | `C000` | `P000` |
| 사업코드 | `C000-P000` | `P000-B000` |
| 기간코드 | `C000-P000-Y26A` | `P000-B000-Y26A` |
| 예약코드 | `CXXX` | `PXXX` |

## 4. partner_type 확장

현행 `customer_type` (자유 텍스트) → `partner_type` (권장 값):

- `CUSTOMER` — 고객사
- `IMPLEMENTER` — 수행사
- `MAINTAINER` — 유지보수사
- `CARRIER` — 통신사
- `VENDOR` — 벤더/제조사
- `ETC` — 기타

DB 타입은 `String(50)` 유지 (ENUM 아님, 확장 가능).

## 5. period_partner.role

현행 `PeriodCustomer.role` → `PeriodPartner.role`:

- `CUSTOMER`, `IMPLEMENTER`, `MAINTAINER`, `CARRIER`, `VENDOR`

## 6. API 엔드포인트 변경

| 현행 | 변경 |
|------|------|
| `/api/v1/customers` | `/api/v1/partners` |
| `/api/v1/customers/{id}` | `/api/v1/partners/{id}` |
| `/api/v1/customers/{id}/contacts` | `/api/v1/partners/{id}/contacts` |
| `/api/v1/customers/{id}/contacts/{cid}/roles` | `/api/v1/partners/{id}/contacts/{cid}/roles` |
| `/api/v1/period-customers` | `/api/v1/period-partners` |
| `/api/v1/period-customer-contacts` | `/api/v1/period-partner-contacts` |
| 쿼리파라미터 `customer_id` | `partner_id` |

## 7. 파일 리네이밍

### 모델

| 현행 | 변경 |
|------|------|
| `common/models/customer.py` | `common/models/partner.py` |
| `common/models/customer_contact.py` | `common/models/partner_contact.py` |
| `common/models/customer_contact_role.py` | `common/models/partner_contact_role.py` |
| `infra/models/period_customer.py` | `infra/models/period_partner.py` |
| `infra/models/period_customer_contact.py` | `infra/models/period_partner_contact.py` |

### 스키마

| 현행 | 변경 |
|------|------|
| `common/schemas/customer.py` | `common/schemas/partner.py` |
| `common/schemas/customer_contact.py` | `common/schemas/partner_contact.py` |
| `common/schemas/customer_contact_role.py` | `common/schemas/partner_contact_role.py` |
| `infra/schemas/period_customer.py` | `infra/schemas/period_partner.py` |
| `infra/schemas/period_customer_contact.py` | `infra/schemas/period_partner_contact.py` |

### 서비스

| 현행 | 변경 |
|------|------|
| `common/services/customer.py` | `common/services/partner.py` |
| `common/services/_customer_helpers.py` | `common/services/_partner_helpers.py` |
| `infra/services/period_customer_service.py` | `infra/services/period_partner_service.py` |
| `infra/services/period_customer_contact_service.py` | `infra/services/period_partner_contact_service.py` |

### 라우터

| 현행 | 변경 |
|------|------|
| `common/routers/customers.py` | `common/routers/partners.py` |
| `infra/routers/period_customers.py` | `infra/routers/period_partners.py` |
| `infra/routers/period_customer_contacts.py` | `infra/routers/period_partner_contacts.py` |

### 테스트

| 현행 | 변경 |
|------|------|
| `tests/infra/test_period_customer_service.py` | `tests/infra/test_period_partner_service.py` |
| `tests/infra/test_period_customer_contact_service.py` | `tests/infra/test_period_partner_contact_service.py` |
| `tests/infra/test_customer_centric.py` | `tests/infra/test_partner_centric.py` |

### 프론트엔드

| 현행 | 변경 |
|------|------|
| `app/static/js/customers.js` | `app/static/js/partners.js` |
| `app/templates/customers.html` | `app/templates/partners.html` |

## 8. 클래스/함수 리네이밍 (주요)

| 현행 | 변경 |
|------|------|
| `Customer` | `Partner` |
| `CustomerContact` | `PartnerContact` |
| `CustomerContactRole` | `PartnerContactRole` |
| `PeriodCustomer` | `PeriodPartner` |
| `PeriodCustomerContact` | `PeriodPartnerContact` |
| `CustomerCreate/Update/Read` | `PartnerCreate/Update/Read` |
| `next_customer_code()` | `next_partner_code()` |
| `next_contract_code()` | `next_business_code()` |
| `RESERVED_CUSTOMER_CODE = "CXXX"` | `RESERVED_PARTNER_CODE = "PXXX"` |

## 9. UI 라벨

- topbar "고객사" 라벨: **유지** (사용자 관점에서 고객사가 자연스러움)
- 사이드바/메뉴 "거래처": **유지**
- 프론트엔드 API 호출 경로만 `/partners`로 변경

## 10. 마이그레이션 (Alembic 0012)

단일 마이그레이션 `0012_customer_to_partner.py`:

### Step 1: 테이블 리네이밍

```python
op.rename_table("customers", "partners")
op.rename_table("customer_contacts", "partner_contacts")
op.rename_table("customer_contact_roles", "partner_contact_roles")
op.rename_table("period_customers", "period_partners")
op.rename_table("period_customer_contacts", "period_partner_contacts")
```

### Step 2: FK 컬럼 리네이밍

모든 `customer_id` → `partner_id`, `end_customer_id` → `end_partner_id` 등.
`op.alter_column()` 사용.

### Step 3: 코드 변환

```sql
-- partner_code: C→P
UPDATE partners SET partner_code = 'P' || SUBSTRING(partner_code FROM 2);
-- contract_code: C→P prefix, -P→-B
UPDATE contracts SET contract_code =
  'P' || SUBSTRING(contract_code FROM 2 FOR 3) || '-B' || SUBSTRING(contract_code FROM 6);
-- period_code: 같은 패턴
UPDATE contract_periods SET period_code =
  'P' || SUBSTRING(period_code FROM 2 FOR 3) || '-B' || SUBSTRING(period_code FROM 6);
```

### Step 4: 인덱스/제약 이름 변경

기존 인덱스, unique constraint 이름에 `customer`가 포함된 것들 rename.

비가역 마이그레이션 — `downgrade()` raises `NotImplementedError`.

## 11. 유지 항목 (변경 없음)

- Contract / ContractPeriod 구조
- ContractSalesDetail
- PeriodPhase / PeriodDeliverable
- Asset / AssetIp / AssetRelation / AssetContact
- PolicyDefinition / PolicyAssignment
- ProductCatalog / HardwareSpec
- code_generator.py의 base36 유틸리티 함수 (int_to_base36, base36_to_int)

## 12. 영향 범위 요약

| 카테고리 | 파일 수 |
|---------|--------|
| 모델 (rename + 내용) | 5 |
| 스키마 (rename + 내용) | 5 |
| 서비스 (rename + 내용) | 4 |
| 라우터 (rename + 내용) | 3 |
| code_generator.py | 1 |
| 마이그레이션 신규 | 1 |
| __init__.py 갱신 | 6 |
| 2차 import 수정 (accounting/infra 서비스) | ~20 |
| JS 파일 | ~16 |
| HTML 템플릿 | ~8 |
| 테스트 | ~10 |
| 문서 | ~10 |
| **총계** | **~90 파일** |
