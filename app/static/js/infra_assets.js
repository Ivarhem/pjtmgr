/* ── 자산 인벤토리 (고객사 중심) ── */

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
  { field: "asset_code", headerName: "코드", width: 120, sort: "asc" },
  {
    field: "asset_name", headerName: "자산명", flex: 1, minWidth: 180,
    cellRenderer: (params) => {
      const wrapper = document.createElement("span");
      wrapper.textContent = params.value;
      const aliases = params.data.aliases;
      if (aliases && aliases.length) {
        aliases.forEach(a => {
          const tag = document.createElement("span");
          tag.textContent = a;
          tag.className = "alias-tag";
          tag.style.cssText = "margin-left:6px;padding:1px 6px;font-size:11px;border-radius:3px;background:#e0e7ff;color:#3730a3";
          wrapper.appendChild(tag);
        });
      }
      return wrapper;
    },
  },
  {
    field: "asset_type",
    headerName: "유형",
    width: 110,
    valueFormatter: (p) => getAssetTypeLabel(p.value),
  },
  { field: "vendor", headerName: "제조사", width: 130 },
  { field: "model", headerName: "모델", width: 130 },
  { field: "hostname", headerName: "호스트명", width: 140 },
  { field: "mgmt_ip", headerName: "관리IP", width: 130 },
  { field: "zone", headerName: "존", width: 100 },
  { field: "category", headerName: "분류", width: 110 },
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
let _editMode = false;
let _currentTab = "basic";

const NUMERIC_FIELDS = ["size_unit", "lc_count", "ha_count", "utp_count", "power_count", "year_acquired"];

/* ── Data loading ── */

async function loadAssets() {
  const cid = getCtxPartnerId();
  if (!cid) {
    gridApi.setGridOption("rowData", []);
    return;
  }
  let url = "/api/v1/assets?partner_id=" + cid;
  const pid = getCtxProjectId();
  if (pid && isProjectFilterActive()) url += "&period_id=" + pid;
  const typeFilter = document.getElementById("filter-type").value;
  const statusFilter = document.getElementById("filter-status").value;
  const q = document.getElementById("filter-search").value.trim();
  if (typeFilter) url += "&asset_type=" + typeFilter;
  if (statusFilter) url += "&status=" + statusFilter;
  if (q) url += "&q=" + encodeURIComponent(q);

  try {
    const data = await apiFetch(url);
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Grid init ── */

async function initGrid() {
  await loadAssetTypeCodes();
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
    ["자산명", "asset_name"], ["유형", "asset_type", v => getAssetTypeLabel(v)],
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
  _currentTab = tab;
  if (_editMode) _editMode = false;

  const container = document.getElementById("detail-content");
  while (container.firstChild) container.removeChild(container.firstChild);

  document.querySelectorAll(".detail-tabs .tab-btn").forEach(b => {
    b.classList.toggle("active", b.dataset.dtab === tab);
  });

  if (!_selectedAsset) return;

  // Sub-entity tabs
  if (tab === "software") { renderSoftwareTab(container); return; }
  if (tab === "ip") { renderIpTab(container); return; }
  if (tab === "contacts") { renderContactsTab(container); return; }
  if (tab === "relations") { renderRelationsTab(container); return; }
  if (tab === "aliases") { renderAliasesTab(container); return; }

  const fields = DETAIL_TABS[tab];
  if (!fields) return;

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

/* ── Sub-entity tab helpers ── */

function _subTabHeader(container, title, onAdd) {
  const hdr = document.createElement("div");
  hdr.style.cssText = "display:flex;justify-content:space-between;align-items:center;margin-bottom:8px";
  const h = document.createElement("span");
  h.style.cssText = "font-size:13px;font-weight:600";
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
    p.className = "text-muted";
    p.style.fontSize = "13px";
    p.textContent = "데이터가 없습니다.";
    container.appendChild(p);
    return;
  }
  const tbl = document.createElement("table");
  tbl.style.cssText = "width:100%;font-size:12px;border-collapse:collapse";
  const thead = document.createElement("thead");
  const hr = document.createElement("tr");
  columns.forEach(c => { const th = document.createElement("th"); th.textContent = c.label; th.style.cssText = "text-align:left;padding:4px 8px;border-bottom:1px solid var(--border-color)"; hr.appendChild(th); });
  if (actions) { const th = document.createElement("th"); th.style.cssText = "width:80px;padding:4px 8px;border-bottom:1px solid var(--border-color)"; hr.appendChild(th); }
  thead.appendChild(hr);
  tbl.appendChild(thead);
  const tbody = document.createElement("tbody");
  rows.forEach(row => {
    const tr = document.createElement("tr");
    tr.style.borderBottom = "1px solid var(--border-color)";
    columns.forEach(c => {
      const td = document.createElement("td");
      td.style.cssText = "padding:4px 8px";
      const v = row[c.field];
      td.textContent = c.fmt ? c.fmt(v, row) : (v != null ? String(v) : "—");
      if (c.style) td.style.cssText += ";" + c.style;
      tr.appendChild(td);
    });
    if (actions) {
      const td = document.createElement("td");
      td.style.cssText = "padding:4px 8px;text-align:right";
      actions.forEach(a => {
        const b = document.createElement("button");
        b.className = "btn btn-sm" + (a.danger ? " btn-danger" : "");
        b.textContent = a.label;
        b.style.marginLeft = "4px";
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
    renderDetailTab("software");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteSoftware(sw) {
  confirmDelete("소프트웨어 '" + sw.software_name + "'을(를) 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-software/" + sw.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("software");
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
    renderDetailTab("ip");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteIp(ip) {
  confirmDelete("IP '" + ip.ip_address + "'을(를) 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-ips/" + ip.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("ip");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── 담당자 탭 ── */

async function renderContactsTab(container) {
  _subTabHeader(container, "담당자", () => openContactModal());
  try {
    const data = await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/contacts");
    _subTable(container, [
      { label: "담당자 ID", field: "contact_id" },
      { label: "역할", field: "role" },
    ], data, [
      { label: "수정", handler: (r) => openContactModal(r) },
      { label: "해제", danger: true, handler: (r) => deleteContact(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

function openContactModal(ct) {
  const m = document.getElementById("modal-contact");
  document.getElementById("ct-id").value = ct ? ct.id : "";
  document.getElementById("ct-contact-id").value = ct ? ct.contact_id : "";
  document.getElementById("ct-contact-id").disabled = !!ct;
  document.getElementById("ct-role").value = ct ? (ct.role || "") : "";
  m.showModal();
}

async function saveContact() {
  const ctId = document.getElementById("ct-id").value;
  const payload = {
    contact_id: Number(document.getElementById("ct-contact-id").value),
    role: document.getElementById("ct-role").value || null,
  };
  try {
    if (ctId) {
      await apiFetch("/api/v1/asset-contacts/" + ctId, { method: "PATCH", body: { role: payload.role } });
    } else {
      await apiFetch("/api/v1/assets/" + _selectedAsset.id + "/contacts", { method: "POST", body: payload });
    }
    document.getElementById("modal-contact").close();
    showToast(ctId ? "수정되었습니다." : "연결되었습니다.");
    renderDetailTab("contacts");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteContact(ct) {
  confirmDelete("담당자 연결을 해제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-contacts/" + ct.id, { method: "DELETE" });
      showToast("해제되었습니다.");
      renderDetailTab("contacts");
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
      { label: "관계 유형", field: "relation_type" },
      { label: "비고", field: "note" },
    ], data, [
      { label: "삭제", danger: true, handler: (r) => deleteRelation(r) },
    ]);
  } catch (e) { showToast(e.message, "error"); }
}

function openRelationModal() {
  const m = document.getElementById("modal-relation");
  document.getElementById("rel-id").value = "";
  document.getElementById("rel-dst-asset-id").value = "";
  document.getElementById("rel-type").value = "HOSTS";
  document.getElementById("rel-note").value = "";
  document.getElementById("modal-relation-title").textContent = "관계 추가";
  m.showModal();
}

async function saveRelation() {
  const payload = {
    src_asset_id: _selectedAsset.id,
    dst_asset_id: Number(document.getElementById("rel-dst-asset-id").value),
    relation_type: document.getElementById("rel-type").value,
    note: document.getElementById("rel-note").value || null,
  };
  try {
    await apiFetch("/api/v1/asset-relations", { method: "POST", body: payload });
    document.getElementById("modal-relation").close();
    showToast("관계가 추가되었습니다.");
    renderDetailTab("relations");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteRelation(rel) {
  confirmDelete("이 관계를 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-relations/" + rel.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("relations");
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
    renderDetailTab("aliases");
  } catch (e) { showToast(e.message, "error"); }
}

async function deleteAlias(alias) {
  confirmDelete("별칭 '" + alias.alias_name + "'을(를) 삭제하시겠습니까?", async () => {
    try {
      await apiFetch("/api/v1/asset-aliases/" + alias.id, { method: "DELETE" });
      showToast("삭제되었습니다.");
      renderDetailTab("aliases");
    } catch (e) { showToast(e.message, "error"); }
  });
}

/* ── Inline edit mode ── */

function enterEditMode(tab) {
  _editMode = true;
  const container = document.getElementById("detail-content");
  while (container.firstChild) container.removeChild(container.firstChild);

  const fields = DETAIL_TABS[tab];
  if (!fields) return;

  const form = document.createElement("form");
  form.id = "detail-edit-form";
  form.addEventListener("submit", (e) => e.preventDefault());

  const grid = document.createElement("div");
  grid.className = "detail-grid";

  fields.forEach(([label, key]) => {
    const dt = document.createElement("dt");
    dt.textContent = label;
    grid.appendChild(dt);

    const dd = document.createElement("dd");
    const currentVal = _selectedAsset[key];

    if (key === "asset_type") {
      // Read-only: 유형 변경 금지
      const span = document.createElement("span");
      span.textContent = currentVal != null ? getAssetTypeLabel(currentVal) : "—";
      span.style.color = "var(--text-color-secondary)";
      dd.appendChild(span);
    } else if (key === "status") {
      const sel = document.createElement("select");
      sel.dataset.field = key;
      sel.className = "edit-input";
      Object.entries(ASSET_STATUS_MAP).forEach(([val, lbl]) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent = lbl;
        if (val === currentVal) opt.selected = true;
        sel.appendChild(opt);
      });
      dd.appendChild(sel);
    } else if (key === "environment") {
      const sel = document.createElement("select");
      sel.dataset.field = key;
      sel.className = "edit-input";
      // 빈 옵션
      const empty = document.createElement("option");
      empty.value = "";
      empty.textContent = "—";
      sel.appendChild(empty);
      Object.entries(ENV_MAP).forEach(([val, lbl]) => {
        const opt = document.createElement("option");
        opt.value = val;
        opt.textContent = lbl;
        if (val === currentVal) opt.selected = true;
        sel.appendChild(opt);
      });
      dd.appendChild(sel);
    } else {
      const input = document.createElement("input");
      input.dataset.field = key;
      input.className = "edit-input";
      if (NUMERIC_FIELDS.includes(key)) {
        input.type = "number";
        input.value = currentVal != null ? currentVal : "";
      } else {
        input.type = "text";
        input.value = currentVal != null ? String(currentVal) : "";
      }
      dd.appendChild(input);
    }
    grid.appendChild(dd);
  });

  form.appendChild(grid);

  // 저장/취소 버튼
  const actions = document.createElement("div");
  actions.style.cssText = "display:flex;gap:8px;justify-content:flex-end;margin-top:12px;padding-top:12px;border-top:1px solid var(--border-color)";

  const cancelBtn = document.createElement("button");
  cancelBtn.type = "button";
  cancelBtn.className = "btn btn-sm btn-secondary";
  cancelBtn.textContent = "취소";
  cancelBtn.addEventListener("click", exitEditMode);

  const saveBtn = document.createElement("button");
  saveBtn.type = "button";
  saveBtn.className = "btn btn-sm btn-primary";
  saveBtn.textContent = "저장";
  saveBtn.addEventListener("click", () => saveDetailEdit(tab));

  actions.appendChild(cancelBtn);
  actions.appendChild(saveBtn);
  form.appendChild(actions);

  container.appendChild(form);
}

function exitEditMode() {
  _editMode = false;
  renderDetailTab(_currentTab);
}

async function saveDetailEdit(tab) {
  const form = document.getElementById("detail-edit-form");
  if (!form) return;
  const fields = DETAIL_TABS[tab];
  const changes = {};
  fields.forEach(([label, key]) => {
    const input = form.querySelector('[data-field="' + key + '"]');
    if (!input) return;
    const val = input.value.trim();
    const original = _selectedAsset[key];
    if (NUMERIC_FIELDS.includes(key)) {
      const numVal = val === "" ? null : Number(val);
      if (numVal !== original) changes[key] = numVal;
    } else {
      const strVal = val || null;
      if (strVal !== original) changes[key] = strVal;
    }
  });
  if (Object.keys(changes).length === 0) {
    exitEditMode();
    return;
  }
  try {
    const updated = await apiFetch("/api/v1/assets/" + _selectedAsset.id, { method: "PATCH", body: changes });
    Object.assign(_selectedAsset, updated);
    showToast("수정되었습니다.");
    exitEditMode();
    loadAssets();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function closeDetail() {
  document.getElementById("asset-detail-panel").classList.add("hidden");
  _selectedAsset = null;
}

/* ── Modal (간소화 등록) ── */
const modal = document.getElementById("modal-asset");
let _catalogSearchTimer = null;

async function openCreateModal() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }

  // Reset form
  document.getElementById("form-asset").reset();
  document.getElementById("catalog-id").value = "";
  document.getElementById("catalog-search").value = "";
  document.getElementById("catalog-summary").classList.add("hidden");
  document.getElementById("catalog-summary").textContent = "";
  document.getElementById("catalog-summary").classList.remove("placeholder-style");
  document.getElementById("catalog-dropdown").classList.add("hidden");
  document.getElementById("inline-catalog-form").classList.add("hidden");

  // 귀속사업 드롭다운 채우기
  const periodSel = document.getElementById("asset-period");
  periodSel.textContent = "";
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "-- 선택 안함 --";
  periodSel.appendChild(emptyOpt);

  try {
    const cid = getCtxPartnerId();
    const periods = await apiFetch("/api/v1/contract-periods?partner_id=" + cid);
    periods.forEach(p => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name || ("사업 #" + p.id);
      periodSel.appendChild(opt);
    });
    // topbar 프로젝트 선택 시 자동 선택
    const pid = getCtxProjectId();
    if (pid) periodSel.value = pid;
  } catch (_) { /* ignore */ }

  modal.showModal();
}

/* ── 카탈로그 검색 ── */

function renderCatalogDropdown(items) {
  const dd = document.getElementById("catalog-dropdown");
  dd.textContent = "";

  items.forEach(item => {
    const div = document.createElement("div");
    const label = (item.vendor || "") + " " + (item.name || "");
    div.textContent = label.trim();

    if (!item.asset_type_key) {
      div.className = "catalog-dropdown-item disabled";
      const warn = document.createElement("span");
      warn.textContent = " (유형 미설정)";
      warn.style.color = "var(--danger-color, #dc3545)";
      warn.style.fontSize = "12px";
      div.appendChild(warn);
    } else {
      div.className = "catalog-dropdown-item" + (item.is_placeholder ? " placeholder" : "");
      if (item.is_placeholder) div.textContent += " (placeholder)";
      div.addEventListener("click", () => selectCatalogItem(item));
    }
    dd.appendChild(div);
  });

  // 맨 아래: 새 제품 등록
  const addDiv = document.createElement("div");
  addDiv.className = "catalog-dropdown-add";
  addDiv.textContent = "+ 새 제품 등록";
  addDiv.addEventListener("click", openInlineCatalogForm);
  dd.appendChild(addDiv);

  dd.classList.remove("hidden");
}

async function onCatalogSearchInput() {
  const q = document.getElementById("catalog-search").value.trim();
  if (!q) {
    document.getElementById("catalog-dropdown").classList.add("hidden");
    return;
  }
  clearTimeout(_catalogSearchTimer);
  _catalogSearchTimer = setTimeout(async () => {
    try {
      const items = await apiFetch("/api/v1/product-catalog?q=" + encodeURIComponent(q));
      renderCatalogDropdown(items);
    } catch (e) { showToast(e.message, "error"); }
  }, 300);
}

function selectCatalogItem(item) {
  document.getElementById("catalog-id").value = item.id;
  document.getElementById("catalog-search").value = ((item.vendor || "") + " " + (item.name || "")).trim();
  document.getElementById("catalog-dropdown").classList.add("hidden");

  // 요약 표시
  const summary = document.getElementById("catalog-summary");
  const typeLabel = item.asset_type_key ? getAssetTypeLabel(item.asset_type_key) : "미설정";
  summary.textContent = "제조사: " + (item.vendor || "-") +
    " | 모델: " + (item.name || "-") +
    " | 유형: " + typeLabel +
    " | 분류: " + (item.category || "-");
  summary.classList.remove("hidden");
  if (item.is_placeholder) {
    summary.classList.add("placeholder-style");
  } else {
    summary.classList.remove("placeholder-style");
  }
}

// 바깥 클릭 시 드롭다운 닫기
document.addEventListener("click", (e) => {
  const wrap = document.querySelector(".catalog-search-wrap");
  if (wrap && !wrap.contains(e.target)) {
    document.getElementById("catalog-dropdown").classList.add("hidden");
  }
});

/* ── 인라인 카탈로그 등록 ── */

async function openInlineCatalogForm() {
  document.getElementById("catalog-dropdown").classList.add("hidden");
  const form = document.getElementById("inline-catalog-form");
  form.classList.remove("hidden");
  document.getElementById("inline-vendor").value = "";
  document.getElementById("inline-model").value = "";
  document.getElementById("inline-category").value = "";
  await populateAssetTypeSelect("inline-asset-type");
}

async function saveInlineCatalog() {
  const vendor = document.getElementById("inline-vendor").value.trim();
  const name = document.getElementById("inline-model").value.trim();
  const category = document.getElementById("inline-category").value.trim();
  const assetTypeKey = document.getElementById("inline-asset-type").value;
  if (!vendor || !name || !category || !assetTypeKey) {
    showToast("모든 필수 항목을 입력하세요.", "warning");
    return;
  }
  try {
    const item = await apiFetch("/api/v1/product-catalog", {
      method: "POST",
      body: { vendor, name, category, asset_type_key: assetTypeKey },
    });
    document.getElementById("inline-catalog-form").classList.add("hidden");
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
    hardware_model_id: Number(catalogId),
    asset_name: name,
    hostname: document.getElementById("asset-hostname").value || null,
    period_id: document.getElementById("asset-period").value ? Number(document.getElementById("asset-period").value) : null,
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

/* ── Events ── */
document.addEventListener("DOMContentLoaded", async () => {
  await populateAssetTypeSelect("filter-type", true);
  initGrid();
});
document.getElementById("btn-add-asset").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-asset").addEventListener("click", () => modal.close());
document.getElementById("btn-save-asset").addEventListener("click", saveAsset);
document.getElementById("btn-edit-asset").addEventListener("click", () => {
  if (!_selectedAsset) return;
  const editableTabs = ["basic", "location", "network", "hw", "mgmt"];
  if (!editableTabs.includes(_currentTab)) {
    showToast("이 탭은 개별 항목을 추가/수정하세요.", "info");
    return;
  }
  if (_editMode) { exitEditMode(); return; }
  enterEditMode(_currentTab);
});
document.getElementById("btn-delete-asset").addEventListener("click", deleteAssetAction);

// 카탈로그 검색
document.getElementById("catalog-search").addEventListener("input", onCatalogSearchInput);

// 인라인 카탈로그 등록
document.getElementById("btn-inline-save").addEventListener("click", saveInlineCatalog);
document.getElementById("btn-inline-cancel").addEventListener("click", () => {
  document.getElementById("inline-catalog-form").classList.add("hidden");
});
document.getElementById("btn-close-detail").addEventListener("click", closeDetail);

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
document.getElementById("btn-cancel-rel").addEventListener("click", () => document.getElementById("modal-relation").close());
document.getElementById("btn-save-rel").addEventListener("click", saveRelation);
document.getElementById("btn-cancel-alias").addEventListener("click", () => document.getElementById("modal-alias").close());
document.getElementById("btn-save-alias").addEventListener("click", saveAlias);

// Search & filter
document.getElementById("filter-type").addEventListener("change", loadAssets);
document.getElementById("filter-status").addEventListener("change", loadAssets);
initTextFilter("filter-search", loadAssets);

// Global project filter checkbox
initProjectFilterCheckbox(loadAssets);

// Context selector change
window.addEventListener("ctx-changed", () => {
  closeDetail();
  loadAssets();
});
