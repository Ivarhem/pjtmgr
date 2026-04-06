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
  } catch (err) {
    showToast(err.message, "error");
  }
}

function applyRoleQuickFilter() {
  if (!roleGridApi) return;
  const query = document.getElementById("filter-role-search").value.trim().toLowerCase();
  roleGridApi.setGridOption("quickFilterText", query);
}

/* ── Detail Panel ── */

function showRoleDetail(role) {
  _selectedRole = role;
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

/* ── Splitter ── */

function initRoleSplitter() {
  const splitter = document.getElementById("role-splitter");
  const listPanel = document.getElementById("role-list-panel");
  const layout = document.getElementById("role-layout");
  if (!splitter || !listPanel || !layout) return;

  let dragging = false;
  splitter.addEventListener("mousedown", (e) => {
    e.preventDefault();
    dragging = true;
    document.body.style.cursor = "col-resize";
  });
  document.addEventListener("mousemove", (e) => {
    if (!dragging) return;
    const rect = layout.getBoundingClientRect();
    const pct = ((e.clientX - rect.left) / rect.width) * 100;
    const clamped = Math.max(20, Math.min(50, pct));
    listPanel.style.flex = `0 0 ${clamped}%`;
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = "";
  });
}

/* ── Events ── */
document.addEventListener("DOMContentLoaded", async () => {
  initRoleSplitter();
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
document.getElementById("btn-role-history").addEventListener("click", openRoleHistoryModal);
document.getElementById("btn-close-role-history").addEventListener("click", () => document.getElementById("modal-role-history").close());
document.getElementById("btn-cancel-role").addEventListener("click", () => document.getElementById("modal-asset-role").close());
document.getElementById("btn-save-role").addEventListener("click", saveRole);
document.getElementById("btn-cancel-role-assignment").addEventListener("click", () => document.getElementById("modal-role-assignment").close());
document.getElementById("btn-save-role-assignment").addEventListener("click", saveRoleAssignment);
document.getElementById("btn-cancel-role-action").addEventListener("click", () => document.getElementById("modal-role-action").close());
document.getElementById("btn-save-role-action").addEventListener("click", saveRoleAction);
document.getElementById("filter-role-search").addEventListener("input", applyRoleQuickFilter);

initProjectFilterCheckbox(loadAssetRoles);
window.addEventListener("ctx-changed", () => {
  closeRoleDetail();
  _rolePartnerAssetsCache = [];
  loadAssetRoles();
});
