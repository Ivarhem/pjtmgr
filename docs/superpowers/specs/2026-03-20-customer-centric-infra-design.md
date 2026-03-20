# 인프라모듈 고객사 중심 구조 전환 설계

> **Status:** Draft
> **Date:** 2026-03-20
> **Scope:** 인프라모듈의 데이터 소유 구조를 프로젝트 중심에서 고객사 중심으로 전환하고, 네비게이션/UI를 재설계한다.

---

## 1. 배경 및 목적

### 현재 문제

- 자산/IP/포트맵이 `project_id` FK로 프로젝트에 귀속되어 있어, 같은 고객사의 병렬 프로젝트에서 **동일 물리 자산을 중복 등록**해야 한다.
- 프로젝트 중심 네비게이션으로는 고객사 전체 인프라를 한 눈에 파악하기 어렵다.

### 목표

- 자산/IP/포트맵의 소유 주체를 **고객사(Customer)**로 변경한다.
- 프로젝트는 자산을 소유하지 않고 **참조(ProjectAsset N:M)**한다.
- 고객사 + 프로젝트 2단 셀렉터로 컨텍스트를 전환하고, 수평 메뉴로 페이지를 탐색한다.

---

## 2. 데이터 모델 변경

### 2.1 FK 교체

| 모델 | 현재 | 변경 후 |
|------|------|--------|
| `Asset` | `project_id` FK (NOT NULL) | `customer_id` FK (NOT NULL) |
| `IpSubnet` | `project_id` FK (NOT NULL) | `customer_id` FK (NOT NULL) |
| `PortMap` | `project_id` FK (NOT NULL) | `customer_id` FK (NOT NULL) |
| `PolicyAssignment` | `project_id` FK (NOT NULL) | `customer_id` FK (NOT NULL) + `asset_id` 유지 |
| `Project` | `customer_id` FK (nullable) | `customer_id` FK (**NOT NULL**) |

### 2.2 프로젝트 연결

- `Asset` ↔ `Project`: 기존 `ProjectAsset` N:M 테이블 활용 (변경 없음)
- `IpSubnet`, `PortMap`: 프로젝트 N:M 불필요 — 자산 FK를 통해 간접 추적
- `Asset.project_id` FK: **삭제** (ProjectAsset N:M이 대체)

### 2.3 Pin 프로젝트 → Pin 고객사

| UserPreference key | 변경 |
|---|---|
| `infra.pinned_project_id` | **삭제** |
| `infra.pinned_customer_id` | 신규 — 고정 고객사 |
| `infra.last_project_id` | 신규 — 마지막 선택 프로젝트 |

---

## 3. 네비게이션 구조

### 3.1 topbar 배치

```
[프로젝트관리] | [고객사 ▼ OO공사] [프로젝트 ▼ 전체]  ···  [영업관리 전환] | admin 로그아웃
```

- **좌측**: 모듈 제목 + 고객사/프로젝트 셀렉터 (인프라 모듈 전용)
- **우측**: 모듈 전환 버튼 + 사용자 영역 (모듈 공통)
- 영업관리 모듈에는 셀렉터 없이 제목만 표시

### 3.2 subnav 메뉴 (수평)

```
프로젝트 | 자산 | IP인벤토리 | 포트맵 | 정책정의 | 적용현황 | 담당자 | 이력 | 현황판
```

회계모듈(내 사업 | 사업 관리 | 대시보드 | 보고서)과 동일한 수평 메뉴 패턴.

### 3.3 메뉴별 조회 범위

| 메뉴 | 범위 | 프로젝트 필터 |
|------|------|--------------|
| 프로젝트 | 선택 고객사의 프로젝트 목록 | 해당 없음 |
| 자산 | 고객사 전체 | ☐ 선택 프로젝트만 (ProjectAsset 기준) |
| IP 인벤토리 | 고객사 전체 | 필터 없음 (서브넷은 고객사 레벨) |
| 포트맵 | 고객사 전체 | ☐ 선택 프로젝트만 (자산 FK 경유) |
| 정책 정의 | 고객사 적용 정책 | 없음 |
| 적용 현황 | 고객사 전체 | ☐ 선택 프로젝트만 (자산 FK 경유) |
| 담당자/업체 | 고객사 연락처 | 없음 |
| 변경이력 | 고객사 감사 로그 | 없음 |
| 현황판 | 고객사 현황 요약 | 없음 |

### 3.4 프로젝트 필터링 동작

- 프로젝트 드롭다운 "전체": 고객사 범위 전체 데이터
- 특정 프로젝트 선택: 각 페이지에 `☐ 선택 프로젝트만 보기` 체크박스 제공
  - 자산: `ProjectAsset.project_id` 기준
  - 포트맵: `src/dst_asset_id`가 프로젝트 자산에 포함된 것만
  - 적용 현황: `asset_id`가 프로젝트 자산에 포함된 것만

### 3.5 고객사 셀렉터 동작

1. **최초 로그인**: 고객사 미선택 → 선택 안내 표시
2. **고객사 선택**: `UserPreference(infra.pinned_customer_id)` 저장, 메뉴 활성화
3. **프로젝트 선택**: `UserPreference(infra.last_project_id)` 저장
4. **재로그인**: 이전 고객사 + 프로젝트 자동 복원
5. **topbar 표시**: 셀렉터 드롭다운에 현재 선택값 표시 (기존 Pin 뱃지 대체)

---

## 4. 페이지별 UI 레이아웃

### 4.1 자산 페이지

**기본: 전체 그리드 + 하단 확장 패널 (B안)**

```
┌─────────────────────────────────────────────┐
│ 자산         [검색] ☐선택프로젝트만  Import +등록│
├─────────────────────────────────────────────┤
│ 자산명    유형   벤더   모델   호스트명  IP  상태│
│ srv-web   서버   Dell   R750  web01  ...  운영│
│▶sw-core   NW    Cisco  C9300 core01 ...  운영│← 선택 행
│ fw-edge   보안   Palo   PA850 edge01 ...  계획│
├─────────────────────────────────────────────┤
│ sw-core-01 상세                    [수정][삭제]│
│ [기본정보][설치위치][네트워크][HW사양][자산관리][관계]│
│  자산코드: AST-0042  유형: 네트워크             │
│  벤더: Cisco         모델: C9300-48T           │
│  ...                                          │
└─────────────────────────────────────────────┘
```

- 행 클릭 시 하단에 그룹별 탭 상세 확장
- 상세 미선택 시 그리드만 전체 높이 사용
- **옵션**: 좌우 분할 레이아웃(A안)으로 전환 가능 (사용자 설정)

### 4.2 IP 인벤토리 페이지

**좌우 분할 — 서브넷 목록 + 상세/IP**

```
┌──────────────────┬──────────────────────────┐
│ 서브넷 목록       │ 서브넷 상세               │
│                  │ ┌────────────────────────┐│
│ ▶서비스대역       │ │서비스대역 (10.0.1.0/24)││
│   10.0.1.0/24    │ │GW: 10.0.1.1 VLAN: 100 ││
│                  │ │역할: 서비스  존: DMZ    ││
│   관리대역        │ │설명: 웹서버 서비스 구간 ││
│   10.0.2.0/24    │ └────────────────────────┘│
│                  │                           │
│  ─ ─ ─ ─ ─ ─    │ IP 할당 현황               │
│  [전체]          │ ┌────────────────────────┐│
│  [+ 대역 추가]   │ │10.0.1.2 srv-web-01 eth0││
│                  │ │10.0.1.3 srv-web-02 eth0││
│                  │ │10.0.1.4 srv-db-01  eth0││
│                  │ │☐ 선택 프로젝트만 보기   ││
│                  │ └────────────────────────┘│
└──────────────────┴──────────────────────────┘
```

- 왼쪽: 서브넷 명칭 + 대역 모두 표시, "전체" 선택 시 모든 IP 표시
- 오른쪽 상단: 선택 서브넷의 상세 (게이트웨이, VLAN, 역할, 존, 설명)
- 오른쪽 하단: 해당 대역 IP 할당 목록 (AG Grid)
- 게이트웨이 매핑: 자산 인터페이스 IP → IpSubnet 매칭으로 게이트웨이 자동 표시 활용

### 4.3 기타 페이지

| 페이지 | 레이아웃 | 비고 |
|--------|---------|------|
| 프로젝트 | 그리드 | 선택 고객사의 프로젝트 목록, 클릭 시 상세 페이지 |
| 포트맵 | 전체 그리드 | 필드 많아 전체 너비 활용, 프로젝트 필터 체크박스 |
| 정책 정의 | 전체 그리드 | 고객사에 적용된 정책 목록 |
| 적용 현황 | 전체 그리드 | 자산별 정책 준수 상태 |
| 담당자/업체 | 카드 레이아웃 | 기존 패턴 유지 (업체 카드 + 소속 담당자) |
| 변경이력 | 전체 그리드 | 감사 로그 |
| 현황판 | 대시보드 카드 | 요약 통계 |

---

## 5. API 변경

### 5.1 기존 API 변경

| 현재 | 변경 후 |
|------|--------|
| `GET /api/v1/assets?project_id=N` | `GET /api/v1/assets?customer_id=N` |
| `GET /api/v1/projects/{id}/ip-subnets` | `GET /api/v1/ip-subnets?customer_id=N` |
| `GET /api/v1/projects/{id}/port-maps` | `GET /api/v1/port-maps?customer_id=N` |
| `GET /api/v1/projects/{id}/policy-assignments` | `GET /api/v1/policy-assignments?customer_id=N` |
| `GET /api/v1/projects/{id}/asset-relations` | `GET /api/v1/asset-relations?customer_id=N` |

### 5.2 프로젝트 필터 (옵션 파라미터)

- `GET /api/v1/assets?customer_id=N&project_id=M` → ProjectAsset 기준 필터
- `GET /api/v1/port-maps?customer_id=N&project_id=M` → 자산 FK 경유
- `GET /api/v1/policy-assignments?customer_id=N&project_id=M` → 자산 FK 경유

### 5.3 유지/추가 API

| API | 변경 |
|-----|------|
| `GET /api/v1/projects?customer_id=N` | customer_id 파라미터 추가 |
| `POST/PATCH/DELETE /api/v1/assets` | `customer_id` 필수 |
| `GET /api/v1/project-assets` | 유지 (N:M 연결 관리) |
| `GET /api/v1/policy-definitions` | 유지 (전역) |
| `GET /api/v1/preferences/{key}` | 유지 (키값만 변경) |

### 5.4 공통 헬퍼

```python
def get_project_asset_ids(db: Session, project_id: int) -> set[int]:
    """프로젝트에 연결된 자산 ID 목록 — 프로젝트 필터용"""
    return set(db.scalars(
        select(ProjectAsset.asset_id).where(ProjectAsset.project_id == project_id)
    ))
```

---

## 6. 마이그레이션 전략

### 6.1 Alembic migration (`0005_customer_centric_restructure`)

```
upgrade:
  1. Asset, IpSubnet, PortMap, PolicyAssignment에 customer_id 컬럼 추가 (nullable, FK → customers.id)
  2. Project.customer_id를 NOT NULL로 변경
  3. 데이터 백필: 각 테이블의 project_id → Project.customer_id 역추적 → customer_id 채움
  4. customer_id NOT NULL 제약 적용
  5. Asset.project_id, IpSubnet.project_id, PortMap.project_id, PolicyAssignment.project_id FK 제거

downgrade:
  역순 복원 (customer_id → project_id 역추적)
```

### 6.2 UserPreference 마이그레이션

기존 `infra.pinned_project_id` 값이 있으면:
1. 해당 프로젝트의 `customer_id`를 조회
2. `infra.pinned_customer_id`에 저장
3. `infra.last_project_id`에 기존 값 이동
4. `infra.pinned_project_id` 삭제

### 6.3 프론트엔드 변경 범위

| 영역 | 변경 |
|------|------|
| `base.html` topbar | 고객사/프로젝트 셀렉터 추가, 모듈전환 버튼 우측 이동 |
| `base.html` subnav | 인프라 메뉴 항목 재구성 (9개), 자산검색/Import 제거 |
| `utils.js` | `getPinnedCustomerId()`, `getLastProjectId()` 등 유틸 변경 |
| 각 인프라 페이지 JS | `project_id` → `customer_id` 기준 API 호출 변경 |
| 자산 페이지 | 그리드 + 하단 확장 패널 (B안 기본, A안 전환 가능) |
| IP 인벤토리 페이지 | 좌우 분할 + 서브넷 상세 카드 |
| 프로젝트 상세 페이지 | 자산/IP/포트맵 탭의 scope 조정 (프로젝트 연결 항목만) |

---

## 7. 영향 받지 않는 영역

- **회계모듈**: 변경 없음. Customer 모델은 common 모듈 소유로 공유만 됨.
- **PolicyDefinition**: 전역 테이블 유지. 정책 정의 페이지에서 고객사별 적용 현황만 필터.
- **AssetContact**: asset_id FK — 자산이 고객사로 이동하면 자동으로 따라감.
- **ProjectCustomer, ProjectCustomerContact**: 프로젝트-업체 연결 유지 (프로젝트 상세에서 사용).
