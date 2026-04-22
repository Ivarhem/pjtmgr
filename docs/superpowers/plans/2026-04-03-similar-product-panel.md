# 유사 제품 패널 + 병합 기능 Implementation Plan

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** 기준정보관리 탭에서 제품 클릭 시 유사 제품을 조회하고, 병합(흡수)/무시할 수 있는 수평 확장 패널을 구현한다.

**Architecture:** 백엔드에 dismissal 모델 + merge/dismiss 서비스를 추가하고, similarity-check API를 확장한다. 프론트엔드에서는 기존 MDM 2패널 레이아웃 오른쪽에 유사 제품 패널을 수평 확장하는 3패널 구조로 전환한다.

**Tech Stack:** Python/FastAPI/SQLAlchemy (백엔드), vanilla JS + ag-Grid (프론트엔드), Alembic (마이그레이션)

---

## File Structure

### 새로 생성

| 파일 | 역할 |
|------|------|
| `app/modules/infra/models/product_similarity_dismissal.py` | 무시 쌍 DB 모델 |
| `app/modules/infra/services/catalog_merge_service.py` | 병합 + 무시 비즈니스 로직 |
| `alembic/versions/0059_product_similarity_dismissal.py` | 마이그레이션 |

### 수정

| 파일 | 변경 내용 |
|------|-----------|
| `app/modules/infra/models/__init__.py` | dismissal 모델 import/export 추가 |
| `app/modules/infra/schemas/catalog_similarity.py` | asset_count 필드, merge/dismiss 스키마 추가 |
| `app/modules/infra/services/catalog_similarity_service.py` | dismissal 필터 + asset_count 추가 |
| `app/modules/infra/routers/product_catalogs.py` | merge, dismiss 엔드포인트 추가 |
| `app/templates/catalog_integrity.html` | 유사 제품 패널 HTML (스플리터 + 토글 + 카드 영역) |
| `app/static/js/infra_catalog_integrity.js` | 제품 클릭 → 유사 제품 로드/렌더, 병합/무시 액션, 스플리터 |
| `app/static/css/infra_common.css` | `.mdm-similar-*` 스타일 추가 |

---

## Task 1: Dismissal 모델 + 마이그레이션

**Files:**
- Create: `app/modules/infra/models/product_similarity_dismissal.py`
- Create: `alembic/versions/0059_product_similarity_dismissal.py`
- Modify: `app/modules/infra/models/__init__.py`

- [ ] **Step 1: Create dismissal model**

```python
# app/modules/infra/models/product_similarity_dismissal.py
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.base_model import TimestampMixin


class ProductSimilarityDismissal(TimestampMixin, Base):
    __tablename__ = "product_similarity_dismissal"
    __table_args__ = (
        UniqueConstraint("product_id_a", "product_id_b", name="uq_similarity_dismissal_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id_a: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_catalog.id", ondelete="CASCADE"), index=True
    )
    product_id_b: Mapped[int] = mapped_column(
        Integer, ForeignKey("product_catalog.id", ondelete="CASCADE"), index=True
    )
```

- [ ] **Step 2: Register in `__init__.py`**

`app/modules/infra/models/__init__.py` 끝에 추가:

```python
from app.modules.infra.models.product_similarity_dismissal import ProductSimilarityDismissal
```

`__all__` 리스트에 `"ProductSimilarityDismissal"` 추가.

- [ ] **Step 3: Create Alembic migration**

```python
# alembic/versions/0059_product_similarity_dismissal.py
"""product similarity dismissal table

Revision ID: 0059
Revises: 0058
"""
from alembic import op
import sqlalchemy as sa

revision = "0059"
down_revision = "0058"

def upgrade() -> None:
    op.create_table(
        "product_similarity_dismissal",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id_a", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("product_id_b", sa.Integer(), sa.ForeignKey("product_catalog.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("product_id_a", "product_id_b", name="uq_similarity_dismissal_pair"),
    )

def downgrade() -> None:
    op.drop_table("product_similarity_dismissal")
```

- [ ] **Step 4: Run migration**

Run: `docker exec pjtmgr-app alembic upgrade head`
Expected: "Running upgrade 0058 -> 0059"

- [ ] **Step 5: Commit**

```bash
git add app/modules/infra/models/product_similarity_dismissal.py app/modules/infra/models/__init__.py alembic/versions/0059_product_similarity_dismissal.py
git commit -m "feat: add product_similarity_dismissal model and migration"
```

---

## Task 2: Schemas 확장

**Files:**
- Modify: `app/modules/infra/schemas/catalog_similarity.py`

- [ ] **Step 1: Add merge/dismiss schemas and asset_count**

`app/modules/infra/schemas/catalog_similarity.py`를 다음으로 교체:

```python
from __future__ import annotations

from pydantic import BaseModel


class CatalogSimilarityCheckRequest(BaseModel):
    vendor: str
    name: str
    exclude_product_id: int | None = None


class CatalogSimilarityCandidate(BaseModel):
    id: int
    vendor: str
    name: str
    score: int
    exact_normalized: bool = False
    asset_count: int = 0


class CatalogSimilarityCheckResponse(BaseModel):
    normalized_vendor: str
    normalized_name: str
    exact_matches: list[CatalogSimilarityCandidate]
    similar_matches: list[CatalogSimilarityCandidate]


class ProductMergeRequest(BaseModel):
    source_id: int
    target_id: int


class ProductMergeResponse(BaseModel):
    merged_asset_count: int
    source_vendor: str
    source_name: str
    target_vendor: str
    target_name: str


class ProductDismissRequest(BaseModel):
    product_id_a: int
    product_id_b: int
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/schemas/catalog_similarity.py
git commit -m "feat: add merge/dismiss schemas and asset_count to similarity candidate"
```

---

## Task 3: Merge + Dismiss 서비스

**Files:**
- Create: `app/modules/infra/services/catalog_merge_service.py`

- [ ] **Step 1: Create merge service**

```python
# app/modules/infra/services/catalog_merge_service.py
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import BusinessRuleError
from app.modules.common.models.user import User
from app.modules.common.services import audit
from app.modules.infra.models.asset import Asset
from app.modules.infra.models.product_catalog import ProductCatalog
from app.modules.infra.models.product_similarity_dismissal import ProductSimilarityDismissal
from app.modules.infra.services.product_catalog_service import invalidate_product_list_cache


def merge_products(
    db: Session,
    *,
    source_id: int,
    target_id: int,
    current_user: User,
) -> dict:
    if source_id == target_id:
        raise BusinessRuleError("동일한 제품을 병합할 수 없습니다.")

    source = db.get(ProductCatalog, source_id)
    target = db.get(ProductCatalog, target_id)
    if not source:
        raise BusinessRuleError("원본 제품을 찾을 수 없습니다.", status_code=404)
    if not target:
        raise BusinessRuleError("대상 제품을 찾을 수 없습니다.", status_code=404)
    if source.is_placeholder:
        raise BusinessRuleError("시스템 placeholder 항목은 병합할 수 없습니다.")

    # 자산 이전
    asset_count = db.scalar(
        select(func.count()).select_from(Asset).where(Asset.model_id == source_id)
    ) or 0

    if asset_count > 0:
        db.execute(
            update(Asset).where(Asset.model_id == source_id).values(model_id=target_id)
        )

    result = {
        "merged_asset_count": asset_count,
        "source_vendor": source.vendor,
        "source_name": source.name,
        "target_vendor": target.vendor,
        "target_name": target.name,
    }

    audit.log(
        db,
        user_id=current_user.id,
        action="merge",
        entity_type="product_catalog",
        entity_id=target.id,
        summary=f"제품 병합: {source.vendor} {source.name} → {target.vendor} {target.name} (자산 {asset_count}건 이전)",
        module="infra",
    )

    # source 삭제 (CASCADE: specs, interfaces, attributes, cache)
    db.delete(source)
    db.commit()
    invalidate_product_list_cache(db)

    return result


def dismiss_similarity(
    db: Session,
    *,
    product_id_a: int,
    product_id_b: int,
) -> None:
    # a < b로 정규화
    a, b = min(product_id_a, product_id_b), max(product_id_a, product_id_b)

    existing = db.scalar(
        select(ProductSimilarityDismissal).where(
            ProductSimilarityDismissal.product_id_a == a,
            ProductSimilarityDismissal.product_id_b == b,
        )
    )
    if existing:
        return

    db.add(ProductSimilarityDismissal(product_id_a=a, product_id_b=b))
    db.commit()


def get_dismissed_pairs(db: Session, product_id: int) -> set[int]:
    """주어진 product_id와 무시 관계에 있는 상대 product_id 집합을 반환."""
    rows = db.execute(
        select(
            ProductSimilarityDismissal.product_id_a,
            ProductSimilarityDismissal.product_id_b,
        ).where(
            (ProductSimilarityDismissal.product_id_a == product_id)
            | (ProductSimilarityDismissal.product_id_b == product_id)
        )
    ).all()
    result: set[int] = set()
    for a, b in rows:
        result.add(a if a != product_id else b)
    return result
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/services/catalog_merge_service.py
git commit -m "feat: add catalog merge and dismiss services"
```

---

## Task 4: similarity-check API 확장

**Files:**
- Modify: `app/modules/infra/services/catalog_similarity_service.py:47-96`

- [ ] **Step 1: Add asset_count and dismissal filtering**

`find_similar_products` 함수의 시그니처와 본문을 수정한다. 기존 함수 전체를 다음으로 교체:

```python
def find_similar_products(
    db: Session,
    *,
    vendor: str,
    name: str,
    exclude_product_id: int | None = None,
    limit: int = 5,
) -> dict:
    from app.modules.infra.models.asset import Asset
    from app.modules.infra.services.catalog_merge_service import get_dismissed_pairs

    normalized_vendor = normalize_vendor_name(vendor)
    normalized_name = normalize_product_name(name)
    tokens = tokenize_product_name(name)
    stmt = select(ProductCatalog).order_by(ProductCatalog.vendor.asc(), ProductCatalog.name.asc())
    candidates = list(db.scalars(stmt))

    # dismissal 필터
    dismissed_ids: set[int] = set()
    if exclude_product_id is not None:
        dismissed_ids = get_dismissed_pairs(db, exclude_product_id)

    # 자산 수 일괄 조회
    asset_count_map: dict[int, int] = {}
    if candidates:
        from sqlalchemy import func
        rows = db.execute(
            select(Asset.model_id, func.count()).group_by(Asset.model_id)
        ).all()
        asset_count_map = {r[0]: r[1] for r in rows}

    exact_matches: list[dict] = []
    similar_matches: list[dict] = []
    for candidate in candidates:
        if exclude_product_id is not None and candidate.id == exclude_product_id:
            continue
        if candidate.id in dismissed_ids:
            continue
        score = score_product_similarity(
            normalized_vendor=normalized_vendor,
            normalized_name=normalized_name,
            source_tokens=tokens,
            candidate=candidate,
        )
        if score <= 0:
            continue
        payload = {
            "id": candidate.id,
            "vendor": candidate.vendor,
            "name": candidate.name,
            "score": score,
            "asset_count": asset_count_map.get(candidate.id, 0),
            "exact_normalized": bool(
                normalized_vendor
                and normalized_name
                and candidate.normalized_vendor == normalized_vendor
                and candidate.normalized_name == normalized_name
            ),
        }
        if payload["exact_normalized"]:
            exact_matches.append(payload)
        elif score >= 75:
            similar_matches.append(payload)
    exact_matches.sort(key=lambda item: (-item["score"], item["vendor"], item["name"], item["id"]))
    similar_matches.sort(key=lambda item: (-item["score"], item["vendor"], item["name"], item["id"]))
    return {
        "normalized_vendor": normalized_vendor,
        "normalized_name": normalized_name,
        "exact_matches": exact_matches[:limit],
        "similar_matches": similar_matches[:limit],
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/services/catalog_similarity_service.py
git commit -m "feat: add asset_count and dismissal filtering to similarity check"
```

---

## Task 5: Router 엔드포인트 추가

**Files:**
- Modify: `app/modules/infra/routers/product_catalogs.py`

- [ ] **Step 1: Add imports**

`product_catalogs.py` 상단 imports에 추가:

```python
from app.modules.infra.schemas.catalog_similarity import (
    CatalogSimilarityCheckRequest,
    CatalogSimilarityCheckResponse,
    ProductMergeRequest,
    ProductMergeResponse,
    ProductDismissRequest,
)
from app.modules.infra.services.catalog_merge_service import (
    merge_products,
    dismiss_similarity,
)
```

기존 `CatalogSimilarityCheckRequest`, `CatalogSimilarityCheckResponse` import는 새 import 블록에 통합되므로 기존 줄(17-20)을 제거.

- [ ] **Step 2: Add merge endpoint**

`similarity-check` 엔드포인트(라인 98-109) 바로 뒤에 추가:

```python
@router.post("/merge", response_model=ProductMergeResponse)
def merge_products_endpoint(
    payload: ProductMergeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProductMergeResponse:
    result = merge_products(
        db,
        source_id=payload.source_id,
        target_id=payload.target_id,
        current_user=current_user,
    )
    return ProductMergeResponse(**result)
```

- [ ] **Step 3: Add dismiss endpoint**

merge 엔드포인트 바로 뒤에 추가:

```python
@router.post("/similarity-dismiss", status_code=status.HTTP_204_NO_CONTENT)
def dismiss_similarity_endpoint(
    payload: ProductDismissRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    dismiss_similarity(db, product_id_a=payload.product_id_a, product_id_b=payload.product_id_b)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/infra/routers/product_catalogs.py
git commit -m "feat: add merge and dismiss API endpoints"
```

---

## Task 6: 프론트엔드 — HTML 패널 구조

**Files:**
- Modify: `app/templates/catalog_integrity.html`

- [ ] **Step 1: Add similar product panel HTML**

`catalog_integrity.html`의 `</section>` (라인 81, mdm-detail-panel 닫힘) 바로 뒤, `</div>` (mdm-layout 닫힘, 라인 82) 바로 앞에 유사 제품 패널 블록을 삽입한다:

```html
  <!-- 유사 제품 스플리터 + 패널 -->
  <div class="mdm-similar-splitter hidden" id="mdm-similar-splitter"></div>
  <div class="mdm-similar-handle-wrap hidden" id="mdm-similar-handle-wrap">
    <button class="catalog-detail-minimize" id="btn-mdm-similar-toggle" title="유사 제품 패널 접기/펴기">❮</button>
  </div>
  <section class="mdm-similar-panel hidden" id="mdm-similar-panel">
    <div class="mdm-similar-header">
      <h3 id="mdm-similar-title">유사 제품</h3>
    </div>
    <div class="mdm-similar-selected" id="mdm-similar-selected">
      <div class="mdm-similar-selected-name" id="mdm-similar-selected-name"></div>
      <div class="mdm-similar-selected-meta" id="mdm-similar-selected-meta"></div>
    </div>
    <div class="mdm-similar-list" id="mdm-similar-list">
      <!-- 유사 제품 카드가 동적으로 렌더 -->
    </div>
    <div class="mdm-similar-empty hidden" id="mdm-similar-empty">
      <p>유사 제품이 없습니다.</p>
    </div>
  </section>
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/catalog_integrity.html
git commit -m "feat: add similar product panel HTML to MDM page"
```

---

## Task 7: 프론트엔드 — CSS 스타일

**Files:**
- Modify: `app/static/css/infra_common.css`

- [ ] **Step 1: Add similar panel styles**

`infra_common.css`의 `.mdm-product-grid` 블록(라인 1943-1946) 뒤, `@media` 블록(라인 1948) 앞에 추가:

```css
/* ── 유사 제품 패널 ── */
.mdm-similar-splitter {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  position: relative;
  flex-shrink: 0;
}
.mdm-similar-splitter::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 32px;
  background: var(--border-color);
  border-radius: 2px;
}
.mdm-similar-splitter:hover::after { background: var(--text-color-tertiary); height: 48px; }

.mdm-similar-handle-wrap {
  width: 18px;
  flex: 0 0 18px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mdm-similar-panel {
  flex: 0 0 320px;
  min-width: 260px;
  max-width: 50%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-left: 1px solid var(--border-color);
}

.mdm-similar-header {
  padding: 12px 14px 8px;
  flex-shrink: 0;
}
.mdm-similar-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.mdm-similar-selected {
  padding: 8px 14px 12px;
  border-bottom: 1px solid var(--border-color);
  flex-shrink: 0;
}
.mdm-similar-selected-name {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}
.mdm-similar-selected-meta {
  font-size: 12px;
  color: var(--text-color-secondary);
}

.mdm-similar-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.mdm-similar-card {
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 8px;
  background: var(--bg-primary);
}
.mdm-similar-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}
.mdm-similar-card-name {
  font-size: 13px;
  font-weight: 600;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mdm-similar-card-meta {
  font-size: 12px;
  color: var(--text-color-secondary);
  margin-bottom: 8px;
}

.mdm-similar-score {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  line-height: 1.2;
}
.mdm-similar-score.score-high {
  background: color-mix(in srgb, var(--danger-color) 15%, transparent);
  color: var(--danger-color);
}
.mdm-similar-score.score-medium {
  background: color-mix(in srgb, var(--warning-color, #f59e0b) 15%, transparent);
  color: var(--warning-color, #f59e0b);
}

.mdm-similar-card-actions {
  display: flex;
  gap: 6px;
}
.mdm-similar-card-actions .btn {
  font-size: 12px;
  padding: 3px 8px;
}

.mdm-similar-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  text-align: center;
  color: var(--text-color-tertiary);
  font-size: 13px;
}

@media (max-width: 1080px) {
  .mdm-similar-splitter,
  .mdm-similar-handle-wrap,
  .mdm-similar-panel { display: none; }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/css/infra_common.css
git commit -m "feat: add MDM similar product panel styles"
```

---

## Task 8: 프론트엔드 — JavaScript 유사 제품 로직

**Files:**
- Modify: `app/static/js/infra_catalog_integrity.js`

- [ ] **Step 1: Add state variables and constants**

파일 상단 (라인 2, `const MDM_AUTO_COLLAPSE_KEY` 뒤)에 추가:

```javascript
const MDM_SIMILAR_PANEL_WIDTH_KEY = "mdm_similar_panel_width";
const MDM_SIMILAR_OPEN_KEY = "mdm_similar_open";
let _mdmSimilarProductId = null;
let _mdmSimilarOpen = false;
```

- [ ] **Step 2: Add product grid row click handler**

`initIntegrityProductGrid` 함수(라인 272-292)의 ag-Grid 옵션에 `onRowClicked` 추가. 기존 함수의 grid 옵션 객체에서 `overlayNoRowsTemplate` 바로 앞에 추가:

```javascript
    onRowClicked: (event) => {
      const row = event.data;
      if (row && row.id) {
        openMdmSimilarPanel(row);
      }
    },
```

- [ ] **Step 3: Add similar panel open/close/toggle functions**

파일 끝(`});` 직전, DOMContentLoaded 밖)에 추가. 유사 제품 카드는 DOM API로 안전하게 생성하며 `textContent`를 사용한다:

```javascript
function setMdmSimilarPanelOpen(isOpen) {
  _mdmSimilarOpen = isOpen;
  const splitter = document.getElementById("mdm-similar-splitter");
  const handleWrap = document.getElementById("mdm-similar-handle-wrap");
  const panel = document.getElementById("mdm-similar-panel");
  const btn = document.getElementById("btn-mdm-similar-toggle");
  if (!splitter || !handleWrap || !panel || !btn) return;

  splitter.classList.toggle("hidden", !isOpen);
  handleWrap.classList.toggle("hidden", !isOpen);
  panel.classList.toggle("hidden", !isOpen);
  btn.textContent = isOpen ? "\u276E" : "\u276F";
  localStorage.setItem(MDM_SIMILAR_OPEN_KEY, isOpen ? "1" : "0");
}

function closeMdmSimilarPanel() {
  _mdmSimilarProductId = null;
  setMdmSimilarPanelOpen(false);
}

async function openMdmSimilarPanel(product) {
  _mdmSimilarProductId = product.id;
  setMdmSimilarPanelOpen(true);

  // 선택된 제품 요약
  const nameEl = document.getElementById("mdm-similar-selected-name");
  const metaEl = document.getElementById("mdm-similar-selected-meta");
  if (nameEl) nameEl.textContent = ((product.vendor || "") + " " + (product.name || "")).trim();

  const parts = [product.classification_level_2_name, product.classification_level_3_name].filter(Boolean);
  const classPath = parts.join(" > ") || product.product_type || "";
  if (metaEl) metaEl.textContent = classPath;

  await loadMdmSimilarProducts(product);
}

async function loadMdmSimilarProducts(product) {
  const listEl = document.getElementById("mdm-similar-list");
  const emptyEl = document.getElementById("mdm-similar-empty");
  if (!listEl || !emptyEl) return;

  listEl.textContent = "";
  emptyEl.classList.add("hidden");

  try {
    const result = await apiFetch("/api/v1/product-catalog/similarity-check", {
      method: "POST",
      body: {
        vendor: product.vendor || "",
        name: product.name || "",
        exclude_product_id: product.id,
      },
    });

    const items = [...(result.exact_matches || []), ...(result.similar_matches || [])];
    if (!items.length) {
      emptyEl.classList.remove("hidden");
      return;
    }

    for (const item of items) {
      listEl.appendChild(renderMdmSimilarCard(item, product));
    }
  } catch (err) {
    console.error("similarity check failed:", err);
    emptyEl.classList.remove("hidden");
  }
}

function _createEl(tag, className, textContent) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (textContent != null) el.textContent = textContent;
  return el;
}

function renderMdmSimilarCard(item, targetProduct) {
  const card = _createEl("div", "mdm-similar-card");

  // Header row: name + score
  const header = _createEl("div", "mdm-similar-card-header");
  const nameSpan = _createEl("span", "mdm-similar-card-name", (item.vendor || "") + " " + (item.name || ""));
  const scoreClass = item.score >= 90 ? "score-high" : "score-medium";
  const scoreSpan = _createEl("span", "mdm-similar-score " + scoreClass, String(item.score));
  header.appendChild(nameSpan);
  header.appendChild(scoreSpan);
  card.appendChild(header);

  // Meta
  const meta = _createEl("div", "mdm-similar-card-meta", "\uc790\uc0b0 " + (item.asset_count ?? 0) + "\uac74");
  card.appendChild(meta);

  // Action buttons
  const actions = _createEl("div", "mdm-similar-card-actions");

  const mergeBtn = _createEl("button", "btn btn-primary btn-sm btn-merge vendor-write-only", "\u2190 \ubcd1\ud569");
  mergeBtn.type = "button";
  mergeBtn.addEventListener("click", async () => {
    const sourceLabel = (item.vendor || "") + " " + (item.name || "");
    const targetLabel = ((targetProduct.vendor || "") + " " + (targetProduct.name || "")).trim();
    const msg = "\uc81c\ud488 '" + sourceLabel + "'(\uc790\uc0b0 " + (item.asset_count ?? 0) + "\uac74)\uc744 '" + targetLabel + "'\uc73c\ub85c \ubcd1\ud569\ud569\ub2c8\ub2e4.\n\n\uc790\uc0b0\uc774 \ub300\uc0c1 \uc81c\ud488\uc73c\ub85c \uc774\uc804\ub418\uace0, \uc6d0\ubcf8 \uc81c\ud488\uc740 \uc0ad\uc81c\ub429\ub2c8\ub2e4.";
    if (!confirm(msg)) return;

    try {
      const result = await apiFetch("/api/v1/product-catalog/merge", {
        method: "POST",
        body: { source_id: item.id, target_id: targetProduct.id },
      });
      showToast("\ubcd1\ud569 \uc644\ub8cc: \uc790\uc0b0 " + result.merged_asset_count + "\uac74 \uc774\uc804", "success");
      if (_integrityVendorOriginal) {
        await loadIntegrityVendorProducts(_integrityVendorOriginal);
      }
      await loadMdmSimilarProducts(targetProduct);
    } catch (err) {
      showToast(err.message || "\ubcd1\ud569\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.", "error");
    }
  });
  actions.appendChild(mergeBtn);

  const dismissBtn = _createEl("button", "btn btn-secondary btn-sm btn-dismiss vendor-write-only", "\ubb34\uc2dc");
  dismissBtn.type = "button";
  dismissBtn.addEventListener("click", async () => {
    try {
      await apiFetch("/api/v1/product-catalog/similarity-dismiss", {
        method: "POST",
        body: { product_id_a: targetProduct.id, product_id_b: item.id },
      });
      card.remove();
      const listEl = document.getElementById("mdm-similar-list");
      if (listEl && !listEl.children.length) {
        document.getElementById("mdm-similar-empty")?.classList.remove("hidden");
      }
      showToast("\uc720\uc0ac \uad00\uacc4\ub97c \ubb34\uc2dc\ud588\uc2b5\ub2c8\ub2e4.", "success");
    } catch (err) {
      showToast(err.message || "\ubb34\uc2dc \ucc98\ub9ac\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.", "error");
    }
  });
  actions.appendChild(dismissBtn);

  card.appendChild(actions);

  // 권한에 따라 버튼 숨김
  if (!_canManageVendor) {
    card.querySelectorAll(".vendor-write-only").forEach((el) => { el.style.display = "none"; });
  }

  return card;
}
```

- [ ] **Step 4: Add similar panel splitter drag**

위 함수들 뒤에 추가:

```javascript
function initMdmSimilarSplitter() {
  const splitter = document.getElementById("mdm-similar-splitter");
  const panel = document.getElementById("mdm-similar-panel");
  if (!splitter || !panel) return;

  const saved = localStorage.getItem(MDM_SIMILAR_PANEL_WIDTH_KEY);
  if (saved) panel.style.flexBasis = saved + "px";

  splitter.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = panel.getBoundingClientRect().width;
    const onMove = (ev) => {
      const newW = Math.max(260, Math.min(startW + (startX - ev.clientX), window.innerWidth * 0.5));
      panel.style.flexBasis = newW + "px";
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      localStorage.setItem(MDM_SIMILAR_PANEL_WIDTH_KEY, Math.round(panel.getBoundingClientRect().width));
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}
```

- [ ] **Step 5: Wire up in DOMContentLoaded**

`DOMContentLoaded` 이벤트 핸들러 내부, `initIntegrityProductGrid()` 호출(라인 336) 뒤에 추가:

```javascript
  initMdmSimilarSplitter();
  document.getElementById("btn-mdm-similar-toggle")?.addEventListener("click", () => {
    if (_mdmSimilarOpen) {
      closeMdmSimilarPanel();
    } else if (_mdmSimilarProductId) {
      setMdmSimilarPanelOpen(true);
    }
  });
```

- [ ] **Step 6: Close similar panel on vendor change**

`setIntegrityVendorEmptyMode` 함수(라인 68-76)에서 `mdmSetCollapsed(false);` 뒤에 추가:

```javascript
  closeMdmSimilarPanel();
```

`setIntegrityVendorEditMode` 함수(라인 96-123)에서 `loadIntegrityVendorProducts(vendor);` 뒤에 추가:

```javascript
  closeMdmSimilarPanel();
```

- [ ] **Step 7: Commit**

```bash
git add app/static/js/infra_catalog_integrity.js
git commit -m "feat: add similar product panel logic with merge and dismiss"
```

---

## Task 9: 통합 테스트 + 브라우저 확인

- [ ] **Step 1: Restart app and verify migration**

Run: `docker restart pjtmgr-app && sleep 3 && docker logs pjtmgr-app --tail 20`
Expected: "Running upgrade 0058 -> 0059" in logs, app started successfully

- [ ] **Step 2: Test dismissal table**

Run:
```bash
docker exec pjtmgr-app python -c "
from app.core.database import SessionLocal
from app.modules.infra.models.product_similarity_dismissal import ProductSimilarityDismissal
db = SessionLocal()
print('Table accessible:', db.query(ProductSimilarityDismissal).count())
db.close()
"
```
Expected: "Table accessible: 0"

- [ ] **Step 3: Browser test — panel open/close**

브라우저에서 `http://localhost:9000/catalog-management/integrity` 접속:
1. 제조사 선택 → 제품 목록 표시됨
2. 제품 행 클릭 → 우측에 유사 제품 패널 슬라이드
3. 유사 제품 있으면 카드 표시, 없으면 "유사 제품이 없습니다"
4. 스플리터 드래그 동작 확인
5. 토글 버튼 클릭으로 패널 접기/펴기
6. 다른 제조사 선택 → 패널 자동 닫힘

- [ ] **Step 4: Browser test — merge flow**

1. 유사 제품 카드의 "← 병합" 클릭
2. 확인 다이얼로그 표시됨
3. 확인 → 병합 성공 토스트, 제품 목록 갱신, 유사 패널 갱신

- [ ] **Step 5: Browser test — dismiss flow**

1. 유사 제품 카드의 "무시" 클릭
2. 카드가 사라지고 "유사 관계를 무시했습니다" 토스트
3. 다시 같은 제품 클릭 → 무시된 제품이 유사 목록에 나타나지 않음

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: complete similar product panel with merge and dismiss"
```
