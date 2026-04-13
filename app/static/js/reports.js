// ═══ 보고서 페이지 ═══════════════════════════════════════════════

const RPT_FILTER_KEY = 'reports_filter_state';
const RPT_TAB_KEY = 'reports_tab';
const FA_COL_STATE_KEY = 'reports_fa_col_state_v1';
const AR_COL_STATE_KEY = 'reports_ar_col_state_v1';

let faGridApi = null;   // Forecast vs Actual AG Grid
let arGridApi = null;   // 미수 현황 AG Grid
let allContracts = [];      // 매입매출관리 사업 목록
let currentPnlContractId = null;
let currentTab = localStorage.getItem(RPT_TAB_KEY) || 'summary';

// ── 초기화 ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
  await loadTermLabels();
  applyTermLabels();
  initDateDefaults();
  await populateContractTypeCheckboxes('#rpt-drop-type .chk-drop-menu');
  await initFilters();
  restoreRptFilterState();
  initTabs();
  restoreTab();
  initContractPnl();
  loadCurrentTab();
});

function initDateDefaults() {
  const now = new Date();
  const y = now.getFullYear();
  document.getElementById('rpt-date-from').value = `${y}-01`;
  document.getElementById('rpt-date-to').value = `${y}-12`;
}

async function initFilters() {
  const users = await fetch(withRootPath('/api/v1/users')).then(r => r.json());
  const depts = [...new Set(users.map(u => u.department).filter(Boolean))].sort();
  const deptMenu = document.querySelector('#rpt-drop-dept .chk-drop-menu');
  deptMenu.innerHTML = depts.map(d => `<label><input type="checkbox" value="${escapeHtml(d)}"> ${escapeHtml(d)}</label>`).join('');

  const ownerMenu = document.querySelector('#rpt-drop-owner .chk-drop-menu');
  ownerMenu.innerHTML = users.filter(u => u.is_active).sort((a, b) => a.name.localeCompare(b.name))
    .map(u => `<label><input type="checkbox" value="${u.id}"> ${escapeHtml(u.name)}</label>`).join('');

  initDropdownToggles();

  document.getElementById('btn-rpt-search').addEventListener('click', loadCurrentTab);
  document.getElementById('btn-rpt-reset').addEventListener('click', resetFilter);
  document.getElementById('btn-rpt-export').addEventListener('click', exportCurrentTab);
}

function initTabs() {
  document.querySelectorAll('.report-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      activateTab(tab.dataset.tab);
    });
  });
}

/** 탭 활성화 공통 함수 */
function activateTab(tabName) {
  document.querySelectorAll('.report-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.report-tab-content').forEach(c => {
    c.classList.add('is-hidden');
    c.classList.remove('active');
  });
  const tabBtn = document.querySelector(`.report-tab[data-tab="${tabName}"]`);
  if (tabBtn) tabBtn.classList.add('active');
  const target = document.getElementById(`tab-${tabName}`);
  if (target) { target.classList.remove('is-hidden'); target.classList.add('active'); }

  currentTab = tabName;
  localStorage.setItem(RPT_TAB_KEY, currentTab);

  // 매입매출관리 탭은 별도 필터바 사용
  const filterBar = document.getElementById('report-filter-bar');
  currentTab === 'contract-pnl' ? filterBar.classList.add('is-hidden') : filterBar.classList.remove('is-hidden');

  if (currentTab === 'contract-pnl' && allContracts.length === 0) {
    loadContractList();
  } else if (currentTab !== 'contract-pnl') {
    loadCurrentTab();
  }
}

/** 저장된 탭 복원 */
function restoreTab() {
  const saved = localStorage.getItem(RPT_TAB_KEY);
  if (saved && saved !== 'summary') {
    activateTab(saved);
  }
}

// ── 필터 상태 저장/복원 (localStorage) ──────────────────────────

function saveRptFilterState() {
  const state = { drops: {} };
  state.dateFrom = document.getElementById('rpt-date-from').value;
  state.dateTo = document.getElementById('rpt-date-to').value;
  document.querySelectorAll('#report-filter-bar .chk-drop').forEach(drop => {
    if (!drop.id) return;
    state.drops[drop.id] = [...drop.querySelectorAll('input:checked')].map(cb => cb.value);
  });
  localStorage.setItem(RPT_FILTER_KEY, JSON.stringify(state));
}

function restoreRptFilterState() {
  const raw = localStorage.getItem(RPT_FILTER_KEY);
  if (!raw) return;
  try {
    const state = JSON.parse(raw);
    if (state.dateFrom) document.getElementById('rpt-date-from').value = state.dateFrom;
    if (state.dateTo) document.getElementById('rpt-date-to').value = state.dateTo;
    if (state.drops) {
      Object.entries(state.drops).forEach(([dropId, values]) => {
        const drop = document.getElementById(dropId);
        if (!drop) return;
        drop.querySelectorAll('input[type="checkbox"]').forEach(cb => {
          cb.checked = values.includes(cb.value);
        });
        updateDropLabel(drop);
      });
    }
  } catch { /* 잘못된 데이터 무시 */ }
}

// ── 공통 필터 파라미터 ──────────────────────────────────────────

function getFilterParams() {
  const params = new URLSearchParams();
  params.set('date_from', document.getElementById('rpt-date-from').value);
  params.set('date_to', document.getElementById('rpt-date-to').value);
  document.querySelectorAll('#rpt-drop-type input:checked').forEach(cb => params.append('contract_type', cb.value));
  document.querySelectorAll('#rpt-drop-stage input:checked').forEach(cb => params.append('stage', cb.value));
  document.querySelectorAll('#rpt-drop-dept input:checked').forEach(cb => params.append('department', cb.value));
  document.querySelectorAll('#rpt-drop-owner input:checked').forEach(cb => params.append('owner_id', cb.value));
  return params;
}

function resetFilter() {
  initDateDefaults();
  document.querySelectorAll('#report-filter-bar input[type="checkbox"]').forEach(cb => { cb.checked = false; });
  document.querySelectorAll('#report-filter-bar .chk-drop').forEach(drop => updateDropLabel(drop));
  localStorage.removeItem(RPT_FILTER_KEY);
  loadCurrentTab();
}

function loadCurrentTab() {
  saveRptFilterState();
  if (currentTab === 'summary') loadSummary();
  else if (currentTab === 'forecast-actual') loadFa();
  else if (currentTab === 'receivables') loadAr();
}

function exportCurrentTab() {
  const params = getFilterParams();
  if (currentTab === 'summary') {
    window.location.href = withRootPath(`/api/v1/reports/summary/export?${params}`);
  } else if (currentTab === 'forecast-actual') {
    window.location.href = withRootPath(`/api/v1/reports/forecast-vs-actual/export?${params}`);
  } else if (currentTab === 'receivables') {
    window.location.href = withRootPath(`/api/v1/reports/receivables/export?${params}`);
  }
}

// ═══ 탭 1: 요약 현황 ════════════════════════════════════════════

async function loadSummary() {
  const params = getFilterParams();
  const res = await fetch(withRootPath(`/api/v1/reports/summary?${params}`));
  if (!res.ok) { alert('데이터 조회에 실패했습니다.'); return; }
  const data = await res.json();
  renderKpis(data.kpis);
  renderSummaryTable(data.period_summary, data.kpis);
}

function renderKpis(kpis) {
  const container = document.getElementById('summary-kpis');
  const cards = [
    { label: 'Forecast 매출', value: kpis.forecast_revenue, type: 'number' },
    { label: 'Actual 매출', value: kpis.actual_revenue, type: 'number' },
    { label: '달성률', value: kpis.achievement_rate, type: 'pct' },
    { label: 'GP', value: kpis.gp, type: 'number', sub: kpis.gp_pct != null ? `GP% ${kpis.gp_pct}%` : '' },
    { label: '입금', value: kpis.receipt, type: 'number' },
    { label: '미수금', value: kpis.ar, type: 'number', warn: kpis.ar > 0 },
  ];
  container.innerHTML = cards.map(c => {
    const val = c.type === 'pct'
      ? (c.value != null ? `${c.value}%` : '-')
      : fmt(c.value);
    const warnClass = c.warn ? ' kpi-warn' : '';
    const sub = c.sub ? `<div class="kpi-sub">${c.sub}</div>` : '';
    return `<div class="kpi-card${warnClass}">
      <div class="kpi-label">${c.label}</div>
      <div class="kpi-value">${val}</div>
      ${sub}
    </div>`;
  }).join('');
}

function renderSummaryTable(rows, kpis) {
  const tbody = document.querySelector('#summary-table tbody');
  const tfoot = document.querySelector('#summary-table tfoot');
  tbody.innerHTML = rows.map(r => `<tr>
    <td>${r.month}</td>
    <td class="cell-number">${fmt(r.forecast_revenue)}</td>
    <td class="cell-number">${fmt(r.actual_revenue)}</td>
    <td class="cell-number">${fmt(r.cost)}</td>
    <td class="cell-number">${fmt(r.gp)}</td>
    <td class="cell-number">${r.gp_pct != null ? r.gp_pct + '%' : '-'}</td>
    <td class="cell-number">${fmt(r.receipt)}</td>
    <td class="cell-number ${r.ar > 0 ? 'ar-positive' : ''}">${fmt(r.ar)}</td>
  </tr>`).join('');

  tfoot.innerHTML = `<tr class="row-total">
    <td><strong>합계</strong></td>
    <td class="cell-number"><strong>${fmt(kpis.forecast_revenue)}</strong></td>
    <td class="cell-number"><strong>${fmt(kpis.actual_revenue)}</strong></td>
    <td class="cell-number"><strong>${fmt(kpis.cost)}</strong></td>
    <td class="cell-number"><strong>${fmt(kpis.gp)}</strong></td>
    <td class="cell-number"><strong>${kpis.gp_pct != null ? kpis.gp_pct + '%' : '-'}</strong></td>
    <td class="cell-number"><strong>${fmt(kpis.receipt)}</strong></td>
    <td class="cell-number ${kpis.ar > 0 ? 'ar-positive' : ''}"><strong>${fmt(kpis.ar)}</strong></td>
  </tr>`;
}

// ═══ 탭 2: Forecast vs Actual ═══════════════════════════════════

function initFaGrid() {
  const el = document.getElementById('grid-forecast-actual');
  faGridApi = agGrid.createGrid(el, {
    columnDefs: [
      { field: 'contract_name', headerName: '사업명', width: 280, pinned: 'left',
        cellClass: 'cell-link' },
      { field: 'contract_type', headerName: '사업유형', width: 75 },
      { field: 'owner_name', headerName: '담당', width: 75 },
      { field: 'department', headerName: '부서', width: 85 },
      { field: 'end_partner_name', headerName: getTermLabel('customer', '고객'), width: 130 },
      { field: 'stage', headerName: '단계', width: 90 },
      { field: 'forecast_revenue', headerName: 'Forecast', width: 120, valueFormatter: fmtNumber,
        cellClass: 'cell-number', type: 'numericColumn' },
      { field: 'actual_revenue', headerName: 'Actual', width: 120, valueFormatter: fmtNumber,
        cellClass: 'cell-number', type: 'numericColumn' },
      { field: 'gap_revenue', headerName: 'Gap', width: 110, valueFormatter: fmtNumber,
        type: 'numericColumn',
        cellClass: p => {
          if (!p.value) return 'cell-number';
          return p.value > 0 ? 'cell-number cell-negative' : 'cell-number cell-positive';
        }},
      { field: 'achievement_rate', headerName: '달성률(%)', width: 100,
        valueFormatter: p => p.value != null ? `${p.value}%` : '-',
        cellClass: 'cell-number', type: 'numericColumn' },
      { field: 'gp', headerName: 'GP', width: 110, valueFormatter: fmtNumber,
        cellClass: 'cell-number', type: 'numericColumn' },
      { field: 'gp_pct', headerName: 'GP%', width: 80,
        valueFormatter: p => p.value != null ? `${p.value}%` : '-',
        cellClass: 'cell-number', type: 'numericColumn' },
    ],
    rowData: [],
    defaultColDef: { resizable: true, sortable: true },
    animateRows: false,
    pinnedBottomRowData: [],
    onColumnMoved: () => saveColState(faGridApi, FA_COL_STATE_KEY),
    onColumnResized: (e) => { if (e.finished) saveColState(faGridApi, FA_COL_STATE_KEY); },
    onCellClicked: e => {
      if (e.column.getColId() === 'contract_name' && e.data?.contract_period_id) {
        window.location.href = withRootPath(`/contracts/${e.data.contract_period_id}`);
      }
    },
  });
  // 저장된 컬럼 상태 복원
  const savedFa = JSON.parse(localStorage.getItem(FA_COL_STATE_KEY) || 'null');
  if (savedFa) faGridApi.applyColumnState({ state: savedFa, applyOrder: true });
}

async function loadFa() {
  if (!faGridApi) initFaGrid();
  const params = getFilterParams();
  const res = await fetch(withRootPath(`/api/v1/reports/forecast-vs-actual?${params}`));
  if (!res.ok) { alert('데이터 조회에 실패했습니다.'); return; }
  const data = await res.json();
  faGridApi.setGridOption('rowData', data.rows);
  faGridApi.setGridOption('pinnedBottomRowData', data.totals ? [data.totals] : []);
}

// ═══ 탭 3: 미수 현황 ════════════════════════════════════════════

function initArGrid() {
  const el = document.getElementById('grid-receivables');
  arGridApi = agGrid.createGrid(el, {
    columnDefs: [
      { field: 'contract_name', headerName: '사업명', width: 280, pinned: 'left' },
      { field: 'contract_type', headerName: '사업유형', width: 75 },
      { field: 'owner_name', headerName: '담당', width: 75 },
      { field: 'department', headerName: '부서', width: 85 },
      { field: 'end_partner_name', headerName: getTermLabel('customer', '고객'), width: 130 },
      { field: 'actual_revenue', headerName: '매출 확정', width: 120, valueFormatter: fmtNumber,
        cellClass: 'cell-number', type: 'numericColumn' },
      { field: 'receipt', headerName: '입금', width: 120, valueFormatter: fmtNumber,
        cellClass: 'cell-number', type: 'numericColumn' },
      { field: 'ar', headerName: '미수금', width: 120, valueFormatter: fmtNumber,
        type: 'numericColumn',
        cellClass: p => p.value > 0 ? 'cell-number cell-negative' : 'cell-number' },
      { field: 'ar_rate', headerName: '미수율(%)', width: 100,
        valueFormatter: p => p.value != null ? `${p.value}%` : '-',
        cellClass: 'cell-number', type: 'numericColumn' },
    ],
    rowData: [],
    defaultColDef: { resizable: true, sortable: true },
    animateRows: false,
    pinnedBottomRowData: [],
    onColumnMoved: () => saveColState(arGridApi, AR_COL_STATE_KEY),
    onColumnResized: (e) => { if (e.finished) saveColState(arGridApi, AR_COL_STATE_KEY); },
  });
  // 저장된 컬럼 상태 복원
  const savedAr = JSON.parse(localStorage.getItem(AR_COL_STATE_KEY) || 'null');
  if (savedAr) arGridApi.applyColumnState({ state: savedAr, applyOrder: true });
}

async function loadAr() {
  if (!arGridApi) initArGrid();
  const params = getFilterParams();
  const res = await fetch(withRootPath(`/api/v1/reports/receivables?${params}`));
  if (!res.ok) { alert('데이터 조회에 실패했습니다.'); return; }
  const data = await res.json();
  arGridApi.setGridOption('rowData', data.rows);
  if (data.totals) {
    arGridApi.setGridOption('pinnedBottomRowData', [{
      contract_name: '합계',
      actual_revenue: data.totals.actual_revenue,
      receipt: data.totals.receipt,
      ar: data.totals.ar,
      ar_rate: data.totals.ar_rate,
    }]);
  }
}

// ═══ 탭 4: 매입매출관리 (기존) ═══════════════════════════════════

async function loadContractList() {
  const res = await fetch(withRootPath('/api/v1/ledger/periods'));
  if (!res.ok) return;
  const data = await res.json();
  allContracts = data;

  const dl = document.getElementById('pnl-contract-list');
  const seen = new Set();
  dl.innerHTML = data.filter(d => {
    if (seen.has(d.contract_id)) return false;
    seen.add(d.contract_id);
    return true;
  }).map(d => `<option value="${d.contract_name}" data-contract-id="${d.contract_id}">`).join('');

  const years = [...new Set(data.map(d => d.period_year))].sort();
  const sel = document.getElementById('pnl-year-select');
  sel.innerHTML = '<option value="">전체</option>' + years.map(y => `<option value="${y}">${y}</option>`).join('');
}

function initContractPnl() {
  document.getElementById('btn-pnl-search').addEventListener('click', loadPnlData);
  document.getElementById('btn-pnl-export').addEventListener('click', exportPnl);
}

async function loadPnlData() {
  const searchText = document.getElementById('pnl-contract-search').value.trim();
  if (!searchText) { alert('사업을 선택하세요.'); return; }

  const contract = allContracts.find(d => d.contract_name === searchText);
  if (!contract) { alert('사업을 찾을 수 없습니다. 목록에서 선택하세요.'); return; }

  currentPnlContractId = contract.contract_id;
  const year = document.getElementById('pnl-year-select').value;
  const params = new URLSearchParams();
  if (year) params.set('period_year', year);

  const res = await fetch(withRootPath(`/api/v1/reports/contract-pnl/${contract.contract_id}?${params}`));
  if (!res.ok) { alert('데이터 조회에 실패했습니다.'); return; }
  const data = await res.json();
  renderPnl(data);
}

function exportPnl() {
  if (!currentPnlContractId) { alert('먼저 사업을 조회하세요.'); return; }
  const year = document.getElementById('pnl-year-select').value;
  const params = new URLSearchParams();
  if (year) params.set('period_year', year);
  window.location.href = withRootPath(`/api/v1/reports/contract-pnl/${currentPnlContractId}/export?${params}`);
}

function renderPnl(data) {
  const container = document.getElementById('pnl-content');
  const months = data.months;
  if (months.length === 0) {
    container.innerHTML = '<p class="placeholder-box">해당 기간에 데이터가 없습니다.</p>';
    return;
  }

  const monthHeaders = months.map(m => `<th>${m.slice(0, 7)}</th>`).join('');
  const fmtCell = (v) => v ? fmt(v) : '';
  const fmtPctCell = (v) => v != null ? (v).toFixed(1) + '%' : '';

  function buildRows(rows) {
    return rows.map(r => {
      const cells = months.map(m => {
        const v = r.months[m] || 0;
        return `<td class="cell-number">${fmtCell(v)}</td>`;
      }).join('');
      return `<tr>
        <td>${r.partner_name}</td>
        <td>${r.contact_name || ''}</td>
        <td>${r.contact_phone || ''}</td>
        <td>${r.contact_email || ''}</td>
        ${cells}
        <td class="cell-number cell-total">${fmtCell(r.total)}</td>
      </tr>`;
    }).join('');
  }

  function buildTotalRow(label, totals, cssClass) {
    const cells = months.map(m => `<td class="cell-number ${cssClass}">${fmtCell(totals[m] || 0)}</td>`).join('');
    const grand = Object.values(totals).reduce((a, b) => a + b, 0);
    return `<tr class="${cssClass}"><td colspan="4"><strong>${label}</strong></td>${cells}<td class="cell-number ${cssClass}"><strong>${fmtCell(grand)}</strong></td></tr>`;
  }

  let html = `
    <h3 class="pnl-title">▣ ${data.contract_name}</h3>
    <p class="pnl-subtitle">[단위:원,VAT별도]</p>
    <div class="pnl-table-wrap">
    <table class="pnl-table" id="pnl-pivot-table" tabindex="0">
      <thead>
        <tr>
          <th>거래처명</th><th>담당자</th><th>연락처</th><th>이메일</th>
          ${monthHeaders}
          <th>합계</th>
        </tr>
      </thead>
      <tbody>
        ${buildRows(data.revenue_rows)}
        ${buildTotalRow('[매출] 합계', data.revenue_totals, 'row-subtotal')}
        <tr class="row-spacer"><td colspan="${months.length + 5}"></td></tr>
        ${buildRows(data.cost_rows)}
        ${buildTotalRow('[매입] 합계', data.cost_totals, 'row-subtotal')}
        <tr class="row-spacer"><td colspan="${months.length + 5}"></td></tr>
        <tr class="row-gp">
          <td colspan="4"><strong>GP</strong></td>
          ${months.map(m => `<td class="cell-number">${fmtCell(data.gp_monthly[m] || 0)}</td>`).join('')}
          <td class="cell-number"><strong>${fmtCell(data.grand_gp)}</strong></td>
        </tr>
        <tr class="row-gp">
          <td colspan="4"><strong>GP%</strong></td>
          ${months.map(m => `<td class="cell-number">${fmtPctCell(data.gp_pct_monthly[m])}</td>`).join('')}
          <td class="cell-number"><strong>${fmtPctCell(data.grand_gp_pct)}</strong></td>
        </tr>
        <tr class="row-spacer"><td colspan="${months.length + 5}"></td></tr>
        ${buildRows(data.receipt_rows)}
        ${buildTotalRow('[입금] 합계', data.receipt_totals, 'row-subtotal')}
        <tr class="row-spacer"><td colspan="${months.length + 5}"></td></tr>
        <tr class="row-ar">
          <td colspan="4"><strong>미수금</strong></td>
          ${months.map(m => {
            const v = data.ar_monthly[m] || 0;
            const cls = v > 0 ? 'ar-positive' : '';
            return `<td class="cell-number ${cls}">${fmtCell(v)}</td>`;
          }).join('')}
          <td class="cell-number ${data.grand_ar > 0 ? 'ar-positive' : ''}"><strong>${fmtCell(data.grand_ar)}</strong></td>
        </tr>
      </tbody>
    </table>
    </div>
  `;
  container.innerHTML = html;

  enableTableCopy(document.getElementById('pnl-pivot-table'));
}

// ═══ 다중 셀 복사 ════════════════════════════════════════════════

function enableTableCopy(tableEl) {
  let selecting = false;
  let startCell = null;
  let selectedCells = [];

  function getCellCoords(td) {
    const tr = td.closest('tr');
    if (!tr) return null;
    const rows = [...tableEl.querySelectorAll('tr')];
    const ri = rows.indexOf(tr);
    const cells = [...tr.children];
    const ci = cells.indexOf(td);
    return { row: ri, col: ci };
  }

  function clearSelection() {
    selectedCells.forEach(c => c.classList.remove('cell-selected'));
    selectedCells = [];
  }

  function selectRange(start, end) {
    clearSelection();
    const rows = [...tableEl.querySelectorAll('tr')];
    const minR = Math.min(start.row, end.row);
    const maxR = Math.max(start.row, end.row);
    const minC = Math.min(start.col, end.col);
    const maxC = Math.max(start.col, end.col);

    for (let r = minR; r <= maxR; r++) {
      const cells = rows[r]?.children;
      if (!cells) continue;
      for (let c = minC; c <= maxC; c++) {
        if (cells[c]) {
          cells[c].classList.add('cell-selected');
          selectedCells.push(cells[c]);
        }
      }
    }
  }

  tableEl.addEventListener('mousedown', e => {
    const td = e.target.closest('td, th');
    if (!td) return;
    selecting = true;
    startCell = getCellCoords(td);
    selectRange(startCell, startCell);
    e.preventDefault();
  });

  tableEl.addEventListener('mousemove', e => {
    if (!selecting) return;
    const td = e.target.closest('td, th');
    if (!td) return;
    const coords = getCellCoords(td);
    if (coords) selectRange(startCell, coords);
  });

  document.addEventListener('mouseup', () => { selecting = false; });

  tableEl.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'c' && selectedCells.length > 0) {
      e.preventDefault();
      const rows = [...tableEl.querySelectorAll('tr')];
      const cellsByRow = new Map();
      selectedCells.forEach(cell => {
        const tr = cell.closest('tr');
        const ri = rows.indexOf(tr);
        if (!cellsByRow.has(ri)) cellsByRow.set(ri, []);
        cellsByRow.get(ri).push(cell.textContent.trim());
      });
      const tsv = [...cellsByRow.entries()]
        .sort((a, b) => a[0] - b[0])
        .map(([, vals]) => vals.join('\t'))
        .join('\n');
      navigator.clipboard.writeText(tsv);
    }
  });
}
