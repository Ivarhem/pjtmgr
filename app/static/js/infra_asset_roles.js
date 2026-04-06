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
let _currentRoleTab = "basic";
let _rolePartnerAssetsCache = [];
let _currentRoleAction = null;

const roleColumnDefs = [
  { field: "role_name", headerName: "역할명", flex: 1, minWidth: 180, sort: "asc" },
  { field: "role_type", headerName: "유형", width: 140, valueFormatter: (p) => p.value || "—" },
  { field: "current_asset_name", headerName: "현재 자산", width: 180, valueFormatter: (p) => p.value || "미할당" },
  { field: "current_asset_code", headerName: "현재 자산코드", width: 140, valueFormatter: (p) => p.value || "—" },
  {
    field: "current_asset_status",
    headerName: "자산 상태",
    width: 110,
    valueFormatter: (p) => p.value ? getAssetStatusLabel(p.value) : "—",
  },
  {
    field: "status",
    headerName: "역할 상태",
    width: 110,
    cellRenderer: (params) => {
      const span = document.createElement("span");
      span.className = "badge badge-" + (params.value || "planned");
      span.textContent = ROLE_STATUS_LABELS[params.value] || params.value || "—";
      return span;
    },
  },
];

function getAssetStatusLabel(value) {
  return {
    active: "운영중",
    planned: "계획",
    decommissioned: "폐기",
    failed: "장애",
  }[value] || value;
}

async function initRoleGrid() {
  const gridDiv = document.getElementById("grid-asset-roles");
  roleGridApi = agGrid.createGrid(gridDiv, {
    columnDefs: roleColumnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true, filter: true },
    rowSelection: "single",
    animateRows: true,
    enableCellTextSelection: true,
    ...buildStandardGridBehavior({
      type: 'detail-panel',
      onSelect: (data) => showRoleDetail(data),
      onEdit: (data) => openRoleModal(data),
    }),
  });
  if (getCtxPartnerId()) loadAssetRoles();
}

async function loadAssetRoles() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) {
    roleGridApi.setGridOption("rowData", []);
    return;
  }
  let url = `/api/v1/asset-roles?partner_id=${partnerId}`;
  const status = document.getElementById("filter-role-status").value;
  const projectId = getCtxProjectId();
  if (projectId && isProjectFilterActive()) {
    url += `&contract_period_id=${projectId}`;
  }
  if (status) url += `&status=${encodeURIComponent(status)}`;
  try {
    const rows = await apiFetch(url);
    roleGridApi.setGridOption("rowData", rows);
    applyRoleQuickFilter();
  } catch (err) {
    showToast(err.message, "error");
  }
}

function applyRoleQuickFilter() {
  if (!roleGridApi) return;
  const query = document.getElementById("filter-role-search").value.trim().toLowerCase();
  roleGridApi.setGridOption("quickFilterText", query);
}

function showRoleDetail(role) {
  _selectedRole = role;
  document.getElementById("asset-role-detail-panel").classList.remove("is-hidden");
  document.getElementById("detail-role-name").textContent = role.role_name;
  syncRoleActionButtons();
  renderRoleDetailTab("basic");
}

function closeRoleDetail() {
  document.getElementById("asset-role-detail-panel").classList.add("is-hidden");
  _selectedRole = null;
  syncRoleActionButtons();
}

function syncRoleActionButtons() {
  const hasCurrent = !!_selectedRole?.current_asset_id;
  ["btn-role-replacement", "btn-role-failover", "btn-role-repurpose", "btn-add-role-assignment", "btn-edit-role", "btn-delete-role"].forEach((id) => {
    const btn = document.getElementById(id);
    if (!btn) return;
    if (id === "btn-edit-role" || id === "btn-delete-role") {
      btn.disabled = !_selectedRole;
      return;
    }
    if (id === "btn-add-role-assignment") {
      btn.disabled = !_selectedRole;
      return;
    }
    btn.disabled = !_selectedRole || !hasCurrent;
  });
}

function renderRoleDetailTab(tab) {
  _currentRoleTab = tab;
  const container = document.getElementById("asset-role-detail-content");
  container.textContent = "";
  document.querySelectorAll(".detail-tabs .tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.rtab === tab);
  });
  if (!_selectedRole) return;
  if (tab === "basic") {
    renderRoleBasicTab(container);
    return;
  }
  if (tab === "assignments") {
    renderRoleAssignmentsTab(container);
  }
}

function renderRoleBasicTab(container) {
  const rows = [
    ["역할명", _selectedRole.role_name],
    ["유형", _selectedRole.role_type || "—"],
    ["상태", ROLE_STATUS_LABELS[_selectedRole.status] || _selectedRole.status],
    ["현재 자산", _selectedRole.current_asset_name || "미할당"],
    ["현재 자산코드", _selectedRole.current_asset_code || "—"],
    ["비고", _selectedRole.note || "—"],
  ];
  const wrap = document.createElement("div");
  wrap.className = "detail-grid";
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "detail-row";
    const strong = document.createElement("strong");
    strong.textContent = label;
    const span = document.createElement("span");
    span.textContent = value;
    row.append(strong, span);
    wrap.appendChild(row);
  });
  container.appendChild(wrap);
}

async function renderRoleAssignmentsTab(container) {
  const header = document.createElement("div");
  header.className = "subtab-header";
  const title = document.createElement("h3");
  title.textContent = "할당 이력";
  const addBtn = document.createElement("button");
  addBtn.className = "btn btn-sm btn-primary";
  addBtn.textContent = "할당 추가";
  addBtn.addEventListener("click", () => openRoleAssignmentModal());
  header.append(title, addBtn);
  container.appendChild(header);

  try {
    const rows = await apiFetch(`/api/v1/asset-roles/${_selectedRole.id}/assignments`);
    const current = rows.find((row) => row.is_current) || null;
    const summary = document.createElement("div");
    summary.className = "asset-history-summary";
    summary.innerHTML = `
      <div class="asset-history-stat">
        <span class="asset-history-stat-label">현재 담당</span>
        <strong class="asset-history-stat-value">${escapeHtml(current ? (current.asset_name || current.asset_code || "할당됨") : "미할당")}</strong>
      </div>
      <div class="asset-history-stat">
        <span class="asset-history-stat-label">현재 유형</span>
        <strong class="asset-history-stat-value">${escapeHtml(current ? (ASSIGNMENT_TYPE_LABELS[current.assignment_type] || current.assignment_type) : "—")}</strong>
      </div>
      <div class="asset-history-stat">
        <span class="asset-history-stat-label">할당 이력</span>
        <strong class="asset-history-stat-value">${rows.length}건</strong>
      </div>
    `;
    container.appendChild(summary);

    if (!rows.length) {
      const empty = document.createElement("p");
      empty.className = "text-muted asset-subtable-empty";
      empty.textContent = "아직 등록된 역할 할당 이력이 없습니다.";
      container.appendChild(empty);
      return;
    }

    const timeline = document.createElement("div");
    timeline.className = "asset-timeline";
    rows.forEach((row) => {
      const item = document.createElement("article");
      item.className = "asset-timeline-item";
      item.innerHTML = `
        <div class="asset-timeline-marker asset-timeline-marker-${row.is_current ? "current" : "history"}"></div>
        <div class="asset-timeline-main">
          <div class="asset-timeline-meta">
            <span class="badge">${escapeHtml(ASSIGNMENT_TYPE_LABELS[row.assignment_type] || row.assignment_type)}</span>
            <span>${escapeHtml(row.valid_from || "시작 미기재")} ~ ${escapeHtml(row.valid_to || "현재")}</span>
            ${row.is_current ? '<span class="badge badge-active">현재 담당</span>' : ""}
          </div>
          <div class="asset-timeline-title">${escapeHtml([row.asset_name, row.asset_code].filter(Boolean).join(" / ") || "미지정 자산")}</div>
          ${row.note ? `<div class="asset-timeline-body">${escapeHtml(row.note)}</div>` : ""}
        </div>
        <div class="asset-timeline-actions"></div>
      `;
      const actions = item.querySelector(".asset-timeline-actions");
      const editBtn = document.createElement("button");
      editBtn.className = "asset-subtable-action";
      editBtn.textContent = "수정";
      editBtn.addEventListener("click", () => openRoleAssignmentModal(row));
      const deleteBtn = document.createElement("button");
      deleteBtn.className = "asset-subtable-action danger";
      deleteBtn.textContent = "삭제";
      deleteBtn.addEventListener("click", () => deleteRoleAssignment(row));
      actions.append(editBtn, deleteBtn);
      timeline.appendChild(item);
    });
    container.appendChild(timeline);
  } catch (err) {
    showToast(err.message, "error");
  }
}

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
  } catch (_) {
    // ignore
  }
}

async function openRoleModal(role) {
  await populateRolePeriodSelect(role ? role.contract_period_id : getCtxProjectId());
  document.getElementById("asset-role-id").value = role ? role.id : "";
  document.getElementById("role-name").value = role ? role.role_name : "";
  document.getElementById("role-type").value = role ? (role.role_type || "") : "";
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
    role_type: document.getElementById("role-type").value.trim() || null,
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
  confirmDelete(`역할 "${_selectedRole.role_name}"을(를) 삭제하시겠습니까?`, async () => {
    try {
      await apiFetch(`/api/v1/asset-roles/${_selectedRole.id}`, { method: "DELETE" });
      showToast("삭제되었습니다.");
      closeRoleDetail();
      await loadAssetRoles();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

async function loadRolePartnerAssets() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) return [];
  const assets = await apiFetch(`/api/v1/assets/inventory?partner_id=${partnerId}`);
  _rolePartnerAssetsCache = assets;
  return assets;
}

async function populateAssignmentAssetSelect(selectedId) {
  const select = document.getElementById("assignment-asset-id");
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "-- 자산 선택 --";
  select.appendChild(empty);
  const assets = _rolePartnerAssetsCache.length ? _rolePartnerAssetsCache : await loadRolePartnerAssets();
  assets.forEach((asset) => {
    const opt = document.createElement("option");
    opt.value = asset.id;
    opt.textContent = [asset.asset_name, asset.asset_code, asset.hostname].filter(Boolean).join(" / ");
    if (asset.id === selectedId) opt.selected = true;
    select.appendChild(opt);
  });
}

async function openRoleAssignmentModal(assignment) {
  if (!_selectedRole) return;
  await populateAssignmentAssetSelect(assignment ? assignment.asset_id : null);
  document.getElementById("role-assignment-id").value = assignment ? assignment.id : "";
  document.getElementById("assignment-asset-id").value = assignment ? assignment.asset_id : "";
  document.getElementById("assignment-asset-id").disabled = !!assignment;
  document.getElementById("assignment-type").value = assignment ? assignment.assignment_type : "primary";
  document.getElementById("assignment-valid-from").value = assignment?.valid_from || "";
  document.getElementById("assignment-valid-to").value = assignment?.valid_to || "";
  document.getElementById("assignment-is-current").checked = assignment ? assignment.is_current : true;
  document.getElementById("assignment-note").value = assignment?.note || "";
  document.getElementById("role-assignment-modal-title").textContent = assignment ? "역할 할당 수정" : "역할 할당 추가";
  document.getElementById("modal-role-assignment").showModal();
}

async function saveRoleAssignment() {
  if (!_selectedRole) return;
  const assignmentId = document.getElementById("role-assignment-id").value;
  const assetId = document.getElementById("assignment-asset-id").value;
  if (!assetId) {
    showToast("자산을 선택하세요.", "warning");
    return;
  }
  const payload = {
    asset_id: Number(assetId),
    assignment_type: document.getElementById("assignment-type").value,
    valid_from: document.getElementById("assignment-valid-from").value || null,
    valid_to: document.getElementById("assignment-valid-to").value || null,
    is_current: document.getElementById("assignment-is-current").checked,
    note: document.getElementById("assignment-note").value.trim() || null,
  };
  try {
    if (assignmentId) {
      await apiFetch(`/api/v1/asset-roles/assignments/${assignmentId}`, { method: "PATCH", body: payload });
    } else {
      await apiFetch(`/api/v1/asset-roles/${_selectedRole.id}/assignments`, { method: "POST", body: payload });
    }
    document.getElementById("modal-role-assignment").close();
    showToast(assignmentId ? "수정되었습니다." : "할당되었습니다.");
    await loadAssetRoles();
    if (_selectedRole) {
      const row = roleGridApi.getDisplayedRowCount()
        ? roleGridApi.getDisplayedRowAtIndex(0)
        : null;
      const rows = [];
      roleGridApi.forEachNode((node) => rows.push(node.data));
      const updated = rows.find((item) => item.id === _selectedRole.id);
      if (updated) _selectedRole = updated;
    }
    renderRoleDetailTab("assignments");
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function deleteRoleAssignment(assignment) {
  confirmDelete("이 역할 할당을 삭제하시겠습니까?", async () => {
    try {
      await apiFetch(`/api/v1/asset-roles/assignments/${assignment.id}`, { method: "DELETE" });
      showToast("삭제되었습니다.");
      await loadAssetRoles();
      renderRoleDetailTab("assignments");
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

async function openRoleActionModal(actionType) {
  if (!_selectedRole) return;
  _currentRoleAction = actionType;
  const titles = {
    replacement: ["교체", "현재 담당 자산을 다른 물리 자산으로 교체합니다."],
    failover: ["장애 대체", "현재 담당 자산 장애로 대체 자산을 현재 역할에 배정합니다."],
    repurpose: ["용도 전환", "현재 담당 자산을 다른 역할로 전환합니다."],
  };
  const [title, desc] = titles[actionType];
  document.getElementById("role-action-modal-title").textContent = title;
  document.getElementById("role-action-modal-desc").textContent = desc;
  document.getElementById("form-role-action").reset();
  document.getElementById("role-action-occurred-at").value = formatDateTimeLocalValue(new Date());
  document.getElementById("role-action-note").value = "";
  document.getElementById("role-action-new-role-name").value = "";
  document.getElementById("role-action-new-role-type").value = "";
  await populateRoleActionAssets();
  await populateRolePeriodSelectForAction(_selectedRole.contract_period_id);
  toggleRoleActionFields(actionType);
  document.getElementById("modal-role-action").showModal();
}


async function populateRoleActionAssets() {
  const select = document.getElementById("role-action-asset-id");
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "-- 자산 선택 --";
  select.appendChild(empty);
  const assets = _rolePartnerAssetsCache.length ? _rolePartnerAssetsCache : await loadRolePartnerAssets();
  assets
    .filter((asset) => asset.id !== _selectedRole?.current_asset_id)
    .forEach((asset) => {
      const opt = document.createElement("option");
      opt.value = asset.id;
      opt.textContent = [asset.asset_name, asset.asset_code, asset.hostname].filter(Boolean).join(" / ");
      select.appendChild(opt);
    });
}

async function populateRolePeriodSelectForAction(selectedId) {
  const select = document.getElementById("role-action-new-period-id");
  select.textContent = "";
  const empty = document.createElement("option");
  empty.value = "";
  empty.textContent = "-- 현재와 동일 --";
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
  } catch (_) {
    // ignore
  }
}

function toggleRoleActionFields(actionType) {
  const showAsset = actionType === "replacement" || actionType === "failover";
  const showNewRole = actionType === "repurpose";
  document.getElementById("role-action-asset-wrap").classList.toggle("is-hidden", !showAsset);
  document.getElementById("role-action-new-role-name-wrap").classList.toggle("is-hidden", !showNewRole);
  document.getElementById("role-action-new-role-type-wrap").classList.toggle("is-hidden", !showNewRole);
  document.getElementById("role-action-new-period-wrap").classList.toggle("is-hidden", !showNewRole);
}

async function saveRoleAction() {
  if (!_selectedRole || !_currentRoleAction) return;
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
    payload.new_role_type = document.getElementById("role-action-new-role-type").value.trim() || null;
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
    if (updated) {
      _selectedRole = updated;
      showRoleDetail(updated);
      renderRoleDetailTab("assignments");
    } else {
      closeRoleDetail();
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initRoleGrid();
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
document.getElementById("btn-close-role-detail").addEventListener("click", closeRoleDetail);
document.getElementById("btn-cancel-role").addEventListener("click", () => document.getElementById("modal-asset-role").close());
document.getElementById("btn-save-role").addEventListener("click", saveRole);
document.getElementById("btn-cancel-role-assignment").addEventListener("click", () => document.getElementById("modal-role-assignment").close());
document.getElementById("btn-save-role-assignment").addEventListener("click", saveRoleAssignment);
document.getElementById("btn-cancel-role-action").addEventListener("click", () => document.getElementById("modal-role-action").close());
document.getElementById("btn-save-role-action").addEventListener("click", saveRoleAction);
document.getElementById("filter-role-status").addEventListener("change", loadAssetRoles);
document.getElementById("filter-role-search").addEventListener("input", applyRoleQuickFilter);
document.querySelectorAll(".detail-tabs .tab-btn[data-rtab]").forEach((btn) => {
  btn.addEventListener("click", () => renderRoleDetailTab(btn.dataset.rtab));
});

initProjectFilterCheckbox(loadAssetRoles);
window.addEventListener("ctx-changed", () => {
  closeRoleDetail();
  _rolePartnerAssetsCache = [];
  loadAssetRoles();
});
