# 유사 제품 패널 + 병합 기능

> 기준정보관리 탭에서 제품 클릭 시 유사 제품을 조회하고, 병합/무시할 수 있는 패널.

## 배경

기준정보관리 페이지는 현재 2패널(제조사 목록 | 제조사 편집 + 제품 그리드) 구조다. 제조사별 제품 목록은 표시되지만, 유사/중복 제품을 정리하는 기능이 없다. Import나 수동 등록으로 생긴 중복 제품을 하나로 병합하는 워크플로우가 필요하다.

## 레이아웃

```
┌──────────┬──────────────────────────┬───────────────────┐
│ 제조사    │  제조사 편집폼 (상단)      │                   │
│ 목록     │  제품 그리드 (하단)        │  유사 제품 패널    │
│          │  [제품 클릭] ──────────→  │  (수평 확장)       │
└──────────┴──────────────────────────┴───────────────────┘
```

- 제품 행 클릭 → 우측에 유사 제품 패널 슬라이드
- 카탈로그의 `.catalog-detail-panel` 패턴 재사용: 스플리터 + 토글 버튼(❮/❯)
- 패널 너비는 드래그로 조정, localStorage에 저장
- 다른 제품 클릭 시 패널 내용 갱신, 토글 버튼으로 닫기

## 유사 제품 패널 구성

### 상단: 선택된 제품 요약

```
┌─────────────────────────────────┐
│  Cisco Catalyst 9300            │
│  분류: Network > Switch         │
│  연결 자산: 12건                 │
└─────────────────────────────────┘
```

- 제조사 + 모델명 (h3)
- 분류 경로 (classification_level_2 > level_3)
- 연결 자산 수 (`SELECT count(*) FROM assets WHERE model_id = ?`)

### 하단: 유사 제품 목록 + 액션

기존 `POST /api/v1/product-catalog/similarity-check` API를 호출하되, 응답에 `asset_count`를 추가해야 한다.

각 유사 제품 카드:

```
┌─────────────────────────────────┐
│  Cisco Catalyst9300 (score: 92) │
│  분류: Network > Switch  자산 3건│
│  [← 병합] [무시]                │
└─────────────────────────────────┘
```

- 유사도 점수 뱃지 (색상: 90+ 빨강, 75+ 주황)
- "← 병합" 버튼: 이 유사 제품(source)을 선택된 제품(target)으로 흡수
- "무시" 버튼: 이 쌍을 유사 목록에서 제외

유사 제품이 없으면 "유사 제품이 없습니다" 메시지 표시.

## 병합 동작 (Merge)

### 흐름

1. "← 병합" 클릭
2. 확인 다이얼로그:
   - "제품 'Cisco Catalyst9300'(자산 3건)을 'Cisco Catalyst 9300'으로 병합합니다."
   - "자산 3건이 대상 제품으로 이전되고, 원본 제품은 삭제됩니다."
   - 원본에 스펙이 있고 대상에도 스펙이 있는 경우: "원본 제품의 스펙 정보는 유지되지 않습니다." 경고 추가
3. 확인 시 `POST /api/v1/product-catalog/merge` 호출
4. 성공 후: 제품 그리드 새로고침, 유사 제품 패널 갱신

### 백엔드: `POST /api/v1/product-catalog/merge`

**Request:**
```json
{
  "source_id": 42,
  "target_id": 15
}
```

**로직 (트랜잭션 내):**
1. source, target 존재 확인
2. source == target 거부
3. `UPDATE assets SET model_id = target_id WHERE model_id = source_id`
4. `DELETE FROM product_catalog WHERE id = source_id` (CASCADE: specs, interfaces, attributes, cache 자동 삭제)
5. target의 list_cache 재생성

**Response:**
```json
{
  "merged_asset_count": 3,
  "source_vendor": "Cisco",
  "source_name": "Catalyst9300",
  "target_vendor": "Cisco",
  "target_name": "Catalyst 9300"
}
```

## 무시 동작 (Dismiss)

### DB 모델: `ProductSimilarityDismissal`

```
product_similarity_dismissal
  id              PK
  product_id_a    FK → product_catalog.id (CASCADE)
  product_id_b    FK → product_catalog.id (CASCADE)
  created_at      timestamp
  UNIQUE(product_id_a, product_id_b)  -- a < b로 정규화
```

- a, b는 항상 min/max로 정규화하여 저장 (방향 무관)
- 어느 한쪽 제품이 삭제되면 CASCADE로 자동 정리

### 백엔드: `POST /api/v1/product-catalog/similarity-dismiss`

**Request:**
```json
{
  "product_id_a": 15,
  "product_id_b": 42
}
```

### similarity-check API 수정

- 응답에 `asset_count` 필드 추가 (각 candidate별)
- dismissal 테이블을 조인해서 무시된 쌍을 결과에서 제외
- 기존 `exclude_product_id` 파라미터를 dismissal 필터링에도 활용 (선택된 제품 ID)

## CSS 클래스

기존 MDM 스타일(`.mdm-*`)에 추가:

- `.mdm-similar-panel` — 유사 제품 패널 (flex: 1, min-width: 280px)
- `.mdm-similar-splitter` — 스플리터 (6px, `.catalog-splitter` 패턴)
- `.mdm-similar-handle-wrap` — 토글 버튼 래퍼 (18px)
- `.mdm-similar-card` — 유사 제품 카드
- `.mdm-similar-score` — 점수 뱃지
- `.mdm-similar-actions` — 카드 내 버튼 영역

## 파일 변경 목록

### 백엔드
- `app/modules/infra/models/product_similarity_dismissal.py` — 새 모델
- `app/modules/infra/schemas/catalog_similarity.py` — 스키마 확장 (asset_count, merge request/response, dismiss request)
- `app/modules/infra/services/catalog_similarity_service.py` — find_similar_products에 dismissal 필터 + asset_count 추가
- `app/modules/infra/services/catalog_merge_service.py` — 병합 로직 (새 파일)
- `app/modules/infra/routers/product_catalogs.py` — merge, dismiss 엔드포인트 추가
- `alembic/versions/0059_product_similarity_dismissal.py` — 마이그레이션

### 프론트엔드
- `app/templates/catalog_integrity.html` — 유사 제품 패널 HTML (스플리터 + 토글 + 패널)
- `app/static/js/infra_catalog_integrity.js` — 제품 클릭 핸들러, 유사 제품 로드/렌더, 병합/무시 액션, 스플리터 드래그
- `app/static/css/infra_common.css` — `.mdm-similar-*` 스타일 추가
