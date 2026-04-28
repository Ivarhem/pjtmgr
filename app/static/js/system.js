let editingCode = null;
let editingTermKey = null;

const CATEGORY_LABELS = { entity: "엔티티", metric: "지표", report: "보고서" };

/* ── 속성 관리 (프로젝트관리 탭) ── */
let systemAttrGridApi = null;
let _systemAttrDefs = [];
let _systemAttrMode = "empty";
let _systemAttrCurrentOption = null;
let _systemAttrAliases = [];
let _canManageAttr = false;
let _systemDomainOptions = null;

async function loadSystemAttrPermissions() {
  try {
    const me = window.__me || await apiFetch("/api/v1/auth/me");
    window.__me = me;
    _canManageAttr = !!me?.permissions?.can_manage_catalog_taxonomy;
  } catch (_) {
    _canManageAttr = false;
  }
  document.querySelectorAll(".attr-write-only").forEach((el) => {
    setElementHidden(el, !_canManageAttr);
  });
}

async function loadSystemAttrDefs() {
  const attrs = await apiFetch("/api/v1/catalog-attributes?active_only=true");
  _systemAttrDefs = Array.isArray(attrs)
    ? attrs.filter((a) => a.value_type === "option" && a.attribute_key !== "vendor_series" && a.attribute_key !== "license_model")
    : [];
  const select = document.getElementById("system-attr-key-filter");
  if (!select) return;
  const current = select.value || "";
  select.textContent = "";
  _systemAttrDefs
    .sort((a, b) => (a.sort_order ?? 100) - (b.sort_order ?? 100) || String(a.label || "").localeCompare(String(b.label || ""), "ko-KR"))
    .forEach((attr) => {
      const opt = document.createElement("option");
      opt.value = attr.attribute_key;
      opt.textContent = `${attr.label} (${attr.attribute_key})`;
      select.appendChild(opt);
    });
  if (_systemAttrDefs.some((a) => a.attribute_key === current)) {
    select.value = current;
  } else if (select.options.length > 0) {
    select.value = select.options[0].value;
  }
}

function getSystemAttrDef(attributeKey) {
  return _systemAttrDefs.find((a) => a.attribute_key === attributeKey) || null;
}

function isSystemAttrDomainDependent(attributeKey) {
  return attributeKey === "product_family";
}

async function loadSystemDomainOptions() {
  if (_systemDomainOptions) return _systemDomainOptions;
  const domainAttr = getSystemAttrDef("domain");
  if (!domainAttr) return [];
  _systemDomainOptions = await apiFetch(`/api/v1/catalog-attributes/${domainAttr.id}/options?active_only=true`);
  return _systemDomainOptions;
}

async function populateSystemDomainSelect(selectedId) {
  const select = document.getElementById("system-attr-domain-option");
  const label = document.getElementById("system-attr-domain-label");
  const attributeKey = document.getElementById("system-attr-key-filter")?.value || "";
  if (!select || !label) return;
  if (!isSystemAttrDomainDependent(attributeKey)) {
    label.classList.add("is-hidden");
    return;
  }
  label.classList.remove("is-hidden");
  const options = await loadSystemDomainOptions();
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

function initSystemAttrGrid() {
  const target = document.getElementById("grid-system-attrs");
  if (!target) return;
  systemAttrGridApi = agGrid.createGrid(target, {
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
    domLayout: "autoHeight",
    defaultColDef: { sortable: true, filter: true, resizable: true },
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => setSystemAttrEditMode(data),
    }),
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">속성 키를 선택하세요.</span>',
  });
}

async function loadSystemAttrOptions() {
  if (!systemAttrGridApi) return;
  const attributeKey = document.getElementById("system-attr-key-filter")?.value || "";
  const attr = getSystemAttrDef(attributeKey);
  if (!attributeKey || !attr) {
    systemAttrGridApi.setGridOption("rowData", []);
    systemAttrGridApi.showNoRowsOverlay();
    setSystemAttrEmptyMode();
    return;
  }
  const q = document.getElementById("system-attr-search")?.value?.trim() || "";
  let items = await apiFetch(`/api/v1/catalog-attributes/${attr.id}/options?active_only=false`);
  if (q) {
    const lower = q.toLowerCase();
    items = items.filter((item) =>
      (item.option_key || "").toLowerCase().includes(lower) ||
      (item.label || "").toLowerCase().includes(lower) ||
      (item.label_kr || "").toLowerCase().includes(lower)
    );
  }
  systemAttrGridApi.setGridOption("rowData", items);
  if (!items.length) {
    systemAttrGridApi.setGridOption("overlayNoRowsTemplate", '<span class="ag-overlay-loading-center">등록된 아이템이 없습니다.</span>');
    systemAttrGridApi.showNoRowsOverlay();
  } else {
    systemAttrGridApi.hideOverlay();
  }
}

function setSystemAttrEmptyMode() {
  _systemAttrMode = "empty";
  _systemAttrCurrentOption = null;
  _systemAttrAliases = [];
  document.getElementById("system-attr-empty")?.classList.remove("is-hidden");
  document.getElementById("system-attr-form")?.classList.add("is-hidden");
}

function setSystemAttrNewMode() {
  _systemAttrMode = "new";
  _systemAttrCurrentOption = null;
  _systemAttrAliases = [];

  document.getElementById("system-attr-empty")?.classList.add("is-hidden");
  document.getElementById("system-attr-form")?.classList.remove("is-hidden");
  document.getElementById("system-attr-title").textContent = "새 아이템 등록";
  document.getElementById("system-attr-option-key").value = "";
  document.getElementById("system-attr-option-key").readOnly = false;
  document.getElementById("system-attr-option-label").value = "";
  document.getElementById("system-attr-option-label-kr").value = "";
  document.getElementById("system-attr-sort-order").value = "100";
  document.getElementById("system-attr-active").checked = true;
  document.getElementById("btn-system-attr-delete")?.classList.add("is-hidden");
  document.getElementById("system-attr-alias-section")?.classList.add("is-hidden");
  populateSystemDomainSelect(null);
  renderSystemAttrAliasChips();
}

function setSystemAttrEditMode(option) {
  _systemAttrMode = "edit";
  _systemAttrCurrentOption = option;

  document.getElementById("system-attr-empty")?.classList.add("is-hidden");
  document.getElementById("system-attr-form")?.classList.remove("is-hidden");
  document.getElementById("system-attr-title").textContent = "아이템 편집";
  document.getElementById("system-attr-option-key").value = option.option_key || "";
  document.getElementById("system-attr-option-key").readOnly = true;
  document.getElementById("system-attr-option-label").value = option.label || "";
  document.getElementById("system-attr-option-label-kr").value = option.label_kr || "";
  document.getElementById("system-attr-sort-order").value = option.sort_order ?? 100;
  document.getElementById("system-attr-active").checked = option.is_active !== false;
  if (_canManageAttr) {
    document.getElementById("btn-system-attr-delete")?.classList.remove("is-hidden");
  }
  _systemAttrAliases = (option.aliases || []).map((a) => ({
    id: a.id,
    alias_value: a.alias_value,
    normalized_alias: a.normalized_alias,
  }));
  document.getElementById("system-attr-alias-section")?.classList.remove("is-hidden");
  populateSystemDomainSelect(option.domain_option_id || null);
  renderSystemAttrAliasChips();
}

function renderSystemAttrAliasChips() {
  const listEl = document.getElementById("system-attr-alias-list");
  if (!listEl) return;
  listEl.textContent = "";
  _systemAttrAliases.forEach((alias, idx) => {
    const chip = document.createElement("span");
    chip.className = "tag-chip";
    chip.textContent = alias.alias_value;
    if (_canManageAttr) {
      const xBtn = document.createElement("span");
      xBtn.className = "tag-chip-x";
      xBtn.dataset.idx = idx;
      xBtn.textContent = "\u00d7";
      xBtn.addEventListener("click", async () => {
        if (await showConfirmDialog(`별칭 '${alias.alias_value}'을(를) 삭제하시겠습니까?`, {
          title: "별칭 삭제",
          confirmText: "삭제",
        })) {
          deleteSystemAttrAlias(alias.id, idx);
        }
      });
      chip.appendChild(xBtn);
    }
    listEl.appendChild(chip);
  });
}

async function saveSystemAttrOption() {
  const attributeKey = document.getElementById("system-attr-key-filter")?.value || "";
  const attr = getSystemAttrDef(attributeKey);
  if (!attr) {
    showToast("속성 키를 먼저 선택하세요.", "warning");
    return;
  }
  const optionKey = document.getElementById("system-attr-option-key")?.value?.trim() || "";
  const label = document.getElementById("system-attr-option-label")?.value?.trim() || "";
  const labelKr = document.getElementById("system-attr-option-label-kr")?.value?.trim() || null;
  const sortOrder = Number(document.getElementById("system-attr-sort-order")?.value || 100);
  const isActive = !!document.getElementById("system-attr-active")?.checked;

  if (!optionKey) { showToast("아이템 키를 입력하세요.", "warning"); return; }
  if (!label) { showToast("아이템명을 입력하세요.", "warning"); return; }

  const domainOptionId = Number(document.getElementById("system-attr-domain-option")?.value || 0) || null;

  if (_systemAttrMode === "new") {
    const payload = { option_key: optionKey, label, label_kr: labelKr, sort_order: sortOrder, is_active: isActive, domain_option_id: domainOptionId };
    const saved = await apiFetch(`/api/v1/catalog-attributes/${attr.id}/options`, { method: "POST", body: payload });
    showToast("아이템을 등록했습니다.", "success");
    await loadSystemAttrOptions();
    const newOption = findSystemAttrOptionInGrid(saved.id);
    if (newOption) setSystemAttrEditMode(newOption);
  } else if (_systemAttrMode === "edit" && _systemAttrCurrentOption) {
    const payload = { label, label_kr: labelKr, sort_order: sortOrder, is_active: isActive, domain_option_id: domainOptionId };
    await apiFetch(`/api/v1/catalog-attributes/options/${_systemAttrCurrentOption.id}`, { method: "PATCH", body: payload });
    showToast("아이템을 수정했습니다.", "success");
    await loadSystemAttrOptions();
    const updated = findSystemAttrOptionInGrid(_systemAttrCurrentOption.id);
    if (updated) setSystemAttrEditMode(updated);
  }
}

function findSystemAttrOptionInGrid(optionId) {
  if (!systemAttrGridApi) return null;
  let found = null;
  systemAttrGridApi.forEachNode((node) => {
    if (node.data?.id === optionId) found = node.data;
  });
  return found;
}

async function deleteSystemAttrOption() {
  if (!_systemAttrCurrentOption) return;
  if (!await showConfirmDialog(`아이템 '${_systemAttrCurrentOption.label}'을(를) 삭제하시겠습니까?`, {
    title: "아이템 삭제",
    confirmText: "삭제",
  })) return;
  try {
    await apiFetch(`/api/v1/catalog-attributes/options/${_systemAttrCurrentOption.id}`, { method: "DELETE" });
    showToast("아이템을 삭제했습니다.", "success");
    await loadSystemAttrOptions();
    setSystemAttrEmptyMode();
  } catch (err) {
    alert(err.message || "삭제에 실패했습니다.");
  }
}

async function addSystemAttrAlias(aliasValue) {
  if (!_systemAttrCurrentOption) return;
  const attributeKey = document.getElementById("system-attr-key-filter")?.value || "";
  const payload = {
    attribute_key: attributeKey,
    option_id: _systemAttrCurrentOption.id,
    alias_value: aliasValue,
    sort_order: 100,
    is_active: true,
    match_type: "normalized_exact",
  };
  try {
    await apiFetch("/api/v1/catalog-integrity/attribute-aliases", { method: "POST", body: payload });
    await loadSystemAttrOptions();
    const updated = findSystemAttrOptionInGrid(_systemAttrCurrentOption.id);
    if (updated) setSystemAttrEditMode(updated);
    showToast("alias를 추가했습니다.", "success");
  } catch (err) {
    showToast(err.message || "alias 추가에 실패했습니다.", "error");
  }
}

async function deleteSystemAttrAlias(aliasId, idx) {
  try {
    await apiFetch(`/api/v1/catalog-integrity/attribute-aliases/${aliasId}`, { method: "DELETE" });
    _systemAttrAliases.splice(idx, 1);
    renderSystemAttrAliasChips();
    showToast("alias를 삭제했습니다.", "success");
  } catch (err) {
    showToast(err.message || "alias 삭제에 실패했습니다.", "error");
  }
}

function bindSystemAttrActions() {
  document.getElementById("system-attr-key-filter")?.addEventListener("change", () => {
    const key = document.getElementById("system-attr-key-filter")?.value || "";
    if (systemAttrGridApi) {
      systemAttrGridApi.setColumnsVisible(["domain_option_label"], isSystemAttrDomainDependent(key));
    }
    loadSystemAttrOptions().catch((err) => console.error(err));
    setSystemAttrEmptyMode();
  });
  document.getElementById("system-attr-search")?.addEventListener("input", () => {
    loadSystemAttrOptions().catch((err) => console.error(err));
  });
  document.getElementById("btn-system-attr-add")?.addEventListener("click", () => {
    const attributeKey = document.getElementById("system-attr-key-filter")?.value || "";
    if (!attributeKey) { showToast("속성 키를 먼저 선택하세요.", "warning"); return; }
    setSystemAttrNewMode();
  });
  document.getElementById("btn-system-attr-new")?.addEventListener("click", () => {
    const attributeKey = document.getElementById("system-attr-key-filter")?.value || "";
    if (!attributeKey) { showToast("속성 키를 먼저 선택하세요.", "warning"); return; }
    setSystemAttrNewMode();
  });
  document.getElementById("btn-system-attr-save")?.addEventListener("click", () => {
    saveSystemAttrOption().catch((err) => {
      console.error(err);
      showToast(err.message || "저장에 실패했습니다.", "error");
    });
  });
  document.getElementById("btn-system-attr-delete")?.addEventListener("click", () => {
    deleteSystemAttrOption().catch((err) => {
      console.error(err);
      showToast(err.message || "삭제에 실패했습니다.", "error");
    });
  });
  document.getElementById("btn-system-attr-cancel")?.addEventListener("click", () => {
    setSystemAttrEmptyMode();
  });
  document.getElementById("system-attr-alias-input")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const input = e.target;
      const val = input.value.replace(/,/g, "").trim();
      if (val && _systemAttrCurrentOption) {
        addSystemAttrAlias(val);
      }
      input.value = "";
    }
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  bindSystemTabs();
  await loadSettings();
  bindSettingsActions();
  bindContractTypeActions();
  bindTermActions();

  if (document.getElementById("btn-add-contract-type")) {
    await loadContractTypeTable();
  }
  await loadTermConfigTable();

  // 속성 관리 (프로젝트관리 탭)
  if (document.getElementById("grid-system-attrs")) {
    bindSystemAttrActions();
    initSystemAttrGrid();
    loadSystemAttrPermissions().then(() => {
      loadSystemAttrDefs().then(() => {
        const initKey = document.getElementById("system-attr-key-filter")?.value || "";
        if (systemAttrGridApi) {
          systemAttrGridApi.setColumnsVisible(["domain_option_label"], isSystemAttrDomainDependent(initKey));
        }
        loadSystemAttrOptions().catch((err) => console.error(err));
      }).catch((err) => console.error(err));
    });
  }
});

function bindSystemTabs() {
  document.querySelectorAll("#system-tabs .tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#system-tabs .tab-btn").forEach((node) => node.classList.remove("active"));
      btn.classList.add("active");
      ["tab-common", "tab-accounting", "tab-infra"].forEach((id) => {
        const el = document.getElementById(id);
        if (!el) return;
        const isActive = id === `tab-${btn.dataset.tab}`;
        el.classList.toggle("is-hidden", !isActive);
      });
      history.replaceState(null, "", `#${btn.dataset.tab}`);
    });
  });

  const initTab = location.hash.slice(1) || "common";
  const initBtn = document.querySelector(`#system-tabs .tab-btn[data-tab="${initTab}"]`);
  if (initBtn) initBtn.click();
}

async function loadSettings() {
  const res = await fetch(withRootPath("/api/v1/settings"));
  const data = await res.json();
  document.getElementById("input-org-name").value = data.org_name ?? "";
  document.getElementById("input-password-min-length").value = data.password_min_length ?? 8;

  // Load catalog label lang preference
  try {
    const langPref = await apiFetch("/api/v1/preferences/catalog.label_lang");
    const langInput = document.getElementById("input-catalog-label-lang");
    if (langInput && langPref?.value) langInput.value = langPref.value;
  } catch (_) {}
}

function bindSettingsActions() {
  document.getElementById("btn-save-settings").addEventListener("click", async () => {
    const orgName = document.getElementById("input-org-name").value.trim();
    const passwordMinLength = parseInt(document.getElementById("input-password-min-length").value, 10);
    const [res] = await Promise.all([
      fetch(withRootPath("/api/v1/settings"), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          org_name: orgName || null,
          password_min_length: Number.isNaN(passwordMinLength) ? null : passwordMinLength,
        }),
      }),
      apiFetch("/api/v1/preferences/catalog.label_lang", {
        method: "PATCH",
        body: { value: document.getElementById("input-catalog-label-lang")?.value || "ko" },
      }).catch(() => {}),
    ]);

    if (res.ok) {
      const updated = await res.json();
      document.getElementById("input-password-min-length").value = updated.password_min_length;
      alert("저장되었습니다.");
      return;
    }
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "저장에 실패했습니다.");
  });
}

function bindContractTypeActions() {
  if (!document.getElementById("btn-add-contract-type")) return;
  document.getElementById("btn-add-contract-type").addEventListener("click", () => openContractTypeModal());
  document.getElementById("btn-dt-cancel").addEventListener("click", () => document.getElementById("modal-contract-type").close());
  document.getElementById("btn-dt-submit").addEventListener("click", submitContractType);
}

async function loadContractTypeTable() {
  const res = await fetch(withRootPath("/api/v1/contract-types?active_only=false"));
  const types = await res.json();
  const tbody = document.getElementById("contract-type-tbody");
  tbody.innerHTML = types.map((dt) => `
    <tr class="${dt.is_active ? "" : "row-inactive"}">
      <td><span class="cell-code">${escapeHtml(dt.code)}</span></td>
      <td>${escapeHtml(dt.label)}</td>
      <td class="cell-center">${dt.sort_order}</td>
      <td class="cell-center">${dt.default_gp_pct != null ? `${dt.default_gp_pct}%` : '<span class="cell-muted">-</span>'}</td>
      <td class="cell-center">${inspectionText(dt)}</td>
      <td class="cell-center cell-text-sm">${invoiceText(dt)}</td>
      <td class="cell-center">${dt.is_active ? '<span class="ui-badge ui-status-success badge-active">활성</span>' : '<span class="ui-badge ui-status-neutral badge-inactive">비활성</span>'}</td>
      <td class="cell-center">
        <button class="btn btn-secondary btn-xs" onclick="openContractTypeModal(${JSON.stringify(dt.code)})">수정</button>
      </td>
    </tr>
  `).join("");
}

function inspectionText(dt) {
  if (dt.default_inspection_day == null) return '<span class="cell-muted">-</span>';
  return dt.default_inspection_day === 0 ? "말일" : `${dt.default_inspection_day}일`;
}

function invoiceText(dt) {
  const parts = [];
  if (dt.default_invoice_month_offset != null) parts.push(dt.default_invoice_month_offset === 0 ? "당월" : "익월");
  if (dt.default_invoice_day_type) parts.push(dt.default_invoice_day_type === "특정일" ? `${dt.default_invoice_day || "?"}일` : dt.default_invoice_day_type);
  if (dt.default_invoice_holiday_adjust) parts.push(`(휴일:${dt.default_invoice_holiday_adjust})`);
  return parts.length ? parts.join(" ") : '<span class="cell-muted">-</span>';
}

async function openContractTypeModal(code = null) {
  editingCode = code;
  const modal = document.getElementById("modal-contract-type");
  const title = document.getElementById("modal-contract-type-title");
  const codeInput = document.getElementById("dt-code");

  if (code) {
    title.textContent = "사업유형 수정";
    codeInput.value = code;
    codeInput.readOnly = true;
    const res = await fetch(withRootPath("/api/v1/contract-types?active_only=false"));
    const types = await res.json();
    const dt = types.find((item) => item.code === code);
    if (dt) {
      document.getElementById("dt-label").value = dt.label;
      document.getElementById("dt-sort-order").value = dt.sort_order;
      document.getElementById("dt-gp-pct").value = dt.default_gp_pct ?? "";
      document.getElementById("dt-inspection-day").value = dt.default_inspection_day ?? "";
      document.getElementById("dt-invoice-month-offset").value = dt.default_invoice_month_offset ?? "";
      document.getElementById("dt-invoice-day-type").value = dt.default_invoice_day_type ?? "";
      document.getElementById("dt-invoice-day").value = dt.default_invoice_day ?? "";
      document.getElementById("dt-invoice-holiday-adjust").value = dt.default_invoice_holiday_adjust ?? "";
    }
  } else {
    title.textContent = "사업유형 추가";
    codeInput.value = "";
    codeInput.readOnly = false;
    document.getElementById("dt-label").value = "";
    document.getElementById("dt-sort-order").value = "0";
    document.getElementById("dt-gp-pct").value = "";
    document.getElementById("dt-inspection-day").value = "";
    document.getElementById("dt-invoice-month-offset").value = "";
    document.getElementById("dt-invoice-day-type").value = "";
    document.getElementById("dt-invoice-day").value = "";
    document.getElementById("dt-invoice-holiday-adjust").value = "";
  }
  modal.showModal();
}

async function submitContractType() {
  const code = document.getElementById("dt-code").value.trim();
  const label = document.getElementById("dt-label").value.trim();
  if (!code || !label) {
    alert("코드와 표시명은 필수입니다.");
    return;
  }

  const body = {
    label,
    sort_order: parseInt(document.getElementById("dt-sort-order").value, 10) || 0,
    default_gp_pct: numOrNull("dt-gp-pct"),
    default_inspection_day: numOrNull("dt-inspection-day"),
    default_invoice_month_offset: numOrNull("dt-invoice-month-offset"),
    default_invoice_day_type: document.getElementById("dt-invoice-day-type").value || null,
    default_invoice_day: numOrNull("dt-invoice-day"),
    default_invoice_holiday_adjust: document.getElementById("dt-invoice-holiday-adjust").value || null,
  };

  const res = editingCode
    ? await fetch(withRootPath(`/api/v1/contract-types/${encodeURIComponent(editingCode)}`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    : await fetch(withRootPath("/api/v1/contract-types"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, code }),
    });

  if (res.ok) {
    document.getElementById("modal-contract-type").close();
    await loadContractTypeTable();
    return;
  }
  const err = await res.json().catch(() => ({}));
  alert(err.detail || "저장에 실패했습니다.");
}

function numOrNull(id) {
  const value = document.getElementById(id).value;
  return value !== "" ? parseInt(value, 10) : null;
}

function bindTermActions() {
  document.getElementById("btn-add-term").addEventListener("click", () => openTermModal());
  document.getElementById("btn-tc-cancel").addEventListener("click", () => document.getElementById("modal-term-config").close());
  document.getElementById("btn-tc-submit").addEventListener("click", submitTermConfig);
}

async function loadTermConfigTable() {
  const res = await fetch(withRootPath("/api/v1/term-configs?active_only=false"));
  const terms = await res.json();
  const tbody = document.getElementById("term-config-tbody");
  tbody.innerHTML = terms.map((term) => `
    <tr class="${term.is_active ? "" : "row-inactive"}">
      <td class="cell-center"><span class="ui-badge badge-category" data-cat="${escapeHtml(term.category)}">${escapeHtml(CATEGORY_LABELS[term.category] || term.category)}</span></td>
      <td><span class="cell-code">${escapeHtml(term.term_key)}</span></td>
      <td>${escapeHtml(term.standard_label_ko)}</td>
      <td>${escapeHtml(term.default_ui_label)}</td>
      <td>${term.is_customized ? `<span class="ui-badge ui-status-info badge-customized">${escapeHtml(term.custom_ui_label)}</span>` : '<span class="cell-muted">-</span>'}</td>
      <td class="cell-center">${term.is_active ? '<span class="ui-badge ui-status-success badge-active">활성</span>' : '<span class="ui-badge ui-status-neutral badge-inactive">비활성</span>'}</td>
      <td class="cell-center">
        <button class="btn btn-secondary btn-xs" onclick="openTermModal(${JSON.stringify(term.term_key)})">수정</button>
        ${term.is_customized ? `<button class="btn btn-secondary btn-xs" onclick="resetTermLabel(${JSON.stringify(term.term_key)})">초기화</button>` : ""}
      </td>
    </tr>
  `).join("");
}

async function openTermModal(termKey = null) {
  editingTermKey = termKey;
  const modal = document.getElementById("modal-term-config");
  const title = document.getElementById("modal-term-title");
  const keyInput = document.getElementById("tc-term-key");

  if (termKey) {
    title.textContent = "용어 수정";
    keyInput.readOnly = true;
    document.getElementById("tc-category").disabled = true;
    document.getElementById("tc-standard-ko").readOnly = true;
    document.getElementById("tc-default-label").readOnly = true;
    const res = await fetch(withRootPath(`/api/v1/term-configs/${encodeURIComponent(termKey)}`));
    const term = await res.json();
    keyInput.value = term.term_key;
    document.getElementById("tc-category").value = term.category;
    document.getElementById("tc-standard-en").value = term.standard_label_en;
    document.getElementById("tc-standard-ko").value = term.standard_label_ko;
    document.getElementById("tc-default-label").value = term.default_ui_label;
    document.getElementById("tc-custom-label").value = term.custom_ui_label ?? "";
    document.getElementById("tc-sort-order").value = term.sort_order;
    document.getElementById("tc-definition").value = term.definition ?? "";
  } else {
    title.textContent = "용어 추가";
    keyInput.readOnly = false;
    document.getElementById("tc-category").disabled = false;
    document.getElementById("tc-standard-ko").readOnly = false;
    document.getElementById("tc-default-label").readOnly = false;
    keyInput.value = "";
    document.getElementById("tc-category").value = "entity";
    document.getElementById("tc-standard-en").value = "";
    document.getElementById("tc-standard-ko").value = "";
    document.getElementById("tc-default-label").value = "";
    document.getElementById("tc-custom-label").value = "";
    document.getElementById("tc-sort-order").value = "0";
    document.getElementById("tc-definition").value = "";
  }
  modal.showModal();
}

async function submitTermConfig() {
  const termKey = document.getElementById("tc-term-key").value.trim();
  const standardEn = document.getElementById("tc-standard-en").value.trim();
  const standardKo = document.getElementById("tc-standard-ko").value.trim();
  const defaultLabel = document.getElementById("tc-default-label").value.trim();

  if (!termKey || !standardEn || !standardKo || !defaultLabel) {
    alert("키, 영문 표준명, 한글 표준명, 기본 표시명은 필수입니다.");
    return;
  }

  const body = {
    category: document.getElementById("tc-category").value,
    standard_label_en: standardEn,
    standard_label_ko: standardKo,
    default_ui_label: defaultLabel,
    custom_ui_label: document.getElementById("tc-custom-label").value.trim() || null,
    sort_order: parseInt(document.getElementById("tc-sort-order").value, 10) || 0,
    definition: document.getElementById("tc-definition").value.trim() || null,
  };

  const res = editingTermKey
    ? await fetch(withRootPath(`/api/v1/term-configs/${encodeURIComponent(editingTermKey)}`), {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
    : await fetch(withRootPath("/api/v1/term-configs"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...body, term_key: termKey }),
    });

  if (res.ok) {
    document.getElementById("modal-term-config").close();
    await loadTermConfigTable();
    return;
  }
  const err = await res.json().catch(() => ({}));
  alert(err.detail || "저장에 실패했습니다.");
}

async function resetTermLabel(termKey) {
  if (!await showConfirmDialog("커스텀 표시명을 기본값으로 초기화하시겠습니까?", {
    title: "표시명 초기화",
    confirmText: "초기화",
  })) return;
  const res = await fetch(withRootPath(`/api/v1/term-configs/${encodeURIComponent(termKey)}/reset`), { method: "POST" });
  if (res.ok) {
    await loadTermConfigTable();
    return;
  }
  const err = await res.json().catch(() => ({}));
  alert(err.detail || "초기화에 실패했습니다.");
}
