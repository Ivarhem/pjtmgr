/* ── 케이블 배선도 (Port Maps, 고객사 중심) ── */

const PORTMAP_STATUS_MAP = {
  active: "active", planned: "planned", temporary: "temporary", retired: "retired", candidate: "candidate",
  required: "필요", open: "오픈", closed: "차단", pending: "대기",
};
const PORTMAP_PRESET_DEFAULTS = {
  "direct-copper": {
    status: "active",
    connection_type: "direct",
    cable_type: "UTP",
    media_category: "copper",
    src_connector_type: "RJ45",
    dst_connector_type: "RJ45",
    cable_speed: "1G",
    duplex: "auto",
  },
  "breakout-fiber": {
    status: "active",
    connection_type: "breakout",
    cable_type: "SM",
    media_category: "fiber",
    src_connector_type: "LC",
    dst_connector_type: "LC",
    cable_speed: "40G",
    duplex: "full",
  },
};

const PORTMAP_MEDIA_TYPE_OPTIONS = {
  copper: ["RJ45", "UTP", "STP", "other"],
  fiber: ["LC", "SC", "ST", "MPO/MTP", "other"],
  dac: ["DAC", "AOC", "other"],
  other: ["other"],
};

/* ── Asset / Interface Cache ── */
let _pmAssets = [];
let _pmIfaceCache = {};  // { asset_id: [interfaces] }
const _pmNextIfaceSuggestions = {}; // { "side:assetId": nextName }

async function _loadPmAssets() {
  const cid = getCtxPartnerId();
  if (!cid) { _pmAssets = []; return; }
  try {
    _pmAssets = await apiFetch("/api/v1/assets?partner_id=" + cid);
  } catch (err) {
    _pmAssets = [];
    showToast("자산 목록 로딩 실패: " + err.message, "error");
  }
}

async function _loadPmInterfaces(assetId) {
  if (!assetId) return [];
  if (_pmIfaceCache[assetId]) return _pmIfaceCache[assetId];
  try {
    const data = await apiFetch("/api/v1/assets/" + assetId + "/interfaces");
    _pmIfaceCache[assetId] = data;
    return data;
  } catch (err) {
    return [];
  }
}

/* ── AssetCellEditor (createComboBoxCellEditor 사용) ── */
const AssetCellEditor = createComboBoxCellEditor({
  getItems: () => _pmAssets.map(a => ({
    id: a.id,
    label: a.asset_name || "",
    sub: a.hostname || "",
  })),
  getDisplayValue: (item) => item.label,
  onSelect: (item, params) => {
    const side = params.colDef.field.startsWith("src_") ? "src" : "dst";
    params.data[side + "_asset_id"] = item.id;
  },
});

/* ── InterfaceCellEditor (createComboBoxCellEditor 사용, async getItems) ── */
const InterfaceCellEditor = createComboBoxCellEditor({
  getItems: async (params) => {
    const side = params.colDef.field.startsWith("src_") ? "src" : "dst";
    const assetId = params.data[side + "_asset_id"];
    if (!assetId) return [];
    const ifaces = await _loadPmInterfaces(assetId);
    return ifaces.map(i => ({
      id: i.id,
      label: i.name || "(이름 없음)",
      sub: i.if_type ? (i.if_type + (i.speed ? ", " + i.speed : "")) : "",
    }));
  },
  getDisplayValue: (item) => item.label,
  onSelect: (item, params) => {
    const side = params.colDef.field.startsWith("src_") ? "src" : "dst";
    params.data[side + "_interface_id"] = item.id;
  },
});

function renderAssetNameCell(params) {
  const side = params.colDef.field.startsWith("src_") ? "src" : "dst";
  const wrap = document.createElement("div");
  wrap.className = "flex-col-gap-sm";
  const name = document.createElement("span");
  name.textContent = params.value || "";
  wrap.appendChild(name);
  if (params.value && params.data && params.data[`${side}_is_registered`] === false) {
    const badge = document.createElement("span");
    badge.className = "badge badge-pending";
    badge.textContent = "미등록";
    wrap.appendChild(badge);
  }
  return wrap;
}

function renderInterfaceNameCell(params) {
  const side = params.colDef.field.startsWith("src_") ? "src" : "dst";
  const wrap = document.createElement("div");
  wrap.className = "flex-col-gap-sm";
  const name = document.createElement("span");
  name.textContent = params.value || "";
  wrap.appendChild(name);
  if (params.value && params.data && !params.data[`${side}_interface_id`]) {
    const badge = document.createElement("span");
    badge.className = "badge badge-pending";
    badge.textContent = "미등록IF";
    wrap.appendChild(badge);
  }
  return wrap;
}

function suggestNextInterfaceName(side, assetId, currentName) {
  if (!assetId) return null;
  const key = `${side}:${assetId}`;
  const cached = _pmNextIfaceSuggestions[key];
  if (cached) {
    _pmNextIfaceSuggestions[key] = incrementInterfaceName(cached) || cached;
    return cached;
  }
  const asset = _pmIfaceCache[assetId] || [];
  const names = asset.map((i) => i.name).filter(Boolean);
  if (currentName) names.push(currentName);
  const candidate = names.sort().at(-1);
  const next = incrementInterfaceName(candidate || "eth0");
  if (!next) return null;
  _pmNextIfaceSuggestions[key] = incrementInterfaceName(next) || next;
  return next;
}

function incrementInterfaceName(name) {
  if (!name) return null;
  const match = String(name).match(/^(.*?)(\d+)([^\d]*)$/);
  if (!match) return null;
  const [, prefix, digits, suffix] = match;
  const nextNum = String(Number(digits) + 1).padStart(digits.length, "0");
  return `${prefix}${nextNum}${suffix}`;
}

/* ── Column Definitions ── */
const columnDefs = [
  { field: "seq", headerName: "순번", width: 70 },
  { field: "src_asset_name", headerName: "출발 자산", width: 150, editable: true, cellEditor: AssetCellEditor, cellRenderer: renderAssetNameCell },
  { field: "src_interface_name", headerName: "출발 IF", width: 120, editable: true, cellEditor: InterfaceCellEditor, cellRenderer: renderInterfaceNameCell },
  { field: "src_hostname", headerName: "출발 호스트", width: 120 },
  { field: "dst_asset_name", headerName: "도착 자산", width: 150, editable: true, cellEditor: AssetCellEditor, cellRenderer: renderAssetNameCell },
  { field: "dst_interface_name", headerName: "도착 IF", width: 120, editable: true, cellEditor: InterfaceCellEditor, cellRenderer: renderInterfaceNameCell },
  { field: "dst_hostname", headerName: "도착 호스트", width: 120 },
  {
    field: "connection_type", headerName: "연결유형", width: 100, editable: true,
    cellEditor: "agSelectCellEditor", cellEditorParams: { values: ["physical", "logical"] },
  },
  { field: "cable_no", headerName: "케이블번호", width: 110, editable: true },
  {
    field: "cable_type", headerName: "케이블종류", width: 100, editable: true,
    cellEditor: "agSelectCellEditor", cellEditorParams: { values: ["SM", "MM", "UTP", "STP", "DAC", "other"] },
  },
  {
    field: "media_category", headerName: "매체", width: 90, editable: true,
    cellEditor: "agSelectCellEditor", cellEditorParams: { values: ["copper", "fiber", "dac", "other"] },
  },
  { field: "src_connector_type", headerName: "출발타입", width: 100, editable: true },
  { field: "dst_connector_type", headerName: "도착타입", width: 100, editable: true },
  {
    field: "cable_speed", headerName: "속도", width: 80, editable: true,
    cellEditor: "agSelectCellEditor", cellEditorParams: { values: ["100M", "1G", "10G", "25G", "40G", "100G", "other"] },
  },
  {
    field: "duplex", headerName: "Duplex", width: 90, editable: true,
    cellEditor: "agSelectCellEditor", cellEditorParams: { values: ["full", "half", "auto"] },
  },
  { field: "purpose", headerName: "용도", flex: 1, minWidth: 120, editable: true },
  {
    field: "status", headerName: "상태", width: 80, editable: true,
    cellEditor: "agSelectCellEditor", cellEditorParams: { values: ["required", "open", "closed", "pending"] },
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = PORTMAP_STATUS_MAP[params.value] || params.value;
      return span;
    },
  },
  {
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm infra-inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary"; btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditModal(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger"; btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deletePortMap(params.data));
      wrap.appendChild(btnEdit); wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

const EDITABLE_FIELDS = [
  "src_asset_name", "src_interface_name",
  "dst_asset_name", "dst_interface_name",
  "connection_type", "cable_no", "cable_type", "media_category", "src_connector_type", "dst_connector_type", "cable_speed", "duplex", "purpose", "status",
];

const PORTMAP_GRID_COLUMN_STATE_KEY = "infra.portmaps.gridColumnState";
const DEFAULT_PORTMAP_COLUMN_STATE = [
  { colId: "seq", width: 94, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "cable_no", width: 132, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "status", width: 80, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "connection_type", width: 120, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "cable_type", width: 132, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "cable_speed", width: 80, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "duplex", width: 130, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "media_category", width: 90, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "src_connector_type", width: 100, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "src_asset_name", width: 130, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "src_interface_name", width: 110, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "src_hostname", width: 120, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "dst_connector_type", width: 100, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "dst_asset_name", width: 130, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "dst_interface_name", width: 109, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "dst_hostname", width: 136, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
  { colId: "purpose", width: 120, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: 1 },
  { colId: "0", width: 51, hide: false, pinned: null, sort: null, sortIndex: null, aggFunc: null, rowGroup: false, rowGroupIndex: null, pivot: false, pivotIndex: null, flex: null },
];

function savePortMapColumnState() {
  if (!gridApi?.getColumnState) return;
  const state = gridApi.getColumnState();
  if (!Array.isArray(state) || !state.length) return;
  localStorage.setItem(PORTMAP_GRID_COLUMN_STATE_KEY, JSON.stringify(state));
}

function restorePortMapColumnState() {
  if (!gridApi?.applyColumnState) return false;
  const raw = localStorage.getItem(PORTMAP_GRID_COLUMN_STATE_KEY);
  if (raw) {
    try {
      return !!gridApi.applyColumnState({ state: JSON.parse(raw), applyOrder: true });
    } catch {
      localStorage.removeItem(PORTMAP_GRID_COLUMN_STATE_KEY);
    }
  }
  return !!gridApi.applyColumnState({ state: DEFAULT_PORTMAP_COLUMN_STATE, applyOrder: true });
}

const EDIT_MODE_FIELDS = new Set([
  "connection_type", "cable_no", "cable_type", "media_category", "src_connector_type", "dst_connector_type", "cable_speed", "duplex", "purpose", "status",
]);

let gridApi;
let editMode;
let _hasNewRows = false;

function _getPortMapGridTotalRowCount() {
  let count = 0;
  gridApi?.forEachNode(() => { count += 1; });
  return count;
}

function _updatePortMapNewRowIndicators() {
  const saveBtn = document.getElementById("btn-save-new-portmaps");
  if (saveBtn) saveBtn.classList.toggle("is-hidden", !_hasNewRows);
}

function resolvePortMapAssetIdsBeforeSave(row) {
  ["src", "dst"].forEach((side) => {
    const assetName = (row[`${side}_asset_name`] || "").trim();
    if (!assetName || row[`${side}_asset_id`]) return;
    const asset = _pmAssets.find((a) => (a.asset_name || "").trim().toLowerCase() === assetName.toLowerCase());
    if (asset) {
      row[`${side}_asset_id`] = asset.id;
      row[`${side}_hostname`] = asset.hostname || "";
      row[`${side}_is_registered`] = true;
    }
  });
}

function addPortMapRow() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const newRow = {
    _isNew: true,
    id: null,
    partner_id: Number(getCtxPartnerId()),
    seq: null,
    src_asset_id: null,
    src_asset_name: "",
    src_interface_id: null,
    src_interface_name: "",
    src_hostname: "",
    dst_asset_id: null,
    dst_asset_name: "",
    dst_interface_id: null,
    dst_interface_name: "",
    dst_hostname: "",
    connection_type: "physical",
    cable_no: "",
    cable_type: "UTP",
    media_category: "copper",
    src_connector_type: "RJ45",
    dst_connector_type: "RJ45",
    cable_speed: "1G",
    duplex: "auto",
    purpose: "",
    status: "required",
  };
  const res = gridApi.applyTransaction({ add: [newRow], addIndex: _getPortMapGridTotalRowCount() });
  _hasNewRows = true;
  _updatePortMapNewRowIndicators();
  if (res.add && res.add.length) {
    gridApi.ensureNodeVisible(res.add[0], "bottom");
    setTimeout(() => gridApi.setFocusedCell(res.add[0].rowIndex, "src_asset_name"), 50);
  }
}

async function saveNewPortMaps() {
  const newRows = [];
  gridApi.forEachNode((n) => {
    if (n.data?._isNew) newRows.push(n);
  });
  if (!newRows.length) { showToast("저장할 새 배선이 없습니다.", "info"); return; }

  let successCount = 0;
  for (const node of newRows) {
    const d = node.data;
    resolvePortMapAssetIdsBeforeSave(d);
    try {
      const created = await apiFetch("/api/v1/port-maps", {
        method: "POST",
        body: {
          partner_id: d.partner_id || Number(getCtxPartnerId()),
          src_interface_id: d.src_interface_id || null,
          dst_interface_id: d.dst_interface_id || null,
          src_asset_name_raw: d.src_asset_name || null,
          src_interface_name_raw: d.src_interface_name || null,
          dst_asset_name_raw: d.dst_asset_name || null,
          dst_interface_name_raw: d.dst_interface_name || null,
          seq: d.seq != null && d.seq !== "" ? Number(d.seq) : null,
          connection_type: d.connection_type || "physical",
          cable_no: d.cable_no || null,
          cable_type: d.cable_type || "UTP",
          media_category: d.media_category || "copper",
          src_connector_type: d.src_connector_type || "RJ45",
          dst_connector_type: d.dst_connector_type || d.src_connector_type || "RJ45",
          cable_speed: d.cable_speed || "1G",
          duplex: d.duplex || "auto",
          purpose: d.purpose || null,
          status: d.status || "required",
        },
      });
      Object.assign(d, created);
      d._isNew = false;
      successCount++;
    } catch (e) {
      showToast((d.cable_no || d.purpose || "새 배선") + ": " + e.message, "error");
    }
  }
  gridApi.refreshCells({ force: true });
  _hasNewRows = false;
  gridApi.forEachNode((n) => { if (n.data?._isNew) _hasNewRows = true; });
  _updatePortMapNewRowIndicators();
  if (successCount) {
    showToast(successCount + "건 배선이 등록되었습니다.");
    loadPortMaps();
  }
}

/* ── Data Loading ── */

function _setPortMapsEmptyState(isEmpty) {
  const guide = document.getElementById("ctx-empty-portmaps");
  const content = document.getElementById("portmaps-content");
  if (guide) guide.classList.toggle("is-hidden", !isEmpty);
  if (content) content.classList.toggle("is-hidden", isEmpty);
}

async function loadPortMaps() {
  const cid = getCtxPartnerId();
  if (!cid) { gridApi.setGridOption("rowData", []); _setPortMapsEmptyState(true); return; }
  _setPortMapsEmptyState(false);

  // Load assets cache, clear interface cache
  await _loadPmAssets();
  _pmIfaceCache = {};

  let url = "/api/v1/port-maps?partner_id=" + cid;
  const pid = getCtxProjectId();
  if (pid && isProjectFilterActive()) url += "&period_id=" + pid;
  try {
    const data = await apiFetch(url);
    gridApi.setGridOption("rowData", data);
    const kw = document.getElementById("portmap-search")?.value?.trim() || "";
    if (kw) gridApi.setGridOption("quickFilterText", kw);
  } catch (err) { showToast(err.message, "error"); }
}

async function portmapSaveEditMode() {
  if (!editMode) return;
  const result = await editMode.save();
  if (result.success && result.count > 0) {
    showToast(`${result.count}건 포트맵이 업데이트되었습니다.`);
    editMode.toggle(false);
  } else if (result.success && result.count === 0) {
    showToast("변경사항이 없습니다.", "info");
    editMode.toggle(false);
  }
}

function portmapCancelEditMode() {
  if (!editMode) return;
  editMode.cancel();
  editMode.toggle(false);
}

function initGrid() {
  const gridEl = document.getElementById("grid-portmaps");
  gridApi = agGrid.createGrid(gridEl, {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "multiple", animateRows: true, enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: "modal-edit",
      onEdit: (data) => openEditModal(data),
    }),
    onCellValueChanged: handlePortMapCellChanged,
  });

  editMode = new GridEditMode({
    gridApi,
    editableFields: EDIT_MODE_FIELDS,
    bulkEndpoint: () => `/api/v1/port-maps/bulk?partner_id=${getCtxPartnerId()}`,
    prefix: "portmap",

    onAfterSave: (results) => {
      for (const updated of results) {
        let node = null;
        gridApi.forEachNode((n) => { if (n.data?.id === updated.id) node = n; });
        if (node) Object.assign(node.data, updated);
      }
    },

    bulkApplyFields: [
      { field: "connection_type", label: "연결유형", type: "select",
        options: () => [
          { value: "physical", label: "physical" },
          { value: "logical", label: "logical" },
        ],
      },
      { field: "cable_type", label: "케이블", type: "select",
        options: () => ["SM", "MM", "UTP", "STP", "DAC", "other"]
          .map((v) => ({ value: v, label: v })),
      },
      { field: "media_category", label: "매체", type: "select",
        options: () => ["copper", "fiber", "dac", "other"].map((v) => ({ value: v, label: v })),
      },
      { field: "cable_speed", label: "속도", type: "select",
        options: () => ["100M", "1G", "10G", "25G", "40G", "100G", "other"]
          .map((v) => ({ value: v, label: v })),
      },
      { field: "duplex", label: "Duplex", type: "select",
        options: () => ["full", "half", "auto"].map((v) => ({ value: v, label: v })),
      },
      { field: "status", label: "상태", type: "select",
        options: () => Object.entries(PORTMAP_STATUS_MAP)
          .map(([v, l]) => ({ value: v, label: l })),
      },
    ],

    selectors: {
      toggleBtn: "#btn-toggle-edit",
      saveBtn: "#btn-save-edit",
      cancelBtn: "#btn-cancel-edit",
      statusBar: "#edit-mode-bar",
      changeCount: "#edit-mode-count",
      errorCount: "#edit-mode-errors",
      bulkContainer: "#edit-mode-selection",
    },
  });

  restorePortMapColumnState();
  initColChooser(gridApi, columnDefs, PORTMAP_GRID_COLUMN_STATE_KEY, savePortMapColumnState);
  gridApi.addEventListener("columnMoved", savePortMapColumnState);
  gridApi.addEventListener("columnVisible", savePortMapColumnState);
  gridApi.addEventListener("columnPinned", savePortMapColumnState);
  gridApi.addEventListener("columnResized", (event) => {
    if (event.finished) savePortMapColumnState();
  });

  addCopyPasteHandler(gridEl, gridApi, {
    editableFields: EDITABLE_FIELDS,
    autoCreateRows: true,
    newRowDefaults: {
      _isNew: true,
      partner_id: Number(getCtxPartnerId() || 0),
      connection_type: "direct",
      cable_type: "UTP",
      media_category: "copper",
      src_connector_type: "RJ45",
      dst_connector_type: "RJ45",
      cable_speed: "1G",
      duplex: "auto",
      status: "active",
    },
    typeMap: { seq: "number" },
    onPaste: (changes) => {
      if (editMode && editMode.isActive()) {
        // 편집 모드: 단순 필드는 dirty 축적, asset/interface 필드는 무시
        for (const c of changes) {
          const node = gridApi.getDisplayedRowAtIndex(c.rowIndex);
          if (node?.data?.id && EDIT_MODE_FIELDS.has(c.field)) {
            editMode.markDirty(node.data.id, c.field, c.newValue, c.oldValue);
          }
        }
        gridApi.refreshCells({ force: true });
        return;
      }
      // 비편집 모드: 기존 동작 (개별 PATCH per row)
      const rowIds = [...new Set(changes.map(c => c.rowIndex))];
      rowIds.forEach(ri => {
        const node = gridApi.getDisplayedRowAtIndex(ri);
        if (!node || !node.data) return;
        if (!node.data.id && node.data._isNew) return;
        if (!node.data.id) return;
        const rowChanges = changes.filter(c => c.rowIndex === ri);
        const payload = {};
        rowChanges.forEach(c => { payload[c.field] = c.newValue; });
        apiFetch("/api/v1/port-maps/" + node.data.id, { method: "PATCH", body: payload })
          .catch(err => showToast(err.message, "error"));
      });
    },
  });

  loadPortMaps();
}

/* ── Inline Edit Handler ── */

async function handlePortMapCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue) return;
  const field = colDef.field;

  if (!data.id && data._isNew) {
    if (field === "src_asset_name" || field === "dst_asset_name") {
      const side = field.startsWith("src_") ? "src" : "dst";
      const asset = _pmAssets.find(a => a.asset_name === newValue);
      if (asset) {
        data[side + "_asset_id"] = asset.id;
        data[side + "_hostname"] = asset.hostname || "";
        data[side + "_is_registered"] = true;
        data[side + "_interface_id"] = null;
        data[side + "_interface_name"] = suggestNextInterfaceName(side, asset.id, data[side + "_interface_name"] || "") || "";
      } else {
        data[side + "_asset_id"] = null;
        data[side + "_hostname"] = "";
        data[side + "_is_registered"] = false;
      }
    }
    if (field === "src_interface_name" || field === "dst_interface_name") {
      const side = field.startsWith("src_") ? "src" : "dst";
      const assetId = data[side + "_asset_id"];
      if (assetId) {
        const ifaces = await _loadPmInterfaces(assetId);
        const iface = ifaces.find(i => i.name === newValue);
        if (iface) {
          data[side + "_interface_id"] = iface.id;
        } else {
          data[side + "_interface_id"] = null;
        }
      }
    }
    gridApi.refreshCells({ rowNodes: [event.node], force: true });
    return;
  }

  if (!data.id) return;

  // 편집 모드: 단순 필드는 dirty 축적
  if (editMode && editMode.isActive() && EDIT_MODE_FIELDS.has(field)) {
    editMode.handleCellChange(event);
    return;
  }

  try {
    // Asset name cells: resolve to asset_id and update hostname
    if (field === "src_asset_name" || field === "dst_asset_name") {
      const side = field.startsWith("src_") ? "src" : "dst";
      const asset = _pmAssets.find(a => a.asset_name === newValue);
      if (!asset) {
        showToast("자산을 찾을 수 없습니다: " + newValue, "warning");
        data[field] = oldValue;
        gridApi.refreshCells({ rowNodes: [event.node], force: true });
        return;
      }
      data[side + "_asset_id"] = asset.id;
      data[side + "_hostname"] = asset.hostname || "";
      // Clear interface when asset changes
      data[side + "_interface_id"] = null;
      data[side + "_interface_name"] = "";

      await apiFetch("/api/v1/port-maps/" + data.id, {
        method: "PATCH",
        body: { [side + "_interface_id"]: null },
      });
      // Reload to get server-denormalized data
      loadPortMaps();
      showToast("저장되었습니다.", "success");
      return;
    }

    // Interface name cells: resolve to interface_id and PATCH
    if (field === "src_interface_name" || field === "dst_interface_name") {
      const side = field.startsWith("src_") ? "src" : "dst";
      const assetId = data[side + "_asset_id"];
      if (!assetId) {
        showToast("자산을 먼저 선택하세요.", "warning");
        data[field] = oldValue;
        gridApi.refreshCells({ rowNodes: [event.node], force: true });
        return;
      }
      const ifaces = await _loadPmInterfaces(assetId);
      const iface = ifaces.find(i => i.name === newValue);
      if (!iface) {
        showToast("인터페이스를 찾을 수 없습니다: " + newValue, "warning");
        data[field] = oldValue;
        gridApi.refreshCells({ rowNodes: [event.node], force: true });
        return;
      }
      data[side + "_interface_id"] = iface.id;
      await apiFetch("/api/v1/port-maps/" + data.id, {
        method: "PATCH",
        body: { [side + "_interface_id"]: iface.id },
      });
      showToast("저장되었습니다.", "success");
      return;
    }

    // Other fields: PATCH directly
    await apiFetch("/api/v1/port-maps/" + data.id, {
      method: "PATCH",
      body: { [field]: newValue },
    });
    showToast("저장되었습니다.", "success");
  } catch (err) {
    showToast(err.message, "error");
    data[field] = oldValue;
    gridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}

/* ── Field Helpers (modal) ── */
const TEXT_FIELDS = [
  ["portmap-seq", "seq", "number"],
  ["portmap-cable-no", "cable_no", "text"],
  ["portmap-cable-request", "cable_request", "text"],
  ["portmap-purpose", "purpose", "text"],
  ["portmap-summary", "summary", "text"],
  ["portmap-protocol", "protocol", "text"],
  ["portmap-port", "port", "number"],
];

const SELECT_FIELDS = [
  ["portmap-connection-type", "connection_type", ""],
  ["portmap-cable-type", "cable_type", ""],
  ["portmap-media-category", "media_category", "copper"],
  ["portmap-src-connector-type", "src_connector_type", "RJ45"],
  ["portmap-dst-connector-type", "dst_connector_type", "RJ45"],
  ["portmap-cable-speed", "cable_speed", ""],
  ["portmap-duplex", "duplex", ""],
  ["portmap-cable-category", "cable_category", ""],
  ["portmap-status", "status", "required"],
];

/* ── Modal ── */
const modal = document.getElementById("modal-portmap");

const CONNECTOR_DEFAULTS = { copper: "RJ45", fiber: "LC", dac: "DAC", other: "other" };

function getConnectorOptions(mediaCategory) {
  return PORTMAP_MEDIA_TYPE_OPTIONS[mediaCategory || "other"] || PORTMAP_MEDIA_TYPE_OPTIONS.other;
}

function populateConnectorSelect(selectId, mediaCategory, selectedValue) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const options = getConnectorOptions(mediaCategory);
  sel.innerHTML = "";
  options.forEach((value) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    if ((selectedValue || "") === value) opt.selected = true;
    sel.appendChild(opt);
  });
  if (!sel.value) sel.value = selectedValue || CONNECTOR_DEFAULTS[mediaCategory] || options[0] || "";
}

function applyPortMapPreset(presetKey, { force = false } = {}) {
  const preset = PORTMAP_PRESET_DEFAULTS[presetKey];
  if (!preset) return;
  const fields = ["status", "connection_type", "cable_type", "media_category", "src_connector_type", "dst_connector_type", "cable_speed", "duplex"];
  fields.forEach((field) => {
    const el = document.getElementById(`portmap-${field.replaceAll("_", "-")}`);
    if (!el) return;
    const touched = el.dataset.touched === "1";
    if (force || !el.value || !touched) {
      el.value = preset[field] || "";
      if (field === "src_connector_type") el.dataset.lastMirroredValue = el.value;
    }
  });
  syncConnectorTypeControls({ mirrorDst: true });
}

function bindPresetTouchedFlags() {
  ["portmap-status", "portmap-connection-type", "portmap-cable-type", "portmap-media-category", "portmap-src-connector-type", "portmap-dst-connector-type", "portmap-cable-speed", "portmap-duplex"].forEach((id) => {
    const el = document.getElementById(id);
    if (!el || el.dataset.boundTouched === "1") return;
    el.dataset.boundTouched = "1";
    el.addEventListener("change", () => { el.dataset.touched = "1"; });
  });
}

function syncConnectorTypeControls({ mirrorDst = false } = {}) {
  const mediaCategory = document.getElementById("portmap-media-category")?.value || "copper";
  const srcSel = document.getElementById("portmap-src-connector-type");
  const dstSel = document.getElementById("portmap-dst-connector-type");
  const prevDst = dstSel?.value || "";
  populateConnectorSelect("portmap-src-connector-type", mediaCategory, srcSel?.value || CONNECTOR_DEFAULTS[mediaCategory]);
  populateConnectorSelect("portmap-dst-connector-type", mediaCategory, dstSel?.value || CONNECTOR_DEFAULTS[mediaCategory]);
  if (mirrorDst && dstSel && srcSel && (!prevDst || prevDst === srcSel.value)) {
    dstSel.value = srcSel.value;
  }
}

function resetForm() {
  document.getElementById("portmap-id").value = "";
  document.querySelectorAll("#modal-portmap select, #modal-portmap input, #modal-portmap textarea").forEach((el) => {
    delete el.dataset.touched;
    delete el.dataset.manual;
    delete el.dataset.lastMirroredValue;
  });
  TEXT_FIELDS.forEach(([elId]) => { document.getElementById(elId).value = ""; });
  SELECT_FIELDS.forEach(([elId, , dv]) => { document.getElementById(elId).value = dv; });
  document.getElementById("portmap-src-asset").value = "";
  _clearIfaceSelect("portmap-src-iface");
  document.getElementById("portmap-dst-asset").value = "";
  _clearIfaceSelect("portmap-dst-iface");
  document.getElementById("portmap-note").value = "";
  const presetSel = document.getElementById("portmap-link-preset");
  if (presetSel) presetSel.value = "direct-copper";
  applyPortMapPreset("direct-copper", { force: true });
  // Clear stored asset IDs
  modal._srcAssetId = null;
  modal._dstAssetId = null;
  modal._srcIfaceId = null;
  modal._dstIfaceId = null;
}

function _clearIfaceSelect(selectId) {
  const sel = document.getElementById(selectId);
  while (sel.options.length > 0) sel.remove(0);
  const defaultOpt = document.createElement("option");
  defaultOpt.value = "";
  defaultOpt.textContent = "\u2014 선택 \u2014";
  sel.appendChild(defaultOpt);
}

function openCreateModal() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  resetForm();
  document.getElementById("modal-portmap-title").textContent = "배선 등록";
  document.getElementById("btn-save-portmap").textContent = "등록";
  syncConnectorTypeControls({ mirrorDst: true });
  modal.showModal();
}

async function openEditModal(pm) {
  resetForm();
  document.getElementById("portmap-id").value = pm.id;
  TEXT_FIELDS.forEach(([elId, key]) => {
    document.getElementById(elId).value = pm[key] != null ? pm[key] : "";
  });
  SELECT_FIELDS.forEach(([elId, key, dv]) => {
    document.getElementById(elId).value = pm[key] || dv;
  });
  const presetSel = document.getElementById("portmap-link-preset");
  if (presetSel) {
    presetSel.value = pm.connection_type === "breakout" ? "breakout-fiber" : "direct-copper";
  }
  syncConnectorTypeControls();
  document.getElementById("portmap-note").value = pm.note || "";

  // Set asset fields
  document.getElementById("portmap-src-asset").value = pm.src_asset_name || "";
  modal._srcAssetId = pm.src_asset_id || null;
  document.getElementById("portmap-dst-asset").value = pm.dst_asset_name || "";
  modal._dstAssetId = pm.dst_asset_id || null;

  // Load interfaces for src/dst assets
  if (pm.src_asset_id) {
    const srcIfaces = await _loadPmInterfaces(pm.src_asset_id);
    _populateIfaceSelect("portmap-src-iface", srcIfaces, pm.src_interface_id);
    modal._srcIfaceId = pm.src_interface_id || null;
  }
  if (pm.dst_asset_id) {
    const dstIfaces = await _loadPmInterfaces(pm.dst_asset_id);
    _populateIfaceSelect("portmap-dst-iface", dstIfaces, pm.dst_interface_id);
    modal._dstIfaceId = pm.dst_interface_id || null;
  }

  document.getElementById("modal-portmap-title").textContent = "배선 수정";
  document.getElementById("btn-save-portmap").textContent = "저장";
  modal.showModal();
}

function _populateIfaceSelect(selectId, ifaces, selectedId) {
  const sel = document.getElementById(selectId);
  _clearIfaceSelect(selectId);
  ifaces.forEach(iface => {
    const opt = document.createElement("option");
    opt.value = iface.id;
    opt.textContent = iface.name || "(이름 없음)";
    if (selectedId && iface.id === selectedId) opt.selected = true;
    sel.appendChild(opt);
  });
}

async function _handleModalAssetInput(inputId, selectId, side) {
  const inputEl = document.getElementById(inputId);
  const keyword = inputEl.value.trim().toLowerCase();
  const asset = _pmAssets.find(a =>
    (a.asset_name || "").toLowerCase() === keyword ||
    (a.hostname || "").toLowerCase() === keyword
  );
  if (asset) {
    modal["_" + side + "AssetId"] = asset.id;
    inputEl.value = asset.asset_name;
    const ifaces = await _loadPmInterfaces(asset.id);
    _populateIfaceSelect(selectId, ifaces, null);
  } else {
    modal["_" + side + "AssetId"] = null;
    _clearIfaceSelect(selectId);
  }
}

async function savePortMap() {
  const cid = getCtxPartnerId();
  if (!cid) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const pmId = document.getElementById("portmap-id").value;

  const payload = { partner_id: cid };

  TEXT_FIELDS.forEach(([elId, key, type]) => {
    const raw = document.getElementById(elId).value.trim();
    payload[key] = type === "number" ? (raw ? Number(raw) : null) : (raw || null);
  });
  SELECT_FIELDS.forEach(([elId, key]) => {
    payload[key] = document.getElementById(elId).value || null;
  });
  payload.note = document.getElementById("portmap-note").value.trim() || null;

  // Interface FK fields
  const srcIfaceVal = document.getElementById("portmap-src-iface").value;
  const dstIfaceVal = document.getElementById("portmap-dst-iface").value;
  payload.src_interface_id = srcIfaceVal ? Number(srcIfaceVal) : null;
  payload.dst_interface_id = dstIfaceVal ? Number(dstIfaceVal) : null;

  try {
    if (pmId) {
      await apiFetch("/api/v1/port-maps/" + pmId, { method: "PATCH", body: payload });
      showToast("배선이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/port-maps", { method: "POST", body: payload });
      showToast("배선이 등록되었습니다.");
    }
    modal.close();
    loadPortMaps();
  } catch (err) { showToast(err.message, "error"); }
}

async function deletePortMap(pm) {
  confirmDelete("이 배선을 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/port-maps/" + pm.id, { method: "DELETE" });
      showToast("배선이 삭제되었습니다.");
      loadPortMaps();
    } catch (err) { showToast(err.message, "error"); }
  });
}

/* ── Modal Asset Autocomplete (datalist approach) ── */

function _setupModalAssetAutocomplete(inputId, datalistId, selectId, side) {
  const inputEl = document.getElementById(inputId);

  // Create datalist for asset suggestions
  let dl = document.getElementById(datalistId);
  if (!dl) {
    dl = document.createElement("datalist");
    dl.id = datalistId;
    inputEl.parentElement.appendChild(dl);
    inputEl.setAttribute("list", datalistId);
  }

  // Populate datalist using safe DOM methods
  function _refreshDatalist() {
    while (dl.firstChild) dl.removeChild(dl.firstChild);
    _pmAssets.forEach(a => {
      const opt = document.createElement("option");
      opt.value = a.asset_name || "";
      opt.textContent = a.asset_name + (a.hostname ? " (" + a.hostname + ")" : "");
      dl.appendChild(opt);
    });
  }

  inputEl.addEventListener("focus", _refreshDatalist);
  inputEl.addEventListener("change", () => _handleModalAssetInput(inputId, selectId, side));
  inputEl.addEventListener("blur", () => _handleModalAssetInput(inputId, selectId, side));
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", () => {
  initGrid();
  bindPresetTouchedFlags();
  applyPortMapPreset("direct-copper", { force: true });
  document.getElementById("portmap-link-preset")?.addEventListener("change", (e) => {
    applyPortMapPreset(e.target.value, { force: false });
  });
  document.getElementById("portmap-media-category")?.addEventListener("change", () => syncConnectorTypeControls({ mirrorDst: true }));
  document.getElementById("portmap-src-connector-type")?.addEventListener("change", () => {
    const dst = document.getElementById("portmap-dst-connector-type");
    const src = document.getElementById("portmap-src-connector-type");
    if (dst && src && (!dst.dataset.manual || dst.value === dst.dataset.lastMirroredValue || !dst.value)) {
      dst.value = src.value;
      dst.dataset.lastMirroredValue = src.value;
    }
  });
  document.getElementById("portmap-dst-connector-type")?.addEventListener("change", () => {
    const dst = document.getElementById("portmap-dst-connector-type");
    if (dst) dst.dataset.manual = "1";
  });
  document.getElementById("portmap-connection-type")?.addEventListener("change", (e) => {
    const presetSel = document.getElementById("portmap-link-preset");
    if (!presetSel) return;
    if (e.target.value === "breakout") {
      presetSel.value = "breakout-fiber";
      applyPortMapPreset("breakout-fiber", { force: false });
    } else if (e.target.value === "direct") {
      presetSel.value = "direct-copper";
      applyPortMapPreset("direct-copper", { force: false });
    }
  });

  _setupModalAssetAutocomplete("portmap-src-asset", "dl-pm-src-assets", "portmap-src-iface", "src");
  _setupModalAssetAutocomplete("portmap-dst-asset", "dl-pm-dst-assets", "portmap-dst-iface", "dst");

  // Interface select change handlers
  document.getElementById("portmap-src-iface").addEventListener("change", (e) => {
    modal._srcIfaceId = e.target.value ? Number(e.target.value) : null;
  });
  document.getElementById("portmap-dst-iface").addEventListener("change", (e) => {
    modal._dstIfaceId = e.target.value ? Number(e.target.value) : null;
  });
});

document.getElementById("btn-add-portmap").addEventListener("click", openCreateModal);
document.getElementById("btn-add-portmap-row-bottom").addEventListener("click", addPortMapRow);
document.getElementById("btn-save-new-portmaps").addEventListener("click", saveNewPortMaps);
document.getElementById("btn-cancel-portmap").addEventListener("click", () => modal.close());
document.getElementById("btn-save-portmap").addEventListener("click", savePortMap);
document.getElementById("btn-save-edit").addEventListener("click", portmapSaveEditMode);
document.getElementById("btn-cancel-edit").addEventListener("click", portmapCancelEditMode);
document.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === "s") {
    e.preventDefault();
    if (editMode && editMode.isActive()) {
      portmapSaveEditMode();
      return;
    }
    if (_hasNewRows) {
      saveNewPortMaps();
      return;
    }
    showToast("저장할 변경사항이 없습니다.", "info");
  }
});
initProjectFilterCheckbox(loadPortMaps);
window.addEventListener("ctx-changed", loadPortMaps);


document.getElementById("portmap-search")?.addEventListener("input", (e) => {
  if (gridApi) gridApi.setGridOption("quickFilterText", e.target.value || "");
});
