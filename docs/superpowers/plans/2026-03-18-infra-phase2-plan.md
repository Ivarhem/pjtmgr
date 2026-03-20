# 인프라모듈 고도화 Phase 2 — 통합 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin 프로젝트, Asset 전역화, 프로젝트-거래처 연결, 자산 간 관계, Excel Export, 감사 로그 연동을 점진적으로 구현.

**Architecture:** 기존 인프라모듈 위에 신규 테이블(project_asset, asset_relation, project_customer, project_customer_contact)을 추가. Pin 프로젝트는 UserPreference 기반 DB 저장, topbar에 표시, 인프라 전 페이지에서 기본 컨텍스트로 활용. 기존 Asset.project_id FK는 유지한 채 병행 운영.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Jinja2, HTMX, AG Grid Community, openpyxl, pytest

**Spec:** `docs/superpowers/specs/2026-03-18-infra-module-enhancement-design.md`
**이전 계획:** `docs/superpowers/plans/2026-03-18-infra-module-enhancement-plan.md` (Phase 1-6 완료)

---

## 검증 루핑 탈출 프로토콜

> **모든 에이전트와 리뷰어에게 적용되는 필수 규칙.**

1. **동일 오류로 2회 연속 실패하면 즉시 중단**한다. 3번째 시도를 하지 않는다.
2. 중단 시 실패 원인, 시도한 접근 방식 2가지, 원인 추정을 보고한다.
3. **범위 축소 제안**을 포함한다.
4. 사용자 승인 없이 재시도하지 않는다.

---

## 전체 Phase 구성

| Phase | 내용 | 의존성 | 상태 |
|-------|------|--------|------|
| A | Asset 구조 정비 (project_asset, asset_code, asset_relation) | 없음 | **완료** |
| A+ | Pin 프로젝트 (DB 기반 고정 프로젝트 + 전 페이지 연동) | 없음 | 미착수 |
| B | 프로젝트-거래처 연결 (ProjectCustomer, ProjectCustomerContact) | 없음 | 미착수 |
| C | Excel Export (프로젝트 단위 다운로드) | 없음 | 미착수 |
| D | 감사 로그 연동 + 변경이력 탭 활성화 | 없음 | 미착수 |
| E | 마이그레이션 통합 확인 + 문서 | A+~D 후 | 미착수 |

권장 순서: A(완료) → **A+** → B → C → D → E

---

## Phase A: Asset 구조 정비 ✅ 완료

- Task A1: `project_assets` N:M 연결 테이블 (모델/스키마/서비스/라우터/테스트)
- Task A2: `assets.asset_code` 컬럼 추가 (nullable unique)
- Task A3: `asset_relations` 테이블 (모델/스키마/서비스/라우터/테스트)
- Task A4: Alembic migration `0003` (백필 포함)
- Task A5: 프로젝트 상세 UI 자산 관계 표시 → Phase B와 통합 진행

---

## Phase A+: Pin 프로젝트

### 설계 개요

사용자가 "작업 중인 프로젝트"를 DB에 고정. 인프라모듈 전 페이지에서 해당 프로젝트가 기본 컨텍스트로 동작.

**저장**: `UserPreference` 테이블 (key=`infra.pinned_project_id`, value=프로젝트 ID)
**표시**: topbar에 "📌 PRJ-001 — 프로젝트명" 뱃지 (infra 컨텍스트일 때만)
**동작**: Import, 필터, 포트맵 등에서 pin된 프로젝트가 기본 선택

**네비게이션 동작 변경:**
- 사이드바 "프로젝트" 메뉴 클릭 → Pin된 프로젝트가 있으면 **프로젝트 상세 페이지로 직행**
- Pin이 없으면 기존대로 프로젝트 목록 페이지로 이동
- 프로젝트 상세 페이지에 "← 프로젝트 목록" 버튼으로 목록 페이지 접근 가능
- 프로젝트 목록에서 다른 프로젝트를 Pin하면 해당 프로젝트 상세로 자동 이동

구현 방식: `/projects` 라우트를 서버사이드에서 분기하지 않고, **JS에서 pin 여부 확인 후 redirect**. 이유: UserPreference는 사용자별이므로 서버 라우트에서 처리하면 매 요청마다 DB 조회가 필요. JS redirect가 더 가벼움.

### Task A+1: Pin 프로젝트 API + topbar 표시

**Files:**
- Modify: `app/templates/base.html` (topbar에 pin 뱃지 영역 추가)
- Modify: `app/static/js/utils.js` (pin 관련 유틸 함수)

- [ ] **Step 1: topbar에 pin 프로젝트 뱃지 추가**

`base.html` topbar-right 영역에 pin 표시 영역 추가:

```html
{% if "infra" in enabled_modules %}
<span id="pinned-project-badge" class="pinned-badge" style="display:none;"></span>
{% endif %}
```

- [ ] **Step 2: utils.js에 pin 관련 함수 추가**

```javascript
// Pin 프로젝트 로드/저장/해제
async function getPinnedProjectId() { ... }
async function setPinnedProject(projectId) { ... }
async function clearPinnedProject() { ... }
function updatePinnedBadge(projectCode, projectName) { ... }
```

기존 `/api/v1/preferences/{key}` API를 활용. key=`infra.pinned_project_id`.

- [ ] **Step 3: base.html 초기화 시 pin 뱃지 렌더링**

로그인 후 `/api/v1/preferences/infra.pinned_project_id` 조회 → 값이 있으면 프로젝트 정보 조회 → topbar 뱃지 표시.

- [ ] **Step 4: CSS 스타일**

`infra_common.css`에 `.pinned-badge` 스타일 추가.

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: pinned project badge in topbar with DB persistence"
```

---

### Task A+2: 프로젝트 목록 — Pin 버튼 + Pin 시 상세 이동

**Files:**
- Modify: `app/static/js/infra_projects.js`
- Modify: `app/modules/infra/templates/infra_projects.html`

- [ ] **Step 1: 프로젝트 목록 페이지 로드 시 pin 확인 → redirect**

`infra_projects.js` DOMContentLoaded에서:
```javascript
// /projects 진입 시 pin된 프로젝트가 있으면 상세로 바로 이동
// 단, URL에 ?list=1 파라미터가 있으면 목록 유지 (← 프로젝트목록 버튼용)
if (!new URLSearchParams(location.search).has('list')) {
  const pinnedId = await getPinnedProjectId();
  if (pinnedId) { location.href = '/projects/' + pinnedId; return; }
}
```

- [ ] **Step 2: 프로젝트 Grid에 Pin 버튼 컬럼 추가**

AG Grid 액션 컬럼에 📌 버튼. 클릭 시:
1. `setPinnedProject(projectId)` 호출
2. topbar 뱃지 갱신
3. **해당 프로젝트 상세 페이지로 이동** (`location.href = '/projects/' + projectId`)

현재 pin된 프로젝트 행은 강조 표시.

- [ ] **Step 3: 커밋**

```bash
git add -A && git commit -m "feat: pin project with auto-navigate to detail page"
```

---

### Task A+3: 인프라 페이지들에 Pin 프로젝트 연동

**Files:**
- Modify: `app/static/js/infra_inventory_assets.js`
- Modify: `app/static/js/infra_ip_inventory.js`
- Modify: `app/static/js/infra_port_maps.js`
- Modify: `app/static/js/infra_project_detail.js`
- Modify: `app/modules/infra/templates/infra_project_detail.html`

- [ ] **Step 1: 프로젝트 상세 — "← 프로젝트 목록" 버튼 + 자동 Pin**

`infra_project_detail.html` 상단에 "← 프로젝트 목록" 링크 추가 (href="/projects?list=1").
`infra_project_detail.js` 로드 시 `setPinnedProject(PROJECT_ID)` 자동 호출.

- [ ] **Step 2: 자산 검색 페이지 — pin 프로젝트 기본 선택**

페이지 로드 시 `getPinnedProjectId()` → 프로젝트 드롭다운 기본값 설정 + Import 패널 프로젝트 자동 채움.

- [ ] **Step 3: IP 인벤토리 페이지 — Import 패널 프로젝트 자동 채움**

Import 토글 시 pin된 프로젝트가 기본 선택.

- [ ] **Step 4: 포트맵 페이지 — 프로젝트 필터 기본값**

페이지 로드 시 pin된 프로젝트로 자동 필터링 + Import 프로젝트 자동 채움.

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: auto-select pinned project across all infra pages"
```

---

## Phase B: 프로젝트-거래처 연결

### Task B1: ProjectCustomer 모델

**목표:** 프로젝트별 업체 역할(고객사/수행사/유지보수사/통신사) 관리.

**Files:**
- Create: `app/modules/infra/models/project_customer.py`
- Modify: `app/modules/infra/models/__init__.py`
- Create: `app/modules/infra/schemas/project_customer.py`
- Create: `app/modules/infra/services/project_customer_service.py`
- Create: `app/modules/infra/routers/project_customers.py`
- Modify: `app/modules/infra/routers/__init__.py`
- Create: `tests/infra/test_project_customer_service.py`

- [ ] **Step 1: 모델 생성**

```python
class ProjectCustomer(TimestampMixin, Base):
    __tablename__ = "project_customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    # role: "고객사" | "수행사" | "유지보수사" | "통신사" | "벤더"
    scope_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("project_id", "customer_id", "role"),)
```

- [ ] **Step 2: 스키마/서비스/라우터 생성**

```
POST   /api/v1/project-customers                    — 연결 생성
DELETE /api/v1/project-customers/{id}               — 연결 해제
PATCH  /api/v1/project-customers/{id}               — 수정
GET    /api/v1/project-customers?project_id=N       — 프로젝트별 업체 조회
```

Read 스키마에 customer_name, business_no enrichment 포함.

- [ ] **Step 3: 테스트 작성**

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: add ProjectCustomer for project-level vendor role mapping"
```

---

### Task B2: ProjectCustomerContact 모델

**목표:** 프로젝트별 담당자 역할(고객PM, 보안실무, 구축엔지니어 등) 매핑.

**Files:**
- Create: `app/modules/infra/models/project_customer_contact.py`
- Modify: `app/modules/infra/models/__init__.py`
- Create: `app/modules/infra/schemas/project_customer_contact.py`
- Create: `app/modules/infra/services/project_customer_contact_service.py`
- Create: `app/modules/infra/routers/project_customer_contacts.py`
- Modify: `app/modules/infra/routers/__init__.py`
- Create: `tests/infra/test_project_customer_contact_service.py`

- [ ] **Step 1: 모델 생성**

```python
class ProjectCustomerContact(TimestampMixin, Base):
    __tablename__ = "project_customer_contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project_customers.id"), nullable=False, index=True
    )
    contact_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_contacts.id"), nullable=False, index=True
    )
    project_role: Mapped[str] = mapped_column(String(100), nullable=False)
    # "고객PM", "고객실무", "승인자", "수행PM", "구축엔지니어", "유지보수담당", "보안업무담당"
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("project_customer_id", "contact_id", "project_role"),)
```

- [ ] **Step 2: 스키마/서비스/라우터 생성**

```
POST   /api/v1/project-customer-contacts                           — 연결 생성
DELETE /api/v1/project-customer-contacts/{id}                      — 연결 해제
PATCH  /api/v1/project-customer-contacts/{id}                      — 수정
GET    /api/v1/project-customer-contacts?project_customer_id=N     — 업체별 담당자 조회
```

- [ ] **Step 3: 테스트 작성**

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: add ProjectCustomerContact for project-level contact role mapping"
```

---

### Task B3: Alembic migration (Phase B)

**Files:**
- Create: `alembic/versions/0004_project_customer.py`

- [ ] **Step 1: migration 생성** — project_customers, project_customer_contacts 테이블

- [ ] **Step 2: 커밋**

---

### Task B4: 프로젝트 상세 — 담당자/업체 탭 개편

**Files:**
- Modify: `app/modules/infra/templates/infra_project_detail.html`
- Modify: `app/static/js/infra_project_detail.js`

- [ ] **Step 1: 담당자/업체 탭 HTML 구조 변경**

업체별 카드 레이아웃:
- 역할 뱃지 (고객사/수행사/유지보수사)
- 업체명, scope
- 소속 담당자 목록 (project_role + 연락처)
- 업체 연결/해제, 담당자 추가/해제 버튼

기존 AssetContact 그리드는 하단 "자산별 담당자" 접기 섹션으로 유지.

- [ ] **Step 2: JS — 업체/담당자 CRUD 구현**

- [ ] **Step 3: 자산 관계(Phase A5) 표시도 함께 구현**

자산 탭 하단에 선택 자산의 관계 표시.

- [ ] **Step 4: 커밋**

```bash
git add -A && git commit -m "feat: project detail contacts tab with customer/vendor/relation display"
```

---

## Phase C: Excel Export

### Task C1: Export 서비스 + API + UI

**Files:**
- Create: `app/modules/infra/services/infra_exporter.py`
- Modify: `app/modules/infra/routers/infra_excel.py`
- Modify: `app/modules/infra/templates/infra_project_detail.html`
- Modify: `app/static/js/infra_project_detail.js`

- [ ] **Step 1: exporter 서비스 — 프로젝트 데이터를 xlsx로 내보내기**

3개 시트: 01. Inventory (Asset), 05. 네트워크 대역 (IpSubnet), 03. Portmap (PortMap).
기존 import의 컬럼 매핑을 역순 활용.

- [ ] **Step 2: Export API 엔드포인트**

```
GET /api/v1/infra-excel/export/{project_id}
```

- [ ] **Step 3: 프로젝트 상세에 Export 버튼 추가**

- [ ] **Step 4: 테스트**

- [ ] **Step 5: 커밋**

```bash
git add -A && git commit -m "feat: project-level Excel Export"
```

---

## Phase D: 감사 로그 연동

### Task D1: 인프라 CRUD에 audit.log() 추가

**Files:**
- Modify: `app/modules/infra/services/asset_service.py`
- Modify: `app/modules/infra/services/project_service.py`
- Modify: `app/modules/infra/services/network_service.py`
- Modify: `app/modules/infra/services/policy_service.py`

- [ ] **Step 1: 각 서비스 create/update/delete에 audit.log() 추가**

```python
audit.log(db, user_id=current_user.id, action="create", entity_type="asset",
          entity_id=asset.id, summary=f"자산 생성: {asset.asset_name}", module="infra")
```

- [ ] **Step 2: 커밋**

---

### Task D2: 변경이력 탭 활성화

- [ ] **Step 1: 감사 로그 조회 API** — `GET /api/v1/infra-dashboard/audit-log?project_id=N`

- [ ] **Step 2: 변경이력 탭 AG Grid 표시**

- [ ] **Step 3: 커밋**

---

## Phase E: 마이그레이션 통합 + 문서

### Task E1: Docker 환경 전체 검증

- [ ] **Step 1: fresh DB migration 테스트**
- [ ] **Step 2: 기존 데이터 환경 migration 테스트**

### Task E2: 문서 업데이트

- [ ] **Step 1: PROJECT_STRUCTURE.md**
- [ ] **Step 2: CLAUDE.md 데이터 원칙** — Pin 프로젝트, Asset 전역화, ProjectCustomer 반영
- [ ] **Step 3: 커밋**

---

## 요약: 신규/변경 엔티티 목록

| 테이블 | 유형 | 용도 | Phase |
|--------|------|------|-------|
| `project_assets` | **신규** | Asset↔Project N:M 연결 | A ✅ |
| `assets.asset_code` | **컬럼 추가** | 전역 고유 식별자 | A ✅ |
| `asset_relations` | **신규** | 자산 간 관계 | A ✅ |
| `user_preferences` (key 추가) | **데이터만** | `infra.pinned_project_id` | A+ |
| `project_customers` | **신규** | 프로젝트별 업체 역할 | B |
| `project_customer_contacts` | **신규** | 프로젝트별 담당자 역할 | B |

기존 테이블 구조 변경: `assets`에 `asset_code` 1개 컬럼만. 파괴적 변경 없음.
