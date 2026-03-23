const COL_STATE_KEY = 'my_contracts_col_state_v1';
const FILTER_STATE_KEY = 'my_contracts_filter_state';

let gridApi;
let currentUserId = null;
let columnDefs;

document.addEventListener('DOMContentLoaded', async () => {
  await loadTermLabels();
  applyTermLabels();

  columnDefs = buildContractPeriodColumns({ showOwner: false });
  const gridOptions = buildContractGridOptions({
    columnDefs,
    backPath: '/my-contracts',
    customerInputId: 'filter-customer-text',
    nameInputId: 'filter-name-text',
    onColChange: () => saveColState(gridApi, COL_STATE_KEY),
  });

  const me = await fetch('/api/v1/auth/me').then(r => r.ok ? r.json() : null);
  currentUserId = me?.id ?? null;

  loadCustomerDatalist();
  initEndCustomerPicker();
  initYearDropdown();
  await populateContractTypeCheckboxes('#drop-type .chk-drop-menu');
  await populateContractTypeSelect('add-contract-type');
  initDropdownToggles();

  // 저장된 필터 상태 복원
  restoreFilterState(FILTER_STATE_KEY);

  // "수행중" 토글 초기화
  const chkActive = document.getElementById('chk-active-period');
  if (chkActive) {
    toggleYearDropdowns(!chkActive.checked);
    chkActive.addEventListener('change', () => {
      toggleYearDropdowns(!chkActive.checked);
      loadData();
      loadSummary();
    });
  }

  const el = document.getElementById('grid-my-contracts');
  gridApi = agGrid.createGrid(el, gridOptions);
  loadData();
  loadSummary();
  initColChooser(gridApi, columnDefs, COL_STATE_KEY, () => saveColState(gridApi, COL_STATE_KEY));

  // 텍스트 필터: Enter 시 즉시 필터 적용
  initTextFilter('filter-customer-text', () => { loadData(); loadSummary(); });
  initTextFilter('filter-name-text', () => { loadData(); loadSummary(); });
  document.getElementById('btn-filter').addEventListener('click', () => { loadData(); loadSummary(); });
  document.getElementById('btn-filter-reset').addEventListener('click', () => {
    resetContractFilters(loadData, FILTER_STATE_KEY);
    loadSummary();
  });
  document.getElementById('btn-add').addEventListener('click', () => openContractModal());
  document.getElementById('btn-cancel').addEventListener('click', () => document.getElementById('modal-add').close());
  document.getElementById('btn-submit').addEventListener('click', () => submitContractModal(loadData));
  document.getElementById('btn-delete').addEventListener('click', () => deleteSelectedContracts(gridApi, loadData));
});

async function loadData() {
  const params = new URLSearchParams();
  const chkActive = document.getElementById('chk-active-period');
  if (chkActive && chkActive.checked) {
    const now = new Date();
    const m = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    params.set('active_month', m);
  } else {
    document.querySelectorAll('#drop-calendar-year input:checked').forEach(cb => params.append('calendar_year', cb.value));
    document.querySelectorAll('#drop-period input:checked').forEach(cb => params.append('period_year', cb.value));
  }
  document.querySelectorAll('#drop-type input:checked').forEach(cb => params.append('contract_type', cb.value));
  document.querySelectorAll('#drop-stage input:checked').forEach(cb => params.append('stage', cb.value));
  if (currentUserId) params.set('owner_id', currentUserId);

  saveFilterState(FILTER_STATE_KEY);
  const res = await fetch(`/api/v1/ledger/periods?${params}`);
  const data = await res.json();
  gridApi.setGridOption('rowData', data);
  gridApi.onFilterChanged();
}

// ── 요약 바 ─────────────────────────────────────────────────────
async function loadSummary() {
  const params = new URLSearchParams();
  const chkActive = document.getElementById('chk-active-period');
  if (chkActive && chkActive.checked) {
    const now = new Date();
    const m = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
    params.set('active_month', m);
  } else {
    document.querySelectorAll('#drop-calendar-year input:checked').forEach(cb => params.append('calendar_year', cb.value));
    document.querySelectorAll('#drop-period input:checked').forEach(cb => params.append('period_year', cb.value));
  }
  const res = await fetch(`/api/v1/my-contracts/summary?${params}`);
  if (!res.ok) return;
  const s = await res.json();
  const el = document.getElementById('my-contracts-summary');
  if (!el) return;
  el.classList.remove('is-hidden');
  el.innerHTML = `
    <div class="summary-card"><div class="s-label">진행 사업</div><div class="s-value">${s.contract_count}<span class="s-unit">건</span></div></div>
    <div class="summary-card"><div class="s-label">이번 달 매출</div><div class="s-value">${fmt(s.current_month_revenue)}<span class="s-unit">원</span></div></div>
    <div class="summary-card"><div class="s-label">매출 확정 (누적)</div><div class="s-value">${fmt(s.revenue_confirmed)}<span class="s-unit">원</span></div></div>
    <div class="summary-card highlight"><div class="s-label">GP</div><div class="s-value">${fmt(s.gp)}<span class="s-unit">원</span></div></div>
    <div class="summary-card highlight"><div class="s-label">GP%</div><div class="s-value">${s.gp_pct != null ? s.gp_pct + '%' : '-'}</div></div>
    <div class="summary-card ${s.ar > 0 ? 'warn' : ''}"><div class="s-label">미수금</div><div class="s-value">${fmt(s.ar)}<span class="s-unit">원</span></div></div>
  `;
}
