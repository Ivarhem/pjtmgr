# 인프라모듈 전체 구현 로드맵

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 인프라모듈(프로젝트관리)의 자산/IP인벤토리/포트맵/배치도/Alias/업체 기능을 실제 사용 가능한 수준으로 완성한다.

**Architecture:** 기존 코드 뼈대(모델/스키마/서비스/라우터/템플릿)는 유지. 각 Phase를 독립 세션으로 진행하며, Phase 완료 시마다 브라우저 E2E 검증 수행.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, Jinja2, Vanilla JS, AG Grid

**관련 스펙:** `docs/superpowers/specs/2026-03-24-layout-and-alias-design.md`
**관련 계획:** `docs/superpowers/plans/2026-03-24-layout-and-alias.md` (배치도/Alias DB+서비스 상세)

---

## 현재 상태 (2026-03-24 최종)

| 페이지 | 상태 | 비고 |
| --- | --- | --- |
| 프로젝트 목록 `/periods` | **동작** | AG Grid + CRUD 정상 |
| 자산 목록 `/assets` | **동작** | 간소화 모달(4필드) + 카탈로그 연동 + 상세 패널 10탭 + 인라인 편집 + alias 태그 + 검색(alias/code 통합) |
| IP 인벤토리 `/ip-inventory` | 부분 동작 | 서브넷 목록 미표시, IP 할당 CRUD 미검증 → **Phase 3** |
| 포트맵 `/port-maps` | 부분 동작 | Import UI 있음, 배선 등록 미확인 → **Phase 4** |
| 업체 `/contacts` | 부분 동작 | 프로젝트 미선택 시 빈 화면 → **Phase 6** |
| 이력 `/audit-history` | **동작** | audit 로그 정상 |
| 배치도 | 미구현 | → **Phase 5** |
| 카탈로그 `/product-catalog` | **동작** | 자산 유형 컬럼/드롭다운 추가, placeholder 7개 시드 |

**완료된 Phase:**
- Phase 1: 자산 기본 CRUD ✅
- Phase 2: 자산 부속 정보 (5탭 CRUD + Alias) ✅
- 자산유형 코드 체계 ✅
- 자산 등록 간소화 + 카탈로그 연동 ✅

---

## Phase 구성

```
Phase 1: 자산 기본 CRUD 완성 ← 최우선
Phase 2: 자산 부속 정보 (소프트웨어/IP할당/담당자/관계/Alias)
Phase 3: IP 인벤토리 완성
Phase 4: 포트맵 완성
Phase 5: 전산실 배치도 (신규)
Phase 6: 업체 관리 + 참여업체-자산 연결
```

Phase 2의 Alias와 Phase 5는 독립적이므로 순서 조정 가능.
각 Phase는 독립 세션에서 진행하며, 이전 Phase 완료를 전제하지 않는 항목은 병행 가능.

---

## Phase 1: 자산 기본 CRUD 완성

**목표:** 자산 목록 조회 → 등록 → 상세 보기 → 수정 → 삭제 → 검색/필터 전체 플로우가 실제로 동작.

**기존 코드:**
- 모델: `app/modules/infra/models/asset.py` (74 컬럼, 완성)
- 스키마: `app/modules/infra/schemas/asset.py` (Create/Update/Read, 완성)
- 서비스: `app/modules/infra/services/asset_service.py` (list/create/update/delete, 완성)
- 라우터: `app/modules/infra/routers/assets.py` (CRUD 엔드포인트, 완성)
- JS: `app/static/js/infra_assets.js` (AG Grid + 등록 모달, 부분 구현)
- 템플릿: `app/modules/infra/templates/infra_assets.html`

### Task 1-1: 공통 이슈 수정

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html` 또는 `app/templates/base.html`
- Modify: `app/static/js/utils.js`

- [ ] utils.js 이중 로드 해결 (`_termLabelsCache has already been declared` 에러)
- [ ] topbar 고객사 셀렉터 → `_ctxPartnerId` 초기화 타이밍 확인 및 수정
- [ ] `ctx-changed` 이벤트 발생 시 자산 목록이 자동 reload 되는지 확인
- [ ] 브라우저에서 자산 목록이 정상 표시되는지 검증
- [ ] 커밋

### Task 1-2: 자산 목록 표시 완성

**Files:**
- Modify: `app/static/js/infra_assets.js`

- [ ] `loadAssets()` 호출이 페이지 로드 시 + `ctx-changed` 이벤트 시 모두 실행되는지 확인
- [ ] AG Grid 컬럼 정의 검토 (현재 7개 → 필요 시 조정)
- [ ] 행 클릭 → 자산 상세 패널/모달 열기 구현
- [ ] 브라우저에서 더미 자산 등록 후 목록 표시 검증
- [ ] 커밋

### Task 1-3: 자산 상세 보기

**Files:**
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/modules/infra/templates/infra_assets.html`

- [ ] 자산 상세 모달/사이드패널 구현 (등록 모달의 4개 섹션 재사용)
- [ ] `GET /api/v1/assets/{id}` 호출로 전체 필드 표시
- [ ] 읽기 전용 모드로 표시
- [ ] 커밋

### Task 1-4: 자산 수정/삭제

**Files:**
- Modify: `app/static/js/infra_assets.js`

- [ ] 상세 모달에서 "수정" 버튼 → 편집 모드 전환
- [ ] 수정 저장 → `PATCH /api/v1/assets/{id}` → 목록 새로고침
- [ ] "삭제" 버튼 → 확인 다이얼로그 → `DELETE /api/v1/assets/{id}` → 목록 새로고침
- [ ] 브라우저에서 수정/삭제 플로우 검증
- [ ] 커밋

### Task 1-5: 자산 검색/필터

**Files:**
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/modules/infra/services/asset_service.py` (이미 `q` 파라미터 지원)

- [ ] 검색 입력 필드 추가 (asset_name, hostname, service_ip, equipment_id 통합 검색)
- [ ] 유형/상태 필터 드롭다운 추가
- [ ] "선택 프로젝트만" 체크박스 동작 확인 (이미 UI 존재)
- [ ] 브라우저에서 검색/필터 검증
- [ ] 커밋

### Task 1-6: 자산 Import 검증

**Files:**
- Modify: `app/static/js/infra_assets.js` (Import 버튼 핸들러)

- [ ] Import 버튼 클릭 → 파일 업로드 → `POST /api/v1/infra-excel/import` 동작 확인
- [ ] Import 후 목록 새로고침 확인
- [ ] 에러 시 사용자에게 피드백 표시 확인
- [ ] 커밋

**Phase 1 완료 기준:** 자산 등록→목록 표시→상세 보기→수정→삭제→검색 전체가 브라우저에서 동작.

---

## Phase 2: 자산 부속 정보

**목표:** 자산 상세에서 소프트웨어/IP할당/담당자/관계/Alias를 관리.

**기존 코드:**
- AssetSoftware: 모델/스키마/서비스/라우터 완성, UI 미구현
- AssetIP: 모델/스키마/서비스/라우터 완성, UI 미구현
- AssetContact: 모델/스키마/서비스/라우터 완성, UI 미구현
- AssetRelation: 모델/스키마/서비스/라우터 완성, UI 미구현
- AssetAlias: 신규 (layout-and-alias 계획에 상세 코드 있음)

### Task 2-1: AssetAlias DB 기반 구축

`docs/superpowers/plans/2026-03-24-layout-and-alias.md`의 Task 1(모델) + Task 2(Migration) + Task 3(스키마) + Task 4(서비스) + Task 5(라우터)에서 **AssetAlias 관련 부분만** 실행.

- [ ] AssetAlias 모델 생성 + models/__init__.py 등록
- [ ] Alembic migration (asset_aliases 테이블만)
- [ ] AssetAlias 스키마 (Create/Update/Read + AliasType Enum)
- [ ] asset_alias_service.py
- [ ] asset_aliases.py 라우터 + routers/__init__.py 등록
- [ ] 커밋

### Task 2-2: 자산 상세 — 탭/섹션 구조

**Files:**
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/modules/infra/templates/infra_assets.html`

자산 상세 모달을 탭 구조로 확장:

```
기본 정보 | 소프트웨어 | IP 할당 | 담당자 | 관계 | 별칭(Alias)
```

- [ ] 탭 UI 프레임 구현 (기본 정보 탭은 Task 1-3에서 이미 구현)
- [ ] 각 탭은 빈 컨테이너로 시작 (Phase 2 Task별로 채움)
- [ ] 커밋

### Task 2-3: 소프트웨어 탭

- [ ] `GET /api/v1/assets/{id}/software` 로 목록 조회
- [ ] 소프트웨어 추가/수정/삭제 UI
- [ ] 브라우저 검증
- [ ] 커밋

### Task 2-4: IP 할당 탭

- [ ] `GET /api/v1/assets/{id}/ips` 로 IP 목록 조회
- [ ] IP 추가/수정/삭제 UI
- [ ] 커밋

### Task 2-5: 담당자 탭

- [ ] `GET /api/v1/assets/{id}/contacts` 로 담당자 목록 조회
- [ ] 담당자 연결/해제 UI (partner_contacts에서 선택)
- [ ] 커밋

### Task 2-6: 관계 탭

- [ ] `GET /api/v1/assets/{id}/relations` 로 관계 목록 조회
- [ ] 관계 추가/삭제 UI (관계 유형: HOSTS, INSTALLED_ON, PROTECTS 등)
- [ ] 커밋

### Task 2-7: Alias 탭

- [ ] `GET /api/v1/assets/{id}/aliases` 로 Alias 목록 조회
- [ ] Alias 추가/수정/삭제 UI
- [ ] source_partner_id 있으면 정상색, source_text만 있으면 회색 표시
- [ ] 커밋

### Task 2-8: 자산 검색에 Alias 통합

- [ ] `asset_service.py`의 `list_assets()` 검색에 alias_name + asset_code 서브쿼리 추가
- [ ] 브라우저에서 alias로 검색 검증
- [ ] 커밋

**Phase 2 완료 기준:** 자산 상세에서 6개 탭 모두 CRUD 동작. Alias 검색 통합 완료.

---

## Phase 3: IP 인벤토리 완성

**목표:** 서브넷 목록 + IP 할당 목록이 정상 표시되고 CRUD 동작.

**기존 코드:**
- IpSubnet: 모델/스키마/서비스/라우터 완성
- AssetIP: 모델/스키마/서비스/라우터 완성
- JS: `app/static/js/infra_ip_inventory.js` (좌우 분할 UI, 부분 구현)
- 템플릿: `app/modules/infra/templates/infra_ip_inventory.html`

### Task 3-1: 서브넷 목록 표시 수정

- [ ] `loadSubnets()` 에서 `getCtxPartnerId()` 연동 확인/수정
- [ ] 서브넷 목록 좌측 패널에 정상 표시
- [ ] 서브넷 선택 → 우측 IP 할당 목록 필터링
- [ ] 커밋

### Task 3-2: 서브넷 CRUD

- [ ] "+ 대역 추가" → 서브넷 등록 모달 동작 확인
- [ ] 수정/삭제 버튼 동작 확인
- [ ] 커밋

### Task 3-3: IP 할당 CRUD

- [ ] "IP 등록" → IP 할당 등록 모달 (asset 선택 포함)
- [ ] IP 할당 목록에서 수정/삭제
- [ ] 커밋

**Phase 3 완료 기준:** 서브넷 등록 → IP 할당 → 목록 표시 전체 동작.

---

## Phase 4: 포트맵 완성

**목표:** 포트맵(케이블 배선도) CRUD + Excel Import 동작.

**기존 코드:**
- PortMap: 모델/스키마/서비스/라우터 완성 (40+ 필드)
- JS: `app/static/js/infra_port_maps.js` (부분 구현)
- 템플릿: `app/modules/infra/templates/infra_port_maps.html`

### Task 4-1: 포트맵 목록 표시 수정

- [ ] `loadPortMaps()` partner_id 연동 확인/수정
- [ ] AG Grid 컬럼 정의 검토 (출발/도착 호스트/포트/존 등)
- [ ] 커밋

### Task 4-2: 배선 등록/수정/삭제

- [ ] "배선 등록" 모달 구현 (출발/도착 자산 선택, 포트/케이블 정보)
- [ ] 행 클릭 → 상세/수정
- [ ] 삭제
- [ ] 커밋

### Task 4-3: 포트맵 Excel Import

- [ ] Import UI 동작 확인 (파일 선택 → Import 버튼)
- [ ] `POST /api/v1/infra-excel/import` 포트맵 시트 처리 확인
- [ ] Import 결과 토스트 표시
- [ ] 커밋

**Phase 4 완료 기준:** 포트맵 등록 + Excel Import + 목록 조회 동작.

---

## Phase 5: 전산실 배치도 (신규)

**목표:** 센터/전산실/Zone/Rack 공간 구조 정의 + 자산 매핑 시각화.

**상세 계획:** `docs/superpowers/plans/2026-03-24-layout-and-alias.md` 참조.

이 Phase는 DB 기반이 먼저 구축되어야 함. layout-and-alias 계획의 Task 1~7 중 배치도 관련 부분 실행.

### Task 5-1: 배치도 DB 기반 (모델 + Migration + 스키마 + 서비스 + 라우터)

layout-and-alias 계획의 Center/Room/RoomZone/RackPosition/AssetRackMapping 관련 전체 실행.

- [ ] 5개 모델 생성 + migration
- [ ] 5개 스키마 생성
- [ ] center_service, room_service, layout_service 생성
- [ ] 6개 라우터 생성 (centers, rooms, room_zones, rack_positions, asset_rack_mappings, layout)
- [ ] 모델/라우터 등록
- [ ] 커밋

### Task 5-2: 사이드바 메뉴 + 페이지 라우트 + 기본 템플릿

- [ ] `/layout` 페이지 라우트 추가
- [ ] 사이드바에 "배치도" 메뉴 추가
- [ ] 4개 탭 placeholder 템플릿
- [ ] 커밋

### Task 5-3: 센터/전산실 관리 탭

- [ ] 센터 AG Grid CRUD
- [ ] 전산실 AG Grid CRUD (선택 센터 하위)
- [ ] 커밋

### Task 5-4: 배치도 편집 — 그리드 캔버스

- [ ] 센터/전산실 선택 → `GET /rooms/{id}/layout` → HTML table 그리드 렌더링
- [ ] 편집/조회 모드 전환
- [ ] 빈 셀 드래그 → zone 생성
- [ ] 빈 셀 클릭 → 랙 등록 모달
- [ ] 기존 zone/rack 편집/삭제
- [ ] 커밋

### Task 5-5: 자산 매핑 + 시각화

- [ ] 자동 매핑 버튼 → `POST /rooms/{id}/auto-map`
- [ ] 매핑 상태별 색상 (mapped=기본, unmapped=회색, empty=연한색, conflict=빨간색)
- [ ] 미매핑 자산 목록 표시
- [ ] 수동 매핑 (자산 → 랙 드래그 또는 모달 선택)
- [ ] 커밋

**Phase 5 완료 기준:** 센터/전산실 등록 → 그리드에 zone/rack 배치 → 자산 매핑 → 상태별 색상 시각화 동작.

---

## Phase 6: 업체 관리 + 참여업체-자산 연결

**목표:** 프로젝트별 참여업체 관리 완성 + 업체-자산 연결 기능 추가.

**기존 코드:**
- PeriodPartner/PeriodPartnerContact: 모델/스키마/서비스/라우터 완성
- JS: 업체 페이지 부분 구현 (프로젝트 선택 필요)
- 참여업체-자산 연결: KNOWN_ISSUES.md에 TODO 기록

### Task 6-1: 업체 페이지 프로젝트 의존성 개선

- [ ] 프로젝트 미선택 시에도 고객사 스코프로 전체 업체 표시 (또는 명확한 안내)
- [ ] 프로젝트 선택 시 해당 프로젝트 참여업체만 필터
- [ ] 커밋

### Task 6-2: 참여업체 CRUD 완성

- [ ] 업체 연결 모달 (거래처 목록에서 선택 + 역할 지정)
- [ ] 담당자 매핑 (PeriodPartnerContact)
- [ ] 수정/해제
- [ ] 커밋

### Task 6-3: 참여업체-자산 연결 (신규)

- [ ] PeriodPartnerAsset 모델 생성 (period_partner_id, asset_id, role)
- [ ] Migration
- [ ] 스키마/서비스/라우터
- [ ] 업체 상세에서 담당 자산 목록 표시 + 자산 연결/해제 UI
- [ ] KNOWN_ISSUES.md에서 해당 TODO 삭제
- [ ] 커밋

**Phase 6 완료 기준:** 참여업체 연결/담당자 매핑/자산 연결이 모두 동작.

---

## Phase 순서 권장

```
Phase 1 (자산 기본) ──→ Phase 2 (자산 부속)
                                    ↓
Phase 3 (IP인벤토리) ←──── Phase 2-4 (IP 할당 탭과 연동)
Phase 4 (포트맵) ←── 독립
Phase 5 (배치도) ←── Phase 1 완료 후 (자산 데이터 필요)
Phase 6 (업체) ←── Phase 1 완료 후
```

- **Phase 1은 필수 선행.** 모든 기능이 자산 데이터에 의존.
- **Phase 2-D (Alias)** 는 Phase 2의 다른 탭과 독립이므로 먼저 진행 가능.
- **Phase 3, 4, 5, 6**은 Phase 1 이후 어떤 순서로든 진행 가능.

---

## 세션 전환 가이드

각 Phase 시작 시:
1. memory의 `project_active_plan.md` 읽기
2. 이 로드맵 파일 읽기
3. 해당 Phase의 기존 코드 파일 확인
4. 서버 기동 + 브라우저 확인으로 현재 상태 파악
5. Task 순차 진행, 완료 시 커밋

Phase 완료 시:
1. 브라우저 E2E 검증
2. memory 업데이트 (완료 Phase, 다음 Phase)
3. 필요 시 이 로드맵의 현재 상태 표 갱신
