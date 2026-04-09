# AssetInterface L3 UI 전환 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 백엔드 완료된 AssetInterface L3 모델을 UI에 반영 — 자산 상세 5탭 재구성, 포트맵 인라인 그리드, Excel export 재설계.

**Architecture:** 백엔드 추가(AssetLicense CRUD, AssetSoftware 라이선스 필드 제거, PortMap API 역참조 확장, Export 재설계) → 프론트엔드 전환(탭 재구성, 네트워크 탭 신설, 포트맵 그리드, IP 인벤토리 강화) 순서. 각 트랙은 독립적으로 병렬 실행 가능.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Alembic, AG-Grid Community v32, Vanilla JS, openpyxl

**Spec:** `docs/superpowers/specs/2026-04-07-interface-l3-ui-transition-design.md`

**XSS 참고:** 기존 코드베이스의 CellEditor 패턴이 innerHTML을 사용한다. 새 코드에서도 동일 패턴을 따르되, 사용자 입력은 escapeHtml()을 거쳐 삽입한다. 기존 utils.js의 escapeHtml 함수를 활용할 것.

---

## 파일 구조

### 신규 생성

| 파일 | 역할 |
|------|------|
| `app/modules/infra/models/asset_license.py` | AssetLicense ORM 모델 |
| `app/modules/infra/schemas/asset_license.py` | Pydantic Create/Update/Read 스키마 |
| `app/modules/infra/services/asset_license_service.py` | CRUD 서비스 |
| `app/modules/infra/routers/asset_licenses.py` | REST 엔드포인트 |
| `tests/infra/test_asset_license_service.py` | 라이선스 CRUD 테스트 |
| `alembic/versions/0067_add_asset_licenses_remove_sw_license.py` | 마이그레이션 |

### 주요 수정

| 파일 | 변경 요약 |
|------|----------|
| `app/modules/infra/models/asset_software.py` | license_type, license_count 컬럼 제거 |
| `app/modules/infra/schemas/asset_software.py` | 라이선스 필드 제거 |
| `app/modules/infra/schemas/port_map.py` | PortMapRead에 역참조 필드 추가 |
| `app/modules/infra/services/network_service.py` | 포트맵 역참조 헬퍼 추가 |
| `app/modules/infra/routers/port_maps.py` | 응답에 역참조 적용 |
| `app/modules/infra/routers/__init__.py` | asset_licenses 라우터 등록 |
| `app/modules/infra/services/infra_exporter.py` | 메뉴별 시트 구조 재설계 |
| `app/modules/infra/templates/infra_assets.html` | 5탭 버튼, 인터페이스/라이선스 모달, IP 모달 변경 |
| `app/modules/infra/templates/infra_port_maps.html` | 모달 src/dst 필드 교체 |
| `app/modules/infra/templates/infra_ip_inventory.html` | IP 모달 변경 |
| `app/static/js/infra_assets.js` | 탭 재구성, 인터페이스/IP/라이선스 UI |
| `app/static/js/infra_port_maps.js` | 인라인 그리드 전환, 셀 에디터 |
| `app/static/js/infra_ip_inventory.js` | 인터페이스 컬럼 추가, 모달 변경 |
| `app/templates/base.html` | 사이드바 그룹 매핑 변경 |

---

## Task 1: AssetLicense 백엔드 — 모델, 스키마, 서비스, 라우터

**Files:**
- Create: `app/modules/infra/models/asset_license.py`
- Create: `app/modules/infra/schemas/asset_license.py`
- Create: `app/modules/infra/services/asset_license_service.py`
- Create: `app/modules/infra/routers/asset_licenses.py`
- Modify: `app/modules/infra/routers/__init__.py`
- Create: `tests/infra/test_asset_license_service.py`

구현 패턴은 기존 `asset_softwares` 라우터/서비스와 동일하다 (`app/modules/infra/routers/asset_softwares.py`, `app/modules/infra/services/asset_software_service.py` 참조).

- [ ] **Step 1:** AssetLicense 모델 생성 — 필드: id(PK), asset_id(FK CASCADE), license_type(str50), license_key(str255 nullable), licensed_to(str200 nullable), start_date(Date nullable), end_date(Date nullable), note(Text nullable), TimestampMixin
- [ ] **Step 2:** Pydantic 스키마 생성 — AssetLicenseCreate(asset_id=0, license_type 필수, 나머지 optional), AssetLicenseUpdate(모두 optional), AssetLicenseRead(from_attributes)
- [ ] **Step 3:** 서비스 생성 — list_asset_licenses, create_asset_license, update_asset_license, delete_asset_license. `_require_inventory_edit` 권한 체크, `audit.log` 호출 포함
- [ ] **Step 4:** 라우터 생성 — GET/POST `/api/v1/assets/{asset_id}/licenses`, PATCH/DELETE `/api/v1/asset-licenses/{id}`
- [ ] **Step 5:** `routers/__init__.py`에 asset_licenses_router import 및 include_router 추가
- [ ] **Step 6:** 테스트 작성 — CRUD 전체 플로우 + NotFoundError 케이스
- [ ] **Step 7:** `pytest tests/infra/test_asset_license_service.py -v` 실행 확인
- [ ] **Step 8:** 커밋 `feat(infra): add AssetLicense model, service, router with CRUD`

---

## Task 2: AssetSoftware 라이선스 필드 제거 + 마이그레이션

**Files:**
- Modify: `app/modules/infra/models/asset_software.py:19-20`
- Modify: `app/modules/infra/schemas/asset_software.py`
- Create: `alembic/versions/0067_add_asset_licenses_remove_sw_license.py`

- [ ] **Step 1:** `asset_software.py` 모델에서 `license_type`, `license_count` 두 컬럼 삭제. `Integer` import도 불필요하면 제거
- [ ] **Step 2:** `asset_software.py` 스키마(Create/Update/Read)에서 `license_type`, `license_count` 필드 모두 삭제
- [ ] **Step 3:** Alembic 마이그레이션 작성 — `asset_licenses` 테이블 생성 + `asset_software`에서 `license_type`/`license_count` drop_column. down_revision="0066"
- [ ] **Step 4:** `alembic upgrade head` 실행 확인
- [ ] **Step 5:** `pytest tests/infra/ -k "software" -v` — 기존 SW 테스트에서 라이선스 필드 사용 시 수정
- [ ] **Step 6:** 커밋 `feat(infra): add asset_licenses table, remove SW license fields`

---

## Task 3: PortMap API 역참조 확장

포트맵 목록 API 응답에 자산명, 인터페이스명, 호스트명 등을 포함시킨다.

**Files:**
- Modify: `app/modules/infra/schemas/port_map.py:47-70`
- Modify: `app/modules/infra/services/network_service.py`
- Modify: `app/modules/infra/routers/port_maps.py`

- [ ] **Step 1:** `PortMapRead`에 역참조 필드 추가 — `src_asset_id`, `src_asset_name`, `src_hostname`, `src_interface_name`, `src_zone`, `dst_asset_id`, `dst_asset_name`, `dst_hostname`, `dst_interface_name`, `dst_zone` (모두 `| None = None`)
- [ ] **Step 2:** `network_service.py`에 `build_interface_map(db, port_maps)` 함수 추가 — 포트맵 목록에서 참조하는 인터페이스 ID를 수집, AssetInterface JOIN Asset으로 자산명/호스트명/인터페이스명/존을 조회하여 `{iface_id: info_dict}` 반환
- [ ] **Step 3:** `network_service.py`에 `enrich_port_map(pm, iface_map)` 함수 추가 — PortMap ORM의 컬럼값 + iface_map에서 src/dst 역참조 필드를 채운 dict 반환
- [ ] **Step 4:** `port_maps.py` 라우터의 list endpoint에서 `list_port_maps` 호출 후 `build_interface_map` + `enrich_port_map`으로 변환하여 반환
- [ ] **Step 5:** `pytest tests/infra/test_port_map_service.py -v` 확인
- [ ] **Step 6:** 커밋 `feat(infra): add denormalized asset/interface fields to PortMap API response`

---

## Task 4: 자산 상세 탭 재구성 (HTML + JS 구조)

4탭(overview/operations/connections/history) → 5탭(overview/operations/network/contacts/history) 전환.

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html:67-70`
- Modify: `app/static/js/infra_assets.js` (여러 위치)

- [ ] **Step 1:** HTML 탭 버튼 4개→5개 교체 — overview(개요), operations(운영), network(네트워크), contacts(업체·담당), history(이력)
- [ ] **Step 2:** `DETAIL_TAB_FIELDS.operations`에서 "네트워크 및 서비스" 섹션의 `service_ip`/`mgmt_ip` 제거, "담당자 메모" 섹션(`primary_contact_name`/`secondary_contact_name`/비고) 전체 제거. 호스트/서비스 섹션은 hostname, cluster, service_name, zone만 유지
- [ ] **Step 3:** `DETAIL_EDIT_FIELDS.operations`에서 `service_ip`, `mgmt_ip`, `primary_contact_name`, `secondary_contact_name`, `note` 제거
- [ ] **Step 4:** `renderDetailTab` 분기 수정 — `connections` 제거, `network` → `renderNetworkTab`, `contacts` → `renderContactsGroupTab` 추가. overview/operations는 `renderStructuredDetailTab` 후 서브섹션 추가
- [ ] **Step 5:** 새 그룹 렌더 함수 4개 작성:
  - `renderOverviewSubSections(container)` — 별칭 + 라이선스 (structured 탭 뒤에 호출)
  - `renderOperationsSubSections(container)` — 설치SW + 자산관계 (structured 탭 뒤에 호출)
  - `renderNetworkTab(container)` — 인터페이스 + IP할당
  - `renderContactsGroupTab(container)` — 담당자 + 관련업체
- [ ] **Step 6:** `syncAssetDetailTabs` 허용 탭 목록을 `["overview", "operations", "network", "contacts", "history"]`로 변경
- [ ] **Step 7:** 파일 전체에서 `renderDetailTab("connections")` 호출을 해당 섹션의 새 탭으로 교체:
  - SW 저장/삭제 → `"operations"`
  - IP 저장/삭제 → `"network"`
  - 담당자/관련업체 저장/삭제 → `"contacts"`
  - 관계 저장/삭제 → `"operations"`
  - 별칭 저장/삭제 → `"overview"`
- [ ] **Step 8:** 브라우저에서 5탭 전환 수동 검증
- [ ] **Step 9:** 커밋 `feat(ui): reorganize asset detail into 5 tabs`

---

## Task 5: 네트워크 탭 — 인터페이스 섹션 UI

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html` (인터페이스 모달 추가)
- Modify: `app/static/js/infra_assets.js` (renderInterfacesTab 등)

- [ ] **Step 1:** 인터페이스 추가/수정 모달 HTML 작성 — 필드: name, if_type(select: physical/lag/virtual), speed(select), media_type(select), slot, mac_address, admin_status(select: up/down), description
- [ ] **Step 2:** `renderInterfacesTab(container)` 구현 — API `GET /assets/{id}/interfaces` 호출, 계층 정렬(LAG→멤버→나머지), `_subTable`로 렌더. 카탈로그 자동생성 버튼(`hardware_model_id` 있을 때만)
- [ ] **Step 3:** `sortInterfacesHierarchically(ifaces)` 함수 — LAG 먼저, 그 parent_id 멤버 바로 뒤, 나머지 순서
- [ ] **Step 4:** `openInterfaceModal(iface)`, `saveInterface()`, `deleteInterface(iface)`, `generateInterfacesFromCatalog()` 구현
- [ ] **Step 5:** 모달 이벤트 바인딩 (btn-cancel-iface, btn-save-iface)
- [ ] **Step 6:** 수동 검증 — 네트워크 탭에서 인터페이스 CRUD 동작 확인
- [ ] **Step 7:** 커밋 `feat(ui): add interface section to asset detail network tab`

---

## Task 6: 네트워크 탭 — IP 할당 인터페이스 기반 전환

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html` (IP 모달 변경)
- Modify: `app/static/js/infra_assets.js:1592-1660` (renderIpTab, openIpModal, saveIp)

- [ ] **Step 1:** IP 모달 HTML 수정 — `interface_name` 텍스트→`interface_id` select, `network`/`netmask`/`gateway` 필드 제거, `service_name` 추가
- [ ] **Step 2:** `openIpModal` 수정 — 인터페이스 드롭다운을 `GET /assets/{id}/interfaces`로 동적 로드
- [ ] **Step 3:** `saveIp` payload 수정 — `interface_id`(Number), `ip_address`, `ip_type`, `is_primary`, `hostname`, `service_name`, `zone`, `vlan_id`, `note`. `network`/`netmask`/`gateway`/`interface_name` 제거
- [ ] **Step 4:** 커밋 `feat(ui): convert IP allocation to interface-based selection`

---

## Task 7: 라이선스 탭 UI (개요 탭 하위)

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html` (라이선스 모달)
- Modify: `app/static/js/infra_assets.js` (renderLicensesTab 등)

- [ ] **Step 1:** 라이선스 모달 HTML — 필드: license_type(select: perpetual/subscription/eval/oem), license_key, licensed_to, start_date(date), end_date(date), note
- [ ] **Step 2:** `renderLicensesTab(container)` — API `GET /assets/{id}/licenses`, `_subTable` 렌더
- [ ] **Step 3:** `openLicenseModal(lic)`, `saveLicense()`, `deleteLicense(lic)` 구현
- [ ] **Step 4:** 모달 이벤트 바인딩 + SW 탭에서 `license_type`/`license_count` 컬럼 제거, SW 모달/payload에서도 제거
- [ ] **Step 5:** 커밋 `feat(ui): add license section to overview tab, remove SW license fields`

---

## Task 8: 포트맵 페이지 인라인 그리드 전환

**Files:**
- Rewrite: `app/static/js/infra_port_maps.js`
- Modify: `app/modules/infra/templates/infra_port_maps.html`

- [ ] **Step 1:** `AssetCellEditor` 클래스 작성 — `PartnerCellEditor` (contract_detail.js:2418) 패턴 기반. 텍스트 입력→자산 목록 필터링→선택 시 asset_id 저장. dropdown 렌더 시 `escapeHtml` 사용
- [ ] **Step 2:** `InterfaceCellEditor` 클래스 작성 — 같은 행의 src/dst asset_id에 연동, `GET /assets/{id}/interfaces`로 목록 로드→필터링→선택 시 interface_id 저장
- [ ] **Step 3:** `columnDefs` 재정의 — seq, src_asset_name(AssetCellEditor), src_interface_name(InterfaceCellEditor), src_hostname(readonly), dst 동일, connection_type, cable_no, cable_type, cable_speed, purpose, status, 액션
- [ ] **Step 4:** `loadPortMaps` — 자산 캐시 로드(`loadPmAssets`), API 호출, 그리드 데이터 설정
- [ ] **Step 5:** `handlePortMapCellChanged` — 자산/인터페이스 셀 변경 시 ID 해석→PATCH API 호출
- [ ] **Step 6:** `addCopyPasteHandler` 적용 — editableFields 지정, onPaste 콜백에서 행별 API 저장
- [ ] **Step 7:** 모달 HTML 재작성 — src/dst 텍스트 24필드 제거, 자산 콤보+인터페이스 셀렉트로 교체. 공통/케이블 필드 유지
- [ ] **Step 8:** 모달 JS(resetForm, openEditModal, savePortMap) 인터페이스 기반으로 전환
- [ ] **Step 9:** 수동 검증 — 그리드 인라인 편집, 콤보박스, 복사/붙여넣기, 모달 CRUD
- [ ] **Step 10:** 커밋 `feat(ui): convert portmap to inline grid with interface FK combo editors`

---

## Task 9: IP 인벤토리 페이지 인터페이스 강화

**Files:**
- Modify: `app/static/js/infra_ip_inventory.js`
- Modify: `app/modules/infra/templates/infra_ip_inventory.html`
- Modify: `app/modules/infra/routers/asset_ips.py` (IP 인벤토리 역참조)

- [ ] **Step 1:** IP 인벤토리 API 응답에 `asset_name`, `interface_name`, `if_type` 역참조 필드 추가 — 라우터에서 interface→asset 조인 결과를 enrich
- [ ] **Step 2:** `ipColDefs`에 `asset_name`, `if_type` 컬럼 추가
- [ ] **Step 3:** IP 모달 변경 — `ip-asset-id` → 자산 선택(텍스트 검색) + `ip-interface-id` select 2단계. `network`/`netmask`/`gateway`/`dns-primary`/`dns-secondary` 제거
- [ ] **Step 4:** 커밋 `feat(ui): enhance IP inventory with interface/asset columns`

---

## Task 10: 사이드바 메뉴 변경

**Files:**
- Modify: `app/templates/base.html:165-172`

- [ ] **Step 1:** `_navGroups` 객체에서 자산 페이지 내 IP인벤토리/포트맵 하위 탭 관련 매핑 확인 및 정리. 네트워크 메뉴가 `/ip-inventory`로 독립 유지되므로 기존 매핑 대부분 유지
- [ ] **Step 2:** 커밋 `refactor(ui): update sidebar nav group mappings`

---

## Task 11: Excel Export 재설계

**Files:**
- Modify: `app/modules/infra/services/infra_exporter.py`

- [ ] **Step 1:** `_INVENTORY_HEADERS`에서 service_ip, mgmt_ip 항목 제거 (현재 Asset 모델에서 이미 삭제됨)
- [ ] **Step 2:** `_PORTMAP_HEADERS` 재정의 — src/dst 텍스트 필드 제거, 자산명+IF명+호스트명+Zone으로 교체 (역참조 필드 사용)
- [ ] **Step 3:** Portmap 시트 작성 로직 수정 — `build_interface_map` 활용하여 역참조 필드 채우기
- [ ] **Step 4:** `_INTERFACE_HEADERS` 정의 및 Interfaces 시트 추가 — 자산별 인터페이스 목록 출력
- [ ] **Step 5:** `pytest tests/infra/ -k "export" -v` 확인
- [ ] **Step 6:** 커밋 `feat(infra): redesign Excel export with interface sheet and portmap update`

---

## Task 12: 문서 갱신

**Files:**
- Modify: `docs/guidelines/infra.md`
- Check: `docs/KNOWN_ISSUES.md`

- [ ] **Step 1:** `infra.md`에 AssetLicense 용어 추가, AssetSoftware 라이선스 필드 제거 기록, 자산 상세 5탭 구조 언급, 포트맵 인터페이스 FK 기반 명시
- [ ] **Step 2:** `KNOWN_ISSUES.md`에서 이번 변경으로 해소된 항목 삭제
- [ ] **Step 3:** `project_interface_l3_status.md` 메모리를 UI 전환 완료로 업데이트
- [ ] **Step 4:** 커밋 `docs: update infra guidelines for L3 UI transition`
