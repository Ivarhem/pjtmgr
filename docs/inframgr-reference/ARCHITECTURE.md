# 시스템 아키텍처

## 1. 목표와 범위

본 시스템은 PM Tool이 아니라 프로젝트 기술 인벤토리 시스템이다.

MVP 목표:

- 프로젝트 기술 인벤토리 구조 검증
- Asset 중심 데이터 모델 검증
- 프로젝트 단계 및 산출물 관리 기능 검증
- 담당자 관리 기능 검증

MVP 제외 범위:

- 태스크 관리
- 간트 차트
- 협업/메시징
- 알림
- 일정 관리
- 외부 시스템 연동

---

## 2. 시스템 구조

```text
Browser
  ├─ Jinja2 HTML pages
  ├─ HTMX partial updates
  └─ AG Grid inventory tables
       ↓
FastAPI
  ├─ page routers
  ├─ api routers (/api/v1/...)
  ├─ auth/session
  ├─ services
  ├─ SQLAlchemy ORM
  └─ startup/bootstrap
       ↓
PostgreSQL
```

### 레이어 원칙

- Interface: 페이지 템플릿, API 라우터
- Application: 서비스 레이어, 유효성 검증, 워크플로우
- Data Access: SQLAlchemy ORM
- Domain: 프로젝트, 자산, 정책, 연락망 모델

---

## 3. 핵심 엔티티

### 프로젝트

- `Project`
- `ProjectPhase`
- `ProjectDeliverable`

### 기술 인벤토리

- `Asset`
- `IpSubnet`
- `AssetIP`
- `PortMap`

### 정책

- `PolicyDefinition`
- `PolicyAssignment`

### 연락망

- `Partner`
- `Contact`
- `AssetContact`

---

## 4. 데이터베이스 스키마 제안

### projects

- `id`
- `project_code` unique
- `project_name`
- `client_name`
- `start_date`
- `end_date`
- `description`
- `status`
- `created_at`
- `updated_at`

### project_phases

- `id`
- `project_id` FK
- `phase_type`
- `task_scope`
- `deliverables_note`
- `cautions`
- `submission_required`
- `submission_status`
- `status`
- unique(`project_id`, `phase_type`)

### project_deliverables

- `id`
- `project_phase_id` FK
- `name`
- `description`
- `is_submitted`
- `submitted_at`
- `note`

### assets

- `id`
- `project_id` FK
- `asset_name`
- `asset_type`
- `vendor`
- `model`
- `role`
- `environment`
- `location`
- `status`
- `note`
- unique(`project_id`, `asset_name`)

### ip_subnets

- `id`
- `project_id` FK
- `name`
- `subnet` (CIDR 표기)
- `role` (service, management, backup, dmz, other)
- `vlan_id`
- `gateway`
- `region`
- `floor`
- `counterpart` (상대국/기관/지점명)
- `description`
- `note`

### asset_ips

- `id`
- `asset_id` FK
- `ip_subnet_id` FK nullable (ip_subnets 참조)
- `ip_address`
- `ip_type`
- `interface_name`
- `is_primary`
- `note`
- unique(`asset_id`, `ip_address`)

권장:

- 서비스 레이어에서 프로젝트 범위 IP 중복 검증

### port_maps

- `id`
- `project_id` FK
- `src_asset_id` FK nullable
- `src_ip`
- `dst_asset_id` FK nullable
- `dst_ip`
- `protocol`
- `port`
- `purpose`
- `status`
- `note`

### policy_definitions

- `id`
- `policy_code` unique
- `policy_name`
- `category`
- `description`
- `is_active`
- `effective_from`
- `effective_to`

### policy_assignments

- `id`
- `project_id` FK
- `asset_id` FK nullable
- `policy_definition_id` FK
- `status`
- `exception_reason`
- `checked_by`
- `checked_date`
- `evidence_note`
- unique(`project_id`, `asset_id`, `policy_definition_id`)

### partners

- `id`
- `project_id` FK nullable
- `partner_name`
- `partner_type`
- `contact_phone`
- `note`

### contacts

- `id`
- `partner_id` FK
- `name`
- `role`
- `email`
- `phone`
- `emergency_phone`
- `note`

### asset_contacts

- `id`
- `asset_id` FK
- `contact_id` FK
- `role`
- unique(`asset_id`, `contact_id`, `role`)

---

## 5. 주요 API 설계

### Projects

- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}`
- `PATCH /api/v1/projects/{project_id}`
- `DELETE /api/v1/projects/{project_id}`

현재 구현:

- 프로젝트 CRUD 기본 경로 제공
- 프로젝트 overview, phase 연결은 후속 단계

### Project Phases / Deliverables

- `GET /api/v1/projects/{project_id}/phases`
- `POST /api/v1/projects/{project_id}/phases`
- `GET /api/v1/project-phases/{phase_id}`
- `PATCH /api/v1/project-phases/{phase_id}`
- `DELETE /api/v1/project-phases/{phase_id}`
- `GET /api/v1/project-phases/{phase_id}/deliverables`
- `POST /api/v1/project-phases/{phase_id}/deliverables`
- `GET /api/v1/project-deliverables/{deliverable_id}`
- `PATCH /api/v1/project-deliverables/{deliverable_id}`
- `DELETE /api/v1/project-deliverables/{deliverable_id}`

### Assets

- `GET /api/v1/assets`
- `POST /api/v1/assets`
- `GET /api/v1/assets/{asset_id}`
- `PATCH /api/v1/assets/{asset_id}`
- `DELETE /api/v1/assets/{asset_id}`

현재 구현:

- `project_id` query parameter로 프로젝트별 자산 필터 제공
- 프로젝트 하위 중첩 asset 경로는 후속 단계

### IP Subnets

- `GET /api/v1/projects/{project_id}/ip-subnets`
- `POST /api/v1/projects/{project_id}/ip-subnets`
- `GET /api/v1/ip-subnets/{subnet_id}`
- `PATCH /api/v1/ip-subnets/{subnet_id}`
- `DELETE /api/v1/ip-subnets/{subnet_id}`

### IP Inventory

- `GET /api/v1/assets/{asset_id}/ips`
- `POST /api/v1/assets/{asset_id}/ips`
- `PATCH /api/v1/asset-ips/{ip_id}`
- `DELETE /api/v1/asset-ips/{ip_id}`
- `GET /api/v1/projects/{project_id}/ip-inventory`

### Port Maps

- `GET /api/v1/projects/{project_id}/port-maps`
- `POST /api/v1/projects/{project_id}/port-maps`
- `PATCH /api/v1/port-maps/{port_map_id}`
- `DELETE /api/v1/port-maps/{port_map_id}`

### Policies

- `GET /api/v1/policies`
- `POST /api/v1/policies`
- `PATCH /api/v1/policies/{policy_id}`
- `GET /api/v1/projects/{project_id}/policy-assignments`
- `POST /api/v1/projects/{project_id}/policy-assignments`
- `PATCH /api/v1/policy-assignments/{assignment_id}`

### Partners / Contacts

- `GET /api/v1/projects/{project_id}/partners`
- `POST /api/v1/projects/{project_id}/partners`
- `GET /api/v1/partners/{partner_id}/contacts`
- `POST /api/v1/partners/{partner_id}/contacts`
- `POST /api/v1/assets/{asset_id}/contacts`
- `DELETE /api/v1/asset-contacts/{asset_contact_id}`

---

## 6. 화면 구조 제안

### 1) 프로젝트 목록

- 프로젝트 검색, 상태 필터
- 프로젝트 생성
- 프로젝트 상세 진입

### 2) 프로젝트 상세

- 기본 정보
- 단계 및 산출물 현황
- 자산 요약
- 정책 요약
- 연락망 요약

### 3) Asset 인벤토리

- AG Grid 중심
- 자산 유형, 환경, 상태 필터
- 자산 상세 진입

### 4) IP 인벤토리

- IP 대역(IpSubnet) 목록: 역할, 지역, 상대국별 조회
- 대역별 할당 IP 현황
- Asset 기준 필터
- 중복/충돌 표시

### 5) PortMap 인벤토리

- 출발지/목적지/포트/프로토콜 필터
- 상태별 조회

### 6) 정책 관리

- 정책 정의 목록
- 프로젝트/자산 적용 현황
- 예외 사유 및 점검자 기록

### 7) 업체 / 담당자

- 업체 목록
- 연락처 목록
- 자산 연결 담당자 표시

---

## 7. MVP 구현 단계

### 1단계: 기반 정리

- 프로젝트 전용 문서 및 지침 정비
- FastAPI 앱 뼈대, 세션 인증, PostgreSQL, Alembic 준비
- 공통 레이아웃 및 페이지 구조 준비

### 2단계: 프로젝트 + 단계

- 프로젝트 CRUD
- 프로젝트 단계 CRUD
- 산출물 제출 상태 관리

### 3단계: Asset 인벤토리

- Asset CRUD
- Asset 목록/상세 화면

### 4단계: 네트워크 인벤토리

- IpSubnet CRUD (대역 인벤토리)
- AssetIP CRUD
- PortMap CRUD
- 프로젝트 내 IP 중복 검증

### 5단계: 정책 관리

- 정책 정의 CRUD
- 정책 적용 상태 CRUD

### 6단계: 연락망

- Partner / Contact CRUD
- AssetContact 연결

### 7단계: 마감

- 테스트 보강
- Seed 데이터
- 샘플 프로젝트 데이터
- 문서 보정

---

## 8. 향후 확장 가능성

- Excel Import/Export
- 감사 로그 및 변경 이력
- 정책 점검 리포트
- 역할 세분화 (`admin`, `editor`, `viewer`)
- 프로젝트 템플릿 복제
- 외부 CMDB/NMS/API 연동

원칙:

- 미래 확장은 고려하되, MVP에서 실제로 쓰지 않는 기능은 구현하지 않는다.
