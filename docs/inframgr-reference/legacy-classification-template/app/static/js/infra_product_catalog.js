/* ── 제품 카탈로그 ── */

let catalogGridApi, ifaceGridApi;
let currentProductId = null;
let currentProductType = null;
let _currentProductIsPlaceholder = false;
let _catalogImportPreviewReady = false;
let _catalogClassificationLeafOptions = [];
let _catalogClassificationNodes = [];
let _catalogClassificationNodeMap = new Map();
let _selectedCatalogClassificationCode = "";
const _catalogClassificationCollapsed = new Set();
let _catalogPermissions = {
  canManageCatalogProducts: false,
  canManageCatalogTaxonomy: false,
};
const CATALOG_CLASSIFICATION_ALIAS_DEFAULTS = ["대구분", "중구분", "소구분", "세구분", "상세구분"];
const CATALOG_CATEGORY_WIDTH_KEY = "catalog_category_width";
const CATALOG_LIST_WIDTH_KEY = "catalog_list_width";
const CATALOG_GRID_COLUMN_STATE_KEY = "catalog_grid_column_state_v1";
const CATALOG_CLASSIFICATION_COLLAPSED_KEY = "catalog_classification_collapsed_nodes";
const CATALOG_DETAIL_OPEN_KEY = "catalog_detail_open";
const CATALOG_DETAIL_LAST_ID_KEY = "catalog_detail_last_id";
let _catalogClassificationScheme = null;
let _catalogClassificationEditMode = false;

const PRODUCT_KIND_LABELS = {
  hardware: "하드웨어",
  software: "소프트웨어",
  service: "서비스",
  model: "모델",
  business_capability: "업무기능",
  dataset: "데이터셋",
};

const CATALOG_IMPORT_STATUS_LABELS = {
  new: "신규",
  update: "갱신예정",
  skip_existing: "기존존재",
  unmatched: "미매칭",
  unchanged: "변경없음",
  invalid: "검증오류",
};

const CATALOG_LEVEL_ALIAS_DEFAULTS = ["대구분", "중구분", "소구분", "세구분", "상세구분"];

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function loadCatalogPermissions() {
  try {
    const me = window.__me || await apiFetch("/api/v1/auth/me");
    _catalogPermissions = {
      canManageCatalogProducts: !!me?.permissions?.can_manage_catalog_products,
      canManageCatalogTaxonomy: !!me?.permissions?.can_manage_catalog_taxonomy,
    };
  } catch (_) {
    _catalogPermissions = {
      canManageCatalogProducts: false,
      canManageCatalogTaxonomy: false,
    };
  }
}

function setButtonAvailability(id, enabled, disabledTitle = "권한이 없습니다.") {
  const el = document.getElementById(id);
  if (!el) return;
  el.disabled = !enabled;
  el.title = enabled ? "" : disabledTitle;
}

function applyCatalogPermissionState() {
  const canProducts = _catalogPermissions.canManageCatalogProducts;
  const canTaxonomy = _catalogPermissions.canManageCatalogTaxonomy;
  setButtonAvailability("btn-open-import", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-add-product", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-edit-product", canProducts && !!currentProductId, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-delete-product", canProducts && !!currentProductId && !_currentProductIsPlaceholder, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-save-spec", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-save-software-spec", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-save-model-spec", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-save-generic-profile", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-save-eosl", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-add-interface", canProducts, "카탈로그 제품 관리 권한이 없습니다.");
  setButtonAvailability("btn-catalog-classification-edit-toggle", canTaxonomy, "카탈로그 기준 관리 권한이 없습니다.");
  setButtonAvailability("btn-catalog-classification-edit-scheme", canTaxonomy, "카탈로그 기준 관리 권한이 없습니다.");
  setButtonAvailability("btn-catalog-classification-add-root", canTaxonomy, "카탈로그 기준 관리 권한이 없습니다.");
  setButtonAvailability("btn-catalog-classification-add-child", canTaxonomy && !!getSelectedCatalogClassificationNode(), "카탈로그 기준 관리 권한이 없습니다.");
  const editToolbar = document.getElementById("catalog-classification-edit-toolbar");
  if (editToolbar) editToolbar.classList.toggle("hidden", !_catalogClassificationEditMode || !canTaxonomy);
  const editToggle = document.getElementById("btn-catalog-classification-edit-toggle");
  if (editToggle) editToggle.textContent = _catalogClassificationEditMode ? "편집 종료" : "편집";
}

function loadCatalogClassificationCollapsedState() {
  try {
    const raw = localStorage.getItem(CATALOG_CLASSIFICATION_COLLAPSED_KEY);
    if (!raw) return;
    const ids = JSON.parse(raw);
    if (!Array.isArray(ids)) return;
    _catalogClassificationCollapsed.clear();
    ids
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0)
      .forEach((value) => _catalogClassificationCollapsed.add(value));
  } catch (_) {
    _catalogClassificationCollapsed.clear();
  }
}

function saveCatalogClassificationCollapsedState() {
  localStorage.setItem(
    CATALOG_CLASSIFICATION_COLLAPSED_KEY,
    JSON.stringify([..._catalogClassificationCollapsed]),
  );
}

function getStoredCatalogGridColumnState() {
  const raw = localStorage.getItem(CATALOG_GRID_COLUMN_STATE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : null;
  } catch (_) {
    return null;
  }
}

function hasStoredCatalogGridColumnState() {
  return !!getStoredCatalogGridColumnState()?.length;
}

function saveCatalogGridColumnState() {
  if (!catalogGridApi?.getColumnState) return;
  const state = catalogGridApi.getColumnState();
  if (!Array.isArray(state) || !state.length) return;
  localStorage.setItem(CATALOG_GRID_COLUMN_STATE_KEY, JSON.stringify(state));
}

function restoreCatalogGridColumnState() {
  const state = getStoredCatalogGridColumnState();
  if (!state?.length || !catalogGridApi?.applyColumnState) return false;
  return !!catalogGridApi.applyColumnState({ state, applyOrder: true });
}

function fitCatalogGridColumnsIfNeeded() {
  if (!catalogGridApi || hasStoredCatalogGridColumnState()) return;
  setTimeout(() => catalogGridApi.sizeColumnsToFit(), 0);
}

/* ── 목록 그리드 ── */

const catalogColDefs = [
  { field: "vendor", headerName: "제조사", width: 120, sort: "asc" },
  { field: "name", headerName: "모델명", flex: 1, minWidth: 160 },
  { field: "asset_type_key", headerName: "자산 유형", width: 110,
    valueFormatter: (p) => getAssetTypeLabel(p.value) || "-",
  },
  { field: "classification_level_1_name", headerName: "대구분", width: 130, valueFormatter: (p) => p.value || "-" },
  { field: "classification_level_2_name", headerName: "중구분", width: 130, valueFormatter: (p) => p.value || "-" },
  { field: "classification_level_3_name", headerName: "소구분", width: 140, valueFormatter: (p) => p.value || "-" },
  { field: "category", headerName: "최종분류", width: 120, hide: true },
  {
    field: "product_type", headerName: "상위분류", width: 110,
    valueFormatter: (p) => PRODUCT_KIND_LABELS[p.value] || p.value || "-",
  },
  {
    field: "eosl_date", headerName: "EOSL", width: 110,
    valueFormatter: (p) => fmtDate(p.value),
    cellClassRules: {
      "cell-warn": (p) => {
        if (!p.value) return false;
        const d = new Date(p.value);
        const now = new Date();
        const sixMo = new Date();
        sixMo.setMonth(sixMo.getMonth() + 6);
        return d <= sixMo && d >= now;
      },
      "cell-danger": (p) => p.value && new Date(p.value) < new Date(),
    },
  },
];

function getCatalogClassificationAliases() {
  if (!_catalogClassificationScheme) return [...CATALOG_LEVEL_ALIAS_DEFAULTS];
  return [
    _catalogClassificationScheme.level_1_alias || CATALOG_LEVEL_ALIAS_DEFAULTS[0],
    _catalogClassificationScheme.level_2_alias || CATALOG_LEVEL_ALIAS_DEFAULTS[1],
    _catalogClassificationScheme.level_3_alias || CATALOG_LEVEL_ALIAS_DEFAULTS[2],
    _catalogClassificationScheme.level_4_alias || CATALOG_LEVEL_ALIAS_DEFAULTS[3],
    _catalogClassificationScheme.level_5_alias || CATALOG_LEVEL_ALIAS_DEFAULTS[4],
  ];
}

function getCatalogLeafAlias() {
  const aliases = getCatalogClassificationAliases().filter(Boolean);
  return aliases[aliases.length - 1] || CATALOG_LEVEL_ALIAS_DEFAULTS[2];
}

function applyCatalogClassificationAliases() {
  const aliases = getCatalogClassificationAliases();
  const leafAlias = getCatalogLeafAlias();
  const levelColumns = [
    { field: "classification_level_1_name", alias: aliases[0] },
    { field: "classification_level_2_name", alias: aliases[1] || "2레벨" },
    { field: "classification_level_3_name", alias: aliases[2] || "3레벨" },
  ];
  const productTypeCol = catalogColDefs.find((col) => col.field === "product_type");
  const categoryCol = catalogColDefs.find((col) => col.field === "category");
  levelColumns.forEach(({ field, alias }) => {
    const col = catalogColDefs.find((item) => item.field === field);
    if (col) col.headerName = alias;
  });
  if (productTypeCol) productTypeCol.headerName = "분류축";
  if (categoryCol) categoryCol.headerName = leafAlias;
  document.getElementById("catalog-classification-title").textContent = leafAlias;
  document.getElementById("product-classification-label").textContent = leafAlias;
  if (catalogGridApi) {
    catalogGridApi.setGridOption("columnDefs", catalogColDefs);
    const restored = restoreCatalogGridColumnState();
    if (!restored) fitCatalogGridColumnsIfNeeded();
  }
}

function renderCatalogClassificationSummary() {
  const container = document.getElementById("catalog-classification-summary");
  if (!container) return;
  if (!_catalogClassificationScheme) {
    container.innerHTML = `
      <div class="classification-stat"><span class="classification-stat-label">분류체계</span><span class="classification-stat-value">미설정</span></div>
      <div class="classification-stat"><span class="classification-stat-label">노드 수</span><span class="classification-stat-value">0</span></div>
      <div class="classification-stat"><span class="classification-stat-label">최종 라벨</span><span class="classification-stat-value">${escapeHtml(getCatalogLeafAlias())}</span></div>
    `;
    return;
  }
  container.innerHTML = `
    <div class="classification-stat"><span class="classification-stat-label">분류체계</span><span class="classification-stat-value">${escapeHtml(_catalogClassificationScheme.name)}</span></div>
    <div class="classification-stat"><span class="classification-stat-label">노드 수</span><span class="classification-stat-value">${_catalogClassificationScheme.node_count ?? _catalogClassificationNodes.length}</span></div>
    <div class="classification-stat"><span class="classification-stat-label">최종 라벨</span><span class="classification-stat-value">${escapeHtml(getCatalogLeafAlias())}</span></div>
  `;
}

function initCatalogGrid() {
  catalogGridApi = agGrid.createGrid(document.getElementById("grid-catalog"), {
    columnDefs: catalogColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    onRowClicked: (e) => selectProduct(e.data),
    onColumnMoved: saveCatalogGridColumnState,
    onColumnVisible: saveCatalogGridColumnState,
    onDragStopped: saveCatalogGridColumnState,
    onColumnPinned: saveCatalogGridColumnState,
    onColumnResized: (event) => {
      if (event.finished) saveCatalogGridColumnState();
    },
  });
  const restored = restoreCatalogGridColumnState();
  if (!restored) fitCatalogGridColumnsIfNeeded();
}

async function loadCatalog() {
  try {
    const data = await apiFetch("/api/v1/product-catalog");
    catalogGridApi.setGridOption("rowData", data);
    const kinds = [...new Set(data.map(d => d.product_type).filter(Boolean))].sort();
    const kindSel = document.getElementById("catalog-kind-filter");
    const currentKind = kindSel.value;
    while (kindSel.options.length > 1) kindSel.remove(1);
    kinds.forEach((k) => {
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = PRODUCT_KIND_LABELS[k] || k;
      kindSel.appendChild(opt);
    });
    kindSel.value = currentKind;

    // 분류 필터 갱신
    updateCatalogListMeta(data);
    applyFilter();
    if (localStorage.getItem(CATALOG_DETAIL_OPEN_KEY) === "1") {
      const lastId = Number(localStorage.getItem(CATALOG_DETAIL_LAST_ID_KEY) || 0);
      const match = data.find((item) => item.id === lastId);
      if (match) {
        selectProduct(match);
      } else {
        setCatalogDetailOpen(false);
      }
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadCatalogClassificationLeaves() {
  const schemes = await apiFetch("/api/v1/classification-schemes?scope_type=global");
  const scheme = schemes[0];
  _catalogClassificationScheme = scheme || null;
  _catalogClassificationLeafOptions = [];
  _catalogClassificationNodes = [];
  _catalogClassificationNodeMap = new Map();
  applyCatalogClassificationAliases();
  renderCatalogClassificationSummary();
  if (!scheme) return;
  const nodes = await apiFetch(`/api/v1/classification-schemes/${scheme.id}/nodes`);
  _catalogClassificationNodes = nodes.filter((node) => node.is_active);
  const activeNodeIds = new Set(_catalogClassificationNodes.map((node) => node.id));
  [..._catalogClassificationCollapsed].forEach((nodeId) => {
    if (!activeNodeIds.has(nodeId)) _catalogClassificationCollapsed.delete(nodeId);
  });
  saveCatalogClassificationCollapsedState();
  nodes.forEach((node) => {
    _catalogClassificationNodeMap.set(node.node_code, node);
  });
  const parentIds = new Set(_catalogClassificationNodes.filter((node) => node.parent_id).map((node) => node.parent_id));
  _catalogClassificationLeafOptions = _catalogClassificationNodes
    .filter((node) => node.is_active && !parentIds.has(node.id))
    .map((node) => ({
      value: node.node_code,
      label: node.path_label || node.node_name,
    }))
    .sort((a, b) => a.label.localeCompare(b.label, "ko-KR"));
  syncCatalogClassificationSelect();
  renderCatalogClassificationSummary();
  renderCatalogClassificationTree();
}

function syncCatalogClassificationSelect(selectedValue = "") {
  const select = document.getElementById("product-classification-node-code");
  if (!select) return;
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = _catalogClassificationLeafOptions.length ? "-- 최종 분류 선택 --" : "-- 선택 가능한 분류 없음 --";
  select.appendChild(empty);
  _catalogClassificationLeafOptions.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.value;
    opt.textContent = item.label;
    select.appendChild(opt);
  });
  select.value = selectedValue || "";
  updateCatalogClassificationHint();
}

function updateCatalogClassificationHint() {
  const select = document.getElementById("product-classification-node-code");
  const hint = document.getElementById("product-classification-hint");
  if (!select || !hint) return;
  const node = _catalogClassificationNodeMap.get(select.value);
  const leafAlias = getCatalogLeafAlias();
  hint.textContent = node
    ? `선택 경로: ${node.path_label || node.node_name}`
    : `카탈로그는 글로벌 기본 분류체계의 최종 ${leafAlias}에 연결합니다.`;
}

function renderCatalogClassificationTree() {
  const container = document.getElementById("catalog-classification-tree");
  if (!container) return;
  if (!_catalogClassificationNodes.length) {
    container.innerHTML = '<div class="catalog-classification-empty">선택 가능한 leaf 분류가 없습니다.</div>';
    return;
  }
  const roots = buildCatalogClassificationTreeRoots();
  container.innerHTML = `<ul class="classification-tree-root">${roots.map(renderCatalogClassificationTreeNode).join("")}</ul>`;
  applyCatalogPermissionState();
}

function buildCatalogClassificationTreeRoots() {
  const cloned = _catalogClassificationNodes.map((node) => ({ ...node, children: [] }));
  const byId = new Map(cloned.map((node) => [node.id, node]));
  const roots = [];
  cloned.forEach((node) => {
    if (node.parent_id && byId.has(node.parent_id)) {
      byId.get(node.parent_id).children.push(node);
      return;
    }
    roots.push(node);
  });
  return roots.sort(sortCatalogClassificationNodes);
}

function sortCatalogClassificationNodes(a, b) {
  const sortGap = Number(a.sort_order || 0) - Number(b.sort_order || 0);
  if (sortGap !== 0) return sortGap;
  return String(a.node_name || "").localeCompare(String(b.node_name || ""), "ko-KR");
}

function renderCatalogClassificationTreeNode(node) {
  const children = [...(node.children || [])].sort(sortCatalogClassificationNodes);
  const hasChildren = children.length > 0;
  const collapsed = hasChildren && _catalogClassificationCollapsed.has(node.id);
  const selectedClass = node.node_code === _selectedCatalogClassificationCode ? " is-selected" : "";
  const toggleMarkup = hasChildren
    ? `<span class="classification-tree-toggle" data-catalog-toggle-node="${node.id}">${collapsed ? "▸" : "▾"}</span>`
    : '<span class="classification-tree-toggle is-placeholder">•</span>';
  const actionAttrs = `data-catalog-classification-code="${escapeHtml(node.node_code)}"`;
  const actionButtons = _catalogClassificationEditMode && _catalogPermissions.canManageCatalogTaxonomy
    ? `<span class="classification-tree-meta">
        <button type="button" class="btn btn-secondary btn-xs" data-catalog-edit-node="${node.id}">수정</button>
        <button type="button" class="btn btn-danger btn-xs" data-catalog-delete-node="${node.id}">삭제</button>
      </span>`
    : "";
  const childMarkup = hasChildren && !collapsed
    ? `<ul>${children.map(renderCatalogClassificationTreeNode).join("")}</ul>`
    : "";
  return `
    <li class="classification-tree-item">
      <div class="classification-tree-node${selectedClass}">
        <button type="button" class="classification-tree-node-main" ${actionAttrs}>
          ${toggleMarkup}
          <span class="classification-tree-main">
            <span class="classification-tree-title">
              <span class="classification-tree-name">${escapeHtml(node.node_name)}</span>
              <span class="classification-tree-code">${escapeHtml(node.node_code)}</span>
            </span>
          </span>
        </button>
        ${actionButtons}
      </div>
      ${childMarkup}
    </li>
  `;
}

function updateCatalogListMeta(data) {
  const filteredRows = [];
  catalogGridApi?.forEachNodeAfterFilterAndSort((node) => filteredRows.push(node.data));
  const titleEl = document.getElementById("catalog-list-title");
  const countEl = document.getElementById("catalog-list-count");
  const selectedNode = _catalogClassificationNodeMap.get(_selectedCatalogClassificationCode);
  if (titleEl) {
    titleEl.textContent = selectedNode ? `${selectedNode.node_name} 제품` : "전체 제품";
  }
  if (countEl) {
    const count = filteredRows.length || 0;
    countEl.textContent = `${count}건`;
  }
}

function getCatalogSelectedClassificationCodes() {
  if (!_selectedCatalogClassificationCode) return null;
  const selectedNode = _catalogClassificationNodeMap.get(_selectedCatalogClassificationCode);
  if (!selectedNode) return null;

  const childrenByParentId = new Map();
  _catalogClassificationNodes.forEach((node) => {
    if (!node.parent_id) return;
    if (!childrenByParentId.has(node.parent_id)) {
      childrenByParentId.set(node.parent_id, []);
    }
    childrenByParentId.get(node.parent_id).push(node);
  });

  const codes = new Set();
  const stack = [selectedNode];
  while (stack.length) {
    const node = stack.pop();
    const children = childrenByParentId.get(node.id) || [];
    if (!children.length) {
      codes.add(node.node_code);
      continue;
    }
    stack.push(...children);
  }
  return codes;
}

function getSelectedCatalogClassificationNode() {
  if (!_selectedCatalogClassificationCode) return null;
  return _catalogClassificationNodeMap.get(_selectedCatalogClassificationCode) || null;
}

function populateCatalogClassificationParentOptions(selectedParentId = null, excludedNodeId = null) {
  const parentEl = document.getElementById("catalog-classification-node-parent");
  if (!parentEl) return;
  parentEl.innerHTML = '<option value="">최상위 분류</option>';
  _catalogClassificationNodes
    .filter((node) => node.id !== excludedNodeId)
    .forEach((node) => {
      const option = document.createElement("option");
      option.value = String(node.id);
      option.textContent = `${"· ".repeat(Math.max((node.level || 1) - 1, 0))}${node.path_label || node.node_name}`;
      parentEl.appendChild(option);
    });
  parentEl.value = selectedParentId ? String(selectedParentId) : "";
}

function openCatalogClassificationSchemeModal() {
  if (!_catalogPermissions.canManageCatalogTaxonomy) {
    showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!_catalogClassificationScheme) return;
  document.getElementById("catalog-classification-scheme-name").value = _catalogClassificationScheme.name || "";
  document.getElementById("catalog-classification-scheme-description").value = _catalogClassificationScheme.description || "";
  ["1", "2", "3", "4", "5"].forEach((level) => {
    document.getElementById(`catalog-classification-scheme-level-${level}-alias`).value =
      _catalogClassificationScheme[`level_${level}_alias`] || "";
  });
  document.getElementById("catalog-classification-scheme-active").value = String(_catalogClassificationScheme.is_active !== false);
  document.getElementById("modal-catalog-classification-scheme").showModal();
}

function openCatalogClassificationNodeModal(mode) {
  if (!_catalogPermissions.canManageCatalogTaxonomy) {
    showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
    return;
  }
  const node = mode === "edit" ? getSelectedCatalogClassificationNode() : null;
  document.getElementById("modal-catalog-classification-node-title").textContent = mode === "edit" ? "분류 수정" : "분류 등록";
  document.getElementById("catalog-classification-node-id").value = node?.id || "";
  document.getElementById("catalog-classification-node-code").value = node?.node_code || "";
  document.getElementById("catalog-classification-node-name").value = node?.node_name || "";
  document.getElementById("catalog-classification-node-sort-order").value = node?.sort_order ?? 100;
  document.getElementById("catalog-classification-node-asset-type-key").value = node?.asset_type_key || "";
  document.getElementById("catalog-classification-node-asset-type-code").value = node?.asset_type_code || "";
  document.getElementById("catalog-classification-node-asset-type-label").value = node?.asset_type_label || "";
  document.getElementById("catalog-classification-node-asset-kind").value = node?.asset_kind || "";
  document.getElementById("catalog-classification-node-catalog-assignable").value = String(node?.is_catalog_assignable ?? false);
  document.getElementById("catalog-classification-node-active").value = String(node?.is_active ?? true);
  document.getElementById("catalog-classification-node-note").value = node?.note || "";
  populateCatalogClassificationParentOptions(
    mode === "add_child" ? getSelectedCatalogClassificationNode()?.id : node?.parent_id,
    node?.id || null,
  );
  document.getElementById("modal-catalog-classification-node").showModal();
}

function setCatalogClassificationEditMode(enabled) {
  _catalogClassificationEditMode = !!enabled;
  renderCatalogClassificationTree();
  applyCatalogPermissionState();
}

async function saveCatalogClassificationScheme() {
  if (!_catalogPermissions.canManageCatalogTaxonomy || !_catalogClassificationScheme) return;
  const payload = {
    name: document.getElementById("catalog-classification-scheme-name").value.trim(),
    description: document.getElementById("catalog-classification-scheme-description").value.trim() || null,
    level_1_alias: document.getElementById("catalog-classification-scheme-level-1-alias").value.trim() || null,
    level_2_alias: document.getElementById("catalog-classification-scheme-level-2-alias").value.trim() || null,
    level_3_alias: document.getElementById("catalog-classification-scheme-level-3-alias").value.trim() || null,
    level_4_alias: document.getElementById("catalog-classification-scheme-level-4-alias").value.trim() || null,
    level_5_alias: document.getElementById("catalog-classification-scheme-level-5-alias").value.trim() || null,
    is_active: document.getElementById("catalog-classification-scheme-active").value === "true",
  };
  await apiFetch(`/api/v1/classification-schemes/${_catalogClassificationScheme.id}`, { method: "PATCH", body: payload });
  document.getElementById("modal-catalog-classification-scheme").close();
  await loadCatalogClassificationLeaves();
  await loadCatalog();
}

async function saveCatalogClassificationNode() {
  if (!_catalogPermissions.canManageCatalogTaxonomy || !_catalogClassificationScheme) return;
  const nodeId = Number(document.getElementById("catalog-classification-node-id").value || 0);
  const payload = {
    node_code: document.getElementById("catalog-classification-node-code").value.trim(),
    node_name: document.getElementById("catalog-classification-node-name").value.trim(),
    parent_id: document.getElementById("catalog-classification-node-parent").value
      ? Number(document.getElementById("catalog-classification-node-parent").value)
      : null,
    sort_order: Number(document.getElementById("catalog-classification-node-sort-order").value || 100),
    asset_type_key: document.getElementById("catalog-classification-node-asset-type-key").value.trim() || null,
    asset_type_code: document.getElementById("catalog-classification-node-asset-type-code").value.trim().toUpperCase() || null,
    asset_type_label: document.getElementById("catalog-classification-node-asset-type-label").value.trim() || null,
    asset_kind: document.getElementById("catalog-classification-node-asset-kind").value || null,
    is_catalog_assignable: document.getElementById("catalog-classification-node-catalog-assignable").value === "true",
    is_active: document.getElementById("catalog-classification-node-active").value === "true",
    note: document.getElementById("catalog-classification-node-note").value.trim() || null,
  };
  if (nodeId) {
    await apiFetch(`/api/v1/classification-nodes/${nodeId}`, { method: "PATCH", body: payload });
  } else {
    await apiFetch(`/api/v1/classification-schemes/${_catalogClassificationScheme.id}/nodes`, { method: "POST", body: payload });
  }
  document.getElementById("modal-catalog-classification-node").close();
  const previousSelection = _selectedCatalogClassificationCode;
  await loadCatalogClassificationLeaves();
  _selectedCatalogClassificationCode = previousSelection || payload.node_code;
  renderCatalogClassificationTree();
  applyFilter();
}

async function deleteCatalogClassificationNode() {
  if (!_catalogPermissions.canManageCatalogTaxonomy) {
    showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
    return;
  }
  const node = getSelectedCatalogClassificationNode();
  if (!node || !confirm(`분류 "${node.node_name}"을(를) 삭제하시겠습니까?`)) return;
  await apiFetch(`/api/v1/classification-nodes/${node.id}`, { method: "DELETE" });
  _selectedCatalogClassificationCode = "";
  await loadCatalogClassificationLeaves();
  applyFilter();
}

function setCatalogDetailOpen(isOpen) {
  const panel = document.querySelector(".catalog-main-panel");
  const detailPanel = document.getElementById("detail-panel");
  const detailContent = document.getElementById("detail-content");
  const detailEmpty = document.getElementById("detail-empty");
  const splitter = document.getElementById("catalog-splitter");
  const handle = document.getElementById("btn-minimize-catalog-detail");
  if (!panel || !detailPanel || !detailContent || !detailEmpty || !splitter || !handle) return;
  panel.classList.toggle("is-detail-open", !!isOpen);
  detailPanel.classList.toggle("hidden", !isOpen);
  detailContent.classList.toggle("is-hidden", !isOpen || !currentProductId);
  detailEmpty.classList.toggle("is-hidden", !!currentProductId);
  splitter.classList.toggle("hidden", !isOpen);
  handle.textContent = isOpen ? "❮" : "❯";
  localStorage.setItem(CATALOG_DETAIL_OPEN_KEY, isOpen ? "1" : "0");
}

function closeCatalogDetail() {
  currentProductId = null;
  currentProductType = null;
  _currentProductIsPlaceholder = false;
  setCatalogDetailOpen(false);
  applyCatalogPermissionState();
}

function rememberCatalogDetailState(productId) {
  if (!productId) return;
  localStorage.setItem(CATALOG_DETAIL_LAST_ID_KEY, String(productId));
}

function reopenCatalogDetail() {
  if (!currentProductId) {
    const savedId = Number(localStorage.getItem(CATALOG_DETAIL_LAST_ID_KEY) || 0);
    if (!Number.isFinite(savedId) || savedId <= 0) {
      showToast("제품을 먼저 선택하세요.", "info");
      return;
    }
    const row = [];
    catalogGridApi?.forEachNode((node) => {
      if (node.data?.id === savedId) row.push(node.data);
    });
    if (!row.length) {
      showToast("제품을 먼저 선택하세요.", "info");
      return;
    }
    selectProduct(row[0]);
    return;
  }
  setCatalogDetailOpen(true);
}

function toggleCatalogDetailPanel() {
  const panel = document.querySelector(".catalog-main-panel");
  if (panel?.classList.contains("is-detail-open")) {
    closeCatalogDetail();
  } else {
    reopenCatalogDetail();
  }
}

function initCategorySplitter() {
  const splitter = document.getElementById("catalog-category-splitter");
  const layout = document.querySelector(".catalog-layout");
  if (!splitter || !layout) return;
  const storedWidth = Number(localStorage.getItem(CATALOG_CATEGORY_WIDTH_KEY) || 0);
  if (storedWidth >= 280 && storedWidth <= 520) {
    layout.style.setProperty("--catalog-category-width", `${storedWidth}px`);
  }
  let dragging = false;
  splitter.addEventListener("mousedown", (event) => {
    dragging = true;
    splitter.classList.add("is-dragging");
    event.preventDefault();
  });
  document.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    const width = Math.min(520, Math.max(280, event.clientX - rect.left));
    layout.style.setProperty("--catalog-category-width", `${width}px`);
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    const current = parseInt(getComputedStyle(layout).getPropertyValue("--catalog-category-width"), 10);
    if (!Number.isNaN(current)) {
      localStorage.setItem(CATALOG_CATEGORY_WIDTH_KEY, String(current));
    }
  });
}

/* ── 필터 ── */

function applyFilter() {
  const q = document.getElementById("catalog-search").value.toLowerCase();
  const kind = document.getElementById("catalog-kind-filter").value;
  const selectedCodes = getCatalogSelectedClassificationCodes();
  catalogGridApi.setGridOption("isExternalFilterPresent", () => !!(q || kind || (selectedCodes && selectedCodes.size)));
  catalogGridApi.setGridOption("doesExternalFilterPass", (node) => {
    const d = node.data;
    if (kind && d.product_type !== kind) return false;
    if (selectedCodes && selectedCodes.size && !selectedCodes.has(d.classification_node_code)) return false;
    if (q && !(d.vendor?.toLowerCase().includes(q) || d.name?.toLowerCase().includes(q))) return false;
    return true;
  });
  catalogGridApi.onFilterChanged();
  updateCatalogListMeta();
}

/* ── 상세 패널 ── */

async function selectProduct(product) {
  currentProductId = product.id;
  setCatalogDetailOpen(true);
  document.getElementById("detail-empty").classList.add("is-hidden");
  document.getElementById("detail-content").classList.remove("is-hidden");
  rememberCatalogDetailState(product.id);

  try {
    const detail = await apiFetch(`/api/v1/product-catalog/${product.id}`);
    _currentProductIsPlaceholder = !!detail.is_placeholder;
    const btnDel = document.getElementById("btn-delete-product");
    if (_currentProductIsPlaceholder) {
      btnDel.disabled = true;
      btnDel.title = "Placeholder 제품은 삭제할 수 없습니다";
    } else {
      btnDel.disabled = false;
      btnDel.title = "";
    }
    renderDetail(detail);
    applyCatalogPermissionState();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function _infoRow(label, value) {
  const row = document.createElement("div");
  row.className = "info-row";
  const lbl = document.createElement("span");
  lbl.className = "info-label";
  lbl.textContent = label;
  const val = document.createElement("span");
  val.className = "info-value";
  if (label === "참조 URL" && value && value !== "-") {
    const a = document.createElement("a");
    a.href = value;
    a.target = "_blank";
    a.textContent = value;
    val.appendChild(a);
  } else {
    val.textContent = value || "-";
  }
  row.appendChild(lbl);
  row.appendChild(val);
  return row;
}

function renderDetail(d) {
  currentProductType = d.product_type || "hardware";
  document.getElementById("detail-title").textContent = `${d.vendor} ${d.name}`;
  syncCatalogDetailPanels(d);

  // 기본정보 탭
  const infoGrid = document.getElementById("info-grid");
  const leafAlias = getCatalogLeafAlias();
  const level1Alias = getCatalogClassificationAliases()[0];
  infoGrid.replaceChildren();
  infoGrid.appendChild(_infoRow("제조사", d.vendor));
  infoGrid.appendChild(_infoRow("모델명", d.name));
  infoGrid.appendChild(_infoRow("자산 유형", getAssetTypeLabel(d.asset_type_key) || "-"));
  infoGrid.appendChild(_infoRow(level1Alias, PRODUCT_KIND_LABELS[d.product_type] || d.product_type || "-"));
  infoGrid.appendChild(_infoRow("버전", d.version || "-"));
  infoGrid.appendChild(_infoRow(leafAlias, d.category));
  infoGrid.appendChild(_infoRow("분류 경로", _catalogClassificationNodeMap.get(d.classification_node_code)?.path_label || d.category || "-"));
  infoGrid.appendChild(_infoRow("참조 URL", d.reference_url || "-"));
  infoGrid.appendChild(_infoRow("출처", d.source_name || "-"));
  infoGrid.appendChild(_infoRow("검증상태", d.verification_status || "-"));
  infoGrid.appendChild(_infoRow("검증일", fmtDate(d.last_verified_at)));
  infoGrid.appendChild(_infoRow("등록일", fmtDate(d.created_at)));
  infoGrid.appendChild(_infoRow("수정일", fmtDate(d.updated_at)));

  const sw = d.software_spec || {};
  document.getElementById("software-edition").value = sw.edition ?? "";
  document.getElementById("software-license-type").value = sw.license_type ?? "";
  document.getElementById("software-license-unit").value = sw.license_unit ?? "";
  document.getElementById("software-deployment-type").value = sw.deployment_type ?? "";
  document.getElementById("software-runtime-env").value = sw.runtime_env ?? "";
  document.getElementById("software-support-vendor").value = sw.support_vendor ?? "";
  document.getElementById("software-architecture-note").value = sw.architecture_note ?? "";

  const model = d.model_spec || {};
  document.getElementById("model-provider").value = model.provider ?? "";
  document.getElementById("model-family").value = model.model_family ?? "";
  document.getElementById("model-modality").value = model.modality ?? "";
  document.getElementById("model-deployment-scope").value = model.deployment_scope ?? "";
  document.getElementById("model-context-window").value = model.context_window ?? "";
  document.getElementById("model-endpoint-format").value = model.endpoint_format ?? "";
  document.getElementById("model-capability-note").value = model.capability_note ?? "";

  const generic = d.generic_profile || {};
  document.getElementById("generic-owner-scope").value = generic.owner_scope ?? "";
  document.getElementById("generic-service-level").value = generic.service_level ?? "";
  document.getElementById("generic-criticality").value = generic.criticality ?? "";
  document.getElementById("generic-exposure-scope").value = generic.exposure_scope ?? "";
  document.getElementById("generic-data-classification").value = generic.data_classification ?? "";
  document.getElementById("generic-default-runtime").value = generic.default_runtime ?? "";
  document.getElementById("generic-summary-note").value = generic.summary_note ?? "";

  // HW 스펙 탭
  const s = d.hardware_spec || {};
  document.getElementById("spec-size-unit").value = s.size_unit ?? "";
  document.getElementById("spec-width-mm").value = s.width_mm ?? "";
  document.getElementById("spec-height-mm").value = s.height_mm ?? "";
  document.getElementById("spec-depth-mm").value = s.depth_mm ?? "";
  document.getElementById("spec-weight-kg").value = s.weight_kg ?? "";
  document.getElementById("spec-power-count").value = s.power_count ?? "";
  document.getElementById("spec-power-type").value = s.power_type ?? "";
  document.getElementById("spec-power-watt").value = s.power_watt ?? "";
  document.getElementById("spec-cpu-summary").value = s.cpu_summary ?? "";
  document.getElementById("spec-memory-summary").value = s.memory_summary ?? "";
  document.getElementById("spec-throughput-summary").value = s.throughput_summary ?? "";
  document.getElementById("spec-os-firmware").value = s.os_firmware ?? "";
  document.getElementById("spec-spec-url").value = s.spec_url ?? "";

  // 인터페이스 탭
  if (ifaceGridApi) {
    ifaceGridApi.setGridOption("rowData", d.interfaces || []);
  }

  // EOSL 탭
  document.getElementById("eosl-eos-date").value = d.eos_date || "";
  document.getElementById("eosl-eosl-date").value = d.eosl_date || "";
  document.getElementById("eosl-eosl-note").value = d.eosl_note || "";
}

function renderKindSpecificInfoGrid(elementId, rows) {
  const grid = document.getElementById(elementId);
  if (!grid) return;
  grid.replaceChildren();
  rows.forEach((row) => grid.appendChild(row));
}

function syncCatalogDetailPanels(detail) {
  const kind = detail.product_type || "hardware";
  document.querySelectorAll("[data-kind-scope]").forEach((element) => {
    const scopes = (element.dataset.kindScope || "").split(/\s+/).filter(Boolean);
    const isVisible = scopes.length === 0 || scopes.includes(kind);
    element.classList.toggle("is-hidden", !isVisible);
  });

  const activeTab = document.querySelector(".catalog-tab.active");
  if (activeTab?.classList.contains("is-hidden")) {
    activateCatalogTab("info");
  }
}

function activateCatalogTab(tabName) {
  document.querySelectorAll(".catalog-tab").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  document.querySelectorAll(".catalog-tab-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `tab-${tabName}`);
  });
}

/* ── 탭 전환 ── */

function initTabs() {
  document.querySelectorAll(".catalog-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      if (btn.classList.contains("is-hidden")) return;
      activateCatalogTab(btn.dataset.tab);
    });
  });
}

/* ── 인터페이스 그리드 ── */

const ifaceColDefs = [
  { field: "interface_type", headerName: "유형", width: 120 },
  { field: "speed", headerName: "속도", width: 100 },
  { field: "count", headerName: "수량", width: 80 },
  { field: "connector_type", headerName: "커넥터", width: 110 },
  {
    field: "capacity_type", headerName: "구분", width: 80,
    cellRenderer: (p) => {
      const span = document.createElement("span");
      span.className = "badge badge-" + (p.value === "fixed" ? "active" : p.value === "base" ? "planned" : "on-hold");
      span.textContent = p.value === "fixed" ? "고정" : p.value === "base" ? "기본" : "최대";
      return span;
    },
  },
  { field: "note", headerName: "비고", flex: 1 },
  {
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm infra-inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditInterface(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteInterface(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

function initIfaceGrid() {
  ifaceGridApi = agGrid.createGrid(document.getElementById("grid-interfaces"), {
    columnDefs: ifaceColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true },
    animateRows: true,
    domLayout: "autoHeight",
  });
}

/* ── 제품 CRUD ── */

const productModal = document.getElementById("modal-product");

function openCreateProduct() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  document.getElementById("product-id").value = "";
  document.getElementById("product-vendor").value = "";
  document.getElementById("product-name").value = "";
  document.getElementById("product-type").value = "hardware";
  document.getElementById("product-version").value = "";
  syncCatalogClassificationSelect("");
  document.getElementById("product-reference-url").value = "";
  document.getElementById("modal-product-title").textContent = "제품 등록";
  document.getElementById("btn-save-product").textContent = "등록";
  productModal.showModal();
}

function openEditProduct() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  apiFetch(`/api/v1/product-catalog/${currentProductId}`).then(d => {
    document.getElementById("product-id").value = d.id;
    document.getElementById("product-vendor").value = d.vendor;
    document.getElementById("product-name").value = d.name;
    document.getElementById("product-type").value = d.product_type;
    document.getElementById("product-version").value = d.version || "";
    syncCatalogClassificationSelect(d.classification_node_code || "");
    document.getElementById("product-reference-url").value = d.reference_url || "";
    document.getElementById("modal-product-title").textContent = "제품 수정";
    document.getElementById("btn-save-product").textContent = "저장";
    productModal.showModal();
  });
}

async function saveProduct() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  const id = document.getElementById("product-id").value;
  const payload = {
    vendor: document.getElementById("product-vendor").value,
    name: document.getElementById("product-name").value,
    product_type: document.getElementById("product-type").value,
    version: document.getElementById("product-version").value || null,
    classification_node_code: document.getElementById("product-classification-node-code").value || null,
    reference_url: document.getElementById("product-reference-url").value || null,
  };

  try {
    if (id) {
      await apiFetch(`/api/v1/product-catalog/${id}`, { method: "PATCH", body: payload });
      showToast("제품이 수정되었습니다.");
    } else {
      const created = await apiFetch("/api/v1/product-catalog", { method: "POST", body: payload });
      showToast("제품이 등록되었습니다.");
      currentProductId = created.id;
    }
    productModal.close();
    await loadCatalog();
    if (currentProductId) selectProduct({ id: currentProductId });
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── 카탈로그 Import ── */

const catalogImportModal = document.getElementById("modal-catalog-import");

function openCatalogImport() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  resetCatalogImportState();
  catalogImportModal.showModal();
}

function resetCatalogImportState() {
  _catalogImportPreviewReady = false;
  document.getElementById("form-catalog-import").reset();
  document.getElementById("catalog-import-domain").value = "spec";
  document.getElementById("catalog-import-dup").value = "skip";
  document.getElementById("catalog-import-summary").classList.add("is-hidden");
  document.getElementById("catalog-import-summary").textContent = "";
  document.getElementById("catalog-import-errors").classList.add("is-hidden");
  document.getElementById("catalog-import-errors").textContent = "";
  document.getElementById("catalog-import-preview-wrap").classList.add("is-hidden");
  document.getElementById("catalog-import-preview-head").replaceChildren();
  document.getElementById("catalog-import-preview-body").replaceChildren();
  document.getElementById("btn-confirm-import").disabled = true;
}

function buildCatalogImportFormData() {
  const fileInput = document.getElementById("catalog-import-file");
  const file = fileInput.files?.[0];
  if (!file) {
    showToast("엑셀 파일을 선택하세요.", "warning");
    return null;
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("domain", document.getElementById("catalog-import-domain").value);
  formData.append("on_duplicate", document.getElementById("catalog-import-dup").value);
  return formData;
}

function getCatalogImportColumns(domain) {
  if (domain === "eosl") {
    return [
      { key: "row_num", label: "행" },
      { key: "status", label: "상태" },
      { key: "vendor", label: "제조사" },
      { key: "name", label: "모델명" },
      { key: "eos_date", label: "EOS" },
      { key: "eosl_date", label: "EOSL" },
      { key: "eosl_note", label: "비고" },
      { key: "__errors", label: "오류" },
    ];
  }
  if (domain === "software") {
    return [
      { key: "row_num", label: "행" },
      { key: "status", label: "상태" },
      { key: "vendor", label: "제조사" },
      { key: "name", label: "제품명" },
      { key: "version", label: "버전" },
      { key: "asset_type_key", label: "자산유형" },
      { key: "category", label: "분류" },
      { key: "edition", label: "에디션" },
      { key: "deployment_type", label: "배포형태" },
      { key: "runtime_env", label: "실행환경" },
      { key: "__errors", label: "오류" },
    ];
  }
  if (domain === "model") {
    return [
      { key: "row_num", label: "행" },
      { key: "status", label: "상태" },
      { key: "vendor", label: "제공자" },
      { key: "name", label: "모델명" },
      { key: "version", label: "버전" },
      { key: "asset_type_key", label: "자산유형" },
      { key: "category", label: "분류" },
      { key: "model_family", label: "모델계열" },
      { key: "modality", label: "모달리티" },
      { key: "context_window", label: "컨텍스트" },
      { key: "__errors", label: "오류" },
    ];
  }
  return [
    { key: "row_num", label: "행" },
    { key: "status", label: "상태" },
    { key: "vendor", label: "제조사" },
    { key: "name", label: "모델명" },
    { key: "product_type", label: "상위분류" },
    { key: "category", label: "분류" },
    { key: "size_unit", label: "U" },
    { key: "power_count", label: "전원수량" },
    { key: "cpu_summary", label: "CPU 요약" },
    { key: "__errors", label: "오류" },
  ];
}

function renderCatalogImportPreview(result) {
  const summary = document.getElementById("catalog-import-summary");
  const errors = document.getElementById("catalog-import-errors");
  const wrap = document.getElementById("catalog-import-preview-wrap");
  const thead = document.getElementById("catalog-import-preview-head");
  const tbody = document.getElementById("catalog-import-preview-body");
  const domain = document.getElementById("catalog-import-domain").value;
  const columns = getCatalogImportColumns(domain);
  const statusCounts = result.rows.reduce((acc, row) => {
    const key = row.status || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
  const statusSummary = Object.entries(statusCounts)
    .map(([key, count]) => `${CATALOG_IMPORT_STATUS_LABELS[key] || key} ${count}건`)
    .join(", ");

  summary.textContent = `총 ${result.total}건, 유효 ${result.valid_count}건, 오류 ${result.errors.length}건, 경고 ${result.warnings.length}건`;
  if (statusSummary) {
    summary.textContent += `, ${statusSummary}`;
  }
  summary.classList.remove("is-hidden");

  if (result.errors.length || result.warnings.length) {
    const lines = [];
    result.errors.forEach((msg) => lines.push(`[오류] ${msg}`));
    result.warnings.forEach((msg) => lines.push(`[경고] ${msg}`));
    errors.textContent = lines.join("\n");
    errors.classList.remove("is-hidden");
  } else {
    errors.classList.add("is-hidden");
    errors.textContent = "";
  }

  thead.replaceChildren();
  const hr = document.createElement("tr");
  columns.forEach((col) => {
    const th = document.createElement("th");
    th.textContent = col.label;
    hr.appendChild(th);
  });
  thead.appendChild(hr);

  tbody.replaceChildren();
  result.rows.forEach((row) => {
    const tr = document.createElement("tr");
    const rowClass = row.errors?.length
      ? "catalog-import-preview-row-error"
      : row.status
        ? `catalog-import-preview-row-${row.status}`
        : "";
    if (rowClass) tr.className = rowClass;

    columns.forEach((col) => {
      const td = document.createElement("td");
      let value = "";
      if (col.key === "__errors") {
        value = row.errors?.join(", ") || "";
      } else if (col.key === "status") {
        const badge = document.createElement("span");
        badge.className = `badge ${getCatalogImportStatusBadgeClass(row.status)}`;
        badge.textContent = row.status_label || CATALOG_IMPORT_STATUS_LABELS[row.status] || "-";
        td.appendChild(badge);
        tr.appendChild(td);
        return;
      } else if (col.key === "product_type") {
        value = PRODUCT_KIND_LABELS[row.product_type] || row.product_type || "-";
      } else if (col.key === "asset_type_key") {
        value = getAssetTypeLabel(row.asset_type_key) || row.asset_type_key || "-";
      } else {
        value = row[col.key] ?? "-";
      }
      td.textContent = value;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  wrap.classList.remove("is-hidden");
}

async function previewCatalogImport() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  const formData = buildCatalogImportFormData();
  if (!formData) return;

  try {
    const res = await fetch("/api/v1/infra-excel/import/preview", {
      method: "POST",
      body: formData,
      credentials: "same-origin",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail?.[0] || data.message || "미리보기 실패");

    renderCatalogImportPreview(data);
    _catalogImportPreviewReady = true;
    document.getElementById("btn-confirm-import").disabled = false;
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function confirmCatalogImport() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!_catalogImportPreviewReady) {
    showToast("먼저 미리보기를 실행하세요.", "warning");
    return;
  }

  const formData = buildCatalogImportFormData();
  if (!formData) return;

  try {
    const res = await fetch("/api/v1/infra-excel/import/confirm", {
      method: "POST",
      body: formData,
      credentials: "same-origin",
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail?.[0] || data.message || "반영 실패");

    showToast(`반영 완료: 생성 ${data.created}건, 스킵 ${data.skipped}건`);
    if (data.import_batch_id) {
      document.getElementById("catalog-import-summary").textContent += `, 배치 ${data.import_batch_id}`;
    }
    await loadCatalog();
    _catalogImportPreviewReady = false;
    document.getElementById("btn-confirm-import").disabled = true;
  } catch (err) {
    showToast(err.message, "error");
  }
}

function getCatalogImportStatusBadgeClass(status) {
  switch (status) {
    case "new":
      return "badge-active";
    case "update":
      return "badge-in_progress";
    case "skip_existing":
    case "unchanged":
      return "badge-completed";
    case "unmatched":
      return "badge-on-hold";
    case "invalid":
      return "badge-denied";
    default:
      return "badge-completed";
  }
}

async function deleteProduct() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  // placeholder 제품은 삭제 불가 (백엔드에서도 403 차단)
  if (_currentProductIsPlaceholder) {
    showToast("Placeholder 제품은 삭제할 수 없습니다.", "error");
    return;
  }
  const title = document.getElementById("detail-title").textContent;
  confirmDelete(`"${title}"을(를) 삭제하시겠습니까?`, async () => {
    try {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}`, { method: "DELETE" });
      showToast("제품이 삭제되었습니다.");
      closeCatalogDetail();
      await loadCatalog();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

/* ── 스펙 저장 ── */

async function saveSpec() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  if (currentProductType !== "hardware") {
    showToast("하드웨어 제품에서만 스펙을 저장할 수 있습니다.", "warning");
    return;
  }
  const g = (id) => { const v = document.getElementById(id).value; return v === "" ? null : v; };
  const gn = (id) => { const v = g(id); return v === null ? null : Number(v); };
  const payload = {
    size_unit: gn("spec-size-unit"),
    width_mm: gn("spec-width-mm"),
    height_mm: gn("spec-height-mm"),
    depth_mm: gn("spec-depth-mm"),
    weight_kg: gn("spec-weight-kg"),
    power_count: gn("spec-power-count"),
    power_type: g("spec-power-type"),
    power_watt: gn("spec-power-watt"),
    cpu_summary: g("spec-cpu-summary"),
    memory_summary: g("spec-memory-summary"),
    throughput_summary: g("spec-throughput-summary"),
    os_firmware: g("spec-os-firmware"),
    spec_url: g("spec-spec-url"),
  };

  try {
    await apiFetch(`/api/v1/product-catalog/${currentProductId}/spec`, { method: "POST", body: payload });
    showToast("스펙이 저장되었습니다.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── EOSL 저장 ── */

async function saveEosl() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  const payload = {
    eos_date: document.getElementById("eosl-eos-date").value || null,
    eosl_date: document.getElementById("eosl-eosl-date").value || null,
    eosl_note: document.getElementById("eosl-eosl-note").value || null,
  };

  try {
    await apiFetch(`/api/v1/product-catalog/${currentProductId}`, { method: "PATCH", body: payload });
    showToast("EOSL 정보가 저장되었습니다.");
    await loadCatalog();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function saveSoftwareSpec() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  if (currentProductType !== "software") {
    showToast("소프트웨어 제품에서만 저장할 수 있습니다.", "warning");
    return;
  }
  const payload = {
    edition: document.getElementById("software-edition").value || null,
    license_type: document.getElementById("software-license-type").value || null,
    license_unit: document.getElementById("software-license-unit").value || null,
    deployment_type: document.getElementById("software-deployment-type").value || null,
    runtime_env: document.getElementById("software-runtime-env").value || null,
    support_vendor: document.getElementById("software-support-vendor").value || null,
    architecture_note: document.getElementById("software-architecture-note").value || null,
  };

  try {
    await apiFetch(`/api/v1/product-catalog/${currentProductId}/software-spec`, { method: "POST", body: payload });
    showToast("소프트웨어 상세가 저장되었습니다.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function saveModelSpec() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  if (currentProductType !== "model") {
    showToast("모델 제품에서만 저장할 수 있습니다.", "warning");
    return;
  }
  const contextWindowValue = document.getElementById("model-context-window").value;
  const payload = {
    provider: document.getElementById("model-provider").value || null,
    model_family: document.getElementById("model-family").value || null,
    modality: document.getElementById("model-modality").value || null,
    deployment_scope: document.getElementById("model-deployment-scope").value || null,
    context_window: contextWindowValue === "" ? null : Number(contextWindowValue),
    endpoint_format: document.getElementById("model-endpoint-format").value || null,
    capability_note: document.getElementById("model-capability-note").value || null,
  };

  try {
    await apiFetch(`/api/v1/product-catalog/${currentProductId}/model-spec`, { method: "POST", body: payload });
    showToast("모델 상세가 저장되었습니다.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function saveGenericProfile() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  if (!["service", "business_capability", "dataset"].includes(currentProductType)) {
    showToast("서비스/업무기능/데이터셋 분류에서만 저장할 수 있습니다.", "warning");
    return;
  }
  const payload = {
    owner_scope: document.getElementById("generic-owner-scope").value || null,
    service_level: document.getElementById("generic-service-level").value || null,
    criticality: document.getElementById("generic-criticality").value || null,
    exposure_scope: document.getElementById("generic-exposure-scope").value || null,
    data_classification: document.getElementById("generic-data-classification").value || null,
    default_runtime: document.getElementById("generic-default-runtime").value || null,
    summary_note: document.getElementById("generic-summary-note").value || null,
  };

  try {
    await apiFetch(`/api/v1/product-catalog/${currentProductId}/generic-profile`, { method: "POST", body: payload });
    showToast("공통 프로필이 저장되었습니다.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── 인터페이스 CRUD ── */

const ifaceModal = document.getElementById("modal-interface");

function openAddInterface() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  if (currentProductType !== "hardware") {
    showToast("인터페이스는 하드웨어 제품에서만 관리합니다.", "warning");
    return;
  }
  document.getElementById("iface-id").value = "";
  document.getElementById("iface-type").value = "";
  document.getElementById("iface-speed").value = "";
  document.getElementById("iface-count").value = "1";
  document.getElementById("iface-connector").value = "";
  document.getElementById("iface-capacity-type").value = "fixed";
  document.getElementById("iface-note").value = "";
  document.getElementById("modal-iface-title").textContent = "인터페이스 추가";
  document.getElementById("btn-save-iface").textContent = "추가";
  ifaceModal.showModal();
}

function openEditInterface(iface) {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  document.getElementById("iface-id").value = iface.id;
  document.getElementById("iface-type").value = iface.interface_type;
  document.getElementById("iface-speed").value = iface.speed || "";
  document.getElementById("iface-count").value = iface.count;
  document.getElementById("iface-connector").value = iface.connector_type || "";
  document.getElementById("iface-capacity-type").value = iface.capacity_type || "fixed";
  document.getElementById("iface-note").value = iface.note || "";
  document.getElementById("modal-iface-title").textContent = "인터페이스 수정";
  document.getElementById("btn-save-iface").textContent = "저장";
  ifaceModal.showModal();
}

async function saveInterface() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  const ifaceId = document.getElementById("iface-id").value;
  const payload = {
    interface_type: document.getElementById("iface-type").value,
    speed: document.getElementById("iface-speed").value || null,
    count: parseInt(document.getElementById("iface-count").value) || 1,
    connector_type: document.getElementById("iface-connector").value || null,
    capacity_type: document.getElementById("iface-capacity-type").value,
    note: document.getElementById("iface-note").value || null,
  };

  try {
    if (ifaceId) {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}/interfaces/${ifaceId}`, { method: "PATCH", body: payload });
      showToast("인터페이스가 수정되었습니다.");
    } else {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}/interfaces`, { method: "POST", body: payload });
      showToast("인터페이스가 추가되었습니다.");
    }
    ifaceModal.close();
    selectProduct({ id: currentProductId });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteInterface(iface) {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  confirmDelete(`인터페이스 "${iface.interface_type}"을(를) 삭제하시겠습니까?`, async () => {
    try {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}/interfaces/${iface.id}`, { method: "DELETE" });
      showToast("인터페이스가 삭제되었습니다.");
      selectProduct({ id: currentProductId });
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

/* ── 스플리터 드래그 ── */

function initSplitter() {
  const splitter = document.getElementById("catalog-splitter");
  const listPanel = document.querySelector(".catalog-list-panel");
  const mainPanel = document.querySelector(".catalog-main-panel");
  if (!splitter || !listPanel || !mainPanel) return;
  const storedWidth = Number(localStorage.getItem(CATALOG_LIST_WIDTH_KEY) || 0);
  if (storedWidth >= 28 && storedWidth <= 70) {
    mainPanel.style.setProperty("--catalog-list-width", `${storedWidth}%`);
  }
  let dragging = false;
  splitter.addEventListener("mousedown", (e) => {
    dragging = true;
    splitter.classList.add("is-dragging");
    e.preventDefault();
  });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = mainPanel.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    if (pct > 28 && pct < 70) {
      mainPanel.style.setProperty("--catalog-list-width", `${pct}%`);
      listPanel.style.width = `${pct}%`;
    }
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    const current = parseFloat(getComputedStyle(mainPanel).getPropertyValue("--catalog-list-width"));
    if (!Number.isNaN(current)) {
      localStorage.setItem(CATALOG_LIST_WIDTH_KEY, String(current));
    }
  });
}

/* ── Init ── */

document.addEventListener("DOMContentLoaded", async () => {
  await loadCatalogPermissions();
  loadCatalogClassificationCollapsedState();
  await loadCatalogClassificationLeaves();
  initCatalogGrid();
  initIfaceGrid();
  initTabs();
  activateCatalogTab("info");
  initCategorySplitter();
  initSplitter();
  setCatalogDetailOpen(localStorage.getItem(CATALOG_DETAIL_OPEN_KEY) === "1");
  applyCatalogPermissionState();
  await loadCatalog();

  // 이벤트 바인딩
  document.getElementById("btn-open-import").addEventListener("click", openCatalogImport);
  document.getElementById("btn-catalog-classification-edit-toggle").addEventListener("click", () => {
    if (!_catalogPermissions.canManageCatalogTaxonomy) {
      showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
      return;
    }
    setCatalogClassificationEditMode(!_catalogClassificationEditMode);
  });
  document.getElementById("btn-catalog-classification-edit-scheme").addEventListener("click", openCatalogClassificationSchemeModal);
  document.getElementById("btn-catalog-classification-add-root").addEventListener("click", () => openCatalogClassificationNodeModal("add_root"));
  document.getElementById("btn-catalog-classification-add-child").addEventListener("click", () => openCatalogClassificationNodeModal("add_child"));
  document.getElementById("btn-catalog-classification-scheme-cancel").addEventListener("click", () => document.getElementById("modal-catalog-classification-scheme").close());
  document.getElementById("btn-catalog-classification-scheme-submit").addEventListener("click", () => saveCatalogClassificationScheme().catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-catalog-classification-node-cancel").addEventListener("click", () => document.getElementById("modal-catalog-classification-node").close());
  document.getElementById("btn-catalog-classification-node-submit").addEventListener("click", () => saveCatalogClassificationNode().catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-clear-classification-filter").addEventListener("click", () => {
    _selectedCatalogClassificationCode = "";
    renderCatalogClassificationTree();
    applyFilter();
  });
  document.getElementById("btn-add-product").addEventListener("click", openCreateProduct);
  document.getElementById("btn-minimize-catalog-detail").addEventListener("click", toggleCatalogDetailPanel);
  document.getElementById("btn-edit-product").addEventListener("click", openEditProduct);
  document.getElementById("btn-delete-product").addEventListener("click", deleteProduct);
  document.getElementById("btn-cancel-product").addEventListener("click", () => productModal.close());
  document.getElementById("btn-save-product").addEventListener("click", saveProduct);
  document.getElementById("product-classification-node-code").addEventListener("change", updateCatalogClassificationHint);
  document.getElementById("btn-preview-import").addEventListener("click", previewCatalogImport);
  document.getElementById("btn-confirm-import").addEventListener("click", confirmCatalogImport);
  document.getElementById("btn-close-import").addEventListener("click", () => catalogImportModal.close());

  document.getElementById("btn-save-spec").addEventListener("click", saveSpec);
  document.getElementById("btn-save-software-spec").addEventListener("click", saveSoftwareSpec);
  document.getElementById("btn-save-model-spec").addEventListener("click", saveModelSpec);
  document.getElementById("btn-save-generic-profile").addEventListener("click", saveGenericProfile);
  document.getElementById("btn-save-eosl").addEventListener("click", saveEosl);

  document.getElementById("btn-add-interface").addEventListener("click", openAddInterface);
  document.getElementById("btn-cancel-iface").addEventListener("click", () => ifaceModal.close());
  document.getElementById("btn-save-iface").addEventListener("click", saveInterface);

  document.getElementById("catalog-search").addEventListener("input", applyFilter);
  document.getElementById("catalog-kind-filter").addEventListener("change", applyFilter);
  document.getElementById("catalog-classification-tree").addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-catalog-toggle-node]");
    if (toggle) {
      const nodeId = Number(toggle.dataset.catalogToggleNode);
      if (_catalogClassificationCollapsed.has(nodeId)) _catalogClassificationCollapsed.delete(nodeId);
      else _catalogClassificationCollapsed.add(nodeId);
      saveCatalogClassificationCollapsedState();
      renderCatalogClassificationTree();
      return;
    }
    const editBtn = event.target.closest("[data-catalog-edit-node]");
    if (editBtn) {
      event.preventDefault();
      event.stopPropagation();
      const node = _catalogClassificationNodes.find((item) => item.id === Number(editBtn.dataset.catalogEditNode));
      if (node) {
        _selectedCatalogClassificationCode = node.node_code;
        renderCatalogClassificationTree();
        applyFilter();
        openCatalogClassificationNodeModal("edit");
      }
      return;
    }
    const deleteBtn = event.target.closest("[data-catalog-delete-node]");
    if (deleteBtn) {
      event.preventDefault();
      event.stopPropagation();
      const node = _catalogClassificationNodes.find((item) => item.id === Number(deleteBtn.dataset.catalogDeleteNode));
      if (node) {
        _selectedCatalogClassificationCode = node.node_code;
        renderCatalogClassificationTree();
        applyFilter();
        deleteCatalogClassificationNode().catch((err) => showToast(err.message, "error"));
      }
      return;
    }
    const button = event.target.closest("[data-catalog-classification-code]");
    if (!button) return;
    _selectedCatalogClassificationCode = button.dataset.catalogClassificationCode || "";
    renderCatalogClassificationTree();
    applyFilter();
  });
});
