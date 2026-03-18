/* ── 프로젝트 상세 (단계 + 산출물) ── */

const PROJECT_ID = window.__PROJECT_ID__;

/* ── Tab switching ── */
function activateTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));
  document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
  document.getElementById(`tab-${tabId}`).classList.remove('hidden');
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

