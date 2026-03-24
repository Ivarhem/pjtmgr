/* ── 자산 인벤토리 (고객사 중심) ── */

const ASSET_TYPE_MAP = {
  server: "서버",
  network: "네트워크",
  security: "보안장비",
  storage: "스토리지",
  other: "기타",
};

const ENV_MAP = {
  prod: "운영",
  dev: "개발",
  staging: "스테이징",
  dr: "DR",
};

const ASSET_STATUS_MAP = {
  planned: "계획",
  active: "운영중",
  decommissioned: "폐기",
};

const columnDefs = [
  { field: "asset_name", headerName: "자산명", flex: 1, minWidth: 180, sort: "asc" },
  {
    field: "asset_type",
    headerName: "유형",
    width: 110,
    valueFormatter: (p) => ASSET_TYPE_MAP[p.value] || p.value,
  },
  { field: "vendor", headerName: "제조사", width: 130 },
  { field: "model", headerName: "모델", width: 130 },
  { field: "hostname", headerName: "호스트명", width: 140 },
  { field: "service_ip", headerName: "서비스IP", width: 130 },
  { field: "zone", headerName: "존", width: 100 },
  { field: "category", headerName: "분류", width: 110 },
  { field: "rack_no", headerName: "랙", width: 80 },
  {
    field: "status",
    headerName: "상태",
    width: 100,
    cellRenderer: (params) => {
      const label = ASSET_STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
  },
];

let gridApi;
let _selectedAsset = null;

/* ── Data loading ── */

async function loadAssets() {
  const cid = getCtxPartnerId();
  if (!cid) {
    gridApi.setGridOption("rowData", []);
    return;
  }
  let url = "/api/v1/assets?partner_id=" + cid;
  const pid = getCtxProjectId();
  if (pid && isProjectFilterActive()) url += "&project_id=" + pid;

  try {
    const data = await apiFetch(url);
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Grid init ── */

function initGrid() {
  const gridDiv = document.getElementById("grid-assets");
  gridApi = agGrid.createGrid(gridDiv, {
    columnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    onRowClicked: (e) => showAssetDetail(e.data),
  });
  // 초기 로드는 ctx-changed 이벤트에서 처리 (initContextSelectors 완료 후 dispatch)
  if (getCtxPartnerId()) loadAssets();
}

/* ── Detail panel ── */

const DETAIL_TABS = {
  basic: [
    ["자산명", "asset_name"], ["유형", "asset_type", v => ASSET_TYPE_MAP[v] || v],
    ["제조사", "vendor"], ["모델", "model"], ["시리얼", "serial_no"],
    ["환경", "environment", v => ENV_MAP[v] || v], ["상태", "status", v => ASSET_STATUS_MAP[v] || v],
    ["비고", "note"],
  ],
  location: [
    ["센터", "center"], ["장비 ID", "equipment_id"],
    ["랙 번호", "rack_no"], ["랙 유닛", "rack_unit"],
    ["위치", "location"], ["운영 유형", "operation_type"],
    ["분류", "category"], ["세부 분류", "subcategory"],
    ["단계", "phase"], ["입고일", "received_date"],
  ],
  network: [
    ["호스트명", "hostname"], ["클러스터", "cluster"],
    ["서비스명", "service_name"], ["존", "zone"],
    ["서비스 IP", "service_ip"], ["관리 IP", "mgmt_ip"],
  ],
  hw: [
    ["크기(U)", "size_unit"], ["LC", "lc_count"], ["HA", "ha_count"],
    ["UTP", "utp_count"], ["전원", "power_count"], ["전원 유형", "power_type"],
    ["펌웨어", "firmware_version"],
  ],
  mgmt: [
    ["자산 등급", "asset_class"], ["자산 번호", "asset_number"],
    ["도입 연도", "year_acquired"], ["부서", "dept"],
    ["주 담당자", "primary_contact_name"], ["부 담당자", "secondary_contact_name"],
    ["유지보수 업체", "maintenance_vendor"],
  ],
};

function showAssetDetail(asset) {
  _selectedAsset = asset;
  const panel = document.getElementById("asset-detail-panel");
  panel.classList.remove("hidden");
  document.getElementById("detail-asset-name").textContent =
    asset.asset_name + (asset.hostname ? " (" + asset.hostname + ")" : "");
  renderDetailTab("basic");
}

function renderDetailTab(tab) {
  const container = document.getElementById("detail-content");
  // Clear safely
  while (container.firstChild) container.removeChild(container.firstChild);

  document.querySelectorAll(".detail-tabs .tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.dtab === tab);
  });

  if (tab === "relations") {
    const p = document.createElement("p");
    p.className = "text-muted";
    p.textContent = "관계 정보는 별도 탭에서 조회합니다.";
    container.appendChild(p);
    return;
  }

  const fields = DETAIL_TABS[tab];
  if (!fields || !_selectedAsset) return;

  const grid = document.createElement("div");
  grid.className = "detail-grid";
  fields.forEach(([label, key, fmt]) => {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    const raw = _selectedAsset[key];
    dd.textContent = raw != null ? (fmt ? fmt(raw) : String(raw)) : "—";
    grid.appendChild(dt);
    grid.appendChild(dd);
  });
  container.appendChild(grid);
}

function closeDetail() {
  document.getElementById("asset-detail-panel").classList.add("hidden");
  _selectedAsset = null;
}

/* ── Modal ── */
const modal = document.getElementById("modal-asset");

function resetForm() {
  document.getElementById("asset-id").value = "";
  document.getElementById("form-asset").reset();
}

function openCreateModal() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  resetForm();
  document.getElementById("modal-asset-title").textContent = "자산 등록";
  document.getElementById("btn-save-asset").textContent = "등록";
  modal.showModal();
}

function openEditModal(asset) {
  if (!asset) asset = _selectedAsset;
  if (!asset) return;
  document.getElementById("asset-id").value = asset.id;
  document.getElementById("asset-name").value = asset.asset_name;
  document.getElementById("asset-type").value = asset.asset_type;
  document.getElementById("asset-vendor").value = asset.vendor || "";
  document.getElementById("asset-model").value = asset.model || "";
  document.getElementById("asset-status").value = asset.status;
  document.getElementById("asset-note").value = asset.note || "";

  document.getElementById("asset-serial-no").value = asset.serial_no || "";
  document.getElementById("asset-equipment-id").value = asset.equipment_id || "";
  document.getElementById("asset-rack-no").value = asset.rack_no || "";
  document.getElementById("asset-rack-unit").value = asset.rack_unit || "";
  document.getElementById("asset-center").value = asset.center || "";
  document.getElementById("asset-operation-type").value = asset.operation_type || "";
  document.getElementById("asset-category").value = asset.category || "";
  document.getElementById("asset-subcategory").value = asset.subcategory || "";
  document.getElementById("asset-phase").value = asset.phase || "";
  document.getElementById("asset-received-date").value = asset.received_date || "";

  document.getElementById("asset-hostname").value = asset.hostname || "";
  document.getElementById("asset-cluster").value = asset.cluster || "";
  document.getElementById("asset-service-name").value = asset.service_name || "";
  document.getElementById("asset-zone").value = asset.zone || "";
  document.getElementById("asset-service-ip").value = asset.service_ip || "";
  document.getElementById("asset-mgmt-ip").value = asset.mgmt_ip || "";

  document.getElementById("asset-size-unit").value = asset.size_unit != null ? asset.size_unit : "";
  document.getElementById("asset-lc-count").value = asset.lc_count != null ? asset.lc_count : "";
  document.getElementById("asset-ha-count").value = asset.ha_count != null ? asset.ha_count : "";
  document.getElementById("asset-utp-count").value = asset.utp_count != null ? asset.utp_count : "";
  document.getElementById("asset-power-count").value = asset.power_count != null ? asset.power_count : "";
  document.getElementById("asset-power-type").value = asset.power_type || "";
  document.getElementById("asset-firmware-version").value = asset.firmware_version || "";

  document.getElementById("asset-asset-class").value = asset.asset_class || "";
  document.getElementById("asset-asset-number").value = asset.asset_number || "";
  document.getElementById("asset-year-acquired").value = asset.year_acquired != null ? asset.year_acquired : "";
  document.getElementById("asset-dept").value = asset.dept || "";
  document.getElementById("asset-primary-contact-name").value = asset.primary_contact_name || "";
  document.getElementById("asset-secondary-contact-name").value = asset.secondary_contact_name || "";
  document.getElementById("asset-maintenance-vendor").value = asset.maintenance_vendor || "";

  document.getElementById("modal-asset-title").textContent = "자산 수정";
  document.getElementById("btn-save-asset").textContent = "저장";
  modal.showModal();
}

function intOrNull(id) {
  const v = document.getElementById(id).value;
  return v !== "" ? Number(v) : null;
}

async function saveAsset() {
  const cid = getCtxPartnerId();
  if (!cid) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const assetId = document.getElementById("asset-id").value;
  const payload = {
    partner_id: cid,
    asset_name: document.getElementById("asset-name").value,
    asset_type: document.getElementById("asset-type").value,
    vendor: document.getElementById("asset-vendor").value || null,
    model: document.getElementById("asset-model").value || null,
    status: document.getElementById("asset-status").value,
    note: document.getElementById("asset-note").value || null,
    serial_no: document.getElementById("asset-serial-no").value || null,
    equipment_id: document.getElementById("asset-equipment-id").value || null,
    rack_no: document.getElementById("asset-rack-no").value || null,
    rack_unit: document.getElementById("asset-rack-unit").value || null,
    center: document.getElementById("asset-center").value || null,
    operation_type: document.getElementById("asset-operation-type").value || null,
    category: document.getElementById("asset-category").value || null,
    subcategory: document.getElementById("asset-subcategory").value || null,
    phase: document.getElementById("asset-phase").value || null,
    received_date: document.getElementById("asset-received-date").value || null,
    hostname: document.getElementById("asset-hostname").value || null,
    cluster: document.getElementById("asset-cluster").value || null,
    service_name: document.getElementById("asset-service-name").value || null,
    zone: document.getElementById("asset-zone").value || null,
    service_ip: document.getElementById("asset-service-ip").value || null,
    mgmt_ip: document.getElementById("asset-mgmt-ip").value || null,
    size_unit: intOrNull("asset-size-unit"),
    lc_count: intOrNull("asset-lc-count"),
    ha_count: intOrNull("asset-ha-count"),
    utp_count: intOrNull("asset-utp-count"),
    power_count: intOrNull("asset-power-count"),
    power_type: document.getElementById("asset-power-type").value || null,
    firmware_version: document.getElementById("asset-firmware-version").value || null,
    asset_class: document.getElementById("asset-asset-class").value || null,
    asset_number: document.getElementById("asset-asset-number").value || null,
    year_acquired: intOrNull("asset-year-acquired"),
    dept: document.getElementById("asset-dept").value || null,
    primary_contact_name: document.getElementById("asset-primary-contact-name").value || null,
    secondary_contact_name: document.getElementById("asset-secondary-contact-name").value || null,
    maintenance_vendor: document.getElementById("asset-maintenance-vendor").value || null,
  };

  try {
    if (assetId) {
      await apiFetch("/api/v1/assets/" + assetId, { method: "PATCH", body: payload });
      showToast("자산이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/assets", { method: "POST", body: payload });
      showToast("자산이 등록되었습니다.");
    }
    modal.close();
    loadAssets();
    closeDetail();
  } catch (err) {
    showToast(err.message, "error");
  }
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

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-add-asset").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-asset").addEventListener("click", () => modal.close());
document.getElementById("btn-save-asset").addEventListener("click", saveAsset);
document.getElementById("btn-edit-asset").addEventListener("click", () => openEditModal());
document.getElementById("btn-delete-asset").addEventListener("click", deleteAssetAction);
document.getElementById("btn-close-detail").addEventListener("click", closeDetail);

// Detail tab switching
document.querySelectorAll(".detail-tabs .tab-btn").forEach(btn => {
  btn.addEventListener("click", () => renderDetailTab(btn.dataset.dtab));
});

// Global project filter checkbox
initProjectFilterCheckbox(loadAssets);

// Context selector change
window.addEventListener("ctx-changed", () => {
  closeDetail();
  loadAssets();
});
