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

  // 사업별 담당자 추가
  document.getElementById('btn-add-contract-contact').addEventListener('click', openAddContractContact);
  document.getElementById('btn-dc-cancel').addEventListener('click', () => document.getElementById('modal-add-contract-contact').close());
  document.getElementById('btn-dc-submit').addEventListener('click', submitNewContractContact);

  // 마스터 담당자 등록
  document.getElementById('btn-add-master-contact').addEventListener('click', openAddMasterContact);
  document.getElementById('btn-mc-cancel').addEventListener('click', () => document.getElementById('modal-add-master-contact').close());
  document.getElementById('btn-mc-submit').addEventListener('click', submitNewMasterContact);

  // 탭 전환
  document.getElementById('cust-tabs').addEventListener('click', (e) => {
    const btn = e.target.closest('.cust-tab');
    if (!btn) return;
    switchTab(btn.dataset.tab);
  });

  // 진행중만 필터 토글
  document.getElementById('chk-active-only').addEventListener('change', (e) => {
    activeOnlyFilter = e.target.checked;
    if (contractsGridApi) contractsGridApi.onFilterChanged();
  });

  // 사업별 담당자 - 구분 변경 시 담당자 목록 필터링
  document.getElementById('new-dc-type').addEventListener('change', updateContactDropdown);
});

// ── 탭 전환 ───────────────────────────────────────────────────
function switchTab(tabName) {
  document.querySelectorAll('.cust-tab').forEach(t => t.classList.remove('active'));
  document.querySelector(`.cust-tab[data-tab="${tabName}"]`)?.classList.add('active');
  document.querySelectorAll('.cust-tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + tabName)?.classList.add('active');

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

  document.getElementById('detail-empty').classList.add('hidden');
  document.getElementById('detail-content').classList.remove('hidden');

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
  document.getElementById('cust-info-card').innerHTML = `
    <div class="info-row" id="cust-info-view">
      <span class="info-item"><b>사업자번호</b> ${cust.business_no || '-'}</span>
      <span class="info-item"><b>비고</b> ${cust.notes || '-'}</span>
      <span class="info-item">
        <button class="btn btn-secondary btn-sm" onclick="openEditCustomerInfo()">수정</button>
      </span>
    </div>
    <div class="info-edit-form hidden" id="cust-info-edit">
      <div class="info-edit-row">
        <div class="info-edit-field">
          <label>사업자번호</label>
          <input type="text" id="info-business-no" value="${cust.business_no || ''}">
        </div>
        <div class="info-edit-field">
          <label>비고</label>
          <input type="text" id="info-notes" value="${cust.notes || ''}" class="input-wide">
        </div>
        <div class="info-edit-field info-edit-actions">
          <label>&nbsp;</label>
          <div class="btn-group">
            <button class="btn btn-secondary btn-sm" onclick="cancelEditCustomerInfo()">취소</button>
            <button id="btn-save-info" class="btn btn-primary btn-sm" onclick="saveInfo()">저장</button>
          </div>
        </div>
      </div>
    </div>`;
}

function openEditCustomerInfo() {
  document.getElementById('cust-info-view').classList.add('hidden');
  document.getElementById('cust-info-edit').classList.remove('hidden');
}

function cancelEditCustomerInfo() {
  const cust = allCustomers.find(d => d.id === selectedCustomerId);
  if (cust) renderCustomerInfo(cust);
}

function hideDetail() {
  selectedCustomerId = null;
  document.getElementById('detail-empty').classList.remove('hidden');
  document.getElementById('detail-content').classList.add('hidden');
}

// ══════════════════════════════════════════════════════════════
// 사업현황 탭
// ══════════════════════════════════════════════════════════════
async function loadContractsTab() {
  if (!selectedCustomerId) return;
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}/contracts`);
  contractsData = await res.json();
  relatedContracts = contractsData.contracts || [];

  renderContractsSummary(contractsData.summary);
  renderContractsGrid(relatedContracts);
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
    { field: 'end_customer_name', headerName: 'END고객', width: 110 },
    { field: 'contract_type', headerName: '유형', width: 70 },
    { field: 'stage', headerName: '단계', width: 90,
      cellRenderer: (p) => {
        const v = p.value;
        if (!v) return '';
        const done = p.data.is_all_completed;
        const cls = done ? 'stage-badge completed' : 'stage-badge active';
        return `<span class="${cls}">${v}</span>`;
      },
    },
    { field: 'period_range', headerName: '기간', width: 140 },
    { field: 'revenue_amount', headerName: '매출액', width: 110, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-' },
    { field: 'cost_amount', headerName: '매입액', width: 110, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-' },
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
      return !node.data.is_all_completed;
    },
    onCellClicked: (e) => {
      if (e.column.getColId() === 'contract_name' && e.data?.id) {
        const url = e.data.latest_period_id
          ? `/contracts/${e.data.latest_period_id}`
          : `/contracts/new/${e.data.id}`;
        window.location.href = url;
      }
    },
    onModelUpdated: () => {
      const el = document.getElementById('contracts-filter-empty');
      if (!el) return;
      const displayed = contractsGridApi?.getDisplayedRowCount?.() ?? 0;
      el.classList.toggle('hidden', displayed > 0);
    },
  });
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
    { headerName: '', width: 50, sortable: false, resizable: false,
      cellRenderer: (p) => {
        return `<button class="btn btn-danger btn-xs" onclick="deleteMasterContact(${p.data.id}, '${(p.data.name || '').replace(/'/g, "\\'")}')">삭제</button>`;
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

// ── 사업별 담당자 그리드 (피벗) ──────────────────────────────
function renderContractContactGrid(contacts) {
  // 폴백 적용: 사업별 담당자가 비어있으면 마스터 기본 담당자를 참조
  const defaults = {};
  for (const mc of masterContacts) {
    for (const role of (mc.roles || [])) {
      if (role.is_default && !defaults[role.role_type]) {
        defaults[role.role_type] = mc;
      }
    }
  }

  // 폴백 정보를 _fallback 필드에 저장
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

  // 폴백 cellRenderer 팩토리
  const fallbackRenderer = (prefix, field) => (p) => {
    const val = p.value;
    if (val) return val;
    const fb = p.data._fallback?.[prefix];
    if (fb) return `<span class="cell-fallback">${fb[field] || ''}</span>`;
    return '';
  };

  const DC_AUTO_COLS = ['contract_name','sales_name','sales_phone','sales_email','tax_name','tax_phone','tax_email','ops_name','ops_phone','ops_email'];

  const colDefs = [
    { field: 'contract_name', headerName: '사업명', minWidth: 120,
      cellClass: 'cell-link' },
    { headerName: '영업',
      headerClass: 'col-group-sales',
      children: [
        { field: 'sales_name', headerName: '담당자', width: 80,
          cellRenderer: fallbackRenderer('sales', 'name') },
        { field: 'sales_phone', headerName: '연락처', width: 120,
          cellRenderer: fallbackRenderer('sales', 'phone') },
        { field: 'sales_email', headerName: '이메일', width: 160,
          cellRenderer: fallbackRenderer('sales', 'email') },
      ],
    },
    { headerName: '세금계산서',
      headerClass: 'col-group-tax',
      children: [
        { field: 'tax_name', headerName: '담당자', width: 80,
          cellRenderer: fallbackRenderer('tax', 'name') },
        { field: 'tax_phone', headerName: '연락처', width: 120,
          cellRenderer: fallbackRenderer('tax', 'phone') },
        { field: 'tax_email', headerName: '이메일', width: 160,
          cellRenderer: fallbackRenderer('tax', 'email') },
      ],
    },
    { headerName: '업무',
      headerClass: 'col-group-ops',
      children: [
        { field: 'ops_name', headerName: '담당자', width: 80,
          cellRenderer: fallbackRenderer('ops', 'name') },
        { field: 'ops_phone', headerName: '연락처', width: 120,
          cellRenderer: fallbackRenderer('ops', 'phone') },
        { field: 'ops_email', headerName: '이메일', width: 160,
          cellRenderer: fallbackRenderer('ops', 'email') },
      ],
    },
    { field: 'notes', headerName: '비고', flex: 1, minWidth: 60 },
    { headerName: '', width: 80, sortable: false, resizable: false,
      cellRenderer: (p) => {
        const ids = [p.data.sales_id, p.data.tax_id, p.data.ops_id].filter(Boolean);
        if (!ids.length) return '';
        return ids.map(id =>
          `<button class="btn btn-danger btn-xs btn-cell" onclick="deleteContractContact(${id})">X</button>`
        ).join('');
      },
    },
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
    onCellClicked: (e) => {
      if (e.column.getColId() === 'contract_name' && e.data?.contract_id) {
        window.location.href = `/contracts/${e.data.contract_id}`;
      }
    },
  });
  if (contacts.length > 0) {
    contractContactGridApi.autoSizeColumns(DC_AUTO_COLS);
  }
}

// ══════════════════════════════════════════════════════════════
// 매출·매입 탭
// ══════════════════════════════════════════════════════════════
async function loadFinancialsTab() {
  if (!selectedCustomerId) return;
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}/financials`);
  const data = await res.json();

  renderFinancialsSummary(data.summary);
  renderFinancialsGrid(data.months);
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

function renderFinancialsGrid(months) {
  const el = document.getElementById('grid-financials');
  el.innerHTML = '';
  const colDefs = [
    { field: 'month', headerName: '월', width: 90 },
    { field: 'revenue', headerName: '매출', width: 120, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-' },
    { field: 'cost', headerName: '매입', width: 120, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-' },
    { field: 'gp', headerName: 'GP', width: 120, type: 'numericColumn',
      valueFormatter: p => p.value != null ? fmt(p.value) : '-' },
    { field: 'gp_pct', headerName: 'GP%', flex: 1, type: 'numericColumn',
      valueFormatter: p => p.value != null ? p.value + '%' : '-' },
  ];
  financialsGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: months || [],
    defaultColDef: { resizable: true, sortable: true },
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
  });
}

// ══════════════════════════════════════════════════════════════
// 입금 탭
// ══════════════════════════════════════════════════════════════
async function loadReceiptsTab() {
  if (!selectedCustomerId) return;
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}/receipts`);
  const data = await res.json();

  renderReceiptsSummary(data.summary);
  renderReceiptsGrid(data.receipts);
}

function renderReceiptsSummary(summary) {
  const el = document.getElementById('receipts-summary');
  if (!summary) { el.innerHTML = ''; return; }
  el.innerHTML = `
    <div class="summary-grid">
      <div class="summary-item">
        <div class="summary-label">총 입금</div>
        <div class="summary-value">${fmt(summary.total_receipt)}<span class="unit">원</span></div>
      </div>
      <div class="summary-item ${summary.ar_balance > 0 ? 'warn' : ''}">
        <div class="summary-label">미수금 잔액</div>
        <div class="summary-value">${fmt(summary.ar_balance)}<span class="unit">원</span></div>
      </div>
    </div>`;
}

function renderReceiptsGrid(receipts) {
  const el = document.getElementById('grid-receipts');
  el.innerHTML = '';
  const colDefs = [
    { field: 'receipt_date', headerName: '입금일', width: 100 },
    { field: 'amount', headerName: '금액', width: 120, type: 'numericColumn',
      valueFormatter: p => p.value ? fmt(p.value) : '-' },
    { field: 'contract_name', headerName: '사업명', minWidth: 140,
      cellClass: 'cell-link' },
    { field: 'description', headerName: '적요', flex: 1, minWidth: 100 },
    { field: 'revenue_month', headerName: '귀속월', width: 90 },
  ];
  receiptsGridApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: receipts || [],
    defaultColDef: { resizable: true, sortable: true },
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
    onCellClicked: (e) => {
      if (e.column.getColId() === 'contract_name' && e.data?.contract_id) {
        window.location.href = `/contracts/${e.data.contract_id}`;
      }
    },
  });
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
  const res = await fetch(`/api/v1/customers/${selectedCustomerId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      business_no: document.getElementById('info-business-no').value.trim() || null,
      notes: document.getElementById('info-notes').value.trim() || null,
    }),
  });
  if (res.ok) {
    await loadData();
    const cust = allCustomers.find(d => d.id === selectedCustomerId);
    if (cust) renderCustomerInfo(cust);
  } else {
    alert('저장에 실패했습니다.');
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

// ── API 호출: 사업별 담당자 ──────────────────────────────────

/** 구분(contact_type) 변경 시 해당 역할의 마스터 담당자만 드롭다운에 표시 */
function updateContactDropdown() {
  const contactType = document.getElementById('new-dc-type').value;
  const sel = document.getElementById('new-dc-contact-id');
  // 선택한 역할을 가진 마스터 담당자만 필터링
  const filtered = masterContacts.filter(mc =>
    (mc.roles || []).some(r => r.role_type === contactType)
  );
  sel.innerHTML = filtered.length === 0
    ? '<option value="">해당 역할의 담당자가 없습니다</option>'
    : filtered.map(mc =>
        `<option value="${mc.id}">${mc.name}${mc.phone ? ' (' + mc.phone + ')' : ''}</option>`
      ).join('');
}

function openAddContractContact() {
  if (!selectedCustomerId) return;
  const contracts = relatedContracts.length > 0 ? relatedContracts : (contractsData?.contracts || []);
  if (contracts.length === 0) {
    alert('관련 사업이 없습니다. 사업을 먼저 등록해 주세요.');
    return;
  }
  if (masterContacts.length === 0) {
    alert('기본 담당자가 없습니다. 기본 담당자를 먼저 등록해 주세요.');
    return;
  }
  const sel = document.getElementById('new-dc-contract-id');
  sel.innerHTML = contracts.map(d =>
    `<option value="${d.id}">${d.contract_code ? d.contract_code + ' ' : ''}${d.contract_name}</option>`
  ).join('');
  document.getElementById('new-dc-type').value = '영업';
  document.getElementById('new-dc-rank').value = '정';
  updateContactDropdown();
  document.getElementById('modal-add-contract-contact').showModal();
}

async function submitNewContractContact() {
  const contactId = document.getElementById('new-dc-contact-id').value;
  if (!contactId) { alert('담당자를 선택하세요.'); return; }
  const contractId = document.getElementById('new-dc-contract-id').value;
  const payload = {
    customer_id: selectedCustomerId,
    customer_contact_id: parseInt(contactId, 10),
    contact_type: document.getElementById('new-dc-type').value,
    rank: document.getElementById('new-dc-rank').value,
  };
  const res = await fetch(`/api/v1/contracts/${contractId}/contacts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (res.ok) {
    document.getElementById('modal-add-contract-contact').close();
    loadedTabs['contacts'] = false;
    loadedTabs['contacts'] = true;
    loadContactsTab();
  } else {
    const body = await res.json().catch(() => null);
    alert(body?.detail || '담당자 등록에 실패했습니다.');
  }
}

async function deleteContractContact(contactId) {
  if (!confirm('이 담당자를 삭제하시겠습니까?')) return;
  const res = await fetch(`/api/v1/contract-contacts/${contactId}`, { method: 'DELETE' });
  if (res.ok) {
    loadedTabs['contacts'] = false;
    loadedTabs['contacts'] = true;
    loadContactsTab();
  } else {
    alert('삭제에 실패했습니다.');
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
