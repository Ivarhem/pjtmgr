# GridEditMode Phase 0 — 공통 클래스 추출 상세 설계

> 2026-04-09 | 상위 설계: `docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`

---

## 1. 목적

`infra_assets.js`에 인라인으로 존재하는 편집 모드 로직(~300줄)을 `GridEditMode` 클래스로 추출한다.
자산 그리드를 이 클래스의 첫 번째 소비자로 리팩토링하여, Phase 1 이후 다른 그리드에서 인스턴스만 생성하면 편집 모드를 사용할 수 있게 한다.

**전략:** Big Bang 추출 — 중간 상태 없이 한 번에 추출 + 자산 그리드 교체.

---

## 2. 파일 구조

| 파일 | 역할 | 변경 유형 |
|---|---|---|
| `app/static/js/grid_edit_mode.js` | GridEditMode 클래스 | 신규 생성 |
| `app/static/js/infra_assets.js` | 자산 그리드 — 편집 모드 로직을 GridEditMode 호출로 교체 | 수정 |
| `app/modules/infra/templates/infra_assets.html` | `<script>` 태그에 grid_edit_mode.js 추가, bulk apply HTML 제거 (동적 생성으로 대체) | 수정 |
| `app/static/css/infra_common.css` | 변경 없음 (기존 dirty/error/readonly 스타일 그대로 사용) | 무변경 |
| 백엔드 | 변경 없음 (기존 bulk API 그대로 사용) | 무변경 |

---

## 3. GridEditMode 클래스 설계

### 3.1 config 객체

```javascript
new GridEditMode({
  // ── 필수 ──
  gridApi,                          // AG Grid API 인스턴스
  editableFields: Set,              // 편집 가능 필드 이름 집합
  bulkEndpoint: "/api/v1/assets/bulk",  // PATCH 엔드포인트

  // ── 선택: 검증 ──
  requiredFields: Set,              // 빈 값 허용 불가 필드
  validators: {                     // 필드별 커스텀 검증
    fieldName: (value, rowData) => errorMsg | null,
  },

  // ── 선택: 셀 값 정규화 ──
  // FK+표시값 복합 필드 변환 (예: model 셀 → model_id + vendor + model)
  // 반환: null(기본 동작) | "reject"(입력 거부) | { dirtyChanges, rowMutations }
  normalizeChange: (event) => null,

  // ── 선택: 신규 행 ──
  // GridEditMode는 신규 행을 직접 관리하지 않음.
  // save() 시 이 훅을 먼저 호출, 결과에 따라 편집 모드 유지/이탈 결정.
  saveNewItems: async (gridApi) => ({ saved: number, remaining: boolean }),

  // ── 선택: bulk apply ──
  bulkApplyFields: [
    { field: "status", label: "상태", type: "select",
      options: () => [{ value: "active", label: "활성" }, ...] },
  ],

  // ── 선택: UI 셀렉터 ──
  selectors: {
    toggleBtn: "#btn-toggle-edit",
    saveBtn: "#btn-save-edit",
    cancelBtn: "#btn-cancel-edit",
    statusBar: "#edit-mode-bar",
    changeCount: "#edit-mode-count",
    errorCount: "#edit-mode-errors",
    bulkContainer: "#edit-mode-selection",  // bulk apply UI가 렌더링될 컨테이너
  },

  // ── 선택: 다중 인스턴스 ──
  prefix: "asset",                  // 동적 생성 요소 ID prefix (기본: "gem")

  // ── 선택: 콜백 ──
  onBeforeSave: (items) => items,   // PATCH payload 변환
  onAfterSave: (results) => void,   // 저장 완료 후 처리 (예: 행 데이터 갱신)
  onBeforeCancel: () => void,       // 취소 전 도메인별 정리 (예: 신규 행 상태 리셋)
  onModeChange: (isActive) => void, // 편집 모드 진입/이탈 시
})
```

### 3.2 내부 상태

```javascript
_active          // boolean — 편집 모드 활성 여부
_dirtyRows       // Map<rowId, {field: newValue}> — 변경 추적
_originalValues  // Map<rowId, {field: originalValue}> — 원본 백업
_errorCells      // Map<"rowId:field", errorMessage> — 검증 오류
```

### 3.3 공개 API

| 메서드 | 설명 |
|---|---|
| `isActive()` | 편집 모드 활성 여부 반환 |
| `toggle(force?)` | 편집 모드 진입/이탈 |
| `markDirty(rowId, field, newValue, oldValue)` | 셀 변경 기록. 원본 복원 시 dirty 자동 제거 |
| `isDirty(rowId, field)` | 특정 셀의 dirty 여부 |
| `hasErrors()` | 검증 오류 존재 여부 |
| `validateCell(rowId, field, value)` | 필수 필드 + 커스텀 validator 실행 |
| `getCellError(rowId, field)` | 특정 셀의 오류 메시지 |
| `getCellClass(params)` | AG Grid cellClass 콜백용 — dirty/error/readonly 클래스 반환 |
| `handleCellChange(event)` | onCellValueChanged 핸들러 — normalizeChange → markDirty |
| `async save()` | saveNewItems → dirty 수집 → PATCH → 부분 성공 지원 |
| `cancel()` | originalValues로 복원 → 상태 초기화 |
| `getDirtyCount()` | 변경된 행 수 |
| `getErrorCount()` | 오류 셀 수 |

### 3.4 내부 메서드

| 메서드 | 설명 |
|---|---|
| `_updateStatusBar()` | 변경 N건 / 오류 N건 갱신, 저장 버튼 disabled 토글 |
| `_buildBulkApplyUI(container)` | bulkApplyFields 기반 드롭다운 동적 생성 |
| `_populateBulkSelects()` | toggle(true) 시 옵션 목록 갱신 |
| `_applyBulkValues()` | 선택 행에 일괄 값 적용 → markDirty 호출 |
| `_updateBulkSelectionUI()` | 선택 행 수 표시, 선택 없으면 bulk 패널 숨김 |
| `_bindButtons()` | selectors 기반 이벤트 리스너 등록 |

---

## 4. 핵심 메서드 상세

### 4.1 handleCellChange(event)

`onCellValueChanged`에서 호출. 편집 모드에서 기존 행의 변경만 처리한다.

```
handleCellChange(event):
  1. _active가 false이거나 row.id가 없으면 → return false (신규 행/비편집 모드)
  2. normalizeChange 훅이 있으면 호출:
     - "reject" → 원래 값 복원, return false
     - { dirtyChanges, rowMutations } → row에 mutations 적용, 각 change를 markDirty
     - null → 기본 동작으로 fall through
  3. 기본 동작: markDirty(rowId, field, newValue, oldValue)
  4. gridApi.refreshCells() → return true
```

### 4.2 save()

```
save():
  1. hasErrors() → showToast("검증 오류") + return
  
  2. saveNewItems 훅이 있으면 호출:
     → { saved, remaining } 반환
     → remaining이 true면 신규 행이 아직 남아 있음
  
  3. _dirtyRows 수집 → items = [{id, changes}]
     → items가 비어있으면:
        - saveNewItems가 성공했고 remaining false → toggle(false) + return
        - remaining true → "저장되지 않은 신규 항목이 있습니다" 토스트 + return
        - saveNewItems 없었으면 → "변경사항 없음" 토스트 + toggle(false) + return
  
  4. onBeforeSave(items) → 변환된 payload
  
  5. PATCH bulkEndpoint 호출
     → 성공 시: 성공한 행을 _dirtyRows에서 제거
     → 실패 시: 실패한 행은 dirty 유지 (부분 성공 지원)
  
  6. onAfterSave(results)
  
  7. _dirtyRows가 모두 비고 + remaining !== true → toggle(false)
     → 아니면 편집 모드 유지 + _updateStatusBar()
```

### 4.3 cancel()

```
cancel():
  1. _originalValues 순회 → 각 행의 원래 값 복원
  2. _dirtyRows, _originalValues, _errorCells 초기화
  3. onBeforeCancel 훅이 있으면 호출 (도메인별 정리, 예: _hasNewRows 리셋)
  4. toggle(false)
  5. gridApi.refreshCells({ force: true })
```

### 4.4 getCellClass(params)

```
getCellClass(params):
  1. _active가 false → return []
  2. field가 editableFields에 없으면 → return ["infra-cell-readonly"]
  3. isDirty(rowId, field) → "infra-cell-dirty" 추가
  4. getCellError(rowId, field) → "infra-cell-error" 추가
  5. return classes 배열
```

각 그리드가 컬럼 정의의 cellClass에서 이 메서드를 호출하고, 도메인 고유 스타일과 합성할 수 있다.

### 4.5 toggle(force?)

```
toggle(force):
  1. _active = force ?? !_active
  2. document.body.classList.toggle("edit-mode-active", _active)
  3. toggleBtn/saveBtn/cancelBtn show/hide 전환
  4. statusBar show/hide 전환
  5. _active가 true면:
     - _populateBulkSelects()
  6. _active가 false면:
     - gridApi.deselectAll()
  7. onModeChange(_active) 콜백
  8. _updateStatusBar()
  9. _updateBulkSelectionUI()
  10. gridApi.refreshCells({ force: true })
```

---

## 5. Bulk Apply UI 동적 생성

### 5.1 _buildBulkApplyUI(container)

생성자에서 `bulkApplyFields`가 있고 `selectors.bulkContainer`가 있으면 호출.

생성되는 DOM 구조:
```html
<label>
  <input type="checkbox" id="{prefix}-sel-all">
  <span id="{prefix}-sel-count">선택</span>
</label>
<select class="select-sm" id="{prefix}-bulk-{field}">
  <option value="">{label}</option>
</select>
<!-- ... 각 bulkApplyField마다 반복 ... -->
<button class="btn btn-sm">일괄 적용</button>
```

### 5.2 _applyBulkValues()

```
_applyBulkValues():
  1. gridApi.getSelectedNodes() → 선택된 행
  2. 없으면 → showToast("행을 먼저 선택하세요")
  3. 각 bulkApplyField의 select 값 읽기
  4. 모두 비어있으면 → showToast("적용할 값을 선택하세요")
  5. 선택된 행 순회:
     - 값이 있는 필드마다 row.data[field] = value
     - row.id가 있으면 markDirty(row.id, field, value, oldValue)
  6. select 값 초기화
  7. gridApi.refreshCells({ force: true })
  8. showToast("N행에 일괄 적용됨")
```

---

## 6. 이벤트 바인딩

### 6.1 생성자에서 자동 바인딩

| 대상 | 이벤트 | 동작 |
|---|---|---|
| `selectors.toggleBtn` | click | `toggle()` |
| `selectors.saveBtn` | click | `save()` |
| `selectors.cancelBtn` | click | `cancel()` |
| gridApi | selectionChanged | `_updateBulkSelectionUI()` |

### 6.2 각 그리드가 연결하는 이벤트

| 이벤트 | 연결 방식 |
|---|---|
| `onCellValueChanged` | 그리드의 기존 핸들러에서 `editMode.handleCellChange(event)` 호출 |
| copy/paste | 기존 `addCopyPasteHandler()` 그대로 사용. paste → AG Grid setValue → onCellValueChanged → handleCellChange |

copy/paste와 GridEditMode는 독립적. `onCellValueChanged`가 유일한 연결점 (느슨한 결합).

---

## 7. 자산 그리드 리팩토링

### 7.1 제거 대상 (infra_assets.js에서)

| 현재 코드 | 대체 |
|---|---|
| `_editMode`, `_dirtyRows`, `_originalValues`, `_errorCells` 변수 | GridEditMode 내부 상태 |
| `toggleEditMode()`, `markDirty()`, `isDirty()` 등 함수 | GridEditMode 메서드 |
| `validateCell()`, `hasErrors()`, `getCellError()` | GridEditMode 메서드 |
| `_updateEditModeBar()` | GridEditMode `_updateStatusBar()` |
| `_populateBulkSelects()`, `_applyBulkValues()` | GridEditMode bulk apply |
| `saveEditMode()` 중 dirty 수집 + PATCH 호출 부분 | GridEditMode `save()` |
| `cancelEditMode()` 중 원본 복원 + 초기화 | GridEditMode `cancel()` |
| `_updateBulkSelectionUI()` | GridEditMode `_updateBulkSelectionUI()` |

### 7.2 유지 대상 (infra_assets.js에 남는 것)

| 코드 | 이유 |
|---|---|
| `addAssetRow()` | 도메인 고유 — 신규 행 기본값, `_isNew` 플래그 |
| `saveNewAssets()` | 도메인 고유 — POST + 역할 자동 생성/할당. `saveNewItems` 훅으로 연결 |
| `deleteSelectedAssets()` | 도메인 고유 — DELETE API + 신규/기존 분기 |
| `handleGridCellValueChanged()` | 도메인 고유 분기 (신규 행, 비편집 모드 즉시 저장) 후 `editMode.handleCellChange()` 위임 |
| `applyAssetRowUpdate()` | 도메인 고유 — 서버 응답을 행 데이터에 매핑. `onAfterSave`에서 호출 |
| `_rememberOriginalField()` | 삭제 가능 — `handleCellChange`의 `normalizeChange`가 대체 |
| `CatalogCellEditor` | 도메인 고유 — 카탈로그 검색 에디터 |

### 7.3 normalizeChange 구현 (자산 그리드)

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
      { field: "vendor", value: val._catalogVendor || "", oldValue: event.data.vendor },
    ],
  };
}
```

### 7.4 GridEditMode 인스턴스 생성 (자산 그리드)

```javascript
const editMode = new GridEditMode({
  gridApi,
  editableFields: EDITABLE_FIELDS,
  bulkEndpoint: "/api/v1/assets/bulk",
  requiredFields: new Set(["asset_name"]),
  normalizeChange: assetNormalizeChange,
  prefix: "asset",

  saveNewItems: async (api) => {
    await saveNewAssets();
    let remaining = false;
    api.forEachNode(n => { if (n.data._isNew) remaining = true; });
    return { saved: 0 /* saveNewAssets가 successCount를 반환하도록 리팩토링 */, remaining };
  },

  onAfterSave: (results) => {
    for (const updated of results) {
      let node = null;
      gridApi.forEachNode(n => { if (n.data?.id === updated.id) node = n; });
      if (node) applyAssetRowUpdate(node.data, updated);
    }
  },

  onBeforeSave: (items) => items,

  bulkApplyFields: [
    { field: "period_id", label: "계약기간", type: "select",
      options: () => _periodsCache.map(p => ({
        value: p.id, label: p.contract_name || p.period_label || String(p.id),
      })),
    },
    { field: "center_id", label: "센터", type: "select",
      options: () => _layoutCentersCache.map(c => ({ value: c.id, label: c.center_name })),
    },
    { field: "environment", label: "환경", type: "select",
      options: () => Object.entries(ENV_MAP).map(([v, l]) => ({ value: v, label: l })),
    },
    { field: "status", label: "상태", type: "select",
      options: () => Object.entries(ASSET_STATUS_MAP).map(([v, l]) => ({ value: v, label: l })),
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

---

## 8. 검증 전략

### 8.1 자동 검증

- `pytest` — 백엔드 변경 없으므로 기존 테스트 통과 확인만

### 8.2 수동 체크리스트 (브라우저)

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | 편집 모드 진입 | 토글/저장/취소 버튼 전환, 상태바 표시, bulk apply UI 생성 |
| 2 | 셀 수정 | dirty 셀 파란 배경, 상태바 "변경 N건" 갱신 |
| 3 | 필수 필드 비우기 | error 셀 빨간 배경, "오류 N건" 표시, 저장 버튼 disabled |
| 4 | 원래 값으로 되돌리기 | dirty 자동 해제 |
| 5 | model 셀 수정 (카탈로그 선택) | model_id + vendor 동시 dirty 기록 |
| 6 | model 셀 잘못된 입력 | "reject" — 원래 값 복원 |
| 7 | bulk apply (행 선택 → 값 일괄 적용) | 선택된 행에 값 적용, dirty 기록 |
| 8 | 저장 (기존 행만) | PATCH /bulk → 성공 → 편집 모드 이탈 |
| 9 | 저장 (기존 행 + 신규 행) | saveNewItems → PATCH /bulk → 모두 성공 시 이탈 |
| 10 | 저장 (신규 행 일부 실패) | 실패 행 _isNew 유지, 편집 모드 유지 |
| 11 | 취소 | 모든 셀 원본 복원, dirty/error 초기화 |
| 12 | copy/paste (기존 행) | paste → onCellValueChanged → dirty 기록 |
| 13 | copy/paste (신규 행 자동 생성) | 신규 행 추가 → 편집 → saveNewItems로 저장 |
| 14 | Ctrl+Z (undo) | paste 전 상태로 복원 |

---

## 9. 비변경 사항

- **백엔드:** 변경 없음. 기존 `PATCH /api/v1/assets/bulk`, `POST /api/v1/assets` 그대로.
- **CSS:** `infra_common.css`의 dirty/error/readonly 스타일 그대로 사용.
- **copy/paste:** `utils.js`의 `addCopyPasteHandler()` 변경 없음. 기존 동작 유지.
- **다른 그리드:** Phase 0에서는 자산 그리드만 리팩토링. 다른 그리드는 Phase 1 이후.
