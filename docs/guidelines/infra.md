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
- `ProductCatalog` 삭제 시 참조하는 자산이 있으면 409로 차단.
- `Asset`은 계약단위와 `PeriodAsset` N:M으로만 연결한다 (`project_id` FK는 제거됨).
- `AssetRelation`으로 자산 간 관계(parent-child, cluster, ha-pair 등)를 표현한다.
- `PeriodPartner`로 계약단위-업체 역할(고객사/수행사/유지보수사/통신사/벤더)을 관리한다.
- `PeriodPartnerContact`로 계약단위-담당자 역할(고객PM/수행PM/구축엔지니어 등)을 관리한다. `PeriodPartner`에 종속(CASCADE 삭제).
- Pin 업체: `UserPreference`(key=`infra.pinned_partner_id`)로 사용자별 고정 업체를 DB 저장. `infra.last_period_id`로 마지막 선택 계약단위 기억. topbar 2단 셀렉터(업체+계약단위)로 컨텍스트 전환.
- 정책은 반드시 `PolicyDefinition`과 `PolicyAssignment`로 분리한다.
- IP 중복 검증은 업체 범위 내에서 수행한다.
- 자산명은 업체 내 unique를 기본 원칙으로 한다.
- 상태값은 문자열 하드코딩 대신 enum으로 통일한다.
- 포트맵은 자산 간 연결뿐 아니라 외부 구간 표현을 위해 `src_asset_id`, `dst_asset_id`를 nullable로 둘 수 있다.
- 정책 적용 상태는 `not_checked`, `compliant`, `non_compliant`, `exception`, `not_applicable` 범위를 기본값으로 사용한다.
- 연락처는 업체에 소속되고, 자산에는 매핑(AssetContact)으로 연결한다.
- 인프라 CRUD(계약단위/자산/IP대역/포트맵/정책)는 `audit.log()`로 감사 로그를 기록한다.
- Excel Import/Export는 업체 단위로 수행한다. Export 시 옵션 계약단위 필터로 해당 계약단위 자산만 포함 가능. 3시트(Inventory/IP대역/Portmap) 구조.
- 제품 카탈로그 Import는 글로벌(partner_id 불필요). `spec` 도메인(제품+HW스펙)과 `eosl` 도메인(EOS/EOSL 날짜)으로 분리.
- `ContractPeriod`는 common 모듈에 위치하며, infra에서 `contract_period_id` FK로 참조한다. infra → common 방향 import만 허용.
