# 역할기준보기 3패널 트리 뷰 설계

## 개요

역할기준보기 페이지를 제품 카탈로그와 동일한 3패널 트리 구조로 재구성한다.
좌측 트리에서 도메인→센터→제품군 계층으로 역할을 그룹핑하고,
중앙 그리드에서 필터된 역할 목록을 표시하며,
우측 상세 패널에서 역할 정보와 현재 할당 자산을 보여준다.

## 레이아웃

```
[트리 (20%)]  |  [역할 그리드 (45%)]  |  [역할 상세 + 할당자산 (35%)]
```

- 패널 사이 스플리터로 비율 조절 가능 (카탈로그 페이지와 동일)
- 상세 패널은 역할 선택 전에는 빈 상태 메시지 표시

## 트리 구조

고정 3레벨, 프리셋 전환 없음:

```
▼ {도메인}          — 보안, 네트워크, 서버, 스��리지 등
  ▼ {센터}          — IDC-A, IDC-B 등
    ▼ {제품군}      — 방화벽, IPS, L3스위치 등
```

- 트리 데이터는 역할 API 응답��� enrichment 필드에서 구성
- 각 역할의 현재 할당 자산의 카탈로그 속성(도메인, 센터, 제품군)을 기준으로 분류
- 할당 자산이 없거나 카탈로그 속성이 없는 역할은 "미분류" 그룹에 표시
- 트리 노드에 하위 역할 수를 카운트로 표���: `보안 (5)`
- 노드 클릭 시 해당 노드와 하위 노드에 속하는 역할만 그리드에 필터링

## 역할 그리드 (중앙)

| 컬럼 | 필드 | 편집 |
|------|------|------|
| 역할명 | role_name | 더블클릭 텍스트 |
| 현재 자산 | current_asset_name | 읽기전용 |
| 자산코드 | current_asset_code | 읽기전용 |

- 싱글클릭: 우측 상세 패널 표시
- 더블클릭: 역할 편집 모달
- 상단에 검색 입력 + "역할 ��록" 버튼
- ag-Grid quickFilter로 검색

## 상세 패널 (우측)

### 상단: 역할 정보
기존 MDM 패턴(mdm-vendor-info) 재사용:
- 역할명, 상태(활성/비활성/종료), 귀속사업, 비고
- 액션 버튼: 교체, 장애대체, 용도전환, 수정, 삭제

### 하단: 현재 할당 자산
기존 MDM 패턴(mdm-product-section) 재사용:
- ag-Grid로 현재 할당(`is_current=true`) 자산 표시
- 컬럼: 자산명, 자산코드, 할당유형, ���작일, 종료일, 비고
- 더블클릭: 할당 수정 모달
- "이력 보기" 버튼: 전체 할당 이력을 모달로 표시
- "할당 추가" 버튼: 할당 추가 모달

## 서버 API 변경

### 역할 목록 응답 enrichment

`_enrich_roles_with_current_assignment()` 함수를 확장하여 현재 할당 자산의 카탈로그 분류 정보를 추가한다.

**추가 필드 (AssetRoleRead 스키마):**

| 필드 | 타입 | 설명 |
|------|------|------|
| current_asset_domain | str or None | 현재 자산의 카탈로그 도메인 (보안, 네트워크 등) |
| current_asset_center_label | str or None | 현재 자산의 센터명 |
| current_asset_product_family | str or None | 현재 자산의 제품군 |

**구현 방식:**
1. 현재 할당의 asset_id로 Asset 조회
2. Asset의 model_id로 ProductCatalog 조회
3. ProductCatalog의 attribute_values에서 domain, product_family 추출
4. Asset의 center_id로 Center.center_name 조회

`layout_id`와 `lang` 파라미터는 불필요 — 도메인/제품군은 카탈로그 속성의 label을 직접 사용.

### 역할 목록 엔드포인트

기존 `GET /api/v1/asset-roles?partner_id={id}` 유지. 응답에 위 enrichment 필드가 추가됨.

## 프론트엔드 구현

### HTML 템플릿

`infra_asset_roles.html`을 카탈로그 페이지(`product_catalog.html`) 구조를 참고하여 3패널로 재작성:
- 좌측: 트리 컨테이너 (`role-tree-panel`)
- 중앙: 그리드 + 검색바 (`role-grid-panel`)
- 우측: 상세 패널 (`role-detail-panel`) — 기존 MDM 패턴 유지

### JavaScript

`infra_asset_roles.js`에 추가할 로직:

1. **트리 구성**: 역할 목록 응답에서 `current_asset_domain` / `current_asset_center_label` / `current_asset_product_family`를 추출하여 3레벨 트리 노드를 구성
2. **트리 렌더링**: 카탈로그의 `renderCatalogClassificationTree` 패턴 참고
3. **트리 필터**: 노드 선택 시 ag-Grid external filter로 역할 목록 필터링
4. **스플리터**: 카탈로그의 3패널 스플리터 패턴 재사용

### CSS

기존 `infra_common.css`의 카탈로그 3패널 CSS 클래스를 재사용:
- `.catalog-layout` → 3패널 flex 컨테이너
- `.catalog-tree-panel` → 트리 패널
- `.catalog-grid-panel` → 그리드 패널
- `.catalog-detail-panel` → 상세 ���널

또는 MDM 클래스(`mdm-layout` 등)를 확장하여 3패널 지원. 구현 시 기존 패턴 중 더 적합한 것을 선택.

## 트리 데이터 구조 (JS)

```javascript
// 역할 응답에서 트리 빌드
// 입력: [{ role_name, current_asset_domain, current_asset_center_label, current_asset_product_family, ... }]
// 출력: { domain → { center → { product_family → [roles] } } }

// 예시 결과:
{
  "보안": {
    "IDC-A": {
      "방화벽": [{ role_name: "인터넷방화벽#1", ... }, { role_name: "내부방화벽#1", ... }],
      "IPS": [{ role_name: "IPS#1", ... }]
    },
    "IDC-B": {
      "방화벽": [{ role_name: "DR인터넷방화벽#1", ... }]
    }
  },
  "네트워크": {
    "IDC-A": {
      "L3스위치": [{ role_name: "L3스위치#1", ... }]
    }
  },
  "미분류": {
    "미분류": {
      "미분류": [{ role_name: "신규역할", ... }]
    }
  }
}
```

## 기존 기능 유지

- 역할 CRUD 모달 (등록/수정/삭제)
- 할당 CRUD 모달 (추가/수정/삭제)
- 역할 액션 모달 (교체/장애대체/용도전환)
- 할당 이력 모달
- 컨텍스트 셀렉터 연동 (고객사/프로젝트)
- 프로젝트 필터 체크박스

## 고려사항

- 역할 수가 0인 트리 노드는 표시하지 않음
- 트리 접기/펼치기 상태는 localStorage에 저장
- 상세 패널 열림/닫힘 상태 저장
- 역할 등록/수정/삭제 후 트리와 그리드 모두 갱��
