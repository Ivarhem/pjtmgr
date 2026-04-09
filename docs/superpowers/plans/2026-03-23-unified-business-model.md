# 사업/계약단위 통합 모델 구현 계획

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** Contract/ContractPeriod를 common 모듈로 이동하고, infra의 Project 테이블을 제거하여 사업/계약단위를 전 모듈 공통 기본정보로 통합한다.

**Architecture:** accounting의 Contract/ContractPeriod/ContractTypeConfig 모델을 common으로 이동한다. ContractPeriod의 영업 전용 필드(매출/검수/계산서)는 accounting의 새 ContractSalesDetail 1:1 확장 테이블로 분리한다. infra의 Project 테이블과 ProjectContractLink를 삭제하고, infra 하위 테이블(phase/deliverable/asset/customer)의 FK를 contract_period_id로 변경 + period_* 접두사로 리네이밍한다. 단일 Alembic 마이그레이션으로 원자적 실행한다.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (mapped_column), Alembic, PostgreSQL 16, Pydantic v2

**Spec:** `docs/superpowers/specs/2026-03-23-unified-business-model-design.md`

---

## Scope Check

이 스펙은 단일 통합 리팩토링이다. 하위 시스템(모델/서비스/라우터/프론트엔드)은 상호 의존적이므로 분리 불가. 단, **Phase별로 커밋**하여 각 Phase가 독립적으로 리뷰 가능하도록 한다.

> **주의:** Task 1~15(코드 변경)와 Task 16(Alembic 마이그레이션) 사이에는 ORM 모델과 DB 스키마가 불일치한다. Task 16까지 완료되기 전에는 앱을 기동하지 않는다.

---

## File Structure

### Phase 1: Common 모듈에 모델/스키마/서비스/라우터 생성

| Action | Path | 책임 |
|--------|------|------|
| Create | `app/modules/common/models/contract.py` | Contract ORM (accounting에서 이동, 검수/계산서 필드 제거) |
| Create | `app/modules/common/models/contract_period.py` | ContractPeriod ORM (영업 전용 필드 제거, description 추가) |
| Create | `app/modules/common/models/contract_type_config.py` | ContractTypeConfig ORM (그대로 이동) |
| Modify | `app/modules/common/models/__init__.py` | 3개 모델 import 추가, ProjectContractLink 제거 |
| Create | `app/modules/common/schemas/contract.py` | 공통 필드만 포함하는 Create/Update/Read |
| Create | `app/modules/common/schemas/contract_period.py` | 공통 필드만 포함하는 Create/Update/Read |
| Create | `app/modules/common/schemas/contract_type_config.py` | 이동 |
| Create | `app/modules/common/services/contract_service.py` | Contract/ContractPeriod 공통 CRUD |
| Create | `app/modules/common/services/contract_type_config.py` | 이동 |
| Create | `app/modules/common/routers/contracts.py` | 공통 Contract/Period CRUD 엔드포인트 |
| Create | `app/modules/common/routers/contract_types.py` | 이동 |
| Modify | `app/modules/common/routers/__init__.py` | 새 라우터 등록, project_contract_links 제거 |

### Phase 2: Accounting 모듈 ContractSalesDetail + 기존 코드 정리

| Action | Path | 책임 |
|--------|------|------|
| Create | `app/modules/accounting/models/contract_sales_detail.py` | 영업 확장 1:1 테이블 |
| Modify | `app/modules/accounting/models/__init__.py` | Contract/Period/TypeConfig import → common, SalesDetail 추가 |
| Create | `app/modules/accounting/schemas/contract_sales_detail.py` | SalesDetail Create/Update/Read |
| Modify | `app/modules/accounting/schemas/contract.py` | 공통 필드 제거, 영업 전용 스키마만 유지 (ContractPeriodListRead 등) |
| Create | `app/modules/accounting/services/contract_sales_detail.py` | SalesDetail CRUD + lazy-create |
| Modify | `app/modules/accounting/services/contract.py` | common 서비스 import로 전환, 영업 전용 로직만 유지 |
| Create | `app/modules/accounting/routers/contract_sales_details.py` | SalesDetail API |
| Modify | `app/modules/accounting/routers/contracts.py` | 공통 CRUD 제거, 영업 전용만 유지 (ledger, my-contracts 등) |
| Modify | `app/modules/accounting/routers/__init__.py` | contract_types 제거, sales_details 추가 |
| Delete | `app/modules/accounting/models/contract.py` | common으로 이동 완료 |
| Delete | `app/modules/accounting/models/contract_period.py` | common으로 이동 완료 |
| Delete | `app/modules/accounting/models/contract_type_config.py` | common으로 이동 완료 |
| Delete | `app/modules/accounting/schemas/contract_type_config.py` | common으로 이동 완료 |
| Delete | `app/modules/accounting/routers/contract_types.py` | common으로 이동 완료 |

### Phase 3: Infra 모듈 FK 변경 + 리네이밍

| Action | Path | 책임 |
|--------|------|------|
| Create | `app/modules/infra/models/period_phase.py` | ProjectPhase → PeriodPhase, FK: contract_period_id |
| Create | `app/modules/infra/models/period_deliverable.py` | ProjectDeliverable → PeriodDeliverable, FK: period_phase_id→period_phases.id |
| Create | `app/modules/infra/models/period_asset.py` | ProjectAsset → PeriodAsset, FK: contract_period_id |
| Create | `app/modules/infra/models/period_customer.py` | ProjectCustomer → PeriodCustomer, FK: contract_period_id |
| Create | `app/modules/infra/models/period_customer_contact.py` | ProjectCustomerContact → PeriodCustomerContact, FK: period_customer_id |
| Delete | `app/modules/infra/models/project.py` | Project 삭제 |
| Delete | `app/modules/infra/models/project_phase.py` | → period_phase.py |
| Delete | `app/modules/infra/models/project_deliverable.py` | → period_deliverable.py |
| Delete | `app/modules/infra/models/project_asset.py` | → period_asset.py |
| Delete | `app/modules/infra/models/project_customer.py` | → period_customer.py |
| Delete | `app/modules/infra/models/project_customer_contact.py` | → period_customer_contact.py |
| Modify | `app/modules/infra/models/__init__.py` | 리네이밍된 모델 import 갱신 |
| Modify | `app/modules/infra/schemas/` | 모든 project 참조 → period 참조로 변경 |
| Modify | `app/modules/infra/services/` | 모든 서비스 FK/model 참조 변경 |
| Modify | `app/modules/infra/routers/` | 모든 라우터 엔드포인트/import 변경 |

### Phase 4: Alembic 마이그레이션

| Action | Path | 책임 |
|--------|------|------|
| Create | `alembic/versions/0010_unified_business_model.py` | 원자적 마이그레이션 |

### Phase 5: 공유 인프라 코드 수정

| Action | Path | 책임 |
|--------|------|------|
| Modify | `app/core/auth/authorization.py` | Contract/Period import 경로 → common |
| Modify | `app/core/startup/bootstrap.py` | seed_contract_types import 경로 변경 |
| Delete | `app/modules/common/models/project_contract_link.py` | 모델 삭제 |
| Delete | `app/modules/common/services/project_contract_link.py` | 서비스 삭제 |
| Delete | `app/modules/common/schemas/project_contract_link.py` | 스키마 삭제 |
| Delete | `app/modules/common/routers/project_contract_links.py` | 라우터 삭제 |

### Phase 6: 프론트엔드 수정

| Action | Path | 책임 |
|--------|------|------|
| Modify | `app/static/js/utils.js` | localStorage 키 변경, ctx 셀렉터 API |
| Modify | `app/static/js/infra_projects.js` | project → period API 호출 변경 |
| Modify | `app/static/js/infra_project_detail.js` | project → period 기반 변경 |
| Modify | `app/static/js/contract_detail.js` | sales-detail API 분리 호출 |
| Modify | `app/modules/infra/templates/infra_projects.html` | 사업명 (Y26) 표시 형식 |
| Modify | `app/modules/infra/templates/infra_project_detail.html` | period 기반 상세 뷰 |

### Phase 7: 테스트

| Action | Path | 책임 |
|--------|------|------|
| Create | `tests/common/test_contract_service.py` | common Contract/Period CRUD 테스트 |
| Create | `tests/accounting/test_contract_sales_detail.py` | SalesDetail CRUD + lazy-create 테스트 |
| Modify | `tests/accounting/test_contract_service.py` | import 경로 변경, 영업 전용 테스트 유지 |
| Modify | `tests/infra/test_customer_centric.py` | project → period 참조 변경 |
| Delete | `tests/common/test_project_contract_link.py` | 삭제 |

---

## Task 1: Common Contract 모델 생성

**Files:**
- Create: `app/modules/common/models/contract.py`
- Test: `tests/common/test_contract_service.py`

- [ ] **Step 1: Contract 모델 파일 생성**

accounting 버전에서 검수/계산서 필드를 제거한 공통 모델을 생성한다.

```python
# app/modules/common/models/contract.py
"""사업 (Contract) - 하나의 사업/프로젝트 본체. 공통 기본정보."""
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_code: Mapped[str | None] = mapped_column(String(50), unique=True)
    contract_name: Mapped[str] = mapped_column(String(300), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    end_customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(30), default="active", index=True)
    notes: Mapped[str | None] = mapped_column(String(500))

    end_customer: Mapped["Customer | None"] = relationship(back_populates="contracts")
    owner: Mapped["User | None"] = relationship(back_populates="contracts")
    periods: Mapped[list["ContractPeriod"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan", order_by="ContractPeriod.period_year"
    )
    transaction_lines: Mapped[list["TransactionLine"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )
    receipts: Mapped[list["Receipt"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/common/models/contract.py
git commit -m "feat(common): add Contract model (moved from accounting, no inspection/invoice fields)"
```

---

## Task 2: Common ContractPeriod 모델 생성

**Files:**
- Create: `app/modules/common/models/contract_period.py`

- [ ] **Step 1: ContractPeriod 모델 파일 생성**

영업 전용 필드(expected_revenue_total, expected_gp_total, inspection_*, invoice_*)를 제거하고, description을 추가한다.

```python
# app/modules/common/models/contract_period.py
"""사업 기간 (ContractPeriod) - 계약 주기 단위 (Y25, Y26 등). 공통 기본정보."""
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class ContractPeriod(TimestampMixin, Base):
    __tablename__ = "contract_periods"
    __table_args__ = (UniqueConstraint("contract_id", "period_year", name="uq_contract_period"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_label: Mapped[str] = mapped_column(String(20), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    start_month: Mapped[str | None] = mapped_column(String(10), index=True)
    end_month: Mapped[str | None] = mapped_column(String(10), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"))
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_planned: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(String(500))

    contract: Mapped["Contract"] = relationship(back_populates="periods")
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_user_id])
    customer: Mapped["Customer | None"] = relationship(foreign_keys=[customer_id])
    # Note: forecasts, contract_contacts relationships는 accounting 모델 측에서
    # backref로 정의한다 (common → accounting 역방향 의존 방지).
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/common/models/contract_period.py
git commit -m "feat(common): add ContractPeriod model (moved from accounting, sales fields removed, description added)"
```

---

## Task 3: Common ContractTypeConfig 모델 이동

**Files:**
- Create: `app/modules/common/models/contract_type_config.py`

- [ ] **Step 1: ContractTypeConfig 모델 복사**

기존 `app/modules/accounting/models/contract_type_config.py` 내용을 그대로 `app/modules/common/models/contract_type_config.py`에 복사한다. 변경 없음.

- [ ] **Step 2: Commit**

```bash
git add app/modules/common/models/contract_type_config.py
git commit -m "feat(common): add ContractTypeConfig model (moved from accounting)"
```

---

## Task 4: Common 모델 __init__.py 갱신

**Files:**
- Modify: `app/modules/common/models/__init__.py`

- [ ] **Step 1: import 추가 및 ProjectContractLink 제거**

```python
# 추가:
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.contract_type_config import ContractTypeConfig

# 제거:
# from app.modules.common.models.project_contract_link import ProjectContractLink

# __all__에서 "ProjectContractLink" 제거, "Contract", "ContractPeriod", "ContractTypeConfig" 추가
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/common/models/__init__.py
git commit -m "refactor(common): register Contract/Period/TypeConfig models, remove ProjectContractLink"
```

---

## Task 5: Common Contract/Period 스키마 생성

**Files:**
- Create: `app/modules/common/schemas/contract.py`
- Create: `app/modules/common/schemas/contract_period.py`
- Create: `app/modules/common/schemas/contract_type_config.py`

- [ ] **Step 1: common Contract 스키마 작성**

공통 필드만 포함. 검수/계산서 필드는 **포함하지 않는다.**

```python
# app/modules/common/schemas/contract.py
from typing import Literal

from pydantic import BaseModel

ContractStatus = Literal["active", "closed", "cancelled"]


class ContractCreate(BaseModel):
    contract_name: str
    contract_type: str
    end_customer_id: int | None = None
    owner_user_id: int | None = None
    status: ContractStatus = "active"
    notes: str | None = None


class ContractUpdate(BaseModel):
    contract_name: str | None = None
    contract_type: str | None = None
    contract_code: str | None = None
    end_customer_id: int | None = None
    owner_user_id: int | None = None
    status: ContractStatus | None = None
    notes: str | None = None


class ContractRead(BaseModel):
    id: int
    contract_code: str | None
    contract_name: str
    contract_type: str
    end_customer_id: int | None
    end_customer_name: str | None = None
    owner_user_id: int | None
    owner_name: str | None = None
    status: str
    notes: str | None = None

    model_config = {"from_attributes": True}


class BulkAssignOwnerRequest(BaseModel):
    contract_ids: list[int]
    owner_user_id: int | None = None
```

- [ ] **Step 2: common ContractPeriod 스키마 작성**

공통 필드만. `description` 추가, 영업 전용 필드 제외.

```python
# app/modules/common/schemas/contract_period.py
from typing import Literal

from pydantic import BaseModel, field_validator

from app.core._normalize import normalize_month

Stage = Literal["10%", "50%", "70%", "90%", "계약완료", "실주"]


class ContractPeriodCreate(BaseModel):
    period_year: int
    period_label: str | None = None
    stage: Stage = "50%"
    start_month: str | None = None
    end_month: str | None = None
    description: str | None = None
    owner_user_id: int | None = None
    customer_id: int | None = None
    is_planned: bool = True
    notes: str | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v


class ContractPeriodUpdate(BaseModel):
    period_label: str | None = None
    stage: Stage | None = None
    is_planned: bool | None = None
    start_month: str | None = None
    end_month: str | None = None
    description: str | None = None
    owner_user_id: int | None = None
    customer_id: int | None = None
    is_completed: bool | None = None
    notes: str | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def validate_month_fields(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_month(v)
        return v


class ContractPeriodRead(BaseModel):
    id: int
    contract_id: int
    period_year: int
    period_label: str
    stage: str
    start_month: str | None = None
    end_month: str | None = None
    description: str | None = None
    owner_user_id: int | None = None
    owner_name: str | None = None
    customer_id: int | None = None
    customer_name: str | None = None
    is_completed: bool = False
    is_planned: bool = True
    notes: str | None = None

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: common ContractTypeConfig 스키마 복사**

기존 `app/modules/accounting/schemas/contract_type_config.py`를 `app/modules/common/schemas/contract_type_config.py`로 그대로 복사.

- [ ] **Step 4: Commit**

```bash
git add app/modules/common/schemas/contract.py app/modules/common/schemas/contract_period.py app/modules/common/schemas/contract_type_config.py
git commit -m "feat(common): add Contract/Period/TypeConfig schemas (common fields only)"
```

---

## Task 6: Common Contract 서비스 생성

**Files:**
- Create: `app/modules/common/services/contract_service.py`
- Create: `app/modules/common/services/contract_type_config.py`

- [ ] **Step 1: common contract_service.py 작성**

기존 `accounting/services/contract.py`에서 **공통 CRUD만** 추출한다. 영업 전용 로직(`list_periods_flat`, `list_periods_for_template`, `_period_list_dict` 등)은 accounting에 잔류.

주요 함수:
- `get_contract()`, `create_contract()`, `update_contract()`, `delete_contract()`, `restore_contract()`
- `list_periods()` — **customer_id 필터 지원** (인프라에서 `GET /api/v1/contract-periods?customer_id=X`용)
- `get_contract_periods()`, `get_period()`, `create_period()`, `update_period()`, `delete_period()`
- `bulk_assign_owner()`
- 헬퍼: `_period_label()`, `_contract_read_dict()`, `_period_read_dict()`

`list_periods()`는 `customer_id` 파라미터를 받아 Contract.end_customer_id 또는 ContractPeriod.customer_id로 필터링한다. 인프라 프로젝트 목록과 ctx 셀렉터에서 사용.

변경점:
1. import 경로: `app.modules.common.models.contract`, `app.modules.common.schemas.contract`
2. `create_contract()`: 검수/계산서 기본값 적용 로직 제거 (ContractTypeConfig의 default_inspection_* 등은 sales-detail 생성 시 accounting 서비스에서 적용)
3. `_contract_read_dict()`: 검수/계산서 필드 제거
4. `create_period()`: 검수/계산서 필드 상속 로직 제거 (공통 필드: owner_user_id, customer_id만 상속)
5. `_period_read_dict()`: 검수/계산서 필드 제거, description 추가

- [ ] **Step 2: common contract_type_config.py 이동**

기존 `accounting/services/contract_type_config.py`를 `common/services/contract_type_config.py`로 복사. import 경로만 변경:
- `app.modules.accounting.models.contract_type_config` → `app.modules.common.models.contract_type_config`

- [ ] **Step 3: Commit**

```bash
git add app/modules/common/services/contract_service.py app/modules/common/services/contract_type_config.py
git commit -m "feat(common): add Contract/Period/TypeConfig services (common CRUD)"
```

---

## Task 7: Common Contract/TypeConfig 라우터 생성

**Files:**
- Create: `app/modules/common/routers/contracts.py`
- Create: `app/modules/common/routers/contract_types.py`
- Modify: `app/modules/common/routers/__init__.py`

- [ ] **Step 1: common contracts.py 라우터 작성**

공통 CRUD만 포함. 영업 전용(ledger, my-contracts)은 accounting에 잔류.
**권한:** Contract CRUD는 모듈 무관 공통 자원이므로 `get_current_user`만 요구. 생성/수정/삭제는 기존과 동일하게 admin 또는 accounting/infra full 중 하나 필요. 이 부분은 서비스 레이어에서 판단.

```
GET    /api/v1/contracts/{id}
POST   /api/v1/contracts
PATCH  /api/v1/contracts/{id}
DELETE /api/v1/contracts/{id}
POST   /api/v1/contracts/{id}/restore
POST   /api/v1/contracts/bulk-assign-owner
GET    /api/v1/contracts/{id}/periods
POST   /api/v1/contracts/{id}/periods
GET    /api/v1/contract-periods              ← 신규: customer_id 쿼리 파라미터 지원 (인프라용)
GET    /api/v1/contract-periods/{id}
PATCH  /api/v1/contract-periods/{id}
DELETE /api/v1/contract-periods/{id}
```

`GET /api/v1/contract-periods?customer_id=X` 엔드포인트는 `list_periods(customer_id=X)`를 호출한다. 응답에는 contract_name, period_label을 포함하여 프론트엔드에서 `사업명 (Y26)` 형식으로 표시할 수 있도록 한다.

- [ ] **Step 2: common contract_types.py 라우터 이동**

기존 `accounting/routers/contract_types.py`를 복사 후 import 경로 변경.

- [ ] **Step 3: common routers/__init__.py 갱신**

```python
# 추가:
from app.modules.common.routers.contracts import router as contracts_router
from app.modules.common.routers.contract_types import router as contract_types_router
api_router.include_router(contracts_router)
api_router.include_router(contract_types_router)

# 제거:
# project_contract_links_router 관련 전체
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/common/routers/contracts.py app/modules/common/routers/contract_types.py app/modules/common/routers/__init__.py
git commit -m "feat(common): add Contract/Period/TypeConfig routers"
```

---

## Task 8: Accounting ContractSalesDetail 모델 생성

**Files:**
- Create: `app/modules/accounting/models/contract_sales_detail.py`

- [ ] **Step 1: ContractSalesDetail 모델 작성**

```python
# app/modules/accounting/models/contract_sales_detail.py
"""영업 확장 정보 (ContractSalesDetail) - ContractPeriod 1:1 영업 전용 필드."""
import datetime
from sqlalchemy import String, Integer, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.core.base_model import TimestampMixin


class ContractSalesDetail(TimestampMixin, Base):
    __tablename__ = "contract_sales_details"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_period_id: Mapped[int] = mapped_column(
        ForeignKey("contract_periods.id"), unique=True, nullable=False
    )
    expected_revenue_amount: Mapped[int] = mapped_column(Integer, default=0)
    expected_gp_amount: Mapped[int] = mapped_column(Integer, default=0)
    inspection_day: Mapped[int | None] = mapped_column(Integer)
    inspection_date: Mapped[datetime.date | None] = mapped_column(Date)
    invoice_month_offset: Mapped[int | None] = mapped_column(Integer)
    invoice_day_type: Mapped[str | None] = mapped_column(String(20))
    invoice_day: Mapped[int | None] = mapped_column(Integer)
    invoice_holiday_adjust: Mapped[str | None] = mapped_column(String(10))

    contract_period: Mapped["ContractPeriod"] = relationship()
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/accounting/models/contract_sales_detail.py
git commit -m "feat(accounting): add ContractSalesDetail model (1:1 sales extension)"
```

---

## Task 9: Accounting ContractSalesDetail 스키마/서비스/라우터

**Files:**
- Create: `app/modules/accounting/schemas/contract_sales_detail.py`
- Create: `app/modules/accounting/services/contract_sales_detail.py`
- Create: `app/modules/accounting/routers/contract_sales_details.py`

- [ ] **Step 1: SalesDetail 스키마 작성**

```python
# app/modules/accounting/schemas/contract_sales_detail.py
from pydantic import BaseModel, field_validator
from app.core._normalize import normalize_date


class ContractSalesDetailRead(BaseModel):
    id: int
    contract_period_id: int
    expected_revenue_amount: int = 0
    expected_gp_amount: int = 0
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None

    model_config = {"from_attributes": True}


class ContractSalesDetailUpdate(BaseModel):
    expected_revenue_amount: int | None = None
    expected_gp_amount: int | None = None
    inspection_day: int | None = None
    inspection_date: str | None = None
    invoice_month_offset: int | None = None
    invoice_day_type: str | None = None
    invoice_day: int | None = None
    invoice_holiday_adjust: str | None = None

    @field_validator("inspection_date")
    @classmethod
    def validate_inspection_date(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_date(v)
        return v
```

- [ ] **Step 2: SalesDetail 서비스 작성**

핵심 로직: `get_or_create_sales_detail()` — 조회 시 미존재하면 기본값으로 자동 생성 (lazy-create).

```python
# app/modules/accounting/services/contract_sales_detail.py
from __future__ import annotations
import datetime
from typing import TYPE_CHECKING
from sqlalchemy.orm import Session
from app.core.auth.authorization import check_period_access
from app.core.exceptions import NotFoundError
from app.modules.accounting.models.contract_sales_detail import ContractSalesDetail
from app.modules.accounting.schemas.contract_sales_detail import ContractSalesDetailUpdate

if TYPE_CHECKING:
    from app.modules.common.models.user import User


def get_or_create_sales_detail(
    db: Session, period_id: int, *, current_user: User | None = None
) -> dict:
    """SalesDetail 조회. 미존재 시 기본값으로 자동 생성."""
    if current_user:
        check_period_access(db, period_id, current_user)

    detail = db.query(ContractSalesDetail).filter(
        ContractSalesDetail.contract_period_id == period_id
    ).first()

    if not detail:
        detail = ContractSalesDetail(contract_period_id=period_id)
        db.add(detail)
        db.commit()
        db.refresh(detail)

    return _to_dict(detail)


def update_sales_detail(
    db: Session, period_id: int, data: ContractSalesDetailUpdate,
    *, current_user: User | None = None
) -> dict:
    if current_user:
        check_period_access(db, period_id, current_user)

    detail = db.query(ContractSalesDetail).filter(
        ContractSalesDetail.contract_period_id == period_id
    ).first()

    if not detail:
        detail = ContractSalesDetail(contract_period_id=period_id)
        db.add(detail)
        db.flush()

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "inspection_date" and isinstance(value, str):
            value = datetime.date.fromisoformat(value)
        setattr(detail, field, value)

    db.commit()
    db.refresh(detail)
    return _to_dict(detail)


def _to_dict(detail: ContractSalesDetail) -> dict:
    return {
        "id": detail.id,
        "contract_period_id": detail.contract_period_id,
        "expected_revenue_amount": detail.expected_revenue_amount,
        "expected_gp_amount": detail.expected_gp_amount,
        "inspection_day": detail.inspection_day,
        "inspection_date": str(detail.inspection_date) if detail.inspection_date else None,
        "invoice_month_offset": detail.invoice_month_offset,
        "invoice_day_type": detail.invoice_day_type,
        "invoice_day": detail.invoice_day,
        "invoice_holiday_adjust": detail.invoice_holiday_adjust,
    }
```

- [ ] **Step 3: SalesDetail 라우터 작성**

```python
# app/modules/accounting/routers/contract_sales_details.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth.dependencies import get_current_user, require_module_access
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.accounting.schemas.contract_sales_detail import (
    ContractSalesDetailRead,
    ContractSalesDetailUpdate,
)
from app.modules.accounting.services import contract_sales_detail as svc

router = APIRouter(prefix="/api/v1/contract-periods", tags=["contract-sales-details"])


@router.get("/{period_id}/sales-detail", response_model=ContractSalesDetailRead)
def get_sales_detail(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractSalesDetailRead:
    return svc.get_or_create_sales_detail(db, period_id, current_user=current_user)


@router.patch(
    "/{period_id}/sales-detail",
    response_model=ContractSalesDetailRead,
    dependencies=[require_module_access("accounting", "full")],
)
def update_sales_detail(
    period_id: int,
    data: ContractSalesDetailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ContractSalesDetailRead:
    return svc.update_sales_detail(db, period_id, data, current_user=current_user)
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/accounting/schemas/contract_sales_detail.py app/modules/accounting/services/contract_sales_detail.py app/modules/accounting/routers/contract_sales_details.py
git commit -m "feat(accounting): add ContractSalesDetail schema/service/router with lazy-create"
```

---

## Task 10: Accounting 모듈 기존 코드 정리

**Files:**
- Modify: `app/modules/accounting/models/__init__.py`
- Modify: `app/modules/accounting/schemas/contract.py`
- Modify: `app/modules/accounting/services/contract.py`
- Modify: `app/modules/accounting/routers/contracts.py`
- Modify: `app/modules/accounting/routers/__init__.py`
- Delete: `app/modules/accounting/models/contract.py`
- Delete: `app/modules/accounting/models/contract_period.py`
- Delete: `app/modules/accounting/models/contract_type_config.py`
- Delete: `app/modules/accounting/schemas/contract_type_config.py`
- Delete: `app/modules/accounting/routers/contract_types.py`

- [ ] **Step 1: accounting models/__init__.py 수정**

```python
# Contract, ContractPeriod, ContractTypeConfig import를 common에서 re-import
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.contract_type_config import ContractTypeConfig
from app.modules.accounting.models.contract_sales_detail import ContractSalesDetail
from app.modules.accounting.models.contract_contact import ContractContact
# ... 나머지 기존 import 유지

# __all__에 ContractSalesDetail 추가
```

- [ ] **Step 2: accounting schemas/contract.py 수정**

공통 스키마(ContractCreate, ContractUpdate, ContractRead, ContractPeriodCreate, ContractPeriodUpdate, ContractPeriodRead)를 제거하고 common에서 re-export. **영업 전용만 유지:**
- `ContractPeriodListRead` (원장 목록용: 사업+기간+영업정보 조인)
- Stage, VALID_STAGES, InvoiceDayType 등 상수

`ContractPeriodListRead`에서 `expected_revenue_total`/`expected_gp_total` → `expected_revenue_amount`/`expected_gp_amount`로 필드명 변경 (sales-detail 조인 결과 반영).

- [ ] **Step 3: accounting services/contract.py 수정**

- import 경로: `app.modules.common.models.contract`, `app.modules.common.schemas.contract`
- 공통 CRUD 함수 제거 (common 서비스로 이동됨)
- **잔류 함수:** `list_periods_flat()`, `list_periods_for_template()`, `_period_list_dict()`
- `_period_list_dict()`에서 `expected_revenue_total`/`expected_gp_total` → ContractSalesDetail 조인으로 변경
- `list_periods_flat()`에서 ContractSalesDetail 조인 추가

- [ ] **Step 4: accounting routers/contracts.py 수정**

공통 CRUD 엔드포인트 제거. **잔류:**
- `GET /api/v1/contract-periods` (원장 목록 - 영업 전용 필터/데이터)
- `GET /api/v1/contracts/{id}/ledger`
- `GET /api/v1/my-contracts/summary`

- [ ] **Step 5: accounting routers/__init__.py 수정**

- `contract_types_router` 제거 (common으로 이동)
- `contract_sales_details_router` 추가

```python
from app.modules.accounting.routers.contract_sales_details import router as contract_sales_details_router
# ...
api_router.include_router(contract_sales_details_router)
# contract_types_router 관련 줄 삭제
```

- [ ] **Step 6: 이전 accounting 모델/스키마/라우터 파일 삭제**

```bash
rm app/modules/accounting/models/contract.py
rm app/modules/accounting/models/contract_period.py
rm app/modules/accounting/models/contract_type_config.py
rm app/modules/accounting/schemas/contract_type_config.py
rm app/modules/accounting/routers/contract_types.py
```

- [ ] **Step 7: Commit**

```bash
git add -A app/modules/accounting/
git commit -m "refactor(accounting): move Contract/Period/TypeConfig to common, add SalesDetail integration"
```

---

## Task 11: Infra 모델 리네이밍 + FK 변경

**Files:**
- Create: `app/modules/infra/models/period_phase.py`
- Create: `app/modules/infra/models/period_deliverable.py`
- Create: `app/modules/infra/models/period_asset.py`
- Create: `app/modules/infra/models/period_customer.py`
- Create: `app/modules/infra/models/period_customer_contact.py`
- Delete: `app/modules/infra/models/project.py` 외 5개
- Modify: `app/modules/infra/models/__init__.py`

- [ ] **Step 1: PeriodPhase 모델 작성**

```python
# app/modules/infra/models/period_phase.py
from __future__ import annotations
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.base_model import TimestampMixin


class PeriodPhase(TimestampMixin, Base):
    __tablename__ = "period_phases"

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_period_id: Mapped[int] = mapped_column(ForeignKey("contract_periods.id"), index=True)
    phase_type: Mapped[str] = mapped_column(String(30))
    task_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    deliverables_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cautions: Mapped[str | None] = mapped_column(Text, nullable=True)
    submission_required: Mapped[bool] = mapped_column(default=False)
    submission_status: Mapped[str] = mapped_column(String(30), default="pending")
    status: Mapped[str] = mapped_column(String(30), default="not_started")
```

- [ ] **Step 2: PeriodDeliverable 모델 작성**

```python
# app/modules/infra/models/period_deliverable.py
from __future__ import annotations
from datetime import date
from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.core.base_model import TimestampMixin


class PeriodDeliverable(TimestampMixin, Base):
    __tablename__ = "period_deliverables"

    id: Mapped[int] = mapped_column(primary_key=True)
    period_phase_id: Mapped[int] = mapped_column(ForeignKey("period_phases.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
```

- [ ] **Step 3: PeriodAsset 모델 작성**

```python
# app/modules/infra/models/period_asset.py
from __future__ import annotations
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import TimestampMixin
from app.core.database import Base


class PeriodAsset(TimestampMixin, Base):
    __tablename__ = "period_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contract_periods.id"), nullable=False, index=True
    )
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), nullable=False, index=True
    )
    role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("contract_period_id", "asset_id"),)
```

- [ ] **Step 4: PeriodCustomer 모델 작성**

```python
# app/modules/infra/models/period_customer.py
from __future__ import annotations
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import TimestampMixin
from app.core.database import Base


class PeriodCustomer(TimestampMixin, Base):
    __tablename__ = "period_customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contract_periods.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("contract_period_id", "customer_id", "role"),)
```

- [ ] **Step 5: PeriodCustomerContact 모델 작성**

```python
# app/modules/infra/models/period_customer_contact.py
from __future__ import annotations
from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.base_model import TimestampMixin
from app.core.database import Base


class PeriodCustomerContact(TimestampMixin, Base):
    __tablename__ = "period_customer_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    period_customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("period_customers.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_contacts.id"), nullable=False, index=True
    )
    project_role: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("period_customer_id", "contact_id", "project_role"),
    )
```

- [ ] **Step 6: infra models/__init__.py 수정**

```python
# 제거:
# from app.modules.infra.models.project import Project
# from app.modules.infra.models.project_phase import ProjectPhase
# from app.modules.infra.models.project_deliverable import ProjectDeliverable
# from app.modules.infra.models.project_asset import ProjectAsset
# from app.modules.infra.models.project_customer import ProjectCustomer
# from app.modules.infra.models.project_customer_contact import ProjectCustomerContact

# 추가:
from app.modules.infra.models.period_phase import PeriodPhase
from app.modules.infra.models.period_deliverable import PeriodDeliverable
from app.modules.infra.models.period_asset import PeriodAsset
from app.modules.infra.models.period_customer import PeriodCustomer
from app.modules.infra.models.period_customer_contact import PeriodCustomerContact

# __all__ 갱신
```

- [ ] **Step 7: 이전 project 모델 파일 삭제**

```bash
rm app/modules/infra/models/project.py
rm app/modules/infra/models/project_phase.py
rm app/modules/infra/models/project_deliverable.py
rm app/modules/infra/models/project_asset.py
rm app/modules/infra/models/project_customer.py
rm app/modules/infra/models/project_customer_contact.py
```

- [ ] **Step 8: Commit**

```bash
git add -A app/modules/infra/models/
git commit -m "refactor(infra): rename project_* models to period_*, FK → contract_period_id"
```

---

## Task 12: Infra 스키마 갱신

**Files:**
- Modify: `app/modules/infra/schemas/project.py` → 삭제
- Create/Modify: 각 period_* 스키마 파일

- [ ] **Step 1: project.py 스키마 삭제**

이 파일은 더 이상 필요 없다. 인프라에서 "프로젝트 목록"은 common의 ContractPeriod API로 대체.

```bash
rm app/modules/infra/schemas/project.py
```

- [ ] **Step 2: 나머지 infra 스키마에서 project_id → contract_period_id 변경**

영향받는 스키마 파일 목록을 grep으로 확인 후 모두 수정:
- `project_id` → `contract_period_id`
- `ProjectPhase*` → `PeriodPhase*`
- `ProjectAsset*` → `PeriodAsset*`
- `ProjectCustomer*` → `PeriodCustomer*`
- `ProjectDeliverable*` → `PeriodDeliverable*`

Run: `grep -rl "project_id\|ProjectPhase\|ProjectAsset\|ProjectCustomer\|ProjectDeliverable" app/modules/infra/schemas/`

- [ ] **Step 3: Commit**

```bash
git add -A app/modules/infra/schemas/
git commit -m "refactor(infra): update schemas project_* → period_*"
```

---

## Task 13: Infra 서비스 갱신

**Files:**
- Delete: `app/modules/infra/services/project_service.py`
- Modify: `app/modules/infra/services/phase_service.py`
- Modify: `app/modules/infra/services/project_asset_service.py` → `period_asset_service.py`
- Modify: `app/modules/infra/services/project_customer_service.py` → `period_customer_service.py`
- Modify: `app/modules/infra/services/project_customer_contact_service.py` → `period_customer_contact_service.py`
- Modify: `app/modules/infra/services/infra_exporter.py`
- Modify: `app/modules/infra/services/infra_metrics.py`
- Modify: `app/modules/infra/services/network_service.py`
- Modify: `app/modules/infra/services/asset_service.py`
- Modify: `app/modules/infra/services/policy_service.py`
- Modify: `app/modules/infra/services/_helpers.py`

- [ ] **Step 1: project_service.py 삭제**

인프라에서 프로젝트 CRUD는 common의 ContractPeriod CRUD로 대체.

- [ ] **Step 2: 서비스 파일 리네이밍**

```bash
mv app/modules/infra/services/project_asset_service.py app/modules/infra/services/period_asset_service.py
mv app/modules/infra/services/project_customer_service.py app/modules/infra/services/period_customer_service.py
mv app/modules/infra/services/project_customer_contact_service.py app/modules/infra/services/period_customer_contact_service.py
```

- [ ] **Step 3: 리네이밍된 서비스 내부 수정**

각 파일에서:
- `project_id` → `contract_period_id`
- `Project` → `ContractPeriod` (또는 common에서 import)
- `ProjectAsset` → `PeriodAsset`
- `ProjectCustomer` → `PeriodCustomer`
- `ProjectCustomerContact` → `PeriodCustomerContact`
- `ProjectPhase` → `PeriodPhase`
- `ProjectDeliverable` → `PeriodDeliverable`
- import 경로 갱신

- [ ] **Step 4: phase_service.py 수정**

- `project_id` → `contract_period_id`
- `ProjectPhase` → `PeriodPhase`
- `ProjectDeliverable` → `PeriodDeliverable`

- [ ] **Step 5: infra_exporter.py 수정**

- `project_id` 파라미터 → `period_id`
- `ProjectAsset` → `PeriodAsset`
- import 경로 변경

- [ ] **Step 6: infra_metrics.py 수정**

- `Project` → `ContractPeriod` (from common)
- `project_id` → `contract_period_id`
- `ProjectAsset` → `PeriodAsset`
- `ProjectPhase` → `PeriodPhase`
- `ProjectDeliverable` → `PeriodDeliverable`
- `get_project_summary()` → `get_period_summary()`
- `list_projects_summary()` → `list_periods_summary()`
- 감사 로그 entity_type: `"project"` → `"contract_period"`

- [ ] **Step 7: 나머지 서비스 파일 수정**

`asset_service.py`, `network_service.py`, `policy_service.py`, `_helpers.py`에서 project 참조 검색 후 수정.

- [ ] **Step 8: Commit**

```bash
git add -A app/modules/infra/services/
git commit -m "refactor(infra): rename project services to period, update all FK references"
```

---

## Task 14: Infra 라우터 갱신

**Files:**
- Delete: `app/modules/infra/routers/projects.py`
- Rename: `project_phases.py` → `period_phases.py`
- Rename: `project_deliverables.py` → `period_deliverables.py`
- Rename: `project_assets.py` → `period_assets.py`
- Rename: `project_customers.py` → `period_customers.py`
- Rename: `project_customer_contacts.py` → `period_customer_contacts.py`
- Modify: `app/modules/infra/routers/__init__.py`

- [ ] **Step 1: projects.py 라우터 삭제**

```bash
rm app/modules/infra/routers/projects.py
```

- [ ] **Step 2: 라우터 파일 리네이밍 + 내용 수정**

각 파일:
- URL prefix 변경: `/api/v1/projects/{id}/phases` → `/api/v1/period-phases` 등
- import 경로 변경
- `project_id` 파라미터 → `contract_period_id`

```bash
mv app/modules/infra/routers/project_phases.py app/modules/infra/routers/period_phases.py
mv app/modules/infra/routers/project_deliverables.py app/modules/infra/routers/period_deliverables.py
mv app/modules/infra/routers/project_assets.py app/modules/infra/routers/period_assets.py
mv app/modules/infra/routers/project_customers.py app/modules/infra/routers/period_customers.py
mv app/modules/infra/routers/project_customer_contacts.py app/modules/infra/routers/period_customer_contacts.py
```

- [ ] **Step 3: infra routers/__init__.py 수정**

```python
# 제거:
# from app.modules.infra.routers.projects import router as projects_router
# from app.modules.infra.routers.project_phases import router as project_phases_router
# ... 기타 project_* router imports

# 추가:
from app.modules.infra.routers.period_phases import router as period_phases_router
from app.modules.infra.routers.period_deliverables import router as period_deliverables_router
from app.modules.infra.routers.period_assets import router as period_assets_router
from app.modules.infra.routers.period_customers import router as period_customers_router
from app.modules.infra.routers.period_customer_contacts import router as period_customer_contacts_router

# api_router.include_router도 갱신
```

- [ ] **Step 4: Commit**

```bash
git add -A app/modules/infra/routers/
git commit -m "refactor(infra): rename project routers to period, update endpoints"
```

---

## Task 15: 공유 인프라 코드 수정

**Files:**
- Modify: `app/core/auth/authorization.py`
- Modify: `app/core/startup/bootstrap.py`
- Delete: `app/modules/common/models/project_contract_link.py`
- Delete: `app/modules/common/services/project_contract_link.py`
- Delete: `app/modules/common/schemas/project_contract_link.py`
- Delete: `app/modules/common/routers/project_contract_links.py`

- [ ] **Step 1: authorization.py import 경로 수정**

```python
# 변경 전:
#   from app.modules.accounting.models.contract import Contract
#   from app.modules.accounting.models.contract_period import ContractPeriod

# 변경 후:
from app.modules.common.models.contract import Contract
from app.modules.common.models.contract_period import ContractPeriod
```

이 변경은 `_contract_visibility_clause()`, `check_contract_access()`, `check_period_access()`, `list_accessible_contract_ids()` 등에서 사용하는 import에 영향.

- [ ] **Step 2: bootstrap.py import 경로 수정**

```python
# 변경 전:
# from app.modules.accounting.services.contract_type_config import seed_defaults as seed_contract_types

# 변경 후:
from app.modules.common.services.contract_type_config import seed_defaults as seed_contract_types
```

- [ ] **Step 3: ProjectContractLink 관련 파일 삭제**

```bash
rm app/modules/common/models/project_contract_link.py
rm app/modules/common/services/project_contract_link.py
rm app/modules/common/schemas/project_contract_link.py
rm app/modules/common/routers/project_contract_links.py
```

- [ ] **Step 4: 나머지 codebase에서 project_contract_link 참조 검색 및 제거**

Run: `grep -rl "project_contract_link\|ProjectContractLink" app/ tests/`

각 파일에서 참조 제거.

- [ ] **Step 5: Commit**

```bash
git add -A app/core/ app/modules/common/
git commit -m "refactor: update auth/bootstrap imports to common, delete ProjectContractLink"
```

---

## Task 16: Alembic 마이그레이션

**Files:**
- Create: `alembic/versions/0010_unified_business_model.py`

- [ ] **Step 1: 마이그레이션 파일 작성**

단일 파일에서 원자적 실행. 순서:

```python
"""0010 사업/계약단위 통합 모델 리팩토링.

1. contract_sales_details 테이블 생성
2. contract_periods에 description 컬럼 추가
3. 영업 전용 필드 데이터를 contract_sales_details로 복사
4. contract_periods에서 영업 전용 컬럼 삭제
5. contracts에서 검수/계산서 컬럼 삭제
6. infra 테이블 FK 변경: project_id → contract_period_id (데이터 매핑 포함)
7. infra 테이블 리네이밍 (project_* → period_*)
8. projects, project_contract_links 테이블 삭제
9. 감사 로그 entity_type "project" → "contract_period" 변환
"""
```

주요 로직:

**Step 6 데이터 매핑 (가장 복잡):**
- `project_contract_links`에서 `is_primary=true`인 contract를 찾고, 해당 contract의 최신 period를 가져와 매핑
- 고아 project → 자동 contract + period 생성
- `project_assets.project_id`, `project_phases.project_id`, `project_customers.project_id` → `contract_period_id`로 변환

```python
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers
revision = "0010"
down_revision = "0009"  # 0009_hardware_interface_capacity_type 확인 필요


def upgrade() -> None:
    conn = op.get_bind()

    # 1. contract_sales_details 생성
    op.create_table(
        "contract_sales_details",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("contract_period_id", sa.Integer, sa.ForeignKey("contract_periods.id"), unique=True, nullable=False),
        sa.Column("expected_revenue_amount", sa.Integer, server_default="0"),
        sa.Column("expected_gp_amount", sa.Integer, server_default="0"),
        sa.Column("inspection_day", sa.Integer, nullable=True),
        sa.Column("inspection_date", sa.Date, nullable=True),
        sa.Column("invoice_month_offset", sa.Integer, nullable=True),
        sa.Column("invoice_day_type", sa.String(20), nullable=True),
        sa.Column("invoice_day", sa.Integer, nullable=True),
        sa.Column("invoice_holiday_adjust", sa.String(10), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 2. contract_periods에 description 추가
    op.add_column("contract_periods", sa.Column("description", sa.Text, nullable=True))

    # 3. 영업 필드 → contract_sales_details 복사
    conn.execute(text("""
        INSERT INTO contract_sales_details
            (contract_period_id, expected_revenue_amount, expected_gp_amount,
             inspection_day, inspection_date, invoice_month_offset,
             invoice_day_type, invoice_day, invoice_holiday_adjust)
        SELECT id, expected_revenue_total, expected_gp_total,
               inspection_day, inspection_date, invoice_month_offset,
               invoice_day_type, invoice_day, invoice_holiday_adjust
        FROM contract_periods
    """))

    # 4. contract_periods에서 영업 전용 컬럼 삭제
    for col in ["expected_revenue_total", "expected_gp_total",
                "inspection_day", "inspection_date", "invoice_month_offset",
                "invoice_day_type", "invoice_day", "invoice_holiday_adjust"]:
        op.drop_column("contract_periods", col)

    # 5. contracts에서 검수/계산서 컬럼 삭제
    for col in ["inspection_day", "inspection_date", "invoice_month_offset",
                "invoice_day_type", "invoice_day", "invoice_holiday_adjust"]:
        op.drop_column("contracts", col)

    # 6. infra FK 변경
    # 6a. project_id → contract_period_id 매핑 테이블 생성 (임시)
    conn.execute(text("""
        CREATE TEMP TABLE _project_period_map AS
        SELECT DISTINCT ON (p.id)
            p.id AS project_id,
            COALESCE(
                (SELECT cp.id FROM contract_periods cp
                 WHERE cp.contract_id = pcl.contract_id
                 ORDER BY cp.period_year DESC LIMIT 1),
                NULL
            ) AS contract_period_id
        FROM projects p
        LEFT JOIN project_contract_links pcl ON pcl.project_id = p.id
        ORDER BY p.id, pcl.is_primary DESC NULLS LAST, pcl.id ASC
    """))

    # 6b. 고아 프로젝트(매핑 없음)에 대해 자동 contract + period 생성
    orphans = conn.execute(text("""
        SELECT p.id, p.project_code, p.project_name, p.customer_id,
               p.start_date, p.description
        FROM projects p
        LEFT JOIN _project_period_map m ON m.project_id = p.id
        WHERE m.contract_period_id IS NULL
    """)).fetchall()

    for orphan in orphans:
        # contract 생성
        code = orphan.project_code or "MIG-ORPHAN"
        # 충돌 방지
        existing = conn.execute(text(
            "SELECT 1 FROM contracts WHERE contract_code = :code"
        ), {"code": code}).first()
        if existing:
            code = f"{code}-MIG"
        result = conn.execute(text("""
            INSERT INTO contracts (contract_code, contract_name, contract_type, end_customer_id, status)
            VALUES (:code, :name, 'ETC', :cid, 'active')
            RETURNING id
        """), {"code": code, "name": orphan.project_name, "cid": orphan.customer_id})
        contract_id = result.scalar()

        # period 생성
        year = orphan.start_date.year if orphan.start_date else 2026
        label = f"Y{str(year)[-2:]}"
        result = conn.execute(text("""
            INSERT INTO contract_periods (contract_id, period_year, period_label, stage, description)
            VALUES (:cid, :year, :label, '50%', :desc)
            RETURNING id
        """), {"cid": contract_id, "year": year, "label": label, "desc": orphan.description})
        period_id = result.scalar()

        conn.execute(text("""
            UPDATE _project_period_map SET contract_period_id = :pid WHERE project_id = :oid
        """), {"pid": period_id, "oid": orphan.id})
        # 매핑이 없었던 경우 INSERT
        conn.execute(text("""
            INSERT INTO _project_period_map (project_id, contract_period_id)
            SELECT :oid, :pid WHERE NOT EXISTS (
                SELECT 1 FROM _project_period_map WHERE project_id = :oid
            )
        """), {"oid": orphan.id, "pid": period_id})

    # 6c. infra 테이블에 contract_period_id 컬럼 추가 + 데이터 매핑
    for table in ["project_phases", "project_assets", "project_customers"]:
        op.add_column(table, sa.Column("contract_period_id", sa.Integer, nullable=True))
        conn.execute(text(f"""
            UPDATE {table} t SET contract_period_id = m.contract_period_id
            FROM _project_period_map m WHERE t.project_id = m.project_id
        """))
        # NOT NULL 제약 추가
        op.alter_column(table, "contract_period_id", nullable=False)
        # project_id FK/컬럼 삭제
        op.drop_constraint(f"{table}_project_id_fkey", table, type_="foreignkey")
        op.drop_column(table, "project_id")
        # contract_period_id FK 추가
        op.create_foreign_key(None, table, "contract_periods", ["contract_period_id"], ["id"])
        op.create_index(f"ix_{table}_contract_period_id", table, ["contract_period_id"])

    # 6d. unique constraint 갱신
    op.drop_constraint("project_assets_project_id_asset_id_key", "project_assets", type_="unique")
    op.create_unique_constraint(None, "project_assets", ["contract_period_id", "asset_id"])
    op.drop_constraint("project_customers_project_id_customer_id_role_key", "project_customers", type_="unique")
    op.create_unique_constraint(None, "project_customers", ["contract_period_id", "customer_id", "role"])

    # 7. 테이블 리네이밍
    op.rename_table("project_phases", "period_phases")
    op.rename_table("project_deliverables", "period_deliverables")
    op.rename_table("project_assets", "period_assets")
    op.rename_table("project_customers", "period_customers")
    op.rename_table("project_customer_contacts", "period_customer_contacts")

    # period_deliverables FK 갱신 (project_phases → period_phases)
    op.drop_constraint("project_deliverables_project_phase_id_fkey", "period_deliverables", type_="foreignkey")
    op.alter_column("period_deliverables", "project_phase_id", new_column_name="period_phase_id")
    op.create_foreign_key(None, "period_deliverables", "period_phases", ["period_phase_id"], ["id"])

    # period_customer_contacts FK 갱신 (project_customers → period_customers)
    op.drop_constraint("project_customer_contacts_project_customer_id_fkey", "period_customer_contacts", type_="foreignkey")
    op.alter_column("period_customer_contacts", "project_customer_id", new_column_name="period_customer_id")
    op.create_foreign_key(None, "period_customer_contacts", "period_customers", ["period_customer_id"], ["id"], ondelete="CASCADE")

    # 8. projects + project_contract_links 삭제
    op.drop_table("project_contract_links")
    op.drop_table("projects")

    # 9. 감사 로그 변환
    conn.execute(text("""
        UPDATE audit_logs SET entity_type = 'contract_period'
        WHERE entity_type = 'project'
    """))
```

> **Note:** 실제 constraint 이름은 DB에서 확인 필요. `op.drop_constraint` 호출 전에 `\d table_name` 또는 Alembic의 `batch_alter_table` 사용을 고려.

- [ ] **Step 2: downgrade 함수 작성**

복잡한 데이터 매핑이므로 `raise NotImplementedError("Irreversible migration")`로 처리.

- [ ] **Step 3: Commit**

```bash
git add alembic/versions/0010_unified_business_model.py
git commit -m "feat(migration): 0010 unified business model - atomic schema migration"
```

---

## Task 17: 프론트엔드 수정 — utils.js

**Files:**
- Modify: `app/static/js/utils.js`

- [ ] **Step 1: localStorage 키 변경**

```javascript
// 변경: infra.last_project_id → infra.last_period_id
// 검색: "last_project_id" → 모두 "last_period_id"로 교체
```

- [ ] **Step 2: ctx 셀렉터 API 경로 변경**

인프라 프로젝트 셀렉터에서 `/api/v1/projects?customer_id=` → `/api/v1/contract-periods?customer_id=`로 변경. 표시 형식: `사업명 (Y26)` = `contract_name + " (" + period_label + ")"`.

이를 위해 common의 `GET /api/v1/contract-periods` 또는 별도 조회 API가 필요할 수 있다. contract-periods API에 customer_id 필터를 추가한다 (common 서비스에서).

- [ ] **Step 3: Commit**

```bash
git add app/static/js/utils.js
git commit -m "refactor(frontend): update localStorage keys and ctx selector API for period"
```

---

## Task 18: 프론트엔드 수정 — infra 페이지

**Files:**
- Modify: `app/static/js/infra_projects.js`
- Modify: `app/static/js/infra_project_detail.js`
- Modify: `app/modules/infra/templates/infra_projects.html`
- Modify: `app/modules/infra/templates/infra_project_detail.html`

- [ ] **Step 1: infra_projects.js 수정**

- API 호출: `/api/v1/projects?customer_id=` → `/api/v1/contract-periods?customer_id=`
- 그리드 컬럼: `project_code` → `contract_code`, `project_name` → 사업명 (contract_name + period_label)
- 행 클릭: project_id → period_id로 네비게이션

- [ ] **Step 2: infra_project_detail.js 수정**

- API 호출: `/api/v1/projects/{id}` → `/api/v1/contract-periods/{id}`
- 단계/산출물/자산/업체 탭 API: `/api/v1/period-phases`, `/api/v1/period-assets` 등
- project_id → contract_period_id 파라미터

- [ ] **Step 3: 템플릿 수정**

표시 텍스트, 필드명, 바인딩 변경.

- [ ] **Step 4: Commit**

```bash
git add app/static/js/infra_projects.js app/static/js/infra_project_detail.js app/modules/infra/templates/infra_projects.html app/modules/infra/templates/infra_project_detail.html
git commit -m "refactor(frontend): update infra project pages to use contract-periods"
```

---

## Task 19: 프론트엔드 수정 — contract_detail.js

**Files:**
- Modify: `app/static/js/contract_detail.js`

- [ ] **Step 1: 영업 전용 정보를 sales-detail API로 분리**

기존에 ContractPeriod 수정 시 한 번에 보내던 영업 필드(expected_revenue_total, inspection_*, invoice_*)를 `PATCH /api/v1/contract-periods/{id}/sales-detail`로 분리 호출.

- [ ] **Step 2: 필드명 변경**

- `expected_revenue_total` → `expected_revenue_amount`
- `expected_gp_total` → `expected_gp_amount`

- [ ] **Step 3: Commit**

```bash
git add app/static/js/contract_detail.js
git commit -m "refactor(frontend): split sales-detail API calls in contract detail"
```

---

## Task 20: 테스트 갱신

**Files:**
- Create: `tests/common/test_contract_service.py`
- Create: `tests/accounting/test_contract_sales_detail.py`
- Modify: `tests/accounting/test_contract_service.py`
- Modify: `tests/infra/test_customer_centric.py`
- Delete: `tests/common/test_project_contract_link.py`

- [ ] **Step 1: common contract 서비스 테스트 작성**

테스트 항목:
- Contract CRUD (create, read, update, delete, restore)
- ContractPeriod CRUD (create, read, update, delete)
- Period 삭제 시 남은 period 없으면 contract cancelled
- start_month > end_month 검증
- 존재하지 않는 contract/period → NotFoundError

- [ ] **Step 2: SalesDetail 테스트 작성**

테스트 항목:
- `get_or_create_sales_detail()`: 미존재 시 자동 생성 확인
- `update_sales_detail()`: 필드 갱신 확인
- lazy-create 후 재조회 시 동일 행 반환

- [ ] **Step 3: 기존 accounting 테스트 수정**

import 경로 변경, 영업 전용 필드 테스트가 SalesDetail 경유하도록 수정.

- [ ] **Step 4: infra 테스트 수정**

`test_customer_centric.py`에서 `Project` → `ContractPeriod`, `project_id` → `contract_period_id` 등.

- [ ] **Step 5: ProjectContractLink 테스트 삭제**

```bash
rm tests/common/test_project_contract_link.py
```

- [ ] **Step 6: 전체 테스트 실행**

Run: `pytest tests/ -v --tb=short`
Expected: 전체 통과

- [ ] **Step 7: Commit**

```bash
git add -A tests/
git commit -m "test: update tests for unified business model (common contract, sales detail, period)"
```

---

## Task 21: 문서 갱신

**Files:**
- Modify: `docs/guidelines/infra.md`
- Modify: `docs/guidelines/backend.md` (필요 시)
- Modify: `docs/DECISIONS.md`
- Modify: `docs/PROJECT_STRUCTURE.md`
- Modify: `docs/KNOWN_ISSUES.md`

- [ ] **Step 1: infra.md 갱신**

- "프로젝트 (Project)" 용어 → "계약단위 (ContractPeriod)"
- `project_id` 참조 → `contract_period_id`
- `ProjectPhase` 등 → `PeriodPhase` 등
- `infra.last_project_id` → `infra.last_period_id`
- Project 테이블 관련 설명 삭제, ContractPeriod 기반 구조 설명 추가

- [ ] **Step 2: DECISIONS.md에 결정 기록 추가**

```markdown
### D-XXX: 사업/계약단위 통합 (2026-03-23)

**결정:** Contract/ContractPeriod를 common 모듈로 이동, infra의 Project 테이블을 삭제하고 ContractPeriod를 인프라 작업 단위로 사용.

**이유:** 동일 사업이 영업/인프라에 각각 등록되는 데이터 중복 문제 해소, 모듈 간 import 규칙 준수.

**영향:** 모든 infra project_* 테이블이 period_*로 리네이밍, FK가 contract_period_id로 변경.
```

- [ ] **Step 3: PROJECT_STRUCTURE.md 갱신**

새 파일/삭제 파일 반영.

- [ ] **Step 4: KNOWN_ISSUES.md 갱신**

해소된 항목 삭제, 필요 시 새 임시 제약 추가.

- [ ] **Step 5: Commit**

```bash
git add docs/
git commit -m "docs: update guidelines, decisions, and structure for unified business model"
```

---

## Task 22: 최종 검증

- [ ] **Step 1: import 정합성 확인**

Run: `python -c "from app.modules.common.models import Contract, ContractPeriod, ContractTypeConfig; print('OK')"`
Run: `python -c "from app.modules.accounting.models import ContractSalesDetail; print('OK')"`
Run: `python -c "from app.modules.infra.models import PeriodPhase, PeriodAsset, PeriodCustomer; print('OK')"`

- [ ] **Step 2: 순환 import 검사**

Run: `python -c "from app.core.app_factory import create_app; print('OK')"`

- [ ] **Step 3: 모듈 격리 테스트**

Run: `pytest tests/common/test_module_isolation.py -v` (있다면)

- [ ] **Step 4: 전체 테스트 통과 확인**

Run: `pytest tests/ -v --tb=short`

- [ ] **Step 5: Alembic 마이그레이션 dry-run**

Run: `alembic upgrade head --sql` (SQL 출력 확인)

- [ ] **Step 6: 서버 기동 확인**

Run: `docker-compose up -d` 또는 로컬 기동 후 주요 페이지 확인

- [ ] **Step 7: 최종 Commit (필요 시 fix)**

```bash
git commit -m "fix: final adjustments for unified business model integration"
```
