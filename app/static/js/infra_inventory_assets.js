/* ── 자산 횡단 검색 (인벤토리) ── */

const ASSET_TYPE_MAP = {
  server: "서버",
  network: "네트워크",
  security: "보안장비",
  storage: "스토리지",
  other: "기타",
};

const ASSET_STATUS_MAP = {
  planned: "계획",
  active: "운영중",
  decommissioned: "폐기",
};

const ENV_MAP = {
  prod: "운영",
  dev: "개발",
  staging: "스테이징",
  dr: "DR",
};

const columnDefs = [
  {
    field: "project_code",
    headerName: "프로젝트",
    width: 130,
    cellRenderer: (p) => {
      if (!p.data) return "";
      const link = document.createElement("a");
      link.href = `/projects/${p.data.project_id}`;
      link.textContent = p.value || "";
      return link;
    },
  },
  { field: "project_name", headerName: "프로젝트명", width: 160 },
  { field: "asset_name", headerName: "자산명", flex: 1, minWidth: 180, sort: "asc" },
  {
    field: "asset_type",
    headerName: "유형",
    width: 110,
    valueFormatter: (p) => ASSET_TYPE_MAP[p.value] || p.value,
  },
  { field: "vendor", headerName: "제조사", width: 120 },
  { field: "model", headerName: "모델", width: 120 },
  { field: "hostname", headerName: "호스트명", width: 140 },
  { field: "service_ip", headerName: "서비스 IP", width: 130 },
  {
    field: "environment",
    headerName: "환경",
    width: 90,
    valueFormatter: (p) => ENV_MAP[p.value] || p.value,
  },
  { field: "location", headerName: "위치", width: 120 },
  { field: "center", headerName: "센터", width: 100 },
  { field: "zone", headerName: "존", width: 90 },
  { field: "category", headerName: "분류", width: 100 },
  {
    field: "status",
    headerName: "상태",
    width: 100,
    cellRenderer: (params) => {
      const label = ASSET_STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
  },
];

let gridApi;

async function loadInventory() {
  const params = new URLSearchParams();
  const projectId = document.getElementById("filter-project").value;
  const assetType = document.getElementById("filter-type").value;
  const status = document.getElementById("filter-status").value;
  const q = document.getElementById("filter-search").value.trim();

  if (projectId) params.set("period_id", projectId);
  if (assetType) params.set("asset_type", assetType);
  if (status) params.set("status", status);
  if (q) params.set("q", q);

  try {
    const qs = params.toString();
    const url = "/api/v1/assets/inventory" + (qs ? "?" + qs : "");
    const data = await apiFetch(url);
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadProjectFilter() {
  try {
    const projects = await apiFetch("/api/v1/projects");
    const select = document.getElementById("filter-project");
    const pinnedId = await getPinnedProjectId();
    projects.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.project_code + " - " + p.project_name;
      if (pinnedId && String(p.id) === pinnedId) opt.selected = true;
      select.appendChild(opt);
    });
  } catch (_) {
    /* ignore */
  }
}

function initGrid() {
  const gridDiv = document.getElementById("grid-inventory-assets");
  gridApi = agGrid.createGrid(gridDiv, {
    columnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    animateRows: true,
    enableCellTextSelection: true,
  });
  loadProjectFilter().then(() => loadInventory());
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-search").addEventListener("click", loadInventory);
document.getElementById("filter-search").addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadInventory();
});

// ── 자산 Import ──
document.getElementById("btn-asset-import-toggle")?.addEventListener("click", () => {
  const panel = document.getElementById("asset-import-panel");
  panel.classList.toggle("hidden");
  if (!panel.classList.contains("hidden")) _loadImportProjects();
});
document.getElementById("btn-asset-import-close")?.addEventListener("click", () => {
  document.getElementById("asset-import-panel").classList.add("hidden");
});

function _loadImportProjects() {
  const sel = document.getElementById("asset-import-project");
  if (sel.options.length > 1) return;
  apiFetch("/api/v1/projects").then(projects => {
    projects.forEach(p => {
      const o = document.createElement("option");
      o.value = p.id; o.textContent = p.project_code + " — " + p.project_name;
      sel.appendChild(o);
    });
  }).catch(() => {});
}

function setImportResultState(container, message, state) {
  container.textContent = message;
  container.classList.remove("infra-text-danger", "infra-text-success");
  if (state === "error") {
    container.classList.add("infra-text-danger");
  } else if (state === "success") {
    container.classList.add("infra-text-success");
  }
}

document.getElementById("btn-asset-import-run")?.addEventListener("click", async () => {
  const projectId = document.getElementById("asset-import-project").value;
  const file = document.getElementById("asset-import-file").files[0];
  if (!projectId) { showToast("프로젝트를 선택하세요.", "warning"); return; }
  if (!file) { showToast("파일을 선택하세요.", "warning"); return; }
  const fd = new FormData();
  fd.append("file", file);
  fd.append("partner_id", getCtxPartnerId());
  fd.append("domain", "inventory");
  fd.append("on_duplicate", document.getElementById("asset-import-dup").value);
  const btn = document.getElementById("btn-asset-import-run");
  btn.disabled = true; btn.textContent = "Import 중...";
  const r = document.getElementById("asset-import-result");
  setImportResultState(r, "", null);
  try {
    const res = await fetch("/api/v1/infra-excel/import/confirm", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) {
      setImportResultState(r, "오류: " + (data.detail || "실패"), "error");
    } else {
      setImportResultState(r, "생성 " + data.created + "건, 건너뜀 " + data.skipped + "건", "success");
      loadInventory();
    }
  } catch (e) {
    setImportResultState(r, "실패: " + e.message, "error");
  } finally {
    btn.disabled = false; btn.textContent = "Import";
  }
});
