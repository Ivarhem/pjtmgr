let _currentScheme = null;
let _classificationNodes = [];
let _selectedNodeId = null;
let _classificationSources = null;
let _classificationSourcePartnerId = null;
const _classificationCollapsed = new Set();
let _classificationExpandLevel = null;
const CLASSIFICATION_ALIAS_DEFAULTS = ["대구분", "중구분", "소구분", "세구분", "상세구분"];
const CLASSIFICATION_TREE_STATE_KEY = "project_classification_tree_state";
const CLASSIFICATION_LAYOUT_WIDTH_KEY = "project_classification_layout_width";

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function currentProjectId() {
  return getCtxProjectId();
}

function currentProjectLabel() {
  return document.getElementById("ctx-project-text")?.textContent?.trim() || "선택 안 됨";
}

function loadClassificationTreeState(projectId) {
  _selectedNodeId = null;
  _classificationExpandLevel = null;
  _classificationCollapsed.clear();
  if (!projectId) return;
  try {
    const raw = localStorage.getItem(`${CLASSIFICATION_TREE_STATE_KEY}:${projectId}`);
    if (!raw) return;
    const state = JSON.parse(raw);
    _selectedNodeId = Number(state.selectedNodeId) || null;
    _classificationExpandLevel = Number(state.expandLevel) || null;
    (Array.isArray(state.collapsedNodeIds) ? state.collapsedNodeIds : [])
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0)
      .forEach((value) => _classificationCollapsed.add(value));
  } catch (_) {
    _selectedNodeId = null;
    _classificationExpandLevel = null;
    _classificationCollapsed.clear();
  }
}

function saveClassificationTreeState() {
  const projectId = currentProjectId();
  if (!projectId) return;
  localStorage.setItem(`${CLASSIFICATION_TREE_STATE_KEY}:${projectId}`, JSON.stringify({
    selectedNodeId: _selectedNodeId,
    expandLevel: _classificationExpandLevel,
    collapsedNodeIds: [..._classificationCollapsed],
  }));
}

function initClassificationLayoutSplitter() {
  const splitter = document.getElementById("classification-splitter");
  const layout = document.getElementById("classification-layout");
  if (!splitter || !layout) return;
  const storedWidth = Number(localStorage.getItem(CLASSIFICATION_LAYOUT_WIDTH_KEY) || 0);
  if (storedWidth >= 32 && storedWidth <= 68) {
    layout.style.setProperty("--classification-tree-width", `${storedWidth}%`);
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
    const width = ((event.clientX - rect.left) / rect.width) * 100;
    if (width >= 32 && width <= 68) {
      layout.style.setProperty("--classification-tree-width", `${width}%`);
    }
  });
  document.addEventListener("mouseup", () => {
    if (!dragging) return;
    dragging = false;
    splitter.classList.remove("is-dragging");
    const current = parseFloat(getComputedStyle(layout).getPropertyValue("--classification-tree-width"));
    if (!Number.isNaN(current)) {
      localStorage.setItem(CLASSIFICATION_LAYOUT_WIDTH_KEY, String(current));
    }
  });
}

function getClassificationAliases() {
  if (!_currentScheme) return [...CLASSIFICATION_ALIAS_DEFAULTS];
  return [
    _currentScheme.level_1_alias || CLASSIFICATION_ALIAS_DEFAULTS[0],
    _currentScheme.level_2_alias || CLASSIFICATION_ALIAS_DEFAULTS[1],
    _currentScheme.level_3_alias || CLASSIFICATION_ALIAS_DEFAULTS[2],
    _currentScheme.level_4_alias || CLASSIFICATION_ALIAS_DEFAULTS[3],
    _currentScheme.level_5_alias || CLASSIFICATION_ALIAS_DEFAULTS[4],
  ];
}

function getClassificationAlias(level) {
  const aliases = getClassificationAliases();
  const normalized = Math.max(1, Number(level || 1));
  return aliases[normalized - 1] || `${normalized}레벨`;
}

function applyClassificationAliases(node = selectedNode()) {
  const nodeLevel = Number(node?.level || 1);
  const currentAlias = getClassificationAlias(nodeLevel);
  const parentAlias = nodeLevel > 1 ? getClassificationAlias(nodeLevel - 1) : "상위 분류";
  document.getElementById("classification-detail-name-label").textContent = currentAlias;
  document.getElementById("classification-detail-level-label").textContent = "분류 단계";
  document.getElementById("classification-detail-parent-label").textContent = parentAlias;
}

function selectedNode() {
  return _classificationNodes.find((node) => node.id === _selectedNodeId) || null;
}

function visibleNodes() {
  const keyword = (document.getElementById("filter-classification-search")?.value || "").trim().toLowerCase();
  const activeOnly = document.getElementById("chk-classification-active-only")?.checked;
  return _classificationNodes.filter((node) => {
    if (activeOnly && !node.is_active) return false;
    if (!keyword) return true;
    return [node.node_code, node.node_name, node.path_label].some((value) => String(value || "").toLowerCase().includes(keyword));
  });
}

function visibleNodeIdSet() {
  return new Set(visibleNodes().map((node) => node.id));
}

function buildVisibleTree() {
  const visibleIds = visibleNodeIdSet();
  const all = _classificationNodes.map((node) => ({ ...node, children: [] }));
  const map = new Map(all.map((node) => [node.id, node]));
  const roots = [];
  all.forEach((node) => {
    if (!visibleIds.has(node.id)) return;
    const parent = node.parent_id ? map.get(node.parent_id) : null;
    if (parent && visibleIds.has(parent.id)) {
      parent.children.push(node);
    } else {
      roots.push(node);
    }
  });
  const sorter = (a, b) => {
    if ((a.sort_order ?? 100) !== (b.sort_order ?? 100)) return (a.sort_order ?? 100) - (b.sort_order ?? 100);
    if ((a.level ?? 0) !== (b.level ?? 0)) return (a.level ?? 0) - (b.level ?? 0);
    return String(a.node_name || "").localeCompare(String(b.node_name || ""), "ko");
  };
  const sortTree = (nodes) => {
    nodes.sort(sorter);
    nodes.forEach((node) => sortTree(node.children));
  };
  sortTree(roots);
  return roots;
}

function renderPageState() {
  const hasProject = !!currentProjectId();
  const empty = document.getElementById("classification-page-empty");
  const layout = document.getElementById("classification-layout");
  const btnInit = document.getElementById("btn-init-classification");
  const btnEditScheme = document.getElementById("btn-edit-classification-scheme");
  const btnAddRoot = document.getElementById("btn-add-classification-root");
  empty.classList.toggle("is-hidden", hasProject);
  layout.classList.toggle("is-hidden", !hasProject);
  btnInit.disabled = !hasProject;
  btnEditScheme.disabled = !hasProject || !_currentScheme;
  btnAddRoot.disabled = !hasProject || !_currentScheme;
}

function renderSummary() {
  const container = document.getElementById("classification-summary");
  const leafAlias = getClassificationAliases().filter(Boolean).at(-1) || CLASSIFICATION_ALIAS_DEFAULTS[2];
  if (!_currentScheme) {
    container.innerHTML = `
      <div class="classification-stat"><span class="classification-stat-label">현재 프로젝트</span><span class="classification-stat-value">${escapeHtml(currentProjectLabel())}</span></div>
      <div class="classification-stat"><span class="classification-stat-label">분류체계</span><span class="classification-stat-value">미초기화</span></div>
      <div class="classification-stat"><span class="classification-stat-label">분류 노드 수</span><span class="classification-stat-value">0</span></div>
      <div class="classification-stat"><span class="classification-stat-label">최종 라벨</span><span class="classification-stat-value">${escapeHtml(leafAlias)}</span></div>
    `;
    return;
  }
  container.innerHTML = `
    <div class="classification-stat"><span class="classification-stat-label">현재 프로젝트</span><span class="classification-stat-value">${escapeHtml(_currentScheme.project_label || currentProjectLabel())}</span></div>
    <div class="classification-stat"><span class="classification-stat-label">분류체계</span><span class="classification-stat-value">${escapeHtml(_currentScheme.name)}</span></div>
    <div class="classification-stat"><span class="classification-stat-label">분류 노드 수</span><span class="classification-stat-value">${_currentScheme.node_count ?? _classificationNodes.length}</span></div>
    <div class="classification-stat"><span class="classification-stat-label">최종 라벨</span><span class="classification-stat-value">${escapeHtml(leafAlias)}</span></div>
  `;
}

function renderNodes() {
  const container = document.getElementById("classification-node-tree");
  renderLevelControls();
  if (!_currentScheme) {
    container.innerHTML = '<div class="classification-tree-empty">현재 프로젝트 분류체계가 아직 초기화되지 않았습니다.</div>';
    return;
  }
  const roots = buildVisibleTree();
  if (!roots.length) {
    container.innerHTML = '<div class="classification-tree-empty">조건에 맞는 분류가 없습니다.</div>';
    return;
  }
  container.innerHTML = `<ul class="classification-tree-root">${roots.map(renderTreeNode).join("")}</ul>`;
}

function maxClassificationLevel() {
  return Math.min(
    5,
    _classificationNodes.reduce((max, node) => Math.max(max, Number(node.level || 1)), 1),
  );
}

function renderLevelControls() {
  const container = document.getElementById("classification-level-controls");
  if (!container) return;
  if (!_currentScheme || !_classificationNodes.length) {
    container.innerHTML = "";
    return;
  }
  const maxLevel = maxClassificationLevel();
  const levels = [];
  for (let level = 1; level < maxLevel && levels.length < 4; level += 1) {
    levels.push({ value: level, label: String(level), title: `${level}레벨까지 펼치기` });
  }
  levels.push({ value: maxLevel, label: "max", title: `최대(${maxLevel}레벨)까지 펼치기` });
  container.innerHTML = levels.map((item) => `
    <button
      type="button"
      class="classification-level-btn ${_classificationExpandLevel === item.value ? "is-active" : ""}"
      data-expand-level="${item.value}"
      title="${item.title}"
    >${item.label}</button>
  `).join("");
}

function applyExpandLevel(level) {
  _classificationExpandLevel = level;
  _classificationCollapsed.clear();
  _classificationNodes.forEach((node) => {
    const hasChildren = _classificationNodes.some((item) => item.parent_id === node.id);
    if (hasChildren && Number(node.level || 1) >= level) {
      _classificationCollapsed.add(node.id);
    }
  });
  saveClassificationTreeState();
  renderNodes();
}

function renderTreeNode(node) {
  const hasChildren = node.children && node.children.length > 0;
  const collapsed = _classificationCollapsed.has(node.id);
  const levelAlias = getClassificationAlias(node.level || 1);
  const childHtml = hasChildren && !collapsed
    ? `<ul>${node.children.map(renderTreeNode).join("")}</ul>`
    : "";
  return `
    <li class="classification-tree-item">
      <button type="button" class="classification-tree-node ${node.id === _selectedNodeId ? "is-selected" : ""} ${node.is_active ? "" : "is-inactive"}" data-node-id="${node.id}">
        <span class="classification-tree-toggle ${hasChildren ? "" : "is-placeholder"}" data-toggle-node="${hasChildren ? node.id : ""}">${hasChildren ? (collapsed ? "▸" : "▾") : "•"}</span>
        <span class="classification-tree-main">
          <span class="classification-tree-title">
            <span class="classification-tree-name">${escapeHtml(node.node_name)}</span>
            <span class="classification-tree-code">${escapeHtml(node.node_code)}</span>
          </span>
          <span class="classification-tree-path">${escapeHtml(node.path_label || "—")}</span>
        </span>
        <span class="classification-tree-meta">
          <span class="classification-pill classification-pill-alias">${escapeHtml(levelAlias)}</span>
          ${node.is_active ? '<span class="classification-pill">활성</span>' : '<span class="classification-pill">비활성</span>'}
        </span>
      </button>
      ${childHtml}
    </li>
  `;
}

function renderDetail() {
  const empty = document.getElementById("classification-detail-empty");
  const content = document.getElementById("classification-detail-content");
  const node = selectedNode();
  const btnAddChild = document.getElementById("btn-add-classification-child");
  const btnEditNode = document.getElementById("btn-edit-classification-node");
  const btnDeleteNode = document.getElementById("btn-delete-classification-node");
  btnAddChild.disabled = !_currentScheme || !node;
  btnEditNode.disabled = !node;
  btnDeleteNode.disabled = !node;
  if (!node) {
    applyClassificationAliases(null);
    empty.classList.remove("is-hidden");
    content.classList.add("is-hidden");
    return;
  }
  applyClassificationAliases(node);
  empty.classList.add("is-hidden");
  content.classList.remove("is-hidden");
  const parent = _classificationNodes.find((item) => item.id === node.parent_id);
  document.getElementById("classification-detail-title").textContent = node.node_name;
  document.getElementById("classification-detail-help").textContent = "선택한 분류 노드의 경로와 운영 메모를 확인할 수 있습니다.";
  document.getElementById("classification-detail-code").textContent = node.node_code || "—";
  document.getElementById("classification-detail-name").textContent = node.node_name || "—";
  document.getElementById("classification-detail-level").textContent = `${String(node.level || "—")}레벨 · ${getClassificationAlias(node.level || 1)}`;
  document.getElementById("classification-detail-status").textContent = node.is_active ? "활성" : "비활성";
  document.getElementById("classification-detail-sort-order").textContent = String(node.sort_order ?? "—");
  document.getElementById("classification-detail-parent").textContent = parent?.node_name || "최상위";
  document.getElementById("classification-detail-project").textContent = _currentScheme?.project_label || currentProjectLabel();
  document.getElementById("classification-detail-note").textContent = node.note || "—";
  document.getElementById("classification-detail-path").textContent = node.path_label || "—";
}

function refreshAll() {
  renderPageState();
  renderSummary();
  renderNodes();
  renderDetail();
}

async function loadCurrentScheme() {
  const projectId = currentProjectId();
  _currentScheme = null;
  _classificationNodes = [];
  loadClassificationTreeState(projectId);
  if (!projectId) {
    refreshAll();
    return;
  }
  const schemes = await apiFetch(`/api/v1/classification-schemes?scope_type=project&project_id=${projectId}`);
  _currentScheme = schemes[0] || null;
  if (_currentScheme) {
    _classificationNodes = await apiFetch(`/api/v1/classification-schemes/${_currentScheme.id}/nodes`);
  }
  const validNodeIds = new Set(_classificationNodes.map((node) => node.id));
  if (_selectedNodeId && !validNodeIds.has(_selectedNodeId)) _selectedNodeId = null;
  [..._classificationCollapsed].forEach((nodeId) => {
    if (!validNodeIds.has(nodeId)) _classificationCollapsed.delete(nodeId);
  });
  applyClassificationAliases(null);
  saveClassificationTreeState();
  refreshAll();
}

async function ensureSources() {
  const partnerId = getCtxPartnerId();
  if (!partnerId) {
    _classificationSources = { global_schemes: [], partner_project_schemes: [] };
    _classificationSourcePartnerId = null;
    return _classificationSources;
  }
  if (_classificationSources && _classificationSourcePartnerId === partnerId) {
    return _classificationSources;
  }
  _classificationSources = await apiFetch(`/api/v1/classification-scheme-sources?partner_id=${partnerId}`);
  _classificationSourcePartnerId = partnerId;
  return _classificationSources;
}

function getSourceChoices(mode) {
  if (!_classificationSources) return [];
  return mode === "partner_project"
    ? (_classificationSources.partner_project_schemes || [])
    : (_classificationSources.global_schemes || []);
}

function refreshInitSources() {
  const modeEl = document.getElementById("classification-init-mode");
  const sourceEl = document.getElementById("classification-init-source");
  const hintEl = document.getElementById("classification-init-hint");
  let mode = modeEl.value;
  if ((mode === "global" || mode === "partner_project") && !getSourceChoices(mode).length) {
    mode = getSourceChoices("global").length ? "global" : "partner_project";
    modeEl.value = mode;
  }
  const choices = getSourceChoices(mode);
  sourceEl.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = choices.length ? "원본 체계를 선택하세요" : "선택 가능한 원본이 없습니다";
  sourceEl.appendChild(placeholder);
  choices.forEach((item) => {
    const option = document.createElement("option");
    option.value = String(item.id);
    option.textContent = `${item.name} (${item.node_count}개 노드)`;
    sourceEl.appendChild(option);
  });
  if (choices.length) sourceEl.value = String(choices[0].id);
  hintEl.textContent = mode === "global"
    ? "글로벌 기본 체계를 복사해 현재 프로젝트 전용 분류체계를 만듭니다."
    : "같은 고객사의 기존 프로젝트 분류체계를 복사해 현재 프로젝트 기준으로 시작합니다.";
}

function populateParentOptions(selectedParentId = null, excludedNodeId = null) {
  const parentEl = document.getElementById("classification-node-parent");
  parentEl.innerHTML = "";
  const rootOption = document.createElement("option");
  rootOption.value = "";
  rootOption.textContent = "최상위 분류";
  parentEl.appendChild(rootOption);
  _classificationNodes
    .filter((node) => node.id !== excludedNodeId)
    .forEach((node) => {
      const option = document.createElement("option");
      option.value = String(node.id);
      option.textContent = `${"· ".repeat(Math.max((node.level || 1) - 1, 0))}${node.path_label || node.node_name}`;
      parentEl.appendChild(option);
    });
  parentEl.value = selectedParentId ? String(selectedParentId) : "";
}

function openInitModal() {
  if (!currentProjectId()) {
    showToast("프로젝트를 먼저 선택하세요.", "warning");
    return;
  }
  document.getElementById("classification-init-mode").value = "global";
  document.getElementById("classification-init-name").value = `${currentProjectLabel()} 분류체계`;
  refreshInitSources();
  document.getElementById("modal-classification-init").showModal();
}

function openSchemeModal() {
  if (!_currentScheme) {
    showToast("현재 프로젝트 분류체계가 없습니다.", "warning");
    return;
  }
  document.getElementById("classification-scheme-name").value = _currentScheme.name || "";
  document.getElementById("classification-scheme-description").value = _currentScheme.description || "";
  document.getElementById("classification-scheme-level-1-alias").value = _currentScheme.level_1_alias || "";
  document.getElementById("classification-scheme-level-2-alias").value = _currentScheme.level_2_alias || "";
  document.getElementById("classification-scheme-level-3-alias").value = _currentScheme.level_3_alias || "";
  document.getElementById("classification-scheme-level-4-alias").value = _currentScheme.level_4_alias || "";
  document.getElementById("classification-scheme-level-5-alias").value = _currentScheme.level_5_alias || "";
  document.getElementById("classification-scheme-active").value = String(_currentScheme.is_active !== false);
  document.getElementById("modal-classification-scheme").showModal();
}

function openNodeModal(mode) {
  if (!_currentScheme) {
    showToast("먼저 프로젝트 분류체계를 초기화하세요.", "warning");
    return;
  }
  const node = mode === "edit" ? selectedNode() : null;
  if (mode === "edit" && !node) {
    showToast("수정할 분류를 먼저 선택하세요.", "warning");
    return;
  }
  document.getElementById("classification-node-modal-title").textContent = mode === "edit" ? "분류 수정" : "분류 등록";
  document.getElementById("classification-node-id").value = node?.id || "";
  document.getElementById("classification-node-code").value = node?.node_code || "";
  document.getElementById("classification-node-name").value = node?.node_name || "";
  document.getElementById("classification-node-sort-order").value = node?.sort_order ?? 100;
  document.getElementById("classification-node-active").value = String(node?.is_active ?? true);
  document.getElementById("classification-node-note").value = node?.note || "";
  const parentId = mode === "add_child" ? selectedNode()?.id : (node?.parent_id || null);
  populateParentOptions(parentId, node?.id || null);
  document.getElementById("modal-classification-node").showModal();
}

async function saveInit() {
  const projectId = currentProjectId();
  if (!projectId) {
    showToast("프로젝트를 먼저 선택하세요.", "warning");
    return;
  }
  const payload = {
    mode: document.getElementById("classification-init-mode").value,
    source_scheme_id: Number(document.getElementById("classification-init-source").value || 0),
    name: document.getElementById("classification-init-name").value.trim() || `${currentProjectLabel()} 분류체계`,
  };
  if (!payload.source_scheme_id) {
    showToast("복사 원본을 선택하세요.", "warning");
    return;
  }
  await apiFetch(`/api/v1/projects/${projectId}/classification-scheme/init`, { method: "POST", body: payload });
  document.getElementById("modal-classification-init").close();
  showToast("프로젝트 분류체계를 초기화했습니다.");
  await loadCurrentScheme();
}

async function saveScheme() {
  if (!_currentScheme) return;
  const payload = {
    name: document.getElementById("classification-scheme-name").value.trim(),
    description: document.getElementById("classification-scheme-description").value.trim() || null,
    level_1_alias: document.getElementById("classification-scheme-level-1-alias").value.trim() || null,
    level_2_alias: document.getElementById("classification-scheme-level-2-alias").value.trim() || null,
    level_3_alias: document.getElementById("classification-scheme-level-3-alias").value.trim() || null,
    level_4_alias: document.getElementById("classification-scheme-level-4-alias").value.trim() || null,
    level_5_alias: document.getElementById("classification-scheme-level-5-alias").value.trim() || null,
    is_active: document.getElementById("classification-scheme-active").value === "true",
  };
  if (!payload.name) {
    showToast("분류체계명을 입력하세요.", "warning");
    return;
  }
  _currentScheme = await apiFetch(`/api/v1/classification-schemes/${_currentScheme.id}`, { method: "PATCH", body: payload });
  document.getElementById("modal-classification-scheme").close();
  showToast("분류체계를 수정했습니다.");
  await loadCurrentScheme();
}

async function saveNode() {
  if (!_currentScheme) return;
  const nodeId = Number(document.getElementById("classification-node-id").value || 0);
  const payload = {
    node_code: document.getElementById("classification-node-code").value.trim(),
    node_name: document.getElementById("classification-node-name").value.trim(),
    parent_id: document.getElementById("classification-node-parent").value ? Number(document.getElementById("classification-node-parent").value) : null,
    sort_order: Number(document.getElementById("classification-node-sort-order").value || 100),
    is_active: document.getElementById("classification-node-active").value === "true",
    note: document.getElementById("classification-node-note").value.trim() || null,
  };
  if (!payload.node_code || !payload.node_name) {
    showToast("코드와 분류명은 필수입니다.", "warning");
    return;
  }
  if (nodeId) {
    await apiFetch(`/api/v1/classification-nodes/${nodeId}`, { method: "PATCH", body: payload });
    showToast("분류를 수정했습니다.");
  } else {
    await apiFetch(`/api/v1/classification-schemes/${_currentScheme.id}/nodes`, { method: "POST", body: payload });
    showToast("분류를 등록했습니다.");
  }
  document.getElementById("modal-classification-node").close();
  await loadCurrentScheme();
}

async function deleteNode() {
  const node = selectedNode();
  if (!node) {
    showToast("삭제할 분류를 먼저 선택하세요.", "warning");
    return;
  }
  confirmDelete(`분류 "${node.node_name}"을(를) 삭제하시겠습니까?`, async () => {
    try {
      await apiFetch(`/api/v1/classification-nodes/${node.id}`, { method: "DELETE" });
      _selectedNodeId = null;
      showToast("분류를 삭제했습니다.");
      await loadCurrentScheme();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

function bindNodeTable() {
  document.getElementById("classification-node-tree").addEventListener("click", (event) => {
    const toggle = event.target.closest("[data-toggle-node]");
    if (toggle && toggle.dataset.toggleNode) {
      const nodeId = Number(toggle.dataset.toggleNode);
      if (_classificationCollapsed.has(nodeId)) _classificationCollapsed.delete(nodeId);
      else _classificationCollapsed.add(nodeId);
      _classificationExpandLevel = null;
      saveClassificationTreeState();
      renderNodes();
      return;
    }
    const row = event.target.closest("[data-node-id]");
    if (!row) return;
    _selectedNodeId = Number(row.dataset.nodeId);
    saveClassificationTreeState();
    renderNodes();
    renderDetail();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initClassificationLayoutSplitter();
  bindNodeTable();
  document.getElementById("classification-level-controls").addEventListener("click", (event) => {
    const btn = event.target.closest("[data-expand-level]");
    if (!btn) return;
    applyExpandLevel(Number(btn.dataset.expandLevel));
  });
  document.getElementById("filter-classification-search").addEventListener("input", renderNodes);
  document.getElementById("chk-classification-active-only").addEventListener("change", renderNodes);
  document.getElementById("btn-refresh-classification").addEventListener("click", () => loadCurrentScheme().catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-init-classification").addEventListener("click", async () => {
    try {
      await ensureSources();
      openInitModal();
    } catch (err) {
      showToast(err.message, "error");
    }
  });
  document.getElementById("btn-edit-classification-scheme").addEventListener("click", openSchemeModal);
  document.getElementById("btn-add-classification-root").addEventListener("click", () => openNodeModal("add_root"));
  document.getElementById("btn-add-classification-child").addEventListener("click", () => openNodeModal("add_child"));
  document.getElementById("btn-edit-classification-node").addEventListener("click", () => openNodeModal("edit"));
  document.getElementById("btn-delete-classification-node").addEventListener("click", deleteNode);
  document.getElementById("classification-init-mode").addEventListener("change", refreshInitSources);
  document.getElementById("btn-cancel-classification-init").addEventListener("click", () => document.getElementById("modal-classification-init").close());
  document.getElementById("btn-save-classification-init").addEventListener("click", () => saveInit().catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-cancel-classification-scheme").addEventListener("click", () => document.getElementById("modal-classification-scheme").close());
  document.getElementById("btn-save-classification-scheme").addEventListener("click", () => saveScheme().catch((err) => showToast(err.message, "error")));
  document.getElementById("btn-cancel-classification-node").addEventListener("click", () => document.getElementById("modal-classification-node").close());
  document.getElementById("btn-save-classification-node").addEventListener("click", () => saveNode().catch((err) => showToast(err.message, "error")));
  loadCurrentScheme().catch((err) => showToast(err.message, "error"));
});

window.addEventListener("ctx-changed", () => {
  loadCurrentScheme().catch((err) => showToast(err.message, "error"));
});
