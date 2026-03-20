/* ── 정책 적용 현황 ── */

const ASSIGNMENT_STATUS_MAP = {
  not_checked: "미확인",
  compliant: "준수",
  non_compliant: "미준수",
  exception: "예외",
  not_applicable: "해당없음",
};

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
  { field: "evidence_note", headerName: "증적 메모", width: 150 },
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
let allAssignments = [];

/* ── Data Loading ── */
async function loadAssignments() {
  try {
    allAssignments = await apiFetch("/api/v1/policy-assignments");
    applyFilters();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function applyFilters() {
  const projectId = document.getElementById("filter-project").value;
  const status = document.getElementById("filter-status").value;
  let filtered = allAssignments;
  if (projectId) filtered = filtered.filter((a) => String(a.project_id) === projectId);
  if (status) filtered = filtered.filter((a) => a.status === status);
  assignGridApi.setGridOption("rowData", filtered);
}

async function loadComplianceSummary() {
  try {
    const summary = await apiFetch("/api/v1/infra-dashboard/summary");
    const container = document.getElementById("compliance-summary");
    while (container.firstChild) container.removeChild(container.firstChild);
    summary.forEach((proj) => {
      const card = document.createElement("div");
      card.className = "summary-card";
      const title = document.createElement("div");
      title.className = "summary-card-title";
      title.textContent = proj.project_code + " " + proj.project_name;
      const rate = document.createElement("div");
      rate.className = "summary-card-value";
      const pct = proj.policy_compliance_rate != null ? proj.policy_compliance_rate.toFixed(0) + "%" : "-";
      rate.textContent = pct;
      const label = document.createElement("div");
      label.className = "summary-card-label";
      label.textContent = "정책 준수율";
      card.appendChild(title);
      card.appendChild(rate);
      card.appendChild(label);
      container.appendChild(card);
    });
  } catch (_) {
    /* ignore */
  }
}

async function loadDropdowns() {
  try {
    const [projects, assets, policies] = await Promise.all([
      apiFetch("/api/v1/projects"),
      apiFetch("/api/v1/assets"),
      apiFetch("/api/v1/policies"),
    ]);

    // Filter dropdown
    const filterSelect = document.getElementById("filter-project");
    const pinnedId = await getPinnedProjectId();
    projects.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.project_code + " - " + p.project_name;
      if (pinnedId && String(p.id) === pinnedId) opt.selected = true;
      filterSelect.appendChild(opt);
    });

    // Modal dropdowns
    const projSelect = document.getElementById("assignment-project-id");
    while (projSelect.firstChild) projSelect.removeChild(projSelect.firstChild);
    projects.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.project_code + " - " + p.project_name;
      if (pinnedId && String(p.id) === pinnedId) opt.selected = true;
      projSelect.appendChild(opt);
    });

    const assetSelect = document.getElementById("assignment-asset-id");
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

function initGrid() {
  assignGridApi = agGrid.createGrid(document.getElementById("grid-assignments"), {
    columnDefs: assignColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });

  loadDropdowns().then(() => {
    loadAssignments();
    loadComplianceSummary();
  });
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
    loadComplianceSummary();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteAssignment(assign) {
  confirmDelete(
    "이 정책 적용을 삭제하시겠습니까?",
    async () => {
      try {
        await apiFetch(`/api/v1/policy-assignments/${assign.id}`, { method: "DELETE" });
        showToast("정책 적용이 삭제되었습니다.");
        loadAssignments();
        loadComplianceSummary();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-add-assignment").addEventListener("click", openCreateAssignment);
document.getElementById("btn-cancel-assignment").addEventListener("click", () => assignModal.close());
document.getElementById("btn-save-assignment").addEventListener("click", saveAssignment);
document.getElementById("btn-filter").addEventListener("click", applyFilters);
