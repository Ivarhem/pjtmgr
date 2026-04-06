# 제조사관리 폴리싱 Implementation Plan

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** 제조사관리 페이지를 프로토타입에서 완성된 CRUD 관리 페이지로 전환한다.

**Architecture:** 기존 2컬럼 레이아웃(좌: AG-Grid 목록 / 우: 편집 폼) 유지. TSV 벌크 영역 제거, 태그 입력 기반 별칭 관리 추가. 백엔드에 DELETE 엔드포인트와 타입된 응답 스키마 추가. 기존 `renderTagChips` 패턴 참조하되, 삭제 시 confirm 팝업 요구사항에 맞게 커스텀 구현.

**Tech Stack:** Python/FastAPI/SQLAlchemy (백엔드), Vanilla JS + AG-Grid (프론트엔드), Jinja2 HTML 템플릿

**XSS 참고:** 기존 프로젝트의 `renderTagChips` (utils.js:344-355)는 innerHTML로 태그를 렌더링하는 패턴을 사용하고 있음. 이 계획에서도 동일 패턴을 사용하되, alias 값은 사용자 입력이므로 escapeHtml 처리 필수. 프로젝트에 이미 `escapeHtml` 함수가 있다면(`infra_product_catalog.js:87-92`) 이를 사용.

---

## File Map

| Action | File | Role |
|--------|------|------|
| Modify | `app/modules/infra/schemas/catalog_vendor_management.py` | 응답 스키마 추가 |
| Modify | `app/modules/infra/services/catalog_alias_service.py` | `delete_vendor_and_aliases` 함수 추가, `list_vendor_alias_summaries` alias id 포함으로 보강 |
| Modify | `app/modules/infra/services/catalog_integrity_service.py` | 삭제 서비스 위임 함수 추가 |
| Modify | `app/modules/infra/routers/catalog_integrity.py` | DELETE 엔드포인트 추가, GET 응답 타입 지정 |
| Modify | `app/templates/catalog_vendors.html` | TSV 제거, 태그 UI, 빈상태/신규/편집 모드 |
| Modify | `app/static/js/infra_catalog_management.js` | CRUD 로직, 권한 체크, 태그 관리 |
| Modify | `app/static/css/infra_common.css` | 빈상태 placeholder 스타일 추가 |
| Modify | `app/templates/catalog_integrity.html` | 벤더 탭에 제조사관리 링크 추가 |

---

### Task 1: 백엔드 — 응답 스키마 추가

**Files:**
- Modify: `app/modules/infra/schemas/catalog_vendor_management.py`

- [ ] **Step 1: 스키마 클래스 추가**

`catalog_vendor_management.py` 파일 상단, `CatalogVendorBulkUpsertRow` 클래스 위에 아래 두 클래스를 추가:

```python
class CatalogVendorAliasItem(BaseModel):
    id: int
    alias_value: str
    normalized_alias: str
    is_active: bool


class CatalogVendorSummary(BaseModel):
    vendor: str
    product_count: int
    alias_count: int
    aliases: list[CatalogVendorAliasItem]
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/schemas/catalog_vendor_management.py
git commit -m "feat(vendor): add CatalogVendorSummary and CatalogVendorAliasItem response schemas"
```

---

### Task 2: 백엔드 — 서비스 보강 (list 응답 + delete)

**Files:**
- Modify: `app/modules/infra/services/catalog_alias_service.py`
- Modify: `app/modules/infra/services/catalog_integrity_service.py`

- [ ] **Step 1: `list_vendor_alias_summaries`에서 alias id 포함하도록 수정**

`catalog_alias_service.py`의 `list_vendor_alias_summaries` 함수에서 alias_rows select에 `CatalogVendorAlias.id`와 `CatalogVendorAlias.is_active`를 추가하고, alias_map 빌드 시 포함. 또한 검색 시 alias_value도 검색 대상에 포함:

```python
def list_vendor_alias_summaries(db: Session, q: str | None = None) -> list[dict]:
    from app.modules.infra.models.product_catalog import ProductCatalog

    stmt = (
        select(
            ProductCatalog.vendor.label("vendor"),
            func.count(ProductCatalog.id).label("product_count"),
        )
        .group_by(ProductCatalog.vendor)
        .order_by(func.count(ProductCatalog.id).desc(), ProductCatalog.vendor.asc())
    )
    if q:
        like = f"%{q.strip()}%"
        alias_vendors = db.scalars(
            select(CatalogVendorAlias.vendor_canonical).where(
                CatalogVendorAlias.alias_value.ilike(like),
                CatalogVendorAlias.is_active.is_(True),
            )
        ).all()
        stmt = stmt.where(
            ProductCatalog.vendor.ilike(like)
            | ProductCatalog.vendor.in_(alias_vendors)
        )
    vendor_rows = db.execute(stmt).mappings().all()
    alias_rows = db.execute(
        select(
            CatalogVendorAlias.id,
            CatalogVendorAlias.vendor_canonical,
            CatalogVendorAlias.alias_value,
            CatalogVendorAlias.normalized_alias,
            CatalogVendorAlias.is_active,
        )
        .where(CatalogVendorAlias.is_active.is_(True))
        .order_by(CatalogVendorAlias.vendor_canonical.asc(), CatalogVendorAlias.sort_order.asc())
    ).mappings().all()

    alias_map: dict[str, list[dict]] = {}
    for row in alias_rows:
        alias_map.setdefault(row["vendor_canonical"], []).append(
            {
                "id": row["id"],
                "alias_value": row["alias_value"],
                "normalized_alias": row["normalized_alias"],
                "is_active": row["is_active"],
            }
        )

    results: list[dict] = []
    for row in vendor_rows:
        vendor = row["vendor"]
        aliases = alias_map.get(vendor, [])
        results.append(
            {
                "vendor": vendor,
                "product_count": int(row["product_count"] or 0),
                "alias_count": len(aliases),
                "aliases": aliases,
            }
        )
    return results
```

- [ ] **Step 2: `delete_vendor_and_aliases` 함수 추가**

`catalog_alias_service.py`의 `bulk_upsert_vendor_aliases` 함수 아래에 추가:

```python
def delete_vendor_and_aliases(db: Session, vendor_canonical: str, current_user: User) -> None:
    from app.modules.infra.models.product_catalog import ProductCatalog

    _require_taxonomy_edit(current_user)
    canonical = vendor_canonical.strip()
    if not canonical:
        raise BusinessRuleError("제조사명이 비어 있습니다.")

    product_count = db.scalar(
        select(func.count(ProductCatalog.id)).where(ProductCatalog.vendor == canonical)
    ) or 0
    if product_count > 0:
        raise BusinessRuleError(
            f"연결된 제품 {product_count}개가 있어 삭제할 수 없습니다.",
            status_code=409,
        )

    db.query(CatalogVendorAlias).filter(
        CatalogVendorAlias.vendor_canonical == canonical
    ).delete(synchronize_session="fetch")
    db.commit()
```

- [ ] **Step 3: integrity service에 위임 함수 추가**

`catalog_integrity_service.py`에 import에 `delete_vendor_and_aliases` 추가:

```python
from app.modules.infra.services.catalog_alias_service import (
    delete_vendor_and_aliases,
    get_attribute_option_alias,
    list_attribute_option_aliases,
    list_vendor_alias_summaries,
)
```

함수 추가:
```python
def delete_catalog_vendor_integrity(db: Session, vendor_canonical: str, current_user) -> None:
    delete_vendor_and_aliases(db, vendor_canonical, current_user)
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/infra/services/catalog_alias_service.py app/modules/infra/services/catalog_integrity_service.py
git commit -m "feat(vendor): add alias id to list response and delete_vendor_and_aliases service"
```

---

### Task 3: 백엔드 — 라우터 보강 (DELETE + 응답 타입)

**Files:**
- Modify: `app/modules/infra/routers/catalog_integrity.py`

- [ ] **Step 1: import 추가 및 엔드포인트 수정**

`catalog_integrity.py`에서:

1. import에 `CatalogVendorSummary` 추가:
```python
from app.modules.infra.schemas.catalog_vendor_management import (
    CatalogVendorBulkUpsertRequest,
    CatalogVendorBulkUpsertResponse,
    CatalogVendorSummary,
)
```

2. import에 `delete_catalog_vendor_integrity` 추가:
```python
from app.modules.infra.services.catalog_integrity_service import (
    delete_catalog_vendor_integrity,
    get_catalog_attribute_alias_integrity,
    list_catalog_attribute_alias_integrity,
    list_catalog_vendor_integrity,
    list_similar_catalog_products,
)
```

3. GET `/vendors` 엔드포인트의 반환 타입을 `list[dict]` → `list[CatalogVendorSummary]`로 변경:
```python
@router.get("/vendors", response_model=list[CatalogVendorSummary])
def list_catalog_integrity_vendors(
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CatalogVendorSummary]:
    return list_catalog_vendor_integrity(db, q=q)
```

4. DELETE 엔드포인트 추가 (POST `/vendors/bulk-upsert` 아래):
```python
@router.delete("/vendors/{vendor_canonical}", status_code=status.HTTP_204_NO_CONTENT)
def delete_catalog_integrity_vendor(
    vendor_canonical: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    delete_catalog_vendor_integrity(db, vendor_canonical, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/routers/catalog_integrity.py
git commit -m "feat(vendor): add DELETE endpoint and typed response for vendor list"
```

---

### Task 4: 프론트엔드 — HTML 템플릿 재구성

**Files:**
- Modify: `app/templates/catalog_vendors.html`

- [ ] **Step 1: 전체 템플릿 교체**

`catalog_vendors.html`을 아래 내용으로 교체:

```html
{% extends "base.html" %}
{% block title %}제조사 관리{% endblock %}
{% block styles %}<link rel="stylesheet" href="/static/css/infra_common.css">{% endblock %}
{% block content %}
<div class="tab-nav">
  <a href="/product-catalog" class="tab-btn">제품 카탈로그</a>
  <a href="/catalog-management/vendors" class="tab-btn active">제조사 관리</a>
  <a href="/catalog-management/products" class="tab-btn">제품 관리</a>
  <a href="/catalog-management/integrity" class="tab-btn">정합성 관리</a>
</div>

<div class="page-header">
  <h1>제조사 관리</h1>
</div>

<p class="data-note">대표 제조사명과 alias를 관리합니다. 제조사를 선택하면 우측에서 편집할 수 있습니다.</p>

<div class="catalog-management-shell">
  <section class="catalog-management-card">
    <h2>제조사 목록</h2>
    <div class="catalog-management-toolbar">
      <input type="text" id="catalog-vendor-search" class="input-search" placeholder="제조사명 또는 alias 검색">
      <button type="button" class="btn btn-secondary" id="btn-catalog-vendor-refresh">새로고침</button>
      <button type="button" class="btn btn-primary vendor-write-only" id="btn-catalog-vendor-add">+ 신규</button>
    </div>
    <div id="grid-catalog-vendors" class="ag-theme-quartz catalog-management-grid"></div>
  </section>

  <section class="catalog-management-card">
    <div id="vendor-detail-empty" class="vendor-detail-empty">
      <p>좌측에서 제조사를 선택하거나<br>새 제조사를 추가하세요.</p>
    </div>
    <div id="vendor-detail-content" class="is-hidden">
      <h2 id="vendor-detail-title">제조사 편집</h2>
      <form class="catalog-management-form">
        <label id="vendor-source-label">원래 제조사명
          <input type="text" id="catalog-vendor-source" class="input-text" readonly>
        </label>
        <label>정식 제조사명
          <input type="text" id="catalog-vendor-canonical" class="input-text" placeholder="대표 제조사명 입력">
        </label>
        <label class="chk-inline vendor-apply-row is-hidden" id="vendor-apply-row">
          <input type="checkbox" id="catalog-vendor-apply-products" checked>
          기존 제품의 제조사명도 일괄 변경
        </label>
        <label>Alias 목록</label>
        <div class="tag-input-wrap" id="vendor-alias-input-wrap">
          <span class="tag-list" id="vendor-alias-tag-list"></span>
          <input type="text" id="vendor-alias-input" class="tag-input-field vendor-write-only" placeholder="alias 입력 후 Enter">
        </div>
        <div class="catalog-management-actions">
          <button type="button" class="btn btn-primary vendor-write-only" id="btn-catalog-vendor-save">저장</button>
          <button type="button" class="btn btn-danger vendor-write-only is-hidden" id="btn-catalog-vendor-delete">삭제</button>
          <button type="button" class="btn btn-secondary" id="btn-catalog-vendor-cancel">취소</button>
        </div>
      </form>
    </div>
  </section>
</div>
{% endblock %}
{% block scripts %}
<script src="/static/js/infra_catalog_management.js"></script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/catalog_vendors.html
git commit -m "feat(vendor): redesign vendor management template with tag UI and CRUD modes"
```

---

### Task 5: 프론트엔드 — CSS 추가

**Files:**
- Modify: `app/static/css/infra_common.css`

- [ ] **Step 1: vendor detail 빈상태 + 유틸 스타일 추가**

`infra_common.css`에서 `.catalog-management-help` 규칙 블록 아래(약 line 1653 이후)에 추가:

```css
.vendor-detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  text-align: center;
  color: var(--text-color-tertiary);
  font-size: 15px;
  line-height: 1.8;
}

.vendor-apply-row.is-hidden { display: none; }
```

- [ ] **Step 2: Commit**

```bash
git add app/static/css/infra_common.css
git commit -m "feat(vendor): add vendor detail empty state CSS"
```

---

### Task 6: 프론트엔드 — JavaScript CRUD 재구현

**Files:**
- Modify: `app/static/js/infra_catalog_management.js`

- [ ] **Step 1: 전체 JS 파일 교체**

`infra_catalog_management.js`를 아래 내용으로 교체. 제품 관리 쪽 코드는 그대로 유지.

**중요:** 태그 렌더링 시 `escapeHtml` 처리. 이 함수는 `infra_product_catalog.js`에 정의되어 있으나 해당 페이지에서는 로드되지 않으므로, 파일 상단에 로컬 정의를 추가한다. (향후 utils.js로 이동 고려)

```javascript
/* ── 공통 유틸 ──────────────────────────────────────────── */

function _escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.textContent;
}

/* ── 제조사 관리 ──────────────────────────────────────────── */

let catalogVendorGridApi = null;
let _vendorAliases = [];          // 현재 편집 중인 alias 배열
let _vendorMode = "empty";        // "empty" | "new" | "edit"
let _vendorOriginal = null;       // 편집 모드 시 원래 vendor 문자열
let _canManageVendor = false;     // 권한 플래그

function initCatalogVendorGrid() {
  const target = document.getElementById("grid-catalog-vendors");
  if (!target || catalogVendorGridApi) return;
  catalogVendorGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "vendor", headerName: "제조사명", flex: 1, minWidth: 180 },
      { field: "product_count", headerName: "제품 수", width: 100 },
      { field: "alias_count", headerName: "alias 수", width: 100 },
    ],
    rowSelection: { mode: "singleRow" },
    animateRows: true,
    defaultColDef: { sortable: true, filter: true, resizable: true },
    onRowClicked: (event) => {
      const row = event.data || {};
      setVendorEditMode(row.vendor, row.aliases || []);
    },
  });
}

async function loadCatalogVendorPermissions() {
  try {
    const me = window.__me || await apiFetch("/api/v1/auth/me");
    window.__me = me;
    _canManageVendor = !!me?.permissions?.can_manage_catalog_taxonomy;
  } catch (_) {
    _canManageVendor = false;
  }
  document.querySelectorAll(".vendor-write-only").forEach((el) => {
    el.style.display = _canManageVendor ? "" : "none";
  });
}

async function loadCatalogVendorManagement() {
  if (!catalogVendorGridApi) return;
  const q = document.getElementById("catalog-vendor-search")?.value?.trim() || "";
  const rows = await apiFetch(`/api/v1/catalog-integrity/vendors${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  catalogVendorGridApi.setGridOption("rowData", rows);
}

function setVendorEmptyMode() {
  _vendorMode = "empty";
  _vendorOriginal = null;
  _vendorAliases = [];
  document.getElementById("vendor-detail-empty")?.classList.remove("is-hidden");
  document.getElementById("vendor-detail-content")?.classList.add("is-hidden");
}

function setVendorNewMode() {
  _vendorMode = "new";
  _vendorOriginal = null;
  _vendorAliases = [];

  document.getElementById("vendor-detail-empty")?.classList.add("is-hidden");
  document.getElementById("vendor-detail-content")?.classList.remove("is-hidden");
  document.getElementById("vendor-detail-title").textContent = "새 제조사 등록";
  document.getElementById("vendor-source-label")?.classList.add("is-hidden");
  document.getElementById("catalog-vendor-source").value = "";
  document.getElementById("catalog-vendor-canonical").value = "";
  document.getElementById("catalog-vendor-canonical").readOnly = false;
  document.getElementById("vendor-apply-row")?.classList.add("is-hidden");
  document.getElementById("btn-catalog-vendor-delete")?.classList.add("is-hidden");
  renderVendorAliasChips();
}

function setVendorEditMode(vendor, aliases) {
  _vendorMode = "edit";
  _vendorOriginal = vendor;
  _vendorAliases = (aliases || []).map((a) => a.alias_value);

  document.getElementById("vendor-detail-empty")?.classList.add("is-hidden");
  document.getElementById("vendor-detail-content")?.classList.remove("is-hidden");
  document.getElementById("vendor-detail-title").textContent = "제조사 편집";
  document.getElementById("vendor-source-label")?.classList.remove("is-hidden");
  document.getElementById("catalog-vendor-source").value = vendor;
  document.getElementById("catalog-vendor-canonical").value = vendor;
  document.getElementById("catalog-vendor-canonical").readOnly = false;
  document.getElementById("vendor-apply-row")?.classList.add("is-hidden");
  if (_canManageVendor) {
    document.getElementById("btn-catalog-vendor-delete")?.classList.remove("is-hidden");
  }
  renderVendorAliasChips();
}

function renderVendorAliasChips() {
  const listEl = document.getElementById("vendor-alias-tag-list");
  if (!listEl) return;
  // DOM 기반 렌더링으로 XSS 방지
  listEl.textContent = "";
  _vendorAliases.forEach((alias, idx) => {
    const chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.textContent = alias;
    if (_canManageVendor) {
      const xBtn = document.createElement("span");
      xBtn.className = "tag-chip-x";
      xBtn.dataset.idx = idx;
      xBtn.textContent = "\u00d7";
      xBtn.addEventListener("click", () => {
        if (confirm(`별칭 '${alias}'을(를) 삭제하시겠습니까?`)) {
          _vendorAliases.splice(idx, 1);
          renderVendorAliasChips();
        }
      });
      chip.appendChild(xBtn);
    }
    listEl.appendChild(chip);
  });
}

function onVendorCanonicalChange() {
  const canonical = document.getElementById("catalog-vendor-canonical")?.value?.trim() || "";
  const applyRow = document.getElementById("vendor-apply-row");
  if (_vendorMode === "edit" && canonical && canonical !== _vendorOriginal) {
    applyRow?.classList.remove("is-hidden");
  } else {
    applyRow?.classList.add("is-hidden");
  }
}

async function saveCatalogVendor() {
  const canonical = document.getElementById("catalog-vendor-canonical")?.value?.trim() || "";
  if (!canonical) {
    showToast("정식 제조사명을 입력하세요.", "warning");
    return;
  }
  const payload = {
    rows: [
      {
        source_vendor: _vendorMode === "edit" ? _vendorOriginal : null,
        canonical_vendor: canonical,
        aliases: [..._vendorAliases],
        apply_to_products: _vendorMode === "edit" && canonical !== _vendorOriginal
          ? !!document.getElementById("catalog-vendor-apply-products")?.checked
          : false,
        is_active: true,
      },
    ],
  };
  await apiFetch("/api/v1/catalog-integrity/vendors/bulk-upsert", { method: "POST", body: payload });
  showToast("제조사를 저장했습니다.", "success");
  await loadCatalogVendorManagement();
  // 저장 후 편집 모드 유지 — 새 이름으로 갱신
  setVendorEditMode(canonical, _vendorAliases.map((v) => ({ alias_value: v })));
}

async function deleteCatalogVendor() {
  if (!_vendorOriginal) return;
  // 그리드 데이터에서 연결 제품 수 확인
  const rows = [];
  catalogVendorGridApi?.forEachNode((node) => rows.push(node.data));
  const vendorRow = rows.find((r) => r.vendor === _vendorOriginal);
  if (vendorRow && vendorRow.product_count > 0) {
    alert(`연결된 제품 ${vendorRow.product_count}개가 있어 삭제할 수 없습니다.`);
    return;
  }
  if (!confirm(`제조사 '${_vendorOriginal}'과(와) 모든 별칭을 삭제하시겠습니까?`)) return;
  try {
    await apiFetch(`/api/v1/catalog-integrity/vendors/${encodeURIComponent(_vendorOriginal)}`, { method: "DELETE" });
    showToast("제조사를 삭제했습니다.", "success");
    await loadCatalogVendorManagement();
    setVendorEmptyMode();
  } catch (err) {
    alert(err.message || "삭제에 실패했습니다.");
  }
}


/* ── 제품 관리 ──────────────────────────────────────────── */

let catalogProductManageGridApi = null;

function initCatalogProductManageGrid() {
  const target = document.getElementById("grid-catalog-products-manage");
  if (!target || catalogProductManageGridApi) return;
  catalogProductManageGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "id", headerName: "ID", width: 90 },
      { field: "vendor", headerName: "제조사", width: 160 },
      { field: "name", headerName: "제품명", flex: 1, minWidth: 220 },
      { field: "product_type", headerName: "유형", width: 120 },
      { field: "classification_level_1_name", headerName: "1레벨", width: 130 },
      { field: "classification_level_2_name", headerName: "2레벨", width: 130 },
      { field: "classification_level_3_name", headerName: "3레벨", width: 150 },
    ],
    rowSelection: { mode: "singleRow" },
    animateRows: true,
    defaultColDef: { sortable: true, filter: true, resizable: true },
  });
}

async function loadCatalogProductManagement() {
  if (!catalogProductManageGridApi) return;
  const q = document.getElementById("catalog-product-search-manage")?.value?.trim() || "";
  const productType = document.getElementById("catalog-product-type-manage")?.value || "";
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (productType) params.set("product_type", productType);
  const rows = await apiFetch(`/api/v1/product-catalog${params.toString() ? `?${params.toString()}` : ""}`);
  catalogProductManageGridApi.setGridOption("rowData", rows);
}

function buildCatalogProductBulkRow(raw) {
  const row = {
    product_id: raw.product_id ? Number(raw.product_id) : null,
    vendor: String(raw.vendor || "").trim(),
    name: String(raw.name || "").trim(),
    product_type: String(raw.product_type || "hardware").trim() || "hardware",
    version: String(raw.version || "").trim() || null,
    domain: String(raw.domain || "").trim() || null,
    imp_type: String(raw.imp_type || "").trim() || null,
    product_family: String(raw.product_family || "").trim() || null,
    platform: String(raw.platform || "").trim() || null,
    reference_url: String(raw.reference_url || "").trim() || null,
    eos_date: String(raw.eos_date || "").trim() || null,
    eosl_date: String(raw.eosl_date || "").trim() || null,
    eosl_note: String(raw.eosl_note || "").trim() || null,
  };
  if (!row.vendor || !row.name) {
    throw new Error("vendor와 name은 필수입니다.");
  }
  return row;
}

function parseCatalogManagementTsv(text) {
  const lines = String(text || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) throw new Error("헤더와 데이터 행이 필요합니다.");
  const headers = lines[0].split("\t").map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = line.split("\t");
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    return row;
  });
}

function parseCatalogManagementBool(value, fallback = true) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (!normalized) return fallback;
  return !["false", "0", "n", "no"].includes(normalized);
}

async function saveCatalogProductManagementBulk() {
  const rawRows = parseCatalogManagementTsv(document.getElementById("catalog-product-bulk")?.value || "");
  const payload = {
    rows: rawRows.map((row) => buildCatalogProductBulkRow(row)),
  };
  const result = await apiFetch("/api/v1/product-catalog/bulk-upsert", { method: "POST", body: payload });
  const target = document.getElementById("catalog-product-result");
  if (target) {
    const lines = [`총 ${result.total}건`, `실패 ${result.failed}건`];
    if (result.created != null) lines.splice(1, 0, `생성 ${result.created}건`, `수정 ${result.updated}건`);
    if (result.created == null) lines.splice(1, 0, `처리 ${result.updated}건`);
    if (result.rows?.length) {
      lines.push("");
      result.rows.forEach((row) => {
        const prefix = row.status === "error" ? `[실패 ${row.row_no}]` : `[완료 ${row.row_no}]`;
        lines.push(`${prefix} ${row.canonical_vendor || row.vendor || "-"} ${row.name || ""} ${row.message || row.action || ""}`.trim());
      });
    }
    target.textContent = lines.join("\n");
  }
  showToast("제품 TSV 반영이 완료되었습니다.", result.failed ? "warning" : "success");
  await loadCatalogProductManagement();
}


/* ── 초기화 ──────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  initCatalogVendorGrid();
  initCatalogProductManageGrid();

  // 제조사 관리 초기화
  if (catalogVendorGridApi) {
    loadCatalogVendorPermissions().then(() => {
      loadCatalogVendorManagement().catch((error) => {
        console.error(error);
        showToast(error.message || "제조사 목록을 불러오지 못했습니다.", "error");
      });
    });

    document.getElementById("btn-catalog-vendor-refresh")?.addEventListener("click", () => {
      loadCatalogVendorManagement().catch((error) => showToast(error.message, "error"));
    });
    document.getElementById("catalog-vendor-search")?.addEventListener("input", () => {
      loadCatalogVendorManagement().catch((error) => showToast(error.message, "error"));
    });
    document.getElementById("btn-catalog-vendor-add")?.addEventListener("click", () => {
      setVendorNewMode();
    });
    document.getElementById("btn-catalog-vendor-save")?.addEventListener("click", () => {
      saveCatalogVendor().catch((error) => {
        console.error(error);
        showToast(error.message || "저장에 실패했습니다.", "error");
      });
    });
    document.getElementById("btn-catalog-vendor-delete")?.addEventListener("click", () => {
      deleteCatalogVendor().catch((error) => {
        console.error(error);
        showToast(error.message || "삭제에 실패했습니다.", "error");
      });
    });
    document.getElementById("btn-catalog-vendor-cancel")?.addEventListener("click", () => {
      setVendorEmptyMode();
    });
    document.getElementById("catalog-vendor-canonical")?.addEventListener("input", () => {
      onVendorCanonicalChange();
    });

    // 별칭 태그 입력 (Enter 또는 쉼표로 추가)
    document.getElementById("vendor-alias-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        const input = e.target;
        const val = input.value.replace(/,/g, "").trim();
        if (val && !_vendorAliases.includes(val)) {
          _vendorAliases.push(val);
          renderVendorAliasChips();
        }
        input.value = "";
      }
      if (e.key === "Backspace" && e.target.value === "" && _vendorAliases.length > 0) {
        const removed = _vendorAliases[_vendorAliases.length - 1];
        if (confirm(`별칭 '${removed}'을(를) 삭제하시겠습니까?`)) {
          _vendorAliases.pop();
          renderVendorAliasChips();
        }
      }
    });
  }

  // 제품 관리 초기화
  if (catalogProductManageGridApi) {
    loadCatalogProductManagement().catch((error) => {
      console.error(error);
      showToast(error.message || "제품 목록을 불러오지 못했습니다.", "error");
    });
  }

  document.getElementById("btn-catalog-product-refresh")?.addEventListener("click", () => {
    loadCatalogProductManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("catalog-product-search-manage")?.addEventListener("input", () => {
    loadCatalogProductManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("catalog-product-type-manage")?.addEventListener("change", () => {
    loadCatalogProductManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("btn-catalog-product-bulk-apply")?.addEventListener("click", () => {
    saveCatalogProductManagementBulk().catch((error) => {
      console.error(error);
      showToast(error.message || "제품 TSV 반영에 실패했습니다.", "error");
    });
  });
});
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/infra_catalog_management.js
git commit -m "feat(vendor): rewrite vendor management JS with CRUD, permissions, and tag-based alias editing"
```

---

### Task 7: 정합성 관리 — 제조사관리 링크 추가

**Files:**
- Modify: `app/templates/catalog_integrity.html`

- [ ] **Step 1: 벤더 탭에 링크 추가**

`catalog_integrity.html`에서 제조사 정리 안내 항목을 찾아 수정. 현재:
```html
<li>제조사 정리: 표기가 다른 제조사명을 대표명으로 통일합니다.</li>
```

아래로 변경:
```html
<li>제조사 정리: 표기가 다른 제조사명을 대표명으로 통일합니다. <a href="/catalog-management/vendors" class="link-primary">제조사 관리에서 편집 &rarr;</a></li>
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/catalog_integrity.html
git commit -m "feat(vendor): add link from integrity page to vendor management"
```

---

### Task 8: 검증

- [ ] **Step 1: 서버 실행 및 기본 동작 확인**

앱을 실행하고 아래를 확인:
1. `/catalog-management/vendors` 페이지 로드 정상
2. 좌측 그리드에 제조사 목록 로드
3. 행 클릭 시 우측 편집 폼 표시
4. "신규" 버튼 클릭 시 신규 모드 전환
5. 태그 입력(Enter/쉼표)으로 alias 추가
6. 태그 X 클릭 시 confirm 후 삭제
7. 저장 동작
8. 삭제 동작 (제품 없는 제조사)
9. 삭제 차단 (제품 있는 제조사)
10. 권한 없는 사용자로 접근 시 편집 버튼 숨김

- [ ] **Step 2: 정합성 관리 페이지에서 링크 확인**

`/catalog-management/integrity`에서 "제조사 관리에서 편집" 링크 클릭 시 제조사 관리 페이지로 이동 확인.

- [ ] **Step 3: Commit (필요 시 수정사항)**

검증 중 발견된 문제가 있으면 수정 후 커밋.
