# 자산 등록 간소화 + 카탈로그 연동 설계

## 목표

자산 등록 모달을 35개 필드에서 4개 핵심 필드로 축소하고, 카탈로그 선택을 통해 제조사/모델/유형/분류를 자동 결정한다. 상세 정보는 등록 후 하단 상세 패널에서 입력한다.

## 현재 문제

- 등록 모달에 35개 필드가 나열되어 사용자 부담이 큼
- 제조사/모델을 자유 입력하여 오타·불일치 발생 가능
- 카탈로그(product_catalog)와 자산 간 연결이 수동이고 일관성 없음
- 자산 유형을 별도 선택해야 하지만 사실상 제품 모델에 의해 결정됨

## 현재 데이터 모델 참조

- `asset_type_codes`: PK = `type_key` (예: "server", "security"), `code` (예: "SVR", "SEC")는 자산코드 생성용
- `Asset.asset_type`: `type_key` 값을 저장 (예: "security")
- `Asset.asset_code`: `{고객사코드}-{type_code}-{base36}` (예: P000-SEC-0001)
- `product_catalog`: `vendor` + `name` unique, `category` 자유 문자열
- `Asset.hardware_model_id`: FK → `product_catalog.id`, nullable

## 설계

### 1. 등록 모달 필드 구성

| 필드 | 필수 | UI 형태 | 동작 |
|---|---|---|---|
| 카탈로그 제품 | **필수** | 검색 드롭다운 | `vendor + name`으로 검색. 선택 시 자산유형/제조사/모델/분류 자동 결정 |
| 자산명 | **필수** | 텍스트 입력 | 직접 입력 (예: "인터넷방화벽#1") |
| 호스트명 | 선택 | 텍스트 입력 | 직접 입력 |
| 귀속사업 | 선택 | 드롭다운 | topbar 선택 사업 자동 채움, 변경/삭제 가능 |

카탈로그 선택 시 모달 하단에 선택 결과 요약을 읽기 전용으로 표시:

```
제조사: Palo Alto | 모델: PA-3260 | 유형: 보안장비 | 분류: Firewall
```

placeholder 항목은 회색으로 표시: `미분류 보안장비 (placeholder)`

### 2. 카탈로그 인라인 등록

카탈로그 검색에서 매칭 항목이 없을 때 "**+ 새 제품 등록**" 버튼을 표시한다.

클릭 시 모달 내부에 인라인 폼이 펼쳐진다:

| 필드 | 필수 | 비고 |
|---|---|---|
| 제조사 | **필수** | 텍스트 입력 |
| 모델명 | **필수** | 텍스트 입력 |
| 카테고리 | **필수** | 텍스트 입력 (예: Firewall, Switch, Server) |
| 자산 유형 | **필수** | 드롭다운 (asset_type_codes에서 로드) |

등록 즉시 `product_catalog`에 저장되고(`is_placeholder = false`), 해당 항목이 자동 선택된다.

EOS/EOSL 등 부가 정보는 카탈로그 관리 페이지에서 별도로 보완한다.

### 3. 카탈로그 모델 변경

`product_catalog` 테이블에 2개 컬럼을 추가한다:

```sql
ALTER TABLE product_catalog
  ADD COLUMN asset_type_key VARCHAR(30)
    REFERENCES asset_type_codes(type_key) ON DELETE SET NULL,
  ADD COLUMN is_placeholder BOOLEAN NOT NULL DEFAULT false;
```

**컬럼 명명 주의:** `asset_type_key`로 명명한다 (리뷰 이슈 #1 반영). `Asset.asset_type`과 동일하게 `type_key` 값을 저장하여 추가 변환 없이 직접 복사 가능.

**카탈로그 등록/수정 UI:** "자산 유형" 드롭다운 추가.

**기존 데이터 migration:** category 값 기반 초기 매핑:

| category (ILIKE) | → asset_type_key |
|---|---|
| `%server%`, `%서버%` | server |
| `%switch%`, `%스위치%` | network |
| `%router%`, `%라우터%` | network |
| `%firewall%`, `%방화벽%` | security |
| `%storage%`, `%스토리지%` | storage |
| 매핑 불가 | NULL → 카탈로그 UI에서 수동 보정 |

**백엔드 검증:** `asset_type_key`가 NULL인 카탈로그 항목으로 자산 생성 시도 시 422 반환 ("카탈로그에 자산 유형이 설정되지 않았습니다"). 프론트에서도 경고 표시하지만 백엔드가 최종 게이트.

### 4. Placeholder 카탈로그 항목

자산 유형별로 1개씩 placeholder 항목을 시드한다. 모델이 아직 미정인 장비도 등록 가능하게 하기 위함.

| vendor | name | category | asset_type_key | is_placeholder |
|---|---|---|---|---|
| — | 미분류 서버 | Server | server | true |
| — | 미분류 네트워크장비 | Network | network | true |
| — | 미분류 보안장비 | Security | security | true |
| — | 미분류 스토리지 | Storage | storage | true |
| — | 미분류 미들웨어 | Middleware | middleware | true |
| — | 미분류 응용 | Application | application | true |
| — | 미분류 기타 | ETC | other | true |

- `is_placeholder = true` 항목은 검색 드롭다운에서 회색 스타일로 구분
- placeholder로 등록한 자산은 나중에 상세 패널에서 실제 카탈로그 항목으로 교체 가능
- placeholder 항목의 삭제는 불가 (참조 자산이 있을 때 409, 없어도 시스템 항목이므로 UI에서 삭제 버튼 미표시)
- migration에서 `asset_type_codes` 시드와 함께 자동 생성

### 5. 자산 생성 플로우

```
사용자: 카탈로그 제품 선택 + 자산명 입력 + (호스트명) + (귀속사업)
         ↓
프론트 → POST /api/v1/assets
  body: { partner_id, hardware_model_id, asset_name, hostname?, period_id? }
         ↓
백엔드: 단일 트랜잭션으로 처리
  1. catalog = db.get(ProductCatalog, hardware_model_id)
  2. 검증: catalog 존재, catalog.asset_type_key IS NOT NULL
  3. asset 레코드 생성:
     - hardware_model_id = catalog.id
     - asset_type = catalog.asset_type_key
     - vendor = catalog.vendor  (placeholder면 NULL)
     - model = catalog.name     (placeholder면 NULL)
     - category = catalog.category
     - asset_code = 자동 생성 ({고객사코드}-{유형코드}-{base36})
     - partner_id = body.partner_id
     - status = "planned", environment = "prod"
  4. period_id가 있으면: PeriodAsset(asset_id, contract_period_id, role=NULL) 생성
  5. commit
         ↓
프론트: 등록 완료 → 목록 새로고침 → 해당 자산 상세 패널 자동 오픈
```

**vendor 처리:** placeholder 카탈로그(vendor="—")로 자산을 만들면 `Asset.vendor = NULL`, `Asset.model = NULL`로 저장. "—" 문자열을 자산에 복사하지 않는다.

**partner_id:** body에 포함 (기존 패턴과 동일). topbar 선택 고객사 값을 프론트에서 전달.

### 6. 상세 패널에서의 추가 입력

등록 후 상세 패널이 자동으로 열리며, 기존 탭 구조에서 나머지 정보를 입력한다:

| 탭 | 입력 가능 필드 |
|---|---|
| 기본 정보 | 카탈로그 제품(변경 가능), 상태, 환경, 시리얼번호, 비고 |
| 설치 위치 | 센터, 장비ID, 랙번호, 랙유닛, 운영유형, 분류, 세부분류, 단계, 입고일 |
| 네트워크 | 호스트명, 클러스터, 서비스명, 존, 서비스IP, 관리IP |
| HW 사양 | 크기(U), LC/HA/UTP/전원 수량, 전원유형, 펌웨어 |
| 자산 관리 | 자산등급, 자산번호, 도입연도, 부서, 담당자, 유지보수업체 |
| 소프트웨어 | (기존 sub-entity 탭) |
| IP 할당 | (기존 sub-entity 탭) |
| 담당자 | (기존 sub-entity 탭) |
| 관계 | (기존 sub-entity 탭) |
| 별칭 | (기존 sub-entity 탭) |

### 7. 기존 수정 모달 처리

현재 수정 모달(35개 필드)은 **제거**한다. 수정은 상세 패널의 각 탭에서 인라인으로 수행한다.

- 상세 패널 헤더의 "수정" 버튼 → 현재 활성 탭을 편집 모드로 전환
- 각 탭에서 개별 저장 (PATCH)
- 카탈로그 제품 변경: **동일 자산 유형 내에서만 허용**. 유형이 다른 카탈로그로 변경 시도 시 프론트/백엔드 모두 차단. 이유: `asset_code`에 유형 코드가 인코딩되어 있어 유형 변경 시 코드 불일치 발생 (기존 `update_asset`의 유형 변경 금지 규칙 유지)
- 카탈로그 변경 시: vendor/model/category 재세팅 (asset_type은 변경 없음)

### 8. API 변경

| 엔드포인트 | 변경 |
|---|---|
| `POST /api/v1/assets` | body 간소화: `{ partner_id, hardware_model_id, asset_name, hostname?, period_id? }`. 서버에서 catalog 조회 후 나머지 자동 세팅. period_id가 있으면 PeriodAsset도 단일 트랜잭션으로 생성 |
| `PATCH /api/v1/assets/{id}` | `hardware_model_id` 변경 시: 카탈로그의 asset_type_key가 기존과 동일한지 검증. 동일하면 vendor/model/category 재세팅 |
| `GET /api/v1/product-catalog` | 기존과 동일 (검색 드롭다운용). 응답에 `asset_type_key`, `is_placeholder` 포함 |
| `POST /api/v1/product-catalog` | 인라인 등록용. `asset_type_key` 필드 추가 (필수). `is_placeholder`는 서버에서 false 고정 |
| `PATCH /api/v1/product-catalog/{id}` | `asset_type_key` 필드 추가 |

### 9. 데이터 무결성

- 카탈로그 선택 필수이므로 `hardware_model_id`는 항상 NOT NULL (신규 자산)
- 기존 `hardware_model_id = NULL`인 자산은 레거시로 허용 (DB 제약은 nullable 유지)
- 카탈로그 삭제: 참조하는 자산이 있으면 서비스 레이어에서 409 반환 (기존 guideline 준수). `ON DELETE SET NULL`은 DB 안전망으로만 유지
- `asset_type_key`가 NULL인 카탈로그는 자산 등록 시 백엔드에서 422 반환 (프론트 검증에 의존하지 않음)
- 자산 유형 변경 금지: `update_asset`의 기존 규칙 유지. 카탈로그 변경 시에도 동일 유형만 허용
- PeriodAsset 생성은 자산 생성과 단일 트랜잭션 (부분 실패 방지)
- PeriodAsset 생성 시 `role`은 NULL (기본값). 상세 패널에서 나중에 설정

### 10. 범위 외

- 카탈로그 관리 페이지 전면 개편 (자산 유형 드롭다운 추가 + placeholder 표시만 수행)
- 기존 자산의 카탈로그 일괄 매칭 (별도 작업)
- Import 플로우 변경 (별도 작업)
