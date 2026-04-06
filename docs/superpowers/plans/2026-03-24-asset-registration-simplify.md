# 자산 등록 간소화 + 카탈로그 연동 구현 계획

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** 자산 등록 모달을 4개 필드로 간소화하고, 카탈로그 선택으로 유형/제조사/모델을 자동 결정하며, placeholder 카탈로그로 미분류 장비도 등록 가능하게 한다.

**Architecture:** `product_catalog`에 `asset_type_key` + `is_placeholder` 컬럼을 추가하고, 자산 생성 서비스에서 카탈로그 기반으로 필드를 자동 세팅한다. 프론트의 등록 모달을 간소화하고, 수정은 상세 패널 인라인 편집으로 대체한다.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Vanilla JS

**Spec:** `docs/superpowers/specs/2026-03-24-asset-registration-simplify-design.md`

---

## Task 1: 카탈로그 모델 + Migration

`product_catalog` 테이블에 `asset_type_key`, `is_placeholder` 컬럼을 추가하고, placeholder 시드 데이터를 생성한다.

**Files:**
- Modify: `app/modules/infra/models/product_catalog.py`
- Create: `alembic/versions/0015_catalog_asset_type_and_placeholder.py`

- [ ] **Step 1: ProductCatalog 모델에 2개 컬럼 추가**

`app/modules/infra/models/product_catalog.py`에 추가:

```python
from sqlalchemy import Boolean, Date, ForeignKey, String, Text

# 기존 필드 아래에 추가:
asset_type_key: Mapped[str | None] = mapped_column(
    String(30), ForeignKey("asset_type_codes.type_key", ondelete="SET NULL"),
    nullable=True, index=True
)
is_placeholder: Mapped[bool] = mapped_column(Boolean, default=False)
```

- [ ] **Step 2: Alembic migration 작성**

`alembic/versions/0015_catalog_asset_type_and_placeholder.py` 생성:

```python
"""Add asset_type_key and is_placeholder to product_catalog, seed placeholders.

Revision ID: 0015
Revises: 0014
"""
from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"

# category -> asset_type_key 매핑
CATEGORY_MAP = {
    "server": "server", "서버": "server",
    "switch": "network", "스위치": "network",
    "router": "network", "라우터": "network",
    "firewall": "security", "방화벽": "security",
    "storage": "storage", "스토리지": "storage",
}

PLACEHOLDERS = [
    ("—", "미분류 서버", "Server", "server"),
    ("—", "미분류 네트워크장비", "Network", "network"),
    ("—", "미분류 보안장비", "Security", "security"),
    ("—", "미분류 스토리지", "Storage", "storage"),
    ("—", "미분류 미들웨어", "Middleware", "middleware"),
    ("—", "미분류 응용", "Application", "application"),
    ("—", "미분류 기타", "ETC", "other"),
]


def upgrade() -> None:
    # 1. 컬럼 추가
    op.add_column("product_catalog", sa.Column(
        "asset_type_key", sa.String(30),
        sa.ForeignKey("asset_type_codes.type_key", ondelete="SET NULL"),
        nullable=True,
    ))
    op.add_column("product_catalog", sa.Column(
        "is_placeholder", sa.Boolean(), nullable=False, server_default=sa.text("false"),
    ))
    op.create_index("ix_product_catalog_asset_type_key", "product_catalog", ["asset_type_key"])

    # 2. 기존 데이터 category 기반 매핑
    conn = op.get_bind()
    for keyword, type_key in CATEGORY_MAP.items():
        conn.execute(sa.text(
            "UPDATE product_catalog SET asset_type_key = :tk "
            "WHERE asset_type_key IS NULL AND LOWER(category) LIKE :pattern"
        ), {"tk": type_key, "pattern": f"%{keyword}%"})

    # 3. Placeholder 시드 (vendor+name unique 제약 준수)
    for vendor, name, category, type_key in PLACEHOLDERS:
        exists = conn.execute(sa.text(
            "SELECT 1 FROM product_catalog WHERE vendor = :v AND name = :n"
        ), {"v": vendor, "n": name}).scalar()
        if not exists:
            conn.execute(sa.text(
                "INSERT INTO product_catalog (vendor, name, product_type, category, asset_type_key, is_placeholder) "
                "VALUES (:v, :n, 'hardware', :c, :tk, true)"
            ), {"v": vendor, "n": name, "c": category, "tk": type_key})


def downgrade() -> None:
    op.execute("DELETE FROM product_catalog WHERE is_placeholder = true")
    op.drop_index("ix_product_catalog_asset_type_key", "product_catalog")
    op.drop_column("product_catalog", "is_placeholder")
    op.drop_column("product_catalog", "asset_type_key")
```

- [ ] **Step 3: 커밋**

```
feat(infra): add asset_type_key and is_placeholder to product_catalog
```

---

## Task 2: 카탈로그 스키마 + 서비스 수정

카탈로그 CRUD에 `asset_type_key`, `is_placeholder` 필드를 반영한다.

**Files:**
- Modify: `app/modules/infra/schemas/product_catalog.py`
- Modify: `app/modules/infra/services/product_catalog_service.py`

- [ ] **Step 1: 스키마에 필드 추가**

`ProductCatalogCreate`에 추가:
```python
asset_type_key: str | None = None
```

`ProductCatalogUpdate`에 추가:
```python
asset_type_key: str | None = None
```

`ProductCatalogRead`에 추가:
```python
asset_type_key: str | None
is_placeholder: bool
```

- [ ] **Step 2: 서비스에서 asset_type_key 유효성 검증**

`create_product()`에 추가 — payload에 `asset_type_key`가 있으면 `asset_type_codes` 테이블에 존재하는지 확인:

```python
from app.modules.common.services.asset_type_code import get_valid_type_keys

def create_product(db, payload, current_user):
    _require_edit(current_user)
    _ensure_vendor_name_unique(db, payload.vendor, payload.name)
    if payload.asset_type_key:
        valid = get_valid_type_keys(db)
        if payload.asset_type_key not in valid:
            raise NotFoundError(f"유효하지 않은 자산유형: {payload.asset_type_key}")
    product = ProductCatalog(**payload.model_dump())
    # ... 기존 로직
```

`update_product()`에도 동일한 검증 추가 (changes에 `asset_type_key`가 있을 때).

`delete_product()`에서 `is_placeholder = true`인 항목 삭제 차단 추가:

```python
if product.is_placeholder:
    raise BusinessRuleError("시스템 placeholder 항목은 삭제할 수 없습니다.", status_code=403)
```

- [ ] **Step 3: list_products 검색에 vendor도 ILIKE 포함**

현재는 `name`만 검색. 자산 등록 드롭다운에서 `vendor + name`으로 검색해야 하므로:

```python
if q:
    like = f"%{q}%"
    stmt = stmt.where(
        ProductCatalog.name.ilike(like)
        | ProductCatalog.vendor.ilike(like)
    )
```

- [ ] **Step 4: 커밋**

```
feat(infra): add asset_type_key to catalog schemas and service
```

---

## Task 3: 자산 생성 서비스 리팩터링

`create_asset`을 카탈로그 기반으로 전환한다. `hardware_model_id` 필수, 카탈로그에서 type/vendor/model/category 자동 세팅, `period_id` 옵션으로 PeriodAsset 동시 생성.

**Files:**
- Modify: `app/modules/infra/schemas/asset.py` — `AssetCreate` 간소화
- Modify: `app/modules/infra/services/asset_service.py` — `create_asset` 로직 변경

- [x] **Step 1: AssetCreate 스키마 간소화**

`app/modules/infra/schemas/asset.py`에서 `AssetCreate`를 수정:

```python
class AssetCreate(BaseModel):
    partner_id: int
    hardware_model_id: int       # 필수 — 카탈로그 제품
    asset_name: str
    hostname: str | None = None
    period_id: int | None = None  # 귀속사업 (선택)
```

기존 필드(vendor, model, asset_type, status, environment 등)는 제거. 서버에서 카탈로그 기반으로 세팅.

**주의:** `AssetUpdate`는 변경하지 않음 (상세 패널 인라인 편집에서 사용).

- [x] **Step 2: create_asset 서비스 로직 변경**

```python
def create_asset(db: Session, payload: AssetCreate, current_user) -> Asset:
    from sqlalchemy.exc import IntegrityError
    from app.modules.infra.models.product_catalog import ProductCatalog
    from app.modules.infra.models.period_asset import PeriodAsset

    _require_inventory_edit(current_user)
    ensure_partner_exists(db, payload.partner_id)
    _ensure_asset_name_unique(db, payload.partner_id, payload.asset_name)

    # 카탈로그 조회 + 검증
    catalog = db.get(ProductCatalog, payload.hardware_model_id)
    if not catalog:
        raise NotFoundError("카탈로그 제품을 찾을 수 없습니다")
    if not catalog.asset_type_key:
        raise BusinessRuleError("카탈로그에 자산 유형이 설정되지 않았습니다.", status_code=422)

    # placeholder면 vendor/model NULL
    vendor = None if catalog.is_placeholder else catalog.vendor
    model_name = None if catalog.is_placeholder else catalog.name

    data = {
        "partner_id": payload.partner_id,
        "hardware_model_id": catalog.id,
        "asset_name": payload.asset_name,
        "asset_type": catalog.asset_type_key,
        "vendor": vendor,
        "model": model_name,
        "category": catalog.category,
        "hostname": payload.hostname,
        "status": "planned",
        "environment": "prod",
    }

    for attempt in range(3):
        data["asset_code"] = _generate_asset_code(db, payload.partner_id, catalog.asset_type_key)
        asset = Asset(**data)
        db.add(asset)
        try:
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            if attempt == 2:
                raise

    # 귀속사업 연결 (단일 트랜잭션)
    if payload.period_id:
        period_asset = PeriodAsset(
            contract_period_id=payload.period_id,
            asset_id=asset.id,
        )
        db.add(period_asset)

    audit.log(
        db, user_id=current_user.id, action="create", entity_type="asset",
        entity_id=None, summary=f"자산 생성: {asset.asset_name}", module="infra",
    )
    db.commit()
    db.refresh(asset)
    return asset
```

- [x] **Step 3: update_asset에 카탈로그 변경 시 동일 유형 검증 추가**

`update_asset()`에서 `hardware_model_id` 변경 시:

```python
if "hardware_model_id" in changes and changes["hardware_model_id"] is not None:
    new_catalog = db.get(ProductCatalog, changes["hardware_model_id"])
    if not new_catalog:
        raise NotFoundError("카탈로그 제품을 찾을 수 없습니다")
    if new_catalog.asset_type_key != asset.asset_type:
        raise BusinessRuleError("동일한 자산 유형의 카탈로그만 선택할 수 있습니다.", status_code=422)
    # vendor/model/category 재세팅
    new_vendor = None if new_catalog.is_placeholder else new_catalog.vendor
    new_model = None if new_catalog.is_placeholder else new_catalog.name
    changes["vendor"] = new_vendor
    changes["model"] = new_model
    changes["category"] = new_catalog.category
```

- [ ] **Step 4: 커밋**

```
feat(infra): refactor asset creation to catalog-based auto-fill
```

---

## Task 4: 프론트엔드 — 등록 모달 간소화

등록 모달을 4개 필드로 축소하고, 카탈로그 검색 드롭다운 + 인라인 등록을 구현한다.

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html` — 모달 HTML 교체
- Modify: `app/static/js/infra_assets.js` — 모달 로직 교체

- [ ] **Step 1: 등록 모달 HTML 교체**

`infra_assets.html`의 `<dialog id="modal-asset">` 내용을 교체:

```html
<dialog id="modal-asset" class="modal">
  <h2 id="modal-asset-title">자산 등록</h2>
  <form id="form-asset">
    <!-- 카탈로그 검색 -->
    <label>
      카탈로그 제품 <span class="required">*</span>
      <div class="catalog-search-wrap">
        <input type="text" id="catalog-search" placeholder="제조사 또는 모델명 검색" autocomplete="off">
        <input type="hidden" id="catalog-id">
        <div id="catalog-dropdown" class="catalog-dropdown hidden"></div>
      </div>
    </label>
    <div id="catalog-summary" class="catalog-summary hidden"></div>

    <!-- 인라인 카탈로그 등록 -->
    <div id="catalog-inline-form" class="hidden">
      <fieldset class="modal-group">
        <legend class="modal-group-title">새 제품 등록</legend>
        <div class="form-grid">
          <label>제조사 <span class="required">*</span><input type="text" id="new-cat-vendor"></label>
          <label>모델명 <span class="required">*</span><input type="text" id="new-cat-name"></label>
          <label>카테고리 <span class="required">*</span><input type="text" id="new-cat-category"></label>
          <label>자산 유형 <span class="required">*</span><select id="new-cat-type"></select></label>
        </div>
        <div style="margin-top:8px">
          <button type="button" class="btn btn-sm btn-primary" id="btn-save-new-catalog">등록</button>
          <button type="button" class="btn btn-sm" id="btn-cancel-new-catalog">취소</button>
        </div>
      </fieldset>
    </div>

    <!-- 자산명 -->
    <label>
      자산명 <span class="required">*</span>
      <input type="text" id="asset-name" required>
    </label>

    <!-- 호스트명 -->
    <label>
      호스트명
      <input type="text" id="asset-hostname">
    </label>

    <!-- 귀속사업 -->
    <label>
      귀속사업
      <select id="asset-period">
        <option value="">선택 안 함</option>
      </select>
    </label>
  </form>
  <div class="modal-actions">
    <button class="btn btn-secondary" id="btn-cancel-asset">취소</button>
    <button class="btn btn-primary" id="btn-save-asset">등록</button>
  </div>
</dialog>
```

- [ ] **Step 2: CSS — 카탈로그 검색 드롭다운 스타일**

`app/static/css/infra_common.css`에 추가:

```css
.catalog-search-wrap { position: relative; }
.catalog-dropdown {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 100;
  max-height: 240px; overflow-y: auto;
  background: var(--bg-primary); border: 1px solid var(--border-color);
  border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,.12);
}
.catalog-dropdown.hidden { display: none; }
.catalog-dropdown-item {
  padding: 8px 12px; cursor: pointer; font-size: 13px;
  display: flex; justify-content: space-between; align-items: center;
}
.catalog-dropdown-item:hover { background: var(--bg-hover, #f1f5f9); }
.catalog-dropdown-item.placeholder { color: var(--text-color-tertiary); }
.catalog-dropdown-add {
  padding: 8px 12px; cursor: pointer; font-size: 13px;
  color: var(--primary-color); font-weight: 600; border-top: 1px solid var(--border-color);
}
.catalog-dropdown-add:hover { background: var(--bg-hover, #f1f5f9); }
.catalog-summary {
  padding: 8px 12px; margin: 8px 0; border-radius: 6px; font-size: 12px;
  background: var(--bg-secondary, #f8fafc); border: 1px solid var(--border-color);
}
.catalog-summary.hidden { display: none; }
.catalog-summary.placeholder-style { color: var(--text-color-tertiary); }
```

- [ ] **Step 3: JS — 카탈로그 검색 + 선택 + 인라인 등록 로직**

`infra_assets.js`에서 기존 `openCreateModal()`, `saveAsset()` 등을 교체. 주요 함수:

- `openCreateModal()` — 모달 초기화, 귀속사업 드롭다운에 topbar 선택 사업 자동 채움
- `searchCatalog(query)` — `GET /api/v1/product-catalog?q=...` 호출, 드롭다운 렌더링
- `selectCatalog(item)` — hidden input에 id 세팅, summary 표시
- `openInlineCatalogForm()` — 인라인 등록 폼 표시
- `saveNewCatalog()` — `POST /api/v1/product-catalog` 호출 후 자동 선택
- `saveAsset()` — `POST /api/v1/assets` 호출 (body: partner_id, hardware_model_id, asset_name, hostname, period_id)

- [ ] **Step 4: JS — 등록 완료 후 상세 패널 자동 오픈**

```javascript
async function saveAsset() {
  const catalogId = document.getElementById("catalog-id").value;
  if (!catalogId) { showToast("카탈로그 제품을 선택하세요.", "warning"); return; }
  const payload = {
    partner_id: getCtxPartnerId(),
    hardware_model_id: Number(catalogId),
    asset_name: document.getElementById("asset-name").value,
    hostname: document.getElementById("asset-hostname").value || null,
    period_id: document.getElementById("asset-period").value ? Number(document.getElementById("asset-period").value) : null,
  };
  try {
    const asset = await apiFetch("/api/v1/assets", { method: "POST", body: payload });
    modal.close();
    showToast("자산이 등록되었습니다.");
    await loadAssets();
    showAssetDetail(asset);  // 상세 패널 자동 오픈
  } catch (err) { showToast(err.message, "error"); }
}
```

- [ ] **Step 5: 기존 수정 모달 호출 제거**

`openEditModal()` 함수와 관련 이벤트 리스너를 제거한다. 상세 패널 헤더의 "수정" 버튼은 Task 5에서 인라인 편집으로 대체.

- [ ] **Step 6: 커밋**

```
feat(infra): simplify asset registration modal to 4 fields with catalog search
```

---

## Task 5: 프론트엔드 — 상세 패널 인라인 편집

상세 패널의 각 탭에서 직접 수정할 수 있도록 편집 모드를 추가한다.

**Files:**
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/modules/infra/templates/infra_assets.html`

- [x] **Step 1: "수정" 버튼 → 현재 탭 편집 모드 전환**

상세 패널 헤더의 "수정" 버튼 클릭 시:
- 현재 활성 탭의 read-only `detail-grid`를 `form` 요소로 교체
- 각 `<dd>` 값을 `<input>` / `<select>`로 변환
- "저장" / "취소" 버튼을 하단에 표시

기본 정보 탭 편집 시에는 카탈로그 제품 변경 드롭다운도 포함 (동일 유형만 검색).

- [x] **Step 2: 탭별 저장 → PATCH API 호출**

```javascript
async function saveDetailEdit(tab) {
  const changes = collectChangesFromForm(tab);
  if (Object.keys(changes).length === 0) { exitEditMode(); return; }
  try {
    const updated = await apiFetch("/api/v1/assets/" + _selectedAsset.id, { method: "PATCH", body: changes });
    _selectedAsset = updated;
    showToast("수정되었습니다.");
    exitEditMode();
    renderDetailTab(tab);
    loadAssets();  // 그리드도 갱신
  } catch (err) { showToast(err.message, "error"); }
}
```

- [ ] **Step 3: 커밋**

```
feat(infra): add inline edit mode to asset detail panel tabs
```

---

## Task 6: 카탈로그 관리 UI — 자산 유형 드롭다운 추가

카탈로그 관리 페이지에서 자산 유형을 선택/표시할 수 있도록 한다.

**Files:**
- Modify: `app/static/js/infra_product_catalog.js`

- [ ] **Step 1: 카탈로그 목록 그리드에 자산 유형 컬럼 추가**

AG Grid 컬럼에 `asset_type_key` 추가 (label로 표시).

- [ ] **Step 2: 카탈로그 등록/수정 모달에 자산 유형 드롭다운 추가**

`asset_type_codes` API에서 목록을 로드하여 `<select>` 렌더링.

- [ ] **Step 3: placeholder 항목은 삭제 버튼 미표시**

`is_placeholder === true`인 행에서 삭제 버튼을 숨기거나 비활성화.

- [ ] **Step 4: 커밋**

```
feat(infra): add asset type column to product catalog UI
```

---

## Task 7: 문서 갱신 + 최종 검증

**Files:**
- Modify: `docs/PROJECT_STRUCTURE.md` — 변경된 파일 반영
- 브라우저 E2E 검증

- [ ] **Step 1: PROJECT_STRUCTURE.md 갱신** (필요 시)

- [ ] **Step 2: 브라우저 E2E 검증**

1. 자산 등록 모달이 4개 필드만 표시되는지 확인
2. 카탈로그 검색 → 선택 → 요약 표시 확인
3. 카탈로그 매칭 없음 → "+ 새 제품 등록" → 인라인 등록 → 자동 선택 확인
4. placeholder 카탈로그 선택 → 자산 등록 → vendor/model NULL 확인
5. 귀속사업 자동 채움 → 등록 → PeriodAsset 생성 확인
6. 등록 후 상세 패널 자동 오픈 확인
7. 상세 패널에서 인라인 수정 → PATCH 저장 확인
8. 카탈로그 관리 페이지에서 자산 유형 컬럼/드롭다운 확인

- [ ] **Step 3: 커밋**

```
docs: update project structure for asset registration changes
```
