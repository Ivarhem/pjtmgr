/* ── 프로젝트 (목록 + 상세 통합) ── */

const STATUS_MAP = {
  planned: "계획", active: "진행중", on_hold: "보류", completed: "완료",
};

const PHASE_LABELS = {
  analysis: "분석", design: "설계", build: "구축",
  test: "시험", stabilize: "안정화",
};

const PHASE_STATUS_MAP = {
  not_started: "미시작", in_progress: "진행중", completed: "완료",
};

/* ═══════════════════════════════════════════════════
   목록 뷰 (전체)
   ═══════════════════════════════════════════════════ */

const columnDefs = [
  { field: "period_code", headerName: "기간코드", width: 160, sort: "asc" },
  { field: "contract_name", headerName: "사업명", flex: 1, minWidth: 200 },
  {
    field: "stage", headerName: "진행단계", width: 100,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "badge badge-progress";
      span.textContent = params.value || '-';
      return span;
    },
  },
  { field: "start_month", headerName: "시작월", width: 120, valueFormatter: (p) => p.value ? p.value.slice(0, 7) : '' },
  { field: "end_month", headerName: "종료월", width: 120, valueFormatter: (p) => p.value ? p.value.slice(0, 7) : '' },
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
      btnDel.addEventListener("click", () => deletePeriod(params.data));
      wrap.appendChild(btnEdit); wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

let gridApi;
let _listInitialized = false;

async function loadPeriods() {
  const cid = getCtxPartnerId();
  if (!cid) { gridApi.setGridOption("rowData", []); return; }
  try {
    const data = await apiFetch("/api/v1/contract-periods?partner_id=" + cid);
    gridApi.setGridOption("rowData", data);
  } catch (err) { showToast(err.message, "error"); }
}

async function loadListView() {
  await loadPeriods();
}

function initListGrids() {
  if (_listInitialized) return;
  _listInitialized = true;
  gridApi = agGrid.createGrid(document.getElementById("grid-projects"), {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
    onRowClicked: (e) => {
      const d = e.data;
      if (d && d.id && window.setCtxProject) {
        window.setCtxProject(d.id, d.period_code, d.contract_name);
      }
    },
  });
}

/* ═══════════════════════════════════════════════════
   상세 뷰 (프로젝트 선택 시)
   ═══════════════════════════════════════════════════ */

let _detailInitialized = false;
let _currentPeriodId = null;
let phaseGridApi, deliverableGridApi;
let detailPhases = [];

const phaseColDefs = [
  { field: "phase_type", headerName: "단계", width: 120,
    valueFormatter: p => PHASE_LABELS[p.value] || p.value },
  { field: "status", headerName: "상태", width: 100,
    cellRenderer: params => {
      const label = PHASE_STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
  },
  { field: "task_scope", headerName: "업무 범위", flex: 1, minWidth: 200 },
  { field: "deliverables_note", headerName: "산출물 메모", width: 200 },
  { headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: params => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm infra-inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary"; btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditPhase(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger"; btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deletePhase(params.data));
      wrap.appendChild(btnEdit); wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

const deliverableColDefs = [
  { field: "project_phase_id", headerName: "단계", width: 100,
    valueFormatter: params => {
      const ph = detailPhases.find(p => p.id === params.value);
      return ph ? (PHASE_LABELS[ph.phase_type] || ph.phase_type) : params.value;
    },
  },
  { field: "name", headerName: "산출물명", flex: 1, minWidth: 200 },
  { field: "is_submitted", headerName: "제출", width: 80,
    cellRenderer: params => {
      const span = document.createElement("span");
      span.className = "badge " + (params.value ? "badge-active" : "badge-planned");
      span.textContent = params.value ? "제출" : "미제출";
      return span;
    },
  },
  { field: "submitted_at", headerName: "제출일", width: 120, valueFormatter: p => fmtDate(p.value) },
  { field: "description", headerName: "설명", width: 200 },
  { field: "note", headerName: "비고", width: 150 },
  { headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: params => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm infra-inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary"; btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditDeliverable(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger"; btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteDeliverable(params.data));
      wrap.appendChild(btnEdit); wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

function initDetailGrids() {
  if (_detailInitialized) return;
  _detailInitialized = true;
  phaseGridApi = agGrid.createGrid(document.getElementById("grid-phases"), {
    columnDefs: phaseColDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true, enableCellTextSelection: true,
  });
  deliverableGridApi = agGrid.createGrid(document.getElementById("grid-deliverables"), {
    columnDefs: deliverableColDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true, enableCellTextSelection: true,
  });
}

async function loadDetailView(periodId) {
  _currentPeriodId = periodId;
  initDetailGrids();
  await loadPeriodInfo(periodId);
  await loadSummaryCards(periodId);
  await loadDetailPhases(periodId);
  await loadDeliverables();
}

async function loadPeriodInfo(periodId) {
  try {
    const p = await apiFetch("/api/v1/contract-periods/" + periodId);
    document.getElementById("detail-project-title").textContent = p.contract_name + ' (' + p.period_label + ')';
    const info = document.getElementById("detail-project-info");
    while (info.firstChild) info.removeChild(info.firstChild);
    const items = [
      ["사업코드", p.contract_code],
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
    // 수정 버튼 연결
    document.getElementById("btn-edit-project-detail").onclick = () => openEditModal(p);
  } catch (err) { showToast(err.message, "error"); }
}

async function loadSummaryCards(periodId) {
  const cid = getCtxPartnerId();
  try {
    const assets = await apiFetch("/api/v1/assets?partner_id=" + cid + "&contract_period_id=" + periodId);
    document.getElementById("card-asset-count").textContent =
      Array.isArray(assets) ? assets.length + " 대" : "-";
  } catch { document.getElementById("card-asset-count").textContent = "-"; }
  try {
    const ips = await apiFetch("/api/v1/asset-ips?contract_period_id=" + periodId);
    document.getElementById("card-ip-count").textContent =
      Array.isArray(ips) ? ips.length + " 개" : "-";
  } catch { document.getElementById("card-ip-count").textContent = "-"; }
  try {
    const metrics = await apiFetch("/api/v1/infra-dashboard/project/" + periodId);
    document.getElementById("card-policy-rate").textContent =
      metrics.compliance_rate != null ? metrics.compliance_rate + "%" : "-";
  } catch { document.getElementById("card-policy-rate").textContent = "-"; }
}

async function loadDetailPhases(periodId) {
  try {
    detailPhases = await apiFetch("/api/v1/period-phases?contract_period_id=" + periodId);
    phaseGridApi.setGridOption("rowData", detailPhases);
    populatePhaseDropdown();
    renderPhaseTimeline(detailPhases);
  } catch (err) { showToast(err.message, "error"); }
}

function populatePhaseDropdown() {
  const select = document.getElementById("deliverable-phase-id");
  while (select.firstChild) select.removeChild(select.firstChild);
  detailPhases.forEach(ph => {
    const opt = document.createElement("option");
    opt.value = ph.id;
    opt.textContent = PHASE_LABELS[ph.phase_type] || ph.phase_type;
    select.appendChild(opt);
  });
}

async function loadDeliverables() {
  try {
    const all = [];
    for (const ph of detailPhases) {
      const items = await apiFetch("/api/v1/period-phases/" + ph.id + "/deliverables");
      all.push(...items);
    }
    deliverableGridApi.setGridOption("rowData", all);
    const total = all.length;
    const submitted = all.filter(d => d.is_submitted).length;
    document.getElementById("card-deliverable-progress").textContent =
      total > 0 ? submitted + "/" + total : "-";
  } catch (err) { showToast(err.message, "error"); }
}

function renderPhaseTimeline(phaseList) {
  const container = document.getElementById("phase-timeline");
  container.textContent = "";
  if (!phaseList || phaseList.length === 0) {
    const msg = document.createElement("p");
    msg.className = "text-muted";
    msg.textContent = "등록된 단계가 없습니다.";
    container.appendChild(msg);
    return;
  }
  phaseList.forEach((p, i) => {
    const statusClass = p.status === "completed" ? "phase-done" :
                        p.status === "in_progress" ? "phase-active" : "phase-pending";
    const icon = p.status === "completed" ? "\u25CF" :
                 p.status === "in_progress" ? "\u25D0" : "\u25CB";
    const step = document.createElement("div");
    step.className = "phase-step " + statusClass;
    const iconSpan = document.createElement("span");
    iconSpan.className = "phase-icon";
    iconSpan.textContent = icon;
    step.appendChild(iconSpan);
    const labelSpan = document.createElement("span");
    labelSpan.className = "phase-label";
    labelSpan.textContent = PHASE_LABELS[p.phase_type] || p.phase_type;
    step.appendChild(labelSpan);
    container.appendChild(step);
    if (i < phaseList.length - 1) {
      const connector = document.createElement("span");
      connector.className = "phase-connector";
      connector.textContent = "\u2500\u2500";
      container.appendChild(connector);
    }
  });
}

/* ── Phase Modal ── */
const phaseModal = document.getElementById("modal-phase");

function openCreatePhase() {
  document.getElementById("phase-id").value = "";
  document.getElementById("phase-type").value = "analysis";
  document.getElementById("phase-status").value = "not_started";
  document.getElementById("phase-task-scope").value = "";
  document.getElementById("phase-deliverables-note").value = "";
  document.getElementById("phase-cautions").value = "";
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
    contract_period_id: _currentPeriodId,
    phase_type: document.getElementById("phase-type").value,
    status: document.getElementById("phase-status").value,
    task_scope: document.getElementById("phase-task-scope").value || null,
    deliverables_note: document.getElementById("phase-deliverables-note").value || null,
    cautions: document.getElementById("phase-cautions").value || null,
  };
  try {
    if (phaseId) {
      await apiFetch("/api/v1/period-phases/" + phaseId, { method: "PATCH", body: payload });
      showToast("단계가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/period-phases", { method: "POST", body: payload });
      showToast("단계가 등록되었습니다.");
    }
    phaseModal.close();
    await loadDetailPhases(_currentPeriodId);
    loadDeliverables();
  } catch (err) { showToast(err.message, "error"); }
}

async function deletePhase(phase) {
  const label = PHASE_LABELS[phase.phase_type] || phase.phase_type;
  confirmDelete('"' + label + '" 단계를 삭제하시겠습니까?', async () => {
    try {
      await apiFetch("/api/v1/period-phases/" + phase.id, { method: "DELETE" });
      showToast("단계가 삭제되었습니다.");
      await loadDetailPhases(_currentPeriodId);
      loadDeliverables();
    } catch (err) { showToast(err.message, "error"); }
  });
}

/* ── Deliverable Modal ── */
const deliverableModal = document.getElementById("modal-deliverable");

function openCreateDeliverable() {
  document.getElementById("deliverable-id").value = "";
  document.getElementById("deliverable-name").value = "";
  document.getElementById("deliverable-is-submitted").value = "false";
  document.getElementById("deliverable-submitted-at").value = "";
  document.getElementById("deliverable-description").value = "";
  document.getElementById("deliverable-note").value = "";
  document.getElementById("modal-deliverable-title").textContent = "산출물 등록";
  document.getElementById("btn-save-deliverable").textContent = "등록";
  deliverableModal.showModal();
}

function openEditDeliverable(d) {
  document.getElementById("deliverable-id").value = d.id;
  document.getElementById("deliverable-phase-id").value = d.project_phase_id;
  document.getElementById("deliverable-name").value = d.name;
  document.getElementById("deliverable-is-submitted").value = d.is_submitted ? "true" : "false";
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
    name: document.getElementById("deliverable-name").value,
    is_submitted: document.getElementById("deliverable-is-submitted").value === "true",
    submitted_at: document.getElementById("deliverable-submitted-at").value || null,
    description: document.getElementById("deliverable-description").value || null,
    note: document.getElementById("deliverable-note").value || null,
  };
  try {
    if (delId) {
      await apiFetch("/api/v1/period-deliverables/" + delId, { method: "PATCH", body: payload });
      showToast("산출물이 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/period-phases/" + phaseId + "/deliverables", { method: "POST", body: payload });
      showToast("산출물이 등록되었습니다.");
    }
    deliverableModal.close();
    loadDeliverables();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteDeliverable(d) {
  confirmDelete('"' + d.name + '" 산출물을 삭제하시겠습니까?', async () => {
    try {
      await apiFetch("/api/v1/period-deliverables/" + d.id, { method: "DELETE" });
      showToast("산출물이 삭제되었습니다.");
      loadDeliverables();
    } catch (err) { showToast(err.message, "error"); }
  });
}

/* ═══════════════════════════════════════════════════
   뷰 전환 + Period CRUD (공통)
   ═══════════════════════════════════════════════════ */

function showView(mode) {
  const listEl = document.getElementById("view-list");
  const detailEl = document.getElementById("view-detail");
  if (mode === "detail") {
    listEl.classList.add("is-hidden");
    detailEl.classList.remove("is-hidden");
  } else {
    listEl.classList.remove("is-hidden");
    detailEl.classList.add("is-hidden");
  }
}

function onCtxChanged() {
  const pid = getCtxProjectId();
  if (pid) {
    showView("detail");
    loadDetailView(pid);
  } else {
    showView("list");
    initListGrids();
    loadListView();
  }
}

/* ── Period CRUD Modal ── */
const modal = document.getElementById("modal-project");

function resetForm() {
  document.getElementById("project-id").value = "";
  document.getElementById("project-code").value = "";
  document.getElementById("project-name").value = "";
  document.getElementById("project-status").value = "planned";
  document.getElementById("start-date").value = "";
  document.getElementById("end-date").value = "";
  document.getElementById("project-desc").value = "";
}

function openCreateModal() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  resetForm();
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("start-date").value = today;
  document.getElementById("end-date").value = today;
  document.getElementById("modal-project-title").textContent = "프로젝트 등록";
  document.getElementById("btn-save-project").textContent = "등록";
  modal.showModal();
}

function openEditModal(period) {
  document.getElementById("project-id").value = period.id;
  document.getElementById("project-code").value = period.contract_code || '';
  document.getElementById("project-name").value = period.contract_name ? period.contract_name + ' (' + period.period_label + ')' : '';
  document.getElementById("project-status").value = period.stage || "planned";
  document.getElementById("start-date").value = period.start_month ? period.start_month.slice(0, 10) : "";
  document.getElementById("end-date").value = period.end_month ? period.end_month.slice(0, 10) : "";
  document.getElementById("project-desc").value = period.description || "";
  document.getElementById("modal-project-title").textContent = "프로젝트 수정";
  document.getElementById("btn-save-project").textContent = "저장";
  modal.showModal();
}

async function savePeriod() {
  const cid = getCtxPartnerId();
  if (!cid) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const periodId = document.getElementById("project-id").value;
  const payload = {
    description: document.getElementById("project-desc").value || null,
    start_month: document.getElementById("start-date").value || null,
    end_month: document.getElementById("end-date").value || null,
    stage: document.getElementById("project-status").value,
  };
  try {
    if (periodId) {
      await apiFetch("/api/v1/contract-periods/" + periodId, { method: "PATCH", body: payload });
      showToast("프로젝트가 수정되었습니다.");
    } else {
      payload.partner_id = cid;
      await apiFetch("/api/v1/contract-periods", { method: "POST", body: payload });
      showToast("프로젝트가 등록되었습니다.");
    }
    modal.close();
    onCtxChanged(); // 현재 뷰 새로고침
  } catch (err) { showToast(err.message, "error"); }
}

async function deletePeriod(period) {
  const displayName = period.contract_name ? period.contract_name + ' (' + period.period_label + ')' : period.id;
  confirmDelete(
    '프로젝트 "' + displayName + '"을(를) 삭제하시겠습니까?',
    async () => {
      try {
        await apiFetch("/api/v1/contract-periods/" + period.id, { method: "DELETE" });
        showToast("프로젝트가 삭제되었습니다.");
        onCtxChanged();
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

/* ═══════════════════════════════════════════════════
   Events
   ═══════════════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  // initContextSelectors (async)가 완료되면 ctx-changed 이벤트가 발생하므로,
  // 여기서는 초기 fallback만 처리: 짧은 대기 후에도 ctx-changed가 안 오면 목록 표시
  const _initTimer = setTimeout(() => {
    if (!getCtxProjectId()) {
      showView("list");
      initListGrids();
      loadListView();
    }
  }, 300);
  window.addEventListener("ctx-changed", () => clearTimeout(_initTimer), { once: true });
});

document.getElementById("link-back-to-list").addEventListener("click", (e) => {
  e.preventDefault();
  if (window.resetCtxProject) window.resetCtxProject();
});
document.getElementById("btn-add-project").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-project").addEventListener("click", () => modal.close());
document.getElementById("btn-save-project").addEventListener("click", savePeriod);

document.getElementById("btn-add-phase").addEventListener("click", openCreatePhase);
document.getElementById("btn-cancel-phase").addEventListener("click", () => phaseModal.close());
document.getElementById("btn-save-phase").addEventListener("click", savePhase);

document.getElementById("btn-add-deliverable").addEventListener("click", openCreateDeliverable);
document.getElementById("btn-cancel-deliverable").addEventListener("click", () => deliverableModal.close());
document.getElementById("btn-save-deliverable").addEventListener("click", saveDeliverable);

window.addEventListener("ctx-changed", onCtxChanged);
