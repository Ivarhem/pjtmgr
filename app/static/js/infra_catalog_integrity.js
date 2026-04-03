let catalogIntegrityVendorGridApi = null;
let catalogIntegrityProductGridApi = null;
let _integrityVendorAliases = [];
let _integrityVendorMode = "empty";
let _integrityVendorOriginal = null;
let _canManageVendor = false;

let catalogIntegrityAttrGridApi = null;
let _integrityAttrDefs = [];        // all attribute definitions
let _integrityAttrMode = "empty";   // "empty" | "new" | "edit"
let _integrityAttrCurrentOption = null;  // selected option object
let _integrityAttrAliases = [];     // aliases for current option [{id, alias_value, ...}]
let _canManageAttr = false;

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

async function loadIntegrityPermissions() {
  try {
    const me = window.__me || await apiFetch("/api/v1/auth/me");
    window.__me = me;
    const canManage = !!me?.permissions?.can_manage_catalog_taxonomy;
    _canManageVendor = canManage;
    _canManageAttr = canManage;
  } catch (_) {
    _canManageVendor = false;
    _canManageAttr = false;
  }
  document.querySelectorAll(".vendor-write-only").forEach((el) => {
    el.style.display = _canManageVendor ? "" : "none";
  });
  document.querySelectorAll(".attr-write-only").forEach((el) => {
    el.style.display = _canManageAttr ? "" : "none";
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
    onRowClicked: (event) => renderProductDetail(event.data),
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
  renderProductDetail(rows[0] || null);
}

/* ── 속성 탭 ── */

/* loadIntegrityPermissions()에서 통합 처리 */

async function loadIntegrityAttrDefs() {
  const attrs = await apiFetch("/api/v1/catalog-attributes?active_only=true");
  _integrityAttrDefs = Array.isArray(attrs)
    ? attrs.filter((a) => a.value_type === "option" && a.attribute_key !== "vendor_series" && a.attribute_key !== "license_model")
    : [];
  const select = document.getElementById("catalog-integrity-attr-key-filter");
  if (!select) return;
  const current = select.value || "";
  select.textContent = "";
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "속성 키 선택";
  select.appendChild(emptyOpt);
  _integrityAttrDefs
    .sort((a, b) => (a.sort_order ?? 100) - (b.sort_order ?? 100) || String(a.label || "").localeCompare(String(b.label || ""), "ko-KR"))
    .forEach((attr) => {
      const opt = document.createElement("option");
      opt.value = attr.attribute_key;
      opt.textContent = `${attr.label} (${attr.attribute_key})`;
      select.appendChild(opt);
    });
  if (_integrityAttrDefs.some((a) => a.attribute_key === current)) {
    select.value = current;
  } else if (select.options.length > 1) {
    select.value = select.options[1].value;
  }
}

function getIntegrityAttrDef(attributeKey) {
  return _integrityAttrDefs.find((a) => a.attribute_key === attributeKey) || null;
}

function isIntegrityAttrDomainDependent(attributeKey) {
  return attributeKey === "product_family";
}

let _integrityDomainOptions = null;

async function loadIntegrityDomainOptions() {
  if (_integrityDomainOptions) return _integrityDomainOptions;
  const domainAttr = getIntegrityAttrDef("domain");
  if (!domainAttr) return [];
  _integrityDomainOptions = await apiFetch(`/api/v1/catalog-attributes/${domainAttr.id}/options?active_only=true`);
  return _integrityDomainOptions;
}

async function populateIntegrityDomainSelect(selectedId) {
  const select = document.getElementById("integrity-attr-domain-option");
  const label = document.getElementById("integrity-attr-domain-label");
  const attributeKey = document.getElementById("catalog-integrity-attr-key-filter")?.value || "";
  if (!select || !label) return;
  if (!isIntegrityAttrDomainDependent(attributeKey)) {
    label.classList.add("is-hidden");
    return;
  }
  label.classList.remove("is-hidden");
  const options = await loadIntegrityDomainOptions();
  select.textContent = "";
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "선택 안 함";
  select.appendChild(emptyOpt);
  options.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = String(item.id);
    opt.textContent = `${item.label} (${item.option_key})`;
    select.appendChild(opt);
  });
  select.value = selectedId ? String(selectedId) : "";
}

function initIntegrityAttrGrid() {
  const target = document.getElementById("grid-catalog-integrity-attrs");
  if (!target) return;
  catalogIntegrityAttrGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "option_key", headerName: "키", width: 130 },
      { field: "label", headerName: "아이템명", flex: 1, minWidth: 160 },
      { field: "label_kr", headerName: "한글명", width: 130, valueFormatter: (p) => p.value || "-" },
      { field: "domain_option_label", headerName: "도메인", width: 110, valueFormatter: (p) => p.value || "-" },
      { field: "alias_count", headerName: "alias", width: 80, valueGetter: (p) => (p.data.aliases || []).length },
      { field: "sort_order", headerName: "정렬", width: 80 },
      {
        field: "is_active", headerName: "활성", width: 80,
        valueFormatter: (p) => p.value ? "Y" : "N",
      },
    ],
    rowSelection: { mode: "singleRow" },
    defaultColDef: { sortable: true, filter: true, resizable: true },
    onRowClicked: (event) => {
      setIntegrityAttrEditMode(event.data);
    },
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">속성 키를 선택하세요.</span>',
  });
}

async function loadIntegrityAttrOptions() {
  if (!catalogIntegrityAttrGridApi) return;
  const attributeKey = document.getElementById("catalog-integrity-attr-key-filter")?.value || "";
  const attr = getIntegrityAttrDef(attributeKey);
  if (!attributeKey || !attr) {
    catalogIntegrityAttrGridApi.setGridOption("rowData", []);
    catalogIntegrityAttrGridApi.showNoRowsOverlay();
    setIntegrityAttrEmptyMode();
    return;
  }
  const q = document.getElementById("catalog-integrity-attr-search")?.value?.trim() || "";
  let items = await apiFetch(`/api/v1/catalog-attributes/${attr.id}/options?active_only=false`);
  if (q) {
    const lower = q.toLowerCase();
    items = items.filter((item) =>
      (item.option_key || "").toLowerCase().includes(lower) ||
      (item.label || "").toLowerCase().includes(lower) ||
      (item.label_kr || "").toLowerCase().includes(lower)
    );
  }
  catalogIntegrityAttrGridApi.setGridOption("rowData", items);
  if (!items.length) {
    catalogIntegrityAttrGridApi.setGridOption("overlayNoRowsTemplate", '<span class="ag-overlay-loading-center">등록된 아이템이 없습니다.</span>');
    catalogIntegrityAttrGridApi.showNoRowsOverlay();
  } else {
    catalogIntegrityAttrGridApi.hideOverlay();
  }
}

function setIntegrityAttrEmptyMode() {
  _integrityAttrMode = "empty";
  _integrityAttrCurrentOption = null;
  _integrityAttrAliases = [];
  document.getElementById("integrity-attr-empty")?.classList.remove("is-hidden");
  document.getElementById("integrity-attr-form")?.classList.add("is-hidden");
}

function setIntegrityAttrNewMode() {
  _integrityAttrMode = "new";
  _integrityAttrCurrentOption = null;
  _integrityAttrAliases = [];

  document.getElementById("integrity-attr-empty")?.classList.add("is-hidden");
  document.getElementById("integrity-attr-form")?.classList.remove("is-hidden");
  document.getElementById("integrity-attr-title").textContent = "새 아이템 등록";
  document.getElementById("integrity-attr-option-key").value = "";
  document.getElementById("integrity-attr-option-key").readOnly = false;
  document.getElementById("integrity-attr-option-label").value = "";
  document.getElementById("integrity-attr-option-label-kr").value = "";
  document.getElementById("integrity-attr-sort-order").value = "100";
  document.getElementById("integrity-attr-active").checked = true;
  document.getElementById("btn-integrity-attr-delete")?.classList.add("is-hidden");
  document.getElementById("integrity-attr-alias-section")?.classList.add("is-hidden");
  populateIntegrityDomainSelect(null);
  renderIntegrityAttrAliasChips();
}

function setIntegrityAttrEditMode(option) {
  _integrityAttrMode = "edit";
  _integrityAttrCurrentOption = option;

  document.getElementById("integrity-attr-empty")?.classList.add("is-hidden");
  document.getElementById("integrity-attr-form")?.classList.remove("is-hidden");
  document.getElementById("integrity-attr-title").textContent = "아이템 편집";
  document.getElementById("integrity-attr-option-key").value = option.option_key || "";
  document.getElementById("integrity-attr-option-key").readOnly = true;
  document.getElementById("integrity-attr-option-label").value = option.label || "";
  document.getElementById("integrity-attr-option-label-kr").value = option.label_kr || "";
  document.getElementById("integrity-attr-sort-order").value = option.sort_order ?? 100;
  document.getElementById("integrity-attr-active").checked = option.is_active !== false;
  if (_canManageAttr) {
    document.getElementById("btn-integrity-attr-delete")?.classList.remove("is-hidden");
  }
  // Load aliases for this option
  _integrityAttrAliases = (option.aliases || []).map((a) => ({
    id: a.id,
    alias_value: a.alias_value,
    normalized_alias: a.normalized_alias,
  }));
  document.getElementById("integrity-attr-alias-section")?.classList.remove("is-hidden");
  populateIntegrityDomainSelect(option.domain_option_id || null);
  renderIntegrityAttrAliasChips();
}

function renderIntegrityAttrAliasChips() {
  const listEl = document.getElementById("integrity-attr-alias-list");
  if (!listEl) return;
  listEl.textContent = "";
  _integrityAttrAliases.forEach((alias, idx) => {
    const chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.textContent = alias.alias_value;
    if (_canManageAttr) {
      const xBtn = document.createElement("span");
      xBtn.className = "tag-chip-x";
      xBtn.dataset.idx = idx;
      xBtn.textContent = "\u00d7";
      xBtn.addEventListener("click", () => {
        if (confirm(`별칭 '${alias.alias_value}'을(를) 삭제하시겠습니까?`)) {
          deleteIntegrityAttrAlias(alias.id, idx);
        }
      });
      chip.appendChild(xBtn);
    }
    listEl.appendChild(chip);
  });
}

async function saveIntegrityAttrOption() {
  const attributeKey = document.getElementById("catalog-integrity-attr-key-filter")?.value || "";
  const attr = getIntegrityAttrDef(attributeKey);
  if (!attr) {
    showToast("속성 키를 먼저 선택하세요.", "warning");
    return;
  }
  const optionKey = document.getElementById("integrity-attr-option-key")?.value?.trim() || "";
  const label = document.getElementById("integrity-attr-option-label")?.value?.trim() || "";
  const labelKr = document.getElementById("integrity-attr-option-label-kr")?.value?.trim() || null;
  const sortOrder = Number(document.getElementById("integrity-attr-sort-order")?.value || 100);
  const isActive = !!document.getElementById("integrity-attr-active")?.checked;

  if (!optionKey) { showToast("아이템 키를 입력하세요.", "warning"); return; }
  if (!label) { showToast("아이템명을 입력하세요.", "warning"); return; }

  const domainOptionId = Number(document.getElementById("integrity-attr-domain-option")?.value || 0) || null;

  if (_integrityAttrMode === "new") {
    const payload = { option_key: optionKey, label, label_kr: labelKr, sort_order: sortOrder, is_active: isActive, domain_option_id: domainOptionId };
    const saved = await apiFetch(`/api/v1/catalog-attributes/${attr.id}/options`, { method: "POST", body: payload });
    showToast("아이템을 등록했습니다.", "success");
    await loadIntegrityAttrOptions();
    // Select the newly created option in the grid
    const newOption = findIntegrityAttrOptionInGrid(saved.id);
    if (newOption) setIntegrityAttrEditMode(newOption);
  } else if (_integrityAttrMode === "edit" && _integrityAttrCurrentOption) {
    const payload = { label, label_kr: labelKr, sort_order: sortOrder, is_active: isActive, domain_option_id: domainOptionId };
    await apiFetch(`/api/v1/catalog-attributes/options/${_integrityAttrCurrentOption.id}`, { method: "PATCH", body: payload });
    showToast("아이템을 수정했습니다.", "success");
    await loadIntegrityAttrOptions();
    const updated = findIntegrityAttrOptionInGrid(_integrityAttrCurrentOption.id);
    if (updated) setIntegrityAttrEditMode(updated);
  }
}

function findIntegrityAttrOptionInGrid(optionId) {
  if (!catalogIntegrityAttrGridApi) return null;
  let found = null;
  catalogIntegrityAttrGridApi.forEachNode((node) => {
    if (node.data?.id === optionId) found = node.data;
  });
  return found;
}

async function deleteIntegrityAttrOption() {
  if (!_integrityAttrCurrentOption) return;
  if (!confirm(`아이템 '${_integrityAttrCurrentOption.label}'을(를) 삭제하시겠습니까?`)) return;
  try {
    await apiFetch(`/api/v1/catalog-attributes/options/${_integrityAttrCurrentOption.id}`, { method: "DELETE" });
    showToast("아이템을 삭제했습니다.", "success");
    await loadIntegrityAttrOptions();
    setIntegrityAttrEmptyMode();
  } catch (err) {
    alert(err.message || "삭제에 실패했습니다.");
  }
}

async function addIntegrityAttrAlias(aliasValue) {
  if (!_integrityAttrCurrentOption) return;
  const attributeKey = document.getElementById("catalog-integrity-attr-key-filter")?.value || "";
  const payload = {
    attribute_key: attributeKey,
    option_id: _integrityAttrCurrentOption.id,
    alias_value: aliasValue,
    sort_order: 100,
    is_active: true,
    match_type: "normalized_exact",
  };
  try {
    await apiFetch("/api/v1/catalog-integrity/attribute-aliases", { method: "POST", body: payload });
    // Reload options to get updated alias list
    await loadIntegrityAttrOptions();
    const updated = findIntegrityAttrOptionInGrid(_integrityAttrCurrentOption.id);
    if (updated) setIntegrityAttrEditMode(updated);
    showToast("alias를 추가했습니다.", "success");
  } catch (err) {
    showToast(err.message || "alias 추가에 실패했습니다.", "error");
  }
}

async function deleteIntegrityAttrAlias(aliasId, idx) {
  try {
    await apiFetch(`/api/v1/catalog-integrity/attribute-aliases/${aliasId}`, { method: "DELETE" });
    _integrityAttrAliases.splice(idx, 1);
    renderIntegrityAttrAliasChips();
    showToast("alias를 삭제했습니다.", "success");
  } catch (err) {
    showToast(err.message || "alias 삭제에 실패했습니다.", "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initCatalogIntegrityVendorGrid();
  initCatalogIntegrityProductGrid();
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
  // 속성 탭 이벤트
  document.getElementById("catalog-integrity-attr-key-filter")?.addEventListener("change", () => {
    loadIntegrityAttrOptions().catch((err) => console.error(err));
    setIntegrityAttrEmptyMode();
  });
  document.getElementById("catalog-integrity-attr-search")?.addEventListener("input", () => {
    loadIntegrityAttrOptions().catch((err) => console.error(err));
  });
  document.getElementById("btn-integrity-attr-add")?.addEventListener("click", () => {
    const attributeKey = document.getElementById("catalog-integrity-attr-key-filter")?.value || "";
    if (!attributeKey) { showToast("속성 키를 먼저 선택하세요.", "warning"); return; }
    setIntegrityAttrNewMode();
  });
  document.getElementById("btn-integrity-attr-new")?.addEventListener("click", () => {
    const attributeKey = document.getElementById("catalog-integrity-attr-key-filter")?.value || "";
    if (!attributeKey) { showToast("속성 키를 먼저 선택하세요.", "warning"); return; }
    setIntegrityAttrNewMode();
  });
  document.getElementById("btn-integrity-attr-save")?.addEventListener("click", () => {
    saveIntegrityAttrOption().catch((err) => {
      console.error(err);
      showToast(err.message || "저장에 실패했습니다.", "error");
    });
  });
  document.getElementById("btn-integrity-attr-delete")?.addEventListener("click", () => {
    deleteIntegrityAttrOption().catch((err) => {
      console.error(err);
      showToast(err.message || "삭제에 실패했습니다.", "error");
    });
  });
  document.getElementById("btn-integrity-attr-cancel")?.addEventListener("click", () => {
    setIntegrityAttrEmptyMode();
  });
  document.getElementById("integrity-attr-alias-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const input = e.target;
      const val = input.value.replace(/,/g, "").trim();
      if (val && _integrityAttrCurrentOption) {
        addIntegrityAttrAlias(val);
      }
      input.value = "";
    }
  });
  initIntegrityAttrGrid();
  loadIntegrityPermissions().then(() => {
    loadCatalogIntegrityVendors().catch((err) => console.error(err));
    loadIntegrityAttrDefs().then(() => {
      loadIntegrityAttrOptions().catch((err) => console.error(err));
    }).catch((err) => console.error(err));
  });
  loadCatalogIntegrityProducts().catch((err) => console.error(err));

  // URL query param으로 탭 자동 선택
  const urlParams = new URLSearchParams(window.location.search);
  const tabParam = urlParams.get("tab");
  if (tabParam === "vendors") activateCatalogIntegrityTab("vendors");
  else if (tabParam === "products") activateCatalogIntegrityTab("products");
  else if (tabParam === "attributes" || tabParam === "aliases") activateCatalogIntegrityTab("aliases");
});
