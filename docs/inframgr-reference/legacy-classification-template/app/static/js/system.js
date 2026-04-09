let editingCode = null; // null = 추가 모드, 문자열 = 수정 모드

document.addEventListener('DOMContentLoaded', async () => {
  // ── 탭 전환 ──
  document.querySelectorAll('#system-tabs .tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#system-tabs .tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      ['tab-common', 'tab-accounting', 'tab-infra'].forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        const isActive = id === 'tab-' + btn.dataset.tab;
        if (isActive) {
          el.classList.remove('hidden');
          el.style.display = '';
        } else {
          el.classList.add('hidden');
          el.style.display = 'none';
        }
      });
      history.replaceState(null, '', '#' + btn.dataset.tab);
    });
  });
  // URL hash로 초기 탭
  const initTab = location.hash.slice(1) || 'common';
  const initBtn = document.querySelector('#system-tabs .tab-btn[data-tab="' + initTab + '"]');
  if (initBtn) initBtn.click();
  // ── 기본 설정 ─────────────────────────────────────────────────
  const res = await fetch('/api/v1/settings');
  const data = await res.json();
  document.getElementById('input-org-name').value = data.org_name ?? '';
  document.getElementById('input-password-min-length').value = data.password_min_length ?? 8;

  document.getElementById('btn-save-settings').addEventListener('click', async () => {
    const orgName = document.getElementById('input-org-name').value.trim();
    const passwordMinLength = parseInt(document.getElementById('input-password-min-length').value, 10);
    const res = await fetch('/api/v1/settings', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        org_name: orgName || null,
        password_min_length: Number.isNaN(passwordMinLength) ? null : passwordMinLength,
      }),
    });
    if (res.ok) {
      const updated = await res.json();
      document.getElementById('input-password-min-length').value = updated.password_min_length;
      alert('저장되었습니다.');
    } else {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || '저장에 실패했습니다.');
    }
  });

  // ── 사업유형 관리 ──────────────────────────────────────────────
  if (document.getElementById('btn-add-contract-type')) {
    loadContractTypeTable();
    document.getElementById('btn-add-contract-type').addEventListener('click', () => openContractTypeModal());
    document.getElementById('btn-dt-cancel').addEventListener('click', () => document.getElementById('modal-contract-type').close());
    document.getElementById('btn-dt-submit').addEventListener('click', submitContractType);
  }

  // ── 용어 관리 ────────────────────────────────────────────────
  loadTermConfigTable();

  document.getElementById('btn-add-term').addEventListener('click', () => openTermModal());
  document.getElementById('btn-tc-cancel').addEventListener('click', () => document.getElementById('modal-term-config').close());
  document.getElementById('btn-tc-submit').addEventListener('click', submitTermConfig);

});

async function loadContractTypeTable() {
  const res = await fetch('/api/v1/contract-types?active_only=false');
  const types = await res.json();
  const tbody = document.getElementById('contract-type-tbody');
  tbody.innerHTML = types.map(dt => `
    <tr class="${dt.is_active ? '' : 'row-inactive'}">
      <td><span class="cell-code">${dt.code}</span></td>
      <td>${dt.label}</td>
      <td class="cell-center">${dt.sort_order}</td>
      <td class="cell-center">${dt.default_gp_pct != null ? dt.default_gp_pct + '%' : '<span class="cell-muted">-</span>'}</td>
      <td class="cell-center">${_inspectionText(dt)}</td>
      <td class="cell-center cell-text-sm">${_invoiceText(dt)}</td>
      <td class="cell-center">${dt.is_active ? '<span class="badge-active">활성</span>' : '<span class="badge-inactive">비활성</span>'}</td>
      <td class="cell-center">
        <button class="btn btn-secondary btn-xs" onclick="openContractTypeModal('${dt.code}')">수정</button>
      </td>
    </tr>
  `).join('');
}

function _inspectionText(dt) {
  if (dt.default_inspection_day == null) return '<span class="cell-muted">-</span>';
  return dt.default_inspection_day === 0 ? '말일' : `${dt.default_inspection_day}일`;
}

function _invoiceText(dt) {
  const parts = [];
  if (dt.default_invoice_month_offset != null) parts.push(dt.default_invoice_month_offset === 0 ? '당월' : '익월');
  if (dt.default_invoice_day_type) parts.push(dt.default_invoice_day_type === '특정일' ? `${dt.default_invoice_day || '?'}일` : dt.default_invoice_day_type);
  if (dt.default_invoice_holiday_adjust) parts.push(`(휴일:${dt.default_invoice_holiday_adjust})`);
  return parts.length ? parts.join(' ') : '<span class="cell-muted">-</span>';
}

async function openContractTypeModal(code = null) {
  editingCode = code;
  const modal = document.getElementById('modal-contract-type');
  const title = document.getElementById('modal-contract-type-title');
  const codeInput = document.getElementById('dt-code');

  if (code) {
    title.textContent = '사업유형 수정';
    codeInput.value = code;
    codeInput.readOnly = true;
    // 기존 데이터 로드
    const res = await fetch('/api/v1/contract-types?active_only=false');
    const types = await res.json();
    const dt = types.find(t => t.code === code);
    if (dt) {
      document.getElementById('dt-label').value = dt.label;
      document.getElementById('dt-sort-order').value = dt.sort_order;
      document.getElementById('dt-gp-pct').value = dt.default_gp_pct ?? '';
      document.getElementById('dt-inspection-day').value = dt.default_inspection_day ?? '';
      document.getElementById('dt-invoice-month-offset').value = dt.default_invoice_month_offset ?? '';
      document.getElementById('dt-invoice-day-type').value = dt.default_invoice_day_type ?? '';
      document.getElementById('dt-invoice-day').value = dt.default_invoice_day ?? '';
      document.getElementById('dt-invoice-holiday-adjust').value = dt.default_invoice_holiday_adjust ?? '';
    }
  } else {
    title.textContent = '사업유형 추가';
    codeInput.value = '';
    codeInput.readOnly = false;
    document.getElementById('dt-label').value = '';
    document.getElementById('dt-sort-order').value = '0';
    document.getElementById('dt-gp-pct').value = '';
    document.getElementById('dt-inspection-day').value = '';
    document.getElementById('dt-invoice-month-offset').value = '';
    document.getElementById('dt-invoice-day-type').value = '';
    document.getElementById('dt-invoice-day').value = '';
    document.getElementById('dt-invoice-holiday-adjust').value = '';
  }
  modal.showModal();
}

async function submitContractType() {
  const code = document.getElementById('dt-code').value.trim();
  const label = document.getElementById('dt-label').value.trim();
  if (!code || !label) { alert('코드와 표시명은 필수입니다.'); return; }

  const body = {
    label,
    sort_order: parseInt(document.getElementById('dt-sort-order').value) || 0,
    default_gp_pct: _numOrNull('dt-gp-pct'),
    default_inspection_day: _numOrNull('dt-inspection-day'),
    default_invoice_month_offset: _numOrNull('dt-invoice-month-offset'),
    default_invoice_day_type: document.getElementById('dt-invoice-day-type').value || null,
    default_invoice_day: _numOrNull('dt-invoice-day'),
    default_invoice_holiday_adjust: document.getElementById('dt-invoice-holiday-adjust').value || null,
  };

  let res;
  if (editingCode) {
    res = await fetch(`/api/v1/contract-types/${encodeURIComponent(editingCode)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } else {
    body.code = code;
    res = await fetch('/api/v1/contract-types', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  if (res.ok) {
    document.getElementById('modal-contract-type').close();
    loadContractTypeTable();
  } else {
    const err = await res.json();
    alert(err.detail || '저장에 실패했습니다.');
  }
}

function _numOrNull(id) {
  const v = document.getElementById(id).value;
  return v !== '' ? parseInt(v) : null;
}


// ── 용어 관리 ────────────────────────────────────────────────────

let editingTermKey = null;
const CATEGORY_LABELS = { entity: '엔티티', metric: '지표', report: '보고서' };

async function loadTermConfigTable() {
  const res = await fetch('/api/v1/term-configs?active_only=false');
  const terms = await res.json();
  const tbody = document.getElementById('term-config-tbody');
  tbody.innerHTML = terms.map(t => `
    <tr class="${t.is_active ? '' : 'row-inactive'}">
      <td class="cell-center"><span class="badge-category" data-cat="${t.category}">${CATEGORY_LABELS[t.category] || t.category}</span></td>
      <td><span class="cell-code">${t.term_key}</span></td>
      <td>${t.standard_label_ko}</td>
      <td>${t.default_ui_label}</td>
      <td>${t.is_customized ? `<span class="badge-customized">${t.custom_ui_label}</span>` : '<span class="cell-muted">-</span>'}</td>
      <td class="cell-center">${t.is_active ? '<span class="badge-active">활성</span>' : '<span class="badge-inactive">비활성</span>'}</td>
      <td class="cell-center">
        <button class="btn btn-secondary btn-xs" onclick="openTermModal('${t.term_key}')">수정</button>
        ${t.is_customized ? `<button class="btn btn-secondary btn-xs" onclick="resetTermLabel('${t.term_key}')">초기화</button>` : ''}
      </td>
    </tr>
  `).join('');
}

async function openTermModal(termKey = null) {
  editingTermKey = termKey;
  const modal = document.getElementById('modal-term-config');
  const title = document.getElementById('modal-term-title');
  const keyInput = document.getElementById('tc-term-key');

  if (termKey) {
    title.textContent = '용어 수정';
    keyInput.readOnly = true;
    document.getElementById('tc-category').disabled = true;
    document.getElementById('tc-standard-ko').readOnly = true;
    document.getElementById('tc-default-label').readOnly = true;
    const res = await fetch(`/api/v1/term-configs/${encodeURIComponent(termKey)}`);
    const t = await res.json();
    keyInput.value = t.term_key;
    document.getElementById('tc-category').value = t.category;
    document.getElementById('tc-standard-en').value = t.standard_label_en;
    document.getElementById('tc-standard-ko').value = t.standard_label_ko;
    document.getElementById('tc-default-label').value = t.default_ui_label;
    document.getElementById('tc-custom-label').value = t.custom_ui_label ?? '';
    document.getElementById('tc-sort-order').value = t.sort_order;
    document.getElementById('tc-definition').value = t.definition ?? '';
  } else {
    title.textContent = '용어 추가';
    keyInput.readOnly = false;
    document.getElementById('tc-category').disabled = false;
    document.getElementById('tc-standard-ko').readOnly = false;
    document.getElementById('tc-default-label').readOnly = false;
    keyInput.value = '';
    document.getElementById('tc-category').value = 'entity';
    document.getElementById('tc-standard-en').value = '';
    document.getElementById('tc-standard-ko').value = '';
    document.getElementById('tc-default-label').value = '';
    document.getElementById('tc-custom-label').value = '';
    document.getElementById('tc-sort-order').value = '0';
    document.getElementById('tc-definition').value = '';
  }
  modal.showModal();
}

async function submitTermConfig() {
  const termKey = document.getElementById('tc-term-key').value.trim();
  const standardEn = document.getElementById('tc-standard-en').value.trim();
  const standardKo = document.getElementById('tc-standard-ko').value.trim();
  const defaultLabel = document.getElementById('tc-default-label').value.trim();

  if (!termKey || !standardEn || !standardKo || !defaultLabel) {
    alert('키, 영문 표준명, 한글 표준명, 기본 표시명은 필수입니다.');
    return;
  }

  const body = {
    category: document.getElementById('tc-category').value,
    standard_label_en: standardEn,
    standard_label_ko: standardKo,
    default_ui_label: defaultLabel,
    custom_ui_label: document.getElementById('tc-custom-label').value.trim() || null,
    sort_order: parseInt(document.getElementById('tc-sort-order').value) || 0,
    definition: document.getElementById('tc-definition').value.trim() || null,
  };

  let res;
  if (editingTermKey) {
    res = await fetch(`/api/v1/term-configs/${encodeURIComponent(editingTermKey)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  } else {
    body.term_key = termKey;
    res = await fetch('/api/v1/term-configs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  }

  if (res.ok) {
    document.getElementById('modal-term-config').close();
    loadTermConfigTable();
  } else {
    const err = await res.json();
    alert(err.detail || '저장에 실패했습니다.');
  }
}

async function resetTermLabel(termKey) {
  if (!confirm('커스텀 표시명을 기본값으로 초기화하시겠습니까?')) return;
  const res = await fetch(`/api/v1/term-configs/${encodeURIComponent(termKey)}/reset`, { method: 'POST' });
  if (res.ok) {
    loadTermConfigTable();
  } else {
    const err = await res.json();
    alert(err.detail || '초기화에 실패했습니다.');
  }
}


// ── 자산유형 관리 ──
let _editingTypeKey = null;
const ASSET_KIND_LABELS = {
  hardware: 'hardware',
  software: 'software',
  service: 'service',
  model: 'model',
  business_capability: 'business_capability',
  dataset: 'dataset',
};

async function loadAssetTypeTable() {
  const types = await apiFetch('/api/v1/asset-type-codes?active_only=false');
  const tbody = document.getElementById('asset-type-tbody');
  tbody.textContent = '';
  types.forEach(t => {
    const tr = document.createElement('tr');
    const cells = [t.type_key, t.code, ASSET_KIND_LABELS[t.kind] || t.kind, t.label, t.sort_order, t.is_active ? '\u2713' : '\u2014'];
    cells.forEach(val => {
      const td = document.createElement('td');
      td.textContent = val;
      tr.appendChild(td);
    });
    const actionTd = document.createElement('td');
    const editBtn = document.createElement('button');
    editBtn.className = 'btn btn-sm';
    editBtn.textContent = '수정';
    editBtn.addEventListener('click', () => openAssetTypeModal(t.type_key));
    actionTd.appendChild(editBtn);
    tr.appendChild(actionTd);
    tbody.appendChild(tr);
  });
}

function openAssetTypeModal(typeKey) {
  const modal = document.getElementById('modal-asset-type');
  const titleEl = document.getElementById('modal-at-title');
  const keyInput = document.getElementById('at-type-key');
  const codeInput = document.getElementById('at-code');

  if (typeKey) {
    _editingTypeKey = typeKey;
    titleEl.textContent = '자산유형 수정';
    apiFetch('/api/v1/asset-type-codes?active_only=false').then(types => {
      const t = types.find(x => x.type_key === typeKey);
      if (!t) return;
      keyInput.value = t.type_key;
      keyInput.disabled = true;
      codeInput.value = t.code;
      codeInput.disabled = true;
      document.getElementById('at-kind').value = t.kind || 'hardware';
      document.getElementById('at-label').value = t.label;
      document.getElementById('at-sort-order').value = t.sort_order;
      document.getElementById('at-is-active').value = String(t.is_active);
    });
  } else {
    _editingTypeKey = null;
    titleEl.textContent = '자산유형 추가';
    keyInput.value = '';
    keyInput.disabled = false;
    codeInput.value = '';
    codeInput.disabled = false;
    document.getElementById('at-kind').value = 'hardware';
    document.getElementById('at-label').value = '';
    document.getElementById('at-sort-order').value = '0';
    document.getElementById('at-is-active').value = 'true';
  }
  modal.showModal();
}

async function submitAssetType() {
  const label = document.getElementById('at-label').value.trim();
  const kind = document.getElementById('at-kind').value;
  const sortOrder = Number(document.getElementById('at-sort-order').value) || 0;
  const isActive = document.getElementById('at-is-active').value === 'true';

  try {
    if (_editingTypeKey) {
      await apiFetch('/api/v1/asset-type-codes/' + encodeURIComponent(_editingTypeKey), {
        method: 'PATCH', body: { label, kind, sort_order: sortOrder, is_active: isActive },
      });
      showToast('자산유형이 수정되었습니다.');
    } else {
      const typeKey = document.getElementById('at-type-key').value.trim();
      const code = document.getElementById('at-code').value.trim().toUpperCase();
      await apiFetch('/api/v1/asset-type-codes', {
        method: 'POST', body: { type_key: typeKey, code, kind, label, sort_order: sortOrder },
      });
      showToast('자산유형이 추가되었습니다.');
    }
    document.getElementById('modal-asset-type').close();
    if (typeof invalidateAssetTypeCodesCache === 'function') invalidateAssetTypeCodesCache();
    loadAssetTypeTable();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 자산유형 이벤트 바인딩
if (document.getElementById('btn-add-asset-type')) {
  document.getElementById('btn-add-asset-type').addEventListener('click', () => openAssetTypeModal(null));
  document.getElementById('btn-at-cancel').addEventListener('click', () => document.getElementById('modal-asset-type').close());
  document.getElementById('btn-at-submit').addEventListener('click', submitAssetType);
  loadAssetTypeTable();
}

function getSelectedGlobalClassificationNode() {
  return _globalClassificationNodes.find(node => node.id === _globalClassificationSelectedNodeId) || null;
}

function getVisibleGlobalClassificationNodes() {
  const keyword = (document.getElementById('filter-global-classification-search')?.value || '').trim().toLowerCase();
  const activeOnly = document.getElementById('chk-global-classification-active-only')?.checked;
  return _globalClassificationNodes.filter(node => {
    if (activeOnly && !node.is_active) return false;
    if (!keyword) return true;
    return [node.node_code, node.node_name, node.path_label].some(value => String(value || '').toLowerCase().includes(keyword));
  });
}

function buildVisibleGlobalClassificationTree() {
  const visibleIds = new Set(getVisibleGlobalClassificationNodes().map(node => node.id));
  const cloned = _globalClassificationNodes.map(node => ({ ...node, children: [] }));
  const map = new Map(cloned.map(node => [node.id, node]));
  const roots = [];
  cloned.forEach(node => {
    if (!visibleIds.has(node.id)) return;
    const parent = node.parent_id ? map.get(node.parent_id) : null;
    if (parent && visibleIds.has(parent.id)) parent.children.push(node);
    else roots.push(node);
  });
  const sorter = (a, b) => {
    if ((a.sort_order ?? 100) !== (b.sort_order ?? 100)) return (a.sort_order ?? 100) - (b.sort_order ?? 100);
    if ((a.level ?? 0) !== (b.level ?? 0)) return (a.level ?? 0) - (b.level ?? 0);
    return String(a.node_name || '').localeCompare(String(b.node_name || ''), 'ko');
  };
  const sortTree = (nodes) => {
    nodes.sort(sorter);
    nodes.forEach(node => sortTree(node.children));
  };
  sortTree(roots);
  return roots;
}

function renderGlobalClassificationTreeNode(node) {
  const hasChildren = node.children && node.children.length > 0;
  const collapsed = _globalClassificationCollapsed.has(node.id);
  const levelAlias = getGlobalClassificationAlias(node.level || 1);
  const childrenHtml = hasChildren && !collapsed
    ? `<ul>${node.children.map(renderGlobalClassificationTreeNode).join('')}</ul>`
    : '';
  return `
    <li class="classification-tree-item">
      <button type="button" class="classification-tree-node ${node.id === _globalClassificationSelectedNodeId ? 'is-selected' : ''} ${node.is_active ? '' : 'is-inactive'}" data-global-node-id="${node.id}">
        <span class="classification-tree-toggle ${hasChildren ? '' : 'is-placeholder'}" data-global-toggle-node="${hasChildren ? node.id : ''}">${hasChildren ? (collapsed ? '▸' : '▾') : '•'}</span>
        <span class="classification-tree-main">
          <span class="classification-tree-title">
            <span class="classification-tree-name">${escapeHtml(node.node_name)}</span>
            <span class="classification-tree-code">${escapeHtml(node.node_code)}</span>
          </span>
          <span class="classification-tree-path">${escapeHtml(node.path_label || '—')}</span>
        </span>
        <span class="classification-tree-meta">
          <span class="classification-pill classification-pill-alias">${escapeHtml(levelAlias)}</span>
          ${node.is_active ? '<span class="classification-pill">활성</span>' : '<span class="classification-pill">비활성</span>'}
        </span>
      </button>
      ${childrenHtml}
    </li>
  `;
}

function renderGlobalClassificationSummary() {
  const container = document.getElementById('global-classification-summary');
  const leafAlias = getGlobalClassificationAliases().filter(Boolean).at(-1) || GLOBAL_CLASSIFICATION_ALIAS_DEFAULTS[2];
  if (!_globalClassificationScheme) {
    container.innerHTML = `
      <div class="classification-stat"><span class="classification-stat-label">분류체계</span><span class="classification-stat-value">미설정</span></div>
      <div class="classification-stat"><span class="classification-stat-label">노드 수</span><span class="classification-stat-value">0</span></div>
      <div class="classification-stat"><span class="classification-stat-label">최종 라벨</span><span class="classification-stat-value">${escapeHtml(leafAlias)}</span></div>
    `;
    return;
  }
  container.innerHTML = `
    <div class="classification-stat"><span class="classification-stat-label">분류체계</span><span class="classification-stat-value">${escapeHtml(_globalClassificationScheme.name)}</span></div>
    <div class="classification-stat"><span class="classification-stat-label">노드 수</span><span class="classification-stat-value">${_globalClassificationScheme.node_count ?? _globalClassificationNodes.length}</span></div>
    <div class="classification-stat"><span class="classification-stat-label">최종 라벨</span><span class="classification-stat-value">${escapeHtml(leafAlias)}</span></div>
  `;
}

function maxGlobalClassificationLevel() {
  return Math.min(
    5,
    _globalClassificationNodes.reduce((max, node) => Math.max(max, Number(node.level || 1)), 1),
  );
}

function renderGlobalClassificationLevelControls() {
  const container = document.getElementById('global-classification-level-controls');
  if (!container) return;
  if (!_globalClassificationScheme || !_globalClassificationNodes.length) {
    container.innerHTML = '';
    return;
  }
  const maxLevel = maxGlobalClassificationLevel();
  const levels = [];
  for (let level = 1; level < maxLevel && levels.length < 4; level += 1) {
    levels.push({ value: level, label: String(level), title: `${level}레벨까지 펼치기` });
  }
  levels.push({ value: maxLevel, label: 'max', title: `최대(${maxLevel}레벨)까지 펼치기` });
  container.innerHTML = levels.map((item) => `
    <button
      type="button"
      class="classification-level-btn ${_globalClassificationExpandLevel === item.value ? 'is-active' : ''}"
      data-global-expand-level="${item.value}"
      title="${item.title}"
    >${item.label}</button>
  `).join('');
}

function applyGlobalClassificationExpandLevel(level) {
  _globalClassificationExpandLevel = level;
  _globalClassificationCollapsed.clear();
  _globalClassificationNodes.forEach((node) => {
    const hasChildren = _globalClassificationNodes.some((item) => item.parent_id === node.id);
    if (hasChildren && Number(node.level || 1) >= level) {
      _globalClassificationCollapsed.add(node.id);
    }
  });
  saveGlobalClassificationTreeState();
  renderGlobalClassificationTree();
}

function renderGlobalClassificationTree() {
  const container = document.getElementById('global-classification-tree');
  renderGlobalClassificationLevelControls();
  if (!_globalClassificationScheme) {
    container.innerHTML = '<div class="classification-tree-empty">글로벌 기본 분류체계가 없습니다.</div>';
    return;
  }
  const roots = buildVisibleGlobalClassificationTree();
  if (!roots.length) {
    container.innerHTML = '<div class="classification-tree-empty">조건에 맞는 분류가 없습니다.</div>';
    return;
  }
  container.innerHTML = `<ul class="classification-tree-root">${roots.map(renderGlobalClassificationTreeNode).join('')}</ul>`;
}

function renderGlobalClassificationDetail() {
  const node = getSelectedGlobalClassificationNode();
  const emptyEl = document.getElementById('global-classification-detail-empty');
  const contentEl = document.getElementById('global-classification-detail-content');
  document.getElementById('btn-global-classification-add-child').disabled = !_globalClassificationScheme || !node;
  document.getElementById('btn-global-classification-edit-node').disabled = !node;
  document.getElementById('btn-global-classification-delete-node').disabled = !node;
  document.getElementById('btn-global-classification-edit-scheme').disabled = !_globalClassificationScheme;
  document.getElementById('btn-global-classification-add-root').disabled = !_globalClassificationScheme;
  if (!node) {
    applyGlobalClassificationAliases(null);
    emptyEl.classList.remove('hidden');
    contentEl.classList.add('hidden');
    return;
  }
  applyGlobalClassificationAliases(node);
  emptyEl.classList.add('hidden');
  contentEl.classList.remove('hidden');
  const parent = _globalClassificationNodes.find(item => item.id === node.parent_id);
  document.getElementById('global-classification-detail-title').textContent = node.node_name;
  document.getElementById('global-classification-detail-help').textContent = '글로벌 기본 분류 노드의 코드, 경로, 운영 메모를 확인할 수 있습니다.';
  document.getElementById('global-classification-detail-code').textContent = node.node_code || '—';
  document.getElementById('global-classification-detail-name').textContent = node.node_name || '—';
  document.getElementById('global-classification-detail-level').textContent = `${String(node.level || '—')}레벨 · ${getGlobalClassificationAlias(node.level || 1)}`;
  document.getElementById('global-classification-detail-status').textContent = node.is_active ? '활성' : '비활성';
  document.getElementById('global-classification-detail-sort-order').textContent = String(node.sort_order ?? '—');
  document.getElementById('global-classification-detail-parent').textContent = parent?.node_name || '최상위';
  document.getElementById('global-classification-detail-note').textContent = node.note || '—';
  document.getElementById('global-classification-detail-path').textContent = node.path_label || '—';
}

function refreshGlobalClassificationView() {
  renderGlobalClassificationSummary();
  renderGlobalClassificationTree();
  renderGlobalClassificationDetail();
}

async function loadGlobalClassification() {
  loadGlobalClassificationTreeState();
  const schemes = await apiFetch('/api/v1/classification-schemes?scope_type=global');
  _globalClassificationScheme = schemes[0] || null;
  _globalClassificationNodes = [];
  if (_globalClassificationScheme) {
    _globalClassificationNodes = await apiFetch(`/api/v1/classification-schemes/${_globalClassificationScheme.id}/nodes`);
  }
  const validNodeIds = new Set(_globalClassificationNodes.map((node) => node.id));
  if (_globalClassificationSelectedNodeId && !validNodeIds.has(_globalClassificationSelectedNodeId)) _globalClassificationSelectedNodeId = null;
  [..._globalClassificationCollapsed].forEach((nodeId) => {
    if (!validNodeIds.has(nodeId)) _globalClassificationCollapsed.delete(nodeId);
  });
  applyGlobalClassificationAliases(null);
  saveGlobalClassificationTreeState();
  refreshGlobalClassificationView();
}

function populateGlobalClassificationParentOptions(selectedParentId = null, excludedNodeId = null) {
  const parentEl = document.getElementById('global-classification-node-parent');
  parentEl.innerHTML = '';
  const rootOption = document.createElement('option');
  rootOption.value = '';
  rootOption.textContent = '최상위 분류';
  parentEl.appendChild(rootOption);
  _globalClassificationNodes
    .filter(node => node.id !== excludedNodeId)
    .forEach(node => {
      const option = document.createElement('option');
      option.value = String(node.id);
      option.textContent = `${'· '.repeat(Math.max((node.level || 1) - 1, 0))}${node.path_label || node.node_name}`;
      parentEl.appendChild(option);
    });
  parentEl.value = selectedParentId ? String(selectedParentId) : '';
}

function openGlobalClassificationSchemeModal() {
  if (!_globalClassificationScheme) {
    showToast('글로벌 기본 분류체계가 없습니다.', 'warning');
    return;
  }
  document.getElementById('global-classification-scheme-name').value = _globalClassificationScheme.name || '';
  document.getElementById('global-classification-scheme-description').value = _globalClassificationScheme.description || '';
  document.getElementById('global-classification-scheme-level-1-alias').value = _globalClassificationScheme.level_1_alias || '';
  document.getElementById('global-classification-scheme-level-2-alias').value = _globalClassificationScheme.level_2_alias || '';
  document.getElementById('global-classification-scheme-level-3-alias').value = _globalClassificationScheme.level_3_alias || '';
  document.getElementById('global-classification-scheme-level-4-alias').value = _globalClassificationScheme.level_4_alias || '';
  document.getElementById('global-classification-scheme-level-5-alias').value = _globalClassificationScheme.level_5_alias || '';
  document.getElementById('global-classification-scheme-active').value = String(_globalClassificationScheme.is_active !== false);
  document.getElementById('modal-global-classification-scheme').showModal();
}

function openGlobalClassificationNodeModal(mode) {
  if (!_globalClassificationScheme) {
    showToast('글로벌 기본 분류체계가 없습니다.', 'warning');
    return;
  }
  const node = mode === 'edit' ? getSelectedGlobalClassificationNode() : null;
  if (mode === 'edit' && !node) {
    showToast('수정할 분류를 먼저 선택하세요.', 'warning');
    return;
  }
  document.getElementById('modal-global-classification-node-title').textContent = mode === 'edit' ? '분류 수정' : '분류 등록';
  document.getElementById('global-classification-node-id').value = node?.id || '';
  document.getElementById('global-classification-node-code').value = node?.node_code || '';
  document.getElementById('global-classification-node-name').value = node?.node_name || '';
  document.getElementById('global-classification-node-sort-order').value = node?.sort_order ?? 100;
  document.getElementById('global-classification-node-active').value = String(node?.is_active ?? true);
  document.getElementById('global-classification-node-note').value = node?.note || '';
  const parentId = mode === 'add_child' ? getSelectedGlobalClassificationNode()?.id : (node?.parent_id || null);
  populateGlobalClassificationParentOptions(parentId, node?.id || null);
  document.getElementById('modal-global-classification-node').showModal();
}

async function saveGlobalClassificationScheme() {
  if (!_globalClassificationScheme) return;
  const payload = {
    name: document.getElementById('global-classification-scheme-name').value.trim(),
    description: document.getElementById('global-classification-scheme-description').value.trim() || null,
    level_1_alias: document.getElementById('global-classification-scheme-level-1-alias').value.trim() || null,
    level_2_alias: document.getElementById('global-classification-scheme-level-2-alias').value.trim() || null,
    level_3_alias: document.getElementById('global-classification-scheme-level-3-alias').value.trim() || null,
    level_4_alias: document.getElementById('global-classification-scheme-level-4-alias').value.trim() || null,
    level_5_alias: document.getElementById('global-classification-scheme-level-5-alias').value.trim() || null,
    is_active: document.getElementById('global-classification-scheme-active').value === 'true',
  };
  if (!payload.name) {
    showToast('분류체계명을 입력하세요.', 'warning');
    return;
  }
  _globalClassificationScheme = await apiFetch(`/api/v1/classification-schemes/${_globalClassificationScheme.id}`, {
    method: 'PATCH',
    body: payload,
  });
  document.getElementById('modal-global-classification-scheme').close();
  showToast('글로벌 기본 분류체계를 수정했습니다.');
  await loadGlobalClassification();
}

async function saveGlobalClassificationNode() {
  if (!_globalClassificationScheme) return;
  const nodeId = Number(document.getElementById('global-classification-node-id').value || 0);
  const payload = {
    node_code: document.getElementById('global-classification-node-code').value.trim(),
    node_name: document.getElementById('global-classification-node-name').value.trim(),
    parent_id: document.getElementById('global-classification-node-parent').value ? Number(document.getElementById('global-classification-node-parent').value) : null,
    sort_order: Number(document.getElementById('global-classification-node-sort-order').value || 100),
    is_active: document.getElementById('global-classification-node-active').value === 'true',
    note: document.getElementById('global-classification-node-note').value.trim() || null,
  };
  if (!payload.node_code || !payload.node_name) {
    showToast('코드와 분류명은 필수입니다.', 'warning');
    return;
  }
  if (nodeId) {
    await apiFetch(`/api/v1/classification-nodes/${nodeId}`, { method: 'PATCH', body: payload });
    showToast('분류를 수정했습니다.');
  } else {
    await apiFetch(`/api/v1/classification-schemes/${_globalClassificationScheme.id}/nodes`, { method: 'POST', body: payload });
    showToast('분류를 등록했습니다.');
  }
  document.getElementById('modal-global-classification-node').close();
  await loadGlobalClassification();
}

async function deleteGlobalClassificationNode() {
  const node = getSelectedGlobalClassificationNode();
  if (!node) {
    showToast('삭제할 분류를 먼저 선택하세요.', 'warning');
    return;
  }
  if (!confirm(`분류 "${node.node_name}"을(를) 삭제하시겠습니까?`)) return;
  try {
    await apiFetch(`/api/v1/classification-nodes/${node.id}`, { method: 'DELETE' });
    _globalClassificationSelectedNodeId = null;
    showToast('분류를 삭제했습니다.');
    await loadGlobalClassification();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function bindGlobalClassificationEvents() {
  document.getElementById('filter-global-classification-search').addEventListener('input', renderGlobalClassificationTree);
  document.getElementById('chk-global-classification-active-only').addEventListener('change', renderGlobalClassificationTree);
  document.getElementById('btn-global-classification-refresh').addEventListener('click', () => loadGlobalClassification().catch(err => showToast(err.message, 'error')));
  document.getElementById('btn-global-classification-edit-scheme').addEventListener('click', openGlobalClassificationSchemeModal);
  document.getElementById('btn-global-classification-add-root').addEventListener('click', () => openGlobalClassificationNodeModal('add_root'));
  document.getElementById('btn-global-classification-add-child').addEventListener('click', () => openGlobalClassificationNodeModal('add_child'));
  document.getElementById('btn-global-classification-edit-node').addEventListener('click', () => openGlobalClassificationNodeModal('edit'));
  document.getElementById('btn-global-classification-delete-node').addEventListener('click', deleteGlobalClassificationNode);
  document.getElementById('btn-global-classification-scheme-cancel').addEventListener('click', () => document.getElementById('modal-global-classification-scheme').close());
  document.getElementById('btn-global-classification-scheme-submit').addEventListener('click', () => saveGlobalClassificationScheme().catch(err => showToast(err.message, 'error')));
  document.getElementById('btn-global-classification-node-cancel').addEventListener('click', () => document.getElementById('modal-global-classification-node').close());
  document.getElementById('btn-global-classification-node-submit').addEventListener('click', () => saveGlobalClassificationNode().catch(err => showToast(err.message, 'error')));
  document.getElementById('global-classification-level-controls').addEventListener('click', (event) => {
    const btn = event.target.closest('[data-global-expand-level]');
    if (!btn) return;
    applyGlobalClassificationExpandLevel(Number(btn.dataset.globalExpandLevel));
  });
  document.getElementById('global-classification-tree').addEventListener('click', (event) => {
    const toggle = event.target.closest('[data-global-toggle-node]');
    if (toggle && toggle.dataset.globalToggleNode) {
      const nodeId = Number(toggle.dataset.globalToggleNode);
      _globalClassificationExpandLevel = null;
      if (_globalClassificationCollapsed.has(nodeId)) _globalClassificationCollapsed.delete(nodeId);
      else _globalClassificationCollapsed.add(nodeId);
      saveGlobalClassificationTreeState();
      renderGlobalClassificationTree();
      return;
    }
    const row = event.target.closest('[data-global-node-id]');
    if (!row) return;
    _globalClassificationSelectedNodeId = Number(row.dataset.globalNodeId);
    saveGlobalClassificationTreeState();
    renderGlobalClassificationTree();
    renderGlobalClassificationDetail();
  });
}

async function loadAssetTypeClassificationMappings() {
  _assetTypeClassificationMappings = await apiFetch('/api/v1/asset-type-classification-mappings');
  renderAssetTypeClassificationMappingTable();
}

function renderAssetTypeClassificationMappingTable() {
  const tbody = document.getElementById('asset-type-mapping-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  _assetTypeClassificationMappings.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(row.asset_type_label || row.asset_type_key)}</td>
      <td><span class="cell-code">${escapeHtml(row.classification_node_code)}</span></td>
      <td>${escapeHtml(row.classification_node_name || '—')}</td>
      <td>${escapeHtml(row.classification_path_label || '—')}</td>
      <td class="cell-center">${row.is_default ? '<span class="badge-active">기본</span>' : '<span class="cell-muted">-</span>'}</td>
      <td class="cell-center">${row.is_allowed ? '<span class="badge-active">허용</span>' : '<span class="badge-inactive">차단</span>'}</td>
      <td class="cell-center">${row.sort_order}</td>
      <td>${escapeHtml(row.note || '—')}</td>
      <td class="cell-center">
        <button class="btn btn-secondary btn-xs" data-edit-mapping="${row.id}">수정</button>
        <button class="btn btn-danger btn-xs" data-delete-mapping="${row.id}">삭제</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

async function populateAssetTypeMappingOptions(selectedAssetTypeKey = '', selectedNodeCode = '') {
  const typeSel = document.getElementById('asset-type-mapping-asset-type');
  const nodeSel = document.getElementById('asset-type-mapping-node-code');
  const types = await apiFetch('/api/v1/asset-type-codes?active_only=false');
  typeSel.innerHTML = '';
  types.forEach(type => {
    const option = document.createElement('option');
    option.value = type.type_key;
    option.textContent = `${type.label} (${type.type_key})`;
    typeSel.appendChild(option);
  });
  nodeSel.innerHTML = '';
  _globalClassificationNodes.forEach(node => {
    const option = document.createElement('option');
    option.value = node.node_code;
    option.textContent = `${node.path_label || node.node_name} (${node.node_code})`;
    nodeSel.appendChild(option);
  });
  typeSel.value = selectedAssetTypeKey || typeSel.value;
  nodeSel.value = selectedNodeCode || nodeSel.value;
}

async function openAssetTypeClassificationMappingModal(mappingId = null) {
  const title = document.getElementById('modal-asset-type-mapping-title');
  const idEl = document.getElementById('asset-type-mapping-id');
  const sortEl = document.getElementById('asset-type-mapping-sort-order');
  const defaultEl = document.getElementById('asset-type-mapping-is-default');
  const allowedEl = document.getElementById('asset-type-mapping-is-allowed');
  const noteEl = document.getElementById('asset-type-mapping-note');
  if (!_globalClassificationNodes.length) {
    await loadGlobalClassification();
  }
  if (mappingId) {
    const row = _assetTypeClassificationMappings.find(item => item.id === mappingId);
    if (!row) return;
    title.textContent = '자산유형-분류 매핑 수정';
    idEl.value = String(row.id);
    await populateAssetTypeMappingOptions(row.asset_type_key, row.classification_node_code);
    document.getElementById('asset-type-mapping-asset-type').disabled = true;
    sortEl.value = row.sort_order ?? 0;
    defaultEl.checked = !!row.is_default;
    allowedEl.checked = !!row.is_allowed;
    noteEl.value = row.note || '';
  } else {
    title.textContent = '자산유형-분류 매핑 추가';
    idEl.value = '';
    await populateAssetTypeMappingOptions();
    document.getElementById('asset-type-mapping-asset-type').disabled = false;
    sortEl.value = '0';
    defaultEl.checked = false;
    allowedEl.checked = true;
    noteEl.value = '';
  }
  document.getElementById('modal-asset-type-mapping').showModal();
}

async function submitAssetTypeClassificationMapping() {
  const mappingId = Number(document.getElementById('asset-type-mapping-id').value || 0);
  const payload = {
    asset_type_key: document.getElementById('asset-type-mapping-asset-type').value,
    classification_node_code: document.getElementById('asset-type-mapping-node-code').value,
    is_default: document.getElementById('asset-type-mapping-is-default').checked,
    is_allowed: document.getElementById('asset-type-mapping-is-allowed').checked,
    sort_order: Number(document.getElementById('asset-type-mapping-sort-order').value || 0),
    note: document.getElementById('asset-type-mapping-note').value.trim() || null,
  };
  if (!payload.asset_type_key || !payload.classification_node_code) {
    showToast('자산유형과 분류 노드는 필수입니다.', 'warning');
    return;
  }
  if (mappingId) {
    await apiFetch(`/api/v1/asset-type-classification-mappings/${mappingId}`, { method: 'PATCH', body: payload });
    showToast('자산유형-분류 매핑을 수정했습니다.');
  } else {
    await apiFetch('/api/v1/asset-type-classification-mappings', { method: 'POST', body: payload });
    showToast('자산유형-분류 매핑을 추가했습니다.');
  }
  document.getElementById('modal-asset-type-mapping').close();
  await loadAssetTypeClassificationMappings();
}

async function deleteAssetTypeClassificationMapping(mappingId) {
  if (!confirm('이 매핑을 삭제하시겠습니까?')) return;
  try {
    await apiFetch(`/api/v1/asset-type-classification-mappings/${mappingId}`, { method: 'DELETE' });
    showToast('자산유형-분류 매핑을 삭제했습니다.');
    await loadAssetTypeClassificationMappings();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function bindAssetTypeClassificationMappingEvents() {
  document.getElementById('btn-add-asset-type-mapping').addEventListener('click', () => openAssetTypeClassificationMappingModal().catch(err => showToast(err.message, 'error')));
  document.getElementById('btn-asset-type-mapping-cancel').addEventListener('click', () => document.getElementById('modal-asset-type-mapping').close());
  document.getElementById('btn-asset-type-mapping-submit').addEventListener('click', () => submitAssetTypeClassificationMapping().catch(err => showToast(err.message, 'error')));
  document.getElementById('asset-type-mapping-tbody').addEventListener('click', (event) => {
    const editBtn = event.target.closest('[data-edit-mapping]');
    if (editBtn) {
      openAssetTypeClassificationMappingModal(Number(editBtn.dataset.editMapping)).catch(err => showToast(err.message, 'error'));
      return;
    }
    const deleteBtn = event.target.closest('[data-delete-mapping]');
    if (deleteBtn) {
      deleteAssetTypeClassificationMapping(Number(deleteBtn.dataset.deleteMapping));
    }
  });
}
