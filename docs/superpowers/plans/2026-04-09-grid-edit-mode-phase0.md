# GridEditMode Phase 0 — 공통 클래스 추출 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `infra_assets.js`의 기존 행 편집 모드 로직을 `GridEditMode` 클래스로 추출하고, 자산 그리드를 이 클래스의 첫 번째 소비자로 리팩토링한다.

**Architecture:** 새 파일 `grid_edit_mode.js`에 GridEditMode 클래스를 정의한다. 이 클래스는 dirty tracking, validation, 상태바, bulk apply UI를 소유한다. 자산 그리드는 인스턴스를 생성하고, 신규 행/paste 후처리/도메인 고유 저장은 기존 코드에 유지한다. save()/cancel()은 toggle하지 않으며 래퍼가 전체 흐름을 제어한다.

**Tech Stack:** Vanilla JS (ES6 class), AG Grid Community, 기존 `apiFetch()`/`showToast()` 유틸리티

**Spec:** `docs/superpowers/specs/2026-04-09-grid-edit-mode-phase0-design.md` (v2)

---

## 파일 구조

| 파일 | 역할 | 변경 |
|---|---|---|
| `app/static/js/grid_edit_mode.js` | GridEditMode 클래스 | 신규 |
| `app/static/js/infra_assets.js` | 자산 그리드 — 편집 모드를 GridEditMode 호출로 교체 | 수정 |
| `app/modules/infra/templates/infra_assets.html` | script 태그 추가 + bulk apply 하드코딩 HTML 제거 | 수정 |

---

## Task 1: GridEditMode 클래스 — 상태 관리 + toggle

GridEditMode의 핵심 뼈대: 내부 상태, 생성자, toggle, 버튼 show/hide.

**Files:**
- Create: `app/static/js/grid_edit_mode.js`

- [ ] **Step 1: 클래스 뼈대 + 생성자 작성**

```javascript
// app/static/js/grid_edit_mode.js

/**
 * GridEditMode — 기존 행의 dirty 편집을 관리하는 공통 클래스.
 * 신규 행 생명주기, paste 후처리, 도메인 고유 저장은 범위 밖.
 *
 * @param {Object} config
 * @param {Object} config.gridApi - AG Grid API 인스턴스
 * @param {Set<string>} config.editableFields - 편집 가능 필드 이름
 * @param {string|Function} config.bulkEndpoint - PATCH 엔드포인트 (문자열 또는 함수)
 * @param {Set<string>} [config.requiredFields] - 필수 필드
 * @param {Object} [config.validators] - {field: (value, rowData) => errorMsg|null}
 * @param {Function} [config.normalizeChange] - 셀 값 정규화 훅
 * @param {Array} [config.bulkApplyFields] - bulk apply 필드 설정
 * @param {Object} [config.selectors] - UI 요소 셀렉터
 * @param {string} [config.prefix] - 동적 요소 ID prefix
 * @param {Function} [config.onBeforeSave] - PATCH payload 변환
 * @param {Function} [config.onAfterSave] - 저장 완료 콜백
 * @param {Function} [config.onModeChange] - 모드 변경 콜백
 */
class GridEditMode {
  constructor(config) {
    this.gridApi = config.gridApi;
    this.editableFields = config.editableFields;
    this.bulkEndpoint = config.bulkEndpoint;
    this.requiredFields = config.requiredFields || new Set();
    this.validators = config.validators || {};
    this.normalizeChange = config.normalizeChange || null;
    this.bulkApplyFields = config.bulkApplyFields || [];
    this.selectors = config.selectors || {};
    this.prefix = config.prefix || "gem";
    this.onBeforeSave = config.onBeforeSave || null;
    this.onAfterSave = config.onAfterSave || null;
    this.onModeChange = config.onModeChange || null;

    // 내부 상태
    this._active = false;
    this._dirtyRows = new Map();
    this._originalValues = new Map();
    this._errorCells = new Map();

    // UI 바인딩
    this._bindToggleButton();
    if (this.bulkApplyFields.length && this.selectors.bulkContainer) {
      this._buildBulkApplyUI(document.querySelector(this.selectors.bulkContainer));
    }
    // selectionChanged → bulk UI 갱신
    this.gridApi.addEventListener("selectionChanged", () => this._updateBulkSelectionUI());
  }
```

- [ ] **Step 2: toggle() 메서드 작성**

```javascript
  isActive() {
    return this._active;
  }

  toggle(force) {
    this._active = force !== undefined ? force : !this._active;
    document.body.classList.toggle("edit-mode-active", this._active);

    const toggleBtn = this.selectors.toggleBtn
      ? document.querySelector(this.selectors.toggleBtn) : null;
    const saveBtn = this.selectors.saveBtn
      ? document.querySelector(this.selectors.saveBtn) : null;
    const cancelBtn = this.selectors.cancelBtn
      ? document.querySelector(this.selectors.cancelBtn) : null;
    const statusBar = this.selectors.statusBar
      ? document.querySelector(this.selectors.statusBar) : null;

    if (this._active) {
      if (toggleBtn) toggleBtn.classList.add("is-hidden");
      if (saveBtn) saveBtn.classList.remove("is-hidden");
      if (cancelBtn) cancelBtn.classList.remove("is-hidden");
      if (statusBar) statusBar.classList.remove("is-hidden");
      this._populateBulkSelects();
    } else {
      if (toggleBtn) toggleBtn.classList.remove("is-hidden");
      if (saveBtn) saveBtn.classList.add("is-hidden");
      if (cancelBtn) cancelBtn.classList.add("is-hidden");
      if (statusBar) statusBar.classList.add("is-hidden");
      this.gridApi.deselectAll();
    }

    if (this.onModeChange) this.onModeChange(this._active);
    this._updateStatusBar();
    this._updateBulkSelectionUI();
    this.gridApi.refreshCells({ force: true });
  }
```

- [ ] **Step 3: _bindToggleButton() 작성**

```javascript
  _bindToggleButton() {
    const toggleBtn = this.selectors.toggleBtn
      ? document.querySelector(this.selectors.toggleBtn) : null;
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggle());
    }
  }
```

- [ ] **Step 4: 파일 끝 — 클래스 닫기**

파일 맨 끝에:
```javascript
} // class GridEditMode 끝
```

- [ ] **Step 5: 구문 확인**

```bash
node -c app/static/js/grid_edit_mode.js
```
Expected: 오류 없음.

- [ ] **Step 6: Commit**

```bash
git add app/static/js/grid_edit_mode.js
git commit -m "feat: GridEditMode class skeleton — state, constructor, toggle"
```

---

## Task 2: GridEditMode — dirty tracking + validation

`markDirty`, `isDirty`, `validateCell`, `getCellError`, `hasErrors`, `getCellClass`.

**Files:**
- Modify: `app/static/js/grid_edit_mode.js`

- [ ] **Step 1: markDirty() + isDirty() 작성**

`_bindToggleButton()` 뒤, 클래스 닫기 `}` 전에 추가:

```javascript
  markDirty(rowId, field, newValue, oldValue) {
    if (!rowId) return;
    if (!this._dirtyRows.has(rowId)) this._dirtyRows.set(rowId, {});
    if (!this._originalValues.has(rowId)) this._originalValues.set(rowId, {});
    const dirty = this._dirtyRows.get(rowId);
    const originals = this._originalValues.get(rowId);
    if (!(field in originals)) originals[field] = oldValue;
    if (newValue === originals[field]) {
      delete dirty[field];
      if (Object.keys(dirty).length === 0) {
        this._dirtyRows.delete(rowId);
        this._originalValues.delete(rowId);
      }
    } else {
      dirty[field] = newValue;
    }
    this.validateCell(rowId, field, newValue);
    this._updateStatusBar();
  }

  isDirty(rowId, field) {
    const d = this._dirtyRows.get(rowId);
    return d ? field in d : false;
  }
```

- [ ] **Step 2: validateCell(), hasErrors(), getCellError() 작성**

```javascript
  hasErrors() {
    return this._errorCells.size > 0;
  }

  validateCell(rowId, field, value) {
    const key = `${rowId}:${field}`;
    if (this.requiredFields.has(field) && (!value || !String(value).trim())) {
      this._errorCells.set(key, "필수값입니다");
      return false;
    }
    const validator = this.validators[field];
    if (validator) {
      let rowData = null;
      this.gridApi.forEachNode((n) => { if (n.data?.id === rowId) rowData = n.data; });
      const error = validator(value, rowData);
      if (error) {
        this._errorCells.set(key, error);
        return false;
      }
    }
    this._errorCells.delete(key);
    return true;
  }

  getCellError(rowId, field) {
    return this._errorCells.get(`${rowId}:${field}`) || null;
  }
```

- [ ] **Step 3: getCellClass(params) 작성**

```javascript
  getCellClass(params) {
    const { data, colDef } = params;
    const field = colDef?.field;
    if (!field || !this._active) return [];

    const rowId = data?.id;
    if (!this.editableFields.has(field)) return ["infra-cell-readonly"];
    if (!rowId) return [];

    const classes = [];
    if (this.isDirty(rowId, field)) classes.push("infra-cell-dirty");
    if (this.getCellError(rowId, field)) classes.push("infra-cell-error");
    return classes;
  }
```

- [ ] **Step 4: getDirtyCount(), getErrorCount(), reset() 작성**

```javascript
  getDirtyCount() {
    return this._dirtyRows.size;
  }

  getErrorCount() {
    return this._errorCells.size;
  }

  reset() {
    this._dirtyRows.clear();
    this._originalValues.clear();
    this._errorCells.clear();
    this._updateStatusBar();
  }
```

- [ ] **Step 5: 구문 확인**

```bash
node -c app/static/js/grid_edit_mode.js
```

- [ ] **Step 6: Commit**

```bash
git add app/static/js/grid_edit_mode.js
git commit -m "feat: GridEditMode dirty tracking, validation, getCellClass"
```

---

## Task 3: GridEditMode — handleCellChange + 상태바

**Files:**
- Modify: `app/static/js/grid_edit_mode.js`

- [ ] **Step 1: handleCellChange() 작성**

```javascript
  handleCellChange(event) {
    const row = event?.data;
    if (!this._active) return false;
    if (!row?.id) return false;

    const field = event.colDef?.field;
    if (!field) return false;

    if (this.normalizeChange) {
      const result = this.normalizeChange(event);
      if (result === "reject") {
        row[field] = event.oldValue;
        this.gridApi.refreshCells({ rowNodes: [event.node], force: true });
        return false;
      }
      if (result) {
        if (result.rowMutations) Object.assign(row, result.rowMutations);
        for (const dc of result.dirtyChanges) {
          this.markDirty(row.id, dc.field, dc.value, dc.oldValue);
        }
        this.gridApi.refreshCells({ rowNodes: [event.node], force: true });
        return true;
      }
    }

    this.markDirty(row.id, field, event.newValue, event.oldValue);
    this.gridApi.refreshCells({ force: true });
    return true;
  }
```

- [ ] **Step 2: _updateStatusBar() 작성**

```javascript
  _updateStatusBar() {
    const countEl = this.selectors.changeCount
      ? document.querySelector(this.selectors.changeCount) : null;
    const errorsEl = this.selectors.errorCount
      ? document.querySelector(this.selectors.errorCount) : null;
    const saveBtn = this.selectors.saveBtn
      ? document.querySelector(this.selectors.saveBtn) : null;

    if (countEl) countEl.textContent = `변경 ${this._dirtyRows.size}건`;
    if (errorsEl) {
      const errCount = this._errorCells.size;
      errorsEl.textContent = `오류 ${errCount}건`;
      errorsEl.classList.toggle("is-hidden", errCount === 0);
    }
    if (saveBtn) saveBtn.disabled = this.hasErrors();
  }
```

- [ ] **Step 3: 구문 확인**

```bash
node -c app/static/js/grid_edit_mode.js
```

- [ ] **Step 4: Commit**

```bash
git add app/static/js/grid_edit_mode.js
git commit -m "feat: GridEditMode handleCellChange + status bar"
```

---

## Task 4: GridEditMode — save() + cancel()

**Files:**
- Modify: `app/static/js/grid_edit_mode.js`

- [ ] **Step 1: save() 작성**

```javascript
  async save() {
    if (this.hasErrors()) {
      showToast("검증 오류가 있어 저장할 수 없습니다.", "warning");
      return { success: false, count: 0 };
    }

    if (this._dirtyRows.size === 0) {
      return { success: true, count: 0 };
    }

    const items = [];
    for (const [rowId, changes] of this._dirtyRows) {
      items.push({ id: rowId, changes });
    }

    const payload = this.onBeforeSave ? this.onBeforeSave(items) : items;

    const endpoint = typeof this.bulkEndpoint === "function"
      ? this.bulkEndpoint()
      : this.bulkEndpoint;

    try {
      const results = await apiFetch(endpoint, {
        method: "PATCH",
        body: { items: payload },
      });

      for (const updated of results) {
        this._dirtyRows.delete(updated.id);
        this._originalValues.delete(updated.id);
        for (const key of [...this._errorCells.keys()]) {
          if (key.startsWith(`${updated.id}:`)) this._errorCells.delete(key);
        }
      }

      if (this.onAfterSave) this.onAfterSave(results);
      this._updateStatusBar();
      this.gridApi.refreshCells({ force: true });

      return { success: true, count: results.length };
    } catch (err) {
      showToast("저장 실패: " + err.message, "error");
      return { success: false, count: 0 };
    }
  }
```

- [ ] **Step 2: cancel() 작성**

```javascript
  cancel() {
    for (const [rowId, originals] of this._originalValues) {
      let node = null;
      this.gridApi.forEachNode((n) => { if (n.data?.id === rowId) node = n; });
      if (node) {
        for (const [field, value] of Object.entries(originals)) {
          node.data[field] = value;
        }
      }
    }
    this._dirtyRows.clear();
    this._originalValues.clear();
    this._errorCells.clear();
    this.gridApi.refreshCells({ force: true });
  }
```

- [ ] **Step 3: 구문 확인**

```bash
node -c app/static/js/grid_edit_mode.js
```

- [ ] **Step 4: Commit**

```bash
git add app/static/js/grid_edit_mode.js
git commit -m "feat: GridEditMode save (PATCH only) + cancel"
```

---

## Task 5: GridEditMode — bulk apply UI 동적 생성

**Files:**
- Modify: `app/static/js/grid_edit_mode.js`

- [ ] **Step 1: _buildBulkApplyUI() 작성**

```javascript
  _buildBulkApplyUI(container) {
    if (!container) return;
    container.replaceChildren();

    const label = document.createElement("label");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = `${this.prefix}-sel-all`;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        this.gridApi.selectAll();
      } else {
        this.gridApi.deselectAll();
      }
    });
    label.appendChild(checkbox);
    const countSpan = document.createElement("span");
    countSpan.id = `${this.prefix}-sel-count`;
    countSpan.textContent = " 선택";
    label.appendChild(countSpan);
    container.appendChild(label);

    for (const bf of this.bulkApplyFields) {
      const wrapper = document.createElement("label");
      wrapper.textContent = bf.label + " ";
      const sel = document.createElement("select");
      sel.className = "select-sm";
      sel.id = `${this.prefix}-bulk-${bf.field}`;
      sel.appendChild(new Option("--", ""));
      wrapper.appendChild(sel);
      container.appendChild(wrapper);
    }

    const btn = document.createElement("button");
    btn.className = "btn btn-primary btn-xs";
    btn.textContent = "선택 행에 적용";
    btn.addEventListener("click", () => this._applyBulkValues());
    container.appendChild(btn);
  }
```

- [ ] **Step 2: _populateBulkSelects() 작성**

```javascript
  _populateBulkSelects() {
    for (const bf of this.bulkApplyFields) {
      const sel = document.getElementById(`${this.prefix}-bulk-${bf.field}`);
      if (!sel) continue;
      const currentVal = sel.value;
      sel.replaceChildren();
      sel.appendChild(new Option("--", ""));
      const options = bf.options();
      for (const opt of options) {
        sel.appendChild(new Option(opt.label, opt.value));
      }
      sel.value = currentVal || "";
    }
  }
```

- [ ] **Step 3: _applyBulkValues() 작성**

```javascript
  _applyBulkValues() {
    const selected = this.gridApi.getSelectedNodes().filter((n) => n.data);
    if (!selected.length) {
      showToast("행을 먼저 선택하세요.", "warning");
      return;
    }

    const valuesToApply = [];
    for (const bf of this.bulkApplyFields) {
      const sel = document.getElementById(`${this.prefix}-bulk-${bf.field}`);
      const val = sel?.value;
      if (val) valuesToApply.push({ field: bf.field, value: val });
    }

    if (!valuesToApply.length) {
      showToast("적용할 값을 선택하세요.", "warning");
      return;
    }

    let count = 0;
    for (const node of selected) {
      const d = node.data;
      for (const { field, value } of valuesToApply) {
        const old = d[field];
        const coerced = (typeof old === "number") ? Number(value) : value;
        d[field] = coerced;
        if (d.id) this.markDirty(d.id, field, coerced, old);
      }
      count++;
    }

    for (const bf of this.bulkApplyFields) {
      const sel = document.getElementById(`${this.prefix}-bulk-${bf.field}`);
      if (sel) sel.value = "";
    }

    this.gridApi.refreshCells({ force: true });
    this._updateStatusBar();
    showToast(`${count}행에 일괄 적용됨`);
  }
```

- [ ] **Step 4: _updateBulkSelectionUI() 작성**

```javascript
  _updateBulkSelectionUI() {
    const container = this.selectors.bulkContainer
      ? document.querySelector(this.selectors.bulkContainer) : null;
    const countEl = document.getElementById(`${this.prefix}-sel-count`);
    if (!container) return;

    const agSelected = this.gridApi.getSelectedNodes().length;
    let chkSelected = 0;
    this.gridApi.forEachNode((n) => { if (n.data?._selected) chkSelected++; });
    const selCount = Math.max(agSelected, chkSelected);

    if (this._active && selCount > 0) {
      container.classList.remove("is-hidden");
      if (countEl) countEl.textContent = ` ${selCount}행 선택`;
    } else {
      container.classList.add("is-hidden");
    }
  }
```

- [ ] **Step 5: 구문 확인**

```bash
node -c app/static/js/grid_edit_mode.js
```

- [ ] **Step 6: Commit**

```bash
git add app/static/js/grid_edit_mode.js
git commit -m "feat: GridEditMode bulk apply UI dynamic generation"
```

---

## Task 6: infra_assets.html — script 태그 추가 + bulk apply HTML 제거

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html`

- [ ] **Step 1: script 태그에 grid_edit_mode.js 추가**

현재 (line 532-535):
```html
{% block scripts %}
<script src="/static/js/modal_combobox.js"></script>
<script src="/static/js/infra_assets.js"></script>
{% endblock %}
```

변경:
```html
{% block scripts %}
<script src="/static/js/modal_combobox.js"></script>
<script src="/static/js/grid_edit_mode.js"></script>
<script src="/static/js/infra_assets.js"></script>
{% endblock %}
```

- [ ] **Step 2: bulk apply 하드코딩 HTML 제거**

현재 (line 43-49):
```html
  <span class="edit-mode-selection is-hidden" id="edit-mode-selection">
    <span id="edit-mode-sel-count">0행 선택</span>
    <label>귀속프로젝트 <select id="bulk-period-id" class="select-sm"><option value="">--</option></select></label>
    <label>센터 <select id="bulk-center-id" class="select-sm"><option value="">--</option></select></label>
    <label>환경 <select id="bulk-environment" class="select-sm"><option value="">--</option></select></label>
    <label>상태 <select id="bulk-status" class="select-sm"><option value="">--</option></select></label>
    <button class="btn btn-primary btn-xs" id="btn-bulk-apply">선택 행에 적용</button>
  </span>
```

변경 — 빈 컨테이너만 남긴다 (GridEditMode가 동적 생성):
```html
  <span class="edit-mode-selection is-hidden" id="edit-mode-selection"></span>
```

- [ ] **Step 3: Commit**

```bash
git add app/modules/infra/templates/infra_assets.html
git commit -m "feat: add grid_edit_mode.js script + remove hardcoded bulk HTML"
```

---

## Task 7: infra_assets.js — 편집 모드 인라인 코드 제거 + GridEditMode 인스턴스 연결

가장 큰 태스크. 자산 그리드의 인라인 편집 모드 코드를 GridEditMode 호출로 교체한다.

**Files:**
- Modify: `app/static/js/infra_assets.js`

- [ ] **Step 1: 인라인 상태 변수 + 함수 제거**

`infra_assets.js`에서 다음 코드를 제거한다:

- line 138: `let _editMode = false;`
- line 139-141: `_dirtyRows`, `_originalValues`, `_errorCells` 변수
- line 143: `REQUIRED_FIELDS` 상수
- line 145: `isEditMode()` 함수
- line 147-170: `toggleEditMode()` 함수
- line 172-189: `markDirty()` 함수
- line 191-194: `isDirty()` 함수
- line 196: `hasErrors()` 함수
- line 198-206: `validateCell()` 함수
- line 208-210: `getCellError()` 함수
- line 212-223: `_updateEditModeBar()` 함수
- line 225-264: `saveEditMode()` 함수
- line 266-279: `cancelEditMode()` 함수
- line 283-288: `_populateBulkSelects()` 함수
- line 290-304: `_populateSelectFromList()` 함수
- line 306-318: `_populateSelectFromEntries()` 함수
- line 321-340: `_updateBulkSelectionUI()` 함수 (첫 줄 ~ `if (_editMode && selCount > 0)` 블록 전체)
- line 341-389: `_applyBulkValues()` 함수

제거한 자리에 다음을 넣는다:

```javascript
/* ── Edit mode: GridEditMode 클래스로 이전됨 (grid_edit_mode.js) ── */
let editMode; // GridEditMode 인스턴스 — initGrid() 후 초기화
```

- [ ] **Step 2: normalizeChange 함수 + 래퍼 함수 추가**

제거한 자리 바로 아래에 추가:

```javascript
function assetNormalizeChange(event) {
  const field = event.colDef.field;
  if (field !== "model") return null;

  const val = event.newValue;
  if (!val || !val._catalogModelId) return "reject";

  return {
    rowMutations: {
      model_id: val._catalogModelId,
      vendor: val._catalogVendor || "",
      model: val._catalogName || val.display || "",
    },
    dirtyChanges: [
      { field: "model_id", value: val._catalogModelId, oldValue: event.data.model_id },
    ],
  };
}

async function assetSaveEditMode() {
  if (editMode.hasErrors()) {
    showToast("검증 오류가 있어 저장할 수 없습니다.", "warning");
    return;
  }

  const hadNewRows = _hasNewRows;
  if (_hasNewRows) {
    await saveNewAssets();
  }

  const result = await editMode.save();

  if (result.success && result.count === 0 && !_hasNewRows) {
    if (hadNewRows) {
      editMode.toggle(false);
    } else {
      showToast("변경사항이 없습니다.", "info");
      editMode.toggle(false);
    }
    return;
  }
  if (result.count === 0 && _hasNewRows) {
    showToast("저장되지 않은 신규 자산이 남아 있습니다. 필수값과 모델 선택을 확인하세요.", "warning");
    return;
  }
  if (result.success) {
    showToast(`${result.count}건 자산이 업데이트되었습니다.`);
    if (!_hasNewRows) editMode.toggle(false);
  }
}

function assetCancelEditMode() {
  editMode.cancel();

  const newNodes = [];
  gridApi.forEachNode((n) => { if (n.data._isNew) newNodes.push(n.data); });
  if (newNodes.length) {
    gridApi.applyTransaction({ remove: newNodes });
  }
  _hasNewRows = false;
  _updateNewRowIndicators();
  _updateDeleteButtonVisibility();

  editMode.toggle(false);
}
```

- [ ] **Step 3: getGridCellClass() 수정**

현재 (line 653-662):
```javascript
function getGridCellClass(field, row = null) {
  const classes = [];
  classes.push(GRID_EDITABLE_FIELDS.has(field) ? "infra-cell-editable" : "infra-cell-readonly");
  if (isRawFallbackField(field, row)) classes.push("infra-cell-rawtext");
  if (_editMode && row?.id) {
    if (isDirty(row.id, field)) classes.push("infra-cell-dirty");
    if (getCellError(row.id, field)) classes.push("infra-cell-error");
  }
  return classes.join(" ");
}
```

변경:
```javascript
function getGridCellClass(field, row = null) {
  const classes = [];
  classes.push(GRID_EDITABLE_FIELDS.has(field) ? "infra-cell-editable" : "infra-cell-readonly");
  if (isRawFallbackField(field, row)) classes.push("infra-cell-rawtext");
  if (editMode && editMode.isActive() && row?.id) {
    if (editMode.isDirty(row.id, field)) classes.push("infra-cell-dirty");
    if (editMode.getCellError(row.id, field)) classes.push("infra-cell-error");
  }
  return classes.join(" ");
}
```

- [ ] **Step 4: handleGridCellValueChanged() — 편집 모드 분기 교체**

현재 (line 1490-1510):
```javascript
  if (_editMode && row.id) {
    if (field === "model") {
      const val = event.newValue;
      if (!val || !val._catalogModelId) {
        row.model = event.oldValue;
        gridApi.refreshCells({ rowNodes: [event.node], force: true });
        return;
      }
      _rememberOriginalField(row.id, "model", event.oldValue);
      _rememberOriginalField(row.id, "vendor", row.vendor);
      _rememberOriginalField(row.id, "model_id", row.model_id);
      row.model_id = val._catalogModelId;
      row.vendor = val._catalogVendor || row.vendor || "";
      row.model = val._catalogName || val.display || row.model;
      markDirty(row.id, "model_id", row.model_id, _originalValues.get(row.id).model_id);
      gridApi.refreshCells({ rowNodes: [event.node], force: true });
      return;
    }
    markDirty(row.id, field, event.newValue, event.oldValue);
    gridApi.refreshCells({ force: true });
    return;
  }
```

변경:
```javascript
  if (editMode && editMode.isActive() && row.id) {
    editMode.handleCellChange(event);
    return;
  }
```

- [ ] **Step 5: onPaste 콜백 — markDirty 호출 교체**

현재 (line 1281):
```javascript
      if (!_editMode) {
```

변경:
```javascript
      if (!editMode || !editMode.isActive()) {
```

현재 (line 1349-1367):
```javascript
      if (_editMode) {
        for (const c of changes) {
          const node = gridApi.getDisplayedRowAtIndex(c.rowIndex);
          if (node?.data?.id && c.field !== "model") {
            markDirty(node.data.id, c.field, c.newValue, c.oldValue);
          } else if (node?.data?.id && c.field === "model" && node.data.model_id) {
            const original = modelOriginals.get(node.data.id) || {
              model: c.oldValue,
              vendor: node.data.vendor,
              model_id: null,
            };
            _rememberOriginalField(node.data.id, "model", original.model);
            _rememberOriginalField(node.data.id, "vendor", original.vendor);
            _rememberOriginalField(node.data.id, "model_id", original.model_id);
            markDirty(node.data.id, "model_id", node.data.model_id, original.model_id);
          }
        }
        _updateEditModeBar();
        gridApi.refreshCells({ force: true });
```

변경:
```javascript
      if (editMode && editMode.isActive()) {
        for (const c of changes) {
          const node = gridApi.getDisplayedRowAtIndex(c.rowIndex);
          if (node?.data?.id && c.field !== "model") {
            editMode.markDirty(node.data.id, c.field, c.newValue, c.oldValue);
          } else if (node?.data?.id && c.field === "model" && node.data.model_id) {
            const original = modelOriginals.get(node.data.id) || {};
            editMode.markDirty(node.data.id, "model_id", node.data.model_id, original.model_id ?? null);
          }
        }
        gridApi.refreshCells({ force: true });
```

- [ ] **Step 6: 선택 모드 분기 수정**

현재 (line 1239):
```javascript
      if (!_editMode) {
```

변경:
```javascript
      if (!editMode || !editMode.isActive()) {
```

- [ ] **Step 7: Ctrl+S 핸들러 수정**

현재 (line 1417-1418):
```javascript
      if (_editMode) saveEditMode();
```

변경:
```javascript
      if (editMode && editMode.isActive()) assetSaveEditMode();
```

- [ ] **Step 8: 이벤트 리스너 수정**

현재 (line 4338-4341):
```javascript
document.getElementById("btn-toggle-edit").addEventListener("click", () => toggleEditMode());
document.getElementById("btn-save-edit").addEventListener("click", saveEditMode);
document.getElementById("btn-cancel-edit").addEventListener("click", cancelEditMode);
document.getElementById("btn-bulk-apply").addEventListener("click", _applyBulkValues);
```

변경:
```javascript
// btn-toggle-edit: GridEditMode 생성자가 바인딩
document.getElementById("btn-save-edit").addEventListener("click", assetSaveEditMode);
document.getElementById("btn-cancel-edit").addEventListener("click", assetCancelEditMode);
// btn-bulk-apply: GridEditMode가 동적 생성 시 바인딩
```

- [ ] **Step 9: GridEditMode 인스턴스 생성 — gridApi 초기화 직후**

`agGrid.createGrid()` 호출 직후 (현재 line ~1249 부근, onSelectionChanged 다음)에 추가:

```javascript
  editMode = new GridEditMode({
    gridApi,
    editableFields: GRID_EDITABLE_FIELDS,
    bulkEndpoint: () => _assetPatchUrl("/api/v1/assets/bulk"),
    requiredFields: new Set(["asset_name"]),
    normalizeChange: assetNormalizeChange,
    prefix: "asset",

    onBeforeSave: (items) => items,

    onAfterSave: (results) => {
      for (const updated of results) {
        let node = null;
        gridApi.forEachNode((n) => { if (n.data?.id === updated.id) node = n; });
        if (node) applyAssetRowUpdate(node.data, updated);
      }
    },

    bulkApplyFields: [
      { field: "period_id", label: "귀속프로젝트", type: "select",
        options: () => _periodsCache.map((p) => ({
          value: p.id,
          label: p.contract_name || p.period_label || String(p.id),
        })),
      },
      { field: "center_id", label: "센터", type: "select",
        options: () => _layoutCentersCache.map((c) => ({
          value: c.id, label: c.center_name,
        })),
      },
      { field: "environment", label: "환경", type: "select",
        options: () => Object.entries(ENV_MAP).map(([v, l]) => ({
          value: v, label: l,
        })),
      },
      { field: "status", label: "상태", type: "select",
        options: () => Object.entries(ASSET_STATUS_MAP).map(([v, l]) => ({
          value: v, label: l,
        })),
      },
    ],

    selectors: {
      toggleBtn: "#btn-toggle-edit",
      saveBtn: "#btn-save-edit",
      cancelBtn: "#btn-cancel-edit",
      statusBar: "#edit-mode-bar",
      changeCount: "#edit-mode-count",
      errorCount: "#edit-mode-errors",
      bulkContainer: "#edit-mode-selection",
    },
  });
```

- [ ] **Step 10: _rememberOriginalField 호출 정리**

paste 콜백에서 `_rememberOriginalField()` 호출을 제거했으므로, 다른 곳에서 호출되는지 확인:

```bash
grep -n "_rememberOriginalField" app/static/js/infra_assets.js
```

호출이 없으면 함수 자체를 삭제한다. 호출이 남아있으면 유지.

- [ ] **Step 11: 구문 확인**

```bash
node -c app/static/js/infra_assets.js && node -c app/static/js/grid_edit_mode.js
```

- [ ] **Step 12: Commit**

```bash
git add app/static/js/infra_assets.js app/static/js/grid_edit_mode.js
git commit -m "refactor: asset grid uses GridEditMode — inline edit code removed"
```

---

## Task 8: 통합 검증

**Files:**
- 변경 없음 — 검증만

- [ ] **Step 1: pytest 실행**

```bash
cd /c/Users/JBM/Desktop/pjtmgr && python -m pytest tests/ -x -q
```

백엔드 변경 없으므로 기존 테스트 통과 확인.

- [ ] **Step 2: 서버 실행 + 브라우저 수동 검증**

서버를 실행하고 자산 그리드 페이지에서 아래 체크리스트를 수행한다.

**기본 편집:**

| # | 시나리오 | 조작 | 기대 결과 |
|---|---|---|---|
| 1 | 편집 모드 진입 | "편집" 버튼 클릭 | 편집→숨김, 저장/취소→표시, 상태바 표시, bulk apply 드롭다운 동적 생성 |
| 2 | 셀 수정 (기존 행) | asset_name 변경 | 파란 배경, "변경 1건" |
| 3 | 필수 필드 비우기 | asset_name 빈 값 | 빨간 배경, "오류 1건", 저장 disabled |
| 4 | 원래 값 복원 | asset_name 원래 값 | dirty 해제, 카운트 0 |
| 5 | model 수정 | 카탈로그에서 제품 선택 | model_id dirty, vendor/model 표시 갱신 |
| 6 | bulk apply | 3행 선택 → 환경 "prod" → "선택 행에 적용" | 3행 dirty |

**저장/취소:**

| # | 시나리오 | 조작 | 기대 결과 |
|---|---|---|---|
| 7 | 저장 (기존 행만) | 셀 수정 후 "저장" | PATCH 성공, 편집 모드 이탈 |
| 8 | 취소 | 셀 수정 후 "취소" | 원본 복원, 신규 행 제거, 편집 모드 이탈 |
| 9 | 신규 행 + 저장 | "+자산추가" → 값 입력 → "저장" | 신규 POST + dirty PATCH |
| 10 | 신규 행 실패 | model 미선택 신규 행 + "저장" | 경고 토스트, 편집 모드 유지 |

**Paste:**

| # | 시나리오 | 조작 | 기대 결과 |
|---|---|---|---|
| 11 | paste (기존 행) | 기존 행에 값 붙여넣기 | dirty 기록 |
| 12 | paste (model 필드) | model 텍스트 붙여넣기 | 카탈로그 자동매칭 → model_id dirty |
| 13 | paste (신규 행 생성) | 행 수 초과하는 데이터 붙여넣기 | 신규 행 생성, _hasNewRows |
| 14 | paste (비편집 모드) | 편집 모드 아닐 때 붙여넣기 | 원복 + 경고 토스트 |
| 15 | Ctrl+S | 편집 모드에서 Ctrl+S | assetSaveEditMode 호출 |
| 16 | Ctrl+Z | 붙여넣기 후 Ctrl+Z | undo 동작 |

- [ ] **Step 3: 검증 결과 기록**

각 시나리오의 통과/실패를 기록. 실패 시 즉시 수정.

- [ ] **Step 4: 수정이 있었다면 Commit**

```bash
git add -A
git commit -m "fix: GridEditMode integration fixes from manual testing"
```

---

## Task 9: 정리 + 문서 갱신

**Files:**
- Modify: `docs/superpowers/specs/2026-04-09-grid-edit-mode-phase0-design.md`
- Modify: `docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`

- [ ] **Step 1: Phase 0 설계 문서에 완료 상태 기록**

`docs/superpowers/specs/2026-04-09-grid-edit-mode-phase0-design.md`의 2번째 줄을 변경:

현재:
```
> 2026-04-09 | 상위 설계: `docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`
```

변경:
```
> 2026-04-09 | 상태: **Phase 0 완료** | 상위 설계: `docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`
```

- [ ] **Step 2: 상위 로드맵에 Phase 0 완료 기록**

`docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`의 Phase 개요 테이블에서 Phase 0 행:

현재:
```
| **0** | `GridEditMode` 공통 클래스 추출 + 자산 그리드 리팩토링 | 기반 작업 | 지침 재검토 후 |
```

변경:
```
| **0** | `GridEditMode` 공통 클래스 추출 + 자산 그리드 리팩토링 | 기반 작업 | **완료** |
```

- [ ] **Step 3: 사용하지 않는 헬퍼 정리**

```bash
grep -n "_rememberOriginalField\|_populateSelectFromList\|_populateSelectFromEntries" app/static/js/infra_assets.js
```

호출이 없는 함수는 삭제한다.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "docs: mark Phase 0 complete + cleanup unused helpers"
```
