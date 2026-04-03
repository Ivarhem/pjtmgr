/* ── 제조사 관리 ──────────────────────────────────────────── */

let catalogVendorGridApi = null;
let _vendorAliases = [];
let _vendorMode = "empty";
let _vendorOriginal = null;
let _canManageVendor = false;

function initCatalogVendorGrid() {
  const target = document.getElementById("grid-catalog-vendors");
  if (!target || catalogVendorGridApi) return;
  catalogVendorGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "vendor", headerName: "제조사명", flex: 1, minWidth: 180 },
      { field: "product_count", headerName: "제품 수", width: 100 },
      { field: "alias_count", headerName: "alias 수", width: 100 },
    ],
    rowSelection: { mode: "singleRow" },
    animateRows: true,
    defaultColDef: { sortable: true, filter: true, resizable: true },
    onRowClicked: (event) => {
      const row = event.data || {};
      setVendorEditMode(row.vendor, row.aliases || []);
    },
  });
}

async function loadCatalogVendorPermissions() {
  try {
    const me = window.__me || await apiFetch("/api/v1/auth/me");
    window.__me = me;
    _canManageVendor = !!me?.permissions?.can_manage_catalog_taxonomy;
  } catch (_) {
    _canManageVendor = false;
  }
  document.querySelectorAll(".vendor-write-only").forEach((el) => {
    el.style.display = _canManageVendor ? "" : "none";
  });
}

async function loadCatalogVendorManagement() {
  if (!catalogVendorGridApi) return;
  const q = document.getElementById("catalog-vendor-search")?.value?.trim() || "";
  const rows = await apiFetch(`/api/v1/catalog-integrity/vendors${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  catalogVendorGridApi.setGridOption("rowData", rows);
}

function setVendorEmptyMode() {
  _vendorMode = "empty";
  _vendorOriginal = null;
  _vendorAliases = [];
  document.getElementById("vendor-detail-empty")?.classList.remove("is-hidden");
  document.getElementById("vendor-detail-content")?.classList.add("is-hidden");
}

function setVendorNewMode() {
  _vendorMode = "new";
  _vendorOriginal = null;
  _vendorAliases = [];

  document.getElementById("vendor-detail-empty")?.classList.add("is-hidden");
  document.getElementById("vendor-detail-content")?.classList.remove("is-hidden");
  document.getElementById("vendor-detail-title").textContent = "새 제조사 등록";
  document.getElementById("vendor-source-label")?.classList.add("is-hidden");
  document.getElementById("catalog-vendor-source").value = "";
  document.getElementById("catalog-vendor-canonical").value = "";
  document.getElementById("catalog-vendor-canonical").readOnly = false;
  document.getElementById("vendor-apply-row")?.classList.add("is-hidden");
  document.getElementById("btn-catalog-vendor-delete")?.classList.add("is-hidden");
  renderVendorAliasChips();
}

function setVendorEditMode(vendor, aliases) {
  _vendorMode = "edit";
  _vendorOriginal = vendor;
  _vendorAliases = (aliases || []).map((a) => a.alias_value);

  document.getElementById("vendor-detail-empty")?.classList.add("is-hidden");
  document.getElementById("vendor-detail-content")?.classList.remove("is-hidden");
  document.getElementById("vendor-detail-title").textContent = "제조사 편집";
  document.getElementById("vendor-source-label")?.classList.remove("is-hidden");
  document.getElementById("catalog-vendor-source").value = vendor;
  document.getElementById("catalog-vendor-canonical").value = vendor;
  document.getElementById("catalog-vendor-canonical").readOnly = false;
  document.getElementById("vendor-apply-row")?.classList.add("is-hidden");
  if (_canManageVendor) {
    document.getElementById("btn-catalog-vendor-delete")?.classList.remove("is-hidden");
  }
  renderVendorAliasChips();
}

function renderVendorAliasChips() {
  const listEl = document.getElementById("vendor-alias-tag-list");
  if (!listEl) return;
  listEl.textContent = "";
  _vendorAliases.forEach((alias, idx) => {
    const chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.textContent = alias;
    if (_canManageVendor) {
      const xBtn = document.createElement("span");
      xBtn.className = "tag-chip-x";
      xBtn.dataset.idx = idx;
      xBtn.textContent = "\u00d7";
      xBtn.addEventListener("click", () => {
        if (confirm(`별칭 '${alias}'을(를) 삭제하시겠습니까?`)) {
          _vendorAliases.splice(idx, 1);
          renderVendorAliasChips();
        }
      });
      chip.appendChild(xBtn);
    }
    listEl.appendChild(chip);
  });
}

function onVendorCanonicalChange() {
  const canonical = document.getElementById("catalog-vendor-canonical")?.value?.trim() || "";
  const applyRow = document.getElementById("vendor-apply-row");
  if (_vendorMode === "edit" && canonical && canonical !== _vendorOriginal) {
    applyRow?.classList.remove("is-hidden");
  } else {
    applyRow?.classList.add("is-hidden");
  }
}

async function saveCatalogVendor() {
  const canonical = document.getElementById("catalog-vendor-canonical")?.value?.trim() || "";
  if (!canonical) {
    showToast("정식 제조사명을 입력하세요.", "warning");
    return;
  }
  const payload = {
    rows: [
      {
        source_vendor: _vendorMode === "edit" ? _vendorOriginal : null,
        canonical_vendor: canonical,
        aliases: [..._vendorAliases],
        apply_to_products: _vendorMode === "edit" && canonical !== _vendorOriginal
          ? !!document.getElementById("catalog-vendor-apply-products")?.checked
          : false,
        is_active: true,
      },
    ],
  };
  await apiFetch("/api/v1/catalog-integrity/vendors/bulk-upsert", { method: "POST", body: payload });
  showToast("제조사를 저장했습니다.", "success");
  await loadCatalogVendorManagement();
  setVendorEditMode(canonical, _vendorAliases.map((v) => ({ alias_value: v })));
}

async function deleteCatalogVendor() {
  if (!_vendorOriginal) return;
  const rows = [];
  catalogVendorGridApi?.forEachNode((node) => rows.push(node.data));
  const vendorRow = rows.find((r) => r.vendor === _vendorOriginal);
  if (vendorRow && vendorRow.product_count > 0) {
    alert(`연결된 제품 ${vendorRow.product_count}개가 있어 삭제할 수 없습니다.`);
    return;
  }
  if (!confirm(`제조사 '${_vendorOriginal}'과(와) 모든 별칭을 삭제하시겠습니까?`)) return;
  try {
    await apiFetch(`/api/v1/catalog-integrity/vendors/${encodeURIComponent(_vendorOriginal)}`, { method: "DELETE" });
    showToast("제조사를 삭제했습니다.", "success");
    await loadCatalogVendorManagement();
    setVendorEmptyMode();
  } catch (err) {
    alert(err.message || "삭제에 실패했습니다.");
  }
}


/* ── 제품 관리 ──────────────────────────────────────────── */

let catalogProductManageGridApi = null;

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

function parseCatalogManagementBool(value, fallback = true) {
  const normalized = String(value ?? "").trim().toLowerCase();
  if (!normalized) return fallback;
  return !["false", "0", "n", "no"].includes(normalized);
}

async function saveCatalogProductManagementBulk() {
  const rawRows = parseCatalogManagementTsv(document.getElementById("catalog-product-bulk")?.value || "");
  const payload = {
    rows: rawRows.map((row) => buildCatalogProductBulkRow(row)),
  };
  const result = await apiFetch("/api/v1/product-catalog/bulk-upsert", { method: "POST", body: payload });
  const target = document.getElementById("catalog-product-result");
  if (target) {
    const lines = [`총 ${result.total}건`, `실패 ${result.failed}건`];
    if (result.created != null) lines.splice(1, 0, `생성 ${result.created}건`, `수정 ${result.updated}건`);
    if (result.created == null) lines.splice(1, 0, `처리 ${result.updated}건`);
    if (result.rows?.length) {
      lines.push("");
      result.rows.forEach((row) => {
        const prefix = row.status === "error" ? `[실패 ${row.row_no}]` : `[완료 ${row.row_no}]`;
        lines.push(`${prefix} ${row.canonical_vendor || row.vendor || "-"} ${row.name || ""} ${row.message || row.action || ""}`.trim());
      });
    }
    target.textContent = lines.join("\n");
  }
  showToast("제품 TSV 반영이 완료되었습니다.", result.failed ? "warning" : "success");
  await loadCatalogProductManagement();
}


/* ── 초기화 ──────────────────────────────────────────── */

document.addEventListener("DOMContentLoaded", () => {
  initCatalogVendorGrid();
  initCatalogProductManageGrid();

  if (catalogVendorGridApi) {
    loadCatalogVendorPermissions().then(() => {
      loadCatalogVendorManagement().catch((error) => {
        console.error(error);
        showToast(error.message || "제조사 목록을 불러오지 못했습니다.", "error");
      });
    });

    document.getElementById("btn-catalog-vendor-refresh")?.addEventListener("click", () => {
      loadCatalogVendorManagement().catch((error) => showToast(error.message, "error"));
    });
    document.getElementById("catalog-vendor-search")?.addEventListener("input", () => {
      loadCatalogVendorManagement().catch((error) => showToast(error.message, "error"));
    });
    document.getElementById("btn-catalog-vendor-add")?.addEventListener("click", () => {
      setVendorNewMode();
    });
    document.getElementById("btn-catalog-vendor-save")?.addEventListener("click", () => {
      saveCatalogVendor().catch((error) => {
        console.error(error);
        showToast(error.message || "저장에 실패했습니다.", "error");
      });
    });
    document.getElementById("btn-catalog-vendor-delete")?.addEventListener("click", () => {
      deleteCatalogVendor().catch((error) => {
        console.error(error);
        showToast(error.message || "삭제에 실패했습니다.", "error");
      });
    });
    document.getElementById("btn-catalog-vendor-cancel")?.addEventListener("click", () => {
      setVendorEmptyMode();
    });
    document.getElementById("catalog-vendor-canonical")?.addEventListener("input", () => {
      onVendorCanonicalChange();
    });

    document.getElementById("vendor-alias-input")?.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === ",") {
        e.preventDefault();
        const input = e.target;
        const val = input.value.replace(/,/g, "").trim();
        if (val && !_vendorAliases.includes(val)) {
          _vendorAliases.push(val);
          renderVendorAliasChips();
        }
        input.value = "";
      }
      if (e.key === "Backspace" && e.target.value === "" && _vendorAliases.length > 0) {
        const removed = _vendorAliases[_vendorAliases.length - 1];
        if (confirm(`별칭 '${removed}'을(를) 삭제하시겠습니까?`)) {
          _vendorAliases.pop();
          renderVendorAliasChips();
        }
      }
    });
  }

  if (catalogProductManageGridApi) {
    loadCatalogProductManagement().catch((error) => {
      console.error(error);
      showToast(error.message || "제품 목록을 불러오지 못했습니다.", "error");
    });
  }

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
