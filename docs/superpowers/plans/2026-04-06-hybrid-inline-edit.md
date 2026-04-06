# 하이브리드 인라인 편집 전환 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 단순 필드는 더블클릭 셀 편집, 복잡 필드만 모달 유지하는 하이브리드 패턴으로 전환하고, 자산 그리드의 "테이블 편집" 토글 버튼을 제거한다.

**Architecture:** 각 그리드의 columnDefs에서 단순 필드에 `editable: true` + 적절한 `cellEditor`를 추가하고, `onCellValueChanged`에서 해당 행의 PATCH API를 호출한다. 이전 Task에서 적용한 `buildStandardGridBehavior()`의 `singleClickEdit: false` 설정 덕분에 편집은 더블클릭으로만 시작된다. 모달은 복잡 필드 편집용으로 유지하되, 더블클릭 onEdit 콜백은 제거(셀 편집이 대체).

**Tech Stack:** ag-Grid Community (inline editing, cellEditor), vanilla JS, FastAPI PATCH endpoints

---

## 하이브리드 편집 기준

| 인라인 편집 대상 | 모달 유지 대상 |
|-----------------|---------------|
| 텍스트 1줄 (이름, 코드, 메모) | 여러 줄 textarea (scope, description) |
| 드롭다운 선택 (상태, 유형) | 참조 검색 (자산 선택, 카탈로그 검색) |
| 날짜 (단순 입력) | 다중 필드 동시 입력 (신규 생성) |
| 숫자 | 복잡한 관계 설정 (역할 할당) |

---

## File Structure

| 파일 | 변경 내용 |
|------|----------|
| `app/static/js/infra_assets.js` | `_gridEditMode` 토글 제거, editable 컬럼 항상 활성 |
| `app/modules/infra/templates/infra_assets.html` | "테이블 편집" 버튼 제거 |
| `app/static/js/infra_project_detail.js` | phase/deliverable 그리드에 인라인 편집 추가 |
| `app/static/js/infra_port_maps.js` | 단순 필드 인라인 편집 추가 |
| `app/static/js/infra_ip_inventory.js` | 단순 필드 인라인 편집 추가 |
| `app/static/js/infra_policies.js` | 상태/검사 필드 인라인 편집 추가 |
| `app/static/js/infra_asset_roles.js` | role_name/status 인라인 편집 추가 |
| `app/static/js/infra_product_catalog.js` | 더블클릭 onEdit 제거 (셀 편집 불가, 모달 유지) |

---

### Task 1: 자산 그리드 — "테이블 편집" 토글 제거, 항상 편집 가능

**Files:**
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/modules/infra/templates/infra_assets.html`

현재 자산 그리드는 `_gridEditMode` 플래그로 편집 모드를 토글한다. 더블클릭 편집으로 전환했으므로 이 토글이 불필요하다. editable 컬럼을 항상 편집 가능하게 변경한다.

- [ ] **Step 1: infra_assets.html에서 "테이블 편집" 버튼 제거**

`app/modules/infra/templates/infra_assets.html`에서 `btn-toggle-grid-edit` 버튼을 찾아 제거한다.

- [ ] **Step 2: infra_assets.js에서 _gridEditMode 관련 코드 정리**

1. `_gridEditMode` 변수 선언(let _gridEditMode = false)을 찾아 제거
2. `syncGridEditButton()` 함수 전체를 제거
3. `GRID_EDITABLE_FIELDS` Set은 유지 (editable 판단에 사용)
4. columnDefs에서 editable 속성의 조건부 로직을 변경:

```javascript
// 변경 전 (각 editable 컬럼):
editable: (params) => _gridEditMode && GRID_EDITABLE_FIELDS.has(params.colDef.field),

// 변경 후:
editable: (params) => GRID_EDITABLE_FIELDS.has(params.colDef.field),
```

5. DOMContentLoaded 또는 initGrid 내에서 `btn-toggle-grid-edit` 이벤트 리스너를 제거
6. `syncGridEditButton()` 호출부를 모두 제거

- [ ] **Step 3: buildStandardGridBehavior에서 onEdit 콜백이 없어도 셀 편집이 동작하는지 확인**

자산 그리드의 `buildStandardGridBehavior`는 이미 `type: 'detail-panel'`으로 설정되어 있고, `onCellValueChanged`가 연결되어 있다. `onEdit`가 없으면 더블클릭 시 ag-Grid 기본 동작(셀 편집)이 실행된다.

현재 코드:
```javascript
...buildStandardGridBehavior({
  type: 'detail-panel',
  onSelect: (data) => showAssetDetail(data),
  onCellValueChanged: handleGridCellValueChanged,
}),
```
onEdit가 없으므로 onRowDoubleClicked가 설정되지 않고, ag-Grid 기본 더블클릭=셀편집이 동작한다. 이 상태가 정확히 원하는 동작이다.

- [ ] **Step 4: 브라우저 확인**

1. 자산 목록에서 "테이블 편집" 버튼이 사라졌는지 확인
2. editable 컬럼(asset_name, hostname, status 등)을 더블클릭하면 바로 편집 시작
3. 비편집 컬럼(asset_code, contract_name 등)을 더블클릭하면 편집 안 됨
4. 싱글클릭은 여전히 상세 패널 열기

- [ ] **Step 5: Commit**

```bash
git add app/static/js/infra_assets.js app/modules/infra/templates/infra_assets.html
git commit -m "refactor(infra): remove grid edit toggle, make asset columns always editable on double-click"
```

---

### Task 2: 프로젝트 상세 — Phase/Deliverable 인라인 편집

**Files:**
- Modify: `app/static/js/infra_project_detail.js`

Phase 그리드: `phase_type`(드롭다운), `status`(드롭다운) 필드를 인라인 편집.
Deliverable 그리드: `name`(텍스트), `is_submitted`(드롭다운), `note`(텍스트) 필드를 인라인 편집.
나머지 복잡 필드(task_scope textarea, description textarea)는 모달 유지.

- [ ] **Step 1: Phase 컬럼에 editable 추가**

`phaseColDefs` 배열에서 `phase_type`과 `status` 컬럼에 editable + cellEditor를 추가:

```javascript
// phase_type 컬럼:
{
  field: "phase_type", headerName: "유형", width: 120,
  editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: {
    values: ["analysis", "design", "development", "test", "deployment", "maintenance", "other"],
  },
  valueFormatter: (p) => { /* 기존 포매터 유지 */ },
},

// status 컬럼:
{
  field: "status", headerName: "상태", width: 100,
  editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: {
    values: ["planned", "in_progress", "completed", "on_hold"],
  },
  cellRenderer: (p) => { /* 기존 렌더러 유지 */ },
},
```

- [ ] **Step 2: Deliverable 컬럼에 editable 추가**

`deliverableColDefs` 배열에서 `name`, `is_submitted`, `note` 컬럼:

```javascript
// name 컬럼:
{ field: "name", headerName: "산출물명", flex: 1, minWidth: 200, editable: true },

// is_submitted 컬럼:
{
  field: "is_submitted", headerName: "제출", width: 80,
  editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: { values: [true, false] },
  valueFormatter: (p) => p.value ? "제출" : "미제출",
  cellRenderer: (p) => { /* 기존 렌더러 유지 */ },
},

// note 컬럼:
{ field: "note", headerName: "비고", width: 150, editable: true },
```

- [ ] **Step 3: onCellValueChanged 핸들러 추가**

Phase 그리드와 Deliverable 그리드에 각각 onCellValueChanged를 추가. `buildStandardGridBehavior`의 onCellValueChanged로 전달:

```javascript
// Phase 그리드 — buildStandardGridBehavior 변경:
...buildStandardGridBehavior({
  type: 'modal-edit',
  onEdit: (data) => openEditPhase(data),
  onCellValueChanged: handlePhaseCellChanged,
}),

// Deliverable 그리드:
...buildStandardGridBehavior({
  type: 'modal-edit',
  onEdit: (data) => openEditDeliverable(data),
  onCellValueChanged: handleDeliverableCellChanged,
}),
```

핸들러 함수 구현:

```javascript
async function handlePhaseCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/period-phases/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    phaseGridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}

async function handleDeliverableCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/period-deliverables/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    deliverableGridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}
```

- [ ] **Step 4: buildStandardGridBehavior의 modal-edit 타입에 onCellValueChanged 지원 확인**

`utils.js`의 `buildStandardGridBehavior` 함수에서 `modal-edit` 케이스에 `onCellValueChanged`를 전달하는 코드가 없다. 추가 필요:

```javascript
case 'modal-edit':
  if (onSelect) {
    result.onRowClicked = (e) => { if (e.data) onSelect(e.data, e); };
  }
  if (onEdit) {
    result.onRowDoubleClicked = (e) => { if (e.data) onEdit(e.data, e); };
  }
  // 추가:
  if (onCellValueChanged) {
    result.onCellValueChanged = onCellValueChanged;
  }
  break;
```

- [ ] **Step 5: Commit**

```bash
git add app/static/js/infra_project_detail.js app/static/js/utils.js
git commit -m "feat(infra): add inline edit to phase/deliverable grids"
```

---

### Task 3: 포트맵 — 단순 필드 인라인 편집

**Files:**
- Modify: `app/static/js/infra_port_maps.js`

인라인 대상: `cable_no`, `purpose`, `status`, `connection_type`, `cable_type`, `cable_speed`
모달 유지: src/dst 관련 복잡 필드 (hostname, port, zone, vlan, ip 등), note (textarea)

- [ ] **Step 1: 컬럼에 editable 추가**

`columnDefs` 배열에서 해당 컬럼에 editable + cellEditor 추가:

```javascript
{ field: "cable_no", headerName: "케이블번호", width: 110, editable: true },
{ field: "connection_type", headerName: "연결유형", width: 100, editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: { values: ["fiber", "utp", "dac", "console", "serial", "other"] },
},
{ field: "cable_type", headerName: "케이블종류", width: 100, editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: { values: ["SM", "MM", "UTP", "STP", "DAC", "other"] },
},
{ field: "cable_speed", headerName: "속도", width: 80, editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: { values: ["100M", "1G", "10G", "25G", "40G", "100G", "other"] },
},
{ field: "purpose", headerName: "용도", flex: 1, editable: true },
{ field: "status", headerName: "상태", width: 80, editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: { values: ["active", "planned", "disconnected", "reserved"] },
},
```

주의: 기존 컬럼 정의를 읽고 headerName, width, cellRenderer 등을 보존하면서 editable과 cellEditor만 추가해야 한다.

- [ ] **Step 2: onCellValueChanged 핸들러 추가**

```javascript
async function handlePortMapCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/port-maps/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    gridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}
```

buildStandardGridBehavior에 onCellValueChanged 추가:

```javascript
...buildStandardGridBehavior({
  type: 'modal-edit',
  onEdit: (data) => openEditModal(data),
  onCellValueChanged: handlePortMapCellChanged,
}),
```

- [ ] **Step 3: Commit**

```bash
git add app/static/js/infra_port_maps.js
git commit -m "feat(infra): add inline edit to port map grid simple fields"
```

---

### Task 4: IP 인벤토리 — 단순 필드 인라인 편집

**Files:**
- Modify: `app/static/js/infra_ip_inventory.js`

인라인 대상: `hostname`, `service_name`, `zone`, `vlan_id`, `note`
모달 유지: `ip_address`(PK), `ip_type`, `subnet`, 네트워크 설정 필드들

- [ ] **Step 1: 컬럼에 editable 추가**

```javascript
{ field: "hostname", headerName: "호스트명", width: 130, editable: true },
{ field: "service_name", headerName: "서비스명", width: 130, editable: true },
{ field: "zone", headerName: "존", width: 100, editable: true },
{ field: "vlan_id", headerName: "VLAN", width: 80, editable: true },
{ field: "note", headerName: "비고", flex: 1, editable: true },
```

- [ ] **Step 2: onCellValueChanged 핸들러 추가**

```javascript
async function handleIpCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/ip-inventory/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    ipGridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}
```

buildStandardGridBehavior에 onCellValueChanged 추가.

- [ ] **Step 3: Commit**

```bash
git add app/static/js/infra_ip_inventory.js
git commit -m "feat(infra): add inline edit to IP inventory grid simple fields"
```

---

### Task 5: 정책 할당 — 상태/검사 필드 인라인 편집

**Files:**
- Modify: `app/static/js/infra_policies.js`

인라인 대상: `status`, `checked_by`, `checked_date`, `exception_reason`, `evidence_note`
모달 유지: `policy_definition_id`, `asset_id` (참조 선택)

- [ ] **Step 1: 컬럼에 editable 추가**

```javascript
{ field: "status", headerName: "상태", width: 100, editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: { values: ["not_checked", "compliant", "non_compliant", "exception", "not_applicable"] },
},
{ field: "checked_by", headerName: "점검자", width: 120, editable: true },
{ field: "checked_date", headerName: "점검일", width: 120, editable: true },
{ field: "exception_reason", headerName: "예외사유", flex: 1, editable: true },
{ field: "evidence_note", headerName: "근거", width: 150, editable: true },
```

- [ ] **Step 2: onCellValueChanged 핸들러 추가**

```javascript
async function handleAssignmentCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/policy-assignments/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    assignGridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}
```

buildStandardGridBehavior에 onCellValueChanged 추가.

- [ ] **Step 3: Commit**

```bash
git add app/static/js/infra_policies.js
git commit -m "feat(infra): add inline edit to policy assignment grid"
```

---

### Task 6: 역할 목록 — role_name/status 인라인 편집

**Files:**
- Modify: `app/static/js/infra_asset_roles.js`

인라인 대상: `role_name`, `status`
모달 유지: `role_type`, `note`, 역할 할당 관리 (복잡한 관계)

- [ ] **Step 1: 컬럼에 editable 추가**

`roleColumnDefs` 배열에서:

```javascript
{ field: "role_name", headerName: "역할명", flex: 1, minWidth: 180, editable: true },
{ field: "status", headerName: "상태", width: 110, editable: true,
  cellEditor: "agSelectCellEditor",
  cellEditorParams: { values: ["active", "inactive", "retired"] },
  cellRenderer: (p) => { /* 기존 배지 렌더러 유지 */ },
},
```

- [ ] **Step 2: onCellValueChanged 핸들러 추가**

```javascript
async function handleRoleCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/asset-roles/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
    if (colDef.field === "status" || colDef.field === "role_name") {
      showRoleDetail(data);
    }
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    roleGridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}
```

buildStandardGridBehavior 변경 — onEdit를 제거하고 onCellValueChanged 추가:

```javascript
// 변경 전:
...buildStandardGridBehavior({
  type: 'detail-panel',
  onSelect: (data) => showRoleDetail(data),
  onEdit: (data) => openRoleModal(data),
}),

// 변경 후:
...buildStandardGridBehavior({
  type: 'detail-panel',
  onSelect: (data) => showRoleDetail(data),
  onCellValueChanged: handleRoleCellChanged,
}),
```

onEdit를 제거하면 더블클릭 시 ag-Grid 기본 셀 편집이 동작한다. 비편집 컬럼을 더블클릭하면 아무 일도 안 일어난다. 모달은 상세 패널의 "수정" 버튼으로 접근 가능.

- [ ] **Step 3: Commit**

```bash
git add app/static/js/infra_asset_roles.js
git commit -m "feat(infra): add inline edit to asset role grid"
```

---

### Task 7: 제품 카탈로그 — onEdit 제거 (모달 전용 유지)

**Files:**
- Modify: `app/static/js/infra_product_catalog.js`

제품 카탈로그는 분류체계/벤더/속성 등 복잡한 필드로 구성되어 인라인 편집에 적합하지 않다. 더블클릭 시 모달 대신 아무 동작도 하지 않도록 onEdit를 제거한다. 편집은 상세 패널의 "수정" 버튼으로만 접근.

- [ ] **Step 1: buildStandardGridBehavior에서 onEdit 제거**

```javascript
// 변경 전:
...buildStandardGridBehavior({
  type: 'detail-panel',
  onSelect: (data) => selectProduct(data),
  onEdit: (data) => openEditProduct(data.id),
}),

// 변경 후:
...buildStandardGridBehavior({
  type: 'detail-panel',
  onSelect: (data) => selectProduct(data),
}),
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/infra_product_catalog.js
git commit -m "refactor(infra): remove double-click modal from catalog grid, keep panel edit only"
```

---

### Task 8: 프론트엔드 가이드라인 업데이트

**Files:**
- Modify: `docs/guidelines/frontend.md`

- [ ] **Step 1: 하이브리드 편집 패턴 설명 추가**

`frontend.md`의 ag-Grid 상호작용 표준 섹션 뒤에 추가:

```markdown
### 하이브리드 인라인 편집

그리드 셀 편집과 모달 편집을 병행한다. 기준:

- **인라인 (더블클릭):** 텍스트 1줄, 드롭다운, 날짜, 숫자 등 단순 필드
- **모달 (버튼 또는 액션):** textarea, 참조 검색, 다중 필드 동시 입력, 신규 생성

인라인 편집 구현 패턴:
1. columnDefs에 `editable: true` + 필요 시 `cellEditor: "agSelectCellEditor"`
2. `buildStandardGridBehavior()`에 `onCellValueChanged` 핸들러 전달
3. 핸들러에서 `PATCH /api/v1/{resource}/{id}` 호출, 실패 시 `oldValue` 복원
4. `singleClickEdit: true`는 사용 금지 — 더블클릭 편집만 허용
5. "테이블 편집" 같은 모드 토글 버튼은 만들지 않는다
```

- [ ] **Step 2: Commit**

```bash
git add docs/guidelines/frontend.md
git commit -m "docs: add hybrid inline edit pattern to frontend guidelines"
```

---

## Self-Review

1. **Spec coverage:** 자산(테이블편집 제거) ✓, Phase/Deliverable(인라인) ✓, 포트맵(인라인) ✓, IP(인라인) ✓, 정책(인라인) ✓, 역할(인라인) ✓, 카탈로그(모달유지) ✓, 문서 ✓
2. **Placeholder scan:** 모든 코드 블록에 실제 핸들러 코드 포함 ✓
3. **Type consistency:** `handleXxxCellChanged` 네이밍 일관, PATCH 패턴 동일, buildStandardGridBehavior 옵션 키 일관 ✓
4. **utils.js 수정:** Task 2에서 modal-edit의 onCellValueChanged 지원 추가 필요 ✓
