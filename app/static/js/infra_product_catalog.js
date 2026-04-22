/* ── 제품 카탈로그 ── */

const LICENSE_TYPE_LABELS = {
  perpetual: "영구", subscription: "구독", eval: "평가", oem: "OEM",
};
const LICENSE_UNIT_LABELS = {
  site: "사이트별", host: "호스트별", core: "코어별", user: "사용자별",
  device: "장비별", instance: "인스턴스별", session: "세션별", cpu: "CPU별",
};

let catalogGridApi, ifaceGridApi;
let currentProductId = null;
let currentProductType = null;
let _currentProductIsPlaceholder = false;
let _catalogImportPreviewReady = false;
let _catalogRows = [];
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
const CATALOG_GRID_COLUMN_STATE_KEY = "catalog_grid_column_state_v2";
const CATALOG_CLASSIFICATION_COLLAPSED_KEY = "catalog_classification_collapsed_nodes";
const CATALOG_DETAIL_OPEN_KEY = "catalog_detail_open";
const CATALOG_DETAIL_LAST_ID_KEY = "catalog_detail_last_id";
const CATALOG_LAYOUT_PRESET_KEY = "catalog_layout_preset_id";
const CATALOG_CLASSIFICATION_SEARCH_KEY = "catalog_classification_search_query";
const CATALOG_TREE_ACTION_MODE_KEY = "catalog.classification.treeActionMode";
let _catalogClassificationScheme = null;
let _catalogClassificationEditMode = false;
let _catalogLayoutDetail = null;
let _catalogLayouts = [];
let _catalogAttributeDefs = [];
let _catalogClassificationSearchQuery = "";
const _catalogAttributeOptionCache = new Map();
let _catalogClassificationSchemeEditing = false;
let _catalogTreeActionMode = localStorage.getItem(CATALOG_TREE_ACTION_MODE_KEY) || "compact";
const _catalogExpandedTreeActions = new Set();

const CATALOG_LABEL_LANG_PREF_KEY = "catalog.label_lang";
let _catalogLabelLang = "ko";

function getCatalogLabelLang() {
  return _catalogLabelLang;
}

function setCatalogLabelLang(lang) {
  _catalogLabelLang = lang === "en" ? "en" : "ko";
  apiFetch(`/api/v1/preferences/${CATALOG_LABEL_LANG_PREF_KEY}`, {
    method: "PATCH",
    body: { value: _catalogLabelLang },
  }).catch(() => {});
}

async function loadCatalogLabelLangPreference() {
  try {
    const pref = await apiFetch(`/api/v1/preferences/${CATALOG_LABEL_LANG_PREF_KEY}`);
    if (pref?.value === "en" || pref?.value === "ko") _catalogLabelLang = pref.value;
  } catch { /* 기본값 ko 유지 */ }
}

function getCatalogOptionDisplayLabel(option) {
  if (!option) return "";
  const lang = getCatalogLabelLang();
  if (lang === "ko") return option.label_kr || option.label || option.option_key;
  return option.label || option.option_key;
}

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

async function loadCatalogTaxonomyContext() {
  try {
    const [attrDefs, layouts] = await Promise.all([
      apiFetch("/api/v1/catalog-attributes"),
      apiFetch("/api/v1/classification-layouts?scope_type=global&active_only=true"),
    ]);
    _catalogAttributeDefs = attrDefs;
    _catalogLayouts = Array.isArray(layouts) ? layouts : [];
    const preferredId = Number(localStorage.getItem(CATALOG_LAYOUT_PRESET_KEY) || 0);
    const targetLayout = _catalogLayouts.find((item) => Number(item.id) === preferredId)
      || _catalogLayouts.find((item) => item.is_default)
      || _catalogLayouts[0]
      || null;
    _catalogLayoutDetail = targetLayout ? await apiFetch(`/api/v1/classification-layouts/${targetLayout.id}`) : null;
    if (_catalogLayoutDetail?.id) {
      localStorage.setItem(CATALOG_LAYOUT_PRESET_KEY, String(_catalogLayoutDetail.id));
    }
    loadCatalogClassificationCollapsedState();
    refreshCatalogLayoutPresetSelect();
  } catch (err) {
    _catalogAttributeDefs = [];
    _catalogLayouts = [];
    _catalogLayoutDetail = null;
    console.error(err);
  }
}

function getCatalogClassificationCollapsedStorageKey() {
  const layoutId = Number(_catalogLayoutDetail?.id || 0);
  return layoutId > 0
    ? `${CATALOG_CLASSIFICATION_COLLAPSED_KEY}:${layoutId}`
    : CATALOG_CLASSIFICATION_COLLAPSED_KEY;
}

function refreshCatalogLayoutPresetSelect() {
  const select = document.getElementById("catalog-layout-preset-select");
  if (!select) return;
  const currentId = String(_catalogLayoutDetail?.id || "");
  select.textContent = "";
  _catalogLayouts.forEach((layout) => {
    const option = document.createElement("option");
    option.value = String(layout.id);
    option.textContent = layout.name;
    select.appendChild(option);
  });
  select.value = currentId && [...select.options].some((option) => option.value === currentId)
    ? currentId
    : (select.options[0]?.value || "");
}

function getCatalogLayoutLevel(levelNo) {
  return _catalogLayoutDetail?.levels?.find((item) => Number(item.level_no) === Number(levelNo)) || null;
}

function getCatalogPrimaryLevelKey(levelNo) {
  return getCatalogLayoutLevel(levelNo)?.keys?.[0]?.attribute_key || null;
}

function getCatalogConfiguredLevelKey(levelNo) {
  return document.getElementById(`catalog-classification-scheme-level-${levelNo}-key`)?.value
    || getCatalogPrimaryLevelKey(levelNo)
    || "";
}

function getCatalogAttributeDef(attributeKey) {
  return _catalogAttributeDefs.find((item) => item.attribute_key === attributeKey) || null;
}

function isCatalogPrimaryAttributeKey(attributeKey) {
  return ["domain", "imp_type"].includes(String(attributeKey || ""));
}

function isCatalogClassificationAttributeKey(attributeKey) {
  return !["vendor_series", "license_model"].includes(String(attributeKey || ""));
}

function getCatalogAttributeDisplayLabel(attributeKey, fallbackLabel = "") {
  const attribute = getCatalogAttributeDef(attributeKey);
  const baseLabel = attribute?.label || fallbackLabel || attributeKey || "";
  return isCatalogPrimaryAttributeKey(attributeKey) ? `${baseLabel} (기준축)` : baseLabel;
}

function getCatalogAttributeDescription(attributeKey) {
  const attribute = getCatalogAttributeDef(attributeKey);
  return (attribute?.description || "").trim();
}

function getDisplayableCatalogAttributes() {
  return (_catalogAttributeDefs || [])
    .filter((item) => item.is_active !== false && item.is_displayable !== false && isCatalogClassificationAttributeKey(item.attribute_key))
    .sort((a, b) => (a.sort_order ?? 100) - (b.sort_order ?? 100) || String(a.label || "").localeCompare(String(b.label || ""), "ko-KR"));
}

function getCatalogNodeOptionLabel(nodeName, levelNo) {
  const level = getCatalogLayoutLevel(levelNo);
  const joiner = level?.joiner || ", ";
  if (!nodeName) return "";
  if (!joiner || !nodeName.includes(joiner)) return nodeName.trim();
  return nodeName.split(joiner)[0].trim();
}

async function loadCatalogAttributeOptions(attributeKey, activeOnly = false) {
  const cacheKey = `${attributeKey}:${activeOnly ? "active" : "all"}`;
  if (_catalogAttributeOptionCache.has(cacheKey)) {
    return _catalogAttributeOptionCache.get(cacheKey);
  }
  const attribute = getCatalogAttributeDef(attributeKey);
  if (!attribute) return [];
  const items = await apiFetch(`/api/v1/catalog-attributes/${attribute.id}/options?active_only=${activeOnly ? "true" : "false"}`);
  _catalogAttributeOptionCache.set(cacheKey, items);
  return items;
}

function invalidateCatalogCoreAttributeOptionCaches() {
  ["domain", "imp_type", "product_family", "platform"].forEach((attributeKey) => {
    invalidateCatalogAttributeOptionCache(attributeKey);
  });
}

function invalidateCatalogAttributeOptionCache(attributeKey = null) {
  if (!attributeKey) {
    _catalogAttributeOptionCache.clear();
    return;
  }
  [..._catalogAttributeOptionCache.keys()]
    .filter((key) => key.startsWith(`${attributeKey}:`))
    .forEach((key) => _catalogAttributeOptionCache.delete(key));
}

function populateCatalogLayoutKeySelect(levelNo, selectedKey = "") {
  const select = document.getElementById(`catalog-classification-scheme-level-${levelNo}-key`);
  if (!select) return;
  const currentSelections = new Set();
  for (let idx = 1; idx <= 5; idx += 1) {
    if (idx === levelNo) continue;
    const value = document.getElementById(`catalog-classification-scheme-level-${idx}-key`)?.value || "";
    if (value) currentSelections.add(value);
  }
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "-- 키 선택 --";
  select.appendChild(empty);
  const availableAttributes = getDisplayableCatalogAttributes().filter((attribute) => {
    if (levelNo === 1) {
      return ["domain", "imp_type"].includes(attribute.attribute_key);
    }
    return true;
  });
  availableAttributes.forEach((attribute) => {
    if (currentSelections.has(attribute.attribute_key) && attribute.attribute_key !== selectedKey) return;
    const option = document.createElement("option");
    option.value = attribute.attribute_key;
    option.textContent = `${getCatalogAttributeDisplayLabel(attribute.attribute_key, attribute.label)} (${attribute.attribute_key})`;
    select.appendChild(option);
  });
  if (levelNo === 1) {
    empty.disabled = true;
    const nextValue = availableAttributes.some((item) => item.attribute_key === selectedKey)
      ? selectedKey
      : (availableAttributes.find((item) => item.attribute_key === "domain")?.attribute_key
        || availableAttributes[0]?.attribute_key
        || "");
    select.value = nextValue;
  } else {
    const nextValue = availableAttributes.some((item) => item.attribute_key === selectedKey)
      ? selectedKey
      : "";
    select.value = nextValue;
  }
  const description = getCatalogAttributeDescription(select.value || "");
  select.title = description || "키 설명 없음";
  const help = document.getElementById(`catalog-classification-scheme-level-${levelNo}-key-help`);
  if (help) {
    help.textContent = description || "";
  }
}

function syncCatalogLayoutKeyOptions() {
  const selectedKeys = new Map();
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    const select = document.getElementById(`catalog-classification-scheme-level-${levelNo}-key`);
    selectedKeys.set(levelNo, select?.value || "");
  }
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    populateCatalogLayoutKeySelect(levelNo, selectedKeys.get(levelNo) || "");
  }
}

function getCatalogComplementaryPrimaryKey(attributeKey) {
  if (attributeKey === "domain") return "imp_type";
  if (attributeKey === "imp_type") return "domain";
  return "";
}

function handleCatalogPrimaryLevelKeyChange() {
  const level1Select = document.getElementById("catalog-classification-scheme-level-1-key");
  const level2Select = document.getElementById("catalog-classification-scheme-level-2-key");
  if (!level1Select) return;
  const level1Key = level1Select.value || "domain";
  const complementaryKey = getCatalogComplementaryPrimaryKey(level1Key);
  if (level2Select && (!level2Select.value || level2Select.value === getCatalogComplementaryPrimaryKey(complementaryKey))) {
    level2Select.value = complementaryKey;
  }
  syncCatalogLayoutKeyOptions();
}

function getCatalogLayoutConfiguredDepth() {
  let depthCount = 1;
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    const checkbox = document.getElementById(`catalog-classification-scheme-level-${levelNo}-enabled`);
    if (checkbox?.checked) depthCount = levelNo;
  }
  return depthCount;
}

function normalizeCatalogLayoutLevelEnabledState(changedLevelNo = null) {
  const level1 = document.getElementById("catalog-classification-scheme-level-1-enabled");
  if (level1) level1.checked = true;
  if (!changedLevelNo || changedLevelNo <= 1) return;
  const changed = document.getElementById(`catalog-classification-scheme-level-${changedLevelNo}-enabled`);
  if (!changed) return;
  if (changed.checked) {
    for (let levelNo = 1; levelNo <= changedLevelNo; levelNo += 1) {
      const checkbox = document.getElementById(`catalog-classification-scheme-level-${levelNo}-enabled`);
      if (checkbox) checkbox.checked = true;
    }
    return;
  }
  for (let levelNo = changedLevelNo; levelNo <= 5; levelNo += 1) {
    const checkbox = document.getElementById(`catalog-classification-scheme-level-${levelNo}-enabled`);
    if (checkbox) checkbox.checked = false;
  }
}

function updateCatalogLayoutLevelVisibility() {
  normalizeCatalogLayoutLevelEnabledState();
  const depthCount = getCatalogLayoutConfiguredDepth();
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    const row = document.querySelector(`.catalog-layout-level-row[data-level-row="${levelNo}"]`);
    const checkbox = document.getElementById(`catalog-classification-scheme-level-${levelNo}-enabled`);
    const aliasInput = document.getElementById(`catalog-classification-scheme-level-${levelNo}-alias`);
    const keySelect = document.getElementById(`catalog-classification-scheme-level-${levelNo}-key`);
    const enabled = levelNo <= depthCount;
    if (row) {
      row.classList.toggle("is-disabled", !_catalogClassificationSchemeEditing && !enabled);
      row.classList.toggle("is-readonly", !_catalogClassificationSchemeEditing);
    }
    if (checkbox) checkbox.disabled = !_catalogClassificationSchemeEditing || levelNo === 1;
    if (aliasInput) aliasInput.disabled = !_catalogClassificationSchemeEditing || !enabled;
    if (keySelect) keySelect.disabled = !_catalogClassificationSchemeEditing || !enabled;
  }
  const savePresetButton = document.getElementById("btn-catalog-classification-scheme-save-preset");
  if (savePresetButton) savePresetButton.disabled = !_catalogClassificationSchemeEditing;
  const submitButton = document.getElementById("btn-catalog-classification-scheme-submit");
  if (submitButton) submitButton.textContent = _catalogClassificationSchemeEditing ? "저장" : "편집";
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
  setButtonAvailability("btn-catalog-classification-scheme-save-preset", canTaxonomy, "카탈로그 기준 관리 권한이 없습니다.");
  const editToolbar = document.getElementById("catalog-classification-edit-toolbar");
  if (editToolbar) editToolbar.classList.toggle("is-hidden", !_catalogClassificationEditMode || !canTaxonomy);
  const editToggle = document.getElementById("btn-catalog-classification-edit-toggle");
  if (editToggle) editToggle.textContent = _catalogClassificationEditMode ? "편집 종료" : "편집";
}

async function loadCatalogClassificationLeaves() {
  await rebuildCatalogClassificationTree(_catalogRows || []);
}

function loadCatalogClassificationCollapsedState() {
  try {
    const scopedKey = getCatalogClassificationCollapsedStorageKey();
    const raw = localStorage.getItem(scopedKey) || localStorage.getItem(CATALOG_CLASSIFICATION_COLLAPSED_KEY);
    if (!raw) return;
    const ids = JSON.parse(raw);
    if (!Array.isArray(ids)) return;
    _catalogClassificationCollapsed.clear();
    ids
      .map((value) => String(value || "").trim())
      .filter(Boolean)
      .forEach((value) => _catalogClassificationCollapsed.add(value));
  } catch (_) {
    _catalogClassificationCollapsed.clear();
  }
}

function getCatalogRowClassificationToken(row) {
  const parts = [
    row.classification_level_1_name,
    row.classification_level_2_name,
    row.classification_level_3_name,
    row.classification_level_4_name,
    row.classification_level_5_name,
  ].filter(Boolean);
  return parts.length ? parts.join(">") : `product-${row.id}`;
}

function buildCatalogPathLabel(row) {
  const parts = [
    row.classification_level_1_name,
    row.classification_level_2_name,
    row.classification_level_3_name,
    row.classification_level_4_name,
    row.classification_level_5_name,
  ].filter(Boolean);
  return parts.join(" > ") || "-";
}

function saveCatalogClassificationCollapsedState() {
  localStorage.setItem(
    getCatalogClassificationCollapsedStorageKey(),
    JSON.stringify([..._catalogClassificationCollapsed]),
  );
}

function _catalogGridStateKey() {
  const presetId = localStorage.getItem(CATALOG_LAYOUT_PRESET_KEY) || "default";
  return CATALOG_GRID_COLUMN_STATE_KEY + ":" + presetId;
}

function getStoredCatalogGridColumnState() {
  const raw = localStorage.getItem(_catalogGridStateKey());
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
  localStorage.setItem(_catalogGridStateKey(), JSON.stringify(state));
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

function buildCatalogColDefs() {
  const cols = [
    { field: "vendor", headerName: "제조사", width: 120, sort: "asc" },
    { field: "name", headerName: "모델명", flex: 1, minWidth: 160 },
  ];

  /* 레이아웃에 배치된 속성 키 (순서 보존) */
  const layoutKeys = [];
  const layoutAliasMap = new Map();
  if (_catalogLayoutDetail?.levels?.length) {
    _catalogLayoutDetail.levels
      .slice()
      .sort((a, b) => Number(a.level_no) - Number(b.level_no))
      .forEach((level) => {
        (level.keys || []).forEach((key) => {
          const attrKey = key.attribute_key;
          if (attrKey && !layoutKeys.includes(attrKey)) {
            layoutKeys.push(attrKey);
            if (level.alias) layoutAliasMap.set(attrKey, level.alias);
          }
        });
      });
  }

  /* 레이아웃 외 displayable 속성 */
  const allDisplayable = getDisplayableCatalogAttributes();
  const layoutKeySet = new Set(layoutKeys);
  const remainingAttrs = allDisplayable.filter((attr) => !layoutKeySet.has(attr.attribute_key));

  /* 레이아웃 순서 속성 → 나머지 속성 */
  const orderedKeys = [
    ...layoutKeys.map((key) => ({
      key,
      header: layoutAliasMap.get(key) || getCatalogAttributeDef(key)?.label || key,
    })),
    ...remainingAttrs.map((attr) => ({
      key: attr.attribute_key,
      header: attr.label || attr.attribute_key,
    })),
  ];
  orderedKeys.forEach(({ key, header }) => {
    cols.push({
      field: `attr_${key}`,
      headerName: header,
      width: 130,
      valueFormatter: (p) => p.value || "-",
    });
  });

  cols.push({
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
  });
  return cols;
}

let catalogColDefs = [];

function getCatalogClassificationAliases() {
  if (_catalogLayoutDetail?.levels?.length) {
    const aliases = [...CATALOG_LEVEL_ALIAS_DEFAULTS];
    _catalogLayoutDetail.levels.forEach((level) => {
      const index = Math.max(Number(level.level_no || 1) - 1, 0);
      aliases[index] = level.alias || aliases[index];
    });
    return aliases;
  }
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
  catalogColDefs = buildCatalogColDefs();
  const treeTitle = document.getElementById("catalog-classification-title");
  if (treeTitle) treeTitle.textContent = getCatalogLeafAlias();
  if (catalogGridApi) {
    catalogGridApi.setGridOption("columnDefs", catalogColDefs);
    const restored = restoreCatalogGridColumnState();
    if (!restored) fitCatalogGridColumnsIfNeeded();
  }
}

function renderCatalogClassificationSummary() {
  const container = document.getElementById("catalog-classification-summary-stats");
  if (!container) return;
  if (!_catalogLayoutDetail && !_catalogClassificationScheme) {
    container.innerHTML = `
      <div class="classification-stat"><span class="classification-stat-label">레이아웃</span><span class="classification-stat-value">미설정</span></div>
      <div class="classification-stat"><span class="classification-stat-label">노드 수</span><span class="classification-stat-value">0</span></div>
    `;
    return;
  }
  if (_catalogLayoutDetail) {
    container.innerHTML = `
      <div class="classification-stat"><span class="classification-stat-label">깊이</span><span class="classification-stat-value">${_catalogLayoutDetail.depth_count ?? _catalogLayoutDetail.levels?.length ?? 0}</span></div>
    `;
    return;
  }
  container.innerHTML = `
    <div class="classification-stat"><span class="classification-stat-label">노드 수</span><span class="classification-stat-value">${_catalogClassificationScheme.node_count ?? _catalogClassificationNodes.length}</span></div>
  `;
}

function updateCatalogTreeModeBtn() {
  const btn = document.getElementById("btn-catalog-tree-mode");
  if (!btn) return;
  const detail = _catalogTreeActionMode === "detail";
  btn.textContent = detail ? "간단히" : "자세히";
  btn.className = "btn btn-secondary btn-sm" + (detail ? " is-active" : "");
  btn.title = detail ? "모든 분류 노드 액션 항상 표시" : "노드별 작은 토글로 액션 표시";
}

function isCatalogTreeActionExpanded(nodeId) {
  return _catalogTreeActionMode === "detail" || _catalogExpandedTreeActions.has(nodeId);
}

function toggleCatalogTreeActionMenu(nodeId) {
  if (_catalogTreeActionMode === "detail") return;
  const isOpen = _catalogExpandedTreeActions.has(nodeId);
  _catalogExpandedTreeActions.clear();
  if (!isOpen) _catalogExpandedTreeActions.add(nodeId);
  renderCatalogClassificationTree();
}

function isCatalogNodeWithinSelectedBranch(node) {
  if (!_selectedCatalogClassificationCode) return true;
  const target = String(_selectedCatalogClassificationCode || "");
  const current = String(node?.node_code || "");
  if (!target || !current) return true;
  return current === target || current.startsWith(`${target}>`) || target.startsWith(`${current}>`);
}

function getCatalogNodeLevelClass(node) {
  const level = Number(node?.level || 0);
  return level > 0 ? ` classification-tree-node-level-${level}` : "";
}

function canCatalogNodeAddChild(node) {
  const maxDepth = Number(_catalogLayoutDetail?.depth_count || 3);
  return Number(node?.level || 0) < maxDepth;
}

function initCatalogGrid() {
  catalogGridApi = agGrid.createGrid(document.getElementById("grid-catalog"), {
    columnDefs: catalogColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => selectProduct(data),
    }),
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
  initCatalogColChooser();
}

function initCatalogColChooser() {
  const btn = document.getElementById("btn-catalog-col-chooser");
  const menu = document.getElementById("catalog-col-chooser-menu");
  if (!btn || !menu) return;
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    if (menu.classList.contains("is-hidden")) {
      renderCatalogColChooserMenu();
      menu.classList.remove("is-hidden");
    } else {
      menu.classList.add("is-hidden");
    }
  });
  menu.addEventListener("change", (e) => {
    if (e.target.type !== "checkbox") return;
    catalogGridApi.setColumnVisible(e.target.dataset.field, e.target.checked);
    saveCatalogGridColumnState();
  });
  menu.addEventListener("click", (e) => e.stopPropagation());
  document.addEventListener("click", () => menu.classList.add("is-hidden"));
}

function renderCatalogColChooserMenu() {
  const menu = document.getElementById("catalog-col-chooser-menu");
  if (!menu || !catalogGridApi) return;
  const stateMap = Object.fromEntries(catalogGridApi.getColumnState().map((s) => [s.colId, s]));
  const toggleable = catalogColDefs.filter((c) => c.field && c.field !== "vendor" && c.field !== "name");
  menu.replaceChildren();
  toggleable.forEach((col) => {
    const visible = !stateMap[col.field]?.hide;
    const label = document.createElement("label");
    label.className = "col-chooser-item";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.field = col.field;
    checkbox.checked = visible;
    label.appendChild(checkbox);
    label.appendChild(document.createTextNode(` ${col.headerName}`));
    menu.appendChild(label);
  });
}

async function loadCatalog() {
  try {
    const rawData = await apiFetch("/api/v1/product-catalog");
    const data = await projectCatalogRowsForCurrentLayout(rawData);
    _catalogRows = data;
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

    await rebuildCatalogClassificationTree(data);
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

async function rebuildCatalogClassificationTree(rows) {
  const depthCount = _catalogLayoutDetail?.depth_count || 3;
  const aliases = getCatalogClassificationAliases();
  _catalogClassificationScheme = {
    name: "동적 레이아웃",
    node_count: rows.length,
  };
  for (let i = 1; i <= depthCount; i++) {
    _catalogClassificationScheme[`level_${i}_alias`] = aliases[i - 1] || CATALOG_LEVEL_ALIAS_DEFAULTS[i - 1] || `${i}레벨`;
  }
  _catalogClassificationLeafOptions = [];
  _catalogClassificationNodes = [];
  _catalogClassificationNodeMap = new Map();
  applyCatalogClassificationAliases();
  const treeMap = new Map();
  const nodeList = [];
  const levelKeys = [];
  for (let levelNo = 1; levelNo <= (_catalogLayoutDetail?.depth_count || 3); levelNo += 1) {
    const attributeKey = getCatalogConfiguredLevelKey(levelNo);
    if (!attributeKey) break;
    levelKeys.push({ levelNo, attributeKey });
  }
  const levelOptionArrays = await Promise.all(
    levelKeys.map(({ attributeKey }) => loadCatalogAttributeOptions(attributeKey, true)),
  );
  const levelDefinitions = levelKeys.map(({ levelNo, attributeKey }, idx) => ({
    levelNo,
    attributeKey,
    optionMap: new Map(levelOptionArrays[idx].map((item) => [item.option_key, item])),
  }));

  function ensureNode(levelNo, optionKey, optionLabel, parentNode = null, optionData = null) {
    const codePath = [...(parentNode?.code_path || []), optionKey];
    const labelPath = [...(parentNode?.label_path || []), optionLabel];
    const nodeId = codePath.join(">");
    if (!treeMap.has(nodeId)) {
      const node = {
        id: nodeId,
        parent_id: parentNode?.id || null,
        node_code: nodeId,
        node_name: optionLabel,
        path_label: labelPath.join(" > "),
        level: levelNo,
        sort_order: levelNo * 10,
        is_active: true,
        selected_codes: new Set(),
        code_path: codePath,
        label_path: labelPath,
        option_data: optionData,
      };
      treeMap.set(nodeId, node);
      nodeList.push(node);
    }
    return treeMap.get(nodeId);
  }

  rows.forEach((row) => {
    const values = getProductAttributeValueMap(row.attributes || []);
    const segments = levelDefinitions
      .map((level) => {
        const optionKey = values[level.attributeKey] || "";
        if (!optionKey) return null;
        const option = level.optionMap.get(optionKey);
        const lang = getCatalogLabelLang();
        const optionLabel = option
          ? (lang === "ko" ? (option.label_kr || option.label || optionKey) : (option.label || optionKey))
          : (row[`classification_level_${level.levelNo}_name`] || optionKey);
        return { levelNo: level.levelNo, optionKey, optionLabel, optionData: option || null };
      })
      .filter(Boolean);
    if (!segments.length) return;
    const leafToken = getCatalogRowClassificationToken(row);
    let parentNode = null;
    segments.forEach((segment, idx) => {
      const currentNode = ensureNode(segment.levelNo, segment.optionKey, segment.optionLabel, parentNode, segment.optionData);
      currentNode.selected_codes.add(leafToken);
      parentNode = currentNode;
    });
    if (segments.length) {
      _catalogClassificationLeafOptions.push({
        value: segments.map((item) => item.optionKey).join(">"),
        label: buildCatalogPathLabel(row),
      });
    }
  });

  _catalogClassificationNodes = nodeList;
  const activeNodeIds = new Set(_catalogClassificationNodes.map((node) => node.id));
  [..._catalogClassificationCollapsed].forEach((nodeId) => {
    if (!activeNodeIds.has(nodeId)) _catalogClassificationCollapsed.delete(nodeId);
  });
  saveCatalogClassificationCollapsedState();
  _catalogClassificationNodes.forEach((node) => {
    _catalogClassificationNodeMap.set(node.node_code, node);
  });
  _catalogClassificationLeafOptions = _catalogClassificationLeafOptions
    .filter((item, index, list) => item.value && list.findIndex((candidate) => candidate.value === item.value) === index)
    .sort((a, b) => a.label.localeCompare(b.label, "ko-KR"));
  syncCatalogAttributeInputs().catch((err) => console.error(err));
  renderCatalogClassificationSummary();
  renderCatalogClassificationTree();
}

function fillCatalogAttributeSelect(elementId, options, selectedValue = "") {
  const select = document.getElementById(elementId);
  if (!select) return;
  const placeholder = select.querySelector("option[value='']")?.textContent || "-- 선택 --";
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = placeholder;
  select.appendChild(empty);
  options.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.value;
    opt.textContent = item.label;
    select.appendChild(opt);
  });
  select.value = selectedValue || "";
}

function getScopedProductFamilyOptions(domainKey = "") {
  const cached = _catalogAttributeOptionCache.get("product_family:active") || _catalogAttributeOptionCache.get("product_family:all") || [];
  return cached.filter((item) => !item.domain_option_key || !domainKey || item.domain_option_key === domainKey);
}

function syncProductFamilySelect(selectedValue = "") {
  syncFamilyCombobox(selectedValue);
}

async function syncCatalogAttributeInputs(values = {}, forceRefresh = false) {
  if (forceRefresh) {
    invalidateCatalogCoreAttributeOptionCaches();
  }
  await loadCatalogAttributeOptions("domain", true);
  const impTypeOptions = await loadCatalogAttributeOptions("imp_type", true);
  await loadCatalogAttributeOptions("product_family", true);
  const platformOptions = await loadCatalogAttributeOptions("platform", true);
  /* domain은 hidden input — product_family 선택으로 자동 결정 */
  document.getElementById("product-attr-domain").value = values.domain || "";
  fillCatalogAttributeSelect("product-attr-imp-type", impTypeOptions.map((item) => ({ value: item.option_key, label: item.label })), values.imp_type);
  syncProductFamilySelect(values.product_family || "");
  fillCatalogAttributeSelect("product-attr-platform", platformOptions.map((item) => ({ value: item.option_key, label: item.label })), values.platform);
  syncCatalogPrimaryAttributeLabels();
  updateCatalogClassificationHint();
}

function getCatalogAttributeLabel(attributeKey, optionKey) {
  if (!optionKey) return "";
  const cached = _catalogAttributeOptionCache.get(`${attributeKey}:active`) || _catalogAttributeOptionCache.get(`${attributeKey}:all`) || [];
  return cached.find((item) => item.option_key === optionKey)?.label || optionKey;
}

function syncCatalogPrimaryAttributeLabels() {
  const domainLabel = document.querySelector("[data-product-attr-label='domain'] .catalog-field-label-text");
  const impTypeLabel = document.querySelector("[data-product-attr-label='imp_type'] .catalog-field-label-text");
  if (domainLabel) domainLabel.textContent = getCatalogAttributeDisplayLabel("domain", "도메인");
  if (impTypeLabel) impTypeLabel.textContent = getCatalogAttributeDisplayLabel("imp_type", "구현형태");
}

function getCatalogAttributeValuesFromForm() {
  const familyKey = document.getElementById("product-attr-product-family")?.value || "";
  return {
    domain: getDomainKeyForFamily(familyKey) || document.getElementById("product-attr-domain")?.value || "",
    imp_type: document.getElementById("product-attr-imp-type")?.value || "",
    product_family: familyKey,
    platform: document.getElementById("product-attr-platform")?.value || "",
  };
}

let _productNameListCache = [];

function resetProductSimilarityBox() {
  if (_productNameCombobox) {
    _productNameCombobox.reset();
  }
}

async function loadProductNameList(excludeId = null) {
  try {
    const items = await apiFetch("/api/v1/product-catalog");
    _productNameListCache = items;
    const combo = getProductNameCombobox();
    combo.setItems(
      items
        .filter((item) => !excludeId || item.id !== excludeId)
        .map((item) => ({
          value: String(item.id),
          label: ((item.vendor || "") + " " + (item.name || "")).trim(),
          hint: item.product_type || "",
          aliases: [item.vendor || "", item.name || ""],
          modelName: item.name || "",
        }))
    );
  } catch (e) {
    console.error("product name list load error:", e);
  }
}

function bindProductSimilarityInputs() {
  getProductNameCombobox();
}

function buildCatalogAttributePayload(values) {
  const payload = [
    { attribute_key: "domain", option_key: values.domain, raw_value: null },
    { attribute_key: "imp_type", option_key: values.imp_type, raw_value: null },
    { attribute_key: "product_family", option_key: values.product_family, raw_value: null },
  ];
  if (values.platform) {
    payload.push({ attribute_key: "platform", option_key: values.platform, raw_value: null });
  }
  return payload;
}

function getDefaultImpTypeForProductType(productType) {
  switch (productType) {
    case "hardware":
      return "hw";
    case "software":
    case "model":
      return "sw";
    case "service":
    case "business_capability":
    case "dataset":
      return "svc";
    default:
      return "";
  }
}

/* product_family → default imp_type 매핑 */
const _PRODUCT_FAMILY_DEFAULT_IMP_TYPE = {
  /* 네트워크 장비 (hw) */
  fw: "hw", utm: "hw", ips: "hw", ids: "hw", waf: "hw", ddos: "hw", vpn: "hw",
  l2: "hw", l3: "hw", l4: "hw", router: "hw", switch: "hw",
  adc: "hw", load_balancer: "hw", sdwan: "hw", packet_broker: "hw", optical: "hw",
  access_point: "hw", wlan_controller: "hw",
  /* 서버 장비 (hw) */
  x86_server: "hw", unix_server: "hw", blade_server: "hw", gpu_server: "hw",
  /* 스토리지 장비 (hw) */
  nas: "hw", san: "hw", tape: "hw",
  /* 소프트웨어 (sw) */
  dns: "sw", dhcp_ipam: "sw", nms: "sw", monitoring: "sw",
  siem: "sw", soar: "sw", dlp: "sw", edr: "sw", xdr: "sw",
  iam: "sw", pam: "sw", pki: "sw", proxy: "sw", mail_security: "sw",
  ztna: "sw", nac: "sw", sandbox: "sw", sase: "sw", casb: "sw", cspm: "sw",
  anti_malware: "sw", threat_intel: "sw", db_access_control: "sw", swg: "sw", sspm: "sw",
  virtualization: "sw", container_platform: "sw", hci: "sw", vdi: "sw", hypervisor: "sw",
  web_server: "sw", was: "sw", os: "sw", middleware: "sw",
  cache: "sw", message_queue: "sw", etl: "sw", batch_scheduler: "sw",
  devops: "sw", config_mgmt: "sw", ci_cd: "sw", log_mgmt: "sw", automation: "sw", api_gateway: "sw",
  dbms: "sw", db_replication: "sw", nosql: "sw", data_warehouse: "sw",
  db_encryption: "sw", in_memory_db: "sw",
  backup: "sw", backup_sw: "sw", sds: "sw", cdp: "sw",
  generic: "hw",
};

function getDefaultImpTypeForFamily(familyKey) {
  return _PRODUCT_FAMILY_DEFAULT_IMP_TYPE[familyKey] || "";
}

function getProductTypeFromImpType(impTypeKey) {
  switch (impTypeKey) {
    case "hw": return "hardware";
    case "sw": return "software";
    case "svc": return "service";
    default: return "hardware";
  }
}

/* ── 모델명 combobox (유사 제품 검색) ── */

let _productNameCombobox = null;

function getProductNameCombobox() {
  if (!_productNameCombobox) {
    _productNameCombobox = new ModalCombobox({
      inputId: "product-name",
      hiddenId: "product-name-ref-id",
      dropdownId: "product-name-dropdown",
      maxDisplay: 50,
      onSelect: async (item) => {
        await fillFormFromSimilarProduct(item.value);
        // ModalCombobox sets input to full label (vendor + name).
        // Override with just the model name for editing convenience.
        const matched = (_productNameCombobox?.items || []).find((i) => i.value === item.value);
        if (matched?.modelName) {
          document.getElementById("product-name").value = matched.modelName;
        }
      },
    });
    _productNameCombobox.bind();
  }
  return _productNameCombobox;
}

async function fillFormFromSimilarProduct(productId) {
  try {
    const d = await apiFetch("/api/v1/product-catalog/" + productId);
    const attrMap = getProductAttributeValueMap(d.attributes || []);
    // Vendor
    const vendorInput = document.getElementById("product-vendor");
    const vendorValue = document.getElementById("product-vendor-value");
    if (vendorInput) vendorInput.value = d.vendor || "";
    if (vendorValue) vendorValue.value = d.vendor || "";
    // Product type
    const typeInput = document.getElementById("product-type");
    if (typeInput) typeInput.value = d.product_type || "hardware";
    // Name — keep what the user typed (don't overwrite)
    // Classification attributes
    if (attrMap.product_family) {
      syncFamilyCombobox(attrMap.product_family);
      const domainKey = getDomainKeyForFamily(attrMap.product_family);
      if (domainKey) document.getElementById("product-attr-domain").value = domainKey;
    }
    if (attrMap.imp_type) {
      const impSelect = document.getElementById("product-attr-imp-type");
      if (impSelect) {
        impSelect.value = attrMap.imp_type;
        impSelect.dataset.autoSet = "true";
      }
    }
    if (attrMap.platform) {
      const platSelect = document.getElementById("product-attr-platform");
      if (platSelect) platSelect.value = attrMap.platform;
    }
    // Reference URL
    if (d.reference_url) {
      document.getElementById("product-reference-url").value = d.reference_url;
    }
    updateCatalogClassificationHint();
    showToast("유사 제품 정보를 불러왔습니다. 모델명을 수정하세요.", "info");
  } catch (e) {
    showToast("제품 정보를 불러올 수 없습니다: " + e.message, "error");
  }
}

/* ── 제조사 combobox ── */

let _vendorListCache = null;
let _vendorCombobox = null;

async function loadVendorList(forceRefresh = false) {
  if (!forceRefresh && _vendorListCache) return _vendorListCache;
  try {
    const vendors = await apiFetch("/api/v1/catalog-integrity/vendors");
    _vendorListCache = vendors
      .filter((v) => v.vendor)
      .map((v) => ({
        vendor: v.vendor,
        name_ko: v.name_ko || "",
        aliases: (v.aliases || [])
          .filter((a) => a.is_active && a.alias_value !== v.vendor)
          .map((a) => a.alias_value),
      }))
      .sort((a, b) => a.vendor.localeCompare(b.vendor, "ko-KR"));
    return _vendorListCache;
  } catch (err) {
    console.error("vendor list load error:", err);
    return _vendorListCache || [];
  }
}

function getVendorCombobox() {
  if (!_vendorCombobox) {
    _vendorCombobox = new ModalCombobox({
      inputId: "product-vendor",
      hiddenId: "product-vendor-value",
      dropdownId: "product-vendor-dropdown",
      onSelect: () => {},
    });
    _vendorCombobox.bind();
  }
  return _vendorCombobox;
}

function syncVendorCombobox(selectedValue = "") {
  const combo = getVendorCombobox();
  combo.setItems((_vendorListCache || []).map((v) => ({
    value: v.vendor,
    label: v.vendor,
    hint: v.name_ko || "",
    aliases: v.aliases,
  })));
  combo.setValue(selectedValue, selectedValue);
}

/* ── 제품군 combobox ── */

let _familyCombobox = null;

function getFamilyCombobox() {
  if (!_familyCombobox) {
    _familyCombobox = new ModalCombobox({
      inputId: "product-family-input",
      hiddenId: "product-attr-product-family",
      dropdownId: "product-family-dropdown",
      onSelect: (item) => {
        /* 제품군 선택 → domain 자동 결정 + imp_type 기본값 */
        const familyKey = item.value;
        const domainKey = getDomainKeyForFamily(familyKey);
        document.getElementById("product-attr-domain").value = domainKey;
        const impTypeSelect = document.getElementById("product-attr-imp-type");
        if (impTypeSelect) {
          const defaultImp = getDefaultImpTypeForFamily(familyKey);
          if (!impTypeSelect.value || impTypeSelect.dataset.autoSet === "true") {
            impTypeSelect.value = defaultImp;
            impTypeSelect.dataset.autoSet = "true";
          }
        }
        updateCatalogClassificationHint();
      },
    });
    _familyCombobox.bind();
  }
  return _familyCombobox;
}

function syncFamilyCombobox(selectedValue = "") {
  const combo = getFamilyCombobox();
  const cached = _catalogAttributeOptionCache.get("product_family:active") || _catalogAttributeOptionCache.get("product_family:all") || [];
  combo.setItems(cached.map((item) => ({
    value: item.option_key,
    label: item.label,
    hint: item.domain_option_label_kr || item.domain_option_label || "",
  })));
  const match = cached.find((item) => item.option_key === selectedValue);
  combo.setValue(selectedValue, match?.label || "");
}

/* product_family → domain 자동 결정 (domain_option_key 사용) */
function getDomainKeyForFamily(familyKey) {
  if (!familyKey) return "";
  const cached = _catalogAttributeOptionCache.get("product_family:active") || _catalogAttributeOptionCache.get("product_family:all") || [];
  const match = cached.find((item) => item.option_key === familyKey);
  return match?.domain_option_key || "";
}

function getProductAttributeValueMap(attributes = []) {
  return Object.fromEntries(
    (attributes || [])
      .filter((item) => item?.attribute_key)
      .map((item) => [item.attribute_key, item.option_key || item.raw_value || ""]),
  );
}

async function buildCatalogAttributeOptionMaps() {
  const maps = new Map();
  const keys = new Set();
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    const k = getCatalogPrimaryLevelKey(levelNo);
    if (k) keys.add(k);
  }
  for (const attr of getDisplayableCatalogAttributes()) {
    keys.add(attr.attribute_key);
  }
  const entries = await Promise.all(
    [...keys].map(async (attributeKey) => {
      const options = await loadCatalogAttributeOptions(attributeKey, true);
      return [attributeKey, new Map(options.map((item) => [item.option_key, { label: item.label, label_kr: item.label_kr }]))];
    }),
  );
  for (const [key, optionMap] of entries) {
    maps.set(key, optionMap);
  }
  return maps;
}

function projectCatalogRowForCurrentLayout(row, attrOptionMaps = new Map()) {
  const projected = { ...row };
  const values = getProductAttributeValueMap(row.attributes || []);
  const lang = getCatalogLabelLang();

  /* 레이아웃 레벨 필드 (트리 호환 유지) */
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    const attributeKey = getCatalogPrimaryLevelKey(levelNo);
    const optionKey = attributeKey ? values[attributeKey] || "" : "";
    let optionLabel = null;
    if (optionKey) {
      const optionData = attrOptionMaps.get(attributeKey)?.get(optionKey);
      if (optionData) {
        optionLabel = lang === "ko"
          ? (optionData.label_kr || optionData.label || optionKey)
          : (optionData.label || optionKey);
      } else {
        optionLabel = getCatalogAttributeLabel(attributeKey, optionKey) || optionKey;
      }
    }
    projected[`classification_level_${levelNo}_name`] = optionLabel || null;
  }

  /* 모든 속성 → attr_{key} 필드 (그리드 컬럼용) */
  for (const [attributeKey, optionMap] of attrOptionMaps) {
    const optionKey = values[attributeKey] || "";
    let displayLabel = null;
    if (optionKey) {
      const optionData = optionMap.get(optionKey);
      if (optionData) {
        displayLabel = lang === "ko"
          ? (optionData.label_kr || optionData.label || optionKey)
          : (optionData.label || optionKey);
      } else {
        displayLabel = getCatalogAttributeLabel(attributeKey, optionKey) || optionKey;
      }
    }
    projected[`attr_${attributeKey}`] = displayLabel;
  }

  return projected;
}

async function projectCatalogRowsForCurrentLayout(rows) {
  const attrOptionMaps = await buildCatalogAttributeOptionMaps();
  return (rows || []).map((row) => projectCatalogRowForCurrentLayout(row, attrOptionMaps));
}

function updateCatalogClassificationHint() {
  const hint = document.getElementById("product-classification-hint");
  if (!hint) return;
  const values = getCatalogAttributeValuesFromForm();
  const path = [
    getCatalogAttributeLabel("domain", values.domain),
    getCatalogAttributeLabel("imp_type", values.imp_type),
    getCatalogAttributeLabel("product_family", values.product_family),
    getCatalogAttributeLabel("platform", values.platform),
  ].filter(Boolean);
  hint.textContent = path.length
    ? `분류 경로: ${path.join(" > ")}`
    : "";
}

async function populateCatalogClassificationNodeDomainSelect(selectedDomainOptionId = null) {
  const wrap = document.getElementById("catalog-classification-node-domain-wrap");
  const attributeKey = document.getElementById("catalog-classification-node-parent")?.dataset.attributeKey || "";
  if (!wrap) return;
  const isProductFamily = attributeKey === "product_family";
  wrap.classList.toggle("is-hidden", !isProductFamily);
  if (!isProductFamily) return;
  const options = await loadCatalogAttributeOptions("domain", true);
  fillCatalogAttributeSelect(
    "catalog-classification-node-domain",
    options.map((item) => ({ value: String(item.id), label: item.label })),
    selectedDomainOptionId ? String(selectedDomainOptionId) : "",
  );
}

function renderCatalogClassificationTree() {
  const container = document.getElementById("catalog-classification-tree");
  if (!container) return;
  updateCatalogTreeModeBtn();
  if (!_catalogClassificationNodes.length) {
    container.innerHTML = '<div class="catalog-classification-empty">선택 가능한 leaf 분류가 없습니다.</div>';
    return;
  }
  const roots = filterCatalogClassificationTreeRoots(buildCatalogClassificationTreeRoots());
  if (!roots.length) {
    container.innerHTML = '<div class="catalog-classification-empty">검색 결과가 없습니다.</div>';
    return;
  }
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
  return String(a.node_name || "").localeCompare(String(b.node_name || ""), "ko-KR");
}

function filterCatalogClassificationTreeRoots(roots) {
  const query = (_catalogClassificationSearchQuery || "").trim().toLocaleLowerCase("ko-KR");
  if (!query) return roots;
  return roots
    .map((node) => filterCatalogClassificationTreeNode(node, query))
    .filter(Boolean);
}

function matchesCatalogOptionSearch(option, searchTerm) {
  const term = searchTerm.toLowerCase();
  if ((option.option_key || "").toLowerCase().includes(term)) return true;
  if ((option.label || "").toLowerCase().includes(term)) return true;
  if ((option.label_kr || "").toLowerCase().includes(term)) return true;
  if ((option.aliases || []).some((a) => (a.alias_value || "").toLowerCase().includes(term))) return true;
  return false;
}

function filterCatalogClassificationTreeNode(node, query) {
  const haystack = [
    node.node_name,
    node.node_code,
    node.path_label,
  ]
    .filter(Boolean)
    .join(" ")
    .toLocaleLowerCase("ko-KR");
  const optionMatch = node.option_data ? matchesCatalogOptionSearch(node.option_data, query) : false;
  if (haystack.includes(query) || optionMatch) {
    return {
      ...node,
      children: [...(node.children || [])],
    };
  }
  const children = (node.children || [])
    .map((child) => filterCatalogClassificationTreeNode(child, query))
    .filter(Boolean);
  if (!children.length) {
    return null;
  }
  return {
    ...node,
    children,
  };
}

function renderCatalogClassificationTreeNode(node) {
  const children = [...(node.children || [])].sort(sortCatalogClassificationNodes);
  const hasChildren = children.length > 0;
  const forceExpanded = !!(_catalogClassificationSearchQuery || "").trim();
  const collapsed = hasChildren && !forceExpanded && _catalogClassificationCollapsed.has(node.id);
  const selectedClass = node.node_code === _selectedCatalogClassificationCode ? " is-selected" : "";
  const branchMutedClass = isCatalogNodeWithinSelectedBranch(node) ? "" : " is-branch-muted";
  const levelClass = getCatalogNodeLevelClass(node);
  const toggleMarkup = hasChildren
    ? `<span class="classification-tree-toggle" data-catalog-toggle-node="${node.id}">${collapsed ? "▸" : "▾"}</span>`
    : '<span class="classification-tree-toggle is-placeholder">•</span>';
  const actionAttrs = `data-catalog-classification-code="${escapeHtml(node.node_code)}"`;
  const canManage = _catalogClassificationEditMode && _catalogPermissions.canManageCatalogTaxonomy;
  const canAddChild = canManage && canCatalogNodeAddChild(node);
  const actionsOpen = canManage && isCatalogTreeActionExpanded(node.id);
  const actionsMarkup = canManage
    ? `<div class="layout-tree-node-actions${actionsOpen ? " is-visible" : ""}${_catalogTreeActionMode === "detail" ? " is-detail-mode" : ""}">
        ${canAddChild ? `<button type="button" class="btn btn-secondary btn-sm layout-tree-node-action" data-catalog-add-child-node="${node.id}">하위 추가</button>` : ""}
        <button type="button" class="btn btn-secondary btn-sm layout-tree-node-action" data-catalog-edit-node="${node.id}">수정</button>
        <button type="button" class="btn btn-secondary btn-sm layout-tree-node-action is-delete-action" data-catalog-delete-node="${node.id}">삭제</button>
      </div>`
    : "";
  const actionToggleMarkup = canManage && _catalogTreeActionMode !== "detail"
    ? `<button type="button" class="btn btn-icon btn-sm layout-tree-node-toggle" data-catalog-node-action-toggle="${node.id}" aria-expanded="${actionsOpen ? "true" : "false"}" title="${actionsOpen ? "노드 작업 닫기" : "노드 작업 열기"}">${actionsOpen ? ">" : "<"}</button>`
    : "";
  const actionWrapMarkup = canManage
    ? `<div class="layout-tree-node-action-wrap">${actionsMarkup}${actionToggleMarkup}</div>`
    : "";
  const childMarkup = hasChildren && !collapsed
    ? `<ul class="classification-subtree${branchMutedClass}">${children.map(renderCatalogClassificationTreeNode).join("")}</ul>`
    : "";
  return `
    <li class="classification-tree-item${branchMutedClass}">
      <div class="classification-tree-node${levelClass}${selectedClass}${branchMutedClass}">
        <button type="button" class="classification-tree-node-main" ${actionAttrs}>
          ${toggleMarkup}
          <span class="classification-tree-main">
            <span class="classification-tree-title">
              <span class="classification-tree-name">${escapeHtml(node.node_name)}</span>
              <span class="classification-tree-code">${escapeHtml(node.node_code)}</span>
            </span>
          </span>
        </button>
        ${actionWrapMarkup}
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
  return selectedNode.selected_codes || null;
}

function getSelectedCatalogClassificationNode() {
  if (!_selectedCatalogClassificationCode) return null;
  return _catalogClassificationNodeMap.get(_selectedCatalogClassificationCode) || null;
}

function populateCatalogClassificationParentOptions(selectedParentId = null, excludedNodeId = null) {
  const parentEl = document.getElementById("catalog-classification-node-parent");
  if (!parentEl) return;
  parentEl.value = selectedParentId ? String(selectedParentId) : "";
}

function openCatalogClassificationSchemeModal() {
  if (!_catalogPermissions.canManageCatalogTaxonomy) {
    showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!_catalogLayoutDetail) return;
  document.getElementById("catalog-classification-scheme-name").value = _catalogLayoutDetail.name || "";
  document.getElementById("catalog-classification-scheme-description").value = _catalogLayoutDetail.description || "";
  const depthCount = _catalogLayoutDetail.depth_count || _catalogLayoutDetail.levels?.length || 3;
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    const level = getCatalogLayoutLevel(levelNo);
    const checkbox = document.getElementById(`catalog-classification-scheme-level-${levelNo}-enabled`);
    if (checkbox) {
      checkbox.checked = levelNo <= depthCount;
      checkbox.disabled = levelNo === 1;
    }
    document.getElementById(`catalog-classification-scheme-level-${levelNo}-alias`).value = level?.alias || "";
    populateCatalogLayoutKeySelect(levelNo, level?.keys?.[0]?.attribute_key || "");
  }
  syncCatalogLayoutKeyOptions();
  _catalogClassificationSchemeEditing = false;
  updateCatalogLayoutLevelVisibility();
  document.getElementById("modal-catalog-classification-scheme").showModal();
}

async function openCatalogClassificationNodeModal(mode, forcedLevelNo = null, forcedOptionId = null, forcedAttributeKey = "") {
  if (!_catalogPermissions.canManageCatalogTaxonomy) {
    showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
    return;
  }
  const node = mode === "edit" ? getSelectedCatalogClassificationNode() : null;
  const levelNo = forcedLevelNo || (mode === "add_root" ? 1 : mode === "add_child" ? Number(getSelectedCatalogClassificationNode()?.level || 0) + 1 : Number(node?.level || 0));
  const attributeKey = forcedAttributeKey || getCatalogConfiguredLevelKey(levelNo);
  if (!attributeKey) {
    showToast("먼저 분류를 선택하세요.", "warning");
    return;
  }
  const attribute = getCatalogAttributeDef(attributeKey);
  if (!attribute) {
    showToast("속성 정의를 찾을 수 없습니다.", "warning");
    return;
  }
  let option = null;
  if (forcedOptionId) {
    const options = await loadCatalogAttributeOptions(attributeKey, false);
    option = options.find((item) => item.id === forcedOptionId) || null;
  } else if (mode === "edit") {
    const options = await loadCatalogAttributeOptions(attributeKey, false);
    const targetLabel = getCatalogNodeOptionLabel(node?.node_name, levelNo);
    option = options.find((item) => item.label === targetLabel);
    if (!option) {
      showToast("현재 트리 노드는 직접 편집 가능한 단일 속성값이 아닙니다.", "warning");
      return;
    }
  }
  document.getElementById("modal-catalog-classification-node-title").textContent = mode === "edit" ? "속성값 수정" : "속성값 등록";
  document.getElementById("catalog-classification-node-id").value = option?.id || "";
  document.getElementById("catalog-classification-node-parent").value = attribute.label;
  document.getElementById("catalog-classification-node-parent").dataset.attributeId = String(attribute.id);
  document.getElementById("catalog-classification-node-parent").dataset.attributeKey = attribute.attribute_key;
  document.getElementById("catalog-classification-node-code").value = option?.option_key || "";
  document.getElementById("catalog-classification-node-name").value = option?.label || "";
  document.getElementById("catalog-classification-node-name-kr").value = option?.label_kr || "";
  renderCatalogNodeAliasTags(option?.id || null, option?.aliases || []);
  document.getElementById("catalog-node-alias-section").classList.toggle("is-hidden", !option?.id);
  document.getElementById("catalog-classification-node-sort-order").value = option?.sort_order ?? 100;
  document.getElementById("catalog-classification-node-active").value = String(option?.is_active ?? true);
  document.getElementById("catalog-classification-node-note").value = option?.description || "";
  await populateCatalogClassificationNodeDomainSelect(option?.domain_option_id || null);
  document.getElementById("modal-catalog-classification-node").showModal();
}

function setCatalogClassificationEditMode(enabled) {
  _catalogClassificationEditMode = !!enabled;
  renderCatalogClassificationTree();
  applyCatalogPermissionState();
}

async function saveCatalogClassificationScheme() {
  if (!_catalogPermissions.canManageCatalogTaxonomy || !_catalogLayoutDetail) return;
  if (!_catalogClassificationSchemeEditing) {
    _catalogClassificationSchemeEditing = true;
    updateCatalogLayoutLevelVisibility();
    return;
  }
  const payload = buildCatalogClassificationSchemePayload();
  if (!payload) return;
  await apiFetch(`/api/v1/classification-layouts/${_catalogLayoutDetail.id}`, { method: "PATCH", body: payload });
  _catalogClassificationSchemeEditing = false;
  document.getElementById("modal-catalog-classification-scheme").close();
  await loadCatalogTaxonomyContext();
  await loadCatalog();
}

function buildCatalogClassificationSchemePayload() {
  const depthCount = getCatalogLayoutConfiguredDepth();
  const levels = [];
  const usedKeys = new Set();
  for (let levelNo = 1; levelNo <= depthCount; levelNo += 1) {
    const alias = document.getElementById(`catalog-classification-scheme-level-${levelNo}-alias`).value.trim() || `레벨 ${levelNo}`;
    const attributeKey = document.getElementById(`catalog-classification-scheme-level-${levelNo}-key`).value || "";
    if (!attributeKey) {
      showToast(`${levelNo} depth의 키를 선택하세요.`, "warning");
      return null;
    }
    if (usedKeys.has(attributeKey)) {
      showToast("같은 키를 여러 depth에 배치할 수 없습니다.", "warning");
      return null;
    }
    usedKeys.add(attributeKey);
    levels.push({
      level_no: levelNo,
      alias,
      joiner: null,
      prefix_mode: null,
      sort_order: levelNo * 10,
      keys: [{ attribute_key: attributeKey, sort_order: 100, is_visible: true }],
    });
  }
  const name = document.getElementById("catalog-classification-scheme-name").value.trim();
  if (!name) {
    showToast("분류체계명을 입력하세요.", "warning");
    return null;
  }
  return {
    name,
    description: document.getElementById("catalog-classification-scheme-description").value.trim() || null,
    depth_count: depthCount,
    is_active: _catalogLayoutDetail?.is_active !== false,
    levels,
  };
}

async function saveCatalogClassificationSchemeAsPreset() {
  if (!_catalogPermissions.canManageCatalogTaxonomy) return;
  const payload = buildCatalogClassificationSchemePayload();
  if (!payload) return;
  const created = await apiFetch("/api/v1/classification-layouts", {
    method: "POST",
    body: {
      ...payload,
      scope_type: "global",
      project_id: null,
      is_default: false,
    },
  });
  localStorage.setItem(CATALOG_LAYOUT_PRESET_KEY, String(created.id));
  document.getElementById("modal-catalog-classification-scheme").close();
  await loadCatalogTaxonomyContext();
  await loadCatalog();
  showToast("새 프리셋을 저장했습니다.");
}

async function saveCatalogClassificationNode() {
  if (!_catalogPermissions.canManageCatalogTaxonomy) return;
  const optionId = Number(document.getElementById("catalog-classification-node-id").value || 0);
  const attributeId = Number(document.getElementById("catalog-classification-node-parent").dataset.attributeId || 0);
  const attributeKey = document.getElementById("catalog-classification-node-parent").dataset.attributeKey || "";
  const payload = {
    option_key: document.getElementById("catalog-classification-node-code").value.trim(),
    label: document.getElementById("catalog-classification-node-name").value.trim(),
    label_kr: document.getElementById("catalog-classification-node-name-kr").value.trim() || null,
    sort_order: Number(document.getElementById("catalog-classification-node-sort-order").value || 100),
    is_active: document.getElementById("catalog-classification-node-active").value === "true",
    description: document.getElementById("catalog-classification-node-note").value.trim() || null,
  };
  if (!attributeId || !attributeKey) {
    showToast("대상 속성을 찾을 수 없습니다.", "warning");
    return;
  }
  const existingOptions = await loadCatalogAttributeOptions(attributeKey, false);
  const duplicate = existingOptions.find((item) => {
    if (optionId && Number(item.id) === optionId) return false;
    const sameKey = String(item.option_key || "").trim().toLowerCase() === payload.option_key.toLowerCase();
    const sameLabel = String(item.label || "").trim().toLocaleLowerCase("ko-KR") === payload.label.toLocaleLowerCase("ko-KR");
    const sameLabelKr = payload.label_kr && String(item.label_kr || "").trim().toLocaleLowerCase("ko-KR") === payload.label_kr.toLocaleLowerCase("ko-KR");
    return sameKey || sameLabel || sameLabelKr;
  });
  if (duplicate) {
    showToast(
      duplicate.option_key?.trim().toLowerCase() === payload.option_key.toLowerCase()
        ? "이미 같은 속성값 키가 있습니다."
        : "이미 같은 아이템명이 있습니다.",
      "warning",
      4500,
    );
    return;
  }
  if (attributeKey === "product_family") {
    payload.domain_option_id = Number(document.getElementById("catalog-classification-node-domain")?.value || 0) || null;
    if (payload.option_key.toLowerCase() !== "generic" && !payload.domain_option_id) {
      showToast("제품군 아이템에는 도메인을 지정하세요.", "warning");
      return;
    }
  }
  if (optionId) {
    await apiFetch(`/api/v1/catalog-attributes/options/${optionId}`, { method: "PATCH", body: payload });
  } else {
    await apiFetch(`/api/v1/catalog-attributes/${attributeId}/options`, { method: "POST", body: payload });
  }
  document.getElementById("modal-catalog-classification-node").close();
  invalidateCatalogAttributeOptionCache(attributeKey);
  await loadCatalogTaxonomyContext();
  await rebuildCatalogClassificationTree(_catalogRows || []);
  applyFilter();
}

async function deleteCatalogClassificationNode() {
  if (!_catalogPermissions.canManageCatalogTaxonomy) {
    showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
    return;
  }
  const node = getSelectedCatalogClassificationNode();
  if (!node) return;
  if (!await showConfirmDialog(`분류 "${node.node_name}"을(를) 삭제하시겠습니까?`, {
    title: "분류 삭제",
    confirmText: "삭제",
  })) return;
  const attributeKey = getCatalogPrimaryLevelKey(node.level);
  const options = await loadCatalogAttributeOptions(attributeKey, false);
  const option = options.find((item) => item.label === getCatalogNodeOptionLabel(node.node_name, node.level));
  if (!option) {
    showToast("현재 트리 노드는 직접 삭제 가능한 단일 속성값이 아닙니다.", "warning");
    return;
  }
  await apiFetch(`/api/v1/catalog-attributes/options/${option.id}`, { method: "DELETE" });
  invalidateCatalogAttributeOptionCache(attributeKey);
  _selectedCatalogClassificationCode = "";
  await loadCatalogTaxonomyContext();
  await rebuildCatalogClassificationTree(_catalogRows || []);
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
  detailPanel.classList.toggle("is-hidden", !isOpen);
  detailContent.classList.toggle("is-hidden", !isOpen || !currentProductId);
  detailEmpty.classList.toggle("is-hidden", !!currentProductId);
  splitter.classList.toggle("is-hidden", !isOpen);
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
  const hasClassificationSelection = !!_selectedCatalogClassificationCode;
  catalogGridApi.setGridOption("isExternalFilterPresent", () => !!(q || kind || hasClassificationSelection));
  catalogGridApi.setGridOption("doesExternalFilterPass", (node) => {
    const d = node.data;
    if (kind && d.product_type !== kind) return false;
    if (hasClassificationSelection && (!selectedCodes || !selectedCodes.has(getCatalogRowClassificationToken(d)))) return false;
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
    const rawDetail = await apiFetch(`/api/v1/product-catalog/${product.id}`);
    const detail = projectCatalogRowForCurrentLayout(rawDetail);
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
  const attrMap = getProductAttributeValueMap(d.attributes);
  const leafAlias = getCatalogLeafAlias();
  const level1Alias = getCatalogClassificationAliases()[0];
  infoGrid.replaceChildren();
  infoGrid.appendChild(_infoRow("제조사", d.vendor));
  infoGrid.appendChild(_infoRow("모델명", d.name));
  infoGrid.appendChild(_infoRow(level1Alias, getCatalogAttributeLabel("domain", attrMap.domain) || "-"));
  infoGrid.appendChild(_infoRow("버전", d.version || "-"));
  infoGrid.appendChild(_infoRow(leafAlias, d.classification_level_5_name || d.classification_level_4_name || d.classification_level_3_name || d.classification_level_2_name || d.classification_level_1_name || "-"));
  infoGrid.appendChild(_infoRow("분류 경로", buildCatalogPathLabel(d)));
  infoGrid.appendChild(_infoRow("참조 URL", d.reference_url || "-"));
  infoGrid.appendChild(_infoRow("출처", d.source_name || "-"));
  infoGrid.appendChild(_infoRow("검증상태", d.verification_status || "-"));
  infoGrid.appendChild(_infoRow("검증일", fmtDate(d.last_verified_at)));
  infoGrid.appendChild(_infoRow("라이선스 유형", LICENSE_TYPE_LABELS[d.default_license_type] || d.default_license_type || "-"));
  infoGrid.appendChild(_infoRow("라이선스 기준", LICENSE_UNIT_LABELS[d.default_license_unit] || d.default_license_unit || "-"));
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
      btnEdit.type = "button";
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditInterface(params.data));
      const btnDel = document.createElement("button");
      btnDel.type = "button";
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

async function openCreateProduct() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  document.getElementById("product-id").value = "";
  document.getElementById("product-name").value = "";
  document.getElementById("product-name-ref-id").value = "";
  document.getElementById("product-type").value = "hardware";
  document.getElementById("product-version").value = "";
  await loadVendorList();
  syncVendorCombobox("");
  await syncCatalogAttributeInputs({}, true);
  document.getElementById("product-attr-imp-type").dataset.autoSet = "true";
  document.getElementById("product-reference-url").value = "";
  document.getElementById("product-license-type").value = "";
  document.getElementById("product-license-unit").value = "";
  document.getElementById("modal-product-title").textContent = "제품 등록";
  document.getElementById("btn-save-product").textContent = "등록";
  resetProductSimilarityBox();
  await loadProductNameList();
  productModal.showModal();
  document.getElementById("product-name")?.focus();
}

async function openEditProduct() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  apiFetch(`/api/v1/product-catalog/${currentProductId}`).then(async (d) => {
    const attrMap = getProductAttributeValueMap(d.attributes);
    document.getElementById("product-id").value = d.id;
    document.getElementById("product-name").value = d.name;
    document.getElementById("product-name-ref-id").value = "";
    document.getElementById("product-type").value = d.product_type;
    document.getElementById("product-version").value = d.version || "";
    await loadVendorList();
    syncVendorCombobox(d.vendor);
    await syncCatalogAttributeInputs({
      domain: attrMap.domain,
      imp_type: attrMap.imp_type,
      product_family: attrMap.product_family,
      platform: attrMap.platform,
    }, true);
    document.getElementById("product-reference-url").value = d.reference_url || "";
    document.getElementById("product-license-type").value = d.default_license_type || "";
    document.getElementById("product-license-unit").value = d.default_license_unit || "";
    document.getElementById("modal-product-title").textContent = "제품 수정";
    document.getElementById("btn-save-product").textContent = "저장";
    await loadProductNameList(currentProductId);
    productModal.showModal();
  }).catch((err) => showToast(err.message, "error"));
}

async function saveProduct() {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  const id = document.getElementById("product-id").value;
  const vendor = document.getElementById("product-vendor-value").value;
  const name = document.getElementById("product-name").value;
  if (!vendor || !name) {
    showToast("제조사와 모델명은 필수입니다.", "warning");
    return;
  }
  const attrValues = getCatalogAttributeValuesFromForm();
  /* 제품군 미입력 시 generic 자동 적용 */
  if (!attrValues.product_family) {
    attrValues.product_family = "generic";
    attrValues.domain = getDomainKeyForFamily("generic") || attrValues.domain;
  }
  /* 구현형태 미입력 시 제품군 기반 기본값 */
  if (!attrValues.imp_type) {
    attrValues.imp_type = getDefaultImpTypeForFamily(attrValues.product_family) || "hw";
  }
  if (!attrValues.domain) {
    attrValues.domain = getDomainKeyForFamily(attrValues.product_family);
  }
  const productType = getProductTypeFromImpType(attrValues.imp_type);
  const payload = {
    vendor,
    name,
    product_type: productType,
    version: document.getElementById("product-version").value || null,
    reference_url: document.getElementById("product-reference-url").value || null,
    default_license_type: document.getElementById("product-license-type").value || null,
    default_license_unit: document.getElementById("product-license-unit").value || null,
    attributes: buildCatalogAttributePayload(attrValues),
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
    resetProductSimilarityBox();
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
    const res = await fetch(withRootPath("/api/v1/infra-excel/import/preview"), {
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
    const res = await fetch(withRootPath("/api/v1/infra-excel/import/confirm"), {
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

async function runCatalogResearch(fillOnly = true) {
  if (!_catalogPermissions.canManageCatalogProducts) {
    showToast("카탈로그 제품 관리 권한이 없습니다.", "warning");
    return;
  }
  if (!currentProductId) return;
  if (currentProductType !== "hardware") {
    showToast("현재 카탈로그 조사는 하드웨어 제품만 지원합니다.", "warning");
    return;
  }
  try {
    const result = await apiFetch(`/api/v1/product-catalog/${currentProductId}/research`, {
      method: "POST",
      body: { fill_only: fillOnly, force: false },
    });
    if (result.skipped) {
      showToast(`재조사 건너뜀 · ${result.skip_reason || "already_done"}`);
    } else {
      showToast(`조사 반영 완료 · spec ${result.spec_applied}/${result.spec_candidates} · eosl ${result.eosl_applied}/${result.eosl_candidates} · 인터페이스 ${result.interfaces_created}/${result.interface_candidates}`);
    }
    await loadCatalog();
    await selectProduct({ id: currentProductId });
  } catch (err) {
    showToast(err.message, "error");
  }
}

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
  if (storedWidth >= 15 && storedWidth <= 80) {
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
    if (pct > 15 && pct < 80) {
      mainPanel.style.setProperty("--catalog-list-width", `${pct}%`);
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

function loadCatalogClassificationSearchState() {
  _catalogClassificationSearchQuery = localStorage.getItem(CATALOG_CLASSIFICATION_SEARCH_KEY) || "";
  const input = document.getElementById("catalog-classification-search");
  if (input) input.value = _catalogClassificationSearchQuery;
}

/* ── Init ── */

document.addEventListener("DOMContentLoaded", async () => {
  loadCatalogClassificationSearchState();
  await Promise.all([
    loadCatalogPermissions(),
    loadCatalogTaxonomyContext(),
    loadCatalogLabelLangPreference(),
  ]);
  initCatalogGrid();
  initIfaceGrid();
  initTabs();
  activateCatalogTab("info");
  initCategorySplitter();
  initSplitter();
  bindProductSimilarityInputs();
  setCatalogDetailOpen(localStorage.getItem(CATALOG_DETAIL_OPEN_KEY) === "1");
  applyCatalogPermissionState();
  await loadCatalog();

  // 이벤트 바인딩
  document.getElementById("btn-open-import").addEventListener("click", openCatalogImport);
  document.getElementById("btn-research-spec")?.addEventListener("click", () => runCatalogResearch(true));
  document.getElementById("btn-catalog-classification-edit-toggle").addEventListener("click", () => {
    if (!_catalogPermissions.canManageCatalogTaxonomy) {
      showToast("카탈로그 기준 관리 권한이 없습니다.", "warning");
      return;
    }
    setCatalogClassificationEditMode(!_catalogClassificationEditMode);
  });
  document.getElementById("btn-catalog-classification-edit-scheme").addEventListener("click", openCatalogClassificationSchemeModal);
  document.getElementById("catalog-layout-preset-select").addEventListener("change", async (event) => {
    const layoutId = Number(event.target.value || 0);
    if (!layoutId) return;
    localStorage.setItem(CATALOG_LAYOUT_PRESET_KEY, String(layoutId));
    await loadCatalogTaxonomyContext();
    await loadCatalog();
  });
  document.getElementById("btn-catalog-classification-add-root").addEventListener("click", () => openCatalogClassificationNodeModal("add_root").catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-catalog-classification-add-child").addEventListener("click", () => openCatalogClassificationNodeModal("add_child").catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-catalog-classification-scheme-cancel").addEventListener("click", () => {
    _catalogClassificationSchemeEditing = false;
    document.getElementById("modal-catalog-classification-scheme").close();
  });
  document.getElementById("btn-catalog-classification-scheme-save-preset").addEventListener("click", () => saveCatalogClassificationSchemeAsPreset().catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-catalog-classification-scheme-submit").addEventListener("click", () => saveCatalogClassificationScheme().catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-catalog-classification-node-cancel").addEventListener("click", () => document.getElementById("modal-catalog-classification-node").close());
  document.getElementById("btn-catalog-classification-node-submit").addEventListener("click", () => saveCatalogClassificationNode().catch((err) => showToast(err.message, "error")));
  for (let levelNo = 2; levelNo <= 5; levelNo += 1) {
    document.getElementById(`catalog-classification-scheme-level-${levelNo}-enabled`)?.addEventListener("change", () => {
      normalizeCatalogLayoutLevelEnabledState(levelNo);
      updateCatalogLayoutLevelVisibility();
    });
  }
  for (let levelNo = 1; levelNo <= 5; levelNo += 1) {
    document.getElementById(`catalog-classification-scheme-level-${levelNo}-key`)?.addEventListener("change", () => {
      if (levelNo === 1) {
        handleCatalogPrimaryLevelKeyChange();
      } else {
        syncCatalogLayoutKeyOptions();
      }
    });
  }
  document.getElementById("btn-clear-classification-filter").addEventListener("click", () => {
    _selectedCatalogClassificationCode = "";
    renderCatalogClassificationTree();
    applyFilter();
  });
  document.getElementById("btn-add-product").addEventListener("click", openCreateProduct);
  document.getElementById("btn-minimize-catalog-detail").addEventListener("click", toggleCatalogDetailPanel);
  document.getElementById("btn-edit-product").addEventListener("click", openEditProduct);
  document.getElementById("btn-delete-product").addEventListener("click", deleteProduct);
  document.getElementById("btn-cancel-product").addEventListener("click", () => {
    resetProductSimilarityBox();
    productModal.close();
  });
  document.getElementById("btn-save-product").addEventListener("click", saveProduct);
  /* combobox 초기화 (vendor, product_family) — onSelect 콜백에서 자동 처리 */
  getVendorCombobox();
  getFamilyCombobox();
  /* imp_type 수동 변경 시 autoSet 해제 */
  document.getElementById("product-attr-imp-type")?.addEventListener("change", () => {
    document.getElementById("product-attr-imp-type").dataset.autoSet = "false";
    updateCatalogClassificationHint();
  });
  document.getElementById("product-attr-platform")?.addEventListener("change", updateCatalogClassificationHint);
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
  document.getElementById("btn-catalog-tree-mode")?.addEventListener("click", () => {
    _catalogTreeActionMode = _catalogTreeActionMode === "detail" ? "compact" : "detail";
    localStorage.setItem(CATALOG_TREE_ACTION_MODE_KEY, _catalogTreeActionMode);
    _catalogExpandedTreeActions.clear();
    updateCatalogTreeModeBtn();
    renderCatalogClassificationTree();
  });
  updateCatalogTreeModeBtn();
  document.getElementById("catalog-classification-search").addEventListener("input", (event) => {
    _catalogClassificationSearchQuery = event.target.value || "";
    localStorage.setItem(CATALOG_CLASSIFICATION_SEARCH_KEY, _catalogClassificationSearchQuery);
    renderCatalogClassificationTree();
  });
  document.getElementById("catalog-classification-tree").addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-catalog-toggle-node]");
    if (toggle) {
      const nodeId = toggle.dataset.catalogToggleNode || "";
      if (_catalogClassificationCollapsed.has(nodeId)) _catalogClassificationCollapsed.delete(nodeId);
      else _catalogClassificationCollapsed.add(nodeId);
      saveCatalogClassificationCollapsedState();
      renderCatalogClassificationTree();
      return;
    }
    const actionToggle = event.target.closest("[data-catalog-node-action-toggle]");
    if (actionToggle) {
      event.preventDefault();
      event.stopPropagation();
      toggleCatalogTreeActionMenu(actionToggle.dataset.catalogNodeActionToggle || "");
      return;
    }
    const addChildBtn = event.target.closest("[data-catalog-add-child-node]");
    if (addChildBtn) {
      event.preventDefault();
      event.stopPropagation();
      const node = _catalogClassificationNodes.find((item) => item.id === (addChildBtn.dataset.catalogAddChildNode || ""));
      if (node) {
        _selectedCatalogClassificationCode = node.node_code;
        renderCatalogClassificationTree();
        applyFilter();
        openCatalogClassificationNodeModal("add_child").catch((err) => showToast(err.message, "error"));
      }
      return;
    }
    const editBtn = event.target.closest("[data-catalog-edit-node]");
    if (editBtn) {
      event.preventDefault();
      event.stopPropagation();
      const node = _catalogClassificationNodes.find((item) => item.id === (editBtn.dataset.catalogEditNode || ""));
      if (node) {
        _selectedCatalogClassificationCode = node.node_code;
        renderCatalogClassificationTree();
        applyFilter();
        openCatalogClassificationNodeModal("edit").catch((err) => showToast(err.message, "error"));
      }
      return;
    }
    const deleteBtn = event.target.closest("[data-catalog-delete-node]");
    if (deleteBtn) {
      event.preventDefault();
      event.stopPropagation();
      const node = _catalogClassificationNodes.find((item) => item.id === (deleteBtn.dataset.catalogDeleteNode || ""));
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

function renderCatalogNodeAliasTags(optionId, aliases) {
  const container = document.getElementById("catalog-node-alias-tags");
  if (!container) return;
  container.replaceChildren();
  (aliases || []).forEach((alias) => {
    const tag = document.createElement("span");
    tag.className = "catalog-alias-tag" + (alias.match_type === "label_kr_auto" ? " is-auto" : "");
    tag.textContent = alias.alias_value;
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "catalog-alias-tag-remove";
    removeBtn.textContent = "×";
    removeBtn.disabled = alias.match_type === "label_kr_auto";
    if (alias.match_type !== "label_kr_auto") {
      removeBtn.addEventListener("click", () => deleteCatalogNodeAlias(alias.id, optionId));
    }
    tag.appendChild(removeBtn);
    container.appendChild(tag);
  });
  if (optionId) {
    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "btn btn-compact";
    addBtn.textContent = "+ 추가";
    addBtn.addEventListener("click", () => showCatalogNodeAliasInput(optionId));
    container.appendChild(addBtn);
  }
}

function showCatalogNodeAliasInput(optionId) {
  const container = document.getElementById("catalog-node-alias-tags");
  if (!container || container.querySelector(".catalog-alias-add-input")) return;
  const input = document.createElement("input");
  input.type = "text";
  input.className = "catalog-alias-add-input";
  input.placeholder = "별칭 입력";
  const addBtn = container.querySelector(".btn");
  container.insertBefore(input, addBtn);
  input.focus();
  input.addEventListener("keydown", async (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const value = input.value.trim();
      if (value) await addCatalogNodeAlias(optionId, value);
      input.remove();
    } else if (e.key === "Escape") {
      input.remove();
    }
  });
  input.addEventListener("blur", () => input.remove());
}

async function addCatalogNodeAlias(optionId, aliasValue) {
  const attributeKey = document.getElementById("catalog-classification-node-parent").dataset.attributeKey;
  await apiFetch("/api/v1/catalog-integrity/attribute-aliases", {
    method: "POST",
    body: { attribute_key: attributeKey, option_id: optionId, alias_value: aliasValue },
  });
  invalidateCatalogAttributeOptionCache(attributeKey);
  const options = await loadCatalogAttributeOptions(attributeKey, false);
  const option = options.find((item) => item.id === optionId);
  renderCatalogNodeAliasTags(optionId, option?.aliases || []);
}

async function deleteCatalogNodeAlias(aliasId, optionId) {
  await apiFetch(`/api/v1/catalog-integrity/attribute-aliases/${aliasId}`, { method: "DELETE" });
  const attributeKey = document.getElementById("catalog-classification-node-parent").dataset.attributeKey;
  invalidateCatalogAttributeOptionCache(attributeKey);
  const options = await loadCatalogAttributeOptions(attributeKey, false);
  const option = options.find((item) => item.id === optionId);
  renderCatalogNodeAliasTags(optionId, option?.aliases || []);
}
