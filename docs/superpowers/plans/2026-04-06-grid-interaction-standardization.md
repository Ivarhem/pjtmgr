# ag-Grid 상호작용 표준화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 전체 ag-Grid를 "싱글클릭=정보/선택, 더블클릭=편집/이동" 패턴으로 통일

**Architecture:** utils.js에 공용 그리드 옵션 빌더(`buildStandardGridBehavior`)를 추가하고, 각 페이지 그리드가 이를 사용하도록 전환. 기존 `singleClickEdit: true`를 제거하고 `onRowDoubleClicked`로 편집 트리거. 네비게이션 그리드는 싱글클릭=미리보기(가능한 경우), 더블클릭=페이지 이동으로 전환.

**Tech Stack:** ag-Grid Community, vanilla JS, Bulma CSS

---

## 상호작용 표준 규칙

| 그리드 유형 | 싱글클릭 | 더블클릭 |
|------------|----------|----------|
| 마스터-디테일 (자산, 카탈로그, 역할, 파트너, 시스템) | 우측 상세 패널 열기 | 셀 인라인 편집 (편집 가능 그리드) 또는 편집 모달 |
| 네비게이션 (프로젝트, 계약, 내사업) | 행 하이라이트만 | 상세 페이지로 이동 |
| 인라인 편집 (매출/매입, 입금, 사용자) | 행 선택만 | 셀 인라인 편집 |
| 읽기 전용 (감사이력, 대시보드, 리포트, import) | 행 선택만 | 무시 (아무 동작 없음) |
| 하위 탭 그리드 (프로젝트 상세 내 phase, deliverable 등) | 행 선택 | 편집 모달 열기 |

---

## File Structure

| 파일 | 역할 | 변경 유형 |
|------|------|----------|
| `app/static/js/utils.js` | 공용 `buildStandardGridBehavior()` 헬퍼 추가 | Modify |
| `app/static/js/infra_assets.js` | singleClickEdit 제거, 더블클릭 편집 전환 | Modify |
| `app/static/js/infra_projects.js` | 싱글클릭 이동 → 더블클릭 이동 전환 | Modify |
| `app/static/js/infra_product_catalog.js` | 더블클릭 편집 모달 추가 | Modify |
| `app/static/js/infra_asset_roles.js` | 더블클릭 편집 모달 추가 | Modify |
| `app/static/js/infra_catalog_integrity.js` | 더블클릭 편집 연결 | Modify |
| `app/static/js/infra_project_detail.js` | 하위 그리드에 더블클릭 모달 추가 | Modify |
| `app/static/js/infra_contacts.js` | 더블클릭 편집 모달 추가 | Modify |
| `app/static/js/infra_port_maps.js` | 더블클릭 편집 모달 전환 | Modify |
| `app/static/js/infra_ip_inventory.js` | 더블클릭 편집 모달 전환 | Modify |
| `app/static/js/infra_policies.js` | 더블클릭 편집 모달 전환 | Modify |
| `app/static/js/contracts.js` | 싱글클릭 이동 → 더블클릭 이동 전환 | Modify |
| `app/static/js/my_contracts.js` | 싱글클릭 이동 → 더블클릭 이동 전환 | Modify |
| `app/static/js/contract_detail.js` | singleClickEdit 제거, 더블클릭 편집 | Modify |
| `app/static/js/partners.js` | singleClickEdit 제거, 더블클릭 편집 | Modify |
| `app/static/js/users.js` | suppressRowClickSelection 유지, 더블클릭 편집 | Modify |
| `app/static/js/system.js` | 더블클릭 편집 모달 연결 | Modify |
| `docs/guidelines/frontend.md` | 그리드 상호작용 표준 문서화 | Modify |

---

### Task 1: utils.js에 공용 그리드 상호작용 헬퍼 추가

**Files:**
- Modify: `app/static/js/utils.js`

이 헬퍼는 각 그리드가 표준 동작을 쉽게 적용할 수 있게 해주는 옵션 스프레드 객체를 반환한다.

- [ ] **Step 1: utils.js에 buildStandardGridBehavior 함수 추가**

파일 끝(`showConfirmDialog` 함수 뒤, 파일 말미)에 추가:

```javascript
/**
 * ag-Grid 표준 상호작용 옵션을 생성한다.
 *
 * 규칙:
 * - 싱글클릭: 행 선택 / 상세 패널 열기
 * - 더블클릭: 편집(인라인 또는 모달) / 페이지 이동
 * - 읽기 전용 그리드는 더블클릭 무시
 *
 * @param {Object} opts
 * @param {'detail-panel'|'navigate'|'inline-edit'|'readonly'|'modal-edit'} opts.type - 그리드 유형
 * @param {Function} [opts.onSelect] - 싱글클릭 시 콜백 (type=detail-panel, navigate)
 * @param {Function} [opts.onEdit] - 더블클릭 시 콜백 (type=navigate → 이동, modal-edit → 모달, detail-panel → 편집)
 * @param {Function} [opts.onCellValueChanged] - 인라인 편집 완료 시 콜백 (type=inline-edit)
 * @returns {Object} agGrid 옵션에 스프레드할 객체
 */
function buildStandardGridBehavior(opts = {}) {
  const { type = 'readonly', onSelect, onEdit, onCellValueChanged } = opts;
  const result = {};

  // 기본: singleClickEdit 사용하지 않음 (더블클릭으로 편집)
  result.singleClickEdit = false;
  result.stopEditingWhenCellsLoseFocus = true;

  switch (type) {
    case 'detail-panel':
      // 싱글클릭: 상세 패널 열기, 더블클릭: 편집 (인라인 또는 모달)
      result.onRowClicked = (e) => { if (e.data && onSelect) onSelect(e.data, e); };
      if (onEdit) {
        result.onRowDoubleClicked = (e) => { if (e.data) onEdit(e.data, e); };
      }
      if (onCellValueChanged) {
        result.onCellValueChanged = onCellValueChanged;
      }
      break;

    case 'navigate':
      // 싱글클릭: 행 하이라이트만, 더블클릭: 페이지 이동
      result.onRowClicked = (e) => { if (e.data && onSelect) onSelect(e.data, e); };
      result.onRowDoubleClicked = (e) => { if (e.data && onEdit) onEdit(e.data, e); };
      break;

    case 'inline-edit':
      // 싱글클릭: 행 선택만, 더블클릭: 셀 인라인 편집 시작
      if (onSelect) {
        result.onRowClicked = (e) => { if (e.data) onSelect(e.data, e); };
      }
      if (onCellValueChanged) {
        result.onCellValueChanged = onCellValueChanged;
      }
      break;

    case 'modal-edit':
      // 싱글클릭: 행 선택, 더블클릭: 편집 모달 열기
      if (onSelect) {
        result.onRowClicked = (e) => { if (e.data) onSelect(e.data, e); };
      }
      if (onEdit) {
        result.onRowDoubleClicked = (e) => { if (e.data) onEdit(e.data, e); };
      }
      break;

    case 'readonly':
    default:
      // 싱글클릭: 행 선택, 더블클릭: 없음
      if (onSelect) {
        result.onRowClicked = (e) => { if (e.data) onSelect(e.data, e); };
      }
      break;
  }

  return result;
}
```

- [ ] **Step 2: 브라우저 콘솔에서 함수 존재 확인**

서버 기동 후 아무 페이지에서 브라우저 콘솔:
```
typeof buildStandardGridBehavior === 'function'  // → true
```

- [ ] **Step 3: Commit**

```bash
git add app/static/js/utils.js
git commit -m "feat: add buildStandardGridBehavior helper to utils.js"
```

---

### Task 2: 인프라 자산 그리드 — 더블클릭 인라인 편집 전환

**Files:**
- Modify: `app/static/js/infra_assets.js:669-696` (initGrid 함수)

현재 `singleClickEdit: true`로 싱글클릭 시 바로 셀 편집이 시작됨. 이를 더블클릭 편집으로 전환.

- [ ] **Step 1: initGrid의 그리드 옵션 수정**

`app/static/js/infra_assets.js`의 `initGrid()` 함수에서 `agGrid.createGrid` 호출 부분을 수정:

```javascript
// 변경 전:
gridApi = agGrid.createGrid(gridDiv, {
    columnDefs,
    rowData: [],
    defaultColDef: {
      resizable: true,
      sortable: true,
      filter: true,
      tooltipValueGetter: getGridTooltipValue,
    },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    singleClickEdit: true,
    stopEditingWhenCellsLoseFocus: true,
    onCellValueChanged: handleGridCellValueChanged,
    onRowClicked: (e) => showAssetDetail(e.data),
    ...columnStateHandlers,
});

// 변경 후:
gridApi = agGrid.createGrid(gridDiv, {
    columnDefs,
    rowData: [],
    defaultColDef: {
      resizable: true,
      sortable: true,
      filter: true,
      tooltipValueGetter: getGridTooltipValue,
    },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => showAssetDetail(data),
      onCellValueChanged: handleGridCellValueChanged,
    }),
    ...columnStateHandlers,
});
```

핵심 변경: `singleClickEdit: true` 제거. `onRowClicked`와 `onCellValueChanged`를 헬퍼를 통해 설정. 더블클릭 시 ag-Grid 기본 인라인 편집이 작동 (`singleClickEdit: false`가 기본이면 더블클릭으로 편집됨).

- [ ] **Step 2: 편집 모드 토글 버튼(btn-toggle-grid-edit) 동작 확인**

기존 `_gridEditMode` 토글 로직은 컬럼의 `editable` 속성을 제어하므로 그대로 유지. 더블클릭으로 편집이 시작되고, 편집 모드가 꺼져 있으면 `editable: false`라 편집 불가.

- [ ] **Step 3: 브라우저에서 동작 확인**

1. 자산 목록에서 행 싱글클릭 → 우측 상세 패널 열림 (기존과 동일)
2. 편집 모드 켠 후 셀 더블클릭 → 인라인 편집 시작
3. 편집 모드 꺼진 상태에서 더블클릭 → 편집 안 됨

- [ ] **Step 4: Commit**

```bash
git add app/static/js/infra_assets.js
git commit -m "refactor(infra): switch asset grid to double-click edit"
```

---

### Task 3: 네비게이션 그리드 — 더블클릭 이동 전환 (프로젝트, 계약, 내사업)

**Files:**
- Modify: `app/static/js/infra_projects.js:65-83`
- Modify: `app/static/js/utils.js:1128-1156` (buildContractGridOptions)
- Modify: `app/static/js/contracts.js`
- Modify: `app/static/js/my_contracts.js`

#### 3-1. infra_projects.js

- [ ] **Step 1: 프로젝트 그리드 이동 동작을 더블클릭으로 전환**

`app/static/js/infra_projects.js`의 `initListGrids()`:

```javascript
// 변경 전:
gridApi = agGrid.createGrid(document.getElementById("grid-projects"), {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
    onRowClicked: (e) => {
      const d = e.data;
      if (d && d.id) {
        if (window.setCtxProject) {
          window.setCtxProject(d.id, d.period_code, d.contract_name);
        }
        window.location.href = "/periods/" + d.id;
      }
    },
});

// 변경 후:
gridApi = agGrid.createGrid(document.getElementById("grid-projects"), {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'navigate',
      onEdit: (d) => {
        if (window.setCtxProject) {
          window.setCtxProject(d.id, d.period_code, d.contract_name);
        }
        window.location.href = "/periods/" + d.id;
      },
    }),
});
```

#### 3-2. buildContractGridOptions (utils.js)

- [ ] **Step 2: 계약 목록 공용 그리드 옵션을 더블클릭 이동으로 전환**

`app/static/js/utils.js`의 `buildContractGridOptions`:

```javascript
// 변경 전:
    onCellClicked: (e) => {
      if (e.column.getColId() !== '0' && e.data?.id) {
        sessionStorage.setItem('contract-back', opts.backPath);
        window.location.href = `/contracts/${e.data.id}`;
      }
    },

// 변경 후:
    ...buildStandardGridBehavior({
      type: 'navigate',
      onEdit: (d) => {
        sessionStorage.setItem('contract-back', opts.backPath);
        window.location.href = `/contracts/${d.id}`;
      },
    }),
```

`onCellClicked` 전체를 제거하고 위 코드로 대체. `contracts.js`와 `my_contracts.js`는 `buildContractGridOptions`를 사용하므로 자동으로 적용됨.

- [ ] **Step 3: 브라우저에서 동작 확인**

1. 프로젝트 목록 — 싱글클릭: 행 하이라이트, 더블클릭: 상세 페이지 이동
2. 계약 목록 — 싱글클릭: 행 하이라이트, 더블클릭: 계약 상세 이동
3. 내 사업 목록 — 동일

- [ ] **Step 4: Commit**

```bash
git add app/static/js/infra_projects.js app/static/js/utils.js
git commit -m "refactor: switch navigation grids to double-click navigate"
```

---

### Task 4: 카탈로그, 역할, 시스템 그리드 — 더블클릭 편집 모달

**Files:**
- Modify: `app/static/js/infra_product_catalog.js:604-624`
- Modify: `app/static/js/infra_asset_roles.js:53-65`
- Modify: `app/static/js/system.js:93-115`
- Modify: `app/static/js/infra_catalog_integrity.js:246-260, 302-315`

이 그리드들은 싱글클릭→상세패널을 이미 가지고 있음. 더블클릭→편집 모달을 추가.

- [ ] **Step 1: infra_product_catalog.js — 더블클릭 시 제품 편집 모달**

`initCatalogGrid()`:

```javascript
// 변경 전:
    onRowClicked: (e) => selectProduct(e.data),

// 변경 후:
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => selectProduct(data),
      onEdit: (data) => openProductEditModal(data.id),
    }),
```

기존 `onRowClicked` 행 제거, 위 코드로 대체.

- [ ] **Step 2: infra_asset_roles.js — 더블클릭 시 역할 편집 모달**

`initRoleGrid()`:

```javascript
// 변경 전:
    onRowClicked: (e) => showRoleDetail(e.data),

// 변경 후:
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => showRoleDetail(data),
      onEdit: (data) => openRoleModal(data.id),
    }),
```

- [ ] **Step 3: system.js — 더블클릭 시 속성 편집 전환**

`initSystemAttrGrid()`:

```javascript
// 변경 전:
    rowSelection: { mode: "singleRow" },
    animateRows: true,
    enableCellTextSelection: true,
    onRowClicked: (event) => {
      if (event.data) setSystemAttrEditMode(event.data);
    },

// 변경 후:
    rowSelection: { mode: "singleRow" },
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => setSystemAttrEditMode(data),
    }),
```

system의 속성 편집은 이미 사이드 폼이므로 싱글클릭=폼 열기를 유지.

- [ ] **Step 4: infra_catalog_integrity.js — 벤더/제품 그리드에 더블클릭 추가**

`catalogIntegrityVendorGridApi`:

```javascript
// 변경 전:
    onRowClicked: (e) => { ... setIntegrityVendorEditMode(vendor, aliases, data); },

// 변경 후 (onRowClicked 내부 로직을 onSelect로, 더블클릭에 편집 전환):
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => {
        const vendor = data.vendor_canonical;
        const aliases = data.aliases || [];
        setIntegrityVendorEditMode(vendor, aliases, data);
      },
    }),
```

`integrityProductGridApi`:

```javascript
// 변경 전:
    onRowClicked: (e) => { openMdmSimilarPanel(e.data); },

// 변경 후:
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => openMdmSimilarPanel(data),
    }),
```

- [ ] **Step 5: 브라우저에서 동작 확인**

1. 제품 카탈로그 — 싱글클릭: 상세 패널, 더블클릭: 제품 편집 모달
2. 역할 목록 — 싱글클릭: 상세 패널, 더블클릭: 역할 편집 모달
3. 시스템 속성 — 싱글클릭: 편집 폼 (기존 유지)
4. 기준정보 벤더/제품 — 싱글클릭: 상세 패널

- [ ] **Step 6: Commit**

```bash
git add app/static/js/infra_product_catalog.js app/static/js/infra_asset_roles.js app/static/js/system.js app/static/js/infra_catalog_integrity.js
git commit -m "refactor: add double-click edit to catalog/role/system/integrity grids"
```

---

### Task 5: 인라인 편집 그리드 — singleClickEdit 제거 (contract_detail, partners, users)

**Files:**
- Modify: `app/static/js/contract_detail.js` (forecastApi, ledgerApi, receiptApi)
- Modify: `app/static/js/partners.js` (contractsGridApi, financialsGridApi, receiptsGridApi, contractContactGridApi)
- Modify: `app/static/js/users.js`

이 그리드들은 현재 `singleClickEdit: true`로 싱글클릭=즉시편집. 더블클릭 편집으로 전환.

- [ ] **Step 1: contract_detail.js — 3개 그리드에서 singleClickEdit 제거**

각 `agGrid.createGrid` 호출에서:

```javascript
// 변경: singleClickEdit: true → 삭제 또는 false
// ag-Grid 기본값이 singleClickEdit: false이므로 행 삭제만 하면 됨

// forecastApi (line ~1143):
// 삭제: singleClickEdit: true,

// ledgerApi (line ~1483):
// 삭제: singleClickEdit: true,

// receiptApi (line ~2743):
// 삭제: singleClickEdit: true,
```

`stopEditingWhenCellsLoseFocus: true`는 유지.

- [ ] **Step 2: partners.js — 4개 하위 그리드에서 singleClickEdit 제거**

```javascript
// contractsGridApi, financialsGridApi, receiptsGridApi, contractContactGridApi
// 각각에서 singleClickEdit: true 행 삭제
```

partners.js 메인 그리드(`gridApi`)는 현재 편집 기능이 없으므로 변경 불필요. 상세 패널 오픈 유지:

```javascript
// 변경 전:
    onRowClicked: (e) => {
      if (e.data?.id) selectPartner(e.data.id);
    },

// 변경 후:
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => selectPartner(data.id),
    }),
```

- [ ] **Step 3: users.js — 더블클릭 인라인 편집 전환**

users.js는 현재 `suppressRowClickSelection: true`로 싱글클릭 선택 안 함 + 체크박스 선택 사용. 이 패턴은 유지하되 `singleClickEdit`만 기본값(false)으로 되돌림.

users.js의 `gridOptions`:

```javascript
// 기존 그대로 유지 (singleClickEdit이 이미 없음, 기본값 false)
// 단, editable 컬럼에 대해 더블클릭으로 편집이 자동으로 됨
```

users.js는 이미 singleClickEdit을 명시하지 않으므로 변경 불필요. 확인만.

- [ ] **Step 4: 브라우저에서 동작 확인**

1. 계약 상세 — 매출예측/매출매입/입금 그리드: 싱글클릭=셀 선택, 더블클릭=셀 편집
2. 거래처 상세 — 관련사업/재무/입금 그리드: 동일
3. 사용자 관리 — 더블클릭으로 편집 (기존과 동일하면 OK)

- [ ] **Step 5: Commit**

```bash
git add app/static/js/contract_detail.js app/static/js/partners.js app/static/js/users.js
git commit -m "refactor: switch inline-edit grids to double-click edit"
```

---

### Task 6: 하위 탭 그리드 — 더블클릭 모달 편집 추가 (project_detail, ports, IPs, policies, contacts)

**Files:**
- Modify: `app/static/js/infra_project_detail.js`
- Modify: `app/static/js/infra_port_maps.js`
- Modify: `app/static/js/infra_ip_inventory.js`
- Modify: `app/static/js/infra_policies.js`
- Modify: `app/static/js/infra_contacts.js`

이 그리드들은 현재 편집을 cellRenderer 버튼(수정 아이콘) 또는 모달로 처리. 더블클릭으로도 동일 모달을 열 수 있게 추가.

- [ ] **Step 1: infra_project_detail.js — phase/deliverable 그리드에 더블클릭 모달**

phaseGridApi:

```javascript
// 변경 전:
    rowSelection: "single", ...

// 변경 후:
    rowSelection: "single",
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openPhaseModal(data),
    }),
```

deliverableGridApi:

```javascript
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openDeliverableModal(data),
    }),
```

- [ ] **Step 2: infra_port_maps.js — 더블클릭 시 편집 모달**

```javascript
// 변경 전 (cellRenderer 버튼으로만 편집):
    rowSelection: "single", ...

// 변경 후:
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openEditModal(data),
    }),
```

기존 cellRenderer의 수정 버튼은 그대로 유지 (두 가지 경로 모두 동작).

- [ ] **Step 3: infra_ip_inventory.js — 더블클릭 시 편집 모달**

```javascript
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openEditModal(data),
    }),
```

- [ ] **Step 4: infra_policies.js — 더블클릭 시 편집 모달**

```javascript
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openEditAssignment(data),
    }),
```

- [ ] **Step 5: infra_contacts.js — 더블클릭 시 편집 모달**

```javascript
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openContactModal(data),
    }),
```

- [ ] **Step 6: 브라우저에서 동작 확인**

1. 프로젝트 상세 — phase 행 더블클릭 → phase 편집 모달
2. 포트맵 — 행 더블클릭 → 포트맵 편집 모달
3. IP — 행 더블클릭 → IP 편집 모달
4. 정책 — 행 더블클릭 → 정책 할당 편집 모달
5. 업체 연락처 — 행 더블클릭 → 연락처 편집 모달

- [ ] **Step 7: Commit**

```bash
git add app/static/js/infra_project_detail.js app/static/js/infra_port_maps.js app/static/js/infra_ip_inventory.js app/static/js/infra_policies.js app/static/js/infra_contacts.js
git commit -m "refactor: add double-click modal edit to sub-tab grids"
```

---

### Task 7: 읽기 전용 그리드 — 표준 행동 적용 (변경 최소)

**Files:**
- Modify: `app/static/js/infra_audit_history.js`
- Modify: `app/static/js/infra_inventory_assets.js`
- Modify: `app/static/js/infra_policy_definitions.js`
- Modify: `app/static/js/infra_project_classifications.js`
- (dashboard, reports 그리드는 읽기 전용이고 onRowClicked가 없어 변경 불필요)

이 그리드들은 읽기 전용이므로 `buildStandardGridBehavior({ type: 'readonly' })`를 적용. 실질적 동작 변경은 없지만, 향후 기능 추가 시 일관된 패턴 기반이 됨.

- [ ] **Step 1: 읽기 전용 그리드에 표준 헬퍼 적용**

각 파일에서 `agGrid.createGrid` 호출에 추가:

```javascript
// infra_audit_history.js:
    ...buildStandardGridBehavior({ type: 'readonly' }),

// infra_inventory_assets.js:
    ...buildStandardGridBehavior({ type: 'readonly' }),

// infra_policy_definitions.js:
    ...buildStandardGridBehavior({ type: 'readonly' }),

// infra_project_classifications.js:
    ...buildStandardGridBehavior({ type: 'readonly' }),
```

- [ ] **Step 2: Commit**

```bash
git add app/static/js/infra_audit_history.js app/static/js/infra_inventory_assets.js app/static/js/infra_policy_definitions.js app/static/js/infra_project_classifications.js
git commit -m "refactor: apply standard readonly grid behavior"
```

---

### Task 8: 프론트엔드 가이드라인 문서 업데이트

**Files:**
- Modify: `docs/guidelines/frontend.md`

- [ ] **Step 1: frontend.md에 그리드 상호작용 표준 섹션 추가**

`docs/guidelines/frontend.md` 파일의 적절한 위치(ag-Grid 관련 섹션이 있다면 그 안, 없다면 파일 말미)에 추가:

```markdown
### ag-Grid 상호작용 표준

모든 ag-Grid는 `buildStandardGridBehavior()` 헬퍼(utils.js)를 사용하여 일관된 클릭 동작을 적용한다.

| 그리드 유형 | type 값 | 싱글클릭 | 더블클릭 |
|------------|---------|----------|----------|
| 마스터-디테일 | `detail-panel` | 상세 패널 열기 | 편집 (인라인 또는 모달) |
| 네비게이션 | `navigate` | 행 하이라이트 | 상세 페이지 이동 |
| 인라인 편집 | `inline-edit` | 행 선택 | 셀 인라인 편집 |
| 모달 편집 | `modal-edit` | 행 선택 | 편집 모달 열기 |
| 읽기 전용 | `readonly` | 행 선택 | 없음 |

- `singleClickEdit: true`는 사용하지 않는다. 모든 인라인 편집은 더블클릭으로 시작.
- 새 그리드를 추가할 때 반드시 `buildStandardGridBehavior()`를 사용한다.
- `onRowClicked`, `onRowDoubleClicked`를 직접 설정하지 않고 헬퍼를 통해 설정한다.
```

- [ ] **Step 2: Commit**

```bash
git add docs/guidelines/frontend.md
git commit -m "docs: add ag-Grid interaction standard to frontend guidelines"
```

---

## Self-Review Checklist

1. **Spec coverage:** 전체 40+ 그리드 대상, 모든 유형(마스터-디테일, 네비게이션, 인라인편집, 모달편집, 읽기전용)에 대한 표준 규칙 정의 및 적용 ✓
2. **Placeholder scan:** 모든 코드 블록에 실제 코드 포함, TBD/TODO 없음 ✓
3. **Type consistency:** `buildStandardGridBehavior` 함수명과 옵션 키(`type`, `onSelect`, `onEdit`, `onCellValueChanged`)가 전 태스크에서 일관 ✓
4. **기존 기능 보존:** cellRenderer 버튼(수정/삭제 아이콘)은 그대로 유지 — 더블클릭은 추가 경로 ✓
5. **사용자 요구:** 싱글클릭=정보, 더블클릭=편집/이동 — 모든 유형에 적용 ✓
