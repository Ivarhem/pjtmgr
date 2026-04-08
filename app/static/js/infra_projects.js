/* ── 프로젝트 목록 + 인라인 상세 ── */

/* ── Constants ── */
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

const ACTIVE_PROJECTS_ONLY_KEY = "infra_projects_active_only_v1";
const PROJECT_DETAIL_OPEN_KEY = "infra_projects_detail_open_v1";
const PROJECT_LIST_WIDTH_KEY = "infra_projects_list_width_v1";

/* ── State ── */
let gridApi;
let phaseGridApi;
let deliverableGridApi;
let _listInitialized = false;
let _periodRows = [];
let _classificationLayouts = null;
let _selectedProject = null;
let _phases = [];

/* ── Project list column defs ── */
const columnDefs = [
  { field: "period_code", headerName: "기간코드", width: 160, sort: "asc" },
  { field: "contract_name", headerName: "사업명", flex: 1, minWidth: 200 },
  {
    field: "is_completed", headerName: "완료", width: 80,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = params.value ? "badge badge-completed" : "badge badge-active";
      span.textContent = params.value ? "완료" : "진행중";
      return span;
    },
  },
  { field: "start_month", headerName: "시작월", width: 110, valueFormatter: (p) => p.value ? p.value.slice(0, 7) : '' },
  { field: "end_month", headerName: "종료월", width: 110, valueFormatter: (p) => p.value ? p.value.slice(0, 7) : '' },
  {
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm infra-inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary"; btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", (e) => { e.stopPropagation(); openEditModal(params.data); });
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger"; btnDel.textContent = "삭제";
      btnDel.addEventListener("click", (e) => { e.stopPropagation(); deletePeriod(params.data); });
      wrap.appendChild(btnEdit); wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

/* ── Phase column defs ── */
const phaseColDefs = [
  {
    field: "phase_type", headerName: "단계", width: 120,
    editable: true,
    cellEditor: "agSelectCellEditor",
    cellEditorParams: { values: ["analysis", "design", "build", "test", "stabilize"] },
    valueFormatter: (p) => PHASE_TYPE_MAP[p.value] || p.value,
  },
  {
    field: "status", headerName: "상태", width: 100,
    editable: true,
    cellEditor: "agSelectCellEditor",
    cellEditorParams: { values: ["not_started", "in_progress", "completed"] },
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
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
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

/* ── Deliverable column defs ── */
const deliverableColDefs = [
  {
    field: "project_phase_id", headerName: "단계", width: 100,
    valueFormatter: (params) => {
      const ph = _phases.find((p) => p.id === params.value);
      return ph ? (PHASE_TYPE_MAP[ph.phase_type] || ph.phase_type) : params.value;
    },
  },
  { field: "name", headerName: "산출물명", flex: 1, minWidth: 200, editable: true },
  {
    field: "is_submitted", headerName: "제출", width: 80,
    editable: true,
    cellEditor: "agSelectCellEditor",
    cellEditorParams: { values: [true, false] },
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "badge " + (params.value ? "badge-active" : "badge-planned");
      span.textContent = params.value ? "제출" : "미제출";
      return span;
    },
  },
  { field: "submitted_at", headerName: "제출일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  { field: "description", headerName: "설명", width: 200 },
  { field: "note", headerName: "비고", width: 150, editable: true },
  {
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
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

function toMonthValue(value) {
  if (!value) return null;
  return value.length >= 7 ? value.slice(0, 7) : value;
}

/* ═══════════════════════════════════════════
   Project list
   ═══════════════════════════════════════════ */

async function loadPeriods() {
  const cid = getCtxPartnerId();
  if (!cid) {
    _periodRows = [];
    applyProjectFilters();
    return;
  }
  try {
    _periodRows = await apiFetch("/api/v1/contract-periods?partner_id=" + cid);
    applyProjectFilters();
  } catch (err) { showToast(err.message, "error"); }
}

function applyProjectFilters() {
  if (!gridApi) return;
  const activeOnly = document.getElementById("chk-active-projects").checked;
  const rows = activeOnly ? _periodRows.filter((row) => !row.is_completed) : _periodRows;
  gridApi.setGridOption("rowData", rows);
}

function initListGrids() {
  if (_listInitialized) return;
  _listInitialized = true;
  gridApi = agGrid.createGrid(document.getElementById("grid-projects"), {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (d) => {
        if (window.setCtxProject) {
          window.setCtxProject(d.id, d.period_code, d.contract_name);
        }
        showProjectDetail(d);
      },
      onEdit: (d) => {
        if (window.setCtxProject) {
          window.setCtxProject(d.id, d.period_code, d.contract_name);
        }
        showProjectDetail(d);
      },
    }),
  });
}

/* ═══════════════════════════════════════════
   Detail panel layout (mirrors asset pattern)
   ═══════════════════════════════════════════ */

function syncProjectLayoutState(isOpen) {
  const layout = document.getElementById("project-layout");
  const panel = document.getElementById("project-detail-panel");
  const shell = document.getElementById("project-detail-shell");
  const empty = document.getElementById("project-detail-empty");
  const splitter = document.getElementById("project-splitter");
  const handle = document.getElementById("btn-minimize-detail");
  if (!layout || !panel || !shell || !empty || !splitter || !handle) return;
  layout.classList.toggle("is-detail-open", isOpen);
  panel.classList.toggle("is-hidden", !isOpen);
  shell.classList.toggle("is-hidden", !isOpen || !_selectedProject);
  empty.classList.toggle("is-hidden", isOpen && !!_selectedProject);
  splitter.classList.toggle("is-hidden", !isOpen);
  handle.textContent = isOpen ? "\u276E" : "\u276F";
  localStorage.setItem(PROJECT_DETAIL_OPEN_KEY, isOpen ? "1" : "0");
}

function initProjectSplitter() {
  const splitter = document.getElementById("project-splitter");
  const layout = document.getElementById("project-layout");
  const listPanel = layout?.querySelector(".asset-list-panel");
  if (!splitter || !layout || !listPanel) return;

  let dragging = false;

  splitter.addEventListener("mousedown", (event) => {
    if (!layout.classList.contains("is-detail-open")) return;
    event.preventDefault();
    dragging = true;
    splitter.classList.add("is-dragging");
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  });

  document.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const pct = Math.min(Math.max(x / rect.width * 100, 25), 75);
    layout.style.setProperty("--asset-list-width", pct + "%");
    localStorage.setItem(PROJECT_LIST_WIDTH_KEY, pct.toFixed(1));
  });

  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  });

  // Restore saved width
  const savedWidth = localStorage.getItem(PROJECT_LIST_WIDTH_KEY);
  if (savedWidth) {
    layout.style.setProperty("--asset-list-width", savedWidth + "%");
  }
}

/* ═══════════════════════════════════════════
   Show project detail (inline panel)
   ═══════════════════════════════════════════ */

function showProjectDetail(project) {
  _selectedProject = project;
  syncProjectLayoutState(true);

  // Update header
  document.getElementById("detail-project-name").textContent = project.contract_name || project.period_code || "";

  // Show shell, hide empty
  document.getElementById("project-detail-shell").classList.remove("is-hidden");
  document.getElementById("project-detail-empty").classList.add("is-hidden");

  // Render info card
  renderProjectInfo(project);

  // Init phase/deliverable grids (once)
  if (!phaseGridApi) {
    initDetailGrids();
  }

  // Load phases + deliverables
  loadPhases();
}

function renderProjectInfo(p) {
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
}

/* ── Phase timeline ── */
function renderPhaseTimeline(phaseList) {
  const container = document.getElementById("phase-timeline");
  if (!container) return;
  if (!phaseList || phaseList.length === 0) {
    container.textContent = "";
    const msg = document.createElement("p");
    msg.className = "text-muted";
    msg.textContent = "등록된 단계가 없습니다.";
    container.appendChild(msg);
    return;
  }

  container.textContent = "";
  phaseList.forEach((p, i) => {
    const statusClass = p.status === "completed" ? "phase-done" :
                        p.status === "in_progress" ? "phase-active" : "phase-pending";
    const icon = p.status === "completed" ? "\u25CF" :
                 p.status === "in_progress" ? "\u25D0" : "\u25CB";
    const label = PHASE_TYPE_MAP[p.phase_type] || p.phase_type || "";

    const step = document.createElement("div");
    step.className = "phase-step " + statusClass;

    const iconSpan = document.createElement("span");
    iconSpan.className = "phase-icon";
    iconSpan.textContent = icon;
    step.appendChild(iconSpan);

    const labelSpan = document.createElement("span");
    labelSpan.className = "phase-label";
    labelSpan.textContent = label;
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

/* ═══════════════════════════════════════════
   Phase & Deliverable grids (detail panel)
   ═══════════════════════════════════════════ */

function initDetailGrids() {
  phaseGridApi = agGrid.createGrid(document.getElementById("grid-phases"), {
    columnDefs: phaseColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openEditPhase(data),
      onCellValueChanged: handlePhaseCellChanged,
    }),
  });

  deliverableGridApi = agGrid.createGrid(document.getElementById("grid-deliverables"), {
    columnDefs: deliverableColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openEditDeliverable(data),
      onCellValueChanged: handleDeliverableCellChanged,
    }),
  });
}

async function loadPhases() {
  if (!_selectedProject) return;
  try {
    _phases = await apiFetch(`/api/v1/contract-periods/${_selectedProject.id}/phases`);
    if (phaseGridApi) phaseGridApi.setGridOption("rowData", _phases);
    populatePhaseDropdown();
    renderPhaseTimeline(_phases);
    loadDeliverables();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function populatePhaseDropdown() {
  const select = document.getElementById("deliverable-phase-id");
  if (!select) return;
  while (select.firstChild) select.removeChild(select.firstChild);
  _phases.forEach((ph) => {
    const opt = document.createElement("option");
    opt.value = ph.id;
    opt.textContent = PHASE_TYPE_MAP[ph.phase_type] || ph.phase_type;
    select.appendChild(opt);
  });
}

async function loadDeliverables() {
  if (!_selectedProject || !deliverableGridApi) return;
  try {
    const allDeliverables = [];
    for (const ph of _phases) {
      const items = await apiFetch(`/api/v1/period-phases/${ph.id}/deliverables`);
      allDeliverables.push(...items);
    }
    deliverableGridApi.setGridOption("rowData", allDeliverables);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Inline edit handlers ── */
async function handlePhaseCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/period-phases/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
    renderPhaseTimeline(_phases);
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    phaseGridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}

async function handleDeliverableCellChanged(event) {
  const { data, colDef, newValue, oldValue } = event;
  if (newValue === oldValue || !data.id) return;
  try {
    await apiFetch(`/api/v1/period-deliverables/${data.id}`, {
      method: "PATCH",
      body: { [colDef.field]: newValue },
    });
    showToast("저장되었습니다.", "success");
  } catch (err) {
    showToast(err.message, "error");
    data[colDef.field] = oldValue;
    deliverableGridApi.refreshCells({ rowNodes: [event.node], force: true });
  }
}

/* ═══════════════════════════════════════════
   Phase Modal CRUD
   ═══════════════════════════════════════════ */

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
  if (!_selectedProject) { showToast("프로젝트를 먼저 선택하세요.", "warning"); return; }
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
  if (!_selectedProject) return;
  const phaseId = document.getElementById("phase-id").value;
  const payload = {
    contract_period_id: _selectedProject.id,
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
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ═══════════════════════════════════════════
   Deliverable Modal CRUD
   ═══════════════════════════════════════════ */

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
  if (!_selectedProject) { showToast("프로젝트를 먼저 선택하세요.", "warning"); return; }
  if (_phases.length === 0) { showToast("단계를 먼저 등록하세요.", "warning"); return; }
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

/* ═══════════════════════════════════════════
   Period CRUD Modal (project create/edit)
   ═══════════════════════════════════════════ */

const modal = document.getElementById("modal-project");
const classificationGroup = document.getElementById("project-classification-group");
const classificationSourceWrapEl = document.getElementById("project-classification-source-wrap");
const classificationSourceEl = document.getElementById("project-classification-source");
const classificationHintEl = document.getElementById("project-classification-hint");

function resetForm() {
  document.getElementById("project-id").value = "";
  document.getElementById("project-code").value = "";
  document.getElementById("project-name").value = "";
  document.getElementById("project-completed").checked = false;
  document.getElementById("start-date").value = "";
  document.getElementById("end-date").value = "";
  document.getElementById("project-desc").value = "";
  classificationSourceEl.textContent = "";
  classificationHintEl.textContent = "선택한 프리셋은 프로젝트별 자산 분류 표시 기준으로 사용됩니다.";
  setElementHidden(classificationGroup, false);
  setElementHidden(classificationSourceWrapEl, false);
}

async function openCreateModal() {
  if (!getCtxPartnerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  resetForm();
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById("start-date").value = today;
  document.getElementById("end-date").value = today;
  document.getElementById("modal-project-title").textContent = "프로젝트 등록";
  document.getElementById("btn-save-project").textContent = "등록";
  await ensureClassificationLayouts();
  refreshClassificationSourceOptions();
  modal.showModal();
}

function openEditModal(period) {
  document.getElementById("project-id").value = period.id;
  document.getElementById("project-code").value = period.contract_code || '';
  document.getElementById("project-name").value = period.contract_name ? period.contract_name + ' (' + period.period_label + ')' : '';
  document.getElementById("project-completed").checked = !!period.is_completed;
  document.getElementById("start-date").value = period.start_month ? period.start_month.slice(0, 10) : "";
  document.getElementById("end-date").value = period.end_month ? period.end_month.slice(0, 10) : "";
  document.getElementById("project-desc").value = period.description || "";
  setElementHidden(classificationGroup, true);
  document.getElementById("modal-project-title").textContent = "프로젝트 수정";
  document.getElementById("btn-save-project").textContent = "저장";
  modal.showModal();
}

async function ensureClassificationLayouts() {
  if (_classificationLayouts) return _classificationLayouts;
  _classificationLayouts = await apiFetch("/api/v1/classification-layouts?scope_type=global&active_only=true");
  return _classificationLayouts;
}

function refreshClassificationSourceOptions() {
  setElementHidden(classificationSourceWrapEl, false);
  classificationSourceEl.textContent = "";

  const choices = _classificationLayouts || [];
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = choices.length ? "레이아웃 프리셋 선택" : "사용 가능한 프리셋 없음";
  classificationSourceEl.appendChild(placeholder);

  for (const item of choices) {
    const option = document.createElement("option");
    option.value = String(item.id);
    const meta = [];
    if (item.depth_count != null) meta.push(`${item.depth_count}단계`);
    option.textContent = meta.length ? `${item.name} (${meta.join(" / ")})` : item.name;
    classificationSourceEl.appendChild(option);
  }

  if (choices.length) {
    const preferred = choices.find((item) => item.is_default) || choices[0];
    classificationSourceEl.value = String(preferred.id);
  }
}

async function assignProjectClassificationLayout(periodId) {
  if (!classificationSourceEl.value) {
    throw new Error("레이아웃 프리셋을 선택하세요.");
  }
  return apiFetch(`/api/v1/classification-layouts/projects/${periodId}`, {
    method: "POST",
    body: { layout_id: Number(classificationSourceEl.value) },
  });
}

async function savePeriod() {
  const cid = getCtxPartnerId();
  if (!cid) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const periodId = document.getElementById("project-id").value;
  const projectName = document.getElementById("project-name").value.trim();
  if (!projectName) {
    showToast("사업명을 입력하세요.", "warning");
    return;
  }
  const payload = {
    description: document.getElementById("project-desc").value || null,
    start_month: toMonthValue(document.getElementById("start-date").value),
    end_month: toMonthValue(document.getElementById("end-date").value),
    is_completed: document.getElementById("project-completed").checked,
  };
  try {
    if (periodId) {
      await apiFetch("/api/v1/contract-periods/" + periodId, { method: "PATCH", body: payload });
      showToast("프로젝트가 수정되었습니다.");
    } else {
      const contract = await apiFetch("/api/v1/contracts", {
        method: "POST",
        body: {
          contract_name: projectName,
          contract_type: "ETC",
          end_partner_id: cid,
          status: "active",
          notes: payload.description,
        },
      });
      const startDate = document.getElementById("start-date").value || null;
      const periodYear = startDate ? Number(startDate.slice(0, 4)) : new Date().getFullYear();
      const createdPeriod = await apiFetch(`/api/v1/contracts/${contract.id}/periods`, {
        method: "POST",
        body: {
          period_year: periodYear,
          stage: "50%",
          start_month: payload.start_month,
          end_month: payload.end_month,
          description: payload.description,
          partner_id: cid,
          is_planned: true,
        },
      });
      if (payload.is_completed) {
        await apiFetch(`/api/v1/contract-periods/${createdPeriod.id}`, {
          method: "PATCH",
          body: { is_completed: true },
        });
      }
      await assignProjectClassificationLayout(createdPeriod.id);
      showToast("프로젝트가 등록되었습니다.");
    }
    modal.close();
    loadPeriods();
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
        if (_selectedProject && _selectedProject.id === period.id) {
          _selectedProject = null;
          syncProjectLayoutState(false);
        }
        loadPeriods();
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

/* ═══════════════════════════════════════════
   Events
   ═══════════════════════════════════════════ */

document.addEventListener("DOMContentLoaded", () => {
  const activeOnlyCheckbox = document.getElementById("chk-active-projects");
  const savedActiveOnly = localStorage.getItem(ACTIVE_PROJECTS_ONLY_KEY);
  if (savedActiveOnly != null) {
    activeOnlyCheckbox.checked = savedActiveOnly === "true";
  }
  initListGrids();
  initProjectSplitter();

  // Restore detail panel state
  const savedOpen = localStorage.getItem(PROJECT_DETAIL_OPEN_KEY);
  if (savedOpen === "1" && _selectedProject) {
    syncProjectLayoutState(true);
  }

  // ctx-changed: reload list
  const _initTimer = setTimeout(() => loadPeriods(), 300);
  window.addEventListener("ctx-changed", () => {
    clearTimeout(_initTimer);
    loadPeriods();
  }, { once: true });
});

/* Project list buttons */
document.getElementById("btn-add-project").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-project").addEventListener("click", () => modal.close());
document.getElementById("btn-save-project").addEventListener("click", savePeriod);
document.getElementById("chk-active-projects").addEventListener("change", (event) => {
  localStorage.setItem(ACTIVE_PROJECTS_ONLY_KEY, event.target.checked ? "true" : "false");
  applyProjectFilters();
});

/* Phase modal buttons */
document.getElementById("btn-add-phase").addEventListener("click", openCreatePhase);
document.getElementById("btn-cancel-phase").addEventListener("click", () => phaseModal.close());
document.getElementById("btn-save-phase").addEventListener("click", savePhase);

/* Deliverable modal buttons */
document.getElementById("btn-add-deliverable").addEventListener("click", openCreateDeliverable);
document.getElementById("btn-cancel-deliverable").addEventListener("click", () => deliverableModal.close());
document.getElementById("btn-save-deliverable").addEventListener("click", saveDeliverable);

/* Detail panel toggle */
document.getElementById("btn-minimize-detail").addEventListener("click", () => {
  const layout = document.getElementById("project-layout");
  const isOpen = layout.classList.contains("is-detail-open");
  syncProjectLayoutState(!isOpen);
});

/* Context changed: reload list */
window.addEventListener("ctx-changed", () => {
  loadPeriods();
});
