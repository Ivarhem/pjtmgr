const ROLE_STATUS_LABELS = {
  active: "활성",
  inactive: "비활성",
  retired: "종료",
};

const ASSIGNMENT_TYPE_LABELS = {
  primary: "주 담당",
  secondary: "보조",
  backup: "예비/대체",
  temporary: "임시",
};

let roleGridApi;
let _selectedRole = null;
let _rolePartnerAssetsCache = [];

/* ── Tree state ── */
let _roleTreeData = {};            // { domain: { center: { family: [roles] } } }
let _selectedTreeNode = "";        // e.g. "네트워크>IDC-A>방화벽"
let _roleTreeSearchQuery = "";
const _roleTreeCollapsed = new Set();

const ROLE_TREE_COLLAPSED_KEY = "role_tree_collapsed_nodes";
const ROLE_TREE_SEARCH_KEY = "role_tree_search_query";
const ROLE_CATEGORY_WIDTH_KEY = "role_category_width";
const ROLE_LIST_WIDTH_KEY = "role_list_width";
const ROLE_DETAIL_OPEN_KEY = "role_detail_open";

const UNCLASSIFIED = "미분류";

const roleColumnDefs = [
  { field: "role_name", headerName: "역할명", flex: 1, minWidth: 150, sort: "asc" },
];

/* ── Grid ── */

async function initRoleGrid() {
  const gridDiv = document.getElementById("grid-asset-roles");
  roleGridApi = agGrid.createGrid(gridDiv, {
    columnDefs: roleColumnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    isExternalFilterPresent: isRoleExternalFilterPresent,
    doesExternalFilterPass: doesRoleExternalFilterPass,
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => showRoleDetail(data),
    }),
  });
  if (getCtxPartnerId()) loadAssetRoles();
}

async function loadAssetRoles() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) {
    roleGridApi.setGridOption("rowData", []);
    buildRoleTree([]);
    renderRoleTree();
    updateRoleListMeta();
    return;
  }
  let url = `/api/v1/asset-roles?partner_id=${partnerId}`;
  const projectId = getCtxProjectId();
  if (projectId && isProjectFilterActive()) {
    url += `&contract_period_id=${projectId}`;
  }
  try {
    const rows = await apiFetch(url);
    roleGridApi.setGridOption("rowData", rows);
    buildRoleTree(rows);
    renderRoleTree();
    applyRoleFilter();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Tree: build ── */

function buildRoleTree(roles) {
  _roleTreeData = {};
  (roles || []).forEach((role) => {
    const domain = role.current_asset_domain || UNCLASSIFIED;
    const center = role.current_asset_center_label || UNCLASSIFIED;
    const family = role.current_asset_product_family || UNCLASSIFIED;
    const vendor = role.current_asset_vendor || UNCLASSIFIED;
    if (!_roleTreeData[domain]) _roleTreeData[domain] = {};
    if (!_roleTreeData[domain][center]) _roleTreeData[domain][center] = {};
    if (!_roleTreeData[domain][center][family]) _roleTreeData[domain][center][family] = {};
    if (!_roleTreeData[domain][center][family][vendor]) _roleTreeData[domain][center][family][vendor] = [];
    _roleTreeData[domain][center][family][vendor].push(role);
  });
}

/* ── Tree: render ── */

function renderRoleTree() {
  const container = document.getElementById("role-classification-tree");
  if (!container) return;

  const domainKeys = Object.keys(_roleTreeData).sort((a, b) => a.localeCompare(b, "ko-KR"));
  if (!domainKeys.length) {
    container.textContent = "";
    const emptyDiv = document.createElement("div");
    emptyDiv.className = "catalog-classification-empty";
    emptyDiv.textContent = "역할이 없습니다.";
    container.appendChild(emptyDiv);
    return;
  }

  const query = _roleTreeSearchQuery.trim().toLocaleLowerCase("ko-KR");

  const rootUl = document.createElement("ul");
  rootUl.className = "classification-tree-root";
  let hasAnyNodes = false;

  domainKeys.forEach((domain) => {
    const centers = _roleTreeData[domain];
    const centerKeys = Object.keys(centers).sort((a, b) => a.localeCompare(b, "ko-KR"));

    const centerUl = document.createElement("ul");
    let domainCount = 0;
    let domainHasVisibleChildren = false;

    centerKeys.forEach((center) => {
      const families = centers[center];
      const familyKeys = Object.keys(families).sort((a, b) => a.localeCompare(b, "ko-KR"));

      const familyUl = document.createElement("ul");
      let centerCount = 0;
      let centerHasVisibleChildren = false;

      familyKeys.forEach((family) => {
        const vendors = families[family];
        const vendorKeys = Object.keys(vendors).sort((a, b) => a.localeCompare(b, "ko-KR"));

        const vendorUl = document.createElement("ul");
        let familyCount = 0;
        let familyHasVisibleChildren = false;

        vendorKeys.forEach((vendor) => {
          const count = vendors[vendor].length;
          familyCount += count;

          if (query && !vendor.toLocaleLowerCase("ko-KR").includes(query)
              && !family.toLocaleLowerCase("ko-KR").includes(query)
              && !center.toLocaleLowerCase("ko-KR").includes(query)
              && !domain.toLocaleLowerCase("ko-KR").includes(query)) {
            return;
          }

          const vendorKey = `${domain}>${center}>${family}>${vendor}`;
          const isSelected = _selectedTreeNode === vendorKey;
          vendorUl.appendChild(createTreeLeafNode(vendorKey, vendor, count, isSelected));
          familyHasVisibleChildren = true;
        });

        centerCount += familyCount;

        if (query && !familyHasVisibleChildren && !family.toLocaleLowerCase("ko-KR").includes(query)
            && !center.toLocaleLowerCase("ko-KR").includes(query)
            && !domain.toLocaleLowerCase("ko-KR").includes(query)) {
          return;
        }

        const familyKey = `${domain}>${center}>${family}`;
        const isFamilySelected = _selectedTreeNode === familyKey;
        const familyForceExpanded = !!query;
        const familyCollapsed = familyHasVisibleChildren && !familyForceExpanded && _roleTreeCollapsed.has(familyKey);
        familyUl.appendChild(createTreeBranchNode(familyKey, family, familyCount, isFamilySelected, familyHasVisibleChildren, familyCollapsed, vendorUl));
        centerHasVisibleChildren = true;
      });

      if (query && !centerHasVisibleChildren && !center.toLocaleLowerCase("ko-KR").includes(query)
          && !domain.toLocaleLowerCase("ko-KR").includes(query)) {
        return;
      }

      domainCount += centerCount;
      const centerKey = `${domain}>${center}`;
      const isSelected = _selectedTreeNode === centerKey;
      const forceExpanded = !!query;
      const collapsed = centerHasVisibleChildren && !forceExpanded && _roleTreeCollapsed.has(centerKey);
      centerUl.appendChild(createTreeBranchNode(centerKey, center, centerCount, isSelected, centerHasVisibleChildren, collapsed, familyUl));
      domainHasVisibleChildren = true;
    });

    if (query && !domainHasVisibleChildren && !domain.toLocaleLowerCase("ko-KR").includes(query)) {
      return;
    }

    const domainKey = domain;
    const isSelected = _selectedTreeNode === domainKey;
    const forceExpanded = !!query;
    const collapsed = domainHasVisibleChildren && !forceExpanded && _roleTreeCollapsed.has(domainKey);
    rootUl.appendChild(createTreeBranchNode(domainKey, domain, domainCount, isSelected, domainHasVisibleChildren, collapsed, centerUl));
    hasAnyNodes = true;
  });

  container.textContent = "";
  if (!hasAnyNodes) {
    const emptyDiv = document.createElement("div");
    emptyDiv.className = "catalog-classification-empty";
    emptyDiv.textContent = "검색 결과가 없습니다.";
    container.appendChild(emptyDiv);
    return;
  }
  container.appendChild(rootUl);
}

function createTreeLeafNode(key, label, count, isSelected) {
  const li = document.createElement("li");
  li.className = "classification-tree-item";

  const nodeDiv = document.createElement("div");
  nodeDiv.className = "classification-tree-node" + (isSelected ? " is-selected" : "");

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "classification-tree-node-main";
  btn.setAttribute("data-role-tree-key", key);

  const toggle = document.createElement("span");
  toggle.className = "classification-tree-toggle is-placeholder";
  toggle.textContent = "\u2022";

  const mainSpan = document.createElement("span");
  mainSpan.className = "classification-tree-main";

  const titleSpan = document.createElement("span");
  titleSpan.className = "classification-tree-title";

  const nameSpan = document.createElement("span");
  nameSpan.className = "classification-tree-name";
  nameSpan.textContent = label;

  const codeSpan = document.createElement("span");
  codeSpan.className = "classification-tree-code";
  codeSpan.textContent = String(count);

  titleSpan.appendChild(nameSpan);
  titleSpan.appendChild(codeSpan);
  mainSpan.appendChild(titleSpan);
  btn.appendChild(toggle);
  btn.appendChild(mainSpan);
  nodeDiv.appendChild(btn);
  li.appendChild(nodeDiv);
  return li;
}

function createTreeBranchNode(key, label, count, isSelected, hasChildren, collapsed, childUl) {
  const li = document.createElement("li");
  li.className = "classification-tree-item";

  const nodeDiv = document.createElement("div");
  nodeDiv.className = "classification-tree-node" + (isSelected ? " is-selected" : "");

  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "classification-tree-node-main";
  btn.setAttribute("data-role-tree-key", key);

  const toggle = document.createElement("span");
  if (hasChildren) {
    toggle.className = "classification-tree-toggle";
    toggle.setAttribute("data-role-tree-toggle", key);
    toggle.textContent = collapsed ? "\u25B8" : "\u25BE";
  } else {
    toggle.className = "classification-tree-toggle is-placeholder";
    toggle.textContent = "\u2022";
  }

  const mainSpan = document.createElement("span");
  mainSpan.className = "classification-tree-main";

  const titleSpan = document.createElement("span");
  titleSpan.className = "classification-tree-title";

  const nameSpan = document.createElement("span");
  nameSpan.className = "classification-tree-name";
  nameSpan.textContent = label;

  const codeSpan = document.createElement("span");
  codeSpan.className = "classification-tree-code";
  codeSpan.textContent = String(count);

  titleSpan.appendChild(nameSpan);
  titleSpan.appendChild(codeSpan);
  mainSpan.appendChild(titleSpan);
  btn.appendChild(toggle);
  btn.appendChild(mainSpan);
  nodeDiv.appendChild(btn);
  li.appendChild(nodeDiv);

  if (hasChildren && !collapsed) {
    li.appendChild(childUl);
  }

  return li;
}

/* ── Tree: filter / external filter ── */

function applyRoleFilter() {
  if (!roleGridApi) return;
  roleGridApi.onFilterChanged();
  updateRoleListMeta();
}

function isRoleExternalFilterPresent() {
  const q = (document.getElementById("filter-role-search")?.value || "").trim();
  return !!(_selectedTreeNode || q);
}

function doesRoleExternalFilterPass(node) {
  const d = node.data;
  if (_selectedTreeNode) {
    const domain = d.current_asset_domain || UNCLASSIFIED;
    const center = d.current_asset_center_label || UNCLASSIFIED;
    const family = d.current_asset_product_family || UNCLASSIFIED;
    const vendor = d.current_asset_vendor || UNCLASSIFIED;
    const roleKey = `${domain}>${center}>${family}>${vendor}`;
    if (!roleKey.startsWith(_selectedTreeNode)) return false;
  }
  const q = (document.getElementById("filter-role-search")?.value || "").trim().toLowerCase();
  if (q && !(d.role_name || "").toLowerCase().includes(q)) return false;
  return true;
}

function updateRoleListMeta() {
  const titleEl = document.getElementById("role-list-title");
  const countEl = document.getElementById("role-list-count");
  let count = 0;
  roleGridApi?.forEachNodeAfterFilterAndSort(() => { count += 1; });
  if (titleEl) {
    if (_selectedTreeNode) {
      const parts = _selectedTreeNode.split(">");
      titleEl.textContent = parts[parts.length - 1] + " 역할";
    } else {
      titleEl.textContent = "전체 역할";
    }
  }
  if (countEl) countEl.textContent = `${count}건`;
}

/* ── Tree: events (delegated) ── */

function initRoleTreeEvents() {
  const container = document.getElementById("role-classification-tree");
  if (!container) return;

  container.addEventListener("click", (e) => {
    // Toggle collapse
    const toggleEl = e.target.closest("[data-role-tree-toggle]");
    if (toggleEl) {
      e.stopPropagation();
      const key = toggleEl.getAttribute("data-role-tree-toggle");
      if (_roleTreeCollapsed.has(key)) {
        _roleTreeCollapsed.delete(key);
      } else {
        _roleTreeCollapsed.add(key);
      }
      saveRoleTreeCollapsedState();
      renderRoleTree();
      return;
    }

    // Node click (select filter)
    const nodeBtn = e.target.closest("[data-role-tree-key]");
    if (nodeBtn) {
      const key = nodeBtn.getAttribute("data-role-tree-key");
      _selectedTreeNode = (_selectedTreeNode === key) ? "" : key;
      renderRoleTree();
      applyRoleFilter();
    }
  });
}

/* ── Tree: state persistence ── */

function saveRoleTreeCollapsedState() {
  try {
    localStorage.setItem(ROLE_TREE_COLLAPSED_KEY, JSON.stringify([..._roleTreeCollapsed]));
  } catch (_) {}
}

function loadRoleTreeCollapsedState() {
  try {
    const stored = localStorage.getItem(ROLE_TREE_COLLAPSED_KEY);
    if (stored) {
      const arr = JSON.parse(stored);
      if (Array.isArray(arr)) arr.forEach((k) => _roleTreeCollapsed.add(k));
    }
  } catch (_) {}
}

function loadRoleTreeSearchState() {
  _roleTreeSearchQuery = localStorage.getItem(ROLE_TREE_SEARCH_KEY) || "";
  const input = document.getElementById("role-tree-search");
  if (input) input.value = _roleTreeSearchQuery;
}

/* ── Detail Panel ── */

function showRoleDetail(role) {
  _selectedRole = role;
  toggleRoleDetailPanel(true);
  setElementHidden(document.getElementById("role-detail-empty"), true);
  setElementHidden(document.getElementById("role-detail-content"), false);

  document.getElementById("role-detail-title").textContent = role.role_name;
  document.getElementById("role-info-name").textContent = role.role_name;
  document.getElementById("role-info-status").textContent = ROLE_STATUS_LABELS[role.status] || role.status;
  document.getElementById("role-info-period").textContent = role.contract_period_label || "—";
  document.getElementById("role-info-current-asset").textContent =
    role.current_asset_name
      ? `${role.current_asset_name} (${role.current_asset_code || "—"})`
      : "미할당";
  document.getElementById("role-info-note").textContent = role.note || "—";

  syncRoleActionButtons();
  loadCurrentAssignments();
}

function closeRoleDetail() {
  _selectedRole = null;
  setElementHidden(document.getElementById("role-detail-empty"), false);
  setElementHidden(document.getElementById("role-detail-content"), true);
  syncRoleActionButtons();
}

function syncRoleActionButtons() {
  const hasCurrent = !!_selectedRole?.current_asset_id;
  ["btn-role-replacement", "btn-role-failover", "btn-role-repurpose", "btn-edit-role", "btn-delete-role"].forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    if (id === "btn-edit-role" || id === "btn-delete-role") {
      btn.disabled = !_selectedRole;
      return;
    }
    btn.disabled = !_selectedRole || !hasCurrent;
  });
}

/* ── Detail Panel Toggle ── */

function toggleRoleDetailPanel(show) {
  const mainPanel = document.getElementById("role-main-panel");
  const detailPanel = document.getElementById("role-detail-panel");
  const detailContent = document.getElementById("role-detail-content");
  const detailEmpty = document.getElementById("role-detail-empty");
  const splitter = document.getElementById("role-splitter");
  const handle = document.getElementById("btn-minimize-role-detail");
  if (!mainPanel || !detailPanel || !detailContent || !detailEmpty || !splitter || !handle) return;

  const isOpen = !!show;
  mainPanel.classList.toggle("is-detail-open", isOpen);
  detailPanel.classList.toggle("is-hidden", !isOpen);
  detailContent.classList.toggle("is-hidden", !isOpen || !_selectedRole);
  detailEmpty.classList.toggle("is-hidden", !!_selectedRole);
  splitter.classList.toggle("is-hidden", !isOpen);
  handle.textContent = isOpen ? "\u276E" : "\u276F";
  localStorage.setItem(ROLE_DETAIL_OPEN_KEY, isOpen ? "1" : "0");
}

function handleMinimizeRoleDetail() {
  const mainPanel = document.getElementById("role-main-panel");
  if (mainPanel?.classList.contains("is-detail-open")) {
    _selectedRole = null;
    toggleRoleDetailPanel(false);
  } else {
    toggleRoleDetailPanel(true);
  }
}

/* ── Current Assignments Grid ── */

let assignmentGridApi;

const assignmentColDefs = [
  { field: "asset_name", headerName: "자산명", flex: 1, minWidth: 160, valueFormatter: (p) => p.value || "—" },
  { field: "asset_code", headerName: "자산코드", width: 140, valueFormatter: (p) => p.value || "—" },
  { field: "assignment_type", headerName: "할당유형", width: 100, valueFormatter: (p) => ASSIGNMENT_TYPE_LABELS[p.value] || p.value || "—" },
  { field: "valid_from", headerName: "시작일", width: 110, valueFormatter: (p) => p.value || "—" },
  { field: "valid_to", headerName: "종료일", width: 110, valueFormatter: (p) => p.value || "현재" },
  { field: "note", headerName: "비고", width: 150, valueFormatter: (p) => p.value || "" },
];

function initAssignmentGrid() {
  const el = document.getElementById("grid-role-assignments");
  if (!el || assignmentGridApi) return;
  assignmentGridApi = agGrid.createGrid(el, {
    columnDefs: assignmentColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    domLayout: "autoHeight",
    ...buildStandardGridBehavior({
      type: 'modal-edit',
      onEdit: (data) => openRoleAssignmentModal(data),
    }),
  });
}

async function loadCurrentAssignments() {
  if (!assignmentGridApi) initAssignmentGrid();
  if (!_selectedRole) {
    assignmentGridApi?.setGridOption("rowData", []);
    return;
  }
  try {
    const rows = await apiFetch(`/api/v1/asset-roles/${_selectedRole.id}/assignments`);
    const current = rows.filter((r) => r.is_current);
    assignmentGridApi.setGridOption("rowData", current);
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Assignment History Modal ── */

async function openRoleHistoryModal() {
  if (!_selectedRole) return;
  const container = document.getElementById("role-history-content");
  container.textContent = "";
  document.getElementById("role-history-modal-title").textContent = `${_selectedRole.role_name} — 할당 이력`;

  try {
    const rows = await apiFetch(`/api/v1/asset-roles/${_selectedRole.id}/assignments`);
    if (!rows.length) {
      const empty = document.createElement("p");
      empty.className = "text-muted";
      empty.textContent = "할당 이력이 없습니다.";
      container.appendChild(empty);
    } else {
      const timeline = document.createElement("div");
      timeline.className = "asset-timeline";
      rows.forEach((row) => {
        const item = document.createElement("article");
        item.className = "asset-timeline-item";

        const marker = document.createElement("div");
        marker.className = "asset-timeline-marker asset-timeline-marker-" + (row.is_current ? "current" : "history");

        const main = document.createElement("div");
        main.className = "asset-timeline-main";

        const meta = document.createElement("div");
        meta.className = "asset-timeline-meta";
        const typeBadge = document.createElement("span");
        typeBadge.className = "badge";
        typeBadge.textContent = ASSIGNMENT_TYPE_LABELS[row.assignment_type] || row.assignment_type;
        const dateSpan = document.createElement("span");
        dateSpan.textContent = `${row.valid_from || "시작 미기재"} ~ ${row.valid_to || "현재"}`;
        meta.append(typeBadge, dateSpan);
        if (row.is_current) {
          const currentBadge = document.createElement("span");
          currentBadge.className = "badge badge-active";
          currentBadge.textContent = "현재 담당";
          meta.appendChild(currentBadge);
        }

        const title = document.createElement("div");
        title.className = "asset-timeline-title";
        title.textContent = [row.asset_name, row.asset_code].filter(Boolean).join(" / ") || "미지정 자산";
        main.append(meta, title);
        if (row.note) {
          const body = document.createElement("div");
          body.className = "asset-timeline-body";
          body.textContent = row.note;
          main.appendChild(body);
        }

        const actions = document.createElement("div");
        actions.className = "asset-timeline-actions";
        const editBtn = document.createElement("button");
        editBtn.className = "asset-subtable-action";
        editBtn.textContent = "수정";
        editBtn.addEventListener("click", () => {
          document.getElementById("modal-role-history").close();
          openRoleAssignmentModal(row);
        });
        const deleteBtn = document.createElement("button");
        deleteBtn.className = "asset-subtable-action danger";
        deleteBtn.textContent = "삭제";
        deleteBtn.addEventListener("click", async () => {
          await deleteRoleAssignment(row);
          openRoleHistoryModal();
        });
        actions.append(editBtn, deleteBtn);

        item.append(marker, main, actions);
        timeline.appendChild(item);
      });
      container.appendChild(timeline);
    }
  } catch (err) {
    showToast(err.message, "error");
  }

  document.getElementById("modal-role-history").showModal();
}

/* ── Role CRUD ── */

async function populateRolePeriodSelect(selectedId) {
  const select = document.getElementById("role-period-id");
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "-- 선택 안함 --";
  select.appendChild(empty);
  const partnerId = getCtxPartnerId();
  if (!partnerId) return;
  try {
    const periods = await apiFetch(`/api/v1/contract-periods?partner_id=${partnerId}`);
    periods.forEach((period) => {
      const opt = document.createElement("option");
      opt.value = period.id;
      opt.textContent = [period.period_label, period.contract_name].filter(Boolean).join(" · ") || `사업 #${period.id}`;
      if (period.id === selectedId) opt.selected = true;
      select.appendChild(opt);
    });
  } catch (_) {}
}

async function openRoleModal(role) {
  await populateRolePeriodSelect(role ? role.contract_period_id : getCtxProjectId());
  document.getElementById("asset-role-id").value = role ? role.id : "";
  document.getElementById("role-name").value = role ? role.role_name : "";
  document.getElementById("role-status").value = role ? role.status : "active";
  document.getElementById("role-note").value = role ? (role.note || "") : "";
  document.getElementById("asset-role-modal-title").textContent = role ? "역할 수정" : "역할 등록";
  document.getElementById("modal-asset-role").showModal();
}

async function saveRole() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) {
    showToast("고객사를 먼저 선택하세요.", "warning");
    return;
  }
  const roleId = document.getElementById("asset-role-id").value;
  const payload = {
    partner_id: partnerId,
    contract_period_id: document.getElementById("role-period-id").value ? Number(document.getElementById("role-period-id").value) : null,
    role_name: document.getElementById("role-name").value.trim(),
    status: document.getElementById("role-status").value,
    note: document.getElementById("role-note").value.trim() || null,
  };
  if (!payload.role_name) {
    showToast("역할명을 입력하세요.", "warning");
    return;
  }
  try {
    if (roleId) {
      await apiFetch(`/api/v1/asset-roles/${roleId}`, { method: "PATCH", body: payload });
    } else {
      await apiFetch("/api/v1/asset-roles", { method: "POST", body: payload });
    }
    document.getElementById("modal-asset-role").close();
    showToast(roleId ? "수정되었습니다." : "등록되었습니다.");
    await loadAssetRoles();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteRole() {
  if (!_selectedRole) return;
  const confirmed = await showConfirmDialog(`역할 "${_selectedRole.role_name}"을 삭제하시겠습니까?`, {
    title: "역할 삭제",
    confirmText: "삭제",
  });
  if (!confirmed) return;
  try {
    await apiFetch(`/api/v1/asset-roles/${_selectedRole.id}`, { method: "DELETE" });
    showToast("삭제되었습니다.");
    closeRoleDetail();
    await loadAssetRoles();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Assignment CRUD ── */

async function openRoleAssignmentModal(assignment) {
  const select = document.getElementById("assignment-asset-id");
  select.textContent = "";
  const emptyOpt = document.createElement("option");
  emptyOpt.value = "";
  emptyOpt.textContent = "-- 자산 선택 --";
  select.appendChild(emptyOpt);

  const partnerId = getCtxPartnerId();
  if (partnerId && !_rolePartnerAssetsCache.length) {
    try {
      _rolePartnerAssetsCache = await apiFetch(`/api/v1/assets?partner_id=${partnerId}`);
    } catch (_) {}
  }
  _rolePartnerAssetsCache.forEach((a) => {
    const opt = document.createElement("option");
    opt.value = a.id;
    opt.textContent = `${a.asset_name} (${a.asset_code || "—"})`;
    select.appendChild(opt);
  });

  document.getElementById("role-assignment-id").value = assignment ? assignment.id : "";
  select.value = assignment ? String(assignment.asset_id) : "";
  select.disabled = !!assignment;
  document.getElementById("assignment-type").value = assignment ? assignment.assignment_type : "primary";
  document.getElementById("assignment-valid-from").value = assignment?.valid_from || "";
  document.getElementById("assignment-valid-to").value = assignment?.valid_to || "";
  document.getElementById("assignment-is-current").checked = assignment ? assignment.is_current : true;
  document.getElementById("assignment-note").value = assignment?.note || "";
  document.getElementById("role-assignment-modal-title").textContent = assignment ? "할당 수정" : "할당 추가";
  document.getElementById("modal-role-assignment").showModal();
}

async function saveRoleAssignment() {
  const assignmentId = document.getElementById("role-assignment-id").value;
  const payload = {
    asset_id: Number(document.getElementById("assignment-asset-id").value),
    assignment_type: document.getElementById("assignment-type").value,
    valid_from: document.getElementById("assignment-valid-from").value || null,
    valid_to: document.getElementById("assignment-valid-to").value || null,
    is_current: document.getElementById("assignment-is-current").checked,
    note: document.getElementById("assignment-note").value.trim() || null,
  };
  if (!payload.asset_id) {
    showToast("자산을 선택하세요.", "warning");
    return;
  }
  try {
    if (assignmentId) {
      await apiFetch(`/api/v1/asset-roles/assignments/${assignmentId}`, { method: "PATCH", body: payload });
    } else {
      await apiFetch(`/api/v1/asset-roles/${_selectedRole.id}/assignments`, { method: "POST", body: payload });
    }
    document.getElementById("modal-role-assignment").close();
    showToast(assignmentId ? "수정되었습니다." : "할당되었습니다.");
    await loadAssetRoles();
    const rows = [];
    roleGridApi.forEachNode((n) => rows.push(n.data));
    const updated = rows.find((r) => r.id === _selectedRole?.id);
    if (updated) showRoleDetail(updated);
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteRoleAssignment(assignment) {
  const confirmed = await showConfirmDialog("이 할당 이력을 삭제하시겠습니까?", {
    title: "할당 삭제",
    confirmText: "삭제",
  });
  if (!confirmed) return;
  try {
    await apiFetch(`/api/v1/asset-roles/assignments/${assignment.id}`, { method: "DELETE" });
    showToast("삭제되었습니다.");
    await loadAssetRoles();
    const rows = [];
    roleGridApi.forEachNode((n) => rows.push(n.data));
    const updated = rows.find((r) => r.id === _selectedRole?.id);
    if (updated) showRoleDetail(updated);
    else closeRoleDetail();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Role Actions ── */

let _currentRoleAction = null;

function setRoleActionFieldVisibility(actionType) {
  const showAsset = actionType === "replacement" || actionType === "failover";
  const showNewRole = actionType === "repurpose";
  setElementHidden(document.getElementById("role-action-asset-wrap"), !showAsset);
  setElementHidden(document.getElementById("role-action-new-role-name-wrap"), !showNewRole);
  setElementHidden(document.getElementById("role-action-new-period-wrap"), !showNewRole);
}

async function openRoleActionModal(actionType) {
  if (!_selectedRole) return;
  const titleMap = { replacement: "교체", failover: "장애대체", repurpose: "용도전환" };
  document.getElementById("role-action-modal-title").textContent = titleMap[actionType] || actionType;
  document.getElementById("role-action-modal-desc").textContent =
    `현재 ${_selectedRole.role_name}의 담당 자산에 대한 ${titleMap[actionType] || actionType} 처리를 진행합니다.`;
  setRoleActionFieldVisibility(actionType);
  _currentRoleAction = actionType;

  if (actionType === "replacement" || actionType === "failover") {
    const select = document.getElementById("role-action-asset-id");
    select.textContent = "";
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = "-- 대상 자산 선택 --";
    select.appendChild(emptyOpt);
    const partnerId = getCtxPartnerId();
    if (partnerId && !_rolePartnerAssetsCache.length) {
      try {
        _rolePartnerAssetsCache = await apiFetch(`/api/v1/assets?partner_id=${partnerId}`);
      } catch (_) {}
    }
    _rolePartnerAssetsCache.forEach((a) => {
      const opt = document.createElement("option");
      opt.value = a.id;
      opt.textContent = `${a.asset_name} (${a.asset_code || "—"})`;
      select.appendChild(opt);
    });
  }
  if (actionType === "repurpose") {
    document.getElementById("role-action-new-role-name").value = "";
    await populateRoleActionPeriodSelect();
  }
  document.getElementById("role-action-occurred-at").value = "";
  document.getElementById("role-action-note").value = "";
  document.getElementById("modal-role-action").showModal();
}

async function populateRoleActionPeriodSelect() {
  const select = document.getElementById("role-action-new-period-id");
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "-- 선택 안함 --";
  select.appendChild(empty);
  const partnerId = getCtxPartnerId();
  if (!partnerId) return;
  try {
    const periods = await apiFetch(`/api/v1/contract-periods?partner_id=${partnerId}`);
    periods.forEach((period) => {
      const opt = document.createElement("option");
      opt.value = period.id;
      opt.textContent = [period.period_label, period.contract_name].filter(Boolean).join(" · ") || `사업 #${period.id}`;
      select.appendChild(opt);
    });
  } catch (_) {}
}

async function saveRoleAction() {
  const occurredAt = document.getElementById("role-action-occurred-at").value;
  const note = document.getElementById("role-action-note").value.trim() || null;
  let endpoint = "";
  let payload = {
    occurred_at: occurredAt ? new Date(occurredAt).toISOString() : null,
    note,
  };

  if (_currentRoleAction === "replacement" || _currentRoleAction === "failover") {
    const replacementAssetId = document.getElementById("role-action-asset-id").value;
    if (!replacementAssetId) {
      showToast("대상 자산을 선택하세요.", "warning");
      return;
    }
    payload.replacement_asset_id = Number(replacementAssetId);
    endpoint = `/api/v1/asset-roles/${_selectedRole.id}/actions/${_currentRoleAction}`;
  } else if (_currentRoleAction === "repurpose") {
    const newRoleName = document.getElementById("role-action-new-role-name").value.trim();
    if (!newRoleName) {
      showToast("신규 역할명을 입력하세요.", "warning");
      return;
    }
    payload.new_role_name = newRoleName;
    payload.new_contract_period_id = document.getElementById("role-action-new-period-id").value
      ? Number(document.getElementById("role-action-new-period-id").value)
      : null;
    endpoint = `/api/v1/asset-roles/${_selectedRole.id}/actions/repurpose`;
  }

  try {
    const result = await apiFetch(endpoint, { method: "POST", body: payload });
    document.getElementById("modal-role-action").close();
    showToast(result.message || "처리되었습니다.");
    await loadAssetRoles();
    const rows = [];
    roleGridApi.forEachNode((node) => rows.push(node.data));
    const targetRoleId = result.target_role_id || _selectedRole.id;
    const updated = rows.find((item) => item.id === targetRoleId);
    if (updated) showRoleDetail(updated);
    else closeRoleDetail();
  } catch (err) {
    showToast(err.message, "error");
  }
}

/* ── Splitters ── */

function initRoleTreeSplitter() {
  const splitter = document.getElementById("role-category-splitter");
  const layout = document.querySelector(".catalog-layout");
  if (!splitter || !layout) return;
  const storedWidth = Number(localStorage.getItem(ROLE_CATEGORY_WIDTH_KEY) || 0);
  if (storedWidth >= 280 && storedWidth <= 520) {
    layout.style.setProperty("--catalog-category-width", `${storedWidth}px`);
  }
  let dragging = false;
  splitter.addEventListener("mousedown", (event) => {
    dragging = true;
    splitter.classList.add("is-dragging");
    event.preventDefault();
  });
  document.addEventListener("mousemove", (event) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    const width = Math.min(520, Math.max(280, event.clientX - rect.left));
    layout.style.setProperty("--catalog-category-width", `${width}px`);
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    const current = parseInt(getComputedStyle(layout).getPropertyValue("--catalog-category-width"), 10);
    if (!Number.isNaN(current)) {
      localStorage.setItem(ROLE_CATEGORY_WIDTH_KEY, String(current));
    }
  });
}

function initRoleDetailSplitter() {
  const splitter = document.getElementById("role-splitter");
  const listPanel = document.getElementById("role-list-panel");
  const mainPanel = document.getElementById("role-main-panel");
  if (!splitter || !listPanel || !mainPanel) return;
  const storedWidth = Number(localStorage.getItem(ROLE_LIST_WIDTH_KEY) || 0);
  if (storedWidth >= 15 && storedWidth <= 80) {
    mainPanel.style.setProperty("--catalog-list-width", `${storedWidth}%`);
  }
  let dragging = false;
  splitter.addEventListener("mousedown", (e) => {
    dragging = true;
    splitter.classList.add("is-dragging");
    e.preventDefault();
  });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = mainPanel.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    if (pct > 15 && pct < 80) {
      mainPanel.style.setProperty("--catalog-list-width", `${pct}%`);
    }
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    const current = parseFloat(getComputedStyle(mainPanel).getPropertyValue("--catalog-list-width"));
    if (!Number.isNaN(current)) {
      localStorage.setItem(ROLE_LIST_WIDTH_KEY, String(current));
    }
  });
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", async () => {
  loadRoleTreeCollapsedState();
  loadRoleTreeSearchState();
  initRoleTreeSplitter();
  initRoleDetailSplitter();
  initRoleTreeEvents();
  initRoleGrid();

  // Restore detail panel open state
  if (localStorage.getItem(ROLE_DETAIL_OPEN_KEY) === "1") {
    toggleRoleDetailPanel(true);
  }
});
document.getElementById("btn-add-role").addEventListener("click", () => openRoleModal());
document.getElementById("btn-role-replacement").addEventListener("click", () => openRoleActionModal("replacement"));
document.getElementById("btn-role-failover").addEventListener("click", () => openRoleActionModal("failover"));
document.getElementById("btn-role-repurpose").addEventListener("click", () => openRoleActionModal("repurpose"));
document.getElementById("btn-edit-role").addEventListener("click", () => {
  if (_selectedRole) openRoleModal(_selectedRole);
});
document.getElementById("btn-delete-role").addEventListener("click", deleteRole);
document.getElementById("btn-add-role-assignment").addEventListener("click", () => openRoleAssignmentModal());
document.getElementById("btn-role-history").addEventListener("click", openRoleHistoryModal);
document.getElementById("btn-close-role-history").addEventListener("click", () => document.getElementById("modal-role-history").close());
document.getElementById("btn-cancel-role").addEventListener("click", () => document.getElementById("modal-asset-role").close());
document.getElementById("btn-save-role").addEventListener("click", saveRole);
document.getElementById("btn-cancel-role-assignment").addEventListener("click", () => document.getElementById("modal-role-assignment").close());
document.getElementById("btn-save-role-assignment").addEventListener("click", saveRoleAssignment);
document.getElementById("btn-cancel-role-action").addEventListener("click", () => document.getElementById("modal-role-action").close());
document.getElementById("btn-save-role-action").addEventListener("click", saveRoleAction);
document.getElementById("btn-minimize-role-detail").addEventListener("click", handleMinimizeRoleDetail);
document.getElementById("btn-clear-role-tree-filter").addEventListener("click", () => {
  _selectedTreeNode = "";
  renderRoleTree();
  applyRoleFilter();
});

document.getElementById("filter-role-search").addEventListener("input", () => {
  applyRoleFilter();
});

document.getElementById("role-tree-search").addEventListener("input", (e) => {
  _roleTreeSearchQuery = e.target.value.trim();
  try {
    localStorage.setItem(ROLE_TREE_SEARCH_KEY, _roleTreeSearchQuery);
  } catch (_) {}
  renderRoleTree();
});

initProjectFilterCheckbox(loadAssetRoles);
window.addEventListener("ctx-changed", () => {
  _selectedTreeNode = "";
  closeRoleDetail();
  _rolePartnerAssetsCache = [];
  loadAssetRoles();
});
