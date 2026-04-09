# Phase 1a: 포트맵 그리드 편집 모드 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 포트맵 그리드에 `GridEditMode`를 적용하여 단순 필드(connection_type, cable_no, cable_type, cable_speed, purpose, status)의 배치 편집을 지원한다.

**Architecture:** 백엔드에 bulk PATCH 엔드포인트를 추가하고, 프론트엔드에서 GridEditMode 인스턴스를 생성하여 연결한다. asset/interface 필드는 편집 모드에서도 기존 즉시 PATCH를 유지한다.

**Tech Stack:** Python/FastAPI/SQLAlchemy (백엔드), Vanilla JS + AG Grid + GridEditMode (프론트엔드)

**Spec:** `docs/superpowers/specs/2026-04-09-port-map-edit-mode-design.md`

---

## 파일 구조

| 파일 | 역할 | 변경 |
|---|---|---|
| `app/modules/infra/schemas/port_map.py` | bulk 스키마 추가 | 수정 |
| `app/modules/infra/services/network_service.py` | `bulk_update_port_maps()` 추가 | 수정 |
| `app/modules/infra/routers/port_maps.py` | `PATCH /bulk` 엔드포인트 추가 | 수정 |
| `app/modules/infra/templates/infra_port_maps.html` | 편집 모드 버튼/상태바 + script 태그 | 수정 |
| `app/static/js/infra_port_maps.js` | GridEditMode 인스턴스 + 핸들러 수정 | 수정 |

---

## Task 1: 백엔드 — bulk 스키마 + 서비스 + 라우터

**Files:**
- Modify: `app/modules/infra/schemas/port_map.py`
- Modify: `app/modules/infra/services/network_service.py`
- Modify: `app/modules/infra/routers/port_maps.py`

- [ ] **Step 1: bulk 스키마 추가**

`app/modules/infra/schemas/port_map.py` 맨 끝에 추가:

```python
class PortMapBulkUpdateItem(BaseModel):
    id: int
    changes: dict


class PortMapBulkUpdateRequest(BaseModel):
    items: list[PortMapBulkUpdateItem]
```

- [ ] **Step 2: bulk_update_port_maps() 서비스 함수 추가**

`app/modules/infra/services/network_service.py`에서 `delete_port_map()` 함수 뒤 (`# ── Private helpers ──` 앞)에 추가:

```python
def bulk_update_port_maps(
    db: Session,
    items: list,
    current_user,
) -> list[dict]:
    """여러 포트맵을 일괄 업데이트한다."""
    allowed_fields = set(PortMapUpdate.model_fields.keys())
    results: list[PortMap] = []
    for item in items:
        filtered = {k: v for k, v in item.changes.items() if k in allowed_fields}
        if not filtered:
            continue
        payload = PortMapUpdate(**filtered)
        updated = update_port_map(db, item.id, payload, current_user)
        results.append(updated)
    iface_map = build_interface_map(db, results)
    return [enrich_port_map(pm, iface_map) for pm in results]
```

이 함수의 import 의존성은 이미 파일 내에 모두 존재한다 (`PortMapUpdate`, `update_port_map`, `build_interface_map`, `enrich_port_map`, `PortMap`).

- [ ] **Step 3: bulk 라우터 엔드포인트 추가**

`app/modules/infra/routers/port_maps.py`에서:

import에 추가:
```python
from app.modules.infra.schemas.port_map import (
    PortMapBulkUpdateRequest,  # 추가
    PortMapCreate,
    PortMapRead,
    PortMapUpdate,
)
from app.modules.infra.services.network_service import (
    bulk_update_port_maps,  # 추가
    create_port_map,
    delete_port_map,
    get_port_map,
    list_port_maps_enriched,
    update_port_map,
)
```

`list_port_maps_endpoint` 함수 뒤, `create_port_map_endpoint` 함수 앞에 추가:

```python
@router.patch("/bulk", response_model=list[PortMapRead])
def bulk_update_port_maps_endpoint(
    payload: PortMapBulkUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PortMapRead]:
    results = bulk_update_port_maps(db, payload.items, current_user)
    return [PortMapRead(**pm) for pm in results]
```

**중요:** `/bulk` 경로는 `/{port_map_id}` 앞에 선언해야 FastAPI가 `"bulk"`를 정수로 파싱하려 하지 않는다.

- [ ] **Step 4: 구문 확인**

```bash
python -c "from app.modules.infra.routers.port_maps import router; print('OK')"
```

- [ ] **Step 5: Commit**

```bash
git add app/modules/infra/schemas/port_map.py app/modules/infra/services/network_service.py app/modules/infra/routers/port_maps.py
git commit -m "feat: PATCH /api/v1/port-maps/bulk endpoint for batch edit"
```

---

## Task 2: HTML — 편집 모드 UI 요소 + script 태그

**Files:**
- Modify: `app/modules/infra/templates/infra_port_maps.html`

- [ ] **Step 1: 편집 모드 버튼 추가**

현재 (line 18-20):
```html
  <div class="tab-nav-actions">
    <button class="btn btn-primary" id="btn-add-portmap">배선 등록</button>
  </div>
```

변경:
```html
  <div class="tab-nav-actions">
    <button class="btn btn-secondary btn-sm" id="btn-toggle-edit">편집</button>
    <button class="btn btn-primary btn-sm is-hidden" id="btn-save-edit">저장</button>
    <button class="btn btn-secondary btn-sm is-hidden" id="btn-cancel-edit">취소</button>
    <button class="btn btn-primary" id="btn-add-portmap">배선 등록</button>
  </div>
```

- [ ] **Step 2: edit-mode-bar 추가**

`portmaps-content` div (현재 line 39) 바로 앞에 추가:

```html
<div id="edit-mode-bar" class="edit-mode-bar is-hidden">
  <span class="edit-mode-label">편집 모드</span>
  <span class="edit-mode-count" id="edit-mode-count">변경 0건</span>
  <span class="edit-mode-errors is-hidden" id="edit-mode-errors">오류 0건</span>
  <span class="edit-mode-separator">|</span>
  <span class="edit-mode-selection is-hidden" id="edit-mode-selection"></span>
</div>
```

- [ ] **Step 3: script 태그에 grid_edit_mode.js 추가**

현재 (line 105-107):
```html
{% block scripts %}
<script src="/static/js/infra_port_maps.js"></script>
{% endblock %}
```

변경:
```html
{% block scripts %}
<script src="/static/js/grid_edit_mode.js"></script>
<script src="/static/js/infra_port_maps.js"></script>
{% endblock %}
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/infra/templates/infra_port_maps.html
git commit -m "feat: port map edit mode UI — buttons, status bar, script tag"
```

---

## Task 3: JS — GridEditMode 인스턴스 생성 + 핸들러 수정

이 태스크가 핵심. `infra_port_maps.js`를 수정하여 GridEditMode를 연결한다.

**Files:**
- Modify: `app/static/js/infra_port_maps.js`

- [ ] **Step 1: EDIT_MODE_FIELDS 상수 + editMode 변수 추가**

현재 (line 118-124):
```javascript
const EDITABLE_FIELDS = [
  "src_asset_name", "src_interface_name",
  "dst_asset_name", "dst_interface_name",
  "connection_type", "cable_no", "cable_type", "cable_speed", "purpose", "status",
];

let gridApi;
```

변경:
```javascript
const EDITABLE_FIELDS = [
  "src_asset_name", "src_interface_name",
  "dst_asset_name", "dst_interface_name",
  "connection_type", "cable_no", "cable_type", "cable_speed", "purpose", "status",
];

const EDIT_MODE_FIELDS = new Set([
  "connection_type", "cable_no", "cable_type", "cable_speed", "purpose", "status",
]);

let gridApi;
let editMode;
```

- [ ] **Step 2: rowSelection 변경 + GridEditMode 인스턴스 생성**

`initGrid()` 함수 내에서:

현재 (line 158):
```javascript
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
```

변경:
```javascript
    rowSelection: "multiple", animateRows: true, enableCellTextSelection: true,
```

gridApi 생성 직후 (line 164, `addCopyPasteHandler` 호출 전)에 추가:

```javascript
  editMode = new GridEditMode({
    gridApi,
    editableFields: EDIT_MODE_FIELDS,
    bulkEndpoint: () => `/api/v1/port-maps/bulk?partner_id=${getCtxPartnerId()}`,
    prefix: "portmap",

    onAfterSave: (results) => {
      for (const updated of results) {
        let node = null;
        gridApi.forEachNode((n) => { if (n.data?.id === updated.id) node = n; });
        if (node) Object.assign(node.data, updated);
      }
    },

    bulkApplyFields: [
      { field: "connection_type", label: "연결유형", type: "select",
        options: () => [
          { value: "physical", label: "physical" },
          { value: "logical", label: "logical" },
        ],
      },
      { field: "cable_type", label: "케이블", type: "select",
        options: () => ["SM", "MM", "UTP", "STP", "DAC", "other"]
          .map((v) => ({ value: v, label: v })),
      },
      { field: "cable_speed", label: "속도", type: "select",
        options: () => ["100M", "1G", "10G", "25G", "40G", "100G", "other"]
          .map((v) => ({ value: v, label: v })),
      },
      { field: "status", label: "상태", type: "select",
        options: () => Object.entries(PORTMAP_STATUS_MAP)
          .map(([v, l]) => ({ value: v, label: l })),
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

- [ ] **Step 3: 래퍼 함수 추가**

`initGrid()` 함수 앞 (line 153 앞)에 추가:

```javascript
async function portmapSaveEditMode() {
  if (!editMode) return;
  const result = await editMode.save();
  if (result.success && result.count > 0) {
    showToast(`${result.count}건 포트맵이 업데이트되었습니다.`);
    editMode.toggle(false);
  } else if (result.success && result.count === 0) {
    showToast("변경사항이 없습니다.", "info");
    editMode.toggle(false);
  }
}

function portmapCancelEditMode() {
  if (!editMode) return;
  editMode.cancel();
  editMode.toggle(false);
}
```

- [ ] **Step 4: handlePortMapCellChanged() 수정**

현재 (line 188-258)의 함수에서 맨 앞(field 변수 선언 뒤)에 편집 모드 분기를 추가:

현재:
```javascript
async function handlePortMapCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  const field = colDef.field;

  try {
    // Asset name cells: resolve to asset_id and update hostname
    if (field === "src_asset_name" || field === "dst_asset_name") {
```

변경:
```javascript
async function handlePortMapCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  const field = colDef.field;

  // 편집 모드: 단순 필드는 dirty 축적
  if (editMode && editMode.isActive() && EDIT_MODE_FIELDS.has(field)) {
    editMode.handleCellChange(event);
    return;
  }

  try {
    // Asset name cells: resolve to asset_id and update hostname
    if (field === "src_asset_name" || field === "dst_asset_name") {
```

- [ ] **Step 5: onPaste 콜백 수정**

현재 (line 168-181):
```javascript
    onPaste: (changes) => {
      // PATCH each changed row
      const rowIds = [...new Set(changes.map(c => c.rowIndex))];
      rowIds.forEach(ri => {
        const node = gridApi.getDisplayedRowAtIndex(ri);
        if (!node || !node.data || !node.data.id) return;
        const rowChanges = changes.filter(c => c.rowIndex === ri);
        const payload = {};
        rowChanges.forEach(c => { payload[c.field] = c.newValue; });
        apiFetch("/api/v1/port-maps/" + node.data.id, { method: "PATCH", body: payload })
          .catch(err => showToast(err.message, "error"));
      });
    },
```

변경:
```javascript
    onPaste: (changes) => {
      if (editMode && editMode.isActive()) {
        // 편집 모드: 단순 필드는 dirty 축적, asset/interface 필드는 무시
        for (const c of changes) {
          const node = gridApi.getDisplayedRowAtIndex(c.rowIndex);
          if (node?.data?.id && EDIT_MODE_FIELDS.has(c.field)) {
            editMode.markDirty(node.data.id, c.field, c.newValue, c.oldValue);
          }
        }
        gridApi.refreshCells({ force: true });
        return;
      }
      // 비편집 모드: 기존 동작 (개별 PATCH per row)
      const rowIds = [...new Set(changes.map(c => c.rowIndex))];
      rowIds.forEach(ri => {
        const node = gridApi.getDisplayedRowAtIndex(ri);
        if (!node || !node.data || !node.data.id) return;
        const rowChanges = changes.filter(c => c.rowIndex === ri);
        const payload = {};
        rowChanges.forEach(c => { payload[c.field] = c.newValue; });
        apiFetch("/api/v1/port-maps/" + node.data.id, { method: "PATCH", body: payload })
          .catch(err => showToast(err.message, "error"));
      });
    },
```

- [ ] **Step 6: 이벤트 리스너 추가**

파일 맨 끝(line 475 `window.addEventListener` 전)에 추가:

```javascript
document.getElementById("btn-save-edit").addEventListener("click", portmapSaveEditMode);
document.getElementById("btn-cancel-edit").addEventListener("click", portmapCancelEditMode);
```

- [ ] **Step 7: 구문 확인**

```bash
node -c app/static/js/infra_port_maps.js
```

- [ ] **Step 8: Commit**

```bash
git add app/static/js/infra_port_maps.js
git commit -m "feat: port map grid uses GridEditMode for batch editing"
```

---

## Task 4: 통합 검증

**Files:**
- 변경 없음 — 검증만

- [ ] **Step 1: 백엔드 구문 확인**

```bash
python -c "from app.modules.infra.routers.port_maps import router; print('OK')"
```

- [ ] **Step 2: 서버 실행 + 브라우저 수동 검증**

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | 편집 모드 진입 | 편집→숨김, 저장/취소→표시, 상태바 표시, bulk apply 드롭다운(연결유형/케이블/속도/상태) |
| 2 | 단순 필드 수정 (status 등) | dirty 셀 파란 배경, "변경 N건" 갱신 |
| 3 | asset/interface 수정 | 즉시 PATCH (기존 동작), dirty 미적재 |
| 4 | bulk apply (행 선택 → 상태 일괄 적용) | 선택 행에 적용, dirty 기록 |
| 5 | 저장 | PATCH /bulk → 성공 토스트 → 편집 모드 이탈 |
| 6 | 취소 | 원본 복원, 편집 모드 이탈 |
| 7 | paste (단순 필드, 편집 모드) | dirty 축적 |
| 8 | paste (비편집 모드) | 기존 동작 (개별 PATCH) |
| 9 | 모달 수정 버튼 | 기존 동작 유지 |
| 10 | "배선 등록" 버튼 | 기존 동작 유지 |

- [ ] **Step 3: 검증 결과 기록 + 수정이 있으면 Commit**

```bash
git add -A
git commit -m "fix: port map edit mode integration fixes"
```

---

## Task 5: 문서 갱신

**Files:**
- Modify: `docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`
- Modify: `docs/superpowers/specs/2026-04-09-port-map-edit-mode-design.md`

- [ ] **Step 1: 상위 로드맵에 Phase 1a 완료 기록**

`docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`에서 Phase 1a 행:

현재:
```
| **1a** | 포트맵 그리드 편집 모드 | 자체기능 | 적용 시점 |
```

변경:
```
| **1a** | 포트맵 그리드 편집 모드 | 자체기능 | **완료** |
```

- [ ] **Step 2: Phase 1a 설계 문서에 완료 상태 기록**

`docs/superpowers/specs/2026-04-09-port-map-edit-mode-design.md`의 1번째 줄:

변경 후:
```
> 2026-04-09 | 상태: **Phase 1a 완료** | 상위 설계: ...
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: mark Phase 1a (port map edit mode) complete"
```
