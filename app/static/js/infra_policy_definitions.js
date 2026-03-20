/* ── 정책 정의 관리 ── */

const policyColDefs = [
  { field: "policy_code", headerName: "정책 코드", width: 130, sort: "asc" },
  { field: "policy_name", headerName: "정책명", flex: 1, minWidth: 200 },
  { field: "category", headerName: "카테고리", width: 120 },
  { field: "security_domain", headerName: "보안 도메인", width: 130 },
  { field: "architecture_element", headerName: "아키텍처 요소", width: 130 },
  { field: "control_point", headerName: "통제 포인트", width: 130 },
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

async function loadPolicies() {
  try {
    const data = await apiFetch("/api/v1/policies");
    policyGridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function initGrid() {
  policyGridApi = agGrid.createGrid(document.getElementById("grid-policies"), {
    columnDefs: policyColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });
  loadPolicies();
}

/* ── Modal ── */
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
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-add-policy").addEventListener("click", openCreatePolicy);
document.getElementById("btn-cancel-policy").addEventListener("click", () => policyModal.close());
document.getElementById("btn-save-policy").addEventListener("click", savePolicy);
