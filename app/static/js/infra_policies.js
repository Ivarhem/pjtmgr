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

