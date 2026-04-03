const MDM_SELECTED_VENDOR_KEY = "mdm_selected_vendor";
const MDM_AUTO_COLLAPSE_KEY = "mdm_auto_collapse";
const MDM_SIMILAR_PANEL_WIDTH_KEY = "mdm_similar_panel_width";
const MDM_SIMILAR_OPEN_KEY = "mdm_similar_open";
let _mdmSimilarProductId = null;
let _mdmSimilarOpen = false;

let catalogIntegrityVendorGridApi = null;
let integrityProductGridApi = null;
let _integrityVendorAliases = [];
let _integrityVendorMode = "empty";
let _integrityVendorOriginal = null;
let _canManageVendor = false;
let _mdmAutoCollapse = localStorage.getItem(MDM_AUTO_COLLAPSE_KEY) === "true";

function mdmSetCollapsed(collapsed) {
  const layout = document.querySelector(".mdm-layout");
  if (!layout) return;
  if (collapsed) {
    layout.classList.add("mdm-list-collapsed");
  } else {
    layout.classList.remove("mdm-list-collapsed");
  }
  // 그리드 리사이즈 알림
  setTimeout(() => {
    catalogIntegrityVendorGridApi?.sizeColumnsToFit();
    integrityProductGridApi?.sizeColumnsToFit();
  }, 300);
}

function mdmUpdateAutoCollapseBtn() {
  const btn = document.getElementById("btn-mdm-auto-collapse");
  if (!btn) return;
  btn.classList.toggle("active", _mdmAutoCollapse);
  btn.title = _mdmAutoCollapse ? "선택 시 목록 자동 접기 (켜짐)" : "선택 시 목록 자동 접기 (꺼짐)";
}

function _isKorean(str) {
  return /[가-힣]/.test(str || "");
}

function _extractKoreanAlias(aliases) {
  for (const a of aliases) {
    if (_isKorean(a)) return a;
  }
  return "";
}

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
  document.getElementById("integrity-vendor-detail")?.classList.add("is-hidden");
  localStorage.removeItem(MDM_SELECTED_VENDOR_KEY);
  mdmSetCollapsed(false);
  closeMdmSimilarPanel();
}

function setIntegrityVendorNewMode() {
  _integrityVendorMode = "new";
  _integrityVendorOriginal = null;
  _integrityVendorAliases = [];

  document.getElementById("integrity-vendor-empty")?.classList.add("is-hidden");
  document.getElementById("integrity-vendor-detail")?.classList.remove("is-hidden");
  document.getElementById("integrity-vendor-title").textContent = "새 제조사";
  document.getElementById("integrity-vendor-canonical").value = "";
  document.getElementById("integrity-vendor-canonical").readOnly = false;
  document.getElementById("integrity-vendor-korean").value = "";
  document.getElementById("integrity-vendor-apply-row")?.classList.add("is-hidden");
  document.getElementById("btn-integrity-vendor-delete")?.classList.add("is-hidden");
  document.getElementById("integrity-product-title").textContent = "제품 목록";
  if (integrityProductGridApi) integrityProductGridApi.setGridOption("rowData", []);
  renderIntegrityVendorAliasChips();
}

function setIntegrityVendorEditMode(vendor, aliases, rowData) {
  _integrityVendorMode = "edit";
  _integrityVendorOriginal = vendor;
  const allAliasValues = (aliases || []).map((a) => a.alias_value);
  // name_ko가 있으면 우선, 없으면 alias에서 한글 추출
  const nameKo = rowData?.name_ko || "";
  const koreanName = nameKo || _extractKoreanAlias(allAliasValues);
  // 한글명과 동일한 alias는 alias 목록에서 제외
  _integrityVendorAliases = koreanName
    ? allAliasValues.filter((a) => a !== koreanName)
    : [...allAliasValues];

  document.getElementById("integrity-vendor-empty")?.classList.add("is-hidden");
  document.getElementById("integrity-vendor-detail")?.classList.remove("is-hidden");
  document.getElementById("integrity-vendor-title").textContent = vendor;
  document.getElementById("integrity-vendor-canonical").value = vendor;
  document.getElementById("integrity-vendor-canonical").readOnly = false;
  document.getElementById("integrity-vendor-korean").value = koreanName;
  document.getElementById("integrity-vendor-memo").value = rowData?.memo || "";
  document.getElementById("integrity-vendor-apply-row")?.classList.add("is-hidden");
  if (_canManageVendor) {
    document.getElementById("btn-integrity-vendor-delete")?.classList.remove("is-hidden");
  }
  renderIntegrityVendorAliasChips();
  loadIntegrityVendorProducts(vendor);
  closeMdmSimilarPanel();
  localStorage.setItem(MDM_SELECTED_VENDOR_KEY, vendor);
  if (_mdmAutoCollapse) mdmSetCollapsed(true);
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
  // 타이틀 실시간 반영
  if (canonical) {
    document.getElementById("integrity-vendor-title").textContent = canonical;
  }
}

async function saveIntegrityVendor() {
  const canonical = document.getElementById("integrity-vendor-canonical")?.value?.trim() || "";
  if (!canonical) {
    showToast("제조사명(영문)을 입력하세요.", "warning");
    return;
  }
  let koreanName = document.getElementById("integrity-vendor-korean")?.value?.trim() || "";
  // 한글명이 비어있으면 영문명으로 자동 채움
  if (!koreanName) {
    koreanName = canonical;
    document.getElementById("integrity-vendor-korean").value = canonical;
  }
  // 한글명을 alias에 병합 (영문명과 다른 경우에만)
  const allAliases = [..._integrityVendorAliases];
  if (koreanName && koreanName !== canonical && !allAliases.includes(koreanName)) {
    allAliases.unshift(koreanName);
  }
  const memo = document.getElementById("integrity-vendor-memo")?.value?.trim() || "";
  const payload = {
    rows: [
      {
        source_vendor: _integrityVendorMode === "edit" ? _integrityVendorOriginal : null,
        canonical_vendor: canonical,
        aliases: allAliases,
        apply_to_products: _integrityVendorMode === "edit" && canonical !== _integrityVendorOriginal
          ? !!document.getElementById("integrity-vendor-apply-products")?.checked
          : false,
        is_active: true,
        name_ko: koreanName !== canonical ? koreanName : null,
        memo: memo || null,
      },
    ],
  };
  await apiFetch("/api/v1/catalog-integrity/vendors/bulk-upsert", { method: "POST", body: payload });
  showToast("제조사를 저장했습니다.", "success");
  await loadCatalogIntegrityVendors();
  // 저장 후 그리드에서 해당 vendor 찾아 다시 편집모드 진입
  let targetNode = null;
  catalogIntegrityVendorGridApi?.forEachNode((node) => {
    if (node.data.vendor === canonical) targetNode = node;
  });
  if (targetNode) {
    targetNode.setSelected(true);
    setIntegrityVendorEditMode(targetNode.data.vendor, targetNode.data.aliases || [], targetNode.data);
  }
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

function initCatalogIntegrityVendorGrid() {
  const target = document.getElementById("grid-catalog-integrity-vendors");
  if (!target) return;
  catalogIntegrityVendorGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "vendor", headerName: "제조사", flex: 1, minWidth: 140, sort: "asc" },
      {
        field: "aliases",
        headerName: "Alias",
        flex: 1,
        minWidth: 140,
        sortable: false,
        filter: false,
        autoHeight: true,
        wrapText: true,
        cellStyle: { lineHeight: "1.6", paddingTop: "4px", paddingBottom: "4px" },
        cellRenderer: (params) => {
          const aliases = params.value || [];
          if (!aliases.length) return "";
          return aliases.map((a) => {
            const val = String(a.alias_value || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
            return `<span class="tag-chip tag-chip-sm">${val}</span>`;
          }).join(" ");
        },
      },
      { field: "product_count", headerName: "제품 수", width: 90 },
    ],
    rowSelection: { mode: "singleRow" },
    defaultColDef: {
      sortable: true,
      filter: true,
      resizable: true,
    },
    onRowClicked: (event) => {
      const row = event.data || {};
      setIntegrityVendorEditMode(row.vendor, row.aliases || [], row);
    },
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">제조사 데이터가 없습니다.</span>',
  });
}

function initIntegrityProductGrid() {
  const target = document.getElementById("grid-integrity-products");
  if (!target) return;
  integrityProductGridApi = agGrid.createGrid(target, {
    columnDefs: [
      { field: "name", headerName: "제품명", flex: 1, minWidth: 200 },
      {
        headerName: "분류",
        width: 200,
        valueGetter: (params) => {
          const d = params.data || {};
          const parts = [d.classification_level_2_name, d.classification_level_3_name].filter(Boolean);
          return parts.join(" > ") || d.product_type || "";
        },
      },
    ],
    rowSelection: { mode: "singleRow" },
    defaultColDef: { sortable: true, filter: true, resizable: true },
    onRowClicked: (event) => {
      const row = event.data;
      if (row && row.id) {
        openMdmSimilarPanel(row);
      }
    },
    overlayNoRowsTemplate: '<span class="ag-overlay-loading-center">제조사를 선택하세요.</span>',
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

async function loadIntegrityVendorProducts(vendor) {
  if (!integrityProductGridApi || !vendor) return;
  document.getElementById("integrity-product-title").textContent = `${vendor} 제품 목록`;
  const q = document.getElementById("integrity-product-search")?.value?.trim() || "";
  let url = `/api/v1/product-catalog?vendor=${encodeURIComponent(vendor)}`;
  if (q) url += `&q=${encodeURIComponent(q)}`;
  try {
    const rows = await apiFetch(url);
    integrityProductGridApi.setGridOption("rowData", rows);
    if (!rows.length) {
      integrityProductGridApi.setGridOption("overlayNoRowsTemplate", '<span class="ag-overlay-loading-center">등록된 제품이 없습니다.</span>');
      integrityProductGridApi.showNoRowsOverlay();
    } else {
      integrityProductGridApi.hideOverlay();
    }
  } catch (err) {
    console.error(err);
  }
}

function setMdmSimilarPanelOpen(isOpen) {
  _mdmSimilarOpen = isOpen;
  const splitter = document.getElementById("mdm-similar-splitter");
  const handleWrap = document.getElementById("mdm-similar-handle-wrap");
  const panel = document.getElementById("mdm-similar-panel");
  const btn = document.getElementById("btn-mdm-similar-toggle");
  if (!splitter || !handleWrap || !panel || !btn) return;

  splitter.classList.toggle("hidden", !isOpen);
  handleWrap.classList.toggle("hidden", !isOpen);
  panel.classList.toggle("hidden", !isOpen);
  btn.textContent = isOpen ? "\u276E" : "\u276F";
  localStorage.setItem(MDM_SIMILAR_OPEN_KEY, isOpen ? "1" : "0");
}

function closeMdmSimilarPanel() {
  _mdmSimilarProductId = null;
  setMdmSimilarPanelOpen(false);
}

async function openMdmSimilarPanel(product) {
  _mdmSimilarProductId = product.id;
  setMdmSimilarPanelOpen(true);

  const nameEl = document.getElementById("mdm-similar-selected-name");
  const metaEl = document.getElementById("mdm-similar-selected-meta");
  if (nameEl) nameEl.textContent = ((product.vendor || "") + " " + (product.name || "")).trim();

  const parts = [product.classification_level_2_name, product.classification_level_3_name].filter(Boolean);
  const classPath = parts.join(" > ") || product.product_type || "";
  if (metaEl) metaEl.textContent = classPath;

  await loadMdmSimilarProducts(product);
}

async function loadMdmSimilarProducts(product) {
  const listEl = document.getElementById("mdm-similar-list");
  const emptyEl = document.getElementById("mdm-similar-empty");
  if (!listEl || !emptyEl) return;

  listEl.textContent = "";
  emptyEl.classList.add("hidden");

  try {
    const result = await apiFetch("/api/v1/product-catalog/similarity-check", {
      method: "POST",
      body: {
        vendor: product.vendor || "",
        name: product.name || "",
        exclude_product_id: product.id,
      },
    });

    const items = [...(result.exact_matches || []), ...(result.similar_matches || [])];
    if (!items.length) {
      emptyEl.classList.remove("hidden");
      return;
    }

    for (const item of items) {
      listEl.appendChild(renderMdmSimilarCard(item, product));
    }
  } catch (err) {
    console.error("similarity check failed:", err);
    emptyEl.classList.remove("hidden");
  }
}

function _createEl(tag, className, textContent) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (textContent != null) el.textContent = textContent;
  return el;
}

function renderMdmSimilarCard(item, targetProduct) {
  const card = _createEl("div", "mdm-similar-card");

  const header = _createEl("div", "mdm-similar-card-header");
  const nameSpan = _createEl("span", "mdm-similar-card-name", (item.vendor || "") + " " + (item.name || ""));
  const scoreClass = item.score >= 90 ? "score-high" : "score-medium";
  const scoreSpan = _createEl("span", "mdm-similar-score " + scoreClass, String(item.score));
  header.appendChild(nameSpan);
  header.appendChild(scoreSpan);
  card.appendChild(header);

  const meta = _createEl("div", "mdm-similar-card-meta", "\uc790\uc0b0 " + (item.asset_count ?? 0) + "\uac74");
  card.appendChild(meta);

  const actions = _createEl("div", "mdm-similar-card-actions");

  const mergeBtn = _createEl("button", "btn btn-primary btn-sm btn-merge vendor-write-only", "\u2190 \ubcd1\ud569");
  mergeBtn.type = "button";
  mergeBtn.addEventListener("click", async () => {
    const sourceLabel = (item.vendor || "") + " " + (item.name || "");
    const targetLabel = ((targetProduct.vendor || "") + " " + (targetProduct.name || "")).trim();
    const msg = "\uc81c\ud488 '" + sourceLabel + "'(\uc790\uc0b0 " + (item.asset_count ?? 0) + "\uac74)\uc744 '" + targetLabel + "'\uc73c\ub85c \ubcd1\ud569\ud569\ub2c8\ub2e4.\n\n\uc790\uc0b0\uc774 \ub300\uc0c1 \uc81c\ud488\uc73c\ub85c \uc774\uc804\ub418\uace0, \uc6d0\ubcf8 \uc81c\ud488\uc740 \uc0ad\uc81c\ub429\ub2c8\ub2e4.";
    if (!confirm(msg)) return;

    try {
      const result = await apiFetch("/api/v1/product-catalog/merge", {
        method: "POST",
        body: { source_id: item.id, target_id: targetProduct.id },
      });
      showToast("\ubcd1\ud569 \uc644\ub8cc: \uc790\uc0b0 " + result.merged_asset_count + "\uac74 \uc774\uc804", "success");
      if (_integrityVendorOriginal) {
        await loadIntegrityVendorProducts(_integrityVendorOriginal);
      }
      await loadMdmSimilarProducts(targetProduct);
    } catch (err) {
      showToast(err.message || "\ubcd1\ud569\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.", "error");
    }
  });
  actions.appendChild(mergeBtn);

  const dismissBtn = _createEl("button", "btn btn-secondary btn-sm btn-dismiss vendor-write-only", "\ubb34\uc2dc");
  dismissBtn.type = "button";
  dismissBtn.addEventListener("click", async () => {
    try {
      await apiFetch("/api/v1/product-catalog/similarity-dismiss", {
        method: "POST",
        body: { product_id_a: targetProduct.id, product_id_b: item.id },
      });
      card.remove();
      const listEl = document.getElementById("mdm-similar-list");
      if (listEl && !listEl.children.length) {
        document.getElementById("mdm-similar-empty")?.classList.remove("hidden");
      }
      showToast("\uc720\uc0ac \uad00\uacc4\ub97c \ubb34\uc2dc\ud588\uc2b5\ub2c8\ub2e4.", "success");
    } catch (err) {
      showToast(err.message || "\ubb34\uc2dc \ucc98\ub9ac\uc5d0 \uc2e4\ud328\ud588\uc2b5\ub2c8\ub2e4.", "error");
    }
  });
  actions.appendChild(dismissBtn);

  card.appendChild(actions);

  if (!_canManageVendor) {
    card.querySelectorAll(".vendor-write-only").forEach((el) => { el.style.display = "none"; });
  }

  return card;
}

function initMdmSimilarSplitter() {
  const splitter = document.getElementById("mdm-similar-splitter");
  const panel = document.getElementById("mdm-similar-panel");
  if (!splitter || !panel) return;

  const saved = localStorage.getItem(MDM_SIMILAR_PANEL_WIDTH_KEY);
  if (saved) panel.style.flexBasis = saved + "px";

  splitter.addEventListener("mousedown", (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = panel.getBoundingClientRect().width;
    const onMove = (ev) => {
      const newW = Math.max(260, Math.min(startW + (startX - ev.clientX), window.innerWidth * 0.5));
      panel.style.flexBasis = newW + "px";
    };
    const onUp = () => {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      localStorage.setItem(MDM_SIMILAR_PANEL_WIDTH_KEY, Math.round(panel.getBoundingClientRect().width));
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initCatalogIntegrityVendorGrid();
  mdmUpdateAutoCollapseBtn();

  document.getElementById("btn-mdm-auto-collapse")?.addEventListener("click", () => {
    _mdmAutoCollapse = !_mdmAutoCollapse;
    localStorage.setItem(MDM_AUTO_COLLAPSE_KEY, _mdmAutoCollapse);
    mdmUpdateAutoCollapseBtn();
    // 이미 편집 중이면 즉시 접기/펼치기
    if (_integrityVendorMode === "edit") {
      mdmSetCollapsed(_mdmAutoCollapse);
    }
  });
  initIntegrityProductGrid();
  initMdmSimilarSplitter();
  document.getElementById("btn-mdm-similar-toggle")?.addEventListener("click", () => {
    if (_mdmSimilarOpen) {
      closeMdmSimilarPanel();
    } else if (_mdmSimilarProductId) {
      setMdmSimilarPanelOpen(true);
    }
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
  document.getElementById("integrity-vendor-korean")?.addEventListener("blur", () => {
    const koreanEl = document.getElementById("integrity-vendor-korean");
    const canonical = document.getElementById("integrity-vendor-canonical")?.value?.trim() || "";
    if (koreanEl && !koreanEl.value.trim() && canonical) {
      koreanEl.value = canonical;
    }
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
  document.getElementById("integrity-product-search")?.addEventListener("input", () => {
    if (_integrityVendorOriginal) {
      loadIntegrityVendorProducts(_integrityVendorOriginal).catch((err) => console.error(err));
    }
  });
  loadIntegrityPermissions().then(() => {
    loadCatalogIntegrityVendors().then(() => {
      const savedVendor = localStorage.getItem(MDM_SELECTED_VENDOR_KEY);
      if (savedVendor && catalogIntegrityVendorGridApi) {
        let targetNode = null;
        catalogIntegrityVendorGridApi.forEachNode((node) => {
          if (node.data.vendor === savedVendor) targetNode = node;
        });
        if (targetNode) {
          targetNode.setSelected(true);
          catalogIntegrityVendorGridApi.ensureNodeVisible(targetNode);
          setIntegrityVendorEditMode(targetNode.data.vendor, targetNode.data.aliases || [], targetNode.data);
        }
      }
    }).catch((err) => console.error(err));
  });

  // 스플리터 드래그
  const splitter = document.getElementById("mdm-splitter");
  const vendorPanel = document.getElementById("mdm-list-panel");
  if (splitter && vendorPanel) {
    const STORAGE_KEY = "mdm_list_panel_width";
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) vendorPanel.style.width = saved + "px";

    splitter.addEventListener("mousedown", (e) => {
      e.preventDefault();
      const startX = e.clientX;
      const startW = vendorPanel.getBoundingClientRect().width;
      const onMove = (ev) => {
        const newW = Math.max(320, Math.min(startW + ev.clientX - startX, window.innerWidth * 0.5));
        vendorPanel.style.width = newW + "px";
      };
      const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        localStorage.setItem(STORAGE_KEY, Math.round(vendorPanel.getBoundingClientRect().width));
        if (catalogIntegrityVendorGridApi) catalogIntegrityVendorGridApi.sizeColumnsToFit();
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }

  // 접힌 목록 패널 클릭 시 펼치기
  document.getElementById("mdm-list-panel")?.addEventListener("click", (e) => {
    const layout = document.querySelector(".mdm-layout");
    if (layout?.classList.contains("mdm-list-collapsed")) {
      // 토글 버튼 클릭은 무시 (자체 핸들러가 처리)
      if (e.target.closest("#btn-mdm-auto-collapse")) return;
      mdmSetCollapsed(false);
    }
  });
});
