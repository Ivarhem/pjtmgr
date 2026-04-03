# 유사도 사전 계산 캐시 + 무시 롤백 + 그리드 경고 아이콘

> 기준정보관리 그리드에서 중복 검토가 필요한 제조사/제품을 즉시 식별할 수 있도록 하고, 무시한 유사 관계를 복원할 수 있게 한다.

## 배경

유사 제품 패널은 구현되었지만, 어떤 제조사/제품에 중복이 있는지 제품을 하나하나 클릭해야 알 수 있다. 수천 개 제품 규모에서 이는 비현실적이다. 사전 계산된 유사도 카운트를 그리드에 표시하여 중복 검토 대상을 즉시 파악할 수 있어야 한다.

## 1. DB: `product_catalog` 테이블에 `similar_count` 컬럼 추가

`product_catalog` 테이블에 `similar_count` (Integer, default 0) 컬럼을 추가한다. dismissal을 제외한 유사 제품 수를 저장한다.

별도 캐시 테이블 대신 원본 테이블에 직접 추가하는 이유:
- `ProductCatalogListCache`는 layout_id별로 분리되고 전체 무효화되므로 부적합
- 단일 integer 컬럼이라 조인 없이 기존 쿼리에서 바로 읽힘
- 제품 목록 API/제조사 목록 API 모두 product_catalog를 이미 참조함

## 2. 유사도 재계산 함수

`recalc_similar_counts(db, product_ids)` 함수를 만든다.

- 주어진 product_ids 각각에 대해 기존 `score_product_similarity`를 사용하되, 전체 상세 결과 대신 count만 반환
- dismissal 제외, score >= 75인 것만 카운트
- 결과를 `product_catalog.similar_count`에 UPDATE

전체 재계산 함수 `recalc_all_similar_counts(db)`도 제공한다 (초기 데이터 채우기 + 수동 재계산용).

## 3. 갱신 트리거 (동기)

| 이벤트 | 재계산 대상 |
|--------|------------|
| 제품 생성 | 새 제품 + 유사 판정된 상대 제품들 |
| 제품 수정 (vendor/name 변경) | 해당 제품 + 기존 유사 상대들 + 새 유사 상대들 |
| 제품 삭제 | 삭제 전 유사 상대들 (삭제 후 재계산) |
| 제품 병합 | target 제품 + 기존 source의 유사 상대들 |
| 무시 추가 | 해당 쌍의 두 제품 |
| 무시 복원 | 해당 쌍의 두 제품 |

기존 서비스 함수(`create_product`, `update_product`, `delete_product`, `merge_products`, `dismiss_similarity`)의 커밋 직후에 재계산을 호출한다.

## 4. 무시 롤백

### 백엔드

`POST /api/v1/product-catalog/similarity-restore` 엔드포인트 추가.

Request body:

```json
{
  "product_id_a": 15,
  "product_id_b": 42
}
```

서비스: `restore_similarity(db, product_id_a, product_id_b)` — dismissal 행 삭제 후 두 제품의 `similar_count` 재계산. POST를 사용하는 이유: DELETE + body는 일부 환경에서 불안정.

### 프론트엔드

유사 제품 패널에 "무시 목록" 토글 버튼 추가.

- 기본: 무시 목록 숨김 (현재 동작과 동일)
- 토글 ON: 무시된 유사 제품도 표시하되, 카드를 흐리게 렌더링 + "복원" 버튼 표시
- 무시 목록 조회: `POST /api/v1/product-catalog/similarity-check`에 `include_dismissed: true` 파라미터 추가. 무시된 항목은 별도 `dismissed_matches` 배열로 반환.

## 5. 제조사 그리드 경고 아이콘

### 백엔드

`CatalogVendorSummary` 스키마에 `similar_product_count: int = 0` 필드 추가.
`list_vendor_alias_summaries`에서 해당 vendor의 제품 중 `similar_count > 0`인 제품 수를 집계.

### 프론트엔드

제조사 그리드에 "중복" 컬럼 추가 (width: 70px).
- `similar_product_count > 0`이면 경고 아이콘 + 숫자 표시
- 0이면 빈 셀

## 6. 제품 그리드 경고 아이콘

### 백엔드

제품 목록 API (`GET /api/v1/product-catalog`) 응답의 `ProductCatalogRead` 스키마에 `similar_count: int = 0` 필드 추가.

### 프론트엔드

제품 그리드(기준정보관리 페이지)에 "중복" 컬럼 추가 (width: 70px).
- `similar_count > 0`이면 경고 아이콘 + 숫자 표시
- 0이면 빈 셀

## 파일 변경 목록

### 백엔드

- `alembic/versions/0060_product_similar_count.py` — similar_count 컬럼 추가 마이그레이션
- `app/modules/infra/models/product_catalog.py` — similar_count 컬럼 추가
- `app/modules/infra/services/catalog_similarity_service.py` — `recalc_similar_counts`, `recalc_all_similar_counts`, `find_similar_products` include_dismissed 지원
- `app/modules/infra/services/catalog_merge_service.py` — dismiss/restore 후 재계산 호출
- `app/modules/infra/services/product_catalog_service.py` — create/update/delete 후 재계산 호출
- `app/modules/infra/services/catalog_alias_service.py` — vendor summary에 similar_product_count 집계
- `app/modules/infra/schemas/catalog_similarity.py` — dismissed_matches, include_dismissed, restore 스키마
- `app/modules/infra/schemas/catalog_vendor_management.py` — similar_product_count 필드
- `app/modules/infra/schemas/product_catalog.py` — similar_count 필드
- `app/modules/infra/routers/product_catalogs.py` — DELETE dismiss endpoint, similarity-check include_dismissed

### 프론트엔드

- `app/static/js/infra_catalog_integrity.js` — 그리드 컬럼 추가, 무시 목록 토글, 복원 버튼
- `app/static/css/infra_common.css` — 경고 아이콘 + 무시 카드 흐림 스타일
