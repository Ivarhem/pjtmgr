/* ── 프로젝트 상세 (단계 + 산출물) ── */

const PROJECT_ID = window.__PROJECT_ID__;
let _PROJECT_PARTNER_ID = null;

function setResultMessage(container, message, state) {
  container.textContent = message;
  container.classList.remove("infra-text-danger", "infra-text-success");
  if (state === "error") {
    container.classList.add("infra-text-danger");
  } else if (state === "success") {
    container.classList.add("infra-text-success");
  }
}

// Resolve partner_id from the period + set topbar context
(async () => {
  try {
    const period = await apiFetch('/api/v1/contract-periods/' + PROJECT_ID);
    _PROJECT_PARTNER_ID = period.partner_id;

    // Wait for context selectors to initialize, then set project context
    function applyCtx() {
      if (window.setCtxProject) {
        window.setCtxProject(period.id, period.period_code, period.contract_name);
      } else {
        setTimeout(applyCtx, 100);
      }
    }
    applyCtx();
  } catch { /* fallback in individual calls */ }
})();

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
    else if (tabId === 'relations') initRelationsTab();
    else if (tabId === 'ip') initIpTab();
    else if (tabId === 'portmap') initPortmapTab();
    else if (tabId === 'policy') initPolicyTab();
    else if (tabId === 'contacts') initContactsTab();
    else if (tabId === 'history') initHistoryTab();
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

/* ── Pin Period 자동 설정 ── */
function autoPinProject() {
  localStorage.setItem('infra.last_period_id', String(PROJECT_ID));
}

/* ── 프로젝트 기본 정보 ── */
async function loadProjectInfo() {
  try {
    const p = await apiFetch(`/api/v1/contract-periods/${PROJECT_ID}`);
    document.getElementById("project-title").textContent = p.contract_name + ' (' + p.period_code + ')';

    const info = document.getElementById("project-info");
    while (info.firstChild) info.removeChild(info.firstChild);

    const items = [
      ["기간코드", p.period_code],
      ["고객사", p.partner_name || "-"],
      ["진행단계", p.stage || "-"],
      ["시작월", p.start_month ? p.start_month.slice(0, 7) : "-"],
      ["종료월", p.end_month ? p.end_month.slice(0, 7) : "-"],
      ["설명", p.description || "-"],
    ];

    const row = document.createElement("div");
    row.className = "info-row";
    items.forEach(([label, value]) => {
      const span = document.createElement("span");
      span.className = "info-item";
      const b = document.createElement("b");
      b.textContent = label;
      span.appendChild(b);
      span.appendChild(document.createTextNode(" " + (value || "-")));
      row.appendChild(span);
    });
    info.appendChild(row);
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
      wrap.className = "gap-sm infra-inline-flex";
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
    phases = await apiFetch(`/api/v1/contract-periods/${PROJECT_ID}/phases`);
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
      wrap.className = "gap-sm infra-inline-flex";
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
      const items = await apiFetch(`/api/v1/period-phases/${ph.id}/deliverables`);
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
    const assets = await apiFetch(`/api/v1/assets?partner_id=${_PROJECT_PARTNER_ID}&period_id=${projectId}`);
    document.getElementById('card-asset-count').textContent =
      Array.isArray(assets) ? `${assets.length} 대` : '-';
  } catch (e) {
    console.warn('Asset count load error:', e);
  }

  // IP 할당 카드 — contract_period 기반 IP 조회 API 미구현 (TODO)
  // 정책 준수율 — 정책 기능 TODO
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
    contract_period_id: PROJECT_ID,
    phase_type: document.getElementById("phase-type").value,
    status: document.getElementById("phase-status").value,
    task_scope: document.getElementById("phase-task-scope").value || null,
    deliverables_note: document.getElementById("phase-deliverables-note").value || null,
    cautions: document.getElementById("phase-cautions").value || null,
  };

  try {
    if (phaseId) {
      await apiFetch(`/api/v1/period-phases/${phaseId}`, { method: "PATCH", body: payload });
      showToast("단계가 수정되었습니다.");
    } else {
      await apiFetch(`/api/v1/period-phases`, { method: "POST", body: payload });
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
        await apiFetch(`/api/v1/period-phases/${phase.id}`, { method: "DELETE" });
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
      await apiFetch(`/api/v1/period-deliverables/${delId}`, { method: "PATCH", body: payload });
      showToast("산출물이 수정되었습니다.");
    } else {
      await apiFetch(`/api/v1/period-phases/${phaseId}/deliverables`, { method: "POST", body: payload });
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
        await apiFetch(`/api/v1/period-deliverables/${d.id}`, { method: "DELETE" });
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
        const data = await apiFetch(`/api/v1/assets?partner_id=${_PROJECT_PARTNER_ID}&contract_period_id=${PROJECT_ID}`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });
}

/* ── Asset Relations Tab (lazy-load) ── */
const RELATION_TYPE_LABELS = {
  HOSTS: "호스팅",
  USES: "사용",
  INSTALLED_ON: "설치됨",
  PROTECTS: "보호",
  CONNECTS_TO: "연결",
  DEPENDS_ON: "의존",
};

let _relationsGridApi = null;
let _relationAssetsCache = [];

function initRelationsTab() {
  const colDefs = [
    { field: "src_asset_name", headerName: "출발 자산", flex: 1, minWidth: 150, sort: "asc" },
    { field: "src_hostname", headerName: "출발 호스트", width: 130 },
    {
      field: "relation_type", headerName: "관계 유형", width: 120,
      cellRenderer: params => {
        const span = document.createElement("span");
        span.className = "badge";
        span.textContent = RELATION_TYPE_LABELS[params.value] || params.value;
        return span;
      },
    },
    { field: "dst_asset_name", headerName: "도착 자산", flex: 1, minWidth: 150 },
    { field: "dst_hostname", headerName: "도착 호스트", width: 130 },
    { field: "note", headerName: "비고", flex: 1, minWidth: 150 },
    {
      headerName: "", width: 80, sortable: false, filter: false,
      cellRenderer: params => {
        const wrap = document.createElement("span");
        wrap.className = "infra-inline-flex-tight";

        const btnEdit = document.createElement("button");
        btnEdit.className = "btn btn-sm";
        btnEdit.textContent = "수정";
        btnEdit.onclick = () => openRelationModal(params.data);
        wrap.appendChild(btnEdit);

        const btnDel = document.createElement("button");
        btnDel.className = "btn btn-sm btn-danger";
        btnDel.textContent = "삭제";
        btnDel.onclick = () => deleteRelation(params.data.id);
        wrap.appendChild(btnDel);

        return wrap;
      },
    },
  ];

  _relationsGridApi = agGrid.createGrid(document.getElementById("grid-tab-relations"), {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/asset-relations?partner_id=${_PROJECT_PARTNER_ID}`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });

  // 자산 목록 캐싱 (모달 셀렉트용)
  loadRelationAssets();

  // 이벤트 바인딩
  document.getElementById("btn-add-relation").onclick = () => openRelationModal(null);
  document.getElementById("btn-cancel-relation").onclick = () => document.getElementById("modal-relation").close();
  document.getElementById("btn-save-relation").onclick = saveRelation;
}

async function loadRelationAssets() {
  try {
    _relationAssetsCache = await apiFetch(`/api/v1/assets?partner_id=${_PROJECT_PARTNER_ID}&contract_period_id=${PROJECT_ID}`);
  } catch (err) { _relationAssetsCache = []; }
}

function openRelationModal(data) {
  const modal = document.getElementById("modal-relation");
  const isEdit = !!data;
  document.getElementById("modal-relation-title").textContent = isEdit ? "자산 관계 수정" : "자산 관계 등록";
  document.getElementById("relation-id").value = isEdit ? data.id : "";

  // 자산 셀렉트 채우기 (DOM 방식)
  const srcSel = document.getElementById("relation-src-asset");
  const dstSel = document.getElementById("relation-dst-asset");
  [srcSel, dstSel].forEach(sel => {
    while (sel.firstChild) sel.removeChild(sel.firstChild);
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = "선택";
    sel.appendChild(emptyOpt);
    _relationAssetsCache.forEach(a => {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = a.asset_name + " (" + (a.hostname || "-") + ")";
      sel.appendChild(opt);
    });
  });

  if (isEdit) {
    srcSel.value = data.src_asset_id;
    dstSel.value = data.dst_asset_id;
    document.getElementById("relation-type").value = data.relation_type;
    document.getElementById("relation-note").value = data.note || "";
  } else {
    document.getElementById("relation-type").value = "CONNECTS_TO";
    document.getElementById("relation-note").value = "";
  }
  modal.showModal();
}

async function saveRelation() {
  const id = document.getElementById("relation-id").value;
  const isEdit = !!id;

  const body = {
    relation_type: document.getElementById("relation-type").value,
    note: document.getElementById("relation-note").value || null,
  };

  if (!isEdit) {
    body.src_asset_id = parseInt(document.getElementById("relation-src-asset").value);
    body.dst_asset_id = parseInt(document.getElementById("relation-dst-asset").value);
    if (!body.src_asset_id || !body.dst_asset_id) {
      showToast("출발/도착 자산을 선택하세요.", "error");
      return;
    }
    if (body.src_asset_id === body.dst_asset_id) {
      showToast("동일 자산 간 관계를 생성할 수 없습니다.", "error");
      return;
    }
  }

  try {
    if (isEdit) {
      await apiFetch(`/api/v1/asset-relations/${id}`, { method: "PATCH", body });
    } else {
      await apiFetch("/api/v1/asset-relations", { method: "POST", body });
    }
    document.getElementById("modal-relation").close();
    showToast(isEdit ? "관계가 수정되었습니다." : "관계가 등록되었습니다.");
    await refreshRelationsGrid();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteRelation(relId) {
  if (!confirm("이 관계를 삭제하시겠습니까?")) return;
  try {
    await apiFetch(`/api/v1/asset-relations/${relId}`, { method: "DELETE" });
    showToast("관계가 삭제되었습니다.");
    await refreshRelationsGrid();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function refreshRelationsGrid() {
  try {
    const data = await apiFetch(`/api/v1/asset-relations?partner_id=${_PROJECT_PARTNER_ID}`);
    _relationsGridApi.setGridOption("rowData", data);
  } catch (err) { showToast(err.message, "error"); }
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
        const data = await apiFetch(`/api/v1/ip-subnets?partner_id=${_PROJECT_PARTNER_ID}`);
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
        const data = await apiFetch(`/api/v1/ip-inventory?partner_id=${_PROJECT_PARTNER_ID}`);
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
        const data = await apiFetch(`/api/v1/port-maps?partner_id=${_PROJECT_PARTNER_ID}&contract_period_id=${PROJECT_ID}`);
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
        const data = await apiFetch(`/api/v1/policy-assignments?partner_id=${_PROJECT_PARTNER_ID}&contract_period_id=${PROJECT_ID}`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });
}

/* ── Contacts Tab (lazy-load) ── */
let _pcPartnersCache = [];
let _pcContactsCache = [];

function initContactsTab() {
  // 자산별 담당자 Grid (기존)
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
        const data = await apiFetch(`/api/v1/assets?partner_id=${_PROJECT_PARTNER_ID}&contract_period_id=${PROJECT_ID}`);
        params.api.setGridOption("rowData", data);
      } catch (err) { showToast(err.message, "error"); }
    },
  });

  // 프로젝트 업체/담당자 로드
  loadProjectPartners();
  _initPcModals();
}

async function loadProjectPartners() {
  const container = document.getElementById("project-partners-list");
  try {
    const [partners, contacts] = await Promise.all([
      apiFetch(`/api/v1/period-partners?contract_period_id=${PROJECT_ID}`),
      apiFetch(`/api/v1/period-partner-contacts?contract_period_id=${PROJECT_ID}`),
    ]);
    _pcPartnersCache = partners;
    _pcContactsCache = contacts;
    _renderProjectPartners(container, partners, contacts);
  } catch (err) {
    container.textContent = "업체 정보를 불러올 수 없습니다.";
    showToast(err.message, "error");
  }
}

function _renderProjectPartners(container, partners, contacts) {
  container.textContent = "";
  if (partners.length === 0) {
    const p = document.createElement("p");
    p.className = "text-muted pc-placeholder";
    p.textContent = "연결된 업체가 없습니다. '업체 연결' 버튼으로 추가하세요.";
    container.appendChild(p);
    return;
  }

  partners.forEach(pc => {
    const card = document.createElement("div");
    card.className = "card mb-sm pc-card";

    // Header: role badge + partner name + actions
    const header = document.createElement("div");
    header.className = "pc-header";
    const badge = document.createElement("span");
    badge.className = "badge badge-active";
    badge.textContent = pc.role;
    header.appendChild(badge);
    const name = document.createElement("strong");
    name.textContent = pc.partner_name || "(알수없음)";
    header.appendChild(name);
    if (pc.scope_text) {
      const scope = document.createElement("span");
      scope.className = "text-muted pc-scope";
      scope.textContent = " — " + pc.scope_text;
      header.appendChild(scope);
    }
    // spacer
    const spacer = document.createElement("span");
    spacer.className = "pc-spacer";
    header.appendChild(spacer);
    // add contact btn
    const addBtn = document.createElement("button");
    addBtn.className = "btn btn-xs btn-secondary";
    addBtn.textContent = "+ 담당자";
    addBtn.addEventListener("click", () => openAddContactModal(pc));
    header.appendChild(addBtn);
    // delete btn
    const delBtn = document.createElement("button");
    delBtn.className = "btn btn-xs btn-danger";
    delBtn.textContent = "해제";
    delBtn.addEventListener("click", () => deleteProjectPartner(pc.id));
    header.appendChild(delBtn);
    card.appendChild(header);

    // Contacts list
    const pcContacts = contacts.filter(c => c.project_partner_id === pc.id);
    if (pcContacts.length > 0) {
      const table = document.createElement("table");
      table.className = "pc-contacts-table";
      pcContacts.forEach(ct => {
        const tr = document.createElement("tr");
        const cells = [
          ct.project_role,
          ct.contact_name || "",
          ct.contact_phone || "",
          ct.contact_email || "",
        ];
        cells.forEach(txt => {
          const td = document.createElement("td");
          td.textContent = txt;
          tr.appendChild(td);
        });
        // delete contact btn
        const tdAction = document.createElement("td");
        const rmBtn = document.createElement("button");
        rmBtn.className = "btn btn-xs btn-danger";
        rmBtn.textContent = "해제";
        rmBtn.addEventListener("click", () => deleteProjectPartnerContact(ct.id));
        tdAction.appendChild(rmBtn);
        tr.appendChild(tdAction);
        table.appendChild(tr);
      });
      card.appendChild(table);
    } else {
      const empty = document.createElement("p");
      empty.className = "text-muted pc-empty";
      empty.textContent = "담당자 없음";
      card.appendChild(empty);
    }

    container.appendChild(card);
  });
}

/* ── Project Partner Modal ── */
const pcModal = document.getElementById("modal-project-partner");
const pccModal = document.getElementById("modal-project-partner-contact");

function _initPcModals() {
  document.getElementById("btn-add-project-partner")?.addEventListener("click", openAddPartnerModal);
  document.getElementById("btn-cancel-pc")?.addEventListener("click", () => pcModal.close());
  document.getElementById("btn-save-pc")?.addEventListener("click", saveProjectPartner);
  document.getElementById("btn-cancel-pcc")?.addEventListener("click", () => pccModal.close());
  document.getElementById("btn-save-pcc")?.addEventListener("click", saveProjectPartnerContact);
}

async function openAddPartnerModal() {
  document.getElementById("pc-id").value = "";
  document.getElementById("pc-scope-text").value = "";
  document.getElementById("pc-note").value = "";
  document.getElementById("pc-role").value = "고객사";
  document.getElementById("modal-pc-title").textContent = "업체 연결";

  // 거래처 목록 로드
  const sel = document.getElementById("pc-partner-id");
  sel.textContent = "";
  try {
    const partners = await apiFetch("/api/v1/partners");
    partners.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      sel.appendChild(opt);
    });
  } catch (err) { showToast("거래처 로드 실패", "error"); }
  pcModal.showModal();
}

async function saveProjectPartner() {
  const pcId = document.getElementById("pc-id").value;
  const payload = {
    contract_period_id: PROJECT_ID,
    partner_id: Number(document.getElementById("pc-partner-id").value),
    role: document.getElementById("pc-role").value,
    scope_text: document.getElementById("pc-scope-text").value || null,
    note: document.getElementById("pc-note").value || null,
  };

  try {
    if (pcId) {
      await apiFetch(`/api/v1/period-partners/${pcId}`, { method: "PATCH", body: payload });
      showToast("업체 정보가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/period-partners", { method: "POST", body: payload });
      showToast("업체가 연결되었습니다.");
    }
    pcModal.close();
    loadProjectPartners();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteProjectPartner(pcId) {
  confirmDelete("업체 연결을 해제하시겠습니까? 소속 담당자 연결도 함께 삭제됩니다.", async () => {
    try {
      await apiFetch(`/api/v1/period-partners/${pcId}`, { method: "DELETE" });
      showToast("업체 연결이 해제되었습니다.");
      loadProjectPartners();
    } catch (err) { showToast(err.message, "error"); }
  });
}

/* ── Project Partner Contact Modal ── */
async function openAddContactModal(pc) {
  document.getElementById("pcc-id").value = "";
  document.getElementById("pcc-project-partner-id").value = pc.id;
  document.getElementById("pcc-note").value = "";
  document.getElementById("pcc-project-role").value = "고객PM";
  document.getElementById("modal-pcc-title").textContent =
    `담당자 연결 — ${pc.partner_name} (${pc.role})`;

  // 해당 거래처 담당자 목록 로드
  const sel = document.getElementById("pcc-contact-id");
  sel.textContent = "";
  try {
    const contacts = await apiFetch(`/api/v1/partners/${pc.partner_id}/contacts`);
    contacts.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name + (c.phone ? ` (${c.phone})` : "");
      sel.appendChild(opt);
    });
    if (contacts.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "(등록된 담당자 없음)";
      sel.appendChild(opt);
    }
  } catch (err) { showToast("담당자 로드 실패", "error"); }
  pccModal.showModal();
}

async function saveProjectPartnerContact() {
  const pccId = document.getElementById("pcc-id").value;
  const payload = {
    project_partner_id: Number(document.getElementById("pcc-project-partner-id").value),
    contact_id: Number(document.getElementById("pcc-contact-id").value),
    project_role: document.getElementById("pcc-project-role").value,
    note: document.getElementById("pcc-note").value || null,
  };

  try {
    if (pccId) {
      await apiFetch(`/api/v1/period-partner-contacts/${pccId}`, { method: "PATCH", body: payload });
      showToast("담당자 정보가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/period-partner-contacts", { method: "POST", body: payload });
      showToast("담당자가 연결되었습니다.");
    }
    pccModal.close();
    loadProjectPartners();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteProjectPartnerContact(pccId) {
  confirmDelete("담당자 연결을 해제하시겠습니까?", async () => {
    try {
      await apiFetch(`/api/v1/period-partner-contacts/${pccId}`, { method: "DELETE" });
      showToast("담당자 연결이 해제되었습니다.");
      loadProjectPartners();
    } catch (err) { showToast(err.message, "error"); }
  });
}

/* ── History Tab (audit log, lazy-load) ── */
const _ACTION_MAP = { create: "생성", update: "수정", delete: "삭제" };
const _ENTITY_MAP = {
  project: "프로젝트", asset: "자산", ip_subnet: "IP대역",
  port_map: "포트맵", policy: "정책", policy_assignment: "정책적용",
};

function initHistoryTab() {
  const colDefs = [
    { field: "created_at", headerName: "일시", width: 160, valueFormatter: (p) => fmtDate(p.value) + " " + (p.value ? p.value.slice(11, 19) : "") },
    { field: "user_name", headerName: "사용자", width: 120 },
    { field: "action", headerName: "동작", width: 80, valueFormatter: (p) => _ACTION_MAP[p.value] || p.value },
    { field: "entity_type", headerName: "대상", width: 100, valueFormatter: (p) => _ENTITY_MAP[p.value] || p.value },
    { field: "summary", headerName: "요약", flex: 1, minWidth: 250 },
  ];

  agGrid.createGrid(document.getElementById("grid-tab-history"), {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    onGridReady: async (params) => {
      try {
        const data = await apiFetch(`/api/v1/infra-dashboard/audit-log`);
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
  autoPinProject();
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

// ── Excel Export ──
document.getElementById("btn-export-project")?.addEventListener("click", () => {
  window.location.href = `/api/v1/infra-excel/export?partner_id=${_PROJECT_PARTNER_ID}&contract_period_id=${PROJECT_ID}`;
});

// ── Asset Import (프로젝트 상세 내) ──
document.getElementById("btn-asset-import")?.addEventListener("click", () => {
  document.getElementById("asset-import-panel").classList.toggle("hidden");
});
document.getElementById("btn-asset-import-close")?.addEventListener("click", () => {
  document.getElementById("asset-import-panel").classList.add("hidden");
});
document.getElementById("btn-asset-import-run")?.addEventListener("click", async () => {
  const fileInput = document.getElementById("asset-import-file");
  const file = fileInput?.files[0];
  if (!file) { showToast("파일을 선택하세요.", "warning"); return; }
  const dup = document.getElementById("asset-import-dup").value;
  const fd = new FormData();
  fd.append("file", file);
  fd.append("partner_id", _PROJECT_PARTNER_ID);
  fd.append("on_duplicate", dup);
  const btn = document.getElementById("btn-asset-import-run");
  btn.disabled = true;
  btn.textContent = "Import 중...";
  const resultDiv = document.getElementById("asset-import-result");
  resultDiv.textContent = "";
  try {
    const res = await fetch("/api/v1/infra-excel/import/confirm", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      setResultMessage(resultDiv, "오류: " + (data.detail || "Import 실패"), "error");
    } else {
      setResultMessage(
        resultDiv,
        "생성 " + data.created + "건, 건너뜀 " + data.skipped + "건",
        "success"
      );
      // 자산 탭 새로고침
      _tabLoaded["assets"] = false;
      initAssetsTab();
    }
  } catch (e) {
    setResultMessage(resultDiv, "Import 실패: " + e.message, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Import 실행";
  }
});

// ── 컨텍스트 변경 시 네비게이션 ──
window.addEventListener("ctx-changed", (e) => {
  const pid = e.detail?.projectId;
  if (pid && pid !== PROJECT_ID) {
    window.location.href = "/periods/" + pid;
  } else if (!pid) {
    window.location.href = "/periods";
  }
});
