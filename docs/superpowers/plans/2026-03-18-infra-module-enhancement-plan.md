# 인프라모듈 고도화 구현 계획

> ??????? ??? ?? `docs/guidelines/agent_workflow.md`? ??? `docs/agents/*.md`? ???? ??? ???. ? ??? ????? ?? ?????.

**Goal:** 인프라모듈을 실무 업무 플로우에 맞게 고도화 — ProjectContractLink, 프로젝트 상세 탭 구조, 인벤토리 횡단 조회, 현황판, Excel Import/Export 구현.

**Architecture:** 기존 CRUD 기반 인프라모듈 위에 계층 추가. ProjectContractLink(common 소유)로 영업-인프라 연결. 프로젝트 상세 화면을 탭 구조로 고도화. 현황판은 집계 서비스 기반. Excel Import는 회계모듈 importer 패턴 차용.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Jinja2, HTMX, AG Grid Community, openpyxl, pytest

**Spec:** `docs/superpowers/specs/2026-03-18-infra-module-enhancement-design.md`

---

## 검증 루핑 탈출 프로토콜

> **모든 에이전트와 리뷰어에게 적용되는 필수 규칙.**

1. **동일 오류로 2회 연속 실패하면 즉시 중단**한다. 3번째 시도를 하지 않는다.
2. 중단 시 다음을 보고한다:
   - 실패 원인 (오류 메시지, 재현 조건)
   - 시도한 접근 방식 2가지
   - 원인 추정 (환경 문제 / 설계 결함 / 범위 과대)
3. **범위 축소 제안**을 포함한다:
   - 실패 부분을 placeholder/stub으로 대체하는 방안
   - Task를 더 작은 단위로 쪼개는 방안
   - 해당 Task를 후속 작업으로 미루는 방안
4. 사용자 승인 없이 재시도하지 않는다.
5. 리뷰 루프도 동일: spec reviewer나 code reviewer가 **같은 지적을 2회 반복**하면 해당 이슈를 사용자에게 에스컬레이션한다.

## 최적화 원칙

- **변경이력 탭**: 감사 로그 연동이 미완료 상태이므로 placeholder로 구현. "감사 로그 연동 후 활성화" 메시지 표시.
- **Excel Import**: 자산(01. Inventory)만 이번 범위. 나머지 시트(포트맵/IP/보안요건)는 후속 Phase.
- **프로젝트 상세 탭**: 기존 infra_*.js를 최대한 재활용. 전면 재작성 아닌 탭 래핑.
- **횡단 검색**: 자산 검색 1개만 먼저 구현, IP/포트맵은 동일 패턴 복제로 후속.

---

## Phase 1: 기반 작업

### Task 1: ProjectContractLink 모델

**Files:**
- Create: `app/modules/common/models/project_contract_link.py`
- Modify: `app/modules/common/models/__init__.py`
- Create: `app/modules/common/schemas/project_contract_link.py`
- Create: `app/modules/common/services/project_contract_link.py`
- Create: `app/modules/common/routers/project_contract_links.py`
- Modify: `app/modules/common/routers/__init__.py`
- Create: `tests/common/test_project_contract_link.py`

- [ ] **Step 1: 모델 생성**

`app/modules/common/models/project_contract_link.py`:

```python
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import Base, TimestampMixin


class ProjectContractLink(TimestampMixin, Base):
    __tablename__ = "project_contract_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    contract_id: Mapped[int] = mapped_column(Integer, ForeignKey("contracts.id"), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "contract_id"),)
```

`app/modules/common/models/__init__.py`에 import 추가.

- [ ] **Step 2: 스키마 생성**

Create/Update/Read 스키마. Read에는 project_name, contract_code 조인 필드 포함 (서비스에서 조회 시 enrichment).

- [ ] **Step 3: 서비스 생성**

`project_contract_link.py`: `link_project_contract()`, `unlink()`, `list_by_project()`, `list_by_contract()`. admin 권한 체크.

- [ ] **Step 4: 라우터 생성**

```
POST   /api/v1/project-contract-links         — 연결 생성
DELETE /api/v1/project-contract-links/{id}     — 연결 해제
GET    /api/v1/project-contract-links?project_id=N  — 프로젝트별 조회
GET    /api/v1/project-contract-links?contract_id=N — 계약별 조회
```

`app/modules/common/routers/__init__.py`에 등록.

- [ ] **Step 5: 테스트 작성**

`tests/common/test_project_contract_link.py`: 연결 생성, 중복 방지, 삭제, 프로젝트별/계약별 조회.

- [ ] **Step 6: 커밋**

```bash
git add -A && git commit -m "feat: add ProjectContractLink model and API"
```

---

### Task 2: AuditLog module 필드 추가

**Files:**
- Modify: `app/modules/common/models/audit_log.py`
- Modify: `app/modules/common/services/audit.py`

- [ ] **Step 1: AuditLog 모델에 module 필드 추가**

```python
module: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
# "common", "accounting", "infra"
```

- [ ] **Step 2: audit.log() 함수에 module 파라미터 추가**

```python
def log(db, *, user_id, action, entity_type, entity_id=None, summary=None, detail=None, module=None):
    entry = AuditLog(
        user_id=user_id, action=action, entity_type=entity_type,
        entity_id=entity_id, summary=summary, detail=detail, module=module,
    )
    db.add(entry)
    db.flush()
```

기존 호출처는 module=None으로 동작 (하위 호환).

- [ ] **Step 3: 커밋**

```bash
git add -A && git commit -m "feat: add module field to AuditLog for module-scoped filtering"
```

---

### Task 3: 네비게이션 메뉴 그룹 분리

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/static/css/base.css` (또는 `components.css`)

- [ ] **Step 1: base.html 네비게이션을 그룹 헤더로 분리**

```html
<!-- 공통 -->
<li class="nav-group-header">공통</li>
<li><a href="/customers">거래처</a></li>

<!-- 영업관리 -->
{% if "accounting" in enabled_modules %}
<li class="nav-group-header">영업관리</li>
<li><a href="/my-contracts">내 사업</a></li>
<li><a href="/contracts">사업관리</a></li>
<li><a href="/dashboard">대시보드</a></li>
<li><a href="/reports">보고서</a></li>
{% endif %}

<!-- 프로젝트관리 -->
{% if "infra" in enabled_modules %}
<li class="nav-group-header">프로젝트관리</li>
<li><a href="/projects">프로젝트</a></li>
<li><a href="/assets">자산</a></li>
<li><a href="/ip-inventory">IP인벤토리</a></li>
<li><a href="/port-maps">포트맵</a></li>
<li><a href="/policies">정책</a></li>
<li><a href="/infra-dashboard">현황판</a></li>
{% endif %}

<!-- 관리 -->
<li class="nav-group-header">관리</li>
<li><a href="/users">사용자</a></li>
<li><a href="/system">시스템설정</a></li>
```

- [ ] **Step 2: nav-group-header CSS 스타일 추가**

```css
.nav-group-header {
  font-size: 0.7rem;
  text-transform: uppercase;
  color: var(--text-muted);
  padding: 1rem 1rem 0.25rem;
  letter-spacing: 0.05em;
  pointer-events: none;
}
```

- [ ] **Step 3: 네비게이션 href 수정**

현재 base.html에 `/ip-subnets`로 잘못된 링크가 있음 → `/ip-inventory`로 수정.
`/assets` 링크도 실제 pages.py 라우트와 일치하는지 확인.

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: group navigation by module with visual separators"
```

---

### Task 4: Alembic migration (Phase 1)

**Files:**
- Create: `alembic/versions/0002_add_project_contract_link_and_audit_module.py`

- [ ] **Step 1: migration 생성**

project_contract_links 테이블 생성 + audit_logs.module 컬럼 추가.
idempotent (inspector 체크).

- [ ] **Step 2: Docker에서 migration 적용 확인**

```bash
docker compose exec app alembic upgrade head
```

- [ ] **Step 3: 커밋**

```bash
git add -A && git commit -m "migration: add project_contract_links table and audit_log.module column"
```

---

## Phase 2a: 프로젝트 상세 — 탭 구조 + 개요

### Task 5: 프로젝트 상세 — 탭 껍데기 + 개요 탭

**Files:**
- Modify: `app/modules/infra/templates/infra_project_detail.html`
- Modify: `app/static/js/infra_project_detail.js`
- Modify: `app/static/css/infra_common.css` (탭 스타일)

이 Task는 탭 구조의 **껍데기**와 **개요 탭만** 구현한다. 다른 탭은 placeholder로 남긴다.

- [ ] **Step 1: 현재 infra_project_detail.html/js 읽기**

기존 구조와 데이터 바인딩 패턴을 이해한다.

- [ ] **Step 2: 탭 네비게이션 HTML + CSS 작성**

```html
<div class="tab-nav">
  <button class="tab-btn active" data-tab="overview">개요</button>
  <button class="tab-btn" data-tab="assets">자산</button>
  <button class="tab-btn" data-tab="ip">IP/네트워크</button>
  <button class="tab-btn" data-tab="portmap">포트맵</button>
  <button class="tab-btn" data-tab="policy">정책</button>
  <button class="tab-btn" data-tab="contacts">담당자/업체</button>
  <button class="tab-btn" data-tab="history">변경이력</button>
</div>

<div class="tab-content" id="tab-overview"><!-- 개요 구현 --></div>
<div class="tab-content hidden" id="tab-assets"><p class="placeholder">자산 탭 (Phase 2b에서 구현)</p></div>
<div class="tab-content hidden" id="tab-ip"><p class="placeholder">IP 탭 (Phase 2b에서 구현)</p></div>
<div class="tab-content hidden" id="tab-portmap"><p class="placeholder">포트맵 탭 (Phase 2b에서 구현)</p></div>
<div class="tab-content hidden" id="tab-policy"><p class="placeholder">정책 탭 (Phase 2c에서 구현)</p></div>
<div class="tab-content hidden" id="tab-contacts"><p class="placeholder">담당자 탭 (Phase 2c에서 구현)</p></div>
<div class="tab-content hidden" id="tab-history"><p class="placeholder">변경이력 (감사 로그 연동 후 활성화)</p></div>
```

탭 전환 JS:

```javascript
function activateTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.remove('hidden');
}
```

- [ ] **Step 3: 개요 탭에 기존 단계/산출물 UI 이동**

기존 infra_project_detail의 단계/산출물 관리 UI를 `tab-overview` 안으로 감싼다. 기존 JS 로직은 최대한 보존.

- [ ] **Step 4: CSS 탭 스타일 추가**

projmgr의 기존 CSS 패턴(pill-tabs 등)을 참고하여 `infra_common.css`에 탭 스타일 추가.

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: project detail tabbed layout with overview tab"
```

---

### Task 6: 개요 탭 — 단계 추적 및 산출물 체크 강화

**Files:**
- Modify: `app/modules/infra/templates/infra_project_detail.html`
- Modify: `app/static/js/infra_project_detail.js`
- Modify: `app/modules/infra/services/phase_service.py` (필요 시)

- [ ] **Step 1: 단계 진행 시각화 구현**

```html
<div class="phase-timeline">
  <!-- JS로 동적 생성 -->
  <!-- 각 단계: ● 완료 / ◐ 진행중 / ○ 미시작 -->
</div>
```

API: `GET /api/v1/projects/{id}/phases` → 단계 목록 + status 기반 렌더링.

- [ ] **Step 2: 산출물 체크리스트 UI**

각 단계 클릭/펼침 시 산출물 목록 표시. 체크박스로 제출 상태 토글:

```javascript
async function toggleDeliverable(deliverableId, isSubmitted) {
  await apiFetch(`/api/v1/project-deliverables/${deliverableId}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_submitted: isSubmitted, submitted_at: isSubmitted ? new Date().toISOString() : null }),
  });
  loadPhases(); // refresh
}
```

- [ ] **Step 3: 요약 카드 구현**

프로젝트 상세 로드 시 집계 API 호출:
- 자산 수: `GET /api/v1/assets?project_id=N` → count
- IP 할당: `GET /api/v1/asset-ips?project_id=N` → count / 전체 subnet IP 수
- 정책 준수율: 신규 집계 API 필요 (아래 Task 7에서 구현)
- 산출물: phases에서 계산

- [ ] **Step 4: 연결된 계약 섹션 (양쪽 모듈 활성 시)**

```javascript
// enabled_modules에 "accounting"이 포함된 경우에만 표시
if (enabledModules.includes('accounting')) {
  loadLinkedContracts(projectId);
}
```

`GET /api/v1/project-contract-links?project_id=N` 호출.
계약 연결/해제 모달.

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: enhance project overview with phase tracking and summary cards"
```

---

## Phase 2b: 프로젝트 상세 — 자산/IP/포트맵 탭

### Task 6.5: 자산/IP/포트맵 탭 구현

**Files:**
- Modify: `app/modules/infra/templates/infra_project_detail.html`
- Modify: `app/static/js/infra_project_detail.js`

기존 `infra_assets.js`, `infra_ip_inventory.js`, `infra_port_maps.js`의 Grid 초기화/로드 함수를 **재활용**한다. 탭 활성화 시 lazy-load.

- [ ] **Step 1: 기존 infra_assets.js에서 Grid 초기화 함수를 export 가능하게 리팩터링**

`loadAssetsGrid(containerId, projectId)` 형태로 파라미터화. 기존 독립 페이지에서의 호출도 유지.

- [ ] **Step 2: 프로젝트 상세의 자산 탭에서 loadAssetsGrid 호출**

```javascript
function activateTab(tabId) {
  // ...기존 탭 전환 로직...
  if (tabId === 'assets' && !window._assetsLoaded) {
    loadAssetsGrid('tab-assets-grid', projectId);
    window._assetsLoaded = true;
  }
}
```

- [ ] **Step 3: IP/포트맵 탭도 동일 패턴으로 구현**

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: assets/IP/portmap tabs in project detail (lazy-load)"
```

---

## Phase 2c: 프로젝트 상세 — 정책/담당자/계약 연결

### Task 6.6: 정책/담당자 탭 + 연결된 계약 섹션

**Files:**
- Modify: `app/modules/infra/templates/infra_project_detail.html`
- Modify: `app/static/js/infra_project_detail.js`

- [ ] **Step 1: 정책 탭 구현**

`infra_policies.js`의 Grid 로직 재활용. 프로젝트 스코프 필터링.

- [ ] **Step 2: 담당자/업체 탭 구현**

AssetContact + Customer/CustomerContact 조회. 프로젝트 범위 자산의 담당자 매핑 표시.

- [ ] **Step 3: 개요 탭에 연결된 계약 섹션 추가 (양쪽 모듈 활성 시만)**

```javascript
if (window.enabledModules?.includes('accounting')) {
  loadLinkedContracts(projectId);
}
```

ProjectContractLink API로 계약 목록 조회, 연결/해제 UI.

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: policy/contacts tabs and linked contracts section"
```

---

## Phase 3: 현황판 + 알림

### Task 7: 집계 API (현황판/요약 카드용)

**Files:**
- Create: `app/modules/infra/services/infra_metrics.py`
- Create: `app/modules/infra/routers/infra_dashboard.py`
- Modify: `app/modules/infra/routers/__init__.py`

- [ ] **Step 1: infra_metrics 서비스 구현**

```python
def get_project_summary(db, project_id) -> dict:
    """프로젝트 요약: 자산 수, IP 할당률, 정책 준수율, 산출물 진행률."""
    ...

def get_all_projects_summary(db) -> list[dict]:
    """전체 프로젝트 요약 목록 (현황판용)."""
    ...

def get_policy_compliance_rate(db, project_id) -> float:
    """정책 준수율 = compliant / (전체 - not_applicable) * 100"""
    ...

def get_unsubmitted_deliverables(db, user=None) -> list[dict]:
    """미제출 산출물 목록 (in_progress 단계의 미제출 건)."""
    ...
```

- [ ] **Step 2: infra_dashboard 라우터 구현**

```
GET /api/v1/infra-dashboard/summary           — 전체 프로젝트 요약
GET /api/v1/infra-dashboard/project/{id}      — 단일 프로젝트 요약
GET /api/v1/infra-dashboard/unsubmitted       — 미제출 산출물
GET /api/v1/infra-dashboard/non-compliant     — 정책 미준수 항목
```

라우터를 `infra/routers/__init__.py`에 등록.

- [ ] **Step 3: 테스트 작성**

`tests/infra/test_infra_metrics.py`: 정책 준수율 계산, 미제출 산출물 조회, 프로젝트 요약 집계.

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: infra metrics service and dashboard API"
```

---

### Task 8: 현황판 페이지

**Files:**
- Create: `app/modules/infra/templates/infra_dashboard.html`
- Create: `app/static/js/infra_dashboard.js`
- Modify: `app/modules/infra/routers/pages.py`

- [ ] **Step 1: 페이지 라우트 추가**

`app/modules/infra/routers/pages.py`에 추가:

```python
@router.get("/infra-dashboard", response_class=HTMLResponse)
def infra_dashboard_page(request: Request) -> HTMLResponse:
    return _templates(request).TemplateResponse("infra_dashboard.html", {"request": request})
```

- [ ] **Step 2: 현황판 HTML 작성**

Spec §3.5 현황판 레이아웃 기반:
- 프로젝트 단계 요약 (분석/설계/구축/안정화 건수)
- 미제출 산출물 알림 영역
- 프로젝트별 요약 Grid (자산/IP할당률/정책준수율/단계)
- 정책 미준수 항목 Grid

- [ ] **Step 3: 현황판 JS 구현**

```javascript
async function loadDashboard() {
  const [summary, unsubmitted, nonCompliant] = await Promise.all([
    apiFetch('/api/v1/infra-dashboard/summary'),
    apiFetch('/api/v1/infra-dashboard/unsubmitted'),
    apiFetch('/api/v1/infra-dashboard/non-compliant'),
  ]);
  renderPhaseSummary(summary);
  renderUnsubmittedAlerts(unsubmitted);
  renderProjectGrid(summary);
  renderNonCompliantGrid(nonCompliant);
}
```

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: infra dashboard (operations status board)"
```

---

### Task 9: 산출물 미제출 로그인 알림

**Files:**
- Modify: `app/core/auth/router.py` (또는 프론트엔드)
- Modify: `app/modules/common/models/user_preference.py` (설정 키 정의)

- [ ] **Step 1: 로그인 응답에 알림 데이터 포함**

`/api/v1/auth/me` 또는 로그인 성공 후 별도 API로 미제출 산출물 수를 반환.

```python
# auth/router.py의 login 응답 또는 별도 endpoint
{
  "must_change_password": false,
  "notifications": {
    "unsubmitted_deliverables": 3  # infra 활성 시에만
  }
}
```

- [ ] **Step 2: 프론트엔드 알림 표시**

로그인 직후 토스트 또는 배너:

```javascript
if (data.notifications?.unsubmitted_deliverables > 0) {
  showToast(`미제출 산출물 ${data.notifications.unsubmitted_deliverables}건이 있습니다.`, 'warning');
}
```

- [ ] **Step 3: UserPreference로 알림 끄기 옵션**

`infra.notify_unsubmitted` 키로 사용자별 제어. 기본값: true.

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: login notification for unsubmitted deliverables"
```

---

## Phase 4: 인벤토리 횡단 조회 + 정책 분리

### Task 10: 자산 횡단 검색 페이지 (자산만 우선)

**Files:**
- Create: `app/modules/infra/templates/infra_inventory_assets.html`
- Create: `app/static/js/infra_inventory_assets.js`
- Modify: `app/modules/infra/routers/pages.py`
- Modify: `app/modules/infra/routers/assets.py` (project_id optional)
- Modify: `app/modules/infra/services/asset_service.py` (project_id optional)
- Modify: `app/templates/base.html` (인벤토리 네비게이션)

자산 검색 1개만 구현. IP/포트맵 횡단 검색은 동일 패턴이므로 Phase 7(후속)에서 복제.

- [ ] **Step 1: assets API의 project_id를 선택적 파라미터로 변경**

`app/modules/infra/routers/assets.py`에서 project_id 필수 → optional. 미지정 시 전체 반환.
서비스 레이어도 함께 수정.

- [ ] **Step 2: 자산 횡단 검색 페이지 구현**

기존 `infra_assets.html`/`infra_assets.js` 패턴을 복제하되:
- 프로젝트 필터 드롭다운 추가
- 고객사 필터 추가
- AG Grid에 프로젝트명 컬럼 추가

- [ ] **Step 3: 페이지 라우트 및 네비게이션 추가**

```python
@router.get("/inventory/assets", response_class=HTMLResponse)
```

네비게이션에 인벤토리 섹션:

```html
<li class="nav-group-header">인벤토리</li>
<li><a href="/inventory/assets">자산 검색</a></li>
<li><a href="/inventory/ips">IP 검색</a></li>       <!-- Phase 7 -->
<li><a href="/inventory/port-maps">포트맵 검색</a></li> <!-- Phase 7 -->
```

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: cross-project asset inventory search"
```

---

### Task 11: 정책 관리 화면 분리

**Files:**
- Create: `app/modules/infra/templates/infra_policy_definitions.html`
- Create: `app/static/js/infra_policy_definitions.js`
- Modify: `app/modules/infra/templates/infra_policies.html` (적용 현황 전용)
- Modify: `app/modules/infra/routers/pages.py`

- [ ] **Step 1: 정책 정의 관리 페이지 분리**

- `/policy-definitions` — PolicyDefinition CRUD (프로젝트 무관, 전사 기준)
- `/policies` — PolicyAssignment 현황 (프로젝트별 준수 상태)

- [ ] **Step 2: 정책 적용 현황 페이지에 프로젝트별 준수율 요약 추가**

infra_metrics의 `get_policy_compliance_rate()` 활용.

- [ ] **Step 3: 네비게이션 업데이트**

```html
<li><a href="/policy-definitions">정책 정의</a></li>
<li><a href="/policies">적용 현황</a></li>
```

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: separate policy definition and compliance status pages"
```

---

## Phase 5: Excel Import (자산만)

### Task 12: 자산 Excel Import

**Files:**
- Create: `app/modules/infra/services/infra_importer.py`
- Create: `app/modules/infra/routers/infra_excel.py`
- Create: `app/modules/infra/schemas/infra_import.py`
- Modify: `app/modules/infra/routers/__init__.py`
- Create: `tests/infra/test_infra_importer.py`

참조: `app/modules/accounting/services/importer.py` (회계모듈 3단계 Import 패턴)
참조: `input/template.xlsx` (실무 템플릿, `01. Inventory` 시트)

- [ ] **Step 1: importer 서비스 구현 — 파싱 단계**

```python
def parse_inventory_sheet(file_bytes: bytes, project_id: int) -> dict:
    """
    01. Inventory 시트를 파싱하여 프리뷰 데이터 반환.

    Returns:
        {
            "rows": [...],       # 파싱된 행 목록
            "errors": [...],     # 검증 오류
            "warnings": [...],   # 경고 (매핑 안 되는 컬럼 등)
            "total": int,
            "valid": int,
        }
    """
```

컬럼 매핑 (Spec §10 참조):
- Row 3이 실제 헤더 (Row 1-2는 그룹 헤더)
- Seq(col 2) → 자동생성, 센터(col 3) → center, 운영구분(col 4) → operation_type, ...
- 35컬럼 전체 매핑

- [ ] **Step 2: importer 서비스 구현 — 저장 단계**

```python
def import_inventory(db: Session, project_id: int, parsed_rows: list[dict], current_user) -> dict:
    """파싱 결과를 DB에 저장. 중복 검증 (asset_name + project_id unique)."""
```

- [ ] **Step 3: Excel 라우터 구현**

```
POST /api/v1/infra-excel/import/preview   — 파일 업로드 + 파싱 결과 반환
POST /api/v1/infra-excel/import/confirm   — 파싱 결과 확정 저장
```

- [ ] **Step 4: 테스트 작성**

`tests/infra/test_infra_importer.py`:
- 정상 파싱 (샘플 데이터)
- 빈 시트 처리
- 중복 자산명 검증
- 필수 필드 누락 경고

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: asset Excel Import from template (01. Inventory sheet)"
```

---

### Task 13: 자산 Import UI

**Files:**
- Create: `app/modules/infra/templates/infra_import.html`
- Create: `app/static/js/infra_import.js`
- Modify: `app/modules/infra/routers/pages.py`

- [ ] **Step 1: Import 페이지 구현**

3단계 Import UI (자산 시트 전용):

1. 파일 업로드 + 프로젝트 선택
2. 파싱 결과 프리뷰 (AG Grid, 오류/경고 강조)
3. 확인 버튼으로 저장

- [ ] **Step 2: 커밋**

```bash
git add -A && git commit -m "feat: asset Excel Import UI"
```

---

## Phase 6: 영업모듈 연결 + 정리

### Task 14: Alembic migration (전체 변경분)

- [ ] **Step 1: Phase 1-5에서 추가/변경된 모델의 migration 생성**

project_contract_links 테이블, audit_logs.module 컬럼 등.

- [ ] **Step 2: Docker 환경에서 migration 적용 확인**

```bash
docker compose exec app alembic upgrade head
```

- [ ] **Step 3: 커밋**

```bash
git add -A && git commit -m "migration: infra enhancement schema updates"
```

---

### Task 15: 영업모듈 — 연결된 프로젝트 섹션

**Files:**
- Modify: `app/static/js/contract_detail.js`
- Modify: `app/modules/accounting/templates/` (해당 템플릿)

- [ ] **Step 1: 사업 상세 페이지에 "연결된 프로젝트" 섹션 추가**

인프라모듈 활성 시에만 표시. ProjectContractLink API 활용.

```javascript
if (enabledModules.includes('infra')) {
  loadLinkedProjects(contractId);
}
```

- [ ] **Step 2: 커밋**

```bash
git add -A && git commit -m "feat: show linked projects in contract detail page"
```

---

### Task 16: 문서 업데이트 및 최종 검증

**Files:**
- Modify: `docs/PROJECT_STRUCTURE.md`
- Modify: `docs/KNOWN_ISSUES.md`

- [ ] **Step 1: PROJECT_STRUCTURE.md 업데이트**

신규 파일 반영.

- [ ] **Step 2: KNOWN_ISSUES.md 업데이트**

해결된 항목 제거, 신규 이슈 추가.

- [ ] **Step 3: Docker 전체 기동 테스트**

```bash
docker compose up --build -d
# 전체 페이지 접근 확인
```

- [ ] **Step 4: 커밋 및 태그**

```bash
git add -A && git commit -m "docs: update documentation after infra enhancement"
git tag infra-enhancement-v1
```

---

## 후속 Phase (이번 계획 범위 외, 별도 계획 수립)

| Phase | 내용 |
|-------|------|
| Phase 7 | IP/포트맵 횡단 검색 (Task 10 자산 검색 패턴 복제) |
| Phase 8 | Excel Import 확장 — 네트워크 대역(05시트), IP마스터(98시트), 포트맵(03시트), 보안요건(Security_Requirement시트) |
| Phase 9 | Excel Export — 프로젝트 단위 템플릿 형식 다운로드 |
| Phase 10 | 감사 로그 서비스 연동 — CRUD 호출처에 audit.log() 추가, 변경이력 탭 활성화 |
