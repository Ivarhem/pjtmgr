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

  // ── Stubs (implemented in later tasks) ────────────────────────────────────

  /** Task 3: 상태바 텍스트 갱신 */
  _updateStatusBar() {}

  /** Task 5: bulk apply UI DOM 구성 */
  _buildBulkApplyUI(container) {}

  /** Task 5: bulk apply <select> 옵션 채우기 */
  _populateBulkSelects() {}

  /** Task 5: 선택 행 수에 따라 bulk apply 버튼 활성화 */
  _updateBulkSelectionUI() {}

} // class GridEditMode 끝
