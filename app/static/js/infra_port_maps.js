/* ── 케이블 배선도 (Port Maps, 고객사 중심) ── */

const PORTMAP_STATUS_MAP = {
  required: "필요", open: "오픈", closed: "차단", pending: "대기",
};

/* ── Asset / Interface Cache ── */
let _pmAssets = [];
let _pmIfaceCache = {};  // { asset_id: [interfaces] }

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

/* ── Column Definitions ── */
const columnDefs = [
  { field: "seq", headerName: "순번", width: 70 },
  { field: "src_asset_name", headerName: "출발 자산", width: 130, editable: true, cellEditor: AssetCellEditor },
  { field: "src_interface_name", headerName: "출발 IF", width: 110, editable: true, cellEditor: InterfaceCellEditor },
  { field: "src_hostname", headerName: "출발 호스트", width: 120 },
  { field: "dst_asset_name", headerName: "도착 자산", width: 130, editable: true, cellEditor: AssetCellEditor },
  { field: "dst_interface_name", headerName: "도착 IF", width: 110, editable: true, cellEditor: InterfaceCellEditor },
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
    field: "cable_speed", headerName: "속도", width: 80, editable: true,
    cellEditor: "agSelectCellEditor", cellEditorParams: { values: ["100M", "1G", "10G", "25G", "40G", "100G", "other"] },
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
  "connection_type", "cable_no", "cable_type", "cable_speed", "purpose", "status",
];

let gridApi;

/* ── Data Loading ── */

async function loadPortMaps() {
  const cid = getCtxPartnerId();
  if (!cid) { gridApi.setGridOption("rowData", []); return; }

  // Load assets cache, clear interface cache
  await _loadPmAssets();
  _pmIfaceCache = {};

  let url = "/api/v1/port-maps?partner_id=" + cid;
  const pid = getCtxProjectId();
  if (pid && isProjectFilterActive()) url += "&period_id=" + pid;
  try {
    const data = await apiFetch(url);
    gridApi.setGridOption("rowData", data);
  } catch (err) { showToast(err.message, "error"); }
}

function initGrid() {
  const gridEl = document.getElementById("grid-portmaps");
  gridApi = agGrid.createGrid(gridEl, {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: "modal-edit",
      onEdit: (data) => openEditModal(data),
    }),
    onCellValueChanged: handlePortMapCellChanged,
  });

  addCopyPasteHandler(gridEl, gridApi, {
    editableFields: EDITABLE_FIELDS,
    onPaste: (changes) => {
      // PATCH each changed row
      const rowIds = [...new Set(changes.map(c => c.rowIndex))];
      rowIds.forEach(ri => {
        const node = gridApi.getDisplayedRowAtIndex(ri);
        if (!node || !node.data || !node.data.id) return;
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
  if (newValue === oldValue || !data.id) return;
  const field = colDef.field;

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
  ["portmap-cable-speed", "cable_speed", ""],
  ["portmap-duplex", "duplex", ""],
  ["portmap-cable-category", "cable_category", ""],
  ["portmap-status", "status", "required"],
];

/* ── Modal ── */
const modal = document.getElementById("modal-portmap");

function resetForm() {
  document.getElementById("portmap-id").value = "";
  TEXT_FIELDS.forEach(([elId]) => { document.getElementById(elId).value = ""; });
  SELECT_FIELDS.forEach(([elId, , dv]) => { document.getElementById(elId).value = dv; });
  document.getElementById("portmap-src-asset").value = "";
  _clearIfaceSelect("portmap-src-iface");
  document.getElementById("portmap-dst-asset").value = "";
  _clearIfaceSelect("portmap-dst-iface");
  document.getElementById("portmap-note").value = "";
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
document.getElementById("btn-cancel-portmap").addEventListener("click", () => modal.close());
document.getElementById("btn-save-portmap").addEventListener("click", savePortMap);
initProjectFilterCheckbox(loadPortMaps);
window.addEventListener("ctx-changed", loadPortMaps);
