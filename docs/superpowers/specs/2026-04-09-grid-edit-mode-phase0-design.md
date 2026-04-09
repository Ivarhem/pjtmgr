# GridEditMode Phase 0 — 공통 클래스 추출 상세 설계

> 2026-04-09 | 상태: **Phase 0 완료** | 상위 설계: `docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`
> v2 — 코덱스 리뷰 2차 반영: 범위 축소 + paste/신규행/cancel 경계 명확화

---

## 1. 목적과 범위

### 1.1 목적

`infra_assets.js`에 인라인으로 존재하는 **기존 행 편집 모드** 로직을 `GridEditMode` 클래스로 추출한다.
자산 그리드를 이 클래스의 첫 번째 소비자로 리팩토링하여, Phase 1 이후 다른 그리드에서 인스턴스만 생성하면 편집 모드를 사용할 수 있게 한다.

### 1.2 범위 (In Scope)

GridEditMode가 **소유**하는 것:

- dirty tracking: `_dirtyRows`, `_originalValues`, `_errorCells` 상태 관리
- 검증: 필수 필드 + 커스텀 validator
- 셀 스타일링: dirty/error/readonly CSS 클래스 반환
- 상태바: 변경 N건 / 오류 N건 갱신
- 버튼 토글: 편집/저장/취소 버튼 show/hide
- bulk apply: 선언 기반 드롭다운 UI 동적 생성 + 선택 행 일괄 적용
- 저장 (PATCH only): dirty rows 수집 → bulk API PATCH → 부분 성공 지원
- 취소: dirty 행 원본 복원 → 상태 초기화

### 1.3 범위 밖 (Out of Scope — 자산 도메인에 남는 것)

- **신규 행 생명주기**: `addAssetRow()`, `saveNewAssets()`, `_hasNewRows` 관리, `_isNew` 플래그
- **paste 후처리**: `onPaste` 콜백 내 모델 유사매칭, 신규 행 플래그 설정, 역할명 자동 세팅
- **신규 행 취소**: 그리드에서 신규 행 제거 또는 유지 결정
- **도메인 고유 셀 에디터**: `CatalogCellEditor`, `RoleCellEditor` 등
- **비편집 모드 즉시 저장**: `handleGridCellValueChanged()`의 즉시 PATCH 분기

### 1.4 경계 원칙

> **GridEditMode는 `id`가 있는 기존 행의 dirty 편집만 안다.**
> 신규 행(`!row.id`)은 GridEditMode의 관심 밖이다.
> 저장/취소 시 신규 행 처리는 자산 그리드의 **래퍼 함수**가 담당한다.

---

## 2. 파일 구조

| 파일 | 역할 | 변경 유형 |
|---|---|---|
| `app/static/js/grid_edit_mode.js` | GridEditMode 클래스 | 신규 생성 |
| `app/static/js/infra_assets.js` | 자산 그리드 — 편집 모드 로직을 GridEditMode 호출로 교체 | 수정 |
| `app/modules/infra/templates/infra_assets.html` | `<script>` 태그에 grid_edit_mode.js 추가, bulk apply 하드코딩 HTML 제거 (동적 생성으로 대체) | 수정 |
| `app/static/css/infra_common.css` | 변경 없음 | 무변경 |
| 백엔드 | 변경 없음 | 무변경 |

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
  // onCellValueChanged에서 handleCellChange()가 호출할 훅.
  // FK+표시값 복합 필드 변환 담당 (예: model 셀 → model_id dirty + vendor/model 표시값 갱신)
  // 반환: null(기본 동작) | "reject"(입력 거부) | { dirtyChanges, rowMutations }
  //   - dirtyChanges: [{field, value, oldValue}] — _dirtyRows에 적재할 필드 (서버 저장 대상)
  //   - rowMutations: {field: value} — row.data에 반영할 표시값 (dirty 적재 안 함)
  normalizeChange: (event) => null,

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
    bulkContainer: "#edit-mode-selection",
  },

  // ── 선택: 다중 인스턴스 ──
  prefix: "asset",                  // 동적 생성 요소 ID prefix (기본: "gem")

  // ── 선택: 콜백 ──
  onBeforeSave: (items) => items,   // PATCH payload 변환
  onAfterSave: (results) => void,   // PATCH 완료 후 처리 (예: 행 데이터 갱신)
  onModeChange: (isActive) => void, // 편집 모드 진입/이탈 시
})
```

**이전 버전에서 제거된 항목:**
- `saveNewItems` — GridEditMode는 신규 행을 모른다. 자산 래퍼가 처리.
- `onBeforeCancel` — 자산 래퍼의 `assetCancelEditMode()`에서 직접 처리.

### 3.2 내부 상태

```javascript
_active          // boolean — 편집 모드 활성 여부
_dirtyRows       // Map<rowId, {field: newValue}> — 변경 추적 (id가 있는 행만)
_originalValues  // Map<rowId, {field: originalValue}> — 원본 백업
_errorCells      // Map<"rowId:field", errorMessage> — 검증 오류
```

### 3.3 공개 API

| 메서드 | 설명 |
|---|---|
| `isActive()` | 편집 모드 활성 여부 반환 |
| `toggle(force?)` | 편집 모드 진입/이탈 |
| `markDirty(rowId, field, newValue, oldValue)` | 셀 변경 기록. 원본 복원 시 dirty 자동 제거. **rowId가 falsy면 무시** |
| `isDirty(rowId, field)` | 특정 셀의 dirty 여부 |
| `hasErrors()` | 검증 오류 존재 여부 |
| `validateCell(rowId, field, value)` | 필수 필드 + 커스텀 validator 실행 |
| `getCellError(rowId, field)` | 특정 셀의 오류 메시지 |
| `getCellClass(params)` | AG Grid cellClass 콜백용 — dirty/error/readonly 클래스 반환 |
| `handleCellChange(event)` | onCellValueChanged 핸들러 — normalizeChange → markDirty. **id 없는 행은 false 반환** |
| `async save()` | dirty 수집 → PATCH → 부분 성공 지원. **신규 행 무관** |
| `cancel()` | dirty 행 원본 복원 → 상태 초기화. **신규 행 무관** |
| `reset()` | dirty/error 상태만 초기화 (모드 변경 없음). 외부에서 강제 리셋 시 사용 |
| `getDirtyCount()` | 변경된 행 수 |
| `getErrorCount()` | 오류 셀 수 |

### 3.4 내부 메서드

| 메서드 | 설명 |
|---|---|
| `_updateStatusBar()` | 변경 N건 / 오류 N건 갱신, 저장 버튼 disabled 토글 |
| `_buildBulkApplyUI(container)` | bulkApplyFields 기반 드롭다운 동적 생성 |
| `_populateBulkSelects()` | toggle(true) 시 옵션 목록 갱신 |
| `_applyBulkValues()` | 선택 행에 일괄 값 적용 → markDirty 호출 (id 있는 행만) |
| `_updateBulkSelectionUI()` | 선택 행 수 표시, 선택 없으면 bulk 패널 숨김 |
| `_bindButtons()` | selectors 기반 이벤트 리스너 등록 |

---

## 4. 핵심 메서드 상세

### 4.1 handleCellChange(event)

`onCellValueChanged`에서 호출. **기존 행(id 있음) + 편집 모드일 때만 동작.**

```
handleCellChange(event):
  1. _active가 false → return false
  2. row.id가 없으면 → return false (신규 행은 관여 안 함)
  3. normalizeChange 훅이 있으면 호출:
     - "reject" → 원래 값 복원, return false
     - { dirtyChanges, rowMutations }:
       → row.data에 rowMutations 적용 (표시값)
       → dirtyChanges만 markDirty (서버 저장 대상)
     - null → 기본 동작으로 fall through
  4. 기본 동작: markDirty(rowId, field, newValue, oldValue)
  5. gridApi.refreshCells() → return true
```

### 4.2 save()

**dirty 기존 행의 PATCH만 담당. 신규 행 저장은 호출자 책임.**

```
save():
  1. hasErrors() → showToast("검증 오류") + return { success: false }

  2. _dirtyRows 수집 → items = [{id, changes}]
     → items가 비어있으면 → return { success: true, count: 0 }

  3. onBeforeSave(items) → 변환된 payload

  4. PATCH bulkEndpoint 호출
     → 성공한 행: _dirtyRows에서 제거
     → 실패 시: 실패한 행은 dirty 유지

  5. onAfterSave(results)

  6. return { success: true, count: results.length }
     (toggle은 호출자가 결정)
```

**중요 변경:** `save()`는 더 이상 `toggle(false)`을 호출하지 않는다. 반환값을 보고 래퍼가 결정한다.

### 4.3 cancel()

**dirty 기존 행의 원본 복원만 담당. 신규 행 정리는 호출자 책임.**

```
cancel():
  1. _originalValues 순회 → 각 행의 원래 값 복원
  2. _dirtyRows, _originalValues, _errorCells 초기화
  3. gridApi.refreshCells({ force: true })
  (toggle은 호출자가 결정)
```

**중요 변경:** `cancel()`도 `toggle(false)`을 호출하지 않는다. 래퍼가 결정한다.

### 4.4 getCellClass(params)

```
getCellClass(params):
  1. _active가 false → return []
  2. field가 editableFields에 없으면 → return ["infra-cell-readonly"]
  3. rowId가 없으면 (신규 행) → return [] (신규 행 스타일은 도메인 담당)
  4. isDirty(rowId, field) → "infra-cell-dirty" 추가
  5. getCellError(rowId, field) → "infra-cell-error" 추가
  6. return classes 배열
```

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
     - row.id가 없으면 (신규 행) → data만 변경, dirty 미적재
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
| `selectors.saveBtn` | click | `save()` — **직접 바인딩하지 않음 (아래 참조)** |
| `selectors.cancelBtn` | click | `cancel()` — **직접 바인딩하지 않음 (아래 참조)** |
| gridApi | selectionChanged | `_updateBulkSelectionUI()` |

**저장/취소 버튼은 자산 래퍼가 바인딩한다.** GridEditMode의 `save()`/`cancel()`은 toggle을 하지 않고, 래퍼가 신규 행 처리 + toggle 결정을 포함한 전체 흐름을 제어해야 하기 때문이다.

→ `selectors.saveBtn`, `selectors.cancelBtn`은 **show/hide 토글 용도로만** 사용. click 이벤트는 바인딩하지 않음.

### 6.2 자산 그리드의 이벤트 연결

| 이벤트 | 연결 방식 |
|---|---|
| `onCellValueChanged` | `handleGridCellValueChanged()`에서 신규 행/비편집 분기 후 `editMode.handleCellChange(event)` 호출 |
| paste `onPaste` 콜백 | 자산 도메인에서 직접 처리: 모델 유사매칭, 신규 행 플래그 설정 후 기존 행에 대해 `editMode.markDirty()` 호출 |
| 저장 버튼 click | `assetSaveEditMode()` 래퍼 |
| 취소 버튼 click | `assetCancelEditMode()` 래퍼 |

### 6.3 paste 경로 (명확화)

paste는 `onCellValueChanged`를 경유하지 **않는다.**
`addCopyPasteHandler()`는 `node.data[field] = value`로 직접 설정하고 `onPaste` 콜백을 호출한다.

자산 그리드의 `onPaste` 콜백이 하는 일:
1. 비편집 모드면 → 원복 + 경고
2. 신규 행 플래그 설정 (`_isNew`, `_hasNewRows`)
3. `asset_name` → 역할명 자동 세팅
4. `model` → 카탈로그 유사매칭 (async API 호출)
5. **기존 행(id 있음)에 대해 `editMode.markDirty()` 호출**
6. **기존 행 model 변경 시 `_rememberOriginalField()` → `editMode.markDirty("model_id", ...)` 호출**

이 로직은 도메인 고유이므로 GridEditMode에 포함하지 않는다.

---

## 7. 자산 그리드 리팩토링

### 7.1 제거 대상 (infra_assets.js에서)

| 현재 코드 | 대체 |
|---|---|
| `_editMode` 변수 | `editMode.isActive()` |
| `_dirtyRows`, `_originalValues`, `_errorCells` 변수 | GridEditMode 내부 상태 |
| `toggleEditMode()` | `editMode.toggle()` |
| `markDirty()`, `isDirty()` | `editMode.markDirty()`, `editMode.isDirty()` |
| `validateCell()`, `hasErrors()`, `getCellError()` | GridEditMode 메서드 |
| `_updateEditModeBar()` | `editMode._updateStatusBar()` (내부 자동 호출) |
| `_populateBulkSelects()` | GridEditMode 내부 자동 호출 |
| `_applyBulkValues()` | GridEditMode `_applyBulkValues()` |
| `_updateBulkSelectionUI()` | GridEditMode 내부 자동 호출 |
| `_populateSelectFromList()`, `_populateSelectFromEntries()` (bulk 전용) | GridEditMode 동적 생성으로 대체 |

### 7.2 유지 대상 (infra_assets.js에 남는 것)

| 코드 | 이유 |
|---|---|
| `addAssetRow()` | 도메인 고유 — 신규 행 기본값, `_isNew` 플래그 |
| `saveNewAssets()` | 도메인 고유 — POST + 역할 자동 생성/할당 |
| `deleteSelectedAssets()` | 도메인 고유 — DELETE API + 신규/기존 분기 |
| `_hasNewRows`, `_updateNewRowIndicators()` | 신규 행 UI 상태 — GridEditMode 범위 밖 |
| `handleGridCellValueChanged()` | 도메인 고유 분기 (신규 행, 비편집 모드 즉시 저장) 후 `editMode.handleCellChange()` 위임 |
| `onPaste` 콜백 전체 | 도메인 고유 — 모델 유사매칭, 신규 행 처리, dirty는 `editMode.markDirty()` 호출 |
| `_rememberOriginalField()` | paste 경로에서 model 원본 보존용 — `editMode.markDirty()`에 oldValue 전달 시 사용 |
| `applyAssetRowUpdate()` | 도메인 고유 — 서버 응답을 행 데이터에 매핑 |
| `CatalogCellEditor` | 도메인 고유 — 카탈로그 검색 에디터 |

### 7.3 자산 래퍼 함수

기존 `saveEditMode()`와 `cancelEditMode()`를 래퍼로 교체:

```javascript
async function assetSaveEditMode() {
  if (editMode.hasErrors()) {
    showToast("검증 오류가 있어 저장할 수 없습니다.", "warning");
    return;
  }

  // 1단계: 신규 행 저장 (도메인 고유)
  if (_hasNewRows) {
    await saveNewAssets();
    // saveNewAssets가 내부에서 _hasNewRows 재계산
  }

  // 2단계: dirty 기존 행 PATCH (GridEditMode)
  const result = await editMode.save();

  // 3단계: 모드 이탈 판단
  if (result.count === 0 && !_hasNewRows) {
    // dirty도 없고 신규도 없음 → 이탈
    editMode.toggle(false);
  } else if (result.count === 0 && _hasNewRows) {
    showToast("저장되지 않은 신규 자산이 남아 있습니다.", "warning");
  } else if (result.success) {
    if (!_hasNewRows) editMode.toggle(false);
  }
}

function assetCancelEditMode() {
  // 1단계: dirty 기존 행 복원 (GridEditMode)
  editMode.cancel();

  // 2단계: 신규 행 정리 (도메인 고유)
  // 신규 행을 그리드에서 제거
  const newNodes = [];
  gridApi.forEachNode(n => { if (n.data._isNew) newNodes.push(n.data); });
  if (newNodes.length) {
    gridApi.applyTransaction({ remove: newNodes });
  }
  _hasNewRows = false;
  _updateNewRowIndicators();
  _updateDeleteButtonVisibility();

  // 3단계: 모드 이탈
  editMode.toggle(false);
}
```

### 7.4 normalizeChange 구현 (자산 그리드)

```javascript
function assetNormalizeChange(event) {
  const field = event.colDef.field;
  if (field !== "model") return null;

  const val = event.newValue;
  if (!val || !val._catalogModelId) return "reject";

  return {
    // 표시값: row.data에만 반영, dirty 적재 안 함
    rowMutations: {
      model_id: val._catalogModelId,
      vendor: val._catalogVendor || "",
      model: val._catalogName || val.display || "",
    },
    // 서버 저장 대상: dirty에 적재
    dirtyChanges: [
      { field: "model_id", value: val._catalogModelId, oldValue: event.data.model_id },
    ],
  };
}
```

**이전 버전에서 수정:** `vendor`를 `dirtyChanges`에서 제거. 현재 서버는 `model_id`만 PATCH하고 `vendor/model/system_id`는 서버 응답으로 동기화한다.

### 7.5 GridEditMode 인스턴스 생성 (자산 그리드)

```javascript
const editMode = new GridEditMode({
  gridApi,
  editableFields: EDITABLE_FIELDS,
  bulkEndpoint: "/api/v1/assets/bulk",
  requiredFields: new Set(["asset_name"]),
  normalizeChange: assetNormalizeChange,
  prefix: "asset",

  onBeforeSave: (items) => items,

  onAfterSave: (results) => {
    for (const updated of results) {
      let node = null;
      gridApi.forEachNode(n => { if (n.data?.id === updated.id) node = n; });
      if (node) applyAssetRowUpdate(node.data, updated);
    }
  },

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

// 저장/취소는 래퍼가 바인딩
document.getElementById("btn-save-edit").addEventListener("click", assetSaveEditMode);
document.getElementById("btn-cancel-edit").addEventListener("click", assetCancelEditMode);
```

---

## 8. 검증 전략

### 8.1 자동 검증

- `pytest` — 백엔드 변경 없으므로 기존 테스트 통과 확인만

### 8.2 수동 체크리스트 (브라우저)

**기본 편집:**

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | 편집 모드 진입 | 토글/저장/취소 버튼 전환, 상태바 표시, bulk apply UI 동적 생성 |
| 2 | 셀 수정 (기존 행) | dirty 셀 파란 배경, 상태바 "변경 N건" 갱신 |
| 3 | 필수 필드 비우기 | error 셀 빨간 배경, "오류 N건" 표시, 저장 버튼 disabled |
| 4 | 원래 값으로 되돌리기 | dirty 자동 해제, 카운트 감소 |
| 5 | model 셀 수정 (카탈로그 선택) | model_id만 dirty 기록, vendor/model 표시값 갱신 |
| 6 | model 셀 잘못된 입력 | "reject" — 원래 값 복원 |
| 7 | bulk apply (행 선택 → 값 일괄 적용) | 기존 행: dirty 기록, 신규 행: 값만 변경 |

**저장/취소:**

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 8 | 저장 (기존 행만 dirty) | PATCH /bulk → 성공 → 편집 모드 이탈 |
| 9 | 저장 (기존 dirty + 신규 행) | saveNewAssets → PATCH → 모두 성공 시 이탈 |
| 10 | 저장 (신규 행 일부 실패) | 실패 행 `_isNew` 유지, 편집 모드 유지, 상태바 갱신 |
| 11 | 저장 (PATCH 부분 실패) | 실패 행 dirty 유지, 편집 모드 유지 |
| 12 | 취소 | dirty 셀 원본 복원, 신규 행 제거, 편집 모드 이탈 |

**Paste:**

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 13 | paste (기존 행, 일반 필드) | onPaste → editMode.markDirty() → dirty 기록 |
| 14 | paste (기존 행, model 필드) | 카탈로그 유사매칭 → editMode.markDirty("model_id") |
| 15 | paste (신규 행 자동 생성) | _hasNewRows 플래그 설정, dirty 미적재 |
| 16 | paste (비편집 모드) | 원복 + "편집 모드에서만 붙여넣기 가능" 토스트 |
| 17 | Ctrl+Z (undo) | paste 전 상태로 복원 (utils.js undo stack) |

---

## 9. 비변경 사항

- **백엔드:** 변경 없음. 기존 `PATCH /api/v1/assets/bulk`, `POST /api/v1/assets` 그대로.
- **CSS:** `infra_common.css`의 dirty/error/readonly 스타일 그대로 사용.
- **`addCopyPasteHandler()`:** `utils.js` 변경 없음. 기존 동작 유지.
- **`onPaste` 콜백:** `infra_assets.js`에 그대로 남음. `markDirty()` 호출만 `editMode.markDirty()`로 교체.
- **`saveNewAssets()`:** 로직 변경 없음. `successCount`를 반환하도록 시그니처만 수정.
- **다른 그리드:** Phase 0에서는 자산 그리드만 리팩토링. 다른 그리드는 Phase 1 이후.
