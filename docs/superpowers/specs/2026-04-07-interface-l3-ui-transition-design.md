# AssetInterface L3 UI 전환 설계

> 백엔드 완료된 AssetInterface L3 모델을 UI에 반영하고, 자산 상세 탭 재구성·포트맵 그리드 전환·Excel export 재설계를 포함한다.

## 1. 목표

- 자산 상세 화면의 탭 구조를 도메인별로 재배치
- 인터페이스 → IP 계층 구조를 네트워크 탭으로 신설
- 포트맵을 인라인 그리드 편집 방식으로 전환 (인터페이스 FK 기반)
- IP 인벤토리에 인터페이스 정보 강화
- Excel export를 메뉴별 시트 구조로 재설계
- 제거된 백엔드 필드의 JS 참조 정리

### 스코프 외

- Excel import 재설계 — 기능 구현 안정화 후 별도 설계
- 협력업체 메뉴 통합 — 거래처 관리와의 모듈 조건부 렌더링 문제로 별도 작업
- 자산 상단 요약 카드 — 탭 재구성 후 필요성 재평가
- vlan, subinterface, loopback, tunnel if_type UI

## 2. 자산 상세 탭 재구성

### 2.1 AS-IS → TO-BE

**AS-IS (4탭):**
| 탭 | 섹션 |
|---|---|
| 개요 | 식별/기준, 사양/식별자, HW요약 |
| 운영 | 설치위치, 운영속성, 네트워크/서비스(service_ip, mgmt_ip), 담당자메모(주/부담당 텍스트) |
| 연결 | 소프트웨어, IP할당, 담당자, 관련업체, 자산관계, 별칭 |
| 이력 | 변경이력 |

**TO-BE (5탭):**
| 탭 | 섹션 | 변경 내역 |
|---|---|---|
| **개요** | 식별/기준, 사양/식별자, HW요약, **별칭**, **자산 라이선스** | 별칭: 연결→개요 이동. 자산 라이선스: 신규 |
| **운영** | 설치위치, 운영속성, 호스트/서비스, **설치SW**, **자산관계** | SW: 연결→운영 이동(라이선스 필드 제거). 자산관계: 연결→운영 이동. service_ip/mgmt_ip/담당자메모 제거 |
| **네트워크** | **인터페이스**, **IP할당** | 신규 탭. 인터페이스→IP 계층 구조 |
| **업체·담당** | 담당자, 관련업체 | 연결→업체·담당 리네임. 담당자+업체만 남김 |
| **이력** | 변경이력 | 변경 없음 |

### 2.2 제거 대상

| 필드/섹션 | 위치 | 사유 |
|-----------|------|------|
| `service_ip` | operations 네트워크/서비스 | 백엔드 제거됨. 인터페이스 IP로 대체 |
| `mgmt_ip` | operations 네트워크/서비스 | 백엔드 제거됨. 인터페이스 IP로 대체 |
| 주 담당자 (텍스트) | operations 담당자메모 | 업체·담당 탭의 담당자 매핑으로 대체 |
| 부 담당자 (텍스트) | operations 담당자메모 | 업체·담당 탭의 담당자 매핑으로 대체 |

### 2.3 설치 SW 필드 변경

AssetSoftware에서 라이선스 관련 필드를 제거한다:

- **제거:** `license_type`, `license_count`
- **유지:** `software_name`, `version`, `relation_type`, `note`

라이선스가 필요한 SW는 별도 자산으로 등록하여 해당 자산에서 라이선스 정보를 관리한다.

## 3. AssetLicense 모델 (신설)

### 3.1 테이블 구조

```
asset_licenses
├── id (PK)
├── asset_id (FK → assets, CASCADE, indexed)
│
├── license_type (str 50) ─── "perpetual", "subscription", "eval", "oem"
├── license_key (str 255, nullable) ─── 라이선스 키/시리얼
├── licensed_to (str 200, nullable) ─── 귀속 (고객사명 등)
├── start_date (date, nullable) ─── 시작일
├── end_date (date, nullable) ─── 만료일
├── note (text, nullable)
│
├── created_at, updated_at (TimestampMixin)
```

### 3.2 API

- `GET /api/v1/assets/{asset_id}/licenses` — 자산별 라이선스 목록
- `POST /api/v1/assets/{asset_id}/licenses` — 라이선스 추가
- `PATCH /api/v1/asset-licenses/{id}` — 수정
- `DELETE /api/v1/asset-licenses/{id}` — 삭제

### 3.3 UI

개요 탭 하단에 별칭과 같은 패턴으로 _subTable 렌더링:

| 유형 | 라이선스 키 | 귀속 | 시작일 | 만료일 | 메모 | 액션 |
|------|-----------|------|--------|--------|------|------|

## 4. 네트워크 탭 — 인터페이스 & IP

### 4.1 인터페이스 섹션

기존 `_subTable` 패턴으로 인터페이스 목록 표시. 계층 구조로 LAG → 물리IF 관계를 시각화한다.

**표시 컬럼:**

| 이름 | 유형 | 속도 | 미디어 | 슬롯 | Admin | Oper | MAC | 설명 | 액션 |
|------|------|------|--------|------|-------|------|-----|------|------|

**계층 표시:**
- LAG 인터페이스는 일반 행으로 표시
- LAG에 속한 물리 IF는 들여쓰기(padding-left)로 부모-자식 관계 시각화
- if_type별 아이콘 또는 뱃지로 구분 (physical, lag, virtual)

**CRUD:**
- `+ 추가` 버튼 → 인터페이스 추가 모달 (name, if_type, speed, media_type, slot, description)
- 수정/삭제 액션 버튼
- `카탈로그에서 생성` 버튼 → `POST /assets/{id}/interfaces/generate` 호출 (model_id가 있을 때만 활성)

### 4.2 IP 할당 섹션

인터페이스 기반 IP 할당. 인터페이스를 선택한 후 IP를 할당한다.

**변경점:**
- IP 추가 모달에서 `interface_name` 텍스트 입력 → `interface_id` 드롭다운 선택으로 변경
- 드롭다운은 현재 자산의 인터페이스 목록을 API에서 로드
- IP 목록 테이블에 인터페이스명 컬럼 표시 (interface.name 역참조)
- `network`, `netmask`, `gateway` 필드 제거 (백엔드에서 삭제됨)

**IP 모달 필드 (TO-BE):**

| 필드 | 타입 | 설명 |
|------|------|------|
| interface_id | select (인터페이스 목록) | 할당 대상 인터페이스 |
| ip_address | text | IP 주소 |
| ip_type | select | service, mgmt, vip, secondary |
| is_primary | checkbox | 대표 IP 여부 |
| hostname | text | 호스트명 |
| service_name | text | 서비스명 |
| zone | text | 존 |
| vlan_id | text | VLAN |
| note | text | 비고 |

## 5. 포트맵 페이지 전환

### 5.1 모달 → 인라인 그리드

현재 모달 기반 CRUD를 인라인 편집 가능한 AG Grid로 전환한다.

**그리드 컬럼:**

| 필드 | 헤더 | editable | 에디터 |
|------|------|----------|--------|
| seq | 순번 | - | - |
| src_asset_name | 출발 자산 | O | AssetCellEditor (콤보박스) |
| src_interface_name | 출발 IF | O | InterfaceCellEditor (콤보박스, 자산 연동) |
| dst_asset_name | 도착 자산 | O | AssetCellEditor (콤보박스) |
| dst_interface_name | 도착 IF | O | InterfaceCellEditor (콤보박스, 자산 연동) |
| connection_type | 연결유형 | O | agSelectCellEditor |
| cable_no | 케이블번호 | O | text |
| cable_type | 케이블종류 | O | agSelectCellEditor |
| cable_speed | 속도 | O | agSelectCellEditor |
| purpose | 용도 | O | text |
| status | 상태 | O | agSelectCellEditor |
| 액션 | - | - | 수정(모달)/삭제 버튼 |

**표시 전용 (인터페이스 역참조):**
- 출발 호스트명, 출발 존, 도착 호스트명, 도착 존 — 인터페이스 → 자산/IP에서 자동 표시

### 5.2 셀 에디터

**AssetCellEditor:**
- `PartnerCellEditor` 패턴 기반
- 텍스트 입력 → 현재 고객사 자산 목록에서 필터링
- 유사도 경고 표시
- 선택 시 `asset_id` 저장

**InterfaceCellEditor:**
- 같은 행의 자산 선택에 연동
- 자산이 선택되면 해당 자산의 인터페이스 목록을 `/api/v1/assets/{id}/interfaces`에서 로드
- 텍스트 입력으로 필터링

### 5.3 복사/붙여넣기

`addCopyPasteHandler` (이미 구현됨) 적용:
- 자산명/인터페이스명을 텍스트로 붙여넣기 → 매칭 로직으로 ID 해석
- 매칭 실패 시 해당 셀 하이라이트 + 수동 선택 유도

### 5.4 모달 유지

인라인 편집 외에 기존 모달도 "수정" 버튼으로 유지한다. 그리드에는 자주 쓰는 핵심 필드만 노출하고, 모달에서는 전체 필드를 편집할 수 있다:

**모달 전용 필드 (그리드에 없음):**

- `cable_request` (포설 신청)
- `summary` (요약)
- `duplex`
- `cable_category`
- `protocol`, `port` (논리 연결용)
- `note`

모달 내 src/dst 선택도 콤보박스 기반으로 전환한다.

### 5.5 제거 대상 (JS)

`infra_port_maps.js`의 TEXT_FIELDS에서 제거:

```
src_mid, src_rack_no, src_rack_unit, src_vendor, src_model,
src_hostname, src_cluster, src_slot, src_port_name,
src_service_name, src_zone, src_vlan, src_ip,
dst_mid, dst_rack_no, dst_rack_unit, dst_vendor, dst_model,
dst_hostname, dst_cluster, dst_slot, dst_port_name,
dst_service_name, dst_zone, dst_vlan, dst_ip
```

→ `src_interface_id`, `dst_interface_id`로 대체.

## 6. IP 인벤토리 페이지

### 6.1 변경 범위

현재 구조(좌: 서브넷 목록, 우: IP 그리드)를 유지하면서 인터페이스 정보를 강화한다.

**그리드 컬럼 변경:**

| AS-IS | TO-BE |
|-------|-------|
| interface_name (텍스트) | interface_name (인터페이스 역참조) |
| - | asset_name (인터페이스 → 자산 역참조, 신규) |
| - | if_type (인터페이스 유형, 신규) |

**IP 추가/수정 모달:**
- `interface_name` 텍스트 → 자산 선택 + 인터페이스 선택 2단계 드롭다운
- `network`, `netmask`, `gateway` 필드 제거

## 7. 사이드바 메뉴 변경

### 7.1 자산 메뉴

자산 페이지에서 IP인벤토리/포트맵 하위 탭을 제거한다. 자산 상세의 네트워크 탭이 자산 단위 IP/포트맵 역할을 대체.

### 7.2 네트워크 메뉴

독립 메뉴로 유지. 서브넷/IP 인벤토리 기준 전체 뷰 + 포트맵 전체 뷰를 탭으로 제공.
- 탭 1: IP 인벤토리 (서브넷 기준)
- 탭 2: 포트맵 (전체 연결 뷰)

### 7.3 나머지

프로젝트, 배치, 협력업체, 이력 — 변경 없음.

## 8. Excel Export 재설계

### 8.1 메뉴별 시트 구조

각 메뉴에서 export 시 해당 메뉴의 데이터를 시트별로 내보낸다.

**자산 메뉴 export:**
| 시트 | 내용 | 참고 |
|------|------|------|
| Inventory | 자산 목록 (service_ip/mgmt_ip 제거) | 템플릿 01 |
| Interfaces | 자산별 인터페이스 목록 (신규) | 템플릿 04 참고 |

**네트워크 메뉴 export:**
| 시트 | 내용 | 참고 |
|------|------|------|
| Subnets | IP대역 정의 | 템플릿 05 |
| IP Allocation | IP 할당 현황 (인터페이스 정보 포함) | 템플릿 06 |
| Portmap | 포트맵 (자산명+인터페이스명 기반) | 템플릿 03 |

**배치 메뉴 export:**
| 시트 | 내용 | 참고 |
|------|------|------|
| Layout | 랙 배치도 | 템플릿 02 |

### 8.2 Inventory 시트 헤더 변경

**제거:** Service IP, MGMT IP
**나머지:** 현행 유지

### 8.3 Portmap 시트 헤더 변경

src/dst 텍스트 필드 → 자산명+인터페이스명으로 단순화:

```
Seq | Cable No | 유형 | 용도
| 출발 자산 | 출발 IF | 출발 호스트 | 출발 Zone
| 도착 자산 | 도착 IF | 도착 호스트 | 도착 Zone
| Protocol | Port | 상태
| 케이블유형 | 속도 | 비고
```

호스트명, Zone 등은 인터페이스 → 자산/IP에서 역참조하여 채운다.

### 8.4 Interfaces 시트 헤더 (신규)

```
자산명 | IF이름 | 유형 | 속도 | 미디어 | 슬롯 | Admin | Oper | MAC | 설명
```

## 9. JS 정리 대상

### 9.1 infra_assets.js

- `DETAIL_TAB_FIELDS.operations` — "네트워크 및 서비스" 섹션에서 `service_ip`, `mgmt_ip` 제거
- `DETAIL_TAB_FIELDS.operations` — "담당자 메모" 섹션 제거 (`primary_contact_name`, `secondary_contact_name`)
- `DETAIL_EDIT_FIELDS.operations` — `service_ip`, `mgmt_ip`, `primary_contact_name`, `secondary_contact_name` 제거
- `renderConnectionsTab` → 탭 재구성에 따라 리팩토링
- `renderSoftwareTab` → 라이선스 컬럼 제거 (`license_type`, `license_count`)
- `openSoftwareModal` → 라이선스 필드 제거
- `saveSoftware` → payload에서 라이선스 필드 제거
- `openIpModal` → `interface_name` 텍스트 → `interface_id` 선택, `network`/`netmask`/`gateway` 제거
- `saveIp` → payload 필드 업데이트
- 탭 ID 매핑: `connections` → 새 탭 ID들로 분기 로직 변경

### 9.2 infra_port_maps.js

- `TEXT_FIELDS` — src/dst 텍스트 24개 필드 제거
- `columnDefs` — 인터페이스 FK 기반 컬럼으로 교체
- `openEditModal` / `resetForm` / `savePortMap` — 인터페이스 기반으로 전환
- 모달 HTML 필드 정리 (template에서도)
- `AssetCellEditor`, `InterfaceCellEditor` 추가
- `addCopyPasteHandler` 적용

### 9.3 infra_ip_inventory.js

- `ipColDefs` — `asset_name`, `if_type` 컬럼 추가
- IP 추가/수정 모달 — 자산+인터페이스 2단계 선택으로 변경

### 9.4 HTML 템플릿

- `infra_assets.html` — 탭 버튼 5개로 변경, 라이선스 모달 추가, SW 모달에서 라이선스 필드 제거, IP 모달에서 network/netmask/gateway 제거 + interface_id 선택 추가
- `infra_port_maps.html` — 모달 내 src/dst 텍스트 필드 제거, 인터페이스 선택 UI로 교체

## 10. 백엔드 추가 작업

### 10.1 AssetLicense

- 모델: `app/modules/infra/models/asset_license.py`
- 서비스: `app/modules/infra/services/asset_license_service.py`
- 라우터: `app/modules/infra/routers/asset_licenses.py`
- Alembic 마이그레이션

### 10.2 AssetSoftware 변경

- 모델에서 `license_type`, `license_count` 컬럼 제거
- Alembic 마이그레이션

### 10.3 Export 서비스

- `infra_exporter.py` — Inventory 시트 service_ip/mgmt_ip 제거, Portmap 시트 인터페이스 기반 전환, Interfaces 시트 추가
- 메뉴별 export 엔드포인트 분리 또는 파라미터화

### 10.4 API 보강

포트맵 그리드에서 자산/인터페이스 검색용:
- `GET /api/v1/assets?partner_id={id}&q={keyword}` — 자산 검색 (기존 활용 가능 여부 확인)
- 포트맵 목록 API 응답에 자산명/인터페이스명/호스트명 등 역참조 필드 포함

## 11. 영향 범위 요약

| 파일 | 변경 유형 |
|------|----------|
| `infra_assets.js` | 탭 재구성, 필드 제거, 인터페이스/IP/라이선스 탭 추가 |
| `infra_assets.html` | 탭 버튼, 모달 필드 변경, 라이선스 모달 추가 |
| `infra_port_maps.js` | 인라인 그리드 전환, 셀 에디터, 복사/붙여넣기 |
| `infra_port_maps.html` | 모달 필드 정리 |
| `infra_ip_inventory.js` | 컬럼 추가, 모달 변경 |
| `infra_ip_inventory.html` | 모달 필드 변경 |
| `infra_exporter.py` | 시트 구조 재설계 |
| `asset_license.py` (신규) | AssetLicense 모델 |
| `asset_license_service.py` (신규) | CRUD 서비스 |
| `asset_licenses.py` (신규) | 라우터 |
| `asset_software.py` (모델) | 라이선스 필드 제거 |
| `base.html` | 자산 하위 탭 제거 (사이드바 그룹 매핑 변경) |
| Alembic migration | asset_licenses 생성, asset_software 컬럼 제거 |
