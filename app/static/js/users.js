const COL_STATE_KEY = 'users_col_state_v2';

const PERMISSION_DEFS = [
  { key: 'admin', label: '관리자' },
  { key: 'common_manage', label: '공통관리' },
  { key: 'accounting_use', label: '영업사용' },
  { key: 'accounting_manage', label: '영업관리' },
  { key: 'infra_use', label: '프로젝트사용' },
  { key: 'infra_manage', label: '프로젝트관리' },
  { key: 'catalog_products_manage', label: '카탈로그제품관리' },
  { key: 'catalog_taxonomy_manage', label: '카탈로그기준관리' },
];

function getPermissionFlags(row) {
  const permissions = row?.role_permissions || {};
  const modules = permissions.modules || {};
  const scopes = permissions.scopes || {};
  const catalog = permissions.catalog || {};
  const legacyInfraManage = modules.infra === 'full' && !Object.prototype.hasOwnProperty.call(permissions, 'catalog');
  return {
    admin: !!permissions.admin,
    common_manage: !!(permissions.admin || permissions.common?.manage),
    accounting_use: modules.accounting === 'read' || modules.accounting === 'full',
    accounting_manage: permissions.admin || scopes.accounting === 'all',
    infra_use: modules.infra === 'read' || modules.infra === 'full',
    infra_manage: permissions.admin || modules.infra === 'full',
    catalog_products_manage: !!(permissions.admin || catalog.manage_products || legacyInfraManage),
    catalog_taxonomy_manage: !!(permissions.admin || catalog.manage_taxonomy || legacyInfraManage),
  };
}

function buildPermissionsPayload(prefix) {
  return {
    admin: document.getElementById(`${prefix}-perm-admin`).checked,
    common_manage: document.getElementById(`${prefix}-perm-common-manage`).checked,
    accounting_use: document.getElementById(`${prefix}-perm-accounting-use`).checked,
    accounting_manage: document.getElementById(`${prefix}-perm-accounting-manage`).checked,
    infra_use: document.getElementById(`${prefix}-perm-infra-use`).checked,
    infra_manage: document.getElementById(`${prefix}-perm-infra-manage`).checked,
    catalog_products_manage: document.getElementById(`${prefix}-perm-catalog-products-manage`).checked,
    catalog_taxonomy_manage: document.getElementById(`${prefix}-perm-catalog-taxonomy-manage`).checked,
  };
}

function fillPermissionCheckboxes(prefix, flags = {}) {
  PERMISSION_DEFS.forEach(({ key }) => {
    const el = document.getElementById(`${prefix}-perm-${key.replaceAll('_', '-')}`);
    if (el) el.checked = !!flags[key];
  });
}

function permissionTagsRenderer(params) {
  const tags = params.data?.permission_tags || [];
  if (!tags.length) return '—';
  return tags.map((tag) => `<span class="badge">${escapeHtml(tag)}</span>`).join(' ');
}

const columnDefs = [
  {
    headerName: '',
    width: 40,
    checkboxSelection: true,
    headerCheckboxSelection: true,
    pinned: 'left',
    sortable: false,
    resizable: false,
  },
  { field: 'login_id', headerName: '로그인 ID', width: 180, editable: true },
  { field: 'name', headerName: '이름', width: 130, editable: true },
  { field: 'department', headerName: '부서', width: 130, editable: true },
  { field: 'position', headerName: '직급', width: 110, editable: true },
  {
    field: 'permission_tags',
    headerName: '권한',
    width: 280,
    editable: false,
    cellRenderer: permissionTagsRenderer,
  },
  {
    field: 'is_active',
    headerName: '활성',
    width: 90,
    editable: true,
    cellEditor: 'agSelectCellEditor',
    cellEditorParams: { values: [true, false] },
    valueFormatter: (p) => (p.value ? '활성' : '비활성'),
    cellClass: (p) => (p.value ? 'cell-positive' : 'cell-negative'),
  },
];

const gridOptions = {
  columnDefs,
  rowData: [],
  rowSelection: 'multiple',
  suppressRowClickSelection: true,
  defaultColDef: { resizable: true, sortable: true },
  onCellValueChanged: (e) => {
    if (e.data.id) changedRows.set(e.data.id, e.data);
  },
  onColumnMoved: () => saveColState(gridApi, COL_STATE_KEY),
  onColumnResized: (e) => {
    if (e.finished) saveColState(gridApi, COL_STATE_KEY);
  },
};

let gridApi;
const changedRows = new Map();

document.addEventListener('DOMContentLoaded', async () => {
  const el = document.getElementById('grid-users');
  gridApi = agGrid.createGrid(el, gridOptions);
  restoreColState(gridApi, COL_STATE_KEY);
  await loadData();

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
  document.getElementById('btn-bulk-permissions').addEventListener('click', openBulkPermissionsModal);
  document.getElementById('btn-bulk-permissions-cancel').addEventListener('click', () => document.getElementById('modal-bulk-permissions').close());
  document.getElementById('btn-bulk-permissions-apply').addEventListener('click', applyBulkPermissions);
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
  document.getElementById('new-login-id').value = '';
  fillPermissionCheckboxes('new', {});
  document.getElementById('modal-add').showModal();
}

async function submitNew() {
  const name = document.getElementById('new-name').value.trim();
  if (!name) {
    showToast('이름을 입력하세요.', 'warning');
    return;
  }
  const body = {
    name,
    department: document.getElementById('new-department').value.trim() || null,
    position: document.getElementById('new-position').value.trim() || null,
    login_id: document.getElementById('new-login-id').value.trim() || null,
    permissions: buildPermissionsPayload('new'),
  };
  const res = await fetch('/api/v1/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (res.ok) {
    document.getElementById('modal-add').close();
    showToast('사용자가 등록되었습니다.');
    await loadData();
  } else {
    const err = await res.json().catch(() => ({}));
    showToast(err.detail || '등록에 실패했습니다.', 'error');
  }
}

function openBulkPermissionsModal() {
  const rows = gridApi.getSelectedRows();
  if (!rows.length) {
    showToast('권한을 변경할 사용자를 선택하세요.', 'warning');
    return;
  }
  fillPermissionCheckboxes('bulk', getPermissionFlags(rows[0]));
  document.getElementById('modal-bulk-permissions').showModal();
}

async function applyBulkPermissions() {
  const rows = gridApi.getSelectedRows();
  if (!rows.length) {
    showToast('권한을 변경할 사용자를 선택하세요.', 'warning');
    return;
  }
  const permissions = buildPermissionsPayload('bulk');
  const results = await Promise.all(rows.map((row) => (
    fetch(`/api/v1/users/${row.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ permissions }),
    }).then(async (res) => ({ res, data: res.ok ? await res.json() : await res.json().catch(() => ({})), row }))
  )));
  const failed = results.filter((item) => !item.res.ok);
  if (failed.length) {
    showToast(failed.map((item) => `${item.row.name}: ${item.data?.detail || '실패'}`).join(', '), 'error');
    return;
  }
  document.getElementById('modal-bulk-permissions').close();
  await loadData();
  showToast(`${rows.length}명 권한이 변경되었습니다.`);
}

async function importCsv() {
  const file = document.getElementById('import-csv-file').files[0];
  if (!file) {
    showToast('파일을 선택하세요.', 'warning');
    return;
  }
  const fd = new FormData();
  fd.append('file', file);
  const res = await fetch('/api/v1/users/import-csv', { method: 'POST', body: fd });
  if (res.ok) {
    const data = await res.json();
    document.getElementById('modal-import-csv').close();
    const parts = [`신규 ${data.created}명`];
    if (data.updated) parts.push(`업데이트 ${data.updated}명`);
    if (data.skipped) parts.push(`건너뜀 ${data.skipped}명`);
    showToast(`가져오기 완료: ${parts.join(', ')}`);
    await loadData();
  } else {
    showToast('가져오기에 실패했습니다.', 'error');
  }
}

async function resetPassword() {
  const rows = gridApi.getSelectedRows();
  if (rows.length === 0) {
    showToast('비밀번호를 초기화할 사용자를 선택하세요.', 'warning');
    return;
  }
  const names = rows.map((r) => r.name).join(', ');
  if (!await showConfirmDialog(`${names}의 비밀번호를 로그인 ID로 초기화하시겠습니까?`, {
    title: '비밀번호 초기화',
    confirmText: '초기화',
  })) return;
  const results = await Promise.all(
    rows.map((r) => fetch(`/api/v1/users/${r.id}/reset-password`, { method: 'POST' })
      .then(async (res) => ({ res, name: r.name, data: res.ok ? null : await res.json() }))),
  );
  const ok = results.filter((r) => r.res.ok);
  const failed = results.filter((r) => !r.res.ok);
  if (ok.length > 0) showToast(`${ok.length}명 비밀번호 초기화 완료`);
  if (failed.length > 0) showToast(failed.map((r) => `${r.name}: ${r.data?.detail || '실패'}`).join(', '), 'error');
}

async function deleteSelected() {
  const rows = gridApi.getSelectedRows();
  if (rows.length === 0) {
    showToast('삭제할 사용자를 선택하세요.', 'warning');
    return;
  }
  if (!await showConfirmDialog(`선택한 ${rows.length}명을 삭제하시겠습니까?`, {
    title: '사용자 삭제',
    confirmText: '삭제',
  })) return;
  const results = await Promise.all(
    rows.map((r) => fetch(`/api/v1/users/${r.id}`, { method: 'DELETE' }).then(async (res) => ({ res, data: res.ok ? null : await res.json() }))),
  );
  const denied = results.filter((r) => r.res.status === 403);
  const failed = results.filter((r) => !r.res.ok && r.res.status !== 403);
  rows.forEach((r) => changedRows.delete(r.id));
  await loadData();
  if (denied.length > 0) showToast(denied.map((r) => r.data?.detail).join(', '), 'error');
  if (failed.length > 0) showToast(`${failed.length}건 삭제에 실패했습니다.`, 'error');
}

async function saveChanges() {
  if (changedRows.size === 0) {
    showToast('변경된 내용이 없습니다.', 'info');
    return;
  }
  const count = changedRows.size;
  const promises = [...changedRows.values()].map((row) => (
    fetch(`/api/v1/users/${row.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: row.name,
        department: row.department,
        position: row.position,
        login_id: row.login_id,
        is_active: row.is_active,
      }),
    })
  ));
  const results = await Promise.all(promises);
  const denied = results.filter((r) => r.status === 403);
  const errored = results.filter((r) => !r.ok && r.status !== 403);
  if (denied.length > 0) {
    const messages = await Promise.all(denied.map((r) => r.json().then((d) => d.detail)));
    showToast(messages.join(', '), 'error');
  }
  if (errored.length > 0) {
    showToast('일부 저장에 실패했습니다.', 'error');
  } else {
    changedRows.clear();
    if (!denied.length) showToast(`${count}건 저장 완료`);
  }
  await loadData();
}
