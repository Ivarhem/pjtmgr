/* ── 자산 인벤토리 ── */

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
  { field: "role", headerName: "역할", width: 130 },
  {
    field: "environment",
    headerName: "환경",
    width: 90,
    valueFormatter: (p) => ENV_MAP[p.value] || p.value,
  },
  { field: "location", headerName: "위치", width: 130 },
  { field: "equipment_id", headerName: "장비 ID", width: 120 },
  { field: "hostname", headerName: "호스트명", width: 140 },
  { field: "serial_no", headerName: "시리얼", width: 130 },
  { field: "zone", headerName: "존", width: 100 },
  { field: "category", headerName: "분류", width: 110 },
  { field: "rack_no", headerName: "랙 번호", width: 100 },
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
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm";
      wrap.style.display = "inline-flex";

      const editBtn = document.createElement("button");
      editBtn.className = "btn btn-xs btn-secondary";
      editBtn.textContent = "수정";
      editBtn.addEventListener("click", () => openEditModal(params.data));

      const delBtn = document.createElement("button");
      delBtn.className = "btn btn-xs btn-danger";
      delBtn.textContent = "삭제";
      delBtn.addEventListener("click", () => deleteAsset(params.data));

      wrap.appendChild(editBtn);
      wrap.appendChild(delBtn);
      return wrap;
    },
    sortable: false,
    filter: false,
  },
];

let gridApi;

async function loadAssets() {
  try {
    const data = await apiFetch("/api/v1/assets");
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function populateProjectOptions(projects) {
  const select = document.getElementById("asset-project-id");
  while (select.firstChild) select.removeChild(select.firstChild);
  projects.forEach((p) => {
    const opt = document.createElement("option");
    opt.value = p.id;
    opt.textContent = p.project_code + " - " + p.project_name;
    select.appendChild(opt);
  });
}

async function loadProjectOptions() {
  try {
    const projects = await apiFetch("/api/v1/projects");
    populateProjectOptions(projects);
  } catch (err) {
    showToast("프로젝트 목록을 불러올 수 없습니다.", "error");
  }
}

function initGrid() {
  const gridDiv = document.getElementById("grid-assets");
  gridApi = agGrid.createGrid(gridDiv, {
    columnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });
  loadAssets();
  loadProjectOptions();
}

/* ── Modal ── */
const modal = document.getElementById("modal-asset");

function resetForm() {
  document.getElementById("asset-id").value = "";
  document.getElementById("asset-name").value = "";
  document.getElementById("asset-type").value = "server";
  document.getElementById("asset-vendor").value = "";
  document.getElementById("asset-model").value = "";
  document.getElementById("asset-status").value = "planned";
  document.getElementById("asset-note").value = "";

  // 장비 명세
  document.getElementById("asset-serial-no").value = "";
  document.getElementById("asset-equipment-id").value = "";
  document.getElementById("asset-rack-no").value = "";
  document.getElementById("asset-rack-unit").value = "";
  document.getElementById("asset-center").value = "";
  document.getElementById("asset-operation-type").value = "";
  document.getElementById("asset-category").value = "";
  document.getElementById("asset-subcategory").value = "";
  document.getElementById("asset-phase").value = "";
  document.getElementById("asset-received-date").value = "";

  // 논리 구성
  document.getElementById("asset-hostname").value = "";
  document.getElementById("asset-cluster").value = "";
  document.getElementById("asset-service-name").value = "";
  document.getElementById("asset-zone").value = "";
  document.getElementById("asset-service-ip").value = "";
  document.getElementById("asset-mgmt-ip").value = "";

  // Hardware 구성
  document.getElementById("asset-size-unit").value = "";
  document.getElementById("asset-lc-count").value = "";
  document.getElementById("asset-ha-count").value = "";
  document.getElementById("asset-utp-count").value = "";
  document.getElementById("asset-power-count").value = "";
  document.getElementById("asset-power-type").value = "";
  document.getElementById("asset-firmware-version").value = "";

  // 자산 정보
  document.getElementById("asset-asset-class").value = "";
  document.getElementById("asset-asset-number").value = "";
  document.getElementById("asset-year-acquired").value = "";
  document.getElementById("asset-dept").value = "";
  document.getElementById("asset-primary-contact-name").value = "";
  document.getElementById("asset-secondary-contact-name").value = "";
  document.getElementById("asset-maintenance-vendor").value = "";
}

function openCreateModal() {
  resetForm();
  document.getElementById("modal-asset-title").textContent = "자산 등록";
  document.getElementById("btn-save-asset").textContent = "등록";
  modal.showModal();
}

function openEditModal(asset) {
  document.getElementById("asset-id").value = asset.id;
  document.getElementById("asset-project-id").value = asset.project_id;
  document.getElementById("asset-name").value = asset.asset_name;
  document.getElementById("asset-type").value = asset.asset_type;
  document.getElementById("asset-vendor").value = asset.vendor || "";
  document.getElementById("asset-model").value = asset.model || "";
  document.getElementById("asset-status").value = asset.status;
  document.getElementById("asset-note").value = asset.note || "";

  // 장비 명세
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

  // 논리 구성
  document.getElementById("asset-hostname").value = asset.hostname || "";
  document.getElementById("asset-cluster").value = asset.cluster || "";
  document.getElementById("asset-service-name").value = asset.service_name || "";
  document.getElementById("asset-zone").value = asset.zone || "";
  document.getElementById("asset-service-ip").value = asset.service_ip || "";
  document.getElementById("asset-mgmt-ip").value = asset.mgmt_ip || "";

  // Hardware 구성
  document.getElementById("asset-size-unit").value = asset.size_unit != null ? asset.size_unit : "";
  document.getElementById("asset-lc-count").value = asset.lc_count != null ? asset.lc_count : "";
  document.getElementById("asset-ha-count").value = asset.ha_count != null ? asset.ha_count : "";
  document.getElementById("asset-utp-count").value = asset.utp_count != null ? asset.utp_count : "";
  document.getElementById("asset-power-count").value = asset.power_count != null ? asset.power_count : "";
  document.getElementById("asset-power-type").value = asset.power_type || "";
  document.getElementById("asset-firmware-version").value = asset.firmware_version || "";

  // 자산 정보
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
  const assetId = document.getElementById("asset-id").value;
  const payload = {
    project_id: Number(document.getElementById("asset-project-id").value),
    asset_name: document.getElementById("asset-name").value,
    asset_type: document.getElementById("asset-type").value,
    vendor: document.getElementById("asset-vendor").value || null,
    model: document.getElementById("asset-model").value || null,
    status: document.getElementById("asset-status").value,
    note: document.getElementById("asset-note").value || null,

    // 장비 명세
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

    // 논리 구성
    hostname: document.getElementById("asset-hostname").value || null,
    cluster: document.getElementById("asset-cluster").value || null,
    service_name: document.getElementById("asset-service-name").value || null,
    zone: document.getElementById("asset-zone").value || null,
    service_ip: document.getElementById("asset-service-ip").value || null,
    mgmt_ip: document.getElementById("asset-mgmt-ip").value || null,

    // Hardware 구성
    size_unit: intOrNull("asset-size-unit"),
    lc_count: intOrNull("asset-lc-count"),
    ha_count: intOrNull("asset-ha-count"),
    utp_count: intOrNull("asset-utp-count"),
    power_count: intOrNull("asset-power-count"),
    power_type: document.getElementById("asset-power-type").value || null,
    firmware_version: document.getElementById("asset-firmware-version").value || null,

    // 자산 정보
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
      await apiFetch(`/api/v1/assets/${assetId}`, { method: "PATCH", body: payload });
      showToast("자산이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/assets", { method: "POST", body: payload });
      showToast("자산이 등록되었습니다.");
    }
    modal.close();
    loadAssets();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteAsset(asset) {
  confirmDelete(
    `자산 "${asset.asset_name}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/assets/${asset.id}`, { method: "DELETE" });
        showToast("자산이 삭제되었습니다.");
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

