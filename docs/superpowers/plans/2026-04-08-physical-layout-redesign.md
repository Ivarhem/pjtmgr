# 배치 페이지 재설계 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 배치 페이지를 3컬럼 테이블에서 트리 탐색 + 랙/장비 시각화 배치도(드래그 포함)로 전환한다.

**Architecture:** 백엔드(모델 필드 추가 + 마이그레이션 + 랙 자산 API)를 먼저 구현하고, 프론트엔드(트리 + 전산실 뷰 + 랙 뷰 + 드래그)를 순차 구축한다. 역할 기준 보기 페이지의 트리 패턴을 참조한다.

**Tech Stack:** Python/FastAPI/SQLAlchemy/Alembic, Vanilla JS, HTML5 Drag & Drop, CSS

**Spec:** `docs/superpowers/specs/2026-04-08-physical-layout-redesign.md`

---

## 파일 구조

### 신규 생성

| 파일 | 역할 |
|------|------|
| `alembic/versions/0068_physical_layout_fields.py` | 마이그레이션 |

### 주요 수정

| 파일 | 변경 |
|------|------|
| `app/modules/infra/models/room.py` | `racks_per_row` 필드 추가 |
| `app/modules/infra/models/rack.py` | `sort_order` 필드 추가 |
| `app/modules/infra/models/asset.py` | `rack_start_unit`, `rack_end_unit` 필드 추가 |
| `app/modules/common/models/contract_period.py` | `rack_label_base` 필드 추가 |
| `app/modules/infra/schemas/room.py` | `racks_per_row` 필드 추가 |
| `app/modules/infra/schemas/rack.py` | `sort_order` 필드 추가 |
| `app/modules/infra/services/layout_service.py` | 랙 자산 목록, 벌크 reorder |
| `app/modules/infra/routers/racks.py` | 랙 자산 엔드포인트, reorder 엔드포인트 |
| `app/modules/infra/templates/infra_physical_layout.html` | 전면 재작성 |
| `app/static/js/infra_physical_layout.js` | 전면 재작성 |
| `app/static/css/infra_common.css` | 랙 카드, U 다이어그램, 드래그 스타일 |

---

## Task 1: 백엔드 — 모델 필드 추가 + 마이그레이션

**Files:**
- Modify: `app/modules/infra/models/room.py`
- Modify: `app/modules/infra/models/rack.py`
- Modify: `app/modules/infra/models/asset.py`
- Modify: `app/modules/common/models/contract_period.py`
- Modify: `app/modules/infra/schemas/room.py` (Create/Update/Read)
- Modify: `app/modules/infra/schemas/rack.py` (Create/Update/Read)
- Create: `alembic/versions/0068_physical_layout_fields.py`

- [ ] **Step 1:** Room 모델에 `racks_per_row: Mapped[int] = mapped_column(Integer, default=6)` 추가
- [ ] **Step 2:** Rack 모델에 `sort_order: Mapped[int] = mapped_column(Integer, default=0)` 추가
- [ ] **Step 3:** Asset 모델에 `rack_start_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)`, `rack_end_unit: Mapped[int | None] = mapped_column(Integer, nullable=True)` 추가
- [ ] **Step 4:** ContractPeriod 모델에 `rack_label_base: Mapped[str] = mapped_column(String(10), default="start")` 추가
- [ ] **Step 5:** Room 스키마 — RoomCreate에 `racks_per_row: int = 6`, RoomUpdate에 `racks_per_row: int | None = None`, RoomRead에 `racks_per_row: int = 6`
- [ ] **Step 6:** Rack 스키마 — RackUpdate에 `sort_order: int | None = None`, RackRead에 `sort_order: int = 0`
- [ ] **Step 7:** Alembic 마이그레이션 0068 작성 — rooms에 racks_per_row, racks에 sort_order, assets에 rack_start_unit/rack_end_unit, contract_periods에 rack_label_base
- [ ] **Step 8:** `alembic upgrade head` 실행 확인
- [ ] **Step 9:** 커밋 `feat(infra): add physical layout fields (racks_per_row, sort_order, rack units, label base)`

---

## Task 2: 백엔드 — 랙 자산 API + 벌크 reorder

**Files:**
- Modify: `app/modules/infra/services/layout_service.py`
- Modify: `app/modules/infra/routers/racks.py`

- [ ] **Step 1:** layout_service.py에 `list_rack_assets(db, rack_id)` 함수 추가 — Asset을 rack_id로 필터, rack_start_unit 순 정렬, 자산 기본 정보 + rack_start_unit/rack_end_unit/size_unit/status/environment 반환
- [ ] **Step 2:** layout_service.py에 `reorder_racks(db, rack_orders, current_user)` 함수 추가 — `[{id, sort_order}]` 리스트를 받아 벌크 업데이트
- [ ] **Step 3:** racks.py 라우터에 `GET /api/v1/racks/{rack_id}/assets` 엔드포인트 추가
- [ ] **Step 4:** racks.py 라우터에 `PATCH /api/v1/racks/reorder` 엔드포인트 추가 — body: `[{id: int, sort_order: int}]`
- [ ] **Step 5:** 테스트 실행 — `pytest tests/infra/ -k "layout" -v`
- [ ] **Step 6:** 커밋 `feat(infra): add rack assets endpoint and bulk reorder API`

---

## Task 3: 프론트엔드 — HTML 트리+패널 레이아웃

**Files:**
- Rewrite: `app/modules/infra/templates/infra_physical_layout.html`

현재 188줄 3컬럼 테이블을 역할 기준 보기 패턴의 좌우 분할 레이아웃으로 교체.

- [ ] **Step 1:** HTML 전면 재작성

```html
{% extends "base.html" %}
{% block title %}배치 - 프로젝트관리{% endblock %}

{% block styles %}
<link rel="stylesheet" href="/static/css/infra_common.css">
{% endblock %}

{% block content %}
<div class="page-header">
  <h1><i data-lucide="layout-grid" class="icon-sm"></i> 배치</h1>
  <div class="infra-inline-actions">
    <label class="chk-inline" title="U 라벨 기준">
      <select id="rack-label-base" class="select-sm">
        <option value="start">U 기준: Start (하→상)</option>
        <option value="end">U 기준: End (상→하)</option>
      </select>
    </label>
    <button class="btn btn-secondary" id="btn-add-center">센터 등록</button>
  </div>
</div>

<div class="layout-split-panel">
  <!-- 좌측: 트리 -->
  <div class="layout-tree-panel">
    <div class="layout-tree-header">
      <span class="layout-tree-title">배치 구조</span>
    </div>
    <div id="layout-tree" class="layout-tree-root">
      <p class="text-muted" style="padding:12px;">고객사를 선택하면 배치 구조를 표시합니다.</p>
    </div>
  </div>

  <!-- 우측: 콘텐츠 -->
  <div class="layout-content-panel" id="layout-content">
    <div class="placeholder-message">
      <p>왼쪽 트리에서 센터, 전산실 또는 랙을 선택하세요.</p>
    </div>
  </div>
</div>

<!-- 센터/전산실/랙 모달 (기존 유지) -->
<!-- modal-center, modal-room, modal-rack -->
```

기존 모달 HTML(modal-center, modal-room, modal-rack)은 유지하되 Room 모달에 `racks_per_row` 필드 추가.

- [ ] **Step 2:** Room 모달에 `racks_per_row` 필드 추가

```html
<label>한 행 당 랙 수
  <input type="number" id="room-racks-per-row" min="1" max="20" value="6">
</label>
```

- [ ] **Step 3:** 커밋 `feat(ui): rewrite physical layout HTML with tree + content panel`

---

## Task 4: 프론트엔드 — 트리 빌드 + 뷰 전환

**Files:**
- Rewrite: `app/static/js/infra_physical_layout.js`

현재 406줄을 전면 재작성. 트리 구축 + 뷰 전환 로직.

- [ ] **Step 1:** 트리 데이터 로드 및 빌드

```javascript
// 상태 변수
let _centers = [];
let _treeData = {}; // { centerId: { center, floors: { floorName: { rooms: [room...] } } } }
let _selectedNode = null; // { type: "center"|"floor"|"room"|"rack", id, data }

async function loadTree() {
  const cid = getCtxPartnerId();
  if (!cid) { renderEmptyTree(); return; }

  _centers = await apiFetch("/api/v1/centers?partner_id=" + cid);
  _treeData = {};

  for (const center of _centers) {
    const rooms = await apiFetch("/api/v1/centers/" + center.id + "/rooms");
    const floors = {};
    for (const room of rooms) {
      const floorKey = room.floor || "기본층";
      if (!floors[floorKey]) floors[floorKey] = { name: floorKey, rooms: [] };
      // 각 room에 racks도 로드
      room._racks = await apiFetch("/api/v1/rooms/" + room.id + "/racks");
      floors[floorKey].rooms.push(room);
    }
    _treeData[center.id] = { center, floors };
  }

  renderTree();
}
```

- [ ] **Step 2:** 트리 렌더링 — 역할 기준 보기의 `renderRoleTree()` 패턴 참조

각 노드를 `classification-tree-*` CSS 클래스를 재활용하여 렌더. 센터 > 층(가상) > 전산실 > 랙 4단계.

- [ ] **Step 3:** 노드 클릭 시 뷰 전환

```javascript
function selectNode(type, id, data) {
  _selectedNode = { type, id, data };
  highlightTreeNode(type, id);
  const content = document.getElementById("layout-content");
  content.textContent = "";

  if (type === "center") renderCenterView(content, data);
  else if (type === "floor") renderFloorView(content, data);
  else if (type === "room") renderRoomView(content, data);
  else if (type === "rack") renderRackView(content, data);
}
```

- [ ] **Step 4:** 센터 뷰 / 층 뷰 — 기본정보 + 하위 요약 카드 목록

- [ ] **Step 5:** 이벤트 리스너 + ctx-changed 연동

- [ ] **Step 6:** 커밋 `feat(ui): implement layout tree navigation with view switching`

---

## Task 5: 프론트엔드 — 전산실 뷰 (랙 배치도 + 드래그)

**Files:**
- Modify: `app/static/js/infra_physical_layout.js` (renderRoomView 추가)
- Modify: `app/static/css/infra_common.css` (랙 카드 스타일)

- [ ] **Step 1:** renderRoomView 구현 — 전산실 기본정보 + 랙 격자

```javascript
async function renderRoomView(container, room) {
  // 헤더: 전산실명, racks_per_row 표시, "랙 추가" 버튼
  // 랙 격자: room._racks를 sort_order 순으로 정렬, racks_per_row 기준 행 나눔
  // 각 랙 카드: 랙명, 사용률 바, 클릭 시 selectNode("rack", ...)
}
```

- [ ] **Step 2:** 랙 카드 HTML/CSS

```css
.rack-grid { display: grid; gap: 12px; }
.rack-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.rack-card:hover { border-color: var(--primary-color); }
.rack-card.is-selected { border-color: var(--primary-color); background: var(--primary-bg); }
.rack-card-name { font-weight: 600; font-size: 13px; }
.rack-card-usage { font-size: 11px; color: var(--text-color-secondary); margin-top: 4px; }
.rack-usage-bar { height: 4px; background: var(--border-color); border-radius: 2px; margin-top: 4px; }
.rack-usage-bar-fill { height: 100%; border-radius: 2px; background: var(--primary-color); }
```

- [ ] **Step 3:** 드래그 재배치 구현

```javascript
function enableRackDrag(rackCards) {
  rackCards.forEach(card => {
    card.draggable = true;
    card.addEventListener("dragstart", (e) => {
      e.dataTransfer.setData("text/plain", card.dataset.rackId);
      card.classList.add("is-dragging");
    });
    card.addEventListener("dragend", () => card.classList.remove("is-dragging"));
    card.addEventListener("dragover", (e) => { e.preventDefault(); card.classList.add("drag-over"); });
    card.addEventListener("dragleave", () => card.classList.remove("drag-over"));
    card.addEventListener("drop", async (e) => {
      e.preventDefault();
      card.classList.remove("drag-over");
      const draggedId = Number(e.dataTransfer.getData("text/plain"));
      const targetId = Number(card.dataset.rackId);
      if (draggedId === targetId) return;
      await reorderRacks(draggedId, targetId);
    });
  });
}

async function reorderRacks(draggedId, targetId) {
  // 현재 순서에서 draggedId를 targetId 앞으로 이동
  // 새 sort_order 계산 후 PATCH /api/v1/racks/reorder
  // 성공 시 renderRoomView 재호출
}
```

- [ ] **Step 4:** 드래그 CSS

```css
.rack-card.is-dragging { opacity: 0.5; }
.rack-card.drag-over { border-color: var(--primary-color); border-style: dashed; }
```

- [ ] **Step 5:** 커밋 `feat(ui): implement room view with rack grid and drag reorder`

---

## Task 6: 프론트엔드 — 랙 뷰 (장비 배치도 + 드래그)

**Files:**
- Modify: `app/static/js/infra_physical_layout.js` (renderRackView 추가)
- Modify: `app/static/css/infra_common.css` (U 다이어그램 스타일)

- [ ] **Step 1:** renderRackView 구현 — 랙 기본정보 + U 다이어그램

```javascript
async function renderRackView(container, rack) {
  const assets = await apiFetch("/api/v1/racks/" + rack.id + "/assets");
  const totalU = rack.total_units || 42;
  const labelBase = document.getElementById("rack-label-base").value || "start";

  // 헤더: 랙명, 전체 U, 사용률
  // U 다이어그램: totalU 개의 슬롯을 세로로 렌더
  // 배치된 장비: rack_start_unit ~ rack_end_unit 범위에 블록 표시
  // 미배치 장비: rack_start_unit이 null인 장비는 하단 미배치 영역
}
```

- [ ] **Step 2:** U 다이어그램 HTML 구조

```javascript
function buildUDiagram(totalU, assets, labelBase) {
  // U 슬롯 맵: { unitNumber: asset | null }
  const slotMap = {};
  for (let u = 1; u <= totalU; u++) slotMap[u] = null;

  const placed = assets.filter(a => a.rack_start_unit != null);
  const unplaced = assets.filter(a => a.rack_start_unit == null);

  placed.forEach(a => {
    for (let u = a.rack_start_unit; u <= (a.rack_end_unit || a.rack_start_unit); u++) {
      slotMap[u] = a;
    }
  });

  // DOM 생성: 세로 그리드
  // labelBase === "start" → U 번호 1(하)→totalU(상), 표시는 상→하
  // labelBase === "end" → U 번호 totalU(하)→1(상), 표시도 상→하
}
```

- [ ] **Step 3:** 장비 블록 렌더

각 배치된 장비는 `rack_start_unit`~`rack_end_unit` 범위에 걸쳐 하나의 블록으로 표시. 높이 = (end - start + 1) × 슬롯 높이. 환경별 색상 (prod=파랑, dev=초록, staging=노랑).

- [ ] **Step 4:** 장비 드래그 배치 구현

```javascript
function enableEquipmentDrag(diagram) {
  // 장비 블록: draggable
  // U 슬롯: drop zone
  // 미배치 아이템: draggable
  // 드래그 중: 해당 size_unit 만큼 연속 빈 U 체크 → 가능하면 초록 하이라이트
  // 드롭: PATCH /api/v1/assets/{id} with rack_start_unit, rack_end_unit
  // 미배치 영역으로 드롭: rack_start_unit = null, rack_end_unit = null
}
```

- [ ] **Step 5:** 충돌 검사

```javascript
function canPlaceAt(slotMap, startU, sizeUnit, excludeAssetId) {
  for (let u = startU; u < startU + sizeUnit; u++) {
    if (u > totalU) return false;
    const occupant = slotMap[u];
    if (occupant && occupant.id !== excludeAssetId) return false;
  }
  return true;
}
```

- [ ] **Step 6:** U 다이어그램 CSS

```css
.u-diagram { display: flex; flex-direction: column; border: 1px solid var(--border-color); border-radius: 8px; overflow: hidden; }
.u-diagram-header { padding: 8px 12px; font-weight: 600; font-size: 13px; background: var(--surface-color); border-bottom: 1px solid var(--border-color); }
.u-slot { display: flex; align-items: center; height: 24px; border-bottom: 1px solid var(--border-color-light); font-size: 11px; }
.u-slot-number { width: 36px; text-align: center; color: var(--text-color-secondary); flex-shrink: 0; }
.u-slot-content { flex: 1; min-height: 24px; }
.u-slot.drop-ok { background: rgba(34, 197, 94, 0.1); }
.u-slot.drop-no { background: rgba(220, 53, 69, 0.06); }

.equipment-block {
  background: var(--primary-bg);
  border: 1px solid var(--primary-color);
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 11px;
  cursor: grab;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.equipment-block.env-prod { border-color: #2563eb; background: rgba(37, 99, 235, 0.08); }
.equipment-block.env-dev { border-color: #16a34a; background: rgba(22, 163, 74, 0.08); }
.equipment-block.env-staging { border-color: #ca8a04; background: rgba(202, 138, 4, 0.08); }

.unplaced-section { border-top: 2px dashed var(--border-color); padding: 12px; margin-top: 8px; }
.unplaced-item { padding: 4px 8px; margin: 2px 0; background: var(--bg-color); border: 1px solid var(--border-color-light); border-radius: 4px; cursor: grab; font-size: 12px; }
```

- [ ] **Step 7:** 커밋 `feat(ui): implement rack view with U diagram and equipment drag placement`

---

## Task 7: 라벨 기준 토글 + CRUD 연동

**Files:**
- Modify: `app/static/js/infra_physical_layout.js`

- [ ] **Step 1:** 라벨 기준 토글 — 페이지 로드 시 프로젝트의 `rack_label_base` 설정을 읽어 기본값 설정. 토글 변경 시 다이어그램 재렌더만 (데이터 변경 없음).

```javascript
async function loadLabelBaseSetting() {
  const pid = getCtxProjectId();
  if (!pid) return;
  try {
    const period = await apiFetch("/api/v1/contract-periods/" + pid);
    if (period.rack_label_base) {
      document.getElementById("rack-label-base").value = period.rack_label_base;
    }
  } catch { /* 기본값 유지 */ }
}

document.getElementById("rack-label-base").addEventListener("change", () => {
  if (_selectedNode?.type === "rack") renderRackView(document.getElementById("layout-content"), _selectedNode.data);
});
```

- [ ] **Step 2:** 센터/전산실/랙 CRUD 연동 — 기존 모달 로직(openCenterModal, saveCenter, deleteCenter 등)을 트리 + 뷰와 연결

- [ ] **Step 3:** "전산실 추가" / "랙 추가" 버튼을 우측 뷰 헤더에 배치 (센터 뷰에서 전산실 추가, 전산실 뷰에서 랙 추가)

- [ ] **Step 4:** CRUD 후 트리 새로고침

- [ ] **Step 5:** 커밋 `feat(ui): wire label toggle, CRUD modals, and tree refresh`

---

## Task 8: 문서 갱신

**Files:**
- Modify: `docs/guidelines/infra.md`
- Modify: `docs/PROJECT_STRUCTURE.md`

- [ ] **Step 1:** infra.md에 배치 페이지 구조 설명 추가 (트리 + 시각화), `rack_label_base` 프로젝트 설정 언급
- [ ] **Step 2:** PROJECT_STRUCTURE.md — 파일 변경 반영 (모델 필드 추가 사항은 코드가 source of truth이므로 불필요)
- [ ] **Step 3:** 커밋 `docs: update guidelines for physical layout redesign`
