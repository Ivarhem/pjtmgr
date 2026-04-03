let catalogIntegrityVendorGridApi = null;
let catalogIntegrityProductGridApi = null;
let catalogIntegrityAliasGridApi = null;
let catalogIntegrityAttributes = [];
const catalogIntegrityAliasOptionCache = new Map();
let currentCatalogIntegrityAliasId = null;
let currentCatalogIntegrityAliasRow = null;
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

function activateCatalogIntegrityTab(tabId) {
  document.querySelectorAll("[data-integrity-tab]").forEach((button) => {
    button.classList.toggle("active", button.dataset.integrityTab === tabId);
  });
  document.querySelectorAll("[id^='catalog-integrity-tab-']").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `catalog-integrity-tab-${tabId}`);
  });
}

async function loadIntegrityVendorPermissions() {
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
    panel.innerHTML = "<h3>비교 상세</h3><p>유사 후보를 선택하면 기준 제품과 후보 제품의 비교 정보가 표시됩니다.</p>";
    return;
  }
  panel.innerHTML = `
    <h3>유사도 ${row.score}</h3>
    <p><strong>기준</strong><br>${row.base_vendor} ${row.base_name}</p>
    <p><strong>후보</strong><br>${row.candidate_vendor} ${row.candidate_name}</p>
    <p>정규화 기준: ${row.normalized_vendor} / ${row.normalized_name}</p>
  `;
}

function normalizeCatalogIntegrityAliasValue(value) {
  return String(value ?? "")
    .normalize("NFKC")
    .toLowerCase()
    .trim()
    .replace(/[\s\-_./(),]+/g, "")
    .replace(/[^0-9a-z가-힣]+/g, "");
}

function renderAliasDetail(row) {
  const meta = document.getElementById("catalog-integrity-alias-meta");
  const normalizedInput = document.getElementById("catalog-integrity-alias-normalized");
  const deleteButton = document.getElementById("catalog-integrity-alias-delete");
  const aliasValue = document.getElementById("catalog-integrity-alias-value")?.value || "";
  if (normalizedInput) {
    normalizedInput.value = row?.normalized_alias || normalizeCatalogIntegrityAliasValue(aliasValue);
  }
  if (meta) {
    if (!row) {
      meta.innerHTML = "<p>새 alias를 등록합니다. 기준축인 domain, imp_type도 여기서 직접 관리할 수 있습니다.</p>";
    } else {
      meta.innerHTML = `
        <p><strong>${catalogIntegrityEscapeHtml(row.attribute_label)}</strong> / <strong>${catalogIntegrityEscapeHtml(row.option_label)}</strong></p>
        <p>연결 제품 수: <strong>${Number(row.mapped_product_count || 0).toLocaleString("ko-KR")}</strong></p>
        <p>정규화 키: <code>${catalogIntegrityEscapeHtml(row.normalized_alias || "-")}</code></p>
      `;
    }
  }
  if (deleteButton) deleteButton.disabled = !row?.id;
}

async function loadCatalogIntegrityAliasAttributes() {
  const attributes = await apiFetch("/api/v1/catalog-attributes?active_only=true");
  catalogIntegrityAttributes = Array.isArray(attributes)
    ? attributes.filter((item) => item.value_type === "option" && item.attribute_key !== "vendor_series")
    : [];
  const filterSelect = document.getElementById("catalog-integrity-alias-attribute-filter");
  const formSelect = document.getElementById("catalog-integrity-alias-attribute");
  if (filterSelect) {
    filterSelect.textContent = "";
    const allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = "전체 속성";
    filterSelect.appendChild(allOption);
    catalogIntegrityAttributes.forEach((attribute) => {
      const option = document.createElement("option");
      option.value = attribute.attribute_key;
      option.textContent = attribute.label;
      filterSelect.appendChild(option);
    });
  }
  if (formSelect) {
    formSelect.textContent = "";
    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "속성 선택";
    formSelect.appendChild(emptyOption);
    catalogIntegrityAttributes.forEach((attribute) => {
      const option = document.createElement("option");
      option.value = attribute.attribute_key;
      option.textContent = attribute.label;
      formSelect.appendChild(option);
    });
  }
}

async function loadCatalogIntegrityAliasOptions(attributeKey) {
  if (!attributeKey) return [];
  if (catalogIntegrityAliasOptionCache.has(attributeKey)) {
    return catalogIntegrityAliasOptionCache.get(attributeKey);
  }
  const attribute = catalogIntegrityAttributes.find((item) => item.attribute_key === attributeKey);
  if (!attribute) return [];
  const options = await apiFetch(`/api/v1/catalog-attributes/${attribute.id}/options?active_only=false`);
  catalogIntegrityAliasOptionCache.set(attributeKey, options);
  return options;
}

async function populateCatalogIntegrityAliasOptionSelect(attributeKey, selectedOptionId = null) {
  const select = document.getElementById("catalog-integrity-alias-option");
  if (!select) return;
  const options = await loadCatalogIntegrityAliasOptions(attributeKey);
  select.textContent = "";
  const emptyOption = document.createElement("option");
  emptyOption.value = "";
  emptyOption.textContent = "대표 속성값 선택";
  select.appendChild(emptyOption);
  options.forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.id);
    option.textContent = `${item.label} (${item.option_key})`;
    select.appendChild(option);
  });
  select.value = selectedOptionId ? String(selectedOptionId) : "";
}

async function setCatalogIntegrityAliasForm(row) {
  currentCatalogIntegrityAliasId = row?.id || null;
  currentCatalogIntegrityAliasRow = row || null;
  const attributeSelect = document.getElementById("catalog-integrity-alias-attribute");
  const aliasValueInput = document.getElementById("catalog-integrity-alias-value");
  const sortOrderInput = document.getElementById("catalog-integrity-alias-sort-order");
  const activeInput = document.getElementById("catalog-integrity-alias-active");
  if (attributeSelect) attributeSelect.value = row?.attribute_key || document.getElementById("catalog-integrity-alias-attribute-filter")?.value || "";
  await populateCatalogIntegrityAliasOptionSelect(attributeSelect?.value || "", row?.option_id || null);
  if (aliasValueInput) aliasValueInput.value = row?.alias_value || "";
  if (sortOrderInput) sortOrderInput.value = row?.sort_order ?? 100;
  if (activeInput) activeInput.checked = row?.is_active ?? true;
  renderAliasDetail(row || null);
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
    onRowClicked: (event) => renderProductDetail(event.data),
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">유사 후보가 없습니다.</span>',
  });
}

function initCatalogIntegrityAliasGrid() {
  const target = document.getElementById("grid-catalog-integrity-aliases");
  if (!target) return;
  catalogIntegrityAliasGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "attribute_label", headerName: "속성", width: 130 },
      { field: "option_label", headerName: "대표값", width: 150 },
      { field: "alias_value", headerName: "Alias", flex: 1, minWidth: 180 },
      { field: "normalized_alias", headerName: "정규화", width: 150 },
      { field: "mapped_product_count", headerName: "제품 수", width: 95 },
      {
        field: "is_active",
        headerName: "활성",
        width: 85,
        valueFormatter: (params) => (params.value ? "Y" : "N"),
      },
    ],
    rowSelection: { mode: "singleRow" },
    defaultColDef: {
      sortable: true,
      filter: true,
      resizable: true,
    },
    onRowClicked: (event) => {
      setCatalogIntegrityAliasForm(event.data).catch((err) => console.error(err));
    },
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">등록된 속성 alias가 없습니다.</span>',
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
  renderProductDetail(rows[0] || null);
}

async function loadCatalogIntegrityAliases(preferredAliasId = null) {
  if (!catalogIntegrityAliasGridApi) return;
  const attributeKey = document.getElementById("catalog-integrity-alias-attribute-filter")?.value || "";
  const q = document.getElementById("catalog-integrity-alias-search")?.value?.trim() || "";
  const params = new URLSearchParams();
  if (attributeKey) params.set("attribute_key", attributeKey);
  if (q) params.set("q", q);
  const rows = await apiFetch(`/api/v1/catalog-integrity/attribute-aliases${params.toString() ? `?${params.toString()}` : ""}`);
  catalogIntegrityAliasGridApi.setGridOption("rowData", rows);
  if (!rows.length) {
    catalogIntegrityAliasGridApi.showNoRowsOverlay();
    await setCatalogIntegrityAliasForm(null);
    return;
  }
  catalogIntegrityAliasGridApi.hideOverlay();
  const selected = rows.find((item) => item.id === preferredAliasId) || rows[0];
  await setCatalogIntegrityAliasForm(selected);
}

async function saveCatalogIntegrityAlias() {
  const attributeKey = document.getElementById("catalog-integrity-alias-attribute")?.value || "";
  const optionId = Number(document.getElementById("catalog-integrity-alias-option")?.value || 0);
  const aliasValue = document.getElementById("catalog-integrity-alias-value")?.value?.trim() || "";
  const sortOrder = Number(document.getElementById("catalog-integrity-alias-sort-order")?.value || 100);
  const isActive = !!document.getElementById("catalog-integrity-alias-active")?.checked;
  if (!attributeKey) {
    showToast("속성 키를 선택하세요.", "warning");
    return;
  }
  if (!optionId) {
    showToast("대표 속성값을 선택하세요.", "warning");
    return;
  }
  if (!aliasValue) {
    showToast("alias 값을 입력하세요.", "warning");
    return;
  }
  const payload = {
    attribute_key: attributeKey,
    option_id: optionId,
    alias_value: aliasValue,
    sort_order: Number.isFinite(sortOrder) ? sortOrder : 100,
    is_active: isActive,
    match_type: "normalized_exact",
  };
  const url = currentCatalogIntegrityAliasId
    ? `/api/v1/catalog-integrity/attribute-aliases/${currentCatalogIntegrityAliasId}`
    : "/api/v1/catalog-integrity/attribute-aliases";
  const method = currentCatalogIntegrityAliasId ? "PATCH" : "POST";
  const body = currentCatalogIntegrityAliasId
    ? {
        attribute_key: payload.attribute_key,
        option_id: payload.option_id,
        alias_value: payload.alias_value,
        sort_order: payload.sort_order,
        is_active: payload.is_active,
        match_type: payload.match_type,
      }
    : payload;
  const saved = await apiFetch(url, { method, body });
  showToast(currentCatalogIntegrityAliasId ? "속성 alias를 수정했습니다." : "속성 alias를 등록했습니다.");
  document.getElementById("catalog-integrity-alias-attribute-filter").value = saved.attribute_key;
  await loadCatalogIntegrityAliases(saved.id);
}

async function deleteCatalogIntegrityAlias() {
  if (!currentCatalogIntegrityAliasId) {
    showToast("삭제할 alias를 먼저 선택하세요.", "warning");
    return;
  }
  confirmDelete("선택한 속성 alias를 삭제하시겠습니까?", async () => {
    try {
      await apiFetch(`/api/v1/catalog-integrity/attribute-aliases/${currentCatalogIntegrityAliasId}`, { method: "DELETE" });
      showToast("속성 alias를 삭제했습니다.");
      await loadCatalogIntegrityAliases();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initCatalogIntegrityVendorGrid();
  initCatalogIntegrityProductGrid();
  initCatalogIntegrityAliasGrid();
  document.querySelectorAll("[data-integrity-tab]").forEach((button) => {
    button.addEventListener("click", () => activateCatalogIntegrityTab(button.dataset.integrityTab));
  });
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
  document.getElementById("catalog-integrity-alias-search")?.addEventListener("input", () => {
    loadCatalogIntegrityAliases().catch((err) => console.error(err));
  });
  document.getElementById("catalog-integrity-alias-attribute-filter")?.addEventListener("change", () => {
    loadCatalogIntegrityAliases().catch((err) => console.error(err));
  });
  document.getElementById("catalog-integrity-alias-attribute")?.addEventListener("change", () => {
    populateCatalogIntegrityAliasOptionSelect(document.getElementById("catalog-integrity-alias-attribute")?.value || "").catch((err) => console.error(err));
  });
  document.getElementById("catalog-integrity-alias-value")?.addEventListener("input", () => {
    const normalizedValue = normalizeCatalogIntegrityAliasValue(document.getElementById("catalog-integrity-alias-value")?.value || "");
    if (!currentCatalogIntegrityAliasId) {
      const normalizedInput = document.getElementById("catalog-integrity-alias-normalized");
      if (normalizedInput) normalizedInput.value = normalizedValue;
      return;
    }
    renderAliasDetail({
      ...(currentCatalogIntegrityAliasRow || {}),
      id: currentCatalogIntegrityAliasId,
      normalized_alias: normalizedValue,
      attribute_label: currentCatalogIntegrityAliasRow?.attribute_label || document.getElementById("catalog-integrity-alias-attribute")?.selectedOptions?.[0]?.textContent || "",
      option_label: currentCatalogIntegrityAliasRow?.option_label || document.getElementById("catalog-integrity-alias-option")?.selectedOptions?.[0]?.textContent || "",
    });
  });
  document.getElementById("catalog-integrity-alias-new")?.addEventListener("click", () => {
    setCatalogIntegrityAliasForm(null).catch((err) => console.error(err));
  });
  document.getElementById("catalog-integrity-alias-save")?.addEventListener("click", () => {
    saveCatalogIntegrityAlias().catch((err) => showToast(err.message, "error"));
  });
  document.getElementById("catalog-integrity-alias-delete")?.addEventListener("click", () => {
    deleteCatalogIntegrityAlias().catch((err) => showToast(err.message, "error"));
  });
  loadIntegrityVendorPermissions().then(() => {
    loadCatalogIntegrityVendors().catch((err) => console.error(err));
  });
  loadCatalogIntegrityProducts().catch((err) => console.error(err));
  loadCatalogIntegrityAliasAttributes()
    .then(() => loadCatalogIntegrityAliases())
    .catch((err) => console.error(err));
});
