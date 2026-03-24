/* ── 프로젝트 현황판 (고객사 중심) ── */

const PHASE_LABELS = {
  analysis: "분석", design: "설계", build: "구축",
  test: "시험", stabilize: "안정화",
};

const projectColDefs = [
  { field: "project_code", headerName: "코드", width: 110, sort: "asc" },
  { field: "project_name", headerName: "프로젝트명", flex: 1, minWidth: 180 },
  { field: "status", headerName: "상태", width: 90 },
  { field: "current_phase", headerName: "현재 단계", width: 100,
    valueFormatter: p => PHASE_LABELS[p.value] || p.value || "-" },
  { field: "asset_count", headerName: "자산", width: 80, type: "numericColumn" },
  { field: "ip_count", headerName: "IP", width: 70, type: "numericColumn" },
  { field: "compliance_rate", headerName: "정책 준수율", width: 110, type: "numericColumn",
    valueFormatter: p => p.value != null ? p.value + "%" : "-" },
  { headerName: "산출물", width: 100,
    valueGetter: p => {
      const d = p.data;
      return d.deliverable_total > 0 ? d.deliverable_submitted + "/" + d.deliverable_total : "-";
    },
  },
];

const ncColDefs = [
  { field: "partner_name", headerName: "고객사", width: 130 },
  { field: "asset_id", headerName: "자산 ID", width: 90 },
  { field: "checked_by", headerName: "확인자", width: 120 },
  { field: "checked_date", headerName: "확인일", width: 110, valueFormatter: p => fmtDate(p.value) },
  { field: "exception_reason", headerName: "사유", flex: 1, minWidth: 150 },
];

let projectGridApi, ncGridApi;

async function loadDashboard() {
  const cid = getCtxPartnerId();
  try {
    const summaryUrl = cid
      ? "/api/v1/infra-dashboard/summary?partner_id=" + cid
      : "/api/v1/infra-dashboard/summary";
    const ncUrl = cid
      ? "/api/v1/infra-dashboard/non-compliant?partner_id=" + cid
      : "/api/v1/infra-dashboard/non-compliant";

    const [summary, unsubmitted, nonCompliant] = await Promise.all([
      apiFetch(summaryUrl),
      apiFetch(cid
        ? "/api/v1/infra-dashboard/unsubmitted?partner_id=" + cid
        : "/api/v1/infra-dashboard/unsubmitted"),
      apiFetch(ncUrl),
    ]);

    renderPhaseSummary(summary);
    renderAlerts(unsubmitted);
    projectGridApi.setGridOption("rowData", summary);
    ncGridApi.setGridOption("rowData", nonCompliant);
  } catch (err) { showToast(err.message, "error"); }
}

function renderPhaseSummary(projects) {
  document.getElementById("card-total").textContent = projects.length;
  const early = projects.filter(p =>
    p.current_phase === "analysis" || p.current_phase === "design"
  ).length;
  const build = projects.filter(p => p.current_phase === "build").length;
  const late = projects.filter(p =>
    p.current_phase === "test" || p.current_phase === "stabilize"
  ).length;
  document.getElementById("card-early").textContent = early || "0";
  document.getElementById("card-build").textContent = build || "0";
  document.getElementById("card-late").textContent = late || "0";
}

function renderAlerts(unsubmitted) {
  const section = document.getElementById("alert-section");
  const list = document.getElementById("alert-list");
  if (!unsubmitted || unsubmitted.length === 0) {
    section.classList.add("is-hidden");
    return;
  }
  section.classList.remove("is-hidden");
  document.getElementById("alert-title").textContent =
    "미제출 산출물 (" + unsubmitted.length + "건)";
  list.textContent = "";
  unsubmitted.forEach(d => {
    const li = document.createElement("li");
    const phase = PHASE_LABELS[d.phase_type] || d.phase_type;
    li.textContent = "[" + d.project_code + "] " + phase + " — " + d.name;
    list.appendChild(li);
  });
}

function initGrids() {
  projectGridApi = agGrid.createGrid(document.getElementById("grid-projects"), {
    columnDefs: projectColDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true, enableCellTextSelection: true,
  });
  ncGridApi = agGrid.createGrid(document.getElementById("grid-non-compliant"), {
    columnDefs: ncColDefs, rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true, enableCellTextSelection: true,
  });
  loadDashboard();
}

document.addEventListener("DOMContentLoaded", initGrids);
window.addEventListener("ctx-changed", loadDashboard);
