# 인프라모듈 고객사 중심 구조 전환 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 인프라모듈의 데이터 소유를 프로젝트 중심에서 고객사 중심으로 전환하고, 네비게이션/UI를 재설계한다.

**Architecture:** Asset/IpSubnet/PortMap/PolicyAssignment의 `project_id` FK를 `customer_id` FK로 교체. Project는 `customer_id` NOT NULL. Asset↔Project는 `ProjectAsset` N:M으로 연결. topbar에 고객사/프로젝트 2단 셀렉터, subnav에 9개 메뉴.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Alembic, Jinja2, AG Grid, openpyxl, pytest

**Spec:** `docs/superpowers/specs/2026-03-20-customer-centric-infra-design.md`

---

## 검증 루핑 탈출 프로토콜

> **모든 에이전트와 리뷰어에게 적용되는 필수 규칙.**

1. **동일 오류로 2회 연속 실패하면 즉시 중단**한다. 3번째 시도를 하지 않는다.
2. 중단 시 실패 원인, 시도한 접근 방식 2가지, 원인 추정을 보고한다.
3. **범위 축소 제안**을 포함한다.
4. 사용자 승인 없이 재시도하지 않는다.

---

## 전체 Phase 구성

| Phase | 내용 | 의존성 | 예상 파일 수 |
|-------|------|--------|-------------|
| 1 | Alembic migration + 모델 FK 교체 | 없음 | 6 |
| 2 | 스키마 + 서비스 레이어 (customer_id 전환) | Phase 1 | 12 |
| 3 | 라우터 (API 엔드포인트 변경) | Phase 2 | 8 |
| 4 | topbar 셀렉터 + subnav 메뉴 재구성 | Phase 1 | 4 |
| 5 | 자산 페이지 (그리드 + 하단 상세) | Phase 3,4 | 3 |
| 6 | IP 인벤토리 페이지 (좌우 분할) | Phase 3,4 | 3 |
| 7 | 나머지 페이지 (포트맵/정책/담당자/이력/현황판/프로젝트) | Phase 3,4 | 12 |
| 8 | Excel Import/Export + 테스트 + 문서 | Phase 2,3 | 8 |

권장 실행 순서: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8
Phase 4는 Phase 2 이후 병렬 가능.

---

## Phase 1: Alembic Migration + 모델 FK 교체

### Task 1.1: Alembic migration 생성

**Files:**
- Create: `alembic/versions/0005_customer_centric_restructure.py`

- [ ] **Step 1: migration 파일 생성**

```python
"""customer centric restructure

Revision ID: 0005
Revises: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"

def upgrade():
    conn = op.get_bind()

    # Step 1b: Project.customer_id NULL 검증
    result = conn.execute(sa.text("SELECT COUNT(*) FROM projects WHERE customer_id IS NULL"))
    null_count = result.scalar()
    if null_count > 0:
        raise RuntimeError(
            f"Cannot migrate: {null_count} projects have NULL customer_id. "
            "Assign customer_id to all projects before running this migration."
        )

    # Step 1: customer_id 컬럼 추가 (nullable)
    for table in ["assets", "ip_subnets", "port_maps", "policy_assignments"]:
        op.add_column(table, sa.Column("customer_id", sa.Integer, sa.ForeignKey("customers.id"), nullable=True))
        op.create_index(f"ix_{table}_customer_id", table, ["customer_id"])

    # Step 2: Project.customer_id NOT NULL
    op.alter_column("projects", "customer_id", nullable=False)

    # Step 3: 데이터 백필
    for table in ["assets", "ip_subnets", "port_maps", "policy_assignments"]:
        conn.execute(sa.text(f"""
            UPDATE {table} t
            SET customer_id = p.customer_id
            FROM projects p
            WHERE t.project_id = p.id
        """))

    # Step 4: customer_id NOT NULL 적용
    for table in ["assets", "ip_subnets", "port_maps", "policy_assignments"]:
        op.alter_column(table, "customer_id", nullable=False)

    # Step 5: project_id FK 제거
    for table in ["assets", "ip_subnets", "port_maps", "policy_assignments"]:
        op.drop_constraint(f"{table}_project_id_fkey", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_project_id", table)
        op.drop_column(table, "project_id")

def downgrade():
    raise NotImplementedError(
        "Downgrade not supported. Restore from DB backup if rollback needed."
    )
```

- [ ] **Step 2: 커밋**

```bash
git add alembic/versions/0005_customer_centric_restructure.py
git commit -m "feat: add migration 0005 for customer-centric restructure"
```

---

### Task 1.2: 모델 FK 교체

**Files:**
- Modify: `app/modules/infra/models/asset.py:16`
- Modify: `app/modules/infra/models/ip_subnet.py:14`
- Modify: `app/modules/infra/models/port_map.py:14`
- Modify: `app/modules/infra/models/policy_assignment.py:16`
- Modify: `app/modules/infra/models/project.py:18-19`

- [ ] **Step 1: Asset 모델 수정**

`asset.py` line 16:
```python
# 변경 전: project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
# 변경 후:
customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
```

- [ ] **Step 2: IpSubnet 모델 수정**

`ip_subnet.py` line 14:
```python
# 변경 전: project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
# 변경 후:
customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
```

- [ ] **Step 3: PortMap 모델 수정**

`port_map.py` line 14:
```python
# 변경 전: project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
# 변경 후:
customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
```

- [ ] **Step 4: PolicyAssignment 모델 수정**

`policy_assignment.py` line 16:
```python
# 변경 전: project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
# 변경 후:
customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
```

- [ ] **Step 5: Project 모델 — customer_id NOT NULL**

`project.py` lines 18-19:
```python
# 변경 전: customer_id: Mapped[int | None] = mapped_column(...)
# 변경 후:
customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True, nullable=False)
```

- [ ] **Step 6: 커밋**

```bash
git add app/modules/infra/models/asset.py app/modules/infra/models/ip_subnet.py \
  app/modules/infra/models/port_map.py app/modules/infra/models/policy_assignment.py \
  app/modules/infra/models/project.py
git commit -m "refactor: replace project_id with customer_id FK in infra models"
```

---

## Phase 2: 스키마 + 서비스 레이어

### Task 2.1: 스키마 변경

**Files:**
- Modify: `app/modules/infra/schemas/asset.py` — `project_id` → `customer_id`
- Modify: `app/modules/infra/schemas/ip_subnet.py` — 동일
- Modify: `app/modules/infra/schemas/port_map.py` — 동일
- Modify: `app/modules/infra/schemas/policy_assignment.py` — 동일
- Modify: `app/modules/infra/schemas/project.py` — `customer_id` 필수

- [ ] **Step 1: 각 스키마의 Create/Update/Read에서 `project_id` → `customer_id` 변경**

AssetCreate 예시:
```python
# 변경 전: project_id: int
# 변경 후:
customer_id: int
```

AssetRead: `customer_id` 추가, `project_id` 제거. ProjectAsset 기반 프로젝트 정보는 enrichment로 제공.

ProjectCreate/Update: `customer_id: int` 필수(Optional 제거).

- [ ] **Step 2: 커밋**

```bash
git add app/modules/infra/schemas/
git commit -m "refactor: update schemas for customer_id FK"
```

---

### Task 2.2: 공통 헬퍼 함수

**Files:**
- Create or Modify: `app/modules/infra/services/_helpers.py` (없으면 생성)

- [ ] **Step 1: 프로젝트 필터용 헬퍼 추가**

```python
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.modules.infra.models.project_asset import ProjectAsset
from app.modules.common.models.customer import Customer
from app.core.exceptions import NotFoundError

def get_project_asset_ids(db: Session, project_id: int) -> set[int]:
    """프로젝트에 연결된 자산 ID 목록."""
    return set(db.scalars(
        select(ProjectAsset.asset_id).where(ProjectAsset.project_id == project_id)
    ))

def ensure_customer_exists(db: Session, customer_id: int) -> None:
    if db.get(Customer, customer_id) is None:
        raise NotFoundError("Customer not found")
```

- [ ] **Step 2: 커밋**

---

### Task 2.3: asset_service.py 전환

**Files:**
- Modify: `app/modules/infra/services/asset_service.py`

- [ ] **Step 1: `list_assets()` — `project_id` 파라미터를 `customer_id` + 옵션 `project_id`로 변경**

```python
def list_assets(db: Session, customer_id: int, project_id: int | None = None, ...) -> list[dict]:
    stmt = select(Asset).where(Asset.customer_id == customer_id)
    if project_id:
        asset_ids = get_project_asset_ids(db, project_id)
        if asset_ids:
            stmt = stmt.where(Asset.id.in_(asset_ids))
        else:
            return []
    # ... 기존 필터(asset_type, status, q) 유지
```

- [ ] **Step 2: `create_asset()` — `project_id` → `customer_id` 검증**

`_ensure_project_exists()` → `ensure_customer_exists()` 호출.
`_ensure_asset_name_unique(db, project_id, ...)` → `_ensure_asset_name_unique(db, customer_id, ...)`.

- [ ] **Step 3: `_ensure_asset_name_unique()` 수정**

```python
def _ensure_asset_name_unique(db: Session, customer_id: int, asset_name: str, exclude_id: int | None = None):
    stmt = select(Asset.id).where(Asset.customer_id == customer_id, Asset.asset_name == asset_name)
    if exclude_id:
        stmt = stmt.where(Asset.id != exclude_id)
    if db.scalar(stmt):
        raise DuplicateError(f"자산명 '{asset_name}'이 이 고객사에 이미 존재합니다.")
```

- [ ] **Step 4: `update_asset()`, `delete_asset()` 수정 — project_id 참조 제거**

- [ ] **Step 5: 커밋**

---

### Task 2.4: network_service.py 전환

**Files:**
- Modify: `app/modules/infra/services/network_service.py`

- [ ] **Step 1: `list_subnets()` — `project_id` → `customer_id`**

```python
def list_subnets(db: Session, customer_id: int) -> list[dict]:
    return list(db.scalars(
        select(IpSubnet).where(IpSubnet.customer_id == customer_id).order_by(IpSubnet.name)
    ))
```

- [ ] **Step 2: `list_port_maps()` — `project_id` → `customer_id` + 옵션 `project_id`**

```python
def list_port_maps(db: Session, customer_id: int, project_id: int | None = None) -> list[dict]:
    stmt = select(PortMap).where(PortMap.customer_id == customer_id)
    if project_id:
        asset_ids = get_project_asset_ids(db, project_id)
        # 외부 구간(양쪽 NULL)은 항상 포함
        stmt = stmt.where(
            or_(
                PortMap.src_asset_id.in_(asset_ids),
                PortMap.dst_asset_id.in_(asset_ids),
                and_(PortMap.src_asset_id.is_(None), PortMap.dst_asset_id.is_(None)),
            )
        )
    ...
```

- [ ] **Step 3: `create_subnet()`, `create_port_map()` — `project_id` → `customer_id`**

- [ ] **Step 4: `list_project_ips()` — customer 범위로 변경**

- [ ] **Step 5: `_ensure_ip_unique_in_project()` → `_ensure_ip_unique_in_customer()`**

- [ ] **Step 6: 커밋**

---

### Task 2.5: policy_service.py 전환

**Files:**
- Modify: `app/modules/infra/services/policy_service.py`

- [ ] **Step 1: `list_assignments()` — `project_id` → `customer_id` + 옵션 `project_id`**

- [ ] **Step 2: `create_assignment()` — customer_id 검증으로 변경**

- [ ] **Step 3: 커밋**

---

### Task 2.6: 기타 서비스 전환

**Files:**
- Modify: `app/modules/infra/services/asset_relation_service.py` — `list_by_project()` → `list_by_customer()`
- Modify: `app/modules/infra/services/infra_metrics.py` — 모든 `project_id` → `customer_id`
- Modify: `app/modules/infra/services/project_service.py` — `list_projects()`에 `customer_id` 파라미터 추가; `delete_project()` 검증 변경

- [ ] **Step 1: asset_relation_service.py**

```python
def list_by_customer(db: Session, customer_id: int) -> list[dict]:
    asset_ids_q = select(Asset.id).where(Asset.customer_id == customer_id)
    rels = list(db.scalars(
        select(AssetRelation).where(
            or_(
                AssetRelation.src_asset_id.in_(asset_ids_q),
                AssetRelation.dst_asset_id.in_(asset_ids_q),
            )
        ).order_by(AssetRelation.id.asc())
    ))
    return _enrich(db, rels)
```

- [ ] **Step 2: infra_metrics.py — 모든 쿼리에서 `project_id` → `customer_id`**

- [ ] **Step 3: project_service.py — `list_projects(db, customer_id=None)` 필터 추가**

- [ ] **Step 4: 커밋**

---

## Phase 3: 라우터 (API 엔드포인트 변경)

### Task 3.1: assets 라우터

**Files:**
- Modify: `app/modules/infra/routers/assets.py`

- [ ] **Step 1: `GET /api/v1/assets` — `project_id` 파라미터를 `customer_id` + 옵션 `project_id`로 변경**
- [ ] **Step 2: `POST /api/v1/assets` — payload에 `customer_id` 필수**
- [ ] **Step 3: 커밋**

---

### Task 3.2: ip_subnets 라우터

**Files:**
- Modify: `app/modules/infra/routers/ip_subnets.py`

- [ ] **Step 1: `GET /api/v1/projects/{project_id}/ip-subnets` → `GET /api/v1/ip-subnets?customer_id=N`**
- [ ] **Step 2: `POST` 동일 변경**
- [ ] **Step 3: 커밋**

---

### Task 3.3: port_maps 라우터

**Files:**
- Modify: `app/modules/infra/routers/port_maps.py`

- [ ] **Step 1: `GET /api/v1/projects/{project_id}/port-maps` → `GET /api/v1/port-maps?customer_id=N`**
- [ ] **Step 2: `POST` 동일 변경**
- [ ] **Step 3: 커밋**

---

### Task 3.4: policy_assignments 라우터

**Files:**
- Modify: `app/modules/infra/routers/policy_assignments.py`

- [ ] **Step 1: `GET /api/v1/projects/{project_id}/policy-assignments` → `GET /api/v1/policy-assignments?customer_id=N`**
- [ ] **Step 2: `POST` 동일 변경**
- [ ] **Step 3: 커밋**

---

### Task 3.5: asset_relations + projects 라우터

**Files:**
- Modify: `app/modules/infra/routers/asset_relations.py`
- Modify: `app/modules/infra/routers/projects.py`

- [ ] **Step 1: asset_relations — `GET /api/v1/projects/{id}/asset-relations` → `GET /api/v1/asset-relations?customer_id=N`**
- [ ] **Step 2: projects — `GET /api/v1/projects`에 `customer_id` 옵션 파라미터 추가**
- [ ] **Step 3: 커밋**

---

## Phase 4: topbar 셀렉터 + subnav 재구성

### Task 4.1: topbar 고객사/프로젝트 셀렉터

**Files:**
- Modify: `app/templates/base.html:29-74` (topbar)
- Modify: `app/static/js/utils.js`
- Modify: `app/static/css/base.css`

- [ ] **Step 1: topbar HTML 변경**

제목 오른쪽에 고객사/프로젝트 셀렉터 추가:
```html
<span class="mock-logo">프로젝트관리</span>
{% if "infra" in enabled_modules and mc == "infra" %}
<span class="topbar-sep"></span>
<div class="ctx-selector">
  <label class="ctx-label">고객사</label>
  <select id="ctx-customer"></select>
</div>
<div class="ctx-selector">
  <label class="ctx-label">프로젝트</label>
  <select id="ctx-project"><option value="">전체</option></select>
</div>
{% endif %}
```

모듈전환 버튼을 우측으로 이동.
기존 `pinned-project-badge` 제거.

- [ ] **Step 2: utils.js — Pin 함수 교체**

`getPinnedProjectId()` → `getPinnedCustomerId()`, `getLastProjectId()` 로 교체.
`setPinnedProject()` → `setPinnedCustomer()`, `setLastProject()` 로 교체.
기존 `refreshPinnedBadge()` 제거.

새 함수: `initContextSelectors()` — 고객사 목록 로드, 셀렉터 이벤트 바인딩, UserPreference 복원.

- [ ] **Step 3: base.css — 셀렉터 스타일**

```css
.ctx-selector { display: flex; align-items: center; gap: 4px; }
.ctx-label { font-size: 10px; color: var(--text-color-tertiary); }
.ctx-selector select { ... }
.topbar-sep { width: 1px; height: 20px; background: var(--border-color); margin: 0 8px; }
```

- [ ] **Step 4: 커밋**

---

### Task 4.2: subnav 메뉴 재구성

**Files:**
- Modify: `app/templates/base.html:78-126` (subnav)

- [ ] **Step 1: 인프라 메뉴 항목을 9개로 재구성**

```html
{% if "infra" in enabled_modules and mc == "infra" %}
<li><a href="/projects"><i class="icon" data-lucide="folder-kanban"></i><span>프로젝트</span></a></li>
<li><a href="/assets"><i class="icon" data-lucide="server"></i><span>자산</span></a></li>
<li><a href="/ip-inventory"><i class="icon" data-lucide="network"></i><span>IP인벤토리</span></a></li>
<li><a href="/port-maps"><i class="icon" data-lucide="cable"></i><span>포트맵</span></a></li>
<li><a href="/policy-definitions"><i class="icon" data-lucide="shield-check"></i><span>정책정의</span></a></li>
<li><a href="/policies"><i class="icon" data-lucide="shield-alert"></i><span>적용현황</span></a></li>
<li><a href="/contacts"><i class="icon" data-lucide="users"></i><span>담당자</span></a></li>
<li><a href="/audit-history"><i class="icon" data-lucide="history"></i><span>이력</span></a></li>
<li><a href="/infra-dashboard"><i class="icon" data-lucide="monitor-check"></i><span>현황판</span></a></li>
{% endif %}
```

자산 검색(`/inventory/assets`), Import(`/infra-import`) 메뉴 제거.
subnav-sub 설명은 스크롤 시 숨겨지므로 제거 가능 (공간 절약).

- [ ] **Step 2: standalone 모듈 subnav도 동일 적용**

- [ ] **Step 3: 커밋**

---

## Phase 5: 자산 페이지 (그리드 + 하단 상세)

### Task 5.1: 자산 페이지 레이아웃 변경

**Files:**
- Modify: `app/modules/infra/templates/infra_assets.html`
- Modify: `app/static/js/infra_assets.js`
- Modify: `app/static/css/components.css`

- [ ] **Step 1: HTML — 그리드 + 하단 확장 패널 구조**

기존 그리드 아래에 상세 패널 추가:
```html
<div id="asset-detail-panel" class="detail-panel hidden">
  <div class="detail-header">
    <span id="detail-asset-name"></span>
    <div><button class="btn btn-sm" id="btn-edit-asset">수정</button>
    <button class="btn btn-sm btn-danger" id="btn-delete-asset">삭제</button></div>
  </div>
  <div class="detail-tabs">
    <button class="tab-btn active" data-dtab="basic">기본 정보</button>
    <button class="tab-btn" data-dtab="location">설치 위치</button>
    <button class="tab-btn" data-dtab="network">네트워크</button>
    <button class="tab-btn" data-dtab="hw">HW 사양</button>
    <button class="tab-btn" data-dtab="mgmt">자산 관리</button>
    <button class="tab-btn" data-dtab="relations">관계</button>
  </div>
  <div id="detail-content"></div>
</div>
```

toolbar에 `☐ 선택 프로젝트만` 체크박스, Import 버튼 추가.

- [ ] **Step 2: JS — 행 클릭 시 하단 상세 표시 + API customer_id 전환**

`apiFetch('/api/v1/assets?customer_id=' + CUSTOMER_ID)` 로 변경.
행 클릭 → `showAssetDetail(assetData)` → 하단 패널 표시, 탭별 필드 그룹 렌더링.
프로젝트 필터 체크박스 → `project_id` 파라미터 추가/제거 후 재조회.

- [ ] **Step 3: CSS — 상세 패널 스타일**

```css
.detail-panel { border-top: 2px solid var(--primary-color); padding: 16px; background: var(--surface-color); }
.detail-panel.hidden { display: none; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.detail-tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border-color); }
```

- [ ] **Step 4: 커밋**

---

## Phase 6: IP 인벤토리 페이지 (좌우 분할)

### Task 6.1: IP 인벤토리 레이아웃 변경

**Files:**
- Modify: `app/modules/infra/templates/infra_ip_inventory.html`
- Modify: `app/static/js/infra_ip_inventory.js`

- [ ] **Step 1: HTML — 좌우 분할 구조**

```html
<div class="split-layout">
  <div class="split-left" id="subnet-list-panel">
    <div class="panel-header"><h3>서브넷</h3><button class="btn btn-sm" id="btn-add-subnet">+ 대역 추가</button></div>
    <div id="subnet-list"></div>
  </div>
  <div class="split-right">
    <div id="subnet-detail-card" class="card mb-md hidden">
      <!-- 서브넷 상세: 명칭, 대역, GW, VLAN, 역할, 존, 설명 -->
    </div>
    <div class="panel-header"><h3>IP 할당</h3></div>
    <div id="grid-ips" class="ag-theme-quartz" style="height:400px;"></div>
  </div>
</div>
```

- [ ] **Step 2: JS — 서브넷 목록 로드 + 클릭 시 상세/IP 필터**

`apiFetch('/api/v1/ip-subnets?customer_id=' + CUSTOMER_ID)` → 왼쪽 리스트 렌더.
서브넷 클릭 → 상단에 상세 카드 표시, 하단 IP 그리드를 해당 subnet_id로 필터.
"전체" 선택 → 모든 IP 표시.

- [ ] **Step 3: CSS — 분할 레이아웃 스타일**

```css
.split-layout { display: flex; gap: 16px; min-height: 500px; }
.split-left { width: 280px; flex-shrink: 0; }
.split-right { flex: 1; min-width: 0; }
```

- [ ] **Step 4: 커밋**

---

## Phase 7: 나머지 페이지

### Task 7.1: 포트맵 페이지

**Files:**
- Modify: `app/modules/infra/templates/infra_port_maps.html`
- Modify: `app/static/js/infra_port_maps.js`

- [ ] **Step 1: API 호출을 customer_id 기준으로 변경 + 프로젝트 필터 체크박스 추가**
- [ ] **Step 2: 커밋**

---

### Task 7.2: 정책 정의 + 적용 현황 페이지

**Files:**
- Modify: `app/modules/infra/templates/infra_policy_definitions.html`
- Modify: `app/static/js/infra_policy_definitions.js`
- Modify: `app/modules/infra/templates/infra_policies.html`
- Modify: `app/static/js/infra_policies.js` (없으면 생성)

- [ ] **Step 1: 정책 정의 — 전역 목록 + 고객사 적용 정책 강조**
- [ ] **Step 2: 적용 현황 — customer_id 기준 + 프로젝트 필터**
- [ ] **Step 3: 커밋**

---

### Task 7.3: 프로젝트 목록 + 상세 페이지

**Files:**
- Modify: `app/static/js/infra_projects.js`
- Modify: `app/static/js/infra_project_detail.js`

- [ ] **Step 1: 프로젝트 목록 — customer_id 기준 필터링. Pin redirect 로직 제거**
- [ ] **Step 2: 프로젝트 상세 — 자산/IP/포트맵 탭을 ProjectAsset 기반 필터로 변경**
- [ ] **Step 3: 커밋**

---

### Task 7.4: 담당자/업체 + 변경이력 + 현황판 페이지

**Files:**
- Modify: 해당 템플릿 + JS 파일

- [ ] **Step 1: 담당자/업체 — customer_id 기준 거래처/담당자 표시**
- [ ] **Step 2: 변경이력 — customer_id 기준 감사 로그 조회**
- [ ] **Step 3: 현황판 — customer_id 기준 요약 통계**
- [ ] **Step 4: 커밋**

---

## Phase 8: Excel Import/Export + 테스트 + 문서

### Task 8.1: Excel Import/Export 전환

**Files:**
- Modify: `app/modules/infra/services/infra_importer.py`
- Modify: `app/modules/infra/services/infra_exporter.py`
- Modify: `app/modules/infra/routers/infra_excel.py`

- [ ] **Step 1: importer — `parse_inventory_sheet(file_bytes, project_id)` → `(file_bytes, customer_id)`**
- [ ] **Step 2: exporter — 프로젝트 단위 → 고객사 단위 (옵션 프로젝트 필터)**
- [ ] **Step 3: 라우터 — 엔드포인트 파라미터 변경**
- [ ] **Step 4: 커밋**

---

### Task 8.2: 테스트 업데이트

**Files:**
- Modify: `tests/conftest.py` — fixture에 `sample_customer` 추가, `sample_asset`에서 `project_id` → `customer_id`
- Modify: `tests/infra/test_infra_importer.py`
- Create: `tests/infra/test_customer_centric.py` — customer scope CRUD E2E 테스트

- [ ] **Step 1: conftest fixture 업데이트**
- [ ] **Step 2: 기존 인프라 테스트 — project_id → customer_id 참조 수정**
- [ ] **Step 3: 신규 테스트 — customer scope 조회/프로젝트 필터/PortMap nullable 처리 검증**
- [ ] **Step 4: 전체 테스트 실행 확인**

```bash
pytest tests/infra/ -v
```

- [ ] **Step 5: 커밋**

---

### Task 8.3: 문서 갱신

**Files:**
- Modify: `CLAUDE.md` SS6 — Asset 소유 규칙, 자산명 유일성 규칙 변경
- Modify: `docs/guidelines/excel.md` — Import/Export customer_id 기준
- Modify: `docs/KNOWN_ISSUES.md` — 해소된 항목 삭제
- Modify: `docs/PROJECT_STRUCTURE.md` — 파일 구조 갱신

- [ ] **Step 1: CLAUDE.md SS6 인프라모듈 데이터 원칙 업데이트**

"기존 `Asset.project_id` FK는 병행 유지" → "Asset은 `customer_id`로 고객사에 귀속되며, 프로젝트와는 `ProjectAsset` N:M으로만 연결한다."

"자산명은 프로젝트 내 unique" → "자산명은 고객사 내 unique"

Pin 프로젝트 → Pin 고객사 규칙 갱신.

- [ ] **Step 2: 기타 문서 갱신**
- [ ] **Step 3: 커밋**

---

## 요약: 신규/변경 파일 목록

| 유형 | 파일 수 | 핵심 변경 |
|------|---------|----------|
| Migration | 1 신규 | 0005: customer_id 추가, 백필, project_id 제거 |
| Models | 5 수정 | FK 교체 (project_id → customer_id) |
| Schemas | 5 수정 | DTO의 project_id → customer_id |
| Services | 8 수정 | 쿼리 필터, 검증 함수, 헬퍼 |
| Routers | 7 수정 | 엔드포인트 경로/파라미터 |
| Templates | 10 수정 | topbar, subnav, 페이지 레이아웃 |
| JavaScript | 10 수정 | API 호출, 셀렉터, 필터 UI |
| CSS | 2 수정 | topbar 셀렉터, 상세 패널, 분할 레이아웃 |
| Tests | 3 수정/생성 | fixture, 기존 테스트, E2E 신규 |
| Docs | 4 수정 | CLAUDE.md, excel.md, KNOWN_ISSUES, PROJECT_STRUCTURE |
