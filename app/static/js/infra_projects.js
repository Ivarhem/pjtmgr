/* ── 프로젝트 목록 (고객사 중심) ── */

const STATUS_MAP = {
  planned: "계획", active: "진행중", on_hold: "보류", completed: "완료",
};

const columnDefs = [
  { field: "project_code", headerName: "프로젝트 코드", width: 150, sort: "asc" },
  { field: "project_name", headerName: "프로젝트명", flex: 1, minWidth: 200 },
  {
    field: "status", headerName: "상태", width: 100,
    cellRenderer: (params) => {
      const label = STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
  },
  { field: "start_date", headerName: "시작일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  { field: "end_date", headerName: "종료일", width: 120, valueFormatter: (p) => fmtDate(p.value) },
  {
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm"; wrap.style.display = "inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary"; btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditModal(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger"; btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteProject(params.data));
      wrap.appendChild(btnEdit); wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

let gridApi;

async function loadProjects() {
  const cid = getCtxCustomerId();
  if (!cid) { gridApi.setGridOption("rowData", []); return; }
  try {
    const data = await apiFetch("/api/v1/projects?customer_id=" + cid);
    gridApi.setGridOption("rowData", data);
  } catch (err) { showToast(err.message, "error"); }
}

function initGrid() {
  gridApi = agGrid.createGrid(document.getElementById("grid-projects"), {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
    onRowDoubleClicked: (event) => {
      window.location.href = "/projects/" + event.data.id;
    },
  });
  loadProjects();
}

/* ── Modal ── */
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
  if (!getCtxCustomerId()) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  resetForm();
  document.getElementById("modal-project-title").textContent = "프로젝트 등록";
  document.getElementById("btn-save-project").textContent = "등록";
  modal.showModal();
}

function openEditModal(project) {
  document.getElementById("project-id").value = project.id;
  document.getElementById("project-code").value = project.project_code;
  document.getElementById("project-name").value = project.project_name;
  document.getElementById("project-status").value = project.status;
  document.getElementById("start-date").value = project.start_date || "";
  document.getElementById("end-date").value = project.end_date || "";
  document.getElementById("project-desc").value = project.description || "";
  document.getElementById("modal-project-title").textContent = "프로젝트 수정";
  document.getElementById("btn-save-project").textContent = "저장";
  modal.showModal();
}

async function saveProject() {
  const cid = getCtxCustomerId();
  if (!cid) { showToast("고객사를 먼저 선택하세요.", "warning"); return; }
  const projectId = document.getElementById("project-id").value;
  const payload = {
    project_code: document.getElementById("project-code").value,
    project_name: document.getElementById("project-name").value,
    customer_id: cid,
    status: document.getElementById("project-status").value,
    start_date: document.getElementById("start-date").value || null,
    end_date: document.getElementById("end-date").value || null,
    description: document.getElementById("project-desc").value || null,
  };

  try {
    if (projectId) {
      await apiFetch("/api/v1/projects/" + projectId, { method: "PATCH", body: payload });
      showToast("프로젝트가 수정되었습니다.");
    } else {
      await apiFetch("/api/v1/projects", { method: "POST", body: payload });
      showToast("프로젝트가 등록되었습니다.");
    }
    modal.close();
    loadProjects();
  } catch (err) { showToast(err.message, "error"); }
}

async function deleteProject(project) {
  confirmDelete(
    '프로젝트 "' + project.project_name + '"을(를) 삭제하시겠습니까?',
    async () => {
      try {
        await apiFetch("/api/v1/projects/" + project.id, { method: "DELETE" });
        showToast("프로젝트가 삭제되었습니다.");
        loadProjects();
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-add-project").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-project").addEventListener("click", () => modal.close());
document.getElementById("btn-save-project").addEventListener("click", saveProject);
window.addEventListener("ctx-changed", loadProjects);
