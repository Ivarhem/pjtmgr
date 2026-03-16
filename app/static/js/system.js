let editingCode = null; // null = 추가 모드, 문자열 = 수정 모드

document.addEventListener('DOMContentLoaded', async () => {
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
  loadContractTypeTable();

  document.getElementById('btn-add-contract-type').addEventListener('click', () => openContractTypeModal());
  document.getElementById('btn-dt-cancel').addEventListener('click', () => document.getElementById('modal-contract-type').close());
  document.getElementById('btn-dt-submit').addEventListener('click', submitContractType);

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
