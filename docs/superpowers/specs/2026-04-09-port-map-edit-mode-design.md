# Phase 1a: 포트맵 그리드 편집 모드 상세 설계

> 2026-04-09 | 상위 설계: `docs/superpowers/specs/2026-04-09-grid-edit-mode-expansion-design.md`

---

## 1. 목적

포트맵 그리드(`infra_port_maps.js`)에 Phase 0에서 추출한 `GridEditMode` 클래스를 적용하여 배치 편집 기능을 추가한다.

---

## 2. 범위

### 2.1 GridEditMode 대상 필드 (dirty 축적 → bulk save)

| 필드 | 에디터 | 비고 |
|---|---|---|
| `connection_type` | agSelectCellEditor | ["physical", "logical"] |
| `cable_no` | text | 평문 입력 |
| `cable_type` | agSelectCellEditor | ["SM", "MM", "UTP", "STP", "DAC", "other"] |
| `cable_speed` | agSelectCellEditor | ["100M", "1G", "10G", "25G", "40G", "100G", "other"] |
| `purpose` | text | 평문 입력 |
| `status` | agSelectCellEditor | ["required", "open", "closed", "pending"] |

### 2.2 즉시 PATCH 유지 (기존 동작 그대로)

| 필드 | 이유 |
|---|---|
| `src_asset_name` | asset 변경 시 interface 초기화 캐스케이드 |
| `src_interface_name` | asset_id 의존 cascading editor |
| `dst_asset_name` | 위와 동일 |
| `dst_interface_name` | 위와 동일 |

편집 모드에서도 이 4개 필드는 변경 즉시 개별 PATCH → 그리드 리로드.

### 2.3 범위 밖

- 신규 행 추가/삭제 — 기존 모달 + "배선 등록" 버튼 유지
- 모달 전용 필드 (cable_request, cable_category, duplex, summary, protocol, port, note) — 편집 모드 대상 아님

---

## 3. 백엔드 변경

### 3.1 스키마 (`app/modules/infra/schemas/port_map.py`)

```python
class PortMapBulkUpdateItem(BaseModel):
    id: int
    changes: dict

class PortMapBulkUpdateRequest(BaseModel):
    items: list[PortMapBulkUpdateItem]
```

### 3.2 서비스 (`app/modules/infra/services/network_service.py`)

```python
def bulk_update_port_maps(
    db: Session,
    items: list[PortMapBulkUpdateItem],
    current_user: User,
    partner_id: int,
) -> list[dict]:
    """여러 포트맵을 일괄 업데이트한다."""
    allowed_fields = set(PortMapUpdate.model_fields.keys())
    results = []
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

### 3.3 라우터 (`app/modules/infra/routers/port_maps.py`)

```python
@router.patch("/bulk", response_model=list[PortMapRead])
def bulk_update_port_maps_endpoint(
    payload: PortMapBulkUpdateRequest,
    partner_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PortMapRead]:
    results = bulk_update_port_maps(db, payload.items, current_user, partner_id or 0)
    return results
```

---

## 4. 프론트엔드 변경

### 4.1 HTML (`app/modules/infra/templates/infra_port_maps.html`)

툴바에 편집 모드 버튼 추가:
```html
<button class="btn btn-secondary btn-sm" id="btn-toggle-edit">편집</button>
<button class="btn btn-primary btn-sm is-hidden" id="btn-save-edit">저장</button>
<button class="btn btn-secondary btn-sm is-hidden" id="btn-cancel-edit">취소</button>
```

그리드 위에 edit-mode-bar 추가:
```html
<div id="edit-mode-bar" class="edit-mode-bar is-hidden">
  <span class="edit-mode-label">편집 모드</span>
  <span class="edit-mode-count" id="edit-mode-count">변경 0건</span>
  <span class="edit-mode-errors is-hidden" id="edit-mode-errors">오류 0건</span>
  <span class="edit-mode-separator">|</span>
  <span class="edit-mode-selection is-hidden" id="edit-mode-selection"></span>
</div>
```

script 태그에 `grid_edit_mode.js` 추가 (`infra_port_maps.js` 앞).

### 4.2 JS (`app/static/js/infra_port_maps.js`)

#### GridEditMode 대상 필드 집합

```javascript
const EDIT_MODE_FIELDS = new Set([
  "connection_type", "cable_no", "cable_type", "cable_speed", "purpose", "status",
]);
```

#### rowSelection 변경

```javascript
rowSelection: "multiple",
```

#### GridEditMode 인스턴스 생성

```javascript
const editMode = new GridEditMode({
  gridApi,
  editableFields: EDIT_MODE_FIELDS,
  bulkEndpoint: () => `/api/v1/port-maps/bulk?partner_id=${getCtxPartnerId()}`,
  prefix: "portmap",

  bulkApplyFields: [
    { field: "connection_type", label: "연결유형", type: "select",
      options: () => [
        { value: "physical", label: "physical" },
        { value: "logical", label: "logical" },
      ],
    },
    { field: "cable_type", label: "케이블", type: "select",
      options: () => ["SM", "MM", "UTP", "STP", "DAC", "other"]
        .map(v => ({ value: v, label: v })),
    },
    { field: "cable_speed", label: "속도", type: "select",
      options: () => ["100M", "1G", "10G", "25G", "40G", "100G", "other"]
        .map(v => ({ value: v, label: v })),
    },
    { field: "status", label: "상태", type: "select",
      options: () => [
        { value: "required", label: "required" },
        { value: "open", label: "open" },
        { value: "closed", label: "closed" },
        { value: "pending", label: "pending" },
      ],
    },
  ],

  onAfterSave: (results) => {
    for (const updated of results) {
      let node = null;
      gridApi.forEachNode((n) => { if (n.data?.id === updated.id) node = n; });
      if (node) Object.assign(node.data, updated);
    }
  },

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

#### handlePortMapCellChanged() 수정

```
handlePortMapCellChanged(event):
  1. field가 EDIT_MODE_FIELDS에 있고 editMode.isActive()면:
     → editMode.handleCellChange(event) + return
  2. 아니면 기존 로직 (asset/interface 즉시 PATCH)
```

#### onPaste 콜백 수정

```
onPaste(changes):
  1. editMode.isActive()가 아니면 → 기존 동작 (개별 PATCH per row)
  2. editMode.isActive()면:
     → 각 change에 대해:
        - field가 EDIT_MODE_FIELDS이고 row.id가 있으면 → editMode.markDirty()
        - field가 asset/interface면 → 무시 (paste로 asset/interface 변경 불가)
```

#### 저장/취소 래퍼

포트맵은 신규 행 관리가 없으므로 래퍼가 단순:

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

---

## 5. 검증

### 5.1 백엔드 테스트 (`tests/infra/test_port_map_service.py`)

- `bulk_update_port_maps()` — 다건 업데이트 + enriched 결과 확인
- allowed_fields 필터 동작 확인

### 5.2 수동 체크리스트 (브라우저)

| # | 시나리오 | 기대 결과 |
|---|---|---|
| 1 | 편집 모드 진입 | 버튼 전환, 상태바, bulk UI 생성 |
| 2 | 단순 필드 수정 (status 등) | dirty 표시, 카운트 갱신 |
| 3 | asset/interface 수정 | 즉시 PATCH (기존 동작), dirty 미적재 |
| 4 | bulk apply (행 선택 → 상태 일괄 적용) | 선택 행에 적용, dirty |
| 5 | 저장 | PATCH /bulk → 성공 → 편집 모드 이탈 |
| 6 | 취소 | 원본 복원, 편집 모드 이탈 |
| 7 | paste (단순 필드) | dirty 축적 |
| 8 | paste (비편집 모드) | 기존 동작 (개별 PATCH) |

---

## 6. 비변경 사항

- `grid_edit_mode.js` — 변경 없음
- 모달 편집 — 기존 동작 유지
- "배선 등록" 버튼 — 기존 동작 유지
- CSS — 기존 `infra_common.css` 스타일 그대로 사용
