# 프로젝트 구조

> 파일 단위 프로젝트 구조와 모듈별 역할.
> 디렉토리/파일 추가/삭제 시 이 문서도 함께 갱신한다.

---

## 앱 엔트리포인트 및 core

```text
app/
├── main.py                          # uvicorn 엔트리포인트, ENABLED_MODULES 기반 동적 모듈 등록
└── core/                            # 모듈-독립 인프라
    ├── app_factory.py               # FastAPI 앱 생성, 전역 예외 핸들러 등록
    ├── config.py                    # 환경변수/설정값 로드, ENABLED_MODULES 파싱
    ├── database.py                  # SQLAlchemy 엔진/세션 설정 (PostgreSQL)
    ├── exceptions.py                # 커스텀 예외 클래스 (401~422)
    ├── base_model.py                # TimestampMixin, 공통 Base
    ├── code_generator.py            # 계층적 코드 채번 (고객·사업·기간 코드)
    ├── _normalize.py                # 날짜/월 정규화 (normalize_month, normalize_date)
    ├── pages.py                     # 공통 페이지 라우터 (/, /index 등)
    ├── auth/                        # 인증/인가
    │   ├── authorization.py         # can_*() 공통 권한 함수, 모듈 접근 제어
    │   ├── constants.py             # 역할 상수
    │   ├── dependencies.py          # get_current_user, require_admin, require_module_access
    │   ├── middleware.py            # 세션 인증 미들웨어
    │   ├── password.py              # 비밀번호 해싱 (bcrypt)
    │   ├── router.py                # /api/v1/auth 라우터 (로그인/로그아웃)
    │   └── service.py               # 인증 서비스 (사용자 검증, 비밀번호 정책)
    └── startup/                     # 초기화
        ├── lifespan.py              # FastAPI lifespan (startup/shutdown)
        ├── database_init.py         # DB 스키마 준비, Alembic 실행
        └── bootstrap.py             # 초기 관리자 계정 생성, 기본 역할 시드
```

## 공통모듈 (common) — 항상 활성

```text
app/modules/common/
├── models/
│   ├── user.py                  # User (사용자)
│   ├── user_preference.py       # UserPreference (사용자 설정)
│   ├── login_failure.py         # LoginFailure (로그인 실패 기록)
│   ├── role.py                  # Role (RBAC 역할, permissions JSON)
│   ├── partner.py               # Partner (업체)
│   ├── partner_contact.py       # PartnerContact (업체 담당자)
│   ├── partner_contact_role.py  # PartnerContactRole (담당자 역할)
│   ├── setting.py               # Setting (시스템 설정)
│   ├── term_config.py           # TermConfig (UI 용어 설정)
│   ├── audit_log.py             # AuditLog (감사 로그)
│   ├── contract.py              # Contract (사업 원장 — 공통 사업 식별 단위)
│   ├── contract_period.py       # ContractPeriod (계약단위 — 회계/인프라 공유)
│   └── contract_type_config.py  # ContractTypeConfig (사업유형 설정)
├── schemas/
│   ├── auth.py                  # 인증 관련 스키마
│   ├── partner.py               # 업체 스키마
│   ├── partner_contact.py       # 업체 담당자 스키마
│   ├── partner_contact_role.py  # 담당자 역할 스키마
│   ├── contract.py              # 사업 스키마
│   ├── contract_period.py       # 계약단위 스키마
│   ├── contract_type_config.py  # 사업유형 스키마
│   ├── role.py                  # 역할 스키마
│   ├── setting.py               # 시스템 설정 스키마
│   ├── term_config.py           # 용어 설정 스키마
│   └── user.py                  # 사용자 스키마
├── services/
│   ├── user.py                  # 사용자 CRUD, CSV 일괄 등록
│   ├── partner.py               # 업체/담당자 CRUD
│   ├── _partner_helpers.py      # 업체 관련 헬퍼
│   ├── contract_service.py      # 사업/계약단위 CRUD
│   ├── contract_type_config.py  # 사업유형 CRUD, 시드 데이터
│   ├── setting.py               # 시스템 설정 CRUD
│   ├── term_config.py           # 용어 설정 CRUD, 시드 데이터
│   ├── user_preference.py       # 사용자 환경설정
│   ├── role.py                  # 역할 CRUD
│   ├── health.py                # 헬스체크 (DB 연결 확인)
│   └── audit.py                 # 감사 로그 유틸
├── routers/
│   ├── users.py                 # /api/v1/users
│   ├── partners.py              # /api/v1/partners
│   ├── contracts.py             # /api/v1/contracts, /api/v1/contract-periods
│   ├── contract_types.py        # /api/v1/contract-types
│   ├── settings.py              # /api/v1/settings
│   ├── term_configs.py          # /api/v1/term-configs
│   ├── health.py                # /api/v1/health
│   ├── user_preferences.py      # /api/v1/preferences
│   ├── roles.py                 # /api/v1/roles
│   └── pages.py                 # 공통 HTML 페이지 렌더링
└── (templates은 app/templates/에 통합)
```

## 회계모듈 (accounting)

```text
app/modules/accounting/
├── models/
│   ├── contract.py              # Contract (회계 확장 — common 참조용 re-export)
│   ├── contract_period.py       # ContractPeriod (회계 확장 — common 참조용 re-export)
│   ├── contract_type_config.py  # ContractTypeConfig (회계 확장 — common 참조용 re-export)
│   ├── contract_sales_detail.py # ContractSalesDetail (영업 전용 확장 — ContractPeriod 1:1)
│   ├── contract_contact.py      # ContractContact (Period별 담당자)
│   ├── monthly_forecast.py      # MonthlyForecast (월별 예상 매출/GP)
│   ├── transaction_line.py      # TransactionLine (매출/매입 실적)
│   ├── receipt.py               # Receipt (입금)
│   └── receipt_match.py         # ReceiptMatch (입금 배분)
├── schemas/
│   ├── contract.py              # 사업 스키마 (회계 확장)
│   ├── contract_sales_detail.py # 영업 확장 스키마
│   ├── contract_contact.py      # 사업 담당자 스키마
│   ├── monthly_forecast.py      # Forecast 스키마
│   ├── receipt.py               # 입금 스키마
│   ├── receipt_match.py         # 입금 배분 스키마
│   ├── report.py                # 보고서 스키마
│   └── transaction_line.py      # 매출/매입 스키마
├── services/
│   ├── contract.py              # 사업 서비스 (회계 확장)
│   ├── contract_sales_detail.py # 영업 확장 정보 CRUD
│   ├── contract_type_config.py  # 사업유형 서비스 (회계 확장)
│   ├── _contract_helpers.py     # 사업 관련 교차 도메인 헬퍼
│   ├── contract_contact.py      # 사업 담당자 매핑
│   ├── monthly_forecast.py      # Forecast CRUD
│   ├── transaction_line.py      # 매출/매입 실적 CRUD
│   ├── receipt.py               # 입금 CRUD
│   ├── receipt_match.py         # FIFO 자동 배분, 수동 배분
│   ├── forecast_sync.py         # Forecast -> 실적 동기화
│   ├── ledger.py                # 원장 뷰 (통합 조회, /api/v1/ledger/periods)
│   ├── metrics.py               # 공통 집계 엔진
│   ├── dashboard.py             # 대시보드 집계
│   ├── report.py                # 보고서 데이터 생성
│   ├── _report_export.py        # 보고서 Excel Export
│   ├── importer.py              # Excel Import
│   └── exporter.py              # Excel Export (영업관리 원장)
├── routers/
│   ├── contracts.py             # /api/v1/contracts (회계 확장)
│   ├── contract_sales_details.py # /api/v1/contract-periods/{id}/sales-detail
│   ├── contract_contacts.py     # /api/v1/contract-contacts
│   ├── forecasts.py             # /api/v1/.../forecasts
│   ├── transaction_lines.py     # /api/v1/.../transaction-lines
│   ├── receipts.py              # /api/v1/.../receipts
│   ├── receipt_matches.py       # /api/v1/.../receipt-matches
│   ├── dashboard.py             # /api/v1/dashboard
│   ├── reports.py               # /api/v1/reports
│   ├── excel.py                 # /api/v1/excel
│   └── pages.py                 # 회계 HTML 페이지 렌더링
└── (templates은 app/templates/에 통합)
```

## 인프라모듈 (infra)

```text
app/modules/infra/
├── models/
│   ├── period_phase.py          # PeriodPhase (계약단위 단계)
│   ├── period_deliverable.py    # PeriodDeliverable (산출물)
│   ├── asset.py                 # Asset (기술 자산)
│   ├── asset_alias.py           # AssetAlias (자산 별칭)
│   ├── asset_ip.py              # AssetIP (자산 IP)
│   ├── asset_contact.py         # AssetContact (자산 담당자 매핑)
│   ├── asset_relation.py        # AssetRelation (자산 간 관계)
│   ├── asset_event.py           # AssetEvent (자산 변경이력)
│   ├── asset_related_partner.py # AssetRelatedPartner (자산 관련업체 이력)
│   ├── asset_role.py            # AssetRole (논리 역할 정의)
│   ├── asset_role_assignment.py # AssetRoleAssignment (역할 할당)
│   ├── asset_software.py        # AssetSoftware (자산 설치 SW)
│   ├── period_asset.py          # PeriodAsset (계약단위-자산 N:M)
│   ├── period_partner.py        # PeriodPartner (계약단위-업체 역할)
│   ├── period_partner_contact.py # PeriodPartnerContact (계약단위-담당자 역할)
│   ├── ip_subnet.py             # IpSubnet (IP 대역)
│   ├── port_map.py              # PortMap (포트맵)
│   ├── policy_definition.py     # PolicyDefinition (정책 정의)
│   ├── policy_assignment.py     # PolicyAssignment (정책 적용 상태)
│   ├── product_catalog.py       # ProductCatalog (글로벌 제품 카탈로그)
│   ├── hardware_spec.py         # HardwareSpec (제품 1:1 HW 스펙)
│   ├── hardware_interface.py    # HardwareInterface (제품 1:N 인터페이스)
│   ├── software_spec.py         # SoftwareSpec (제품 SW 스펙)
│   ├── model_spec.py            # ModelSpec (모델 스펙)
│   ├── generic_catalog_profile.py # GenericCatalogProfile (범용 카탈로그 프로필)
│   ├── catalog_attribute_def.py # CatalogAttributeDef (카탈로그 속성 정의)
│   ├── catalog_attribute_option.py # CatalogAttributeOption (속성 옵션)
│   ├── catalog_attribute_option_alias.py # CatalogAttributeOptionAlias (옵션 별칭)
│   ├── catalog_vendor_alias.py  # CatalogVendorAlias (제조사 별칭)
│   ├── product_catalog_attribute_value.py # ProductCatalogAttributeValue (제품 속성값)
│   ├── classification_layout.py # ClassificationLayout (분류 레이아웃)
│   ├── classification_layout_level.py # ClassificationLayoutLevel (분류 레벨 정의)
│   ├── classification_layout_level_key.py # ClassificationLayoutLevelKey (레벨 키 매핑)
│   ├── product_catalog_list_cache.py # ProductCatalogListCache (제품 목록 캐시)
│   ├── center.py                # Center (데이터센터)
│   ├── room.py                  # Room (전산실)
│   └── rack.py                  # Rack (랙)
├── schemas/
│   ├── period_phase.py          # 단계 스키마
│   ├── period_deliverable.py    # 산출물 스키마
│   ├── asset.py                 # 자산 스키마
│   ├── asset_alias.py           # 자산 별칭 스키마
│   ├── asset_ip.py              # 자산 IP 스키마
│   ├── asset_contact.py         # 자산 담당자 스키마
│   ├── asset_relation.py        # 자산 관계 스키마
│   ├── asset_event.py           # 자산 변경이력 스키마
│   ├── asset_related_partner.py # 자산 관련업체 스키마
│   ├── asset_role.py            # 자산 역할 스키마
│   ├── asset_role_action.py     # 역할 액션 스키마
│   ├── asset_software.py        # 자산 SW 스키마
│   ├── period_asset.py          # 계약단위-자산 스키마
│   ├── period_partner.py        # 계약단위-업체 스키마
│   ├── period_partner_contact.py # 계약단위-담당자 스키마
│   ├── infra_import.py          # Import 프리뷰/결과 스키마
│   ├── ip_subnet.py             # IP 대역 스키마
│   ├── port_map.py              # 포트맵 스키마
│   ├── policy_definition.py     # 정책 정의 스키마
│   ├── policy_assignment.py     # 정책 적용 스키마
│   ├── product_catalog.py       # 제품 카탈로그 스키마
│   ├── hardware_spec.py         # HW 스펙 스키마
│   ├── hardware_interface.py    # HW 인터페이스 스키마
│   ├── software_spec.py         # SW 스펙 스키마
│   ├── model_spec.py            # 모델 스펙 스키마
│   ├── generic_catalog_profile.py # 범용 프로필 스키마
│   ├── catalog_attribute.py     # 카탈로그 속성 스키마
│   ├── catalog_attribute_option.py # 속성 옵션 스키마
│   ├── catalog_attribute_option_alias.py # 옵션 별칭 스키마
│   ├── catalog_similarity.py    # 카탈로그 유사도 스키마
│   ├── catalog_vendor_management.py # 제조사 관리 스키마
│   ├── product_catalog_attribute_value.py # 제품 속성값 스키마
│   ├── classification_layout.py # 분류 레이아웃 스키마
│   ├── project_classification_layout.py # 프로젝트 분류 레이아웃 스키마
│   ├── center.py                # 센터 스키마
│   ├── room.py                  # 전산실 스키마
│   └── rack.py                  # 랙 스키마
├── services/
│   ├── phase_service.py         # 계약단위 단계 CRUD
│   ├── asset_service.py         # 자산/자산IP/담당자 CRUD
│   ├── asset_alias_service.py   # 자산 별칭 CRUD
│   ├── asset_event_service.py   # 자산 변경이력 CRUD
│   ├── asset_related_partner_service.py # 자산 관련업체 CRUD
│   ├── asset_role_service.py    # 자산 역할 관리
│   ├── asset_relation_service.py # 자산 관계 CRUD
│   ├── asset_software_service.py # 자산 SW CRUD
│   ├── network_service.py       # IP 대역 CRUD
│   ├── policy_service.py        # 정책 정의/적용 CRUD
│   ├── period_asset_service.py  # 계약단위-자산 연결/해제
│   ├── period_partner_service.py # 계약단위-업체 CRUD
│   ├── period_partner_contact_service.py # 계약단위-담당자 CRUD
│   ├── infra_metrics.py         # 현황판 집계 서비스
│   ├── layout_service.py        # 물리 배치(센터/전산실/랙) 관리
│   ├── classification_layout_service.py # 분류 레이아웃 CRUD
│   ├── classification_view_service.py # 분류 조회 서비스
│   ├── classification_identity_service.py # 분류 식별 서비스
│   ├── _helpers.py              # 공유 헬퍼 (ensure_partner_exists, get_period_asset_ids)
│   ├── infra_importer.py        # Excel Import (자산/IP/포트맵, 업체 단위)
│   ├── infra_exporter.py        # Excel Export (업체 단위 3시트, 옵션 계약단위 필터)
│   ├── product_catalog_service.py # 제품 카탈로그/스펙/인터페이스 CRUD
│   ├── product_catalog_importer.py # 제품 카탈로그 Excel Import (SPEC/EOSL)
│   ├── product_catalog_attribute_service.py # 제품 속성값 관리
│   ├── catalog_attribute_service.py # 카탈로그 속성 정의 CRUD
│   ├── catalog_alias_service.py # 제조사/옵션 별칭 관리
│   ├── catalog_integrity_service.py # 카탈로그 정합성 점검
│   └── catalog_similarity_service.py # 카탈로그 유사도/중복 탐지
├── routers/
│   ├── period_phases.py         # /api/v1/contract-periods/{id}/phases
│   ├── period_deliverables.py   # /api/v1/contract-periods/{id}/deliverables
│   ├── assets.py                # /api/v1/assets
│   ├── asset_aliases.py         # /api/v1/assets/{id}/aliases, /api/v1/asset-aliases/{id}
│   ├── asset_ips.py             # /api/v1/.../ips
│   ├── asset_contacts.py        # /api/v1/.../contacts
│   ├── asset_events.py          # /api/v1/.../asset-events
│   ├── asset_related_partners.py # /api/v1/asset-related-partners
│   ├── asset_roles.py           # /api/v1/asset-roles
│   ├── asset_relations.py       # /api/v1/asset-relations
│   ├── asset_softwares.py       # /api/v1/assets/{id}/software, /api/v1/asset-software/{id}
│   ├── ip_subnets.py            # /api/v1/ip-subnets
│   ├── port_maps.py             # /api/v1/port-maps
│   ├── policies.py              # /api/v1/policies
│   ├── policy_assignments.py    # /api/v1/policy-assignments
│   ├── period_assets.py         # /api/v1/period-assets
│   ├── period_partners.py       # /api/v1/period-partners
│   ├── period_partner_contacts.py # /api/v1/period-partner-contacts
│   ├── infra_dashboard.py       # /api/v1/infra-dashboard (집계 + 감사로그)
│   ├── infra_excel.py           # /api/v1/infra-excel (Import/Export, spec/eosl 포함)
│   ├── product_catalogs.py      # /api/v1/product-catalog
│   ├── catalog_attributes.py    # /api/v1/catalog-attributes
│   ├── catalog_integrity.py     # /api/v1/catalog-integrity
│   ├── classification_layouts.py # /api/v1/classification-layouts
│   ├── centers.py               # /api/v1/centers
│   ├── rooms.py                 # /api/v1/rooms
│   ├── racks.py                 # /api/v1/racks
│   └── pages.py                 # 인프라 HTML 페이지 렌더링
└── templates/
    ├── infra_projects.html      # 계약단위 목록 (/periods)
    ├── infra_project_detail.html # 계약단위 상세 (탭 구조)
    ├── infra_project_classifications.html # 프로젝트 분류체계
    ├── infra_assets.html        # 자산 목록
    ├── infra_asset_roles.html   # 자산 역할 관리
    ├── infra_audit_history.html # 인프라 감사 이력
    ├── infra_contacts.html      # 계약단위 업체/담당자 연결
    ├── infra_ip_inventory.html  # IP 대역 관리
    ├── infra_port_maps.html     # 포트맵
    ├── infra_policies.html      # 정책 적용 현황
    ├── infra_policy_definitions.html # 정책 정의 관리
    ├── infra_physical_layout.html # 물리 배치 (센터/전산실/랙)
    ├── infra_dashboard.html     # 인프라 현황판
    ├── infra_inventory_assets.html # 자산 횡단 검색
    └── infra_import.html        # 자산 Excel Import (3단계 위저드)
```

## CLI (MVP 이후)

```text
app/cli/
├── export_standalone.py         # Standalone 배포용 데이터 내보내기 (미구현)
└── import_standalone.py         # Standalone 배포용 데이터 가져오기 (미구현)
```

## 주요 계획 문서

```text
docs/superpowers/plans/
├── 2026-03-24-infra-module-roadmap.md      # 인프라 active roadmap (단일 실행 기준)
├── 2026-03-24-asset-model-expansion.md     # 자산 모델 확장 + 카탈로그 통합 계획
├── 2026-03-24-layout-and-alias.md          # 배치도/Alias 세부 참조 계획
├── 2026-03-24-asset-registration-simplify.md # 자산 등록 간소화 참조 계획
├── 2026-03-25-asset-ledger-and-role-view.md # 자산 원장/역할 뷰 계획
├── 2026-03-26-asset-classification-scheme.md # 자산 분류체계 설계
├── 2026-03-24-asset-type-code.md           # 자산유형 코드 계획
├── 2026-03-24-customer-to-partner.md       # Customer → Partner 리네이밍
├── 2026-03-23-unified-business-model.md    # 사업/계약단위 통합
├── 2026-03-23-code-numbering.md            # 코드 채번 체계
├── 2026-03-20-customer-centric-infra-plan.md # 고객 중심 인프라 전환
├── 2026-03-18-modular-migration-plan.md    # 모듈 분리 마이그레이션
├── 2026-03-18-infra-module-enhancement-plan.md # 인프라 모듈 개선
└── 2026-03-18-infra-phase2-plan.md         # 인프라 Phase 2
```

## 프론트엔드

```text
app/static/
├── js/
│   ├── utils.js                 # 공통 유틸 (fmt, fmtNumber, fmtPct 등)
│   ├── contracts.js             # 사업 목록
│   ├── contract_detail.js       # 사업 상세
│   ├── my_contracts.js          # 내 사업
│   ├── partners.js              # 업체
│   ├── dashboard.js             # 대시보드
│   ├── reports.js               # 보고서
│   ├── users.js                 # 사용자 관리
│   ├── system.js                # 시스템 설정
│   ├── infra_assets.js          # 인프라 자산
│   ├── infra_asset_roles.js     # 자산 역할 관리
│   ├── infra_audit_history.js   # 인프라 감사 이력
│   ├── infra_contacts.js        # 인프라 업체/담당자
│   ├── infra_dashboard.js       # 인프라 현황판
│   ├── infra_import.js          # 자산 Excel Import
│   ├── infra_inventory_assets.js # 자산 횡단 검색
│   ├── infra_ip_inventory.js    # 인프라 IP 대역
│   ├── infra_physical_layout.js # 물리 배치 관리
│   ├── infra_policies.js        # 인프라 정책
│   ├── infra_policy_definitions.js # 정책 정의 관리
│   ├── infra_port_maps.js       # 인프라 포트맵
│   ├── infra_product_catalog.js # 제품 카탈로그
│   ├── infra_catalog_management.js # 카탈로그 제조사/제품 관리
│   ├── infra_catalog_integrity.js # 카탈로그 정합성
│   ├── infra_project_classifications.js # 프로젝트 분류체계
│   ├── infra_projects.js        # 인프라 계약단위 목록
│   ├── infra_project_detail.js  # 인프라 계약단위 상세
│   └── lucide.js                # 아이콘 라이브러리
├── css/
│   ├── base.css                 # 전역 스타일, CSS 변수 (light/dark)
│   ├── components.css           # 재사용 컴포넌트
│   ├── contract_detail.css      # 사업 상세
│   ├── partners.css             # 업체
│   ├── dashboard.css            # 대시보드
│   ├── reports.css              # 보고서
│   ├── system.css               # 시스템 설정
│   ├── infra_common.css         # 인프라 공통
│   ├── login.css                # 로그인 전용
│   └── change_password.css      # 비밀번호 변경 전용
└── img/
    └── logo.svg                 # 로고

app/templates/                   # 공통 및 회계 템플릿
├── base.html                    # 공통 레이아웃 (동적 네비게이션)
├── login.html                   # 로그인
├── change_password.html         # 비밀번호 변경
├── index.html                   # 인덱스
├── dashboard.html               # 대시보드
├── contracts.html               # 사업 목록
├── contract_detail.html         # 사업 상세
├── my_contracts.html            # 내 사업
├── partners.html                # 업체
├── reports.html                 # 보고서
├── users.html                   # 사용자 관리
├── system.html                  # 시스템 설정
├── audit_logs.html              # 감사 로그 (placeholder)
├── product_catalog.html         # 제품 카탈로그 (글로벌 리소스)
├── catalog_vendors.html         # 카탈로그 제조사 관리
├── catalog_products.html        # 카탈로그 제품 관리
├── catalog_integrity.html       # 카탈로그 정합성
└── {components}/
    └── _modal_add_contract.html # 사업 추가 모달
```

## 테스트

```text
tests/
├── conftest.py                  # DB 세션 (PostgreSQL), 기본 유저/역할 fixture
├── common/
│   ├── test_auth_service.py
│   ├── test_code_generator.py
│   ├── test_contract_service.py
│   ├── test_partner_service.py
│   └── test_user_service.py     # 사용자 권한 조합 -> Role 매핑, 태그 표시
├── accounting/
│   ├── test_contract_schema.py
│   ├── test_contract_service.py
│   ├── test_contract_sales_detail.py
│   ├── test_receipt_match_service.py
│   ├── test_transaction_safety.py
│   ├── test_metrics.py
│   ├── test_dashboard_service.py
│   ├── test_report_service.py
│   └── test_importer.py
├── infra/
│   ├── test_phase_service.py
│   ├── test_asset_service.py
│   ├── test_asset_contact_service.py
│   ├── test_asset_event_service.py
│   ├── test_asset_related_partner_service.py
│   ├── test_asset_role_service.py
│   ├── test_asset_type_classification_mapping_service.py
│   ├── test_network_service.py
│   ├── test_port_map_service.py
│   ├── test_policy_service.py
│   ├── test_infra_importer.py
│   ├── test_period_asset_service.py
│   ├── test_asset_relation_service.py
│   ├── test_period_partner_service.py
│   ├── test_period_partner_contact_service.py
│   ├── test_layout_service.py
│   ├── test_catalog_alias_service.py
│   └── test_partner_centric.py     # 업체 scope CRUD, 계약단위 필터, Export E2E
├── test_database.py             # 스키마 정합성
├── test_startup.py              # bootstrap, lifespan
├── test_module_isolation.py     # accounting <-> infra import 금지 검증
└── test_module_registration.py  # 모듈 등록/비활성화 검증
```

## DB 마이그레이션

```text
alembic/
├── env.py                       # Alembic 환경 설정
├── script.py.mako               # 마이그레이션 템플릿
└── versions/
    ├── 0001_initial_modular_baseline.py  # 통합 모듈 초기 스키마
    ├── 0002_add_project_contract_link_and_audit_module.py
    ├── 0003_asset_restructure.py         # project_assets, asset_code, asset_relations
    ├── 0004_project_customer.py          # project_customers, project_customer_contacts
    ├── 0005_customer_centric_restructure.py # partner_id FK 추가, project_id FK 제거
    ├── 0006_add_customer_code.py          # 업체 코드 컬럼
    ├── 0007_product_catalog.py            # product_catalog, hardware_specs, hardware_interfaces
    ├── 0008_asset_hardware_model_and_software.py # asset.hardware_model_id FK, asset_software 테이블
    ├── 0009_hardware_interface_capacity_type.py # hardware_interfaces capacity_type 컬럼
    ├── 0010_unified_business_model.py     # Contract/ContractPeriod → common, project_* → period_*, ContractSalesDetail
    ├── 0011_code_numbering.py             # 사업/계약단위 코드 체계 추가
    ├── 0012_customer_to_partner.py        # customer 명칭을 partner로 통일
    ├── 0013_asset_type_codes.py           # 자산유형 코드 테이블 추가
    ├── 0014_asset_aliases.py              # asset_aliases 테이블 추가
    ├── 0015_catalog_asset_type_and_placeholder.py # 카탈로그 자산유형/placeholder 컬럼 추가
    ├── 0016_asset_kind_and_catalog_metadata.py # 자산유형 kind + 카탈로그 메타 필드 추가
    ├── 0017_software_and_model_specs.py   # software_specs, model_specs 추가
    ├── 0018_generic_catalog_profiles.py   # generic_catalog_profiles 추가
    ├── 0019_seed_model_asset_type_codes.py # model 계열 자산유형 시드
    ├── 0020_asset_events.py               # 자산 변경이력 테이블 추가
    ├── 0021_asset_related_partners.py     # 자산 관련업체 이력 테이블 추가
    ├── 0022_asset_roles.py                # 논리 역할 / 역할 할당 추가
    ├── 0023_asset_project_number.py       # project_asset_number, customer_asset_number
    ├── 0024_centers_rooms_racks.py        # Center -> Room -> Rack 기준 데이터
    ├── 0025_asset_layout_refs.py          # asset.center_id / room_id / rack_id
    ├── 0026_asset_classification_schemes.py # 분류체계 / 분류노드 / asset.classification_node_id
    ├── 0027_asset_type_classification_mappings.py # 자산유형-분류 매핑 테이블
    ├── 0028_seed_asset_type_classification_mappings.py # 자산유형-분류 매핑 시드
    ├── 0029_seed_deeper_classification_nodes.py # 깊은 분류 노드 시드
    ├── 0030_fix_deeper_classification_nodes_seed.py # 깊은 분류 노드 시드 수정
    ├── 0031_seed_richer_classification_defaults.py # richer 글로벌 기본 분류체계 시드
    ├── 0032_fix_classification_scheme_descriptions.py # 깨진 분류체계 설명 복구
    ├── 0033_classification_level_aliases.py # 분류체계 레벨 alias(대구분/중구분/소구분 등)
    ├── 0034_catalog_classification_leaf_link.py # 카탈로그-최종분류 연결
    ├── 0035_merge_asset_type_into_classification_nodes.py # 자산유형 메타를 분류노드에 통합
    ├── 0036_add_catalog_attribute_model.py # 카탈로그 속성 모델 추가
    ├── 0037_seed_catalog_attributes_and_layouts.py # 카탈로그 속성/레이아웃 시드
    ├── 0038_migrate_catalog_classification_to_attributes.py # 분류→속성 마이그레이션
    ├── 0039_drop_legacy_classification_model.py # 레거시 분류 모델 제거
    ├── 0040_fix_attribute_inference_edge_cases.py # 속성 추론 엣지케이스 수정
    ├── 0041_normalize_catalog_layout_single_key_depths.py # 레이아웃 단일키 깊이 정규화
    ├── 0042_expand_product_family_seed_options.py # 제품군 시드 옵션 확장
    ├── 0043_make_product_catalog_category_nullable.py # category nullable 변경
    ├── 0044_drop_product_catalog_legacy_classification_columns.py # 레거시 분류 컬럼 제거
    ├── 0045_drop_legacy_classification_tables.py # 레거시 분류 테이블 제거
    ├── 0046_drop_asset_identity_rules.py   # 자산 식별 규칙 제거
    ├── 0047_drop_assets_asset_type.py      # assets.asset_type 컬럼 제거
    ├── 0048_add_product_catalog_normalized_names.py # 정규화된 제품명 추가
    ├── 0049_seed_common_catalog_products.py # 공통 카탈로그 제품 시드
    ├── 0050_add_vendor_aliases_and_vendor_series_options.py # 제조사 별칭, 시리즈 옵션
    ├── 0051_normalize_existing_vendor_names.py # 기존 제조사명 정규화
    ├── 0052_add_catalog_attribute_option_aliases.py # 속성 옵션 별칭 추가
    ├── 0053_add_domain_scope_to_product_family.py # 제품군 도메인 scope 추가
    ├── 0054_expand_catalog_seeds.py              # 카탈로그 시드 확장 (속성 옵션, 벤더 별칭, 제품)
    └── 0055_option_label_kr.py                   # 속성 옵션 label_kr 컬럼 추가 + 한/영 backfill
```

## 문서

```text
docs/
├── DECISIONS.md                # 아키텍처 결정 기록 (추가 전용)
├── KNOWN_ISSUES.md             # 알려진 제약, 임시 우회
├── PROJECT_CONTEXT.md          # 프로젝트 배경, 사용자, 문제 정의
├── PROJECT_STRUCTURE.md        # 이 파일 — 파일 단위 구조와 역할
└── guidelines/
    ├── backend.md              # 백엔드 코드 규칙, 예외 처리, 감사 로그
    ├── frontend.md             # 프론트엔드 명명, CSS, 모달, UI/UX
    ├── auth.md                 # 인증/권한/보안 규칙
    ├── excel.md                # Excel Import/Export 규칙
    ├── accounting.md           # 회계모듈 용어, 데이터 원칙
    └── infra.md                # 인프라모듈 용어, 데이터 원칙
```

## 스크립트

```text
scripts/
├── seed_catalog.py             # 제품 카탈로그 시드 데이터
└── migrate_contacts.py         # 연락처 마이그레이션
```

## 루트 파일

```text
├── alembic.ini              # Alembic 설정
├── requirements.txt         # Python 의존성
├── .env                     # 환경변수 (git 미추적)
├── .env.example             # 환경변수 템플릿 (전체 배포 참조)
├── .env.standalone.example  # Standalone 배포 환경변수 (인프라 오프라인)
├── Dockerfile               # 컨테이너 이미지 빌드
├── docker-compose.yml       # 컨테이너 실행 구성 (앱 + PostgreSQL)
├── .dockerignore            # Docker 빌드 제외 파일
├── CLAUDE.md                # 상위 개발 지침
└── README.md                # 프로젝트 소개
```
