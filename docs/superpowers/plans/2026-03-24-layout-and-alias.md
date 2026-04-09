# 전산실 배치도 + Alias 관리 구현 계획

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** 인프라모듈에 전산실 배치도(센터/전산실/랙 공간 관리 + 자산 매핑 시각화)와 자산 Alias 관리 기능의 DB 기반 + API 스켈레톤 + placeholder UI를 구축한다. 실제 기능 구현은 모듈 단위 후속 세션에서 진행한다.

**Architecture:** Center→Room→RoomZone/RackPosition→AssetRackMapping 계층으로 공간을 정규화하고, AssetAlias로 자산 별칭을 관리한다. 기존 Asset 문자열 필드(center, rack_no, rack_unit)는 유지하며 배치도 모델과 bridge 테이블로 느슨하게 연결한다.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Jinja2

**Spec:** `docs/superpowers/specs/2026-03-24-layout-and-alias-design.md`

---

## 이번 계획의 범위

**Foundation만 구축한다.** DB 스키마, 스키마(Pydantic), 서비스 스켈레톤, API 라우터, placeholder UI를 생성하여 후속 모듈별 구현의 기반을 잡는다.

| 이번 범위 (Foundation) | 후속 모듈 (별도 세션) |
|---|---|
| 모델 6종 + Migration | **모듈 A:** 센터/전산실 CRUD 완성 |
| 스키마 6종 (Create/Update/Read) | **모듈 B:** Zone/Rack 편집 + 그리드 캔버스 |
| 서비스 함수 시그니처 + 기본 CRUD | **모듈 C:** 자산 매핑 + 자동 매핑 + 시각화 |
| API 라우터 (엔드포인트 + 서비스 연결) | **모듈 D:** Alias CRUD + 자산 검색 통합 |
| 사이드바 메뉴 + placeholder 페이지 | |
| 모델/라우터 등록 + 문서 갱신 | |

---

## 기존 패턴 참조

| 항목 | 참조 파일 | 패턴 요약 |
|---|---|---|
| 모델 (child entity) | `app/modules/infra/models/asset_software.py` | TimestampMixin + Base, FK ondelete, `Mapped[int]` (타입 추론, `Integer` 생략) |
| 스키마 | `app/modules/infra/schemas/asset_contact.py` | Create/Update/Read 3종, ConfigDict(from_attributes=True) |
| 서비스 | `app/modules/infra/services/asset_software_service.py` | `current_user: User` 타입, `audit.log(module="infra")` 필수 |
| 라우터 | `app/modules/infra/routers/asset_contacts.py` | 얇은 래퍼, GET list/POST nested, PATCH/DELETE flat |
| 라우터 등록 | `app/modules/infra/routers/__init__.py` | api_router.include_router() |
| 모델 등록 | `app/modules/infra/models/__init__.py` | import + __all__ |
| 사이드바 | `app/templates/base.html:119-125` | subnav-links + lucide icon |
| 페이지 라우트 | `app/modules/infra/routers/pages.py` | _templates(request).TemplateResponse() |
| Migration | `alembic/versions/0012_customer_to_partner.py` | NNNN_desc.py, revision="NNNN" |

**코드 스타일 규칙** (기존 패턴에서 도출):
- 모델 PK: `mapped_column(primary_key=True)` — `Integer`, `autoincrement=True` 생략
- 모델 FK: `mapped_column(ForeignKey("table.id"), index=True)` — `Mapped[int]`이면 `nullable=False` 생략
- 서비스 함수: `current_user: User` 타입힌트 필수 (`from app.modules.common.models.user import User`)
- audit.log: `module="infra"` 파라미터 필수

---

## Task 1: 모델 6종 생성

**Files:**
- Create: `app/modules/infra/models/center.py`
- Create: `app/modules/infra/models/room.py`
- Create: `app/modules/infra/models/room_zone.py`
- Create: `app/modules/infra/models/rack_position.py`
- Create: `app/modules/infra/models/asset_rack_mapping.py`
- Create: `app/modules/infra/models/asset_alias.py`
- Modify: `app/modules/infra/models/__init__.py`

- [ ] **Step 1: Center 모델 생성**

```python
# app/modules/infra/models/center.py
from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class Center(TimestampMixin, Base):
    __tablename__ = "centers"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(ForeignKey("partners.id"), index=True)
    center_code: Mapped[str] = mapped_column(String(50))
    center_name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("partner_id", "center_code"),)
```

- [ ] **Step 2: Room 모델 생성**

```python
# app/modules/infra/models/room.py
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class Room(TimestampMixin, Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    center_id: Mapped[int] = mapped_column(
        ForeignKey("centers.id", ondelete="CASCADE"), index=True
    )
    room_code: Mapped[str] = mapped_column(String(50))
    room_name: Mapped[str] = mapped_column(String(200))
    grid_rows: Mapped[int] = mapped_column(Integer)
    grid_cols: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("center_id", "room_code"),
        CheckConstraint("grid_rows >= 1", name="ck_rooms_grid_rows_min"),
        CheckConstraint("grid_cols >= 1", name="ck_rooms_grid_cols_min"),
    )
```

- [ ] **Step 3: RoomZone 모델 생성**

```python
# app/modules/infra/models/room_zone.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class RoomZone(TimestampMixin, Base):
    __tablename__ = "room_zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    zone_name: Mapped[str] = mapped_column(String(100))
    start_row: Mapped[int] = mapped_column(Integer)
    start_col: Mapped[int] = mapped_column(Integer)
    end_row: Mapped[int] = mapped_column(Integer)
    end_col: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("room_id", "zone_name"),)
```

- [ ] **Step 4: RackPosition 모델 생성**

```python
# app/modules/infra/models/rack_position.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class RackPosition(TimestampMixin, Base):
    __tablename__ = "rack_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    row_no: Mapped[int] = mapped_column(Integer)
    col_no: Mapped[int] = mapped_column(Integer)
    rack_code: Mapped[str] = mapped_column(String(50))
    rack_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ru_size: Mapped[int] = mapped_column(Integer)
    face_direction: Mapped[str] = mapped_column(String(10))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("room_id", "row_no", "col_no"),
        UniqueConstraint("room_id", "rack_code"),
    )
```

- [ ] **Step 5: AssetRackMapping 모델 생성**

```python
# app/modules/infra/models/asset_rack_mapping.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetRackMapping(TimestampMixin, Base):
    __tablename__ = "asset_rack_mappings"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    rack_position_id: Mapped[int] = mapped_column(
        ForeignKey("rack_positions.id", ondelete="CASCADE"), index=True
    )
    ru_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ru_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("asset_id"),)
```

- [ ] **Step 6: AssetAlias 모델 생성**

```python
# app/modules/infra/models/asset_alias.py
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class AssetAlias(TimestampMixin, Base):
    __tablename__ = "asset_aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    alias_name: Mapped[str] = mapped_column(String(255), unique=True)
    alias_type: Mapped[str] = mapped_column(String(30))
    source_partner_id: Mapped[int | None] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 7: models/__init__.py에 6개 모델 등록**

`app/modules/infra/models/__init__.py`에 import 및 `__all__` 추가:
```python
from app.modules.infra.models.center import Center
from app.modules.infra.models.room import Room
from app.modules.infra.models.room_zone import RoomZone
from app.modules.infra.models.rack_position import RackPosition
from app.modules.infra.models.asset_rack_mapping import AssetRackMapping
from app.modules.infra.models.asset_alias import AssetAlias
```

- [ ] **Step 8: 커밋**

```bash
git add app/modules/infra/models/center.py app/modules/infra/models/room.py \
  app/modules/infra/models/room_zone.py app/modules/infra/models/rack_position.py \
  app/modules/infra/models/asset_rack_mapping.py app/modules/infra/models/asset_alias.py \
  app/modules/infra/models/__init__.py
git commit -m "feat(infra): add 6 layout/alias models"
```

---

## Task 2: Alembic Migration

**Files:**
- Create: `alembic/versions/0013_layout_and_alias_tables.py`

- [ ] **Step 1: Migration 자동 생성**

```bash
alembic revision --autogenerate -m "add layout and alias tables"
```

- [ ] **Step 2: 생성된 migration 파일 검증 및 수정**

- revision을 `"0013"`으로, down_revision을 `"0012"`로 설정
- 파일명을 `0013_layout_and_alias_tables.py`로 변경
- 6개 테이블 + 제약조건 확인: centers, rooms, room_zones, rack_positions, asset_rack_mappings, asset_aliases
- CheckConstraint 2개 (ck_rooms_grid_rows_min, ck_rooms_grid_cols_min) 포함 확인

- [ ] **Step 3: Migration 적용**

```bash
alembic upgrade head
```

- [ ] **Step 4: 커밋**

```bash
git add alembic/versions/0013_layout_and_alias_tables.py
git commit -m "migration(0013): add layout and alias tables"
```

---

## Task 3: 스키마 6종 생성

**Files:**
- Create: `app/modules/infra/schemas/center.py`
- Create: `app/modules/infra/schemas/room.py`
- Create: `app/modules/infra/schemas/room_zone.py`
- Create: `app/modules/infra/schemas/rack_position.py`
- Create: `app/modules/infra/schemas/asset_rack_mapping.py`
- Create: `app/modules/infra/schemas/asset_alias.py`

각 스키마는 기존 패턴(`asset_contact.py` 참조)에 따라 Create/Update/Read 3종 구성.

- [ ] **Step 1: Center 스키마**

```python
# app/modules/infra/schemas/center.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CenterCreate(BaseModel):
    partner_id: int
    center_code: str
    center_name: str
    address: str | None = None
    note: str | None = None


class CenterUpdate(BaseModel):
    center_code: str | None = None
    center_name: str | None = None
    address: str | None = None
    note: str | None = None


class CenterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    partner_id: int
    center_code: str
    center_name: str
    address: str | None
    note: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 2: Room 스키마**

```python
# app/modules/infra/schemas/room.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator


class RoomCreate(BaseModel):
    center_id: int
    room_code: str
    room_name: str
    grid_rows: int
    grid_cols: int
    note: str | None = None

    @field_validator("grid_rows", "grid_cols")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("must be >= 1")
        return v


class RoomUpdate(BaseModel):
    room_code: str | None = None
    room_name: str | None = None
    grid_rows: int | None = None
    grid_cols: int | None = None
    note: str | None = None

    @field_validator("grid_rows", "grid_cols")
    @classmethod
    def must_be_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("must be >= 1")
        return v


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    center_id: int
    room_code: str
    room_name: str
    grid_rows: int
    grid_cols: int
    note: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: RoomZone 스키마**

```python
# app/modules/infra/schemas/room_zone.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class RoomZoneCreate(BaseModel):
    room_id: int
    zone_name: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    note: str | None = None


class RoomZoneUpdate(BaseModel):
    zone_name: str | None = None
    start_row: int | None = None
    start_col: int | None = None
    end_row: int | None = None
    end_col: int | None = None
    note: str | None = None


class RoomZoneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    zone_name: str
    start_row: int
    start_col: int
    end_row: int
    end_col: int
    note: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 4: RackPosition 스키마 (FaceDirection Enum 포함)**

```python
# app/modules/infra/schemas/rack_position.py
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict


class FaceDirection(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class RackPositionCreate(BaseModel):
    room_id: int
    row_no: int
    col_no: int
    rack_code: str
    rack_name: str | None = None
    ru_size: int
    face_direction: FaceDirection
    note: str | None = None


class RackPositionUpdate(BaseModel):
    rack_code: str | None = None
    rack_name: str | None = None
    ru_size: int | None = None
    face_direction: FaceDirection | None = None
    note: str | None = None


class RackPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    row_no: int
    col_no: int
    rack_code: str
    rack_name: str | None
    ru_size: int
    face_direction: str
    note: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 5: AssetRackMapping 스키마**

```python
# app/modules/infra/schemas/asset_rack_mapping.py
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AssetRackMappingCreate(BaseModel):
    asset_id: int
    rack_position_id: int
    ru_start: int | None = None
    ru_end: int | None = None
    note: str | None = None


class AssetRackMappingUpdate(BaseModel):
    ru_start: int | None = None
    ru_end: int | None = None
    note: str | None = None


class AssetRackMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    rack_position_id: int
    ru_start: int | None
    ru_end: int | None
    note: str | None
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 6: AssetAlias 스키마 (AliasType Enum 포함)**

```python
# app/modules/infra/schemas/asset_alias.py
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict


class AliasType(str, Enum):
    INTERNAL = "INTERNAL"
    CUSTOMER = "CUSTOMER"
    VENDOR = "VENDOR"
    TEAM = "TEAM"
    LEGACY = "LEGACY"
    ETC = "ETC"


class AssetAliasCreate(BaseModel):
    asset_id: int
    alias_name: str
    alias_type: AliasType
    source_partner_id: int | None = None
    source_text: str | None = None
    note: str | None = None
    is_primary: bool = False


class AssetAliasUpdate(BaseModel):
    alias_name: str | None = None
    alias_type: AliasType | None = None
    source_partner_id: int | None = None
    source_text: str | None = None
    note: str | None = None
    is_primary: bool | None = None


class AssetAliasRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    asset_id: int
    alias_name: str
    alias_type: str
    source_partner_id: int | None
    source_text: str | None
    note: str | None
    is_primary: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 7: 커밋**

```bash
git add app/modules/infra/schemas/center.py app/modules/infra/schemas/room.py \
  app/modules/infra/schemas/room_zone.py app/modules/infra/schemas/rack_position.py \
  app/modules/infra/schemas/asset_rack_mapping.py app/modules/infra/schemas/asset_alias.py
git commit -m "feat(infra): add schemas for layout/alias entities"
```

---

## Task 4: 서비스 생성 (기본 CRUD)

**Files:**
- Create: `app/modules/infra/services/center_service.py`
- Create: `app/modules/infra/services/room_service.py`
- Create: `app/modules/infra/services/layout_service.py`
- Create: `app/modules/infra/services/asset_alias_service.py`

모든 서비스는 `asset_software_service.py` 패턴을 따른다: `_require_edit(current_user: User)` → `_ensure_parent_exists(db, id)` → CRUD → `audit.log(module="infra")` → commit.

- [ ] **Step 1: center_service.py — Center CRUD**

```python
# app/modules/infra/services/center_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.center import Center
from app.modules.infra.schemas.center import CenterCreate, CenterUpdate
from app.modules.infra.services._helpers import ensure_partner_exists


def _require_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("편집 권한이 없습니다")


def list_centers(db: Session, partner_id: int) -> list[Center]:
    return list(db.scalars(
        select(Center).where(Center.partner_id == partner_id).order_by(Center.center_code)
    ))


def get_center(db: Session, center_id: int) -> Center:
    center = db.get(Center, center_id)
    if not center:
        raise NotFoundError("센터를 찾을 수 없습니다")
    return center


def create_center(db: Session, payload: CenterCreate, current_user: User) -> Center:
    _require_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)
    existing = db.scalars(
        select(Center).where(
            Center.partner_id == payload.partner_id,
            Center.center_code == payload.center_code,
        )
    ).first()
    if existing:
        raise DuplicateError(f"센터 코드 '{payload.center_code}'가 이미 존재합니다")
    center = Center(**payload.model_dump())
    db.add(center)
    audit.log(db, user_id=current_user.id, action="create", module="infra",
              entity_type="center", entity_id=None, summary=f"센터 생성: {payload.center_name}")
    db.commit()
    db.refresh(center)
    return center


def update_center(db: Session, center_id: int, payload: CenterUpdate, current_user: User) -> Center:
    _require_edit(current_user)
    center = get_center(db, center_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(center, k, v)
    audit.log(db, user_id=current_user.id, action="update", module="infra",
              entity_type="center", entity_id=center_id, summary=f"센터 수정: {center.center_name}")
    db.commit()
    db.refresh(center)
    return center


def delete_center(db: Session, center_id: int, current_user: User) -> None:
    _require_edit(current_user)
    center = get_center(db, center_id)
    audit.log(db, user_id=current_user.id, action="delete", module="infra",
              entity_type="center", entity_id=center_id, summary=f"센터 삭제: {center.center_name}")
    db.delete(center)
    db.commit()
```

- [ ] **Step 2: room_service.py — Room CRUD**

`center_service.py`와 동일 패턴:
```python
# app/modules/infra/services/room_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.center import Center
from app.modules.infra.models.room import Room
from app.modules.infra.schemas.room import RoomCreate, RoomUpdate


def _require_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("편집 권한이 없습니다")


def _ensure_center_exists(db: Session, center_id: int) -> Center:
    center = db.get(Center, center_id)
    if not center:
        raise NotFoundError("센터를 찾을 수 없습니다")
    return center


def list_rooms(db: Session, center_id: int) -> list[Room]:
    _ensure_center_exists(db, center_id)
    return list(db.scalars(
        select(Room).where(Room.center_id == center_id).order_by(Room.room_code)
    ))


def get_room(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if not room:
        raise NotFoundError("전산실을 찾을 수 없습니다")
    return room


def create_room(db: Session, payload: RoomCreate, current_user: User) -> Room:
    _require_edit(current_user)
    _ensure_center_exists(db, payload.center_id)
    existing = db.scalars(
        select(Room).where(
            Room.center_id == payload.center_id, Room.room_code == payload.room_code,
        )
    ).first()
    if existing:
        raise DuplicateError(f"전산실 코드 '{payload.room_code}'가 이미 존재합니다")
    room = Room(**payload.model_dump())
    db.add(room)
    audit.log(db, user_id=current_user.id, action="create", module="infra",
              entity_type="room", entity_id=None, summary=f"전산실 생성: {payload.room_name}")
    db.commit()
    db.refresh(room)
    return room


def update_room(db: Session, room_id: int, payload: RoomUpdate, current_user: User) -> Room:
    _require_edit(current_user)
    room = get_room(db, room_id)
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(room, k, v)
    audit.log(db, user_id=current_user.id, action="update", module="infra",
              entity_type="room", entity_id=room_id, summary=f"전산실 수정: {room.room_name}")
    db.commit()
    db.refresh(room)
    return room


def delete_room(db: Session, room_id: int, current_user: User) -> None:
    _require_edit(current_user)
    room = get_room(db, room_id)
    audit.log(db, user_id=current_user.id, action="delete", module="infra",
              entity_type="room", entity_id=room_id, summary=f"전산실 삭제: {room.room_name}")
    db.delete(room)
    db.commit()
```

- [ ] **Step 3: layout_service.py — Zone/Rack/Mapping CRUD + 자동매핑 + 레이아웃 조회**

```python
# app/modules/infra/services/layout_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import (
    BusinessRuleError, DuplicateError, NotFoundError, PermissionDeniedError,
)
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_rack_mapping import AssetRackMapping
from app.modules.infra.models.center import Center
from app.modules.infra.models.rack_position import RackPosition
from app.modules.infra.models.room import Room
from app.modules.infra.models.room_zone import RoomZone
from app.modules.infra.schemas.asset_rack_mapping import AssetRackMappingCreate, AssetRackMappingUpdate
from app.modules.infra.schemas.rack_position import RackPositionCreate, RackPositionUpdate
from app.modules.infra.schemas.room_zone import RoomZoneCreate, RoomZoneUpdate


def _require_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("편집 권한이 없습니다")


def _ensure_room_exists(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if not room:
        raise NotFoundError("전산실을 찾을 수 없습니다")
    return room


# ── Zone ──

def _check_zone_overlap(
    db: Session, room_id: int, sr: int, sc: int, er: int, ec: int,
    exclude_id: int | None = None,
) -> None:
    stmt = select(RoomZone).where(
        RoomZone.room_id == room_id,
        RoomZone.start_row <= er, RoomZone.end_row >= sr,
        RoomZone.start_col <= ec, RoomZone.end_col >= sc,
    )
    if exclude_id:
        stmt = stmt.where(RoomZone.id != exclude_id)
    overlap = db.scalars(stmt).first()
    if overlap:
        raise BusinessRuleError(f"영역 '{overlap.zone_name}'과 겹칩니다")


def list_zones(db: Session, room_id: int) -> list[RoomZone]:
    return list(db.scalars(
        select(RoomZone).where(RoomZone.room_id == room_id).order_by(RoomZone.zone_name)
    ))


def create_zone(db: Session, payload: RoomZoneCreate, current_user: User) -> RoomZone:
    _require_edit(current_user)
    _ensure_room_exists(db, payload.room_id)
    _check_zone_overlap(db, payload.room_id, payload.start_row, payload.start_col, payload.end_row, payload.end_col)
    zone = RoomZone(**payload.model_dump())
    db.add(zone)
    audit.log(db, user_id=current_user.id, action="create", module="infra",
              entity_type="room_zone", entity_id=None, summary=f"영역 생성: {payload.zone_name}")
    db.commit()
    db.refresh(zone)
    return zone


def update_zone(db: Session, zone_id: int, payload: RoomZoneUpdate, current_user: User) -> RoomZone:
    _require_edit(current_user)
    zone = db.get(RoomZone, zone_id)
    if not zone:
        raise NotFoundError("영역을 찾을 수 없습니다")
    data = payload.model_dump(exclude_unset=True)
    sr = data.get("start_row", zone.start_row)
    sc = data.get("start_col", zone.start_col)
    er = data.get("end_row", zone.end_row)
    ec = data.get("end_col", zone.end_col)
    _check_zone_overlap(db, zone.room_id, sr, sc, er, ec, exclude_id=zone_id)
    for k, v in data.items():
        setattr(zone, k, v)
    audit.log(db, user_id=current_user.id, action="update", module="infra",
              entity_type="room_zone", entity_id=zone_id, summary=f"영역 수정: {zone.zone_name}")
    db.commit()
    db.refresh(zone)
    return zone


def delete_zone(db: Session, zone_id: int, current_user: User) -> None:
    _require_edit(current_user)
    zone = db.get(RoomZone, zone_id)
    if not zone:
        raise NotFoundError("영역을 찾을 수 없습니다")
    audit.log(db, user_id=current_user.id, action="delete", module="infra",
              entity_type="room_zone", entity_id=zone_id, summary=f"영역 삭제: {zone.zone_name}")
    db.delete(zone)
    db.commit()


# ── RackPosition ──

def list_racks(db: Session, room_id: int) -> list[RackPosition]:
    return list(db.scalars(
        select(RackPosition).where(RackPosition.room_id == room_id).order_by(RackPosition.rack_code)
    ))


def create_rack(db: Session, payload: RackPositionCreate, current_user: User) -> RackPosition:
    _require_edit(current_user)
    _ensure_room_exists(db, payload.room_id)
    # 셀 중복 체크
    existing = db.scalars(
        select(RackPosition).where(
            RackPosition.room_id == payload.room_id,
            RackPosition.row_no == payload.row_no,
            RackPosition.col_no == payload.col_no,
        )
    ).first()
    if existing:
        raise DuplicateError(f"셀 ({payload.row_no}, {payload.col_no})에 이미 랙이 있습니다")
    rack = RackPosition(**payload.model_dump())
    db.add(rack)
    audit.log(db, user_id=current_user.id, action="create", module="infra",
              entity_type="rack_position", entity_id=None, summary=f"랙 등록: {payload.rack_code}")
    db.commit()
    db.refresh(rack)
    return rack


def update_rack(db: Session, rack_id: int, payload: RackPositionUpdate, current_user: User) -> RackPosition:
    _require_edit(current_user)
    rack = db.get(RackPosition, rack_id)
    if not rack:
        raise NotFoundError("랙을 찾을 수 없습니다")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(rack, k, v)
    audit.log(db, user_id=current_user.id, action="update", module="infra",
              entity_type="rack_position", entity_id=rack_id, summary=f"랙 수정: {rack.rack_code}")
    db.commit()
    db.refresh(rack)
    return rack


def delete_rack(db: Session, rack_id: int, current_user: User) -> None:
    _require_edit(current_user)
    rack = db.get(RackPosition, rack_id)
    if not rack:
        raise NotFoundError("랙을 찾을 수 없습니다")
    audit.log(db, user_id=current_user.id, action="delete", module="infra",
              entity_type="rack_position", entity_id=rack_id, summary=f"랙 삭제: {rack.rack_code}")
    db.delete(rack)
    db.commit()


# ── AssetRackMapping ──

def _check_ru_overlap(
    db: Session, rack_position_id: int,
    ru_start: int | None, ru_end: int | None,
    exclude_id: int | None = None,
) -> str | None:
    """RU 겹침 검사. 충돌 시 경고 메시지 반환 (저장은 허용)."""
    if ru_start is None or ru_end is None:
        return None
    stmt = select(AssetRackMapping).where(
        AssetRackMapping.rack_position_id == rack_position_id,
        AssetRackMapping.ru_start.isnot(None),
        AssetRackMapping.ru_end.isnot(None),
        AssetRackMapping.ru_start <= ru_end,
        AssetRackMapping.ru_end >= ru_start,
    )
    if exclude_id:
        stmt = stmt.where(AssetRackMapping.id != exclude_id)
    conflict = db.scalars(stmt).first()
    if conflict:
        return f"RU {ru_start}-{ru_end} 범위가 기존 매핑(asset_id={conflict.asset_id})과 겹칩니다"
    return None


def list_rack_mappings(db: Session, rack_position_id: int) -> list[AssetRackMapping]:
    return list(db.scalars(
        select(AssetRackMapping).where(
            AssetRackMapping.rack_position_id == rack_position_id
        )
    ))


def create_rack_mapping(
    db: Session, payload: AssetRackMappingCreate, current_user: User,
) -> tuple[AssetRackMapping, str | None]:
    """매핑 생성. RU 충돌 시 경고 메시지와 함께 반환 (저장은 진행)."""
    _require_edit(current_user)
    warning = _check_ru_overlap(db, payload.rack_position_id, payload.ru_start, payload.ru_end)
    mapping = AssetRackMapping(**payload.model_dump())
    db.add(mapping)
    audit.log(db, user_id=current_user.id, action="create", module="infra",
              entity_type="asset_rack_mapping", entity_id=None,
              summary=f"자산-랙 매핑: asset={payload.asset_id} → rack={payload.rack_position_id}")
    db.commit()
    db.refresh(mapping)
    return mapping, warning


def update_rack_mapping(
    db: Session, mapping_id: int, payload: AssetRackMappingUpdate, current_user: User,
) -> tuple[AssetRackMapping, str | None]:
    _require_edit(current_user)
    mapping = db.get(AssetRackMapping, mapping_id)
    if not mapping:
        raise NotFoundError("매핑을 찾을 수 없습니다")
    data = payload.model_dump(exclude_unset=True)
    ru_start = data.get("ru_start", mapping.ru_start)
    ru_end = data.get("ru_end", mapping.ru_end)
    warning = _check_ru_overlap(db, mapping.rack_position_id, ru_start, ru_end, exclude_id=mapping_id)
    for k, v in data.items():
        setattr(mapping, k, v)
    audit.log(db, user_id=current_user.id, action="update", module="infra",
              entity_type="asset_rack_mapping", entity_id=mapping_id, summary="자산-랙 매핑 수정")
    db.commit()
    db.refresh(mapping)
    return mapping, warning


def delete_rack_mapping(db: Session, mapping_id: int, current_user: User) -> None:
    _require_edit(current_user)
    mapping = db.get(AssetRackMapping, mapping_id)
    if not mapping:
        raise NotFoundError("매핑을 찾을 수 없습니다")
    audit.log(db, user_id=current_user.id, action="delete", module="infra",
              entity_type="asset_rack_mapping", entity_id=mapping_id, summary="자산-랙 매핑 삭제")
    db.delete(mapping)
    db.commit()


# ── Layout 일괄 조회 ──

def get_room_layout(db: Session, room_id: int) -> dict:
    """전산실의 zone + rack + mapping을 한 번에 조회."""
    room = _ensure_room_exists(db, room_id)
    zones = list(db.scalars(select(RoomZone).where(RoomZone.room_id == room_id)))
    racks = list(db.scalars(select(RackPosition).where(RackPosition.room_id == room_id)))
    rack_ids = [r.id for r in racks]
    mappings = []
    if rack_ids:
        mappings = list(db.scalars(
            select(AssetRackMapping).where(AssetRackMapping.rack_position_id.in_(rack_ids))
        ))
    return {"room": room, "zones": zones, "racks": racks, "mappings": mappings}


# ── 자동 매핑 ──

def auto_map_assets(db: Session, room_id: int, current_user: User) -> dict:
    """Asset.center/rack_no 문자열 ↔ Center.center_code/RackPosition.rack_code 완전일치 매핑."""
    _require_edit(current_user)
    room = _ensure_room_exists(db, room_id)
    center = db.get(Center, room.center_id)
    racks = list(db.scalars(select(RackPosition).where(RackPosition.room_id == room_id)))
    if not racks:
        return {"mapped": 0, "skipped": 0}

    rack_map = {r.rack_code: r for r in racks}
    existing = set(db.scalars(
        select(AssetRackMapping.asset_id).where(
            AssetRackMapping.rack_position_id.in_([r.id for r in racks])
        )
    ))

    # 1순위: center + rack_no 완전일치
    candidates = list(db.scalars(
        select(Asset).where(
            Asset.center == center.center_code,
            Asset.rack_no.in_(list(rack_map.keys())),
        )
    ))
    # 2순위: rack_no만 일치 (center 미기재)
    candidates.extend(db.scalars(
        select(Asset).where(
            (Asset.center.is_(None)) | (Asset.center == ""),
            Asset.rack_no.in_(list(rack_map.keys())),
        )
    ))

    mapped_count = 0
    skipped_count = 0
    for asset in candidates:
        if asset.id in existing:
            skipped_count += 1
            continue
        rack = rack_map.get(asset.rack_no)
        if not rack:
            continue
        db.add(AssetRackMapping(asset_id=asset.id, rack_position_id=rack.id))
        existing.add(asset.id)
        mapped_count += 1

    if mapped_count > 0:
        audit.log(db, user_id=current_user.id, action="auto_map", module="infra",
                  entity_type="asset_rack_mapping", entity_id=room_id,
                  summary=f"자동 매핑: {mapped_count}건 매핑, {skipped_count}건 스킵")
        db.commit()
    return {"mapped": mapped_count, "skipped": skipped_count}
```

- [ ] **Step 4: asset_alias_service.py — AssetAlias CRUD**

```python
# app/modules/infra/services/asset_alias_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.authorization import can_edit_inventory
from app.core.exceptions import DuplicateError, NotFoundError, PermissionDeniedError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.asset_alias import AssetAlias
from app.modules.infra.schemas.asset_alias import AssetAliasCreate, AssetAliasUpdate


def _require_edit(current_user: User) -> None:
    if not can_edit_inventory(current_user):
        raise PermissionDeniedError("편집 권한이 없습니다")


def _ensure_asset_exists(db: Session, asset_id: int) -> None:
    if not db.get(Asset, asset_id):
        raise NotFoundError("자산을 찾을 수 없습니다")


def _check_alias_unique(db: Session, alias_name: str, exclude_id: int | None = None) -> None:
    stmt = select(AssetAlias).where(AssetAlias.alias_name == alias_name)
    if exclude_id:
        stmt = stmt.where(AssetAlias.id != exclude_id)
    if db.scalars(stmt).first():
        raise DuplicateError(f"별칭 '{alias_name}'이 이미 사용 중입니다")


def list_asset_aliases(db: Session, asset_id: int) -> list[AssetAlias]:
    _ensure_asset_exists(db, asset_id)
    return list(db.scalars(
        select(AssetAlias).where(AssetAlias.asset_id == asset_id)
        .order_by(AssetAlias.is_primary.desc(), AssetAlias.alias_name)
    ))


def create_asset_alias(db: Session, payload: AssetAliasCreate, current_user: User) -> AssetAlias:
    _require_edit(current_user)
    _ensure_asset_exists(db, payload.asset_id)
    _check_alias_unique(db, payload.alias_name)
    alias = AssetAlias(**payload.model_dump())
    db.add(alias)
    audit.log(db, user_id=current_user.id, action="create", module="infra",
              entity_type="asset_alias", entity_id=None,
              summary=f"별칭 생성: {payload.alias_name} (asset={payload.asset_id})")
    db.commit()
    db.refresh(alias)
    return alias


def update_asset_alias(db: Session, alias_id: int, payload: AssetAliasUpdate, current_user: User) -> AssetAlias:
    _require_edit(current_user)
    alias = db.get(AssetAlias, alias_id)
    if not alias:
        raise NotFoundError("별칭을 찾을 수 없습니다")
    data = payload.model_dump(exclude_unset=True)
    if "alias_name" in data:
        _check_alias_unique(db, data["alias_name"], exclude_id=alias_id)
    for k, v in data.items():
        setattr(alias, k, v)
    audit.log(db, user_id=current_user.id, action="update", module="infra",
              entity_type="asset_alias", entity_id=alias_id,
              summary=f"별칭 수정: {alias.alias_name}")
    db.commit()
    db.refresh(alias)
    return alias


def delete_asset_alias(db: Session, alias_id: int, current_user: User) -> None:
    _require_edit(current_user)
    alias = db.get(AssetAlias, alias_id)
    if not alias:
        raise NotFoundError("별칭을 찾을 수 없습니다")
    audit.log(db, user_id=current_user.id, action="delete", module="infra",
              entity_type="asset_alias", entity_id=alias_id,
              summary=f"별칭 삭제: {alias.alias_name}")
    db.delete(alias)
    db.commit()
```

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/services/center_service.py app/modules/infra/services/room_service.py \
  app/modules/infra/services/layout_service.py app/modules/infra/services/asset_alias_service.py
git commit -m "feat(infra): add layout/alias services with full CRUD"
```

---

## Task 5: API 라우터 생성

**Files:**
- Create: `app/modules/infra/routers/centers.py`
- Create: `app/modules/infra/routers/rooms.py`
- Create: `app/modules/infra/routers/room_zones.py`
- Create: `app/modules/infra/routers/rack_positions.py`
- Create: `app/modules/infra/routers/asset_rack_mappings.py`
- Create: `app/modules/infra/routers/layout.py` — room layout 일괄조회 + 자동매핑
- Create: `app/modules/infra/routers/asset_aliases.py`
- Modify: `app/modules/infra/routers/__init__.py`

패턴 참조: `asset_contacts.py` — nested GET/POST at parent, flat PATCH/DELETE

- [ ] **Step 1: centers.py 라우터**

```python
# app/modules/infra/routers/centers.py
from __future__ import annotations
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session
from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.schemas.center import CenterCreate, CenterRead, CenterUpdate
from app.modules.infra.services.center_service import (
    create_center, delete_center, list_centers, update_center,
)

router = APIRouter(tags=["infra-centers"])

@router.get("/api/v1/centers", response_model=list[CenterRead])
def list_centers_endpoint(
    partner_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user),
) -> list[CenterRead]:
    return list_centers(db, partner_id)

@router.post("/api/v1/centers", response_model=CenterRead, status_code=status.HTTP_201_CREATED)
def create_center_endpoint(
    payload: CenterCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user),
) -> CenterRead:
    return create_center(db, payload, current_user)

@router.patch("/api/v1/centers/{center_id}", response_model=CenterRead)
def update_center_endpoint(
    center_id: int, payload: CenterUpdate,
    db: Session = Depends(get_db), current_user=Depends(get_current_user),
) -> CenterRead:
    return update_center(db, center_id, payload, current_user)

@router.delete("/api/v1/centers/{center_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_center_endpoint(
    center_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user),
) -> Response:
    delete_center(db, center_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 2: rooms.py 라우터** — `GET /centers/{center_id}/rooms`, `POST`, `PATCH /rooms/{room_id}`, `DELETE`

- [ ] **Step 3: room_zones.py 라우터** — `GET /rooms/{room_id}/zones`, `POST`, `PATCH /room-zones/{zone_id}`, `DELETE`

- [ ] **Step 4: rack_positions.py 라우터** — `GET /rooms/{room_id}/racks`, `POST`, `PATCH /rack-positions/{rack_id}`, `DELETE`

- [ ] **Step 5: asset_rack_mappings.py 라우터** — `GET /rack-positions/{rack_id}/mappings`, `POST`, `PATCH /asset-rack-mappings/{mapping_id}`, `DELETE`

POST/PATCH 응답에 `warning` 필드 포함 (RU 충돌 경고):
```python
@router.post("/api/v1/rack-positions/{rack_id}/mappings", status_code=status.HTTP_201_CREATED)
def create_mapping_endpoint(...) -> dict:
    mapping, warning = create_rack_mapping(db, payload, current_user)
    result = AssetRackMappingRead.model_validate(mapping).model_dump()
    if warning:
        result["warning"] = warning
    return result
```

- [ ] **Step 6: layout.py 라우터** — room 레이아웃 일괄 조회 + 자동 매핑 (별도 파일)

```python
# app/modules/infra/routers/layout.py
from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.infra.services.layout_service import auto_map_assets, get_room_layout

router = APIRouter(tags=["infra-layout"])

@router.get("/api/v1/rooms/{room_id}/layout")
def room_layout_endpoint(
    room_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user),
) -> dict:
    return get_room_layout(db, room_id)

@router.post("/api/v1/rooms/{room_id}/auto-map")
def auto_map_endpoint(
    room_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user),
) -> dict:
    return auto_map_assets(db, room_id, current_user)
```

- [ ] **Step 7: asset_aliases.py 라우터** — `GET /assets/{asset_id}/aliases`, `POST`, `PATCH /asset-aliases/{alias_id}`, `DELETE`

- [ ] **Step 8: routers/__init__.py에 7개 라우터 등록**

```python
from app.modules.infra.routers.centers import router as centers_router
from app.modules.infra.routers.rooms import router as rooms_router
from app.modules.infra.routers.room_zones import router as room_zones_router
from app.modules.infra.routers.rack_positions import router as rack_positions_router
from app.modules.infra.routers.asset_rack_mappings import router as asset_rack_mappings_router
from app.modules.infra.routers.layout import router as layout_router
from app.modules.infra.routers.asset_aliases import router as asset_aliases_router

api_router.include_router(centers_router)
api_router.include_router(rooms_router)
api_router.include_router(room_zones_router)
api_router.include_router(rack_positions_router)
api_router.include_router(asset_rack_mappings_router)
api_router.include_router(layout_router)
api_router.include_router(asset_aliases_router)
```

- [ ] **Step 9: 커밋**

```bash
git add app/modules/infra/routers/centers.py app/modules/infra/routers/rooms.py \
  app/modules/infra/routers/room_zones.py app/modules/infra/routers/rack_positions.py \
  app/modules/infra/routers/asset_rack_mappings.py app/modules/infra/routers/layout.py \
  app/modules/infra/routers/asset_aliases.py app/modules/infra/routers/__init__.py
git commit -m "feat(infra): add layout/alias API routers"
```

---

## Task 6: 페이지 라우트 + 사이드바 + placeholder 템플릿

**Files:**
- Modify: `app/modules/infra/routers/pages.py`
- Modify: `app/templates/base.html`
- Create: `app/modules/infra/templates/infra_layout.html`

- [ ] **Step 1: pages.py에 layout 페이지 라우트 추가**

```python
@router.get("/layout", response_class=HTMLResponse)
def layout_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse(
        "infra_layout.html", {"request": request}
    )
```

- [ ] **Step 2: base.html 사이드바에 "배치도" 메뉴 추가**

인프라 메뉴(line 119-125)에서 Assets와 Contacts 사이에:
```html
<li><a href="/layout"><i data-lucide="layout-grid"></i><span>배치도<small>전산실 배치도</small></span></a></li>
```

sidebar active 그룹 매핑에 `/layout` 추가.

- [ ] **Step 3: infra_layout.html placeholder 템플릿 생성**

기존 `infra_assets.html` 구조 참조. 4개 탭(센터 관리 / 전산실 관리 / 배치도 편집 / 자산 매핑 현황)을 빈 컨테이너로 구성:

```html
{% extends "base.html" %}
{% block title %}전산실 배치도{% endblock %}
{% block content %}
<div class="page-header">
    <h2>전산실 배치도</h2>
</div>

<!-- 탭 네비게이션 -->
<ul class="tab-nav">
    <li class="active" data-tab="centers">센터 관리</li>
    <li data-tab="rooms">전산실 관리</li>
    <li data-tab="grid">배치도 편집</li>
    <li data-tab="mapping">자산 매핑 현황</li>
</ul>

<!-- 센터 관리 탭 -->
<div id="tab-centers" class="tab-content active">
    <p class="placeholder-text">센터 관리 — 구현 예정 (모듈 A)</p>
</div>

<!-- 전산실 관리 탭 -->
<div id="tab-rooms" class="tab-content">
    <p class="placeholder-text">전산실 관리 — 구현 예정 (모듈 A)</p>
</div>

<!-- 배치도 편집 탭 -->
<div id="tab-grid" class="tab-content">
    <p class="placeholder-text">배치도 편집 — 구현 예정 (모듈 B/C)</p>
</div>

<!-- 자산 매핑 현황 탭 -->
<div id="tab-mapping" class="tab-content">
    <p class="placeholder-text">자산 매핑 현황 — 구현 예정 (모듈 C)</p>
</div>

<script>
// 탭 전환 기본 로직
document.querySelectorAll('.tab-nav li').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab-nav li').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        tab.classList.add('active');
        document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
});
</script>
{% endblock %}
```

- [ ] **Step 4: 커밋**

```bash
git add app/modules/infra/routers/pages.py app/templates/base.html \
  app/modules/infra/templates/infra_layout.html
git commit -m "feat(infra): add layout page route, sidebar menu, and placeholder template"
```

---

## Task 7: 문서 갱신

**Files:**
- Modify: `docs/guidelines/infra.md` — 도메인 용어 추가
- Modify: `docs/PROJECT_STRUCTURE.md` — 새 파일 추가
- Modify: `docs/KNOWN_ISSUES.md` — 해당 시 업데이트

- [ ] **Step 1: infra.md에 도메인 용어 추가**

| 용어 | 설명 |
|---|---|
| Center (센터) | 데이터센터. partner_id 스코프 |
| Room (전산실) | 센터 내 전산실. 그리드 기반 배치도 |
| RoomZone (영역) | 전산실 내 논리적 영역 경계 |
| RackPosition (랙 위치) | 전산실 그리드 내 랙 위치 |
| AssetRackMapping (자산-랙 매핑) | 자산과 랙의 bridge 테이블 (Asset 원장과 느슨한 연결) |
| AssetAlias (자산 별칭) | 자산의 다양한 호칭 (INTERNAL/CUSTOMER/VENDOR/TEAM/LEGACY/ETC) |

- [ ] **Step 2: PROJECT_STRUCTURE.md 업데이트**

새로 생성된 파일들을 프로젝트 구조에 반영.

- [ ] **Step 3: 커밋**

```bash
git add docs/guidelines/infra.md docs/PROJECT_STRUCTURE.md
git commit -m "docs: add layout/alias domain terms and update project structure"
```

---

## 후속 모듈별 구현 가이드 (별도 세션)

Foundation 완료 후, 다음 모듈을 독립 세션에서 구현한다. 각 모듈은 DB/API가 이미 존재하므로 프론트엔드 + 서비스 보완에 집중.

### 모듈 A: 센터/전산실 CRUD 완성
- **범위:** 센터 관리 탭 + 전산실 관리 탭 AG Grid UI
- **의존:** Task 4-6의 center_service/room_service (이미 완성)
- **산출물:** 센터/전산실 목록/생성/수정/삭제 UI 동작

### 모듈 B: Zone/Rack 편집 + 그리드 캔버스
- **범위:** 배치도 편집 탭 — 그리드 렌더링, zone 드래그 생성, 랙 셀 클릭 등록
- **의존:** 모듈 A (센터/전산실 선택 가능해야 함)
- **산출물:** 그리드 캔버스에 zone/rack 표시 및 편집

### 모듈 C: 자산 매핑 + 자동 매핑 + 시각화
- **범위:** 자산 매핑 현황 탭, 자동 매핑 버튼, 매핑 상태 색상 시각화
- **의존:** 모듈 B (랙이 등록되어 있어야 매핑 가능)
- **산출물:** 매핑 상태별 색상, 자동 매핑, 미매핑 목록

### 모듈 D: Alias CRUD + 자산 검색 통합
- **범위:** 자산 상세 내 alias 섹션 UI + 자산 검색에 alias_name/asset_code 포함
- **의존:** 없음 (독립)
- **산출물:** Alias CRUD UI, 검색 시 alias 포함, source 연결 시각화 (정상색/회색)

### 모듈 순서 권장
- 모듈 D는 독립적이므로 아무 때나 진행 가능
- 모듈 A → B → C는 순차 의존
- 따라서: **모듈 A + D 병행 → 모듈 B → 모듈 C** 가 효율적
