# 자산유형 코드 체계 구현 계획

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** 자산유형을 DB 관리형 테이블로 전환하고, `{고객사코드}-{유형코드}-{base36 4자리}` 형식의 자산 코드를 자동 생성한다. 시스템관리 페이지를 탭 구조로 개편한다.

**Architecture:** common 모듈에 `AssetTypeCode` 모델/서비스/라우터 추가 (ContractTypeConfig 패턴 동일). asset_service.py에 코드 자동 생성 로직. system.html을 공통/영업/인프라 탭으로 분리. 프론트엔드의 하드코딩 유형 맵을 API 동적 로드로 교체.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Jinja2, Vanilla JS, AG Grid

**스펙:** `docs/superpowers/specs/2026-03-24-asset-type-code-design.md`

---

## 파일 구조

### 신규 생성

| 파일 | 역할 |
|------|------|
| `app/modules/common/models/asset_type_code.py` | AssetTypeCode ORM 모델 |
| `app/modules/common/schemas/asset_type_code.py` | Pydantic Create/Update/Read 스키마 |
| `app/modules/common/services/asset_type_code.py` | CRUD + seed + validation 서비스 |
| `app/modules/common/routers/asset_type_codes.py` | REST API 라우터 |
| `alembic/versions/0013_asset_type_codes.py` | Migration: 테이블 생성 + 기존 자산 코드 재생성 |

### 수정

| 파일 | 변경 내용 |
|------|----------|
| `app/modules/common/models/__init__.py` | AssetTypeCode import + `__all__` 추가 |
| `app/modules/common/routers/__init__.py` | 라우터 import + include + re-export + `__all__` 추가 |
| `app/core/startup/bootstrap.py` | `seed_asset_type_codes()` 호출 추가 |
| `app/modules/infra/services/asset_service.py` | 코드 자동 생성 로직 교체, 유형 변경 차단, 유형 검증 |
| `app/static/js/utils.js` | `loadAssetTypeCodes()`, `populateAssetTypeSelect()`, `getAssetTypeLabel()` 추가 |
| `app/static/js/infra_assets.js` | 하드코딩 ASSET_TYPE_MAP 제거, 동적 로드 |
| `app/modules/infra/templates/infra_assets.html` | select 옵션 동적화, 수정 시 유형 읽기 전용 |
| `app/templates/system.html` | 탭 구조 + 자산유형 관리 섹션 추가 |
| `app/static/js/system.js` | 탭 전환 + 자산유형 CRUD 함수 추가 |

---

## Task 1: AssetTypeCode 모델

**Files:**
- Create: `app/modules/common/models/asset_type_code.py`
- Modify: `app/modules/common/models/__init__.py`

- [ ] `app/modules/common/models/asset_type_code.py` 생성:

```python
"""자산유형 코드 설정 (AssetTypeCode) - 관리자가 관리하는 자산유형 목록."""
from sqlalchemy import String, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AssetTypeCode(Base):
    __tablename__ = "asset_type_codes"

    type_key: Mapped[str] = mapped_column(String(30), primary_key=True)   # server, network 등
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)  # SVR, NET 등
    label: Mapped[str] = mapped_column(String(50), nullable=False)        # 서버, 네트워크 등
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

- [ ] `app/modules/common/models/__init__.py` 수정 — import 추가:

```python
# 기존 마지막 import 뒤에 추가
from app.modules.common.models.asset_type_code import AssetTypeCode
```

`__all__`에 `"AssetTypeCode"` 추가.

- [ ] 커밋: `feat: add AssetTypeCode model`

---

## Task 2: AssetTypeCode 스키마

**Files:**
- Create: `app/modules/common/schemas/asset_type_code.py`

- [ ] `app/modules/common/schemas/asset_type_code.py` 생성:

```python
from pydantic import BaseModel, Field


class AssetTypeCodeRead(BaseModel):
    type_key: str
    code: str
    label: str
    sort_order: int
    is_active: bool


class AssetTypeCodeCreate(BaseModel):
    type_key: str = Field(pattern=r'^[a-z][a-z0-9_]{0,29}$')
    code: str = Field(pattern=r'^[A-Z]{3}$')
    label: str = Field(min_length=1, max_length=50)
    sort_order: int = 0


class AssetTypeCodeUpdate(BaseModel):
    label: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
```

- [ ] 커밋: `feat: add AssetTypeCode schemas`

---

## Task 3: AssetTypeCode 서비스

**Files:**
- Create: `app/modules/common/services/asset_type_code.py`

- [ ] `app/modules/common/services/asset_type_code.py` 생성. `contract_type_config.py` 패턴을 따른다:

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateError, NotFoundError
from app.modules.common.models.asset_type_code import AssetTypeCode
from app.modules.common.schemas.asset_type_code import AssetTypeCodeRead


def to_read(at: AssetTypeCode) -> AssetTypeCodeRead:
    return AssetTypeCodeRead(
        type_key=at.type_key, code=at.code, label=at.label,
        sort_order=at.sort_order, is_active=at.is_active,
    )


_SEED = [
    {"type_key": "server", "code": "SVR", "label": "서버", "sort_order": 1},
    {"type_key": "network", "code": "NET", "label": "네트워크", "sort_order": 2},
    {"type_key": "security", "code": "SEC", "label": "보안장비", "sort_order": 3},
    {"type_key": "storage", "code": "STO", "label": "스토리지", "sort_order": 4},
    {"type_key": "middleware", "code": "MID", "label": "미들웨어", "sort_order": 5},
    {"type_key": "application", "code": "APP", "label": "응용", "sort_order": 6},
    {"type_key": "other", "code": "ETC", "label": "기타", "sort_order": 7},
]


def seed_defaults(db: Session) -> None:
    """테이블이 비어있으면 기본 자산유형을 삽입한다."""
    from sqlalchemy import inspect as sa_inspect

    tbl = AssetTypeCode.__table__
    engine = db.get_bind()
    insp = sa_inspect(engine)
    tbl_name = AssetTypeCode.__tablename__

    if insp.has_table(tbl_name):
        existing_cols = {c["name"] for c in insp.get_columns(tbl_name)}
        model_cols = {c.name for c in tbl.columns}
        if model_cols.issubset(existing_cols):
            cnt = db.query(AssetTypeCode).count()
            if cnt > 0:
                return
        else:
            common_cols = sorted(existing_cols & model_cols)
            col_attrs = [tbl.c[c] for c in common_cols]
            with engine.connect() as conn:
                rows = conn.execute(tbl.select().with_only_columns(*col_attrs)).fetchall()
                backup = [dict(zip(common_cols, r)) for r in rows]
            db.close()
            tbl.drop(engine)
            tbl.create(engine)
            if backup:
                with engine.connect() as conn:
                    conn.execute(tbl.insert(), backup)
                    conn.commit()
            return
    else:
        tbl.create(engine)

    with engine.connect() as conn:
        conn.execute(tbl.insert(), _SEED)
        conn.commit()


def list_asset_type_codes(db: Session, *, active_only: bool = True) -> list[AssetTypeCodeRead]:
    q = db.query(AssetTypeCode).order_by(AssetTypeCode.sort_order, AssetTypeCode.type_key)
    if active_only:
        q = q.filter(AssetTypeCode.is_active.is_(True))
    return [to_read(at) for at in q.all()]


def get_valid_type_keys(db: Session) -> set[str]:
    """활성 자산유형 type_key set 반환 (검증용)."""
    rows = db.query(AssetTypeCode.type_key).filter(AssetTypeCode.is_active.is_(True)).all()
    return {r[0] for r in rows}


def get_code_for_type_key(db: Session, type_key: str) -> str:
    """type_key에 대응하는 3자리 코드 반환. 없으면 NotFoundError."""
    at = db.get(AssetTypeCode, type_key)
    if not at:
        raise NotFoundError(f"자산유형 '{type_key}'을(를) 찾을 수 없습니다.")
    return at.code


def create_asset_type_code(
    db: Session, type_key: str, code: str, label: str, sort_order: int = 0,
) -> AssetTypeCodeRead:
    if db.get(AssetTypeCode, type_key):
        raise DuplicateError(f"자산유형 '{type_key}'이(가) 이미 존재합니다.")
    existing_code = db.scalar(select(AssetTypeCode).where(AssetTypeCode.code == code))
    if existing_code:
        raise DuplicateError(f"유형코드 '{code}'이(가) 이미 사용 중입니다.")
    at = AssetTypeCode(type_key=type_key, code=code, label=label, sort_order=sort_order)
    db.add(at)
    db.commit()
    return to_read(at)


def update_asset_type_code(db: Session, type_key: str, *, updates: dict) -> AssetTypeCodeRead:
    at = db.get(AssetTypeCode, type_key)
    if not at:
        raise NotFoundError(f"자산유형 '{type_key}'을(를) 찾을 수 없습니다.")
    updates.pop("code", None)
    updates.pop("type_key", None)
    for k, v in updates.items():
        if hasattr(at, k):
            setattr(at, k, v)
    db.commit()
    return to_read(at)


def delete_asset_type_code(db: Session, type_key: str) -> None:
    from app.modules.infra.models.asset import Asset

    at = db.get(AssetTypeCode, type_key)
    if not at:
        raise NotFoundError(f"자산유형 '{type_key}'을(를) 찾을 수 없습니다.")
    count = db.query(Asset).filter(Asset.asset_type == type_key).count()
    if count > 0:
        raise DuplicateError(f"이 유형의 자산이 {count}건 존재하여 삭제할 수 없습니다. 비활성화를 사용하세요.")
    db.delete(at)
    db.commit()
```

- [ ] 커밋: `feat: add AssetTypeCode service with CRUD and seed`

---

## Task 4: AssetTypeCode API 라우터

**Files:**
- Create: `app/modules/common/routers/asset_type_codes.py`
- Modify: `app/modules/common/routers/__init__.py`

- [ ] `app/modules/common/routers/asset_type_codes.py` 생성:

```python
"""AssetTypeCode CRUD 라우터."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user, require_admin
from app.core.database import get_db
from app.modules.common.models.user import User
from app.modules.common.schemas.asset_type_code import (
    AssetTypeCodeCreate,
    AssetTypeCodeRead,
    AssetTypeCodeUpdate,
)
from app.modules.common.services import asset_type_code as svc

router = APIRouter(prefix="/api/v1/asset-type-codes", tags=["asset-type-codes"])


@router.get("", response_model=list[AssetTypeCodeRead])
def list_asset_type_codes(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> list[AssetTypeCodeRead]:
    return svc.list_asset_type_codes(db, active_only=active_only)


@router.post("", response_model=AssetTypeCodeRead, status_code=201)
def create_asset_type_code(
    data: AssetTypeCodeCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AssetTypeCodeRead:
    return svc.create_asset_type_code(db, data.type_key, data.code, data.label, data.sort_order)


@router.patch("/{type_key}", response_model=AssetTypeCodeRead)
def update_asset_type_code(
    type_key: str,
    data: AssetTypeCodeUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AssetTypeCodeRead:
    return svc.update_asset_type_code(db, type_key, updates=data.model_dump(exclude_unset=True))


@router.delete("/{type_key}", status_code=204)
def delete_asset_type_code(
    type_key: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> None:
    svc.delete_asset_type_code(db, type_key)
```

- [ ] `app/modules/common/routers/__init__.py` 수정 — 3곳 추가:

1. import 블록에 추가:
```python
from app.modules.common.routers.asset_type_codes import router as asset_type_codes_router
```

2. include 블록에 추가:
```python
api_router.include_router(asset_type_codes_router)
```

3. re-export 블록에 추가:
```python
from app.modules.common.routers import asset_type_codes  # noqa: E402, F811
```

4. `__all__`에 `"asset_type_codes"` 추가.

- [ ] 커밋: `feat: add AssetTypeCode API router`

---

## Task 5: Bootstrap + Migration

**Files:**
- Modify: `app/core/startup/bootstrap.py`
- Create: `alembic/versions/0013_asset_type_codes.py`

- [ ] `app/core/startup/bootstrap.py`의 `initialize_reference_data()` 내부, `seed_contract_types(db)` 다음 줄에 추가:

```python
from app.modules.common.services.asset_type_code import seed_defaults as seed_asset_type_codes
seed_asset_type_codes(db)
```

- [ ] `alembic/versions/0013_asset_type_codes.py` 생성:

```python
"""Add asset_type_codes table and regenerate asset codes.

Revision ID: 0013
Revises: 0012
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"

_SEED = [
    ("server", "SVR", "서버", 1),
    ("network", "NET", "네트워크", 2),
    ("security", "SEC", "보안장비", 3),
    ("storage", "STO", "스토리지", 4),
    ("middleware", "MID", "미들웨어", 5),
    ("application", "APP", "응용", 6),
    ("other", "ETC", "기타", 7),
]

_TYPE_KEY_ALIASES = {"etc": "other"}
_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base36(num: int, width: int = 4) -> str:
    if num == 0:
        return "0" * width
    result = ""
    while num:
        result = _BASE36[num % 36] + result
        num //= 36
    return result.zfill(width)


def upgrade() -> None:
    op.create_table(
        "asset_type_codes",
        sa.Column("type_key", sa.String(30), primary_key=True),
        sa.Column("code", sa.String(3), nullable=False),
        sa.Column("label", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
    )
    op.create_index("ix_asset_type_codes_code", "asset_type_codes", ["code"], unique=True)

    atc = sa.table(
        "asset_type_codes",
        sa.column("type_key", sa.String),
        sa.column("code", sa.String),
        sa.column("label", sa.String),
        sa.column("sort_order", sa.Integer),
    )
    op.bulk_insert(atc, [
        {"type_key": tk, "code": c, "label": l, "sort_order": s}
        for tk, c, l, s in _SEED
    ])

    conn = op.get_bind()
    assets_t = sa.table(
        "assets",
        sa.column("id", sa.Integer),
        sa.column("partner_id", sa.Integer),
        sa.column("asset_type", sa.String),
        sa.column("asset_code", sa.String),
    )
    partners_t = sa.table(
        "partners",
        sa.column("id", sa.Integer),
        sa.column("partner_code", sa.String),
    )

    type_code_map = {tk: c for tk, c, _, _ in _SEED}
    rows = conn.execute(
        sa.select(assets_t.c.id, assets_t.c.partner_id, assets_t.c.asset_type)
        .order_by(assets_t.c.id)
    ).fetchall()

    partner_codes = {}
    for r in conn.execute(sa.select(partners_t.c.id, partners_t.c.partner_code)).fetchall():
        partner_codes[r.id] = r.partner_code

    counters: dict[tuple[int, str], int] = {}
    for asset_id, partner_id, asset_type in rows:
        type_key = _TYPE_KEY_ALIASES.get(asset_type, asset_type)
        type_code = type_code_map.get(type_key, "ETC")
        partner_code = partner_codes.get(partner_id, "X000")

        key = (partner_id, type_code)
        seq = counters.get(key, 0)
        new_code = f"{partner_code}-{type_code}-{_to_base36(seq)}"
        counters[key] = seq + 1

        conn.execute(
            assets_t.update()
            .where(assets_t.c.id == asset_id)
            .values(asset_code=new_code)
        )


def downgrade() -> None:
    op.drop_index("ix_asset_type_codes_code", table_name="asset_type_codes")
    op.drop_table("asset_type_codes")
```

- [ ] 커밋: `feat: add asset_type_codes migration with code regeneration`

---

## Task 6: asset_service.py 코드 생성 로직 교체

**Files:**
- Modify: `app/modules/infra/services/asset_service.py`

- [ ] 기존 `_generate_asset_code` 함수를 삭제하고 새 버전으로 교체:

```python
_BASE36_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _to_base36(num: int, width: int = 4) -> str:
    if num == 0:
        return "0" * width
    result = ""
    while num:
        result = _BASE36_CHARS[num % 36] + result
        num //= 36
    return result.zfill(width)


def _generate_asset_code(db: Session, partner_id: int, type_key: str) -> str:
    """Generate asset code: {partner_code}-{type_code}-{base36 4자리}."""
    from app.modules.common.models.partner import Partner
    from app.modules.common.services.asset_type_code import get_code_for_type_key

    partner = db.get(Partner, partner_id)
    partner_code = partner.partner_code if partner else "X000"
    type_code = get_code_for_type_key(db, type_key)
    prefix = f"{partner_code}-{type_code}-"

    max_code = db.scalar(
        select(func.max(Asset.asset_code))
        .where(Asset.partner_id == partner_id)
        .where(Asset.asset_code.like(f"{prefix}%"))
    )

    if max_code:
        suffix = max_code[len(prefix):]
        next_seq = int(suffix, 36) + 1
    else:
        next_seq = 0

    return prefix + _to_base36(next_seq)
```

- [ ] `create_asset` 함수 수정 — 유형 검증 + 코드 자동 생성 + IntegrityError 재시도:

```python
def create_asset(db: Session, payload: AssetCreate, current_user) -> Asset:
    from sqlalchemy.exc import IntegrityError
    from app.modules.common.services.asset_type_code import get_valid_type_keys

    _require_inventory_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)
    _ensure_asset_name_unique(db, payload.partner_id, payload.asset_name)

    valid_keys = get_valid_type_keys(db)
    if payload.asset_type not in valid_keys:
        raise NotFoundError(f"유효하지 않은 자산유형: {payload.asset_type}")

    if payload.hardware_model_id is not None:
        _ensure_hardware_model_exists(db, payload.hardware_model_id)

    data = payload.model_dump()
    data.pop("asset_code", None)

    for attempt in range(3):
        data["asset_code"] = _generate_asset_code(db, payload.partner_id, payload.asset_type)
        asset = Asset(**data)
        db.add(asset)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise

    audit.log(
        db, user_id=current_user.id, action="create", entity_type="asset",
        entity_id=None, summary=f"자산 생성: {asset.asset_name}", module="infra",
    )
    db.commit()
    db.refresh(asset)
    return asset
```

- [ ] `update_asset` 함수 수정 — `asset_type` 변경 차단. `changes = payload.model_dump(exclude_unset=True)` 다음에 추가:

```python
    if "asset_type" in changes and changes["asset_type"] != asset.asset_type:
        raise PermissionDeniedError("자산 유형은 변경할 수 없습니다.")
    changes.pop("asset_type", None)
    changes.pop("asset_code", None)
```

- [ ] 커밋: `feat: replace asset code generation with type-based base36 format`

---

## Task 7: 프론트엔드 — utils.js 유틸 함수

**Files:**
- Modify: `app/static/js/utils.js`

- [ ] 기존 `loadContractTypes` 관련 함수 블록 뒤에 자산유형 함수 추가:

```javascript
// ── 자산유형 코드 ──────────────────────────────────────────
let _assetTypeCodesCache = null;

async function loadAssetTypeCodes() {
  if (!_assetTypeCodesCache) {
    _assetTypeCodesCache = await apiFetch('/api/v1/asset-type-codes');
  }
  return _assetTypeCodesCache;
}

// system.js에서 자산유형 CRUD 성공 후 반드시 호출
function invalidateAssetTypeCodesCache() {
  _assetTypeCodesCache = null;
}

async function populateAssetTypeSelect(selectId, includeAll) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const types = await loadAssetTypeCodes();
  sel.textContent = '';
  if (includeAll) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '전체';
    sel.appendChild(opt);
  }
  types.forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.type_key;
    opt.textContent = t.label;
    sel.appendChild(opt);
  });
}

function getAssetTypeLabel(typeKey) {
  if (!_assetTypeCodesCache) return typeKey;
  const found = _assetTypeCodesCache.find(t => t.type_key === typeKey);
  return found ? found.label : typeKey;
}
```

- [ ] 커밋: `feat: add asset type code utils (load, populate, label)`

---

## Task 8: 프론트엔드 — infra_assets.js + HTML 동적화

**Files:**
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/modules/infra/templates/infra_assets.html`

- [ ] `infra_assets.js` 수정:

1. **`ASSET_TYPE_MAP` 상수 삭제** (파일 상단 3-9행)

2. **AG Grid `valueFormatter` 변경:**
```javascript
// 기존: valueFormatter: (p) => ASSET_TYPE_MAP[p.value] || p.value,
// 변경:
valueFormatter: (p) => getAssetTypeLabel(p.value),
```

3. **상세 패널 DETAIL_TABS.basic의 유형 formatter 변경:**
```javascript
// 기존: ["유형", "asset_type", v => ASSET_TYPE_MAP[v] || v],
// 변경:
["유형", "asset_type", v => getAssetTypeLabel(v)],
```

4. **`initGrid` 함수를 async로 변경하고 선두에 로드 호출:**
```javascript
async function initGrid() {
  await loadAssetTypeCodes();
  // ... 기존 코드
}
```

5. **DOMContentLoaded 핸들러 변경:**
```javascript
document.addEventListener("DOMContentLoaded", async () => {
  await populateAssetTypeSelect("asset-type");
  await populateAssetTypeSelect("filter-type", true);
  initGrid();
});
```

6. **기존 `document.addEventListener("DOMContentLoaded", initGrid);` 삭제**

7. **수정 모달에서 유형 disabled 처리:**

`openEditModal` 함수에 추가:
```javascript
document.getElementById("asset-type").disabled = true;
```

`openCreateModal` 함수에 추가:
```javascript
document.getElementById("asset-type").disabled = false;
```

- [ ] `infra_assets.html` 수정:

1. **등록 모달의 유형 select에서 하드코딩 option 제거** — 빈 `<select id="asset-type" required></select>` 유지
2. **필터바의 유형 select에서 하드코딩 option 제거** — 빈 `<select id="filter-type"></select>` 유지

- [ ] 커밋: `feat: replace hardcoded asset types with dynamic API loading`

---

## Task 9: 시스템관리 페이지 — 탭 구조 개편

**Files:**
- Modify: `app/templates/system.html`
- Modify: `app/static/js/system.js`

- [ ] `system.html` 수정:

1. `{% block content %}` 직후에 탭 네비게이션 추가:
```html
<div class="tab-nav" id="system-tabs">
  <button class="tab-btn active" data-tab="common">공통</button>
  {% if "accounting" in enabled_modules %}
  <button class="tab-btn" data-tab="accounting">영업관리</button>
  {% endif %}
  {% if "infra" in enabled_modules %}
  <button class="tab-btn" data-tab="infra">프로젝트관리</button>
  {% endif %}
</div>
```

2. 기존 "기본 설정" + "용어 관리" 섹션을 `<div id="tab-common">` 으로 래핑
3. 기존 "사업유형 관리" 섹션을 `<div id="tab-accounting" class="hidden">` 으로 래핑
4. 새 프로젝트관리 탭 추가:

```html
<div id="tab-infra" class="hidden">
  <div class="section-header">
    <h2>자산유형 관리</h2>
    <button class="btn btn-primary" id="btn-add-asset-type">유형 추가</button>
  </div>
  <table class="data-table" id="tbl-asset-types">
    <thead>
      <tr><th>키</th><th>코드</th><th>표시명</th><th>순서</th><th>활성</th><th>액션</th></tr>
    </thead>
    <tbody></tbody>
  </table>
</div>
```

5. 자산유형 모달 (DOM API로 안전하게 렌더링):

```html
<dialog id="modal-asset-type" class="modal">
  <h2 id="modal-at-title">자산유형 추가</h2>
  <form class="form-grid">
    <label>키 <input type="text" id="at-type-key" required pattern="[a-z][a-z0-9_]*" placeholder="예: server"></label>
    <label>코드 <input type="text" id="at-code" required pattern="[A-Z]{3}" maxlength="3" placeholder="예: SVR"></label>
    <label>표시명 <input type="text" id="at-label" required placeholder="예: 서버"></label>
    <label>정렬순서 <input type="number" id="at-sort-order" value="0"></label>
    <label>활성 <select id="at-is-active"><option value="true">활성</option><option value="false">비활성</option></select></label>
  </form>
  <div class="modal-actions">
    <button class="btn btn-secondary" id="btn-at-cancel">취소</button>
    <button class="btn btn-primary" id="btn-at-submit">저장</button>
  </div>
</dialog>
```

6. `infra_common.css` 링크 추가 (탭 스타일):
```html
{% block styles %}
<link rel="stylesheet" href="/static/css/infra_common.css">
{% endblock %}
```

- [ ] `system.js` 수정:

1. **탭 전환 로직** (파일 상단에 추가):
```javascript
document.querySelectorAll('#system-tabs .tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('#system-tabs .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('[id^="tab-"]').forEach(div => {
      if (div.closest('#system-tabs')) return;
      div.classList.toggle('hidden', div.id !== 'tab-' + btn.dataset.tab);
    });
    history.replaceState(null, '', '#' + btn.dataset.tab);
  });
});
const initTab = location.hash.slice(1) || 'common';
const initBtn = document.querySelector('#system-tabs .tab-btn[data-tab="' + initTab + '"]');
if (initBtn) initBtn.click();
```

2. **자산유형 CRUD 함수** — DOM API로 안전하게 렌더링:
```javascript
let _editingTypeKey = null;

async function loadAssetTypeTable() {
  const types = await apiFetch('/api/v1/asset-type-codes?active_only=false');
  const tbody = document.querySelector('#tbl-asset-types tbody');
  tbody.textContent = '';
  types.forEach(t => {
    const tr = document.createElement('tr');
    const cells = [t.type_key, t.code, t.label, t.sort_order, t.is_active ? '\u2713' : '\u2014'];
    cells.forEach(val => {
      const td = document.createElement('td');
      td.textContent = val;
      tr.appendChild(td);
    });
    const actionTd = document.createElement('td');
    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-sm';
    editBtn.textContent = '수정';
    editBtn.addEventListener('click', () => openAssetTypeModal(t.type_key));
    actionTd.appendChild(editBtn);
    tr.appendChild(actionTd);
    tbody.appendChild(tr);
  });
}

function openAssetTypeModal(typeKey) {
  const modal = document.getElementById('modal-asset-type');
  const titleEl = document.getElementById('modal-at-title');
  const keyInput = document.getElementById('at-type-key');
  const codeInput = document.getElementById('at-code');

  if (typeKey) {
    _editingTypeKey = typeKey;
    titleEl.textContent = '자산유형 수정';
    apiFetch('/api/v1/asset-type-codes?active_only=false').then(types => {
      const t = types.find(x => x.type_key === typeKey);
      if (!t) return;
      keyInput.value = t.type_key;
      keyInput.disabled = true;
      codeInput.value = t.code;
      codeInput.disabled = true;
      document.getElementById('at-label').value = t.label;
      document.getElementById('at-sort-order').value = t.sort_order;
      document.getElementById('at-is-active').value = String(t.is_active);
    });
  } else {
    _editingTypeKey = null;
    titleEl.textContent = '자산유형 추가';
    keyInput.value = '';
    keyInput.disabled = false;
    codeInput.value = '';
    codeInput.disabled = false;
    document.getElementById('at-label').value = '';
    document.getElementById('at-sort-order').value = '0';
    document.getElementById('at-is-active').value = 'true';
  }
  modal.showModal();
}

async function submitAssetType() {
  const label = document.getElementById('at-label').value.trim();
  const sortOrder = Number(document.getElementById('at-sort-order').value) || 0;
  const isActive = document.getElementById('at-is-active').value === 'true';

  try {
    if (_editingTypeKey) {
      await apiFetch('/api/v1/asset-type-codes/' + encodeURIComponent(_editingTypeKey), {
        method: 'PATCH', body: { label, sort_order: sortOrder, is_active: isActive },
      });
      showToast('자산유형이 수정되었습니다.');
    } else {
      const typeKey = document.getElementById('at-type-key').value.trim();
      const code = document.getElementById('at-code').value.trim().toUpperCase();
      await apiFetch('/api/v1/asset-type-codes', {
        method: 'POST', body: { type_key: typeKey, code, label, sort_order: sortOrder },
      });
      showToast('자산유형이 추가되었습니다.');
    }
    document.getElementById('modal-asset-type').close();
    invalidateAssetTypeCodesCache();
    loadAssetTypeTable();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

if (document.getElementById('btn-add-asset-type')) {
  document.getElementById('btn-add-asset-type').addEventListener('click', () => openAssetTypeModal(null));
  document.getElementById('btn-at-cancel').addEventListener('click', () => document.getElementById('modal-asset-type').close());
  document.getElementById('btn-at-submit').addEventListener('click', submitAssetType);
  loadAssetTypeTable();
}
```

- [ ] 커밋: `feat: add system page tabs (common/sales/infra) with asset type management`

---

## Task 10: 브라우저 E2E 검증

- [ ] Docker 앱 재시작 (`docker restart pjtmgr-app`)
- [ ] `/system#infra` 페이지 접속 → 3개 탭 확인
- [ ] 프로젝트관리 탭 → 자산유형 7개 시드 데이터 표시 확인
- [ ] 자산유형 추가/수정 테스트
- [ ] `/assets` 페이지 → 필터 드롭다운 동적 로드 확인
- [ ] 자산 등록 → 코드 자동 생성 확인 (예: `P000-SEC-0004`)
- [ ] 자산 수정 모달 → 유형 필드 disabled 확인
- [ ] 커밋 (검증 중 발견한 수정사항이 있으면)
