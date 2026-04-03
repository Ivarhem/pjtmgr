let catalogIntegrityVendorGridApi = null;
let catalogIntegrityProductGridApi = null;
let _integrityVendorAliases = [];
let _integrityVendorMode = "empty";
let _integrityVendorOriginal = null;
let _canManageVendor = false;

function catalogIntegrityEscapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

async function loadIntegrityPermissions() {
  try {
    const me = window.__me || await apiFetch("/api/v1/auth/me");
    window.__me = me;
    const canManage = !!me?.permissions?.can_manage_catalog_taxonomy;
    _canManageVendor = canManage;
  } catch (_) {
    _canManageVendor = false;
  }
  document.querySelectorAll(".vendor-write-only").forEach((el) => {
    el.style.display = _canManageVendor ? "" : "none";
  });
}

function setIntegrityVendorEmptyMode() {
  _integrityVendorMode = "empty";
  _integrityVendorOriginal = null;
  _integrityVendorAliases = [];
  document.getElementById("integrity-vendor-empty")?.classList.remove("is-hidden");
  document.getElementById("integrity-vendor-form")?.classList.add("is-hidden");
}

function setIntegrityVendorNewMode() {
  _integrityVendorMode = "new";
  _integrityVendorOriginal = null;
  _integrityVendorAliases = [];

  document.getElementById("integrity-vendor-empty")?.classList.add("is-hidden");
  document.getElementById("integrity-vendor-form")?.classList.remove("is-hidden");
  document.getElementById("integrity-vendor-title").textContent = "새 제조사 등록";
  document.getElementById("integrity-vendor-source-label")?.classList.add("is-hidden");
  document.getElementById("integrity-vendor-source").value = "";
  document.getElementById("integrity-vendor-canonical").value = "";
  document.getElementById("integrity-vendor-canonical").readOnly = false;
  document.getElementById("integrity-vendor-apply-row")?.classList.add("is-hidden");
  document.getElementById("btn-integrity-vendor-delete")?.classList.add("is-hidden");
  renderIntegrityVendorAliasChips();
}

function setIntegrityVendorEditMode(vendor, aliases) {
  _integrityVendorMode = "edit";
  _integrityVendorOriginal = vendor;
  _integrityVendorAliases = (aliases || []).map((a) => a.alias_value);

  document.getElementById("integrity-vendor-empty")?.classList.add("is-hidden");
  document.getElementById("integrity-vendor-form")?.classList.remove("is-hidden");
  document.getElementById("integrity-vendor-title").textContent = "제조사 편집";
  document.getElementById("integrity-vendor-source-label")?.classList.remove("is-hidden");
  document.getElementById("integrity-vendor-source").value = vendor;
  document.getElementById("integrity-vendor-canonical").value = vendor;
  document.getElementById("integrity-vendor-canonical").readOnly = false;
  document.getElementById("integrity-vendor-apply-row")?.classList.add("is-hidden");
  if (_canManageVendor) {
    document.getElementById("btn-integrity-vendor-delete")?.classList.remove("is-hidden");
  }
  renderIntegrityVendorAliasChips();
}

function renderIntegrityVendorAliasChips() {
  const listEl = document.getElementById("integrity-vendor-alias-list");
  if (!listEl) return;
  listEl.textContent = "";
  _integrityVendorAliases.forEach((alias, idx) => {
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
          _integrityVendorAliases.splice(idx, 1);
          renderIntegrityVendorAliasChips();
        }
      });
      chip.appendChild(xBtn);
    }
    listEl.appendChild(chip);
  });
}

function onIntegrityVendorCanonicalChange() {
  const canonical = document.getElementById("integrity-vendor-canonical")?.value?.trim() || "";
  const applyRow = document.getElementById("integrity-vendor-apply-row");
  if (_integrityVendorMode === "edit" && canonical && canonical !== _integrityVendorOriginal) {
    applyRow?.classList.remove("is-hidden");
  } else {
    applyRow?.classList.add("is-hidden");
  }
}

async function saveIntegrityVendor() {
  const canonical = document.getElementById("integrity-vendor-canonical")?.value?.trim() || "";
  if (!canonical) {
    showToast("정식 제조사명을 입력하세요.", "warning");
    return;
  }
  const payload = {
    rows: [
      {
        source_vendor: _integrityVendorMode === "edit" ? _integrityVendorOriginal : null,
        canonical_vendor: canonical,
        aliases: [..._integrityVendorAliases],
        apply_to_products: _integrityVendorMode === "edit" && canonical !== _integrityVendorOriginal
          ? !!document.getElementById("integrity-vendor-apply-products")?.checked
          : false,
        is_active: true,
      },
    ],
  };
  await apiFetch("/api/v1/catalog-integrity/vendors/bulk-upsert", { method: "POST", body: payload });
  showToast("제조사를 저장했습니다.", "success");
  await loadCatalogIntegrityVendors();
  setIntegrityVendorEditMode(canonical, _integrityVendorAliases.map((v) => ({ alias_value: v })));
}

async function deleteIntegrityVendor() {
  if (!_integrityVendorOriginal) return;
  const rows = [];
  catalogIntegrityVendorGridApi?.forEachNode((node) => rows.push(node.data));
  const vendorRow = rows.find((r) => r.vendor === _integrityVendorOriginal);
  if (vendorRow && vendorRow.product_count > 0) {
    alert(`연결된 제품 ${vendorRow.product_count}개가 있어 삭제할 수 없습니다.`);
    return;
  }
  if (!confirm(`제조사 '${_integrityVendorOriginal}'과(와) 모든 별칭을 삭제하시겠습니까?`)) return;
  try {
    await apiFetch(`/api/v1/catalog-integrity/vendors/${encodeURIComponent(_integrityVendorOriginal)}`, { method: "DELETE" });
    showToast("제조사를 삭제했습니다.", "success");
    await loadCatalogIntegrityVendors();
    setIntegrityVendorEmptyMode();
  } catch (err) {
    alert(err.message || "삭제에 실패했습니다.");
  }
}

function renderProductDetail(row) {
  const panel = document.getElementById("catalog-integrity-product-detail");
  if (!panel) return;
  if (!row) {
    panel.textContent = "";
    const h = document.createElement("h3");
    h.textContent = "비교 상세";
    const p = document.createElement("p");
    p.textContent = "유사 후보를 선택하면 기준 제품과 후보 제품의 비교 정보가 표시됩니다.";
    panel.appendChild(h);
    panel.appendChild(p);
    return;
  }
  panel.textContent = "";
  const h = document.createElement("h3");
  h.textContent = `유사도 ${row.score}`;
  panel.appendChild(h);

  const pBase = document.createElement("p");
  const strongBase = document.createElement("strong");
  strongBase.textContent = "기준";
  pBase.appendChild(strongBase);
  pBase.appendChild(document.createElement("br"));
  pBase.appendChild(document.createTextNode(`${row.base_vendor} ${row.base_name}`));
  panel.appendChild(pBase);

  const pCand = document.createElement("p");
  const strongCand = document.createElement("strong");
  strongCand.textContent = "후보";
  pCand.appendChild(strongCand);
  pCand.appendChild(document.createElement("br"));
  pCand.appendChild(document.createTextNode(`${row.candidate_vendor} ${row.candidate_name}`));
  panel.appendChild(pCand);

  const pNorm = document.createElement("p");
  pNorm.textContent = `정규화 기준: ${row.normalized_vendor} / ${row.normalized_name}`;
  panel.appendChild(pNorm);
}

function initCatalogIntegrityVendorGrid() {
  const target = document.getElementById("grid-catalog-integrity-vendors");
  if (!target) return;
  catalogIntegrityVendorGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "vendor", headerName: "대표 제조사", flex: 1, minWidth: 180 },
      { field: "product_count", headerName: "제품 수", width: 110 },
      { field: "alias_count", headerName: "Alias 수", width: 110 },
    ],
    rowSelection: { mode: "singleRow" },
    defaultColDef: {
      sortable: true,
      filter: true,
      resizable: true,
    },
    onRowClicked: (event) => {
      const row = event.data || {};
      setIntegrityVendorEditMode(row.vendor, row.aliases || []);
    },
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">제조사 데이터가 없습니다.</span>',
  });
}

function initCatalogIntegrityProductGrid() {
  const target = document.getElementById("grid-catalog-integrity-products");
  if (!target) return;
  catalogIntegrityProductGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "base_vendor", headerName: "기준 제조사", width: 140 },
      { field: "base_name", headerName: "기준 제품명", flex: 1, minWidth: 220 },
      { field: "candidate_vendor", headerName: "후보 제조사", width: 140 },
      { field: "candidate_name", headerName: "후보 제품명", flex: 1, minWidth: 220 },
      { field: "score", headerName: "유사도", width: 100, sort: "desc" },
    ],
    rowSelection: { mode: "singleRow" },
    defaultColDef: {
      sortable: true,
      filter: true,
      resizable: true,
    },
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">유사 후보가 없습니다.</span>',
  });
}

async function loadCatalogIntegrityVendors() {
  if (!catalogIntegrityVendorGridApi) return;
  const q = document.getElementById("catalog-integrity-vendor-search")?.value?.trim() || "";
  const rows = await apiFetch(`/api/v1/catalog-integrity/vendors${q ? `?q=${encodeURIComponent(q)}` : ""}`);
  catalogIntegrityVendorGridApi.setGridOption("rowData", rows);
  if (!rows.length) catalogIntegrityVendorGridApi.showNoRowsOverlay();
  else catalogIntegrityVendorGridApi.hideOverlay();
}

async function loadCatalogIntegrityProducts() {
  if (!catalogIntegrityProductGridApi) return;
  const q = document.getElementById("catalog-integrity-product-search")?.value?.trim() || "";
  const minScore = document.getElementById("catalog-integrity-min-score")?.value || "75";
  const rows = await apiFetch(`/api/v1/catalog-integrity/similar-products?min_score=${encodeURIComponent(minScore)}${q ? `&q=${encodeURIComponent(q)}` : ""}`);
  catalogIntegrityProductGridApi.setGridOption("rowData", rows);
  if (!rows.length) catalogIntegrityProductGridApi.showNoRowsOverlay();
  else catalogIntegrityProductGridApi.hideOverlay();
}

document.addEventListener("DOMContentLoaded", () => {
  initCatalogIntegrityVendorGrid();
  initCatalogIntegrityProductGrid();
  document.getElementById("catalog-integrity-vendor-search")?.addEventListener("input", () => {
    loadCatalogIntegrityVendors().catch((err) => console.error(err));
  });
  document.getElementById("btn-integrity-vendor-add")?.addEventListener("click", () => {
    setIntegrityVendorNewMode();
  });
  document.getElementById("btn-integrity-vendor-save")?.addEventListener("click", () => {
    saveIntegrityVendor().catch((err) => {
      console.error(err);
      showToast(err.message || "저장에 실패했습니다.", "error");
    });
  });
  document.getElementById("btn-integrity-vendor-delete")?.addEventListener("click", () => {
    deleteIntegrityVendor().catch((err) => {
      console.error(err);
      showToast(err.message || "삭제에 실패했습니다.", "error");
    });
  });
  document.getElementById("btn-integrity-vendor-cancel")?.addEventListener("click", () => {
    setIntegrityVendorEmptyMode();
  });
  document.getElementById("integrity-vendor-canonical")?.addEventListener("input", () => {
    onIntegrityVendorCanonicalChange();
  });
  document.getElementById("integrity-vendor-alias-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const input = e.target;
      const val = input.value.replace(/,/g, "").trim();
      const normalizedVal = val.toLowerCase().replace(/[\s\-_./(),]+/g, "");
      const isDuplicate = _integrityVendorAliases.some((a) => a.toLowerCase().replace(/[\s\-_./(),]+/g, "") === normalizedVal);
      if (val && !isDuplicate) {
        _integrityVendorAliases.push(val);
        renderIntegrityVendorAliasChips();
      }
      input.value = "";
    }
    if (e.key === "Backspace" && e.target.value === "" && _integrityVendorAliases.length > 0) {
      _integrityVendorAliases.pop();
      renderIntegrityVendorAliasChips();
    }
  });
  document.getElementById("catalog-integrity-product-search")?.addEventListener("input", () => {
    loadCatalogIntegrityProducts().catch((err) => console.error(err));
  });
  document.getElementById("catalog-integrity-min-score")?.addEventListener("change", () => {
    loadCatalogIntegrityProducts().catch((err) => console.error(err));
  });
  loadIntegrityPermissions().then(() => {
    loadCatalogIntegrityVendors().catch((err) => console.error(err));
  });
  loadCatalogIntegrityProducts().catch((err) => console.error(err));
});
