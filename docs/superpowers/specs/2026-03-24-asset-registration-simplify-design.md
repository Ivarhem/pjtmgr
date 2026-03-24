# 자산 등록 간소화 + 카탈로그 연동 설계

## 목표

자산 등록 모달을 35개 필드에서 4개 핵심 필드로 축소하고, 카탈로그 선택을 통해 제조사/모델/유형/분류를 자동 결정한다. 상세 정보는 등록 후 하단 상세 패널에서 입력한다.

## 현재 문제

- 등록 모달에 35개 필드가 나열되어 사용자 부담이 큼
- 제조사/모델을 자유 입력하여 오타·불일치 발생 가능
- 카탈로그(product_catalog)와 자산 간 연결이 수동이고 일관성 없음
- 자산 유형을 별도 선택해야 하지만 사실상 제품 모델에 의해 결정됨

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

### 2. 카탈로그 인라인 등록

카탈로그 검색에서 매칭 항목이 없을 때 "**+ 새 제품 등록**" 버튼을 표시한다.

클릭 시 모달 내부에 인라인 폼이 펼쳐진다:

| 필드 | 필수 | 비고 |
|---|---|---|
| 제조사 | **필수** | 텍스트 입력 |
| 모델명 | **필수** | 텍스트 입력 |
| 카테고리 | **필수** | 텍스트 입력 (예: Firewall, Switch, Server) |
| 자산 유형 | **필수** | 드롭다운 (asset_type_codes에서 로드) |

등록 즉시 `product_catalog`에 저장되고, 해당 항목이 자동 선택된다.

EOS/EOSL 등 부가 정보는 카탈로그 관리 페이지에서 별도로 보완한다.

### 3. 카탈로그 모델 변경

`product_catalog` 테이블에 `asset_type_code` 컬럼을 추가한다:

```sql
ALTER TABLE product_catalog
  ADD COLUMN asset_type_code VARCHAR(30)
  REFERENCES asset_type_codes(code) ON DELETE SET NULL;
```

- 기존 데이터: migration에서 `category` 값 기반으로 초기 매핑 시도. 매핑 불가 항목은 NULL로 두고 카탈로그 UI에서 수동 보정.
- 카탈로그 등록/수정 UI에 "자산 유형" 드롭다운 추가.
- `asset_type_code`가 NULL인 카탈로그 항목은 자산 등록 시 검색 결과에서 경고 표시 ("자산 유형 미설정").

### 4. 자산 생성 플로우

```
사용자: 카탈로그 제품 선택 + 자산명 입력 + (호스트명) + (귀속사업)
         ↓
백엔드: asset 레코드 생성
  - hardware_model_id = catalog.id
  - asset_type = catalog.asset_type_code
  - vendor = catalog.vendor
  - model = catalog.name
  - category = catalog.category
  - asset_code = 자동 생성 ({고객사코드}-{유형코드}-{base36})
  - partner_id = topbar 선택 고객사
  - status = "planned" (기본값)
  - environment = "prod" (기본값)
         ↓
귀속사업 선택 시: PeriodAsset 레코드도 함께 생성
         ↓
프론트: 등록 완료 → 목록 새로고침 → 해당 자산 상세 패널 자동 오픈
```

### 5. 상세 패널에서의 추가 입력

등록 후 상세 패널이 자동으로 열리며, 기존 탭 구조에서 나머지 정보를 입력한다:

| 탭 | 입력 가능 필드 |
|---|---|
| 기본 정보 | 상태, 환경, 시리얼번호, 비고 |
| 설치 위치 | 센터, 장비ID, 랙번호, 랙유닛, 운영유형, 분류, 세부분류, 단계, 입고일 |
| 네트워크 | 호스트명, 클러스터, 서비스명, 존, 서비스IP, 관리IP |
| HW 사양 | 크기(U), LC/HA/UTP/전원 수량, 전원유형, 펌웨어 |
| 자산 관리 | 자산등급, 자산번호, 도입연도, 부서, 담당자, 유지보수업체 |
| 소프트웨어 | (기존 sub-entity 탭) |
| IP 할당 | (기존 sub-entity 탭) |
| 담당자 | (기존 sub-entity 탭) |
| 관계 | (기존 sub-entity 탭) |
| 별칭 | (기존 sub-entity 탭) |

### 6. 기존 수정 모달 처리

현재 수정 모달(35개 필드)은 **제거**한다. 수정은 상세 패널의 각 탭에서 인라인으로 수행한다.

- 상세 패널 헤더의 "수정" 버튼 → 현재 활성 탭을 편집 모드로 전환
- 각 탭에서 개별 저장 (PATCH)
- 카탈로그 제품 변경도 기본 정보 탭에서 가능 (변경 시 vendor/model/type/category 재세팅)

### 7. API 변경

| 엔드포인트 | 변경 |
|---|---|
| `POST /api/v1/assets` | body를 간소화: `{ hardware_model_id, asset_name, hostname?, period_id? }`. 서버에서 catalog 조회 후 나머지 자동 세팅 |
| `PATCH /api/v1/assets/{id}` | 기존과 동일 (부분 업데이트) |
| `GET /api/v1/product-catalog` | 기존과 동일 (검색 드롭다운용) |
| `POST /api/v1/product-catalog` | 인라인 등록용. `asset_type_code` 필드 추가 |
| `PATCH /api/v1/product-catalog/{id}` | `asset_type_code` 필드 추가 |

### 8. 데이터 무결성

- 카탈로그 선택 필수이므로 `hardware_model_id`는 항상 NOT NULL (신규 자산)
- 기존 `hardware_model_id = NULL`인 자산은 레거시로 허용 (DB 제약은 nullable 유지)
- 카탈로그 삭제 시 `ON DELETE SET NULL`로 자산의 vendor/model 값은 보존되지만 catalog 연결만 끊어짐
- `asset_type_code`가 NULL인 카탈로그는 자산 등록 시 선택 불가 (프론트 검증)

### 9. 범위 외

- 카탈로그 관리 페이지 전면 개편 (자산 유형 드롭다운 추가만 수행)
- 기존 자산의 카탈로그 일괄 매칭 (별도 작업)
- Import 플로우 변경 (별도 작업)
