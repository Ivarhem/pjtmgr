const COL_STATE_KEY = 'users_col_state_v1';
const ROLE_LABELS = { user: '일반', admin: '관리자' };

const columnDefs = [
  { headerName: '', width: 40, checkboxSelection: true, headerCheckboxSelection: true,
    pinned: 'left', sortable: false, resizable: false },
  { field: 'login_id', headerName: '로그인 ID', width: 150, editable: true },
  { field: 'name', headerName: '이름', width: 120, editable: true },
  { field: 'department', headerName: '부서', width: 120, editable: true },
  { field: 'position', headerName: '직급', width: 100, editable: true },
  { field: 'role', headerName: '역할', width: 90,
    editable: true,
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values: ['user', 'admin'] },
    valueFormatter: p => ROLE_LABELS[p.value] || p.value },
  { field: 'is_active', headerName: '활성', width: 70,
    editable: true,
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values: [true, false] },
    valueFormatter: p => p.value ? '활성' : '비활성',
    cellClass: p => p.value ? 'cell-positive' : 'cell-negative' },
];

const gridOptions = {
  columnDefs,
  rowData: [],
  rowSelection: 'multiple',
  suppressRowClickSelection: true,
  defaultColDef: { resizable: true, sortable: true },
  onCellValueChanged: e => {
    if (e.data.id) changedRows.set(e.data.id, e.data);
  },
  onColumnMoved: () => saveColState(gridApi, COL_STATE_KEY),
  onColumnResized: (e) => { if (e.finished) saveColState(gridApi, COL_STATE_KEY); },
};

let gridApi;
const changedRows = new Map();

document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('grid-users');
  gridApi = agGrid.createGrid(el, gridOptions);
  restoreColState(gridApi, COL_STATE_KEY);
  loadData();

  document.getElementById('btn-import-csv').addEventListener('click', () => {
    document.getElementById('import-csv-file').value = '';
    document.getElementById('modal-import-csv').showModal();
  });
  document.getElementById('btn-import-csv-cancel').addEventListener('click', () => document.getElementById('modal-import-csv').close());
  document.getElementById('btn-import-csv-confirm').addEventListener('click', importCsv);
  document.getElementById('btn-add').addEventListener('click', openAddModal);
  document.getElementById('btn-cancel').addEventListener('click', () => document.getElementById('modal-add').close());
  document.getElementById('btn-submit').addEventListener('click', submitNew);
  document.getElementById('btn-save').addEventListener('click', saveChanges);
  document.getElementById('btn-reset-pw').addEventListener('click', resetPassword);
  document.getElementById('btn-delete').addEventListener('click', deleteSelected);
});

async function loadData() {
  const res = await fetch('/api/v1/users');
  const data = await res.json();
  gridApi.setGridOption('rowData', data);
  changedRows.clear();
}

function openAddModal() {
  document.getElementById('new-name').value = '';
  document.getElementById('new-department').value = '';
  document.getElementById('new-position').value = '';
  document.getElementById('new-role').value = 'user';
  document.getElementById('new-login-id').value = '';
  document.getElementById('modal-add').showModal();
}

async function submitNew() {
  const name = document.getElementById('new-name').value.trim();
  if (!name) { alert('이름을 입력하세요.'); return; }
  const body = {
    name,
    department: document.getElementById('new-department').value.trim() || null,
    position: document.getElementById('new-position').value.trim() || null,
    role: document.getElementById('new-role').value,
    login_id: document.getElementById('new-login-id').value.trim() || null,
  };
  const res = await fetch('/api/v1/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    document.getElementById('modal-add').close();
    await loadData();
  } else {
    alert('등록에 실패했습니다.');
  }
}

async function importCsv() {
  const file = document.getElementById('import-csv-file').files[0];
  if (!file) { alert('파일을 선택하세요.'); return; }
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/v1/users/import-csv', { method: 'POST', body: fd });
  if (res.ok) {
    const data = await res.json();
    document.getElementById('modal-import-csv').close();
    const parts = [`신규 ${data.created}명`];
    if (data.updated) parts.push(`업데이트 ${data.updated}명`);
    if (data.skipped) parts.push(`건너뜀 ${data.skipped}명`);
    alert(`가져오기 완료: ${parts.join(', ')}`);;
    await loadData();
  } else {
    alert('가져오기에 실패했습니다.');
  }
}

async function resetPassword() {
  const rows = gridApi.getSelectedRows();
  if (rows.length === 0) { alert('비밀번호를 초기화할 사용자를 선택하세요.'); return; }
  const names = rows.map(r => r.name).join(', ');
  if (!confirm(`${names}의 비밀번호를 로그인 ID로 초기화하시겠습니까?`)) return;
  const results = await Promise.all(
    rows.map(r => fetch(`/api/v1/users/${r.id}/reset-password`, { method: 'POST' })
      .then(async res => ({ res, name: r.name, data: res.ok ? null : await res.json() })))
  );
  const ok = results.filter(r => r.res.ok);
  const failed = results.filter(r => !r.res.ok);
  if (ok.length > 0) alert(`${ok.length}명 비밀번호 초기화 완료`);
  if (failed.length > 0) alert(failed.map(r => `${r.name}: ${r.data?.detail || '실패'}`).join('\n'));
}

async function deleteSelected() {
  const rows = gridApi.getSelectedRows();
  if (rows.length === 0) { alert('삭제할 사용자를 선택하세요.'); return; }
  if (!confirm(`선택한 ${rows.length}명을 삭제하시겠습니까?`)) return;
  const results = await Promise.all(
    rows.map(r => fetch(`/api/v1/users/${r.id}`, { method: 'DELETE' }).then(async res => ({ res, data: res.ok ? null : await res.json() })))
  );
  const denied = results.filter(r => r.res.status === 403);
  const failed = results.filter(r => !r.res.ok && r.res.status !== 403);
  rows.forEach(r => changedRows.delete(r.id));
  await loadData();
  if (denied.length > 0) alert(denied.map(r => r.data?.detail).join('\n'));
  if (failed.length > 0) alert(`${failed.length}건 삭제에 실패했습니다.`);
}

async function saveChanges() {
  if (changedRows.size === 0) { alert('변경된 내용이 없습니다.'); return; }
  const count = changedRows.size;
  const promises = [...changedRows.values()].map(row =>
    fetch(`/api/v1/users/${row.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: row.name,
        department: row.department,
        position: row.position,
        role: row.role,
        login_id: row.login_id,
        is_active: row.is_active,
      }),
    })
  );
  const results = await Promise.all(promises);
  const failed = results.filter(r => !r.ok).length;
  const denied = results.filter(r => r.status === 403);
  const errored = results.filter(r => !r.ok && r.status !== 403);
  if (denied.length > 0) {
    const messages = await Promise.all(denied.map(r => r.json().then(d => d.detail)));
    alert(messages.join('\n'));
  }
  if (errored.length > 0) alert('일부 저장에 실패했습니다.');
  else { changedRows.clear(); if (!denied.length) alert(`${count}건 저장 완료`); }
}
