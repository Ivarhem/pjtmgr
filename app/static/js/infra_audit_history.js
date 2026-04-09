/* ── 변경 이력 (고객사 스코프) ── */

const ACTION_MAP = { create: "생성", update: "수정", delete: "삭제" };
const ENTITY_MAP = {
  project: "프로젝트", asset: "자산", ip_subnet: "IP대역",
  port_map: "포트맵", policy: "정책", policy_assignment: "정책적용",
};

let gridApi;

function initGrid() {
  const colDefs = [
    { field: "created_at", headerName: "일시", width: 160,
      valueFormatter: (p) => fmtDate(p.value) + " " + (p.value ? p.value.slice(11, 19) : "") },
    { field: "user_name", headerName: "사용자", width: 120 },
    { field: "action", headerName: "동작", width: 80,
      valueFormatter: (p) => ACTION_MAP[p.value] || p.value },
    { field: "entity_type", headerName: "대상", width: 100,
      valueFormatter: (p) => ENTITY_MAP[p.value] || p.value },
    { field: "summary", headerName: "요약", flex: 1, minWidth: 250 },
  ];

  gridApi = agGrid.createGrid(document.getElementById("grid-history"), {
    columnDefs: colDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({ type: 'readonly' }),
  });
}

async function loadHistory() {
  const cid = getCtxPartnerId();
  if (!cid) { gridApi.setGridOption("rowData", []); return; }
  try {
    const qs = "?partner_id=" + cid;
    const data = await apiFetch("/api/v1/infra-dashboard/audit-log" + qs);
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    gridApi.setGridOption("rowData", []);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initGrid();
  setTimeout(() => loadHistory(), 400);
});

window.addEventListener("ctx-changed", () => {
  loadHistory();
});
