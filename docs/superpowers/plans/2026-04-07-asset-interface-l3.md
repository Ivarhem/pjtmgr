# Asset Interface L3 모델링 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자산 인터페이스 인스턴스 테이블 신설 + AssetIP/PortMap 인터페이스 기반 전환 + 공통 그리드 복사/붙여넣기 컴포넌트 구현

**Architecture:** AssetInterface를 자산과 IP/PortMap 사이의 중심 엔티티로 신설한다. AssetIP는 interface_id FK로, PortMap은 src/dst_interface_id FK로 전환하여 24개 텍스트 중복 필드를 제거한다. 카탈로그 HardwareInterface 스펙에서 자산 생성 시 인터페이스 인스턴스를 자동 생성한다.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, AG-Grid Community v32, PostgreSQL 16

**Design spec:** `docs/superpowers/specs/2026-04-07-asset-interface-l3-design.md`

---

## File Structure

### 신규 파일

| 파일 | 역할 |
|------|------|
| `app/modules/infra/models/asset_interface.py` | AssetInterface SQLAlchemy 모델 |
| `app/modules/infra/schemas/asset_interface.py` | Pydantic Create/Update/Read 스키마 |
| `app/modules/infra/services/asset_interface_service.py` | 인터페이스 CRUD + 본딩 관리 + 카탈로그 자동 생성 |
| `app/modules/infra/routers/asset_interfaces.py` | 인터페이스 API 엔드포인트 |
| `tests/infra/test_asset_interface_service.py` | 인터페이스 서비스 테스트 |
| `alembic/versions/0063_create_asset_interfaces.py` | 테이블 생성 마이그레이션 |
| `alembic/versions/0064_asset_ip_interface_fk.py` | AssetIP 전환 마이그레이션 |
| `alembic/versions/0065_port_map_interface_fk.py` | PortMap 전환 마이그레이션 |

### 변경 파일

| 파일 | 변경 내용 |
|------|----------|
| `app/modules/infra/models/__init__.py` | AssetInterface import 추가 |
| `app/modules/infra/models/asset_ip.py` | asset_id → interface_id, 중복 필드 제거 |
| `app/modules/infra/models/port_map.py` | src/dst 텍스트 24개 필드 → interface FK 2개 |
| `app/modules/infra/models/asset.py` | service_ip, mgmt_ip 필드 제거 |
| `app/modules/infra/schemas/asset_ip.py` | interface_id 기반으로 전환 |
| `app/modules/infra/schemas/port_map.py` | interface FK 기반으로 축소 |
| `app/modules/infra/services/network_service.py` | AssetIP/PortMap CRUD를 interface 기반으로 수정 |
| `app/modules/infra/services/asset_service.py` | create_asset에 인터페이스 자동 생성 호출 추가 |
| `app/modules/infra/routers/asset_ips.py` | interface 경유 경로 지원 |
| `app/modules/infra/routers/port_maps.py` | interface FK 기반으로 수정 |
| `app/modules/infra/routers/__init__.py` | asset_interfaces_router 등록 |
| `tests/conftest.py` | AssetInterface import 추가 |
| `tests/infra/test_network_service.py` | interface 기반으로 테스트 수정 |
| `tests/infra/test_port_map_service.py` | interface FK 기반으로 테스트 수정 |
| `app/static/js/utils.js` | addCopyPasteHandler() 공통 유틸리티 추가 |

---

## Task 1: AssetInterface 모델 + 마이그레이션

**Files:**
- Create: `app/modules/infra/models/asset_interface.py`
- Modify: `app/modules/infra/models/__init__.py`
- Modify: `tests/conftest.py`
- Create: `alembic/versions/0063_create_asset_interfaces.py`

- [ ] **Step 1: AssetInterface 모델 파일 생성**

```python
# app/modules/infra/models/asset_interface.py
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetInterface(TimestampMixin, Base):
    __tablename__ = "asset_interfaces"
    __table_args__ = (
        UniqueConstraint("asset_id", "name", name="uq_asset_interface_name"),
        CheckConstraint("parent_id != id", name="ck_no_self_parent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    hw_interface_id: Mapped[int | None] = mapped_column(
        ForeignKey("hardware_interfaces.id", ondelete="SET NULL"), nullable=True
    )

    name: Mapped[str] = mapped_column(String(100))
    if_type: Mapped[str] = mapped_column(String(30), default="physical")
    slot: Mapped[str | None] = mapped_column(String(30), nullable=True)
    slot_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    speed: Mapped[str | None] = mapped_column(String(20), nullable=True)
    media_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True)

    admin_status: Mapped[str] = mapped_column(String(20), default="up")
    oper_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)
```

- [ ] **Step 2: models/__init__.py에 import 추가**

`app/modules/infra/models/__init__.py` 파일에 추가:

```python
from app.modules.infra.models.asset_interface import AssetInterface
```

`__all__` 리스트에 `"AssetInterface"` 추가.

- [ ] **Step 3: tests/conftest.py에 import 추가**

`tests/conftest.py`의 infra models import 블록에 추가:

```python
from app.modules.infra.models import (
    # ... 기존 imports ...
    AssetInterface,
)
```

- [ ] **Step 4: Alembic 마이그레이션 생성**

Run: `alembic revision --autogenerate -m "create_asset_interfaces"`

마이그레이션 파일명을 `0063_create_asset_interfaces.py`로 리네임. 생성된 upgrade/downgrade 내용 확인:
- `asset_interfaces` 테이블 생성
- unique constraint `uq_asset_interface_name`
- check constraint `ck_no_self_parent`
- FK indexes on `asset_id`, `parent_id`

- [ ] **Step 5: 마이그레이션 적용 확인**

Run: `alembic upgrade head`
Expected: 성공, `asset_interfaces` 테이블 생성됨

- [ ] **Step 6: 커밋**

```bash
git add app/modules/infra/models/asset_interface.py app/modules/infra/models/__init__.py tests/conftest.py alembic/versions/0063_*
git commit -m "feat(infra): add AssetInterface model and migration"
```

---

## Task 2: AssetInterface 스키마 + 서비스 + 테스트

**Files:**
- Create: `app/modules/infra/schemas/asset_interface.py`
- Create: `app/modules/infra/services/asset_interface_service.py`
- Create: `tests/infra/test_asset_interface_service.py`

- [ ] **Step 1: 스키마 파일 생성**

```python
# app/modules/infra/schemas/asset_interface.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetInterfaceCreate(BaseModel):
    asset_id: int = 0
    parent_id: int | None = None
    hw_interface_id: int | None = None
    name: str
    if_type: str = "physical"
    slot: str | None = None
    slot_position: int | None = None
    speed: str | None = None
    media_type: str | None = None
    mac_address: str | None = None
    admin_status: str = "up"
    oper_status: str | None = None
    description: str | None = None
    sort_order: int = 0


class AssetInterfaceUpdate(BaseModel):
    parent_id: int | None = None
    name: str | None = None
    if_type: str | None = None
    slot: str | None = None
    slot_position: int | None = None
    speed: str | None = None
    media_type: str | None = None
    mac_address: str | None = None
    admin_status: str | None = None
    oper_status: str | None = None
    description: str | None = None
    sort_order: int | None = None


class AssetInterfaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    parent_id: int | None
    hw_interface_id: int | None
    name: str
    if_type: str
    slot: str | None
    slot_position: int | None
    speed: str | None
    media_type: str | None
    mac_address: str | None
    admin_status: str
    oper_status: str | None
    description: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime


class AssetInterfaceBulkCreate(BaseModel):
    """카탈로그 기반 자동 생성 시 사용."""
    asset_id: int
    generate_from_catalog: bool = True
```

- [ ] **Step 2: 테스트 파일 생성 (실패 테스트 먼저)**

```python
# tests/infra/test_asset_interface_service.py
"""Infra module: asset interface service tests."""
from __future__ import annotations

import pytest

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.common.models.partner import Partner
from app.modules.infra.schemas.asset import AssetCreate
from app.modules.infra.schemas.asset_interface import (
    AssetInterfaceCreate,
    AssetInterfaceUpdate,
)
from app.modules.infra.services.asset_service import create_asset
from app.modules.infra.services.asset_interface_service import (
    create_interface,
    delete_interface,
    get_interface,
    list_interfaces,
    set_lag_members,
    update_interface,
)


def _make_admin_user(db_session, admin_role_id: int):
    from app.modules.common.models.user import User

    user = User(login_id="admin_if", name="Admin", role_id=admin_role_id)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_partner(db_session, name="테스트고객", bno="123-45-67890"):
    partner = Partner(name=name, business_no=bno)
    db_session.add(partner)
    db_session.flush()
    return partner


def _make_asset(db, partner_id: int, name: str, admin):
    return create_asset(
        db,
        AssetCreate(partner_id=partner_id, asset_name=name, asset_type="server"),
        admin,
    )


# -- Basic CRUD --


def test_create_and_list_interfaces(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0", if_type="physical"),
        admin,
    )
    create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth1", if_type="physical"),
        admin,
    )

    interfaces = list_interfaces(db_session, asset.id)
    assert len(interfaces) == 2
    assert interfaces[0].name == "eth0"


def test_create_interface_requires_existing_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    with pytest.raises(NotFoundError):
        create_interface(
            db_session,
            AssetInterfaceCreate(asset_id=9999, name="eth0"),
            admin,
        )


def test_create_interface_duplicate_name_rejected(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
        admin,
    )
    with pytest.raises(DuplicateError):
        create_interface(
            db_session,
            AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
            admin,
        )


def test_update_interface(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    iface = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0", speed="1G"),
        admin,
    )

    updated = update_interface(
        db_session,
        iface.id,
        AssetInterfaceUpdate(speed="10G", media_type="sfp+"),
        admin,
    )
    assert updated.speed == "10G"
    assert updated.media_type == "sfp+"


def test_delete_interface(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    iface = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
        admin,
    )
    delete_interface(db_session, iface.id, admin)

    with pytest.raises(NotFoundError):
        get_interface(db_session, iface.id)


# -- LAG / Bonding --


def test_set_lag_members(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    eth0 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0", if_type="physical"),
        admin,
    )
    eth1 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth1", if_type="physical"),
        admin,
    )
    bond0 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="bond0", if_type="lag"),
        admin,
    )

    set_lag_members(db_session, bond0.id, [eth0.id, eth1.id], admin)

    members = list_interfaces(db_session, asset.id)
    physical = [m for m in members if m.parent_id == bond0.id]
    assert len(physical) == 2


def test_lag_member_must_be_same_asset(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset_a = _make_asset(db_session, partner.id, "SRV-A", admin)
    asset_b = _make_asset(db_session, partner.id, "SRV-B", admin)

    eth0_b = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset_b.id, name="eth0", if_type="physical"),
        admin,
    )
    bond0_a = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset_a.id, name="bond0", if_type="lag"),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        set_lag_members(db_session, bond0_a.id, [eth0_b.id], admin)


def test_lag_member_must_be_physical_type(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    lag1 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="bond0", if_type="lag"),
        admin,
    )
    lag2 = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="bond1", if_type="lag"),
        admin,
    )

    with pytest.raises(BusinessRuleError):
        set_lag_members(db_session, lag1.id, [lag2.id], admin)
```

- [ ] **Step 3: 테스트 실행하여 실패 확인**

Run: `pytest tests/infra/test_asset_interface_service.py -v`
Expected: ImportError — `asset_interface_service` 모듈 없음

- [ ] **Step 4: 서비스 구현**

```python
# app/modules/infra/services/asset_interface_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError, DuplicateError, NotFoundError
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_interface import AssetInterface
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.schemas.asset_interface import (
    AssetInterfaceCreate,
    AssetInterfaceUpdate,
)

_VALID_IF_TYPES = frozenset(
    ["physical", "lag", "vlan", "subinterface", "loopback", "tunnel", "virtual"]
)


def _require_inventory_edit(current_user) -> None:
    from app.modules.infra.services.network_service import _require_inventory_edit as _req
    _req(current_user)


def _ensure_asset_exists(db: Session, asset_id: int) -> Asset:
    asset = db.get(Asset, asset_id)
    if asset is None:
        raise NotFoundError("Asset not found")
    return asset


def _ensure_name_unique(db: Session, asset_id: int, name: str, exclude_id: int | None = None) -> None:
    stmt = select(AssetInterface).where(
        AssetInterface.asset_id == asset_id,
        AssetInterface.name == name,
    )
    if exclude_id is not None:
        stmt = stmt.where(AssetInterface.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise DuplicateError(f"Interface '{name}' already exists on this asset")


def list_interfaces(db: Session, asset_id: int) -> list[AssetInterface]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetInterface)
            .where(AssetInterface.asset_id == asset_id)
            .order_by(AssetInterface.sort_order, AssetInterface.name)
        )
    )


def get_interface(db: Session, interface_id: int) -> AssetInterface:
    iface = db.get(AssetInterface, interface_id)
    if iface is None:
        raise NotFoundError("Interface not found")
    return iface


def create_interface(
    db: Session, payload: AssetInterfaceCreate, current_user
) -> AssetInterface:
    _require_inventory_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _ensure_name_unique(db, payload.asset_id, payload.name)

    if payload.if_type not in _VALID_IF_TYPES:
        raise BusinessRuleError(f"Invalid if_type: {payload.if_type}")

    if payload.parent_id is not None:
        parent = get_interface(db, payload.parent_id)
        if parent.asset_id != payload.asset_id:
            raise BusinessRuleError("Parent interface must belong to the same asset")
        if parent.if_type != "lag":
            raise BusinessRuleError("Parent must be a LAG interface")

    iface = AssetInterface(**payload.model_dump())
    db.add(iface)
    db.commit()
    db.refresh(iface)
    return iface


def update_interface(
    db: Session, interface_id: int, payload: AssetInterfaceUpdate, current_user
) -> AssetInterface:
    _require_inventory_edit(current_user)
    iface = get_interface(db, interface_id)
    changes = payload.model_dump(exclude_unset=True)

    if "name" in changes and changes["name"] != iface.name:
        _ensure_name_unique(db, iface.asset_id, changes["name"], exclude_id=iface.id)

    if "if_type" in changes and changes["if_type"] not in _VALID_IF_TYPES:
        raise BusinessRuleError(f"Invalid if_type: {changes['if_type']}")

    for field, value in changes.items():
        setattr(iface, field, value)
    db.commit()
    db.refresh(iface)
    return iface


def delete_interface(db: Session, interface_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    iface = get_interface(db, interface_id)
    db.delete(iface)
    db.commit()


def set_lag_members(
    db: Session, lag_id: int, member_ids: list[int], current_user
) -> None:
    _require_inventory_edit(current_user)
    lag = get_interface(db, lag_id)
    if lag.if_type != "lag":
        raise BusinessRuleError("Target interface must be a LAG")

    # 기존 멤버 해제
    old_members = db.scalars(
        select(AssetInterface).where(AssetInterface.parent_id == lag_id)
    )
    for m in old_members:
        m.parent_id = None

    # 새 멤버 설정
    for mid in member_ids:
        member = get_interface(db, mid)
        if member.asset_id != lag.asset_id:
            raise BusinessRuleError(
                f"Member {member.name} belongs to a different asset"
            )
        if member.if_type != "physical":
            raise BusinessRuleError(
                f"LAG member {member.name} must be physical type, got {member.if_type}"
            )
        member.parent_id = lag.id

    db.commit()


def generate_interfaces_from_catalog(
    db: Session, asset_id: int, current_user
) -> list[AssetInterface]:
    """카탈로그 HardwareInterface 스펙에서 인터페이스 인스턴스를 자동 생성한다."""
    _require_inventory_edit(current_user)
    asset = _ensure_asset_exists(db, asset_id)

    if asset.model_id is None:
        raise BusinessRuleError("Asset has no catalog model assigned")

    catalog = db.get(ProductCatalog, asset.model_id)
    if catalog is None:
        raise NotFoundError("Product catalog not found")

    hw_interfaces = list(
        db.scalars(
            select(HardwareInterface)
            .where(HardwareInterface.product_id == catalog.id)
            .order_by(HardwareInterface.id)
        )
    )

    if not hw_interfaces:
        return []

    created: list[AssetInterface] = []
    for hw in hw_interfaces:
        prefix = hw.interface_type.lower().replace(" ", "")
        slot_label = hw.note if hw.capacity_type == "modular" else None

        for i in range(hw.count):
            if hw.capacity_type == "modular" and slot_label:
                name = f"{slot_label}/port{i + 1}"
            else:
                name = f"{prefix}-0/0/{i}"

            # 이미 동일 이름이 있으면 건너뛰기
            existing = db.scalar(
                select(AssetInterface).where(
                    AssetInterface.asset_id == asset_id,
                    AssetInterface.name == name,
                )
            )
            if existing is not None:
                continue

            iface = AssetInterface(
                asset_id=asset_id,
                hw_interface_id=hw.id,
                name=name,
                if_type="physical",
                slot=slot_label,
                slot_position=i if slot_label else None,
                speed=hw.speed,
                media_type=hw.connector_type,
                admin_status="up",
                oper_status="not_present" if hw.capacity_type == "modular" else None,
                sort_order=len(created),
            )
            db.add(iface)
            created.append(iface)

    db.commit()
    for c in created:
        db.refresh(c)
    return created
```

- [ ] **Step 5: 테스트 실행**

Run: `pytest tests/infra/test_asset_interface_service.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 6: 커밋**

```bash
git add app/modules/infra/schemas/asset_interface.py app/modules/infra/services/asset_interface_service.py tests/infra/test_asset_interface_service.py
git commit -m "feat(infra): add AssetInterface service with CRUD and LAG support"
```

---

## Task 3: AssetInterface 라우터

**Files:**
- Create: `app/modules/infra/routers/asset_interfaces.py`
- Modify: `app/modules/infra/routers/__init__.py`

- [ ] **Step 1: 라우터 생성**

```python
# app/modules/infra/routers/asset_interfaces.py
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.infra.schemas.asset_interface import (
    AssetInterfaceBulkCreate,
    AssetInterfaceCreate,
    AssetInterfaceRead,
    AssetInterfaceUpdate,
)
from app.modules.infra.services.asset_interface_service import (
    create_interface,
    delete_interface,
    generate_interfaces_from_catalog,
    get_interface,
    list_interfaces,
    set_lag_members,
    update_interface,
)

router = APIRouter(tags=["infra-asset-interfaces"])


@router.get(
    "/api/v1/assets/{asset_id}/interfaces",
    response_model=list[AssetInterfaceRead],
)
def list_interfaces_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetInterfaceRead]:
    return list_interfaces(db, asset_id)


@router.post(
    "/api/v1/assets/{asset_id}/interfaces",
    response_model=AssetInterfaceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_interface_endpoint(
    asset_id: int,
    payload: AssetInterfaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetInterfaceRead:
    payload.asset_id = asset_id
    return create_interface(db, payload, current_user)


@router.post(
    "/api/v1/assets/{asset_id}/interfaces/generate",
    response_model=list[AssetInterfaceRead],
    status_code=status.HTTP_201_CREATED,
)
def generate_interfaces_endpoint(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetInterfaceRead]:
    return generate_interfaces_from_catalog(db, asset_id, current_user)


@router.get(
    "/api/v1/asset-interfaces/{interface_id}",
    response_model=AssetInterfaceRead,
)
def get_interface_endpoint(
    interface_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetInterfaceRead:
    return get_interface(db, interface_id)


@router.patch(
    "/api/v1/asset-interfaces/{interface_id}",
    response_model=AssetInterfaceRead,
)
def update_interface_endpoint(
    interface_id: int,
    payload: AssetInterfaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetInterfaceRead:
    return update_interface(db, interface_id, payload, current_user)


@router.delete(
    "/api/v1/asset-interfaces/{interface_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_interface_endpoint(
    interface_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    delete_interface(db, interface_id, current_user)


@router.post(
    "/api/v1/asset-interfaces/{lag_id}/members",
    status_code=status.HTTP_204_NO_CONTENT,
)
def set_lag_members_endpoint(
    lag_id: int,
    member_ids: list[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    set_lag_members(db, lag_id, member_ids, current_user)
```

- [ ] **Step 2: __init__.py에 라우터 등록**

`app/modules/infra/routers/__init__.py`에 추가:

```python
from app.modules.infra.routers.asset_interfaces import router as asset_interfaces_router
```

그리고 `api_router.include_router(asset_interfaces_router)` 추가.

- [ ] **Step 3: 커밋**

```bash
git add app/modules/infra/routers/asset_interfaces.py app/modules/infra/routers/__init__.py
git commit -m "feat(infra): add AssetInterface API endpoints"
```

---

## Task 4: AssetIP 모델 전환 (asset_id → interface_id)

**Files:**
- Modify: `app/modules/infra/models/asset_ip.py`
- Modify: `app/modules/infra/schemas/asset_ip.py`
- Create: `alembic/versions/0064_asset_ip_interface_fk.py`

- [ ] **Step 1: AssetIP 모델 수정**

`app/modules/infra/models/asset_ip.py`를 아래로 교체:

```python
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class AssetIP(TimestampMixin, Base):
    __tablename__ = "asset_ips"
    __table_args__ = (
        UniqueConstraint("interface_id", "ip_address", name="uq_interface_ip"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    interface_id: Mapped[int] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="CASCADE"), index=True
    )
    ip_subnet_id: Mapped[int | None] = mapped_column(
        ForeignKey("ip_subnets.id"), index=True, nullable=True
    )
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    ip_type: Mapped[str] = mapped_column(String(30), default="service")
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vlan_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
```

제거된 필드: `asset_id`, `interface_name`, `network`, `netmask`, `gateway`, `dns_primary`, `dns_secondary`

- [ ] **Step 2: AssetIP 스키마 수정**

`app/modules/infra/schemas/asset_ip.py`를 아래로 교체:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetIPCreate(BaseModel):
    interface_id: int = 0
    ip_subnet_id: int | None = None
    ip_address: str
    ip_type: str = "service"
    is_primary: bool = False
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    note: str | None = None


class AssetIPUpdate(BaseModel):
    ip_subnet_id: int | None = None
    ip_address: str | None = None
    ip_type: str | None = None
    is_primary: bool | None = None
    zone: str | None = None
    service_name: str | None = None
    hostname: str | None = None
    vlan_id: str | None = None
    note: str | None = None


class AssetIPRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    interface_id: int
    ip_subnet_id: int | None
    ip_address: str
    ip_type: str
    is_primary: bool
    zone: str | None
    service_name: str | None
    hostname: str | None
    vlan_id: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: Alembic 마이그레이션 생성**

Run: `alembic revision --autogenerate -m "asset_ip_interface_fk"`

마이그레이션 파일명을 `0064_asset_ip_interface_fk.py`로 리네임. 확인 사항:
- `asset_id` 컬럼 삭제
- `interface_id` FK 컬럼 추가 (CASCADE)
- `interface_name`, `network`, `netmask`, `gateway`, `dns_primary`, `dns_secondary` 컬럼 삭제
- `uq_interface_ip` unique constraint 추가

**주의:** 제로베이스이므로 데이터 마이그레이션 불필요. 기존 테이블이 비어있다면 단순 drop/add column으로 충분.

- [ ] **Step 4: 마이그레이션 적용**

Run: `alembic upgrade head`
Expected: 성공

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/models/asset_ip.py app/modules/infra/schemas/asset_ip.py alembic/versions/0064_*
git commit -m "feat(infra): migrate AssetIP to interface-based FK"
```

---

## Task 5: AssetIP 서비스/라우터 전환 + 테스트 수정

**Files:**
- Modify: `app/modules/infra/services/network_service.py` (AssetIP 함수들)
- Modify: `app/modules/infra/routers/asset_ips.py`
- Modify: `tests/infra/test_network_service.py`

- [ ] **Step 1: network_service.py의 AssetIP 함수 수정**

AssetIP 관련 함수들을 interface 기반으로 수정:

- `list_asset_ips(db, asset_id)` → `list_interface_ips(db, interface_id)` + `list_asset_ips(db, asset_id)` (asset의 모든 인터페이스 IP를 JOIN으로 반환)
- `create_asset_ip()` — `payload.asset_id` 대신 `payload.interface_id`로 인터페이스 존재 검증, partner scope에서 IP 유일성 검증은 interface → asset → partner 경로로
- `_ensure_asset_exists()` 호출 대신 `_ensure_interface_exists()` 호출
- IP 유일성 검증: `interface.asset.partner_id` 기준 유지

핵심 변경 — `create_asset_ip`:

```python
def create_asset_ip(db: Session, payload: AssetIPCreate, current_user) -> AssetIP:
    _require_inventory_edit(current_user)
    iface = db.get(AssetInterface, payload.interface_id)
    if iface is None:
        raise NotFoundError("Interface not found")
    asset = db.get(Asset, iface.asset_id)
    if payload.ip_subnet_id is not None:
        _ensure_subnet_exists(db, payload.ip_subnet_id)
    _ensure_ip_unique_in_partner(db, asset.partner_id, payload.ip_address)

    asset_ip = AssetIP(**payload.model_dump())
    db.add(asset_ip)
    db.commit()
    db.refresh(asset_ip)
    return asset_ip
```

핵심 변경 — `list_asset_ips` (자산 전체 IP 조회 유지):

```python
def list_asset_ips(db: Session, asset_id: int) -> list[AssetIP]:
    _ensure_asset_exists(db, asset_id)
    return list(
        db.scalars(
            select(AssetIP)
            .join(AssetInterface, AssetIP.interface_id == AssetInterface.id)
            .where(AssetInterface.asset_id == asset_id)
            .order_by(AssetIP.ip_address)
        )
    )
```

`_ensure_ip_unique_in_partner` 수정 — interface 경유:

```python
def _ensure_ip_unique_in_partner(
    db: Session, partner_id: int, ip_address: str, exclude_id: int | None = None
) -> None:
    stmt = (
        select(AssetIP)
        .join(AssetInterface, AssetIP.interface_id == AssetInterface.id)
        .join(Asset, AssetInterface.asset_id == Asset.id)
        .where(Asset.partner_id == partner_id, AssetIP.ip_address == ip_address)
    )
    if exclude_id is not None:
        stmt = stmt.where(AssetIP.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise DuplicateError(f"IP address {ip_address} already exists for this partner")
```

- [ ] **Step 2: asset_ips.py 라우터 수정**

경로 유지 (`/api/v1/assets/{asset_id}/ips`는 JOIN으로 자산 전체 IP 반환), 인터페이스 기반 생성 경로 추가:

```python
@router.post(
    "/api/v1/interfaces/{interface_id}/ips",
    response_model=AssetIPRead,
    status_code=status.HTTP_201_CREATED,
)
def create_interface_ip_endpoint(
    interface_id: int,
    payload: AssetIPCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssetIPRead:
    payload.interface_id = interface_id
    return create_asset_ip(db, payload, current_user)
```

기존 `/api/v1/assets/{asset_id}/ips` GET 엔드포인트는 유지 (JOIN 쿼리 결과 반환).

- [ ] **Step 3: test_network_service.py의 AssetIP 테스트 수정**

테스트에서 `AssetIPCreate(asset_id=...)` → `AssetIPCreate(interface_id=...)`로 변경.
각 테스트에서 자산 생성 후 인터페이스를 먼저 생성하고, 그 interface_id를 사용:

```python
from app.modules.infra.schemas.asset_interface import AssetInterfaceCreate
from app.modules.infra.services.asset_interface_service import create_interface

def test_create_and_list_asset_ips(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)
    iface = create_interface(
        db_session,
        AssetInterfaceCreate(asset_id=asset.id, name="eth0"),
        admin,
    )

    create_asset_ip(
        db_session,
        AssetIPCreate(interface_id=iface.id, ip_address="10.10.1.10", ip_type="service"),
        admin,
    )
    # ... 나머지 기존 패턴 유지, asset_id → interface_id
```

- [ ] **Step 4: 테스트 실행**

Run: `pytest tests/infra/test_network_service.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/services/network_service.py app/modules/infra/routers/asset_ips.py tests/infra/test_network_service.py
git commit -m "feat(infra): migrate AssetIP service/router to interface-based"
```

---

## Task 6: PortMap 모델 전환

**Files:**
- Modify: `app/modules/infra/models/port_map.py`
- Modify: `app/modules/infra/schemas/port_map.py`
- Create: `alembic/versions/0065_port_map_interface_fk.py`

- [ ] **Step 1: PortMap 모델 수정**

`app/modules/infra/models/port_map.py`를 아래로 교체:

```python
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class PortMap(TimestampMixin, Base):
    __tablename__ = "port_maps"
    __table_args__ = (
        UniqueConstraint(
            "src_interface_id", "dst_interface_id", "connection_type", "protocol", "port",
            name="uq_portmap_connection",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)

    src_interface_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dst_interface_id: Mapped[int | None] = mapped_column(
        ForeignKey("asset_interfaces.id", ondelete="SET NULL"), nullable=True, index=True
    )

    protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    purpose: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="required")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Common
    seq: Mapped[int | None] = mapped_column(Integer, nullable=True)
    connection_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Cable info
    cable_no: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cable_request: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cable_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cable_speed: Mapped[str | None] = mapped_column(String(30), nullable=True)
    duplex: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cable_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

제거된 필드 (24개): `src_asset_id`, `dst_asset_id`, `src_ip`, `dst_ip`, `src_mid`, `dst_mid`, `src_rack_no`, `dst_rack_no`, `src_rack_unit`, `dst_rack_unit`, `src_vendor`, `dst_vendor`, `src_model`, `dst_model`, `src_hostname`, `dst_hostname`, `src_cluster`, `dst_cluster`, `src_slot`, `dst_slot`, `src_port_name`, `dst_port_name`, `src_service_name`, `dst_service_name`, `src_zone`, `dst_zone`, `src_vlan`, `dst_vlan`

- [ ] **Step 2: PortMap 스키마 수정**

`app/modules/infra/schemas/port_map.py`를 아래로 교체:

```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PortMapCreate(BaseModel):
    partner_id: int
    src_interface_id: int | None = None
    dst_interface_id: int | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str = "required"
    note: str | None = None
    seq: int | None = None
    connection_type: str | None = None
    summary: str | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapUpdate(BaseModel):
    src_interface_id: int | None = None
    dst_interface_id: int | None = None
    protocol: str | None = None
    port: int | None = None
    purpose: str | None = None
    status: str | None = None
    note: str | None = None
    seq: int | None = None
    connection_type: str | None = None
    summary: str | None = None
    cable_no: str | None = None
    cable_request: str | None = None
    cable_type: str | None = None
    cable_speed: str | None = None
    duplex: str | None = None
    cable_category: str | None = None


class PortMapRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    partner_id: int
    src_interface_id: int | None
    dst_interface_id: int | None
    protocol: str | None
    port: int | None
    purpose: str | None
    status: str
    note: str | None
    seq: int | None
    connection_type: str | None
    summary: str | None
    cable_no: str | None
    cable_request: str | None
    cable_type: str | None
    cable_speed: str | None
    duplex: str | None
    cable_category: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: Alembic 마이그레이션 생성**

Run: `alembic revision --autogenerate -m "port_map_interface_fk"`

파일명을 `0065_port_map_interface_fk.py`로 리네임. 확인:
- src/dst 텍스트 컬럼 24개 삭제
- `src_interface_id`, `dst_interface_id` FK 추가
- `uq_portmap_connection` unique constraint 추가

- [ ] **Step 4: 마이그레이션 적용**

Run: `alembic upgrade head`
Expected: 성공

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/models/port_map.py app/modules/infra/schemas/port_map.py alembic/versions/0065_*
git commit -m "feat(infra): migrate PortMap to interface-based FK"
```

---

## Task 7: PortMap 서비스/라우터 전환 + 테스트 수정

**Files:**
- Modify: `app/modules/infra/services/network_service.py` (PortMap 함수들)
- Modify: `app/modules/infra/routers/port_maps.py`
- Modify: `tests/infra/test_port_map_service.py`

- [ ] **Step 1: network_service.py의 PortMap 함수 수정**

`create_port_map()` — `src_asset_id`/`dst_asset_id` 검증 대신 `src_interface_id`/`dst_interface_id` 검증:

```python
def create_port_map(db: Session, payload: PortMapCreate, current_user) -> PortMap:
    _require_inventory_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)

    if payload.src_interface_id is not None:
        iface = db.get(AssetInterface, payload.src_interface_id)
        if iface is None:
            raise NotFoundError("Source interface not found")
    if payload.dst_interface_id is not None:
        iface = db.get(AssetInterface, payload.dst_interface_id)
        if iface is None:
            raise NotFoundError("Destination interface not found")

    port_map = PortMap(**payload.model_dump())
    db.add(port_map)
    db.commit()
    db.refresh(port_map)
    return port_map
```

`update_port_map()` — 동일 패턴으로 interface 검증 추가.

- [ ] **Step 2: port_maps.py 라우터 수정**

스키마가 바뀌었으므로 import만 확인하면 됨. 기존 엔드포인트 구조 유지.

- [ ] **Step 3: test_port_map_service.py 수정**

기존 `src_asset_id`/`dst_asset_id` → `src_interface_id`/`dst_interface_id` 전환.
각 테스트에서 인터페이스를 먼저 생성:

```python
from app.modules.infra.schemas.asset_interface import AssetInterfaceCreate
from app.modules.infra.services.asset_interface_service import create_interface

# 각 테스트 내에서:
src_iface = create_interface(db_session, AssetInterfaceCreate(asset_id=asset.id, name="eth0"), admin)
dst_iface = create_interface(db_session, AssetInterfaceCreate(asset_id=asset2.id, name="eth0"), admin)

create_port_map(
    db_session,
    PortMapCreate(
        partner_id=partner.id,
        src_interface_id=src_iface.id,
        dst_interface_id=dst_iface.id,
        protocol="TCP",
        port=443,
    ),
    admin,
)
```

- [ ] **Step 4: 테스트 실행**

Run: `pytest tests/infra/test_port_map_service.py tests/infra/test_network_service.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/services/network_service.py app/modules/infra/routers/port_maps.py tests/infra/test_port_map_service.py
git commit -m "feat(infra): migrate PortMap service/router to interface-based"
```

---

## Task 8: 카탈로그 자동 생성 테스트 + asset_service 연동

**Files:**
- Modify: `app/modules/infra/services/asset_service.py`
- Add to: `tests/infra/test_asset_interface_service.py`

- [ ] **Step 1: 카탈로그 자동 생성 테스트 추가**

`tests/infra/test_asset_interface_service.py`에 추가:

```python
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.hardware_interface import HardwareInterface
from app.modules.infra.services.asset_interface_service import generate_interfaces_from_catalog


def _make_catalog_with_interfaces(db_session):
    """카탈로그 + HardwareInterface 스펙 생성 헬퍼."""
    catalog = ProductCatalog(vendor="Cisco", name="C9300-48T")
    db_session.add(catalog)
    db_session.flush()

    hw1 = HardwareInterface(
        product_id=catalog.id,
        interface_type="1GE",
        speed="1G",
        count=4,
        connector_type="copper",
        capacity_type="fixed",
    )
    hw2 = HardwareInterface(
        product_id=catalog.id,
        interface_type="10GE",
        speed="10G",
        count=2,
        connector_type="sfp+",
        capacity_type="modular",
        note="Slot 1",
    )
    db_session.add_all([hw1, hw2])
    db_session.flush()
    return catalog


def test_generate_interfaces_from_catalog(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog_with_interfaces(db_session)

    asset = _make_asset(db_session, partner.id, "SW-01", admin)
    # model_id 설정 (asset_service의 create_asset은 catalog 검증하므로 직접 설정)
    asset.model_id = catalog.id
    db_session.commit()

    created = generate_interfaces_from_catalog(db_session, asset.id, admin)

    assert len(created) == 6  # 4 fixed + 2 modular
    fixed = [c for c in created if c.slot is None]
    modular = [c for c in created if c.slot is not None]
    assert len(fixed) == 4
    assert len(modular) == 2
    assert all(m.oper_status == "not_present" for m in modular)
    assert all(f.speed == "1G" for f in fixed)


def test_generate_no_model_raises(db_session, admin_role_id) -> None:
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    asset = _make_asset(db_session, partner.id, "SRV-01", admin)

    with pytest.raises(BusinessRuleError, match="no catalog model"):
        generate_interfaces_from_catalog(db_session, asset.id, admin)


def test_generate_idempotent(db_session, admin_role_id) -> None:
    """이미 동일 이름 인터페이스가 있으면 건너뛴다."""
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog = _make_catalog_with_interfaces(db_session)

    asset = _make_asset(db_session, partner.id, "SW-01", admin)
    asset.model_id = catalog.id
    db_session.commit()

    first = generate_interfaces_from_catalog(db_session, asset.id, admin)
    second = generate_interfaces_from_catalog(db_session, asset.id, admin)

    assert len(first) == 6
    assert len(second) == 0  # 중복 건너뜀
```

- [ ] **Step 2: 테스트 실행**

Run: `pytest tests/infra/test_asset_interface_service.py::test_generate_interfaces_from_catalog tests/infra/test_asset_interface_service.py::test_generate_no_model_raises tests/infra/test_asset_interface_service.py::test_generate_idempotent -v`
Expected: PASS

- [ ] **Step 3: 커밋**

```bash
git add tests/infra/test_asset_interface_service.py
git commit -m "test(infra): add catalog auto-generation tests for AssetInterface"
```

---

## Task 9: Asset 모델 정리 (service_ip, mgmt_ip 제거)

**Files:**
- Modify: `app/modules/infra/models/asset.py`
- Modify: `app/modules/infra/schemas/asset.py` (해당 필드 제거)
- Create: `alembic/versions/0066_drop_asset_ip_fields.py`

- [ ] **Step 1: asset.py에서 service_ip, mgmt_ip 컬럼 제거**

`app/modules/infra/models/asset.py`에서 아래 두 줄 삭제:

```python
service_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
mgmt_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
```

- [ ] **Step 2: asset.py 스키마에서 해당 필드 제거**

`app/modules/infra/schemas/asset.py`의 `AssetCreate`, `AssetUpdate`, `AssetRead`에서 `service_ip`, `mgmt_ip` 필드 제거.

- [ ] **Step 3: 서비스/라우터에서 해당 필드 참조 검색 및 제거**

Run: grep으로 `service_ip`, `mgmt_ip` 참조하는 코드 검색.
인프라 importer, exporter 등에서 참조가 있으면 제거 또는 interface IP 경유로 대체.

- [ ] **Step 4: Alembic 마이그레이션**

Run: `alembic revision --autogenerate -m "drop_asset_ip_fields"`
파일명을 `0066_drop_asset_ip_fields.py`로 리네임.

- [ ] **Step 5: 전체 테스트 실행**

Run: `pytest tests/ -v`
Expected: 모든 테스트 PASS (service_ip/mgmt_ip 참조 제거 확인)

- [ ] **Step 6: 커밋**

```bash
git add app/modules/infra/models/asset.py app/modules/infra/schemas/asset.py alembic/versions/0066_*
git commit -m "refactor(infra): remove service_ip/mgmt_ip from Asset (moved to AssetIP via interface)"
```

---

## Task 10: 공통 그리드 복사/붙여넣기 컴포넌트

**Files:**
- Modify: `app/static/js/utils.js`

- [ ] **Step 1: addCopyPasteHandler 함수 구현**

`app/static/js/utils.js` 파일 끝에 추가:

```javascript
/**
 * AG-Grid 공통 복사/붙여넣기 핸들러.
 *
 * @param {HTMLElement} gridEl  - 그리드 래퍼 DOM 엘리먼트
 * @param {object} gridApi      - AG-Grid API 인스턴스
 * @param {object} opts
 * @param {string[]} opts.editableFields  - 붙여넣기 대상 필드명 배열
 * @param {boolean}  [opts.autoCreateRows=false] - 행 자동 추가 여부
 * @param {function} [opts.onPaste]  - 붙여넣기 후 콜백 (changes: Array<{rowIndex, field, oldValue, newValue}>)
 * @param {function} [opts.onCopy]   - 복사 후 콜백 (data: string[][])
 * @param {object}   [opts.typeMap]  - 컬럼별 타입 힌트 {field: 'number' | {type:'enum', values:[...]}}
 */
function addCopyPasteHandler(gridEl, gridApi, opts = {}) {
  const {
    editableFields = [],
    autoCreateRows = false,
    onPaste = null,
    onCopy = null,
    typeMap = {},
  } = opts;

  let _undoStack = [];

  // ── Copy ──
  gridEl.addEventListener('keydown', (e) => {
    if (!(e.ctrlKey && e.key === 'c') && !(e.metaKey && e.key === 'c')) return;
    const ranges = gridApi.getCellRanges?.();
    if (!ranges || ranges.length === 0) return;

    const range = ranges[0];
    const cols = range.columns.map(c => c.getColId());
    const startRow = Math.min(range.startRow.rowIndex, range.endRow.rowIndex);
    const endRow = Math.max(range.startRow.rowIndex, range.endRow.rowIndex);

    const rows = [];
    for (let ri = startRow; ri <= endRow; ri++) {
      const node = gridApi.getDisplayedRowAtIndex(ri);
      if (!node || !node.data) continue;
      rows.push(cols.map(col => node.data[col] ?? ''));
    }

    const tsv = rows.map(r => r.join('\t')).join('\n');
    navigator.clipboard.writeText(tsv).catch(() => {});
    e.preventDefault();

    if (onCopy) onCopy(rows);
  });

  // ── Paste ──
  gridEl.addEventListener('paste', (e) => {
    const focused = gridApi.getFocusedCell();
    if (!focused) return;

    const text = (e.clipboardData || window.clipboardData)?.getData('text/plain');
    if (!text) return;
    e.preventDefault();
    e.stopPropagation();
    gridApi.stopEditing();

    const pasteRows = text.trim().split('\n').map(r => r.split('\t'));
    const startRowIdx = focused.rowIndex;
    const allCols = gridApi.getColumnDefs()
      .map(c => c.field)
      .filter(f => f && editableFields.includes(f));

    const focusedField = focused.column.getColId();
    const colStart = allCols.indexOf(focusedField);
    if (colStart < 0) return;

    const changes = [];
    const totalRowsNeeded = startRowIdx + pasteRows.length;
    const currentRowCount = gridApi.getDisplayedRowCount();

    // 행 자동 추가
    if (autoCreateRows && totalRowsNeeded > currentRowCount) {
      const newRows = [];
      for (let i = 0; i < totalRowsNeeded - currentRowCount; i++) {
        newRows.push({});
      }
      gridApi.applyTransaction({ add: newRows });
    }

    for (let ri = 0; ri < pasteRows.length; ri++) {
      const rowIdx = startRowIdx + ri;
      const node = gridApi.getDisplayedRowAtIndex(rowIdx);
      if (!node || !node.data) continue;

      for (let ci = 0; ci < pasteRows[ri].length; ci++) {
        const field = allCols[colStart + ci];
        if (!field) continue;

        let value = pasteRows[ri][ci].trim();
        const oldValue = node.data[field];

        // 타입 변환
        const hint = typeMap[field];
        if (hint === 'number') {
          value = Number(value.replace(/[^0-9.\-]/g, '')) || 0;
        } else if (hint && hint.type === 'enum') {
          if (!hint.values.includes(value)) value = oldValue;
        }

        changes.push({ rowIndex: rowIdx, field, oldValue, newValue: value });
        node.data[field] = value;
      }
    }

    // UI 갱신
    const rowNodes = [];
    for (let ri = 0; ri < pasteRows.length; ri++) {
      const node = gridApi.getDisplayedRowAtIndex(startRowIdx + ri);
      if (node) rowNodes.push(node);
    }
    gridApi.refreshCells({ rowNodes, force: true });

    // 플래시 효과
    const flashCols = [...new Set(changes.map(c => c.field))];
    gridApi.flashCells({
      rowNodes,
      columns: flashCols,
      flashDuration: 300,
      fadeDuration: 200,
    });

    // Undo 스택 저장
    _undoStack.push(changes);

    if (onPaste) onPaste(changes);
  });

  // ── Undo (Ctrl+Z) ──
  gridEl.addEventListener('keydown', (e) => {
    if (!(e.ctrlKey && e.key === 'z') && !(e.metaKey && e.key === 'z')) return;
    if (_undoStack.length === 0) return;

    const lastChanges = _undoStack.pop();
    const affectedNodes = new Set();

    for (const { rowIndex, field, oldValue } of lastChanges) {
      const node = gridApi.getDisplayedRowAtIndex(rowIndex);
      if (!node || !node.data) continue;
      node.data[field] = oldValue;
      affectedNodes.add(node);
    }

    gridApi.refreshCells({ rowNodes: [...affectedNodes], force: true });
    e.preventDefault();
  });
}
```

- [ ] **Step 2: 브라우저에서 기능 확인**

기존 editable 그리드(예: 자산 목록)에 `addCopyPasteHandler`를 연결하고:
- 다중 셀 선택 → Ctrl+C → 다른 위치에 Ctrl+V
- Ctrl+Z로 되돌리기
- 행 자동 추가 (autoCreateRows: true인 경우)

- [ ] **Step 3: 커밋**

```bash
git add app/static/js/utils.js
git commit -m "feat(ui): add common grid copy/paste handler with undo support"
```

---

## Task 11: 문서 갱신

**Files:**
- Modify: `docs/guidelines/infra.md`
- Modify: `docs/DECISIONS.md`
- Modify: `docs/PROJECT_STRUCTURE.md`

- [ ] **Step 1: infra.md에 인터페이스 모델 설명 추가**

AssetInterface 테이블, if_type enum, LAG parent-child 규칙, IP/PortMap 연동 관계 기술.

- [ ] **Step 2: DECISIONS.md에 설계 결정 기록**

```markdown
## 2026-04-07: Asset Interface L3 모델링

AssetInterface 테이블을 신설하여 자산별 물리/논리 인터페이스 인스턴스를 관리한다.
AssetIP는 interface FK로, PortMap은 src/dst interface FK로 전환하여 SSOT를 달성.
제로베이스이므로 데이터 마이그레이션 없이 Big Bang 전환.
설계 스펙: `docs/superpowers/specs/2026-04-07-asset-interface-l3-design.md`
```

- [ ] **Step 3: PROJECT_STRUCTURE.md 갱신**

신규 파일 추가: `asset_interface.py` (model, schema, service, router, test)

- [ ] **Step 4: 커밋**

```bash
git add docs/guidelines/infra.md docs/DECISIONS.md docs/PROJECT_STRUCTURE.md
git commit -m "docs: update guidelines and decisions for interface L3 modeling"
```

---

## Task 12: 전체 회귀 테스트

- [ ] **Step 1: 전체 테스트 실행**

Run: `pytest tests/ -v`
Expected: 모든 테스트 PASS

- [ ] **Step 2: import 검증**

Run: `python -c "from app.modules.infra.models import AssetInterface; print('OK')"`
Expected: OK

- [ ] **Step 3: Alembic 정합성 확인**

Run: `alembic check`
Expected: 모델과 마이그레이션이 일치

---

## 요약

| Task | 내용 | 파일 수 |
|------|------|---------|
| 1 | AssetInterface 모델 + 마이그레이션 | 4 |
| 2 | 스키마 + 서비스 + 테스트 | 3 |
| 3 | 라우터 + 등록 | 2 |
| 4 | AssetIP 모델/스키마 전환 + 마이그레이션 | 3 |
| 5 | AssetIP 서비스/라우터/테스트 수정 | 3 |
| 6 | PortMap 모델/스키마 전환 + 마이그레이션 | 3 |
| 7 | PortMap 서비스/라우터/테스트 수정 | 3 |
| 8 | 카탈로그 자동 생성 테스트 | 1 |
| 9 | Asset 모델 정리 | 3+ |
| 10 | 공통 그리드 복사/붙여넣기 | 1 |
| 11 | 문서 갱신 | 3 |
| 12 | 전체 회귀 테스트 | 0 |
