/* ── 케이블 배선도 (Port Maps) ── */

const PORTMAP_STATUS_MAP = {
  required: "필요",
  open: "오픈",
  closed: "차단",
  pending: "대기",
};

const columnDefs = [
  { field: "seq", headerName: "순번", width: 70 },
  { field: "cable_no", headerName: "케이블번호", width: 110 },
  { field: "connection_type", headerName: "연결유형", width: 110 },
  { field: "src_hostname", headerName: "출발 호스트", width: 130 },
  { field: "src_port_name", headerName: "출발 포트", width: 100 },
  { field: "src_zone", headerName: "출발 존", width: 90 },
  { field: "dst_hostname", headerName: "도착 호스트", width: 130 },
  { field: "dst_port_name", headerName: "도착 포트", width: 100 },
  { field: "dst_zone", headerName: "도착 존", width: 90 },
  { field: "cable_type", headerName: "케이블종류", width: 100 },
  { field: "cable_speed", headerName: "속도", width: 80 },
  { field: "purpose", headerName: "용도", flex: 1, minWidth: 120 },
  {
    field: "status",
    headerName: "상태",
    width: 80,
    cellRenderer: (params) => {
      const label = PORTMAP_STATUS_MAP[params.value] || params.value;
      const span = document.createElement("span");
      span.className = "badge badge-" + params.value;
      span.textContent = label;
      return span;
    },
  },
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
      btnEdit.addEventListener("click", () => openEditModal(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deletePortMap(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
    sortable: false,
    filter: false,
  },
];

let gridApi;
let currentProjectId = null;

/* ── Data Loading ── */

async function loadPortMaps() {
  if (!currentProjectId) {
    gridApi.setGridOption("rowData", []);
    return;
  }
  try {
    const data = await apiFetch(`/api/v1/projects/${currentProjectId}/port-maps`);
    gridApi.setGridOption("rowData", data);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function loadProjects() {
  try {
    const projects = await apiFetch("/api/v1/projects");
    const filterSelect = document.getElementById("filter-project");
    const modalSelect = document.getElementById("portmap-project-id");

    // Clear existing options (keep placeholder for filter)
    while (filterSelect.options.length > 1) filterSelect.remove(1);
    while (modalSelect.firstChild) modalSelect.removeChild(modalSelect.firstChild);

    projects.forEach((p) => {
      const text = p.project_code + " - " + p.project_name;

      const opt1 = document.createElement("option");
      opt1.value = p.id;
      opt1.textContent = text;
      filterSelect.appendChild(opt1);

      const opt2 = document.createElement("option");
      opt2.value = p.id;
      opt2.textContent = text;
      modalSelect.appendChild(opt2);
    });

    // Auto-select first project if available
    if (projects.length > 0) {
      filterSelect.value = projects[0].id;
      currentProjectId = projects[0].id;
      loadPortMaps();
    }
  } catch (err) {
    showToast("프로젝트를 불러올 수 없습니다.", "error");
  }
}

function initGrid() {
  gridApi = agGrid.createGrid(document.getElementById("grid-portmaps"), {
    columnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
  });
  loadProjects();
}

/* ── Field Helpers ── */

// All text/number input fields in the modal (id -> payload key)
const TEXT_FIELDS = [
  ["portmap-seq", "seq", "number"],
  ["portmap-cable-no", "cable_no", "text"],
  ["portmap-cable-request", "cable_request", "text"],
  ["portmap-purpose", "purpose", "text"],
  ["portmap-summary", "summary", "text"],
  // src
  ["portmap-src-mid", "src_mid", "text"],
  ["portmap-src-rack-no", "src_rack_no", "text"],
  ["portmap-src-rack-unit", "src_rack_unit", "text"],
  ["portmap-src-vendor", "src_vendor", "text"],
  ["portmap-src-model", "src_model", "text"],
  ["portmap-src-hostname", "src_hostname", "text"],
  ["portmap-src-cluster", "src_cluster", "text"],
  ["portmap-src-slot", "src_slot", "text"],
  ["portmap-src-port-name", "src_port_name", "text"],
  ["portmap-src-service-name", "src_service_name", "text"],
  ["portmap-src-zone", "src_zone", "text"],
  ["portmap-src-vlan", "src_vlan", "text"],
  ["portmap-src-ip", "src_ip", "text"],
  // dst
  ["portmap-dst-mid", "dst_mid", "text"],
  ["portmap-dst-rack-no", "dst_rack_no", "text"],
  ["portmap-dst-rack-unit", "dst_rack_unit", "text"],
  ["portmap-dst-vendor", "dst_vendor", "text"],
  ["portmap-dst-model", "dst_model", "text"],
  ["portmap-dst-hostname", "dst_hostname", "text"],
  ["portmap-dst-cluster", "dst_cluster", "text"],
  ["portmap-dst-slot", "dst_slot", "text"],
  ["portmap-dst-port-name", "dst_port_name", "text"],
  ["portmap-dst-service-name", "dst_service_name", "text"],
  ["portmap-dst-zone", "dst_zone", "text"],
  ["portmap-dst-vlan", "dst_vlan", "text"],
  ["portmap-dst-ip", "dst_ip", "text"],
];

const SELECT_FIELDS = [
  ["portmap-connection-type", "connection_type", ""],
  ["portmap-cable-type", "cable_type", ""],
  ["portmap-cable-speed", "cable_speed", ""],
  ["portmap-duplex", "duplex", ""],
  ["portmap-cable-category", "cable_category", ""],
  ["portmap-status", "status", "required"],
];

/* ── Modal ── */
const modal = document.getElementById("modal-portmap");

function resetForm() {
  document.getElementById("portmap-id").value = "";

  // Reset project to current filter selection
  const projSelect = document.getElementById("portmap-project-id");
  if (currentProjectId) projSelect.value = currentProjectId;

  // Reset text/number fields
  TEXT_FIELDS.forEach(([elId]) => {
    document.getElementById(elId).value = "";
  });

  // Reset selects to defaults
  SELECT_FIELDS.forEach(([elId, , defaultVal]) => {
    document.getElementById(elId).value = defaultVal;
  });

  document.getElementById("portmap-note").value = "";
}

function openCreateModal() {
  resetForm();
  document.getElementById("modal-portmap-title").textContent = "배선 등록";
  document.getElementById("btn-save-portmap").textContent = "등록";
  modal.showModal();
}

function openEditModal(pm) {
  document.getElementById("portmap-id").value = pm.id;
  document.getElementById("portmap-project-id").value = pm.project_id;

  // Populate text/number fields
  TEXT_FIELDS.forEach(([elId, key, type]) => {
    const val = pm[key];
    document.getElementById(elId).value = val != null ? val : "";
  });

  // Populate selects
  SELECT_FIELDS.forEach(([elId, key, defaultVal]) => {
    document.getElementById(elId).value = pm[key] || defaultVal;
  });

  document.getElementById("portmap-note").value = pm.note || "";

  document.getElementById("modal-portmap-title").textContent = "배선 수정";
  document.getElementById("btn-save-portmap").textContent = "저장";
  modal.showModal();
}

async function savePortMap() {
  const pmId = document.getElementById("portmap-id").value;
  const payload = {
    project_id: Number(document.getElementById("portmap-project-id").value),
    // Legacy fields set to null
    protocol: null,
    port: null,
    src_asset_id: null,
    dst_asset_id: null,
  };

  // Collect text/number fields
  TEXT_FIELDS.forEach(([elId, key, type]) => {
    const raw = document.getElementById(elId).value.trim();
    if (type === "number") {
      payload[key] = raw ? Number(raw) : null;
    } else {
      payload[key] = raw || null;
    }
  });

  // Collect select fields
  SELECT_FIELDS.forEach(([elId, key]) => {
    const raw = document.getElementById(elId).value;
    payload[key] = raw || null;
  });

  payload.note = document.getElementById("portmap-note").value.trim() || null;

  try {
    if (pmId) {
      await apiFetch(`/api/v1/port-maps/${pmId}`, { method: "PATCH", body: payload });
      showToast("배선이 수정되었습니다.");
    } else {
      const projId = payload.project_id;
      await apiFetch(`/api/v1/projects/${projId}/port-maps`, { method: "POST", body: payload });
      showToast("배선이 등록되었습니다.");
    }
    modal.close();
    loadPortMaps();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deletePortMap(pm) {
  confirmDelete(
    "이 배선을 삭제하시겠습니까?",
    async () => {
      try {
        await apiFetch(`/api/v1/port-maps/${pm.id}`, { method: "DELETE" });
        showToast("배선이 삭제되었습니다.");
        loadPortMaps();
      } catch (err) {
        showToast(err.message, "error");
      }
    }
  );
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", initGrid);
document.getElementById("btn-add-portmap").addEventListener("click", openCreateModal);
document.getElementById("btn-cancel-portmap").addEventListener("click", () => modal.close());
document.getElementById("btn-save-portmap").addEventListener("click", savePortMap);
document.getElementById("filter-project").addEventListener("change", (e) => {
  currentProjectId = e.target.value ? Number(e.target.value) : null;
  loadPortMaps();
});

