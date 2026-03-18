/* ── 프로젝트 상세 (단계 + 산출물) ── */

const PROJECT_ID = window.__PROJECT_ID__;

/* ── Tab switching + lazy-load ── */
const _tabLoaded = {};

function activateTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.remove('hidden');

  if (!_tabLoaded[tabId]) {
    _tabLoaded[tabId] = true;
    if (tabId === 'assets') initAssetsTab();
    else if (tabId === 'ip') initIpTab();
    else if (tabId === 'portmap') initPortmapTab();
    else if (tabId === 'policy') initPolicyTab();
    else if (tabId === 'contacts') initContactsTab();
  }
}

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
    renderPhaseTimeline(phases);
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
    updateDeliverableProgress(allDeliverables);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── 요약 카드 ── */
async function loadSummaryCards(projectId) {
  try {
    const assets = await apiFetch(`/api/v1/assets?project_id=${projectId}`);
    document.getElementById('card-asset-count').textContent =
      Array.isArray(assets) ? `${assets.length} 대` : '-';
  } catch (e) {
    console.warn('Asset count load error:', e);
  }

  try {
    const ips = await apiFetch(`/api/v1/asset-ips?project_id=${projectId}`);
    document.getElementById('card-ip-count').textContent =
      Array.isArray(ips) ? `${ips.length} 개` : '-';
  } catch (e) {
    console.warn('IP count load error:', e);
  }

  try {
    const metrics = await apiFetch(`/api/v1/infra-dashboard/project/${projectId}`);
    document.getElementById('card-policy-rate').textContent =
      metrics.compliance_rate != null ? metrics.compliance_rate + '%' : '-';
  } catch (e) {
    document.getElementById('card-policy-rate').textContent = '-';
  }
}

function updateDeliverableProgress(deliverables) {
  const total = deliverables.length;
  const submitted = deliverables.filter(d => d.is_submitted).length;
  document.getElementById('card-deliverable-progress').textContent =
    total > 0 ? `${submitted}/${total}` : '-';
}

/* ── 단계 타임라인 ── */
function renderPhaseTimeline(phaseList) {
  const container = document.getElementById('phase-timeline');
  if (!phaseList || phaseList.length === 0) {
    container.textContent = '';
    const msg = document.createElement('p');
    msg.className = 'text-muted';
    msg.textContent = '등록된 단계가 없습니다.';
    container.appendChild(msg);
    return;
  }

  container.textContent = '';
  phaseList.forEach((p, i) => {
    const statusClass = p.status === 'completed' ? 'phase-done' :
                        p.status === 'in_progress' ? 'phase-active' : 'phase-pending';
    const icon = p.status === 'completed' ? '\u25CF' :
                 p.status === 'in_progress' ? '\u25D0' : '\u25CB';
    const label = PHASE_TYPE_MAP[p.phase_type] || p.phase_type || '';

    const step = document.createElement('div');
    step.className = 'phase-step ' + statusClass;

    const iconSpan = document.createElement('span');
    iconSpan.className = 'phase-icon';
    iconSpan.textContent = icon;
    step.appendChild(iconSpan);

    const labelSpan = document.createElement('span');
    labelSpan.className = 'phase-label';
    labelSpan.textContent = label;
    step.appendChild(labelSpan);

    container.appendChild(step);

    if (i < phaseList.length - 1) {
      const connector = document.createElement('span');
      connector.className = 'phase-connector';
      connector.textContent = '\u2500\u2500';
      container.appendChild(connector);
    }
  });
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
  loadSummaryCards(PROJECT_ID);
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

/* ── Assets Tab (lazy-load) ── */
const ASSET_TYPE_LABELS = { server: "서버", network: "네트워크", security: "보안장비", storage: "스토리지", other: "기타" };
const ASSET_ENV_LABELS = { prod: "운영", dev: "개발", staging: "스테이징", dr: "DR" };
const ASSET_STATUS_LABELS = { planned: "계획", active: "운영중", decommissioned: "폐기" };

function initAssetsTab() {
  const colDefs = [
    { field: "asset_name", headerName: "자산명", flex: 1, minWidth: 180, sort: "asc" },
    { field: "asset_type", headerName: "유형", width: 110, valueFormatter: p => ASSET_TYPE_LABELS[p.value] || p.value },
    { field: "vendor", headerName: "제조사", width: 130 },
    { field: "model", headerName: "모델", width: 130 },
    { field: "role", headerName: "역할", width: 130 },
    { field: "environment", headerName: "환경", width: 90, valueFormatter: p => ASSET_ENV_LABELS[p.value] || p.value },
    { field: "hostname", headerName: "호스트명", width: 140 },
    { field: "location", headerName: "위치", width: 130 },
    { field: "zone", headerName: "존", width: 100 },
    {
      field: "status", headerName: "상태", width: 100,
      cellRenderer: params => {
        const span = document.createElement("span");
        span.className = "badge badge-" + params.value;
        span.textContent = ASSET_STATUS_LABELS[params.value] || params.value;
        return span;
      },
    },
  ];

  agGrid.createGrid(document.getElementById("grid-tab-assets"), {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/assets?project_id=${PROJECT_ID}`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });
}

/* ── IP / Network Tab (lazy-load) ── */
const SUBNET_ROLE_LABELS = { service: "서비스", management: "관리", backup: "백업", dmz: "DMZ", other: "기타" };
const IP_TYPE_LABELS = { service: "서비스", management: "관리", backup: "백업", vip: "VIP", other: "기타" };

function initIpTab() {
  // Subnet grid
  const subnetCols = [
    { field: "name", headerName: "대역명", flex: 1, minWidth: 160, sort: "asc" },
    { field: "subnet", headerName: "서브넷", width: 160 },
    { field: "role", headerName: "역할", width: 100, valueFormatter: p => SUBNET_ROLE_LABELS[p.value] || p.value },
    { field: "vlan_id", headerName: "VLAN", width: 80 },
    { field: "gateway", headerName: "게이트웨이", width: 140 },
    { field: "region", headerName: "지역", width: 100 },
    { field: "zone", headerName: "존", width: 100 },
  ];

  agGrid.createGrid(document.getElementById("grid-tab-subnets"), {
    columnDefs: subnetCols,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/projects/${PROJECT_ID}/ip-subnets`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });

  // IP grid
  const ipCols = [
    { field: "ip_address", headerName: "IP 주소", width: 160, sort: "asc" },
    { field: "ip_type", headerName: "용도", width: 100, valueFormatter: p => IP_TYPE_LABELS[p.value] || p.value },
    { field: "hostname", headerName: "호스트명", width: 130 },
    { field: "service_name", headerName: "서비스명", width: 130 },
    { field: "interface_name", headerName: "인터페이스", width: 120 },
    { field: "zone", headerName: "존", width: 100 },
    { field: "vlan_id", headerName: "VLAN", width: 80 },
    { field: "note", headerName: "비고", flex: 1, minWidth: 150 },
  ];

  agGrid.createGrid(document.getElementById("grid-tab-ips"), {
    columnDefs: ipCols,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/projects/${PROJECT_ID}/ip-inventory`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });
}

/* ── Portmap Tab (lazy-load) ── */
const PORTMAP_STATUS_LABELS = { required: "필요", open: "오픈", closed: "차단", pending: "대기" };

function initPortmapTab() {
  const colDefs = [
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
      field: "status", headerName: "상태", width: 80,
      cellRenderer: params => {
        const span = document.createElement("span");
        span.className = "badge badge-" + params.value;
        span.textContent = PORTMAP_STATUS_LABELS[params.value] || params.value;
        return span;
      },
    },
  ];

  agGrid.createGrid(document.getElementById("grid-tab-portmaps"), {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/projects/${PROJECT_ID}/port-maps`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });
}

/* ── Policy Tab (lazy-load) ── */
const ASSIGN_STATUS_LABELS = { not_checked: "미확인", compliant: "준수", non_compliant: "미준수", exception: "예외", not_applicable: "해당없음" };

function initPolicyTab() {
  const colDefs = [
    { field: "policy_definition_id", headerName: "정책 ID", width: 90 },
    { field: "asset_id", headerName: "자산 ID", width: 90 },
    {
      field: "status", headerName: "상태", width: 100,
      cellRenderer: params => {
        const span = document.createElement("span");
        span.className = "badge badge-" + params.value;
        span.textContent = ASSIGN_STATUS_LABELS[params.value] || params.value;
        return span;
      },
    },
    { field: "checked_by", headerName: "확인자", width: 120 },
    { field: "checked_date", headerName: "확인일", width: 120, valueFormatter: p => fmtDate(p.value) },
    { field: "exception_reason", headerName: "예외 사유", flex: 1, minWidth: 160 },
  ];

  agGrid.createGrid(document.getElementById("grid-tab-policies"), {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/projects/${PROJECT_ID}/policy-assignments`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });
}

/* ── Contacts Tab (lazy-load) ── */
function initContactsTab() {
  const colDefs = [
    { field: "asset_name", headerName: "자산명", flex: 1, minWidth: 180, sort: "asc" },
    { field: "primary_contact_name", headerName: "주 담당자", width: 140 },
    { field: "secondary_contact_name", headerName: "부 담당자", width: 140 },
    { field: "maintenance_vendor", headerName: "유지보수사", width: 150 },
    { field: "dept", headerName: "부서", width: 120 },
    { field: "hostname", headerName: "호스트명", width: 140 },
    { field: "location", headerName: "위치", width: 130 },
  ];

  agGrid.createGrid(document.getElementById("grid-tab-contacts"), {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/assets?project_id=${PROJECT_ID}`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });
}

/* ── Linked Contracts (overview tab, accounting module only) ── */
let linkedContractsGridApi;

function initLinkedContracts() {
  const el = document.getElementById("grid-linked-contracts");
  if (!el) return;

  const colDefs = [
    { field: "contract_code", headerName: "사업코드", width: 130 },
    { field: "contract_name", headerName: "사업명", flex: 1, minWidth: 200 },
    { field: "is_primary", headerName: "주계약", width: 90,
      cellRenderer: params => {
        const span = document.createElement("span");
        span.className = "badge " + (params.value ? "badge-active" : "badge-planned");
        span.textContent = params.value ? "주" : "-";
        return span;
      },
    },
    { field: "note", headerName: "메모", width: 200 },
    {
      headerName: "", width: 80,
      cellRenderer: params => {
        const btn = document.createElement("button");
        btn.className = "btn btn-xs btn-danger";
        btn.textContent = "해제";
        btn.addEventListener("click", () => unlinkContract(params.data));
        return btn;
      },
      sortable: false, filter: false,
    },
  ];

  linkedContractsGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
  });

  loadLinkedContracts();
}

async function loadLinkedContracts() {
  if (!linkedContractsGridApi) return;
  try {
    const data = await apiFetch(`/api/v1/project-contract-links?project_id=${PROJECT_ID}`);
    linkedContractsGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function unlinkContract(link) {
  confirmDelete(
    `계약 연결을 해제하시겠습니까?`,
    async () => {
      try {
        await apiFetch(`/api/v1/project-contract-links/${link.id}`, { method: "DELETE" });
        showToast("계약 연결이 해제되었습니다.");
        loadLinkedContracts();
        loadSummaryCards(PROJECT_ID);
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

async function linkContract() {
  const code = prompt("연결할 계약의 ID를 입력하세요:");
  if (!code) return;
  try {
    await apiFetch("/api/v1/project-contract-links", {
      method: "POST",
      body: { project_id: PROJECT_ID, contract_id: Number(code), is_primary: false },
    });
    showToast("계약이 연결되었습니다.");
    loadLinkedContracts();
    loadSummaryCards(PROJECT_ID);
  } catch (err) { showToast(err.message, "error"); }
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", () => {
  initGrids();
  if (window.__ENABLED_MODULES__?.includes('accounting')) {
    initLinkedContracts();
    const linkBtn = document.getElementById("btn-link-contract");
    if (linkBtn) linkBtn.addEventListener("click", linkContract);
  }
});
document.getElementById("btn-add-phase").addEventListener("click", openCreatePhase);
document.getElementById("btn-cancel-phase").addEventListener("click", () => phaseModal.close());
document.getElementById("btn-save-phase").addEventListener("click", savePhase);
document.getElementById("btn-add-deliverable").addEventListener("click", openCreateDeliverable);
document.getElementById("btn-cancel-deliverable").addEventListener("click", () => deliverableModal.close());
document.getElementById("btn-save-deliverable").addEventListener("click", saveDeliverable);

