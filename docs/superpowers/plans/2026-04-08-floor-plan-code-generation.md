# 전산실 상면도 고도화 + 시스템ID/프로젝트코드 자동생성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전산실 격자 기반 상면도 시각화 + 이원 코드 체계(system_id 자동생성 + project_code 템플릿 기반)를 구현한다.

**Architecture:** 기존 layout_service.py에 system_id 생성/cascade 로직과 RackLine CRUD를 추가한다. 프로젝트코드 생성은 별도 code_generation_service.py로 분리한다. 프론트엔드는 기존 infra_physical_layout.js의 전산실 뷰를 격자 상면도로 교체한다.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy / Alembic / Vanilla JS / HTML5 Drag&Drop

**Spec:** `docs/superpowers/specs/2026-04-08-floor-plan-code-generation-design.md`

---

## 파일 구조

### 생성할 파일

| 파일 | 역할 |
|------|------|
| `app/modules/infra/models/rack_line.py` | RackLine 모델 |
| `app/modules/infra/schemas/rack_line.py` | RackLine Pydantic 스키마 |
| `app/modules/infra/routers/rack_lines.py` | RackLine CRUD 라우터 |
| `app/modules/infra/services/code_generation_service.py` | system_id 생성/cascade + project_code 템플릿 파싱/일괄생성 |
| `alembic/versions/0069_floor_plan_and_code_system.py` | 마이그레이션 |
| `tests/infra/test_code_generation_service.py` | 코드 생성 서비스 테스트 |
| `tests/infra/test_rack_line_service.py` | RackLine CRUD 테스트 |

### 수정할 파일

| 파일 | 변경 내용 |
|------|----------|
| `app/modules/infra/models/center.py` | system_id, prefix, project_code 추가 |
| `app/modules/infra/models/room.py` | system_id, prefix, project_code, grid_cols, grid_rows 추가 |
| `app/modules/infra/models/rack.py` | system_id, project_code, rack_line_id, line_position 추가 |
| `app/modules/infra/models/asset.py` | asset_code → system_id rename, project_code 추가 |
| `app/modules/common/models/contract_period.py` | rack_project_code_template, asset_project_code_template 추가 |
| `app/modules/infra/models/__init__.py` | RackLine import 추가 |
| `app/modules/infra/schemas/center.py` | system_id, prefix, project_code 필드 |
| `app/modules/infra/schemas/room.py` | system_id, prefix, project_code, grid_cols, grid_rows 필드 |
| `app/modules/infra/schemas/rack.py` | system_id, project_code, rack_line_id, line_position 필드 |
| `app/modules/infra/schemas/asset.py` | asset_code → system_id, project_code 필드 |
| `app/modules/infra/services/layout_service.py` | system_id 자동생성 통합, RackLine CRUD |
| `app/modules/infra/services/asset_service.py` | asset_code → system_id rename |
| `app/modules/infra/routers/rooms.py` | rack-lines 하위 엔드포인트 등록 |
| `app/static/js/infra_physical_layout.js` | 격자 상면도 UI 전면 교체 |
| `app/static/css/infra_common.css` | 격자/라인/슬롯 스타일 추가 |
| `app/modules/infra/templates/infra_physical_layout.html` | 격자 컨테이너 마크업 |

### asset_code rename 영향 파일

| 파일 | 변경 내용 |
|------|----------|
| `app/modules/infra/models/asset_event.py` | asset_code_snapshot → system_id_snapshot |
| `app/modules/infra/schemas/asset_event.py` | 동일 rename |
| `app/modules/infra/services/asset_event_service.py` | 동일 rename |
| `app/modules/infra/services/period_partner_service.py` | 직렬화에서 asset_code → system_id |
| `app/modules/infra/services/asset_role_service.py` | 직렬화에서 asset_code → system_id |
| `app/static/js/infra_assets.js` | 그리드 컬럼/표시에서 asset_code → system_id |
| `app/static/js/infra_asset_roles.js` | 동일 rename |
| `app/static/js/infra_contacts.js` | 동일 rename |
| `tests/infra/test_asset_service.py` | 테스트 assertion rename |
| `tests/infra/test_asset_event_service.py` | 테스트 assertion rename |

---

## Task 1: Alembic 마이그레이션

**Files:**
- Create: `alembic/versions/0069_floor_plan_and_code_system.py`

- [ ] **Step 1: 마이그레이션 파일 작성**

```python
"""Add system_id/project_code to center/room/rack/asset, create rack_lines table,
rename asset_code to system_id.

Revision ID: 0069
Revises: 0068
"""
from alembic import op
import sqlalchemy as sa

revision = "0069"
down_revision = "0068"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Center ---
    op.add_column("centers", sa.Column("system_id", sa.String(100), nullable=True))
    op.add_column("centers", sa.Column("prefix", sa.String(10), nullable=True))
    op.add_column("centers", sa.Column("project_code", sa.String(100), nullable=True))
    op.create_index("ix_centers_system_id", "centers", ["system_id"], unique=True)

    # --- Room ---
    op.add_column("rooms", sa.Column("system_id", sa.String(100), nullable=True))
    op.add_column("rooms", sa.Column("prefix", sa.String(20), nullable=True))
    op.add_column("rooms", sa.Column("project_code", sa.String(100), nullable=True))
    op.add_column("rooms", sa.Column("grid_cols", sa.Integer(), nullable=False, server_default="10"))
    op.add_column("rooms", sa.Column("grid_rows", sa.Integer(), nullable=False, server_default="12"))
    op.create_index("ix_rooms_system_id", "rooms", ["system_id"], unique=True)

    # --- rack_lines table ---
    op.create_table(
        "rack_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("room_id", sa.Integer(), sa.ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("line_name", sa.String(50), nullable=False),
        sa.Column("col_index", sa.Integer(), nullable=False),
        sa.Column("slot_count", sa.Integer(), nullable=False),
        sa.Column("disabled_slots", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("prefix", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("room_id", "col_index", name="uq_rack_lines_room_col"),
    )

    # --- Rack ---
    op.add_column("racks", sa.Column("system_id", sa.String(100), nullable=True))
    op.add_column("racks", sa.Column("project_code", sa.String(100), nullable=True))
    op.add_column("racks", sa.Column("rack_line_id", sa.Integer(), sa.ForeignKey("rack_lines.id", ondelete="SET NULL"), nullable=True))
    op.add_column("racks", sa.Column("line_position", sa.Integer(), nullable=True))
    op.create_index("ix_racks_system_id", "racks", ["system_id"], unique=True)

    # --- Asset: rename asset_code -> system_id ---
    op.alter_column("assets", "asset_code", new_column_name="system_id")
    op.add_column("assets", sa.Column("project_code", sa.String(100), nullable=True))

    # --- Asset Event: rename asset_code_snapshot -> system_id_snapshot ---
    op.alter_column("asset_events", "asset_code_snapshot", new_column_name="system_id_snapshot")

    # --- ContractPeriod ---
    op.add_column("contract_periods", sa.Column("rack_project_code_template", sa.String(200), nullable=True))
    op.add_column("contract_periods", sa.Column("asset_project_code_template", sa.String(200), nullable=True))

    # --- Backfill system_id for centers ---
    op.execute("""
        UPDATE centers c
        SET system_id = p.partner_code || '-' || c.center_code
        FROM partners p
        WHERE c.partner_id = p.id
    """)

    # --- Backfill system_id for rooms ---
    op.execute("""
        UPDATE rooms r
        SET system_id = c.system_id || '-' || r.room_code
        FROM centers c
        WHERE r.center_id = c.id
    """)

    # --- Backfill system_id for racks ---
    op.execute("""
        UPDATE racks rk
        SET system_id = rm.system_id || '-' || rk.rack_code
        FROM rooms rm
        WHERE rk.room_id = rm.id
    """)


def downgrade() -> None:
    op.drop_column("contract_periods", "asset_project_code_template")
    op.drop_column("contract_periods", "rack_project_code_template")
    op.alter_column("asset_events", "system_id_snapshot", new_column_name="asset_code_snapshot")
    op.drop_column("assets", "project_code")
    op.alter_column("assets", "system_id", new_column_name="asset_code")
    op.drop_index("ix_racks_system_id", table_name="racks")
    op.drop_column("racks", "line_position")
    op.drop_column("racks", "rack_line_id")
    op.drop_column("racks", "project_code")
    op.drop_column("racks", "system_id")
    op.drop_table("rack_lines")
    op.drop_index("ix_rooms_system_id", table_name="rooms")
    op.drop_column("rooms", "grid_rows")
    op.drop_column("rooms", "grid_cols")
    op.drop_column("rooms", "project_code")
    op.drop_column("rooms", "prefix")
    op.drop_column("rooms", "system_id")
    op.drop_index("ix_centers_system_id", table_name="centers")
    op.drop_column("centers", "project_code")
    op.drop_column("centers", "prefix")
    op.drop_column("centers", "system_id")
```

- [ ] **Step 2: 마이그레이션 실행**

Run: `alembic upgrade head`
Expected: 성공, 기존 데이터의 system_id가 채워짐

- [ ] **Step 3: 커밋**

```bash
git add alembic/versions/0069_floor_plan_and_code_system.py
git commit -m "feat: add migration 0069 for floor plan and code system"
```

---

## Task 2: 모델 변경 (Center, Room, Rack, Asset, ContractPeriod)

**Files:**
- Modify: `app/modules/infra/models/center.py`
- Modify: `app/modules/infra/models/room.py`
- Modify: `app/modules/infra/models/rack.py`
- Modify: `app/modules/infra/models/asset.py`
- Modify: `app/modules/infra/models/asset_event.py`
- Modify: `app/modules/common/models/contract_period.py`

- [ ] **Step 1: Center 모델에 system_id, prefix, project_code 추가**

`app/modules/infra/models/center.py`에 추가:

```python
system_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

- [ ] **Step 2: Room 모델에 system_id, prefix, project_code, grid_cols, grid_rows 추가**

`app/modules/infra/models/room.py`에 추가:

```python
system_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
prefix: Mapped[str | None] = mapped_column(String(20), nullable=True)
project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
grid_cols: Mapped[int] = mapped_column(Integer, default=10)
grid_rows: Mapped[int] = mapped_column(Integer, default=12)
```

- [ ] **Step 3: Rack 모델에 system_id, project_code, rack_line_id, line_position 추가**

`app/modules/infra/models/rack.py`에 추가:

```python
system_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)
project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
rack_line_id: Mapped[int | None] = mapped_column(ForeignKey("rack_lines.id", ondelete="SET NULL"), nullable=True)
line_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

- [ ] **Step 4: Asset 모델 — asset_code → system_id rename, project_code 추가**

`app/modules/infra/models/asset.py`:

변경 전:
```python
asset_code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
```

변경 후:
```python
system_id: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True, index=True)
project_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

- [ ] **Step 5: AssetEvent 모델 — asset_code_snapshot → system_id_snapshot**

`app/modules/infra/models/asset_event.py`:
```python
# 변경 전
asset_code_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)
# 변경 후
system_id_snapshot: Mapped[str | None] = mapped_column(String(50), nullable=True)
```

- [ ] **Step 6: ContractPeriod 모델에 템플릿 필드 추가**

`app/modules/common/models/contract_period.py`에 추가:
```python
rack_project_code_template: Mapped[str | None] = mapped_column(String(200), nullable=True)
asset_project_code_template: Mapped[str | None] = mapped_column(String(200), nullable=True)
```

- [ ] **Step 7: 커밋**

```bash
git add app/modules/infra/models/center.py app/modules/infra/models/room.py \
  app/modules/infra/models/rack.py app/modules/infra/models/asset.py \
  app/modules/infra/models/asset_event.py app/modules/common/models/contract_period.py
git commit -m "feat: add system_id/project_code fields, rename asset_code"
```

---

## Task 3: RackLine 모델 + 스키마 + 모델 등록

**Files:**
- Create: `app/modules/infra/models/rack_line.py`
- Create: `app/modules/infra/schemas/rack_line.py`
- Modify: `app/modules/infra/models/__init__.py`

- [ ] **Step 1: RackLine 모델 작성**

```python
# app/modules/infra/models/rack_line.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import TimestampMixin
from app.core.database import Base


class RackLine(TimestampMixin, Base):
    __tablename__ = "rack_lines"
    __table_args__ = (
        UniqueConstraint("room_id", "col_index", name="uq_rack_lines_room_col"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True
    )
    line_name: Mapped[str] = mapped_column(String(50))
    col_index: Mapped[int] = mapped_column(Integer)
    slot_count: Mapped[int] = mapped_column(Integer)
    disabled_slots: Mapped[list] = mapped_column(JSON, default=list)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    prefix: Mapped[str | None] = mapped_column(String(20), nullable=True)
```

- [ ] **Step 2: RackLine 스키마 작성**

```python
# app/modules/infra/schemas/rack_line.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RackLineCreate(BaseModel):
    line_name: str
    col_index: int
    slot_count: int
    disabled_slots: list[int] = []
    prefix: str | None = None


class RackLineUpdate(BaseModel):
    line_name: str | None = None
    col_index: int | None = None
    slot_count: int | None = None
    disabled_slots: list[int] | None = None
    prefix: str | None = None
    sort_order: int | None = None


class RackLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    line_name: str
    col_index: int
    slot_count: int
    disabled_slots: list[int]
    sort_order: int
    prefix: str | None = None
    racks: list[dict] = []
    created_at: datetime
    updated_at: datetime
```

- [ ] **Step 3: __init__.py에 RackLine 등록**

`app/modules/infra/models/__init__.py`에 추가:
```python
from app.modules.infra.models.rack_line import RackLine
```
`__all__`에 `"RackLine"` 추가.

- [ ] **Step 4: 커밋**

```bash
git add app/modules/infra/models/rack_line.py app/modules/infra/schemas/rack_line.py \
  app/modules/infra/models/__init__.py
git commit -m "feat: add RackLine model and schema"
```

---

## Task 4: 스키마 업데이트 (Center, Room, Rack, Asset)

**Files:**
- Modify: `app/modules/infra/schemas/center.py`
- Modify: `app/modules/infra/schemas/room.py`
- Modify: `app/modules/infra/schemas/rack.py`
- Modify: `app/modules/infra/schemas/asset.py`
- Modify: `app/modules/infra/schemas/asset_event.py`

- [ ] **Step 1: CenterCreate/Update/Read에 system_id, prefix, project_code 추가**

```python
# CenterCreate — prefix 추가 (system_id는 자동, project_code는 수동 입력 가능)
prefix: str | None = None
project_code: str | None = None

# CenterUpdate — prefix, project_code 추가
prefix: str | None = None
project_code: str | None = None

# CenterRead — system_id, prefix, project_code 추가
system_id: str | None = None
prefix: str | None = None
project_code: str | None = None
```

- [ ] **Step 2: RoomCreate/Update/Read에 필드 추가**

```python
# RoomCreate — prefix, grid_cols, grid_rows 추가
prefix: str | None = None
project_code: str | None = None
grid_cols: int = 10
grid_rows: int = 12

# RoomUpdate — prefix, project_code, grid_cols, grid_rows 추가
prefix: str | None = None
project_code: str | None = None
grid_cols: int | None = None
grid_rows: int | None = None

# RoomRead — system_id, prefix, project_code, grid_cols, grid_rows 추가
system_id: str | None = None
prefix: str | None = None
project_code: str | None = None
grid_cols: int = 10
grid_rows: int = 12
```

- [ ] **Step 3: RackCreate/Update/Read에 필드 추가**

```python
# RackUpdate — project_code 추가 (rack_line_id, line_position은 드래그로 설정)
project_code: str | None = None

# RackRead — system_id, project_code, rack_line_id, line_position 추가
system_id: str | None = None
project_code: str | None = None
rack_line_id: int | None = None
line_position: int | None = None
```

- [ ] **Step 4: Asset 스키마에서 asset_code → system_id rename, project_code 추가**

`app/modules/infra/schemas/asset.py`에서:
- 모든 `asset_code` 참조를 `system_id`로 변경
- `project_code: str | None = None` 추가 (AssetRead, AssetUpdate)
- AssetCreate에서 system_id 관련 필드 제거 (자동 생성이므로)

- [ ] **Step 5: AssetEvent 스키마 rename**

`app/modules/infra/schemas/asset_event.py`에서 `asset_code_snapshot` → `system_id_snapshot`

- [ ] **Step 6: 커밋**

```bash
git add app/modules/infra/schemas/
git commit -m "feat: update schemas for system_id/project_code fields"
```

---

## Task 5: asset_code → system_id rename (서비스 + 프론트엔드)

**Files:**
- Modify: `app/modules/infra/services/asset_service.py`
- Modify: `app/modules/infra/services/asset_event_service.py`
- Modify: `app/modules/infra/services/asset_role_service.py`
- Modify: `app/modules/infra/services/period_partner_service.py`
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/static/js/infra_asset_roles.js`
- Modify: `app/static/js/infra_contacts.js`
- Modify: `tests/infra/test_asset_service.py`
- Modify: `tests/infra/test_asset_event_service.py`

- [ ] **Step 1: asset_service.py에서 asset_code → system_id 일괄 변경**

주요 변경점:
- `_generate_asset_code()` → `_generate_system_id()`
- `changes.pop("asset_code", None)` → `changes.pop("system_id", None)`
- 검색 필터에서 `Asset.asset_code` → `Asset.system_id`
- 직렬화 dict에서 `"asset_code"` → `"system_id"`

- [ ] **Step 2: asset_event_service.py에서 asset_code_snapshot → system_id_snapshot**

- [ ] **Step 3: asset_role_service.py, period_partner_service.py 직렬화 rename**

- [ ] **Step 4: JS 파일 rename**

`infra_assets.js`:
- 그리드 컬럼 `field: "asset_code"` → `field: "system_id"`
- 헤더/라벨 텍스트에서 "자산코드" → "시스템ID"

`infra_asset_roles.js`, `infra_contacts.js`:
- `asset_code` 참조 → `system_id`

- [ ] **Step 5: 테스트 파일 rename**

`test_asset_service.py`, `test_asset_event_service.py`에서 `asset_code` 관련 assertion을 `system_id`로 변경

- [ ] **Step 6: 테스트 실행**

Run: `pytest tests/infra/test_asset_service.py tests/infra/test_asset_event_service.py -v`
Expected: PASS

- [ ] **Step 7: 커밋**

```bash
git add app/modules/infra/services/ app/static/js/ tests/infra/
git commit -m "refactor: rename asset_code to system_id across services and frontend"
```

---

## Task 6: system_id 자동생성 서비스 + 테스트

**Files:**
- Create: `app/modules/infra/services/code_generation_service.py`
- Create: `tests/infra/test_code_generation_service.py`

- [ ] **Step 1: 테스트 작성 — system_id 생성**

```python
# tests/infra/test_code_generation_service.py
import pytest
from app.modules.infra.services.code_generation_service import (
    build_center_system_id,
    build_room_system_id,
    build_rack_system_id,
    render_template,
    TEMPLATE_VARIABLES,
)


def test_build_center_system_id():
    assert build_center_system_id("P000", "C01") == "P000-C01"


def test_build_room_system_id():
    assert build_room_system_id("P000-C01", "R01") == "P000-C01-R01"


def test_build_rack_system_id():
    assert build_rack_system_id("P000-C01-R01", "A12") == "P000-C01-R01-A12"


def test_render_template_rack_project_code():
    context = {
        "center.prefix": "S",
        "room.prefix": "07A",
        "line.prefix": "A",
        "rack.position": "12",
    }
    result = render_template("{center.prefix}{room.prefix}-{line.prefix}{rack.position}", context)
    assert result == "S07A-A12"


def test_render_template_asset_project_code():
    context = {
        "rack.project_code": "S07A-A12",
        "unit": "41",
    }
    result = render_template("{rack.project_code}-{unit}", context)
    assert result == "S07A-A12-41"


def test_render_template_missing_prefix_returns_empty():
    context = {
        "center.prefix": "",
        "room.prefix": "07A",
        "line.prefix": "A",
        "rack.position": "12",
    }
    result = render_template("{center.prefix}{room.prefix}-{line.prefix}{rack.position}", context)
    assert result == "07A-A12"


def test_render_template_invalid_variable_raises():
    with pytest.raises(ValueError, match="지원하지 않는 템플릿 변수"):
        render_template("{invalid.var}", {})
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/infra/test_code_generation_service.py -v`
Expected: ImportError

- [ ] **Step 3: code_generation_service.py 구현**

```python
# app/modules/infra/services/code_generation_service.py
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.infra.models.center import Center
from app.modules.infra.models.rack import Rack
from app.modules.infra.models.rack_line import RackLine
from app.modules.infra.models.room import Room


TEMPLATE_VARIABLES = {
    "center.prefix",
    "room.prefix",
    "line.prefix",
    "rack.position",
    "rack.project_code",
    "unit",
}

_VAR_PATTERN = re.compile(r"\{([^}]+)\}")


def build_center_system_id(partner_code: str, center_code: str) -> str:
    return f"{partner_code}-{center_code}"


def build_room_system_id(center_system_id: str, room_code: str) -> str:
    return f"{center_system_id}-{room_code}"


def build_rack_system_id(room_system_id: str, rack_code: str) -> str:
    return f"{room_system_id}-{rack_code}"


def render_template(template: str, context: dict[str, str]) -> str:
    """템플릿 문자열의 {variable}을 context 값으로 치환한다."""
    variables = _VAR_PATTERN.findall(template)
    for var in variables:
        if var not in TEMPLATE_VARIABLES:
            raise ValueError(f"지원하지 않는 템플릿 변수: {{{var}}}")
    result = template
    for var in variables:
        value = context.get(var, "")
        result = result.replace(f"{{{var}}}", str(value))
    return result


def cascade_update_system_ids(db: Session, center: Center) -> None:
    """센터의 system_id가 변경되었을 때, 하위 전산실/랙의 system_id를 재귀 갱신한다."""
    rooms = list(db.scalars(select(Room).where(Room.center_id == center.id)))
    for room in rooms:
        room.system_id = build_room_system_id(center.system_id, room.room_code)
        racks = list(db.scalars(select(Rack).where(Rack.room_id == room.id)))
        for rack in racks:
            rack.system_id = build_rack_system_id(room.system_id, rack.rack_code)


def cascade_update_room_system_ids(db: Session, room: Room) -> None:
    """전산실의 system_id가 변경되었을 때, 하위 랙의 system_id를 재귀 갱신한다."""
    racks = list(db.scalars(select(Rack).where(Rack.room_id == room.id)))
    for rack in racks:
        rack.system_id = build_rack_system_id(room.system_id, rack.rack_code)


def preview_rack_codes(
    db: Session,
    template: str,
    room_ids: list[int],
) -> dict:
    """템플릿에 따라 변경 대상 목록을 반환한다 (미리보기)."""
    changes = []
    for room_id in room_ids:
        room = db.get(Room, room_id)
        if not room:
            continue
        center = db.get(Center, room.center_id)
        lines = list(db.scalars(select(RackLine).where(RackLine.room_id == room_id)))
        for line in lines:
            racks = list(db.scalars(
                select(Rack).where(Rack.rack_line_id == line.id)
            ))
            for rack in racks:
                context = {
                    "center.prefix": center.prefix or "",
                    "room.prefix": room.prefix or "",
                    "line.prefix": line.prefix or "",
                    "rack.position": str((rack.line_position or 0) + 1),
                }
                missing = [k for k, v in context.items() if not v and f"{{{k}}}" in template]
                generated = render_template(template, context) if not missing else None
                changes.append({
                    "id": rack.id,
                    "system_id": rack.system_id,
                    "current_project_code": rack.project_code,
                    "generated_project_code": generated,
                    "missing_fields": missing,
                })
    will_update = sum(1 for c in changes if c["generated_project_code"] is not None)
    return {
        "template": template,
        "changes": changes,
        "summary": {
            "total": len(changes),
            "will_update": will_update,
            "skipped": len(changes) - will_update,
        },
    }


def generate_rack_codes(
    db: Session,
    template: str,
    room_ids: list[int],
) -> dict:
    """템플릿에 따라 프로젝트코드를 일괄 적용한다."""
    preview = preview_rack_codes(db, template, room_ids)
    updated = 0
    for change in preview["changes"]:
        if change["generated_project_code"] is not None:
            rack = db.get(Rack, change["id"])
            if rack:
                rack.project_code = change["generated_project_code"]
                updated += 1
    db.commit()
    return {"updated": updated, "skipped": preview["summary"]["skipped"]}
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/infra/test_code_generation_service.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/services/code_generation_service.py \
  tests/infra/test_code_generation_service.py
git commit -m "feat: add code_generation_service with system_id and template rendering"
```

---

## Task 7: layout_service.py에 system_id 자동생성 통합

**Files:**
- Modify: `app/modules/infra/services/layout_service.py`

- [ ] **Step 1: create_center에 system_id 자동생성 통합**

`create_center()` 수정 — center 생성 직후 system_id 계산:

```python
from app.modules.infra.services.code_generation_service import (
    build_center_system_id,
    build_room_system_id,
    build_rack_system_id,
    cascade_update_system_ids,
    cascade_update_room_system_ids,
)

# create_center() 내부, db.flush() 이후:
partner = db.get(Partner, payload.partner_id)
center.system_id = build_center_system_id(partner.partner_code, center_code)
# default_room도 system_id 설정:
default_room.system_id = build_room_system_id(center.system_id, "MAIN")
```

- [ ] **Step 2: update_center에 system_id cascade 통합**

`update_center()` 수정 — center_code 변경 시 system_id 재계산 + cascade:

```python
# center_code가 변경되었으면 system_id 재계산
if next_code != center.center_code:
    partner = db.get(Partner, center.partner_id)
    # 기존 코드 유효성 검사 후...
    for field, value in changes.items():
        setattr(center, field, value)
    center.system_id = build_center_system_id(partner.partner_code, next_code)
    cascade_update_system_ids(db, center)
```

- [ ] **Step 3: create_room에 system_id 자동생성 통합**

```python
# create_room() 내부:
center = get_center(db, payload.center_id)
# room 생성 후:
room.system_id = build_room_system_id(center.system_id, room_code)
```

- [ ] **Step 4: update_room에 system_id cascade 통합**

```python
# room_code 변경 시:
center = get_center(db, room.center_id)
for field, value in changes.items():
    setattr(room, field, value)
room.system_id = build_room_system_id(center.system_id, next_code)
cascade_update_room_system_ids(db, room)
```

- [ ] **Step 5: create_rack, update_rack에 system_id 자동생성 통합**

```python
# create_rack() 내부:
room = get_room(db, payload.room_id)
rack.system_id = build_rack_system_id(room.system_id, rack_code)

# update_rack() 내부 — rack_code 변경 시:
room = get_room(db, rack.room_id)
rack.system_id = build_rack_system_id(room.system_id, next_code)
```

- [ ] **Step 6: list 함수들에 system_id, prefix, project_code 필드 추가**

`list_centers()`, `list_rooms()`, `list_racks()` 반환 dict에 추가:
```python
"system_id": center.system_id,
"prefix": center.prefix,
"project_code": center.project_code,
```

- [ ] **Step 7: 기존 layout_service 테스트 실행**

Run: `pytest tests/infra/test_layout_service.py -v`
Expected: PASS

- [ ] **Step 8: 커밋**

```bash
git add app/modules/infra/services/layout_service.py
git commit -m "feat: integrate system_id auto-generation into layout service"
```

---

## Task 8: RackLine CRUD 서비스 + 테스트

**Files:**
- Modify: `app/modules/infra/services/layout_service.py`
- Create: `tests/infra/test_rack_line_service.py`

- [ ] **Step 1: 테스트 작성 — RackLine CRUD**

```python
# tests/infra/test_rack_line_service.py
import pytest
from app.modules.infra.services.layout_service import (
    create_rack_line,
    list_rack_lines,
    update_rack_line,
    delete_rack_line,
    create_center,
    create_rack,
)
from app.modules.infra.schemas.rack_line import RackLineCreate
from app.modules.infra.schemas.rack import RackCreate
from app.modules.infra.schemas.center import CenterCreate
from app.core.exceptions import NotFoundError, DuplicateError


def _make_admin_user(db, admin_role_id):
    """test_layout_service.py의 _make_admin_user와 동일한 헬퍼."""
    from app.modules.common.models.user import User
    user = User(
        username="testadmin",
        display_name="Test Admin",
        password_hash="dummy",
        role_id=admin_role_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_partner(db):
    from app.modules.common.models.partner import Partner
    p = Partner(partner_code="T001", name="테스트사")
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_create_rack_line(db_session, admin_role_id):
    user = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    center = create_center(db_session, CenterCreate(
        partner_id=partner.id, center_name="센터A"
    ), user)
    from app.modules.infra.services.layout_service import list_rooms
    rooms = list_rooms(db_session, center.id)
    room_id = rooms[0]["id"]

    payload = RackLineCreate(line_name="A열", col_index=0, slot_count=12, prefix="A")
    line = create_rack_line(db_session, room_id, payload, user)

    assert line.line_name == "A열"
    assert line.col_index == 0
    assert line.slot_count == 12
    assert line.prefix == "A"
    assert line.disabled_slots == []


def test_create_rack_line_duplicate_col_raises(db_session, admin_role_id):
    user = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    center = create_center(db_session, CenterCreate(
        partner_id=partner.id, center_name="센터A"
    ), user)
    from app.modules.infra.services.layout_service import list_rooms
    rooms = list_rooms(db_session, center.id)
    room_id = rooms[0]["id"]

    payload = RackLineCreate(line_name="A열", col_index=0, slot_count=12)
    create_rack_line(db_session, room_id, payload, user)

    with pytest.raises(DuplicateError):
        create_rack_line(db_session, room_id, payload, user)


def test_list_rack_lines(db_session, admin_role_id):
    user = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    center = create_center(db_session, CenterCreate(
        partner_id=partner.id, center_name="센터A"
    ), user)
    from app.modules.infra.services.layout_service import list_rooms
    rooms = list_rooms(db_session, center.id)
    room_id = rooms[0]["id"]

    create_rack_line(db_session, room_id, RackLineCreate(
        line_name="A열", col_index=0, slot_count=12, prefix="A"
    ), user)

    lines = list_rack_lines(db_session, room_id)
    assert len(lines) == 1
    assert lines[0]["line_name"] == "A열"
    assert lines[0]["racks"] == []


def test_delete_rack_line_nullifies_rack(db_session, admin_role_id):
    user = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    center = create_center(db_session, CenterCreate(
        partner_id=partner.id, center_name="센터A"
    ), user)
    from app.modules.infra.services.layout_service import list_rooms
    rooms = list_rooms(db_session, center.id)
    room_id = rooms[0]["id"]

    line = create_rack_line(db_session, room_id, RackLineCreate(
        line_name="A열", col_index=0, slot_count=12
    ), user)
    rack = create_rack(db_session, RackCreate(room_id=room_id, rack_code="R01"), user)
    rack.rack_line_id = line.id
    rack.line_position = 0
    db_session.commit()

    delete_rack_line(db_session, line.id, user)
    db_session.refresh(rack)
    assert rack.rack_line_id is None
    assert rack.line_position is None
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `pytest tests/infra/test_rack_line_service.py -v`
Expected: ImportError (create_rack_line 미정의)

- [ ] **Step 3: layout_service.py에 RackLine CRUD 구현**

```python
from app.modules.infra.models.rack_line import RackLine
from app.modules.infra.schemas.rack_line import RackLineCreate, RackLineUpdate


def list_rack_lines(db: Session, room_id: int) -> list[dict]:
    """전산실의 라인 목록 (소속 랙 포함)."""
    room = get_room(db, room_id)
    lines = list(db.scalars(
        select(RackLine)
        .where(RackLine.room_id == room.id)
        .order_by(RackLine.col_index.asc())
    ))
    result = []
    for line in lines:
        racks = list(db.scalars(
            select(Rack)
            .where(Rack.rack_line_id == line.id)
            .order_by(Rack.line_position.asc().nullslast())
        ))
        result.append({
            "id": line.id,
            "room_id": line.room_id,
            "line_name": line.line_name,
            "col_index": line.col_index,
            "slot_count": line.slot_count,
            "disabled_slots": line.disabled_slots or [],
            "sort_order": line.sort_order,
            "prefix": line.prefix,
            "created_at": line.created_at,
            "updated_at": line.updated_at,
            "racks": [
                {
                    "id": r.id,
                    "rack_code": r.rack_code,
                    "rack_name": r.rack_name,
                    "system_id": r.system_id,
                    "project_code": r.project_code,
                    "line_position": r.line_position,
                    "total_units": r.total_units,
                }
                for r in racks
            ],
        })
    return result


def create_rack_line(db: Session, room_id: int, payload: RackLineCreate, current_user) -> RackLine:
    _require_inventory_edit(current_user)
    room = get_room(db, room_id)
    existing = db.scalar(
        select(RackLine).where(RackLine.room_id == room.id, RackLine.col_index == payload.col_index)
    )
    if existing:
        raise DuplicateError("같은 전산실에 이미 등록된 열 위치입니다.")
    if payload.col_index < 0 or payload.col_index >= room.grid_cols:
        raise BusinessRuleError("열 위치가 격자 범위를 벗어납니다.", status_code=422)
    line = RackLine(room_id=room.id, **payload.model_dump())
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_rack_line(db: Session, line_id: int, payload: RackLineUpdate, current_user) -> RackLine:
    _require_inventory_edit(current_user)
    line = db.get(RackLine, line_id)
    if line is None:
        raise NotFoundError("RackLine not found")
    changes = payload.model_dump(exclude_unset=True)
    next_col = changes.get("col_index", line.col_index)
    if next_col != line.col_index:
        existing = db.scalar(
            select(RackLine).where(
                RackLine.room_id == line.room_id, RackLine.col_index == next_col
            )
        )
        if existing and existing.id != line.id:
            raise DuplicateError("같은 전산실에 이미 등록된 열 위치입니다.")
    for field, value in changes.items():
        setattr(line, field, value)
    db.commit()
    db.refresh(line)
    return line


def delete_rack_line(db: Session, line_id: int, current_user) -> None:
    _require_inventory_edit(current_user)
    line = db.get(RackLine, line_id)
    if line is None:
        raise NotFoundError("RackLine not found")
    racks = list(db.scalars(select(Rack).where(Rack.rack_line_id == line.id)))
    for rack in racks:
        rack.rack_line_id = None
        rack.line_position = None
    db.delete(line)
    db.commit()
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `pytest tests/infra/test_rack_line_service.py -v`
Expected: ALL PASS

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/services/layout_service.py tests/infra/test_rack_line_service.py
git commit -m "feat: add RackLine CRUD to layout_service with tests"
```

---

## Task 9: RackLine 라우터

**Files:**
- Create: `app/modules/infra/routers/rack_lines.py`

- [ ] **Step 1: rack_lines 라우터 작성**

```python
# app/modules/infra/routers/rack_lines.py
from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.modules.common.models.user import User
from app.modules.infra.schemas.rack_line import RackLineCreate, RackLineUpdate
from app.modules.infra.services.layout_service import (
    create_rack_line,
    delete_rack_line,
    list_rack_lines,
    update_rack_line,
)

router = APIRouter(tags=["infra-rack-lines"])


@router.get("/api/v1/rooms/{room_id}/rack-lines")
def list_rack_lines_endpoint(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return list_rack_lines(db, room_id)


@router.post("/api/v1/rooms/{room_id}/rack-lines", status_code=status.HTTP_201_CREATED)
def create_rack_line_endpoint(
    room_id: int,
    payload: RackLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return create_rack_line(db, room_id, payload, current_user)


@router.patch("/api/v1/rack-lines/{line_id}")
def update_rack_line_endpoint(
    line_id: int,
    payload: RackLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return update_rack_line(db, line_id, payload, current_user)


@router.delete("/api/v1/rack-lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rack_line_endpoint(
    line_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_rack_line(db, line_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 2: 모듈 라우터 등록**

앱의 라우터 등록 파일에 `rack_lines.router`를 include.

- [ ] **Step 3: 커밋**

```bash
git add app/modules/infra/routers/rack_lines.py
git commit -m "feat: add rack-lines API endpoints"
```

---

## Task 10: 프로젝트코드 일괄생성 API

**Files:**
- Create: `app/modules/infra/routers/code_generation.py`

- [ ] **Step 1: 코드 생성 라우터 작성**

```python
# app/modules/infra/routers/code_generation.py
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.database import get_db
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.common.models.contract_period import ContractPeriod
from app.modules.common.models.user import User
from app.modules.infra.models.room import Room
from app.modules.infra.services.code_generation_service import (
    generate_rack_codes,
    preview_rack_codes,
)

router = APIRouter(tags=["infra-code-generation"])


@router.get("/api/v1/contract-periods/{period_id}/preview-codes")
def preview_codes_endpoint(
    period_id: int,
    target: str = "rack",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    period = db.get(ContractPeriod, period_id)
    if not period:
        raise NotFoundError("ContractPeriod not found")
    template = (
        period.rack_project_code_template if target == "rack"
        else period.asset_project_code_template
    )
    if not template:
        return {
            "template": None,
            "changes": [],
            "summary": {"total": 0, "will_update": 0, "skipped": 0},
        }
    room_ids = _get_period_room_ids(db, period)
    return preview_rack_codes(db, template, room_ids)


@router.post("/api/v1/contract-periods/{period_id}/generate-codes")
def generate_codes_endpoint(
    period_id: int,
    target: str = "rack",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    period = db.get(ContractPeriod, period_id)
    if not period:
        raise NotFoundError("ContractPeriod not found")
    template = (
        period.rack_project_code_template if target == "rack"
        else period.asset_project_code_template
    )
    if not template:
        raise BusinessRuleError("프로젝트코드 템플릿이 설정되지 않았습니다.", status_code=422)
    room_ids = _get_period_room_ids(db, period)
    return generate_rack_codes(db, template, room_ids)


def _get_period_room_ids(db: Session, period: ContractPeriod) -> list[int]:
    """프로젝트에 속한 모든 room ID를 조회."""
    from app.modules.infra.models.center import Center
    centers = list(db.scalars(
        select(Center).where(Center.partner_id == period.partner_id)
    ))
    room_ids = []
    for center in centers:
        rooms = list(db.scalars(
            select(Room.id).where(Room.center_id == center.id)
        ))
        room_ids.extend(rooms)
    return room_ids
```

- [ ] **Step 2: 라우터 등록 + 커밋**

```bash
git add app/modules/infra/routers/code_generation.py
git commit -m "feat: add project code preview and bulk generation API"
```

---

## Task 11: 상면도 UI — 격자 렌더링 + 라인 편집

**Files:**
- Modify: `app/static/js/infra_physical_layout.js`
- Modify: `app/static/css/infra_common.css`
- Modify: `app/modules/infra/templates/infra_physical_layout.html`

- [ ] **Step 1: CSS — 격자/라인/슬롯 스타일 추가**

`app/static/css/infra_common.css`에 추가:

```css
/* === Floor Plan Grid === */
.floor-plan-grid {
  display: grid;
  gap: 2px;
  background: var(--color-gray-100, #f3f4f6);
  border: 1px solid var(--color-gray-300, #d1d5db);
  border-radius: 6px;
  padding: 8px;
  overflow-x: auto;
}
.floor-plan-cell {
  width: 64px;
  height: 40px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s;
}
.floor-plan-cell.empty {
  background: var(--color-gray-100, #f3f4f6);
}
.floor-plan-cell.line-slot {
  background: var(--color-blue-50, #eff6ff);
  border: 1px solid var(--color-blue-200, #bfdbfe);
}
.floor-plan-cell.line-slot.disabled {
  background: var(--color-gray-100, #f3f4f6);
  border: 1px solid transparent;
}
.floor-plan-cell.line-slot.has-rack {
  background: var(--color-blue-100, #dbeafe);
  border: 1px solid var(--color-blue-400, #60a5fa);
  font-weight: 600;
}
.floor-plan-cell.line-slot.drag-over {
  background: var(--color-green-100, #dcfce7);
  border: 1px solid var(--color-green-400, #4ade80);
}
.floor-plan-cell.line-slot.drag-invalid {
  background: var(--color-red-50, #fef2f2);
  border: 1px solid var(--color-red-300, #fca5a5);
}
.floor-plan-header {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-gray-500, #6b7280);
  text-align: center;
  padding: 2px 0;
}
.floor-plan-row-label {
  font-size: 10px;
  color: var(--color-gray-400, #9ca3af);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
}
.unplaced-racks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 8px;
  min-height: 48px;
  background: var(--color-gray-50, #f9fafb);
  border: 1px dashed var(--color-gray-300, #d1d5db);
  border-radius: 6px;
  margin-top: 12px;
}
.unplaced-rack-chip {
  padding: 4px 10px;
  background: var(--color-gray-200, #e5e7eb);
  border-radius: 4px;
  font-size: 12px;
  cursor: grab;
}
.unplaced-rack-chip:active {
  cursor: grabbing;
}
```

- [ ] **Step 2: HTML — 격자 컨테이너 마크업 업데이트**

`infra_physical_layout.html`의 전산실 뷰 영역에 상면도 격자 컨테이너 + 코드 표시 토글 + 편집 모드 버튼 추가. 기존 rack-grid 영역을 교체.

- [ ] **Step 3: JS — renderFloorPlan() 구현**

기존 `renderRoomView()`를 `renderFloorPlan()`으로 교체. API에서 rack-lines 로드 후 격자 DOM을 빌드. 셀은 `document.createElement()`와 `textContent` 사용 (DOM API 안전 방식).

핵심 로직:
- `grid_cols x grid_rows` 격자 생성
- 라인이 있는 열은 `.line-slot` 클래스
- 비활성 슬롯은 `.disabled` 클래스 (바닥색과 동일)
- 배치된 랙은 `.has-rack` + 랙 코드 표시
- 빈 열 클릭 → 라인 생성 모달

- [ ] **Step 4: JS — 미배치 랙 목록 렌더링**

격자 하단에 미배치 랙 칩을 렌더링. `document.createElement()`로 DOM 생성.

- [ ] **Step 5: JS — 편집 모드 (슬롯 토글 + 라인 수정/삭제)**

편집 모드 ON일 때:
- 라인 슬롯 클릭 → disabled_slots 토글 (PATCH API)
- 라인 헤더 클릭 → 수정/삭제 옵션
- 빈 열 클릭 → 라인 생성

- [ ] **Step 6: 커밋**

```bash
git add app/static/css/infra_common.css app/static/js/infra_physical_layout.js \
  app/modules/infra/templates/infra_physical_layout.html
git commit -m "feat(ui): implement floor plan grid with line editing"
```

---

## Task 12: 상면도 UI — 랙 드래그 배치 + 코드 표시 토글

**Files:**
- Modify: `app/static/js/infra_physical_layout.js`

- [ ] **Step 1: 드래그 이벤트 핸들러 구현**

- `onRackDragStart`: `_draggedRackId` 저장
- `onSlotDragOver`: 유효 슬롯이면 `.drag-over`, 아니면 `.drag-invalid`
- `onSlotDragLeave`: 하이라이트 제거
- `onSlotDrop`: PATCH `/api/v1/racks/{id}` 호출 → `rack_line_id`, `line_position` 설정 → 격자 새로고침
- `onUnplaceRackDrop`: 미배치 영역 drop → `rack_line_id: null, line_position: null`

- [ ] **Step 2: 배치된 랙 클릭 → 트리에서 랙 선택 + U 다이어그램**

격자 셀 클릭 시 `selectTreeNode("rack", rackId)` 호출.

- [ ] **Step 3: 코드 표시 토글 (system_id / project_code / rack_code)**

`<select>` 토글 → `_codeDisplay` 변수 변경 → 격자 셀 텍스트 갱신.

- [ ] **Step 4: 커밋**

```bash
git add app/static/js/infra_physical_layout.js \
  app/modules/infra/templates/infra_physical_layout.html
git commit -m "feat(ui): add rack drag placement and code display toggle"
```

---

## Task 13: layout_service — update_rack 프로젝트코드 자동완성

**Files:**
- Modify: `app/modules/infra/services/layout_service.py`

- [ ] **Step 1: update_rack에서 rack_line_id 설정 시 project_code 자동 계산**

`update_rack()` 수정 — `rack_line_id`가 변경되고 라인에 배치되었을 때 활성 프로젝트의 `rack_project_code_template`을 조회하여 project_code 자동 생성:

```python
def _auto_fill_project_code(db: Session, rack: Rack, line_id: int | None, position: int | None) -> None:
    """라인 배치 시 프로젝트코드 템플릿이 설정되어 있으면 자동 생성."""
    if line_id is None:
        return
    line = db.get(RackLine, line_id)
    if not line:
        return
    room = db.get(Room, line.room_id)
    center = db.get(Center, room.center_id)

    from app.modules.common.models.contract_period import ContractPeriod
    period = db.scalar(
        select(ContractPeriod).where(
            ContractPeriod.partner_id == center.partner_id,
            ContractPeriod.rack_project_code_template.isnot(None),
        ).order_by(ContractPeriod.id.desc())
    )
    if not period or not period.rack_project_code_template:
        return

    from app.modules.infra.services.code_generation_service import render_template
    context = {
        "center.prefix": center.prefix or "",
        "room.prefix": room.prefix or "",
        "line.prefix": line.prefix or "",
        "rack.position": str((position or 0) + 1),
    }
    try:
        rack.project_code = render_template(period.rack_project_code_template, context)
    except ValueError:
        pass
```

- [ ] **Step 2: 커밋**

```bash
git add app/modules/infra/services/layout_service.py
git commit -m "feat: auto-fill project_code on rack line placement"
```

---

## Task 14: 문서 업데이트 + 최종 검증

**Files:**
- Modify: `docs/guidelines/infra.md`
- Modify: `docs/PROJECT_STRUCTURE.md`

- [ ] **Step 1: infra guideline에 이원 코드 체계 설명 추가**

- system_id vs project_code 개념
- RackLine 엔티티
- 상면도 UI 설명
- 템플릿 변수 목록

- [ ] **Step 2: PROJECT_STRUCTURE.md에 신규 파일 추가**

- `app/modules/infra/models/rack_line.py`
- `app/modules/infra/schemas/rack_line.py`
- `app/modules/infra/routers/rack_lines.py`
- `app/modules/infra/routers/code_generation.py`
- `app/modules/infra/services/code_generation_service.py`

- [ ] **Step 3: 전체 테스트 실행**

Run: `pytest tests/ -v --tb=short`
Expected: ALL PASS

- [ ] **Step 4: 커밋**

```bash
git add docs/
git commit -m "docs: update guidelines and project structure for floor plan feature"
```
