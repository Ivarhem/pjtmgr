# 자산 카탈로그 선택 UX 변경 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자산의 model/vendor/category를 카탈로그 기반 읽기 전용으로 전환하고, 상세 패널 + 그리드에서 카탈로그 검색/선택 UX를 제공한다.

**Architecture:** `hardware_model_id` → `model_id`(NOT NULL, RESTRICT)로 변경. vendor/model/category 컬럼은 캐시로 유지하되 UI 직접 편집 차단. 상세 패널에 카탈로그 검색 위젯 추가, 그리드에 CatalogCellEditor 추가.

**Tech Stack:** Python/FastAPI/SQLAlchemy (백엔드), Vanilla JS + AG Grid (프론트엔드), Alembic (마이그레이션), pytest (테스트)

**Spec:** `docs/superpowers/specs/2026-04-02-catalog-cell-editor-design.md`

---

## Task 1: Alembic 마이그레이션 — hardware_model_id → model_id

**Files:**
- Create: `alembic/versions/0057_rename_hardware_model_id_to_model_id.py`

- [ ] **Step 1: 마이그레이션 파일 작성**

```python
"""Rename hardware_model_id to model_id, make NOT NULL, change ondelete to RESTRICT."""
revision = "0057"
down_revision = "0056"

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # 1. NULL인 자산 삭제 (연관 테이블 포함)
    op.execute("""
        DELETE FROM period_assets WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_aliases WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_events WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_role_assignments WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_contacts WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_relations WHERE source_asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        ) OR target_asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_related_partners WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_ips WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM asset_software WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM policy_assignments WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("""
        DELETE FROM port_maps WHERE asset_id IN (
            SELECT id FROM assets WHERE hardware_model_id IS NULL
        )
    """)
    op.execute("DELETE FROM assets WHERE hardware_model_id IS NULL")

    # 2. 기존 FK 제약 삭제
    op.drop_constraint("assets_hardware_model_id_fkey", "assets", type_="foreignkey")
    op.drop_index("ix_assets_hardware_model_id", "assets")

    # 3. 컬럼 리네임
    op.alter_column("assets", "hardware_model_id", new_column_name="model_id")

    # 4. NOT NULL 설정
    op.alter_column("assets", "model_id", nullable=False)

    # 5. 새 FK (RESTRICT) + 인덱스
    op.create_foreign_key(
        "assets_model_id_fkey", "assets",
        "product_catalog", ["model_id"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_assets_model_id", "assets", ["model_id"])


def downgrade() -> None:
    op.drop_constraint("assets_model_id_fkey", "assets", type_="foreignkey")
    op.drop_index("ix_assets_model_id", "assets")
    op.alter_column("assets", "model_id", new_column_name="hardware_model_id")
    op.alter_column("assets", "hardware_model_id", nullable=True)
    op.create_foreign_key(
        "assets_hardware_model_id_fkey", "assets",
        "product_catalog", ["hardware_model_id"], ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_assets_hardware_model_id", "assets", ["hardware_model_id"])
```

- [ ] **Step 2: 마이그레이션 적용 확인**

Run: `docker exec projmgr-app alembic upgrade head`
Expected: 성공, `0057` 적용

- [ ] **Step 3: 커밋**

```bash
git add alembic/versions/0057_rename_hardware_model_id_to_model_id.py
git commit -m "migration: rename hardware_model_id to model_id, NOT NULL + RESTRICT"
```

---

## Task 2: Asset 모델 + 스키마 변경

**Files:**
- Modify: `app/modules/infra/models/asset.py:29-32`
- Modify: `app/modules/infra/schemas/asset.py:10,28-29,35,47,95`

- [ ] **Step 1: Asset 모델 수정**

`app/modules/infra/models/asset.py` 라인 29-32 교체:

```python
    # Product Catalog 연동
    model_id: Mapped[int] = mapped_column(
        ForeignKey("product_catalog.id", ondelete="RESTRICT"), nullable=False, index=True
    )
```

- [ ] **Step 2: AssetCreate 스키마 수정**

`app/modules/infra/schemas/asset.py` 라인 10:

```python
    model_id: int               # 필수 — 카탈로그 제품
```

- [ ] **Step 3: AssetUpdate 스키마 수정**

`app/modules/infra/schemas/asset.py` 라인 28-29, 35, 47 — vendor/model/category/hardware_model_id 제거하고 model_id 추가:

```python
class AssetUpdate(BaseModel):
    period_id: int | None = None
    partner_id: int | None = None
    asset_code: str | None = None
    project_asset_number: str | None = None
    customer_asset_number: str | None = None
    asset_name: str | None = None
    role: str | None = None
    environment: str | None = None
    location: str | None = None
    status: str | None = None
    note: str | None = None
    model_id: int | None = None
    # Equipment Spec
    center_id: int | None = None
    room_id: int | None = None
    rack_id: int | None = None
    center: str | None = None
    operation_type: str | None = None
    equipment_id: str | None = None
    rack_no: str | None = None
    rack_unit: str | None = None
    phase: str | None = None
    received_date: date | None = None
    subcategory: str | None = None
    serial_no: str | None = None
    # Logical Config
    hostname: str | None = None
    cluster: str | None = None
    service_name: str | None = None
    zone: str | None = None
    service_ip: str | None = None
    mgmt_ip: str | None = None
    # Hardware Config
    size_unit: int | None = None
    lc_count: int | None = None
    ha_count: int | None = None
    utp_count: int | None = None
    power_count: int | None = None
    power_type: str | None = None
    firmware_version: str | None = None
    # Asset Info
    asset_class: str | None = None
    asset_number: str | None = None
    year_acquired: int | None = None
    dept: str | None = None
    primary_contact_name: str | None = None
    secondary_contact_name: str | None = None
    maintenance_vendor: str | None = None
```

제거된 필드: `vendor`, `model`, `category`, `hardware_model_id`
추가된 필드: `model_id`

- [ ] **Step 4: AssetRead 스키마 수정**

`app/modules/infra/schemas/asset.py` 라인 95:

```python
    model_id: int
```

(기존 `hardware_model_id: int | None = None` → `model_id: int`로 변경. NOT NULL이므로 Optional 아님.)

- [ ] **Step 5: 커밋**

```bash
git add app/modules/infra/models/asset.py app/modules/infra/schemas/asset.py
git commit -m "refactor: rename hardware_model_id to model_id in model and schemas"
```

---

## Task 3: 백엔드 서비스 리네임 + 직접 수정 차단

**Files:**
- Modify: `app/modules/infra/services/asset_service.py` (13곳)
- Modify: `app/modules/infra/services/product_catalog_service.py:585`

- [ ] **Step 1: asset_service.py 전체 hardware_model_id → model_id 리네임**

모든 `hardware_model_id` 참조를 `model_id`로 변경한다 (라인 86, 135, 146, 173, 246, 257, 290, 291, 376, 399, 448, 481, 482):

- 라인 86: `catalog_ids = {a.model_id for a in assets if a.model_id}`
  → model_id가 NOT NULL이므로: `catalog_ids = {a.model_id for a in assets}`
- 라인 135: `d["catalog_kind"] = catalog_map.get(asset.model_id)`
- 라인 146: `catalog_entity_map.get(asset.model_id),`
- 라인 173: `catalog_ids = {a.model_id for a in assets}`
- 라인 246: `d["catalog_kind"] = catalog_map.get(a.model_id)`
- 라인 257: `catalog_entity_map.get(a.model_id),`
- 라인 290: `if asset.model_id:` → 항상 True이므로 조건 제거 가능, 또는 유지
- 라인 291: `catalog = db.get(ProductCatalog, asset.model_id)`
- 라인 376: `catalog = db.get(ProductCatalog, payload.model_id)`
- 라인 399: `"model_id": payload.model_id,`
- 라인 448: `detail=f"카탈로그 #{payload.model_id} 기반으로 ..."`
- 라인 481: `if "model_id" in changes and changes["model_id"] is not None:`
- 라인 482: `new_catalog = db.get(ProductCatalog, changes["model_id"])`

- [ ] **Step 2: update_asset에서 vendor/model/category 직접 변경 차단 확인**

`AssetUpdate` 스키마에서 vendor/model/category 필드를 제거했으므로, `changes = payload.model_dump(exclude_unset=True)`에 이 필드들이 포함되지 않는다. 별도 코드 변경 불필요.

단, `update_asset` 함수 내에서 `model_id` 변경 시 자동으로 vendor/model/category를 카탈로그에서 동기화하는 기존 로직(라인 481-508)은 그대로 유지한다.

- [ ] **Step 3: product_catalog_service.py 삭제 가드 수정**

라인 585: `Asset.hardware_model_id` → `Asset.model_id`:

```python
count = db.scalar(
    select(Asset.id).where(Asset.model_id == product_id).limit(1)
)
```

- [ ] **Step 4: 커밋**

```bash
git add app/modules/infra/services/asset_service.py app/modules/infra/services/product_catalog_service.py
git commit -m "refactor: rename hardware_model_id to model_id in services"
```

---

## Task 4: 기존 테스트 수정 + 회귀 테스트

**Files:**
- Modify: `tests/infra/test_asset_service.py`

- [ ] **Step 1: 테스트 파일에서 hardware_model_id → model_id 일괄 리네임**

`tests/infra/test_asset_service.py` 전체에서 `hardware_model_id` → `model_id` 치환.

주요 변경 위치:
- `AssetCreate(..., hardware_model_id=catalog.id, ...)` → `AssetCreate(..., model_id=catalog.id, ...)`
- 모든 테스트 함수에서 동일 패턴 적용

- [ ] **Step 2: vendor/model 직접 수정 테스트가 있다면 model_id 기반으로 변경**

`AssetUpdate(vendor=..., model=..., category=...)` 형태의 테스트가 있으면 삭제하거나, `AssetUpdate(model_id=new_catalog.id)` 형태로 변경.

- [ ] **Step 3: 새 테스트 추가 — model_id 변경 시 vendor/model/category 자동 동기화**

```python
def test_update_model_id_syncs_vendor_model_category(db_session, admin_role_id) -> None:
    """model_id 변경 시 vendor/model/category가 카탈로그에서 자동 동기화된다."""
    admin = _make_admin_user(db_session, admin_role_id)
    partner = _make_partner(db_session)
    catalog1 = _make_catalog(db_session, type_key="server")

    asset = create_asset(
        db_session,
        AssetCreate(partner_id=partner.id, model_id=catalog1.id, asset_name="SRV-01"),
        admin,
    )
    assert asset.vendor == "Dell"
    assert asset.model == "PowerEdge R760"

    # 새 카탈로그 생성
    catalog2 = ProductCatalog(
        vendor="HP", name="ProLiant DL380", product_type="hardware",
        category="서버", asset_type_key="server",
    )
    db_session.add(catalog2)
    db_session.flush()

    updated = update_asset(
        db_session, asset.id,
        AssetUpdate(model_id=catalog2.id),
        admin,
    )
    assert updated.model_id == catalog2.id
    assert updated.vendor == "HP"
    assert updated.model == "ProLiant DL380"
```

- [ ] **Step 4: 테스트 실행**

Run: `docker exec projmgr-app pytest tests/infra/test_asset_service.py -v`
Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```bash
git add tests/infra/test_asset_service.py
git commit -m "test: update asset tests for model_id rename and sync behavior"
```

---

## Task 5: 프론트엔드 — CatalogCellEditor (그리드 인라인 편집)

**Files:**
- Modify: `app/static/js/infra_assets.js`

- [ ] **Step 1: CatalogCellEditor 클래스 작성**

`infra_assets.js`에서 기존 그리드 관련 코드 영역(GRID_EDITABLE_FIELDS 근처, 라인 160 이후)에 추가:

```javascript
/* ── CatalogCellEditor (AG Grid 셀 에디터) ── */
class CatalogCellEditor {
  init(params) {
    this.params = params;
    this.selectedModelId = null;

    this.container = document.createElement("div");
    this.container.className = "ag-cell-catalog-editor";

    this.input = document.createElement("input");
    this.input.type = "text";
    this.input.value = params.value || "";
    this.input.className = "ag-cell-input-editor";
    this.input.placeholder = "제조사 또는 모델명 검색";
    this.container.appendChild(this.input);

    this.dropdown = document.createElement("div");
    this.dropdown.className = "ag-cell-catalog-dropdown is-hidden";
    document.body.appendChild(this.dropdown);

    this._searchTimer = null;
    this.input.addEventListener("input", () => this._search());
    this.input.addEventListener("focus", () => this._search());
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        const first = this.dropdown.querySelector(".catalog-cell-option");
        if (first) first.focus();
      }
      if (e.key === "Escape") {
        setElementHidden(this.dropdown, true);
        this.params.stopEditing();
      }
    });
  }

  _search() {
    const q = this.input.value.trim();
    if (!q) { setElementHidden(this.dropdown, true); return; }
    clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(async () => {
      try {
        const items = await apiFetch("/api/v1/product-catalog?q=" + encodeURIComponent(q));
        this._renderDropdown(items);
      } catch (e) { showToast(e.message, "error"); }
    }, 300);
  }

  _renderDropdown(items) {
    this.dropdown.textContent = "";
    items.forEach((item) => {
      const div = document.createElement("div");
      const label = ((item.vendor || "") + " " + (item.name || "")).trim();
      const kindLabel = CATALOG_KIND_LABELS[item.product_type] || item.product_type || "미지정";
      div.textContent = "[" + kindLabel + "] " + label;

      if (!buildCatalogClassificationPath(item)) {
        div.className = "catalog-cell-option disabled";
        const warn = document.createElement("span");
        warn.textContent = " (분류 미설정)";
        warn.className = "catalog-warning-note";
        div.appendChild(warn);
      } else {
        div.className = "catalog-cell-option" + (item.is_placeholder ? " placeholder" : "");
        div.tabIndex = -1;
        div.addEventListener("mousedown", (e) => {
          e.preventDefault();
          this._selectItem(item);
        });
        div.addEventListener("keydown", (e) => {
          if (e.key === "Enter") this._selectItem(item);
          if (e.key === "ArrowDown" && div.nextElementSibling) { e.preventDefault(); div.nextElementSibling.focus(); }
          if (e.key === "ArrowUp" && div.previousElementSibling) { e.preventDefault(); div.previousElementSibling.focus(); }
          if (e.key === "Escape") { setElementHidden(this.dropdown, true); this.params.stopEditing(); }
        });
      }
      this.dropdown.appendChild(div);
    });

    // 새 제품 등록 옵션
    const addDiv = document.createElement("div");
    addDiv.className = "catalog-cell-option-new";
    addDiv.textContent = "+ 새 제품 등록";
    addDiv.addEventListener("mousedown", (e) => {
      e.preventDefault();
      setElementHidden(this.dropdown, true);
      this.params.stopEditing();
      openInlineCatalogForm();
    });
    this.dropdown.appendChild(addDiv);

    const rect = this.input.getBoundingClientRect();
    this.dropdown.style.left = rect.left + "px";
    this.dropdown.style.top = rect.bottom + "px";
    this.dropdown.style.width = Math.max(rect.width, 320) + "px";
    setElementHidden(this.dropdown, false);
  }

  _selectItem(item) {
    this.selectedModelId = item.id;
    this.input.value = ((item.vendor || "") + " " + (item.name || "")).trim();
    setElementHidden(this.dropdown, true);
    this.params.stopEditing();
  }

  getGui() { return this.container; }
  afterGuiAttached() { this.input.focus(); this.input.select(); }
  getValue() {
    // selectedModelId가 있으면 선택됨, 없으면 변경 없음
    if (this.selectedModelId) {
      return { _catalogModelId: this.selectedModelId, display: this.input.value };
    }
    return this.params.value; // 변경 없음 — 원래 값 반환
  }
  destroy() { this.dropdown.remove(); }
  isPopup() { return true; }
}
```

- [ ] **Step 2: 그리드 model 컬럼에 CatalogCellEditor 적용**

`infra_assets.js` 라인 257 교체:

```javascript
  {
    field: "model", headerName: "모델명", width: 190,
    valueFormatter: (p) => {
      if (p.value && typeof p.value === "object") return p.value.display || "—";
      return p.value || "—";
    },
    editable: () => isGridFieldEditable("model"),
    cellEditor: CatalogCellEditor,
    cellClass: (p) => getGridCellClass(p.colDef.field),
  },
```

- [ ] **Step 3: handleGridCellValueChanged에 model 필드 특수 처리 추가**

`infra_assets.js` 라인 596-624, `handleGridCellValueChanged` 함수 내에서 model 필드 분기 추가.

기존 `if (field === "current_role_id")` 분기 뒤에 `else if (field === "model")` 추가:

```javascript
    } else if (field === "model") {
      // CatalogCellEditor가 { _catalogModelId, display } 객체를 반환
      const val = event.newValue;
      if (!val || !val._catalogModelId) {
        // 선택 안됨 — 원래 값 복원
        row.model = event.oldValue;
        gridApi?.refreshCells({ rowNodes: [event.node], force: true });
        return;
      }
      updated = await apiFetch(`/api/v1/assets/${row.id}`, {
        method: "PATCH",
        body: { model_id: val._catalogModelId },
      });
      // 서버 응답으로 model/vendor/category 등 갱신
      row.model = updated.model;
    } else {
```

- [ ] **Step 4: GRID_EDITABLE_FIELDS에서 category 제거**

라인 152-161에서 `"category"` 제거 (카탈로그에서 파생되므로 직접 편집 불가):

```javascript
const GRID_EDITABLE_FIELDS = new Set([
  "project_asset_number",
  "asset_name",
  "current_role_id",
  "hostname",
  "model",
  "operation_type",
  "status",
]);
```

- [ ] **Step 5: 커밋**

```bash
git add app/static/js/infra_assets.js
git commit -m "feat: add CatalogCellEditor for grid inline catalog selection"
```

---

## Task 6: 프론트엔드 — 상세 패널 카탈로그 편집 위젯

**Files:**
- Modify: `app/static/js/infra_assets.js:721-739` (DETAIL_EDIT_FIELDS)
- Modify: `app/static/js/infra_assets.js:1602-1686` (buildDetailEditFields)
- Modify: `app/static/js/infra_assets.js:1777-1815` (saveDetailEdit)

- [ ] **Step 1: DETAIL_EDIT_FIELDS에서 vendor/model 제거, model_id 추가**

라인 721-740 교체:

```javascript
const DETAIL_EDIT_FIELDS = {
  overview: [
    ["프로젝트코드", "project_asset_number"],
    ["고객 자산번호", "customer_asset_number"],
    ["자산명", "asset_name"],
    ["귀속사업", "period_id"],
    ["카탈로그 제품", "model_id"],
    ["시리얼", "serial_no"],
    ["장비 ID", "equipment_id"],
    ["자산 번호", "asset_number"],
    ["자산 등급", "asset_class"],
    ["크기(U)", "size_unit"],
    ["LC", "lc_count"],
    ["HA", "ha_count"],
    ["UTP", "utp_count"],
    ["전원", "power_count"],
    ["전원 유형", "power_type"],
    ["펌웨어", "firmware_version"],
  ],
```

- [ ] **Step 2: buildDetailEditFields에 model_id 카탈로그 검색 위젯 추가**

`buildDetailEditFields` 함수(라인 1602)에서, `key === "period_id"` 분기와 동일한 수준에 `key === "model_id"` 분기 추가.

`} else if (key === "center_id") {` 앞에 삽입:

```javascript
    } else if (key === "model_id") {
      // 카탈로그 검색 위젯
      const wrap = document.createElement("div");
      wrap.className = "catalog-search-wrap";

      input = document.createElement("input");
      input.type = "text";
      input.placeholder = "제조사 또는 모델명 검색";
      // 현재 카탈로그 정보를 초기값으로 표시
      const currentDisplay = [_selectedAsset.vendor, _selectedAsset.model].filter(Boolean).join(" ");
      input.value = currentDisplay;
      input.autocomplete = "off";
      wrap.appendChild(input);

      const hiddenId = document.createElement("input");
      hiddenId.type = "hidden";
      hiddenId.value = _selectedAsset.model_id || "";
      hiddenId.dataset.field = "model_id";
      wrap.appendChild(hiddenId);

      const dd = document.createElement("div");
      dd.className = "catalog-dropdown hidden";
      wrap.appendChild(dd);

      let searchTimer = null;
      input.addEventListener("input", () => {
        const q = input.value.trim();
        if (!q) { dd.classList.add("hidden"); return; }
        clearTimeout(searchTimer);
        searchTimer = setTimeout(async () => {
          try {
            const items = await apiFetch("/api/v1/product-catalog?q=" + encodeURIComponent(q));
            dd.textContent = "";
            items.forEach((item) => {
              const div = document.createElement("div");
              const itemLabel = ((item.vendor || "") + " " + (item.name || "")).trim();
              const kindLabel = CATALOG_KIND_LABELS[item.product_type] || item.product_type || "미지정";
              div.textContent = "[" + kindLabel + "] " + itemLabel;
              if (!buildCatalogClassificationPath(item)) {
                div.className = "catalog-dropdown-item disabled";
                const warn = document.createElement("span");
                warn.textContent = " (분류 미설정)";
                warn.className = "catalog-warning-note";
                div.appendChild(warn);
              } else {
                div.className = "catalog-dropdown-item" + (item.is_placeholder ? " placeholder" : "");
                div.addEventListener("click", () => {
                  hiddenId.value = item.id;
                  input.value = itemLabel;
                  dd.classList.add("hidden");
                });
              }
              dd.appendChild(div);
            });
            const addDiv = document.createElement("div");
            addDiv.className = "catalog-dropdown-add";
            addDiv.textContent = "+ 새 제품 등록";
            addDiv.addEventListener("click", () => { dd.classList.add("hidden"); openInlineCatalogForm(); });
            dd.appendChild(addDiv);
            dd.classList.remove("hidden");
          } catch (e) { showToast(e.message, "error"); }
        }, 300);
      });

      // input이 아닌 wrap을 fieldWrap에 추가
      fieldWrap.appendChild(wrap);
      container.appendChild(fieldWrap);
      continue; // 아래 기본 input 추가 로직 건너뛰기
```

- [ ] **Step 3: saveDetailEdit에 model_id 변경 감지 추가**

`saveDetailEdit` 함수(라인 1777)에서, `fields.forEach` 내부의 `key === "period_id"` 분기 뒤에 `model_id` 분기 추가:

```javascript
    } else if (key === "model_id") {
      const parsed = val === "" ? null : Number(val);
      const original = _selectedAsset.model_id;
      if (parsed !== original && parsed !== null) changes.model_id = parsed;
```

- [ ] **Step 4: 커밋**

```bash
git add app/static/js/infra_assets.js
git commit -m "feat: add catalog search widget in detail panel edit mode"
```

---

## Task 7: 프론트엔드 — 등록 모달 + 기타 정리

**Files:**
- Modify: `app/static/js/infra_assets.js:2525` (saveAsset)
- Modify: `app/static/js/infra_assets.js:255` (category 컬럼 editable)

- [ ] **Step 1: saveAsset에서 hardware_model_id → model_id**

라인 2525:

```javascript
    model_id: Number(catalogId),
```

- [ ] **Step 2: category 그리드 컬럼 editable 제거**

라인 255에서 `editable: () => isGridFieldEditable("category")` → `editable: false`:

```javascript
  { field: "category", headerName: "분류", width: 130, valueFormatter: (p) => p.value || "—", editable: false, cellClass: (p) => getGridCellClass(p.colDef.field), hide: true },
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/js/infra_assets.js
git commit -m "fix: rename hardware_model_id to model_id in frontend, lock category editing"
```

---

## Task 8: CSS 스타일 — CatalogCellEditor 드롭다운

**Files:**
- Modify: `app/static/css/infra_assets.css` (또는 해당 CSS 파일)

- [ ] **Step 1: CatalogCellEditor 스타일 추가**

기존 `contract_detail.css`의 `ag-cell-partner-dropdown` 스타일을 참조하여, `infra_assets.css`(또는 해당 CSS 파일)에 추가:

```css
/* CatalogCellEditor 드롭다운 */
.ag-cell-catalog-dropdown {
  position: fixed;
  z-index: 9999;
  background: var(--surface-color);
  border: 1px solid var(--border-color);
  border-radius: 4px;
  max-height: 260px;
  overflow-y: auto;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.catalog-cell-option {
  padding: 5px 8px;
  cursor: pointer;
  font-size: 12px;
  border-bottom: 1px solid var(--border-color-light);
  color: var(--text-color);
}
.catalog-cell-option:hover { background: color-mix(in srgb, var(--primary-color) 10%, var(--surface-color)); }
.catalog-cell-option:focus { background: var(--info-soft-bg); outline: none; }
.catalog-cell-option.disabled {
  color: var(--text-muted);
  cursor: not-allowed;
  opacity: 0.6;
}
.catalog-cell-option.placeholder { font-style: italic; opacity: 0.8; }

.catalog-cell-option-new {
  padding: 6px 8px;
  cursor: pointer;
  font-size: 12px;
  color: var(--primary-color);
  font-weight: 600;
  border-top: 1px solid var(--border-color);
}
.catalog-cell-option-new:hover { background: color-mix(in srgb, var(--primary-color) 10%, var(--surface-color)); }
```

- [ ] **Step 2: 커밋**

```bash
git add app/static/css/infra_assets.css
git commit -m "style: add CatalogCellEditor dropdown styles"
```

---

## Task 9: 통합 검증

- [ ] **Step 1: 서버 재시작 및 마이그레이션 확인**

Run: `docker restart projmgr-app`
확인: 로그에서 `alembic upgrade head` → `0057` 적용 확인

- [ ] **Step 2: 브라우저 E2E 검증**

1. 자산 목록 페이지 접속 → 기존 자산 표시 확인
2. 자산 등록 모달 → 카탈로그 검색/선택 → 등록 → 성공
3. 그리드에서 모델명 셀 클릭 → CatalogCellEditor 드롭다운 → 검색 → 선택 → vendor/model 자동 갱신
4. 상세 패널 편집 → 카탈로그 제품 검색/선택 → 저장 → vendor/model/category 자동 갱신
5. 상세 패널에서 vendor/model/category 직접 편집 불가 확인

- [ ] **Step 3: 테스트 스위트 실행**

Run: `docker exec projmgr-app pytest tests/infra/ -v`
Expected: 전체 PASS

- [ ] **Step 4: 문서 갱신 확인**

CLAUDE.md SS2 매핑표 기준:
- 인프라 비즈니스 규칙 변경 → `docs/guidelines/infra.md` 확인 필요 여부 검토
- 프론트엔드 패턴 변경 → `docs/guidelines/frontend.md` 확인 필요 여부 검토
- 해소된 KNOWN_ISSUES 항목 확인
