const COL_STATE_KEY = 'contracts_col_state_v3';
const FILTER_STATE_KEY = 'contracts_filter_state';

let gridApi;
let allUsers = [];
let currentMe = null;
let columnDefs;

document.addEventListener('DOMContentLoaded', async () => {
  await loadTermLabels();
  applyTermLabels();

  columnDefs = buildContractPeriodColumns({ showOwner: true });
  const gridOptions = buildContractGridOptions({
    columnDefs,
    backPath: '/contracts',
    customerInputId: 'filter-customer-text',
    nameInputId: 'filter-name-text',
    onColChange: () => saveColState(gridApi, COL_STATE_KEY),
  });

  const me = await fetch('/api/v1/auth/me').then(r => r.ok ? r.json() : null);
  currentMe = me;
  await initDropdownFilters(me);
  loadCustomerDatalist();
  initEndCustomerPicker();

  const el = document.getElementById('grid-contracts');
  gridApi = agGrid.createGrid(el, gridOptions);

  // 저장된 필터 상태 복원
  restoreFilterState(FILTER_STATE_KEY);

  // "수행중" 토글 초기화
  const chkActive = document.getElementById('chk-active-period');
  if (chkActive) {
    toggleYearDropdowns(!chkActive.checked);
    chkActive.addEventListener('change', () => {
      toggleYearDropdowns(!chkActive.checked);
      loadData();
    });
  }

  // "내 사업만" 토글 초기화
  const chkMyContracts = document.getElementById('chk-my-contracts');
  chkMyContracts.addEventListener('change', () => {
    loadData();
  });

  loadData();
  initColChooser(gridApi, columnDefs, COL_STATE_KEY, () => saveColState(gridApi, COL_STATE_KEY));

  // 텍스트 필터: Enter 시 즉시 필터 적용
  initTextFilter('filter-customer-text', () => { loadData(); });
  initTextFilter('filter-name-text', () => { loadData(); });
  document.getElementById('btn-filter').addEventListener('click', () => { loadData(); });
  document.getElementById('btn-filter-reset').addEventListener('click', () => {
    resetContractFilters(loadData, FILTER_STATE_KEY);
  });
  const btnAdd = document.getElementById('btn-add');
  if (btnAdd) {
    if (me?.permissions?.can_admin_create_contract) {
      btnAdd.addEventListener('click', () => openContractModal());
    } else {
      btnAdd.classList.add('is-hidden');
    }
  }
  document.getElementById('btn-cancel').addEventListener('click', () => document.getElementById('modal-add').close());
  document.getElementById('btn-submit').addEventListener('click', () => submitContractModal(loadData));
  document.getElementById('btn-assign-owner').addEventListener('click', openAssignOwner);
  document.getElementById('btn-assign-cancel').addEventListener('click', () => document.getElementById('modal-assign-owner').close());
  document.getElementById('btn-assign-submit').addEventListener('click', submitAssignOwner);
  document.getElementById('btn-delete').addEventListener('click', () => deleteSelectedContracts(gridApi, loadData));
  setupImportModal();
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
  document.querySelectorAll('#drop-dept input:checked').forEach(cb => params.append('owner_department', cb.value));
  document.querySelectorAll('#drop-owner input:checked').forEach(cb => params.append('owner_id', cb.value));

  // "내 사업만" 토글 적용
  const chkMyContracts = document.getElementById('chk-my-contracts');
  if (chkMyContracts && chkMyContracts.checked && currentMe) {
    params.append('owner_id', currentMe.id);
  }

  saveFilterState(FILTER_STATE_KEY);
  const res = await fetch(`/api/v1/contract-periods?${params}`);
  const data = await res.json();
  gridApi.setGridOption('rowData', data);
  gridApi.onFilterChanged();
}

// ── 체크박스 드랍다운 필터 ──────────────────────────────────────
async function initDropdownFilters(me = null) {
  initYearDropdown();
  await populateContractTypeCheckboxes('#drop-type .chk-drop-menu');
  await populateContractTypeSelect('add-contract-type');

  // 부서 옵션 API에서 동적 로드
  const users = await fetch('/api/v1/users').then(r => r.json());
  allUsers = users;
  // 담당자 검색용 datalist 생성
  const dl = document.getElementById('user-list');
  dl.innerHTML = users.filter(u => u.is_active).map(u => {
    const label = u.department ? `${u.name} (${u.department})` : u.name;
    return `<option value="${label}">`;
  }).join('');
  const depts = [...new Set(users.map(u => u.department).filter(Boolean))].sort();
  const deptMenu = document.querySelector('#drop-dept .chk-drop-menu');
  deptMenu.innerHTML = '';
  const autoCheckDept = !me?.permissions?.can_manage_users ? me?.department : null;
  depts.forEach(dept => {
    const label = document.createElement('label');
    label.innerHTML = `<input type="checkbox" value="${dept}"> ${dept}`;
    if (autoCheckDept && dept === autoCheckDept) label.querySelector('input').checked = true;
    deptMenu.appendChild(label);
  });
  updateDropLabel(document.getElementById('drop-dept'));
  deptMenu.addEventListener('change', () => updateDropLabel(document.getElementById('drop-dept')));

  // 담당자 옵션 동적 생성
  const ownerMenu = document.querySelector('#drop-owner .chk-drop-menu');
  ownerMenu.innerHTML = '';
  users.filter(u => u.is_active).sort((a, b) => a.name.localeCompare(b.name)).forEach(u => {
    const label = document.createElement('label');
    label.innerHTML = `<input type="checkbox" value="${u.id}"> ${u.name}`;
    ownerMenu.appendChild(label);
  });
  updateDropLabel(document.getElementById('drop-owner'));
  ownerMenu.addEventListener('change', () => updateDropLabel(document.getElementById('drop-owner')));

  initDropdownToggles();
}

// ── Import 모달 ────────────────────────────────────────────────
function setupImportModal() {
  const modal = document.getElementById('modal-import');
  document.getElementById('btn-import').addEventListener('click', () => modal.showModal());
  document.getElementById('btn-import-close').addEventListener('click', () => modal.close());

  document.getElementById('btn-do-import-contracts').addEventListener('click', () => doImportContracts());
  document.getElementById('btn-do-import-forecast').addEventListener('click', () => doImportSheet('forecast'));
  document.getElementById('btn-do-import-txn-lines').addEventListener('click', () => doImportSheet('transaction-lines'));
}

function _setImportStatus(elId, html) {
  document.getElementById(elId).innerHTML = html;
}

async function doImportContracts() {
  const file = document.getElementById('import-file-contracts').files[0];
  if (!file) { alert('파일을 선택하세요.'); return; }
  const onDuplicate = document.getElementById('import-dup-contracts').value;
  _setImportStatus('import-status-contracts', '<span class="import-loading">처리 중...</span>');

  const fd = new FormData();
  fd.append('file', file);
  fd.append('on_duplicate', onDuplicate);
  const res = await fetch('/api/v1/excel/import', { method: 'POST', body: fd });
  if (res.ok) {
    const data = await res.json();
    _setImportStatus('import-status-contracts',
      `<span class="import-ok">✔ 완료: 신규 ${data.created}건${data.skipped ? ` / 건너뜀 ${data.skipped}건` : ''}${data.new_users?.length ? ` / 신규 담당자: ${data.new_users.join(', ')}` : ''}</span>`);
    await loadData();
  } else {
    const err = await res.json();
    const msgs = Array.isArray(err.detail) ? err.detail : [err.detail];
    _setImportStatus('import-status-contracts',
      `<span class="import-err">✗ 오류 ${msgs.length}건</span><ul class="import-err-list">${msgs.map(m => `<li>${m}</li>`).join('')}</ul>`);
  }
}

// ── 담당자 일괄 지정 ──────────────────────────────────────────
function openAssignOwner() {
  const rows = gridApi.getSelectedRows();
  if (rows.length === 0) { alert('담당자를 지정할 사업을 선택하세요.'); return; }
  const contractIds = [...new Set(rows.map(r => r.contract_id))];
  document.getElementById('assign-owner-info').textContent = `선택된 사업 ${contractIds.length}건에 담당자를 지정합니다.`;
  document.getElementById('assign-owner-input').value = '';
  document.getElementById('modal-assign-owner').showModal();
}

async function submitAssignOwner() {
  const rows = gridApi.getSelectedRows();
  const contractIds = [...new Set(rows.map(r => r.contract_id))];
  const text = document.getElementById('assign-owner-input').value.trim();
  let ownerUserId = null;

  if (text) {
    const user = allUsers.find(u => {
      const label = u.department ? `${u.name} (${u.department})` : u.name;
      return label === text || u.name === text;
    });
    if (!user) { alert('사용자를 찾을 수 없습니다. 목록에서 선택해 주세요.'); return; }
    ownerUserId = user.id;
  }

  const res = await fetch('/api/v1/contracts/bulk-assign-owner', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ contract_ids: contractIds, owner_user_id: ownerUserId }),
  });
  if (res.ok) {
    const data = await res.json();
    document.getElementById('modal-assign-owner').close();
    showToast(`${data.updated}건 담당자 ${text || '해제'} 완료`);
    await loadData();
  } else {
    alert('담당자 변경에 실패했습니다.');
  }
}

async function doImportSheet(type) {
  const fileEl = document.getElementById(`import-file-${type}`);
  const statusEl = `import-status-${type}`;
  const file = fileEl.files[0];
  if (!file) { alert('파일을 선택하세요.'); return; }
  _setImportStatus(statusEl, '<span class="import-loading">처리 중...</span>');

  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch(`/api/v1/excel/import/${type}`, { method: 'POST', body: fd });
  if (res.ok) {
    const data = await res.json();
    _setImportStatus(statusEl, `<span class="import-ok">✔ 완료: ${data.saved}건 저장</span>`);
    await loadData();
  } else {
    const err = await res.json();
    const msgs = Array.isArray(err.detail) ? err.detail : [err.detail];
    _setImportStatus(statusEl,
      `<span class="import-err">✗ 오류 ${msgs.length}건</span><ul class="import-err-list">${msgs.map(m => `<li>${m}</li>`).join('')}</ul>`);
  }
}
