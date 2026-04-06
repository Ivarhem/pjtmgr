// fmt, fmtPct are provided by utils.js

/** 숫자를 한글 금액 표기로 변환 (예: 120000 → "12만") */
function formatKoreanAmount(n) {
  if (!n || isNaN(n)) return '-';
  n = Math.abs(Math.round(n));
  if (n === 0) return '0원';
  const units = [
    { val: 1_0000_0000, lbl: '억' },
    { val: 1_0000,      lbl: '만' },
  ];
  let result = '';
  for (const { val, lbl } of units) {
    const d = Math.floor(n / val);
    if (d > 0) { result += d + lbl + ' '; n %= val; }
  }
  if (n > 0) result += n;
  return result.trim() + '원';
}

let periodData = null;   // current contract_period
let contractId = null;
let currentContract = null;
let partners = [];
let users = [];           // 담당자 선택용
let allPeriods = [];      // 모든 period 목록
let viewMode = 'period';  // 'period' | 'multi'
let multiSelectMode = false;  // 다중선택 모드 토글
let selectedPeriodIds = new Set();  // 멀티셀렉트: 선택된 period ID 목록
let cachedAllForecasts = null;     // 전체 forecast 캐시 (멀티뷰용)
let _addPeriodMonthManuallyEdited = false;  // 사업기간 수동 편집 여부 추적
// AG Grid API references
let forecastApi, ledgerApi, receiptApi, receiptMatchApi;
let externalTypeFilter = '';
let lastLedger = [];
let lastReceipts = [];
let lastForecastTotals = { sales: 0, gp: 0 };
let lastReceiptTotal = 0;
let fullLedger = [];       // 전체 원장 (멀티뷰 필터용)
let fullReceipts = [];     // 전체 입금 (멀티뷰 필터용)
let fullAllocations = [];  // 전체 배분 (기간 필터용)
let me = null;  // 현재 사용자 정보 (permissions 포함)
// 통합/분리 뷰 모드
// TODO: 통합 보기 기능 방향 결정 필요 — 현재 기본값 분리(off), 토글 UI 숨김 상태.
//       유지할 경우 토글 UI 노출 방식 결정, 불필요하면 관련 코드 제거.
const UNIFIED_VIEW_KEY = 'contract-unified-view';
let unifiedView = localStorage.getItem(UNIFIED_VIEW_KEY) === 'true'; // 기본값: 분리
// 현재 period 완료 여부
function _isPeriodCompleted() { return periodData?.is_completed === true; }

/** 컬럼 정의 배열의 editable을 완료 상태 체크로 래핑 */
function _wrapEditableWithCompleted(colDefs) {
  colDefs.forEach(col => {
    if (col.children) { _wrapEditableWithCompleted(col.children); return; }
    const orig = col.editable;
    if (orig === false || orig === undefined) return;
    col.editable = (p) => {
      if (_isPeriodCompleted()) return false;
      return typeof orig === 'function' ? orig(p) : orig;
    };
  });
  return colDefs;
}

// dirty state tracking
let dirtyForecast = false;
let dirtyLedger = false;
let dirtyReceipt = false;
function isDirty() { return dirtyForecast || dirtyLedger || dirtyReceipt; }
function markCleanAll() { dirtyForecast = false; dirtyLedger = false; dirtyReceipt = false; _updateDirtyIndicators(); }
function _updateDirtyIndicators() {
  const fc = document.querySelector('.btn-save-forecast');
  const lg = document.getElementById('btn-save-ledger');
  const pm = document.getElementById('btn-save-receipt');
  if (fc) fc.textContent = dirtyForecast ? '저장 *' : '저장';
  if (lg) lg.textContent = dirtyLedger ? '저장 *' : '저장';
  if (pm) pm.textContent = dirtyReceipt ? '저장 *' : '저장';
}

document.addEventListener('DOMContentLoaded', async () => {
  await loadTermLabels();
  applyTermLabels();
  me = await fetch('/api/v1/auth/me').then(r => r.ok ? r.json() : null);
  // 뒤로가기 링크: sessionStorage에 저장된 진입 경로 사용
  const backLink = document.getElementById('back-link');
  if (backLink) {
    const backPath = sessionStorage.getItem('contract-back');
    if (backPath === '/my-contracts') {
      backLink.href = '/my-contracts';
      backLink.textContent = '← 내 사업';
    }
  }
  await Promise.all([loadPartners(), loadUsers()]);
  await loadAll();
  setupModals();
  _initPillNav();
  // 날짜 텍스트 입력 blur 시 자동 정규화
  document.querySelectorAll('.date-text-input').forEach(el => {
    el.addEventListener('blur', () => { if (el.value) el.value = _normalizeDate(el.value); });
  });
  initEndPartnerPicker();
  await populateContractTypeSelect('add-contract-type');
  // 공용 Contract 모달 (사업정보 수정)
  const btnCancel = document.getElementById('btn-cancel');
  const btnSubmit = document.getElementById('btn-submit');
  if (btnCancel) btnCancel.addEventListener('click', () => document.getElementById('modal-add').close());
  if (btnSubmit) btnSubmit.addEventListener('click', () => submitContractModal(null, _onContractUpdated));
  document.querySelector('.btn-save-forecast').addEventListener('click', saveForecast);
  document.getElementById('btn-fc-edit-expected').addEventListener('click', openEditExpected);
  document.getElementById('btn-expected-cancel').addEventListener('click', () => document.getElementById('modal-edit-expected').close());
  document.getElementById('btn-expected-apply-save').addEventListener('click', applyEditExpected);
  _initExpectedGpCalc();
  document.getElementById('btn-save-ledger').addEventListener('click', saveLedger);
  document.getElementById('btn-add-receipt').addEventListener('click', () => { _closeDropdowns(); addReceiptRow(true); });
  document.getElementById('btn-add-receipt-bottom').addEventListener('click', () => addReceiptRow(true));
  document.getElementById('btn-from-ledger').addEventListener('click', () => { _closeDropdowns(); openReceiptFromLedger(); });
  document.getElementById('btn-delete-receipt').addEventListener('click', deleteSelectedReceiptRows);
  document.getElementById('btn-save-receipt').addEventListener('click', saveReceipt);
  document.getElementById('btn-receipt-from-ledger-cancel').addEventListener('click', () => document.getElementById('modal-receipt-from-ledger').close());
  document.getElementById('btn-receipt-from-ledger-submit').addEventListener('click', submitReceiptFromLedger);
  document.getElementById('btn-add-ledger').addEventListener('click', () => { _closeDropdowns(); addLedgerRow(true); });
  document.getElementById('btn-add-ledger-bottom').addEventListener('click', () => addLedgerRow(true));
  document.getElementById('btn-delete-ledger').addEventListener('click', deleteSelectedLedgerRows);
  document.getElementById('btn-from-forecast').addEventListener('click', () => { _closeDropdowns(); importFromForecast(); });
  document.getElementById('btn-bulk-confirm').addEventListener('click', bulkConfirmTransactionLines);
  // 드롭다운 토글
  _initDropdowns();
  // 원장 필터
  document.getElementById('filter-ledger-type').addEventListener('change', () => applyLedgerFilter());
  document.getElementById('filter-ledger-status').addEventListener('change', () => applyLedgerFilter());
  document.getElementById('ledger-hide-future').addEventListener('change', () => applyLedgerFilter());
  document.getElementById('btn-ledger-filter').addEventListener('click', () => applyLedgerFilter());
  document.getElementById('btn-ledger-filter-reset').addEventListener('click', resetLedgerFilter);
  initTextFilter('ledger-filter-partner', () => applyLedgerFilter());
  // 입금 필터
  document.getElementById('btn-receipt-filter').addEventListener('click', () => applyReceiptFilter());
  document.getElementById('btn-receipt-filter-reset').addEventListener('click', resetReceiptFilter);
  initTextFilter('receipt-filter-partner', () => applyReceiptFilter());

  // 통합/분리 뷰 토글
  const chkUnified = document.getElementById('chk-unified-view');
  chkUnified.checked = unifiedView;
  chkUnified.addEventListener('change', () => {
    unifiedView = chkUnified.checked;
    localStorage.setItem(UNIFIED_VIEW_KEY, unifiedView);
    applyViewMode();
    showToast(unifiedView ? '통합 보기로 전환했습니다.' : '분리 보기로 전환했습니다.', 'info');
  });

  // 인라인 거래처 등록
  document.getElementById('btn-new-cust-cancel').addEventListener('click', () => document.getElementById('modal-new-partner').close());
  document.getElementById('btn-new-cust-submit').addEventListener('click', _submitNewPartnerInline);

  // 미저장 이탈 경고
  window.addEventListener('beforeunload', (e) => {
    if (isDirty()) { e.preventDefault(); e.returnValue = ''; }
  });

  // Ctrl+S 키보드 단축키: dirty 상태인 섹션 저장
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      if (dirtyForecast) saveForecast();
      if (dirtyLedger) saveLedger();
      if (dirtyReceipt) saveReceipt();
      if (!isDirty()) showToast('변경사항이 없습니다.', 'info');
    }
  });

  document.getElementById('btn-repeat-txn-line').addEventListener('click', () => {
    _closeDropdowns();
    const pd = periodData;
    if (pd?.start_month && pd?.end_month) {
      if (!document.getElementById('repeat-start').value) document.getElementById('repeat-start').value = pd.start_month.slice(0, 7);
      if (!document.getElementById('repeat-end').value) document.getElementById('repeat-end').value = pd.end_month.slice(0, 7);
    } else if (pd?.period_year) {
      if (!document.getElementById('repeat-start').value) document.getElementById('repeat-start').value = `${pd.period_year}-01`;
      if (!document.getElementById('repeat-end').value) document.getElementById('repeat-end').value = `${pd.period_year}-12`;
    }
    // 거래처 select 채우기
    const sel = document.getElementById('repeat-partner');
    sel.innerHTML = '<option value="">-- 선택 --</option>' +
      partners.map(c => `<option value="${c.name}">${c.name}</option>`).join('');
    // Forecast 매입 기준 체크박스 초기화
    const chkFc = document.getElementById('repeat-use-forecast');
    chkFc.checked = false;
    document.getElementById('repeat-amount').disabled = false;
    document.getElementById('modal-repeat').showModal();
  });
});

async function loadAll() {
  // 신규 Contract (Period 없음): INIT_CONTRACT_ID로 진입
  if (CONTRACT_PERIOD_ID === 0 && INIT_CONTRACT_ID > 0) {
    contractId = INIT_CONTRACT_ID;
    const contractRes = await fetch(`/api/v1/contracts/${contractId}`);
    if (!contractRes.ok) { document.getElementById('contract-title').textContent = '로딩 실패'; return; }
    const contract = await contractRes.json();
    currentContract = contract;
    allPeriods = [];
    periodData = null;

    renderHeader(contract, null);
    renderPeriodTabs([]);
    renderGpSummary();
    initForecastGrid([]);
    initLedgerGrid([]);
    initReceiptGrid([]);
    applyViewMode();
    markCleanAll();

    // Period 추가 모달 자동 팝업
    if (sessionStorage.getItem('contract-auto-add-period') === 'true') {
      sessionStorage.removeItem('contract-auto-add-period');
      setTimeout(() => _openAddPeriodModal(), 300);
    }
    return;
  }

  const [res, salesDetailRes] = await Promise.all([
    fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}`),
    fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}/sales-detail`),
  ]);
  if (!res.ok) { document.getElementById('contract-title').textContent = '로딩 실패'; return; }
  periodData = await res.json();
  // Merge sales-detail into periodData
  if (salesDetailRes.ok) {
    const sd = await salesDetailRes.json();
    Object.assign(periodData, sd);
  }
  contractId = periodData.contract_id;

  const [contractRes, periodsRes, forecastRes, ledgerRes, receiptsRes, allocRes] = await Promise.all([
    fetch(`/api/v1/contracts/${contractId}`),
    fetch(`/api/v1/contracts/${contractId}/periods`),
    fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}/forecasts`),
    fetch(`/api/v1/contracts/${contractId}/ledger`),
    fetch(`/api/v1/contracts/${contractId}/receipts`),
    fetch(`/api/v1/contracts/${contractId}/receipt-matches`),
  ]);
  if ([contractRes, periodsRes, forecastRes, ledgerRes, receiptsRes].some(r => !r.ok)) {
    document.getElementById('contract-title').textContent = '데이터 로딩 실패';
    return;
  }
  const contract = await contractRes.json();
  currentContract = contract;
  const periods = await periodsRes.json();
  allPeriods = periods;
  const forecasts = await forecastRes.json();
  const ledger = await ledgerRes.json();
  const receipts = await receiptsRes.json();
  const allocations = allocRes.ok ? await allocRes.json() : [];
  // allocation 맵 구축 (전체 기준 — 입금 컬럼 등에서 사용)
  _buildAllocationMap(allocations);

  // Period 선택을 먼저 설정 (필터링에 필요)
  viewMode = 'period';
  selectedPeriodIds.clear();
  selectedPeriodIds.add(CONTRACT_PERIOD_ID);

  fullLedger = ledger;
  fullReceipts = receipts;
  fullAllocations = allocations;
  const filteredLedger = _filterBySelectedPeriods(ledger);
  const filteredReceipts = _filterBySelectedPeriods(receipts);
  const filteredAllocations = _filterBySelectedPeriods(allocations);
  lastLedger = filteredLedger;
  lastReceipts = filteredReceipts;
  lastReceiptTotal = filteredReceipts.reduce((s, p) => s + (p.amount || 0), 0);
  lastForecastTotals = {
    sales: forecasts.reduce((s, f) => s + (f.revenue_amount || 0), 0),
    gp: forecasts.reduce((s, f) => s + (f.gp_amount || 0), 0),
  };

  renderHeader(contract, periodData);
  renderPeriodTabs(allPeriods);
  renderGpSummary();
  initForecastGrid(forecasts);
  const mergedRows = unifiedView ? _mergeLedgerAndReceipts(filteredLedger, filteredReceipts) : filteredLedger;
  initLedgerGrid(mergedRows);
  initReceiptGrid(filteredReceipts);
  initReceiptMatchGrid(filteredAllocations);
  applyViewMode();

  markCleanAll();

  // 완료된 기간은 편집 버튼 숨김
  if (_isPeriodCompleted()) {
    setElementHidden(document.querySelector('.btn-save-forecast'), true);
    setElementHidden(document.getElementById('btn-fc-edit-expected'), true);
    ['btn-save-ledger', 'btn-add-ledger-bottom', 'btn-delete-ledger',
     'btn-confirm-ledger', 'dropdown-ledger-add', 'btn-bulk-confirm'
    ].forEach(id => setElementHidden(document.getElementById(id), true));
    ['btn-save-receipt', 'btn-add-receipt', 'btn-add-receipt-bottom', 'btn-delete-receipt',
     'dropdown-receipt-add', 'btn-add-receipt-match'
    ].forEach(id => { const el = document.getElementById(id); if (el) setElementHidden(el, true); });
  }

  if (window.location.hash === '#period') {
    window.history.replaceState(null, '', window.location.pathname);
  }
}

// ── 통합/분리 뷰 ──────────────────────────────────────────────
function _receiptToLedgerRow(p) {
  return {
    _receipt_id: p.id,         // 입금 원본 ID
    revenue_month: p.revenue_month || null,
    type: '입금',
    partner_name: p.partner_name || '',
    amount: p.amount || 0,
    date: p.receipt_date || '',
    status: '',                // 입금은 상태 없음
    description: p.description || '',
  };
}

function _mergeLedgerAndReceipts(ledger, receipts) {
  const receiptRows = receipts.map(_receiptToLedgerRow);
  return [...ledger, ...receiptRows];
}

function applyViewMode() {
  const filterReceiptOpt = document.getElementById('filter-type-receipt');
  if (unifiedView) {
    setElementHidden(filterReceiptOpt, false);
    // 원장에 입금 데이터가 아직 없으면 병합
    let hasReceiptRows = false;
    ledgerApi.forEachNode(n => { if (n.data.type === '입금') hasReceiptRows = true; });
    if (!hasReceiptRows && lastReceipts.length > 0) {
      const receiptRows = lastReceipts.map(_receiptToLedgerRow);
      ledgerApi.applyTransaction({ add: receiptRows });
    }
  } else {
    setElementHidden(filterReceiptOpt, true);
    // 입금 타입 필터 선택 중이면 초기화
    if (document.getElementById('filter-ledger-type').value === '입금') {
      document.getElementById('filter-ledger-type').value = '';
    }
    // 원장에서 입금 행 제거
    const receiptRows = [];
    ledgerApi.forEachNode(n => { if (n.data.type === '입금') receiptRows.push(n.data); });
    if (receiptRows.length) ledgerApi.applyTransaction({ remove: receiptRows });
  }
  refreshLedgerSummary();
  ledgerApi.onFilterChanged();
}

async function loadPartners() {
  const res = await fetch('/api/v1/partners');
  partners = await res.json();
  // datalist for partner autocomplete
  const dl = document.getElementById('partner-list');
  if (dl) dl.innerHTML = partners.map(c => `<option value="${c.name}">`).join('');
}

async function loadUsers() {
  const res = await fetch('/api/v1/users');
  if (res.ok) {
    users = await res.json();
    const dl = document.getElementById('user-list');
    dl.innerHTML = users.filter(u => u.is_active).map(u => {
      const label = u.department ? `${u.name} (${u.department})` : u.name;
      return `<option value="${label}">`;
    }).join('');
  }
}

function _userDisplayName(u) {
  return u.department ? `${u.name} (${u.department})` : u.name;
}

function _findUserByDisplay(text) {
  return users.find(u => _userDisplayName(u) === text) || users.find(u => u.name === text);
}

/** 검수/계산서 규칙 텍스트. src = periodData 또는 contract (Period 우선)
 *  형식: "검수일 : 매월 말일 | 계산서 발행 : 당월 말일 (휴일 전)" */
/** 검수/계산서 정보를 개별 info-item HTML 배열로 반환 */
function _invoiceRuleItems(src) {
  const items = [];

  // 검수일
  if (src.inspection_date) {
    items.push(`<span class="info-item"><b>검수일</b> ${src.inspection_date}</span>`);
  } else if (src.inspection_day != null) {
    items.push(`<span class="info-item"><b>검수일</b> 매월 ${src.inspection_day === 0 ? '말일' : src.inspection_day + '일'}</span>`);
  }

  // 계산서 발행 규칙
  const baseParts = [];
  if (src.invoice_month_offset != null) baseParts.push(src.invoice_month_offset === 0 ? '당월' : '익월');
  if (src.invoice_day_type) {
    let dayText = src.invoice_day_type;
    if (src.invoice_day_type === '특정일' && src.invoice_day) dayText = `${src.invoice_day}일`;
    baseParts.push(dayText);
  }
  if (baseParts.length) {
    let text = `<b>계산서 발행</b> ${baseParts.join(' ')}`;
    if (src.invoice_holiday_adjust) text += ` (휴일 ${src.invoice_holiday_adjust})`;
    items.push(`<span class="info-item">${text}</span>`);
  }

  return items;
}

function renderHeader(contract, period) {
  document.getElementById('contract-title').textContent = contract.contract_name;
  document.getElementById('contract-info').innerHTML = `
    <div class="info-row">
      <span class="info-item"><b>사업코드</b> ${contract.contract_code || '-'}</span>
      <span class="info-item"><b>사업유형</b> ${contract.contract_type}</span>
      <span class="info-item"><b>${getTermLabel('customer', '고객')}</b> ${contract.end_partner_name || '-'}</span>
      <span class="info-item">
        <button class="btn btn-secondary btn-sm" onclick="openEditContractInfo()">수정</button>
      </span>
    </div>`;
  renderPeriodInfoSections();
}

/** 검수일 표시 텍스트 */
function _fmtInspection(src) {
  if (src.inspection_date) return src.inspection_date;
  if (src.inspection_day != null) return `매월 ${src.inspection_day === 0 ? '말일' : src.inspection_day + '일'}`;
  return '미설정';
}

/** 계산서 발행 규칙 표시 텍스트 */
function _fmtInvoiceRule(src) {
  const parts = [];
  if (src.invoice_month_offset != null) parts.push(src.invoice_month_offset === 0 ? '당월' : '익월');
  if (src.invoice_day_type) {
    parts.push(src.invoice_day_type === '특정일' && src.invoice_day ? `${src.invoice_day}일` : src.invoice_day_type);
  }
  if (!parts.length) return '미설정';
  let text = parts.join(' ');
  if (src.invoice_holiday_adjust) text += ` (휴일 ${src.invoice_holiday_adjust})`;
  return text;
}

function renderPeriodInfoSections() {
  const container = document.getElementById('period-info-container');
  if (!container) return;
  const html = allPeriods.map(p => {
    const isCurrent = p.id === CONTRACT_PERIOD_ID;
    const collapsed = !isCurrent;
    // 기간: "2025년 01월 ~ 2025년 12월"
    const fmtMonth = m => {
      if (!m) return '';
      const [y, mo] = m.slice(0, 7).split('-');
      return `${y}년 ${mo}월`;
    };
    const range = p.start_month && p.end_month
      ? `${fmtMonth(p.start_month)} ~ ${fmtMonth(p.end_month)}`
      : '-';
    // GP%
    const rev = p.expected_revenue_amount || 0;
    const gp = p.expected_gp_amount || 0;
    const gpPct = rev ? (Math.round(gp / rev * 1000) / 10) : 0;
    const ownerName = p.owner_name || '-';
    const contactsId = `period-contacts-${p.id}`;
    return `
      <div class="period-info-card${collapsed ? ' collapsed' : ''}" data-period-id="${p.id}">
        <div class="period-info-header" onclick="this.parentElement.classList.toggle('collapsed')">
          <span class="period-info-toggle">${collapsed ? '▶' : '▼'}</span>
          <b>${p.period_label}</b>
          <span class="info-item"><b>사업기간</b> ${range}</span>
          <span class="info-item"><b>진행단계</b> <span class="badge badge-${p.stage === '계약완료' ? 'done' : 'progress'}">${p.stage}</span></span>
          <span class="info-item">${p.is_completed ? '<span class="contract-status-badge closed">완료</span>' : '<span class="contract-status-badge active">진행중</span>'}</span>
          <span class="info-item">${p.is_planned ? '<span class="contract-status-badge active">계획사업</span>' : '<span class="contract-status-badge planned-new">수시사업</span>'}</span>
          <span class="period-header-actions">
            <button class="btn btn-xs" onclick="event.stopPropagation(); togglePeriodCompleted(${p.id}, ${!p.is_completed})" title="${p.is_completed ? '진행중으로 변경' : '사업완료 처리'}">${p.is_completed ? '진행중으로 변경' : '사업완료'}</button>
            <button class="btn btn-xs btn-text-danger period-delete-btn" onclick="event.stopPropagation(); deletePeriodById(${p.id}, '${p.period_label}')" title="Period 삭제">삭제</button>
          </span>
        </div>
        <div class="period-info-body">
          <div class="info-row">
            <span class="info-item"><b>담당</b> ${ownerName}</span>
            <span class="info-item"><b>매출처</b> ${p.partner_name || currentContract?.end_partner_name || '-'}</span>
            <span class="info-item"><b>예상 매출</b> ${rev ? fmt(rev) + '원' : '미설정'}</span>
            <span class="info-item"><b>예상 GP</b> ${gp ? fmt(gp) + '원' : '미설정'}</span>
            <span class="info-item"><b>GP%</b> ${rev ? gpPct + '%' : '-'}</span>
          </div>
          <div class="info-row">
            <span class="info-item"><b>검수일</b> ${_fmtInspection(p)}</span>
            <span class="info-item"><b>계산서 발행</b> ${_fmtInvoiceRule(p)}</span>
            ${isCurrent ? `<span class="info-item"><button class="btn btn-secondary btn-sm" onclick="openEditPeriodInfo()">수정</button></span>` : ''}
          </div>
          <div id="${contactsId}" class="contacts-bar is-hidden"></div>
        </div>
      </div>`;
  }).join('');
  container.innerHTML = html;
  // 토글 아이콘 업데이트
  container.querySelectorAll('.period-info-header').forEach(h => {
    h.addEventListener('click', () => {
      const toggle = h.querySelector('.period-info-toggle');
      toggle.textContent = h.parentElement.classList.contains('collapsed') ? '▶' : '▼';
    });
  });
  // 각 Period의 담당자 로드
  allPeriods.forEach(p => loadPeriodContacts(p.id));
}

async function loadPeriodContacts(periodId) {
  const bar = document.getElementById(`period-contacts-${periodId}`);
  if (!bar) return;
  const res = await fetch(`/api/v1/contract-periods/${periodId}/contacts`);
  if (!res.ok) { bar.classList.add('is-hidden'); return; }
  const contacts = await res.json();
  if (!contacts.length) { bar.classList.add('is-hidden'); return; }
  bar.classList.remove('is-hidden');
  bar.innerHTML = '<span class="contact-label">담당자</span>' + contacts.map(c => {
    const roleClass = c.contact_type === '세금계산서' ? 'contact-role tax' : 'contact-role';
    const rankLabel = c.rank === '부' ? '(부)' : '';
    const info = [c.contact_name, c.contact_phone, c.contact_email].filter(Boolean).join(' · ');
    return `<span class="contact-item"><span class="${roleClass}">${c.contact_type}${rankLabel}</span> ${info}</span>`;
  }).join('');
}

async function togglePeriodCompleted(periodId, newValue) {
  const action = newValue ? '사업완료 처리' : '진행중으로 변경';
  if (!await showConfirmDialog(`이 귀속기간을 ${action}하시겠습니까?`, {
    title: '귀속기간 상태 변경',
    confirmText: '진행',
  })) return;

  const res = await fetch(`/api/v1/contract-periods/${periodId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ is_completed: newValue }),
  });
  if (!res.ok) {
    alert('상태 변경에 실패했습니다.');
    return;
  }
  // allPeriods 업데이트 후 리렌더
  const updated = await res.json();
  const idx = allPeriods.findIndex(p => p.id === periodId);
  if (idx >= 0) allPeriods[idx] = updated;
  renderPeriodInfoSections();
}

// ── 기본정보 (Contract) 수정 — 공용 모달 사용 ─────────────────────
function openEditContractInfo() {
  openContractModal(currentContract);
}
function openEditInfo() { openEditContractInfo(); }

/** 공용 모달 수정 완료 후 콜백 */
function _onContractUpdated(updated) {
  currentContract = updated;
  document.getElementById('contract-title').textContent = updated.contract_name;
  renderHeader(updated, periodData);
}

// ── Period 정보 수정 ─────────────────────────────────────────
function openEditPeriodInfo() {
  const period = periodData;
  const contract = currentContract;
  const isMA = contract.contract_type === 'MA';
  const ownerDisplay = period.owner_name
    ? (users.find(u => u.id === period.owner_user_id) ? _userDisplayName(users.find(u => u.id === period.owner_user_id)) : period.owner_name)
    : '';
  const card = document.querySelector(`.period-info-card[data-period-id="${CONTRACT_PERIOD_ID}"]`);
  if (!card) return;
  const body = card.querySelector('.period-info-body');
  body.innerHTML = `
    <form class="info-edit-form" onsubmit="return false">
      <fieldset class="edit-group">
        <legend class="edit-group-title">기본 정보</legend>
        <div class="info-edit-row">
          <label class="info-edit-field">
            <span>담당</span>
            <input type="text" id="edit-owner" value="${ownerDisplay}" list="user-list" placeholder="이름 검색">
          </label>
          <label class="info-edit-field">
            <span>매출처</span>
            <select id="edit-partner">
              <option value="">-- ${getTermLabel('customer', '고객')} 동일 --</option>
              ${partners.map(c => `<option value="${c.id}"${period.partner_id===c.id?' selected':''}>${c.name}</option>`).join('')}
            </select>
          </label>
          <label class="info-edit-field">
            <span>진행단계</span>
            <select id="edit-stage">
              ${['10%','50%','70%','90%','계약완료','실주'].map(v => `<option value="${v}"${period.stage===v?' selected':''}>${v}</option>`).join('')}
            </select>
          </label>
          <label class="info-edit-field chk-inline">
            <input type="checkbox" id="edit-is-planned" ${period.is_planned ? 'checked' : ''}>
            연초 보고 사업
          </label>
        </div>
      </fieldset>
      <fieldset class="edit-group">
        <legend class="edit-group-title">사업 기간</legend>
        <div class="info-edit-row">
          <label class="info-edit-field">
            <span>시작월</span>
            <input type="month" id="edit-start-month" value="${period.start_month ? period.start_month.slice(0,7) : ''}">
          </label>
          <label class="info-edit-field">
            <span>종료월</span>
            <input type="month" id="edit-end-month" value="${period.end_month ? period.end_month.slice(0,7) : ''}">
          </label>
        </div>
      </fieldset>
      <fieldset class="edit-group">
        <legend class="edit-group-title">정산 설정</legend>
        <div class="info-edit-row">
          <label class="info-edit-field${isMA?'':' is-hidden'}" id="edit-inspection-day-wrap">
            <span>검수일 (매월)</span>
            <select id="edit-inspection-day">
              <option value="">미설정</option>
              ${[0,1,5,10,15,20,25].map(d => `<option value="${d}"${period.inspection_day===d?' selected':''}>${d===0?'말일':d+'일'}</option>`).join('')}
            </select>
          </label>
          <label class="info-edit-field${!isMA?'':' is-hidden'}" id="edit-inspection-date-wrap">
            <span>검수일</span>
            <input type="text" id="edit-inspection-date" value="${period.inspection_date||''}" placeholder="YYYY-MM-DD" class="date-text-input">
          </label>
          <label class="info-edit-field">
            <span>발행월</span>
            <select id="edit-invoice-month-offset">
              <option value="">미설정</option>
              <option value="0"${period.invoice_month_offset===0?' selected':''}>당월</option>
              <option value="1"${period.invoice_month_offset===1?' selected':''}>익월</option>
            </select>
          </label>
          <label class="info-edit-field">
            <span>발행일</span>
            <select id="edit-invoice-day-type">
              <option value="">미설정</option>
              ${['1일','말일','특정일'].map(v => `<option value="${v}"${period.invoice_day_type===v?' selected':''}>${v}</option>`).join('')}
            </select>
          </label>
          <label class="info-edit-field${period.invoice_day_type==='특정일'?'':' is-hidden'}" id="edit-invoice-day-wrap">
            <span>발행일(일)</span>
            <input type="number" id="edit-invoice-day" value="${period.invoice_day||''}" min="1" max="31">
          </label>
          <label class="info-edit-field">
            <span>휴일 조정</span>
            <select id="edit-invoice-holiday-adjust">
              <option value="">미설정</option>
              <option value="전"${period.invoice_holiday_adjust==='전'?' selected':''}>전 (앞당김)</option>
              <option value="후"${period.invoice_holiday_adjust==='후'?' selected':''}>후 (순연)</option>
            </select>
          </label>
        </div>
      </fieldset>
      <div class="info-edit-actions">
        <button type="button" class="btn btn-secondary btn-sm" onclick="cancelEditPeriodInfo()">취소</button>
        <button type="button" class="btn btn-primary btn-sm" onclick="savePeriodInfo()">저장</button>
      </div>
    </form>`;
  document.getElementById('edit-invoice-day-type')?.addEventListener('change', (e) => {
    setElementHidden(document.getElementById('edit-invoice-day-wrap'), e.target.value !== '특정일');
  });
}

function cancelEditPeriodInfo() {
  renderPeriodInfoSections();
}
async function savePeriodInfo() {
  const ownerText = document.getElementById('edit-owner').value.trim();
  const ownerUser = ownerText ? _findUserByDisplay(ownerText) : null;
  const ownerUserId = ownerUser ? ownerUser.id : null;
  const stageEl = document.getElementById('edit-stage');

  const inspDayEl = document.getElementById('edit-inspection-day');
  const inspDateEl = document.getElementById('edit-inspection-date');
  const invMonthEl = document.getElementById('edit-invoice-month-offset');
  const invDayTypeEl = document.getElementById('edit-invoice-day-type');
  const invDayEl = document.getElementById('edit-invoice-day');
  const invHolidayEl = document.getElementById('edit-invoice-holiday-adjust');

  const isMA = currentContract.contract_type === 'MA';

  const custEl = document.getElementById('edit-partner');
  const custId = custEl?.value ? parseInt(custEl.value) : null;

  const startMonthEl = document.getElementById('edit-start-month');
  const endMonthEl = document.getElementById('edit-end-month');

  // Common period fields
  const periodBody = {
    start_month: startMonthEl?.value ? startMonthEl.value + '-01' : null,
    end_month: endMonthEl?.value ? endMonthEl.value + '-01' : null,
    owner_user_id: ownerUserId,
    partner_id: custId,
    stage: stageEl ? stageEl.value : undefined,
  };
  const isPlannedEl = document.getElementById('edit-is-planned');
  if (isPlannedEl) periodBody.is_planned = isPlannedEl.checked;

  // Sales-detail fields (inspection/invoice)
  const salesDetailBody = {
    inspection_day: isMA && inspDayEl?.value !== '' ? parseInt(inspDayEl.value) : null,
    inspection_date: !isMA && inspDateEl?.value ? _normalizeDate(inspDateEl.value) : null,
    invoice_month_offset: invMonthEl?.value !== '' ? parseInt(invMonthEl.value) : null,
    invoice_day_type: invDayTypeEl?.value || null,
    invoice_day: invDayEl?.value ? parseInt(invDayEl.value) : null,
    invoice_holiday_adjust: invHolidayEl?.value || null,
  };

  const [res, sdRes] = await Promise.all([
    fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(periodBody),
    }),
    fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}/sales-detail`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(salesDetailBody),
    }),
  ]);
  if (!res.ok || !sdRes.ok) { showToast('저장에 실패했습니다.', 'error'); return; }

  const periodResult = await res.json();
  const salesDetail = await sdRes.json();
  periodData = { ...periodResult, ...salesDetail };

  // allPeriods 업데이트
  const idx = allPeriods.findIndex(p => p.id === CONTRACT_PERIOD_ID);
  if (idx >= 0) {
    allPeriods[idx] = { ...allPeriods[idx], ...periodData };
  }

  renderPeriodInfoSections();
  renderGpSummary();
  showToast('Period 정보가 저장되었습니다.');
}

function _updatePillNavVisibility() {
  const container = document.getElementById('period-tabs');
  const leftNav = document.getElementById('pill-nav-left');
  const rightNav = document.getElementById('pill-nav-right');
  if (!container || !leftNav || !rightNav) return;
  const hasOverflow = container.scrollWidth > container.clientWidth;
  setElementHidden(leftNav, !hasOverflow);
  setElementHidden(rightNav, !hasOverflow);
}

function _initPillNav() {
  const container = document.getElementById('period-tabs');
  const leftNav = document.getElementById('pill-nav-left');
  const rightNav = document.getElementById('pill-nav-right');
  if (!leftNav || !rightNav || !container) return;
  leftNav.addEventListener('click', () => { container.scrollBy({ left: -120, behavior: 'smooth' }); });
  rightNav.addEventListener('click', () => { container.scrollBy({ left: 120, behavior: 'smooth' }); });
}

function renderPeriodTabs(periods) {
  const container = document.getElementById('period-tabs');
  const isAllSelected = selectedPeriodIds.size === allPeriods.length;

  // 다중선택 토글 버튼
  const multiToggle = `<button class="pill-tab pill-tab-multi-toggle${multiSelectMode ? ' selected' : ''}" data-action="multi-toggle">다중선택</button>`;

  // ALL 버튼은 다중선택 모드에서만 표시
  const allBtn = multiSelectMode
    ? `<button class="pill-tab${isAllSelected ? ' selected' : ''}" data-view="all">ALL</button>`
    : '';

  const periodBtns = periods.map(p => {
    const isCurrent = p.id === CONTRACT_PERIOD_ID;
    const isSelected = selectedPeriodIds.has(p.id);
    const classes = ['pill-tab'];
    if (!multiSelectMode && isCurrent && viewMode === 'period') classes.push('active');
    if (multiSelectMode && isSelected) classes.push('selected');
    if (!multiSelectMode && isSelected && selectedPeriodIds.size === 1) classes.push('active');
    return `<button class="${classes.join(' ')}" data-period-id="${p.id}" title="${p.period_label}">${p.period_label}</button>`;
  }).join('');

  container.innerHTML = multiToggle + periodBtns + allBtn;

  // ◀▶ 네비게이션 표시 (탭이 많을 때)
  _updatePillNavVisibility();

  // 다중선택 토글 이벤트
  container.querySelector('[data-action="multi-toggle"]').addEventListener('click', async () => {
    if (isDirty() && !await showConfirmDialog('저장하지 않은 변경 사항이 있습니다. 계속하시겠습니까?', {
      title: '저장되지 않은 변경',
      confirmText: '계속',
    })) return;
    multiSelectMode = !multiSelectMode;
    if (!multiSelectMode) {
      // 다중선택 해제 → 현재 period로 복귀
      selectedPeriodIds.clear();
      selectedPeriodIds.add(CONTRACT_PERIOD_ID);
      switchToPeriodView();
    } else {
      renderPeriodTabs(allPeriods);
    }
  });

  // ALL 버튼 이벤트 (다중선택 모드에서만 존재)
  const allBtnEl = container.querySelector('[data-view="all"]');
  if (allBtnEl) {
    allBtnEl.addEventListener('click', async () => {
      if (isDirty() && !await showConfirmDialog('저장하지 않은 변경 사항이 있습니다. 계속하시겠습니까?', {
        title: '저장되지 않은 변경',
        confirmText: '계속',
      })) return;
      if (isAllSelected) {
        selectedPeriodIds.clear();
        selectedPeriodIds.add(CONTRACT_PERIOD_ID);
        switchToPeriodView();
        multiSelectMode = false;
      } else {
        allPeriods.forEach(p => selectedPeriodIds.add(p.id));
        switchToMultiView();
      }
    });
  }

  container.querySelectorAll('[data-period-id]').forEach(btn => {
    btn.addEventListener('click', async () => {
      const pid = parseInt(btn.dataset.periodId);
      if (isDirty() && !await showConfirmDialog('저장하지 않은 변경 사항이 있습니다. 계속하시겠습니까?', {
        title: '저장되지 않은 변경',
        confirmText: '계속',
      })) return;

      if (multiSelectMode) {
        // 다중선택 모드: 토글 방식
        if (selectedPeriodIds.has(pid)) {
          if (selectedPeriodIds.size <= 1) return;
          selectedPeriodIds.delete(pid);
        } else {
          selectedPeriodIds.add(pid);
        }

        if (selectedPeriodIds.size === 1 && selectedPeriodIds.has(CONTRACT_PERIOD_ID)) {
          switchToPeriodView();
        } else if (selectedPeriodIds.size === 1) {
          const targetId = [...selectedPeriodIds][0];
          window.location.href = `/contracts/${targetId}#period`;
        } else {
          switchToMultiView();
        }
      } else {
        // 단일선택 모드: 해당 period만 선택
        if (pid === CONTRACT_PERIOD_ID) {
          selectedPeriodIds.clear();
          selectedPeriodIds.add(CONTRACT_PERIOD_ID);
          switchToPeriodView();
        } else {
          window.location.href = `/contracts/${pid}#period`;
        }
      }
    });
  });
}

async function _ensureAllForecasts() {
  if (cachedAllForecasts) return cachedAllForecasts;
  const res = await fetch(`/api/v1/contracts/${contractId}/all-forecasts`);
  cachedAllForecasts = res.ok ? await res.json() : [];
  return cachedAllForecasts;
}

/** 선택된 period들의 start_month/end_month 합집합으로 min~max 범위 반환 */
function _getSelectedMonthRange() {
  let minMonth = null, maxMonth = null;
  for (const p of allPeriods) {
    if (!selectedPeriodIds.has(p.id)) continue;
    const s = p.start_month ? p.start_month.slice(0, 7) : null;
    const e = p.end_month ? p.end_month.slice(0, 7) : null;
    if (s && (!minMonth || s < minMonth)) minMonth = s;
    if (e && (!maxMonth || e > maxMonth)) maxMonth = e;
  }
  return { minMonth, maxMonth };
}

/** revenue_month 기반으로 선택된 period 월 범위에 해당하는 행만 필터 */
function _buildAllocationMap(allocations) {
  const allocMap = {};
  let totalAllocated = 0;
  for (const a of allocations) {
    allocMap[a.transaction_line_id] = (allocMap[a.transaction_line_id] || 0) + a.matched_amount;
    totalAllocated += a.matched_amount;
  }
  window._allocationMap = allocMap;
  window._lastAllocatedTotal = totalAllocated;
}

function _filterBySelectedPeriods(rows) {
  const { minMonth, maxMonth } = _getSelectedMonthRange();
  if (!minMonth || !maxMonth) return rows;
  const min = minMonth + '-01';
  const max = maxMonth + '-01';
  return rows.filter(r => {
    // 원장: revenue_month, 입금: revenue_month 또는 receipt_date에서 월 추출
    let m = r.revenue_month;
    if (!m && r.receipt_date) m = r.receipt_date.slice(0, 7) + '-01';
    if (!m) return false;
    return m >= min && m <= max;
  });
}

async function switchToMultiView() {
  viewMode = 'multi';
  renderPeriodTabs(allPeriods);

  // 선택된 period의 forecast만 필터
  const allForecasts = await _ensureAllForecasts();
  const filtered = allForecasts.filter(f => selectedPeriodIds.has(f.contract_period_id));

  lastForecastTotals = {
    sales: filtered.reduce((s, f) => s + (f.revenue_amount || 0), 0),
    gp: filtered.reduce((s, f) => s + (f.gp_amount || 0), 0),
  };

  // 원장/입금도 선택 period 범위로 필터
  const filteredLedger = _filterBySelectedPeriods(fullLedger);
  const filteredReceipts = _filterBySelectedPeriods(fullReceipts);
  lastLedger = filteredLedger;
  lastReceipts = filteredReceipts;
  lastReceiptTotal = filteredReceipts.reduce((s, p) => s + (p.amount || 0), 0);

  renderGpSummary();
  initAllForecastGrid(filtered);

  // 원장/입금/배분 그리드 갱신
  const mergedRows = unifiedView ? _mergeLedgerAndReceipts(filteredLedger, filteredReceipts) : filteredLedger;
  if (ledgerApi) {
    ledgerApi.setGridOption('rowData', mergedRows);
    refreshLedgerSummary();
  }
  if (receiptApi) {
    receiptApi.setGridOption('rowData', filteredReceipts);
    refreshReceiptSummary();
  }
  const filteredAllocations = _filterBySelectedPeriods(fullAllocations);
  if (receiptMatchApi) {
    receiptMatchApi.setGridOption('rowData', filteredAllocations);
    receiptMatchApi.setGridOption('domLayout', filteredAllocations.length > 8 ? 'normal' : 'autoHeight');
    refreshReceiptMatchSummary(filteredAllocations);
  }

  // 멀티뷰에서는 읽기 전용 — 편집 버튼 숨김
  setElementHidden(document.querySelector('.btn-save-forecast'), true);
  setElementHidden(document.getElementById('btn-fc-edit-expected'), true);
  ['btn-save-ledger', 'btn-add-ledger-bottom', 'btn-delete-ledger',
   'btn-confirm-ledger', 'dropdown-ledger-add', 'btn-bulk-confirm'
  ].forEach(id => setElementHidden(document.getElementById(id), true));

  // 헤더 — 기본정보만 표시
  document.getElementById('contract-info').innerHTML = `
    <div class="info-row">
      <span class="info-item"><b>사업코드</b> ${currentContract.contract_code || '-'}</span>
      <span class="info-item"><b>사업유형</b> ${currentContract.contract_type}</span>
      <span class="info-item"><b>${getTermLabel('customer', '고객')}</b> ${currentContract.end_partner_name || '-'}</span>
      <span class="info-item">
        <button class="btn btn-secondary btn-sm" onclick="openEditContractInfo()">수정</button>
      </span>
    </div>`;
  renderPeriodInfoSections();
}

function switchToPeriodView() {
  viewMode = 'period';
  multiSelectMode = false;
  selectedPeriodIds.clear();
  selectedPeriodIds.add(CONTRACT_PERIOD_ID);
  renderPeriodTabs(allPeriods);

  // 편집 버튼 복원 (완료된 기간은 읽기 전용 유지)
  const completed = _isPeriodCompleted();
  setElementHidden(document.querySelector('.btn-save-forecast'), completed);
  setElementHidden(document.getElementById('btn-fc-edit-expected'), completed);
  ['btn-save-ledger', 'btn-add-ledger-bottom', 'btn-delete-ledger',
   'btn-confirm-ledger', 'dropdown-ledger-add', 'btn-bulk-confirm'
  ].forEach(id => setElementHidden(document.getElementById(id), completed));
  // 입금 관련 버튼
  ['btn-save-receipt', 'btn-add-receipt', 'btn-add-receipt-bottom', 'btn-delete-receipt',
   'dropdown-receipt-add', 'btn-add-receipt-match'
  ].forEach(id => { const el = document.getElementById(id); if (el) setElementHidden(el, completed); });

  // 헤더 복원
  renderHeader(currentContract, periodData);

  // 원장/입금/배분을 현재 Period 범위로 필터
  const filteredLedger = _filterBySelectedPeriods(fullLedger);
  const filteredReceipts = _filterBySelectedPeriods(fullReceipts);
  const filteredAllocations = _filterBySelectedPeriods(fullAllocations);
  lastLedger = filteredLedger;
  lastReceipts = filteredReceipts;
  lastReceiptTotal = filteredReceipts.reduce((s, p) => s + (p.amount || 0), 0);
  const mergedRows = unifiedView ? _mergeLedgerAndReceipts(filteredLedger, filteredReceipts) : filteredLedger;
  if (ledgerApi) {
    ledgerApi.setGridOption('rowData', mergedRows);
    refreshLedgerSummary();
  }
  if (receiptApi) {
    receiptApi.setGridOption('rowData', filteredReceipts);
    refreshReceiptSummary();
  }
  if (receiptMatchApi) {
    receiptMatchApi.setGridOption('rowData', filteredAllocations);
    receiptMatchApi.setGridOption('domLayout', filteredAllocations.length > 8 ? 'normal' : 'autoHeight');
    refreshReceiptMatchSummary(filteredAllocations);
  }

  // Forecast 그리드 복원 — 원래 period 데이터로
  fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}/forecasts`)
    .then(r => r.json())
    .then(forecasts => {
      lastForecastTotals = {
        sales: forecasts.reduce((s, f) => s + (f.revenue_amount || 0), 0),
        gp: forecasts.reduce((s, f) => s + (f.gp_amount || 0), 0),
      };
      renderGpSummary();
      initForecastGrid(forecasts);
    });
}

function renderGpSummary() {
  const rows = lastLedger;
  const confirmed = r => r.status === '확정';
  const totalSales = rows.filter(r => r.type === '매출' && confirmed(r)).reduce((s, r) => s + (r.amount || 0), 0);
  const totalCost = rows.filter(r => r.type === '매입' && confirmed(r)).reduce((s, r) => s + (r.amount || 0), 0);
  const gp = totalSales - totalCost;
  const gpPct = totalSales > 0 ? gp / totalSales : null;
  const fc = lastForecastTotals;

  // 미수금 = 도래한 매출확정 - 배분완료 (미래 귀속월 제외)
  const receiptTotal = lastReceiptTotal;
  const allocMap = window._allocationMap || {};
  const now = new Date();
  const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`;
  const arRevenueRows = rows.filter(r => r.type === '매출' && confirmed(r) && r.revenue_month <= currentMonth);
  const arRevenue = arRevenueRows.reduce((s, r) => s + (r.amount || 0), 0);
  const allocatedTotal = arRevenueRows.reduce((s, r) => s + (allocMap[r.transaction_line_id] || 0), 0);
  const ar = arRevenue - allocatedTotal;

  document.getElementById('gp-summary').innerHTML = `
    <div class="summary-grid">
      <div class="summary-item forecast"><div class="summary-label">예상 매출 (Forecast)</div><div class="summary-value">${fmt(fc.sales)}<span class="unit">원</span></div></div>
      <div class="summary-item forecast"><div class="summary-label">예상 GP (Forecast)</div><div class="summary-value">${fmt(fc.gp)}<span class="unit">원</span></div></div>
      <div class="summary-item"><div class="summary-label">매출 확정</div><div class="summary-value">${fmt(totalSales)}<span class="unit">원</span></div></div>
      <div class="summary-item"><div class="summary-label">매입 확정</div><div class="summary-value">${fmt(totalCost)}<span class="unit">원</span></div></div>
      <div class="summary-item highlight"><div class="summary-label">GP</div><div class="summary-value">${fmt(gp)}<span class="unit">원</span></div></div>
      <div class="summary-item highlight"><div class="summary-label">GP%</div><div class="summary-value">${fmtPct(gpPct)}</div></div>
      <div class="summary-item"><div class="summary-label">입금 합계</div><div class="summary-value">${fmt(receiptTotal)}<span class="unit">원</span></div></div>
      <div class="summary-item ${ar > 0 ? 'warn' : ''}"><div class="summary-label">${ar < 0 ? '선수금' : '미수(AR)'}</div><div class="summary-value">${fmt(Math.abs(ar))}<span class="unit">원</span></div></div>
    </div>
    <p class="data-note">※ 확정 기준. 예정 상태는 제외. 미수 = 이번 달까지 도래한 매출확정 - 배분완료. 미래 귀속월은 미수 집계에서 제외됩니다. VAT 별도.</p>`;
}

// ── Forecast Grid ──────────────────────────────────────────────

/** Period의 start/end_month 기반 월 키 목록 반환. 미설정 시 calendar year fallback */
function _getPeriodMonths(pd) {
  pd = pd || periodData;
  if (!pd) {
    const y = new Date().getFullYear();
    return Array.from({ length: 12 }, (_, i) => `${y}-${String(i + 1).padStart(2, '0')}-01`);
  }
  if (pd.start_month && pd.end_month) {
    return _generateMonthRange(pd.start_month.slice(0, 7), pd.end_month.slice(0, 7));
  }
  const y = pd.period_year;
  return Array.from({ length: 12 }, (_, i) => `${y}-${String(i + 1).padStart(2, '0')}-01`);
}

/** 월 키(YYYY-MM-01)에 대한 열 헤더 라벨 생성 */
function _monthColHeader(key, months) {
  const m = parseInt(key.slice(5, 7));
  // 여러 연도에 걸치면 연도 prefix 표시
  const years = new Set(months.map(k => k.slice(0, 4)));
  if (years.size > 1) return `${key.slice(2, 4)}/${m}월`;
  return `${m}월`;
}

function initForecastGrid(forecasts) {
  const forecastMap = {};
  forecasts.forEach(f => { forecastMap[f.forecast_month] = f; });

  const months = _getPeriodMonths();

  // 행: 예상 매출, 예상 GP / 열: 사업기간 월 + 합계
  const salesRow = { _rowType: 'sales', label: '예상 매출(원)' };
  const gpRow = { _rowType: 'gp', label: '예상 GP(원)' };
  months.forEach(key => {
    const f = forecastMap[key] || {};
    salesRow[key] = f.revenue_amount || 0;
    gpRow[key] = f.gp_amount || 0;
  });
  salesRow._total = months.reduce((s, k) => s + (salesRow[k] || 0), 0);
  gpRow._total = months.reduce((s, k) => s + (gpRow[k] || 0), 0);

  // 연도별 그룹 컬럼 생성 (여러 연도에 걸치는 경우 그룹 헤더 사용)
  const years = [...new Set(months.map(m => parseInt(m.slice(0, 4))))];
  const useFlex = months.length <= 12;
  const monthColBase = { editable: () => !_isPeriodCompleted(), type: 'numericColumn',
    valueParser: p => Math.max(0, parseInt(String(p.newValue).replace(/,/g, '')) || 0),
    valueFormatter: p => p.value > 0 ? fmt(p.value) : '-',
  };
  const monthColSize = useFlex ? { flex: 1, minWidth: 80 } : { width: 90 };
  const monthColDefs = years.length > 1
    ? years.map(year => {
        const yearMonths = months.filter(m => m.startsWith(`${year}-`));
        return {
          headerName: `${year}년`,
          children: yearMonths.map(key => ({
            field: key, headerName: `${parseInt(key.slice(5, 7))}월`,
            ...monthColBase, ...monthColSize,
          })),
        };
      })
    : months.map(key => ({
        field: key, headerName: `${parseInt(key.slice(5, 7))}월`,
        ...monthColBase, ...(useFlex ? { flex: 1, minWidth: 80 } : { width: 100 }),
      }));

  const colDefs = [
    { field: 'label', headerName: '', pinned: 'left', width: 110, editable: false,
      cellClass: 'cell-label-strong' },
    ...monthColDefs,
    { field: '_total', headerName: '합계', editable: false, type: 'numericColumn', width: 130, pinned: 'right',
      valueFormatter: p => p.value > 0 ? fmt(p.value) : '-',
      cellClass: 'cell-total' },
  ];

  const el = document.getElementById('grid-forecast');
  el.innerHTML = '';
  forecastApi = agGrid.createGrid(el, {
    columnDefs: _wrapEditableWithCompleted(colDefs),
    rowData: [salesRow, gpRow],
    defaultColDef: { resizable: true, sortable: false },
    getRowClass: p => p.data?._rowType === 'sales' ? 'forecast-row-sales' : 'forecast-row-gp',
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
    singleClickEdit: true,
    stopEditingWhenCellsLoseFocus: true,
    onCellValueChanged: () => { dirtyForecast = true; _updateDirtyIndicators(); updateForecastTotals(); },
  });

  addPasteHandler(el, forecastApi, months);
}

function updateForecastTotals() {
  const months = _getPeriodMonths();
  let salesRow = null, gpRow = null;
  const nodes = [];
  forecastApi.forEachNode(n => { nodes.push(n); });
  nodes.forEach(node => {
    node.data._total = months.reduce((s, k) => s + (node.data[k] || 0), 0);
    forecastApi.refreshCells({ rowNodes: [node], columns: ['_total'] });
    if (node.data._rowType === 'sales') salesRow = node.data;
    if (node.data._rowType === 'gp') gpRow = node.data;
  });
  lastForecastTotals = {
    sales: salesRow ? months.reduce((s, k) => s + (salesRow[k] || 0), 0) : lastForecastTotals.sales,
    gp: gpRow ? months.reduce((s, k) => s + (gpRow[k] || 0), 0) : lastForecastTotals.gp,
  };
  renderGpSummary();
}

// ── 예상매출정보 수정 모달 ─────────────────────────────────────────

function _parseAmount(el) {
  return parseInt(String(el.value).replace(/,/g, '')) || 0;
}
function _formatAmountInput(el) {
  const v = _parseAmount(el);
  if (v > 0) el.value = fmt(v);
  else el.value = '';
}

function _initExpectedGpCalc() {
  const salesEl = document.getElementById('expected-sales-total');
  const pctEl = document.getElementById('expected-gp-pct');
  const gpEl = document.getElementById('expected-gp-total');
  let updating = false;

  salesEl.addEventListener('blur', () => _formatAmountInput(salesEl));
  gpEl.addEventListener('blur', () => _formatAmountInput(gpEl));

  function recalcGp() {
    if (updating) return;
    updating = true;
    const sales = _parseAmount(salesEl);
    const pct = parseFloat(pctEl.value) || 0;
    const gpVal = Math.round(sales * pct / 100);
    gpEl.value = gpVal > 0 ? fmt(gpVal) : '';
    updating = false;
  }
  function recalcPct() {
    if (updating) return;
    updating = true;
    const sales = _parseAmount(salesEl);
    const gp = _parseAmount(gpEl);
    if (sales > 0) pctEl.value = (gp / sales * 100).toFixed(1);
    else pctEl.value = '';
    updating = false;
  }

  salesEl.addEventListener('input', recalcGp);
  pctEl.addEventListener('input', recalcGp);
  gpEl.addEventListener('input', recalcPct);
}

function _generateMonthRange(start, end) {
  // start/end: YYYY-MM (from <input type="month">)
  if (!start || !end || start > end) return [];
  const [sy, sm] = start.split('-').map(Number);
  const [ey, em] = end.split('-').map(Number);
  const months = [];
  let y = sy, m = sm;
  while (y < ey || (y === ey && m <= em)) {
    months.push(`${y}-${String(m).padStart(2, '0')}-01`);
    m++;
    if (m > 12) { m = 1; y++; }
  }
  return months;
}

function _distributeAmounts(contractType, months, salesTotal, gpTotal) {
  if (!months.length) return [];
  const result = months.map(m => ({ month: m, sales: 0, gp: 0 }));
  const count = months.length;

  // 모든 계약유형에 대해 균등 배분 (나머지는 마지막 달에 합산)
  const perSales = Math.floor(salesTotal / count);
  const perGp = Math.floor(gpTotal / count);
  result.forEach((r, i) => {
    r.sales = perSales + (i === count - 1 ? salesTotal - perSales * count : 0);
    r.gp = perGp + (i === count - 1 ? gpTotal - perGp * count : 0);
  });
  return result;
}

async function openEditExpected() {
  if (!currentContract || !periodData) return;
  const period = periodData;
  const modal = document.getElementById('modal-edit-expected');

  const totalSales = period.expected_revenue_amount || 0;
  const totalGp = period.expected_gp_amount || 0;

  const salesEl = document.getElementById('expected-sales-total');
  const pctEl = document.getElementById('expected-gp-pct');
  const gpEl = document.getElementById('expected-gp-total');

  salesEl.value = totalSales > 0 ? fmt(totalSales) : '';
  gpEl.value = totalGp > 0 ? fmt(totalGp) : '';
  if (totalSales > 0) {
    pctEl.value = (totalGp / totalSales * 100).toFixed(1);
  } else {
    const dtypes = await loadContractTypes();
    const dtConf = dtypes.find(d => d.code === currentContract.contract_type);
    pctEl.value = dtConf?.default_gp_pct != null ? dtConf.default_gp_pct : '';
  }

  modal.showModal();
}

async function applyEditExpected() {
  const salesTotal = _parseAmount(document.getElementById('expected-sales-total'));
  const gpTotal = _parseAmount(document.getElementById('expected-gp-total'));

  if (salesTotal <= 0) {
    showToast('총 매출액을 입력하세요.', 'error');
    return;
  }

  const btn = document.getElementById('btn-expected-apply-save');
  btn.disabled = true;
  btn.textContent = '등록 중...';

  try {
    // Period의 사업기간으로 월 범위 결정
    const months = _getPeriodMonths();
    if (!months.length) {
      showToast('사업기간이 설정되지 않았습니다.', 'error');
      return;
    }
    const dist = _distributeAmounts(currentContract.contract_type, months, salesTotal, gpTotal);

    // 1. Period expected 정보 업데이트 (sales-detail)
    const patchRes = await fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}/sales-detail`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        expected_revenue_amount: salesTotal,
        expected_gp_amount: gpTotal,
      }),
    });
    if (!patchRes.ok) {
      showToast('예상매출정보 저장 실패', 'error');
      return;
    }
    periodData = await patchRes.json();

    // 2. Forecast 그리드에 배분 적용
    const distMap = {};
    dist.forEach(d => { distMap[d.month] = d; });
    const forecastItems = months.map(m => ({
      forecast_month: m,
      revenue_amount: distMap[m]?.sales || 0,
      gp_amount: distMap[m]?.gp || 0,
    }));
    initForecastGrid(forecastItems);

    // 3. 즉시 저장
    try {
      await saveForecast();
    } catch {
      // saveForecast에서 이미 에러 토스트 표시, 여기서는 중단만
      return;
    }

    // 4. allPeriods 갱신
    cachedAllForecasts = null;
    const periodsRes = await fetch(`/api/v1/contracts/${contractId}/periods`);
    if (periodsRes.ok) allPeriods = await periodsRes.json();

    renderPeriodTabs(allPeriods);
    renderHeader(currentContract, periodData);

    document.getElementById('modal-edit-expected').close();
    showToast('예상매출정보가 등록되었습니다.');
  } finally {
    btn.disabled = false;
    btn.textContent = '등록';
  }
}

// ── ALL Forecast Grid (전체 기간 읽기 전용) ────────────────────────
function initAllForecastGrid(allForecasts) {
  const forecastMap = {};
  allForecasts.forEach(f => { forecastMap[f.forecast_month] = f; });

  // 선택된 기간의 월 목록 생성 (각 Period의 start/end 기반)
  const months = [];
  const targetPeriods = viewMode === 'multi'
    ? allPeriods.filter(p => selectedPeriodIds.has(p.id))
    : allPeriods;
  const sorted = [...targetPeriods].sort((a, b) => a.period_year - b.period_year);
  sorted.forEach(p => {
    const pMonths = _getPeriodMonths(p);
    pMonths.forEach(m => { if (!months.includes(m)) months.push(m); });
  });
  months.sort();
  const years = [...new Set(months.map(m => parseInt(m.slice(0, 4))))];

  const salesRow = { _rowType: 'sales', label: '예상 매출(원)' };
  const gpRow = { _rowType: 'gp', label: '예상 GP(원)' };
  months.forEach(key => {
    const f = forecastMap[key] || {};
    salesRow[key] = f.revenue_amount || 0;
    gpRow[key] = f.gp_amount || 0;
  });
  salesRow._total = months.reduce((s, k) => s + (salesRow[k] || 0), 0);
  gpRow._total = months.reduce((s, k) => s + (gpRow[k] || 0), 0);

  // 연도별 그룹 컬럼 생성
  const colSize = months.length <= 12 ? { flex: 1, minWidth: 80 } : { width: 90 };
  const yearGroups = years.map(year => {
    const yearMonths = months.filter(m => m.startsWith(`${year}-`));
    return {
      headerName: `${year}년`,
      children: yearMonths.map(key => {
        const monthNum = parseInt(key.slice(5, 7));
        return {
          field: key,
          headerName: `${monthNum}월`,
          editable: false,
          type: 'numericColumn',
          ...colSize,
          valueFormatter: p => p.value > 0 ? fmt(p.value) : '-',
          cellClass: 'cell-readonly-soft',
        };
      }),
    };
  });

  const colDefs = [
    { field: 'label', headerName: '', pinned: 'left', width: 110, editable: false,
      cellClass: 'cell-label-strong' },
    ...yearGroups,
    { field: '_total', headerName: '합계', editable: false, type: 'numericColumn', width: 130, pinned: 'right',
      valueFormatter: p => p.value > 0 ? fmt(p.value) : '-',
      cellClass: 'cell-total' },
  ];

  const el = document.getElementById('grid-forecast');
  el.innerHTML = '';
  forecastApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: [salesRow, gpRow],
    defaultColDef: { resizable: true, sortable: false },
    getRowClass: p => p.data?._rowType === 'sales' ? 'forecast-row-sales' : 'forecast-row-gp',
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: 'autoHeight',
  });
  if (months.length > 12) {
    forecastApi.autoSizeAllColumns();
  }
}

// ── Ledger Grid (매출/매입 실적 + 통합시 입금) ──────────────────
function _ledgerTypeValues() {
  return ['매출', '매입'];
}

function initLedgerGrid(ledgerRows) {
  const renderTypeBadge = (value) => {
    if (!value) return '';
    const cls = value === '매출' ? 'type-badge-sales'
      : value === '매입' ? 'type-badge-cost'
      : value === '입금' ? 'type-badge-receipt'
      : '';
    return `<span class="type-badge ${cls}">${value}</span>`;
  };
  const renderStatusBadge = (value) => {
    if (!value) return '';
    const cls = value === '확정' ? 'status-badge-confirmed' : 'status-badge-pending';
    return `<span class="status-badge ${cls}">${value}</span>`;
  };
  const colDefs = [
    { headerName: '', field: '_chk', width: 40, pinned: 'left', lockPosition: true,
      headerCheckboxSelection: true, headerCheckboxSelectionFilteredOnly: true, checkboxSelection: true,
      editable: false, sortable: false, resizable: false, suppressMovable: true },
    { field: 'revenue_month', headerName: '귀속월', editable: true, width: 110,
      cellEditor: MonthCellEditor,
      valueFormatter: p => p.value ? p.value.slice(0, 7) : '',
      valueSetter: p => { p.data.revenue_month = toMonthFirst(p.newValue); return true; },
      cellClassRules: { 'cell-missing': p => p.data._missingFields?.includes('revenue_month') } },
    { field: 'type', headerName: '구분', editable: () => !_isPeriodCompleted(), width: 80,
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: () => ({ values: _ledgerTypeValues() }),
      cellClassRules: { 'cell-missing': p => p.data._missingFields?.includes('type') },
      cellRenderer: p => renderTypeBadge(p.value) },
    { field: 'partner_name', headerName: '거래처', editable: true, width: 140,
      cellEditor: PartnerCellEditor,
      cellClassRules: { 'cell-missing': p => p.data._missingFields?.includes('partner_name') } },
    { field: 'amount', headerName: '금액(원)', editable: true, type: 'numericColumn', width: 130,
      valueParser: p => Math.max(0, parseInt(String(p.newValue).replace(/,/g, '')) || 0),
      valueFormatter: p => p.value > 0 ? fmt(p.value) : '',
      tooltipValueGetter: p => p.value >= 10000 ? fmtKoreanCurrency(p.value) : null,
      cellClass: p => p.data?.type === '매출' ? 'cell-revenue' : p.data?.type === '매입' ? 'cell-cost-blue' : '' },
    { field: 'date', headerName: '계산서 발행일', editable: p => p.data.type !== '입금', width: 130,
      cellEditor: DateCellEditor,
      cellClass: 'cell-muted',
      cellClassRules: { 'cell-missing': p => p.data._missingFields?.includes('date') } },
    { field: 'status', headerName: '발행 상태', headerTooltip: '예정 = 미청구, 확정 = 청구완료', width: 100,
      editable: p => p.data.type !== '입금',
      cellEditor: 'agSelectCellEditor',
      cellEditorParams: { values: ['예정', '확정'] },
      cellRenderer: p => p.node.rowPinned ? '' : renderStatusBadge(p.value),
    },
    { field: '_receipt_status', headerName: '입금', width: 160,
      editable: false,
      valueGetter: p => {
        if (p.node.rowPinned || p.data.type !== '매출') return null;
        const amt = p.data.amount || 0;
        if (amt <= 0) return null;
        const alloc = (window._allocationMap || {})[p.data.transaction_line_id] || 0;
        return amt - alloc;
      },
      cellRenderer: p => {
        if (p.value == null) return '';
        if (p.value <= 0) return '<span class="receipt-badge receipt-badge-paid">완료</span>';
        return `<span class="receipt-badge receipt-badge-unpaid">${fmt(p.value)}원 미수</span>`;
      },
    },
    { field: 'description', headerName: '메모', editable: true, flex: 1 },
  ];

  const el = document.getElementById('grid-ledger');
  ledgerApi = agGrid.createGrid(el, {
    columnDefs: _wrapEditableWithCompleted(colDefs),
    rowData: ledgerRows,
    defaultColDef: { resizable: true, sortable: true },
    tooltipShowDelay: 300,
    enableCellTextSelection: true,
    ensureDomOrder: true,
    rowSelection: 'multiple',
    suppressRowClickSelection: true,
    singleClickEdit: true,
    stopEditingWhenCellsLoseFocus: true,
    getRowClass: p => {
      if (p.data.type === '매출') return 'ledger-row-sales';
      if (p.data.type === '매입') return 'ledger-row-cost';
      if (p.data.type === '입금') return 'ledger-row-receipt';
      return '';
    },
    onCellValueChanged: (e) => {
      dirtyLedger = true; _updateDirtyIndicators();
      if (e.column.getColId() === 'type') {
        ledgerApi.redrawRows({ rowNodes: [e.node] });
        // 매입으로 변경 시 같은 귀속월 매출의 계산서발행일 + Forecast 기준 금액 자동 입력
        if (e.newValue === '매입' && e.data.revenue_month) {
          const month = e.data.revenue_month;
          const refreshCols = [];
          // 계산서발행일
          if (!e.data.date) {
            let invoiceDate = null;
            ledgerApi.forEachNode(n => {
              if (!n.rowPinned && n.data.type === '매출' && n.data.revenue_month === month && n.data.date) {
                invoiceDate = n.data.date;
              }
            });
            if (invoiceDate) { e.data.date = invoiceDate; refreshCols.push('date'); }
          }
          // 금액: Forecast 매출 - GP
          if (!e.data.amount) {
            const costMap = _getForecastCostMap();
            const cost = costMap[month] || 0;
            if (cost > 0) { e.data.amount = cost; refreshCols.push('amount'); }
          }
          if (refreshCols.length) e.api.refreshCells({ rowNodes: [e.node], columns: refreshCols });
        }
      }
      refreshLedgerSummary();
    },
    isExternalFilterPresent: () => _hasLedgerFilter(),
    doesExternalFilterPass: node => _passLedgerFilter(node),
    onDragStopped: () => saveColumnOrder('ledger', ledgerApi),
  });
  applyColumnOrder('ledger', ledgerApi);
  addPasteHandlerLedger(el, ledgerApi);
  refreshLedgerSummary();
}

function refreshLedgerSummary() {
  const rows = [];
  ledgerApi.forEachNode(n => { if (!n.rowPinned) rows.push(n.data); });
  const confirmed = r => r.status === '확정';
  const sales = rows.filter(r => r.type === '매출' && confirmed(r)).reduce((s, r) => s + (r.amount || 0), 0);
  const cost = rows.filter(r => r.type === '매입' && confirmed(r)).reduce((s, r) => s + (r.amount || 0), 0);
  const gp = sales - cost;
  const allocMap = window._allocationMap || {};
  const totalAllocated = rows.filter(r => r.type === '매출' && confirmed(r)).reduce((s, r) => s + (allocMap[r.transaction_line_id] || 0), 0);
  const ar = sales - totalAllocated;
  const paid = totalAllocated;

  let html =
    `<span class="summary-entry"><span class="label">매출(확정)</span> <span class="value summary-value-income">${fmt(sales)}원</span></span>` +
    `<span class="summary-entry"><span class="label">매입(확정)</span> <span class="value summary-value-expense">${fmt(cost)}원</span></span>` +
    `<span class="summary-entry"><span class="label">GP</span> <span class="value">${fmt(gp)}원</span></span>` +
    `<span class="summary-entry"><span class="label">입금</span> <span class="value summary-value-receipt">${fmt(paid)}원</span></span>` +
    `<span class="summary-entry"><span class="label">${ar < 0 ? '선수금' : '미수'}</span> <span class="value${ar > 0 ? ' cell-warn' : ''}">${fmt(Math.abs(ar))}원</span></span>`;
  html += `<span class="summary-entry"><span class="label">행 수</span> <span class="value">${rows.length}</span></span>`;
  document.getElementById('ledger-summary-bar').innerHTML = html;
}

async function deleteSelectedLedgerRows() {
  if (!me?.permissions?.can_delete_transaction_line) { alert('관리자만 삭제할 수 있습니다.'); return; }
  const selected = ledgerApi.getSelectedRows();
  if (!selected.length) { alert('삭제할 행을 선택해주세요.'); return; }
  // 입금 매칭이 있는 행 사전 차단
  const allocMap = window._allocationMap || {};
  const matched = selected.filter(r => r.type === '매출' && r.transaction_line_id && (allocMap[r.transaction_line_id] || 0) > 0);
  if (matched.length) {
    alert(`입금 매칭이 존재하는 ${matched.length}건은 삭제할 수 없습니다.\n매칭을 먼저 해제하세요.`);
    return;
  }
  if (!await showConfirmDialog(`선택한 ${selected.length}건을 삭제하시겠습니까?`, {
    title: '실적 행 삭제',
    confirmText: '삭제',
  })) return;
  const toRemove = [];
  for (const row of selected) {
    if (row.type === '입금' && row._receipt_id) {
      const r = await fetch(`/api/v1/receipts/${row._receipt_id}`, { method: 'DELETE' });
      if (!r.ok) { alert(`입금 삭제 실패: ${row.partner_name || ''} ${row.date || ''}`); continue; }
    } else if (row.transaction_line_id) {
      const r = await fetch(`/api/v1/transaction-lines/${row.transaction_line_id}`, { method: 'DELETE' });
      if (!r.ok) {
        const err = await r.json().catch(() => ({}));
        alert(err.detail || `삭제 실패: ${row.partner_name || ''} ${row.revenue_month || ''}`);
        continue;
      }
    }
    toRemove.push(row);
  }
  if (toRemove.length) {
    ledgerApi.applyTransaction({ remove: toRemove });
    refreshLedgerSummary();
    showToast(`${toRemove.length}건이 삭제되었습니다.`);
  }
}

// ── Save handlers ──────────────────────────────────────────────
async function saveForecast() {
  const btn = document.querySelector('.btn-save-forecast');
  btn.disabled = true; btn.textContent = '저장 중...';
  try {
    await _doSaveForecast();
  } catch (e) {
    showToast(e.message || 'Forecast 저장에 실패했습니다.', 'error');
    throw e;
  } finally { btn.disabled = false; _updateDirtyIndicators(); }
}
async function _doSaveForecast() {
  const months = _getPeriodMonths();
  let salesRow = null, gpRow = null;
  forecastApi.forEachNode(n => {
    if (n.data._rowType === 'sales') salesRow = n.data;
    if (n.data._rowType === 'gp') gpRow = n.data;
  });
  // 값이 있는 월만 전송 (0인 월은 서버에서 기존 행 삭제)
  const items = months
    .filter(k => (salesRow?.[k] || 0) !== 0 || (gpRow?.[k] || 0) !== 0)
    .map(k => ({ forecast_month: k, revenue_amount: salesRow?.[k] || 0, gp_amount: gpRow?.[k] || 0 }));
  const res = await fetch(`/api/v1/contract-periods/${CONTRACT_PERIOD_ID}/forecasts`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(items),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Forecast 저장에 실패했습니다.');
  }
  // 저장 성공 후 forecast 합계 갱신 & GP 요약 반영
  cachedAllForecasts = null;  // 멀티뷰 캐시 무효화
  dirtyForecast = false; _updateDirtyIndicators();
  updateForecastTotals();
  showToast('Forecast가 저장되었습니다.');
}

async function saveLedger() {
  const btn = document.getElementById('btn-save-ledger');
  btn.disabled = true; btn.textContent = '저장 중...';
  try { await _doSaveLedger(); } finally { btn.disabled = false; _updateDirtyIndicators(); }
}
async function _doSaveLedger() {
  // 매출 행 중 거래처 미입력 → END 고객 자동 채우기 제안
  const endName = currentContract?.end_partner_name;
  if (endName) {
    const salesNoPartner = [];
    ledgerApi.forEachNode(n => {
      if (n.rowPinned) return;
      const d = n.data;
      if (d.type === '매출' && !d.partner_name && (d.revenue_month || d.amount)) {
        salesNoPartner.push(n);
      }
    });
    if (salesNoPartner.length > 0) {
      const fill = await showConfirmDialog(
        `거래처가 비어있는 매출 ${salesNoPartner.length}건이 있습니다.\n${getTermLabel('customer', '고객')}(${endName})으로 자동 채우시겠습니까?`,
        { title: '거래처 자동 채우기', confirmText: '채우기' }
      );
      if (fill) {
        salesNoPartner.forEach(n => { n.setDataValue('partner_name', endName); });
      }
    }
  }

  // 누락 필드 검증
  const missing = _validateLedgerRows(ledgerApi);
  if (missing.length) {
    _highlightMissing(ledgerApi, missing);
    const first = missing[0].node;
    ledgerApi.ensureNodeVisible(first, 'middle');
    showToast(`필수 필드가 누락된 행이 ${missing.length}건 있습니다. (귀속월, 구분, 거래처, 금액)`, 'error');
    return;
  }
  _clearMissingHighlight(ledgerApi);

  const rows = [];
  ledgerApi.forEachNode(n => { if (!n.rowPinned) rows.push(n.data); });

  // 매출/매입 행과 입금 행 분리
  const txnLineRows = rows.filter(r => r.type === '매출' || r.type === '매입');
  const receiptRows = rows.filter(r => r.type === '입금');

  // 미등록 거래처 검증 (모든 행)
  const allValid = rows.filter(r => r.amount && r.type);
  const unregistered = allValid
    .filter(r => r.partner_name && !findPartnerId(r.partner_name))
    .map(r => r.partner_name);
  if (unregistered.length > 0) {
    alert(`등록되지 않은 거래처가 있습니다: ${[...new Set(unregistered)].join(', ')}\n거래처를 먼저 등록해 주세요.`);
    return;
  }

  // 매출/매입 저장
  const txnLineReqs = txnLineRows.filter(r => r.amount)
    .map(row => {
      const body = {
        revenue_month: toMonthFirst(row.revenue_month),
        line_type: row.type === '매출' ? 'revenue' : 'cost',
        partner_id: findPartnerId(row.partner_name),
        partner_name: row.partner_name || null,
        supply_amount: row.amount || 0,
        invoice_issue_date: row.date || null,
        status: row.status || null,
        description: row.description || null,
      };
      return row.transaction_line_id
        ? fetch(`/api/v1/transaction-lines/${row.transaction_line_id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        : fetch(`/api/v1/contracts/${contractId}/transaction-lines`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    });

  // 입금 저장 (통합 뷰일 때)
  const receiptReqs = receiptRows.filter(r => r.amount)
    .map(row => {
      const body = {
        partner_id: findPartnerId(row.partner_name),
        receipt_date: row.date || null,
        revenue_month: row.revenue_month || null,
        amount: row.amount || 0,
        description: row.description || null,
      };
      return row._receipt_id
        ? fetch(`/api/v1/receipts/${row._receipt_id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        : fetch(`/api/v1/contracts/${contractId}/receipts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    });

  const results = await Promise.all([...txnLineReqs, ...receiptReqs]);
  const failCount = results.filter(r => !r.ok).length;
  if (failCount) showToast(`${failCount}건 저장에 실패했습니다.`, 'error');
  else showToast('원장이 저장되었습니다.');
  dirtyLedger = false; _updateDirtyIndicators();
  await reloadLedger();
}

// ── 부분 재로드 ────────────────────────────────────────────────
async function reloadLedger() {
  const [ledgerRes, partnersRes, receiptsRes, allocRes] = await Promise.all([
    fetch(`/api/v1/contracts/${contractId}/ledger`),
    fetch('/api/v1/partners'),
    fetch(`/api/v1/contracts/${contractId}/receipts`),
    fetch(`/api/v1/contracts/${contractId}/receipt-matches`),
  ]);
  const ledger = await ledgerRes.json();
  partners = await partnersRes.json();
  const receipts = await receiptsRes.json();
  const allocations = allocRes.ok ? await allocRes.json() : [];
  _buildAllocationMap(allocations);
  const _dl = document.getElementById('partner-list');
  if (_dl) _dl.innerHTML = partners.map(c => `<option value="${c.name}">`).join('');
  fullLedger = ledger;
  fullReceipts = receipts;
  fullAllocations = allocations;
  const filteredLedger = _filterBySelectedPeriods(ledger);
  const filteredReceipts = _filterBySelectedPeriods(receipts);
  const filteredAllocations = _filterBySelectedPeriods(allocations);
  lastLedger = filteredLedger;
  lastReceipts = filteredReceipts;
  lastReceiptTotal = filteredReceipts.reduce((s, p) => s + (p.amount || 0), 0);
  // 통합 뷰: 입금을 원장에 병합, 분리 뷰: 원장만
  const mergedRows = unifiedView ? _mergeLedgerAndReceipts(filteredLedger, filteredReceipts) : filteredLedger;
  ledgerApi.setGridOption('rowData', mergedRows);
  refreshLedgerSummary();
  if (receiptApi) {
    receiptApi.setGridOption('rowData', filteredReceipts);
    refreshReceiptSummary();
  }
  // 배분 현황 그리드 갱신
  if (receiptMatchApi) {
    receiptMatchApi.setGridOption('rowData', filteredAllocations);
    receiptMatchApi.setGridOption('domLayout', filteredAllocations.length > 8 ? 'normal' : 'autoHeight');
    refreshReceiptMatchSummary(filteredAllocations);
  } else {
    initReceiptMatchGrid(filteredAllocations);
  }
  renderGpSummary();
}

async function bulkConfirmTransactionLines() {
  const selected = ledgerApi.getSelectedRows();
  let targets;
  let autoMode = false;

  if (selected.length) {
    // 체크박스 선택 대상 우선
    targets = selected.filter(r => r.type !== '입금' && r.status !== '확정');
  } else {
    // 선택 없으면: 발행일이 오늘 이하 + 예정 상태인 행 자동 탐색
    autoMode = true;
    const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
    targets = [];
    ledgerApi.forEachNode(n => {
      if (n.rowPinned) return;
      const d = n.data;
      if (d.type === '입금' || d.status === '확정') return;
      if (d.date && d.date <= today && d.status === '예정') targets.push(d);
    });
  }

  if (!targets.length) {
    showToast(autoMode
      ? '확정 대상이 없습니다. (발행일이 오늘 이전인 예정 행이 없음)'
      : '확정 대상 행이 없습니다. (이미 확정이거나 입금 행)', 'info');
    return;
  }

  const incomplete = targets.filter(r => !r.partner_name || !r.date);
  if (incomplete.length) {
    incomplete.forEach(r => {
      const issues = [];
      if (!r.partner_name) issues.push('partner_name');
      if (!r.date) issues.push('date');
      r._missingFields = issues;
    });
    ledgerApi.refreshCells({ force: true });
    ledgerApi.forEachNode(n => {
      if (n.data._missingFields?.length && !n._scrolled) {
        ledgerApi.ensureNodeVisible(n, 'middle');
        n._scrolled = true;
      }
    });
    showToast(`거래처/발행일 미입력 ${incomplete.length}건이 있습니다. 빨간 셀을 확인해주세요.`, 'error');
    return;
  }

  const msg = autoMode
    ? `발행일이 오늘 이전인 예정 ${targets.length}건을 확정하시겠습니까?`
    : `선택한 ${targets.length}건을 확정하시겠습니까?`;
  if (!await showConfirmDialog(msg, {
    title: '일괄 확정',
    confirmText: '확정',
  })) return;

  _clearMissingHighlight(ledgerApi);
  targets.forEach(r => { r.status = '확정'; });
  ledgerApi.applyTransaction({ update: targets });
  ledgerApi.redrawRows();
  dirtyLedger = true; _updateDirtyIndicators();
  showToast(`${targets.length}건이 확정되었습니다. 저장 버튼을 눌러주세요.`, 'info');
}

function _lastLedgerRowOfType(targetType) {
  let last = null;
  ledgerApi.forEachNode(n => {
    if (!n.rowPinned && n.data.type === targetType) last = n.data;
  });
  return last;
}

function _findOldestEmptyMonth(rowType) {
  // 사업기간 내에서 해당 구분(매출/매입)의 행이 없는 가장 오래된 월 탐색
  const months = _getPeriodMonths();
  if (!months.length || !ledgerApi) return null;
  const existingMonths = new Set();
  ledgerApi.forEachNode(n => {
    if (!n.rowPinned && n.data.type === rowType) existingMonths.add(n.data.revenue_month);
  });
  return months.find(m => !existingMonths.has(m)) || null;
}

function addLedgerRow(scrollToNew, type) {
  const today = new Date();
  const ym = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;
  const rowType = type || '매입';
  const prev = _lastLedgerRowOfType(rowType);
  const emptyMonth = _findOldestEmptyMonth(rowType);
  let newRow;
  if (rowType === '입금') {
    const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
    newRow = {
      revenue_month: prev?.revenue_month || ym,
      type: '입금',
      partner_name: prev?.partner_name || '',
      amount: 0,
      date: dateStr,
      status: '',
      description: '',
    };
  } else {
    const month = emptyMonth || prev?.revenue_month || ym;
    newRow = {
      revenue_month: month,
      type: rowType,
      partner_name: prev?.partner_name || '',
      amount: 0,
      status: '예정',
    };
    // 매입: 같은 귀속월 매출에서 발행일, Forecast에서 금액 자동 입력
    if (rowType === '매입') {
      let salesRow = null;
      ledgerApi.forEachNode(n => {
        if (!n.rowPinned && n.data.type === '매출' && n.data.revenue_month === month) salesRow = n.data;
      });
      if (salesRow?.date) newRow.date = salesRow.date;
      const costMap = _getForecastCostMap();
      if (costMap[month] > 0) newRow.amount = costMap[month];
    }
  }
  const res = ledgerApi.applyTransaction({ add: [newRow] });
  dirtyLedger = true; _updateDirtyIndicators();
  if (scrollToNew && res.add && res.add.length) {
    ledgerApi.ensureNodeVisible(res.add[0], 'bottom');
    res.add[0].setSelected(false);
    setTimeout(() => ledgerApi.setFocusedCell(res.add[0].rowIndex, 'revenue_month'), 50);
  }
}

/** GP 자동 계산 (span + hidden input 동시 업데이트) */
function _updateAddPeriodGp() {
  const sales = parseInt(document.getElementById('add-period-sales').value) || 0;
  const pct = parseFloat(document.getElementById('add-period-gp-pct').value) || 0;
  const gp = sales ? Math.round(sales * pct / 100) : 0;
  document.getElementById('add-period-gp').textContent = gp ? fmt(gp) : '-';
  document.getElementById('add-period-gp-val').value = gp;
}

/** Period 추가 모달 열기 (신규 Contract 진입 시 자동 팝업에도 사용) */
async function _openAddPeriodModal() {
  // ── 기본값 우선순위: 1) 이전 Period → 2) 사업유형 시스템 설정 ──
  const prev = periodData;                                   // 이전 Period (없으면 null)
  const dtypes = await loadContractTypes();
  const dtConf = dtypes.find(d => d.code === currentContract?.contract_type) || {};

  // ── 기본 정보 ──
  const curYear = new Date().getFullYear();
  document.getElementById('add-period-year').value = prev ? prev.period_year + 1 : curYear;

  const stageEl = document.getElementById('add-period-stage');
  if (prev?.stage) stageEl.value = prev.stage;

  // 매출처
  const custSel = document.getElementById('add-period-partner');
  custSel.innerHTML = `<option value="">-- ${getTermLabel('customer', '고객')} 동일 --</option>` +
    partners.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
  const defaultCustId = prev?.partner_id || currentContract?.end_partner_id || '';
  custSel.value = String(defaultCustId);

  // ── 기간 ──
  const prevEnd = prev?.end_month;
  if (prevEnd) {
    const [py, pm] = prevEnd.slice(0, 7).split('-').map(Number);
    const ns = pm === 12 ? `${py + 1}-01` : `${py}-${String(pm + 1).padStart(2, '0')}`;
    const ne = pm === 12 ? `${py + 1}-12` : `${py + 1}-${String(pm).padStart(2, '0')}`;
    document.getElementById('add-period-start').value = ns;
    document.getElementById('add-period-end').value = ne;
  } else {
    document.getElementById('add-period-start').value = `${curYear}-01`;
    document.getElementById('add-period-end').value = `${curYear}-12`;
  }

  // ── 실적 (매출 / GP% / GP) ──
  const prevSales = prev?.expected_revenue_amount || 0;
  const prevGp = prev?.expected_gp_amount || 0;
  document.getElementById('add-period-sales').value = prevSales || '';
  document.getElementById('add-period-sales-kr').textContent = formatKoreanAmount(prevSales);

  let gpPctSource = '';   // 힌트용 출처 추적
  let gpPct;
  if (prevSales) {
    gpPct = Math.round(prevGp / prevSales * 1000) / 10;   // 1순위: 이전 Period 역산
    gpPctSource = 'prev';
  } else if (dtConf.default_gp_pct != null) {
    gpPct = dtConf.default_gp_pct;                         // 2순위: 사업유형 기본값
    gpPctSource = 'system';
  } else {
    gpPct = '';
  }
  document.getElementById('add-period-gp-pct').value = gpPct;
  _updateAddPeriodGp();

  // 안내 문구 (GP% 출처)
  const hintEl = document.getElementById('add-period-hint');
  if (hintEl) {
    if (gpPctSource === 'prev') {
      hintEl.textContent = '* GP%는 이전 기간 실적에서 산출했습니다.';
    } else if (gpPctSource === 'system') {
      hintEl.textContent = `* GP%는 사업유형(${currentContract?.contract_type || ''}) 시스템 설정에서 가져왔습니다.`;
    } else {
      hintEl.textContent = '';
    }
  }

  // ── 정산 설정 (검수 / 세금계산서) ──
  const isMA = ['MA', 'TS'].includes(currentContract?.contract_type);
  setElementHidden(document.getElementById('label-add-period-inspect-day'), !isMA);
  setElementHidden(document.getElementById('label-add-period-inspect-date'), isMA);

  const inspDay = prev?.inspection_day ?? dtConf.default_inspection_day ?? null;
  document.getElementById('add-period-inspect-day').value = inspDay != null ? String(inspDay) : '';
  document.getElementById('add-period-inspect-date').value = prev?.inspection_date ?? '';

  const invMonth = prev?.invoice_month_offset ?? dtConf.default_invoice_month_offset ?? null;
  document.getElementById('add-period-invoice-month').value = invMonth != null ? String(invMonth) : '';

  const invDayType = prev?.invoice_day_type ?? dtConf.default_invoice_day_type ?? '';
  document.getElementById('add-period-invoice-day-type').value = invDayType;

  const invDay = prev?.invoice_day ?? dtConf.default_invoice_day ?? '';
  document.getElementById('add-period-invoice-day').value = invDay;
  setElementHidden(document.getElementById('label-add-period-invoice-day'), invDayType !== '특정일');

  const invHoliday = prev?.invoice_holiday_adjust ?? dtConf.default_invoice_holiday_adjust ?? '';
  document.getElementById('add-period-invoice-holiday').value = invHoliday;

  document.getElementById('add-period-is-planned').checked = true;
  _addPeriodMonthManuallyEdited = false;
  document.getElementById('modal-add-period').showModal();
}

// ── 모달 설정 ──────────────────────────────────────────────────
function setupModals() {
  document.getElementById('btn-repeat-cancel').addEventListener('click', () => document.getElementById('modal-repeat').close());
  document.getElementById('btn-repeat-submit').addEventListener('click', generateRepeatRows);

  // Forecast 매입 기준 체크박스: 매입 선택 시만 활성, 체크 시 금액 비활성
  const repeatType = document.getElementById('repeat-line-type');
  const repeatChk = document.getElementById('repeat-use-forecast');
  const repeatAmt = document.getElementById('repeat-amount');
  repeatChk.addEventListener('change', () => {
    repeatAmt.disabled = repeatChk.checked;
    if (repeatChk.checked) repeatAmt.value = '';
  });
  repeatType.addEventListener('change', () => {
    if (repeatType.value !== '매입') {
      repeatChk.checked = false;
      repeatAmt.disabled = false;
    }
  });
  document.getElementById('add-period-invoice-day-type').addEventListener('change', (e) => {
    setElementHidden(document.getElementById('label-add-period-invoice-day'), e.target.value !== '특정일');
  });

  // Forecast 동기화 모달
  document.getElementById('btn-sync-cancel').addEventListener('click', () => document.getElementById('modal-forecast-sync').close());
  document.getElementById('btn-sync-submit').addEventListener('click', submitForecastSync);

  document.getElementById('btn-add-period').addEventListener('click', () => _openAddPeriodModal());
  document.getElementById('btn-add-period-cancel').addEventListener('click', () => document.getElementById('modal-add-period').close());
  document.getElementById('btn-add-period-submit').addEventListener('click', submitAddPeriod);

  // 매출/GP 자동 계산 + 한글 표기
  document.getElementById('add-period-sales').addEventListener('input', () => {
    const sales = parseInt(document.getElementById('add-period-sales').value) || 0;
    document.getElementById('add-period-sales-kr').textContent = formatKoreanAmount(sales);
    _updateAddPeriodGp();
  });
  document.getElementById('add-period-gp-pct').addEventListener('input', _updateAddPeriodGp);

  // 귀속연도 변경 → 사업기간 자동 연동
  document.getElementById('add-period-year').addEventListener('change', () => {
    if (_addPeriodMonthManuallyEdited) return;
    const y = parseInt(document.getElementById('add-period-year').value);
    if (!y || y < 2020 || y > 2099) return;
    document.getElementById('add-period-start').value = `${y}-01`;
    document.getElementById('add-period-end').value = `${y}-12`;
  });

  // 사업기간 수동 편집 추적
  document.getElementById('add-period-start').addEventListener('change', () => { _addPeriodMonthManuallyEdited = true; });
  document.getElementById('add-period-end').addEventListener('change', () => { _addPeriodMonthManuallyEdited = true; });

  // Period 삭제 모달
}

async function submitAddPeriod() {
  const year = parseInt(document.getElementById('add-period-year').value);
  const stage = document.getElementById('add-period-stage').value;
  const expectedSales = parseInt(document.getElementById('add-period-sales').value) || 0;
  const expectedGp = parseInt(document.getElementById('add-period-gp-val').value) || 0;
  const startMonth = document.getElementById('add-period-start').value;
  const endMonth = document.getElementById('add-period-end').value;

  if (!year || year < 2020 || year > 2099) { showToast('연도를 올바르게 입력하세요.', 'error'); return; }
  if (allPeriods.some(p => p.period_year === year)) { showToast(`${year}년은 이미 존재합니다.`, 'error'); return; }

  // 귀속연도 ↔ 사업기간 불일치 경고
  if (startMonth && endMonth) {
    const startYear = parseInt(startMonth.split('-')[0]);
    const endYear = parseInt(endMonth.split('-')[0]);
    if (endYear < year || startYear > year) {
      if (!await showConfirmDialog(`사업기간(${startMonth} ~ ${endMonth})이 귀속연도(${year})와 겹치지 않습니다.\n계속 진행하시겠습니까?`, {
        title: '기간 경고',
        confirmText: '계속',
      })) return;
    }
  }

  const custId = document.getElementById('add-period-partner').value;
  const body = {
    period_year: year,
    stage,
    start_month: startMonth ? startMonth + '-01' : null,
    end_month: endMonth ? endMonth + '-01' : null,
  };
  if (custId) body.partner_id = parseInt(custId);
  body.is_planned = document.getElementById('add-period-is-planned').checked;

  const res = await fetch(`/api/v1/contracts/${contractId}/periods`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showToast(err.detail || '기간 추가에 실패했습니다.', 'error');
    return;
  }
  const newPeriod = await res.json();

  // Sales-detail fields (inspection/invoice/expected amounts)
  const salesBody = {
    expected_revenue_amount: expectedSales,
    expected_gp_amount: expectedGp,
  };
  const inspDay = document.getElementById('add-period-inspect-day').value;
  const inspDate = document.getElementById('add-period-inspect-date').value;
  if (inspDay !== '') salesBody.inspection_day = parseInt(inspDay);
  if (inspDate) salesBody.inspection_date = _normalizeDate(inspDate);
  const invMonth = document.getElementById('add-period-invoice-month').value;
  const invDayType = document.getElementById('add-period-invoice-day-type').value;
  const invDay = document.getElementById('add-period-invoice-day').value;
  const invHoliday = document.getElementById('add-period-invoice-holiday').value;
  if (invMonth !== '') salesBody.invoice_month_offset = parseInt(invMonth);
  if (invDayType) salesBody.invoice_day_type = invDayType;
  if (invDay) salesBody.invoice_day = parseInt(invDay);
  if (invHoliday) salesBody.invoice_holiday_adjust = invHoliday;

  // Save sales-detail to the new period
  await fetch(`/api/v1/contract-periods/${newPeriod.id}/sales-detail`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(salesBody),
  }).catch(() => {});

  document.getElementById('modal-add-period').close();
  window.location.href = `/contracts/${newPeriod.id}`;
}

/** Period의 계산서 발행 규칙으로 발행일 계산.
 *  revenueMonth: "YYYY-MM-01", src: periodData (또는 계산서 설정 객체)
 *  반환: "YYYY-MM-DD" 또는 null */
function _calcInvoiceDate(revenueMonth, src) {
  if (!src || !src.invoice_day_type) return null;
  const base = new Date(revenueMonth + 'T00:00:00');
  const offset = src.invoice_month_offset || 0;
  base.setMonth(base.getMonth() + offset);
  const y = base.getFullYear();
  const m = base.getMonth(); // 0-based
  const lastDay = new Date(y, m + 1, 0).getDate();
  let day;
  if (src.invoice_day_type === '1일') {
    day = 1;
  } else if (src.invoice_day_type === '말일') {
    day = lastDay;
  } else if (src.invoice_day_type === '특정일' && src.invoice_day) {
    day = Math.min(src.invoice_day, lastDay);
  } else {
    return null;
  }
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

function _getForecastCostMap() {
  // Forecast 그리드에서 월별 cost(매출 - GP) 맵 생성
  const costMap = {};
  if (!forecastApi) return costMap;
  const rows = [];
  forecastApi.forEachNode(n => rows.push(n.data));
  const salesRow = rows.find(r => r._rowType === 'sales');
  const gpRow = rows.find(r => r._rowType === 'gp');
  if (!salesRow || !gpRow) return costMap;
  const months = _getPeriodMonths();
  months.forEach(m => {
    const rev = salesRow[m] || 0;
    const gp = gpRow[m] || 0;
    costMap[m] = Math.max(0, rev - gp);
  });
  return costMap;
}

function generateRepeatRows() {
  const start = document.getElementById('repeat-start').value;
  const end = document.getElementById('repeat-end').value;
  const type = document.getElementById('repeat-line-type').value; // 매출 / 매입
  const partnerName = document.getElementById('repeat-partner').value;
  const useForecast = document.getElementById('repeat-use-forecast').checked;
  const amount = parseInt(document.getElementById('repeat-amount').value) || 0;
  const desc = document.getElementById('repeat-desc').value;

  if (!start || !end) { alert('시작월, 종료월을 입력하세요.'); return; }
  if (!useForecast && amount <= 0) { alert('금액을 입력하세요.'); return; }

  const costMap = useForecast ? _getForecastCostMap() : {};

  // 동일 구분+거래처+귀속월 조합이 이미 존재하는지 확인
  const existingKeys = new Set();
  if (ledgerApi) {
    ledgerApi.forEachNode(n => {
      if (!n.rowPinned && n.data.type === type) {
        existingKeys.add(`${n.data.revenue_month}|${n.data.partner_name || ''}`);
      }
    });
  }

  const rows = [];
  let skipped = 0;
  let cur = new Date(start + '-01');
  const endDate = new Date(end + '-01');
  while (cur <= endDate) {
    const ym = `${cur.getFullYear()}-${String(cur.getMonth() + 1).padStart(2, '0')}-01`;
    const rowAmount = useForecast ? (costMap[ym] || 0) : amount;
    if (rowAmount > 0) {
      if (existingKeys.has(`${ym}|${partnerName}`)) {
        skipped++;
      } else {
        const row = { revenue_month: ym, type, partner_name: partnerName, amount: rowAmount, status: '예정', description: desc };
        const invoiceDate = _calcInvoiceDate(ym, periodData);
        if (invoiceDate) row.date = invoiceDate;
        rows.push(row);
      }
    }
    cur.setMonth(cur.getMonth() + 1);
  }
  if (rows.length === 0) {
    alert(skipped > 0
      ? `동일 구분·거래처·귀속월의 행이 이미 ${skipped}건 존재하여 추가할 항목이 없습니다.`
      : '생성할 행이 없습니다. Forecast 데이터를 확인하세요.');
    return;
  }
  if (skipped > 0) showToast(`기존 행과 중복되는 ${skipped}건은 건너뛰었습니다.`, 'info');
  ledgerApi.applyTransaction({ add: rows });
  dirtyLedger = true; _updateDirtyIndicators();
  refreshLedgerSummary();
  document.getElementById('modal-repeat').close();
}


// ── 컬럼 순서 저장/복원 (localStorage) ────────────────────────────
function saveColumnOrder(gridKey, api) {
  const cols = api.getAllDisplayedColumns();
  if (!cols || !cols.length) return;
  const order = cols.map(c => c.getColId());
  localStorage.setItem(`col_order_${gridKey}`, JSON.stringify(order));
}

function applyColumnOrder(gridKey, api) {
  const saved = localStorage.getItem(`col_order_${gridKey}`);
  if (!saved) return;
  try {
    const order = JSON.parse(saved);
    // 현재 그리드에 실제 존재하는 컬럼만 필터
    const allColIds = api.getAllDisplayedColumns().map(c => c.getColId());
    const validOrder = order.filter(id => allColIds.includes(id));
    // 저장된 순서에 없는 새 컬럼은 끝에 유지
    if (validOrder.length > 0) {
      api.moveColumns(validOrder, 0);
    }
  } catch { /* ignore */ }
}

// ── 드롭다운 ─────────────────────────────────────────────────────
function _initDropdowns() {
  document.querySelectorAll('.dropdown-trigger').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const dd = btn.closest('.dropdown');
      const wasOpen = dd.classList.contains('open');
      _closeDropdowns();
      if (!wasOpen) dd.classList.add('open');
    });
  });
  document.addEventListener('click', () => _closeDropdowns());
}
function _closeDropdowns() {
  document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
}

// ── 유틸 ────────────────────────────────────────────────────────
function toMonthFirst(val) {
  if (!val) return null;
  const s = String(val).trim();
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s.slice(0, 8) + '01';
  if (/^\d{4}-\d{2}$/.test(s)) return s + '-01';
  return s;
}

function findPartnerId(name) {
  if (!name) return null;
  const c = partners.find(c => c.name === name);
  return c ? c.id : null;
}

// ── 누락 필드 검증 & 하이라이트 ──────────────────────────────────
function _validateLedgerRows(api) {
  // 데이터가 있는 행 중 필수 필드(구분, 거래처, 금액) 누락을 검사
  const missing = [];
  api.forEachNode(n => {
    if (n.rowPinned) return;
    const d = n.data;
    if (!d.type && !d.amount && !d.partner_name && !d.revenue_month) return; // 완전 빈 행은 무시
    const issues = [];
    if (!d.revenue_month) issues.push('revenue_month');
    if (!d.type) issues.push('type');
    if (!d.partner_name) issues.push('partner_name');
    if (!d.amount || d.amount <= 0) issues.push('amount');
    if (issues.length) missing.push({ node: n, issues });
  });
  return missing;
}

function _highlightMissing(api, missing, colMap) {
  // 기존 하이라이트 제거
  api.forEachNode(n => { n.data._missingFields = null; });
  missing.forEach(({ node, issues }) => { node.data._missingFields = issues; });
  api.refreshCells({ force: true });
}

function _clearMissingHighlight(api) {
  api.forEachNode(n => { n.data._missingFields = null; });
  api.refreshCells({ force: true });
}

// ── 월 선택 셀 에디터 (input type="month") ──────────────────────
class MonthCellEditor {
  init(params) {
    this.value = params.value || '';
    this.input = document.createElement('input');
    this.input.type = 'month';
    this.input.className = 'ag-cell-input-editor';
    // YYYY-MM-01 → YYYY-MM
    if (this.value && this.value.length >= 7) this.input.value = this.value.slice(0, 7);
    this.input.addEventListener('change', () => { this.params.stopEditing(); });
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.params.stopEditing(true);
    });
    this.params = params;
  }
  getGui() { return this.input; }
  afterGuiAttached() { this.input.focus(); }
  getValue() {
    const v = this.input.value; // YYYY-MM
    return v ? v + '-01' : this.value;
  }
  isPopup() { return true; }
}

// ── 날짜 선택 셀 에디터 (input type="date") ──────────────────────
/** 날짜 텍스트 정규화: 250115, 20250115, 0115, 2025-1-5, 2025/01/15 → 2025-01-15 */
function _normalizeDate(raw) {
  if (!raw) return '';
  const s = String(raw).trim().replace(/[\/\.]/g, '-');
  // YYYY-MM-DD (이미 정규 형식)
  let m = s.match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
  if (m) return `${m[1]}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`;
  // YYYYMMDD
  m = s.match(/^(\d{4})(\d{2})(\d{2})$/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  // YYMMDD
  m = s.match(/^(\d{2})(\d{2})(\d{2})$/);
  if (m) {
    const yy = parseInt(m[1]);
    const yyyy = yy <= 79 ? 2000 + yy : 1900 + yy;
    return `${yyyy}-${m[2]}-${m[3]}`;
  }
  // MMDD (4자리 → 올해 기준)
  m = s.match(/^(\d{2})(\d{2})$/);
  if (m) {
    const mm = parseInt(m[1]);
    if (mm >= 1 && mm <= 12) return `${new Date().getFullYear()}-${m[1]}-${m[2]}`;
  }
  // YY-MM-DD
  m = s.match(/^(\d{2})-(\d{1,2})-(\d{1,2})$/);
  if (m) {
    const yy = parseInt(m[1]);
    const yyyy = yy <= 79 ? 2000 + yy : 1900 + yy;
    return `${yyyy}-${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`;
  }
  return s;
}

class DateCellEditor {
  init(params) {
    this.value = params.value || '';
    this.params = params;

    this.container = document.createElement('div');
    this.container.className = 'ag-cell-date-editor';

    // 텍스트 입력
    this.input = document.createElement('input');
    this.input.type = 'text';
    this.input.className = 'ag-cell-input-editor';
    this.input.placeholder = 'YYYY-MM-DD';
    if (this.value) this.input.value = this.value;
    this.container.appendChild(this.input);

    // 달력 버튼
    this.dateInput = document.createElement('input');
    this.dateInput.type = 'date';
    this.dateInput.className = 'ag-cell-date-picker';
    if (this.value) this.dateInput.value = this.value;
    this.container.appendChild(this.dateInput);

    this.dateInput.addEventListener('change', () => {
      this.input.value = this.dateInput.value;
      this.params.stopEditing();
    });
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.params.stopEditing();
      if (e.key === 'Escape') this.params.stopEditing(true);
      if (e.key === 'Tab') this.params.stopEditing();
    });
  }
  getGui() { return this.container; }
  afterGuiAttached() { this.input.focus(); this.input.select(); }
  getValue() {
    const normalized = _normalizeDate(this.input.value);
    return normalized || this.value;
  }
  isPopup() { return true; }
}

// ── 거래처 검색 셀 에디터 ────────────────────────────────────────
class PartnerCellEditor {
  init(params) {
    this.value = params.value || '';
    this.params = params;

    this.container = document.createElement('div');
    this.container.className = 'ag-cell-partner-editor';

    this.input = document.createElement('input');
    this.input.type = 'text';
    this.input.value = this.value;
    this.input.className = 'ag-cell-input-editor';
    this.container.appendChild(this.input);

    this.dropdown = document.createElement('div');
    this.dropdown.className = 'ag-cell-partner-dropdown is-hidden';
    document.body.appendChild(this.dropdown);

    this.input.addEventListener('input', () => this._renderList());
    this.input.addEventListener('focus', () => this._renderList());
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        const first = this.dropdown.querySelector('.cust-option');
        if (first) first.focus();
      }
      if (e.key === 'Escape') {
        setElementHidden(this.dropdown, true);
      }
      if (e.key === 'Enter') {
        // 목록에 정확히 일치하는 항목이 있으면 선택
        const match = partners.find(c => c.name === this.input.value.trim());
        if (match) {
          this.value = match.name;
          this.params.stopEditing();
        }
      }
    });
  }

  _findSimilar(keyword) {
    if (!keyword || keyword.length < 2) return [];
    const kw = keyword.toLowerCase().replace(/\s/g, '');
    return partners.filter(c => {
      const cn = c.name.toLowerCase().replace(/\s/g, '');
      if (cn === kw) return false; // 완전 일치는 제외
      // 포함 관계 또는 편집 거리 2 이내
      if (cn.includes(kw) || kw.includes(cn)) return true;
      // 간단한 유사도: 공통 문자 비율
      const common = [...new Set(kw)].filter(ch => cn.includes(ch)).length;
      const ratio = common / Math.max(kw.length, cn.length);
      return ratio >= 0.7;
    }).slice(0, 3);
  }

  _renderList() {
    const keyword = this.input.value.trim().toLowerCase();
    const filtered = keyword
      ? partners.filter(c => c.name.toLowerCase().includes(keyword))
      : partners;
    const limited = filtered.slice(0, 50);

    let html = limited.map(c =>
      `<div class="cust-option" tabindex="-1" data-name="${c.name}">${c.name}</div>`
    ).join('');

    // 완전 일치 없고 입력값이 있으면 유사 거래처 경고
    if (keyword && !partners.find(c => c.name.toLowerCase() === keyword)) {
      const similar = this._findSimilar(this.input.value.trim());
      if (similar.length) {
        html += `<div class="cust-similar-warn">⚠ 유사 거래처: ${similar.map(c => `<b>${c.name}</b>`).join(', ')}</div>`;
      }
    }

    html += `<div class="cust-option-new">+ 신규 거래처 등록</div>`;

    this.dropdown.innerHTML = html;
    // input 위치 기준으로 드롭다운 배치
    const rect = this.input.getBoundingClientRect();
    this.dropdown.style.left = rect.left + 'px';
    this.dropdown.style.top = rect.bottom + 'px';
    this.dropdown.style.width = rect.width + 'px';
    setElementHidden(this.dropdown, false);

    this.dropdown.querySelectorAll('.cust-option').forEach(el => {
      el.addEventListener('mousedown', (e) => {
        e.preventDefault(); // blur 방지: stopEditingWhenCellsLoseFocus 대응
        this.value = el.dataset.name;
        this.input.value = this.value;
        setElementHidden(this.dropdown, true);
        this.params.stopEditing();
      });
      el.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') { this.value = el.dataset.name; this.input.value = this.value; setElementHidden(this.dropdown, true); this.params.stopEditing(); }
        if (e.key === 'ArrowDown' && el.nextElementSibling) { e.preventDefault(); el.nextElementSibling.focus(); }
        if (e.key === 'ArrowUp' && el.previousElementSibling) { e.preventDefault(); el.previousElementSibling.focus(); }
      });
    });

    const newBtn = this.dropdown.querySelector('.cust-option-new');
    if (newBtn) {
      newBtn.addEventListener('mousedown', (e) => {
        e.preventDefault(); // blur 방지
        setElementHidden(this.dropdown, true);
        this.params.stopEditing();
        _openNewPartnerPopup(this.input.value.trim());
      });
    }
  }

  getGui() { return this.container; }
  afterGuiAttached() { this.input.focus(); this.input.select(); }
  getValue() { return this.value; }
  destroy() { this.dropdown.remove(); }
  isPopup() { return true; }
}

function _openNewPartnerPopup(prefill) {
  document.getElementById('new-cust-name-inline').value = prefill || '';
  document.getElementById('modal-new-partner').showModal();
}

async function _submitNewPartnerInline() {
  const name = document.getElementById('new-cust-name-inline').value.trim();
  if (!name) { alert('거래처명을 입력하세요.'); return; }
  const res = await fetch('/api/v1/partners', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  });
  if (res.ok) {
    document.getElementById('modal-new-partner').close();
    await loadPartners();
    showToast(`"${name}" 거래처가 등록되었습니다.`);
  } else {
    const body = await res.json().catch(() => null);
    alert(body?.detail || '등록에 실패했습니다.');
  }
}

function addPasteHandler(el, api, editableFields) {
  function _handlePaste(e) {
    const focused = api.getFocusedCell();
    if (!focused) return;
    const text = (e.clipboardData || window.clipboardData)?.getData('text/plain');
    if (!text) return;
    e.preventDefault();
    e.stopPropagation();
    api.stopEditing();
    const pasteRows = text.trim().split('\n').map(r => r.split('\t'));
    const startRow = focused.rowIndex;
    const allCols = api.getAllDisplayedColumns();
    const startColIdx = allCols.findIndex(c => c.getColId() === focused.column.getColId());
    pasteRows.forEach((pr, ri) => {
      const node = api.getDisplayedRowAtIndex(startRow + ri);
      if (!node || node.rowPinned) return;
      pr.forEach((val, ci) => {
        const col = allCols[startColIdx + ci];
        if (!col) return;
        const colId = col.getColId();
        if (!editableFields.includes(colId)) return;
        const num = parseInt(String(val).replace(/,/g, '').replace(/[^0-9-]/g, ''));
        node.setDataValue(colId, isNaN(num) ? val : num);
      });
    });
  }
  el.addEventListener('paste', _handlePaste, true);
}

async function deletePeriodById(periodId, label) {
  const msg = allPeriods.length <= 1
    ? `${label} Period를 삭제하시겠습니까?\n마지막 Period이므로 사업이 삭제(비활성) 처리됩니다.`
    : `${label} Period를 삭제하시겠습니까?\nForecast, 매출/매입 실적, 입금 데이터가 모두 삭제됩니다.`;
  if (!await showConfirmDialog(msg, {
    title: 'Period 삭제',
    confirmText: '삭제',
  })) return;

  const res = await fetch(`/api/v1/contract-periods/${periodId}`, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || 'Period 삭제에 실패했습니다.');
    return;
  }

  if (allPeriods.length <= 1) {
    window.location.href = '/contracts';
  } else if (periodId === CONTRACT_PERIOD_ID) {
    const other = allPeriods.find(p => p.id !== periodId);
    window.location.href = `/contracts/${other.id}`;
  } else {
    window.location.reload();
  }
}

async function importFromForecast() {
  if (!contractId || !CONTRACT_PERIOD_ID) return;

  const res = await fetch(`/api/v1/contracts/${contractId}/forecast-sync-preview`);
  if (!res.ok) { alert('Forecast 대조에 실패했습니다.'); return; }
  const preview = await res.json();

  const container = document.getElementById('forecast-sync-content');
  const btnSubmit = document.getElementById('btn-sync-submit');

  if (!preview.to_create.length && !preview.to_delete.length) {
    container.innerHTML = '<p class="sync-empty">변경 사항이 없습니다.<br>Forecast와 실적 원장이 동기화되어 있습니다.</p>';
    btnSubmit.disabled = true;
    document.getElementById('modal-forecast-sync').showModal();
    return;
  }

  let html = '';
  if (preview.to_create.length) {
    html += '<div class="sync-section-title"><b class="text-success">+ 생성</b> <span class="sync-desc">Forecast에 있으나 실적에 없는 월</span></div>';
    html += preview.to_create.map(r =>
      `<div class="sync-row">
        <span>${r.revenue_month.slice(0,7)}</span>
        <span class="sync-row-amount">${fmt(r.amount)}원</span>
      </div>`
    ).join('');
  }
  if (preview.to_delete.length) {
    html += '<div class="sync-section-title sync-section-gap"><b class="text-danger">− 삭제 대상</b> <span class="sync-desc">Forecast에 없는 "예정" 매출행 (거래처 미지정)</span></div>';
    html += preview.to_delete.map(r =>
      `<label class="sync-row-delete">
        <span class="sync-chk-wrap">
          <input type="checkbox" class="sync-delete-chk" value="${r.id}" checked>
          ${r.revenue_month.slice(0,7)}
        </span>
        <span class="sync-row-amount">${fmt(r.amount)}원</span>
      </label>`
    ).join('');
  }
  container.innerHTML = html;
  btnSubmit.disabled = false;
  document.getElementById('modal-forecast-sync').showModal();
}

async function submitForecastSync() {
  const deleteIds = [...document.querySelectorAll('.sync-delete-chk:checked')].map(c => parseInt(c.value));
  const res = await fetch(`/api/v1/contracts/${contractId}/forecast-sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ delete_ids: deleteIds }),
  });
  if (!res.ok) { alert('동기화에 실패했습니다.'); return; }
  const result = await res.json();
  document.getElementById('modal-forecast-sync').close();
  const msgs = [];
  if (result.created) msgs.push(`${result.created}건 생성`);
  if (result.deleted) msgs.push(`${result.deleted}건 삭제`);
  if (msgs.length) showToast(msgs.join(', ') + ' 완료');
  else showToast('변경 사항이 없습니다.', 'info');
  await reloadLedger();
}

function addPasteHandlerLedger(el, api) {
  function _handlePaste(e) {
    const focused = api.getFocusedCell();
    if (!focused) return;
    const text = (e.clipboardData || window.clipboardData)?.getData('text/plain');
    if (!text) return;
    e.preventDefault();
    e.stopPropagation();
    api.stopEditing();

    const pasteRows = text.trim().split('\n').map(r => r.split('\t'));
    const startRow = focused.rowIndex;

    pasteRows.forEach((pr, ri) => {
      let node = api.getDisplayedRowAtIndex(startRow + ri);
      if (!node || node.rowPinned) {
        api.applyTransaction({ add: [{}] });
        const count = api.getDisplayedRowCount();
        node = api.getDisplayedRowAtIndex(count - 1);
      }
      if (!node) return;

      const allCols = api.getAllDisplayedColumns();
      const startColIdx = allCols.findIndex(c => c.getColId() === focused.column.getColId());

      pr.forEach((val, ci) => {
        const col = allCols[startColIdx + ci];
        if (!col) return;
        const colId = col.getColId();
        if (colId === 'amount') {
          const num = parseInt(String(val).replace(/,/g, '').replace(/[^0-9-]/g, '')) || 0;
          node.setDataValue(colId, num);
        } else {
          node.setDataValue(colId, val.trim());
        }
      });
    });
    refreshLedgerSummary();
  }
  el.addEventListener('paste', _handlePaste, true);
}

// ── Receipt Grid (입금 내역) ──────────────────────────────────────
function initReceiptGrid(receipts) {
  const colDefs = [
    { headerName: '', field: '_chk', width: 40, pinned: 'left', lockPosition: true,
      headerCheckboxSelection: true, headerCheckboxSelectionFilteredOnly: true, checkboxSelection: true,
      editable: false, sortable: false, resizable: false, suppressMovable: true },
    { field: 'receipt_date', headerName: '입금일', editable: true, width: 130,
      cellEditor: DateCellEditor,
      cellClassRules: { 'cell-missing': p => p.data._missingFields?.includes('receipt_date') } },
    { field: 'revenue_month', headerName: '귀속월', editable: true, width: 110,
      cellEditor: MonthCellEditor,
      valueFormatter: p => p.value ? p.value.slice(0, 7) : '',
      valueSetter: p => { p.data.revenue_month = toMonthFirst(p.newValue); return true; } },
    { field: 'partner_name', headerName: '거래처', editable: true, width: 140,
      cellEditor: PartnerCellEditor },
    { field: 'amount', headerName: '금액(원)', editable: true, type: 'numericColumn', width: 130,
      valueParser: p => Math.max(0, parseInt(String(p.newValue).replace(/,/g, '')) || 0),
      valueFormatter: p => p.value ? fmt(p.value) : '',
      tooltipValueGetter: p => p.value >= 10000 ? fmtKoreanCurrency(p.value) : null },
    { field: 'description', headerName: '메모', editable: true, flex: 1 },
  ];

  const el = document.getElementById('grid-receipt');
  el.innerHTML = '';
  receiptApi = agGrid.createGrid(el, {
    columnDefs: _wrapEditableWithCompleted(colDefs),
    rowData: receipts,
    defaultColDef: { resizable: true, sortable: true },
    tooltipShowDelay: 300,
    enableCellTextSelection: true,
    ensureDomOrder: true,
    rowSelection: 'multiple',
    suppressRowClickSelection: true,
    singleClickEdit: true,
    stopEditingWhenCellsLoseFocus: true,
    onCellValueChanged: () => { dirtyReceipt = true; _updateDirtyIndicators(); refreshReceiptSummary(); },
    isExternalFilterPresent: () => _hasReceiptFilter(),
    doesExternalFilterPass: node => _passReceiptFilter(node),
    onDragStopped: () => saveColumnOrder('receipt', receiptApi),
  });
  applyColumnOrder('receipt', receiptApi);
  refreshReceiptSummary();
}

function refreshReceiptSummary() {
  const rows = [];
  receiptApi.forEachNode(n => { if (!n.rowPinned) rows.push(n.data); });
  const total = rows.reduce((s, r) => s + (r.amount || 0), 0);
  document.getElementById('receipt-summary-bar').innerHTML =
    `<span class="summary-entry"><span class="label">입금 합계</span> <span class="value summary-value-receipt">${fmt(total)}원</span></span>` +
    `<span class="summary-entry"><span class="label">건수</span> <span class="value">${rows.length}</span></span>`;
}

function addReceiptRow(scrollToNew) {
  const today = new Date();
  const dateStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const ym = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-01`;

  // 그리드 내 미저장 입금 행의 금액을 귀속월별로 합산
  const pendingByMonth = {};
  if (receiptApi) {
    receiptApi.forEachNode(n => {
      if (n.rowPinned) return;
      const d = n.data;
      if (!d._isNew && d.id) return;  // 저장된 행은 이미 allocation에 반영됨
      const m = d.revenue_month;
      if (m) pendingByMonth[m] = (pendingByMonth[m] || 0) + (d.amount || 0);
    });
  }

  // 가장 오래된 미배분 확정 매출 행 탐색 (미저장 입금 반영)
  const allocMap = window._allocationMap || {};
  let oldest = null;
  if (ledgerApi) {
    ledgerApi.forEachNode(n => {
      if (n.rowPinned) return;
      const d = n.data;
      if (d.type !== '매출' || d.status !== '확정') return;
      const remaining = (d.amount || 0) - (allocMap[d.transaction_line_id] || 0) - (pendingByMonth[d.revenue_month] || 0);
      if (remaining <= 0) return;
      if (!oldest || (d.revenue_month || '') < (oldest.revenue_month || '')) {
        oldest = { revenue_month: d.revenue_month, partner_name: d.partner_name, amount: remaining, date: d.date };
      }
    });
  }

  // 미배분 매출이 있으면 해당 정보로, 없으면 직전 행 복사
  let prevReceipt = null;
  receiptApi.forEachNode(n => { if (!n.rowPinned) prevReceipt = n.data; });
  const res = receiptApi.applyTransaction({ add: [{
    receipt_date: oldest?.date || dateStr,
    revenue_month: oldest?.revenue_month || prevReceipt?.revenue_month || ym,
    partner_name: oldest?.partner_name || prevReceipt?.partner_name || currentContract?.end_partner_name || '',
    amount: oldest?.amount || 0,
  }] });
  dirtyReceipt = true; _updateDirtyIndicators();
  refreshReceiptSummary();
  if (scrollToNew && res.add && res.add.length) {
    receiptApi.ensureNodeVisible(res.add[0], 'bottom');
    setTimeout(() => receiptApi.setFocusedCell(res.add[0].rowIndex, 'amount'), 50);
  }
}

async function saveReceipt() {
  const btn = document.getElementById('btn-save-receipt');
  btn.disabled = true; btn.textContent = '저장 중...';
  try { await _doSaveReceipt(); } finally { btn.disabled = false; _updateDirtyIndicators(); }
}
async function _doSaveReceipt() {
  // 누락 필드 검증: 금액 > 0인데 입금일이 없는 행
  const payMissing = [];
  receiptApi.forEachNode(n => {
    if (n.rowPinned) return;
    const d = n.data;
    if (!d.amount && !d.receipt_date && !d.partner_name) return;
    const issues = [];
    if (d.amount > 0 && !d.receipt_date) issues.push('receipt_date');
    if (issues.length) payMissing.push({ node: n, issues });
  });
  if (payMissing.length) {
    payMissing.forEach(({ node, issues }) => { node.data._missingFields = issues; });
    receiptApi.refreshCells({ force: true });
    receiptApi.ensureNodeVisible(payMissing[0].node, 'middle');
    showToast(`입금일이 누락된 행이 ${payMissing.length}건 있습니다.`, 'error');
    return;
  }
  receiptApi.forEachNode(n => { n.data._missingFields = null; });
  receiptApi.refreshCells({ force: true });

  const rows = [];
  receiptApi.forEachNode(n => { if (!n.rowPinned) rows.push(n.data); });

  // 미등록 거래처 검증
  const validRows = rows.filter(r => r.receipt_date && r.amount);
  const unregistered = validRows
    .filter(r => r.partner_name && !findPartnerId(r.partner_name))
    .map(r => r.partner_name);
  if (unregistered.length > 0) {
    alert(`등록되지 않은 거래처가 있습니다: ${[...new Set(unregistered)].join(', ')}\n거래처를 먼저 등록해 주세요.`);
    return;
  }

  const reqs = validRows
    .map(row => {
      const body = {
        partner_id: findPartnerId(row.partner_name),
        receipt_date: row.receipt_date,
        revenue_month: row.revenue_month || null,
        amount: row.amount || 0,
        description: row.description || null,
      };
      return row.id
        ? fetch(`/api/v1/receipts/${row.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
        : fetch(`/api/v1/contracts/${contractId}/receipts`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    });

  const results = await Promise.all(reqs);
  const failed = results.filter(r => !r.ok);
  if (failed.length) {
    const errMsg = await failed[0].json().catch(() => ({}));
    showToast(errMsg.detail || `${failed.length}건 저장에 실패했습니다.`, 'error');
  }
  else showToast('입금 내역이 저장되었습니다.');
  dirtyReceipt = false; _updateDirtyIndicators();
  await reloadLedger();
}

async function deleteSelectedReceiptRows() {
  if (!me?.permissions?.can_delete_receipt) { alert('관리자만 삭제할 수 있습니다.'); return; }
  const selected = receiptApi.getSelectedRows();
  if (!selected.length) { alert('삭제할 행을 선택해주세요.'); return; }
  if (!await showConfirmDialog(`선택한 ${selected.length}건을 삭제하시겠습니까?`, {
    title: '입금 행 삭제',
    confirmText: '삭제',
  })) return;
  const toRemove = [];
  for (const row of selected) {
    if (row.id) {
      const r = await fetch(`/api/v1/receipts/${row.id}`, { method: 'DELETE' });
      if (!r.ok) { alert(`삭제 실패: ${row.partner_name || ''} ${row.receipt_date || ''}`); continue; }
    }
    toRemove.push(row);
  }
  if (toRemove.length) {
    receiptApi.applyTransaction({ remove: toRemove });
    refreshReceiptSummary();
    const rows = [];
    receiptApi.forEachNode(n => { if (!n.rowPinned) rows.push(n.data); });
    lastReceiptTotal = rows.reduce((s, r) => s + (r.amount || 0), 0);
    renderGpSummary();
    showToast(`${toRemove.length}건이 삭제되었습니다.`);
  }
}

// ── 매출 원장에서 입금 가져오기 ──────────────────────────────────────

function openReceiptFromLedger() {
  const allocMap = window._allocationMap || {};
  // 확정 매출 행 중 미수잔액이 있는 항목 추출
  const arRows = [];
  ledgerApi.forEachNode(n => {
    if (n.rowPinned) return;
    const d = n.data;
    if (d.type !== '매출' || d.status !== '확정') return;
    const amt = d.amount || 0;
    const alloc = allocMap[d.transaction_line_id] || 0;
    const remaining = amt - alloc;
    if (remaining <= 0) return;
    arRows.push({ ...d, _remaining: remaining });
  });

  const container = document.getElementById('receipt-from-ledger-content');
  const btnSubmit = document.getElementById('btn-receipt-from-ledger-submit');
  const summaryEl = document.getElementById('receipt-from-ledger-summary');

  // 입금일 기본값: 오늘 (발행일 없는 행의 fallback)
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  document.getElementById('receipt-from-ledger-date').value = todayStr;

  if (!arRows.length) {
    container.innerHTML = '<p class="sync-empty">미수잔액이 있는 확정 매출 행이 없습니다.</p>';
    summaryEl.innerHTML = '';
    btnSubmit.disabled = true;
    document.getElementById('modal-receipt-from-ledger').showModal();
    return;
  }

  const html = arRows.map((r, i) => `
    <label class="sync-row-delete">
      <span class="sync-chk-wrap">
        <input type="checkbox" class="receipt-from-ledger-chk" data-idx="${i}" checked>
        ${r.revenue_month ? r.revenue_month.slice(0, 7) : '-'}
      </span>
      <span class="sync-row-detail">${r.partner_name || '-'}</span>
      <span class="sync-row-detail">${r.date || '-'}</span>
      <span class="sync-row-amount">${fmt(r._remaining)}원</span>
    </label>`
  ).join('');
  container.innerHTML = html;
  window._receiptFromLedgerRows = arRows;

  const updateSummary = () => {
    const chks = container.querySelectorAll('.receipt-from-ledger-chk:checked');
    const count = chks.length;
    const total = Array.from(chks).reduce((s, c) => s + arRows[parseInt(c.dataset.idx)]._remaining, 0);
    summaryEl.innerHTML = count
      ? `<span>${count}건 선택 · 합계 <b>${fmt(total)}원</b></span>`
      : '';
    btnSubmit.disabled = count === 0;
  };
  container.querySelectorAll('.receipt-from-ledger-chk').forEach(c => c.addEventListener('change', updateSummary));
  updateSummary();
  document.getElementById('modal-receipt-from-ledger').showModal();
}

function submitReceiptFromLedger() {
  const fallbackDate = _normalizeDate(document.getElementById('receipt-from-ledger-date').value);

  const arRows = window._receiptFromLedgerRows || [];
  const container = document.getElementById('receipt-from-ledger-content');
  const chks = container.querySelectorAll('.receipt-from-ledger-chk:checked');
  if (!chks.length) return;

  // 발행일이 없는 행이 있는데 fallback 날짜도 없으면 경고
  const needsFallback = Array.from(chks).some(c => !arRows[parseInt(c.dataset.idx)].date);
  if (needsFallback && !fallbackDate) { showToast('발행일이 없는 행이 있습니다. 입금일을 입력하세요.', 'error'); return; }

  const newRows = Array.from(chks).map(c => {
    const r = arRows[parseInt(c.dataset.idx)];
    const receiptDate = r.date || fallbackDate;
    return {
      receipt_date: receiptDate,
      revenue_month: r.revenue_month || (receiptDate ? receiptDate.slice(0, 7) + '-01' : null),
      partner_name: r.partner_name || '',
      amount: r._remaining,
      description: '',
    };
  });

  receiptApi.applyTransaction({ add: newRows });
  dirtyReceipt = true;
  _updateDirtyIndicators();
  refreshReceiptSummary();
  document.getElementById('modal-receipt-from-ledger').close();
  showToast(`${newRows.length}건의 입금 행이 추가되었습니다. 저장을 눌러주세요.`, 'info');
}

// ── 원장 필터 ─────────────────────────────────────────────────────

function _hasLedgerFilter() {
  const type = document.getElementById('filter-ledger-type').value;
  const start = document.getElementById('ledger-filter-start').value;
  const end = document.getElementById('ledger-filter-end').value;
  const status = document.getElementById('filter-ledger-status').value;
  const hideFuture = document.getElementById('ledger-hide-future').checked;
  const partnerFilter = document.getElementById('ledger-filter-partner').value.trim();
  return type !== '' || start !== '' || end !== '' || status !== '' || hideFuture || partnerFilter !== '';
}

function _passLedgerFilter(node) {
  const d = node.data;
  const type = document.getElementById('filter-ledger-type').value;
  if (type && d.type !== type) return false;

  const status = document.getElementById('filter-ledger-status').value;
  if (status && d.status !== status) return false;

  const start = document.getElementById('ledger-filter-start').value;
  const end = document.getElementById('ledger-filter-end').value;
  const ym = d.revenue_month ? d.revenue_month.slice(0, 7) : '';
  if (start && ym < start) return false;
  if (end && ym > end) return false;

  const hideFuture = document.getElementById('ledger-hide-future').checked;
  if (hideFuture && ym) {
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    if (ym > currentMonth) return false;
  }

  const partnerFilter = document.getElementById('ledger-filter-partner').value.trim().toLowerCase();
  if (partnerFilter && !(d.partner_name || '').toLowerCase().includes(partnerFilter)) return false;

  return true;
}

function applyLedgerFilter() {
  externalTypeFilter = document.getElementById('filter-ledger-type').value;
  ledgerApi.onFilterChanged();
  refreshLedgerSummary();
}

function resetLedgerFilter() {
  document.getElementById('filter-ledger-type').value = '';
  document.getElementById('filter-ledger-status').value = '';
  document.getElementById('ledger-filter-start').value = '';
  document.getElementById('ledger-filter-end').value = '';
  document.getElementById('ledger-hide-future').checked = false;
  document.getElementById('ledger-filter-partner').value = '';
  externalTypeFilter = '';
  ledgerApi.onFilterChanged();
  refreshLedgerSummary();
}

// ── 입금 필터 ─────────────────────────────────────────────────────

function _hasReceiptFilter() {
  const start = document.getElementById('receipt-filter-start').value;
  const end = document.getElementById('receipt-filter-end').value;
  const partnerFilter = document.getElementById('receipt-filter-partner').value.trim();
  return start !== '' || end !== '' || partnerFilter !== '';
}

function _passReceiptFilter(node) {
  const d = node.data;
  const start = document.getElementById('receipt-filter-start').value;
  const end = document.getElementById('receipt-filter-end').value;
  const ym = d.revenue_month ? d.revenue_month.slice(0, 7) : '';
  if (start && ym < start) return false;
  if (end && ym > end) return false;

  const partnerFilter = document.getElementById('receipt-filter-partner').value.trim().toLowerCase();
  if (partnerFilter && !(d.partner_name || '').toLowerCase().includes(partnerFilter)) return false;

  return true;
}

function applyReceiptFilter() {
  receiptApi.onFilterChanged();
  refreshReceiptSummary();
}

function resetReceiptFilter() {
  document.getElementById('receipt-filter-start').value = '';
  document.getElementById('receipt-filter-end').value = '';
  document.getElementById('receipt-filter-partner').value = '';
  receiptApi.onFilterChanged();
  refreshReceiptSummary();
}

// ── 배분 현황 그리드 ─────────────────────────────────────────────

function initReceiptMatchGrid(allocations) {
  const colDefs = [
    { field: 'revenue_month', headerName: '귀속월', width: 110,
      valueFormatter: p => p.value ? p.value.slice(0, 7) : '' },
    { field: 'partner_name', headerName: '거래처', width: 140 },
    { field: 'supply_amount', headerName: '매출액', type: 'numericColumn', width: 120,
      valueFormatter: p => p.value ? fmt(p.value) : '' },
    { field: 'matched_amount', headerName: '배분액', type: 'numericColumn', width: 120,
      editable: p => p.data.match_type === 'manual',
      valueFormatter: p => p.value ? fmt(p.value) : '',
      valueParser: p => Number(String(p.newValue).replace(/,/g, '')) || 0,
      cellClassRules: { 'cell-editable-manual': p => p.data.match_type === 'manual' },
    },
    { field: 'receipt_date', headerName: '입금일', width: 110 },
    { field: 'match_type', headerName: '구분', width: 80,
      valueFormatter: p => p.value === 'auto' ? '자동' : '수동' },
  ];

  const el = document.getElementById('grid-receipt-match');
  if (!el) return;
  el.innerHTML = '';
  receiptMatchApi = agGrid.createGrid(el, {
    columnDefs: colDefs,
    rowData: allocations,
    defaultColDef: { resizable: true, sortable: true },
    rowSelection: { mode: 'multiRow', checkboxes: true, headerCheckbox: true },
    enableCellTextSelection: true,
    ensureDomOrder: true,
    domLayout: allocations.length > 8 ? undefined : 'autoHeight',
    onCellValueChanged: onReceiptMatchCellChanged,
  });
  refreshReceiptMatchSummary(allocations);
}

async function onReceiptMatchCellChanged(e) {
  if (e.colDef.field !== 'matched_amount') return;
  const id = e.data.id;
  const newAmount = Number(e.newValue) || 0;
  if (newAmount <= 0) {
    showToast('배분 금액은 0보다 커야 합니다.', 'error');
    e.node.setDataValue('matched_amount', e.oldValue);
    return;
  }
  try {
    const res = await fetch(`/api/v1/receipt-matches/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ matched_amount: newAmount }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || '배분 수정 실패', 'error');
      e.node.setDataValue('matched_amount', e.oldValue);
      return;
    }
    showToast('배분 금액이 수정되었습니다.');
    await reloadLedger();
  } catch {
    showToast('배분 수정 중 오류 발생', 'error');
    e.node.setDataValue('matched_amount', e.oldValue);
  }
}

function refreshReceiptMatchSummary(allocations) {
  const bar = document.getElementById('receipt-match-summary-bar');
  if (!bar) return;
  const total = (allocations || []).reduce((s, a) => s + (a.matched_amount || 0), 0);
  const count = (allocations || []).length;
  bar.innerHTML =
    `<span class="summary-entry"><span class="label">배분 건수</span> <span class="value">${count}</span></span>` +
    `<span class="summary-entry"><span class="label">배분 합계</span> <span class="value summary-value-receipt">${fmt(total)}원</span></span>`;
}

async function autoMatch() {
  if (!contractId) return;
  if (!await showConfirmDialog('자동 배분(FIFO)을 재실행하시겠습니까? 기존 자동 배분이 재계산됩니다.', {
    title: '자동 배분 재실행',
    confirmText: '재실행',
  })) return;
  const res = await fetch(`/api/v1/contracts/${contractId}/receipt-matches/auto`, { method: 'POST' });
  if (!res.ok) { showToast('자동 배분 실패', 'error'); return; }
  showToast('자동 배분이 완료되었습니다.');
  await reloadLedger();
}

// ── 수동 배분 추가 모달 ──────────────────────────────────────
function openReceiptMatchModal() {
  const modal = document.getElementById('modal-add-receipt-match');
  if (!modal) return;

  // 입금 select 채우기
  const paySelect = document.getElementById('match-receipt-select');
  paySelect.innerHTML = '<option value="">-- 입금을 선택하세요 --</option>';
  (fullReceipts || []).forEach(p => {
    const label = `${p.receipt_date} / ${p.partner_name || '미지정'} / ${fmt(p.amount)}원`;
    paySelect.innerHTML += `<option value="${p.id}">${label}</option>`;
  });

  // 매출 라인 select 채우기 (확정 매출만)
  const txnLineSelect = document.getElementById('match-txn-line-select');
  txnLineSelect.innerHTML = '<option value="">-- 매출 라인을 선택하세요 --</option>';
  (fullLedger || []).filter(r => r.line_type === 'revenue' && r.status === '확정').forEach(r => {
    const month = (r.revenue_month || '').slice(0, 7);
    const label = `${month} / ${r.partner_name || '미지정'} / ${fmt(r.supply_amount)}원`;
    txnLineSelect.innerHTML += `<option value="${r.transaction_line_id || r.id}">${label}</option>`;
  });

  document.getElementById('match-alloc-amount').value = '';
  modal.showModal();
}

async function saveManualMatch() {
  const receiptId = Number(document.getElementById('match-receipt-select').value);
  const transactionLineId = Number(document.getElementById('match-txn-line-select').value);
  const amount = Number(document.getElementById('match-alloc-amount').value);

  if (!receiptId) { showToast('입금을 선택하세요.', 'error'); return; }
  if (!transactionLineId) { showToast('매출 라인을 선택하세요.', 'error'); return; }
  if (!amount || amount <= 0) { showToast('배분 금액을 입력하세요.', 'error'); return; }

  try {
    const res = await fetch(`/api/v1/contracts/${contractId}/receipt-matches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        receipt_id: receiptId,
        transaction_line_id: transactionLineId,
        matched_amount: amount,
        match_type: 'manual',
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || '수동 배분 생성 실패', 'error');
      return;
    }
    document.getElementById('modal-add-receipt-match').close();
    showToast('수동 배분이 추가되었습니다.');
    await reloadLedger();
  } catch {
    showToast('수동 배분 생성 중 오류 발생', 'error');
  }
}

async function deleteSelectedMatches() {
  if (!receiptMatchApi) return;
  const selected = receiptMatchApi.getSelectedRows();
  if (!selected.length) { showToast('삭제할 배분을 선택하세요.', 'error'); return; }
  if (!await showConfirmDialog(`선택한 ${selected.length}건의 배분을 삭제하시겠습니까?`, {
    title: '배분 삭제',
    confirmText: '삭제',
  })) return;

  let failed = 0;
  for (const row of selected) {
    try {
      const res = await fetch(`/api/v1/receipt-matches/${row.id}`, { method: 'DELETE' });
      if (!res.ok) failed++;
    } catch { failed++; }
  }
  if (failed) showToast(`${failed}건 삭제 실패`, 'error');
  else showToast('배분이 삭제되었습니다.');
  await reloadLedger();
}

// 버튼 이벤트
document.getElementById('btn-auto-match')?.addEventListener('click', autoMatch);
document.getElementById('btn-add-receipt-match')?.addEventListener('click', openReceiptMatchModal);
document.getElementById('btn-delete-receipt-match')?.addEventListener('click', deleteSelectedMatches);
document.getElementById('btn-match-save')?.addEventListener('click', saveManualMatch);
document.getElementById('btn-match-cancel')?.addEventListener('click', () => {
  document.getElementById('modal-add-receipt-match')?.close();
});
