/* ── 거래처 관리 ────────────────────────────────────────────── */
let gridApi;
let contractContactGridApi;
let contractsGridApi;
let masterContactGridApi;
let financialsGridApi;
let receiptsGridApi;
let selectedCustomerId = null;
let customerFilterTags = [];
let allCustomers = [];
let relatedContracts = [];   // 관련 사업 목록 (담당자 추가 모달용)
let masterContacts = []; // 마스터 담당자 (폴백용 + 사업별 담당자 선택용)
let loadedTabs = {};     // 탭별 로드 상태
let activeOnlyFilter = true;  // 진행중 사업만 필터
let contractsData = null;  // 관련 사업 API 응답 캐시

// ── 거래처 목록 그리드 (좌측) ──────────────────────────────────
const listColDefs = [
  { field: 'name', headerName: '거래처명', flex: 1, minWidth: 120,
    cellRenderer: (params) => {
      const d = params.data;
      if (!d) return '';
      const sub = d.active_count > 0 || d.total_revenue > 0
        ? `<div class="cust-list-sub">진행중 ${d.active_count}건 · 매출 ${fmt(d.total_revenue)}원</div>`
        : '';
      return `<div class="cust-list-cell">${d.name}${sub}</div>`;
    },
    autoHeight: true,
  },
];

// ── 초기화 ────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadTermLabels();
  applyTermLabels();

  const el = document.getElementById('grid-customers');
  gridApi = agGrid.createGrid(el, {
    columnDefs: listColDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true },
    enableCellTextSelection: true,
    ensureDomOrder: true,
    rowSelection: 'single',
    onRowClicked: (e) => {
      if (e.data?.id) selectCustomer(e.data.id);
    },
    isExternalFilterPresent: () => customerFilterTags.length > 0,
    doesExternalFilterPass: (node) => {
      const name = (node.data.name || '').toLowerCase();
      return customerFilterTags.some(t => name.includes(t.toLowerCase()));
    },
  });
  loadData(true);
  initTagInput('customer-tag-input', 'customer-tag-list', customerFilterTags, () => gridApi.onFilterChanged());
  _initSplitter();

  // 저장된 필터 상태 복원
  const savedActiveOnly = localStorage.getItem(LS_ACTIVE_ONLY);
  if (savedActiveOnly !== null) {
    activeOnlyFilter = savedActiveOnly === 'true';
    document.getElementById('chk-active-only').checked = activeOnlyFilter;
  }

  // 저장된 탭 복원
  const savedTab = localStorage.getItem(LS_ACTIVE_TAB);
  if (savedTab && savedTab !== 'contracts') {
    switchTab(savedTab);
  }

  // "내 거래처만" 토글
  document.getElementById('chk-my-customers').addEventListener('change', () => loadData());

  // 신규 거래처
  document.getElementById('btn-add').addEventListener('click', () => {
    document.getElementById('new-customer-name').value = '';
    document.getElementById('modal-add').showModal();
  });
  document.getElementById('btn-cancel').addEventListener('click', () => document.getElementById('modal-add').close());
  document.getElementById('btn-submit').addEventListener('click', submitNew);

  // 거래처 삭제
  document.getElementById('btn-delete-customer').addEventListener('click', deleteCustomer);

  // 마스터 담당자 등록
  document.getElementById('btn-add-master-contact').addEventListener('click', openAddMasterContact);
  document.getElementById('btn-mc-cancel').addEventListener('click', () => document.getElementById('modal-add-master-contact').close());
  document.getElementById('btn-mc-submit').addEventListener('click', submitNewMasterContact);

  // 마스터 담당자 수정 모달
  document.getElementById('btn-edit-mc-cancel').addEventListener('click', () => document.getElementById('modal-edit-master-contact').close());
  document.getElementById('btn-edit-mc-submit').addEventListener('click', submitEditMasterContact);

  // 탭 전환
  document.getElementById('cust-tabs').addEventListener('click', (e) => {
    const btn = e.target.closest('.cust-tab');
    if (!btn) return;
    switchTab(btn.dataset.tab);
  });

  // 진행중만 필터 토글 (글로벌 — 모든 탭에 적용)
  document.getElementById('chk-active-only').addEventListener('change', (e) => {
    activeOnlyFilter = e.target.checked;
    localStorage.setItem(LS_ACTIVE_ONLY, String(activeOnlyFilter));
    if (contractsGridApi) contractsGridApi.onFilterChanged();
    if (contractContactGridApi) contractContactGridApi.onFilterChanged();
    if (financialsGridApi) financialsGridApi.onFilterChanged();
    if (receiptsGridApi) receiptsGridApi.onFilterChanged();
  });

  // Ctrl+S: 사업별 담당자 저장 (담당자 탭 활성 시)
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      const activeTab = document.querySelector('.cust-tab.active')?.dataset.tab;
      if (activeTab === 'contacts') {
        e.preventDefault();
        saveAllContractContacts();
      }
    }
  });
});

// ── 상태 저장/복원 키 ─────────────────────────────────────────
const LS_ACTIVE_TAB = 'cust_active_tab';
const LS_ACTIVE_ONLY = 'cust_active_only';
const LS_COL_STATE_PREFIX = 'cust_col_';

function _saveColState(key, api) {
  if (!api) return;
  try { localStorage.setItem(LS_COL_STATE_PREFIX + key, JSON.stringify(api.getColumnState())); } catch {}
}
function _restoreColState(key, api) {
  if (!api) return;
  try {
    const saved = localStorage.getItem(LS_COL_STATE_PREFIX + key);
    if (saved) api.applyColumnState({ state: JSON.parse(saved), applyOrder: true });
  } catch {}
}

// ── 탭 전환 ───────────────────────────────────────────────────
function switchTab(tabName) {
  document.querySelectorAll('.cust-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.cust-tab[data-tab="${tabName}"]`)?.classList.add('active');
  document.querySelectorAll('.cust-tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + tabName)?.classList.add('active');
  localStorage.setItem(LS_ACTIVE_TAB, tabName);

  if (!loadedTabs[tabName] && selectedCustomerId) {
    loadedTabs[tabName] = true;
    loadTabContent(tabName);
  }
}

function loadTabContent(tabName) {
  switch (tabName) {
    case 'contracts': loadContractsTab(); break;
    case 'contacts': loadContactsTab(); break;
    case 'financials': loadFinancialsTab(); break;
    case 'receipts': loadReceiptsTab(); break;
  }
}

// ── 데이터 로드 ───────────────────────────────────────────────
async function loadData(restoreLast = false) {
  const params = new URLSearchParams();
  const chkMy = document.getElementById('chk-my-customers');
  if (chkMy && chkMy.checked) params.set('my_only', 'true');
  const res = await fetch('/api/v1/customers?' + params.toString());
  allCustomers = await res.json();
  gridApi.setGridOption('rowData', allCustomers);
  gridApi.onFilterChanged();

  // 초기 로드 시 서버에 저장된 마지막 선택 거래처 복원
  if (restoreLast && !selectedCustomerId) {
    try {
      const prefRes = await fetch('/api/v1/preferences/last_selected_customer');
      const pref = await prefRes.json();
      if (pref.value) {
        const lastId = parseInt(pref.value, 10);
        if (allCustomers.find(d => d.id === lastId)) {
          selectedCustomerId = lastId;
        }
      }
    } catch { /* ignore */ }
  }

  if (selectedCustomerId) {
    const row = allCustomers.find(d => d.id === selectedCustomerId);
    if (row) {
      loadDetail(selectedCustomerId);
      gridApi.forEachNode(node => {
        if (node.data.id === selectedCustomerId) node.setSelected(true);
      });
    } else {
      hideDetail();
    }
  }
}

// ── 거래처 선택 ───────────────────────────────────────────────
function selectCustomer(customerId) {
  selectedCustomerId = customerId;
  loadDetail(customerId);
  fetch('/api/v1/preferences/last_selected_customer', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value: String(customerId) }),
  }).catch(() => {});
}

async function loadDetail(customerId) {
  const cust = allCustomers.find(d => d.id === customerId);
  if (!cust) return;

  document.getElementById('detail-empty').classList.add('is-hidden');
  document.getElementById('detail-content').classList.remove('is-hidden');

  // 기본정보
  document.getElementById('detail-name').textContent = cust.name;
  renderCustomerInfo(cust);

  // 탭 상태 리셋 — 첫 탭(사업현황) 로드
  loadedTabs = {};
  contractsData = null;
  const activeTab = document.querySelector('.cust-tab.active')?.dataset.tab || 'contracts';
  loadedTabs[activeTab] = true;
  loadTabContent(activeTab);
}

function renderCustomerInfo(cust) {
  const card = document.getElementById('cust-info-card');
  card.textContent = '';

  // -- 읽기 전용 뷰 --
  const viewRow = document.createElement('div');
  viewRow.className = 'info-row';
  viewRow.id = 'cust-info-view';

  const bizItem = document.createElement('span');
  bizItem.className = 'info-item';
  bizItem.innerHTML = '<b>사업자번호</b> ';
  bizItem.appendChild(document.createTextNode(cust.business_no || '-'));

  const noteItem = document.createElement('span');
  noteItem.className = 'info-item';
  noteItem.innerHTML = '<b>비고</b> ';
  noteItem.appendChild(document.createTextNode(cust.notes || '-'));

  const btnItem = document.createElement('span');
  btnItem.className = 'info-item';
  const editBtn = document.createElement('button');
  editBtn.className = 'btn btn-secondary btn-sm';
  editBtn.textContent = '수정';
  editBtn.onclick = openEditCustomerInfo;
  btnItem.appendChild(editBtn);

  viewRow.append(bizItem, noteItem, btnItem);

  // -- 편집 폼 --
  const editDiv = document.createElement('div');
  editDiv.className = 'info-edit-form is-hidden';
  editDiv.id = 'cust-info-edit';

  const editRow = document.createElement('div');
  editRow.className = 'info-edit-row';

  // 거래처명
  const nameField = _createEditField('거래처명', 'info-name', cust.name || '');
  // 사업자번호
  const bizField = _createEditField('사업자번호', 'info-business-no', cust.business_no || '');
  // 비고
  const notesField = _createEditField('비고', 'info-notes', cust.notes || '', 'input-wide');

  // 버튼
  const actField = document.createElement('div');
  actField.className = 'info-edit-field info-edit-actions';
  const actLabel = document.createElement('label');
  actLabel.innerHTML = '&nbsp;';
  const btnGroup = document.createElement('div');
  btnGroup.className = 'btn-group';
  const cancelBtn = document.createElement('button');
  cancelBtn.className = 'btn btn-secondary btn-sm';
  cancelBtn.textContent = '취소';
  cancelBtn.onclick = cancelEditCustomerInfo;
  const saveBtn = document.createElement('button');
  saveBtn.id = 'btn-save-info';
  saveBtn.className = 'btn btn-primary btn-sm';
  saveBtn.textContent = '저장';
  saveBtn.onclick = saveInfo;
  btnGroup.append(cancelBtn, saveBtn);
  actField.append(actLabel, btnGroup);

  editRow.append(nameField, bizField, notesField, actField);
  editDiv.appendChild(editRow);

  card.append(viewRow, editDiv);
}

function _createEditField(label, inputId, value, extraClass) {
  const wrap = document.createElement('div');
  wrap.className = 'info-edit-field';
  const lbl = document.createElement('label');
  lbl.textContent = label;
  const input = document.createElement('input');
  input.type = 'text';
  input.id = inputId;
  input.value = value;
  if (extraClass) input.className = extraClass;
  wrap.append(lbl, input);
  return wrap;
}

function openEditCustomerInfo() {
  document.getElementById('cust-info-view').classList.add('is-hidden');
  document.getElementById('cust-info-edit').classList.remove('is-hidden');
}

function cancelEditCustomerInfo() {
  const cust = allCustomers.find(d => d.id === selectedCustomerId);
  if (cust) renderCustomerInfo(cust);
}

function hideDetail() {
  selectedCustomerId = null;
  document.getElementById('detail-empty').classList.remove('is-hidden');
  document.getElementById('detail-content').classList.add('is-hidden');
}

// ══════════════════════════════════════════════════════════════
// 사업현황 탭
// ══════════════════════════════════════════════════════════════
async function loadContractsTab() {
  if (!selectedCustomerId) return;
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}/contracts`);
  if (!res.ok) { console.error('contracts API error', res.status); return; }
  contractsData = await res.json();
  relatedContracts = contractsData.contracts || [];

  renderContractsSummary(contractsData.summary);
  renderContractsGrid(relatedContracts);
}

function _recalcContractsSummary() {
  if (!contractsGridApi) return;
  let active = 0, completed = 0, revenue = 0;
  // 건수는 전체 데이터 기준
  contractsGridApi.forEachNode(node => {
    if (node.data.is_completed) completed++; else active++;
  });
  // 매출은 필터 반영
  contractsGridApi.forEachNodeAfterFilter(node => {
    revenue += node.data.revenue_amount || 0;
  });
  renderContractsSummary({ active_count: active, completed_count: completed, total_revenue: revenue });
}

function renderContractsSummary(summary) {
  const el = document.getElementById('contracts-summary');
  if (!summary) { el.innerHTML = ''; return; }
  el.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item">
        <div class="summary-label">진행중 사업</div>
        <div class="summary-value">${summary.active_count}<span class="unit">건</span></div>
      </div>
      <div class="summary-item">
        <div class="summary-label">계약완료</div>
        <div class="summary-value">${summary.completed_count}<span class="unit">건</span></div>
      </div>
      <div class="summary-item highlight">
        <div class="summary-label">총 매출</div>
        <div class="summary-value">${fmt(summary.total_revenue)}<span class="unit">원</span></div>
      </div>
    </div>`;
}

function renderContractsGrid(contracts) {
  const el = document.getElementById('grid-related-contracts');
  el.innerHTML = '';
  const colDefs = [
    { field: 'contract_name', headerName: '사업명', minWidth: 140,
      cellClass: 'cell-link' },
    { field: 'period_label', headerName: '기간', width: 60 },
    { field: 'end_customer_name', headerName: 'END고객', width: 110 },
    { field: 'contract_type', headerName: '유형', width: 70 },
    { field: 'stage', headerName: '단계', width: 90,
      cellRenderer: (p) => {
        const v = p.value;
        if (!v) return '';
        const done = p.data.is_completed;
        const cls = done ? 'stage-badge completed' : 'stage-badge active';
        return `<span class="${cls}">${v}</span>`;
      },
    },
    { field: 'period_range', headerName: '사업기간', width: 140 },
    { field: 'revenue_amount', headerName: '매출액', width: 110, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-', cellClass: 'cell-revenue' },
    { field: 'cost_amount', headerName: '매입액', width: 110, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-', cellClass: 'cell-cost-blue' },
    { field: 'gp_pct', headerName: 'GP%', width: 70, type: 'numericColumn',
      valueFormatter: p => p.value != null ? p.value + '%' : '-' },
    { field: 'owner_name', headerName: '담당', width: 70 },
    { field: 'roles', headerName: '역할', width: 160,
      cellRenderer: (p) => {
        if (!p.value || !p.value.length) return '';
        return p.value.map(r => {
          let cls = 'contact';
          if (r === 'END고객') cls = 'end';
          else if (r === '매출처') cls = 'revenue';
          else if (r === '매입처') cls = 'cost';
          return `<span class="role-badge ${cls}">${r}</span>`;
        }).join('');
      },
    },
    { field: 'notes', headerName: '비고', flex: 1, minWidth: 60 },
  ];
  contractsGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: contracts,
    defaultColDef: {
      resizable: true, sortable: true,
      tooltipValueGetter: (p) => p.value,
    },
    tooltipShowDelay: 300,
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
    isExternalFilterPresent: () => activeOnlyFilter,
    doesExternalFilterPass: (node) => {
      return !node.data.is_completed;
    },
    onCellClicked: (e) => {
      if (e.column.getColId() === 'contract_name' && e.data?.period_id) {
        window.location.href = `/contracts/${e.data.period_id}`;
      }
    },
    onModelUpdated: () => {
      const el = document.getElementById('contracts-filter-empty');
      if (!el) return;
      const displayed = contractsGridApi?.getDisplayedRowCount?.() ?? 0;
      el.classList.toggle('is-hidden', displayed > 0);
      _recalcContractsSummary();
    },
    onSortChanged: () => _saveColState('contracts', contractsGridApi),
    onColumnResized: (e) => { if (e.finished) _saveColState('contracts', contractsGridApi); },
    onColumnMoved: () => _saveColState('contracts', contractsGridApi),
  });
  _restoreColState('contracts', contractsGridApi);
}

// ══════════════════════════════════════════════════════════════
// 담당자 탭
// ══════════════════════════════════════════════════════════════
async function loadContactsTab() {
  if (!selectedCustomerId) return;
  const [mcRes, dcRes] = await Promise.all([
    fetch(`/api/v1/customers/${selectedCustomerId}/contacts`),
    fetch(`/api/v1/customers/${selectedCustomerId}/contract-contacts-pivoted`),
  ]);
  masterContacts = await mcRes.json();
  const contractContacts = await dcRes.json();

  renderMasterContactGrid(masterContacts);
  renderContractContactGrid(contractContacts);
}

// ── 마스터 담당자 그리드 ──────────────────────────────────────
function renderMasterContactGrid(contacts) {
  const el = document.getElementById('grid-master-contacts');
  el.innerHTML = '';

  const ROLE_CLASS = { '영업': 'sales', '세금계산서': 'tax', '업무': 'ops' };

  const colDefs = [
    { field: 'roles', headerName: '역할', width: 180,
      cellRenderer: (p) => {
        if (!p.value || !p.value.length) return '';
        return p.value.map(r => {
          const cls = ROLE_CLASS[r.role_type] || '';
          const defCls = r.is_default ? ' default' : '';
          return `<span class="contact-role-badge ${cls}${defCls}">${r.role_type}${r.is_default ? '(기본)' : ''}</span>`;
        }).join('');
      },
    },
    { field: 'name', headerName: '이름', width: 90 },
    { field: 'phone', headerName: '연락처', width: 130 },
    { field: 'email', headerName: '이메일', flex: 1, minWidth: 160 },
    { headerName: '', width: 120, sortable: false, resizable: false,
      cellRenderer: (p) => {
        const id = p.data.id;
        const name = (p.data.name || '').replace(/'/g, "\\'");
        return `<button class="btn btn-secondary btn-xs btn-cell" onclick="openEditMasterContact(${id})">수정</button> `
             + `<button class="btn btn-danger btn-xs btn-cell" onclick="deleteMasterContact(${id}, '${name}')">삭제</button>`;
      },
    },
  ];
  masterContactGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: contacts,
    defaultColDef: { resizable: true, sortable: true },
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
  });
}

// ── 사업별 담당자 그리드 (인라인 편집) ──────────────────────
function renderContractContactGrid(contacts) {
  // 폴백: 마스터 기본 담당자
  const defaults = {};
  for (const mc of masterContacts) {
    for (const role of (mc.roles || [])) {
      if (role.is_default && !defaults[role.role_type]) {
        defaults[role.role_type] = mc;
      }
    }
  }
  for (const row of contacts) {
    row._fallback = {};
    for (const [prefix, type] of [['sales', '영업'], ['tax', '세금계산서'], ['ops', '업무']]) {
      if (!row[prefix + '_name'] && defaults[type]) {
        row._fallback[prefix] = defaults[type];
      }
    }
  }

  const el = document.getElementById('grid-contract-contacts');
  el.innerHTML = '';

  // 역할별 마스터 담당자 필터
  const contactsByRole = (roleType) =>
    masterContacts.filter(mc => (mc.roles || []).some(r => r.role_type === roleType));

  // 담당자 드롭다운 셀 에디터 클래스
  class ContactSelectEditor {
    init(params) {
      this.params = params;
      this.roleType = params.colDef._roleType;
      this.prefix = params.colDef._prefix;
      this.value = params.value || '';
      this.container = document.createElement('select');
      this.container.className = 'ag-cell-input-editor';
      // 빈 옵션 (삭제용)
      const emptyOpt = document.createElement('option');
      emptyOpt.value = '';
      emptyOpt.textContent = '-- 선택 해제 --';
      this.container.appendChild(emptyOpt);
      // 역할별 마스터 담당자
      for (const mc of contactsByRole(this.roleType)) {
        const opt = document.createElement('option');
        opt.value = String(mc.id);
        opt.textContent = mc.name + (mc.phone ? ` (${mc.phone})` : '');
        if (String(mc.id) === String(params.data[this.prefix + '_cc_id'])) {
          opt.selected = true;
        }
        this.container.appendChild(opt);
      }
    }
    getGui() { return this.container; }
    afterGuiAttached() { this.container.focus(); }
    getValue() {
      const selVal = this.container.value;
      // 선택한 cc_id를 row 데이터에 임시 저장 (에디터 파괴 전)
      this.params.data['_pending_' + this.prefix + '_cc_id'] = selVal ? parseInt(selVal, 10) : null;
      if (!selVal) return '';
      const mc = masterContacts.find(c => String(c.id) === selVal);
      return mc ? mc.name : '';
    }
    isPopup() { return false; }
  }

  // 담당자 셀 렌더러 (폴백 포함)
  const contactRenderer = (prefix) => (p) => {
    const val = p.value;
    if (val) return val;
    const fb = p.data._fallback?.[prefix];
    if (fb) return `<span class="cell-fallback">${fb.name || ''}</span>`;
    return `<span class="cell-placeholder">클릭하여 선택</span>`;
  };

  // 편집 가능 여부 (완료된 period는 편집 불가)
  const isEditable = (p) => !p.data.is_completed;

  const contactColDef = (prefix, roleType, headerName) => ({
    field: prefix + '_name',
    headerName: headerName,
    width: 110,
    editable: isEditable,
    cellEditor: ContactSelectEditor,
    cellRenderer: contactRenderer(prefix),
    cellClass: (p) => isEditable(p) ? 'cell-editable' : '',
    _roleType: roleType,
    _prefix: prefix,
  });

  const colDefs = [
    { field: 'contract_name', headerName: '사업명', minWidth: 120, cellClass: 'cell-link' },
    { field: 'period_label', headerName: '기간', width: 60 },
    contactColDef('sales', '영업', '영업 담당자'),
    contactColDef('tax', '세금계산서', '세금계산서 담당자'),
    contactColDef('ops', '업무', '업무 담당자'),
  ];

  contractContactGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: contacts,
    defaultColDef: {
      resizable: true, sortable: true,
      tooltipValueGetter: (p) => p.value,
    },
    tooltipShowDelay: 300,
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
    singleClickEdit: true,
    stopEditingWhenCellsLoseFocus: true,
    isExternalFilterPresent: () => activeOnlyFilter,
    doesExternalFilterPass: (node) => !node.data.is_completed,
    onCellClicked: (e) => {
      if (e.column.getColId() === 'contract_name' && e.data?.contract_period_id) {
        window.location.href = `/contracts/${e.data.contract_period_id}`;
      }
    },
    onCellValueChanged: (e) => {
      const prefix = e.colDef._prefix;
      if (!prefix) return;
      e.data._dirty = true;
    },
    onSortChanged: () => _saveColState('contacts', contractContactGridApi),
    onColumnResized: (e) => { if (e.finished) _saveColState('contacts', contractContactGridApi); },
    onColumnMoved: () => _saveColState('contacts', contractContactGridApi),
  });
  _restoreColState('contacts', contractContactGridApi);
}

/** 사업별 담당자 변경 사항 일괄 저장 */
async function saveAllContractContacts() {
  if (!contractContactGridApi) return;

  const dirtyRows = [];
  contractContactGridApi.forEachNode(node => {
    if (node.data._dirty) dirtyRows.push(node.data);
  });
  if (dirtyRows.length === 0) return;

  const roleTypeMap = { sales: '영업', tax: '세금계산서', ops: '업무' };
  const errors = [];

  for (const row of dirtyRows) {
    for (const prefix of ['sales', 'tax', 'ops']) {
      const pendingCcId = row['_pending_' + prefix + '_cc_id'];
      if (pendingCcId === undefined) continue;  // 이 역할은 변경되지 않음

      const existingId = row[prefix + '_id'];
      const roleType = roleTypeMap[prefix];

      try {
        if (!pendingCcId && existingId) {
          // 삭제
          const res = await fetch(`/api/v1/contract-contacts/${existingId}`, { method: 'DELETE' });
          if (!res.ok) errors.push(`${row.contract_name} ${roleType} 삭제 실패`);
        } else if (pendingCcId && existingId) {
          // 수정
          const res = await fetch(`/api/v1/contract-contacts/${existingId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ customer_contact_id: pendingCcId, contact_type: roleType }),
          });
          if (!res.ok) errors.push(`${row.contract_name} ${roleType} 수정 실패`);
        } else if (pendingCcId && !existingId) {
          // 신규 생성
          const res = await fetch(`/api/v1/contract-periods/${row.contract_period_id}/contacts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              customer_id: selectedCustomerId,
              customer_contact_id: pendingCcId,
              contact_type: roleType,
              rank: '정',
            }),
          });
          if (!res.ok) errors.push(`${row.contract_name} ${roleType} 등록 실패`);
        }
      } catch (err) {
        errors.push(`${row.contract_name} ${roleType}: ${err.message}`);
      }
    }
  }

  if (errors.length > 0) {
    alert('일부 저장 실패:\n' + errors.join('\n'));
  }

  // 새로고침
  loadedTabs['contacts'] = false;
  loadedTabs['contacts'] = true;
  loadContactsTab();
}

// ══════════════════════════════════════════════════════════════
// 매출·매입 탭
// ══════════════════════════════════════════════════════════════
async function loadFinancialsTab() {
  if (!selectedCustomerId) return;
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}/financials`);
  if (!res.ok) { console.error('financials API error', res.status); return; }
  const data = await res.json();

  renderFinancialsSummary(data.summary);
  renderFinancialsGrid(data.lines);
}

function _recalcFinancialsGroupTotals() {
  if (!financialsGridApi) return;
  // 필터 후 보이는 디테일 행 기준으로 그룹 행 금액 재계산
  const byGroup = {};
  financialsGridApi.forEachNodeAfterFilter(node => {
    const d = node.data;
    if (!d._is_group) {
      const key = d._group_key;
      if (!byGroup[key]) byGroup[key] = { revenue: 0, cost: 0 };
      byGroup[key].revenue += d.revenue || 0;
      byGroup[key].cost += d.cost || 0;
    }
  });
  financialsGridApi.forEachNode(node => {
    const d = node.data;
    if (d._is_group) {
      const g = byGroup[d._group_key] || { revenue: 0, cost: 0 };
      d.revenue = g.revenue;
      d.cost = g.cost;
      d.gp = g.revenue - g.cost;
      d.gp_pct = g.revenue > 0 ? Math.round((g.revenue - g.cost) / g.revenue * 1000) / 10 : null;
    }
  });
  financialsGridApi.refreshCells({ force: true });
}

function _recalcFinancialsSummary() {
  if (!financialsGridApi) return;
  let totalRev = 0, totalCost = 0;
  financialsGridApi.forEachNodeAfterFilter(node => {
    const d = node.data;
    // 디테일 행(period 단위)만 합산하여 정확한 필터 반영
    if (!d._is_group) {
      totalRev += d.revenue || 0;
      totalCost += d.cost || 0;
    }
  });
  renderFinancialsSummary({ total_revenue: totalRev, total_cost: totalCost, ar: null });
}

function renderFinancialsSummary(summary) {
  const el = document.getElementById('financials-summary');
  if (!summary) { el.innerHTML = ''; return; }
  el.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item">
        <div class="summary-label">총 매출</div>
        <div class="summary-value">${fmt(summary.total_revenue)}<span class="unit">원</span></div>
      </div>
      <div class="summary-item">
        <div class="summary-label">총 매입</div>
        <div class="summary-value">${fmt(summary.total_cost)}<span class="unit">원</span></div>
      </div>
      <div class="summary-item ${summary.ar > 0 ? 'warn' : ''}">
        <div class="summary-label">미수금</div>
        <div class="summary-value">${fmt(summary.ar)}<span class="unit">원</span></div>
      </div>
    </div>`;
}

// ── 그룹 expand/collapse 공통 ──────────────────────────────
const _expandedGroups = {};  // { gridKey: Set<groupKey> }

function _toggleGroup(gridKey, groupKey, api) {
  if (!_expandedGroups[gridKey]) _expandedGroups[gridKey] = new Set();
  const set = _expandedGroups[gridKey];
  if (set.has(groupKey)) set.delete(groupKey); else set.add(groupKey);
  api.onFilterChanged();
}

function _isGroupExpanded(gridKey, groupKey) {
  return _expandedGroups[gridKey]?.has(groupKey) || false;
}

function _groupFilterPass(gridKey, node) {
  const d = node.data;
  if (d._is_group) return true;  // 그룹 행은 항상 표시
  return _isGroupExpanded(gridKey, d._group_key);
}

function _groupCellRenderer(gridKey, api) {
  return (p) => {
    const d = p.data;
    if (!d._is_group) return p.value || '';
    const expanded = _isGroupExpanded(gridKey, d._group_key);
    const icon = expanded ? '▼' : '▶';
    const name = d.contract_name || d.period_label || '';
    return `<span class="group-toggle">${icon} <b>${name}</b></span>`;
  };
}

function renderFinancialsGrid(lines) {
  const el = document.getElementById('grid-financials');
  el.innerHTML = '';
  const GK = 'financials';
  // 기본 전부 펼침
  if (!_expandedGroups[GK]) {
    _expandedGroups[GK] = new Set(lines.filter(l => l._is_group).map(l => l._group_key));
  }
  const fmtAmt = (p) => p.value ? fmt(p.value) : '-';
  const colDefs = [
    { field: 'contract_name', headerName: '사업명', minWidth: 160,
      cellRenderer: (p) => {
        const d = p.data;
        if (d._is_group) return _groupCellRenderer(GK)(p);
        return '';
      },
    },
    { field: 'period_label', headerName: '기간', width: 60 },
    { field: 'revenue', headerName: '매출', width: 120, type: 'numericColumn', valueFormatter: fmtAmt, cellClass: 'cell-revenue' },
    { field: 'cost', headerName: '매입', width: 120, type: 'numericColumn', valueFormatter: fmtAmt, cellClass: 'cell-cost-blue' },
    { field: 'gp', headerName: 'GP', width: 120, type: 'numericColumn',
      valueFormatter: p => p.value != null ? fmt(p.value) : '-' },
    { field: 'gp_pct', headerName: 'GP%', flex: 1, type: 'numericColumn',
      valueFormatter: p => p.value != null ? p.value + '%' : '-' },
  ];
  financialsGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: lines || [],
    defaultColDef: { resizable: true, sortable: false },
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
    isExternalFilterPresent: () => true,
    doesExternalFilterPass: (node) => {
      if (activeOnlyFilter && node.data.is_completed) return false;
      return _groupFilterPass(GK, node);
    },
    getRowClass: (p) => p.data?._is_group ? 'group-row' : 'detail-row',
    onCellClicked: (e) => {
      if (e.data?._is_group && e.column.getColId() === 'contract_name') {
        _toggleGroup(GK, e.data._group_key, financialsGridApi);
      }
    },
    onColumnResized: (e) => { if (e.finished) _saveColState(GK, financialsGridApi); },
    onColumnMoved: () => _saveColState(GK, financialsGridApi),
    onModelUpdated: () => {
      _recalcFinancialsGroupTotals();
      _recalcFinancialsSummary();
    },
  });
  _restoreColState(GK, financialsGridApi);
}

// ══════════════════════════════════════════════════════════════
// 입금 탭
// ══════════════════════════════════════════════════════════════
async function loadReceiptsTab() {
  if (!selectedCustomerId) return;
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}/receipts`);
  if (!res.ok) { console.error('receipts API error', res.status); return; }
  const data = await res.json();

  renderReceiptsSummary(data.summary);
  renderReceiptsGrid(data.receipts);
}

function _recalcReceiptsGroupTotals() {
  if (!receiptsGridApi) return;
  // 필터 후 보이는 개별 입금 행 기준으로 그룹/소계 행 금액 재계산
  const byContract = {};
  const byPeriod = {};
  receiptsGridApi.forEachNodeAfterFilter(node => {
    const d = node.data;
    if (!d._is_group) {
      const cid = d._group_key;
      byContract[cid] = (byContract[cid] || 0) + (d.amount || 0);
    }
  });
  // period 소계는 하위 개별 행 합산
  receiptsGridApi.forEachNodeAfterFilter(node => {
    const d = node.data;
    if (d._is_group && d._period_group) {
      // period 소계는 바로 다음에 오는 개별 행들의 합
      // → 필터 후 보이는 개별 행을 이미 contract 단위로 합산했으므로, period 소계는 그대로 둠
    }
  });
  // 사업 그룹 행의 amount 갱신
  receiptsGridApi.forEachNode(node => {
    const d = node.data;
    if (d._is_group && d.contract_name) {
      d.amount = byContract[d._group_key] || 0;
    }
  });
  receiptsGridApi.refreshCells({ force: true });
}

function _recalcReceiptsSummary() {
  if (!receiptsGridApi) return;
  let total = 0;
  receiptsGridApi.forEachNodeAfterFilter(node => {
    const d = node.data;
    // 개별 입금 행만 합산 (그룹/소계 행 제외)
    if (!d._is_group) {
      total += d.amount || 0;
    }
  });
  renderReceiptsSummary({ total_receipt: total, ar_balance: null });
}

function renderReceiptsSummary(summary) {
  const el = document.getElementById('receipts-summary');
  if (!summary) { el.innerHTML = ''; return; }
  const arHtml = summary.ar_balance != null
    ? `<div class="summary-item ${summary.ar_balance > 0 ? 'warn' : ''}">
        <div class="summary-label">미수금 잔액</div>
        <div class="summary-value">${fmt(summary.ar_balance)}<span class="unit">원</span></div>
      </div>` : '';
  el.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item">
        <div class="summary-label">총 입금</div>
        <div class="summary-value">${fmt(summary.total_receipt)}<span class="unit">원</span></div>
      </div>
      ${arHtml}
    </div>`;
}

function renderReceiptsGrid(receipts) {
  const el = document.getElementById('grid-receipts');
  el.innerHTML = '';
  const GK = 'receipts';
  // 기본 축소 (사업 그룹만 표시)
  if (!_expandedGroups[GK]) _expandedGroups[GK] = new Set();

  const colDefs = [
    { field: 'contract_name', headerName: '사업명', minWidth: 160,
      cellRenderer: (p) => {
        const d = p.data;
        if (d._is_group && d.contract_name) return _groupCellRenderer(GK)(p);
        if (d._is_group && d._period_group) return `<span class="period-label">${d.period_label}</span>`;
        return '';
      },
    },
    { field: 'period_label', headerName: '기간', width: 60,
      cellRenderer: (p) => p.data._is_group ? '' : '',
    },
    { field: 'receipt_date', headerName: '입금일', width: 100 },
    { field: 'amount', headerName: '금액', width: 120, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-' },
    { field: 'description', headerName: '적요', flex: 1, minWidth: 100 },
    { field: 'revenue_month', headerName: '귀속월', width: 90 },
  ];
  receiptsGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: receipts || [],
    defaultColDef: { resizable: true, sortable: false },
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
    isExternalFilterPresent: () => true,
    doesExternalFilterPass: (node) => {
      if (activeOnlyFilter && node.data.is_completed) return false;
      return _groupFilterPass(GK, node);
    },
    getRowClass: (p) => p.data?._is_group ? 'group-row' : 'detail-row',
    onCellClicked: (e) => {
      if (e.data?._is_group && e.data.contract_name && e.column.getColId() === 'contract_name') {
        _toggleGroup(GK, e.data._group_key, receiptsGridApi);
      }
    },
    onColumnResized: (e) => { if (e.finished) _saveColState(GK, receiptsGridApi); },
    onColumnMoved: () => _saveColState(GK, receiptsGridApi),
    onModelUpdated: () => {
      _recalcReceiptsGroupTotals();
      _recalcReceiptsSummary();
    },
  });
  _restoreColState(GK, receiptsGridApi);
}

// ── API 호출: 거래처 ──────────────────────────────────────────
async function submitNew() {
  const name = document.getElementById('new-customer-name').value.trim();
  if (!name) { alert('거래처명을 입력하세요.'); return; }
  const res = await fetch('/api/v1/customers', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (res.ok) {
    document.getElementById('modal-add').close();
    await loadData();
  } else {
    const body = await res.json().catch(() => null);
    alert(body?.detail || '등록에 실패했습니다.');
  }
}

async function saveInfo() {
  if (!selectedCustomerId) return;
  const name = document.getElementById('info-name').value.trim();
  if (!name) { showToast('거래처명을 입력하세요.', 'error'); return; }
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name,
      business_no: document.getElementById('info-business-no').value.trim() || null,
      notes: document.getElementById('info-notes').value.trim() || null,
    }),
  });
  if (res.ok) {
    await loadData();
    const cust = allCustomers.find(d => d.id === selectedCustomerId);
    if (cust) {
      renderCustomerInfo(cust);
      document.getElementById('detail-name').textContent = cust.name;
    }
    showToast('거래처 정보가 수정되었습니다.');
  } else {
    const body = await res.json().catch(() => null);
    showToast(body?.detail || '저장에 실패했습니다.', 'error');
  }
}

async function deleteCustomer() {
  if (!selectedCustomerId) { alert('삭제할 거래처를 선택하세요.'); return; }
  const cust = allCustomers.find(d => d.id === selectedCustomerId);
  const name = cust ? cust.name : '';
  if (!confirm(`"${name}" 거래처를 삭제하시겠습니까?`)) return;
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}`, { method: 'DELETE' });
  if (res.ok) {
    selectedCustomerId = null;
    hideDetail();
    await loadData();
  } else if (res.status === 403) {
    const body = await res.json().catch(() => null);
    alert(body?.detail || '권한이 없습니다. 삭제는 관리자만 가능합니다.');
  } else {
    const body = await res.json().catch(() => null);
    alert(body?.detail || '삭제에 실패했습니다.');
  }
}

// ── API 호출: 마스터 담당자 ──────────────────────────────────
function openAddMasterContact() {
  if (!selectedCustomerId) return;
  document.getElementById('new-mc-name').value = '';
  document.getElementById('new-mc-phone').value = '';
  document.getElementById('new-mc-email').value = '';
  document.getElementById('new-mc-default').checked = false;
  document.querySelectorAll('#new-mc-roles input[type="checkbox"]').forEach(cb => { cb.checked = false; });
  document.getElementById('modal-add-master-contact').showModal();
}

async function submitNewMasterContact() {
  const name = document.getElementById('new-mc-name').value.trim();
  if (!name) { alert('이름을 입력하세요.'); return; }

  const checkedRoles = [];
  const isDefault = document.getElementById('new-mc-default').checked;
  document.querySelectorAll('#new-mc-roles input[type="checkbox"]:checked').forEach(cb => {
    checkedRoles.push({ role_type: cb.value, is_default: isDefault });
  });
  if (checkedRoles.length === 0) { alert('최소 1개 이상의 역할을 선택하세요.'); return; }

  const payload = {
    name,
    phone: document.getElementById('new-mc-phone').value.trim() || null,
    email: document.getElementById('new-mc-email').value.trim() || null,
    roles: checkedRoles,
  };
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}/contacts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    document.getElementById('modal-add-master-contact').close();
    loadedTabs['contacts'] = false;
    loadedTabs['contacts'] = true;
    loadContactsTab();
  } else {
    const body = await res.json().catch(() => null);
    alert(body?.detail || '담당자 등록에 실패했습니다.');
  }
}

async function deleteMasterContact(contactId, contactName) {
  if (!confirm(`${contactName} 담당자를 삭제하시겠습니까?`)) return;
  const res = await fetch(`/api/v1/customers/contacts/${contactId}`, { method: 'DELETE' });
  if (res.ok) {
    loadedTabs['contacts'] = false;
    loadedTabs['contacts'] = true;
    loadContactsTab();
  } else {
    alert('삭제에 실패했습니다.');
  }
}

// ── 마스터 담당자 수정 ──────────────────────────────────────
function openEditMasterContact(contactId) {
  const mc = masterContacts.find(c => c.id === contactId);
  if (!mc) return;
  document.getElementById('edit-mc-id').value = mc.id;
  document.getElementById('edit-mc-name').value = mc.name || '';
  document.getElementById('edit-mc-phone').value = mc.phone || '';
  document.getElementById('edit-mc-email').value = mc.email || '';
  const roles = (mc.roles || []).map(r => r.role_type);
  const hasDefault = (mc.roles || []).some(r => r.is_default);
  document.querySelectorAll('#edit-mc-roles input[type="checkbox"]').forEach(cb => {
    cb.checked = roles.includes(cb.value);
  });
  document.getElementById('edit-mc-default').checked = hasDefault;
  document.getElementById('modal-edit-master-contact').showModal();
}

async function submitEditMasterContact() {
  const contactId = document.getElementById('edit-mc-id').value;
  const name = document.getElementById('edit-mc-name').value.trim();
  if (!name) { alert('이름을 입력하세요.'); return; }

  const checkedRoles = [];
  const isDefault = document.getElementById('edit-mc-default').checked;
  document.querySelectorAll('#edit-mc-roles input[type="checkbox"]:checked').forEach(cb => {
    checkedRoles.push({ role_type: cb.value, is_default: isDefault });
  });
  if (checkedRoles.length === 0) { alert('최소 1개 이상의 역할을 선택하세요.'); return; }

  const payload = {
    name,
    phone: document.getElementById('edit-mc-phone').value.trim() || null,
    email: document.getElementById('edit-mc-email').value.trim() || null,
    roles: checkedRoles,
  };
  const res = await fetch(`/api/v1/customers/contacts/${contactId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    document.getElementById('modal-edit-master-contact').close();
    loadedTabs['contacts'] = false;
    loadedTabs['contacts'] = true;
    loadContactsTab();
  } else {
    const body = await res.json().catch(() => null);
    alert(body?.detail || '담당자 수정에 실패했습니다.');
  }
}

// ── 스플리터 드래그 리사이즈 ──────────────────────────────────
const SPLITTER_KEY = 'cust_splitter_width';
const CUSTOMER_PANEL_RULE_SELECTOR = '.customers-layout .cust-list-panel';

function _setCustomerPanelWidth(widthPx) {
  const width = `${Math.round(widthPx)}px`;
  const styleId = 'customer-panel-width-style';
  let styleEl = document.getElementById(styleId);
  if (!styleEl) {
    styleEl = document.createElement('style');
    styleEl.id = styleId;
    document.head.appendChild(styleEl);
  }
  styleEl.textContent = `${CUSTOMER_PANEL_RULE_SELECTOR} { width: ${width}; }`;
}

function _initSplitter() {
  const splitter = document.getElementById('cust-splitter');
  const panel = document.querySelector('.cust-list-panel');

  const saved = localStorage.getItem(SPLITTER_KEY);
  if (saved) _setCustomerPanelWidth(Number(saved));

  let startX, startW;

  splitter.addEventListener('mousedown', (e) => {
    e.preventDefault();
    startX = e.clientX;
    startW = panel.getBoundingClientRect().width;
    splitter.classList.add('dragging');
    document.body.classList.add('col-resizing');

    const onMove = (ev) => {
      const newW = Math.max(180, Math.min(startW + ev.clientX - startX, window.innerWidth * 0.5));
      _setCustomerPanelWidth(newW);
    };
    const onUp = () => {
      splitter.classList.remove('dragging');
      document.body.classList.remove('col-resizing');
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onUp);
      localStorage.setItem(SPLITTER_KEY, Math.round(panel.getBoundingClientRect().width));
      if (gridApi) gridApi.sizeColumnsToFit();
    };
    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onUp);
  });
}
