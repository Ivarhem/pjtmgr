# 유사도 사전 캐시 + 그리드 경고 + 무시 롤백 Implementation Plan

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** `product_catalog.similar_count` 사전 계산 캐시를 추가하여 제조사/제품 그리드에 중복 경고 아이콘을 표시하고, 무시한 유사 관계를 복원할 수 있게 한다.

**Architecture:** product_catalog 테이블에 similar_count 컬럼을 추가하고, 제품 CUD/병합/무시/복원 시 동기적으로 재계산한다. 프론트엔드 그리드에 "중복" 컬럼을 추가하고, 유사 제품 패널에 무시 목록 토글 + 복원 버튼을 넣는다.

**Tech Stack:** Python/FastAPI/SQLAlchemy, vanilla JS + ag-Grid, Alembic

---

## File Structure

### 새로 생성

| 파일 | 역할 |
|------|------|
| `alembic/versions/0060_product_similar_count.py` | similar_count 컬럼 마이그레이션 |

### 수정

| 파일 | 변경 내용 |
|------|-----------|
| `app/modules/infra/models/product_catalog.py` | similar_count 컬럼 |
| `app/modules/infra/services/catalog_similarity_service.py` | recalc 함수 + include_dismissed 지원 |
| `app/modules/infra/services/catalog_merge_service.py` | restore_similarity + recalc 호출 |
| `app/modules/infra/services/product_catalog_service.py` | CUD 후 recalc 호출 |
| `app/modules/infra/services/catalog_alias_service.py` | vendor summary에 similar_product_count |
| `app/modules/infra/schemas/product_catalog.py` | similar_count 필드 |
| `app/modules/infra/schemas/catalog_similarity.py` | include_dismissed + dismissed_matches + restore 스키마 |
| `app/modules/infra/schemas/catalog_vendor_management.py` | similar_product_count 필드 |
| `app/modules/infra/routers/product_catalogs.py` | similarity-restore 엔드포인트 |
| `app/static/js/infra_catalog_integrity.js` | 그리드 컬럼 + 무시 목록 토글 + 복원 |
| `app/static/css/infra_common.css` | 경고 아이콘 + 무시 카드 스타일 |

---

## Task 1: 마이그레이션 + 모델

**Files:**
- Create: `alembic/versions/0060_product_similar_count.py`
- Modify: `app/modules/infra/models/product_catalog.py`

- [ ] **Step 1: Add similar_count to model**

`app/modules/infra/models/product_catalog.py`에서 `is_placeholder` 필드 뒤에 추가:

```python
    similar_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
```

상단 imports에 `Integer` 추가 (이미 없다면):

```python
from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text, UniqueConstraint
```

- [ ] **Step 2: Create migration**

```python
# alembic/versions/0060_product_similar_count.py
"""add similar_count to product_catalog

Revision ID: 0060
Revises: 0059
"""
from alembic import op
import sqlalchemy as sa

revision = "0060"
down_revision = "0059"

def upgrade() -> None:
    op.add_column("product_catalog", sa.Column("similar_count", sa.Integer(), server_default="0", nullable=False))

def downgrade() -> None:
    op.drop_column("product_catalog", "similar_count")
```

- [ ] **Step 3: Run migration**

Run: `docker exec pjtmgr-app alembic upgrade head`

- [ ] **Step 4: Commit**

```bash
git add app/modules/infra/models/product_catalog.py alembic/versions/0060_product_similar_count.py
git commit -m "feat: add similar_count column to product_catalog"
```

---

## Task 2: 유사도 재계산 함수

**Files:**
- Modify: `app/modules/infra/services/catalog_similarity_service.py`

- [ ] **Step 1: Add recalc functions**

파일 끝에 다음 두 함수를 추가:

```python
def recalc_similar_counts(db: Session, product_ids: list[int]) -> None:
    """주어진 product_ids의 similar_count를 재계산한다."""
    if not product_ids:
        return
    from app.modules.infra.services.catalog_merge_service import get_dismissed_pairs

    all_products = list(db.scalars(
        select(ProductCatalog).order_by(ProductCatalog.id)
    ))
    product_map = {p.id: p for p in all_products}

    for pid in product_ids:
        product = product_map.get(pid)
        if not product:
            continue
        dismissed = get_dismissed_pairs(db, pid)
        n_vendor = normalize_vendor_name(product.vendor)
        n_name = normalize_product_name(product.name)
        tokens = tokenize_product_name(product.name)

        count = 0
        for candidate in all_products:
            if candidate.id == pid or candidate.id in dismissed:
                continue
            score = score_product_similarity(
                normalized_vendor=n_vendor,
                normalized_name=n_name,
                source_tokens=tokens,
                candidate=candidate,
            )
            if score >= 75:
                count += 1
        product.similar_count = count

    db.commit()


def recalc_all_similar_counts(db: Session) -> int:
    """전체 제품의 similar_count를 재계산한다. 초기 데이터 채움용."""
    all_ids = list(db.scalars(select(ProductCatalog.id)))
    recalc_similar_counts(db, all_ids)
    return len(all_ids)
```

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/services/catalog_similarity_service.py
git commit -m "feat: add recalc_similar_counts functions"
```

---

## Task 3: CUD/병합/무시 후 재계산 호출

**Files:**
- Modify: `app/modules/infra/services/product_catalog_service.py`
- Modify: `app/modules/infra/services/catalog_merge_service.py`

- [ ] **Step 1: Hook recalc into create_product**

`app/modules/infra/services/product_catalog_service.py`의 `create_product` 함수에서 `invalidate_product_list_cache(db)` (라인 152) 뒤에 추가:

```python
    _recalc_product_similarity(db, product.id)
```

- [ ] **Step 2: Hook recalc into update_product**

`update_product` 함수에서 `invalidate_product_list_cache(db)` (라인 187) 뒤에, vendor/name 변경 시에만 재계산:

```python
    if "vendor" in changes or "name" in changes:
        _recalc_product_similarity(db, product.id)
```

- [ ] **Step 3: Hook recalc into delete_product**

`delete_product` 함수에서 `db.delete(product)` (라인 206) 직전에 유사 상대 목록을 수집하고, 삭제+커밋 후 재계산:

기존 코드:
```python
    db.delete(product)
    db.commit()
    invalidate_product_list_cache(db)
```

변경:
```python
    # 삭제 전에 유사 상대 수집
    affected_ids = _collect_similar_peer_ids(db, product_id)
    db.delete(product)
    db.commit()
    invalidate_product_list_cache(db)
    if affected_ids:
        from app.modules.infra.services.catalog_similarity_service import recalc_similar_counts
        recalc_similar_counts(db, affected_ids)
```

- [ ] **Step 4: Add helper functions**

`product_catalog_service.py` 끝에 추가:

```python
def _collect_similar_peer_ids(db: Session, product_id: int) -> list[int]:
    """재계산이 필요한 유사 상대 product_id 목록을 반환."""
    from app.modules.infra.services.catalog_similarity_service import (
        find_similar_products,
    )
    product = db.get(ProductCatalog, product_id)
    if not product:
        return []
    result = find_similar_products(
        db, vendor=product.vendor, name=product.name, exclude_product_id=product_id
    )
    ids = [m["id"] for m in result.get("exact_matches", [])]
    ids += [m["id"] for m in result.get("similar_matches", [])]
    return ids


def _recalc_product_similarity(db: Session, product_id: int) -> None:
    """제품과 그 유사 상대들의 similar_count를 재계산."""
    from app.modules.infra.services.catalog_similarity_service import recalc_similar_counts
    peer_ids = _collect_similar_peer_ids(db, product_id)
    all_ids = [product_id] + peer_ids
    recalc_similar_counts(db, all_ids)
```

- [ ] **Step 5: Hook recalc into merge_products**

`app/modules/infra/services/catalog_merge_service.py`의 `merge_products` 함수에서 `invalidate_product_list_cache(db)` 뒤에 추가:

```python
    from app.modules.infra.services.catalog_similarity_service import recalc_similar_counts
    from app.modules.infra.services.product_catalog_service import _collect_similar_peer_ids
    peer_ids = _collect_similar_peer_ids(db, target_id)
    recalc_similar_counts(db, [target_id] + peer_ids)
```

- [ ] **Step 6: Hook recalc into dismiss_similarity**

`dismiss_similarity` 함수에서 `db.commit()` 뒤에 추가:

```python
    from app.modules.infra.services.catalog_similarity_service import recalc_similar_counts
    recalc_similar_counts(db, [a, b])
```

- [ ] **Step 7: Commit**

```bash
git add app/modules/infra/services/product_catalog_service.py app/modules/infra/services/catalog_merge_service.py
git commit -m "feat: hook similar_count recalc into CUD, merge, dismiss"
```

---

## Task 4: 무시 복원 서비스 + 엔드포인트

**Files:**
- Modify: `app/modules/infra/services/catalog_merge_service.py`
- Modify: `app/modules/infra/schemas/catalog_similarity.py`
- Modify: `app/modules/infra/routers/product_catalogs.py`

- [ ] **Step 1: Add restore_similarity function**

`catalog_merge_service.py`의 `dismiss_similarity` 함수 뒤에 추가:

```python
def restore_similarity(
    db: Session,
    *,
    product_id_a: int,
    product_id_b: int,
) -> None:
    a, b = min(product_id_a, product_id_b), max(product_id_a, product_id_b)
    from sqlalchemy import delete as sa_delete
    db.execute(
        sa_delete(ProductSimilarityDismissal).where(
            ProductSimilarityDismissal.product_id_a == a,
            ProductSimilarityDismissal.product_id_b == b,
        )
    )
    db.commit()
    from app.modules.infra.services.catalog_similarity_service import recalc_similar_counts
    recalc_similar_counts(db, [a, b])
```

- [ ] **Step 2: Add ProductRestoreRequest schema**

`app/modules/infra/schemas/catalog_similarity.py` 끝에 추가:

```python
class ProductRestoreRequest(BaseModel):
    product_id_a: int
    product_id_b: int
```

- [ ] **Step 3: Add restore endpoint**

`app/modules/infra/routers/product_catalogs.py`에서 imports에 추가:

```python
from app.modules.infra.schemas.catalog_similarity import (
    ...
    ProductRestoreRequest,
)
from app.modules.infra.services.catalog_merge_service import (
    ...
    restore_similarity,
)
```

`similarity-dismiss` 엔드포인트 뒤에 추가:

```python
@router.post("/similarity-restore", status_code=status.HTTP_204_NO_CONTENT)
def restore_similarity_endpoint(
    payload: ProductRestoreRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    restore_similarity(db, product_id_a=payload.product_id_a, product_id_b=payload.product_id_b)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/infra/services/catalog_merge_service.py app/modules/infra/schemas/catalog_similarity.py app/modules/infra/routers/product_catalogs.py
git commit -m "feat: add similarity restore endpoint"
```

---

## Task 5: 스키마 + API 응답 확장

**Files:**
- Modify: `app/modules/infra/schemas/product_catalog.py`
- Modify: `app/modules/infra/schemas/catalog_vendor_management.py`
- Modify: `app/modules/infra/schemas/catalog_similarity.py`
- Modify: `app/modules/infra/services/catalog_alias_service.py`
- Modify: `app/modules/infra/services/catalog_similarity_service.py`

- [ ] **Step 1: Add similar_count to ProductCatalogRead**

`app/modules/infra/schemas/product_catalog.py`의 `ProductCatalogRead` 클래스에서 `is_placeholder: bool` 뒤에 추가:

```python
    similar_count: int = 0
```

- [ ] **Step 2: Add similar_product_count to CatalogVendorSummary**

`app/modules/infra/schemas/catalog_vendor_management.py`의 `CatalogVendorSummary`에서 `memo` 뒤에 추가:

```python
    similar_product_count: int = 0
```

- [ ] **Step 3: Add similar_product_count to vendor summary service**

`app/modules/infra/services/catalog_alias_service.py`의 `list_vendor_alias_summaries`에서 vendor_product_map 쿼리 뒤 (라인 141 부근), meta_rows 쿼리 전에 유사 제품 집계를 추가:

```python
    # similar_count > 0인 제품 수 (제조사별)
    similar_stmt = (
        select(
            ProductCatalog.vendor.label("vendor"),
            func.count(ProductCatalog.id).label("similar_product_count"),
        )
        .where(ProductCatalog.similar_count > 0)
        .group_by(ProductCatalog.vendor)
    )
    vendor_similar_map: dict[str, int] = {}
    for row in db.execute(similar_stmt).mappings().all():
        vendor_similar_map[row["vendor"]] = int(row["similar_product_count"] or 0)
```

그리고 결과 dict 생성 (라인 192-200)에서 `"memo"` 뒤에 추가:

```python
                "similar_product_count": vendor_similar_map.get(vendor, 0),
```

- [ ] **Step 4: Add include_dismissed to similarity-check**

`app/modules/infra/schemas/catalog_similarity.py`의 `CatalogSimilarityCheckRequest`에 필드 추가:

```python
    include_dismissed: bool = False
```

`CatalogSimilarityCheckResponse`에 필드 추가:

```python
    dismissed_matches: list[CatalogSimilarityCandidate] = []
```

- [ ] **Step 5: Update find_similar_products for include_dismissed**

`app/modules/infra/services/catalog_similarity_service.py`의 `find_similar_products` 시그니처에 파라미터 추가:

```python
    include_dismissed: bool = False,
```

함수 본문에서 dismissed 필터 부분을 수정. 기존:

```python
        if candidate.id in dismissed_ids:
            continue
```

변경:

```python
        is_dismissed = candidate.id in dismissed_ids
        if is_dismissed and not include_dismissed:
            continue
```

그리고 payload dict에 추가:

```python
            "is_dismissed": is_dismissed,
```

return dict에 `dismissed_matches` 추가. 기존 exact/similar 분류 로직 뒤에:

```python
        if is_dismissed:
            dismissed_matches.append(payload)
        elif payload["exact_normalized"]:
```

함수 상단에 `dismissed_matches: list[dict] = []` 초기화 추가.

return에 추가:

```python
        "dismissed_matches": dismissed_matches[:limit] if include_dismissed else [],
```

- [ ] **Step 6: Update router to pass include_dismissed**

`app/modules/infra/routers/product_catalogs.py`의 `check_product_similarity_endpoint`에서:

```python
    return CatalogSimilarityCheckResponse(**find_similar_products(
        db,
        vendor=payload.vendor,
        name=payload.name,
        exclude_product_id=payload.exclude_product_id,
        include_dismissed=payload.include_dismissed,
    ))
```

- [ ] **Step 7: Add is_dismissed to CatalogSimilarityCandidate**

`app/modules/infra/schemas/catalog_similarity.py`의 `CatalogSimilarityCandidate`에:

```python
    is_dismissed: bool = False
```

- [ ] **Step 8: Commit**

```bash
git add app/modules/infra/schemas/product_catalog.py app/modules/infra/schemas/catalog_vendor_management.py app/modules/infra/schemas/catalog_similarity.py app/modules/infra/services/catalog_alias_service.py app/modules/infra/services/catalog_similarity_service.py app/modules/infra/routers/product_catalogs.py
git commit -m "feat: add similar_count to API responses and include_dismissed support"
```

---

## Task 6: 초기 데이터 채우기 + 앱 재시작

- [ ] **Step 1: Run migration and recalc**

```bash
docker exec pjtmgr-app alembic upgrade head
docker exec pjtmgr-app python -c "
from app.core.database import SessionLocal
from app.modules.infra.services.catalog_similarity_service import recalc_all_similar_counts
db = SessionLocal()
n = recalc_all_similar_counts(db)
print(f'Recalculated {n} products')
db.close()
"
```

- [ ] **Step 2: Restart and verify**

```bash
docker restart pjtmgr-app
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat: run initial similar_count recalculation"
```

---

## Task 7: 프론트엔드 — 그리드 경고 컬럼 + 무시 롤백 UI

**Files:**
- Modify: `app/static/js/infra_catalog_integrity.js`
- Modify: `app/static/css/infra_common.css`

- [ ] **Step 1: Add warning column to vendor grid**

`infra_catalog_integrity.js`의 `initCatalogIntegrityVendorGrid` (라인 241)에서 `columnDefs` 배열의 `{ field: "product_count", headerName: "제품 수", width: 90 }` 뒤에 추가:

```javascript
      {
        field: "similar_product_count",
        headerName: "중복",
        width: 70,
        sortable: true,
        filter: false,
        cellRenderer: (params) => {
          const count = params.value || 0;
          if (!count) return "";
          const span = document.createElement("span");
          span.className = "mdm-warning-badge";
          span.textContent = "\u26A0 " + count;
          return span;
        },
      },
```

- [ ] **Step 2: Add warning column to product grid**

`initIntegrityProductGrid` (라인 282)에서 `columnDefs` 배열의 분류 컬럼 뒤에 추가:

```javascript
      {
        field: "similar_count",
        headerName: "중복",
        width: 70,
        sortable: true,
        filter: false,
        cellRenderer: (params) => {
          const count = params.value || 0;
          if (!count) return "";
          const span = document.createElement("span");
          span.className = "mdm-warning-badge";
          span.textContent = "\u26A0 " + count;
          return span;
        },
      },
```

- [ ] **Step 3: Add dismissed toggle to similar panel**

`openMdmSimilarPanel` 함수에서 `await loadMdmSimilarProducts(product);` 호출 전에 토글 버튼 상태 초기화:

```javascript
  const toggleBtn = document.getElementById("btn-mdm-dismissed-toggle");
  if (toggleBtn) {
    toggleBtn.classList.remove("active");
    toggleBtn.dataset.showing = "false";
  }
```

그리고 `loadMdmSimilarProducts` 함수를 수정하여 `include_dismissed` 지원:

기존 body:
```javascript
      body: {
        vendor: product.vendor || "",
        name: product.name || "",
        exclude_product_id: product.id,
      },
```

변경:
```javascript
      body: {
        vendor: product.vendor || "",
        name: product.name || "",
        exclude_product_id: product.id,
        include_dismissed: showDismissed,
      },
```

함수 시그니처도 변경:

```javascript
async function loadMdmSimilarProducts(product, showDismissed = false) {
```

dismissed_matches도 렌더링:

```javascript
    const items = [...(result.exact_matches || []), ...(result.similar_matches || [])];
    const dismissedItems = result.dismissed_matches || [];
```

기존 카드 렌더 루프 뒤에:

```javascript
    if (showDismissed && dismissedItems.length) {
      for (const item of dismissedItems) {
        listEl.appendChild(renderMdmSimilarCard(item, product, true));
      }
    }
```

- [ ] **Step 4: Update renderMdmSimilarCard for dismissed state**

함수 시그니처 변경:

```javascript
function renderMdmSimilarCard(item, targetProduct, isDismissed = false) {
```

카드 생성 뒤에 dismissed 스타일:

```javascript
  if (isDismissed) card.classList.add("mdm-similar-card-dismissed");
```

액션 버튼 부분에서 isDismissed면 "복원" 버튼만 표시:

```javascript
  if (isDismissed) {
    const restoreBtn = _createEl("button", "btn btn-secondary btn-sm vendor-write-only", "\ubcf5\uc6d0");
    restoreBtn.type = "button";
    restoreBtn.addEventListener("click", async () => {
      try {
        await apiFetch("/api/v1/product-catalog/similarity-restore", {
          method: "POST",
          body: { product_id_a: targetProduct.id, product_id_b: item.id },
        });
        showToast("\uc720\uc0ac \uad00\uacc4\ub97c \ubcf5\uc6d0\ud588\uc2b5\ub2c8\ub2e4.", "success");
        await loadMdmSimilarProducts(targetProduct, true);
        if (_integrityVendorOriginal) {
          await loadIntegrityVendorProducts(_integrityVendorOriginal);
        }
      } catch (err) {
        showToast(err.message || "\ubcf5\uc6d0\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.", "error");
      }
    });
    actions.appendChild(restoreBtn);
  } else {
    // 기존 병합 + 무시 버튼 코드
  }
```

- [ ] **Step 5: Add dismissed toggle button to HTML**

`app/templates/catalog_integrity.html`의 유사 제품 패널 헤더 (`mdm-similar-header`) 안에서 `<h3>` 뒤에 추가:

```html
      <button type="button" class="btn btn-secondary btn-sm" id="btn-mdm-dismissed-toggle" title="무시 목록 보기">무시 목록</button>
```

- [ ] **Step 6: Wire toggle in DOMContentLoaded**

`infra_catalog_integrity.js`의 `initMdmSimilarSplitter()` 호출 뒤에 추가:

```javascript
  document.getElementById("btn-mdm-dismissed-toggle")?.addEventListener("click", async () => {
    const btn = document.getElementById("btn-mdm-dismissed-toggle");
    if (!btn || !_mdmSimilarProductId) return;
    const showing = btn.dataset.showing === "true";
    btn.dataset.showing = showing ? "false" : "true";
    btn.classList.toggle("active", !showing);
    // 현재 선택된 제품의 유사 목록 다시 로드
    let currentProduct = null;
    integrityProductGridApi?.forEachNode((node) => {
      if (node.data?.id === _mdmSimilarProductId) currentProduct = node.data;
    });
    if (currentProduct) {
      await loadMdmSimilarProducts(currentProduct, !showing);
    }
  });
```

- [ ] **Step 7: Add CSS styles**

`app/static/css/infra_common.css`의 `.mdm-similar-empty` 블록 뒤에 추가:

```css
.mdm-warning-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
  font-weight: 600;
  color: var(--warning-color, #f59e0b);
}

.mdm-similar-card-dismissed {
  opacity: 0.5;
  border-style: dashed;
}

.mdm-similar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
```

주의: `.mdm-similar-header`가 이미 정의되어 있으면 `display: flex; align-items: center; justify-content: space-between;`을 추가.

- [ ] **Step 8: Refresh grids after merge/dismiss/restore**

병합/무시 후 제조사 그리드도 새로고침되도록, 병합/무시 성공 콜백에서:

```javascript
await loadCatalogIntegrityVendors();
```

를 추가하여 vendor grid의 `similar_product_count`가 갱신되게 한다.

- [ ] **Step 9: Commit**

```bash
git add app/static/js/infra_catalog_integrity.js app/static/css/infra_common.css app/templates/catalog_integrity.html
git commit -m "feat: add grid warning columns and dismiss rollback UI"
```

---

## Task 8: 브라우저 검증

- [ ] **Step 1: Restart app**

```bash
docker restart pjtmgr-app && sleep 4 && docker logs pjtmgr-app --tail 10
```

- [ ] **Step 2: Verify vendor grid warning**

브라우저에서 기준정보관리 접속. 제조사 그리드에 "중복" 컬럼이 표시되고, Cisco 등 유사 제품이 있는 제조사에 ⚠ 아이콘 + 숫자가 보이는지 확인.

- [ ] **Step 3: Verify product grid warning**

Cisco 선택. 제품 그리드에 "중복" 컬럼이 표시되고, Catalyst 9300/9300L에 ⚠ 아이콘이 보이는지 확인.

- [ ] **Step 4: Verify dismiss rollback**

1. Catalyst 9300 클릭 → 유사 제품 패널
2. "무시 목록" 버튼 클릭 → 이전에 무시한 항목이 흐리게 표시 + "복원" 버튼
3. "복원" 클릭 → 토스트 + 카드가 정상 상태로 전환 + 그리드 경고 숫자 갱신

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete similarity cache, grid warnings, and dismiss rollback"
```
