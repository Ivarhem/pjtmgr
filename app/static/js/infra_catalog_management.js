let catalogVendorGridApi = null;
let catalogProductManageGridApi = null;

function parseCatalogManagementBool(value, fallback = true) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (!normalized) return fallback;
  return !["false", "0", "n", "no"].includes(normalized);
}

function splitCatalogManagementAliases(value) {
  return String(value || "")
    .split(/[\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function setCatalogManagementResult(targetId, text) {
  const target = document.getElementById(targetId);
  if (target) target.textContent = text;
}

function formatCatalogManagementRows(summary) {
  if (!summary?.rows?.length) return "반영 결과가 없습니다.";
  const lines = [`총 ${summary.total}건`, `실패 ${summary.failed}건`, ""];
  if (summary.created != null) lines.splice(1, 0, `생성 ${summary.created}건`, `수정 ${summary.updated}건`);
  if (summary.created == null) lines.splice(1, 0, `처리 ${summary.updated}건`);
  summary.rows.forEach((row) => {
    const prefix = row.status === "error" ? `[실패 ${row.row_no}]` : `[완료 ${row.row_no}]`;
    lines.push(`${prefix} ${row.canonical_vendor || row.vendor || "-"} ${row.name || ""} ${row.message || row.action || ""}`.trim());
  });
  return lines.join("\n");
}

function parseCatalogManagementTsv(text) {
  const lines = String(text || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  if (lines.length < 2) throw new Error("헤더와 데이터 행이 필요합니다.");
  const headers = lines[0].split("\t").map((item) => item.trim());
  return lines.slice(1).map((line) => {
    const values = line.split("\t");
    const row = {};
    headers.forEach((header, index) => {
      row[header] = values[index] ?? "";
    });
    return row;
  });
}

function initCatalogVendorGrid() {
  const target = document.getElementById("grid-catalog-vendors");
  if (!target || catalogVendorGridApi) return;
  catalogVendorGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "vendor", headerName: "대표 제조사", flex: 1, minWidth: 180 },
      { field: "product_count", headerName: "제품 수", width: 100 },
      { field: "alias_count", headerName: "alias 수", width: 100 },
      {
        field: "aliases",
        headerName: "alias",
        flex: 1.2,
        minWidth: 220,
        valueFormatter: (params) => (params.value || []).map((item) => item.alias_value).join(", "),
      },
    ],
    rowSelection: { mode: "singleRow" },
    animateRows: true,
    defaultColDef: { sortable: true, filter: true, resizable: true },
    onRowClicked: (event) => {
      const row = event.data || {};
      const sourceInput = document.getElementById("catalog-vendor-source");
      const canonicalInput = document.getElementById("catalog-vendor-canonical");
      const aliasesInput = document.getElementById("catalog-vendor-aliases");
      if (sourceInput) sourceInput.value = row.vendor || "";
      if (canonicalInput) canonicalInput.value = row.vendor || "";
      if (aliasesInput) aliasesInput.value = (row.aliases || []).map((item) => item.alias_value).join(", ");
    },
  });
}

async function loadCatalogVendorManagement() {
  if (!catalogVendorGridApi) return;
  const q = document.getElementById("catalog-vendor-search")?.value?.trim() || "";
  const rows = await apiFetch(`/api/v1/catalog-integrity/vendors${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  catalogVendorGridApi.setGridOption("rowData", rows);
}

async function saveCatalogVendorManagementRow() {
  const canonicalVendor = document.getElementById("catalog-vendor-canonical")?.value?.trim() || "";
  if (!canonicalVendor) {
    showToast("대표 제조사명을 입력하세요.", "warning");
    return;
  }
  const payload = {
    rows: [
      {
        source_vendor: document.getElementById("catalog-vendor-source")?.value?.trim() || null,
        canonical_vendor: canonicalVendor,
        aliases: splitCatalogManagementAliases(document.getElementById("catalog-vendor-aliases")?.value || ""),
        apply_to_products: !!document.getElementById("catalog-vendor-apply-products")?.checked,
        is_active: true,
      },
    ],
  };
  const result = await apiFetch("/api/v1/catalog-integrity/vendors/bulk-upsert", { method: "POST", body: payload });
  setCatalogManagementResult("catalog-vendor-result", formatCatalogManagementRows(result));
  showToast("제조사 기준을 반영했습니다.", "success");
  await loadCatalogVendorManagement();
}

async function saveCatalogVendorManagementBulk() {
  const rawRows = parseCatalogManagementTsv(document.getElementById("catalog-vendor-bulk")?.value || "");
  const payload = {
    rows: rawRows.map((row) => ({
      source_vendor: String(row.source_vendor || "").trim() || null,
      canonical_vendor: String(row.canonical_vendor || "").trim(),
      aliases: splitCatalogManagementAliases(row.aliases || ""),
      apply_to_products: parseCatalogManagementBool(row.apply_to_products, true),
      is_active: true,
    })),
  };
  const result = await apiFetch("/api/v1/catalog-integrity/vendors/bulk-upsert", { method: "POST", body: payload });
  setCatalogManagementResult("catalog-vendor-result", formatCatalogManagementRows(result));
  showToast("제조사 TSV 반영이 완료되었습니다.", result.failed ? "warning" : "success");
  await loadCatalogVendorManagement();
}

function initCatalogProductManageGrid() {
  const target = document.getElementById("grid-catalog-products-manage");
  if (!target || catalogProductManageGridApi) return;
  catalogProductManageGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "id", headerName: "ID", width: 90 },
      { field: "vendor", headerName: "제조사", width: 160 },
      { field: "name", headerName: "제품명", flex: 1, minWidth: 220 },
      { field: "product_type", headerName: "유형", width: 120 },
      { field: "classification_level_1_name", headerName: "1레벨", width: 130 },
      { field: "classification_level_2_name", headerName: "2레벨", width: 130 },
      { field: "classification_level_3_name", headerName: "3레벨", width: 150 },
    ],
    rowSelection: { mode: "singleRow" },
    animateRows: true,
    defaultColDef: { sortable: true, filter: true, resizable: true },
  });
}

async function loadCatalogProductManagement() {
  if (!catalogProductManageGridApi) return;
  const q = document.getElementById("catalog-product-search-manage")?.value?.trim() || "";
  const productType = document.getElementById("catalog-product-type-manage")?.value || "";
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (productType) params.set("product_type", productType);
  const rows = await apiFetch(`/api/v1/product-catalog${params.toString() ? `?${params.toString()}` : ""}`);
  catalogProductManageGridApi.setGridOption("rowData", rows);
}

function buildCatalogProductBulkRow(raw) {
  const row = {
    product_id: raw.product_id ? Number(raw.product_id) : null,
    vendor: String(raw.vendor || "").trim(),
    name: String(raw.name || "").trim(),
    product_type: String(raw.product_type || "hardware").trim() || "hardware",
    version: String(raw.version || "").trim() || null,
    domain: String(raw.domain || "").trim() || null,
    imp_type: String(raw.imp_type || "").trim() || null,
    product_family: String(raw.product_family || "").trim() || null,
    platform: String(raw.platform || "").trim() || null,
    reference_url: String(raw.reference_url || "").trim() || null,
    eos_date: String(raw.eos_date || "").trim() || null,
    eosl_date: String(raw.eosl_date || "").trim() || null,
    eosl_note: String(raw.eosl_note || "").trim() || null,
  };
  if (!row.vendor || !row.name) {
    throw new Error("vendor와 name은 필수입니다.");
  }
  return row;
}

async function saveCatalogProductManagementBulk() {
  const rawRows = parseCatalogManagementTsv(document.getElementById("catalog-product-bulk")?.value || "");
  const payload = {
    rows: rawRows.map((row) => buildCatalogProductBulkRow(row)),
  };
  const result = await apiFetch("/api/v1/product-catalog/bulk-upsert", { method: "POST", body: payload });
  setCatalogManagementResult("catalog-product-result", formatCatalogManagementRows(result));
  showToast("제품 TSV 반영이 완료되었습니다.", result.failed ? "warning" : "success");
  await loadCatalogProductManagement();
}

document.addEventListener("DOMContentLoaded", () => {
  initCatalogVendorGrid();
  initCatalogProductManageGrid();

  if (catalogVendorGridApi) {
    loadCatalogVendorManagement().catch((error) => {
      console.error(error);
      showToast(error.message || "제조사 목록을 불러오지 못했습니다.", "error");
    });
  }
  if (catalogProductManageGridApi) {
    loadCatalogProductManagement().catch((error) => {
      console.error(error);
      showToast(error.message || "제품 목록을 불러오지 못했습니다.", "error");
    });
  }

  document.getElementById("btn-catalog-vendor-refresh")?.addEventListener("click", () => {
    loadCatalogVendorManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("catalog-vendor-search")?.addEventListener("input", () => {
    loadCatalogVendorManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("btn-catalog-vendor-save")?.addEventListener("click", () => {
    saveCatalogVendorManagementRow().catch((error) => {
      console.error(error);
      showToast(error.message || "제조사 반영에 실패했습니다.", "error");
    });
  });
  document.getElementById("btn-catalog-vendor-bulk-apply")?.addEventListener("click", () => {
    saveCatalogVendorManagementBulk().catch((error) => {
      console.error(error);
      showToast(error.message || "제조사 TSV 반영에 실패했습니다.", "error");
    });
  });

  document.getElementById("btn-catalog-product-refresh")?.addEventListener("click", () => {
    loadCatalogProductManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("catalog-product-search-manage")?.addEventListener("input", () => {
    loadCatalogProductManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("catalog-product-type-manage")?.addEventListener("change", () => {
    loadCatalogProductManagement().catch((error) => showToast(error.message, "error"));
  });
  document.getElementById("btn-catalog-product-bulk-apply")?.addEventListener("click", () => {
    saveCatalogProductManagementBulk().catch((error) => {
      console.error(error);
      showToast(error.message || "제품 TSV 반영에 실패했습니다.", "error");
    });
  });
});
