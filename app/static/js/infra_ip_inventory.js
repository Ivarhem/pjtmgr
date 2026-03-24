/* ── IP 인벤토리 (좌우 분할, 고객사 중심) ── */

const SUBNET_ROLE_MAP = {
  service: "서비스", management: "관리", backup: "백업", dmz: "DMZ", other: "기타",
};
const IP_TYPE_MAP = {
  service: "서비스", management: "관리", backup: "백업", vip: "VIP", other: "기타",
};

let ipGridApi;
let _subnets = [];
let _selectedSubnet = null;

/* ── IP Grid columns ── */
const ipColDefs = [
  { field: "ip_address", headerName: "IP 주소", width: 160, sort: "asc" },
  { field: "ip_type", headerName: "용도", width: 100, valueFormatter: p => IP_TYPE_MAP[p.value] || p.value },
  { field: "interface_name", headerName: "인터페이스", width: 120 },
  { field: "hostname", headerName: "호스트명", width: 130 },
  { field: "service_name", headerName: "서비스명", width: 130 },
  { field: "zone", headerName: "존", width: 100 },
  { field: "vlan_id", headerName: "VLAN", width: 80 },
  { field: "note", headerName: "비고", flex: 1, minWidth: 150 },
  {
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm infra-inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditIp(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteIp(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

/* ── Data Loading ── */

async function loadSubnets() {
  const cid = getCtxPartnerId();
  if (!cid) { _subnets = []; renderSubnetList(); return; }
  try {
    _subnets = await apiFetch("/api/v1/ip-subnets?partner_id=" + cid);
  } catch { _subnets = []; }
  renderSubnetList();
}

function renderSubnetList() {
  const container = document.getElementById("subnet-list");
  while (container.firstChild) container.removeChild(container.firstChild);

  // "전체" 항목
  const allItem = document.createElement("div");
  allItem.className = "subnet-item" + (!_selectedSubnet ? " active" : "");
  allItem.textContent = "전체 (" + _subnets.length + ")";
  allItem.addEventListener("click", () => { _selectedSubnet = null; renderSubnetList(); showSubnetDetail(null); loadIps(); });
  container.appendChild(allItem);

  _subnets.forEach(s => {
    const item = document.createElement("div");
    item.className = "subnet-item" + (_selectedSubnet && _selectedSubnet.id === s.id ? " active" : "");
    const name = document.createElement("div");
    name.className = "subnet-item-name";
    name.textContent = s.name;
    const sub = document.createElement("div");
    sub.className = "subnet-item-sub";
    sub.textContent = s.subnet + (s.vlan_id ? " (VLAN " + s.vlan_id + ")" : "");
    item.appendChild(name);
    item.appendChild(sub);
    item.addEventListener("click", () => { _selectedSubnet = s; renderSubnetList(); showSubnetDetail(s); loadIps(); });
    container.appendChild(item);
  });
}

function showSubnetDetail(subnet) {
  const card = document.getElementById("subnet-detail-card");
  if (!subnet) { card.classList.add("hidden"); return; }
  card.classList.remove("hidden");
  document.getElementById("subnet-detail-name").textContent = subnet.name + " (" + subnet.subnet + ")";

  const fields = document.getElementById("subnet-detail-fields");
  while (fields.firstChild) fields.removeChild(fields.firstChild);
  const pairs = [
    ["역할", SUBNET_ROLE_MAP[subnet.role] || subnet.role],
    ["VLAN", subnet.vlan_id], ["게이트웨이", subnet.gateway],
    ["지역", subnet.region], ["층", subnet.floor],
    ["상대국", subnet.counterpart], ["존", subnet.zone],
    ["넷마스크", subnet.netmask], ["할당유형", subnet.allocation_type],
  ];
  pairs.forEach(([label, val]) => {
    const dt = document.createElement("dt");
    dt.textContent = label;
    const dd = document.createElement("dd");
    dd.textContent = val || "—";
    fields.appendChild(dt);
    fields.appendChild(dd);
  });
}

async function loadIps() {
  const cid = getCtxPartnerId();
  if (!cid) { ipGridApi.setGridOption("rowData", []); return; }
  try {
    const data = await apiFetch("/api/v1/ip-inventory?partner_id=" + cid);
    if (_selectedSubnet) {
      ipGridApi.setGridOption("rowData", data.filter(ip => ip.ip_subnet_id === _selectedSubnet.id));
    } else {
      ipGridApi.setGridOption("rowData", data);
    }
  } catch (err) { showToast(err.message, "error"); }
}

async function loadDropdowns() {
  const cid = getCtxPartnerId();
  if (!cid) return;
  try {
    const [assets, subnets] = await Promise.all([
      apiFetch("/api/v1/assets?partner_id=" + cid),
      apiFetch("/api/v1/ip-subnets?partner_id=" + cid),
    ]);

    const assetSelect = document.getElementById("ip-asset-id");
    while (assetSelect.firstChild) assetSelect.removeChild(assetSelect.firstChild);
    assets.forEach(a => {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = a.asset_name;
      assetSelect.appendChild(opt);
    });

    const subnetSelect = document.getElementById("ip-subnet-id");
    while (subnetSelect.options.length > 1) subnetSelect.remove(1);
    subnets.forEach(s => {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name + " (" + s.subnet + ")";
      subnetSelect.appendChild(opt);
    });
  } catch { /* ignore */ }
}

function initPage() {
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
  document.getElementById("form-subnet").reset();
}

function openCreateSubnet() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  resetSubnetForm();
  document.getElementById("modal-subnet-title").textContent = "대역 등록";
  document.getElementById("btn-save-subnet").textContent = "등록";
  subnetModal.showModal();
}

function openEditSubnet(subnet) {
  if (!subnet) subnet = _selectedSubnet;
  if (!subnet) return;
  document.getElementById("subnet-id").value = subnet.id;
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
  const cid = getCtxPartnerId();
  if (!cid) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const subnetId = document.getElementById("subnet-id").value;
  const payload = {
    partner_id: cid,
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
      await apiFetch("/api/v1/ip-subnets/" + subnetId, { method: "PATCH", body: payload });
      showToast("대역이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/ip-subnets", { method: "POST", body: payload });
      showToast("대역이 등록되었습니다.");
    }
    subnetModal.close();
    _selectedSubnet = null;
    loadSubnets();
    loadDropdowns();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteSubnet(subnet) {
  if (!subnet) subnet = _selectedSubnet;
  if (!subnet) return;
  confirmDelete(
    '대역 "' + subnet.name + '"을(를) 삭제하시겠습니까?',
    async () => {
      try {
        await apiFetch("/api/v1/ip-subnets/" + subnet.id, { method: "DELETE" });
        showToast("대역이 삭제되었습니다.");
        _selectedSubnet = null;
        loadSubnets();
        loadIps();
        loadDropdowns();
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

/* ── IP Modal ── */
const ipModal = document.getElementById("modal-ip");

function resetIpForm() {
  document.getElementById("ip-id").value = "";
  document.getElementById("form-ip").reset();
}

function openCreateIp() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
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
      await apiFetch("/api/v1/asset-ips/" + ipId, { method: "PATCH", body: payload });
      showToast("IP가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/asset-ips", { method: "POST", body: payload });
      showToast("IP가 등록되었습니다.");
    }
    ipModal.close();
    loadIps();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteIp(ip) {
  confirmDelete(
    'IP "' + ip.ip_address + '"을(를) 삭제하시겠습니까?',
    async () => {
      try {
        await apiFetch("/api/v1/asset-ips/" + ip.id, { method: "DELETE" });
        showToast("IP가 삭제되었습니다.");
        loadIps();
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initPage);
initProjectFilterCheckbox();
document.getElementById("btn-add-subnet").addEventListener("click", openCreateSubnet);
document.getElementById("btn-cancel-subnet").addEventListener("click", () => subnetModal.close());
document.getElementById("btn-save-subnet").addEventListener("click", saveSubnet);
document.getElementById("btn-add-ip").addEventListener("click", openCreateIp);
document.getElementById("btn-cancel-ip").addEventListener("click", () => ipModal.close());
document.getElementById("btn-save-ip").addEventListener("click", saveIp);
document.getElementById("btn-edit-subnet-detail").addEventListener("click", () => openEditSubnet());
document.getElementById("btn-delete-subnet-detail").addEventListener("click", () => deleteSubnet());

window.addEventListener("ctx-changed", () => {
  _selectedSubnet = null;
  loadSubnets();
  loadIps();
  loadDropdowns();
});
