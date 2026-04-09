# 자산 모델 확장 + 카탈로그 통합 구현 계획

> 범위: 하드웨어를 넘어 소프트웨어, 미들웨어, 컨테이너, 업무 시스템, 모델/LLM까지 확장 가능한 자산 체계를 설계하고, `template.xlsx` / `spec.xlsx` / 카탈로그 / 자산 원장 간 역할을 정리한다.

**Goal:** 인프라모듈의 자산 체계를 `공통 코어 + 유형별 확장 + 카탈로그 기준 데이터` 구조로 재정렬하여, 기능 하나를 구현할 때마다 분류/필드/정규화 기준이 다시 흔들리는 문제를 줄인다.

**핵심 문제**
- 현재 자산 모델은 하드웨어 중심으로 시작했지만, 실제 관리 대상은 하드웨어 외에도 소프트웨어, 미들웨어, 컨테이너, 업무 시스템, 모델/LLM까지 확장될 가능성이 높다.
- 유형별 특성이 크게 달라서, 모든 필드를 `Asset` 하나에 누적하면 영향 범위가 과도하게 커진다.
- `template.xlsx`는 운영 기준문서이고, `spec.xlsx`는 카탈로그 보강 기준문서인데 역할 분리가 문서화되어 있지 않다.
- 분류 체계가 흔들리면 카탈로그, Import, 자산 상세, 검색, 관계, 이력까지 연쇄적으로 수정된다.

---

## 1. 기준문서 역할 정의

### 1.1 `input/template.xlsx`

- 현재 프로젝트 투입 시 사용하는 **운영 기준문서**
- 자산, 네트워크, 포트맵, 실장도 등 현업 입력과 관리 흐름의 출발점
- 시스템은 이 문서의 업무 의미를 보존해야 하지만, 시트 구조를 그대로 복제할 의무는 없다

### 1.2 `input/spec.xlsx`

- 제품/사양/EOSL 정보를 보강하기 위한 **카탈로그 정제 기준문서**
- 자동 수집 스크립트 결과물
- 현재 확인된 시트:
  - `SPEC`
  - `EOSL`
- 장기적으로 `product_catalog` 기능에 통합될 대상

### 1.3 시스템 내 역할 분리

- `template.xlsx` -> 운영/입력 기준
- `spec.xlsx` -> 카탈로그 보강/정제 기준
- `product_catalog` -> 제품 마스터
- `Asset` -> 실제 운영 중인 관리 대상 원장

즉, `template.xlsx`와 `spec.xlsx`는 같은 용도가 아니다. 하나는 현업 운영 흐름의 기준이고, 다른 하나는 카탈로그 품질을 높이기 위한 정제 원본이다.

---

## 2. 설계 원칙

### 2.1 공통 코어 + 유형별 확장

처음부터 모든 유형을 하나의 완전 일반화 스키마로 풀지 않는다. 대신 다음 구조를 따른다.

- 공통 코어
  - 모든 관리 대상이 공유하는 최소 필드
- 유형 분류
  - `kind` + `type_key`의 2단 체계
- 유형별 확장
  - 하드웨어, 소프트웨어, 모델 등은 별도 상세 구조로 분리

### 2.2 카탈로그와 인스턴스 분리

- 카탈로그는 “제품/사양/수명주기 기준 정보”
- 자산은 “실제 운영 중인 개체”

예:
- 카탈로그: `Palo Alto PA-3260`
- 자산: `본사 인터넷방화벽#1`
- 카탈로그: `OpenAI GPT-4.1`
- 자산: `고객지원 챗봇 운영 모델`

### 2.3 공통 관리 행위는 통일

유형이 달라도 아래는 공통 프레임으로 유지한다.

- 상태
- 관계
- 담당자
- Alias
- 사업 귀속
- 변경 이력
- 검색 진입 방식

### 2.4 세부 사양은 단계적으로 정규화

초기에는 반복적으로 쓰이는 속성만 정규화한다.

우선 정규화 대상:
- 분류
- 상태
- lifecycle(EOS/EOL/EOSL)
- 카탈로그 연결
- 식별자
- 관계 유형

후속 정규화 대상:
- 벤더별 세부 사양 전부
- 자유형 설명문
- 드물게 쓰는 특수 속성

---

## 3. 목표 데이터 구조

### 3.1 공통 코어

`Asset`은 “관리 대상 엔티티”의 최소 공통 원장으로 유지한다.

권장 공통 필드 범위:
- `id`
- `partner_id`
- `asset_code`
- `asset_name`
- `kind`
- `asset_type`
- `status`
- `lifecycle_state`
- `hardware_model_id` 또는 향후 일반화된 `catalog_item_id`
- `note`
- `created_at`
- `updated_at`

현 시점에서는 기존 `Asset.asset_type`과 `hardware_model_id` 구조를 유지하되, 확장 방향은 `kind`와 일반화 카탈로그 연결을 수용할 수 있도록 설계한다.

### 3.2 분류 체계

#### 상위 분류: `kind`

제안 값:
- `hardware`
- `software`
- `service`
- `dataset`
- `model`
- `business_capability`

#### 실무 분류: `type_key`

예:
- hardware
  - `server`, `network`, `security`, `storage`
- software
  - `os`, `dbms`, `middleware`, `application`
- service
  - `container_service`, `saas`, `api_service`
- model
  - `llm`, `embedding_model`, `vision_model`
- business_capability
  - `portal`, `billing`, `trading`, `groupware`

`kind`는 큰 분류, `type_key`는 실무 분류다. UI/Import/검색은 이 2단 체계를 기준으로 간다.

#### 권장 분류표 초안

| kind | type_key 예시 | 설명 | 1차 구현 대상 |
| --- | --- | --- | --- |
| hardware | `server`, `network`, `security`, `storage` | 물리 장비 | 예 |
| software | `os`, `dbms`, `middleware`, `application` | 설치형/배포형 SW | 예 |
| service | `container_service`, `saas`, `api_service` | 운영 서비스/배포 단위 | 아니오 |
| model | `llm`, `embedding_model`, `vision_model` | AI/ML 모델 | 예 |
| business_capability | `portal`, `billing`, `trading`, `groupware` | 업무 기능/시스템 | 아니오 |
| dataset | `document_store`, `feature_store`, `knowledge_base` | 데이터 자산 | 아니오 |

#### 현재 코드와의 연결 기준

- 현재 `product_catalog.product_type`는 사실상 `kind`의 초기 축으로 재해석할 수 있다.
- 현재 `asset_type_key`는 실무 분류(`type_key`) 축으로 유지한다.
- 즉, 단기적으로는 다음 매핑을 권장한다.
  - `product_type` -> `kind`로 수렴
  - `asset_type_key` -> `type_key` 유지
- 기존 하드웨어 중심 필드와 호환성을 깨지 않기 위해, 1차 구현에서는 DB 전면 개편보다 문서/서비스 기준 정렬을 먼저 수행한다.

### 3.3 카탈로그

`product_catalog`는 장기적으로 “제품 마스터” 역할을 맡는다.

단계적 확장 방향:
- 현재: 하드웨어 중심 제품 카탈로그
- 다음: 소프트웨어/미들웨어/컨테이너/모델 카탈로그까지 수용

추천 확장 필드:
- 기본 식별
  - vendor
  - name
  - version
  - category
  - kind
  - asset_type_key
- lifecycle
  - eos_date
  - eosl_date
  - last_verified_at
- 출처
  - source_name
  - source_url
  - source_confidence
  - import_batch_id
- 검증
  - is_placeholder
  - verification_status

#### 카탈로그 메뉴의 장기 역할

카탈로그 메뉴는 장기적으로 아래 4개 기능을 함께 가진다.

1. 제품 마스터 관리
- vendor / name / version / category / kind / type_key

2. 정제 정보 관리
- SPEC 기반 사양
- EOS/EOSL 기반 lifecycle

3. 수집 결과 검토/반영
- 자동 수집 결과 preview
- 수동 승인 또는 overwrite 규칙

4. 자산 원장 기준 데이터 제공
- 자산 등록
- 상세 수정 시 카탈로그 변경
- 검색/분류/수명주기 판단의 기준

### 3.4 유형별 상세

초기에는 모든 유형을 다 만들지 않는다. 대표 유형만 먼저 typed detail로 둔다.

우선 대상:
- `HardwareSpec`
- `SoftwareSpec`
- `ModelSpec`

후속 대상:
- `ContainerSpec`
- `BusinessServiceSpec`

typed detail로 빼기 어려운 초기 확장 속성은 보조 attribute 구조를 허용할 수 있다.

예:
- `catalog_attributes`
  - `catalog_id`, `group_key`, `attr_key`, `attr_value`, `value_type`

다만 attribute 구조는 보조 수단이다. 반복적으로 조회/정렬/필터에 쓰이는 속성은 typed table로 승격한다.

#### 대표 유형별 상세 예시

##### HardwareSpec
- size_unit
- width_mm / height_mm / depth_mm
- weight_kg
- power_count / power_type / power_watt
- cpu_summary / memory_summary / throughput_summary
- os_firmware

##### SoftwareSpec
- edition
- license_type
- runtime_env
- vendor_support_end
- compatibility_note

##### ModelSpec
- provider
- model_family
- context_window
- modality
- deployment_type
- safety_note

이 3개만 먼저 패턴으로 검증하고, container/service/business capability는 후속 확장으로 둔다.

---

## 3.5 `spec.xlsx` -> 카탈로그 매핑 기준

현재 코드 기준으로 `product_catalog_importer.py`는 이미 `SPEC`와 `EOSL` 시트를 파싱하고 있다. 다만 이 importer는 아직 “카탈로그 메뉴 통합 전의 import 유틸” 성격이 강하므로, 아래 방향으로 정리한다.

### SPEC 시트 역할

- 제품 기본 식별
  - vendor
  - name
  - product_type
  - category
- 대표 하드웨어 스펙
  - size_unit
  - width_mm / height_mm / depth_mm
  - weight_kg
  - power_count / power_type / power_watt
  - cpu_summary / memory_summary / throughput_summary
  - os_firmware
- 참조 링크
  - spec_url
  - reference_url

### EOSL 시트 역할

- lifecycle 보강
  - eos_date
  - eosl_date
  - eosl_note

### 1차 매핑 방향

| 원본 | 시스템 대상 | 비고 |
| --- | --- | --- |
| `SPEC.vendor`, `SPEC.name` | `product_catalog.vendor`, `product_catalog.name` | 제품 식별 기준 |
| `SPEC.product_type` | `product_catalog.product_type` | 후속 `kind` 축으로 수렴 |
| `SPEC.category` | `product_catalog.category` | 운영 분류 보조 |
| `SPEC.*spec fields` | `hardware_spec` | 하드웨어 대표 스펙 |
| `EOSL.eos_date`, `EOSL.eosl_date`, `EOSL.eosl_note` | `product_catalog` lifecycle 필드 | 제품 수준 lifecycle |

### 후속 확장 방향

- software/middleware/model이 들어오면 `SPEC` 시트 구조를 그대로 쓰지 않을 수도 있다.
- `SPEC`가 하드웨어 중심이라면, 카탈로그 메뉴 내부에서는 kind별 입력 폼/Import 규칙을 분리할 수 있다.
- 즉, `spec.xlsx`는 현재 하드웨어 카탈로그 강화 기준이고, 범용 카탈로그 전체의 영구 입력 포맷으로 고정하지 않는다.

### 현재 연결 범위와 확장 원칙

현재 구현 기준:
- `SPEC` -> `product_catalog(kind=hardware)` + `hardware_spec`
- `EOSL` -> `product_catalog` lifecycle
- `software`, `model`, `service`, `business_capability`, `dataset`는 현재 카탈로그 상세 화면에서 수동 입력/저장

이 기준은 의도된 것이다.
- `spec.xlsx`는 지금 당장 모든 kind의 단일 입력 포맷이 아니다.
- 먼저 하드웨어 카탈로그 정제 파이프라인을 안정화하고,
- 그 다음에 software/model/generic 확장 입력원을 별도로 설계한다.

즉, 지금의 importer는 “하드웨어 중심 카탈로그 Import 1차 버전”으로 본다.

### kind별 입력원 전략

| kind | 현재 입력원 | 1차 저장 대상 | 후속 확장 방향 |
| --- | --- | --- | --- |
| `hardware` | `spec.xlsx` `SPEC/EOSL` + 수동 보정 | `product_catalog`, `hardware_spec`, `EOS/EOSL` | `spec.xlsx` 정교화, 벤더별 정규화 확대 |
| `software` | 카탈로그 상세 수동 입력 | `product_catalog`, `software_spec` | 별도 software catalog import 또는 CSV/XLSX 정의 |
| `model` | 카탈로그 상세 수동 입력 | `product_catalog`, `model_spec` | 모델 목록 수집 결과 import 형식 별도 정의 |
| `service` | 카탈로그 상세 수동 입력 | `product_catalog`, `generic_profile` | service inventory/CMDB 연계 검토 |
| `business_capability` | 카탈로그 상세 수동 입력 | `product_catalog`, `generic_profile` | 업무 체계/시스템 맵 기준 import 검토 |
| `dataset` | 카탈로그 상세 수동 입력 | `product_catalog`, `generic_profile` | 데이터 카탈로그/메타스토어 연계 검토 |

### importer 확장 원칙

앞으로 importer를 넓힐 때는 다음 원칙을 따른다.

1. `hardware` importer와 `software/model/generic` importer를 분리한다.
- 하나의 `SPEC` 시트에 모든 kind를 억지로 욱여넣지 않는다.

2. 새 입력원은 kind별 typed detail과 1:1로 연결한다.
- `software` -> `software_spec`
- `model` -> `model_spec`
- `service/business_capability/dataset` -> `generic_profile`

3. preview/confirm/audit 플로우는 공통으로 유지한다.
- 입력원은 달라도 검토 방식은 동일하게 가져간다.

4. 엑셀 형식은 시스템 설계의 종속변수가 아니다.
- 운영상 불편하면 `spec.xlsx`와 별도 관리 문서를 추가/수정할 수 있다.

### 구현 파동 제안

#### Wave 1. 현재 유지
- `spec.xlsx`는 hardware + lifecycle 강화에 집중
- software/model/generic은 상세 화면 수동 입력으로 운영

#### Wave 2. software/model 입력원 정의
- software catalog용 import 포맷 정의
- model/LLM catalog용 import 포맷 정의
- 카탈로그 메뉴에서 kind별 import 진입점 분리

### Wave 2 초안: software import 포맷

제안 시트명:
- `SOFTWARE`

제안 컬럼:

| 컬럼 | 시스템 대상 | 필수 | 비고 |
| --- | --- | --- | --- |
| 제조사 | `product_catalog.vendor` | 예 | 벤더/제공사 |
| 제품명 | `product_catalog.name` | 예 | 기준 식별 |
| 버전 | `product_catalog.version` | 아니오 | 예: `19c`, `2024.1` |
| 상위분류 | `product_catalog.product_type` | 예 | 기본값 `software` |
| 자산유형 | `product_catalog.asset_type_key` | 아니오 | 예: `middleware`, `application`, `dbms` |
| 분류 | `product_catalog.category` | 예 | 예: DBMS, WAS, 협업도구 |
| 에디션 | `software_spec.edition` | 아니오 | Standard, Enterprise 등 |
| 라이선스유형 | `software_spec.license_type` | 아니오 | subscription, perpetual 등 |
| 라이선스단위 | `software_spec.license_unit` | 아니오 | core, user, instance 등 |
| 배포형태 | `software_spec.deployment_type` | 아니오 | on-prem, saas, container |
| 실행환경 | `software_spec.runtime_env` | 아니오 | Linux, Kubernetes, JVM |
| 지원벤더 | `software_spec.support_vendor` | 아니오 | 리셀러/지원사 가능 |
| 참조URL | `product_catalog.reference_url` | 아니오 | 제품 정보 페이지 |
| 비고 | `software_spec.architecture_note` | 아니오 | 자유 메모 |

운영 원칙:
- `상위분류`가 비어 있으면 `software`로 보정
- `자산유형`이 비어 있어도 등록은 허용
- `제조사 + 제품명 + 버전` 조합은 preview 단계에서 표시하되, DB 1차 유니크 기준은 당분간 `제조사 + 제품명` 유지

### Wave 2 초안: model import 포맷

제안 시트명:
- `MODEL`
- 또는 업무 문맥상 `LLM`

제안 컬럼:

| 컬럼 | 시스템 대상 | 필수 | 비고 |
| --- | --- | --- | --- |
| 제공자 | `product_catalog.vendor` 또는 `model_spec.provider` | 예 | 예: OpenAI, Anthropic |
| 모델명 | `product_catalog.name` | 예 | 예: GPT-4.1 |
| 버전 | `product_catalog.version` | 아니오 | 날짜/리비전 포함 가능 |
| 상위분류 | `product_catalog.product_type` | 예 | 기본값 `model` |
| 자산유형 | `product_catalog.asset_type_key` | 아니오 | 예: `llm`, `embedding_model` |
| 분류 | `product_catalog.category` | 예 | 예: 생성형AI, 임베딩 |
| 모델계열 | `model_spec.model_family` | 아니오 | GPT, Claude, Llama 등 |
| 모달리티 | `model_spec.modality` | 아니오 | text, image, multimodal |
| 배포범위 | `model_spec.deployment_scope` | 아니오 | api, self-hosted, internal |
| 컨텍스트윈도우 | `model_spec.context_window` | 아니오 | 정수 |
| 엔드포인트형식 | `model_spec.endpoint_format` | 아니오 | chat, responses, batch |
| 참조URL | `product_catalog.reference_url` | 아니오 | 문서/제품 페이지 |
| 기능비고 | `model_spec.capability_note` | 아니오 | 제한사항/운영 메모 |

운영 원칙:
- `상위분류`가 비어 있으면 `model`로 보정
- `제공자`는 `product_catalog.vendor`와 `model_spec.provider`를 같은 값으로 시작하고, 후속에 분리 필요가 생기면 재검토
- 모델 수집 원본이 수시로 바뀔 수 있으므로, 하드웨어보다 `source_url`, `verification_status`, `last_verified_at` 의미가 더 중요하다

### preview/confirm 공통 규칙 초안

software/model import가 들어오면 다음 규칙을 하드웨어와 동일하게 적용한다.

- preview에서 상태를 계산한다
  - `신규`
  - `기존존재`
  - `갱신예정`
  - `검증오류`
- confirm은 항상 batch 단위로 기록한다
- overwrite 정책은 kind별 상세까지 함께 적용한다
  - `software` -> `software_spec`
  - `model` -> `model_spec`

### 미구현 경계

아래는 현재 **문서 초안만 존재하고 코드 미구현** 상태다.

- `SOFTWARE` 시트 parser/importer
- `MODEL` 시트 parser/importer
- 카탈로그 Import 모달의 kind별 진입점 분리
- `software/model`용 preview 컬럼 세분화

#### Wave 3. generic profile 연계
- service/business capability/dataset용 기준문서가 필요하면 별도 입력 포맷 정의
- 또는 외부 CMDB/서비스 카탈로그/데이터 카탈로그와 동기화 검토

### 구현 메모

- `product_catalog_importer.py`는 현재 명확히 hardware 전용 필드를 다루므로, 이름은 유지하되 문서상 “hardware-oriented importer”로 해석한다.
- software/model/generic 확장 시에는 기존 importer에 조건문을 누적하기보다 하위 도메인별 parser/importer 모듈 분리를 우선 검토한다.

---

## 4. 구현 방향

### Phase 0. 분류/역할 기준 고정

목표:
- `template.xlsx`, `spec.xlsx`, 카탈로그, 자산 원장의 역할 구분 확정
- `kind` / `type_key` 체계 초안 확정

작업:
- 운영 기준문서와 정제 기준문서 역할 명시
- 카탈로그가 소유할 필드와 자산이 소유할 필드 구분
- 현재 `asset_type_codes`를 `kind` 수용 가능한 방향으로 확장할지 검토
- `product_catalog.product_type` / `asset_type_key`의 역할 정리

산출물:
- 문서 기준 확정
- 분류표 초안

### Phase 1. 카탈로그 보강 파이프라인 구축

목표:
- `spec.xlsx`를 카탈로그 메뉴와 연결 가능한 형태로 수용

작업:
- `SPEC` 시트 -> 제품/사양 적재 규칙 정의
- `EOSL` 시트 -> lifecycle 적재 규칙 정의
- `product_catalog_importer.py`를 카탈로그 메뉴 기준으로 정비
- 출처/검증/갱신시각 저장 규칙 정의
- 카탈로그 메뉴에 import preview / confirm / overwrite 정책 정의

주의:
- 자동 수집 결과를 무조건 실시간 반영하지 않는다.
- `수집 -> 검토 -> 반영` 흐름이 필요하다.

산출물:
- 카탈로그 Import/동기화 규칙
- spec/eosl 매핑 규칙
- 카탈로그 메뉴 통합 시나리오

### Phase 1A. DB/스키마 정렬 초안

목표:
- 현재 코드 기준(`product_catalog.product_type`, `asset_type_key`, `hardware_spec`, `product_catalog_importer.py`)을 유지하면서 확장 가능한 축을 문서로 먼저 고정

작업:
- `asset_type_codes`에 `kind` 축을 도입할지 결정
- `product_catalog.product_type`와 `kind`의 역할 중복을 해소
- 카탈로그 검증/출처 필드 초안 추가

권장 방향:
- 단기:
  - `product_catalog.product_type` 유지
  - 문서상 `product_type == kind`로 해석
  - `asset_type_key == type_key` 유지
- 중기:
  - `asset_type_codes`에 `kind` 컬럼 추가
  - `product_catalog.product_type`는 deprecated 후보로 전환

---

## 4A. DB / 스키마 변경 초안

### 4A.1 `asset_type_codes`

현재:
- `type_key`
- `code`
- `label`
- `sort_order`
- `is_active`

권장 추가:
- `kind: str`
  - 예: `hardware`, `software`, `model`

의도:
- `type_key`를 실무 분류로 유지하면서, 상위 분류를 질의/필터/입력폼 분기에 사용할 수 있게 함

예시:

| type_key | code | label | kind |
| --- | --- | --- | --- |
| server | SVR | 서버 | hardware |
| network | NET | 네트워크 | hardware |
| middleware | MID | 미들웨어 | software |
| application | APP | 응용 | software |
| llm | LLM | LLM | model |

주의:
- 이 변경은 `asset_code` 생성 규칙과 직접 연결되므로, code 3자리 체계는 당분간 유지
- `kind`는 code 생성이 아니라 분류/입력/UI 분기 기준으로 사용

### 4A.2 `product_catalog`

현재:
- `vendor`
- `name`
- `product_type`
- `category`
- `eos_date`
- `eosl_date`
- `eosl_note`
- `reference_url`
- `asset_type_key`
- `is_placeholder`

권장 추가:
- `version: str | None`
- `source_name: str | None`
- `source_url: str | None`
- `source_confidence: str | None`
- `last_verified_at: datetime | None`
- `verification_status: str | None`
- `import_batch_id: str | None`

권장 해석:
- `product_type`는 당장은 유지하되 `kind`와 동일 축으로 해석
- `asset_type_key`는 세부 분류(type_key)

즉:
- `product_type = hardware`
- `asset_type_key = security`

또는:
- `product_type = model`
- `asset_type_key = llm`

### 4A.3 상세 스키마 방향

현재 유지:
- `HardwareSpec`
- `HardwareInterface`

다음 후보:
- `SoftwareSpec`
- `ModelSpec`

예상 필드 예시:

#### `SoftwareSpec`
- `product_id`
- `edition`
- `license_type`
- `runtime_env`
- `support_end_date`
- `compatibility_note`

#### `ModelSpec`
- `product_id`
- `provider`
- `model_family`
- `context_window`
- `modality`
- `deployment_type`
- `safety_note`

초기에는 실제 DB 추가 전, 스키마 초안과 UI 입력 항목만 먼저 고정해도 충분하다.

### Phase 2. 공통 코어 안정화

목표:
- 현재 자산 원장이 하드웨어 중심이더라도, 향후 `kind` 확장을 수용할 수 있게 구조를 정리

작업:
- `Asset` 공통 필드 범위 재검토
- `kind` 추가 여부 검토
- 카탈로그 참조 구조를 일반화 가능한 형태로 점검
- 공통 검색/상태/관계/이력 API가 유형 중립적으로 유지되는지 점검

산출물:
- Asset 공통 코어 기준
- 확장 가능성 체크리스트

### Phase 3. 대표 유형 3종 시범 확장

목표:
- 모든 유형을 한 번에 처리하지 말고 대표 유형으로 패턴을 검증

우선 대상:
- hardware
- software/middleware
- model/LLM

작업:
- 카탈로그에서 각 유형별 필드 범위 정의
- 상세 화면/등록 흐름 차이 정리
- 관계/상태/검색은 공통 프레임 유지
- 하드웨어는 `spec.xlsx` 기반, software/model은 수동 입력 기준부터 시작

산출물:
- typed detail 패턴 검증
- 추가 유형 확장 기준

### Phase 4. 운영 문서와 시스템 매핑 고도화

목표:
- `template.xlsx`와 시스템 필드 간의 대응을 안정화

작업:
- 시트/컬럼별 업무 의미 정의
- 중복/비효율 항목 통합
- 엑셀 기준과 시스템 기준 차이 문서화

산출물:
- 시트 -> 엔티티 매핑표
- 변경 이유 기록

---

## 5. 구현 우선순위

1. 자산 원장 안정화는 계속 최우선 유지
2. 그와 병행하여 카탈로그 모델 확장 기준을 먼저 고정
3. `spec.xlsx`를 카탈로그 정제 소스로 연결
4. 유형 확장은 representative types로만 먼저 검증
5. 모든 유형의 완전 일반화는 고도화 단계에서 진행

즉, 지금 당장 해야 할 것은 “모든 자산 유형 구현”이 아니라:
- 기준문서 역할 고정
- 카탈로그 확장 구조 고정
- 공통 코어 흔들림 방지
- 대표 유형 패턴 검증

---

## 5A. `spec.xlsx` 검토 -> 반영 플로우

현재 코드의 `product_catalog_importer.py`는 parse/import 유틸은 갖고 있지만, 운영 플로우 기준으로는 아직 “파일 업로드 후 즉시 반영”에 가깝다. 카탈로그 메뉴 통합 시에는 아래 흐름으로 재정렬한다.

### Step 1. 업로드

- 사용자가 카탈로그 메뉴에서 `spec.xlsx` 업로드
- 시스템이 `SPEC`, `EOSL` 시트를 각각 파싱

### Step 2. Preview

- 신규 제품
- 기존 제품과 충돌
- EOS/EOSL만 갱신될 항목
- 필수값 누락/중복/형식 오류

을 구분해서 보여준다.

### Step 3. 검토

사용자는 항목별로 다음 중 하나를 선택할 수 있어야 한다.

- 신규 생성
- 기존 항목 overwrite
- 기존 항목 skip
- 수동 보정 후 반영

### Step 4. Confirm

- 사용자가 확정한 항목만 반영
- 반영 결과를 import batch 단위로 기록

### Step 5. Audit / Trace

- 누가
- 언제
- 어떤 파일로
- 어떤 항목을
- 신규/수정/스킵 했는지

추적 가능해야 한다.

### 권장 API 흐름

1차 초안:
- `POST /api/v1/product-catalog/import/spec/preview`
- `POST /api/v1/product-catalog/import/spec/confirm`
- `POST /api/v1/product-catalog/import/eosl/preview`
- `POST /api/v1/product-catalog/import/eosl/confirm`

또는 운영 편의상:
- `POST /api/v1/product-catalog/import/preview`
- `POST /api/v1/product-catalog/import/confirm`

단일 엔드포인트로 묶고 시트별 결과를 나눠도 된다.

### UI 초안

카탈로그 메뉴에 아래 섹션을 둔다.

1. 제품 목록 그리드
2. 제품 상세/스펙
3. `spec.xlsx` Import 패널
   - 파일 업로드
   - Preview 결과
   - 충돌 정책 선택
   - Confirm

즉, Import는 별도 개발자 유틸이 아니라 카탈로그 관리 기능의 일부가 된다.

---

## 6. 지금 당장 결정해야 하는 것

### 필수 결정 1. 카탈로그의 장기 역할

- 단순 HW 제품 목록인지
- 제품/소프트웨어/모델까지 포함하는 범용 catalog인지

권장: 범용 catalog를 지향하되, 1차 구현은 hardware + software/middleware + model까지만 검증

### 필수 결정 2. `kind` 도입 시점

- 즉시 도입
- `asset_type_codes` 확장 후 후속 도입

권장: 문서 기준은 지금 확정하고, DB 반영은 자산 원장 안정화 이후 도입

### 필수 결정 3. spec 반영 방식

- 자동 반영
- 수동 Import
- 검토 후 반영

권장: `검토 후 반영`

보강:
- preview 없이 즉시 overwrite는 금지에 가깝게 보는 편이 안전하다
- 특히 `SPEC`와 `EOSL`은 기존 제품에 영향을 주므로 batch 단위 검토가 필요하다

### 필수 결정 4. 커스텀 범위

허용:
- 유형별 상세 폼
- 유형별 검증
- 유형별 카탈로그 Import 규칙

공통 유지:
- CRUD 흐름
- 상태/관계/담당자/Alias/사업 귀속
- 검색 진입
- 이력

---

## 7. 실행 메모

- 지금 멈추게 만드는 것은 구현 속도가 아니라 분류/모델 기준의 흔들림이다.
- 따라서 이 계획의 목적은 기능 수를 늘리는 것이 아니라, 이후 변경이 사방에 영향을 주는 범위를 줄이는 것이다.
- 자산 쪽은 계속 `원장`으로 보고, 카탈로그는 `정제된 기준 데이터`, `spec.xlsx`는 `카탈로그 보강 원본`, `template.xlsx`는 `운영 기준문서`로 분리해서 생각한다.
