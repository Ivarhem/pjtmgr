# Customer → Partner 리네이밍 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename Customer to Partner across the entire codebase — DB tables/columns, Python models/schemas/services/routers, JS/HTML frontend, tests, docs — and update code prefixes (C→P for partners, P→B for contracts).

**Architecture:** Mechanical rename following spec `docs/superpowers/specs/2026-03-24-customer-to-partner-design.md`. File renames via `git mv`, content changes via find-replace with manual review. Single Alembic migration 0012 handles DB schema + data changes. Non-reversible.

**Tech Stack:** Python/FastAPI/SQLAlchemy, Alembic, Jinja2, vanilla JS, PostgreSQL

**Branch:** `feat/unified-business-model` (continue existing)

---

## File Structure

### Files to Rename (17 files via `git mv`)

| From | To |
|------|------|
| `app/modules/common/models/customer.py` | `→ partner.py` |
| `app/modules/common/models/customer_contact.py` | `→ partner_contact.py` |
| `app/modules/common/models/customer_contact_role.py` | `→ partner_contact_role.py` |
| `app/modules/common/schemas/customer.py` | `→ partner.py` |
| `app/modules/common/schemas/customer_contact.py` | `→ partner_contact.py` |
| `app/modules/common/schemas/customer_contact_role.py` | `→ partner_contact_role.py` |
| `app/modules/common/services/customer.py` | `→ partner.py` |
| `app/modules/common/services/_customer_helpers.py` | `→ _partner_helpers.py` |
| `app/modules/common/routers/customers.py` | `→ partners.py` |
| `app/modules/infra/models/period_customer.py` | `→ period_partner.py` |
| `app/modules/infra/models/period_customer_contact.py` | `→ period_partner_contact.py` |
| `app/modules/infra/schemas/period_customer.py` | `→ period_partner.py` |
| `app/modules/infra/schemas/period_customer_contact.py` | `→ period_partner_contact.py` |
| `app/modules/infra/services/period_customer_service.py` | `→ period_partner_service.py` |
| `app/modules/infra/services/period_customer_contact_service.py` | `→ period_partner_contact_service.py` |
| `app/modules/infra/routers/period_customers.py` | `→ period_partners.py` |
| `app/modules/infra/routers/period_customer_contacts.py` | `→ period_partner_contacts.py` |

### Files to Rename — Frontend (2 files)

| From | To |
|------|------|
| `app/static/js/customers.js` | `→ partners.js` |
| `app/templates/customers.html` | `→ partners.html` |

### Files to Rename — Tests (4 files)

| From | To |
|------|------|
| `tests/common/test_customer_service.py` | `→ test_partner_service.py` |
| `tests/infra/test_period_customer_service.py` | `→ test_period_partner_service.py` |
| `tests/infra/test_period_customer_contact_service.py` | `→ test_period_partner_contact_service.py` |
| `tests/infra/test_customer_centric.py` | `→ test_partner_centric.py` |

### New Files (1)

| Path | Purpose |
|------|---------|
| `alembic/versions/0012_customer_to_partner.py` | DB migration: table/column rename + code prefix conversion |

### Files to Modify (content only, ~70 files)

Grouped by task below. Every file with `customer` in its content needs updating.

---

## Task 1: Alembic Migration 0012

**Files:**
- Create: `alembic/versions/0012_customer_to_partner.py`

- [ ] **Step 1: Create migration file**

```python
"""Customer → Partner rename.

Revision ID: 0012
Revises: 0011
Create Date: 2026-03-24

NON-REVERSIBLE: 테이블/컬럼/코드 prefix 변경. 실행 전 DB 백업 권장.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # === Step 1: 테이블 리네이밍 ===
    op.rename_table("customers", "partners")
    op.rename_table("customer_contacts", "partner_contacts")
    op.rename_table("customer_contact_roles", "partner_contact_roles")
    op.rename_table("period_customers", "period_partners")
    op.rename_table("period_customer_contacts", "period_partner_contacts")

    # === Step 2: FK 컬럼 리네이밍 ===
    # partners 테이블
    op.alter_column("partners", "customer_code", new_column_name="partner_code")
    op.alter_column("partners", "customer_type", new_column_name="partner_type")

    # partner_contacts 테이블
    op.alter_column("partner_contacts", "customer_id", new_column_name="partner_id")

    # partner_contact_roles 테이블
    op.alter_column("partner_contact_roles", "customer_contact_id", new_column_name="partner_contact_id")

    # contracts 테이블
    op.alter_column("contracts", "end_customer_id", new_column_name="end_partner_id")

    # contract_periods 테이블
    op.alter_column("contract_periods", "customer_id", new_column_name="partner_id")

    # period_partners 테이블
    op.alter_column("period_partners", "customer_id", new_column_name="partner_id")

    # period_partner_contacts 테이블
    # Note: contact_id 컬럼은 generic name이므로 rename 불필요 (FK target만 테이블 rename으로 자동 갱신)
    op.alter_column("period_partner_contacts", "period_customer_id", new_column_name="period_partner_id")

    # transaction_lines 테이블 (accounting)
    op.alter_column("transaction_lines", "customer_id", new_column_name="partner_id")

    # receipts 테이블 (accounting)
    op.alter_column("receipts", "customer_id", new_column_name="partner_id")

    # contract_contacts 테이블 (accounting) — customer_id + customer_contact_id 둘 다 존재
    op.alter_column("contract_contacts", "customer_id", new_column_name="partner_id")
    op.alter_column("contract_contacts", "customer_contact_id", new_column_name="partner_contact_id")

    # assets 테이블 (infra)
    op.alter_column("assets", "customer_id", new_column_name="partner_id")

    # ip_subnets 테이블 (infra)
    op.alter_column("ip_subnets", "customer_id", new_column_name="partner_id")

    # policy_assignments 테이블 (infra)
    op.alter_column("policy_assignments", "customer_id", new_column_name="partner_id")

    # port_maps 테이블 (infra)
    op.alter_column("port_maps", "customer_id", new_column_name="partner_id")

    # asset_contacts 테이블 (infra)
    # Note: contact_id 컬럼은 generic name이므로 rename 불필요 (FK target만 테이블 rename으로 자동 갱신)

    # === Step 3: 코드 변환 ===
    conn = op.get_bind()
    # partner_code: C→P
    conn.execute(text(
        "UPDATE partners SET partner_code = 'P' || SUBSTRING(partner_code FROM 2) "
        "WHERE partner_code LIKE 'C%'"
    ))
    # contract_code: C→P prefix, -P→-B
    conn.execute(text(
        "UPDATE contracts SET contract_code = "
        "'P' || SUBSTRING(contract_code FROM 2 FOR 3) || '-B' || SUBSTRING(contract_code FROM 6) "
        "WHERE contract_code LIKE 'C%'"
    ))
    # period_code: 같은 패턴
    conn.execute(text(
        "UPDATE contract_periods SET period_code = "
        "'P' || SUBSTRING(period_code FROM 2 FOR 3) || '-B' || SUBSTRING(period_code FROM 6) "
        "WHERE period_code LIKE 'C%'"
    ))

    # === Step 4: 인덱스/제약 이름 변경 ===
    # SQLAlchemy가 테이블 rename 시 자동으로 FK constraint를 갱신하지 않으므로
    # 주요 인덱스 이름을 수동 갱신한다.
    # Note: PostgreSQL은 테이블 rename 시 인덱스 이름을 자동 변경하지 않음.
    # 기능에는 영향 없으므로 인덱스 이름 변경은 선택적.
    # 필요 시 op.f()로 인덱스/constraint를 drop-recreate 한다.


def downgrade() -> None:
    raise NotImplementedError("Customer→Partner rename은 비가역 마이그레이션입니다.")
```

**중요:** 이 migration은 실제 DB에서 실행하기 전에 모든 코드 변경이 완료된 후 통합 테스트해야 한다. migration 파일 작성은 먼저 하되, 실행은 마지막에 한다.

**실제 모델 확인 결과 (2026-03-24):**

- `asset_contacts.contact_id` — generic name, rename 불필요 (FK ref만 테이블 rename으로 자동 갱신)
- `period_customer_contacts.contact_id` — generic name, rename 불필요
- `receipt_matches` — `customer_id` 컬럼 없음, migration 불필요
- `contract_contacts` — `customer_id` + `customer_contact_id` 둘 다 존재, 둘 다 rename
- `assets`, `ip_subnets`, `policy_assignments`, `port_maps` — 각각 `customer_id` 존재, 모두 rename

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/0012_customer_to_partner.py
git commit -m "feat(migration): 0012 customer-to-partner rename (tables, columns, codes)"
```

---

## Task 2: Common Module — Models Rename + Content

**Files:**
- Rename: `app/modules/common/models/customer.py` → `partner.py`
- Rename: `app/modules/common/models/customer_contact.py` → `partner_contact.py`
- Rename: `app/modules/common/models/customer_contact_role.py` → `partner_contact_role.py`
- Modify: `app/modules/common/models/__init__.py`
- Modify: `app/modules/common/models/contract.py` (end_customer_id → end_partner_id)
- Modify: `app/modules/common/models/contract_period.py` (customer_id refs if any)

- [ ] **Step 1: git mv the 3 model files**

```bash
git mv app/modules/common/models/customer.py app/modules/common/models/partner.py
git mv app/modules/common/models/customer_contact.py app/modules/common/models/partner_contact.py
git mv app/modules/common/models/customer_contact_role.py app/modules/common/models/partner_contact_role.py
```

- [ ] **Step 2: Update partner.py content**

In `app/modules/common/models/partner.py`:
- Docstring: `"""거래처 (매출처/매입처 공용)"""` → `"""업체 (Partner) — 고객사/수행사/유지보수사/통신사/벤더 공용"""`
- Class: `Customer` → `Partner`
- `__tablename__`: `"customers"` → `"partners"`
- Column: `customer_code` → `partner_code`
- Column: `customer_type` → `partner_type`
- Relationship: `CustomerContact` → `PartnerContact`
- Relationship `back_populates`: `"customer"` → `"partner"`
- Relationship: `end_customer` → `end_partner`

- [ ] **Step 3: Update partner_contact.py content**

- Class: `CustomerContact` → `PartnerContact`
- `__tablename__`: `"customer_contacts"` → `"partner_contacts"`
- FK: `customer_id` → `partner_id`, ForeignKey `"customers.id"` → `"partners.id"`
- Relationship `back_populates`: `"contacts"` (keep) but type ref `"Customer"` → `"Partner"`

- [ ] **Step 4: Update partner_contact_role.py content**

- Class: `CustomerContactRole` → `PartnerContactRole`
- `__tablename__`: `"customer_contact_roles"` → `"partner_contact_roles"`
- FK: `customer_contact_id` → `partner_contact_id`, ForeignKey `"customer_contacts.id"` → `"partner_contacts.id"`

- [ ] **Step 5: Update contract.py**

- `end_customer_id` → `end_partner_id`
- ForeignKey `"customers.id"` → `"partners.id"`
- Relationship `end_customer` → `end_partner`, type `"Customer"` → `"Partner"`

- [ ] **Step 6: Update contract_period.py** (if it has customer refs)

Check and update any `customer_id` or `Customer` references.

- [ ] **Step 7: Update __init__.py**

```python
# Old:
from app.modules.common.models.customer import Customer
from app.modules.common.models.customer_contact import CustomerContact
from app.modules.common.models.customer_contact_role import CustomerContactRole
# New:
from app.modules.common.models.partner import Partner
from app.modules.common.models.partner_contact import PartnerContact
from app.modules.common.models.partner_contact_role import PartnerContactRole
```

Update `__all__` list accordingly.

- [ ] **Step 8: Commit**

```bash
git add -A app/modules/common/models/
git commit -m "refactor(common/models): Customer → Partner rename"
```

---

## Task 3: Common Module — Schemas Rename + Content

**Files:**
- Rename: `app/modules/common/schemas/customer.py` → `partner.py`
- Rename: `app/modules/common/schemas/customer_contact.py` → `partner_contact.py`
- Rename: `app/modules/common/schemas/customer_contact_role.py` → `partner_contact_role.py`
- Modify: `app/modules/common/schemas/contract.py` (customer_id → partner_id fields)
- Modify: `app/modules/common/schemas/contract_period.py` (customer refs)

- [ ] **Step 1: git mv the 3 schema files**

```bash
git mv app/modules/common/schemas/customer.py app/modules/common/schemas/partner.py
git mv app/modules/common/schemas/customer_contact.py app/modules/common/schemas/partner_contact.py
git mv app/modules/common/schemas/customer_contact_role.py app/modules/common/schemas/partner_contact_role.py
```

- [ ] **Step 2: Update all schema class names and fields**

In each file:
- `CustomerCreate/Update/Read` → `PartnerCreate/Update/Read`
- `CustomerContactCreate/Update/Read` → `PartnerContactCreate/Update/Read`
- `CustomerContactRoleCreate/Update/Read` → `PartnerContactRoleCreate/Update/Read`
- Field names: `customer_code` → `partner_code`, `customer_type` → `partner_type`, `customer_id` → `partner_id`, `customer_contact_id` → `partner_contact_id`

- [ ] **Step 3: Update contract.py and contract_period.py schemas**

- `end_customer_id` → `end_partner_id`
- `customer_id` → `partner_id`
- `customer_name` → `partner_name` (display fields)

- [ ] **Step 4: Commit**

```bash
git add -A app/modules/common/schemas/
git commit -m "refactor(common/schemas): Customer → Partner rename"
```

---

## Task 4: Common Module — Services Rename + Content

**Files:**
- Rename: `app/modules/common/services/customer.py` → `partner.py`
- Rename: `app/modules/common/services/_customer_helpers.py` → `_partner_helpers.py`
- Modify: `app/modules/common/services/contract_service.py`
- Modify: `app/modules/common/services/term_config.py`

- [ ] **Step 1: git mv the 2 service files**

```bash
git mv app/modules/common/services/customer.py app/modules/common/services/partner.py
git mv app/modules/common/services/_customer_helpers.py app/modules/common/services/_partner_helpers.py
```

- [ ] **Step 2: Update partner.py service content**

- All function names: `*customer*` → `*partner*`
- All imports: `Customer` → `Partner`, `CustomerCreate` → `PartnerCreate`, etc.
- DB queries: `Customer` model references
- `next_customer_code` → `next_partner_code`

- [ ] **Step 3: Update _partner_helpers.py content**

- All `customer` refs → `partner`

- [ ] **Step 4: Update contract_service.py**

- Imports: `Customer` → `Partner`
- `customer_id` → `partner_id` in queries/logic
- `next_contract_code` → `next_business_code`

- [ ] **Step 5: Update term_config.py** (if customer refs exist)

- [ ] **Step 6: Commit**

```bash
git add -A app/modules/common/services/
git commit -m "refactor(common/services): Customer → Partner rename"
```

---

## Task 5: Common Module — Router Rename + Content

**Files:**
- Rename: `app/modules/common/routers/customers.py` → `partners.py`
- Modify: `app/modules/common/routers/__init__.py`
- Modify: `app/modules/common/routers/contracts.py`
- Modify: `app/modules/common/routers/pages.py`

- [ ] **Step 1: git mv router file**

```bash
git mv app/modules/common/routers/customers.py app/modules/common/routers/partners.py
```

- [ ] **Step 2: Update partners.py content**

- Route prefix: `"/customers"` → `"/partners"`
- All imports/function names: `customer` → `partner`
- Query params: `customer_id` → `partner_id`

- [ ] **Step 3: Update __init__.py**

```python
# Old:
from app.modules.common.routers.customers import router as customers_router
# New:
from app.modules.common.routers.partners import router as partners_router
```

Update `api_router.include_router()`, re-export, and `__all__`.

- [ ] **Step 4: Update contracts.py router** (customer_id query params)

- [ ] **Step 5: Update pages.py** (if customer page routes exist)

- [ ] **Step 6: Commit**

```bash
git add -A app/modules/common/routers/
git commit -m "refactor(common/routers): Customer → Partner rename"
```

---

## Task 6: code_generator.py — Prefix Changes

**Files:**
- Modify: `app/core/code_generator.py`

- [ ] **Step 1: Update constants and functions**

```python
# Old:
RESERVED_CUSTOMER_CODE = "CXXX"
def next_customer_code(db: Session) -> str:
def next_contract_code(db: Session, customer_code: str) -> str:

# New:
RESERVED_PARTNER_CODE = "PXXX"
def next_partner_code(db: Session) -> str:
def next_business_code(db: Session, partner_code: str) -> str:
```

- [ ] **Step 2: Update SQL queries inside functions**

`next_partner_code`:
- Table: `partners` (not `customers`)
- Column: `partner_code` (not `customer_code`)
- Prefix: `'P%'` (not `'C%'`)
- Reserved: `RESERVED_PARTNER_CODE`
- Return: `f"P{int_to_base36(n)}"`

`next_business_code`:
- Parameter: `partner_code` (not `customer_code`)
- Pattern: `f"{partner_code}-B%"` (not `-P%`)
- Split: `"-B"` (not `"-P"`)
- Return: `f"{partner_code}-B{int_to_base36(n)}"`

- [ ] **Step 3: Update module docstring**

```python
"""계층적 코드 채번 유틸리티.

코드 형식: P000-B000-Y26A
- 업체코드: P + base36(3) 전역 순번
- 사업코드: {업체코드}-B + base36(3) 업체 내 순번
- 기간코드: {사업코드}-Y + 연도(2) + A~Z 순번
"""
```

- [ ] **Step 4: Commit**

```bash
git add app/core/code_generator.py
git commit -m "refactor(code_generator): C→P partner prefix, P→B business prefix"
```

---

## Task 7: Infra Module — Models Rename + Content

**Files:**
- Rename: `app/modules/infra/models/period_customer.py` → `period_partner.py`
- Rename: `app/modules/infra/models/period_customer_contact.py` → `period_partner_contact.py`
- Modify: `app/modules/infra/models/__init__.py`
- Modify: `app/modules/infra/models/asset.py` (customer_code refs)
- Modify: `app/modules/infra/models/asset_contact.py` (customer_contact refs)
- Modify: `app/modules/infra/models/ip_subnet.py` (customer_code refs)
- Modify: `app/modules/infra/models/policy_assignment.py` (period_customer refs)
- Modify: `app/modules/infra/models/port_map.py` (customer_code refs)

- [ ] **Step 1: git mv the 2 model files**

```bash
git mv app/modules/infra/models/period_customer.py app/modules/infra/models/period_partner.py
git mv app/modules/infra/models/period_customer_contact.py app/modules/infra/models/period_partner_contact.py
```

- [ ] **Step 2: Update period_partner.py content**

- Class: `PeriodCustomer` → `PeriodPartner`
- `__tablename__`: `"period_customers"` → `"period_partners"`
- FK: `customer_id` → `partner_id`, ref `"customers.id"` → `"partners.id"`
- Relationships: all `Customer`/`customer` refs → `Partner`/`partner`

- [ ] **Step 3: Update period_partner_contact.py content**

- Class: `PeriodCustomerContact` → `PeriodPartnerContact`
- `__tablename__`: `"period_customer_contacts"` → `"period_partner_contacts"`
- FK: `period_customer_id` → `period_partner_id`, `customer_contact_id` → `partner_contact_id`

- [ ] **Step 4: Update __init__.py**

```python
# Old:
from app.modules.infra.models.period_customer import PeriodCustomer
from app.modules.infra.models.period_customer_contact import PeriodCustomerContact
# New:
from app.modules.infra.models.period_partner import PeriodPartner
from app.modules.infra.models.period_partner_contact import PeriodPartnerContact
```

Update `__all__`.

- [ ] **Step 5: Update asset.py, asset_contact.py, ip_subnet.py, policy_assignment.py, port_map.py**

All `customer_code` → `partner_code`, `customer_id` → `partner_id`, `customer_contact_id` → `partner_contact_id`, `PeriodCustomer` → `PeriodPartner`, FK table refs `"customers.id"` → `"partners.id"`, etc.

- [ ] **Step 6: Commit**

```bash
git add -A app/modules/infra/models/
git commit -m "refactor(infra/models): Customer → Partner rename"
```

---

## Task 8: Infra Module — Schemas Rename + Content

**Files:**
- Rename: `app/modules/infra/schemas/period_customer.py` → `period_partner.py`
- Rename: `app/modules/infra/schemas/period_customer_contact.py` → `period_partner_contact.py`
- Modify: `app/modules/infra/schemas/asset.py`, `ip_subnet.py`, `policy_assignment.py`, `port_map.py`

- [ ] **Step 1: git mv the 2 schema files**

```bash
git mv app/modules/infra/schemas/period_customer.py app/modules/infra/schemas/period_partner.py
git mv app/modules/infra/schemas/period_customer_contact.py app/modules/infra/schemas/period_partner_contact.py
```

- [ ] **Step 2: Update renamed files content** — all `customer` → `partner` in class names, fields

- [ ] **Step 3: Update secondary schema files** — `customer_code` → `partner_code`, `customer_id` → `partner_id` fields

- [ ] **Step 4: Commit**

```bash
git add -A app/modules/infra/schemas/
git commit -m "refactor(infra/schemas): Customer → Partner rename"
```

---

## Task 9: Infra Module — Services Rename + Content

**Files:**
- Rename: `app/modules/infra/services/period_customer_service.py` → `period_partner_service.py`
- Rename: `app/modules/infra/services/period_customer_contact_service.py` → `period_partner_contact_service.py`
- Modify: `app/modules/infra/services/_helpers.py`
- Modify: `app/modules/infra/services/asset_service.py`, `asset_relation_service.py`, `infra_exporter.py`, `infra_importer.py`, `infra_metrics.py`, `network_service.py`, `policy_service.py`

- [ ] **Step 1: git mv the 2 service files**

```bash
git mv app/modules/infra/services/period_customer_service.py app/modules/infra/services/period_partner_service.py
git mv app/modules/infra/services/period_customer_contact_service.py app/modules/infra/services/period_partner_contact_service.py
```

- [ ] **Step 2: Update renamed files content** — all imports, class refs, function names, `customer` → `partner`

- [ ] **Step 3: Update all secondary service files**

For each file: update imports (`Customer` → `Partner`, `PeriodCustomer` → `PeriodPartner`), variable names, query filters (`customer_id` → `partner_id`, `customer_code` → `partner_code`).

- [ ] **Step 4: Commit**

```bash
git add -A app/modules/infra/services/
git commit -m "refactor(infra/services): Customer → Partner rename"
```

---

## Task 10: Infra Module — Routers Rename + Content

**Files:**
- Rename: `app/modules/infra/routers/period_customers.py` → `period_partners.py`
- Rename: `app/modules/infra/routers/period_customer_contacts.py` → `period_partner_contacts.py`
- Modify: `app/modules/infra/routers/__init__.py`
- Modify: `app/modules/infra/routers/assets.py`, `asset_ips.py`, `asset_relations.py`, `infra_dashboard.py`, `infra_excel.py`, `ip_subnets.py`, `policy_assignments.py`, `port_maps.py`

- [ ] **Step 1: git mv the 2 router files**

```bash
git mv app/modules/infra/routers/period_customers.py app/modules/infra/routers/period_partners.py
git mv app/modules/infra/routers/period_customer_contacts.py app/modules/infra/routers/period_partner_contacts.py
```

- [ ] **Step 2: Update renamed files content**

- Route prefix: `"/period-customers"` → `"/period-partners"`, `"/period-customer-contacts"` → `"/period-partner-contacts"`
- All imports, function names, query params

- [ ] **Step 3: Update __init__.py**

```python
# Old:
from app.modules.infra.routers.period_customers import router as period_customers_router
from app.modules.infra.routers.period_customer_contacts import router as period_customer_contacts_router
# New:
from app.modules.infra.routers.period_partners import router as period_partners_router
from app.modules.infra.routers.period_partner_contacts import router as period_partner_contacts_router
```

Update `include_router()` calls.

- [ ] **Step 4: Update secondary router files** — imports, query params, filter references

- [ ] **Step 5: Commit**

```bash
git add -A app/modules/infra/routers/
git commit -m "refactor(infra/routers): Customer → Partner rename"
```

---

## Task 11: Accounting Module — Models + Schemas + Services

**Files:**
- Modify: `app/modules/accounting/models/contract_contact.py` — `customer_contact_id` → `partner_contact_id`
- Modify: `app/modules/accounting/models/receipt.py` — `customer_id` → `partner_id`
- Modify: `app/modules/accounting/models/transaction_line.py` — `customer_id` → `partner_id`
- Modify: `app/modules/accounting/schemas/contract_contact.py`, `receipt.py`, `report.py`, `transaction_line.py`, `contract.py`
- Modify: `app/modules/accounting/services/contract_contact.py`, `dashboard.py`, `forecast_sync.py`, `importer.py`, `metrics.py`, `receipt.py`, `receipt_match.py`, `report.py`, `transaction_line.py`, `ledger.py`, `_report_export.py`
- Modify: `app/modules/accounting/routers/contract_contacts.py`, `dashboard.py`

- [ ] **Step 1: Update accounting models** — all `customer_id` → `partner_id`, `customer_contact_id` → `partner_contact_id`, FK refs `"customers.id"` → `"partners.id"`, relationship type refs `"Customer"` → `"Partner"`

- [ ] **Step 2: Update accounting schemas** — field names and type refs

- [ ] **Step 3: Update accounting services** — imports, variable names, query filters, function args

- [ ] **Step 4: Update accounting routers** — query params, imports

- [ ] **Step 5: Commit**

```bash
git add -A app/modules/accounting/
git commit -m "refactor(accounting): Customer → Partner rename (models/schemas/services/routers)"
```

---

## Task 12: Core Files — app_factory, auth

**Files:**
- Modify: `app/core/app_factory.py` — model import comments/refs
- Modify: `app/core/auth/authorization.py` — customer entity refs

- [ ] **Step 1: Update app_factory.py** — any `customer` import refs for Alembic model registration

- [ ] **Step 2: Update authorization.py** — permission entity names if referenced

- [ ] **Step 3: Commit**

```bash
git add app/core/
git commit -m "refactor(core): Customer → Partner refs in app_factory and auth"
```

---

## Task 13: Frontend — JS Files

**Files:**
- Rename: `app/static/js/customers.js` → `partners.js`
- Modify: `app/static/js/contract_detail.js`, `contracts.js`, `my_contracts.js`, `dashboard.js`, `reports.js`, `utils.js`
- Modify: `app/static/js/infra_project_detail.js`, `infra_projects.js`, `infra_assets.js`, `infra_dashboard.js`, `infra_import.js`, `infra_inventory_assets.js`, `infra_ip_inventory.js`, `infra_policies.js`, `infra_port_maps.js`

- [ ] **Step 1: git mv customers.js**

```bash
git mv app/static/js/customers.js app/static/js/partners.js
```

- [ ] **Step 2: Update partners.js content**

- API URLs: `/api/v1/customers` → `/api/v1/partners`
- Variable/function names: `customer` → `partner`
- Query params: `customer_id` → `partner_id`
- **Keep UI labels** like "고객사" unchanged (per spec §9)

- [ ] **Step 3: Update all secondary JS files**

For each file:
- API URLs: `/customers` → `/partners`, `/period-customers` → `/period-partners`, `/period-customer-contacts` → `/period-partner-contacts`
- JS variable names: `customerId` → `partnerId`, `customerCode` → `partnerCode`, `customerName` → `partnerName`
- Data property access: `item.customer_id` → `item.partner_id`, `item.customer_code` → `item.partner_code`, `item.customer_name` → `item.partner_name`
- **Preserve all Korean UI labels** (고객사, 거래처, etc.)

- [ ] **Step 4: Commit**

```bash
git add -A app/static/js/
git commit -m "refactor(frontend/js): Customer → Partner API paths and variable names"
```

---

## Task 14: Frontend — HTML Templates

**Files:**
- Rename: `app/templates/customers.html` → `partners.html`
- Modify: `app/templates/base.html` (nav links, script src)
- Modify: `app/templates/contracts.html`, `contract_detail.html`, `dashboard.html`, `my_contracts.html`
- Modify: `app/templates/components/_modal_add_contract.html` (if exists)

- [ ] **Step 1: git mv customers.html**

```bash
git mv app/templates/customers.html app/templates/partners.html
```

- [ ] **Step 2: Update partners.html**

- Script src: `customers.js` → `partners.js`
- Any `customer` data attributes or API refs

- [ ] **Step 3: Update base.html**

- Nav links: `url_for('pages.customers_page')` → `url_for('pages.partners_page')` (or equivalent route name)
- Script includes: `customers.js` → `partners.js`

- [ ] **Step 4: Update pages.py route names** (if template routing references changed)

- [ ] **Step 5: Update remaining templates** — `customer_id` data attrs, API paths in inline scripts

- [ ] **Step 6: Commit**

```bash
git add -A app/templates/
git commit -m "refactor(frontend/html): Customer → Partner template updates"
```

---

## Task 15: Tests — Rename + Content Update

**Files:**
- Rename: `tests/common/test_customer_service.py` → `test_partner_service.py`
- Rename: `tests/infra/test_period_customer_service.py` → `test_period_partner_service.py`
- Rename: `tests/infra/test_period_customer_contact_service.py` → `test_period_partner_contact_service.py`
- Rename: `tests/infra/test_customer_centric.py` → `test_partner_centric.py`
- Modify: `tests/conftest.py` — Customer fixtures → Partner fixtures
- Modify: ~20 test files with secondary customer references

- [ ] **Step 1: git mv the 4 test files**

```bash
git mv tests/common/test_customer_service.py tests/common/test_partner_service.py
git mv tests/infra/test_period_customer_service.py tests/infra/test_period_partner_service.py
git mv tests/infra/test_period_customer_contact_service.py tests/infra/test_period_partner_contact_service.py
git mv tests/infra/test_customer_centric.py tests/infra/test_partner_centric.py
```

- [ ] **Step 2: Update renamed test files** — all imports, class refs, fixture names, assertion values

- [ ] **Step 3: Update conftest.py** — `Customer` → `Partner` fixtures, `customer_code` → `partner_code` in test data

- [ ] **Step 4: Update all secondary test files**

For each test file: imports, fixture references, `customer_id` → `partner_id`, `customer_code` → `partner_code`, model class names.

Files: `test_code_generator.py`, `test_contract_service.py`, `test_startup.py`, `test_module_registration.py`, `test_module_isolation.py`, all `tests/infra/test_*.py`, all `tests/accounting/test_*.py`.

- [ ] **Step 5: Commit**

```bash
git add -A tests/
git commit -m "refactor(tests): Customer → Partner rename across all test files"
```

---

## Task 16: Documentation Update

**Files:**
- Modify: `docs/guidelines/accounting.md`, `backend.md`, `excel.md`, `infra.md`, `auth.md`
- Modify: `docs/DECISIONS.md`, `docs/KNOWN_ISSUES.md`, `docs/PROJECT_CONTEXT.md`, `docs/PROJECT_STRUCTURE.md`
- Modify: `CLAUDE.md` — domain term table (Customer → Partner)
- Modify: `README.md` — if customer-related paths/examples exist

**Note:** Past spec/plan docs under `docs/superpowers/specs/` and `docs/superpowers/plans/` are historical records — do NOT rename customer references in those files.

- [ ] **Step 1: Update CLAUDE.md domain terms**

```markdown
# Old:
| 거래처 (Customer) | 고객사, 공급사, 유지보수사, 통신사 등. 회계/인프라 모듈이 공유 |
| 거래처 담당자 (CustomerContact) | 거래처 소속 담당자 |
# New:
| 업체 (Partner) | 고객사, 수행사, 유지보수사, 통신사, 벤더 등. 회계/인프라 모듈이 공유 |
| 업체 담당자 (PartnerContact) | 업체 소속 담당자 |
```

- [ ] **Step 2: Update guideline docs** — model names, file paths, API endpoints, code examples

- [ ] **Step 3: Update PROJECT_STRUCTURE.md** — file paths

- [ ] **Step 4: Update DECISIONS.md** — add D-015 documenting the Customer→Partner rename decision

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md README.md docs/
git commit -m "docs: update Customer → Partner across guidelines and decisions"
```

---

## Task 17: Verify + Fix Import Chain

**Files:** All modified files

- [ ] **Step 1: Run Python import check**

```bash
python -c "from app.modules.common.models import Partner, PartnerContact, PartnerContactRole; print('common models OK')"
python -c "from app.modules.infra.models import PeriodPartner, PeriodPartnerContact; print('infra models OK')"
python -c "from app.core.code_generator import next_partner_code, next_business_code, RESERVED_PARTNER_CODE; print('code_generator OK')"
```

Expected: All print OK with no ImportError.

- [ ] **Step 2: Grep for remaining `customer` references that should have been renamed**

```bash
grep -rn --include="*.py" "customer" app/ | grep -v "__pycache__" | grep -v "alembic/" | grep -v "# customer" | grep -v "CUSTOMER"
```

Any hits (excluding comments, string enum values like `"CUSTOMER"`) indicate missed renames — fix them.

- [ ] **Step 3: Grep JS/HTML for stale refs**

```bash
grep -rn "customer" app/static/js/ app/templates/ | grep -v "고객"
```

API paths and variable names should all be `partner` now. Korean labels (고객사, 거래처) are intentionally kept.

- [ ] **Step 4: Fix any remaining issues found**

- [ ] **Step 5: Commit fixes if any**

```bash
git add -A
git commit -m "fix: resolve remaining customer → partner references"
```

---

## Task 18: Run Tests

- [ ] **Step 1: Run full test suite**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | head -100
```

Expected: All tests pass. If failures, fix import/rename issues.

- [ ] **Step 2: Fix test failures**

Common failure causes:
- Missed import rename
- Fixture name mismatch
- API endpoint path change in test assertions
- `customer_code` → `partner_code` in test data

- [ ] **Step 3: Commit test fixes if any**

```bash
git add -A
git commit -m "fix: resolve test failures from customer → partner rename"
```

---

## Task 19: Final Verification + Push

- [ ] **Step 1: Final grep audit**

```bash
# Should return 0 hits (excluding alembic migrations, docs/superpowers historical specs, enum values "CUSTOMER")
grep -rn --include="*.py" "\bcustomer_id\b\|\bcustomer_code\b\|\bCustomer\b\|\bcustomer_contact\b" app/ | grep -v __pycache__ | grep -v alembic/
```

- [ ] **Step 2: Verify server can start** (if DB available)

```bash
python -c "from app.core.app_factory import create_app; app = create_app(); print('App factory OK')"
```

- [ ] **Step 3: Push to remote**

```bash
git push origin feat/unified-business-model
```
