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

  _bindToggleButton() {
    const toggleBtn = this.selectors.toggleBtn
      ? document.querySelector(this.selectors.toggleBtn) : null;
    if (toggleBtn) {
      toggleBtn.addEventListener("click", () => this.toggle());
    }
  }

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

  // ── Stubs (implemented in later tasks) ────────────────────────────────────

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

  /** Task 5: bulk apply UI DOM 구성 */
  _buildBulkApplyUI(container) {}

  /** Task 5: bulk apply <select> 옵션 채우기 */
  _populateBulkSelects() {}

  /** Task 5: 선택 행 수에 따라 bulk apply 버튼 활성화 */
  _updateBulkSelectionUI() {}

} // class GridEditMode 끝
