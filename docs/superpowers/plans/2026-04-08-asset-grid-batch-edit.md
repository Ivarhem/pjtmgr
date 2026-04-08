# 자산 그리드 다중셀 편집 (1차) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자산 목록 그리드에 편집 모드 토글, 배치 저장/취소, dirty 추적, 정합성 검증, 엑셀 붙여넣기, 행 선택 기반 복사 기능을 구현한다.

**Architecture:** 기존 단일 셀 즉시 PATCH 모드(normal mode)와 새 배치 편집 모드(edit mode)를 공존시킨다. 편집 모드에서는 변경사항을 로컬 dirty map에 축적하고, 사용자가 [저장]을 누르면 bulk PATCH API로 일괄 반영한다. AG Grid Community v32에서 Range Selection을 사용할 수 없으므로, 복사는 행 단위 다중 선택(`rowSelection: "multiple"`) 기반으로 구현한다.

**Tech Stack:** AG Grid Community v32, Vanilla JS, FastAPI, Pydantic, SQLAlchemy

**핵심 설계 결정:**
- normal mode: 기존 동작 유지 (더블클릭 → 단일 셀 PATCH)
- edit mode: 더블클릭 → 로컬 dirty 축적, 검증, [저장] 시 bulk PATCH
- dirty 추적: `row._dirty = { field: newValue, ... }`, `row._original = { field: oldValue, ... }` 
- 행 선택: edit mode에서 `rowSelection: "multiple"` + 체크박스 컬럼 활성
- 복사: 선택된 행의 editable 필드를 TSV로 클립보드에 복사
- 붙여넣기: 기존 `addCopyPasteHandler()` 활용, dirty 마킹 추가

---

## 파일 구조

| 파일 | 변경 | 역할 |
|------|------|------|
| `app/static/js/infra_assets.js` | 수정 | 편집 모드 토글, dirty 추적, 검증, 배치 저장/취소 |
| `app/static/js/utils.js` | 수정 | `addCopyPasteHandler`에 dirty 콜백 지원 추가 |
| `app/static/css/infra_common.css` | 수정 | dirty/error 셀 스타일 |
| `app/modules/infra/templates/infra_assets.html` | 수정 | 편집/저장/취소 버튼 추가 |
| `app/modules/infra/routers/assets.py` | 수정 | bulk PATCH 엔드포인트 추가 |
| `app/modules/infra/schemas/asset.py` | 수정 | bulk PATCH 스키마 추가 |
| `app/modules/infra/services/asset_service.py` | 수정 | bulk update 서비스 함수 추가 |
| `tests/infra/test_asset_bulk_update.py` | 생성 | bulk PATCH 테스트 |

---

### Task 1: Bulk PATCH 백엔드 API

**Files:**
- Modify: `app/modules/infra/schemas/asset.py`
- Modify: `app/modules/infra/services/asset_service.py`
- Modify: `app/modules/infra/routers/assets.py`
- Create: `tests/infra/test_asset_bulk_update.py`

- [ ] **Step 1: AssetBulkUpdateItem 스키마 추가**

`app/modules/infra/schemas/asset.py` 파일 끝에 추가:

```python
class AssetBulkUpdateItem(BaseModel):
    id: int
    changes: dict  # {field: value, ...} — AssetUpdate 허용 필드만 수용


class AssetBulkUpdateRequest(BaseModel):
    items: list[AssetBulkUpdateItem]
```

- [ ] **Step 2: bulk_update_assets 서비스 함수 추가**

`app/modules/infra/services/asset_service.py` 에 추가:

```python
def bulk_update_assets(
    db: Session,
    items: list[dict],
    current_user: User,
) -> list[dict]:
    """여러 자산을 일괄 업데이트한다. items: [{id, changes: {field: value}}]"""
    from app.modules.infra.schemas.asset import AssetUpdate

    results = []
    for item in items:
        asset_id = item["id"]
        changes = item["changes"]
        # AssetUpdate 허용 필드만 필터링
        allowed = AssetUpdate.model_fields.keys()
        filtered = {k: v for k, v in changes.items() if k in allowed}
        if not filtered:
            continue
        payload = AssetUpdate(**filtered)
        updated = update_asset(db, asset_id, payload, current_user)
        results.append(updated)
    return results
```

- [ ] **Step 3: PATCH /api/v1/assets/bulk 라우터 추가**

`app/modules/infra/routers/assets.py` 에 추가 (단건 PATCH 라우트 **위에** 배치 — FastAPI path matching 순서):

```python
from app.modules.infra.schemas.asset import AssetBulkUpdateRequest
from app.modules.infra.services.asset_service import bulk_update_assets

@router.patch("/bulk", response_model=list[AssetRead])
def bulk_update_assets_endpoint(
    payload: AssetBulkUpdateRequest,
    layout_id: int | None = None,
    lang: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssetRead]:
    results = bulk_update_assets(db, [i.model_dump() for i in payload.items], current_user)
    return [enrich_asset_with_catalog_kind(db, a, layout_id=layout_id, lang=lang) for a in results]
```

**주의:** `/bulk` 라우트를 `/{asset_id}` 라우트보다 위에 두어야 FastAPI가 "bulk"를 asset_id로 파싱하지 않는다.

- [ ] **Step 4: 테스트 작성**

`tests/infra/test_asset_bulk_update.py`:

```python
"""Bulk asset update service tests."""
import pytest
from app.core.exceptions import NotFoundError
from app.modules.infra.services.asset_service import bulk_update_assets, get_asset


def test_bulk_update_changes_multiple_assets(db_session, admin_user, two_assets):
    """2건의 자산을 일괄 업데이트한다."""
    a1, a2 = two_assets
    items = [
        {"id": a1.id, "changes": {"hostname": "host-a"}},
        {"id": a2.id, "changes": {"hostname": "host-b", "status": "active"}},
    ]
    results = bulk_update_assets(db_session, items, admin_user)
    assert len(results) == 2
    assert results[0].hostname == "host-a"
    assert results[1].hostname == "host-b"
    assert results[1].status == "active"


def test_bulk_update_skips_empty_changes(db_session, admin_user, two_assets):
    """변경사항이 없는 항목은 건너뛴다."""
    a1, a2 = two_assets
    items = [
        {"id": a1.id, "changes": {}},
        {"id": a2.id, "changes": {"hostname": "updated"}},
    ]
    results = bulk_update_assets(db_session, items, admin_user)
    assert len(results) == 1


def test_bulk_update_filters_unknown_fields(db_session, admin_user, two_assets):
    """AssetUpdate에 없는 필드는 무시한다."""
    a1, _ = two_assets
    items = [{"id": a1.id, "changes": {"hostname": "ok", "fake_field": "ignored"}}]
    results = bulk_update_assets(db_session, items, admin_user)
    assert len(results) == 1
    assert results[0].hostname == "ok"
```

- [ ] **Step 5: 테스트 실행**

```bash
pytest tests/infra/test_asset_bulk_update.py -v
```

- [ ] **Step 6: 커밋**

```bash
git add app/modules/infra/schemas/asset.py app/modules/infra/services/asset_service.py app/modules/infra/routers/assets.py tests/infra/test_asset_bulk_update.py
git commit -m "feat(infra): add bulk PATCH /api/v1/assets/bulk endpoint"
```

---

### Task 2: CSS — dirty/error 셀 스타일

**Files:**
- Modify: `app/static/css/infra_common.css`

- [ ] **Step 1: dirty/error/edit-mode 셀 스타일 추가**

`app/static/css/infra_common.css` 의 `.infra-cell-editable` 블록 아래에 추가:

```css
/* ── Edit mode cell states ── */
.infra-cell-dirty {
  background: var(--color-blue-50, #eff6ff) !important;
  border-bottom: 2px solid var(--primary-color, #2563eb) !important;
}

.infra-cell-error {
  background: var(--color-red-50, #fef2f2) !important;
  border-bottom: 2px solid var(--danger-color, #dc2626) !important;
}

.infra-cell-dirty.infra-cell-error {
  background: var(--color-red-50, #fef2f2) !important;
  border-bottom: 2px solid var(--danger-color, #dc2626) !important;
}

body.dark-mode .infra-cell-dirty {
  background: color-mix(in srgb, var(--primary-color, #2563eb) 15%, transparent) !important;
}

body.dark-mode .infra-cell-error {
  background: color-mix(in srgb, var(--danger-color, #dc2626) 15%, transparent) !important;
}

/* Edit mode active indicator */
.edit-mode-active #grid-assets {
  border: 2px solid var(--primary-color, #2563eb);
  border-radius: 6px;
}

/* Edit mode toolbar */
.edit-mode-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: var(--color-blue-50, #eff6ff);
  border: 1px solid var(--color-blue-200, #bfdbfe);
  border-radius: 6px;
  font-size: 13px;
  color: var(--primary-color, #2563eb);
}

body.dark-mode .edit-mode-bar {
  background: color-mix(in srgb, var(--primary-color) 10%, transparent);
  border-color: var(--primary-color);
}

.edit-mode-bar .edit-mode-count {
  font-weight: 600;
}
```

- [ ] **Step 2: 커밋**

```bash
git add app/static/css/infra_common.css
git commit -m "style(infra): add dirty/error cell styles for edit mode"
```

---

### Task 3: HTML — 편집 모드 버튼 추가

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html`

- [ ] **Step 1: 편집/저장/취소 버튼 추가**

`infra_assets.html`의 `tab-nav-actions` div 내부, `btn-import-asset` 버튼 앞에 추가:

```html
    <button class="btn btn-secondary btn-sm" id="btn-toggle-edit">편집</button>
    <button class="btn btn-primary btn-sm is-hidden" id="btn-save-edit">저장</button>
    <button class="btn btn-secondary btn-sm is-hidden" id="btn-cancel-edit">취소</button>
```

그리고 그리드 영역 위에 편집 모드 상태바 추가 (filter-bar 아래):

```html
<div id="edit-mode-bar" class="edit-mode-bar is-hidden">
  <span>📝 편집 모드</span>
  <span class="edit-mode-count" id="edit-mode-count">변경 0건</span>
  <span class="edit-mode-errors is-hidden" id="edit-mode-errors">⚠ 오류 0건</span>
</div>
```

- [ ] **Step 2: 커밋**

```bash
git add app/modules/infra/templates/infra_assets.html
git commit -m "feat(infra): add edit mode toggle buttons to asset grid"
```

---

### Task 4: JS — 편집 모드 토글 + dirty 추적 + 검증

**Files:**
- Modify: `app/static/js/infra_assets.js`

이 태스크가 핵심이다. 편집 모드 상태 관리, dirty 추적, 셀 검증, 배치 저장/취소를 모두 구현한다.

- [ ] **Step 1: 편집 모드 상태 변수와 토글 함수 추가**

`infra_assets.js` 상단(`GRID_EDITABLE_FIELDS` 정의 아래)에 추가:

```javascript
/* ── Edit mode state ── */
let _editMode = false;
// _dirtyRows: Map<rowId, { field: newValue, ... }>
const _dirtyRows = new Map();
// _originalValues: Map<rowId, { field: originalValue, ... }>
const _originalValues = new Map();
// _errorCells: Map<"rowId:field", errorMessage>
const _errorCells = new Map();

function isEditMode() { return _editMode; }

function toggleEditMode(force) {
  _editMode = force !== undefined ? force : !_editMode;
  document.body.classList.toggle("edit-mode-active", _editMode);

  // Toggle button visibility
  const btnToggle = document.getElementById("btn-toggle-edit");
  const btnSave = document.getElementById("btn-save-edit");
  const btnCancel = document.getElementById("btn-cancel-edit");
  const bar = document.getElementById("edit-mode-bar");

  if (_editMode) {
    btnToggle.classList.add("is-hidden");
    btnSave.classList.remove("is-hidden");
    btnCancel.classList.remove("is-hidden");
    bar.classList.remove("is-hidden");
    // Switch to multiple row selection
    gridApi.setGridOption("rowSelection", "multiple");
  } else {
    btnToggle.classList.remove("is-hidden");
    btnSave.classList.add("is-hidden");
    btnCancel.classList.add("is-hidden");
    bar.classList.add("is-hidden");
    // Revert to single row selection
    gridApi.setGridOption("rowSelection", "single");
  }
  _updateEditModeBar();
  gridApi.refreshCells({ force: true });
}
```

- [ ] **Step 2: dirty 마킹 함수 추가**

```javascript
function markDirty(rowId, field, newValue, oldValue) {
  if (!_dirtyRows.has(rowId)) _dirtyRows.set(rowId, {});
  if (!_originalValues.has(rowId)) _originalValues.set(rowId, {});

  const dirty = _dirtyRows.get(rowId);
  const originals = _originalValues.get(rowId);

  // 첫 변경 시 원본값 저장
  if (!(field in originals)) originals[field] = oldValue;

  // 원본으로 되돌렸으면 dirty에서 제거
  if (newValue === originals[field]) {
    delete dirty[field];
    if (Object.keys(dirty).length === 0) {
      _dirtyRows.delete(rowId);
      _originalValues.delete(rowId);
    }
  } else {
    dirty[field] = newValue;
  }

  validateCell(rowId, field, newValue);
  _updateEditModeBar();
}

function isDirty(rowId, field) {
  const dirty = _dirtyRows.get(rowId);
  return dirty ? field in dirty : false;
}

function hasErrors() {
  return _errorCells.size > 0;
}

function _updateEditModeBar() {
  const countEl = document.getElementById("edit-mode-count");
  const errorsEl = document.getElementById("edit-mode-errors");
  const btnSave = document.getElementById("btn-save-edit");
  if (countEl) countEl.textContent = `변경 ${_dirtyRows.size}건`;
  if (errorsEl) {
    const errCount = _errorCells.size;
    errorsEl.textContent = `⚠ 오류 ${errCount}건`;
    errorsEl.classList.toggle("is-hidden", errCount === 0);
  }
  if (btnSave) btnSave.disabled = hasErrors();
}
```

- [ ] **Step 3: 셀 검증 함수 추가**

```javascript
const REQUIRED_FIELDS = new Set(["asset_name"]);

function validateCell(rowId, field, value) {
  const key = `${rowId}:${field}`;
  // 필수값 검증
  if (REQUIRED_FIELDS.has(field) && (!value || !String(value).trim())) {
    _errorCells.set(key, "필수값입니다");
    return false;
  }
  // 통과
  _errorCells.delete(key);
  return true;
}

function getCellError(rowId, field) {
  return _errorCells.get(`${rowId}:${field}`) || null;
}
```

- [ ] **Step 4: cellClass 수정 — dirty/error 스타일 반영**

기존 `getGridCellClass` 함수를 수정:

```javascript
function getGridCellClass(field, row = null) {
  const classes = [];
  classes.push(GRID_EDITABLE_FIELDS.has(field) ? "infra-cell-editable" : "infra-cell-readonly");
  if (isRawFallbackField(field, row)) classes.push("infra-cell-rawtext");
  // Edit mode: dirty/error indicators
  if (_editMode && row?.id) {
    if (isDirty(row.id, field)) classes.push("infra-cell-dirty");
    if (getCellError(row.id, field)) classes.push("infra-cell-error");
  }
  return classes.join(" ");
}
```

- [ ] **Step 5: handleGridCellValueChanged 수정 — 편집 모드 분기**

기존 `handleGridCellValueChanged` 함수의 시작 부분에 편집 모드 분기를 추가:

```javascript
async function handleGridCellValueChanged(event) {
  if (_cellChangeInProgress) return;
  const row = event?.data;
  if (!row) return;
  const field = event.colDef.field;
  if (field === "_selected") return;

  // 새 행은 기존 로직 유지
  if (!row.id && row._isNew) {
    _hasNewRows = true;
    _updateNewRowIndicators();
    return;
  }

  // ── 편집 모드: dirty 축적만 하고 서버 전송 안 함 ──
  if (_editMode) {
    markDirty(row.id, field, event.newValue, event.oldValue);
    gridApi.refreshCells({ force: true });
    return;
  }

  // ── Normal mode: 기존 즉시 PATCH 로직 (변경 없음) ──
  if (field !== "current_role_id" && event.newValue === event.oldValue) return;
  _cellChangeInProgress = true;
  // ... (기존 코드 그대로)
```

- [ ] **Step 6: 배치 저장 함수**

```javascript
async function saveEditMode() {
  if (hasErrors()) {
    showToast("검증 오류가 있어 저장할 수 없습니다.", "warning");
    return;
  }
  if (_dirtyRows.size === 0) {
    showToast("변경사항이 없습니다.", "info");
    toggleEditMode(false);
    return;
  }

  const items = [];
  for (const [rowId, changes] of _dirtyRows) {
    items.push({ id: rowId, changes });
  }

  try {
    const results = await apiFetch(_assetPatchUrl("/api/v1/assets/bulk"), {
      method: "PATCH",
      body: { items },
    });
    // 그리드 데이터 갱신
    for (const updated of results) {
      let node = null;
      gridApi.forEachNode((n) => { if (n.data?.id === updated.id) node = n; });
      if (node) applyAssetRowUpdate(node.data, updated);
    }
    showToast(`${results.length}건 자산이 업데이트되었습니다.`);
    _dirtyRows.clear();
    _originalValues.clear();
    _errorCells.clear();
    toggleEditMode(false);
  } catch (err) {
    showToast("저장 실패: " + err.message, "error");
  }
}
```

- [ ] **Step 7: 취소 함수**

```javascript
function cancelEditMode() {
  // 원본값으로 복원
  for (const [rowId, originals] of _originalValues) {
    let node = null;
    gridApi.forEachNode((n) => { if (n.data?.id === rowId) node = n; });
    if (node) {
      for (const [field, value] of Object.entries(originals)) {
        node.data[field] = value;
      }
    }
  }
  _dirtyRows.clear();
  _originalValues.clear();
  _errorCells.clear();
  toggleEditMode(false);
  gridApi.refreshCells({ force: true });
}
```

- [ ] **Step 8: 이벤트 리스너 등록**

기존 이벤트 리스너 등록 영역(파일 하단 DOMContentLoaded 또는 addEventListener 블록)에 추가:

```javascript
document.getElementById("btn-toggle-edit").addEventListener("click", () => toggleEditMode());
document.getElementById("btn-save-edit").addEventListener("click", saveEditMode);
document.getElementById("btn-cancel-edit").addEventListener("click", cancelEditMode);
```

- [ ] **Step 9: 커밋**

```bash
git add app/static/js/infra_assets.js
git commit -m "feat(infra): implement edit mode toggle with dirty tracking and validation"
```

---

### Task 5: JS — 엑셀 붙여넣기 + 행 자동 추가

**Files:**
- Modify: `app/static/js/infra_assets.js`

- [ ] **Step 1: addCopyPasteHandler를 자산 그리드에 연결**

`initGrid()` 함수의 `gridApi = agGrid.createGrid(...)` 호출 직후에 추가:

```javascript
  // 복사/붙여넣기 핸들러
  const gridEl = document.getElementById("grid-assets");
  addCopyPasteHandler(gridEl, gridApi, {
    editableFields: [...GRID_EDITABLE_FIELDS],
    autoCreateRows: true,
    typeMap: {
      environment: { type: "enum", values: Object.keys(ENV_MAP) },
      status: { type: "enum", values: Object.keys(ASSET_STATUS_MAP) },
    },
    onPaste: (changes) => {
      if (_editMode) {
        // Edit mode: mark dirty
        for (const c of changes) {
          const node = gridApi.getDisplayedRowAtIndex(c.rowIndex);
          if (node?.data?.id) {
            markDirty(node.data.id, c.field, c.newValue, c.oldValue);
          } else if (node?.data) {
            // 새 행
            node.data._isNew = true;
            node.data.partner_id = Number(getCtxPartnerId());
            _hasNewRows = true;
          }
        }
        _updateNewRowIndicators();
        _updateEditModeBar();
        gridApi.refreshCells({ force: true });
      } else {
        // Normal mode: 기존 행은 즉시 PATCH
        const rowIds = [...new Set(changes.map(c => c.rowIndex))];
        for (const ri of rowIds) {
          const node = gridApi.getDisplayedRowAtIndex(ri);
          if (!node?.data?.id) continue;
          const rowChanges = changes.filter(c => c.rowIndex === ri);
          const payload = {};
          rowChanges.forEach(c => { payload[c.field] = c.newValue; });
          apiFetch(_assetPatchUrl(`/api/v1/assets/${node.data.id}`), {
            method: "PATCH",
            body: payload,
          }).then(updated => applyAssetRowUpdate(node.data, updated))
            .catch(err => showToast(err.message, "error"));
        }
      }
    },
  });
```

- [ ] **Step 2: 복사 기능 — 행 선택 기반 (getCellRanges 대체)**

`utils.js`의 `addCopyPasteHandler`에서 복사 부분은 `getCellRanges()`에 의존하는데, Community에서는 사용 불가.
자산 그리드에서는 다중 행 선택 기반으로 별도 복사 핸들러를 구현:

`infra_assets.js`의 `initGrid()` 함수 내, `addCopyPasteHandler` 호출 아래에 추가:

```javascript
  // 행 선택 기반 복사 (Ctrl+C) — Range Selection 없는 Community 대체
  gridEl.addEventListener("keydown", (e) => {
    if (!(e.ctrlKey && e.key === "c") && !(e.metaKey && e.key === "c")) return;
    if (gridApi.getEditingCells?.().length > 0) return;

    const selectedNodes = gridApi.getSelectedNodes();
    if (!selectedNodes.length) return;

    const fields = [...GRID_EDITABLE_FIELDS];
    const rows = selectedNodes.map((node) =>
      fields.map((f) => {
        const val = node.data[f];
        return val != null ? String(val) : "";
      })
    );

    const tsv = rows.map((r) => r.join("\t")).join("\n");
    navigator.clipboard.writeText(tsv).catch(() => {});
    e.preventDefault();

    // Flash feedback
    gridApi.flashCells({
      rowNodes: selectedNodes,
      columns: fields,
      flashDuration: 300,
      fadeDuration: 200,
    });
    showToast(`${selectedNodes.length}행 복사됨`, "info");
  });
```

- [ ] **Step 3: 커밋**

```bash
git add app/static/js/infra_assets.js
git commit -m "feat(infra): add Excel paste + row-based copy to asset grid"
```

---

### Task 6: 통합 테스트 및 마무리

**Files:**
- Modify: `app/static/js/infra_assets.js` (버그 수정 등)

- [ ] **Step 1: 브라우저 수동 검증 체크리스트**

아래 항목을 브라우저에서 확인:

1. 편집 버튼 클릭 → 편집 모드 진입, 상태바 표시
2. 더블클릭으로 셀 편집 → dirty 셀 파란색 표시
3. 필수값(asset_name) 비우기 → 빨간색 표시, 저장 버튼 비활성
4. 저장 클릭 → bulk PATCH 호출, 성공 시 편집 모드 종료
5. 취소 클릭 → 원래값 복원, 편집 모드 종료
6. 엑셀에서 복사 → Ctrl+V → 붙여넣기 적용, dirty 마킹
7. 행 초과 붙여넣기 → 새 행 자동 추가
8. 다중 행 선택 → Ctrl+C → TSV 클립보드 복사
9. Normal mode (편집 모드 OFF) → 기존 동작(더블클릭 즉시 PATCH) 유지

- [ ] **Step 2: 커밋**

```bash
git add -A
git commit -m "feat(infra): complete asset grid batch edit mode (phase 1)"
```

---

## 범위 외 (2차)

- 입력값 추천 + 일괄 적용
- 잘라내기 (Ctrl+X)
- 셀 단위 범위 선택 (커스텀 구현 필요)
- dirty 추적의 undo/redo 스택
