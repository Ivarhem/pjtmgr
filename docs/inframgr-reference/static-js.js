// inframgr JavaScript Reference
// Generated for migration reference - 2026-03-18

// ============================================
// FILE: app/static/js/assets.js
// ============================================
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


// ============================================
// FILE: app/static/js/ip_inventory.js
// ============================================
/* ── IP 인벤토리 ── */

const SUBNET_ROLE_MAP = {
  service: "서비스",
  management: "관리",
  backup: "백업",
  dmz: "DMZ",
  other: "기타",
};

const IP_TYPE_MAP = {
  service: "서비스",
  management: "관리",
  backup: "백업",
  vip: "VIP",
  other: "기타",
};

/* ── Subnet Grid ── */
const subnetColDefs = [
  { field: "name", headerName: "대역명", flex: 1, minWidth: 160, sort: "asc" },
  { field: "subnet", headerName: "서브넷", width: 160 },
  {
    field: "role",
    headerName: "역할",
    width: 100,
    valueFormatter: (p) => SUBNET_ROLE_MAP[p.value] || p.value,
  },
  { field: "vlan_id", headerName: "VLAN", width: 80 },
  { field: "gateway", headerName: "게이트웨이", width: 140 },
  { field: "region", headerName: "지역", width: 100 },
  { field: "floor", headerName: "층", width: 70 },
  { field: "counterpart", headerName: "상대국/기관", width: 160 },
  { field: "allocation_type", headerName: "할당유형", width: 100 },
  { field: "category", headerName: "분류", width: 100 },
  { field: "zone", headerName: "존", width: 100 },
  { field: "netmask", headerName: "넷마스크", width: 140 },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "gap-sm";
      span.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditSubnet(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteSubnet(params.data));
      span.appendChild(btnEdit);
      span.appendChild(btnDel);
      return span;
    },
    sortable: false,
    filter: false,
  },
];

let subnetGridApi;

/* ── IP Grid ── */
const ipColDefs = [
  { field: "ip_address", headerName: "IP 주소", width: 160, sort: "asc" },
  {
    field: "ip_type",
    headerName: "용도",
    width: 100,
    valueFormatter: (p) => IP_TYPE_MAP[p.value] || p.value,
  },
  { field: "interface_name", headerName: "인터페이스", width: 120 },
  { field: "asset_id", headerName: "자산 ID", width: 90 },
  { field: "ip_subnet_id", headerName: "대역 ID", width: 90 },
  { field: "note", headerName: "비고", flex: 1, minWidth: 150 },
  { field: "zone", headerName: "존", width: 100 },
  { field: "service_name", headerName: "서비스명", width: 130 },
  { field: "hostname", headerName: "호스트명", width: 130 },
  { field: "vlan_id", headerName: "VLAN", width: 80 },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "gap-sm";
      span.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditIp(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteIp(params.data));
      span.appendChild(btnEdit);
      span.appendChild(btnDel);
      return span;
    },
    sortable: false,
    filter: false,
  },
];

let ipGridApi;

/* ── Data Loading ── */
async function loadSubnets() {
  try {
    const data = await apiFetch("/api/v1/ip-subnets");
    subnetGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadIps() {
  try {
    const data = await apiFetch("/api/v1/asset-ips");
    ipGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function populateSelect(selectEl, items, textFn) {
  while (selectEl.options.length > (selectEl.dataset.keepFirst ? 1 : 0)) {
    selectEl.remove(selectEl.options.length - 1);
  }
  items.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = textFn(item);
    selectEl.appendChild(opt);
  });
}

async function loadDropdowns() {
  try {
    const [projects, assets, subnets] = await Promise.all([
      apiFetch("/api/v1/projects"),
      apiFetch("/api/v1/assets"),
      apiFetch("/api/v1/ip-subnets"),
    ]);
    populateSelect(
      document.getElementById("subnet-project-id"),
      projects,
      (p) => p.project_code + " - " + p.project_name
    );

    const assetSelect = document.getElementById("ip-asset-id");
    while (assetSelect.firstChild) assetSelect.removeChild(assetSelect.firstChild);
    assets.forEach((a) => {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = a.asset_name;
      assetSelect.appendChild(opt);
    });

    const subnetSelect = document.getElementById("ip-subnet-id");
    // keep first "선택 안 함" option
    while (subnetSelect.options.length > 1) subnetSelect.remove(1);
    subnets.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name + " (" + s.subnet + ")";
      subnetSelect.appendChild(opt);
    });
  } catch (err) {
    showToast("드롭다운을 불러올 수 없습니다.", "error");
  }
}

function initGrids() {
  subnetGridApi = agGrid.createGrid(document.getElementById("grid-subnets"), {
    columnDefs: subnetColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  ipGridApi = agGrid.createGrid(document.getElementById("grid-ips"), {
    columnDefs: ipColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  loadSubnets();
  loadIps();
  loadDropdowns();
}

/* ── Subnet Modal ── */
const subnetModal = document.getElementById("modal-subnet");

function resetSubnetForm() {
  document.getElementById("subnet-id").value = "";
  document.getElementById("subnet-name").value = "";
  document.getElementById("subnet-cidr").value = "";
  document.getElementById("subnet-role").value = "service";
  document.getElementById("subnet-vlan-id").value = "";
  document.getElementById("subnet-gateway").value = "";
  document.getElementById("subnet-region").value = "";
  document.getElementById("subnet-floor").value = "";
  document.getElementById("subnet-counterpart").value = "";
  document.getElementById("subnet-description").value = "";
  document.getElementById("subnet-note").value = "";
  document.getElementById("subnet-allocation-type").value = "";
  document.getElementById("subnet-category").value = "";
  document.getElementById("subnet-zone").value = "";
  document.getElementById("subnet-netmask").value = "";
}

function openCreateSubnet() {
  resetSubnetForm();
  document.getElementById("modal-subnet-title").textContent = "대역 등록";
  document.getElementById("btn-save-subnet").textContent = "등록";
  subnetModal.showModal();
}

function openEditSubnet(subnet) {
  document.getElementById("subnet-id").value = subnet.id;
  document.getElementById("subnet-project-id").value = subnet.project_id;
  document.getElementById("subnet-name").value = subnet.name;
  document.getElementById("subnet-cidr").value = subnet.subnet;
  document.getElementById("subnet-role").value = subnet.role;
  document.getElementById("subnet-vlan-id").value = subnet.vlan_id || "";
  document.getElementById("subnet-gateway").value = subnet.gateway || "";
  document.getElementById("subnet-region").value = subnet.region || "";
  document.getElementById("subnet-floor").value = subnet.floor || "";
  document.getElementById("subnet-counterpart").value = subnet.counterpart || "";
  document.getElementById("subnet-description").value = subnet.description || "";
  document.getElementById("subnet-note").value = subnet.note || "";
  document.getElementById("subnet-allocation-type").value = subnet.allocation_type || "";
  document.getElementById("subnet-category").value = subnet.category || "";
  document.getElementById("subnet-zone").value = subnet.zone || "";
  document.getElementById("subnet-netmask").value = subnet.netmask || "";
  document.getElementById("modal-subnet-title").textContent = "대역 수정";
  document.getElementById("btn-save-subnet").textContent = "저장";
  subnetModal.showModal();
}

async function saveSubnet() {
  const subnetId = document.getElementById("subnet-id").value;
  const payload = {
    project_id: Number(document.getElementById("subnet-project-id").value),
    name: document.getElementById("subnet-name").value,
    subnet: document.getElementById("subnet-cidr").value,
    role: document.getElementById("subnet-role").value,
    vlan_id: document.getElementById("subnet-vlan-id").value || null,
    gateway: document.getElementById("subnet-gateway").value || null,
    region: document.getElementById("subnet-region").value || null,
    floor: document.getElementById("subnet-floor").value || null,
    counterpart: document.getElementById("subnet-counterpart").value || null,
    description: document.getElementById("subnet-description").value || null,
    note: document.getElementById("subnet-note").value || null,
    allocation_type: document.getElementById("subnet-allocation-type").value || null,
    category: document.getElementById("subnet-category").value || null,
    zone: document.getElementById("subnet-zone").value || null,
    netmask: document.getElementById("subnet-netmask").value || null,
  };

  try {
    if (subnetId) {
      await apiFetch(`/api/v1/ip-subnets/${subnetId}`, { method: "PATCH", body: payload });
      showToast("대역이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/ip-subnets", { method: "POST", body: payload });
      showToast("대역이 등록되었습니다.");
    }
    subnetModal.close();
    loadSubnets();
    loadDropdowns();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── IP Modal ── */
const ipModal = document.getElementById("modal-ip");

function resetIpForm() {
  document.getElementById("ip-id").value = "";
  document.getElementById("ip-address").value = "";
  document.getElementById("ip-type").value = "service";
  document.getElementById("ip-interface").value = "";
  document.getElementById("ip-subnet-id").value = "";
  document.getElementById("ip-note").value = "";
  document.getElementById("ip-zone").value = "";
  document.getElementById("ip-service-name").value = "";
  document.getElementById("ip-hostname").value = "";
  document.getElementById("ip-vlan-id").value = "";
  document.getElementById("ip-network").value = "";
  document.getElementById("ip-netmask").value = "";
  document.getElementById("ip-gateway").value = "";
  document.getElementById("ip-dns-primary").value = "";
  document.getElementById("ip-dns-secondary").value = "";
}

function openCreateIp() {
  resetIpForm();
  document.getElementById("modal-ip-title").textContent = "IP 등록";
  document.getElementById("btn-save-ip").textContent = "등록";
  ipModal.showModal();
}

function openEditIp(ip) {
  document.getElementById("ip-id").value = ip.id;
  document.getElementById("ip-asset-id").value = ip.asset_id;
  document.getElementById("ip-subnet-id").value = ip.ip_subnet_id || "";
  document.getElementById("ip-address").value = ip.ip_address;
  document.getElementById("ip-type").value = ip.ip_type;
  document.getElementById("ip-interface").value = ip.interface_name || "";
  document.getElementById("ip-note").value = ip.note || "";
  document.getElementById("ip-zone").value = ip.zone || "";
  document.getElementById("ip-service-name").value = ip.service_name || "";
  document.getElementById("ip-hostname").value = ip.hostname || "";
  document.getElementById("ip-vlan-id").value = ip.vlan_id || "";
  document.getElementById("ip-network").value = ip.network || "";
  document.getElementById("ip-netmask").value = ip.netmask || "";
  document.getElementById("ip-gateway").value = ip.gateway || "";
  document.getElementById("ip-dns-primary").value = ip.dns_primary || "";
  document.getElementById("ip-dns-secondary").value = ip.dns_secondary || "";
  document.getElementById("modal-ip-title").textContent = "IP 수정";
  document.getElementById("btn-save-ip").textContent = "저장";
  ipModal.showModal();
}

async function saveIp() {
  const ipId = document.getElementById("ip-id").value;
  const subnetVal = document.getElementById("ip-subnet-id").value;
  const payload = {
    asset_id: Number(document.getElementById("ip-asset-id").value),
    ip_subnet_id: subnetVal ? Number(subnetVal) : null,
    ip_address: document.getElementById("ip-address").value,
    ip_type: document.getElementById("ip-type").value,
    interface_name: document.getElementById("ip-interface").value || null,
    is_primary: false,
    note: document.getElementById("ip-note").value || null,
    zone: document.getElementById("ip-zone").value || null,
    service_name: document.getElementById("ip-service-name").value || null,
    hostname: document.getElementById("ip-hostname").value || null,
    vlan_id: document.getElementById("ip-vlan-id").value || null,
    network: document.getElementById("ip-network").value || null,
    netmask: document.getElementById("ip-netmask").value || null,
    gateway: document.getElementById("ip-gateway").value || null,
    dns_primary: document.getElementById("ip-dns-primary").value || null,
    dns_secondary: document.getElementById("ip-dns-secondary").value || null,
  };

  try {
    if (ipId) {
      await apiFetch(`/api/v1/asset-ips/${ipId}`, { method: "PATCH", body: payload });
      showToast("IP가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/asset-ips", { method: "POST", body: payload });
      showToast("IP가 등록되었습니다.");
    }
    ipModal.close();
    loadIps();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteSubnet(subnet) {
  confirmDelete(
    `대역 "${subnet.name}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/ip-subnets/${subnet.id}`, { method: "DELETE" });
        showToast("대역이 삭제되었습니다.");
        loadSubnets();
        loadDropdowns();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

async function deleteIp(ip) {
  confirmDelete(
    `IP "${ip.ip_address}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/asset-ips/${ip.id}`, { method: "DELETE" });
        showToast("IP가 삭제되었습니다.");
        loadIps();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrids);
document.getElementById("btn-add-subnet").addEventListener("click", openCreateSubnet);
document.getElementById("btn-cancel-subnet").addEventListener("click", () => subnetModal.close());
document.getElementById("btn-save-subnet").addEventListener("click", saveSubnet);
document.getElementById("btn-add-ip").addEventListener("click", openCreateIp);
document.getElementById("btn-cancel-ip").addEventListener("click", () => ipModal.close());
document.getElementById("btn-save-ip").addEventListener("click", saveIp);


// ============================================
// FILE: app/static/js/partners.js
// ============================================
/* ── 업체 / 담당자 ── */

const PARTNER_TYPE_MAP = {
  client: "고객사",
  vendor: "공급사",
  maintenance: "유지보수사",
  telecom: "통신사",
  other: "기타",
};

/* ── Partner Grid ── */
const partnerColDefs = [
  { field: "partner_name", headerName: "업체명", flex: 1, minWidth: 180, sort: "asc" },
  {
    field: "partner_type",
    headerName: "유형",
    width: 110,
    valueFormatter: (p) => PARTNER_TYPE_MAP[p.value] || p.value,
  },
  { field: "contact_phone", headerName: "대표 연락처", width: 150 },
  { field: "address", headerName: "주소", width: 200 },
  { field: "business_no", headerName: "사업자번호", width: 130 },
  { field: "note", headerName: "비고", width: 200 },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "gap-sm";
      span.style.display = "inline-flex";
      const editBtn = document.createElement("button");
      editBtn.className = "btn btn-xs btn-secondary";
      editBtn.textContent = "수정";
      editBtn.addEventListener("click", () => openEditPartner(params.data));
      const delBtn = document.createElement("button");
      delBtn.className = "btn btn-xs btn-danger";
      delBtn.textContent = "삭제";
      delBtn.addEventListener("click", () => deletePartner(params.data));
      span.appendChild(editBtn);
      span.appendChild(delBtn);
      return span;
    },
    sortable: false,
    filter: false,
  },
];

let partnerGridApi;

/* ── Contact Grid ── */
const contactColDefs = [
  { field: "name", headerName: "이름", width: 120, sort: "asc" },
  { field: "partner_id", headerName: "업체 ID", width: 90 },
  { field: "department", headerName: "부서", width: 120 },
  { field: "title", headerName: "직함", width: 120 },
  { field: "role", headerName: "역할", width: 130 },
  { field: "email", headerName: "이메일", width: 200 },
  { field: "phone", headerName: "전화번호", width: 140 },
  { field: "emergency_phone", headerName: "비상연락처", width: 140 },
  { field: "note", headerName: "비고", flex: 1, minWidth: 140 },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "gap-sm";
      span.style.display = "inline-flex";
      const editBtn = document.createElement("button");
      editBtn.className = "btn btn-xs btn-secondary";
      editBtn.textContent = "수정";
      editBtn.addEventListener("click", () => openEditContact(params.data));
      const delBtn = document.createElement("button");
      delBtn.className = "btn btn-xs btn-danger";
      delBtn.textContent = "삭제";
      delBtn.addEventListener("click", () => deleteContact(params.data));
      span.appendChild(editBtn);
      span.appendChild(delBtn);
      return span;
    },
    sortable: false,
    filter: false,
  },
];

let contactGridApi;

/* ── Data Loading ── */
async function loadPartners() {
  try {
    const data = await apiFetch("/api/v1/partners");
    partnerGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadContacts() {
  try {
    const data = await apiFetch("/api/v1/contacts");
    contactGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadDropdowns() {
  try {
    const [projects, partners] = await Promise.all([
      apiFetch("/api/v1/projects"),
      apiFetch("/api/v1/partners"),
    ]);

    const projSelect = document.getElementById("partner-project-id");
    // keep first "프로젝트 무관" option
    while (projSelect.options.length > 1) projSelect.remove(1);
    projects.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.project_code + " - " + p.project_name;
      projSelect.appendChild(opt);
    });

    const partnerSelect = document.getElementById("contact-partner-id");
    while (partnerSelect.firstChild) partnerSelect.removeChild(partnerSelect.firstChild);
    partners.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.partner_name;
      partnerSelect.appendChild(opt);
    });
  } catch (err) {
    showToast("드롭다운을 불러올 수 없습니다.", "error");
  }
}

function initGrids() {
  partnerGridApi = agGrid.createGrid(document.getElementById("grid-partners"), {
    columnDefs: partnerColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  contactGridApi = agGrid.createGrid(document.getElementById("grid-contacts"), {
    columnDefs: contactColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  loadPartners();
  loadContacts();
  loadDropdowns();
}

/* ── Partner Modal ── */
const partnerModal = document.getElementById("modal-partner");

function resetPartnerForm() {
  document.getElementById("partner-id").value = "";
  document.getElementById("partner-project-id").value = "";
  document.getElementById("partner-name").value = "";
  document.getElementById("partner-type").value = "client";
  document.getElementById("partner-phone").value = "";
  document.getElementById("partner-address").value = "";
  document.getElementById("partner-business-no").value = "";
  document.getElementById("partner-note").value = "";
}

function openCreatePartner() {
  resetPartnerForm();
  document.getElementById("modal-partner-title").textContent = "업체 등록";
  document.getElementById("btn-save-partner").textContent = "등록";
  partnerModal.showModal();
}

function openEditPartner(partner) {
  document.getElementById("partner-id").value = partner.id;
  document.getElementById("partner-project-id").value = partner.project_id || "";
  document.getElementById("partner-name").value = partner.partner_name;
  document.getElementById("partner-type").value = partner.partner_type;
  document.getElementById("partner-phone").value = partner.contact_phone || "";
  document.getElementById("partner-address").value = partner.address || "";
  document.getElementById("partner-business-no").value = partner.business_no || "";
  document.getElementById("partner-note").value = partner.note || "";
  document.getElementById("modal-partner-title").textContent = "업체 수정";
  document.getElementById("btn-save-partner").textContent = "저장";
  partnerModal.showModal();
}

async function savePartner() {
  const partnerId = document.getElementById("partner-id").value;
  const projVal = document.getElementById("partner-project-id").value;
  const payload = {
    project_id: projVal ? Number(projVal) : null,
    partner_name: document.getElementById("partner-name").value,
    partner_type: document.getElementById("partner-type").value,
    contact_phone: document.getElementById("partner-phone").value || null,
    address: document.getElementById("partner-address").value || null,
    business_no: document.getElementById("partner-business-no").value || null,
    note: document.getElementById("partner-note").value || null,
  };

  try {
    if (partnerId) {
      await apiFetch(`/api/v1/partners/${partnerId}`, { method: "PATCH", body: payload });
      showToast("업체가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/partners", { method: "POST", body: payload });
      showToast("업체가 등록되었습니다.");
    }
    partnerModal.close();
    loadPartners();
    loadDropdowns();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Contact Modal ── */
const contactModal = document.getElementById("modal-contact");

function resetContactForm() {
  document.getElementById("contact-id").value = "";
  document.getElementById("contact-name").value = "";
  document.getElementById("contact-department").value = "";
  document.getElementById("contact-title").value = "";
  document.getElementById("contact-role").value = "";
  document.getElementById("contact-email").value = "";
  document.getElementById("contact-phone").value = "";
  document.getElementById("contact-emergency-phone").value = "";
  document.getElementById("contact-note").value = "";
}

function openCreateContact() {
  resetContactForm();
  document.getElementById("modal-contact-title").textContent = "담당자 등록";
  document.getElementById("btn-save-contact").textContent = "등록";
  contactModal.showModal();
}

function openEditContact(contact) {
  document.getElementById("contact-id").value = contact.id;
  document.getElementById("contact-partner-id").value = contact.partner_id;
  document.getElementById("contact-name").value = contact.name;
  document.getElementById("contact-department").value = contact.department || "";
  document.getElementById("contact-title").value = contact.title || "";
  document.getElementById("contact-role").value = contact.role || "";
  document.getElementById("contact-email").value = contact.email || "";
  document.getElementById("contact-phone").value = contact.phone || "";
  document.getElementById("contact-emergency-phone").value = contact.emergency_phone || "";
  document.getElementById("contact-note").value = contact.note || "";
  document.getElementById("modal-contact-title").textContent = "담당자 수정";
  document.getElementById("btn-save-contact").textContent = "저장";
  contactModal.showModal();
}

async function saveContact() {
  const contactId = document.getElementById("contact-id").value;
  const payload = {
    partner_id: Number(document.getElementById("contact-partner-id").value),
    name: document.getElementById("contact-name").value,
    department: document.getElementById("contact-department").value || null,
    title: document.getElementById("contact-title").value || null,
    role: document.getElementById("contact-role").value || null,
    email: document.getElementById("contact-email").value || null,
    phone: document.getElementById("contact-phone").value || null,
    emergency_phone: document.getElementById("contact-emergency-phone").value || null,
    note: document.getElementById("contact-note").value || null,
  };

  try {
    if (contactId) {
      await apiFetch(`/api/v1/contacts/${contactId}`, { method: "PATCH", body: payload });
      showToast("담당자가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/contacts", { method: "POST", body: payload });
      showToast("담당자가 등록되었습니다.");
    }
    contactModal.close();
    loadContacts();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deletePartner(partner) {
  confirmDelete(
    `업체 "${partner.partner_name}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/partners/${partner.id}`, { method: "DELETE" });
        showToast("업체가 삭제되었습니다.");
        loadPartners();
        loadDropdowns();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

async function deleteContact(contact) {
  confirmDelete(
    `담당자 "${contact.name}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/contacts/${contact.id}`, { method: "DELETE" });
        showToast("담당자가 삭제되었습니다.");
        loadContacts();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrids);
document.getElementById("btn-add-partner").addEventListener("click", openCreatePartner);
document.getElementById("btn-cancel-partner").addEventListener("click", () => partnerModal.close());
document.getElementById("btn-save-partner").addEventListener("click", savePartner);
document.getElementById("btn-add-contact").addEventListener("click", openCreateContact);
document.getElementById("btn-cancel-contact").addEventListener("click", () => contactModal.close());
document.getElementById("btn-save-contact").addEventListener("click", saveContact);


// ============================================
// FILE: app/static/js/policies.js
// ============================================
/* ── 정책 관리 ── */

const ASSIGNMENT_STATUS_MAP = {
  not_checked: "미확인",
  compliant: "준수",
  non_compliant: "미준수",
  exception: "예외",
  not_applicable: "해당없음",
};

/* ── Policy Definition Grid ── */
const policyColDefs = [
  { field: "policy_code", headerName: "정책 코드", width: 130, sort: "asc" },
  { field: "policy_name", headerName: "정책명", flex: 1, minWidth: 200 },
  { field: "category", headerName: "카테고리", width: 120 },
  { field: "security_domain", headerName: "보안 도메인", width: 130 },
  {
    field: "is_active",
    headerName: "활성",
    width: 80,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "badge " + (params.value ? "badge-active" : "badge-completed");
      span.textContent = params.value ? "활성" : "비활성";
      return span;
    },
  },
  { field: "effective_from", headerName: "시행일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  { field: "effective_to", headerName: "만료일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "gap-sm";
      span.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditPolicy(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deletePolicy(params.data));
      span.appendChild(btnEdit);
      span.appendChild(btnDel);
      return span;
    },
    sortable: false,
    filter: false,
  },
];

let policyGridApi;

/* ── Policy Assignment Grid ── */
const assignColDefs = [
  { field: "policy_definition_id", headerName: "정책 ID", width: 90 },
  { field: "project_id", headerName: "프로젝트 ID", width: 110 },
  { field: "asset_id", headerName: "자산 ID", width: 90 },
  {
    field: "status",
    headerName: "상태",
    width: 100,
    cellRenderer: (params) => {
      const label = ASSIGNMENT_STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
  },
  { field: "checked_by", headerName: "확인자", width: 120 },
  { field: "checked_date", headerName: "확인일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  { field: "exception_reason", headerName: "예외 사유", flex: 1, minWidth: 160 },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "gap-sm";
      span.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditAssignment(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteAssignment(params.data));
      span.appendChild(btnEdit);
      span.appendChild(btnDel);
      return span;
    },
    sortable: false,
    filter: false,
  },
];

let assignGridApi;

/* ── Data Loading ── */
async function loadPolicies() {
  try {
    const data = await apiFetch("/api/v1/policies");
    policyGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadAssignments() {
  try {
    const data = await apiFetch("/api/v1/policy-assignments");
    assignGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadDropdowns() {
  try {
    const [projects, assets, policies] = await Promise.all([
      apiFetch("/api/v1/projects"),
      apiFetch("/api/v1/assets"),
      apiFetch("/api/v1/policies"),
    ]);

    const projSelect = document.getElementById("assignment-project-id");
    while (projSelect.firstChild) projSelect.removeChild(projSelect.firstChild);
    projects.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.project_code + " - " + p.project_name;
      projSelect.appendChild(opt);
    });

    const assetSelect = document.getElementById("assignment-asset-id");
    // keep first "전체 프로젝트" option
    while (assetSelect.options.length > 1) assetSelect.remove(1);
    assets.forEach((a) => {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = a.asset_name;
      assetSelect.appendChild(opt);
    });

    const policySelect = document.getElementById("assignment-policy-id");
    while (policySelect.firstChild) policySelect.removeChild(policySelect.firstChild);
    policies.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.policy_code + " - " + p.policy_name;
      policySelect.appendChild(opt);
    });
  } catch (err) {
    showToast("드롭다운을 불러올 수 없습니다.", "error");
  }
}

function initGrids() {
  policyGridApi = agGrid.createGrid(document.getElementById("grid-policies"), {
    columnDefs: policyColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  assignGridApi = agGrid.createGrid(document.getElementById("grid-assignments"), {
    columnDefs: assignColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  loadPolicies();
  loadAssignments();
  loadDropdowns();
}

/* ── Policy Modal ── */
const policyModal = document.getElementById("modal-policy");

function resetPolicyForm() {
  document.getElementById("policy-id").value = "";
  document.getElementById("policy-code").value = "";
  document.getElementById("policy-name").value = "";
  document.getElementById("policy-category").value = "";
  document.getElementById("policy-is-active").value = "true";
  document.getElementById("policy-effective-from").value = "";
  document.getElementById("policy-effective-to").value = "";
  document.getElementById("policy-description").value = "";
  document.getElementById("policy-security-domain").value = "";
  document.getElementById("policy-requirement").value = "";
  document.getElementById("policy-architecture-element").value = "";
  document.getElementById("policy-control-point").value = "";
  document.getElementById("policy-iso27001-ref").value = "";
  document.getElementById("policy-nist-ref").value = "";
  document.getElementById("policy-isms-p-ref").value = "";
  document.getElementById("policy-implementation-example").value = "";
  document.getElementById("policy-evidence").value = "";
}

function openCreatePolicy() {
  resetPolicyForm();
  document.getElementById("modal-policy-title").textContent = "정책 등록";
  document.getElementById("btn-save-policy").textContent = "등록";
  policyModal.showModal();
}

function openEditPolicy(policy) {
  document.getElementById("policy-id").value = policy.id;
  document.getElementById("policy-code").value = policy.policy_code;
  document.getElementById("policy-name").value = policy.policy_name;
  document.getElementById("policy-category").value = policy.category;
  document.getElementById("policy-is-active").value = String(policy.is_active);
  document.getElementById("policy-effective-from").value = policy.effective_from || "";
  document.getElementById("policy-effective-to").value = policy.effective_to || "";
  document.getElementById("policy-description").value = policy.description || "";
  document.getElementById("policy-security-domain").value = policy.security_domain || "";
  document.getElementById("policy-requirement").value = policy.requirement || "";
  document.getElementById("policy-architecture-element").value = policy.architecture_element || "";
  document.getElementById("policy-control-point").value = policy.control_point || "";
  document.getElementById("policy-iso27001-ref").value = policy.iso27001_ref || "";
  document.getElementById("policy-nist-ref").value = policy.nist_ref || "";
  document.getElementById("policy-isms-p-ref").value = policy.isms_p_ref || "";
  document.getElementById("policy-implementation-example").value = policy.implementation_example || "";
  document.getElementById("policy-evidence").value = policy.evidence || "";
  document.getElementById("modal-policy-title").textContent = "정책 수정";
  document.getElementById("btn-save-policy").textContent = "저장";
  policyModal.showModal();
}

async function savePolicy() {
  const policyId = document.getElementById("policy-id").value;
  const payload = {
    policy_code: document.getElementById("policy-code").value,
    policy_name: document.getElementById("policy-name").value,
    category: document.getElementById("policy-category").value,
    is_active: document.getElementById("policy-is-active").value === "true",
    effective_from: document.getElementById("policy-effective-from").value || null,
    effective_to: document.getElementById("policy-effective-to").value || null,
    description: document.getElementById("policy-description").value || null,
    security_domain: document.getElementById("policy-security-domain").value || null,
    requirement: document.getElementById("policy-requirement").value || null,
    architecture_element: document.getElementById("policy-architecture-element").value || null,
    control_point: document.getElementById("policy-control-point").value || null,
    iso27001_ref: document.getElementById("policy-iso27001-ref").value || null,
    nist_ref: document.getElementById("policy-nist-ref").value || null,
    isms_p_ref: document.getElementById("policy-isms-p-ref").value || null,
    implementation_example: document.getElementById("policy-implementation-example").value || null,
    evidence: document.getElementById("policy-evidence").value || null,
  };

  try {
    if (policyId) {
      await apiFetch(`/api/v1/policies/${policyId}`, { method: "PATCH", body: payload });
      showToast("정책이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/policies", { method: "POST", body: payload });
      showToast("정책이 등록되었습니다.");
    }
    policyModal.close();
    loadPolicies();
    loadDropdowns();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Assignment Modal ── */
const assignModal = document.getElementById("modal-assignment");

function resetAssignmentForm() {
  document.getElementById("assignment-id").value = "";
  document.getElementById("assignment-asset-id").value = "";
  document.getElementById("assignment-status").value = "not_checked";
  document.getElementById("assignment-checked-by").value = "";
  document.getElementById("assignment-checked-date").value = "";
  document.getElementById("assignment-exception-reason").value = "";
  document.getElementById("assignment-evidence-note").value = "";
}

function openCreateAssignment() {
  resetAssignmentForm();
  document.getElementById("modal-assignment-title").textContent = "정책 적용 등록";
  document.getElementById("btn-save-assignment").textContent = "등록";
  assignModal.showModal();
}

function openEditAssignment(assign) {
  document.getElementById("assignment-id").value = assign.id;
  document.getElementById("assignment-project-id").value = assign.project_id;
  document.getElementById("assignment-policy-id").value = assign.policy_definition_id;
  document.getElementById("assignment-asset-id").value = assign.asset_id || "";
  document.getElementById("assignment-status").value = assign.status;
  document.getElementById("assignment-checked-by").value = assign.checked_by || "";
  document.getElementById("assignment-checked-date").value = assign.checked_date || "";
  document.getElementById("assignment-exception-reason").value = assign.exception_reason || "";
  document.getElementById("assignment-evidence-note").value = assign.evidence_note || "";
  document.getElementById("modal-assignment-title").textContent = "정책 적용 수정";
  document.getElementById("btn-save-assignment").textContent = "저장";
  assignModal.showModal();
}

async function saveAssignment() {
  const assignId = document.getElementById("assignment-id").value;
  const assetVal = document.getElementById("assignment-asset-id").value;
  const payload = {
    project_id: Number(document.getElementById("assignment-project-id").value),
    policy_definition_id: Number(document.getElementById("assignment-policy-id").value),
    asset_id: assetVal ? Number(assetVal) : null,
    status: document.getElementById("assignment-status").value,
    checked_by: document.getElementById("assignment-checked-by").value || null,
    checked_date: document.getElementById("assignment-checked-date").value || null,
    exception_reason: document.getElementById("assignment-exception-reason").value || null,
    evidence_note: document.getElementById("assignment-evidence-note").value || null,
  };

  try {
    if (assignId) {
      await apiFetch(`/api/v1/policy-assignments/${assignId}`, { method: "PATCH", body: payload });
      showToast("정책 적용이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/policy-assignments", { method: "POST", body: payload });
      showToast("정책 적용이 등록되었습니다.");
    }
    assignModal.close();
    loadAssignments();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deletePolicy(policy) {
  confirmDelete(
    `정책 "${policy.policy_name}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/policies/${policy.id}`, { method: "DELETE" });
        showToast("정책이 삭제되었습니다.");
        loadPolicies();
        loadDropdowns();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

async function deleteAssignment(assign) {
  confirmDelete(
    "이 정책 적용을 삭제하시겠습니까?",
    async () => {
      try {
        await apiFetch(`/api/v1/policy-assignments/${assign.id}`, { method: "DELETE" });
        showToast("정책 적용이 삭제되었습니다.");
        loadAssignments();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrids);
document.getElementById("btn-add-policy").addEventListener("click", openCreatePolicy);
document.getElementById("btn-cancel-policy").addEventListener("click", () => policyModal.close());
document.getElementById("btn-save-policy").addEventListener("click", savePolicy);
document.getElementById("btn-add-assignment").addEventListener("click", openCreateAssignment);
document.getElementById("btn-cancel-assignment").addEventListener("click", () => assignModal.close());
document.getElementById("btn-save-assignment").addEventListener("click", saveAssignment);


// ============================================
// FILE: app/static/js/port_maps.js
// ============================================
/* ── 케이블 배선도 (Port Maps) ── */

const PORTMAP_STATUS_MAP = {
  required: "필요",
  open: "오픈",
  closed: "차단",
  pending: "대기",
};

const columnDefs = [
  { field: "seq", headerName: "순번", width: 70 },
  { field: "cable_no", headerName: "케이블번호", width: 110 },
  { field: "connection_type", headerName: "연결유형", width: 110 },
  { field: "src_hostname", headerName: "출발 호스트", width: 130 },
  { field: "src_port_name", headerName: "출발 포트", width: 100 },
  { field: "src_zone", headerName: "출발 존", width: 90 },
  { field: "dst_hostname", headerName: "도착 호스트", width: 130 },
  { field: "dst_port_name", headerName: "도착 포트", width: 100 },
  { field: "dst_zone", headerName: "도착 존", width: 90 },
  { field: "cable_type", headerName: "케이블종류", width: 100 },
  { field: "cable_speed", headerName: "속도", width: 80 },
  { field: "purpose", headerName: "용도", flex: 1, minWidth: 120 },
  {
    field: "status",
    headerName: "상태",
    width: 80,
    cellRenderer: (params) => {
      const label = PORTMAP_STATUS_MAP[params.value] || params.value;
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
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditModal(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deletePortMap(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
    sortable: false,
    filter: false,
  },
];

let gridApi;
let currentProjectId = null;

/* ── Data Loading ── */

async function loadPortMaps() {
  if (!currentProjectId) {
    gridApi.setGridOption("rowData", []);
    return;
  }
  try {
    const data = await apiFetch(`/api/v1/projects/${currentProjectId}/port-maps`);
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadProjects() {
  try {
    const projects = await apiFetch("/api/v1/projects");
    const filterSelect = document.getElementById("filter-project");
    const modalSelect = document.getElementById("portmap-project-id");

    // Clear existing options (keep placeholder for filter)
    while (filterSelect.options.length > 1) filterSelect.remove(1);
    while (modalSelect.firstChild) modalSelect.removeChild(modalSelect.firstChild);

    projects.forEach((p) => {
      const text = p.project_code + " - " + p.project_name;

      const opt1 = document.createElement("option");
      opt1.value = p.id;
      opt1.textContent = text;
      filterSelect.appendChild(opt1);

      const opt2 = document.createElement("option");
      opt2.value = p.id;
      opt2.textContent = text;
      modalSelect.appendChild(opt2);
    });

    // Auto-select first project if available
    if (projects.length > 0) {
      filterSelect.value = projects[0].id;
      currentProjectId = projects[0].id;
      loadPortMaps();
    }
  } catch (err) {
    showToast("프로젝트를 불러올 수 없습니다.", "error");
  }
}

function initGrid() {
  gridApi = agGrid.createGrid(document.getElementById("grid-portmaps"), {
    columnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });
  loadProjects();
}

/* ── Field Helpers ── */

// All text/number input fields in the modal (id -> payload key)
const TEXT_FIELDS = [
  ["portmap-seq", "seq", "number"],
  ["portmap-cable-no", "cable_no", "text"],
  ["portmap-cable-request", "cable_request", "text"],
  ["portmap-purpose", "purpose", "text"],
  ["portmap-summary", "summary", "text"],
  // src
  ["portmap-src-mid", "src_mid", "text"],
  ["portmap-src-rack-no", "src_rack_no", "text"],
  ["portmap-src-rack-unit", "src_rack_unit", "text"],
  ["portmap-src-vendor", "src_vendor", "text"],
  ["portmap-src-model", "src_model", "text"],
  ["portmap-src-hostname", "src_hostname", "text"],
  ["portmap-src-cluster", "src_cluster", "text"],
  ["portmap-src-slot", "src_slot", "text"],
  ["portmap-src-port-name", "src_port_name", "text"],
  ["portmap-src-service-name", "src_service_name", "text"],
  ["portmap-src-zone", "src_zone", "text"],
  ["portmap-src-vlan", "src_vlan", "text"],
  ["portmap-src-ip", "src_ip", "text"],
  // dst
  ["portmap-dst-mid", "dst_mid", "text"],
  ["portmap-dst-rack-no", "dst_rack_no", "text"],
  ["portmap-dst-rack-unit", "dst_rack_unit", "text"],
  ["portmap-dst-vendor", "dst_vendor", "text"],
  ["portmap-dst-model", "dst_model", "text"],
  ["portmap-dst-hostname", "dst_hostname", "text"],
  ["portmap-dst-cluster", "dst_cluster", "text"],
  ["portmap-dst-slot", "dst_slot", "text"],
  ["portmap-dst-port-name", "dst_port_name", "text"],
  ["portmap-dst-service-name", "dst_service_name", "text"],
  ["portmap-dst-zone", "dst_zone", "text"],
  ["portmap-dst-vlan", "dst_vlan", "text"],
  ["portmap-dst-ip", "dst_ip", "text"],
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

  // Reset project to current filter selection
  const projSelect = document.getElementById("portmap-project-id");
  if (currentProjectId) projSelect.value = currentProjectId;

  // Reset text/number fields
  TEXT_FIELDS.forEach(([elId]) => {
    document.getElementById(elId).value = "";
  });

  // Reset selects to defaults
  SELECT_FIELDS.forEach(([elId, , defaultVal]) => {
    document.getElementById(elId).value = defaultVal;
  });

  document.getElementById("portmap-note").value = "";
}

function openCreateModal() {
  resetForm();
  document.getElementById("modal-portmap-title").textContent = "배선 등록";
  document.getElementById("btn-save-portmap").textContent = "등록";
  modal.showModal();
}

function openEditModal(pm) {
  document.getElementById("portmap-id").value = pm.id;
  document.getElementById("portmap-project-id").value = pm.project_id;

  // Populate text/number fields
  TEXT_FIELDS.forEach(([elId, key, type]) => {
    const val = pm[key];
    document.getElementById(elId).value = val != null ? val : "";
  });

  // Populate selects
  SELECT_FIELDS.forEach(([elId, key, defaultVal]) => {
    document.getElementById(elId).value = pm[key] || defaultVal;
  });

  document.getElementById("portmap-note").value = pm.note || "";

  document.getElementById("modal-portmap-title").textContent = "배선 수정";
  document.getElementById("btn-save-portmap").textContent = "저장";
  modal.showModal();
}

async function savePortMap() {
  const pmId = document.getElementById("portmap-id").value;
  const payload = {
    project_id: Number(document.getElementById("portmap-project-id").value),
    // Legacy fields set to null
    protocol: null,
    port: null,
    src_asset_id: null,
    dst_asset_id: null,
  };

  // Collect text/number fields
  TEXT_FIELDS.forEach(([elId, key, type]) => {
    const raw = document.getElementById(elId).value.trim();
    if (type === "number") {
      payload[key] = raw ? Number(raw) : null;
    } else {
      payload[key] = raw || null;
    }
  });

  // Collect select fields
  SELECT_FIELDS.forEach(([elId, key]) => {
    const raw = document.getElementById(elId).value;
    payload[key] = raw || null;
  });

  payload.note = document.getElementById("portmap-note").value.trim() || null;

  try {
    if (pmId) {
      await apiFetch(`/api/v1/port-maps/${pmId}`, { method: "PATCH", body: payload });
      showToast("배선이 수정되었습니다.");
    } else {
      const projId = payload.project_id;
      await apiFetch(`/api/v1/projects/${projId}/port-maps`, { method: "POST", body: payload });
      showToast("배선이 등록되었습니다.");
    }
    modal.close();
    loadPortMaps();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deletePortMap(pm) {
  confirmDelete(
    "이 배선을 삭제하시겠습니까?",
    async () => {
      try {
        await apiFetch(`/api/v1/port-maps/${pm.id}`, { method: "DELETE" });
        showToast("배선이 삭제되었습니다.");
        loadPortMaps();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-add-portmap").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-portmap").addEventListener("click", () => modal.close());
document.getElementById("btn-save-portmap").addEventListener("click", savePortMap);
document.getElementById("filter-project").addEventListener("change", (e) => {
  currentProjectId = e.target.value ? Number(e.target.value) : null;
  loadPortMaps();
});


// ============================================
// FILE: app/static/js/project_detail.js
// ============================================
/* ── 프로젝트 상세 (단계 + 산출물) ── */

const PROJECT_ID = window.__PROJECT_ID__;

const PHASE_TYPE_MAP = {
  analysis: "분석",
  design: "설계",
  build: "구축",
  test: "시험",
  stabilize: "안정화",
};

const PHASE_STATUS_MAP = {
  not_started: "미시작",
  in_progress: "진행중",
  completed: "완료",
};

/* ── 프로젝트 기본 정보 ── */
async function loadProjectInfo() {
  try {
    const p = await apiFetch(`/api/v1/projects/${PROJECT_ID}`);
    document.getElementById("project-title").textContent =
      p.project_code + " - " + p.project_name;

    const info = document.getElementById("project-info");
    while (info.firstChild) info.removeChild(info.firstChild);

    const items = [
      ["고객사", p.client_name],
      ["상태", p.status],
      ["시작일", fmtDate(p.start_date) || "-"],
      ["종료일", fmtDate(p.end_date) || "-"],
      ["설명", p.description || "-"],
    ];

    const dl = document.createElement("dl");
    dl.className = "info-grid";
    items.forEach(([label, value]) => {
      const dt = document.createElement("dt");
      dt.textContent = label;
      const dd = document.createElement("dd");
      dd.textContent = value;
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
    info.appendChild(dl);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── 단계 Grid ── */
const phaseColDefs = [
  {
    field: "phase_type",
    headerName: "단계",
    width: 120,
    valueFormatter: (p) => PHASE_TYPE_MAP[p.value] || p.value,
  },
  {
    field: "status",
    headerName: "상태",
    width: 100,
    cellRenderer: (params) => {
      const label = PHASE_STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
  },
  { field: "task_scope", headerName: "업무 범위", flex: 1, minWidth: 200 },
  { field: "deliverables_note", headerName: "산출물 메모", width: 200 },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm";
      wrap.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditPhase(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deletePhase(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
    sortable: false,
    filter: false,
  },
];

let phaseGridApi;
let phases = [];

async function loadPhases() {
  try {
    phases = await apiFetch(`/api/v1/projects/${PROJECT_ID}/phases`);
    phaseGridApi.setGridOption("rowData", phases);
    populatePhaseDropdown();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function populatePhaseDropdown() {
  const select = document.getElementById("deliverable-phase-id");
  while (select.firstChild) select.removeChild(select.firstChild);
  phases.forEach((ph) => {
    const opt = document.createElement("option");
    opt.value = ph.id;
    opt.textContent = (PHASE_TYPE_MAP[ph.phase_type] || ph.phase_type);
    select.appendChild(opt);
  });
}

/* ── 산출물 Grid ── */
const deliverableColDefs = [
  {
    field: "project_phase_id",
    headerName: "단계",
    width: 100,
    valueFormatter: (params) => {
      const ph = phases.find((p) => p.id === params.value);
      return ph ? (PHASE_TYPE_MAP[ph.phase_type] || ph.phase_type) : params.value;
    },
  },
  { field: "name", headerName: "산출물명", flex: 1, minWidth: 200 },
  {
    field: "is_submitted",
    headerName: "제출",
    width: 80,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "badge " + (params.value ? "badge-active" : "badge-planned");
      span.textContent = params.value ? "제출" : "미제출";
      return span;
    },
  },
  { field: "submitted_at", headerName: "제출일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  { field: "description", headerName: "설명", width: 200 },
  { field: "note", headerName: "비고", width: 150 },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm";
      wrap.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditDeliverable(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteDeliverable(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
    sortable: false,
    filter: false,
  },
];

let deliverableGridApi;

async function loadDeliverables() {
  try {
    const allDeliverables = [];
    for (const ph of phases) {
      const items = await apiFetch(`/api/v1/project-phases/${ph.id}/deliverables`);
      allDeliverables.push(...items);
    }
    deliverableGridApi.setGridOption("rowData", allDeliverables);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Init ── */
function initGrids() {
  phaseGridApi = agGrid.createGrid(document.getElementById("grid-phases"), {
    columnDefs: phaseColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  deliverableGridApi = agGrid.createGrid(document.getElementById("grid-deliverables"), {
    columnDefs: deliverableColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  loadProjectInfo();
  loadPhases().then(() => loadDeliverables());
}

/* ── Phase Modal ── */
const phaseModal = document.getElementById("modal-phase");

function resetPhaseForm() {
  document.getElementById("phase-id").value = "";
  document.getElementById("phase-type").value = "analysis";
  document.getElementById("phase-status").value = "not_started";
  document.getElementById("phase-task-scope").value = "";
  document.getElementById("phase-deliverables-note").value = "";
  document.getElementById("phase-cautions").value = "";
}

function openCreatePhase() {
  resetPhaseForm();
  document.getElementById("modal-phase-title").textContent = "단계 등록";
  document.getElementById("btn-save-phase").textContent = "등록";
  phaseModal.showModal();
}

function openEditPhase(phase) {
  document.getElementById("phase-id").value = phase.id;
  document.getElementById("phase-type").value = phase.phase_type;
  document.getElementById("phase-status").value = phase.status;
  document.getElementById("phase-task-scope").value = phase.task_scope || "";
  document.getElementById("phase-deliverables-note").value = phase.deliverables_note || "";
  document.getElementById("phase-cautions").value = phase.cautions || "";
  document.getElementById("modal-phase-title").textContent = "단계 수정";
  document.getElementById("btn-save-phase").textContent = "저장";
  phaseModal.showModal();
}

async function savePhase() {
  const phaseId = document.getElementById("phase-id").value;
  const payload = {
    project_id: PROJECT_ID,
    phase_type: document.getElementById("phase-type").value,
    status: document.getElementById("phase-status").value,
    task_scope: document.getElementById("phase-task-scope").value || null,
    deliverables_note: document.getElementById("phase-deliverables-note").value || null,
    cautions: document.getElementById("phase-cautions").value || null,
  };

  try {
    if (phaseId) {
      await apiFetch(`/api/v1/project-phases/${phaseId}`, { method: "PATCH", body: payload });
      showToast("단계가 수정되었습니다.");
    } else {
      await apiFetch(`/api/v1/projects/${PROJECT_ID}/phases`, { method: "POST", body: payload });
      showToast("단계가 등록되었습니다.");
    }
    phaseModal.close();
    await loadPhases();
    loadDeliverables();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deletePhase(phase) {
  const label = PHASE_TYPE_MAP[phase.phase_type] || phase.phase_type;
  confirmDelete(
    `"${label}" 단계를 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/project-phases/${phase.id}`, { method: "DELETE" });
        showToast("단계가 삭제되었습니다.");
        await loadPhases();
        loadDeliverables();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Deliverable Modal ── */
const deliverableModal = document.getElementById("modal-deliverable");

function resetDeliverableForm() {
  document.getElementById("deliverable-id").value = "";
  document.getElementById("deliverable-name").value = "";
  document.getElementById("deliverable-is-submitted").value = "false";
  document.getElementById("deliverable-submitted-at").value = "";
  document.getElementById("deliverable-description").value = "";
  document.getElementById("deliverable-note").value = "";
}

function openCreateDeliverable() {
  resetDeliverableForm();
  document.getElementById("modal-deliverable-title").textContent = "산출물 등록";
  document.getElementById("btn-save-deliverable").textContent = "등록";
  deliverableModal.showModal();
}

function openEditDeliverable(d) {
  document.getElementById("deliverable-id").value = d.id;
  document.getElementById("deliverable-phase-id").value = d.project_phase_id;
  document.getElementById("deliverable-name").value = d.name;
  document.getElementById("deliverable-is-submitted").value = String(d.is_submitted);
  document.getElementById("deliverable-submitted-at").value = d.submitted_at || "";
  document.getElementById("deliverable-description").value = d.description || "";
  document.getElementById("deliverable-note").value = d.note || "";
  document.getElementById("modal-deliverable-title").textContent = "산출물 수정";
  document.getElementById("btn-save-deliverable").textContent = "저장";
  deliverableModal.showModal();
}

async function saveDeliverable() {
  const delId = document.getElementById("deliverable-id").value;
  const phaseId = document.getElementById("deliverable-phase-id").value;
  const payload = {
    project_phase_id: Number(phaseId),
    name: document.getElementById("deliverable-name").value,
    is_submitted: document.getElementById("deliverable-is-submitted").value === "true",
    submitted_at: document.getElementById("deliverable-submitted-at").value || null,
    description: document.getElementById("deliverable-description").value || null,
    note: document.getElementById("deliverable-note").value || null,
  };

  try {
    if (delId) {
      await apiFetch(`/api/v1/project-deliverables/${delId}`, { method: "PATCH", body: payload });
      showToast("산출물이 수정되었습니다.");
    } else {
      await apiFetch(`/api/v1/project-phases/${phaseId}/deliverables`, { method: "POST", body: payload });
      showToast("산출물이 등록되었습니다.");
    }
    deliverableModal.close();
    loadDeliverables();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteDeliverable(d) {
  confirmDelete(
    `산출물 "${d.name}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/project-deliverables/${d.id}`, { method: "DELETE" });
        showToast("산출물이 삭제되었습니다.");
        loadDeliverables();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrids);
document.getElementById("btn-add-phase").addEventListener("click", openCreatePhase);
document.getElementById("btn-cancel-phase").addEventListener("click", () => phaseModal.close());
document.getElementById("btn-save-phase").addEventListener("click", savePhase);
document.getElementById("btn-add-deliverable").addEventListener("click", openCreateDeliverable);
document.getElementById("btn-cancel-deliverable").addEventListener("click", () => deliverableModal.close());
document.getElementById("btn-save-deliverable").addEventListener("click", saveDeliverable);


// ============================================
// FILE: app/static/js/projects.js
// ============================================
/* ── 프로젝트 목록 ── */

const STATUS_MAP = {
  planned: "계획",
  active: "진행중",
  on_hold: "보류",
  completed: "완료",
};

const columnDefs = [
  { field: "project_code", headerName: "프로젝트 코드", width: 150, sort: "asc" },
  { field: "project_name", headerName: "프로젝트명", flex: 1, minWidth: 200 },
  { field: "client_name", headerName: "고객사", width: 180 },
  {
    field: "status",
    headerName: "상태",
    width: 100,
    cellRenderer: (params) => {
      const label = STATUS_MAP[params.value] || params.value;
      return `<span class="badge badge-${params.value}">${label}</span>`;
    },
  },
  { field: "start_date", headerName: "시작일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  { field: "end_date", headerName: "종료일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  {
    headerName: "",
    width: 120,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm";
      wrap.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditModal(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteProject(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
    sortable: false,
    filter: false,
  },
];

let gridApi;

async function loadProjects() {
  try {
    const data = await apiFetch("/api/v1/projects");
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function initGrid() {
  const gridDiv = document.getElementById("grid-projects");
  gridApi = agGrid.createGrid(gridDiv, {
    columnDefs,
    rowData: [],
    defaultColDef: {
      resizable: true,
      sortable: true,
      filter: true,
    },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    onRowDoubleClicked: (event) => {
      window.location.href = `/projects/${event.data.id}`;
    },
  });
  loadProjects();
}

/* ── Modal ── */
const modal = document.getElementById("modal-project");
const form = document.getElementById("form-project");

function resetForm() {
  document.getElementById("project-id").value = "";
  document.getElementById("project-code").value = "";
  document.getElementById("project-name").value = "";
  document.getElementById("client-name").value = "";
  document.getElementById("project-status").value = "planned";
  document.getElementById("start-date").value = "";
  document.getElementById("end-date").value = "";
  document.getElementById("project-desc").value = "";
}

function openCreateModal() {
  resetForm();
  document.getElementById("modal-project-title").textContent = "프로젝트 등록";
  document.getElementById("btn-save-project").textContent = "등록";
  modal.showModal();
}

function openEditModal(project) {
  document.getElementById("project-id").value = project.id;
  document.getElementById("project-code").value = project.project_code;
  document.getElementById("project-name").value = project.project_name;
  document.getElementById("client-name").value = project.client_name;
  document.getElementById("project-status").value = project.status;
  document.getElementById("start-date").value = project.start_date || "";
  document.getElementById("end-date").value = project.end_date || "";
  document.getElementById("project-desc").value = project.description || "";
  document.getElementById("modal-project-title").textContent = "프로젝트 수정";
  document.getElementById("btn-save-project").textContent = "저장";
  modal.showModal();
}

async function saveProject() {
  const projectId = document.getElementById("project-id").value;
  const payload = {
    project_code: document.getElementById("project-code").value,
    project_name: document.getElementById("project-name").value,
    client_name: document.getElementById("client-name").value,
    status: document.getElementById("project-status").value,
    start_date: document.getElementById("start-date").value || null,
    end_date: document.getElementById("end-date").value || null,
    description: document.getElementById("project-desc").value || null,
  };

  try {
    if (projectId) {
      await apiFetch(`/api/v1/projects/${projectId}`, { method: "PATCH", body: payload });
      showToast("프로젝트가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/projects", { method: "POST", body: payload });
      showToast("프로젝트가 등록되었습니다.");
    }
    modal.close();
    loadProjects();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteProject(project) {
  confirmDelete(
    `프로젝트 "${project.project_name}"을(를) 삭제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/projects/${project.id}`, { method: "DELETE" });
        showToast("프로젝트가 삭제되었습니다.");
        loadProjects();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-add-project").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-project").addEventListener("click", () => modal.close());
document.getElementById("btn-save-project").addEventListener("click", saveProject);


// ============================================
// FILE: app/static/js/utils.js
// ============================================
/* ── 공통 유틸리티 ── */

/**
 * API 요청 헬퍼.
 * JSON body를 자동 직렬화하고 응답 상태를 검증한다.
 */
async function apiFetch(url, options = {}) {
  const defaults = {
    headers: { "Content-Type": "application/json" },
  };
  const merged = { ...defaults, ...options };
  if (merged.body && typeof merged.body === "object") {
    merged.body = JSON.stringify(merged.body);
  }

  const res = await fetch(url, merged);
  if (res.status === 204) return null;

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail || `HTTP ${res.status}`);
  }
  return data;
}

/**
 * 날짜 포맷 (YYYY-MM-DD).
 */
function fmtDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (isNaN(d.getTime())) return value;
  return d.toISOString().slice(0, 10);
}

/**
 * 숫자 천 단위 콤마.
 */
function fmtNumber(value) {
  if (value == null) return "";
  return Number(value).toLocaleString("ko-KR");
}

/**
 * Toast 메시지 표시 (컨테이너 + 슬라이드 애니메이션).
 */
function showToast(message, type = "success", duration = 3000) {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = "toast toast-" + type;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "toast-out 0.25s ease-in forwards";
    toast.addEventListener("animationend", () => toast.remove());
  }, duration);
}

/**
 * 현재 로그인 사용자 정보를 가져온다.
 */
async function fetchCurrentUser() {
  try {
    return await apiFetch("/api/v1/auth/me");
  } catch {
    return null;
  }
}

/**
 * 삭제 확인 다이얼로그를 표시한다.
 * @param {string} message - 확인 메시지
 * @param {Function} onConfirm - 확인 시 실행할 콜백
 */
function confirmDelete(message, onConfirm) {
  const modal = document.getElementById("modal-confirm-delete");
  const msgEl = document.getElementById("confirm-delete-message");
  const btnConfirm = document.getElementById("btn-confirm-delete");
  const btnCancel = document.getElementById("btn-cancel-delete");

  msgEl.textContent = message;

  function cleanup() {
    btnConfirm.removeEventListener("click", handleConfirm);
    btnCancel.removeEventListener("click", handleCancel);
    modal.close();
  }

  function handleConfirm() {
    cleanup();
    onConfirm();
  }

  function handleCancel() {
    cleanup();
  }

  btnConfirm.addEventListener("click", handleConfirm);
  btnCancel.addEventListener("click", handleCancel);
  modal.showModal();
}


