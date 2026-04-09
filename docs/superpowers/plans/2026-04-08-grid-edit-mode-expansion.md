# 그리드 편집 모드 확산 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자산 그리드에서 안정화된 배치 편집 모드 패턴을 공통 모듈(`GridEditMode` 클래스)로 추출하고, IP 인벤토리·포트맵·정책 점검·역할 관리·사용자 관리·연락처 그리드에 일관되게 확산한다.

**Architecture:** `GridEditMode` 클래스를 `app/static/js/grid_edit_mode.js`에 독립 파일로 생성한다. 각 그리드 JS는 `new GridEditMode(config)`로 인스턴스를 생성하고, 그리드별 설정(editable fields, required fields, bulk API endpoint, bulk selects)만 전달한다. 백엔드에는 각 도메인별 `PATCH /bulk` 엔드포인트를 추가한다. 자산 그리드를 리팩토링하여 `GridEditMode`를 적용한 첫 번째 소비자로 만든 뒤, 나머지 그리드를 순차 적용한다.

**Tech Stack:** Vanilla JS (ES6+ class), ag-Grid Community, FastAPI, SQLAlchemy

---

## 파일 구조

### 신규 생성
| 파일 | 역할 |
|------|------|
| `app/static/js/grid_edit_mode.js` | `GridEditMode` 공통 클래스 — dirty tracking, validation, save/cancel, edit mode bar, bulk apply |
| `app/static/css/grid_edit_mode.css` | 편집 모드 공통 CSS (기존 `infra_common.css`에서 추출) |

### 수정 대상
| 파일 | 변경 내용 |
|------|-----------|
| `app/static/js/infra_assets.js` | 인라인 편집 로직 → `GridEditMode` 인스턴스로 교체 |
| `app/static/js/infra_ip_inventory.js` | `GridEditMode` 적용 |
| `app/static/js/infra_port_maps.js` | `GridEditMode` 적용 |
| `app/static/js/infra_policies.js` | `GridEditMode` 적용 |
| `app/static/js/infra_asset_roles.js` | 역할 할당 이력 그리드에 `GridEditMode` 적용 |
| `app/static/js/users.js` | 기존 `changedRows` 패턴 → `GridEditMode`로 교체 |
| `app/static/css/infra_common.css` | 편집 모드 CSS를 `grid_edit_mode.css`로 이전 |
| `app/modules/infra/templates/infra_assets.html` | 편집 모드 바 HTML → `GridEditMode`가 동적 생성 |
| `app/modules/infra/templates/infra_ip_inventory.html` | 편집 모드 버튼 + 바 추가 |
| `app/modules/infra/templates/infra_port_maps.html` | 편집 모드 버튼 + 바 추가 |
| `app/modules/infra/templates/infra_policies.html` | 편집 모드 버튼 + 바 추가 |
| `app/modules/infra/templates/infra_asset_roles.html` | 편집 모드 버튼 + 바 추가 |
| `app/modules/common/templates/users.html` | 기존 저장 버튼 → 편집 모드 버튼으로 교체 |

### 백엔드 신규 엔드포인트
| 라우터 파일 | 엔드포인트 | 서비스 |
|-------------|-----------|--------|
| `app/modules/infra/routers/asset_ips.py` | `PATCH /api/v1/asset-ips/bulk` | `network_service.bulk_update_asset_ips()` |
| `app/modules/infra/routers/port_maps.py` | `PATCH /api/v1/port-maps/bulk` | `network_service.bulk_update_port_maps()` |
| `app/modules/infra/routers/policy_assignments.py` | `PATCH /api/v1/policy-assignments/bulk` | `policy_service.bulk_update_assignments()` |
| `app/modules/infra/routers/asset_roles.py` | `PATCH /api/v1/asset-roles/assignments/bulk` | `asset_role_service.bulk_update_assignments()` |
| `app/modules/common/routers/users.py` | `PATCH /api/v1/users/bulk` | `user.bulk_update_users()` |

---

## Task 1: `GridEditMode` 공통 클래스 생성

**Files:**
- Create: `app/static/js/grid_edit_mode.js`

- [ ] **Step 1: `GridEditMode` 클래스 작성**

```javascript
/**
 * 그리드 배치 편집 모드 공통 클래스.
 *
 * @param {Object} config
 * @param {Object} config.gridApi                - ag-Grid API 인스턴스
 * @param {Set<string>} config.editableFields     - 편집 가능 필드 Set
 * @param {Set<string>} [config.requiredFields]   - 필수값 필드 Set (기본: 빈 Set)
 * @param {string} config.bulkApiUrl              - 배치 저장 API URL (e.g. "/api/v1/assets/bulk")
 * @param {string} [config.apiMethod]             - HTTP 메서드 (기본: "PATCH")
 * @param {Function} [config.buildPayload]        - (dirtyRows: Map) => request body. 기본: { items: [{id, changes}] }
 * @param {Function} [config.onSaveSuccess]       - (results) => void. 저장 성공 후 콜백
 * @param {Function} [config.onCancelRestore]     - (rowId, originals, node) => void. 취소 시 행 복원 커스텀 로직
 * @param {Function} [config.getRowId]            - (rowData) => id. 행 ID 추출 (기본: row.id)
 * @param {Function} [config.validateCell]        - (rowId, field, value) => string|null. 커스텀 검증. null=통과, string=에러메시지
 * @param {Object} [config.bulkSelects]           - { elementId: { field, populate: () => [{value, label}] } }
 * @param {Object} [config.ui]                    - { toggleBtn, saveBtn, cancelBtn, barContainer }. 요소 ID 또는 null (동적 생성)
 * @param {string} [config.entityLabel]           - 토스트에 표시할 엔티티명 (기본: "항목")
 */
class GridEditMode {
  constructor(config) {
    this.gridApi = config.gridApi;
    this.editableFields = config.editableFields;
    this.requiredFields = config.requiredFields || new Set();
    this.bulkApiUrl = config.bulkApiUrl;
    this.apiMethod = config.apiMethod || "PATCH";
    this.buildPayload = config.buildPayload || null;
    this.onSaveSuccess = config.onSaveSuccess || null;
    this.onCancelRestore = config.onCancelRestore || null;
    this.getRowId = config.getRowId || ((row) => row.id);
    this.customValidateCell = config.validateCell || null;
    this.bulkSelectsConfig = config.bulkSelects || {};
    this.entityLabel = config.entityLabel || "항목";

    // State
    this.active = false;
    this.dirtyRows = new Map();
    this.originalValues = new Map();
    this.errorCells = new Map();

    // UI references
    this._ui = config.ui || {};
  }

  // ── 편집 모드 토글 ──

  toggle(force) {
    this.active = force !== undefined ? force : !this.active;
    document.body.classList.toggle("edit-mode-active", this.active);

    const btnToggle = this._el(this._ui.toggleBtn);
    const btnSave = this._el(this._ui.saveBtn);
    const btnCancel = this._el(this._ui.cancelBtn);
    const bar = this._el(this._ui.barContainer);

    if (this.active) {
      btnToggle?.classList.add("is-hidden");
      btnSave?.classList.remove("is-hidden");
      btnCancel?.classList.remove("is-hidden");
      bar?.classList.remove("is-hidden");
      this._populateBulkSelects();
    } else {
      btnToggle?.classList.remove("is-hidden");
      btnSave?.classList.add("is-hidden");
      btnCancel?.classList.add("is-hidden");
      bar?.classList.add("is-hidden");
      this.gridApi.deselectAll();
    }
    this._updateBar();
    this._updateBulkSelectionUI();
    this.gridApi.refreshCells({ force: true });
  }

  // ── Dirty Tracking ──

  markDirty(rowId, field, newValue, oldValue) {
    if (!this.dirtyRows.has(rowId)) this.dirtyRows.set(rowId, {});
    if (!this.originalValues.has(rowId)) this.originalValues.set(rowId, {});
    const dirty = this.dirtyRows.get(rowId);
    const originals = this.originalValues.get(rowId);
    if (!(field in originals)) originals[field] = oldValue;
    if (newValue === originals[field]) {
      delete dirty[field];
      if (Object.keys(dirty).length === 0) {
        this.dirtyRows.delete(rowId);
        this.originalValues.delete(rowId);
      }
    } else {
      dirty[field] = newValue;
    }
    this.validateCell(rowId, field, newValue);
    this._updateBar();
  }

  isDirty(rowId, field) {
    const d = this.dirtyRows.get(rowId);
    return d ? field in d : false;
  }

  // ── Validation ──

  validateCell(rowId, field, value) {
    const key = `${rowId}:${field}`;
    // 커스텀 검증 우선
    if (this.customValidateCell) {
      const err = this.customValidateCell(rowId, field, value);
      if (err) { this.errorCells.set(key, err); return false; }
    }
    // 필수값 검증
    if (this.requiredFields.has(field) && (!value || !String(value).trim())) {
      this.errorCells.set(key, "필수값입니다");
      return false;
    }
    this.errorCells.delete(key);
    return true;
  }

  hasErrors() { return this.errorCells.size > 0; }

  getCellError(rowId, field) {
    return this.errorCells.get(`${rowId}:${field}`) || null;
  }

  // ── Cell Class Helper ──

  getCellClass(field, row = null) {
    const classes = [];
    classes.push(this.editableFields.has(field) ? "grid-cell-editable" : "grid-cell-readonly");
    if (this.active && row) {
      const rowId = this.getRowId(row);
      if (rowId != null) {
        if (this.isDirty(rowId, field)) classes.push("grid-cell-dirty");
        if (this.getCellError(rowId, field)) classes.push("grid-cell-error");
      }
    }
    return classes.join(" ");
  }

  isFieldEditable(field) {
    return this.active && this.editableFields.has(field);
  }

  // ── Save ──

  async save() {
    if (this.hasErrors()) {
      showToast("검증 오류가 있어 저장할 수 없습니다.", "warning");
      return;
    }
    if (this.dirtyRows.size === 0) {
      showToast("변경사항이 없습니다.", "info");
      this.toggle(false);
      return;
    }
    const payload = this.buildPayload
      ? this.buildPayload(this.dirtyRows)
      : { items: [...this.dirtyRows].map(([id, changes]) => ({ id, changes })) };
    try {
      const results = await apiFetch(this.bulkApiUrl, {
        method: this.apiMethod,
        body: payload,
      });
      if (this.onSaveSuccess) {
        this.onSaveSuccess(results);
      } else {
        // 기본 동작: 그리드 행 데이터 업데이트
        for (const updated of (Array.isArray(results) ? results : [])) {
          const uid = this.getRowId(updated);
          this.gridApi.forEachNode((n) => {
            if (n.data && this.getRowId(n.data) === uid) {
              Object.assign(n.data, updated);
            }
          });
        }
      }
      const count = this.dirtyRows.size;
      this._clearState();
      this.toggle(false);
      showToast(`${count}건 ${this.entityLabel}이(가) 업데이트되었습니다.`);
    } catch (err) {
      showToast("저장 실패: " + err.message, "error");
    }
  }

  // ── Cancel ──

  cancel() {
    for (const [rowId, originals] of this.originalValues) {
      let node = null;
      this.gridApi.forEachNode((n) => {
        if (n.data && this.getRowId(n.data) === rowId) node = n;
      });
      if (node) {
        if (this.onCancelRestore) {
          this.onCancelRestore(rowId, originals, node);
        } else {
          for (const [field, value] of Object.entries(originals)) {
            node.data[field] = value;
          }
        }
      }
    }
    this._clearState();
    this.toggle(false);
    this.gridApi.refreshCells({ force: true });
  }

  // ── 내부 헬퍼 ──

  _clearState() {
    this.dirtyRows.clear();
    this.originalValues.clear();
    this.errorCells.clear();
  }

  _el(id) {
    return id ? document.getElementById(id) : null;
  }

  _updateBar() {
    const countEl = this._el(this._ui.countDisplay);
    const errorsEl = this._el(this._ui.errorsDisplay);
    const btnSave = this._el(this._ui.saveBtn);
    if (countEl) countEl.textContent = `변경 ${this.dirtyRows.size}건`;
    if (errorsEl) {
      const errCount = this.errorCells.size;
      errorsEl.textContent = `오류 ${errCount}건`;
      errorsEl.classList.toggle("is-hidden", errCount === 0);
    }
    if (btnSave) btnSave.disabled = this.hasErrors();
  }

  _updateBulkSelectionUI() {
    const selPanel = this._el(this._ui.selectionPanel);
    const countEl = this._el(this._ui.selCountDisplay);
    if (!selPanel) return;
    const selCount = this.gridApi.getSelectedNodes().length;
    if (this.active && selCount > 0) {
      selPanel.classList.remove("is-hidden");
      if (countEl) countEl.textContent = `${selCount}행 선택`;
    } else {
      selPanel.classList.add("is-hidden");
    }
  }

  _populateBulkSelects() {
    for (const [elId, cfg] of Object.entries(this.bulkSelectsConfig)) {
      const sel = this._el(elId);
      if (!sel) continue;
      sel.textContent = "";
      const blank = document.createElement("option");
      blank.value = "";
      blank.textContent = "--";
      sel.appendChild(blank);
      const items = typeof cfg.populate === "function" ? cfg.populate() : [];
      for (const item of items) {
        const opt = document.createElement("option");
        opt.value = item.value;
        opt.textContent = item.label;
        sel.appendChild(opt);
      }
    }
  }

  applyBulkValues(fieldValues) {
    const selected = this.gridApi.getSelectedNodes().filter(n => n.data);
    if (!selected.length) { showToast("행을 먼저 선택하세요.", "warning"); return; }
    const entries = Object.entries(fieldValues).filter(([, v]) => v !== "" && v != null);
    if (!entries.length) { showToast("적용할 값을 선택하세요.", "warning"); return; }
    let count = 0;
    for (const node of selected) {
      const d = node.data;
      const rowId = this.getRowId(d);
      for (const [field, value] of entries) {
        const old = d[field];
        const parsed = typeof old === "number" ? Number(value) : value;
        if (parsed !== old) {
          d[field] = parsed;
          this.markDirty(rowId, field, parsed, old);
          count++;
        }
      }
    }
    this.gridApi.refreshCells({ force: true });
    if (count) showToast(`${selected.length}행에 값이 적용되었습니다.`);
  }

  // ── Cell value change handler factory ──

  handleCellValueChanged(event, extraHandler) {
    const { data, colDef, newValue, oldValue } = event;
    if (newValue === oldValue) return;
    const rowId = this.getRowId(data);
    if (this.active) {
      this.markDirty(rowId, colDef.field, newValue, oldValue);
      this.gridApi.refreshCells({ rowNodes: [event.node], force: true });
    } else if (extraHandler) {
      extraHandler(event);
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/grid_edit_mode.js
git commit -m "feat: add GridEditMode common class for batch edit pattern"
```

---

## Task 2: 공통 편집 모드 CSS 추출

**Files:**
- Create: `app/static/css/grid_edit_mode.css`
- Modify: `app/static/css/infra_common.css`

- [ ] **Step 1: `grid_edit_mode.css` 작성**

기존 `infra_common.css`의 편집 모드 관련 CSS를 복사하되, `infra-cell-*` 접두사를 `grid-cell-*`로 통일한다. 기존 `infra-cell-*` 클래스도 하위 호환성을 위해 alias로 유지한다.

```css
/* ── Grid Edit Mode 공통 스타일 ── */

/* 셀 상태 */
.grid-cell-editable,
.infra-cell-editable {
  /* editable marker - 기본적으로 시각 표시 없음, 편집 모드에서 커서 변경 */
}

.grid-cell-readonly,
.infra-cell-readonly {
  /* readonly - 편집 모드에서 색상 구분 */
}

.grid-cell-dirty,
.infra-cell-dirty {
  background: color-mix(in srgb, var(--primary-color, #2563eb) 6%, transparent) !important;
}

.grid-cell-error,
.infra-cell-error {
  background: color-mix(in srgb, var(--danger-color, #dc2626) 8%, transparent) !important;
}

body.dark-mode .grid-cell-dirty,
body.dark-mode .infra-cell-dirty {
  background: color-mix(in srgb, var(--primary-color, #2563eb) 12%, transparent) !important;
}

body.dark-mode .grid-cell-error,
body.dark-mode .infra-cell-error {
  background: color-mix(in srgb, var(--danger-color, #dc2626) 12%, transparent) !important;
}

/* 편집 모드 바 */
.edit-mode-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px;
  background: color-mix(in srgb, var(--warning-color, #d97706) 10%, var(--bg-secondary));
  border: 1px solid color-mix(in srgb, var(--warning-color, #d97706) 30%, var(--border-color));
  border-radius: 6px;
  font-size: 13px;
  margin-bottom: 6px;
}

.edit-mode-bar .edit-mode-label {
  font-weight: 600;
  color: var(--warning-color, #d97706);
}

.edit-mode-bar .edit-mode-count {
  color: var(--text-secondary);
}

.edit-mode-bar .edit-mode-errors {
  color: var(--danger-color, #dc2626);
  font-weight: 600;
}

.edit-mode-bar .edit-mode-separator {
  color: var(--border-color);
}

.edit-mode-bar .edit-mode-selection {
  display: flex;
  align-items: center;
  gap: 8px;
}

.edit-mode-bar .edit-mode-selection label {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

/* 편집 모드 활성 시 그리드 카드 테두리 */
.edit-mode-active .card {
  border-color: color-mix(in srgb, var(--warning-color, #d97706) 50%, var(--border-color));
}
```

- [ ] **Step 2: `infra_common.css`에서 중복 편집 모드 CSS 제거**

기존 `infra_common.css`에서 `.infra-cell-dirty`, `.infra-cell-error`, `.edit-mode-bar`, `.edit-mode-active` 관련 규칙을 제거한다. (새 파일에서 `infra-cell-*` alias가 포함되어 있으므로 기존 코드가 깨지지 않는다.)

- [ ] **Step 3: 공통 레이아웃 템플릿에 CSS/JS 추가**

`grid_edit_mode.css`와 `grid_edit_mode.js`를 공통 base 템플릿 또는 사용하는 각 페이지에 `<link>` / `<script>` 태그로 추가한다.

- [ ] **Step 4: Commit**

```bash
git add app/static/css/grid_edit_mode.css app/static/css/infra_common.css
git commit -m "refactor: extract grid edit mode CSS into shared file"
```

---

## Task 3: 자산 그리드를 `GridEditMode`로 리팩토링 (검증 기준)

**Files:**
- Modify: `app/static/js/infra_assets.js` (lines 124-263, 612-621 등)
- Modify: `app/modules/infra/templates/infra_assets.html`

- [ ] **Step 1: `GridEditMode` 인스턴스 생성**

`infra_assets.js`의 `initGrid()` 함수 내, `agGrid.createGrid()` 직후에 `GridEditMode` 인스턴스를 생성한다.

```javascript
let editMode; // 모듈 스코프

// initGrid() 내, gridApi = agGrid.createGrid(...) 직후:
editMode = new GridEditMode({
  gridApi,
  editableFields: GRID_EDITABLE_FIELDS,
  requiredFields: new Set(["asset_name"]),
  bulkApiUrl: _assetPatchUrl("/api/v1/assets/bulk"),
  entityLabel: "자산",
  getRowId: (row) => row.id,
  onSaveSuccess: (results) => {
    for (const updated of results) {
      let node = null;
      gridApi.forEachNode((n) => { if (n.data?.id === updated.id) node = n; });
      if (node) applyAssetRowUpdate(node.data, updated);
    }
  },
  bulkSelects: {
    "bulk-period-id": { field: "period_id", populate: () => _periodsCache.map(p => ({ value: p.id, label: p.contract_name || p.period_label || String(p.id) })) },
    "bulk-center-id": { field: "center_id", populate: () => _layoutCentersCache.map(c => ({ value: c.id, label: c.center_name })) },
    "bulk-environment": { field: "environment", populate: () => Object.entries(ENV_MAP).map(([k, v]) => ({ value: k, label: v })) },
    "bulk-status": { field: "status", populate: () => Object.entries(ASSET_STATUS_MAP).map(([k, v]) => ({ value: k, label: v })) },
  },
  ui: {
    toggleBtn: "btn-toggle-edit",
    saveBtn: "btn-save-edit",
    cancelBtn: "btn-cancel-edit",
    barContainer: "edit-mode-bar",
    countDisplay: "edit-mode-count",
    errorsDisplay: "edit-mode-errors",
    selectionPanel: "edit-mode-selection",
    selCountDisplay: "edit-mode-sel-count",
  },
});
```

- [ ] **Step 2: 인라인 함수를 `editMode` 위임으로 교체**

기존 `toggleEditMode`, `markDirty`, `isDirty`, `validateCell`, `getCellError`, `hasErrors`, `saveEditMode`, `cancelEditMode`, `_updateEditModeBar` 함수를 `editMode` 인스턴스 메서드 호출로 래핑하거나 직접 교체한다.

```javascript
// 기존 함수를 래퍼로 유지 (외부 참조 호환)
function toggleEditMode(force) { editMode.toggle(force); }
function markDirty(rowId, field, newValue, oldValue) { editMode.markDirty(rowId, field, newValue, oldValue); }
function isDirty(rowId, field) { return editMode.isDirty(rowId, field); }
function isEditMode() { return editMode.active; }
function hasErrors() { return editMode.hasErrors(); }
function validateCell(rowId, field, value) { return editMode.validateCell(rowId, field, value); }
function getCellError(rowId, field) { return editMode.getCellError(rowId, field); }
async function saveEditMode() { return editMode.save(); }
function cancelEditMode() { editMode.cancel(); }
function _updateEditModeBar() { editMode._updateBar(); }
function _updateBulkSelectionUI() { editMode._updateBulkSelectionUI(); }
```

`getGridCellClass` 함수도 `editMode.getCellClass()`를 활용하도록 변경:

```javascript
function getGridCellClass(field, row = null) {
  const classes = [];
  // rawtext fallback은 자산 그리드 고유 로직이므로 유지
  if (editMode) {
    classes.push(editMode.getCellClass(field, row));
  } else {
    classes.push(GRID_EDITABLE_FIELDS.has(field) ? "infra-cell-editable" : "infra-cell-readonly");
  }
  if (isRawFallbackField(field, row)) classes.push("infra-cell-rawtext");
  return classes.join(" ");
}
```

- [ ] **Step 3: 기존 인라인 상태 변수 제거**

```javascript
// 삭제 대상 (editMode 인스턴스가 관리):
// let _editMode = false;
// const _dirtyRows = new Map();
// const _originalValues = new Map();
// const _errorCells = new Map();
// const REQUIRED_FIELDS = new Set(["asset_name"]);
```

`_editMode` 직접 참조를 `editMode.active`로 교체 (파일 전체 검색/치환).

- [ ] **Step 4: `_applyBulkValues()`를 `editMode.applyBulkValues()` 호출로 교체**

```javascript
function _applyBulkValues() {
  editMode.applyBulkValues({
    period_id: document.getElementById("bulk-period-id").value,
    center_id: document.getElementById("bulk-center-id").value,
    environment: document.getElementById("bulk-environment").value,
    status: document.getElementById("bulk-status").value,
  });
}
```

- [ ] **Step 5: `handleGridCellValueChanged`에서 `editMode` 활용**

편집 모드일 때 `editMode.handleCellValueChanged(event, nonEditHandler)` 패턴 적용.

- [ ] **Step 6: 브라우저 검증**

자산 그리드에서 다음을 수동 확인:
1. 편집 모드 토글 (버튼, 바, body class)
2. 셀 편집 → dirty 표시 (파란색 배경)
3. 필수값 비우기 → error 표시 (빨간색 배경)
4. 저장 → bulk PATCH 호출 → 성공 토스트
5. 취소 → 원래 값 복원
6. 벌크 적용 (행 선택 → 값 선택 → 적용)
7. 복사/붙여넣기 동작

- [ ] **Step 7: Commit**

```bash
git add app/static/js/infra_assets.js app/modules/infra/templates/infra_assets.html
git commit -m "refactor: migrate asset grid to GridEditMode class"
```

---

## Task 4: 백엔드 Bulk 엔드포인트 추가 (IP, 포트맵, 정책, 역할 할당, 사용자)

**Files:**
- Modify: `app/modules/infra/routers/asset_ips.py`
- Modify: `app/modules/infra/routers/port_maps.py`
- Modify: `app/modules/infra/routers/policy_assignments.py`
- Modify: `app/modules/infra/routers/asset_roles.py`
- Modify: `app/modules/common/routers/users.py`
- Modify: `app/modules/infra/services/network_service.py`
- Modify: `app/modules/infra/services/policy_service.py`
- Modify: `app/modules/infra/services/asset_role_service.py`
- Modify: `app/modules/common/services/user.py`
- Create: `app/modules/infra/schemas/bulk_update.py`

- [ ] **Step 1: 공통 Bulk Update 스키마 생성**

```python
# app/modules/infra/schemas/bulk_update.py
from pydantic import BaseModel


class BulkUpdateItem(BaseModel):
    id: int
    changes: dict


class BulkUpdateRequest(BaseModel):
    items: list[BulkUpdateItem]
```

- [ ] **Step 2: IP Inventory bulk 엔드포인트**

`asset_ips.py`에 추가:

```python
from app.modules.infra.schemas.bulk_update import BulkUpdateRequest

@router.patch("/asset-ips/bulk", response_model=list[AssetIPRead])
def bulk_update_asset_ips(
    req: BulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return bulk_update_asset_ips_service(db, req.items, current_user)
```

`network_service.py`에 추가:

```python
def bulk_update_asset_ips_service(
    db: Session,
    items: list,
    current_user,
) -> list[AssetIP]:
    results = []
    allowed = set(AssetIPUpdate.model_fields.keys())
    for item in items:
        filtered = {k: v for k, v in item.changes.items() if k in allowed}
        if not filtered:
            continue
        ip = db.get(AssetIP, item.id)
        if not ip:
            continue
        for k, v in filtered.items():
            setattr(ip, k, v)
        results.append(ip)
    db.commit()
    for r in results:
        db.refresh(r)
    return results
```

- [ ] **Step 3: Port Map bulk 엔드포인트**

같은 패턴으로 `port_maps.py` + `network_service.py`에 추가.

```python
@router.patch("/port-maps/bulk", response_model=list[PortMapRead])
def bulk_update_port_maps(
    req: BulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return bulk_update_port_maps_service(db, req.items, current_user)
```

- [ ] **Step 4: Policy Assignment bulk 엔드포인트**

`policy_assignments.py` + `policy_service.py`에 추가.

```python
@router.patch("/policy-assignments/bulk", response_model=list[PolicyAssignmentRead])
def bulk_update_assignments(
    req: BulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return bulk_update_assignments_service(db, req.items, current_user)
```

- [ ] **Step 5: Asset Role Assignment bulk 엔드포인트**

`asset_roles.py` + `asset_role_service.py`에 추가.

```python
@router.patch("/asset-roles/assignments/bulk", response_model=list[AssetRoleAssignmentRead])
def bulk_update_role_assignments(
    req: BulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return bulk_update_role_assignments_service(db, req.items, current_user)
```

- [ ] **Step 6: Users bulk 엔드포인트**

`users.py` (common) + `user.py` 서비스에 추가.

```python
@router.patch("/users/bulk", response_model=list[UserRead])
def bulk_update_users(
    req: BulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return bulk_update_users_service(db, req.items, current_user)
```

주의: `BulkUpdateRequest`는 infra 스키마에 있으므로, common 모듈에서 import 시 모듈 간 의존 규칙(`core ← common ← {accounting, infra}`)을 위반할 수 있다. **common 모듈용 `BulkUpdateRequest`를 `app/modules/common/schemas/bulk_update.py`에 별도 복사하거나, `app/core/schemas/bulk_update.py`에 배치한다.** → `app/core/schemas/bulk_update.py`에 배치하여 모든 모듈에서 공유.

- [ ] **Step 7: Commit**

```bash
git add app/core/schemas/bulk_update.py app/modules/infra/routers/ app/modules/infra/services/ app/modules/common/routers/users.py app/modules/common/services/user.py
git commit -m "feat: add bulk PATCH endpoints for IP, port map, policy, role assignment, users"
```

---

## Task 5: IP 인벤토리 그리드에 `GridEditMode` 적용

**Files:**
- Modify: `app/static/js/infra_ip_inventory.js`
- Modify: `app/modules/infra/templates/infra_ip_inventory.html`

- [ ] **Step 1: HTML에 편집 모드 UI 추가**

`infra_ip_inventory.html` 필터바 아래에 편집 모드 버튼과 바를 추가한다.

```html
<div class="action-bar">
  <button class="btn btn-sm btn-warning" id="btn-toggle-edit">편집 모드</button>
  <button class="btn btn-sm btn-primary is-hidden" id="btn-save-edit">저장</button>
  <button class="btn btn-sm btn-secondary is-hidden" id="btn-cancel-edit">취소</button>
</div>
<div id="edit-mode-bar" class="edit-mode-bar is-hidden">
  <span class="edit-mode-label">편집 모드</span>
  <span class="edit-mode-count" id="edit-mode-count">변경 0건</span>
  <span class="edit-mode-errors is-hidden" id="edit-mode-errors">오류 0건</span>
</div>
```

- [ ] **Step 2: JS에서 `GridEditMode` 인스턴스 생성**

`infra_ip_inventory.js`의 `initGrid()` 함수 내에서:

```javascript
const IP_EDITABLE_FIELDS = new Set(["hostname", "service_name", "zone", "vlan_id", "note"]);
let editMode;

function initGrid() {
  _populateFilterStatus();
  const gridDiv = document.getElementById("grid-ips");
  gridApi = agGrid.createGrid(gridDiv, {
    columnDefs: ipColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "multiple",  // single → multiple로 변경
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'inline-edit',
      onCellValueChanged: (e) => editMode.handleCellValueChanged(e, handleIpCellChanged),
    }),
  });

  editMode = new GridEditMode({
    gridApi,
    editableFields: IP_EDITABLE_FIELDS,
    bulkApiUrl: "/api/v1/asset-ips/bulk",
    entityLabel: "IP",
    ui: {
      toggleBtn: "btn-toggle-edit",
      saveBtn: "btn-save-edit",
      cancelBtn: "btn-cancel-edit",
      barContainer: "edit-mode-bar",
      countDisplay: "edit-mode-count",
      errorsDisplay: "edit-mode-errors",
    },
  });

  document.getElementById("btn-toggle-edit").addEventListener("click", () => editMode.toggle());
  document.getElementById("btn-save-edit").addEventListener("click", () => editMode.save());
  document.getElementById("btn-cancel-edit").addEventListener("click", () => editMode.cancel());
  // ... 기존 이벤트 바인딩
}
```

- [ ] **Step 3: 컬럼에 `editable` 콜백과 `cellClass` 추가**

```javascript
// ipColDefs 수정 — editable 필드에:
{ field: "hostname", headerName: "호스트명", width: 130,
  editable: () => editMode?.isFieldEditable("hostname"),
  cellClass: (p) => editMode?.getCellClass(p.colDef.field, p.data) || "" },
// zone, vlan_id, service_name, note도 동일 패턴
```

- [ ] **Step 4: 브라우저 검증**

IP 인벤토리에서 편집 모드 토글 → 셀 편집 → dirty 표시 → 저장/취소 동작 확인.

- [ ] **Step 5: Commit**

```bash
git add app/static/js/infra_ip_inventory.js app/modules/infra/templates/infra_ip_inventory.html
git commit -m "feat: apply GridEditMode to IP inventory grid"
```

---

## Task 6: 포트맵 그리드에 `GridEditMode` 적용

**Files:**
- Modify: `app/static/js/infra_port_maps.js`
- Modify: `app/modules/infra/templates/infra_port_maps.html`

- [ ] **Step 1: HTML에 편집 모드 UI 추가**

Task 5와 동일한 버튼+바 패턴.

- [ ] **Step 2: JS에서 `GridEditMode` 인스턴스 생성**

```javascript
const PORTMAP_EDITABLE_FIELDS = new Set([
  "connection_type", "cable_no", "cable_type", "cable_speed", "purpose", "status"
]);
// 참고: src_asset_name, src_interface_name, dst_asset_name, dst_interface_name은
// 특수 로직(자산/인터페이스 ID resolve)이 필요하므로 편집 모드 대상에서 제외하고
// 텍스트 필드만 batch edit 대상으로 한다.

editMode = new GridEditMode({
  gridApi,
  editableFields: PORTMAP_EDITABLE_FIELDS,
  bulkApiUrl: "/api/v1/port-maps/bulk",
  entityLabel: "포트맵",
  bulkSelects: {
    "bulk-portmap-status": {
      field: "status",
      populate: () => Object.entries(PORTMAP_STATUS_MAP).map(([k, v]) => ({ value: k, label: v })),
    },
  },
  ui: { /* 동일 패턴 */ },
});
```

- [ ] **Step 3: 컬럼에 `editable` 콜백과 `cellClass` 추가**

- [ ] **Step 4: 기존 `handlePortMapCellChanged` 수정 — 편집 모드 분기**

- [ ] **Step 5: 브라우저 검증 + Commit**

```bash
git commit -m "feat: apply GridEditMode to port map grid"
```

---

## Task 7: 정책 점검 그리드에 `GridEditMode` 적용

**Files:**
- Modify: `app/static/js/infra_policies.js`
- Modify: `app/modules/infra/templates/infra_policies.html`

- [ ] **Step 1: HTML에 편집 모드 UI 추가**

- [ ] **Step 2: JS에서 `GridEditMode` 인스턴스 생성**

```javascript
const POLICY_EDITABLE_FIELDS = new Set([
  "status", "checked_by", "checked_date", "exception_reason", "evidence_note"
]);

editMode = new GridEditMode({
  gridApi: assignGridApi,
  editableFields: POLICY_EDITABLE_FIELDS,
  bulkApiUrl: "/api/v1/policy-assignments/bulk",
  entityLabel: "점검항목",
  bulkSelects: {
    "bulk-policy-status": {
      field: "status",
      populate: () => Object.entries(ASSIGNMENT_STATUS_MAP).map(([k, v]) => ({ value: k, label: v })),
    },
  },
  ui: { /* 동일 패턴 */ },
});
```

- [ ] **Step 3: 컬럼에 `editable` 콜백과 `cellClass` 추가**

- [ ] **Step 4: 브라우저 검증 + Commit**

```bash
git commit -m "feat: apply GridEditMode to policy assignment grid"
```

---

## Task 8: 역할 할당 이력 그리드에 `GridEditMode` 적용

**Files:**
- Modify: `app/static/js/infra_asset_roles.js`
- Modify: `app/modules/infra/templates/infra_asset_roles.html`

- [ ] **Step 1: HTML에 편집 모드 UI 추가**

역할 상세 패널 내 할당 이력 그리드 영역에 버튼+바 추가.

- [ ] **Step 2: JS에서 `GridEditMode` 인스턴스 생성**

```javascript
const ASSIGNMENT_EDITABLE_FIELDS = new Set([
  "assignment_type", "valid_from", "valid_to", "note"
]);

assignmentEditMode = new GridEditMode({
  gridApi: assignmentGridApi,
  editableFields: ASSIGNMENT_EDITABLE_FIELDS,
  bulkApiUrl: "/api/v1/asset-roles/assignments/bulk",
  entityLabel: "할당이력",
  ui: { /* 동일 패턴 */ },
});
```

- [ ] **Step 3: 컬럼에 `editable` 콜백과 `cellClass` 추가**

- [ ] **Step 4: 브라우저 검증 + Commit**

```bash
git commit -m "feat: apply GridEditMode to role assignment history grid"
```

---

## Task 9: 사용자 관리 그리드에 `GridEditMode` 적용

**Files:**
- Modify: `app/static/js/users.js`
- Modify: `app/modules/common/templates/users.html`

- [ ] **Step 1: HTML에 편집 모드 UI 추가 (기존 저장 버튼 교체)**

기존 `changedRows` 기반 저장 버튼을 편집 모드 토글/저장/취소로 교체.

- [ ] **Step 2: JS에서 기존 `changedRows` 패턴을 `GridEditMode`로 교체**

```javascript
const USER_EDITABLE_FIELDS = new Set([
  "login_id", "name", "department", "position", "is_active"
]);

editMode = new GridEditMode({
  gridApi,
  editableFields: USER_EDITABLE_FIELDS,
  bulkApiUrl: "/api/v1/users/bulk",
  entityLabel: "사용자",
  ui: { /* 동일 패턴 */ },
});

// 기존 changedRows Map과 관련 로직 삭제
```

- [ ] **Step 3: 컬럼에 `editable` 콜백과 `cellClass` 추가**

- [ ] **Step 4: 기존 `saveChanges()` 함수 제거 → `editMode.save()` 사용**

- [ ] **Step 5: 브라우저 검증 + Commit**

```bash
git commit -m "feat: apply GridEditMode to user management grid"
```

---

## Task 10: 문서 갱신 + 최종 검증

**Files:**
- Modify: `docs/guidelines/frontend.md`
- Modify: `docs/guidelines/infra.md`
- Modify: `docs/PROJECT_STRUCTURE.md`

- [ ] **Step 1: `docs/guidelines/frontend.md` 갱신**

그리드 편집 모드 패턴 섹션 추가:
- `GridEditMode` 클래스 사용법
- 새 그리드에 편집 모드 추가할 때의 체크리스트
- UI 요소 ID 명명 규칙

- [ ] **Step 2: `docs/guidelines/infra.md` 갱신**

- 배치 편집 대상 그리드 목록
- bulk API 엔드포인트 목록

- [ ] **Step 3: `docs/PROJECT_STRUCTURE.md` 갱신**

신규 파일 추가:
- `app/static/js/grid_edit_mode.js`
- `app/static/css/grid_edit_mode.css`
- `app/core/schemas/bulk_update.py`

- [ ] **Step 4: 전체 브라우저 회귀 검증**

모든 대상 그리드에서:
1. 편집 모드 진입/퇴장
2. 셀 편집 + dirty 표시
3. 저장 (bulk PATCH)
4. 취소 (원복)
5. 벌크 적용 (해당되는 그리드)
6. 편집 모드 해제 상태에서 기존 인라인 편집 동작 유지 확인

- [ ] **Step 5: Commit**

```bash
git add docs/
git commit -m "docs: update guidelines for GridEditMode pattern expansion"
```
