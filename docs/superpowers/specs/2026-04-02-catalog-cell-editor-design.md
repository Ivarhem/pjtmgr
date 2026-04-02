# 자산 카탈로그 선택 UX 변경 설계

> 자산의 모델/제조사/분류 정보를 카탈로그 기준으로 통합 관리하고,
> 모든 편집 컨텍스트(상세 패널, 그리드)에서 카탈로그 검색/선택 방식을 적용한다.

## 목표

1. 자산의 vendor/model/category를 카탈로그 파생 읽기 전용 캐시로 전환
2. 상세 패널 편집에서 카탈로그 검색/선택 위젯 제공
3. 그리드 인라인 편집에서 CatalogCellEditor 제공
4. `hardware_model_id` → `model_id` 리네임, NOT NULL 강제

## 변경 범위

### 1. DB 스키마 (Migration 0057)

| 항목 | Before | After |
|------|--------|-------|
| 컬럼명 | `hardware_model_id` | `model_id` |
| Nullable | `True` | `False` |
| ondelete | `SET NULL` | `RESTRICT` |
| NULL 행 처리 | — | migration에서 삭제 |

- `vendor`, `model`, `category` 컬럼은 유지 (읽기 전용 캐시).
- `model_id`가 NULL인 기존 자산 행은 migration에서 삭제한다.
  사용자가 카탈로그 연결하여 재등록할 예정.

### 2. 백엔드

#### Asset 모델 (`app/modules/infra/models/asset.py`)

```python
model_id: Mapped[int] = mapped_column(
    ForeignKey("product_catalog.id", ondelete="RESTRICT"),
    nullable=False, index=True
)
```

#### 스키마 (`app/modules/infra/schemas/asset.py`)

- `AssetCreate`: `hardware_model_id: int` → `model_id: int`
- `AssetUpdate`:
  - `hardware_model_id` → `model_id` (Optional[int])
  - `vendor`, `model`, `category` 필드 제거 (카탈로그에서 자동 동기화되므로 직접 수정 차단)
- `AssetRead`: `hardware_model_id` → `model_id`

#### 서비스 (`app/modules/infra/services/asset_service.py`)

- 모든 `hardware_model_id` → `model_id` 리네임 (11+ 곳)
- `update_asset()`: `model_id` 변경 시 vendor/model/category를 카탈로그에서 동기화하는 기존 로직 유지
- vendor/model/category 직접 변경 경로 제거

#### 카탈로그 서비스 (`product_catalog_service.py`)

- 삭제 가드: `Asset.hardware_model_id` → `Asset.model_id`

### 3. 프론트엔드 — 공용 카탈로그 검색 위젯

등록 모달에 이미 구현된 카탈로그 검색 로직을 공용 함수로 추출:

- `createCatalogSearchWidget(container, options)` — 카탈로그 검색 input + dropdown을 생성
  - `options.onSelect(item)`: 선택 콜백
  - `options.kindFilter`: 상위분류 필터 (optional)
  - `options.initialValue`: 초기값 표시 (optional)
- `renderCatalogDropdown(items, dropdown, onSelect)` — 드롭다운 렌더링 (기존 로직 재사용)
- 등록 모달도 이 공용 함수를 사용하도록 리팩터

### 4. 프론트엔드 — 상세 패널 편집

`DETAIL_EDIT_FIELDS.overview`에서:

- `["제조사", "vendor"]`, `["모델", "model"]` 제거
- `["카탈로그 제품", "model_id"]` 추가

`buildDetailEditFields()` 에서 `model_id` 필드일 때:
- 공용 카탈로그 검색 위젯 생성
- 현재 자산의 카탈로그 정보를 초기값으로 표시
- 선택 시 `model_id` 값 세팅

`saveDetailEdit()` 에서:
- `model_id` 변경 감지 → `PATCH /assets/{id}` 에 `{ model_id: newId }` 전송
- 백엔드가 vendor/model/category 자동 동기화 → 응답으로 갱신된 자산 반영

### 5. 프론트엔드 — 그리드 CatalogCellEditor

PartnerCellEditor 패턴을 참조한 AG Grid 셀 에디터:

```
class CatalogCellEditor {
  init(params)         — container + input + dropdown 생성
  _search()            — 카탈로그 API 호출 (300ms 디바운스)
  _renderDropdown()    — 결과 렌더링, 분류 미설정 항목 disabled, "+ 새 제품 등록"
  _selectItem(item)    — 내부에 selectedItem 저장, stopEditing 호출
  getGui()             — container 반환
  afterGuiAttached()   — input focus
  getValue()           — { model_id, display } 객체 반환 (AG Grid가 handleGridCellValueChanged 트리거)
  destroy()            — dropdown 제거
  isPopup()            — true
}
```

키보드 내비게이션: ArrowUp/Down (드롭다운 항목 이동), Enter (선택), Escape (닫기)

그리드 컬럼 설정:
- `GRID_EDITABLE_FIELDS`에 `"model"` 추가
- model 컬럼에 `cellEditor: CatalogCellEditor` 지정
- `handleGridCellValueChanged()`에서 model 필드 변경 시 `model_id` 기반 PATCH 처리

### 6. 프론트엔드 — 읽기 전용 처리

- `DETAIL_EDIT_FIELDS.overview`: vendor, category 항목 제거
- 상세 패널 읽기 모드에서는 vendor/model/category 기존대로 표시 (Asset 컬럼 캐시값)
- 그리드 vendor/category 컬럼: 편집 불가 유지 (카탈로그 파생)

## 영향 받는 파일

| 파일 | 변경 내용 |
|------|-----------|
| `alembic/versions/0057_*.py` | 컬럼 리네임, NOT NULL, ondelete 변경, NULL 행 삭제 |
| `app/modules/infra/models/asset.py` | model_id 컬럼 정의 변경 |
| `app/modules/infra/schemas/asset.py` | Create/Update/Read 스키마 수정 |
| `app/modules/infra/services/asset_service.py` | hardware_model_id → model_id 전체 리네임, update 로직 조정 |
| `app/modules/infra/services/product_catalog_service.py` | 삭제 가드 필드명 변경 |
| `app/static/js/infra_assets.js` | CatalogCellEditor, 상세 편집 위젯, 공용 함수 추출, 읽기 전용 처리 |
| `app/modules/infra/templates/infra_assets.html` | 등록 모달 hidden input name 변경 (hardware_model_id → model_id) |

## 제외 사항

- 등록 모달: 기존 카탈로그 검색 UX 유지 (이미 잘 동작)
- vendor/model/category DB 컬럼 삭제: 하지 않음 (읽기 전용 캐시로 유지)
- 자산 Excel import: 이번 범위 외
