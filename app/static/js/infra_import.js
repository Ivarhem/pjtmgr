/**
 * 자산 Excel Import — 3단계 위저드
 */
(function () {
  'use strict';

  let _previewGridApi = null;
  let _selectedFile = null;

  // ── 초기화 ──

  document.addEventListener('DOMContentLoaded', async () => {
    await loadProjects();
    bindEvents();
  });

  async function loadProjects() {
    try {
      const projects = await apiFetch('/api/v1/projects');
      const sel = document.getElementById('import-project');
      projects.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.project_code + ' \u2014 ' + p.project_name;
        sel.appendChild(opt);
      });
    } catch (e) {
      showToast('프로젝트 목록 로드 실패: ' + e.message, 'error');
    }
  }

  function bindEvents() {
    document.getElementById('btn-preview').addEventListener('click', doPreview);
    document.getElementById('btn-confirm').addEventListener('click', doConfirm);
    document.getElementById('btn-back-upload').addEventListener('click', () => goStep(1));
    document.getElementById('btn-another').addEventListener('click', resetWizard);
    document.getElementById('import-file').addEventListener('change', (e) => {
      _selectedFile = e.target.files[0] || null;
    });
  }

  // ── 단계 전환 ──

  function goStep(n) {
    document.querySelectorAll('.import-panel').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.import-step').forEach(el => el.classList.remove('active', 'done'));

    const panels = ['step-upload', 'step-preview', 'step-result'];
    document.getElementById(panels[n - 1]).classList.remove('hidden');

    document.querySelectorAll('.import-step').forEach(el => {
      const step = parseInt(el.dataset.step);
      if (step < n) el.classList.add('done');
      if (step === n) el.classList.add('active');
    });
  }

  function resetWizard() {
    document.getElementById('import-file').value = '';
    _selectedFile = null;
    goStep(1);
  }

  // ── Step 1 → 2: 미리보기 ──

  async function doPreview() {
    const projectId = document.getElementById('import-project').value;
    if (!projectId) { showToast('프로젝트를 선택하세요.', 'warning'); return; }
    if (!_selectedFile) { showToast('파일을 선택하세요.', 'warning'); return; }

    const fd = new FormData();
    fd.append('file', _selectedFile);
    fd.append('partner_id', getCtxPartnerId());

    const btn = document.getElementById('btn-preview');
    btn.disabled = true;
    btn.textContent = '파싱 중...';

    try {
      const res = await fetch('/api/v1/infra-excel/import/preview', { method: 'POST', body: fd });
      const data = await res.json();

      if (!res.ok) {
        showToast(data.detail || '파싱 실패', 'error');
        return;
      }

      renderPreview(data);
      goStep(2);
    } catch (e) {
      showToast('파싱 실패: ' + e.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '미리보기';
    }
  }

  function _buildMsgList(title, messages) {
    const container = document.createElement('div');
    const strong = document.createElement('strong');
    strong.textContent = title;
    container.appendChild(strong);
    const ul = document.createElement('ul');
    messages.forEach(msg => {
      const li = document.createElement('li');
      li.textContent = msg;
      ul.appendChild(li);
    });
    container.appendChild(ul);
    return container;
  }

  function renderPreview(data) {
    // Summary
    document.getElementById('preview-summary').textContent =
      '전체 ' + data.total + '건 | 유효 ' + data.valid_count + '건';

    // Warnings
    const warnBox = document.getElementById('preview-warnings');
    warnBox.textContent = '';
    if (data.warnings && data.warnings.length > 0) {
      warnBox.appendChild(_buildMsgList('경고', data.warnings));
      warnBox.classList.remove('hidden');
    } else {
      warnBox.classList.add('hidden');
    }

    // Errors
    const errBox = document.getElementById('preview-errors');
    errBox.textContent = '';
    if (data.errors && data.errors.length > 0) {
      errBox.appendChild(_buildMsgList('오류', data.errors));
      errBox.classList.remove('hidden');
    } else {
      errBox.classList.add('hidden');
    }

    // Confirm button
    document.getElementById('btn-confirm').disabled = !data.valid;

    // AG Grid
    const colDefs = [
      { field: 'row_num', headerName: '행', width: 70, pinned: 'left' },
      { field: 'asset_name', headerName: '자산명', width: 160 },
      { field: 'asset_type', headerName: '유형', width: 100 },
      { field: 'hostname', headerName: 'Hostname', width: 140 },
      { field: 'vendor', headerName: '제조사', width: 120 },
      { field: 'model', headerName: '모델', width: 120 },
      { field: 'serial_no', headerName: 'Serial No.', width: 140 },
      { field: 'service_ip', headerName: 'Service IP', width: 130 },
      { field: 'mgmt_ip', headerName: 'MGMT IP', width: 130 },
      { field: 'status', headerName: '상태', width: 90 },
      {
        field: 'errors', headerName: '오류', width: 200,
        cellRenderer: p => {
          if (!p.value || p.value.length === 0) return '';
          const span = document.createElement('span');
          span.className = 'infra-text-danger';
          span.textContent = p.value.join(', ');
          return span;
        },
      },
    ];

    const gridDiv = document.getElementById('grid-preview');
    if (_previewGridApi) {
      _previewGridApi.setGridOption('rowData', data.rows || []);
      _previewGridApi.setGridOption('columnDefs', colDefs);
    } else {
      _previewGridApi = agGrid.createGrid(gridDiv, {
        columnDefs: colDefs,
        rowData: data.rows || [],
        defaultColDef: { sortable: true, resizable: true, filter: true },
        domLayout: 'normal',
        rowClassRules: {
          'infra-grid-row-error': params => Boolean(
            params.data && params.data.errors && params.data.errors.length > 0
          ),
        },
      });
    }
  }

  // ── Step 2 → 3: Import 실행 ──

  async function doConfirm() {
    const projectId = document.getElementById('import-project').value;
    const onDuplicate = document.getElementById('import-duplicate').value;

    if (!_selectedFile) { showToast('파일이 없습니다. 처음부터 다시 시도하세요.', 'error'); return; }

    const fd = new FormData();
    fd.append('file', _selectedFile);
    fd.append('partner_id', getCtxPartnerId());
    fd.append('on_duplicate', onDuplicate);

    const btn = document.getElementById('btn-confirm');
    btn.disabled = true;
    btn.textContent = 'Import 중...';

    try {
      const res = await fetch('/api/v1/infra-excel/import/confirm', { method: 'POST', body: fd });
      const data = await res.json();

      if (!res.ok) {
        showToast(data.detail || 'Import 실패', 'error');
        btn.disabled = false;
        btn.textContent = 'Import 실행';
        return;
      }

      renderResult(data, projectId);
      goStep(3);
    } catch (e) {
      showToast('Import 실패: ' + e.message, 'error');
      btn.disabled = false;
      btn.textContent = 'Import 실행';
    }
  }

  function renderResult(data, projectId) {
    const summary = document.getElementById('result-summary');
    // Clear previous content
    summary.textContent = '';

    const wrapper = document.createElement('div');
    wrapper.className = 'infra-result-stats';

    const card1 = document.createElement('div');
    card1.className = 'stat-card';
    const val1 = document.createElement('div');
    val1.className = 'stat-value';
    val1.textContent = data.created;
    const lbl1 = document.createElement('div');
    lbl1.className = 'stat-label';
    lbl1.textContent = '생성';
    card1.appendChild(val1);
    card1.appendChild(lbl1);

    const card2 = document.createElement('div');
    card2.className = 'stat-card';
    const val2 = document.createElement('div');
    val2.className = 'stat-value';
    val2.textContent = data.skipped;
    const lbl2 = document.createElement('div');
    lbl2.className = 'stat-label';
    lbl2.textContent = '건너뜀';
    card2.appendChild(val2);
    card2.appendChild(lbl2);

    wrapper.appendChild(card1);
    wrapper.appendChild(card2);
    summary.appendChild(wrapper);

    document.getElementById('btn-go-project').href = '/projects/' + projectId;
  }
})();
