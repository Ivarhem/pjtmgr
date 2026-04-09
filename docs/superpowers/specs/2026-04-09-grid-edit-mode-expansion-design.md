# GridEditMode 공통 모듈 추출 + 그리드 편집 확산 설계

> 2026-04-09 | 상태: 로드맵 선언 완료, Phase 0 상세 설계는 지침 재검토 후 진행

---

## 1. 배경 및 목적

자산 그리드(`infra_assets.js`)에서 안정화된 배치 편집 모드 패턴을 다른 독립 페이지 그리드에 확산한다.
현재 편집 모드 로직은 자산 그리드에 인라인으로 존재하며, 다른 그리드에는 편집 모드가 없다.

**목적:**
- 공통 `GridEditMode` 클래스를 추출하여 중복 없이 편집 모드를 확산
- 사용자 편의성(bulk apply, dirty tracking, 셀 검증)을 모든 주요 그리드에 일관되게 제공
- 메인 그리드에서 패턴을 검증한 후, 서브그리드로 확산

---

## 2. 데이터 모델 원칙

**Asset = 허브 구조:**

```
Asset (허브)
  ├── AssetInterface (asset_id FK, CASCADE) → 1:N
  │     ├── AssetIP (interface_id FK, CASCADE) → 1:N
  │     └── PortMap (src/dst_interface_id FK) → N:N
  ├── AssetRoleAssignment (asset_id FK) → N:M via junction
  ├── AssetContact (asset_id FK) → N:M via junction
  ├── AssetRelatedPartner (asset_id FK) → N:M
  └── AssetRelation (src/dst_asset_id) → N:N self-ref
```

- 각 도메인(포트맵, IP, 역할, 연락처)이 **자체 테이블을 소유**하고, `asset_id`/`interface_id` FK로 연결
- **입력 진입점은 복수:** 자산상세 UI에서 인터페이스를 등록하면 `asset_interfaces` 테이블에 생성되고, 포트맵 화면에서 연결하면 `port_maps` 테이블에 생성. 같은 데이터를 다른 진입점에서 조작 가능
- 카탈로그-라이선스 연결 패턴과 동일한 구조

---

## 3. GridEditMode 공통 클래스 설계

### 3.1 파일 위치

`app/static/js/grid_edit_mode.js`

### 3.2 클래스 인터페이스

```javascript
const editMode = new GridEditMode({
  // 필수
  gridApi: gridApi,
  editableFields: new Set(["field1", "field2", ...]),
  bulkApiEndpoint: "/api/v1/{domain}/bulk",

  // 선택
  requiredFields: new Set(["field1"]),
  validators: {
    fieldName: (value, rowData) => errorMessage | null,
  },
  bulkApplyFields: [
    { field: "status", label: "상태", options: () => [...] },
    { field: "center_id", label: "센터", options: () => [...] },
  ],
  selectors: {
    toggleBtn: "#btn-toggle-edit",
    saveBtn: "#btn-save-edit",
    cancelBtn: "#btn-cancel-edit",
    statusBar: "#edit-mode-bar",
    changeCount: "#edit-mode-count",
    errorCount: "#edit-mode-errors",
  },

  // 콜백 (선택)
  onBeforeSave: (dirtyRows) => transformedPayload,
  onAfterSave: (results) => void,
  onModeChange: (isEditMode) => void,
});
```

### 3.3 공통 클래스 책임

| 책임 | 설명 |
|---|---|
| 상태 관리 | `dirtyRows`, `originalValues`, `errorCells` Map 관리 |
| toggle | 편집 모드 진입/이탈, `edit-mode-active` body class 토글 |
| markDirty | 셀 변경 추적, 원본 복원 시 dirty 제거 |
| validate | 필수 필드 + 커스텀 validator 실행 |
| save | dirty rows 수집 → bulk API PATCH → 결과 반영 → 모드 이탈 |
| cancel | originalValues로 복원 → dirty 초기화 → 모드 이탈 |
| 상태바 | 변경 N건 / 오류 N건 자동 갱신 |
| 버튼 토글 | 편집/저장/취소 버튼 show/hide |
| bulk apply | `bulkApplyFields` 선언 기반 드롭다운 UI 자동 생성, 선택된 행에 일괄 적용 |
| 셀 스타일링 | `getCellClass(field, row)` → dirty/error/readonly CSS 클래스 반환 |
| copy/paste | 기존 `addCopyPasteHandler()` 통합 또는 위임 |

### 3.4 그리드별 선언 범위

각 그리드 JS 파일이 책임지는 것:
- `editableFields`, `requiredFields` 목록
- 필드별 커스텀 `validators`
- `bulkApiEndpoint` URL
- `bulkApplyFields` (해당 도메인의 일괄 적용 대상 필드와 옵션 소스)
- 셀렉터 매핑 (HTML 구조에 따라)
- `onBeforeSave` / `onAfterSave` 콜백 (도메인별 변환 로직)

---

## 4. 로드맵

### 진행 순서

```
로드맵 선언 (이 문서) → 지침 재검토 → Phase 0 상세 설계/구현 → Phase 1 → ...
```

### Phase 개요

| Phase | 범위 | 유형 | 설계 시점 |
|---|---|---|---|
| **0** | `GridEditMode` 공통 클래스 추출 + 자산 그리드 리팩토링 | 기반 작업 | **완료** |
| **1a** | 포트맵 그리드 편집 모드 | 자체기능 | **완료** |
| **1b** | IP 인벤토리 그리드 편집 모드 | 자체기능 | 적용 시점 |
| **1c** | 물리배치 그리드 편집 모드 | 자체기능 | 적용 시점 |
| **2a** | 연락처 그리드 편집 모드 | 공통기능 | Phase 1 검증 후 |
| **2b** | 역할 관리 그리드 편집 모드 | 공통기능 | Phase 1 검증 후 |
| **3** | 서브그리드 확산 (자산상세 내 탭) | 공통 UI | Phase 2 이후 |

- **Phase 1~2 순서는 가변적.** 상황에 따라 조정.
- **Phase 1 (자체기능):** 메인 그리드에 `GridEditMode` 인스턴스 생성 + 도메인별 config 선언. 복붙 허용.
- **Phase 2 (공통기능):** Phase 1에서 검증된 패턴 그대로 적용.
- **Phase 3 (서브그리드):** 공통 UI 컴포넌트 형태. 복붙 금지, `GridEditMode` 직접 재사용 원칙.

### 각 Phase별 백엔드 작업

각 그리드에 편집 모드를 적용할 때 필요한 백엔드:
- `PATCH /api/v1/{domain}/bulk` 엔드포인트
- `{Domain}BulkUpdateItem`, `{Domain}BulkUpdateRequest` 스키마
- `bulk_update_{domain}()` 서비스 함수

자산 그리드의 기존 bulk API 패턴(`AssetBulkUpdateRequest` → `bulk_update_assets()`)을 따른다.

---

## 5. 검증 전략

- **백엔드:** pytest — bulk API 엔드포인트 단위/통합 테스트
- **프론트엔드:** 브라우저 수동 체크리스트
  - 편집 모드 진입/이탈
  - 셀 수정 → dirty 표시 (파란 배경)
  - 필수 필드 비우기 → error 표시 (빨간 배경)
  - bulk apply → 선택 행에 값 일괄 적용
  - 저장 → 서버 반영 확인
  - 취소 → 원본 복원 확인
  - copy/paste 동작

### 선행 작업: 지침 재검토

Phase 0 착수 전에 pytest 및 개발 프로세스 전반을 감사한다.
테스트 통과 보고 후 실제 검증에서 문제가 반복되었던 패턴을 식별하고 지침을 개선한다.

---

## 6. 대상 파일 참조

### 현재 (추출 원본)
- `app/static/js/infra_assets.js` — 편집 모드 로직 원본
- `app/static/css/infra_common.css` — dirty/error 셀 스타일
- `app/modules/infra/templates/infra_assets.html` — 편집 모드 UI
- `app/modules/infra/routers/assets.py` — PATCH `/bulk` 엔드포인트
- `app/modules/infra/schemas/asset.py` — `AssetBulkUpdateRequest`
- `app/modules/infra/services/asset_service.py` — `bulk_update_assets()`

### 확산 대상 (메인 그리드)
- `app/static/js/infra_port_maps.js` — 포트맵
- `app/static/js/infra_ip_inventory.js` — IP 인벤토리
- `app/static/js/infra_asset_roles.js` — 역할 관리
- `app/static/js/infra_contacts.js` — 연락처

### 생성 예정
- `app/static/js/grid_edit_mode.js` — 공통 클래스
