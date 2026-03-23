/* ── 제품 카탈로그 ── */

let catalogGridApi, ifaceGridApi;
let currentProductId = null;

/* ── 목록 그리드 ── */

const catalogColDefs = [
  { field: "vendor", headerName: "제조사", width: 120, sort: "asc" },
  { field: "name", headerName: "모델명", flex: 1, minWidth: 160 },
  { field: "category", headerName: "분류", width: 100 },
  { field: "product_type", headerName: "유형", width: 90 },
  {
    field: "eosl_date", headerName: "EOSL", width: 110,
    valueFormatter: (p) => fmtDate(p.value),
    cellClassRules: {
      "cell-warn": (p) => {
        if (!p.value) return false;
        const d = new Date(p.value);
        const now = new Date();
        const sixMo = new Date();
        sixMo.setMonth(sixMo.getMonth() + 6);
        return d <= sixMo && d >= now;
      },
      "cell-danger": (p) => p.value && new Date(p.value) < new Date(),
    },
  },
];

function initCatalogGrid() {
  catalogGridApi = agGrid.createGrid(document.getElementById("grid-catalog"), {
    columnDefs: catalogColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    onRowClicked: (e) => selectProduct(e.data),
  });
}

async function loadCatalog() {
  try {
    const data = await apiFetch("/api/v1/product-catalog");
    catalogGridApi.setGridOption("rowData", data);
    // 분류 필터 갱신
    const cats = [...new Set(data.map(d => d.category).filter(Boolean))].sort();
    const sel = document.getElementById("catalog-category-filter");
    const current = sel.value;
    while (sel.options.length > 1) sel.remove(1);
    cats.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c;
      opt.textContent = c;
      sel.appendChild(opt);
    });
    sel.value = current;
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── 필터 ── */

function applyFilter() {
  const q = document.getElementById("catalog-search").value.toLowerCase();
  const cat = document.getElementById("catalog-category-filter").value;
  catalogGridApi.setGridOption("isExternalFilterPresent", () => !!(q || cat));
  catalogGridApi.setGridOption("doesExternalFilterPass", (node) => {
    const d = node.data;
    if (cat && d.category !== cat) return false;
    if (q && !(d.vendor?.toLowerCase().includes(q) || d.name?.toLowerCase().includes(q))) return false;
    return true;
  });
  catalogGridApi.onFilterChanged();
}

/* ── 상세 패널 ── */

async function selectProduct(product) {
  currentProductId = product.id;
  document.getElementById("detail-empty").classList.add("is-hidden");
  document.getElementById("detail-content").classList.remove("is-hidden");

  try {
    const detail = await apiFetch(`/api/v1/product-catalog/${product.id}`);
    renderDetail(detail);
  } catch (err) {
    showToast(err.message, "error");
  }
}

function _infoRow(label, value) {
  const row = document.createElement("div");
  row.className = "info-row";
  const lbl = document.createElement("span");
  lbl.className = "info-label";
  lbl.textContent = label;
  const val = document.createElement("span");
  val.className = "info-value";
  if (label === "참조 URL" && value && value !== "-") {
    const a = document.createElement("a");
    a.href = value;
    a.target = "_blank";
    a.textContent = value;
    val.appendChild(a);
  } else {
    val.textContent = value || "-";
  }
  row.appendChild(lbl);
  row.appendChild(val);
  return row;
}

function renderDetail(d) {
  document.getElementById("detail-title").textContent = `${d.vendor} ${d.name}`;

  // 기본정보 탭
  const infoGrid = document.getElementById("info-grid");
  infoGrid.replaceChildren();
  infoGrid.appendChild(_infoRow("제조사", d.vendor));
  infoGrid.appendChild(_infoRow("모델명", d.name));
  infoGrid.appendChild(_infoRow("제품유형", d.product_type));
  infoGrid.appendChild(_infoRow("분류", d.category));
  infoGrid.appendChild(_infoRow("참조 URL", d.reference_url || "-"));
  infoGrid.appendChild(_infoRow("등록일", fmtDate(d.created_at)));
  infoGrid.appendChild(_infoRow("수정일", fmtDate(d.updated_at)));

  // HW 스펙 탭
  const s = d.hardware_spec || {};
  document.getElementById("spec-size-unit").value = s.size_unit ?? "";
  document.getElementById("spec-width-mm").value = s.width_mm ?? "";
  document.getElementById("spec-height-mm").value = s.height_mm ?? "";
  document.getElementById("spec-depth-mm").value = s.depth_mm ?? "";
  document.getElementById("spec-weight-kg").value = s.weight_kg ?? "";
  document.getElementById("spec-power-count").value = s.power_count ?? "";
  document.getElementById("spec-power-type").value = s.power_type ?? "";
  document.getElementById("spec-power-watt").value = s.power_watt ?? "";
  document.getElementById("spec-cpu-summary").value = s.cpu_summary ?? "";
  document.getElementById("spec-memory-summary").value = s.memory_summary ?? "";
  document.getElementById("spec-throughput-summary").value = s.throughput_summary ?? "";
  document.getElementById("spec-os-firmware").value = s.os_firmware ?? "";
  document.getElementById("spec-spec-url").value = s.spec_url ?? "";

  // 인터페이스 탭
  if (ifaceGridApi) {
    ifaceGridApi.setGridOption("rowData", d.interfaces || []);
  }

  // EOSL 탭
  document.getElementById("eosl-eos-date").value = d.eos_date || "";
  document.getElementById("eosl-eosl-date").value = d.eosl_date || "";
  document.getElementById("eosl-eosl-note").value = d.eosl_note || "";
}

/* ── 탭 전환 ── */

function initTabs() {
  document.querySelectorAll(".catalog-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".catalog-tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".catalog-tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
    });
  });
}

/* ── 인터페이스 그리드 ── */

const ifaceColDefs = [
  { field: "interface_type", headerName: "유형", width: 120 },
  { field: "speed", headerName: "속도", width: 100 },
  { field: "count", headerName: "수량", width: 80 },
  { field: "connector_type", headerName: "커넥터", width: 110 },
  {
    field: "capacity_type", headerName: "구분", width: 80,
    cellRenderer: (p) => {
      const span = document.createElement("span");
      span.className = "badge badge-" + (p.value === "fixed" ? "active" : p.value === "base" ? "planned" : "on-hold");
      span.textContent = p.value === "fixed" ? "고정" : p.value === "base" ? "기본" : "최대";
      return span;
    },
  },
  { field: "note", headerName: "비고", flex: 1 },
  {
    headerName: "", width: 120, sortable: false, filter: false,
    cellRenderer: (params) => {
      const wrap = document.createElement("span");
      wrap.className = "gap-sm infra-inline-flex";
      const btnEdit = document.createElement("button");
      btnEdit.className = "btn btn-xs btn-secondary";
      btnEdit.textContent = "수정";
      btnEdit.addEventListener("click", () => openEditInterface(params.data));
      const btnDel = document.createElement("button");
      btnDel.className = "btn btn-xs btn-danger";
      btnDel.textContent = "삭제";
      btnDel.addEventListener("click", () => deleteInterface(params.data));
      wrap.appendChild(btnEdit);
      wrap.appendChild(btnDel);
      return wrap;
    },
  },
];

function initIfaceGrid() {
  ifaceGridApi = agGrid.createGrid(document.getElementById("grid-interfaces"), {
    columnDefs: ifaceColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true },
    animateRows: true,
    domLayout: "autoHeight",
  });
}

/* ── 제품 CRUD ── */

const productModal = document.getElementById("modal-product");

function openCreateProduct() {
  document.getElementById("product-id").value = "";
  document.getElementById("product-vendor").value = "";
  document.getElementById("product-name").value = "";
  document.getElementById("product-type").value = "hardware";
  document.getElementById("product-category").value = "";
  document.getElementById("product-reference-url").value = "";
  document.getElementById("modal-product-title").textContent = "제품 등록";
  document.getElementById("btn-save-product").textContent = "등록";
  productModal.showModal();
}

function openEditProduct() {
  if (!currentProductId) return;
  apiFetch(`/api/v1/product-catalog/${currentProductId}`).then(d => {
    document.getElementById("product-id").value = d.id;
    document.getElementById("product-vendor").value = d.vendor;
    document.getElementById("product-name").value = d.name;
    document.getElementById("product-type").value = d.product_type;
    document.getElementById("product-category").value = d.category;
    document.getElementById("product-reference-url").value = d.reference_url || "";
    document.getElementById("modal-product-title").textContent = "제품 수정";
    document.getElementById("btn-save-product").textContent = "저장";
    productModal.showModal();
  });
}

async function saveProduct() {
  const id = document.getElementById("product-id").value;
  const payload = {
    vendor: document.getElementById("product-vendor").value,
    name: document.getElementById("product-name").value,
    product_type: document.getElementById("product-type").value,
    category: document.getElementById("product-category").value,
    reference_url: document.getElementById("product-reference-url").value || null,
  };

  try {
    if (id) {
      await apiFetch(`/api/v1/product-catalog/${id}`, { method: "PATCH", body: payload });
      showToast("제품이 수정되었습니다.");
    } else {
      const created = await apiFetch("/api/v1/product-catalog", { method: "POST", body: payload });
      showToast("제품이 등록되었습니다.");
      currentProductId = created.id;
    }
    productModal.close();
    await loadCatalog();
    if (currentProductId) selectProduct({ id: currentProductId });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteProduct() {
  if (!currentProductId) return;
  const title = document.getElementById("detail-title").textContent;
  confirmDelete(`"${title}"을(를) 삭제하시겠습니까?`, async () => {
    try {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}`, { method: "DELETE" });
      showToast("제품이 삭제되었습니다.");
      currentProductId = null;
      document.getElementById("detail-content").classList.add("is-hidden");
      document.getElementById("detail-empty").classList.remove("is-hidden");
      await loadCatalog();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

/* ── 스펙 저장 ── */

async function saveSpec() {
  if (!currentProductId) return;
  const g = (id) => { const v = document.getElementById(id).value; return v === "" ? null : v; };
  const gn = (id) => { const v = g(id); return v === null ? null : Number(v); };
  const payload = {
    size_unit: gn("spec-size-unit"),
    width_mm: gn("spec-width-mm"),
    height_mm: gn("spec-height-mm"),
    depth_mm: gn("spec-depth-mm"),
    weight_kg: gn("spec-weight-kg"),
    power_count: gn("spec-power-count"),
    power_type: g("spec-power-type"),
    power_watt: gn("spec-power-watt"),
    cpu_summary: g("spec-cpu-summary"),
    memory_summary: g("spec-memory-summary"),
    throughput_summary: g("spec-throughput-summary"),
    os_firmware: g("spec-os-firmware"),
    spec_url: g("spec-spec-url"),
  };

  try {
    await apiFetch(`/api/v1/product-catalog/${currentProductId}/spec`, { method: "POST", body: payload });
    showToast("스펙이 저장되었습니다.");
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── EOSL 저장 ── */

async function saveEosl() {
  if (!currentProductId) return;
  const payload = {
    eos_date: document.getElementById("eosl-eos-date").value || null,
    eosl_date: document.getElementById("eosl-eosl-date").value || null,
    eosl_note: document.getElementById("eosl-eosl-note").value || null,
  };

  try {
    await apiFetch(`/api/v1/product-catalog/${currentProductId}`, { method: "PATCH", body: payload });
    showToast("EOSL 정보가 저장되었습니다.");
    await loadCatalog();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── 인터페이스 CRUD ── */

const ifaceModal = document.getElementById("modal-interface");

function openAddInterface() {
  if (!currentProductId) return;
  document.getElementById("iface-id").value = "";
  document.getElementById("iface-type").value = "";
  document.getElementById("iface-speed").value = "";
  document.getElementById("iface-count").value = "1";
  document.getElementById("iface-connector").value = "";
  document.getElementById("iface-capacity-type").value = "fixed";
  document.getElementById("iface-note").value = "";
  document.getElementById("modal-iface-title").textContent = "인터페이스 추가";
  document.getElementById("btn-save-iface").textContent = "추가";
  ifaceModal.showModal();
}

function openEditInterface(iface) {
  document.getElementById("iface-id").value = iface.id;
  document.getElementById("iface-type").value = iface.interface_type;
  document.getElementById("iface-speed").value = iface.speed || "";
  document.getElementById("iface-count").value = iface.count;
  document.getElementById("iface-connector").value = iface.connector_type || "";
  document.getElementById("iface-capacity-type").value = iface.capacity_type || "fixed";
  document.getElementById("iface-note").value = iface.note || "";
  document.getElementById("modal-iface-title").textContent = "인터페이스 수정";
  document.getElementById("btn-save-iface").textContent = "저장";
  ifaceModal.showModal();
}

async function saveInterface() {
  if (!currentProductId) return;
  const ifaceId = document.getElementById("iface-id").value;
  const payload = {
    interface_type: document.getElementById("iface-type").value,
    speed: document.getElementById("iface-speed").value || null,
    count: parseInt(document.getElementById("iface-count").value) || 1,
    connector_type: document.getElementById("iface-connector").value || null,
    capacity_type: document.getElementById("iface-capacity-type").value,
    note: document.getElementById("iface-note").value || null,
  };

  try {
    if (ifaceId) {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}/interfaces/${ifaceId}`, { method: "PATCH", body: payload });
      showToast("인터페이스가 수정되었습니다.");
    } else {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}/interfaces`, { method: "POST", body: payload });
      showToast("인터페이스가 추가되었습니다.");
    }
    ifaceModal.close();
    selectProduct({ id: currentProductId });
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteInterface(iface) {
  confirmDelete(`인터페이스 "${iface.interface_type}"을(를) 삭제하시겠습니까?`, async () => {
    try {
      await apiFetch(`/api/v1/product-catalog/${currentProductId}/interfaces/${iface.id}`, { method: "DELETE" });
      showToast("인터페이스가 삭제되었습니다.");
      selectProduct({ id: currentProductId });
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

/* ── 스플리터 드래그 ── */

function initSplitter() {
  const splitter = document.getElementById("catalog-splitter");
  const listPanel = document.querySelector(".catalog-list-panel");
  if (!splitter || !listPanel) return;
  let dragging = false;
  splitter.addEventListener("mousedown", (e) => { dragging = true; e.preventDefault(); });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const container = document.querySelector(".catalog-layout");
    const rect = container.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    if (pct > 20 && pct < 70) listPanel.style.width = pct + "%";
  });
  document.addEventListener("mouseup", () => { dragging = false; });
}

/* ── Init ── */

document.addEventListener("DOMContentLoaded", () => {
  initCatalogGrid();
  initIfaceGrid();
  initTabs();
  initSplitter();
  loadCatalog();

  // 이벤트 바인딩
  document.getElementById("btn-add-product").addEventListener("click", openCreateProduct);
  document.getElementById("btn-edit-product").addEventListener("click", openEditProduct);
  document.getElementById("btn-delete-product").addEventListener("click", deleteProduct);
  document.getElementById("btn-cancel-product").addEventListener("click", () => productModal.close());
  document.getElementById("btn-save-product").addEventListener("click", saveProduct);

  document.getElementById("btn-save-spec").addEventListener("click", saveSpec);
  document.getElementById("btn-save-eosl").addEventListener("click", saveEosl);

  document.getElementById("btn-add-interface").addEventListener("click", openAddInterface);
  document.getElementById("btn-cancel-iface").addEventListener("click", () => ifaceModal.close());
  document.getElementById("btn-save-iface").addEventListener("click", saveInterface);

  document.getElementById("catalog-search").addEventListener("input", applyFilter);
  document.getElementById("catalog-category-filter").addEventListener("change", applyFilter);
});
