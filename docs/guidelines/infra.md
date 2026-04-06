# 인프라모듈 작업 지침

> 인프라모듈(infra) 작업 시 참조. 용어 정의와 데이터 원칙을 포함한다.

---

## 도메인 용어

| 용어 | 설명 |
| --- | --- |
| 계약단위 (ContractPeriod) | common 모듈의 ContractPeriod. 인프라 작업의 기준 단위. partner_id NOT NULL |
| 계약단위 단계 (PeriodPhase) | 분석, 설계, 구축, 시험, 안정화 등 진행 단계 |
| 산출물 (Deliverable) | 계약단위 단계별 제출 대상 문서/결과물 |
| 자산 (Asset) | 서버, 네트워크 장비, 보안 장비 등 기술 자산 |
| IP 대역 (IpSubnet) | 업체 범위의 IP 대역, 역할/지역/상대국 등 메타데이터 포함 |
| IP 인벤토리 (AssetIP) | Asset에 연결된 IP 정보, IpSubnet 참조 가능 |
| 포트맵 (PortMap) | 자산 간 통신 관계 |
| 정책 정의 (PolicyDefinition) | 적용 기준이 되는 정책 원본 |
| 정책 적용 상태 (PolicyAssignment) | 고객사/자산 단위 정책 준수 현황 |
| 자산 담당자 매핑 (AssetContact) | 특정 자산과 담당자(PartnerContact)의 역할 연결 |
| 자산 소프트웨어 (AssetSoftware) | 자산에 설치/연동된 SW 정보. relation_type: installed/calls/depends_on |
| 제품 카탈로그 (ProductCatalog) | 글로벌 HW 제품 정보 (partner_id 없음). vendor+name 유니크 |
| HW 스펙 (HardwareSpec) | 제품 카탈로그 1:1 물리 사양 (size_unit, 전원, CPU, 메모리 등) |
| HW 인터페이스 (HardwareInterface) | 제품 카탈로그 1:N 포트/인터페이스 사양 |
| 계약단위-자산 연결 (PeriodAsset) | Asset↔ContractPeriod N:M 연결. role, note 포함 |
| 자산 관계 (AssetRelation) | 자산 간 관계(parent-child, cluster, ha-pair 등) |
| 계약단위 업체 (PeriodPartner) | 계약단위별 업체 역할(고객사/수행사/유지보수사/통신사/벤더) |
| 계약단위 담당자 (PeriodPartnerContact) | 계약단위별 담당자 역할(고객PM/수행PM/구축엔지니어 등) |
| Pin 업체 | UserPreference 기반 사용자별 고정 업체. topbar 셀렉터에 표시, 인프라 전 페이지 기본 컨텍스트 |

---

## 데이터 원칙

- **업체 중심 구조**: `Asset`, `IpSubnet`, `PortMap`, `PolicyAssignment`는 `partner_id` FK로 업체에 귀속된다. `ContractPeriod`는 `partner_id` NOT NULL로 업체에 종속된다.
- `Asset`을 중심으로 `AssetIP`, `PortMap`, `AssetContact`, `AssetSoftware`가 연결된다.
- `Asset.hardware_model_id` FK로 `ProductCatalog`와 연결 (nullable, SET NULL). 기존 vendor/model 컬럼은 하위호환 유지.
- `ProductCatalog`는 글로벌 리소스 (partner_id 없음). `HardwareSpec` 1:1, `HardwareInterface` 1:N 하위 리소스.
- `ProductCatalog`는 사용자 입장에서 제품 등록/조회/편집을 처리하는 메인 화면으로 동작한다.
- **기준정보(마스터 데이터) CRUD는 기준정보 관리 페이지(`/catalog-management/integrity`)에 집중한다.** 제조사 정규화, 속성 아이템, 속성 alias가 여기에 해당한다. 개별 페이지에서 기준정보 편집이 필요하면 기준정보 관리 페이지로 네비게이션 링크를 제공한다 (모달/인라인 폼을 중복 구현하지 않는다).
- 카탈로그 관련 페이지는 2탭 구조: `[제품 카탈로그]` (제품 CRUD) + `[기준정보 관리]` (제조사/제품유사도/속성). 기준정보 관리 내부 탭: 제조사 / 제품 / 속성.
- 카탈로그는 글로벌 기본 분류체계의 **최종 분류 노드**에 직접 연결할 수 있다. 자유입력 `category`는 하위호환 텍스트로만 남기고, 신규 입력은 분류 노드 연결을 우선한다.
- `ProductCatalog` 삭제 시 참조하는 자산이 있으면 409로 차단.
- `Asset`은 계약단위와 `PeriodAsset` N:M으로만 연결한다 (`project_id` FK는 제거됨).
- `AssetRelation`으로 자산 간 관계(parent-child, cluster, ha-pair 등)를 표현한다.
- `PeriodPartner`로 계약단위-업체 역할(고객사/수행사/유지보수사/통신사/벤더)을 관리한다.
- `PeriodPartnerContact`로 계약단위-담당자 역할(고객PM/수행PM/구축엔지니어 등)을 관리한다. `PeriodPartner`에 종속(CASCADE 삭제).
- Pin 업체: `UserPreference`(key=`infra.pinned_partner_id`)로 사용자별 고정 업체를 DB 저장. `infra.last_period_id`로 마지막 선택 계약단위 기억. topbar 2단 셀렉터(업체+계약단위)로 컨텍스트 전환.
- 정책은 반드시 `PolicyDefinition`과 `PolicyAssignment`로 분리한다.
- IP 중복 검증은 업체 범위 내에서 수행한다.
- 자산명은 업체 내 unique를 기본 원칙으로 한다.
- 인프라 탐색 구조는 데이터 모델보다 실제 작업 시작점을 우선한다.
  - 전역 메뉴에서 최소 `프로젝트`, `자산`, `네트워크(IP/포트맵)`, `배치`, `업체`, `이력` 수준의 진입성을 확보하는 방향을 우선 검토한다.
  - `IP 인벤토리`, `포트맵`, `물리배치`처럼 독립 업무 성격이 강한 화면은 특정 페이지 내부 탭에만 숨기지 않는다.
- topbar 고객사/계약단위 선택기가 있더라도, 인프라 화면 본문 상단에 현재 컨텍스트를 다시 드러내는 것을 기본 원칙으로 한다.
  - 최소 노출 정보: 현재 고객사, 현재 계약단위(프로젝트), 현재 범위 필터
  - 컨텍스트 미선택 상태는 단순 빈 메시지 대신 선택 CTA와 안내를 함께 제공한다.
- 자산 식별자는 목적별로 분리한다.
  - `asset_code`: 시스템 내부 식별자
  - `project_asset_number`: 프로젝트 수행 기준 관리번호
  - `customer_asset_number`: 고객 기준 자산번호
  - `asset_name`: 물리 자산 식별명
- 자산 분류는 자유입력 문자열보다 분류체계 노드 참조를 우선한다.
  - 저장 기준은 `classification_node_id`
  - 목록 표시 기준은 분류 경로와 레벨 alias(`대구분/중구분/소구분` 등)
  - 입력 UX는 대/중/소 전체 선택보다 **최종 분류 선택**을 기본으로 한다.
  - 사용자가 원하는 분류가 없더라도 자산 입력 화면에서 자동 생성하지 않고, 카탈로그 메인 화면에서 기준 트리를 수정하도록 유도한다.
- 자산 목록과 입력 UX는 내부 코드보다 `project_asset_number`, `customer_asset_number`, `asset_name`을 우선 노출하는 방향으로 설계한다.
- 상태값은 DB 컬럼에 문자열로 저장하되, 코드에서는 **허용값 집합을 한 곳에서 관리**한다.
  - 스키마 레벨: 가능하면 `Literal` 또는 Enum으로 입력값을 제한한다.
  - 서비스 레벨: 외부 입력을 그대로 신뢰하지 말고 허용값 집합을 다시 검증한다.
  - DB 레벨: 기존 마이그레이션 비용과 호환성을 위해 문자열 컬럼 유지가 기본이다. 실제 DB enum 타입 도입은 별도 아키텍처 결정 없이는 진행하지 않는다.
- 새 상태값/분류값을 추가할 때는 문자열 literal을 여러 서비스/JS 파일에 흩뿌리지 말고, 스키마 또는 상수 모듈을 source of truth로 삼는다.
- 포트맵은 자산 간 연결뿐 아니라 외부 구간 표현을 위해 `src_asset_id`, `dst_asset_id`를 nullable로 둘 수 있다.
- 정책 적용 상태는 `not_checked`, `compliant`, `non_compliant`, `exception`, `not_applicable` 범위를 기본값으로 사용한다.
- 연락처는 업체에 소속되고, 자산에는 매핑(AssetContact)으로 연결한다.
- 인프라 CRUD(계약단위/자산/IP대역/포트맵/정책)는 `audit.log()`로 감사 로그를 기록한다.
- Excel Import/Export는 업체 단위로 수행한다. Export 시 옵션 계약단위 필터로 해당 계약단위 자산만 포함 가능. 3시트(Inventory/IP대역/Portmap) 구조.
- 제품 카탈로그 Import는 글로벌(partner_id 불필요). `spec` 도메인(제품+HW스펙)과 `eosl` 도메인(EOS/EOSL 날짜)으로 분리.
- `ContractPeriod`는 common 모듈에 위치하며, infra에서 `contract_period_id` FK로 참조한다. infra → common 방향 import만 허용.
- 프로젝트별 분류 레이아웃 연결은 `ContractPeriod.classification_layout_id` 숫자 필드로 유지하되, common ORM이 infra 테이블 FK를 직접 참조하지 않도록 관리한다.
  - 실제 레이아웃 해석과 검증 책임은 infra 서비스(`classification_layout_service` 등)에 둔다.
  - DB FK/인덱스 변경이 필요하면 common 모델 변경과 별도 migration으로 따라간다.

## 상태값 / 코드값 규칙

- `classification_nodes` 통합 메타:
  - 분류 노드가 `asset_type_key`, `asset_type_code`, `asset_type_label`, `asset_kind`, `is_catalog_assignable`를 직접 가진다.
  - 자산 코드 생성, 카탈로그 저장, 자산 등록 기본값은 이 메타를 source of truth로 사용한다.
  - 별도 `asset_type_codes`, `asset_type_classification_mappings` 테이블은 migration 0045에서 제거되었다.
- `ProductCatalog.product_type`:
  - 현재는 제품 상위 분류를 나타내는 문자열로 유지한다.
  - 분류 노드의 `asset_kind`와 일관되게 관리하되, 카탈로그 목록 필터와 Import 호환을 위해 독립 필드는 유지한다.
- `ProductCatalog.classification_node_code`:
  - 글로벌 기본 분류체계의 최종 분류 node를 가리키는 연결값이다.
  - 자산 등록 시 사용자가 분류를 따로 고르지 않으면, 카탈로그의 node_code를 현재 프로젝트 분류체계에서 우선 해석해 기본값으로 제안한다.
  - 사용자 화면에서는 “카탈로그의 최종 분류”로 보이게 하고, 내부 메타 구조는 직접 노출하지 않는다.
- `ProductCatalog` 메타 필드(`source_name`, `source_url`, `source_confidence`, `last_verified_at`, `verification_status`, `import_batch_id`)는 수집/검토/반영 추적을 위한 필드다.
  - 단순 표시용이 아니라 import batch와 검증상태를 남기는 운영 메타로 취급한다.
- `Asset.status`:
  - DB에는 문자열로 저장한다.
  - 새 상태를 추가할 때는 스키마와 프론트 필터 값을 함께 갱신한다.
  - Import 기본값과 생성 기본값이 다르면 이유를 문서나 코드 주석으로 남긴다.
- `PeriodPhase.status`, `PeriodPhase.submission_status`, `PolicyAssignment.status`, `PortMap.status`:
  - 스키마에서 허용값 제한을 우선 적용한다.
  - 집계 로직(`infra_metrics` 등)에서 특정 상태값 문자열에 의존하는 경우, 상태 추가/변경 시 같은 변경 세트에서 함께 갱신한다.
- `CatalogAttributeOption.label`: 영문 기본 라벨. 한글(완성형·자모) 포함 불가.
- `CatalogAttributeOption.label_kr`: 한글 보조 라벨. 저장 시 `label_kr_auto` alias 자동 동기화.
- 사용자 표시 라벨(한글)과 DB/API 값(영문 또는 정규화된 문자열)은 분리한다. DB/API 값을 UI 문구 변경에 맞춰 같이 바꾸지 않는다.
- 분류체계의 레벨 alias는 표시용 메타데이터다.
  - 자산 목록 헤더(`대구분/중구분/소구분`)와 입력 라벨은 alias를 사용한다.
  - 실제 검증과 매핑은 `classification_node_id` 또는 `classification_node_code` 기준으로 수행한다.
- 사용자가 조정 가능한 인프라 화면 레이아웃은 상태 저장/복원을 기본 원칙으로 한다.
  - 예: 트리 패널 너비, 목록-상세 패널 비율, 트리 펼침/접힘, 마지막 선택 항목
  - 카탈로그, 분류체계, 자산처럼 탐색형 2~3단 패널 화면은 새로고침/재진입 후에도 직전 상태를 최대한 유지한다.
  - 저장 단위는 화면 범위로 나누고, 프로젝트 컨텍스트 의존 상태는 가능하면 프로젝트별 key로 분리한다.

## 자산명 / 역할명 규칙

- `asset_name`은 물리 자산명이다.
  - 예: `인터넷방화벽#1(old)`, `인터넷방화벽#1(new)`
- `role_name`은 논리 역할명이다.
  - 예: `인터넷방화벽#1`
- 따라서 `asset_name`과 `role_name`을 같은 필드로 합치지 않는다.
- 자산명 기반 역할명 추천은 허용하되, 추천 결과를 자동 선택/자동 연결/자동 생성하면 안 된다.
- 추천 로직은 입력 편의성 보조 장치로만 사용하고, 최종 확정은 사용자가 한다.
