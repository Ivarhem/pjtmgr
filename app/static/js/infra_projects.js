/* ── 프로젝트 목록 ── */

const columnDefs = [
  { field: "period_code", headerName: "기간코드", width: 160, sort: "asc" },
  { field: "contract_name", headerName: "사업명", flex: 1, minWidth: 200 },
  {
    field: "is_completed", headerName: "사업완료여부", width: 120,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = params.value ? "badge badge-completed" : "badge badge-active";
      span.textContent = params.value ? "완료" : "진행중";
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
let _periodRows = [];
let _classificationLayouts = null;
const ACTIVE_PROJECTS_ONLY_KEY = "infra_projects_active_only_v1";

function toMonthValue(value) {
  if (!value) return null;
  return value.length >= 7 ? value.slice(0, 7) : value;
}

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
    onRowClicked: (e) => {
      const d = e.data;
      if (d && d.id) {
        // context 설정 후 상세 페이지로 이동
        if (window.setCtxProject) {
          window.setCtxProject(d.id, d.period_code, d.contract_name);
        }
        window.location.href = "/periods/" + d.id;
      }
    },
  });
}

/* ── Period CRUD Modal ── */
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
  classificationSourceEl.innerHTML = "";
  classificationHintEl.textContent = "선택한 프리셋은 프로젝트별 자산 분류 표시 기준으로 사용됩니다.";
  classificationGroup.hidden = false;
  classificationSourceWrapEl.hidden = false;
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
  classificationGroup.hidden = true;
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
  classificationSourceWrapEl.hidden = false;
  classificationSourceEl.innerHTML = "";

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
  return apiFetch(`/api/v1/projects/${periodId}/classification-layout`, {
    method: "PUT",
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
        loadPeriods();
      } catch (err) { showToast(err.message, "error"); }
    }
  );
}

/* ── Events ── */

document.addEventListener("DOMContentLoaded", () => {
  const activeOnlyCheckbox = document.getElementById("chk-active-projects");
  const savedActiveOnly = localStorage.getItem(ACTIVE_PROJECTS_ONLY_KEY);
  if (savedActiveOnly != null) {
    activeOnlyCheckbox.checked = savedActiveOnly === "true";
  }
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
document.getElementById("chk-active-projects").addEventListener("change", (event) => {
  localStorage.setItem(ACTIVE_PROJECTS_ONLY_KEY, event.target.checked ? "true" : "false");
  applyProjectFilters();
});

window.addEventListener("ctx-changed", () => loadPeriods());
