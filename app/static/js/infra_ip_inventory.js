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

