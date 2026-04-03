# 제조사관리 폴리싱 설계

## 배경

제조사관리 페이지(`/catalog-management/vendors`)는 골격만 존재하는 미완성 상태다.
TSV 벌크 입력 중심의 프로토타입을 정식 CRUD 관리 페이지로 완성한다.

## 범위

- 프론트엔드: `catalog_vendors.html`, `infra_catalog_management.js`
- 백엔드: `catalog_integrity.py` (라우터), `catalog_alias_service.py` (서비스), `catalog_vendor_management.py` (스키마)
- CSS: `infra_common.css` (기존 `.catalog-management-*` 클래스 활용)
- 정합성 관리 연동: `catalog_integrity.html`, `infra_catalog_integrity.js`

## 레이아웃

현재 2컬럼 유지 (좌: 제조사 목록 그리드 / 우: 편집 폼).
TSV 벌크 입력 영역 제거. 단건 폼 기반 CRUD로 전환.

---

## 좌측 패널 — 제조사 목록

### 툴바
- 검색 입력 (`#catalog-vendor-search`): 기존 유지
- 새로고침 버튼 (`#btn-catalog-vendor-refresh`): 기존 유지
- **신규 추가 버튼** 추가 (`#btn-catalog-vendor-add`): 우측 폼을 신규 모드로 전환

### AG-Grid
- 컬럼: 제조사명 (`vendor`), 제품수 (`product_count`), 별칭수 (`alias_count`)
  - `aliases` 컬럼 제거 — 별칭 상세는 우측 폼에서 확인
- 행 선택 시 우측 폼에 데이터 로드 (편집 모드)
- `rowSelection: { mode: "singleRow" }` 유지

---

## 우측 패널 — 편집 폼

### 상태
- **빈 상태**: 제조사 미선택 + 신규 아닐 때 placeholder 표시 ("좌측에서 제조사를 선택하거나 새 제조사를 추가하세요")
- **신규 모드**: 신규 버튼 클릭 시. 정식 제조사명 입력 가능, 삭제 버튼 숨김
- **편집 모드**: 그리드 행 선택 시. 원래 제조사명 읽기전용 표시

### 폼 필드

1. **원래 제조사명** (`source_vendor`)
   - 편집 모드: 읽기전용, 현재 vendor 값 표시
   - 신규 모드: 숨김 (정식 제조사명이 곧 신규 이름)

2. **정식 제조사명** (`canonical_vendor`)
   - 편집 가능. 변경 시 제품 일괄 적용 옵션 노출

3. **제품에 일괄 적용** (`apply_to_products`)
   - 체크박스. 정식 제조사명이 원래 이름과 다를 때만 표시
   - 체크 시 해당 vendor를 사용하는 모든 ProductCatalog 레코드의 vendor 값 변경

4. **별칭 관리** — 태그(chip) 입력 방식
   - 텍스트 input + Enter 또는 쉼표로 태그 추가
   - 각 태그: 별칭 텍스트 + X 삭제 버튼
   - X 클릭 시 `confirm("별칭 'xxx'을(를) 삭제하시겠습니까?")` 확인 후 제거
   - 중복 입력 방지 (normalized 비교)
   - 태그는 폼 내부 배열로 관리, 저장 시 일괄 전송

### 액션 버튼
- **저장** (`#btn-catalog-vendor-save`): 신규/편집 공용. bulk-upsert API 호출
- **삭제** (`#btn-catalog-vendor-delete`): 편집 모드에서만 표시
  - 클릭 시 연결 제품 수 확인 → 있으면 "연결된 제품 N개가 있어 삭제할 수 없습니다" alert
  - 없으면 `confirm("제조사 'xxx'과(와) 모든 별칭을 삭제하시겠습니까?")` 후 DELETE API 호출

### 권한 처리
- 페이지 로드 시 `/api/v1/me`에서 `can_manage_catalog_taxonomy` 확인
- 미보유 시: 신규 추가 버튼, 저장 버튼, 삭제 버튼, 태그 X 버튼 숨김. 폼은 읽기전용.

---

## 백엔드 변경

### 1. 응답 스키마 추가

`catalog_vendor_management.py`에 `CatalogVendorSummary` Pydantic 모델 추가:

```python
class CatalogVendorSummary(BaseModel):
    vendor: str
    product_count: int
    alias_count: int
    aliases: list[CatalogVendorAliasItem]

class CatalogVendorAliasItem(BaseModel):
    id: int
    alias_value: str
    normalized_alias: str
    is_active: bool
```

GET `/api/v1/catalog-integrity/vendors`에 `response_model=list[CatalogVendorSummary]` 지정.

### 2. DELETE 엔드포인트 추가

```
DELETE /api/v1/catalog-integrity/vendors/{vendor_canonical}
```

- 연결된 ProductCatalog 레코드 수 확인
- 0이면: 해당 vendor_canonical의 모든 CatalogVendorAlias 삭제, 204 반환
- 0 초과: 409 Conflict 반환, body에 `{ "detail": "연결된 제품 N개가 있어 삭제할 수 없습니다", "product_count": N }`

### 3. 서비스 함수 추가

`catalog_alias_service.py`에 `delete_vendor_and_aliases(db, vendor_canonical, current_user)` 추가:
- `_require_taxonomy_edit(current_user)` 권한 확인
- `ProductCatalog.vendor == vendor_canonical` 카운트 조회
- 0이면 `CatalogVendorAlias.vendor_canonical == vendor_canonical` 전체 삭제
- 0 초과면 `ConflictError` raise

### 4. list_vendor_alias_summaries 응답 보강

현재 aliases를 문자열 리스트로 반환하는 것을 `CatalogVendorAliasItem` 형태(id, alias_value, normalized_alias, is_active)로 변경.
→ 프론트에서 개별 alias id를 알 수 있어 향후 개별 alias CRUD 확장 가능.

---

## 정합성 관리 연동

`catalog_integrity.html`의 벤더 탭에 "제조사 관리에서 편집" 링크 추가:
- 벤더 요약 영역에 `/catalog-management/vendors` 링크 버튼

---

## 제거 대상

- TSV 벌크 입력 textarea 및 관련 UI (`#catalog-vendor-bulk-text`, `#btn-catalog-vendor-bulk-apply`)
- `parseCatalogManagementTsv`, `saveCatalogVendorManagementBulk` JS 함수
- 결과 표시 영역 (`#catalog-vendor-result`, `.catalog-management-result`)
- TSV 관련 도움말 (`catalog-management-help`)

---

## 미변경 사항

- 데이터 모델: CatalogVendorAlias 테이블 구조 유지 (별도 Vendor 엔티티 미생성)
- 기존 bulk-upsert API: 유지 (단건 저장도 이 API 사용)
- 네비게이션: 기존 탭 구조 유지
- 제품 관리 탭 (`catalog_products.html`): 미변경
