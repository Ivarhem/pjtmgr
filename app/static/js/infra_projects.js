/* ── 프로젝트 목록 ── */

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
      btnEdit.addEventListener("click", (e) => { e.stopPropagation(); openEditModal(params.data); });
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger"; btnDel.textContent = "삭제";
      btnDel.addEventListener("click", (e) => { e.stopPropagation(); deletePeriod(params.data); });
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

function initListGrids() {
  if (_listInitialized) return;
  _listInitialized = true;
  gridApi = agGrid.createGrid(document.getElementById("grid-projects"), {
    columnDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single", animateRows: true, enableCellTextSelection: true,
    onRowClicked: (e) => {
      const d = e.data;
      if (d && d.id) {
        window.location.href = "/periods/" + d.id;
      }
    },
  });
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
        loadPeriods();
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

/* ── Events ── */

document.addEventListener("DOMContentLoaded", () => {
  initListGrids();
  // ctx-changed 이벤트 대기 후 목록 로드 (고객사 복원 후)
  const _initTimer = setTimeout(() => loadPeriods(), 300);
  window.addEventListener("ctx-changed", () => {
    clearTimeout(_initTimer);
    loadPeriods();
  }, { once: true });
});

document.getElementById("btn-add-project").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-project").addEventListener("click", () => modal.close());
document.getElementById("btn-save-project").addEventListener("click", savePeriod);

window.addEventListener("ctx-changed", () => loadPeriods());
