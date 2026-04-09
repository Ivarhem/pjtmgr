# 역할기준보기 3패널 트리 뷰 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 역할기준보기를 카탈로그와 동일한 3패널(트리|그리드|상세) 구조로 재구성하고, 도메인→센터→제품군 트리로 역할을 그룹핑한다.

**Architecture:** 서버에서 역할 목록 응답에 현재 할당 자산의 카탈로그 분류(도메인, 센터, 제품군)를 enrichment로 추가하고, 프론트에서 이 데이터로 트리를 빌드한다. HTML/CSS는 카탈로그 페이지의 `catalog-layout` 패턴을 재사용하고, JS 트리 로직은 단순 3레벨 고정 구조로 새로 작성한다.

**Tech Stack:** FastAPI, SQLAlchemy, ag-Grid, vanilla JS, Bulma CSS

---

## File Structure

| 파일 | 역할 | 변경 유형 |
|------|------|----------|
| `app/modules/infra/services/asset_role_service.py` | 역할 enrichment에 분류 필드 추가 | Modify |
| `app/modules/infra/schemas/asset_role.py` | AssetRoleRead에 분류 필드 추가 | Modify |
| `app/modules/infra/templates/infra_asset_roles.html` | 3패널 레이아웃 HTML | Rewrite |
| `app/static/js/infra_asset_roles.js` | 트리 빌드/렌더 + 3패널 로직 | Rewrite |
| `app/static/css/infra_common.css` | 역할 트리 전용 스타일 (최소) | Modify |

---

### Task 1: 서버 — 역할 enrichment에 분류 필드 추가

**Files:**
- Modify: `app/modules/infra/schemas/asset_role.py`
- Modify: `app/modules/infra/services/asset_role_service.py`

역할 목록 API 응답에 현재 할당 자산의 도메인/센터/제품군 정보를 추가한다.

- [ ] **Step 1: AssetRoleRead 스키마에 필드 추가**

`app/modules/infra/schemas/asset_role.py`의 `AssetRoleRead` 클래스에 3개 필드 추가:

```python
class AssetRoleRead(BaseModel):
    # ... 기존 필드 ...
    current_asset_domain: str | None = None
    current_asset_center_label: str | None = None
    current_asset_product_family: str | None = None
```

- [ ] **Step 2: _enrich_roles_with_current_assignment 함수 확장**

`app/modules/infra/services/asset_role_service.py`의 `_enrich_roles_with_current_assignment()` 함수를 수정한다.

현재 쿼리(line ~328):
```python
current_assignments = list(
    db.execute(
        select(AssetRoleAssignment, Asset.asset_name, Asset.asset_code, Asset.status)
        .join(Asset, Asset.id == AssetRoleAssignment.asset_id)
        .where(...)
    )
)
```

변경: Asset 조인에 `Asset.model_id`, `Asset.center_id`도 가져오고, 별도로 카탈로그 속성과 센터를 벌크 조회:

```python
current_assignments = list(
    db.execute(
        select(
            AssetRoleAssignment,
            Asset.asset_name, Asset.asset_code, Asset.status,
            Asset.model_id, Asset.center_id,
        )
        .join(Asset, Asset.id == AssetRoleAssignment.asset_id)
        .where(
            AssetRoleAssignment.asset_role_id.in_(role_ids),
            AssetRoleAssignment.is_current.is_(True),
        )
        .order_by(AssetRoleAssignment.id.desc())
    )
)

# 벌크 조회: model_id → 카탈로그 속성, center_id → 센터명
model_ids = {row.model_id for _, _, _, _, model_id, _ in current_assignments if model_id}
center_ids = {row.center_id for _, _, _, _, _, center_id in current_assignments if center_id}

# 센터명 맵
from app.modules.infra.models.center import Center
center_map = {}
if center_ids:
    center_map = {
        c.id: c.center_name
        for c in db.scalars(select(Center).where(Center.id.in_(center_ids)))
    }

# 카탈로그 속성 맵 (model_id → {domain, product_family})
from app.modules.infra.services.product_catalog_attribute_service import get_product_attributes
catalog_attr_map = {}
for mid in model_ids:
    attrs = get_product_attributes(db, mid)
    attr_dict = {}
    for item in attrs:
        key = item.get("attribute_key")
        if key in ("domain", "product_family"):
            attr_dict[key] = item.get("option_label_kr") or item.get("option_label") or item.get("option_key")
    catalog_attr_map[mid] = attr_dict
```

current_map 빌드 시 3개 필드 추가:
```python
current_map.setdefault(
    assignment.asset_role_id,
    {
        "current_assignment_id": assignment.id,
        "current_asset_id": assignment.asset_id,
        "current_asset_name": asset_name,
        "current_asset_code": asset_code,
        "current_asset_status": asset_status,
        "current_asset_domain": catalog_attr_map.get(model_id, {}).get("domain"),
        "current_asset_center_label": center_map.get(center_id),
        "current_asset_product_family": catalog_attr_map.get(model_id, {}).get("product_family"),
    },
)
```

result 빌드의 기본값에도 3개 추가:
```python
item.update(
    current_map.get(
        role.id,
        {
            # ... 기존 None 필드들 ...
            "current_asset_domain": None,
            "current_asset_center_label": None,
            "current_asset_product_family": None,
        },
    )
)
```

- [ ] **Step 3: 구문 검증**

```bash
python -c "import ast; ast.parse(open('app/modules/infra/services/asset_role_service.py').read()); print('OK')"
python -c "import ast; ast.parse(open('app/modules/infra/schemas/asset_role.py').read()); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add app/modules/infra/schemas/asset_role.py app/modules/infra/services/asset_role_service.py
git commit -m "feat(infra): enrich role API with current asset domain/center/product_family"
```

---

### Task 2: HTML — 3패널 레이아웃으로 재작성

**Files:**
- Rewrite: `app/modules/infra/templates/infra_asset_roles.html`

카탈로그 `product_catalog.html`의 3패널 구조를 참고하여 역할기준보기 HTML을 재작성한다.

- [ ] **Step 1: infra_asset_roles.html을 3패널 구조로 재작성**

핵심 구조:
```html
<div class="catalog-layout" id="role-layout">
  <!-- 좌: 트리 패널 -->
  <section class="catalog-category-panel" id="role-tree-panel">
    <div class="catalog-category-toolbar">
      <input type="text" class="input-search" id="role-tree-search" placeholder="트리 검색">
    </div>
    <div id="role-classification-tree" class="classification-tree"></div>
  </section>

  <!-- 트리-그리드 스플리터 -->
  <div class="catalog-category-splitter" id="role-category-splitter"></div>

  <!-- 우: 메인 패널 (그리드 + 상세) -->
  <div class="catalog-main-panel" id="role-main-panel">
    <!-- 그리드 -->
    <div class="catalog-list-panel" id="role-grid-panel">
      <div class="catalog-list-toolbar">
        <input type="text" class="input-search" id="filter-role-search" placeholder="역할명 검색">
        <button class="btn btn-primary btn-sm" id="btn-add-role">역할 등록</button>
      </div>
      <div id="grid-asset-roles" class="ag-theme-quartz catalog-grid"></div>
    </div>

    <!-- 그리드-상세 스플리터 -->
    <div class="catalog-splitter is-hidden" id="role-detail-splitter"></div>
    <div class="catalog-detail-handle-wrap">
      <button class="catalog-detail-minimize" id="btn-minimize-role-detail" title="상세 패널 열기/닫기">❯</button>
    </div>

    <!-- 상세 패널 -->
    <div class="catalog-detail-panel is-hidden" id="role-detail-panel">
      <!-- 역할 정보 (상단) -->
      <div class="mdm-detail-section mdm-vendor-info">
        <div class="mdm-vendor-header">
          <h3 id="role-detail-title">역할 정보</h3>
          <div class="mdm-vendor-header-actions">
            <button class="btn btn-sm btn-secondary" id="btn-role-replacement">교체</button>
            <button class="btn btn-sm btn-secondary" id="btn-role-failover">장애대체</button>
            <button class="btn btn-sm btn-secondary" id="btn-role-repurpose">용도전환</button>
            <button class="btn btn-sm btn-secondary" id="btn-edit-role">수정</button>
            <button class="btn btn-sm btn-danger" id="btn-delete-role">삭제</button>
          </div>
        </div>
        <div class="mdm-vendor-body">
          <div class="mdm-vendor-fields">
            <!-- 역할명, 상태, 귀속사업, 현재자산 필드 -->
          </div>
          <div class="mdm-vendor-memo">
            <span class="mdm-field-label">비고</span>
            <p id="role-info-note">—</p>
          </div>
        </div>
      </div>
      <!-- 할당 자산 (하단) -->
      <div class="mdm-detail-section mdm-product-section">
        <div class="mdm-panel-toolbar">
          <h3>할당 자산</h3>
          <div>
            <button class="btn btn-secondary btn-sm" id="btn-role-history">이력 보기</button>
            <button class="btn btn-primary btn-sm" id="btn-add-role-assignment">할당 추가</button>
          </div>
        </div>
        <div id="grid-role-assignments" class="ag-theme-quartz mdm-product-grid"></div>
      </div>
    </div>
  </div>
</div>
```

기존 모달들(역할 등록, 할당 추가, 역할 액션, 이력 보기)은 그대로 유지.

- [ ] **Step 2: Commit**

```bash
git add app/modules/infra/templates/infra_asset_roles.html
git commit -m "refactor(infra): rewrite role view HTML as 3-panel catalog layout"
```

---

### Task 3: JS — 트리 빌드 및 렌더링

**Files:**
- Modify: `app/static/js/infra_asset_roles.js`

카탈로그의 복잡한 동적 트리와 달리, 여기서는 고정 3레벨(도메인→센터→제품군) 트리를 역할 데이터에서 직접 빌드한다.

- [ ] **Step 1: 트리 빌드 함수 구현**

역할 목록에서 트리 데이터를 구성하는 함수:

```javascript
let _roleTreeData = {};      // { domain: { center: { family: [roles] } } }
let _roleTreeCollapsed = new Set();
let _selectedTreeNode = null; // "domain>center>family" or "domain>center" or "domain"

function buildRoleTree(roles) {
  const tree = {};
  roles.forEach((role) => {
    const domain = role.current_asset_domain || "미분류";
    const center = role.current_asset_center_label || "미분류";
    const family = role.current_asset_product_family || "미분류";
    if (!tree[domain]) tree[domain] = {};
    if (!tree[domain][center]) tree[domain][center] = {};
    if (!tree[domain][center][family]) tree[domain][center][family] = [];
    tree[domain][center][family].push(role);
  });
  _roleTreeData = tree;
}
```

- [ ] **Step 2: 트리 렌더링 함수 구현**

DOM으로 트리를 렌더링. 카탈로그의 `classification-tree` CSS 클래스를 재사용:

```javascript
function renderRoleTree() {
  const container = document.getElementById("role-classification-tree");
  container.textContent = "";
  const searchQuery = (document.getElementById("role-tree-search")?.value || "").trim().toLowerCase();

  const ul = document.createElement("ul");
  ul.className = "classification-tree-root";

  Object.keys(_roleTreeData).sort().forEach((domain) => {
    // 검색 필터: 하위에 매칭되는 역할이 있는 노드만 표시
    const domainNode = _roleTreeData[domain];
    let domainCount = 0;
    Object.values(domainNode).forEach((centers) =>
      Object.values(centers).forEach((roles) => {
        domainCount += roles.filter((r) =>
          !searchQuery || r.role_name.toLowerCase().includes(searchQuery)
        ).length;
      })
    );
    if (searchQuery && domainCount === 0) return;

    const domainKey = domain;
    const domainLi = createTreeNode(domainKey, domain, domainCount, 0);
    const domainUl = document.createElement("ul");

    if (!_roleTreeCollapsed.has(domainKey)) {
      Object.keys(domainNode).sort().forEach((center) => {
        let centerCount = 0;
        Object.values(domainNode[center]).forEach((roles) => {
          centerCount += roles.filter((r) =>
            !searchQuery || r.role_name.toLowerCase().includes(searchQuery)
          ).length;
        });
        if (searchQuery && centerCount === 0) return;

        const centerKey = `${domain}>${center}`;
        const centerLi = createTreeNode(centerKey, center, centerCount, 1);
        const centerUl = document.createElement("ul");

        if (!_roleTreeCollapsed.has(centerKey)) {
          Object.keys(domainNode[center]).sort().forEach((family) => {
            const roles = domainNode[center][family].filter((r) =>
              !searchQuery || r.role_name.toLowerCase().includes(searchQuery)
            );
            if (!roles.length) return;

            const familyKey = `${domain}>${center}>${family}`;
            const familyLi = createTreeNode(familyKey, family, roles.length, 2);
            centerUl.appendChild(familyLi);
          });
        }

        centerLi.appendChild(centerUl);
        domainUl.appendChild(centerLi);
      });
    }

    domainLi.appendChild(domainUl);
    ul.appendChild(domainLi);
  });

  container.appendChild(ul);
}

function createTreeNode(key, label, count, level) {
  const li = document.createElement("li");
  li.className = "classification-tree-item";

  const node = document.createElement("div");
  node.className = "classification-tree-node" + (_selectedTreeNode === key ? " is-selected" : "");

  const btn = document.createElement("button");
  btn.className = "classification-tree-node-main";
  btn.dataset.roleTreeKey = key;

  // 토글 아이콘 (리프가 아닌 노드만)
  const toggle = document.createElement("span");
  toggle.className = "classification-tree-toggle";
  if (level < 2) {
    toggle.textContent = _roleTreeCollapsed.has(key) ? "▶" : "▼";
    toggle.addEventListener("click", (e) => {
      e.stopPropagation();
      if (_roleTreeCollapsed.has(key)) _roleTreeCollapsed.delete(key);
      else _roleTreeCollapsed.add(key);
      renderRoleTree();
    });
  } else {
    toggle.classList.add("is-placeholder");
  }

  const name = document.createElement("span");
  name.className = "classification-tree-name";
  name.textContent = label;

  const code = document.createElement("span");
  code.className = "classification-tree-code";
  code.textContent = count;

  btn.append(toggle, name, code);
  btn.addEventListener("click", () => {
    _selectedTreeNode = (_selectedTreeNode === key) ? null : key;
    renderRoleTree();
    applyRoleFilter();
  });

  node.appendChild(btn);
  li.appendChild(node);
  return li;
}
```

- [ ] **Step 3: 그리드 필터 함수 구현**

트리 선택에 따라 그리드를 필터링:

```javascript
function applyRoleFilter() {
  if (!roleGridApi) return;
  roleGridApi.onFilterChanged();
}

function isRoleExternalFilterPresent() {
  return !!_selectedTreeNode || !!(document.getElementById("filter-role-search")?.value.trim());
}

function doesRoleExternalFilterPass(node) {
  const role = node.data;
  if (!role) return false;

  // 검색 필터
  const q = (document.getElementById("filter-role-search")?.value || "").trim().toLowerCase();
  if (q && !role.role_name.toLowerCase().includes(q)) return false;

  // 트리 필터
  if (!_selectedTreeNode) return true;
  const domain = role.current_asset_domain || "미분류";
  const center = role.current_asset_center_label || "미분류";
  const family = role.current_asset_product_family || "미분류";
  const roleKey = `${domain}>${center}>${family}`;

  return roleKey.startsWith(_selectedTreeNode);
}
```

그리드 생성 시 external filter 연결:
```javascript
roleGridApi = agGrid.createGrid(gridDiv, {
  // ... 기존 옵션 ...
  isExternalFilterPresent: isRoleExternalFilterPresent,
  doesExternalFilterPass: doesRoleExternalFilterPass,
});
```

- [ ] **Step 4: loadAssetRoles 후 트리 빌드 연결**

```javascript
async function loadAssetRoles() {
  // ... API 호출 ...
  const rows = await apiFetch(url);
  _allRoles = rows;
  roleGridApi.setGridOption("rowData", rows);
  buildRoleTree(rows);
  renderRoleTree();
}
```

- [ ] **Step 5: Commit**

```bash
git add app/static/js/infra_asset_roles.js
git commit -m "feat(infra): add role tree build/render with domain→center→family hierarchy"
```

---

### Task 4: JS — 3패널 스플리터 및 상세 패널 토글

**Files:**
- Modify: `app/static/js/infra_asset_roles.js`

카탈로그의 스플리터 패턴을 역할 페이지에 적용한다.

- [ ] **Step 1: ���리-그리드 스플리터 구현**

```javascript
const ROLE_TREE_WIDTH_KEY = "infra_role_tree_width";

function initRoleTreeSplitter() {
  const splitter = document.getElementById("role-category-splitter");
  const layout = document.getElementById("role-layout");
  if (!splitter || !layout) return;

  const saved = localStorage.getItem(ROLE_TREE_WIDTH_KEY);
  if (saved) layout.style.setProperty("--catalog-category-width", saved + "px");

  let dragging = false;
  splitter.addEventListener("mousedown", (e) => {
    e.preventDefault();
    dragging = true;
    splitter.classList.add("is-dragging");
    document.body.style.cursor = "col-resize";
  });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    const px = Math.max(200, Math.min(450, e.clientX - rect.left));
    layout.style.setProperty("--catalog-category-width", px + "px");
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    document.body.style.cursor = "";
    const width = parseInt(getComputedStyle(layout).getPropertyValue("--catalog-category-width"));
    if (width) localStorage.setItem(ROLE_TREE_WIDTH_KEY, width);
  });
}
```

- [ ] **Step 2: 그리드-상세 스플리터 + 상세 패널 토글 구현**

```javascript
const ROLE_LIST_WIDTH_KEY = "infra_role_list_width";
const ROLE_DETAIL_OPEN_KEY = "infra_role_detail_open";

function initRoleDetailSplitter() {
  const splitter = document.getElementById("role-detail-splitter");
  const mainPanel = document.getElementById("role-main-panel");
  const listPanel = document.getElementById("role-grid-panel");
  if (!splitter || !mainPanel || !listPanel) return;

  const saved = localStorage.getItem(ROLE_LIST_WIDTH_KEY);
  if (saved) mainPanel.style.setProperty("--catalog-list-width", saved + "%");

  let dragging = false;
  splitter.addEventListener("mousedown", (e) => {
    e.preventDefault();
    dragging = true;
    splitter.classList.add("is-dragging");
    document.body.style.cursor = "col-resize";
  });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = mainPanel.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    const clamped = Math.max(25, Math.min(70, pct));
    mainPanel.style.setProperty("--catalog-list-width", clamped + "%");
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    document.body.style.cursor = "";
    const val = parseFloat(getComputedStyle(mainPanel).getPropertyValue("--catalog-list-width"));
    if (val) localStorage.setItem(ROLE_LIST_WIDTH_KEY, val);
  });
}

function toggleRoleDetailPanel(show) {
  const panel = document.getElementById("role-detail-panel");
  const splitter = document.getElementById("role-detail-splitter");
  const btn = document.getElementById("btn-minimize-role-detail");
  setElementHidden(panel, !show);
  setElementHidden(splitter, !show);
  if (btn) btn.textContent = show ? "❮" : "❯";
  localStorage.setItem(ROLE_DETAIL_OPEN_KEY, show ? "1" : "0");
}
```

- [ ] **Step 3: showRoleDetail에서 상세 패널 열기 연결**

기존 `showRoleDetail` 함수 시작에 추가:
```javascript
function showRoleDetail(role) {
  _selectedRole = role;
  toggleRoleDetailPanel(true);
  // ... 나머지 기존 로직 ...
}
```

- [ ] **Step 4: initGrid에서 스플리터 초기화**

```javascript
document.addEventListener("DOMContentLoaded", async () => {
  initRoleTreeSplitter();
  initRoleDetailSplitter();
  initRoleGrid();
  // minimize 버튼
  document.getElementById("btn-minimize-role-detail").addEventListener("click", () => {
    const panel = document.getElementById("role-detail-panel");
    toggleRoleDetailPanel(panel.classList.contains("is-hidden"));
  });
});
```

- [ ] **Step 5: Commit**

```bash
git add app/static/js/infra_asset_roles.js
git commit -m "feat(infra): add 3-panel splitters and detail panel toggle for role view"
```

---

### Task 5: 트리 검색 + 이벤트 연결 + 기존 기능 통합

**Files:**
- Modify: `app/static/js/infra_asset_roles.js`

트리 검색, 그리드 검색, ctx-changed 이벤트를 연결하고, 기존 모달/액션 기능이 새 레이아웃에서 동작하는지 확인한다.

- [ ] **Step 1: 트리 검색 이벤트 연결**

```javascript
document.getElementById("role-tree-search").addEventListener("input", () => {
  renderRoleTree();
});
```

- [ ] **Step 2: 그리드 검색 이벤트 수정**

기존 `applyRoleQuickFilter`를 external filter 기반으로 변경:
```javascript
document.getElementById("filter-role-search").addEventListener("input", () => {
  applyRoleFilter();
});
```

quickFilter 대신 `doesRoleExternalFilterPass`에서 검색을 처리하므로 `applyRoleQuickFilter` 함수는 제거.

- [ ] **Step 3: ctx-changed에서 트리 초기화**

```javascript
window.addEventListener("ctx-changed", async () => {
  closeRoleDetail();
  _rolePartnerAssetsCache = [];
  _selectedTreeNode = null;
  loadAssetRoles();
});
```

- [ ] **Step 4: 역할 CRUD 후 트리 갱신 확인**

`saveRole`, `deleteRole`, `saveRoleAssignment`, `deleteRoleAssignment`, `saveRoleAction` 모두 `loadAssetRoles()`를 호출하고, 이 함수가 `buildRoleTree` + `renderRoleTree`를 호출하므로 자동 갱신됨. 추가 작업 불필요.

- [ ] **Step 5: 트리 접기/펼치기 상태 저장**

```javascript
const ROLE_TREE_COLLAPSED_KEY = "infra_role_tree_collapsed";

// renderRoleTree 후:
function saveTreeCollapsedState() {
  localStorage.setItem(ROLE_TREE_COLLAPSED_KEY, JSON.stringify([..._roleTreeCollapsed]));
}

// 초기화 시:
function restoreTreeCollapsedState() {
  try {
    const saved = JSON.parse(localStorage.getItem(ROLE_TREE_COLLAPSED_KEY) || "[]");
    _roleTreeCollapsed = new Set(saved);
  } catch { _roleTreeCollapsed = new Set(); }
}
```

`renderRoleTree` 마지막에 `saveTreeCollapsedState()` 호출.
`initRoleGrid` 시작에 `restoreTreeCollapsedState()` 호출.

- [ ] **Step 6: Commit**

```bash
git add app/static/js/infra_asset_roles.js
git commit -m "feat(infra): connect tree search, grid filter, and state persistence for role view"
```

---

### Task 6: 최종 통합 테스트 및 문서

**Files:**
- Modify: `docs/guidelines/frontend.md` (선택)

- [ ] **Step 1: 브라우저 통합 테스트**

1. 역할기준보기 페이지 진입 → 3패널 표시 확인
2. 트리에 도메인→센터→제품군 계층 표시 확인
3. 트리 노드 클릭 → 그리드 필터링 확인
4. 그리드 역할 클릭 → 상세 패널 표시 확인
5. 스플리터 드래그 → 패널 너비 조절 확인
6. 역할 등록/수정/삭제 → 트리 + 그리드 갱신 확인
7. 할당 추가/수정/삭제 → 상세 패널 갱신 확인
8. 컨텍스트 변경(고객사/프로젝트) → 전체 초기화 확인
9. 새로고침 → 스플리터 너비/트리 접기 상태 복원 확인

- [ ] **Step 2: Commit (필요한 경우 수정 후)**

```bash
git add -A
git commit -m "fix(infra): integration fixes for role tree view"
```

---

## Self-Review

1. **Spec coverage:** 3패널 레이아웃 ✓, 도메인→센터→제품군 트리 ✓, 서버 enrichment ✓, 트리 필터 ✓, 상세 패널 ✓, 할당 자산 그리드 ✓, 이력 모달 ✓, 스플리터 ✓, 상태 저장 ✓
2. **Placeholder scan:** 모든 함수에 실제 코드 포함 ✓
3. **Type consistency:** `_roleTreeData`, `_selectedTreeNode`, `buildRoleTree`, `renderRoleTree`, `applyRoleFilter` 네이밍 일관 ✓, enrichment 필드명 `current_asset_domain/center_label/product_family` 스키마-서비스-JS 일관 ✓
