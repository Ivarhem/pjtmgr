/* ── 자산 인벤토리 (고객사 중심) ── */

const ENV_MAP = {
  prod: "운영",
  dev: "개발",
  staging: "스테이징",
  dr: "DR",
};

const ASSET_STATUS_MAP = {
  planned: "도입예정",
  standby: "대기",
  active: "운영중",
  decommissioned: "폐기",
};

const CATALOG_KIND_LABELS = {
  hardware: "하드웨어",
  software: "소프트웨어",
  model: "모델",
  service: "서비스",
  business_capability: "업무기능",
  dataset: "데이터셋",
};

const RELATION_TYPE_LABELS = {
  HOSTS: "호스팅함",
  INSTALLED_ON: "설치됨",
  PROTECTS: "보호함",
  CONNECTS_TO: "연결됨",
  DEPENDS_ON: "의존함",
  BACKUP_OF: "백업/대체",
  HA_PAIR: "HA 페어",
  OTHER: "기타",
};

const RELATION_TYPE_HINTS = {
  HOSTS: "현재 자산이 대상 자산이나 서비스를 직접 호스팅할 때 사용합니다.",
  INSTALLED_ON: "소프트웨어나 서비스가 특정 자산 위에 설치되어 있을 때 사용합니다.",
  PROTECTS: "방화벽, 보안장비처럼 다른 자산을 보호하는 관계에 사용합니다.",
  CONNECTS_TO: "직접 연결되거나 트래픽이 오가는 장비 관계에 사용합니다.",
  DEPENDS_ON: "서비스나 장비가 다른 자산에 의존해 동작할 때 사용합니다.",
  BACKUP_OF: "예비기나 대체 장비, 백업 관계를 나타낼 때 사용합니다.",
  HA_PAIR: "이중화 페어처럼 상호 대응되는 장비 관계에 사용합니다.",
  OTHER: "정해진 유형으로 분류하기 어려운 연결 관계에 사용합니다.",
};

const ASSET_EVENT_LABELS = {
  create: "등록",
  update: "수정",
  delete: "삭제",
  replacement: "교체",
  failover: "장애 대체",
  repurpose: "용도 전환",
  maintenance_change: "유지보수 변경",
  serial_update: "식별정보 변경",
  note: "메모",
};

const RELATED_PARTNER_LABELS = {
  maintainer: "유지보수사",
  supplier: "공급사",
  installer: "설치사",
  operator: "운영사",
  carrier: "통신사",
  vendor: "제조사/벤더",
  lessor: "임대사",
  owner: "소유주체",
  other: "기타",
};

const CONTACT_ROLE_PRESETS = ["운영", "보안", "네트워크", "시스템", "DBA", "애플리케이션", "개발", "관리자", "승인자"];

const ASSET_EVENT_TEMPLATES = {
  replacement: {
    hint: "기존 자산을 새 자산으로 교체할 때 사용합니다.",
    summary: (asset) => `${asset.asset_name} 교체`,
    detail: (asset) => `${asset.asset_name}의 교체 작업을 기록합니다.\n교체 전 장비, 교체 후 장비, 반영 일시를 남겨주세요.`,
  },
  failover: {
    hint: "장애로 인해 임시 또는 영구 대체가 일어났을 때 사용합니다.",
    summary: (asset) => `${asset.asset_name} 장애 대체`,
    detail: (asset) => `${asset.asset_name} 장애로 대체 자산이 투입되었습니다.\n장애 원인, 대체 자산, 복구 계획을 기록하세요.`,
  },
  repurpose: {
    hint: "기존 용도에서 다른 시스템이나 환경으로 전환할 때 사용합니다.",
    summary: (asset) => `${asset.asset_name} 용도 전환`,
    detail: (asset) => `${asset.asset_name}의 운영 목적이 변경되었습니다.\n기존 용도와 신규 용도, 전환 일자를 기록하세요.`,
  },
  maintenance_change: {
    hint: "유지보수 업체나 담당 주체가 바뀔 때 사용합니다.",
    summary: (asset) => `${asset.asset_name} 유지보수 변경`,
    detail: (asset) => `${asset.asset_name}의 유지보수 정보가 변경되었습니다.\n이전 업체, 신규 업체, 계약 반영일을 기록하세요.`,
  },
  serial_update: {
    hint: "시리얼, 자산번호, 장비 식별정보를 정정하거나 갱신할 때 사용합니다.",
    summary: (asset) => `${asset.asset_name} 식별정보 변경`,
    detail: (asset) => `${asset.asset_name}의 시리얼 또는 식별정보가 변경되었습니다.\n이전 값과 현재 값을 함께 남겨주세요.`,
  },
  note: {
    hint: "특정 유형으로 분류되지 않는 일반 메모를 기록합니다.",
    summary: (asset) => `${asset.asset_name} 메모`,
    detail: () => "",
  },
};

function formatDateTime(value) {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return date.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function buildAssetEventMeta(row) {
  const meta = [];
  if (row.related_asset_name || row.related_asset_code) {
    meta.push(`관련 자산: ${[row.related_asset_name, row.related_asset_code].filter(Boolean).join(" / ")}`);
  }
  if (row.created_by_user_name) {
    meta.push(`기록자: ${row.created_by_user_name}`);
  }
  if (row.asset_name_snapshot || row.asset_code_snapshot) {
    meta.push(`대상 스냅샷: ${[row.asset_name_snapshot, row.asset_code_snapshot].filter(Boolean).join(" / ")}`);
  }
  return meta;
}

const EVENT_FIELD_VISIBILITY = {
  replacement: ["relatedAsset"],
  failover: ["relatedAsset"],
  repurpose: ["fromUse", "toUse"],
  maintenance_change: ["relatedPartner"],
  serial_update: ["oldId", "newId"],
  note: [],
};

const GRID_EDITABLE_FIELDS = new Set([
  "project_asset_number",
  "asset_name",
  "current_role_id",
  "hostname",
  "model",
  "environment",
  "status",
  "center_id",
  "period_id",
  "serial_no",
]);

/* ── CatalogCellEditor (AG Grid 셀 에디터) ── */
class CatalogCellEditor {
  init(params) {
    this.params = params;
    this.selectedModelId = null;

    this.container = document.createElement("div");
    this.container.className = "ag-cell-catalog-editor";

    this.input = document.createElement("input");
    this.input.type = "text";
    this.input.value = params.value || "";
    this.input.className = "ag-cell-input-editor";
    this.input.placeholder = "제조사 또는 모델명 검색";
    this.container.appendChild(this.input);

    this.dropdown = document.createElement("div");
    this.dropdown.className = "ag-cell-catalog-dropdown is-hidden";
    document.body.appendChild(this.dropdown);

    this._searchTimer = null;
    this.input.addEventListener("input", () => this._search());
    this.input.addEventListener("focus", () => this._search());
    this.input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        const first = this.dropdown.querySelector(".catalog-cell-option");
        if (first) first.focus();
      }
      if (e.key === "Escape") {
        setElementHidden(this.dropdown, true);
        this.params.stopEditing();
      }
    });
  }

  _search() {
    const q = this.input.value.trim();
    if (!q) { setElementHidden(this.dropdown, true); return; }
    clearTimeout(this._searchTimer);
    this._searchTimer = setTimeout(async () => {
      try {
        const items = await apiFetch("/api/v1/product-catalog?q=" + encodeURIComponent(q));
        this._renderDropdown(items);
      } catch (e) { showToast(e.message, "error"); }
    }, 300);
  }

  _renderDropdown(items) {
    this.dropdown.textContent = "";
    items.forEach((item) => {
      const div = document.createElement("div");
      const label = ((item.vendor || "") + " " + (item.name || "")).trim();
      const kindLabel = CATALOG_KIND_LABELS[item.product_type] || item.product_type || "미지정";
      div.textContent = "[" + kindLabel + "] " + label;

      if (!buildCatalogClassificationPath(item)) {
        div.className = "catalog-cell-option disabled";
        const warn = document.createElement("span");
        warn.textContent = " (분류 미설정)";
        warn.className = "catalog-warning-note";
        div.appendChild(warn);
      } else {
        div.className = "catalog-cell-option" + (item.is_placeholder ? " placeholder" : "");
        div.tabIndex = -1;
        div.addEventListener("mousedown", (e) => {
          e.preventDefault();
          this._selectItem(item);
        });
        div.addEventListener("keydown", (e) => {
          if (e.key === "Enter") this._selectItem(item);
          if (e.key === "ArrowDown" && div.nextElementSibling) { e.preventDefault(); div.nextElementSibling.focus(); }
          if (e.key === "ArrowUp" && div.previousElementSibling) { e.preventDefault(); div.previousElementSibling.focus(); }
          if (e.key === "Escape") { setElementHidden(this.dropdown, true); this.params.stopEditing(); }
        });
      }
      this.dropdown.appendChild(div);
    });

    const addDiv = document.createElement("div");
    addDiv.className = "catalog-cell-option-new";
    addDiv.textContent = "+ 새 제품 등록";
    addDiv.addEventListener("mousedown", (e) => {
      e.preventDefault();
      setElementHidden(this.dropdown, true);
      this.params.stopEditing();
      openInlineCatalogForm();
    });
    this.dropdown.appendChild(addDiv);

    const rect = this.input.getBoundingClientRect();
    this.dropdown.style.left = rect.left + "px";
    this.dropdown.style.top = rect.bottom + "px";
    this.dropdown.style.width = Math.max(rect.width, 320) + "px";
    setElementHidden(this.dropdown, false);
  }

  _selectItem(item) {
    this.selectedModelId = item.id;
    this.input.value = ((item.vendor || "") + " " + (item.name || "")).trim();
    setElementHidden(this.dropdown, true);
    this.params.stopEditing();
  }

  getGui() { return this.container; }
  afterGuiAttached() { this.input.focus(); this.input.select(); }
  getValue() {
    if (this.selectedModelId) {
      return { _catalogModelId: this.selectedModelId, display: this.input.value };
    }
    return this.params.value;
  }
  destroy() { this.dropdown.remove(); }
  isPopup() { return true; }
}

function isGridFieldEditable(field) {
  return GRID_EDITABLE_FIELDS.has(field);
}

function isRawFallbackField(field, row = {}) {
  if (!row) return false;
  if (field === "center_label") return !!row.center_is_fallback_text;
  if (field === "rack_label") return !!row.rack_is_fallback_text;
  if (field === "classification_level_1_name" || field === "classification_level_2_name" || field === "classification_level_3_name") {
    return !!row.classification_is_fallback_text;
  }
  return false;
}

function getGridCellClass(field, row = null) {
  const classes = [];
  classes.push(GRID_EDITABLE_FIELDS.has(field) ? "infra-cell-editable" : "infra-cell-readonly");
  if (isRawFallbackField(field, row)) classes.push("infra-cell-rawtext");
  return classes.join(" ");
}

function getRoleNameById(roleId, fallbackNames) {
  if (!roleId) return fallbackNames?.length ? fallbackNames.join(", ") : "—";
  const match = _assetRoleOptions.find((role) => role.id === Number(roleId));
  return match?.role_name || fallbackNames?.[0] || "—";
}

const columnDefs = [
  { field: "asset_code", headerName: "코드", width: 120, sort: "asc", editable: false, cellClass: () => getGridCellClass("asset_code") },
  {
    field: "project_asset_number",
    headerName: "프로젝트코드",
    width: 160,
    editable: () => isGridFieldEditable("project_asset_number"),
    valueFormatter: (p) => p.value || "—",
    cellClass: (p) => getGridCellClass(p.colDef.field, p.data),
  },
  {
    field: "period_id",
    headerName: "귀속프로젝트",
    width: 220,
    valueGetter: (p) => p.data?.contract_name || p.data?.period_label || "—",
    editable: () => isGridFieldEditable("period_id"),
    cellEditor: "agSelectCellEditor",
    cellEditorParams: () => ({
      values: ["", ..._periodsCache.map((p) => String(p.id))],
      formatValue: (v) => {
        if (!v) return "—";
        const p = _periodsCache.find((x) => String(x.id) === String(v));
        return p ? (p.contract_name || p.period_label || v) : v;
      },
    }),
    valueParser: (p) => (p.newValue === "" || p.newValue == null ? null : Number(p.newValue)),
    cellClass: (p) => getGridCellClass("period_id"),
  },
  {
    field: "asset_name", headerName: "자산명", flex: 1.2, minWidth: 220,
    editable: () => isGridFieldEditable("asset_name"),
    cellRenderer: (params) => {
      const wrapper = document.createElement("span");
      wrapper.textContent = params.value;
      const aliases = params.data.aliases;
      if (aliases && aliases.length) {
        aliases.forEach(a => {
          const tag = document.createElement("span");
          tag.textContent = a;
          tag.className = "alias-tag";
          wrapper.appendChild(tag);
        });
      }
      return wrapper;
    },
    cellClass: (p) => getGridCellClass(p.colDef.field),
  },
  {
    field: "current_role_id",
    headerName: "현재 역할",
    width: 200,
    editable: () => isGridFieldEditable("current_role_id"),
    cellEditor: "agSelectCellEditor",
    cellEditorParams: () => ({
      values: ["", ..._assetRoleOptions.map((role) => String(role.id))],
      formatValue: (value) => value ? getRoleNameById(Number(value)) : "—",
    }),
    valueFormatter: (p) => getRoleNameById(p.value, p.data?.current_role_names),
    valueParser: (p) => (p.newValue === "" || p.newValue == null ? null : Number(p.newValue)),
    cellClass: (p) => getGridCellClass(p.colDef.field, p.data),
  },
  { field: "customer_asset_number", headerName: "고객 자산번호", width: 150, valueFormatter: (p) => p.value || "—", hide: true, editable: false, cellClass: () => getGridCellClass("customer_asset_number") },
  {
    field: "center_id",
    headerName: "센터정보",
    width: 170,
    valueGetter: (p) => p.data?.center_label || p.data?.center || "—",
    editable: () => isGridFieldEditable("center_id"),
    cellEditor: "agSelectCellEditor",
    cellEditorParams: () => ({
      values: ["", ..._layoutCentersCache.map((c) => String(c.id))],
      formatValue: (v) => {
        if (!v) return "—";
        const c = _layoutCentersCache.find((x) => String(x.id) === String(v));
        return c ? c.name : v;
      },
    }),
    cellClass: (p) => getGridCellClass("center_id", p.data),
  },
  { field: "classification_level_1_name", headerName: "대구분", width: 130, valueFormatter: (p) => p.value || "—", editable: false, cellClass: (p) => getGridCellClass("classification_level_1_name", p.data) },
  { field: "classification_level_2_name", headerName: "중구분", width: 130, valueFormatter: (p) => p.value || "—", editable: false, cellClass: (p) => getGridCellClass("classification_level_2_name", p.data) },
  { field: "classification_level_3_name", headerName: "소구분", width: 140, valueFormatter: (p) => p.value || "—", editable: false, cellClass: (p) => getGridCellClass("classification_level_3_name", p.data) },
  { field: "category", headerName: "분류", width: 130, valueFormatter: (p) => p.value || "—", editable: false, cellClass: (p) => getGridCellClass(p.colDef.field), hide: true },
  { field: "hostname", headerName: "호스트명", width: 160, editable: () => isGridFieldEditable("hostname"), cellClass: (p) => getGridCellClass(p.colDef.field) },
  {
    field: "model", headerName: "모델명", width: 190,
    valueFormatter: (p) => {
      if (p.value && typeof p.value === "object") return p.value.display || "—";
      return p.value || "—";
    },
    editable: () => isGridFieldEditable("model"),
    cellEditor: CatalogCellEditor,
    cellClass: (p) => getGridCellClass(p.colDef.field),
  },
  { field: "serial_no", headerName: "시리얼번호", width: 160, valueFormatter: (p) => p.value || "—", editable: () => isGridFieldEditable("serial_no"), cellClass: (p) => getGridCellClass(p.colDef.field) },
  { field: "operation_type", headerName: "운영구분", width: 120, valueFormatter: (p) => p.value || "—", editable: false, cellClass: (p) => getGridCellClass(p.colDef.field), hide: true },
  {
    field: "environment",
    headerName: "환경",
    width: 100,
    editable: () => isGridFieldEditable("environment"),
    cellEditor: "agSelectCellEditor",
    cellEditorParams: { values: Object.keys(ENV_MAP) },
    valueFormatter: (p) => ENV_MAP[p.value] || p.value || "—",
    cellRenderer: (params) => {
      const label = ENV_MAP[params.value] || params.value || "—";
      const span = document.createElement("span");
      span.className = "badge badge-env-" + (params.value || "unknown");
      span.textContent = label;
      return span;
    },
    cellClass: (p) => getGridCellClass(p.colDef.field),
  },
  {
    field: "status",
    headerName: "상태",
    width: 110,
    editable: () => isGridFieldEditable("status"),
    cellEditor: "agSelectCellEditor",
    cellEditorParams: { values: Object.keys(ASSET_STATUS_MAP) },
    cellRenderer: (params) => {
      const label = ASSET_STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
    cellClass: (p) => getGridCellClass(p.colDef.field),
  },
];

let gridApi;
let _selectedAsset = null;
let _editMode = false;
let _currentTab = "overview";
let _partnerContactsCache = [];
let _partnerAssetsCache = [];
let _allPartnersCache = [];
let _assetNameTouched = false;
let _assetHostnameTouched = false;
let _eventSummaryTouched = false;
let _eventDetailTouched = false;
let _currentAssetRoleAction = null;
let _detailEscArmedAt = 0;
let _assetRoleOptions = [];
let _layoutCentersCache = [];
let _periodsCache = [];
const _layoutRoomsCache = new Map();
const _layoutRacksCache = new Map();
let _requestedAssetId = null;

const NUMERIC_FIELDS = ["size_unit", "lc_count", "ha_count", "utp_count", "power_count", "year_acquired"];
const ASSET_LAYOUT_WIDTH_KEY = "infra_assets_list_width_percent";
const ASSET_LAYOUT_DEFAULT_WIDTH = 66;
const ASSET_LAYOUT_MIN_WIDTH = 40;
const ASSET_LAYOUT_MAX_WIDTH = 75;
const ASSET_DETAIL_OPEN_KEY = "infra_assets_detail_open";
const ASSET_DETAIL_LAST_ID_KEY = "infra_assets_detail_last_id";
const ASSET_DETAIL_LAST_PARTNER_KEY = "infra_assets_detail_last_partner_id";
const ASSET_GRID_COLUMN_STATE_KEY = "infra_assets_grid_column_state_v2";
const CLASSIFICATION_LEVEL_ALIAS_DEFAULTS = ["대구분", "중구분", "소구분", "세구분", "상세구분"];
let _classificationLevelAliases = [...CLASSIFICATION_LEVEL_ALIAS_DEFAULTS];
let _catalogLabelLang = "ko";

const INLINE_CATALOG_ATTRIBUTE_OPTIONS = {
  domain: [
    { value: "net", label: "네트워크" },
    { value: "sec", label: "보안" },
    { value: "svr", label: "서버" },
    { value: "sto", label: "스토리지" },
    { value: "db", label: "데이터베이스" },
  ],
  imp_type: [
    { value: "hw", label: "하드웨어" },
    { value: "sw", label: "소프트웨어" },
    { value: "svc", label: "서비스" },
  ],
  product_family: [
    { value: "fw", label: "방화벽" },
    { value: "ips", label: "IPS" },
    { value: "waf", label: "WAF" },
    { value: "ddos", label: "DDoS" },
    { value: "l2", label: "L2 스위치" },
    { value: "l3", label: "L3 스위치" },
    { value: "l4", label: "L4" },
    { value: "nms", label: "NMS" },
    { value: "siem", label: "SIEM" },
    { value: "x86_server", label: "x86 서버" },
    { value: "unix_server", label: "UNIX 서버" },
    { value: "nas", label: "NAS" },
    { value: "san", label: "SAN" },
    { value: "dbms", label: "DBMS" },
    { value: "os", label: "OS" },
    { value: "backup", label: "백업" },
    { value: "middleware", label: "미들웨어" },
    { value: "generic", label: "기타" },
  ],
  platform: [
    { value: "appliance", label: "Appliance" },
    { value: "x86", label: "x86" },
    { value: "windows", label: "Windows" },
    { value: "linux", label: "Linux" },
    { value: "unix", label: "UNIX" },
    { value: "vm", label: "VM" },
    { value: "container", label: "Container" },
  ],
};

function getClassificationManagementUrl() {
  return "/product-catalog";
}

function buildCatalogClassificationPath(item) {
  const levels = [
    item?.classification_level_1_name,
    item?.classification_level_2_name,
    item?.classification_level_3_name,
    item?.classification_level_4_name,
    item?.classification_level_5_name,
  ].filter(Boolean);
  if (levels.length) return levels.join(" > ");
  return item?.category || "분류 미지정";
}

function updateAssetClassificationPreview(text) {
  const preview = document.getElementById("asset-classification-preview");
  if (!preview) return;
  preview.textContent = text || "카탈로그 제품을 선택하면 분류 경로가 표시됩니다.";
}

async function loadLayoutCenters(partnerId) {
  if (!partnerId) return [];
  _layoutCentersCache = await apiFetch(`/api/v1/centers?partner_id=${partnerId}`);
  return _layoutCentersCache;
}

async function loadPeriodsCache(partnerId) {
  if (!partnerId) { _periodsCache = []; return; }
  try {
    _periodsCache = await apiFetch(`/api/v1/contract-periods?partner_id=${partnerId}`);
  } catch { _periodsCache = []; }
}

function _assetGridStateKey() {
  const presetId = localStorage.getItem("catalog_layout_preset_id") || "default";
  return ASSET_GRID_COLUMN_STATE_KEY + ":" + presetId;
}

function getStoredGridColumnState() {
  const raw = localStorage.getItem(_assetGridStateKey());
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function hasStoredGridColumnState() {
  return !!getStoredGridColumnState()?.length;
}

let _suppressColumnSave = false;

function saveGridColumnState() {
  if (_suppressColumnSave) return;
  if (!gridApi?.getColumnState) return;
  const state = gridApi.getColumnState();
  if (!Array.isArray(state) || !state.length) return;
  localStorage.setItem(_assetGridStateKey(), JSON.stringify(state));
}

function restoreGridColumnState() {
  const state = getStoredGridColumnState();
  if (!state?.length || !gridApi?.applyColumnState) return false;
  return !!gridApi.applyColumnState({ state, applyOrder: true });
}

function fitGridColumnsIfNeeded() {
  if (!gridApi || hasStoredGridColumnState()) return;
  setTimeout(() => gridApi.sizeColumnsToFit(), 0);
}

function getGridTooltipValue(params) {
  const value = params?.valueFormatted ?? params?.value;
  if (value == null || value === "") return "";
  return typeof value === "string" ? value : String(value);
}

function getClassificationLevelHeader(level) {
  return _classificationLevelAliases[level - 1] || `${level}레벨`;
}

function applyClassificationLevelHeaders() {
  if (!gridApi) return;
  const headerMap = {
    classification_level_1_name: getClassificationLevelHeader(1),
    classification_level_2_name: getClassificationLevelHeader(2),
    classification_level_3_name: getClassificationLevelHeader(3),
  };
  columnDefs.forEach((col) => {
    if (headerMap[col.field]) col.headerName = headerMap[col.field];
  });
  _suppressColumnSave = true;
  gridApi.setGridOption("columnDefs", columnDefs);
  const restored = restoreGridColumnState();
  if (!restored) fitGridColumnsIfNeeded();
  _suppressColumnSave = false;
}

async function loadClassificationLevelAliases() {
  _classificationLevelAliases = [...CLASSIFICATION_LEVEL_ALIAS_DEFAULTS];
  try {
    const [layouts, langPref] = await Promise.all([
      apiFetch("/api/v1/classification-layouts?scope_type=global&active_only=true"),
      apiFetch("/api/v1/preferences/catalog.label_lang").catch(() => null),
    ]);
    if (langPref?.value === "en" || langPref?.value === "ko") _catalogLabelLang = langPref.value;
    const allLayouts = Array.isArray(layouts) ? layouts : [];
    const preferredId = Number(localStorage.getItem("catalog_layout_preset_id") || 0);
    const targetLayout = allLayouts.find((l) => Number(l.id) === preferredId)
      || allLayouts.find((l) => l.is_default)
      || allLayouts[0];
    if (targetLayout?.id) {
      const detail = await apiFetch(`/api/v1/classification-layouts/${targetLayout.id}`);
      if (detail?.levels?.length) {
        detail.levels.forEach((level) => {
          const idx = Math.max(Number(level.level_no || 1) - 1, 0);
          if (level.alias) _classificationLevelAliases[idx] = level.alias;
        });
      }
    }
  } catch { /* 기본값 유지 */ }
  applyClassificationLevelHeaders();
}

async function loadLayoutRooms(centerId) {
  if (!centerId) return [];
  if (_layoutRoomsCache.has(centerId)) return _layoutRoomsCache.get(centerId);
  const rows = await apiFetch(`/api/v1/centers/${centerId}/rooms`);
  _layoutRoomsCache.set(centerId, rows);
  return rows;
}

async function loadLayoutRacks(roomId) {
  if (!roomId) return [];
  if (_layoutRacksCache.has(roomId)) return _layoutRacksCache.get(roomId);
  const rows = await apiFetch(`/api/v1/rooms/${roomId}/racks`);
  _layoutRacksCache.set(roomId, rows);
  return rows;
}

function fillSelectOptions(select, items, valueKey, labelBuilder, placeholderText, selectedValue = null, disabled = false) {
  if (!select) return;
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = placeholderText;
  select.appendChild(empty);
  items.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item[valueKey];
    opt.textContent = labelBuilder(item);
    if (selectedValue != null && String(item[valueKey]) === String(selectedValue)) {
      opt.selected = true;
    }
    select.appendChild(opt);
  });
  select.disabled = disabled;
}

/* ── Data loading ── */

async function loadAssets() {
  const cid = getCtxPartnerId();
  if (!cid) {
    gridApi.setGridOption("rowData", []);
    return;
  }
  let url = "/api/v1/assets/inventory?partner_id=" + cid;
  const pid = getCtxProjectId();
  if (pid && isProjectFilterActive()) url += "&period_id=" + pid;
  const statusFilter = document.getElementById("filter-status").value;
  const q = document.getElementById("filter-search").value.trim();
  if (statusFilter) url += "&status=" + statusFilter;
  if (q) url += "&q=" + encodeURIComponent(q);
  // 카탈로그 프리셋 + 한/영 설정 전달
  const layoutId = localStorage.getItem("catalog_layout_preset_id");
  if (layoutId) url += "&layout_id=" + layoutId;
  if (_catalogLabelLang) url += "&lang=" + _catalogLabelLang;

  try {
    const data = await apiFetch(url);
    _partnerAssetsCache = data;
    gridApi.setGridOption("rowData", data);
    restoreAssetDetailState(data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadGridRoleOptions() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) {
    _assetRoleOptions = [];
    return [];
  }
  try {
    _assetRoleOptions = await apiFetch(`/api/v1/asset-roles?partner_id=${partnerId}`);
    return _assetRoleOptions;
  } catch (err) {
    _assetRoleOptions = [];
    showToast(err.message, "error");
    return [];
  }
}

/* ── Grid init ── */

async function initGrid() {
  const partnerId = getCtxPartnerId();
  await Promise.all([
    loadGridRoleOptions(),
    loadLayoutCenters(partnerId),
    loadPeriodsCache(partnerId),
  ]);
  setAssetListWidth(getStoredAssetListWidth(), { persist: false });
  const gridDiv = document.getElementById("grid-assets");
  gridApi = agGrid.createGrid(gridDiv, {
    columnDefs,
    rowData: [],
    defaultColDef: {
      resizable: true,
      sortable: true,
      filter: true,
      tooltipValueGetter: getGridTooltipValue,
    },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => showAssetDetail(data),
      onCellValueChanged: handleGridCellValueChanged,
    }),
    onColumnMoved: saveGridColumnState,
    onColumnVisible: saveGridColumnState,
    onDragStopped: saveGridColumnState,
    onColumnPinned: saveGridColumnState,
    onColumnResized: (event) => {
      if (event.finished) saveGridColumnState();
    },
  });
  _suppressColumnSave = true;
  await loadClassificationLevelAliases();
  const restored = restoreGridColumnState();
  if (!restored) fitGridColumnsIfNeeded();
  _suppressColumnSave = false;
  // 초기 로드는 ctx-changed 이벤트에서 처리 (initContextSelectors 완료 후 dispatch)
  if (getCtxPartnerId()) loadAssets();
}


function applyAssetRowUpdate(row, updated) {
  Object.assign(row, updated);
  if (updated.current_role_id != null) {
    row.current_role_id = updated.current_role_id;
  }
  if (Array.isArray(updated.current_role_names)) {
    row.current_role_names = updated.current_role_names;
  }
  if (updated.period_label !== undefined) {
    row.period_label = updated.period_label;
  }
  if (updated.contract_name !== undefined) {
    row.contract_name = updated.contract_name;
  }
  gridApi?.refreshCells({ force: true });
}

async function handleGridCellValueChanged(event) {
  if (!event?.data || event.newValue === event.oldValue) return;
  const row = event.data;
  const field = event.colDef.field;
  try {
    let updated;
    if (field === "current_role_id") {
      updated = await apiFetch(`/api/v1/assets/${row.id}/current-role`, {
        method: "PATCH",
        body: { asset_role_id: row.current_role_id || null },
      });
    } else if (field === "model") {
      const val = event.newValue;
      if (!val || !val._catalogModelId) {
        row.model = event.oldValue;
        gridApi?.refreshCells({ rowNodes: [event.node], force: true });
        return;
      }
      updated = await apiFetch(`/api/v1/assets/${row.id}`, {
        method: "PATCH",
        body: { model_id: val._catalogModelId },
      });
      row.model = updated.model;
    } else if (field === "center_id" || field === "period_id") {
      const val = event.newValue === "" || event.newValue == null ? null : Number(event.newValue);
      updated = await apiFetch(`/api/v1/assets/${row.id}`, {
        method: "PATCH",
        body: { [field]: val },
      });
    } else {
      updated = await apiFetch(`/api/v1/assets/${row.id}`, {
        method: "PATCH",
        body: { [field]: row[field] || null },
      });
    }
    applyAssetRowUpdate(row, updated);
    if (_selectedAsset?.id === row.id) {
      _selectedAsset = { ..._selectedAsset, ...updated };
      syncAssetRoleActionButtons();
      renderDetailTab(_currentTab || "overview");
    }
  } catch (err) {
    row[field] = event.oldValue;
    gridApi?.refreshCells({ rowNodes: [event.node], force: true });
    showToast(err.message, "error");
  }
}

/* ── Detail panel ── */

const DETAIL_TAB_FIELDS = {
  overview: [
    {
      title: "식별 및 기준 정보",
      description: "자산을 식별하고 역할과 기준 모델을 확인하는 핵심 정보입니다.",
      fields: [
        ["코드", "asset_code"],
        ["프로젝트코드", "project_asset_number"],
        ["고객 자산번호", "customer_asset_number"],
        ["자산명", "asset_name"],
        ["현재 역할", "current_role_names", (v) => v && v.length ? v.join(", ") : "—"],
        ["귀속사업", "period_id", () => _selectedAsset?.period_label || "—"],
        ["상위분류", "catalog_kind", (v) => CATALOG_KIND_LABELS[v] || v],
        ["분류 경로", "classification_path"],
      ],
    },
    {
      title: "사양 및 식별자",
      description: "실물 장비 또는 기준 제품을 식별하는 데 필요한 값입니다.",
      fields: [
        ["제조사", "vendor"],
        ["모델", "model"],
        ["시리얼", "serial_no"],
        ["장비 ID", "equipment_id"],
        ["자산 번호", "asset_number"],
        ["자산 등급", "asset_class"],
      ],
    },
    {
      title: "하드웨어 요약",
      description: "하드웨어 자산에서 주로 확인하는 사양 요약입니다.",
      onlyKinds: ["hardware"],
      fields: [
        ["크기(U)", "size_unit"],
        ["LC", "lc_count"],
        ["HA", "ha_count"],
        ["UTP", "utp_count"],
        ["전원", "power_count"],
        ["전원 유형", "power_type"],
        ["펌웨어", "firmware_version"],
      ],
    },
  ],
  operations: [
    {
      title: "설치 위치",
      description: "센터와 위치, 반입 시점처럼 현장 배치를 파악하는 정보입니다.",
      fields: [
        ["센터", "center_label", (v) => v || _selectedAsset?.center || "—"],
        ["전산실", "room_label"],
        ["랙", "rack_label", (v) => v || _selectedAsset?.rack_no || "—"],
        ["랙 유닛", "rack_unit"],
        ["위치", "location"],
        ["입고일", "received_date"],
        ["도입 연도", "year_acquired"],
      ],
    },
    {
      title: "운영 속성",
      description: "운영 상태와 환경, 담당 부서처럼 운영 기준을 파악하는 정보입니다.",
      fields: [
        ["환경", "environment", (v) => ENV_MAP[v] || v],
        ["상태", "status", (v) => ASSET_STATUS_MAP[v] || v],
        ["부서", "dept"],
        ["유지보수 업체", "maintenance_vendor"],
      ],
    },
    {
      title: "네트워크 및 서비스",
      description: "호스트명, IP, 서비스 식별에 필요한 값을 모아 봅니다.",
      fields: [
        ["호스트명", "hostname"],
        ["클러스터", "cluster"],
        ["서비스명", "service_name"],
        ["존", "zone"],
        ["서비스 IP", "service_ip"],
        ["관리 IP", "mgmt_ip"],
      ],
    },
    {
      title: "담당자 메모",
      description: "자산에 직접 기록된 기본 담당자 정보를 빠르게 확인합니다.",
      fields: [
        ["주 담당자", "primary_contact_name"],
        ["부 담당자", "secondary_contact_name"],
        ["비고", "note"],
      ],
    },
  ],
};

const DETAIL_EDIT_FIELDS = {
  overview: [
    ["프로젝트코드", "project_asset_number"],
    ["고객 자산번호", "customer_asset_number"],
    ["자산명", "asset_name"],
    ["귀속사업", "period_id"],
    ["카탈로그 제품", "model_id"],
    ["시리얼", "serial_no"],
    ["장비 ID", "equipment_id"],
    ["자산 번호", "asset_number"],
    ["자산 등급", "asset_class"],
    ["크기(U)", "size_unit"],
    ["LC", "lc_count"],
    ["HA", "ha_count"],
    ["UTP", "utp_count"],
    ["전원", "power_count"],
    ["전원 유형", "power_type"],
    ["펌웨어", "firmware_version"],
  ],
  operations: [
    ["센터", "center_id"],
    ["전산실", "room_id"],
    ["랙", "rack_id"],
    ["랙 유닛", "rack_unit"],
    ["위치", "location"],
    ["입고일", "received_date"],
    ["도입 연도", "year_acquired"],
    ["환경", "environment"],
    ["상태", "status"],
    ["부서", "dept"],
    ["유지보수 업체", "maintenance_vendor"],
    ["호스트명", "hostname"],
    ["클러스터", "cluster"],
    ["서비스명", "service_name"],
    ["존", "zone"],
    ["서비스 IP", "service_ip"],
    ["관리 IP", "mgmt_ip"],
    ["주 담당자", "primary_contact_name"],
    ["부 담당자", "secondary_contact_name"],
    ["비고", "note"],
  ],
};

function showAssetDetail(asset) {
  _selectedAsset = asset;
  _detailEscArmedAt = 0;
  rememberSelectedAssetState(asset);
  syncAssetDetailTabs(asset.catalog_kind || "hardware");
  syncAssetRoleActionButtons();
  syncAssetLayoutState(true);
  document.getElementById("detail-asset-name").textContent =
    asset.asset_name + (asset.hostname ? " (" + asset.hostname + ")" : "");
  renderDetailTab("overview");
}

function syncAssetDetailTabs(kind) {
  const connectionsTab = document.querySelector('.detail-tabs .tab-btn[data-dtab="connections"]');
  if (!connectionsTab) return;
  connectionsTab.classList.toggle("is-hidden", false);
  if (!["overview", "operations", "connections", "history"].includes(_currentTab)) {
    _currentTab = "overview";
  }
}

function clampAssetListWidth(value) {
  return Math.min(ASSET_LAYOUT_MAX_WIDTH, Math.max(ASSET_LAYOUT_MIN_WIDTH, value));
}

function getStoredAssetListWidth() {
  const raw = Number(localStorage.getItem(ASSET_LAYOUT_WIDTH_KEY));
  return Number.isFinite(raw) ? clampAssetListWidth(raw) : ASSET_LAYOUT_DEFAULT_WIDTH;
}

function setAssetListWidth(percent, { persist = true } = {}) {
  const layout = document.getElementById("asset-layout");
  if (!layout) return;
  const normalized = clampAssetListWidth(percent);
  layout.style.setProperty("--asset-list-width", `${normalized}%`);
  if (persist) {
    localStorage.setItem(ASSET_LAYOUT_WIDTH_KEY, String(normalized));
  }
  fitGridColumnsIfNeeded();
}

function rememberSelectedAssetState(asset) {
  const partnerId = asset?.partner_id || getCtxPartnerId();
  if (!asset?.id || !partnerId) return;
  localStorage.setItem(ASSET_DETAIL_LAST_ID_KEY, String(asset.id));
  localStorage.setItem(ASSET_DETAIL_LAST_PARTNER_KEY, String(partnerId));
}

function getRequestedAssetId() {
  if (_requestedAssetId !== null) return _requestedAssetId;
  const raw = new URLSearchParams(window.location.search).get("asset_id");
  const parsed = raw ? Number(raw) : NaN;
  _requestedAssetId = Number.isFinite(parsed) ? parsed : 0;
  return _requestedAssetId;
}

function consumeRequestedAssetId() {
  _requestedAssetId = 0;
  const url = new URL(window.location.href);
  url.searchParams.delete("asset_id");
  window.history.replaceState({}, "", url.pathname + url.search + url.hash);
}

function openAssetDetailFromRows(rows, assetId) {
  const match = (rows || []).find((row) => row.id === assetId);
  if (!match) return false;
  showAssetDetail(match);
  if (gridApi) {
    gridApi.forEachNode((node) => {
      if (node.data?.id === assetId) node.setSelected(true);
    });
  }
  return true;
}

function restoreAssetDetailState(rows) {
  const requestedAssetId = getRequestedAssetId();
  if (requestedAssetId > 0) {
    if (openAssetDetailFromRows(rows, requestedAssetId)) {
      consumeRequestedAssetId();
    }
    return;
  }
  const shouldOpen = localStorage.getItem(ASSET_DETAIL_OPEN_KEY) === "1";
  const lastId = Number(localStorage.getItem(ASSET_DETAIL_LAST_ID_KEY));
  const lastPartnerId = localStorage.getItem(ASSET_DETAIL_LAST_PARTNER_KEY);
  const currentPartnerId = String(getCtxPartnerId() || "");
  if (!shouldOpen || !Number.isFinite(lastId) || !lastPartnerId || lastPartnerId !== currentPartnerId) {
    return;
  }
  openAssetDetailFromRows(rows, lastId);
}

function syncAssetLayoutState(isOpen) {
  const layout = document.getElementById("asset-layout");
  const panel = document.getElementById("asset-detail-panel");
  const shell = document.getElementById("asset-detail-shell");
  const empty = document.getElementById("asset-detail-empty");
  const splitter = document.getElementById("asset-splitter");
  const handle = document.getElementById("btn-minimize-detail");
  if (!layout || !panel || !shell || !empty || !splitter || !handle) return;
  layout.classList.toggle("is-detail-open", isOpen);
  panel.classList.toggle("is-hidden", !isOpen);
  shell.classList.toggle("is-hidden", !isOpen);
  empty.classList.toggle("is-hidden", isOpen);
  splitter.classList.toggle("is-hidden", !isOpen);
  handle.textContent = isOpen ? "❮" : "❯";
  localStorage.setItem(ASSET_DETAIL_OPEN_KEY, isOpen ? "1" : "0");
  if (isOpen) {
    setAssetListWidth(getStoredAssetListWidth(), { persist: false });
  }
  fitGridColumnsIfNeeded();
}

function initAssetSplitter() {
  const splitter = document.getElementById("asset-splitter");
  const layout = document.getElementById("asset-layout");
  const listPanel = layout?.querySelector(".asset-list-panel");
  if (!splitter || !layout || !listPanel) return;

  let dragging = false;

  splitter.addEventListener("mousedown", (event) => {
    if (!layout.classList.contains("is-detail-open")) return;
    dragging = true;
    splitter.classList.add("is-dragging");
    event.preventDefault();
  });

  document.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    if (!rect.width) return;
    const nextPercent = ((event.clientX - rect.left) / rect.width) * 100;
    setAssetListWidth(nextPercent);
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
  });
}

function hasOpenDialog() {
  return !!document.querySelector("dialog[open]");
}

function handleAssetDetailEscape(event) {
  if (event.key !== "Escape") return;
  if (!_selectedAsset || hasOpenDialog()) return;
  const now = Date.now();
  if (now - _detailEscArmedAt < 800) {
    event.preventDefault();
    closeDetail({ clearSelection: false });
    return;
  }
  _detailEscArmedAt = now;
}

function reopenDetail() {
  if (!_selectedAsset) {
    showToast("자산을 먼저 선택하세요.", "info");
    return;
  }
  syncAssetLayoutState(true);
  document.getElementById("detail-asset-name").textContent =
    _selectedAsset.asset_name + (_selectedAsset.hostname ? " (" + _selectedAsset.hostname + ")" : "");
  renderDetailTab(_currentTab || "overview");
}

function toggleDetailPanel() {
  const layout = document.getElementById("asset-layout");
  if (layout?.classList.contains("is-detail-open")) {
    closeDetail({ clearSelection: false });
  } else {
    reopenDetail();
  }
}

function renderDetailTab(tab) {
  _currentTab = tab;
  if (_editMode) _editMode = false;

  const container = document.getElementById("detail-content");
  while (container.firstChild) container.removeChild(container.firstChild);

  document.querySelectorAll(".detail-tabs .tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.dtab === tab);
  });

  if (!_selectedAsset) return;

  if (tab === "connections") { renderConnectionsTab(container); return; }
  if (tab === "history") { renderHistoryTab(container); return; }

  renderStructuredDetailTab(tab, container);
}

function getDetailFieldValue(key, fmt) {
  const raw = _selectedAsset?.[key];
  if (fmt) return fmt(raw);
  if (raw == null || raw === "") return "—";
  return String(raw);
}

function getDetailFieldClass(key) {
  if (!_selectedAsset) return "";
  if (key === "center_label" && _selectedAsset.center_is_fallback_text) return "asset-detail-value-rawtext";
  if (key === "rack_label" && _selectedAsset.rack_is_fallback_text) return "asset-detail-value-rawtext";
  if (key === "classification_path" && _selectedAsset.classification_is_fallback_text) return "asset-detail-value-rawtext";
  return "";
}

function hasVisibleFieldValue(key, fmt) {
  const value = getDetailFieldValue(key, fmt);
  return value !== "—";
}

function createDetailSectionCard(title, description) {
  const section = document.createElement("section");
  section.className = "asset-detail-section";
  if (title) {
    const header = document.createElement("div");
    header.className = "asset-detail-section-header";
    header.innerHTML = `
      <h3 class="asset-detail-section-title">${escapeHtml(title)}</h3>
      ${description ? `<p class="asset-detail-section-desc">${escapeHtml(description)}</p>` : ""}
    `;
    section.appendChild(header);
  }
  return section;
}

function renderStructuredDetailTab(tab, container) {
  const sections = DETAIL_TAB_FIELDS[tab];
  if (!sections) return;
  const wrap = document.createElement("div");
  wrap.className = "asset-detail-sections";

  sections.forEach((sectionConfig) => {
    if (sectionConfig.onlyKinds && !sectionConfig.onlyKinds.includes(_selectedAsset.catalog_kind)) {
      return;
    }
    const visibleFields = sectionConfig.fields.filter(([, key, fmt]) => hasVisibleFieldValue(key, fmt));
    if (!visibleFields.length) return;

    const section = createDetailSectionCard(sectionConfig.title, sectionConfig.description);
    const grid = document.createElement("div");
    grid.className = "detail-grid asset-detail-grid";
    visibleFields.forEach(([label, key, fmt]) => {
      const dt = document.createElement("dt");
      dt.textContent = label === "__CLASSIFICATION__" ? CLASSIFICATION_LEVEL_ALIAS_DEFAULTS[2] : label;
      const dd = document.createElement("dd");
      dd.textContent = getDetailFieldValue(key, fmt);
      const extraClass = getDetailFieldClass(key);
      if (extraClass) dd.classList.add(extraClass);
      grid.appendChild(dt);
      grid.appendChild(dd);
    });
    section.appendChild(grid);
    wrap.appendChild(section);
  });

  if (!wrap.children.length) {
    const empty = document.createElement("p");
    empty.className = "text-muted asset-subtable-empty";
    empty.textContent = "표시할 상세 정보가 없습니다.";
    container.appendChild(empty);
    return;
  }
  container.appendChild(wrap);
}

async function renderConnectionsTab(container) {
  const groups = [
    ["소프트웨어", "연결된 소프트웨어와 라이선스 정보를 관리합니다.", renderSoftwareTab],
    ["IP 할당", "서비스/관리 IP와 인터페이스 연결 정보를 관리합니다.", renderIpTab],
    ["담당자", "운영과 보안, 시스템 담당자를 연결합니다.", renderContactsTab],
    ["관련업체", "유지보수사, 공급사, 운영사 등 연관 업체를 관리합니다.", renderRelatedPartnersTab],
    ["자산 관계", "호스팅, 보호, 의존 같은 자산 간 관계를 관리합니다.", renderRelationsTab],
    ["별칭", "고객사명, 레거시명, 내부명을 함께 관리합니다.", renderAliasesTab],
  ];

  const wrap = document.createElement("div");
  wrap.className = "asset-detail-sections";
  container.appendChild(wrap);

  for (const [title, description, renderer] of groups) {
    const section = createDetailSectionCard(title, description);
    wrap.appendChild(section);
    // eslint-disable-next-line no-await-in-loop
    await renderer(section);
  }
}

/* ── Sub-entity tab helpers ── */

function _subTabHeader(container, title, onAdd) {
  const hdr = document.createElement("div");
  hdr.className = "asset-subtab-header";
  const h = document.createElement("span");
  h.className = "asset-subtab-title";
  h.textContent = title;
  hdr.appendChild(h);
  const btn = document.createElement("button");
  btn.className = "btn btn-sm btn-primary";
  btn.textContent = "+ 추가";
  btn.addEventListener("click", onAdd);
  hdr.appendChild(btn);
  container.appendChild(hdr);
}

function _subTable(container, columns, rows, actions) {
  if (!rows.length) {
    const p = document.createElement("p");
    p.className = "text-muted asset-subtable-empty";
    p.textContent = "데이터가 없습니다.";
    container.appendChild(p);
    return;
  }
  const tbl = document.createElement("table");
  tbl.className = "asset-subtable";
  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  columns.forEach(c => {
    const th = document.createElement("th");
    th.textContent = c.label;
    th.className = "asset-subtable-head";
    hr.appendChild(th);
  });
  if (actions) {
    const th = document.createElement("th");
    th.className = "asset-subtable-head asset-subtable-head-actions";
    hr.appendChild(th);
  }
  thead.appendChild(hr);
  tbl.appendChild(thead);
  const tbody = document.createElement("tbody");
  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.className = "asset-subtable-row";
    columns.forEach(c => {
      const td = document.createElement("td");
      td.className = "asset-subtable-cell";
      const v = row[c.field];
      td.textContent = c.fmt ? c.fmt(v, row) : (v != null ? String(v) : "—");
      if (c.className) td.classList.add(c.className);
      tr.appendChild(td);
    });
    if (actions) {
      const td = document.createElement("td");
      td.className = "asset-subtable-cell asset-subtable-cell-actions";
      actions.forEach(a => {
        const b = document.createElement("button");
        b.className = "btn btn-sm asset-subtable-action" + (a.danger ? " btn-danger" : "");
        b.textContent = a.label;
        b.addEventListener("click", () => a.handler(row));
        td.appendChild(b);
      });
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  });
  tbl.appendChild(tbody);
  container.appendChild(tbl);
}

/* ── 소프트웨어 탭 ── */

async function renderSoftwareTab(container) {
  _subTabHeader(container, "설치 소프트웨어", () => openSoftwareModal());
  try {
    const data = await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/software");
    _subTable(container, [
      { label: "소프트웨어명", field: "software_name" },
      { label: "버전", field: "version" },
      { label: "라이선스", field: "license_type" },
      { label: "수량", field: "license_count" },
      { label: "관계", field: "relation_type" },
      { label: "비고", field: "note" },
    ], data, [
      { label: "수정", handler: (r) => openSoftwareModal(r) },
      { label: "삭제", danger: true, handler: (r) => deleteSoftware(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

function openSoftwareModal(sw) {
  const m = document.getElementById("modal-software");
  document.getElementById("sw-id").value = sw ? sw.id : "";
  document.getElementById("sw-name").value = sw ? sw.software_name : "";
  document.getElementById("sw-version").value = sw ? (sw.version || "") : "";
  document.getElementById("sw-license-type").value = sw ? (sw.license_type || "") : "";
  document.getElementById("sw-license-count").value = sw ? (sw.license_count != null ? sw.license_count : "") : "";
  document.getElementById("sw-relation-type").value = sw ? sw.relation_type : "installed";
  document.getElementById("sw-note").value = sw ? (sw.note || "") : "";
  document.getElementById("modal-software-title").textContent = sw ? "소프트웨어 수정" : "소프트웨어 추가";
  m.showModal();
}

async function saveSoftware() {
  const swId = document.getElementById("sw-id").value;
  const payload = {
    software_name: document.getElementById("sw-name").value,
    version: document.getElementById("sw-version").value || null,
    license_type: document.getElementById("sw-license-type").value || null,
    license_count: document.getElementById("sw-license-count").value ? Number(document.getElementById("sw-license-count").value) : null,
    relation_type: document.getElementById("sw-relation-type").value,
    note: document.getElementById("sw-note").value || null,
  };
  try {
    if (swId) {
      await apiFetch("/api/v1/asset-software/" + swId, { method: "PATCH", body: payload });
    } else {
      await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/software", { method: "POST", body: payload });
    }
    document.getElementById("modal-software").close();
    showToast(swId ? "수정되었습니다." : "추가되었습니다.");
    renderDetailTab("connections");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteSoftware(sw) {
  confirmDelete("소프트웨어 '" + sw.software_name + "'을(를) 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-software/" + sw.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("connections");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── IP 할당 탭 ── */

async function renderIpTab(container) {
  _subTabHeader(container, "IP 할당", () => openIpModal());
  try {
    const data = await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/ips");
    _subTable(container, [
      { label: "IP 주소", field: "ip_address" },
      { label: "유형", field: "ip_type" },
      { label: "인터페이스", field: "interface_name" },
      { label: "호스트명", field: "hostname" },
      { label: "VLAN", field: "vlan_id" },
      { label: "대표", field: "is_primary", fmt: v => v ? "●" : "" },
    ], data, [
      { label: "수정", handler: (r) => openIpModal(r) },
      { label: "삭제", danger: true, handler: (r) => deleteIp(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

function openIpModal(ip) {
  const m = document.getElementById("modal-ip");
  document.getElementById("ip-id").value = ip ? ip.id : "";
  document.getElementById("ip-address").value = ip ? ip.ip_address : "";
  document.getElementById("ip-type").value = ip ? ip.ip_type : "service";
  document.getElementById("ip-interface").value = ip ? (ip.interface_name || "") : "";
  document.getElementById("ip-hostname").value = ip ? (ip.hostname || "") : "";
  document.getElementById("ip-vlan").value = ip ? (ip.vlan_id || "") : "";
  document.getElementById("ip-network").value = ip ? (ip.network || "") : "";
  document.getElementById("ip-netmask").value = ip ? (ip.netmask || "") : "";
  document.getElementById("ip-gateway").value = ip ? (ip.gateway || "") : "";
  document.getElementById("ip-is-primary").checked = ip ? ip.is_primary : false;
  document.getElementById("ip-note").value = ip ? (ip.note || "") : "";
  document.getElementById("modal-ip-title").textContent = ip ? "IP 수정" : "IP 추가";
  m.showModal();
}

async function saveIp() {
  const ipId = document.getElementById("ip-id").value;
  const payload = {
    ip_address: document.getElementById("ip-address").value,
    ip_type: document.getElementById("ip-type").value,
    interface_name: document.getElementById("ip-interface").value || null,
    hostname: document.getElementById("ip-hostname").value || null,
    vlan_id: document.getElementById("ip-vlan").value || null,
    network: document.getElementById("ip-network").value || null,
    netmask: document.getElementById("ip-netmask").value || null,
    gateway: document.getElementById("ip-gateway").value || null,
    is_primary: document.getElementById("ip-is-primary").checked,
    note: document.getElementById("ip-note").value || null,
  };
  try {
    if (ipId) {
      await apiFetch("/api/v1/asset-ips/" + ipId, { method: "PATCH", body: payload });
    } else {
      await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/ips", { method: "POST", body: payload });
    }
    document.getElementById("modal-ip").close();
    showToast(ipId ? "수정되었습니다." : "추가되었습니다.");
    renderDetailTab("connections");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteIp(ip) {
  confirmDelete("IP '" + ip.ip_address + "'을(를) 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-ips/" + ip.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("connections");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── 담당자 탭 ── */

async function renderContactsTab(container) {
  _subTabHeader(container, "담당자", () => openContactModal());
  try {
    const data = await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/contacts");
    _subTable(container, [
      { label: "담당자", field: "contact_name", fmt: (v, row) => {
        const parts = [v || ("담당자#" + row.contact_id)];
        if (row.contact_phone) parts.push(row.contact_phone);
        if (row.contact_email) parts.push(row.contact_email);
        return parts.join(" / ");
      }},
      { label: "역할", field: "role" },
    ], data, [
      { label: "수정", handler: (r) => openContactModal(r) },
      { label: "해제", danger: true, handler: (r) => deleteContact(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

async function openContactModal(ct) {
  const m = document.getElementById("modal-contact");
  await populateContactSelect(ct ? ct.contact_id : null);
  document.getElementById("ct-id").value = ct ? ct.id : "";
  document.getElementById("ct-contact-id").value = ct ? ct.contact_id : "";
  document.getElementById("ct-contact-id").disabled = !!ct;
  setContactRoleValue(ct ? (ct.role || "") : "");
  m.showModal();
}

function syncContactRoleInput() {
  const preset = document.getElementById("ct-role-preset").value;
  document.getElementById("ct-role-custom-wrap").classList.toggle("is-hidden", preset !== "custom");
}

function setContactRoleValue(role) {
  const preset = document.getElementById("ct-role-preset");
  const custom = document.getElementById("ct-role-custom");
  if (!role) {
    preset.value = "";
    custom.value = "";
  } else if (CONTACT_ROLE_PRESETS.includes(role)) {
    preset.value = role;
    custom.value = "";
  } else {
    preset.value = "custom";
    custom.value = role;
  }
  syncContactRoleInput();
}

function getContactRoleValue() {
  const preset = document.getElementById("ct-role-preset").value;
  if (!preset) return null;
  if (preset === "custom") {
    const custom = document.getElementById("ct-role-custom").value.trim();
    return custom || null;
  }
  return preset;
}

async function saveContact() {
  const ctId = document.getElementById("ct-id").value;
  const contactId = document.getElementById("ct-contact-id").value;
  if (!contactId) { showToast("담당자를 선택하세요.", "warning"); return; }
  const role = getContactRoleValue();
  if (document.getElementById("ct-role-preset").value === "custom" && !role) {
    showToast("직접 입력 역할을 입력하세요.", "warning");
    return;
  }
  const payload = {
    contact_id: Number(contactId),
    role,
  };
  try {
    if (ctId) {
      await apiFetch("/api/v1/asset-contacts/" + ctId, { method: "PATCH", body: { role: payload.role } });
    } else {
      await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/contacts", { method: "POST", body: payload });
    }
    document.getElementById("modal-contact").close();
    showToast(ctId ? "수정되었습니다." : "연결되었습니다.");
    renderDetailTab("connections");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteContact(ct) {
  confirmDelete("담당자 연결을 해제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-contacts/" + ct.id, { method: "DELETE" });
      showToast("해제되었습니다.");
      renderDetailTab("connections");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── 관련업체 탭 ── */

async function renderRelatedPartnersTab(container) {
  _subTabHeader(container, "관련업체", () => openRelatedPartnerModal());
  try {
    const data = await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/related-partners");
    _subTable(container, [
      {
        label: "업체",
        field: "partner_name",
        fmt: (v, row) => {
          const parts = [v || ("업체#" + row.partner_id)];
          if (row.partner_type) parts.push(row.partner_type);
          if (row.partner_phone) parts.push(row.partner_phone);
          return parts.join(" / ");
        },
      },
      { label: "관계", field: "relation_type", fmt: (v) => RELATED_PARTNER_LABELS[v] || v },
      { label: "대표", field: "is_primary", fmt: (v) => (v ? "●" : "") },
      {
        label: "유효기간",
        field: "valid_from",
        fmt: (_, row) => {
          const from = row.valid_from || "—";
          const to = row.valid_to || "현재";
          return `${from} ~ ${to}`;
        },
      },
      { label: "비고", field: "note" },
    ], data, [
      { label: "수정", handler: (r) => openRelatedPartnerModal(r) },
      { label: "삭제", danger: true, handler: (r) => deleteRelatedPartner(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

async function loadPartners() {
  if (_allPartnersCache.length) return _allPartnersCache;
  const partners = await apiFetch("/api/v1/partners");
  _allPartnersCache = partners;
  return partners;
}

async function loadAssetRolesForPartner() {
  const partnerId = _selectedAsset?.partner_id || getCtxPartnerId();
  if (!partnerId) return [];
  return apiFetch(`/api/v1/asset-roles?partner_id=${partnerId}`);
}

async function populateRelatedPartnerSelect(selectedId) {
  const sel = document.getElementById("rp-partner-id");
  if (!sel) return;
  const partners = await loadPartners();
  sel.textContent = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = partners.length ? "-- 업체 선택 --" : "(선택 가능한 업체 없음)";
  sel.appendChild(placeholder);
  partners.forEach((partner) => {
    const opt = document.createElement("option");
    opt.value = partner.id;
    const parts = [partner.name];
    if (partner.partner_type) parts.push(partner.partner_type);
    if (partner.phone) parts.push(partner.phone);
    opt.textContent = parts.join(" / ");
    if (partner.id === selectedId) opt.selected = true;
    sel.appendChild(opt);
  });
}

async function openRelatedPartnerModal(rel) {
  const modal = document.getElementById("modal-related-partner");
  await populateRelatedPartnerSelect(rel ? rel.partner_id : null);
  document.getElementById("rp-id").value = rel ? rel.id : "";
  document.getElementById("rp-partner-id").value = rel ? rel.partner_id : "";
  document.getElementById("rp-partner-id").disabled = !!rel;
  document.getElementById("rp-relation-type").value = rel ? rel.relation_type : "maintainer";
  document.getElementById("rp-valid-from").value = rel?.valid_from || "";
  document.getElementById("rp-valid-to").value = rel?.valid_to || "";
  document.getElementById("rp-is-primary").checked = rel ? rel.is_primary : false;
  document.getElementById("rp-note").value = rel?.note || "";
  document.getElementById("modal-related-partner-title").textContent = rel ? "관련업체 수정" : "관련업체 연결";
  modal.showModal();
}

async function saveRelatedPartner() {
  const relationId = document.getElementById("rp-id").value;
  const partnerId = document.getElementById("rp-partner-id").value;
  if (!partnerId) { showToast("업체를 선택하세요.", "warning"); return; }
  const payload = {
    partner_id: Number(partnerId),
    relation_type: document.getElementById("rp-relation-type").value,
    is_primary: document.getElementById("rp-is-primary").checked,
    valid_from: document.getElementById("rp-valid-from").value || null,
    valid_to: document.getElementById("rp-valid-to").value || null,
    note: document.getElementById("rp-note").value.trim() || null,
  };
  try {
    if (relationId) {
      await apiFetch("/api/v1/asset-related-partners/" + relationId, { method: "PATCH", body: payload });
    } else {
      await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/related-partners", { method: "POST", body: payload });
    }
    document.getElementById("modal-related-partner").close();
    showToast(relationId ? "수정되었습니다." : "관련업체가 연결되었습니다.");
    renderDetailTab("connections");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteRelatedPartner(rel) {
  confirmDelete("관련업체 연결을 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-related-partners/" + rel.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("connections");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── 관계 탭 ── */

async function renderRelationsTab(container) {
  _subTabHeader(container, "자산 관계", () => openRelationModal());
  try {
    const data = await apiFetch("/api/v1/asset-relations?asset_id=" + _selectedAsset.id);
    _subTable(container, [
      { label: "방향", field: "src_asset_id", fmt: (v) => v === _selectedAsset.id ? "→" : "←" },
      { label: "대상 자산", field: "id", fmt: (_, r) => {
        const other = r.src_asset_id === _selectedAsset.id;
        const name = other ? r.dst_asset_name : r.src_asset_name;
        const host = other ? r.dst_hostname : r.src_hostname;
        return (name || "?") + (host ? " (" + host + ")" : "");
      }},
      { label: "관계 유형", field: "relation_type", fmt: v => RELATION_TYPE_LABELS[v] || v },
      { label: "비고", field: "note" },
    ], data, [
      { label: "삭제", danger: true, handler: (r) => deleteRelation(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

async function openRelationModal() {
  const m = document.getElementById("modal-relation");
  await populateRelationAssetSelect();
  document.getElementById("rel-id").value = "";
  document.getElementById("rel-dst-asset-id").value = "";
  document.getElementById("rel-type").value = "HOSTS";
  document.getElementById("rel-note").value = "";
  document.getElementById("modal-relation-title").textContent = "관계 추가";
  updateRelationTypeHint();
  m.showModal();
}

function updateRelationTypeHint() {
  const type = document.getElementById("rel-type").value;
  const hint = document.getElementById("rel-type-hint");
  if (!hint) return;
  hint.textContent = RELATION_TYPE_HINTS[type] || "현재 자산과 대상 자산의 연결 의미를 선택하세요.";
  const note = document.getElementById("rel-note");
  if (note && !note.value.trim()) {
    note.placeholder = `${RELATION_TYPE_LABELS[type] || type} 관계의 맥락이나 예외사항을 적어두세요.`;
  }
}

async function saveRelation() {
  const dstAssetId = document.getElementById("rel-dst-asset-id").value;
  if (!dstAssetId) { showToast("대상 자산을 선택하세요.", "warning"); return; }
  const payload = {
    src_asset_id: _selectedAsset.id,
    dst_asset_id: Number(dstAssetId),
    relation_type: document.getElementById("rel-type").value,
    note: document.getElementById("rel-note").value || null,
  };
  try {
    await apiFetch("/api/v1/asset-relations", { method: "POST", body: payload });
    document.getElementById("modal-relation").close();
    showToast("관계가 추가되었습니다.");
    renderDetailTab("connections");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteRelation(rel) {
  confirmDelete("이 관계를 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-relations/" + rel.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("connections");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── 별칭(Alias) 탭 ── */

const ALIAS_TYPE_MAP = { INTERNAL: "내부", CUSTOMER: "고객사", VENDOR: "벤더", TEAM: "팀", LEGACY: "레거시", ETC: "기타" };

async function renderAliasesTab(container) {
  _subTabHeader(container, "별칭", () => openAliasModal());
  try {
    const data = await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/aliases");
    _subTable(container, [
      { label: "별칭", field: "alias_name" },
      { label: "유형", field: "alias_type", fmt: v => ALIAS_TYPE_MAP[v] || v },
      { label: "출처", field: "source_text", fmt: (v, r) => r.source_partner_id ? "업체#" + r.source_partner_id : (v || "—") },
      { label: "대표", field: "is_primary", fmt: v => v ? "●" : "" },
      { label: "비고", field: "note" },
    ], data, [
      { label: "수정", handler: (r) => openAliasModal(r) },
      { label: "삭제", danger: true, handler: (r) => deleteAlias(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

function openAliasModal(alias) {
  const m = document.getElementById("modal-alias");
  document.getElementById("alias-id").value = alias ? alias.id : "";
  document.getElementById("alias-name").value = alias ? alias.alias_name : "";
  document.getElementById("alias-type").value = alias ? alias.alias_type : "INTERNAL";
  document.getElementById("alias-source-partner").value = alias ? (alias.source_partner_id || "") : "";
  document.getElementById("alias-source-text").value = alias ? (alias.source_text || "") : "";
  document.getElementById("alias-note").value = alias ? (alias.note || "") : "";
  document.getElementById("alias-is-primary").checked = alias ? alias.is_primary : false;
  document.getElementById("modal-alias-title").textContent = alias ? "별칭 수정" : "별칭 추가";
  m.showModal();
}

async function saveAlias() {
  const aliasId = document.getElementById("alias-id").value;
  const payload = {
    alias_name: document.getElementById("alias-name").value,
    alias_type: document.getElementById("alias-type").value,
    source_partner_id: document.getElementById("alias-source-partner").value ? Number(document.getElementById("alias-source-partner").value) : null,
    source_text: document.getElementById("alias-source-text").value || null,
    note: document.getElementById("alias-note").value || null,
    is_primary: document.getElementById("alias-is-primary").checked,
  };
  try {
    if (aliasId) {
      await apiFetch("/api/v1/asset-aliases/" + aliasId, { method: "PATCH", body: payload });
    } else {
      await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/aliases", { method: "POST", body: payload });
    }
    document.getElementById("modal-alias").close();
    showToast(aliasId ? "수정되었습니다." : "추가되었습니다.");
    renderDetailTab("connections");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteAlias(alias) {
  confirmDelete("별칭 '" + alias.alias_name + "'을(를) 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-aliases/" + alias.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("connections");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── Detail edit modal ── */

async function buildDetailEditFields(tab) {
  const container = document.getElementById("asset-detail-edit-fields");
  container.textContent = "";
  const fields = DETAIL_EDIT_FIELDS[tab];
  if (!fields) return;

  for (const [label, key] of fields) {
    const fieldWrap = document.createElement("label");
    fieldWrap.className = "full-width";
    if (!["note", "location", "service_name"].includes(key)) {
      fieldWrap.classList.remove("full-width");
    }
    fieldWrap.textContent = label;

    const currentVal = _selectedAsset[key];
    let input;

    if (key === "period_id") {
      input = document.createElement("select");
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "-- 선택 안함 --";
      input.appendChild(empty);
      try {
        const periods = await apiFetch("/api/v1/contract-periods?partner_id=" + _selectedAsset.partner_id);
        periods.forEach((p) => {
          const opt = document.createElement("option");
          opt.value = p.id;
          opt.textContent = [p.period_label, p.contract_name].filter(Boolean).join(" · ") || ("사업 #" + p.id);
          if (p.id === currentVal) opt.selected = true;
          input.appendChild(opt);
        });
      } catch (_) {
        const opt = document.createElement("option");
        opt.value = currentVal || "";
        opt.textContent = _selectedAsset.period_label || "현재 귀속사업";
        opt.selected = true;
        input.appendChild(opt);
      }
    } else if (key === "model_id") {
      // 카탈로그 검색 위젯
      const wrap = document.createElement("div");
      wrap.className = "catalog-search-wrap";

      input = document.createElement("input");
      input.type = "text";
      input.placeholder = "제조사 또는 모델명 검색";
      const currentDisplay = [_selectedAsset.vendor, _selectedAsset.model].filter(Boolean).join(" ");
      input.value = currentDisplay;
      input.autocomplete = "off";
      wrap.appendChild(input);

      const hiddenId = document.createElement("input");
      hiddenId.type = "hidden";
      hiddenId.value = _selectedAsset.model_id || "";
      hiddenId.dataset.field = "model_id";
      wrap.appendChild(hiddenId);

      const dd = document.createElement("div");
      dd.className = "catalog-dropdown is-hidden";
      wrap.appendChild(dd);

      let searchTimer = null;
      input.addEventListener("input", () => {
        const q = input.value.trim();
        if (!q) { dd.classList.add("is-hidden"); return; }
        clearTimeout(searchTimer);
        searchTimer = setTimeout(async () => {
          try {
            const items = await apiFetch("/api/v1/product-catalog?q=" + encodeURIComponent(q));
            dd.textContent = "";
            items.forEach((item) => {
              const div = document.createElement("div");
              const itemLabel = ((item.vendor || "") + " " + (item.name || "")).trim();
              const kindLabel = CATALOG_KIND_LABELS[item.product_type] || item.product_type || "미지정";
              div.textContent = "[" + kindLabel + "] " + itemLabel;
              if (!buildCatalogClassificationPath(item)) {
                div.className = "catalog-dropdown-item disabled";
                const warn = document.createElement("span");
                warn.textContent = " (분류 미설정)";
                warn.className = "catalog-warning-note";
                div.appendChild(warn);
              } else {
                div.className = "catalog-dropdown-item" + (item.is_placeholder ? " placeholder" : "");
                div.addEventListener("click", () => {
                  hiddenId.value = item.id;
                  input.value = itemLabel;
                  dd.classList.add("is-hidden");
                });
              }
              dd.appendChild(div);
            });
            const addDiv = document.createElement("div");
            addDiv.className = "catalog-dropdown-add";
            addDiv.textContent = "+ 새 제품 등록";
            addDiv.addEventListener("click", () => { dd.classList.add("is-hidden"); openInlineCatalogForm(); });
            dd.appendChild(addDiv);
            dd.classList.remove("is-hidden");
          } catch (e) { showToast(e.message, "error"); }
        }, 300);
      });

      fieldWrap.appendChild(wrap);
      container.appendChild(fieldWrap);
      continue;
    } else if (key === "center_id") {
      input = document.createElement("select");
      const centers = await loadLayoutCenters(_selectedAsset.partner_id);
      fillSelectOptions(
        input,
        centers,
        "id",
        (center) => `${center.center_code} · ${center.center_name}`,
        "-- 선택 안함 --",
        currentVal,
      );
    } else if (key === "room_id") {
      input = document.createElement("select");
      const centerId = _selectedAsset.center_id;
      const rooms = centerId ? await loadLayoutRooms(centerId) : [];
      fillSelectOptions(
        input,
        rooms,
        "id",
        (room) => `${room.room_code} · ${room.room_name}`,
        centerId ? "-- 선택 안함 --" : "-- 센터 선택 --",
        currentVal,
        !centerId,
      );
      input.dataset.parentField = "center_id";
    } else if (key === "rack_id") {
      input = document.createElement("select");
      const roomId = _selectedAsset.room_id;
      const racks = roomId ? await loadLayoutRacks(roomId) : [];
      fillSelectOptions(
        input,
        racks,
        "id",
        (rack) => `${rack.rack_code}${rack.rack_name ? " · " + rack.rack_name : ""}`,
        roomId ? "-- 선택 안함 --" : "-- 전산실 선택 --",
        currentVal,
        !roomId,
      );
      input.dataset.parentField = "room_id";
    } else if (key === "status") {
      input = document.createElement("select");
      Object.entries(ASSET_STATUS_MAP).forEach(([val, lbl]) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent = lbl;
        if (val === currentVal) opt.selected = true;
        input.appendChild(opt);
      });
    } else if (key === "environment") {
      input = document.createElement("select");
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "—";
      input.appendChild(empty);
      Object.entries(ENV_MAP).forEach(([val, lbl]) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent = lbl;
        if (val === currentVal) opt.selected = true;
        input.appendChild(opt);
      });
    } else if (key === "note") {
      input = document.createElement("textarea");
      input.rows = 4;
      input.value = currentVal != null ? String(currentVal) : "";
    } else {
      input = document.createElement("input");
      input.type = NUMERIC_FIELDS.includes(key) ? "number" : "text";
      input.value = currentVal != null ? String(currentVal) : "";
    }

    input.dataset.field = key;
    input.className = "edit-input";
    if (key === "center_id") {
      input.addEventListener("change", async () => {
        const roomSelect = container.querySelector('[data-field="room_id"]');
        const rackSelect = container.querySelector('[data-field="rack_id"]');
        const centerId = input.value ? Number(input.value) : null;
        const rooms = centerId ? await loadLayoutRooms(centerId) : [];
        fillSelectOptions(
          roomSelect,
          rooms,
          "id",
          (room) => `${room.room_code} · ${room.room_name}`,
          centerId ? "-- 선택 안함 --" : "-- 센터 선택 --",
          null,
          !centerId,
        );
        fillSelectOptions(
          rackSelect,
          [],
          "id",
          (rack) => rack.rack_code,
          centerId ? "-- 전산실 선택 --" : "-- 전산실 선택 --",
          null,
          true,
        );
      });
    }
    if (key === "room_id") {
      input.addEventListener("change", async () => {
        const rackSelect = container.querySelector('[data-field="rack_id"]');
        const roomId = input.value ? Number(input.value) : null;
        const racks = roomId ? await loadLayoutRacks(roomId) : [];
        fillSelectOptions(
          rackSelect,
          racks,
          "id",
          (rack) => `${rack.rack_code}${rack.rack_name ? " · " + rack.rack_name : ""}`,
          roomId ? "-- 선택 안함 --" : "-- 전산실 선택 --",
          null,
          !roomId,
        );
      });
    }
    fieldWrap.appendChild(input);
    container.appendChild(fieldWrap);
  }
}

async function openDetailEditModal(tab) {
  _editMode = true;
  const title = document.getElementById("asset-detail-edit-title");
  const desc = document.getElementById("asset-detail-edit-desc");
  const tabBtn = document.querySelector(`.detail-tabs .tab-btn[data-dtab="${tab}"]`);
  title.textContent = `${tabBtn ? tabBtn.textContent.trim() : "자산"} 수정`;
  desc.textContent = "현재 탭의 자산 정보를 수정합니다.";
  await buildDetailEditFields(tab);
  document.getElementById("modal-asset-detail-edit").showModal();
}

function closeDetailEditModal() {
  _editMode = false;
  document.getElementById("modal-asset-detail-edit").close();
}

async function saveDetailEdit(tab) {
  const form = document.getElementById("form-asset-detail-edit");
  if (!form) return;
  const fields = DETAIL_EDIT_FIELDS[tab];
  const changes = {};
  fields.forEach(([label, key]) => {
    const input = form.querySelector('[data-field="' + key + '"]');
    if (!input) return;
    const val = input.value.trim();
    const original = _selectedAsset[key];
    if (key === "period_id") {
      const parsed = val === "" ? null : Number(val);
      if (parsed !== original) changes[key] = parsed;
    } else if (key === "model_id") {
      const parsed = val === "" ? null : Number(val);
      const original = _selectedAsset.model_id;
      if (parsed !== original && parsed !== null) changes.model_id = parsed;
    } else if (["center_id", "room_id", "rack_id"].includes(key)) {
      const parsed = val === "" ? null : Number(val);
      if (parsed !== original) changes[key] = parsed;
    } else if (NUMERIC_FIELDS.includes(key)) {
      const numVal = val === "" ? null : Number(val);
      if (numVal !== original) changes[key] = numVal;
    } else {
      const strVal = val || null;
      if (strVal !== original) changes[key] = strVal;
    }
  });
  if (Object.keys(changes).length === 0) {
    closeDetailEditModal();
    return;
  }
  try {
    const updated = await apiFetch("/api/v1/assets/" + _selectedAsset.id, { method: "PATCH", body: changes });
    Object.assign(_selectedAsset, updated);
    showToast("수정되었습니다.");
    closeDetailEditModal();
    renderDetailTab(tab);
    await loadAssets();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function closeDetail({ clearSelection = true } = {}) {
  syncAssetLayoutState(false);
  if (clearSelection && gridApi) gridApi.deselectAll();
  if (clearSelection) _selectedAsset = null;
  _detailEscArmedAt = 0;
  syncAssetRoleActionButtons();
}

function syncAssetRoleActionButtons() {
  const hasRole = !!_selectedAsset?.current_role_id;
  ["btn-asset-replacement", "btn-asset-failover", "btn-asset-repurpose"].forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    btn.disabled = !_selectedAsset || !hasRole;
  });
}

/* ── Modal (간소화 등록) ── */
const modal = document.getElementById("modal-asset");
let _catalogCombobox = null;
let _catalogItemsCache = [];

function getCatalogCombobox() {
  if (!_catalogCombobox) {
    _catalogCombobox = new ModalCombobox({
      inputId: "catalog-search",
      hiddenId: "catalog-id",
      dropdownId: "catalog-dropdown",
      maxDisplay: 50,
      onSelect: (item) => {
        const full = _catalogItemsCache.find((p) => String(p.id) === String(item.value));
        if (full) selectCatalogItem(full);
      },
      footerAction: {
        label: "+ 새 제품 등록",
        onClick: () => openInlineCatalogForm(),
      },
    });
    _catalogCombobox.bind();
  }
  return _catalogCombobox;
}

async function loadCatalogListForModal(productType = "") {
  try {
    let url = "/api/v1/product-catalog";
    if (productType) url += "?product_type=" + encodeURIComponent(productType);
    const items = await apiFetch(url);
    _catalogItemsCache = items;
    const combo = getCatalogCombobox();
    combo.setItems(
      items
        .filter((item) => buildCatalogClassificationPath(item) && buildCatalogClassificationPath(item) !== "분류 미지정")
        .map((item) => {
          const kindLabel = CATALOG_KIND_LABELS[item.product_type] || item.product_type || "";
          const vendorModel = ((item.vendor || "") + " " + (item.name || "")).trim();
          return {
            value: String(item.id),
            label: `[${kindLabel}] ${vendorModel}`,
            hint: buildCatalogClassificationPath(item),
            aliases: [item.vendor || "", item.name || ""],
          };
        })
    );
  } catch (e) {
    showToast("카탈로그 목록을 불러올 수 없습니다: " + e.message, "error");
  }
}

function updateAssetSaveState() {
  const btn = document.getElementById("btn-save-asset");
  if (!btn) return;
  const catalogId = document.getElementById("catalog-id").value;
  const assetName = document.getElementById("asset-name").value.trim();
  const ready = !!catalogId && !!assetName;
  btn.disabled = !ready;
}

function updateAssetNameHint(text) {
  const hint = document.getElementById("asset-name-hint");
  if (!hint) return;
  hint.textContent = text;
}

function updateAssetHostnameHint(text) {
  const hint = document.getElementById("asset-hostname-hint");
  if (!hint) return;
  hint.textContent = text;
}

function updateAssetRoleSuggestionHint(text) {
  const hint = document.getElementById("asset-role-suggestion-hint");
  if (!hint) return;
  hint.textContent = text;
}

function normalizeRoleNameCandidate(name) {
  let normalized = (name || "").trim();
  if (!normalized) return "";

  normalized = normalized
    .replace(/\s*\((old|new|temp|tmp|spare|backup|legacy|임시|예비|교체|대체)\)\s*$/i, "")
    .replace(/[-_\s]+(old|new|temp|tmp|spare|backup|legacy)$/i, "")
    .replace(/\s{2,}/g, " ")
    .trim();

  return normalized;
}

function syncRoleNameSuggestion() {
  const assetName = document.getElementById("asset-name").value.trim();
  const suggestion = normalizeRoleNameCandidate(assetName);
  if (!assetName) {
    updateAssetRoleSuggestionHint("역할명 추천은 자산명 기준으로 참고용 제안만 제공합니다. 자동 선택되지 않습니다.");
    return;
  }
  if (!suggestion) {
    updateAssetRoleSuggestionHint("역할명 추천을 만들 수 없습니다. 필요하면 역할명을 직접 판단해 연결하세요.");
    return;
  }
  if (suggestion === assetName) {
    updateAssetRoleSuggestionHint(`역할명 추천: ${suggestion} (자산명과 동일, 자동 선택 안 함)`);
    return;
  }
  updateAssetRoleSuggestionHint(`역할명 추천: ${suggestion} (참고용 제안, 자동 선택 안 함)`);
}

function clearSelectedCatalog({ keepSearch = false } = {}) {
  const combo = getCatalogCombobox();
  if (keepSearch) {
    combo.setValue("", combo.getDisplayText());
  } else {
    combo.reset();
  }
  const summary = document.getElementById("catalog-summary");
  summary.classList.add("is-hidden");
  summary.textContent = "";
  summary.classList.remove("placeholder-style");
  document.getElementById("btn-clear-catalog").classList.add("is-hidden");
  updateAssetNameHint("카탈로그를 선택하면 자산명이 자동 제안됩니다.");
  updateAssetHostnameHint("호스트명은 자산명 기준으로 자동 제안됩니다.");
  updateAssetRoleSuggestionHint("역할명 추천은 자산명 기준으로 참고용 제안만 제공합니다. 자동 선택되지 않습니다.");
  updateAssetSaveState();
}

function suggestAssetNameBase(item) {
  if (!item) return "";
  if (item.version) return `${item.name} ${item.version}`.trim();
  return (item.name || "").trim();
}

function suggestUniqueAssetName(baseName) {
  const base = (baseName || "").trim();
  if (!base) return "";
  const existing = new Set((_partnerAssetsCache || []).map((asset) => (asset.asset_name || "").trim().toLowerCase()));
  if (!existing.has(base.toLowerCase())) return base;
  for (let i = 2; i < 1000; i += 1) {
    const candidate = `${base}-${String(i).padStart(2, "0")}`;
    if (!existing.has(candidate.toLowerCase())) return candidate;
  }
  return `${base}-${Date.now()}`;
}

function suggestHostname(name) {
  const raw = (name || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  const projectCode = (document.getElementById("asset-project-code")?.value || "")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, "-")
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
  if (raw) {
    const hasAlphaPrefix = /^[a-z]/.test(raw);
    if (hasAlphaPrefix || !projectCode) return raw.slice(0, 63);
  }
  return projectCode ? projectCode.slice(0, 63) : "";
}

function syncHostnameFromAssetName() {
  const assetName = document.getElementById("asset-name").value.trim();
  const hostnameInput = document.getElementById("asset-hostname");
  if (!hostnameInput || _assetHostnameTouched) return;
  const suggested = suggestHostname(assetName);
  hostnameInput.value = suggested;
  updateAssetHostnameHint(
    suggested
      ? `자산명 기준으로 호스트명을 제안했습니다: ${suggested}`
      : "호스트명은 자산명 기준으로 자동 제안됩니다."
  );
  syncRoleNameSuggestion();
}

async function openCreateModal() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }

  // Reset form
  document.getElementById("form-asset").reset();
  _assetNameTouched = false;
  _assetHostnameTouched = false;
  clearSelectedCatalog();
  document.getElementById("catalog-kind-filter-modal").value = "hardware";
  document.getElementById("inline-catalog-form").classList.add("is-hidden");
  document.getElementById("asset-project-code").value = "";
  document.getElementById("asset-customer-code").value = "";
  document.getElementById("asset-hostname").value = "";
  fillSelectOptions(document.getElementById("asset-center-id"), [], "id", (item) => item.id, "-- 선택 안함 --");
  fillSelectOptions(document.getElementById("asset-room-id"), [], "id", (item) => item.id, "-- 센터 선택 --", null, true);
  fillSelectOptions(document.getElementById("asset-rack-id"), [], "id", (item) => item.id, "-- 전산실 선택 --", null, true);
  updateAssetRoleSuggestionHint("역할명 추천은 자산명 기준으로 참고용 제안만 제공합니다. 자동 선택되지 않습니다.");
  updateAssetClassificationPreview("");

  // 귀속사업 드롭다운 채우기
  const periodSel = document.getElementById("asset-period");
  periodSel.textContent = "";
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "-- 선택 안함 --";
  periodSel.appendChild(emptyOpt);

  try {
    const cid = getCtxPartnerId();
    await loadPartnerContacts(cid);
    const centers = await loadLayoutCenters(cid);
    fillSelectOptions(
      document.getElementById("asset-center-id"),
      centers,
      "id",
      (center) => `${center.center_code} · ${center.center_name}`,
      "-- 선택 안함 --",
    );
    const periods = await apiFetch("/api/v1/contract-periods?partner_id=" + cid);
    periods.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = [p.period_label, p.contract_name].filter(Boolean).join(" · ") || p.name || ("사업 #" + p.id);
      periodSel.appendChild(opt);
    });
    // topbar 프로젝트 선택 시 자동 선택
    const pid = getCtxProjectId();
    if (pid) periodSel.value = pid;
  } catch (_) { /* ignore */ }

  await loadCatalogListForModal("hardware");
  modal.showModal();
  updateAssetSaveState();
  document.getElementById("catalog-search").focus();
}

async function refreshAssetClassificationSelect(selectedId = null) {
  const currentCatalogId = Number(document.getElementById("catalog-id").value || 0);
  if (!currentCatalogId || !_catalogItemsCache?.length) {
    return;
  }
  const item = _catalogItemsCache.find((entry) => Number(entry.id) === currentCatalogId);
  updateAssetClassificationPreview(buildCatalogClassificationPath(item));
}

async function applyCatalogClassificationSuggestion(nodeCode) {
  return;
}


async function loadPartnerContacts(partnerId) {
  if (!partnerId) {
    _partnerContactsCache = [];
    return [];
  }
  const contacts = await apiFetch("/api/v1/partners/" + partnerId + "/contacts");
  _partnerContactsCache = contacts;
  return contacts;
}

async function populateContactSelect(selectedId) {
  const sel = document.getElementById("ct-contact-id");
  if (!sel) return;
  let contacts = _partnerContactsCache;
  if (!contacts.length && _selectedAsset?.partner_id) {
    contacts = await loadPartnerContacts(_selectedAsset.partner_id);
  }
  sel.textContent = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = contacts.length ? "-- 담당자 선택 --" : "(등록된 담당자 없음)";
  sel.appendChild(placeholder);
  contacts.forEach((contact) => {
    const opt = document.createElement("option");
    opt.value = contact.id;
    const parts = [contact.name];
    if (contact.department) parts.push(contact.department);
    if (contact.phone) parts.push(contact.phone);
    opt.textContent = parts.join(" / ");
    if (contact.id === selectedId) opt.selected = true;
    sel.appendChild(opt);
  });
}

/* ── 변경 이력 탭 ── */

async function renderHistoryTab(container) {
  _subTabHeader(container, "변경 이력", () => openEventModal());
  try {
    const data = await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/events");
    const summary = document.createElement("div");
    summary.className = "asset-history-summary";
    const rows = Array.isArray(data) ? data : [];
    const latest = rows[0] || null;
    const typeCounts = rows.reduce((acc, row) => {
      acc[row.event_type] = (acc[row.event_type] || 0) + 1;
      return acc;
    }, {});
    const topType = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0];
    summary.innerHTML = `
      <div class="asset-history-stat">
        <span class="asset-history-stat-label">전체 이력</span>
        <strong class="asset-history-stat-value">${rows.length}건</strong>
      </div>
      <div class="asset-history-stat">
        <span class="asset-history-stat-label">최근 변경</span>
        <strong class="asset-history-stat-value">${latest?.occurred_at ? formatDateTime(latest.occurred_at) : "—"}</strong>
      </div>
      <div class="asset-history-stat">
        <span class="asset-history-stat-label">주요 유형</span>
        <strong class="asset-history-stat-value">${topType ? `${ASSET_EVENT_LABELS[topType[0]] || topType[0]} ${topType[1]}건` : "—"}</strong>
      </div>
    `;
    container.appendChild(summary);

    if (!rows.length) {
      const empty = document.createElement("p");
      empty.className = "text-muted asset-subtable-empty";
      empty.textContent = "아직 기록된 변경 이력이 없습니다.";
      container.appendChild(empty);
      return;
    }

    const timeline = document.createElement("div");
    timeline.className = "asset-timeline";
    rows.forEach((row) => {
      const item = document.createElement("article");
      item.className = "asset-timeline-item";
      const typeLabel = ASSET_EVENT_LABELS[row.event_type] || row.event_type || "이력";
      const extraMeta = buildAssetEventMeta(row);
      item.innerHTML = `
        <div class="asset-timeline-marker asset-timeline-marker-${row.event_type || "note"}"></div>
        <div class="asset-timeline-main">
          <div class="asset-timeline-meta">
            <span class="badge">${typeLabel}</span>
            <span>${row.occurred_at ? formatDateTime(row.occurred_at) : "시각 미기재"}</span>
          </div>
          <div class="asset-timeline-title">${escapeHtml(row.summary || `${_selectedAsset.asset_name} ${typeLabel}`)}</div>
          ${extraMeta.length ? `<div class="asset-timeline-tags">${extraMeta.map((value) => `<span class="asset-timeline-tag">${escapeHtml(value)}</span>`).join("")}</div>` : ""}
          ${row.detail ? `<div class="asset-timeline-body">${escapeHtml(row.detail).replace(/\\n/g, "<br>")}</div>` : ""}
        </div>
      `;
      timeline.appendChild(item);
    });
    container.appendChild(timeline);
  } catch (e) { showToast(e.message, "error"); }
}

function openEventModal() {
  const modal = document.getElementById("modal-event");
  document.getElementById("form-event").reset();
  _eventSummaryTouched = false;
  _eventDetailTouched = false;
  document.getElementById("event-type").value = "note";
  document.getElementById("event-occurred-at").value = "";
  document.getElementById("event-related-asset-id").textContent = "";
  document.getElementById("event-related-partner-id").textContent = "";
  document.getElementById("event-summary").value = "";
  document.getElementById("event-detail").value = "";
  document.getElementById("event-from-use").value = "";
  document.getElementById("event-to-use").value = "";
  document.getElementById("event-old-id").value = "";
  document.getElementById("event-new-id").value = "";
  populateEventRelatedAssetSelect();
  populateEventRelatedPartnerSelect();
  updateEventTypeFields();
  applyEventTemplate({ forceSummary: true, forceDetail: true });
  modal.showModal();
}

function getSelectedEventRelatedAsset() {
  const selectedId = Number(document.getElementById("event-related-asset-id").value || 0);
  if (!selectedId) return null;
  return (_partnerAssetsCache || []).find((asset) => asset.id === selectedId) || null;
}

function getSelectedEventRelatedPartner() {
  const selectedId = Number(document.getElementById("event-related-partner-id").value || 0);
  if (!selectedId) return null;
  return (_allPartnersCache || []).find((partner) => partner.id === selectedId) || null;
}

function buildEventDetail(type, asset) {
  const relatedAsset = getSelectedEventRelatedAsset();
  const relatedPartner = getSelectedEventRelatedPartner();
  const fromUse = document.getElementById("event-from-use").value.trim();
  const toUse = document.getElementById("event-to-use").value.trim();
  const oldId = document.getElementById("event-old-id").value.trim();
  const newId = document.getElementById("event-new-id").value.trim();

  switch (type) {
    case "replacement":
      return relatedAsset
        ? `${asset.asset_name}를 ${relatedAsset.asset_name}(${relatedAsset.asset_code || "코드없음"}) 기준으로 교체했습니다.`
        : `${asset.asset_name}의 교체 작업을 기록합니다.\n교체 후 자산과 반영 일시를 남겨주세요.`;
    case "failover":
      return relatedAsset
        ? `${asset.asset_name} 장애로 ${relatedAsset.asset_name}(${relatedAsset.asset_code || "코드없음"})를 대체 투입했습니다.`
        : `${asset.asset_name} 장애로 대체 자산이 투입되었습니다.\n장애 원인과 대체 자산을 기록하세요.`;
    case "repurpose":
      if (fromUse || toUse) {
        return `용도 변경: ${fromUse || "기존 용도 미기재"} -> ${toUse || "신규 용도 미기재"}`;
      }
      return `${asset.asset_name}의 운영 목적이 변경되었습니다.\n기존 용도와 신규 용도를 기록하세요.`;
    case "maintenance_change":
      return relatedPartner
        ? `${asset.asset_name}의 유지보수/관련 업체가 ${relatedPartner.name}로 변경되었습니다.`
        : `${asset.asset_name}의 유지보수 업체 또는 관련 주체 변경을 기록합니다.`;
    case "serial_update":
      if (oldId || newId) {
        return `식별정보 변경: ${oldId || "이전값 미기재"} -> ${newId || "신규값 미기재"}`;
      }
      return `${asset.asset_name}의 시리얼 또는 식별정보가 변경되었습니다.\n이전 값과 현재 값을 함께 남겨주세요.`;
    default:
      return "";
  }
}

function buildEventSummary(type, asset) {
  const relatedAsset = getSelectedEventRelatedAsset();
  const relatedPartner = getSelectedEventRelatedPartner();
  const toUse = document.getElementById("event-to-use").value.trim();
  switch (type) {
    case "replacement":
      return relatedAsset ? `${asset.asset_name} -> ${relatedAsset.asset_name} 교체` : `${asset.asset_name} 교체`;
    case "failover":
      return relatedAsset ? `${asset.asset_name} 장애 대체 (${relatedAsset.asset_name})` : `${asset.asset_name} 장애 대체`;
    case "repurpose":
      return toUse ? `${asset.asset_name} 용도 전환 (${toUse})` : `${asset.asset_name} 용도 전환`;
    case "maintenance_change":
      return relatedPartner ? `${asset.asset_name} 관련업체 변경 (${relatedPartner.name})` : `${asset.asset_name} 유지보수 변경`;
    case "serial_update":
      return `${asset.asset_name} 식별정보 변경`;
    default:
      return (ASSET_EVENT_TEMPLATES[type] || ASSET_EVENT_TEMPLATES.note).summary(asset);
  }
}

function applyEventTemplate({ forceSummary = false, forceDetail = false } = {}) {
  const type = document.getElementById("event-type").value;
  const template = ASSET_EVENT_TEMPLATES[type] || ASSET_EVENT_TEMPLATES.note;
  const asset = _selectedAsset || { asset_name: "자산" };
  const summaryInput = document.getElementById("event-summary");
  const detailInput = document.getElementById("event-detail");
  const hint = document.getElementById("event-template-hint");
  const occurredAt = document.getElementById("event-occurred-at");
  if (hint) hint.textContent = template.hint;
  if ((forceSummary || !_eventSummaryTouched) && summaryInput) {
    summaryInput.value = buildEventSummary(type, asset);
  }
  if ((forceDetail || !_eventDetailTouched) && detailInput) {
    detailInput.value = buildEventDetail(type, asset) || template.detail(asset);
  }
  if (occurredAt && !occurredAt.value) {
    occurredAt.value = formatDateTimeLocalValue(new Date());
  }
}

function updateEventTypeFields() {
  const type = document.getElementById("event-type").value;
  const visible = new Set(EVENT_FIELD_VISIBILITY[type] || []);
  const map = {
    relatedAsset: "event-related-asset-wrap",
    relatedPartner: "event-related-partner-wrap",
    fromUse: "event-from-use-wrap",
    toUse: "event-to-use-wrap",
    oldId: "event-old-id-wrap",
    newId: "event-new-id-wrap",
  };
  Object.entries(map).forEach(([key, id]) => {
    document.getElementById(id).classList.toggle("is-hidden", !visible.has(key));
  });
}

async function saveEvent() {
  const summary = document.getElementById("event-summary").value.trim();
  if (!summary) { showToast("요약을 입력하세요.", "warning"); return; }
  const occurredAt = document.getElementById("event-occurred-at").value;
  const relatedAssetId = document.getElementById("event-related-asset-id").value;
  const payload = {
    event_type: document.getElementById("event-type").value,
    summary,
    detail: document.getElementById("event-detail").value.trim() || null,
    occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
    related_asset_id: relatedAssetId ? Number(relatedAssetId) : null,
  };
  try {
    await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/events", { method: "POST", body: payload });
    document.getElementById("modal-event").close();
    showToast("이력이 추가되었습니다.");
    renderDetailTab("history");
  } catch (e) { showToast(e.message, "error"); }
}

async function populateRelationAssetSelect() {
  const sel = document.getElementById("rel-dst-asset-id");
  if (!sel) return;
  let assets = (_partnerAssetsCache || []).filter((asset) => asset.id !== _selectedAsset?.id);
  if (!assets.length && _selectedAsset?.partner_id) {
    assets = await apiFetch("/api/v1/assets/inventory?partner_id=" + _selectedAsset.partner_id);
    _partnerAssetsCache = [_selectedAsset, ...assets.filter((asset) => asset.id !== _selectedAsset?.id)];
    assets = assets.filter((asset) => asset.id !== _selectedAsset?.id);
  }
  sel.textContent = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = assets.length ? "-- 대상 자산 선택 --" : "(선택 가능한 자산 없음)";
  sel.appendChild(placeholder);
  assets.forEach((asset) => {
    const opt = document.createElement("option");
    opt.value = asset.id;
    const parts = [asset.asset_name];
    if (asset.hostname) parts.push(asset.hostname);
    if (asset.asset_code) parts.push(asset.asset_code);
    opt.textContent = parts.join(" / ");
    sel.appendChild(opt);
  });
}

function selectCatalogItem(item) {
  document.getElementById("catalog-id").value = item.id;
  document.getElementById("catalog-search").value = ((item.vendor || "") + " " + (item.name || "")).trim();
  document.getElementById("btn-clear-catalog").classList.remove("is-hidden");

  // 요약 표시
  const summary = document.getElementById("catalog-summary");
  const kindLabel = CATALOG_KIND_LABELS[item.product_type] || item.product_type || "-";
  summary.textContent = "상위분류: " + kindLabel +
    " | 제조사: " + (item.vendor || "-") +
    " | 모델: " + (item.name || "-") +
    " | 분류경로: " + buildCatalogClassificationPath(item);
  summary.classList.remove("is-hidden");
  if (item.is_placeholder) {
    summary.classList.add("placeholder-style");
  } else {
    summary.classList.remove("placeholder-style");
  }
  const suggestedName = suggestUniqueAssetName(suggestAssetNameBase(item));
  const assetNameInput = document.getElementById("asset-name");
  if (suggestedName && (!_assetNameTouched || !assetNameInput.value.trim())) {
    assetNameInput.value = suggestedName;
    updateAssetNameHint(`카탈로그 기준 제안값을 넣었습니다: ${suggestedName}`);
  } else if (suggestedName) {
    updateAssetNameHint(`카탈로그 기준 제안값: ${suggestedName}`);
  }
  syncHostnameFromAssetName();
  syncRoleNameSuggestion();
  updateAssetClassificationPreview(buildCatalogClassificationPath(item));
  refreshAssetClassificationSelect().catch(() => {});
  updateAssetSaveState();
  assetNameInput.focus();
}


/* ── 인라인 카탈로그 등록 ── */

async function openInlineCatalogForm() {
  getCatalogCombobox()._close();
  const form = document.getElementById("inline-catalog-form");
  form.classList.remove("is-hidden");
  document.getElementById("inline-vendor").value = "";
  document.getElementById("inline-model").value = "";
  document.getElementById("inline-kind").value = document.getElementById("catalog-kind-filter-modal").value || "hardware";
  syncInlineCatalogAttributeInputs({
    imp_type: getInlineDefaultImpTypeForProductType(document.getElementById("inline-kind").value),
    product_family: "generic",
  });
}

function fillInlineCatalogSelect(elementId, options, selectedValue = "") {
  const select = document.getElementById(elementId);
  if (!select) return;
  const placeholder = select.querySelector("option[value='']")?.textContent || "-- 선택 --";
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = placeholder;
  select.appendChild(empty);
  options.forEach((option) => {
    const opt = document.createElement("option");
    opt.value = option.value;
    opt.textContent = option.label;
    select.appendChild(opt);
  });
  select.value = selectedValue || "";
}

function syncInlineCatalogAttributeInputs(values = {}) {
  fillInlineCatalogSelect("inline-attr-domain", INLINE_CATALOG_ATTRIBUTE_OPTIONS.domain, values.domain);
  fillInlineCatalogSelect("inline-attr-imp-type", INLINE_CATALOG_ATTRIBUTE_OPTIONS.imp_type, values.imp_type);
  fillInlineCatalogSelect("inline-attr-product-family", INLINE_CATALOG_ATTRIBUTE_OPTIONS.product_family, values.product_family);
  fillInlineCatalogSelect("inline-attr-platform", INLINE_CATALOG_ATTRIBUTE_OPTIONS.platform, values.platform);
}

function getInlineDefaultImpTypeForProductType(productType) {
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

function buildInlineCatalogAttributePayload(values) {
  const attrs = [
    { attribute_key: "domain", option_key: values.domain, raw_value: null },
    { attribute_key: "imp_type", option_key: values.imp_type, raw_value: null },
    { attribute_key: "product_family", option_key: values.product_family, raw_value: null },
  ];
  if (values.platform) {
    attrs.push({ attribute_key: "platform", option_key: values.platform, raw_value: null });
  }
  return attrs;
}

async function saveInlineCatalog() {
  const vendor = document.getElementById("inline-vendor").value.trim();
  const name = document.getElementById("inline-model").value.trim();
  const productType = document.getElementById("inline-kind").value;
  const attrValues = {
    domain: document.getElementById("inline-attr-domain").value,
    imp_type: document.getElementById("inline-attr-imp-type").value,
    product_family: document.getElementById("inline-attr-product-family").value,
    platform: document.getElementById("inline-attr-platform").value,
  };
  if (!vendor || !name || !productType || !attrValues.domain || !attrValues.imp_type || !attrValues.product_family) {
    showToast("모든 필수 항목을 입력하세요.", "warning");
    return;
  }
  try {
    const item = await apiFetch("/api/v1/product-catalog", {
      method: "POST",
      body: {
        vendor,
        name,
        product_type: productType,
        attributes: buildInlineCatalogAttributePayload(attrValues),
      },
    });
    document.getElementById("inline-catalog-form").classList.add("is-hidden");
    selectCatalogItem(item);
    showToast("제품이 등록되었습니다.");
  } catch (e) { showToast(e.message, "error"); }
}

/* ── 자산 저장 ── */

async function saveAsset() {
  const cid = getCtxPartnerId();
  if (!cid) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const catalogId = document.getElementById("catalog-id").value;
  if (!catalogId) { showToast("카탈로그 제품을 선택하세요.", "warning"); return; }
  const name = document.getElementById("asset-name").value.trim();
  if (!name) { showToast("자산명을 입력하세요.", "warning"); return; }
  const payload = {
    partner_id: cid,
    model_id: Number(catalogId),
    project_asset_number: document.getElementById("asset-project-code").value.trim() || null,
    customer_asset_number: document.getElementById("asset-customer-code").value.trim() || null,
    asset_name: name,
    hostname: document.getElementById("asset-hostname").value || null,
    period_id: document.getElementById("asset-period").value ? Number(document.getElementById("asset-period").value) : null,
    center_id: document.getElementById("asset-center-id").value ? Number(document.getElementById("asset-center-id").value) : null,
    room_id: document.getElementById("asset-room-id").value ? Number(document.getElementById("asset-room-id").value) : null,
    rack_id: document.getElementById("asset-rack-id").value ? Number(document.getElementById("asset-rack-id").value) : null,
  };
  try {
    const asset = await apiFetch("/api/v1/assets", { method: "POST", body: payload });
    modal.close();
    showToast("자산이 등록되었습니다.");
    await loadAssets();
    showAssetDetail(asset);
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteAssetAction() {
  if (!_selectedAsset) return;
  const asset = _selectedAsset;
  confirmDelete(
    '자산 "' + asset.asset_name + '"을(를) 삭제하시겠습니까?',
    async () => {
      try {
        await apiFetch("/api/v1/assets/" + asset.id, { method: "DELETE" });
        showToast("자산이 삭제되었습니다.");
        closeDetail();
        loadAssets();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

async function populateEventRelatedAssetSelect() {
  const sel = document.getElementById("event-related-asset-id");
  if (!sel) return;
  let assets = (_partnerAssetsCache || []).filter((asset) => asset.id !== _selectedAsset?.id);
  if (!assets.length && _selectedAsset?.partner_id) {
    assets = await apiFetch("/api/v1/assets/inventory?partner_id=" + _selectedAsset.partner_id);
    _partnerAssetsCache = [_selectedAsset, ...assets.filter((asset) => asset.id !== _selectedAsset?.id)];
    assets = assets.filter((asset) => asset.id !== _selectedAsset?.id);
  }
  sel.textContent = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = assets.length ? "-- 관련 자산 선택 --" : "(선택 가능한 자산 없음)";
  sel.appendChild(placeholder);
  assets.forEach((asset) => {
    const opt = document.createElement("option");
    opt.value = asset.id;
    opt.textContent = [asset.asset_name, asset.asset_code, asset.hostname].filter(Boolean).join(" / ");
    sel.appendChild(opt);
  });
}

async function populateEventRelatedPartnerSelect() {
  const sel = document.getElementById("event-related-partner-id");
  if (!sel) return;
  const partners = await loadPartners();
  sel.textContent = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = partners.length ? "-- 업체 선택 --" : "(선택 가능한 업체 없음)";
  sel.appendChild(placeholder);
  partners.forEach((partner) => {
    const opt = document.createElement("option");
    opt.value = partner.id;
    opt.textContent = [partner.name, partner.partner_type, partner.phone].filter(Boolean).join(" / ");
    sel.appendChild(opt);
  });
}

async function populateAssetRoleActionRoleSelect(selectedId) {
  const sel = document.getElementById("asset-role-action-role-id");
  if (!sel) return;
  const roles = await loadAssetRolesForPartner();
  sel.textContent = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = roles.length ? "-- 역할 선택 --" : "(선택 가능한 역할 없음)";
  sel.appendChild(placeholder);
  roles.forEach((role) => {
    const opt = document.createElement("option");
    opt.value = role.id;
    const parts = [role.role_name];
    if (role.role_type) parts.push(role.role_type);
    if (role.current_asset_name) parts.push(`현재 ${role.current_asset_name}`);
    opt.textContent = parts.join(" / ");
    if (role.id === selectedId) opt.selected = true;
    sel.appendChild(opt);
  });
}

async function populateAssetRoleActionAssetSelect() {
  const sel = document.getElementById("asset-role-action-asset-id");
  if (!sel) return;
  let assets = (_partnerAssetsCache || []).filter((asset) => asset.id !== _selectedAsset?.id);
  if (!assets.length && _selectedAsset?.partner_id) {
    assets = await apiFetch("/api/v1/assets/inventory?partner_id=" + _selectedAsset.partner_id);
    _partnerAssetsCache = [_selectedAsset, ...assets.filter((asset) => asset.id !== _selectedAsset?.id)];
    assets = assets.filter((asset) => asset.id !== _selectedAsset?.id);
  }
  sel.textContent = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = assets.length ? "-- 대상 자산 선택 --" : "(선택 가능한 자산 없음)";
  sel.appendChild(placeholder);
  assets.forEach((asset) => {
    const opt = document.createElement("option");
    opt.value = asset.id;
    opt.textContent = [asset.asset_name, asset.asset_code, asset.hostname].filter(Boolean).join(" / ");
    sel.appendChild(opt);
  });
}

async function populateAssetRoleActionPeriodSelect(selectedId) {
  const select = document.getElementById("asset-role-action-new-period-id");
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "-- 현재와 동일 --";
  select.appendChild(empty);
  if (!_selectedAsset?.partner_id) return;
  try {
    const periods = await apiFetch(`/api/v1/contract-periods?partner_id=${_selectedAsset.partner_id}`);
    periods.forEach((period) => {
      const opt = document.createElement("option");
      opt.value = period.id;
      opt.textContent = [period.period_label, period.contract_name].filter(Boolean).join(" · ") || `사업 #${period.id}`;
      if (period.id === selectedId) opt.selected = true;
      select.appendChild(opt);
    });
  } catch (_) {
    // ignore
  }
}

function toggleAssetRoleActionFields(actionType) {
  const showAsset = actionType === "replacement" || actionType === "failover";
  const showNewRole = actionType === "repurpose";
  document.getElementById("asset-role-action-asset-wrap").classList.toggle("is-hidden", !showAsset);
  document.getElementById("asset-role-action-new-role-name-wrap").classList.toggle("is-hidden", !showNewRole);
  document.getElementById("asset-role-action-new-role-type-wrap").classList.toggle("is-hidden", !showNewRole);
  document.getElementById("asset-role-action-new-period-wrap").classList.toggle("is-hidden", !showNewRole);
}

async function openAssetRoleActionModal(actionType) {
  if (!_selectedAsset?.current_role_id) {
    showToast("현재 연결된 역할이 없습니다.", "warning");
    return;
  }
  _currentAssetRoleAction = actionType;
  const titles = {
    replacement: ["교체", "현재 자산이 맡고 있는 역할을 다른 자산으로 교체합니다."],
    failover: ["장애대체", "현재 자산의 역할을 대체 자산으로 긴급 전환합니다."],
    repurpose: ["용도전환", "현재 자산을 다른 역할로 전환합니다."],
  };
  const [title, desc] = titles[actionType];
  document.getElementById("asset-role-action-title").textContent = title;
  document.getElementById("asset-role-action-desc").textContent = desc;
  document.getElementById("form-asset-role-action").reset();
  document.getElementById("asset-role-action-occurred-at").value = formatDateTimeLocalValue(new Date());
  await populateAssetRoleActionRoleSelect(_selectedAsset.current_role_id);
  await populateAssetRoleActionAssetSelect();
  await populateAssetRoleActionPeriodSelect(_selectedAsset.period_id || null);
  toggleAssetRoleActionFields(actionType);
  document.getElementById("modal-asset-role-action").showModal();
}

async function saveAssetRoleAction() {
  if (!_selectedAsset || !_currentAssetRoleAction) return;
  const roleId = document.getElementById("asset-role-action-role-id").value;
  if (!roleId) {
    showToast("역할을 선택하세요.", "warning");
    return;
  }
  const occurredAt = document.getElementById("asset-role-action-occurred-at").value;
  const note = document.getElementById("asset-role-action-note").value.trim() || null;
  let endpoint = "";
  let payload = {
    occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
    note,
  };

  if (_currentAssetRoleAction === "replacement" || _currentAssetRoleAction === "failover") {
    const replacementAssetId = document.getElementById("asset-role-action-asset-id").value;
    if (!replacementAssetId) {
      showToast("대상 자산을 선택하세요.", "warning");
      return;
    }
    payload.replacement_asset_id = Number(replacementAssetId);
    endpoint = `/api/v1/asset-roles/${roleId}/actions/${_currentAssetRoleAction}`;
  } else if (_currentAssetRoleAction === "repurpose") {
    const newRoleName = document.getElementById("asset-role-action-new-role-name").value.trim();
    if (!newRoleName) {
      showToast("신규 역할명을 입력하세요.", "warning");
      return;
    }
    payload.new_role_name = newRoleName;
    payload.new_role_type = document.getElementById("asset-role-action-new-role-type").value.trim() || null;
    payload.new_contract_period_id = document.getElementById("asset-role-action-new-period-id").value
      ? Number(document.getElementById("asset-role-action-new-period-id").value)
      : null;
    endpoint = `/api/v1/asset-roles/${roleId}/actions/repurpose`;
  }

  try {
    const result = await apiFetch(endpoint, { method: "POST", body: payload });
    document.getElementById("modal-asset-role-action").close();
    showToast(result.message || "처리되었습니다.");
    await loadAssets();
    const rows = [];
    gridApi.forEachNode((node) => rows.push(node.data));
    const refreshed = rows.find((item) => item.id === _selectedAsset.id);
    if (refreshed) {
      _selectedAsset = refreshed;
      showAssetDetail(refreshed);
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", async () => {
  initAssetSplitter();
  initGrid();
});
document.getElementById("btn-add-asset").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-asset").addEventListener("click", () => modal.close());
document.getElementById("btn-save-asset").addEventListener("click", saveAsset);
document.getElementById("btn-clear-catalog").addEventListener("click", () => {
  clearSelectedCatalog();
  document.getElementById("catalog-search").focus();
});
document.getElementById("btn-edit-asset").addEventListener("click", async () => {
  if (!_selectedAsset) return;
  const editableTabs = ["overview", "operations"];
  if (!editableTabs.includes(_currentTab)) {
    showToast("이 탭은 개별 항목을 추가/수정하세요.", "info");
    return;
  }
  if (_editMode) { closeDetailEditModal(); return; }
  await openDetailEditModal(_currentTab);
});
document.getElementById("btn-asset-replacement").addEventListener("click", () => openAssetRoleActionModal("replacement"));
document.getElementById("btn-asset-failover").addEventListener("click", () => openAssetRoleActionModal("failover"));
document.getElementById("btn-asset-repurpose").addEventListener("click", () => openAssetRoleActionModal("repurpose"));
document.getElementById("btn-delete-asset").addEventListener("click", deleteAssetAction);

document.getElementById("catalog-kind-filter-modal").addEventListener("change", () => {
  clearSelectedCatalog({ keepSearch: true });
  const kind = document.getElementById("catalog-kind-filter-modal").value;
  loadCatalogListForModal(kind);
});
document.getElementById("asset-name").addEventListener("input", () => {
  _assetNameTouched = true;
  syncHostnameFromAssetName();
  updateAssetSaveState();
  syncRoleNameSuggestion();
});
document.getElementById("asset-project-code").addEventListener("input", () => {
  syncHostnameFromAssetName();
});
document.getElementById("asset-hostname").addEventListener("input", () => {
  _assetHostnameTouched = true;
  updateAssetSaveState();
});
document.getElementById("asset-period").addEventListener("change", async () => {
  updateAssetSaveState();
  await refreshAssetClassificationSelect();
});
document.getElementById("btn-open-classification-schemes").addEventListener("click", () => {
  window.location.href = getClassificationManagementUrl();
});
document.getElementById("asset-center-id").addEventListener("change", async (event) => {
  const centerId = event.target.value ? Number(event.target.value) : null;
  const rooms = centerId ? await loadLayoutRooms(centerId) : [];
  fillSelectOptions(
    document.getElementById("asset-room-id"),
    rooms,
    "id",
    (room) => `${room.room_code} · ${room.room_name}`,
    centerId ? "-- 선택 안함 --" : "-- 센터 선택 --",
    null,
    !centerId,
  );
  fillSelectOptions(
    document.getElementById("asset-rack-id"),
    [],
    "id",
    (rack) => rack.rack_code,
    "-- 전산실 선택 --",
    null,
    true,
  );
});
document.getElementById("asset-room-id").addEventListener("change", async (event) => {
  const roomId = event.target.value ? Number(event.target.value) : null;
  const racks = roomId ? await loadLayoutRacks(roomId) : [];
  fillSelectOptions(
    document.getElementById("asset-rack-id"),
    racks,
    "id",
    (rack) => `${rack.rack_code}${rack.rack_name ? " · " + rack.rack_name : ""}`,
    roomId ? "-- 선택 안함 --" : "-- 전산실 선택 --",
    null,
    !roomId,
  );
});

// 인라인 카탈로그 등록
document.getElementById("btn-inline-save").addEventListener("click", saveInlineCatalog);
document.getElementById("inline-kind").addEventListener("change", (event) => {
  const impTypeSelect = document.getElementById("inline-attr-imp-type");
  if (impTypeSelect && !impTypeSelect.value) {
    impTypeSelect.value = getInlineDefaultImpTypeForProductType(event.target.value);
  }
});
document.getElementById("btn-inline-cancel").addEventListener("click", () => {
  document.getElementById("inline-catalog-form").classList.add("is-hidden");
});
document.getElementById("btn-minimize-detail").addEventListener("click", toggleDetailPanel);

// Detail tab switching
document.querySelectorAll(".detail-tabs .tab-btn").forEach(btn => {
  btn.addEventListener("click", () => renderDetailTab(btn.dataset.dtab));
});

// Sub-entity modal events
document.getElementById("btn-cancel-sw").addEventListener("click", () => document.getElementById("modal-software").close());
document.getElementById("btn-save-sw").addEventListener("click", saveSoftware);
document.getElementById("btn-cancel-ip").addEventListener("click", () => document.getElementById("modal-ip").close());
document.getElementById("btn-save-ip").addEventListener("click", saveIp);
document.getElementById("btn-cancel-ct").addEventListener("click", () => document.getElementById("modal-contact").close());
document.getElementById("btn-save-ct").addEventListener("click", saveContact);
document.getElementById("btn-cancel-rp").addEventListener("click", () => document.getElementById("modal-related-partner").close());
document.getElementById("btn-save-rp").addEventListener("click", saveRelatedPartner);
document.getElementById("btn-cancel-rel").addEventListener("click", () => document.getElementById("modal-relation").close());
document.getElementById("btn-save-rel").addEventListener("click", saveRelation);
document.getElementById("btn-cancel-alias").addEventListener("click", () => document.getElementById("modal-alias").close());
document.getElementById("btn-save-alias").addEventListener("click", saveAlias);
document.getElementById("btn-cancel-event").addEventListener("click", () => document.getElementById("modal-event").close());
document.getElementById("btn-save-event").addEventListener("click", saveEvent);
document.getElementById("btn-cancel-asset-detail-edit").addEventListener("click", closeDetailEditModal);
document.getElementById("btn-save-asset-detail-edit").addEventListener("click", () => saveDetailEdit(_currentTab));
document.getElementById("btn-cancel-asset-role-action").addEventListener("click", () => document.getElementById("modal-asset-role-action").close());
document.getElementById("btn-save-asset-role-action").addEventListener("click", saveAssetRoleAction);
document.getElementById("ct-role-preset").addEventListener("change", syncContactRoleInput);
document.getElementById("rel-type").addEventListener("change", updateRelationTypeHint);
document.getElementById("event-type").addEventListener("change", () => applyEventTemplate());
document.getElementById("event-summary").addEventListener("input", () => { _eventSummaryTouched = true; });
document.getElementById("event-detail").addEventListener("input", () => { _eventDetailTouched = true; });
document.getElementById("event-type").addEventListener("change", updateEventTypeFields);
document.getElementById("event-related-asset-id").addEventListener("change", () => applyEventTemplate());
document.getElementById("event-related-partner-id").addEventListener("change", () => applyEventTemplate());
document.getElementById("event-from-use").addEventListener("input", () => applyEventTemplate());
document.getElementById("event-to-use").addEventListener("input", () => applyEventTemplate());
document.getElementById("event-old-id").addEventListener("input", () => applyEventTemplate());
document.getElementById("event-new-id").addEventListener("input", () => applyEventTemplate());

// Search & filter
document.getElementById("filter-status").addEventListener("change", loadAssets);
initTextFilter("filter-search", loadAssets);

// Global project filter checkbox
initProjectFilterCheckbox(loadAssets);

// Context selector change
window.addEventListener("ctx-changed", () => {
  closeDetail({ clearSelection: true });
  loadGridRoleOptions();
  loadClassificationLevelAliases();
  loadAssets();
});
window.addEventListener("resize", () => {
  fitGridColumnsIfNeeded();
});
document.addEventListener("keydown", handleAssetDetailEscape);
