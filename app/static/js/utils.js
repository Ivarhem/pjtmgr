// ── 용어 라벨 (TermConfig) ────────────────────────────────────────

let _termLabelsCache = null;

/** TermConfig 라벨을 API에서 로드하여 캐시 */
async function loadTermLabels() {
  if (!_termLabelsCache) {
    try {
      const res = await fetch('/api/v1/term-configs/labels');
      _termLabelsCache = res.ok ? await res.json() : {};
    } catch {
      _termLabelsCache = {};
    }
  }
  return _termLabelsCache;
}

/** 캐시된 TermConfig 라벨 반환 (동기). loadTermLabels() 호출 후 사용.
 * @param {string} termKey - TermConfig term_key
 * @param {string} [fallback] - 캐시 미스 시 반환값
 */
function getTermLabel(termKey, fallback) {
  return _termLabelsCache?.[termKey] ?? fallback ?? termKey;
}

/** data-term-key 속성이 있는 DOM 요소에 라벨 적용 */
function applyTermLabels() {
  if (!_termLabelsCache) return;
  document.querySelectorAll('[data-term-key]').forEach(el => {
    const key = el.dataset.termKey;
    const prefix = el.dataset.termPrefix || '';
    const suffix = el.dataset.termSuffix || '';
    const label = _termLabelsCache[key];
    if (!label) return;
    const fullLabel = prefix + label + suffix;
    // data-label 속성 업데이트 (드롭다운 버튼용)
    if (el.dataset.label !== undefined) {
      el.dataset.label = fullLabel;
      // 선택된 항목이 없으면 텍스트도 업데이트
      const drop = el.closest('.chk-drop');
      if (drop) {
        const checked = drop.querySelectorAll('input:checked');
        if (checked.length === 0) el.textContent = fullLabel;
      } else {
        el.textContent = fullLabel;
      }
    } else {
      el.textContent = fullLabel;
    }
  });
}

// ── 공통 유틸리티 ────────────────────────────────────────────────

/** API 호출 래퍼 — JSON 요청/응답 처리 및 에러 핸들링
 * @param {string} url - API 엔드포인트 경로
 * @param {Object} [opts] - fetch 옵션
 * @param {string} [opts.method] - HTTP 메서드 (기본 GET)
 * @param {Object} [opts.body] - 요청 바디 (자동 JSON.stringify)
 * @returns {Promise<any>} 응답 JSON
 */
async function apiFetch(url, opts = {}) {
  const fetchOpts = { method: opts.method || 'GET', headers: {} };
  if (opts.body) {
    fetchOpts.headers['Content-Type'] = 'application/json';
    fetchOpts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(url, fetchOpts);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `요청 실패 (${res.status})`);
  }
  if (res.status === 204) return null;
  return res.json();
}

/** 날짜 문자열 포맷 (YYYY-MM-DD)
 * @param {string|null} v - ISO 날짜 문자열
 * @returns {string} 포맷된 날짜 또는 빈 문자열
 */
function fmtDate(v) {
  if (!v) return '';
  return v.slice(0, 10);
}

/** 삭제 확인 대화상자
 * @param {string} message - 확인 메시지
 * @param {Function} onConfirm - 확인 시 실행할 콜백
 */
function confirmDelete(message, onConfirm) {
  if (confirm(message)) onConfirm();
}

/** 토스트 알림 표시
 * @param {string} message - 표시할 메시지
 * @param {'success'|'error'|'info'|'warning'} type - 토스트 유형
 * @param {number} duration - 표시 시간(ms), 기본 3000
 */
function showToast(message, type = 'success', duration = 3000) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  if (type === 'error') {
    container.prepend(toast);
  } else {
    container.appendChild(toast);
  }
  setTimeout(() => {
    toast.classList.add('toast-out');
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

/** AG Grid valueFormatter용: p.value를 한국어 숫자 포맷 */
const fmtNumber = (p) => p.value != null ? Number(p.value).toLocaleString('ko-KR') : '';

/** 일반 숫자 포맷 (null → '-') */
const fmt = (n) => n != null ? Number(n).toLocaleString('ko-KR') : '-';

/** 숫자를 한국어 금액 단위(억, 만, 원)로 포맷합니다.
 * @param {number | null | undefined} n - 포맷할 숫자
 * @returns {string | null} 포맷된 문자열 (e.g., '12억 3456만 7890원') 또는 null
 */
function fmtKoreanCurrency(n) {
  if (n == null || isNaN(n)) {
    return null;
  }
  if (n === 0) {
    return '0원';
  }

  const isNegative = n < 0;
  const num = Math.abs(Number(n));
  
  const eok = Math.floor(num / 100000000);
  const man = Math.floor((num % 100000000) / 10000);
  const won = num % 10000;

  let result = '';
  if (eok > 0) {
    result += `${eok}억 `;
  }
  if (man > 0) {
    result += `${man}만 `;
  }
  
  if (won > 0) {
      result += `${won}`;
  } else {
      result = result.trim();
  }

  result = result.trim();
  if (result) {
      result += '원';
  } else {
      return '0원';
  }

  return (isNegative ? '-' : '') + result;
}

/** 퍼센트 포맷 (0.7 → '70.0%') */
const fmtPct = (n) => n != null && !isNaN(n) ? (n * 100).toFixed(1) + '%' : '-';

function isElementHidden(el) {
  return !el || el.classList.contains('is-hidden');
}

function setElementHidden(el, hidden) {
  if (!el) return;
  el.classList.toggle('is-hidden', hidden);
}

function setElementDisabledState(el, disabled) {
  if (!el) return;
  el.classList.toggle('is-disabled', disabled);
  const btn = el.querySelector?.('.chk-drop-btn');
  if (btn) btn.disabled = disabled;
}

// ── 체크박스 드랍다운 ────────────────────────────────────────────

function updateDropLabel(drop) {
  const btn = drop.querySelector('.chk-drop-btn');
  const checked = [...drop.querySelectorAll('input:checked')];
  const base = btn.dataset.label;
  if (checked.length === 0) btn.textContent = base;
  else if (checked.length === 1) btn.textContent = checked[0].parentElement.textContent.trim();
  else btn.textContent = `${base} (${checked.length})`;
}

function initDropdownToggles() {
  document.querySelectorAll('.chk-drop').forEach(drop => {
    const btn = drop.querySelector('.chk-drop-btn');
    const menu = drop.querySelector('.chk-drop-menu');

    btn.addEventListener('click', e => {
      e.stopPropagation();
      const isOpen = !isElementHidden(menu);
      document.querySelectorAll('.chk-drop-menu').forEach(m => setElementHidden(m, true));
      document.querySelectorAll('.chk-drop-btn').forEach(b => b.classList.remove('active'));
      if (!isOpen) { setElementHidden(menu, false); btn.classList.add('active'); }
    });

    menu.addEventListener('click', e => e.stopPropagation());
    menu.addEventListener('change', () => updateDropLabel(drop));
  });

  document.addEventListener('click', () => {
    document.querySelectorAll('.chk-drop-menu').forEach(m => setElementHidden(m, true));
    document.querySelectorAll('.chk-drop-btn').forEach(b => b.classList.remove('active'));
  });
}

/** 연도 + 기간 드롭다운 초기화. 연도(달력)는 현재 연도 기본 선택. */
function initYearDropdown() {
  const curYear = new Date().getFullYear();

  // 연도 (달력 연도) — 기본 현재 연도 선택
  const calMenu = document.querySelector('#drop-calendar-year .chk-drop-menu');
  if (calMenu) {
    calMenu.innerHTML = '';
    for (let y = curYear - 1; y <= curYear + 2; y++) {
      const label = document.createElement('label');
      const checked = y === curYear ? ' checked' : '';
      label.innerHTML = `<input type="checkbox" value="${y}"${checked}> ${y}`;
      calMenu.appendChild(label);
    }
    updateDropLabel(document.getElementById('drop-calendar-year'));
    calMenu.addEventListener('change', () => updateDropLabel(document.getElementById('drop-calendar-year')));
  }

  // 기간 (Period 귀속 연도)
  const periodMenu = document.querySelector('#drop-period .chk-drop-menu');
  if (periodMenu) {
    periodMenu.innerHTML = '';
    for (let y = curYear - 1; y <= curYear + 2; y++) {
      const label = document.createElement('label');
      label.innerHTML = `<input type="checkbox" value="${y}"> Y${String(y).slice(2)}`;
      periodMenu.appendChild(label);
    }
    updateDropLabel(document.getElementById('drop-period'));
    periodMenu.addEventListener('change', () => updateDropLabel(document.getElementById('drop-period')));
  }
}

/** "수행중" 토글에 따라 귀속연도/사업기간 드롭다운 비활성화/활성화 */
function toggleYearDropdowns(enabled) {
  ['drop-period', 'drop-calendar-year'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    setElementDisabledState(el, !enabled);
  });
}

// ── 사업유형 동적 로드 ──────────────────────────────────────────────

/** 사업유형 목록을 API에서 로드하여 캐시. */
let _contractTypesCache = null;
async function loadContractTypes() {
  if (!_contractTypesCache) {
    const res = await fetch('/api/v1/contract-types');
    _contractTypesCache = res.ok ? await res.json() : [];
  }
  return _contractTypesCache;
}

/** 체크박스 드롭다운 메뉴에 사업유형 옵션을 동적 생성. */
async function populateContractTypeCheckboxes(menuSelector) {
  const menu = document.querySelector(menuSelector);
  if (!menu) return;
  const types = await loadContractTypes();
  menu.innerHTML = '';
  types.forEach(dt => {
    const label = document.createElement('label');
    label.innerHTML = `<input type="checkbox" value="${dt.code}"> ${dt.label}`;
    menu.appendChild(label);
  });
  const drop = menu.closest('.chk-drop');
  if (drop) {
    updateDropLabel(drop);
    menu.addEventListener('change', () => updateDropLabel(drop));
  }
}

/** select 요소에 사업유형 옵션을 동적 생성. */
async function populateContractTypeSelect(selectId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const types = await loadContractTypes();
  sel.innerHTML = '';
  types.forEach(dt => {
    const opt = document.createElement('option');
    opt.value = dt.code;
    opt.textContent = dt.label;
    sel.appendChild(opt);
  });
}

// ── 태그 입력 & 필터 ────────────────────────────────────────────────

function initTagInput(inputId, listId, tagArray, onChangeFn) {
  const input = document.getElementById(inputId);
  const list = document.getElementById(listId);
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const val = input.value.trim();
      if (val && !tagArray.includes(val)) {
        tagArray.push(val);
        renderTagChips(list, tagArray, onChangeFn);
        if (onChangeFn) onChangeFn();
      }
      input.value = '';
    }
    if (e.key === 'Backspace' && input.value === '' && tagArray.length > 0) {
      tagArray.pop();
      renderTagChips(list, tagArray, onChangeFn);
      if (onChangeFn) onChangeFn();
    }
  });
}

function renderTagChips(listEl, tagArray, onChangeFn) {
  listEl.innerHTML = tagArray.map((t, i) =>
    `<span class="tag-chip">${t}<span class="tag-chip-x" data-idx="${i}">&times;</span></span>`
  ).join('');
  listEl.querySelectorAll('.tag-chip-x').forEach(x => {
    x.addEventListener('click', () => {
      tagArray.splice(parseInt(x.dataset.idx), 1);
      renderTagChips(listEl, tagArray, onChangeFn);
      if (onChangeFn) onChangeFn();
    });
  });
}

/** 텍스트 필터 입력 초기화 — Enter 시 콜백 실행 */
function initTextFilter(inputId, onEnterFn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') {
      e.preventDefault();
      onEnterFn();
    }
  });
}

// ── 고객사/프로젝트 컨텍스트 셀렉터 ──────────────────────────────────

let _ctxPartnerId = null;
let _ctxProjectId = null;

/** 현재 선택된 고객사 ID */
function getCtxPartnerId() { return _ctxPartnerId; }
/** 현재 선택된 프로젝트 ID (null = 전체) */
function getCtxProjectId() { return _ctxProjectId; }

/** topbar 고객사/프로젝트 셀렉터 초기화 (자동완성 방식) */
async function initContextSelectors() {
  const custInput = document.getElementById('ctx-partner');
  const custDrop = document.getElementById('ctx-partner-dropdown');
  const projDisplay = document.getElementById('ctx-project-display');
  const projText = document.getElementById('ctx-project-text');
  const projClear = document.getElementById('ctx-project-clear');
  if (!custInput) return;

  let allPartners = [];
  let allProjects = [];

  // ── 드롭다운 헬퍼 (DOM API only, no innerHTML) ──
  function renderDropdown(dropdown, items, onSelect, onNew) {
    dropdown.textContent = '';
    items.forEach(item => {
      const div = document.createElement('div');
      div.className = 'ctx-option';
      div.dataset.id = item.id || '';
      if (item.code) {
        const codeSpan = document.createElement('span');
        codeSpan.className = 'ctx-option-code';
        codeSpan.textContent = item.code;
        div.appendChild(codeSpan);
        div.appendChild(document.createTextNode(item.label));
      } else {
        div.textContent = item.label;
      }
      div.addEventListener('mousedown', (e) => {
        e.preventDefault();
        onSelect(item);
        setElementHidden(dropdown, true);
      });
      dropdown.appendChild(div);
    });
    if (onNew) {
      const newDiv = document.createElement('div');
      newDiv.className = 'ctx-option-new';
      newDiv.textContent = '+ 신규 등록';
      newDiv.addEventListener('mousedown', (e) => {
        e.preventDefault();
        setElementHidden(dropdown, true);
        onNew();
      });
      dropdown.appendChild(newDiv);
    }
    setElementHidden(dropdown, false);
  }

  function filterAndShow(input, dropdown, allItems, onSelect, onNew) {
    const kw = input.value.trim().toLowerCase();
    const filtered = kw
      ? allItems.filter(i => i.label.toLowerCase().includes(kw) || (i.code && i.code.toLowerCase().includes(kw)))
      : allItems;
    renderDropdown(dropdown, filtered.slice(0, 30), onSelect, onNew);
  }

  // ── 고객사 ──
  allPartners = (await apiFetch('/api/v1/partners')).map(c => ({
    id: c.id, code: c.partner_code, label: c.name,
  }));

  function selectPartner(item) {
    _ctxPartnerId = item ? item.id : null;
    custInput.value = item ? item.label : '';
    custInput.title = item ? (item.code + ' ' + item.label) : '';
    _ctxProjectId = null;
    _updateProjectDisplay(null);
    // Pin 저장
    apiFetch('/api/v1/preferences/infra.pinned_partner_id', {
      method: 'PATCH', body: { value: item ? String(item.id) : '' },
    }).catch(() => {});
    localStorage.removeItem('infra.last_period_id');
    loadPeriods(item ? item.id : null);
    window.dispatchEvent(new CustomEvent('ctx-changed', { detail: { partnerId: _ctxPartnerId, projectId: null } }));
  }

  // ── 고객사 신규등록 모달 ──
  const custModal = document.getElementById('ctx-modal-partner');
  function openNewPartnerModal() {
    const nameInput = document.getElementById('ctx-new-partner-name');
    nameInput.value = custInput.value.trim();
    custModal.showModal();
    nameInput.focus();
  }
  if (custModal) {
    document.getElementById('ctx-btn-cust-cancel').addEventListener('click', () => custModal.close());
    document.getElementById('ctx-btn-cust-submit').addEventListener('click', async () => {
      const name = document.getElementById('ctx-new-partner-name').value.trim();
      if (!name) { showToast('고객사명을 입력하세요.', 'warning'); return; }
      try {
        const created = await apiFetch('/api/v1/partners', { method: 'POST', body: { name } });
        custModal.close();
        const newItem = { id: created.id, code: created.partner_code, label: created.name };
        allPartners.push(newItem);
        selectPartner(newItem);
        showToast('"' + name + '" 고객사가 등록되었습니다.');
      } catch (err) { showToast(err.message || '등록에 실패했습니다.', 'error'); }
    });
  }

  custInput.addEventListener('focus', () => filterAndShow(custInput, custDrop, allPartners, selectPartner, openNewPartnerModal));
  custInput.addEventListener('input', () => filterAndShow(custInput, custDrop, allPartners, selectPartner, openNewPartnerModal));
  custInput.addEventListener('blur', () => setTimeout(() => setElementHidden(custDrop, true), 150));
  custInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setElementHidden(custDrop, true);
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const first = custDrop.querySelector('.ctx-option');
      if (first) first.focus();
    }
  });

  // ── 사업기간 (Period) ──
  async function loadPeriods(partnerId) {
    allProjects = [];
    if (!partnerId) return;
    try {
      const periods = await apiFetch('/api/v1/contract-periods?partner_id=' + partnerId);
      allProjects = periods.map(p => ({
        id: p.id, code: p.contract_code || '', label: p.contract_name + ' (' + p.period_label + ')',
      }));
      // 저장된 Period 복원
      const savedPeriodId = localStorage.getItem('infra.last_period_id');
      if (savedPeriodId) {
        const saved = allProjects.find(p => String(p.id) === savedPeriodId);
        if (saved) selectProject(saved);
      }
    } catch { /* ignore */ }
  }

  function _updateProjectDisplay(item) {
    if (projDisplay) {
      if (item) {
        projText.textContent = item.label;
        projDisplay.style.display = '';
      } else {
        projText.textContent = '';
        projDisplay.style.display = 'none';
      }
    }
  }

  function selectProject(item) {
    _ctxProjectId = item ? item.id : null;
    _updateProjectDisplay(item);
    if (item && item.id) {
      localStorage.setItem('infra.last_period_id', String(item.id));
    } else {
      localStorage.removeItem('infra.last_period_id');
    }
    window.dispatchEvent(new CustomEvent('ctx-changed', { detail: { partnerId: _ctxPartnerId, projectId: _ctxProjectId } }));
  }

  /** 프로젝트 선택 해제 (전체 목록으로 복귀) */
  window.resetCtxProject = function() { selectProject(null); };
  /** 외부에서 프로젝트 선택 (프로젝트 목록 행 클릭 등) */
  window.setCtxProject = function(id, code, label) {
    selectProject(id ? { id, code: code || '', label: label || '' } : null);
  };

  // ── X 버튼: 프로젝트 선택 해제 ──
  if (projClear) {
    projClear.addEventListener('click', () => selectProject(null));
  }

  // ── 초기 복원 ──
  try {
    const prefRes = await fetch('/api/v1/preferences/infra.pinned_partner_id');
    if (prefRes.ok) {
      const pref = await prefRes.json();
      if (pref.value) {
        const saved = allPartners.find(c => String(c.id) === String(pref.value));
        if (saved) {
          _ctxPartnerId = saved.id;
          custInput.value = saved.label;
          custInput.title = saved.code + ' ' + saved.label;
          await loadProjects(saved.id);
        }
      }
    }
  } catch { /* ignore */ }
}

// Legacy compat — 기존 코드에서 참조할 수 있는 함수
async function getPinnedProjectId() { return _ctxProjectId ? String(_ctxProjectId) : null; }
async function getPinnedPartnerId() { return _ctxPartnerId ? String(_ctxPartnerId) : null; }

// ── 글로벌 프로젝트 필터 (자산 탭 공유) ──────────────────────────────
const _PROJECT_FILTER_KEY = "infra_project_filter";

/** 프로젝트 필터 체크박스 초기화 (localStorage 연동) */
function initProjectFilterCheckbox(onChangeCallback) {
  const chk = document.getElementById("chk-project-filter");
  if (!chk) return;
  chk.checked = localStorage.getItem(_PROJECT_FILTER_KEY) === "1";
  chk.addEventListener("change", () => {
    localStorage.setItem(_PROJECT_FILTER_KEY, chk.checked ? "1" : "0");
    if (onChangeCallback) onChangeCallback();
  });
}

/** 프로젝트 필터가 활성 상태인지 반환 */
function isProjectFilterActive() {
  return localStorage.getItem(_PROJECT_FILTER_KEY) === "1";
}

// ── END 고객 피커 (필터링 + 신규 등록) ──────────────────────────────

let _pickerPartners = [];

/** 거래처 목록을 가져와 캐시 */
async function _loadPickerPartners() {
  const res = await fetch('/api/v1/partners');
  _pickerPartners = res.ok ? await res.json() : [];
  return _pickerPartners;
}

/** 유사 거래처 검색 */
function _findSimilarPartners(keyword) {
  if (!keyword || keyword.length < 2) return [];
  const kw = keyword.toLowerCase().replace(/\s/g, '');
  return _pickerPartners.filter(c => {
    const cn = c.name.toLowerCase().replace(/\s/g, '');
    if (cn === kw) return false;
    if (cn.includes(kw) || kw.includes(cn)) return true;
    const common = [...new Set(kw)].filter(ch => cn.includes(ch)).length;
    return common / Math.max(kw.length, cn.length) >= 0.7;
  }).slice(0, 3);
}

/** 드롭다운 렌더링 */
function _renderPickerDropdown(input, dropdown, hiddenInput) {
  const keyword = input.value.trim().toLowerCase();
  const filtered = keyword
    ? _pickerPartners.filter(c => c.name.toLowerCase().includes(keyword))
    : _pickerPartners;
  const limited = filtered.slice(0, 50);

  let html = `<div class="cp-new">+ 신규 거래처 등록</div>`;

  if (keyword && !_pickerPartners.find(c => c.name.toLowerCase() === keyword)) {
    const similar = _findSimilarPartners(input.value.trim());
    if (similar.length) {
      html += `<div class="cp-similar">⚠ 유사 거래처: ${similar.map(c => `<b>${c.name}</b>`).join(', ')}</div>`;
    }
  }

  html += limited.map(c =>
    `<div class="cp-item" tabindex="-1" data-id="${c.id}" data-name="${c.name}">${c.name}</div>`
  ).join('');
  dropdown.innerHTML = html;
  setElementHidden(dropdown, false);

  dropdown.querySelectorAll('.cp-item').forEach(el => {
    el.addEventListener('click', () => {
      input.value = el.dataset.name;
      hiddenInput.value = el.dataset.id;
      setElementHidden(dropdown, true);
      _prefillContractName(el.dataset.name);
    });
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') el.click();
      if (e.key === 'ArrowDown' && el.nextElementSibling) { e.preventDefault(); el.nextElementSibling.focus(); }
      if (e.key === 'ArrowUp' && el.previousElementSibling) { e.preventDefault(); el.previousElementSibling.focus(); }
    });
  });

  const newBtn = dropdown.querySelector('.cp-new');
  if (newBtn) {
    newBtn.addEventListener('click', () => {
      setElementHidden(dropdown, true);
      _openNewPartnerFromAdd(input.value.trim());
    });
  }
}

/** 거래처 선택 시 사업명 자동 기입 (비어있을 때만) */
function _prefillContractName(partnerName) {
  const nameInput = document.getElementById('add-contract-name');
  if (nameInput && !nameInput.value.trim()) {
    nameInput.value = partnerName;
  }
}

/** 신규 거래처 등록 모달 열기 */
function _openNewPartnerFromAdd(prefill) {
  document.getElementById('new-cust-name-from-add').value = prefill || '';
  document.getElementById('modal-new-partner-from-add').showModal();
}

/** 사업 등록 모달용 거래처 피커 초기화 */
function initEndPartnerPicker() {
  const input = document.getElementById('add-end-partner');
  const dropdown = document.getElementById('add-end-partner-dropdown');
  const hiddenInput = document.getElementById('add-end-partner-id');
  if (!input || !dropdown || !hiddenInput) return;

  _loadPickerPartners();

  input.addEventListener('input', () => {
    hiddenInput.value = '';
    _renderPickerDropdown(input, dropdown, hiddenInput);
  });
  input.addEventListener('focus', () => {
    _renderPickerDropdown(input, dropdown, hiddenInput);
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      const first = dropdown.querySelector('.cp-item');
      if (first) first.focus();
    }
    if (e.key === 'Escape') setElementHidden(dropdown, true);
    if (e.key === 'Enter') {
      e.preventDefault();
      const match = _pickerPartners.find(c => c.name === input.value.trim());
      if (match) {
        hiddenInput.value = match.id;
        setElementHidden(dropdown, true);
      }
    }
  });

  // 외부 클릭 시 드롭다운 닫기
  document.addEventListener('click', (e) => {
    if (!input.contains(e.target) && !dropdown.contains(e.target)) {
      setElementHidden(dropdown, true);
    }
  });

  // 신규 거래처 등록 모달 이벤트
  document.getElementById('btn-new-cust-cancel-add')?.addEventListener('click', () => {
    document.getElementById('modal-new-partner-from-add').close();
  });
  document.getElementById('btn-new-cust-submit-add')?.addEventListener('click', async () => {
    const name = document.getElementById('new-cust-name-from-add').value.trim();
    if (!name) { alert('거래처명을 입력하세요.'); return; }
    const res = await fetch('/api/v1/partners', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (res.ok) {
      const created = await res.json();
      document.getElementById('modal-new-partner-from-add').close();
      await _loadPickerPartners();
      input.value = created.name;
      hiddenInput.value = created.id;
      _prefillContractName(created.name);
      showToast(`"${name}" 거래처가 등록되었습니다.`);
    } else {
      const body = await res.json().catch(() => null);
      alert(body?.detail || '등록에 실패했습니다.');
    }
  });
}

// ── 사업 등록/수정 공용 모달 ────────────────────────────────────────

/** 사업 등록/수정 모달 열기
 * @param {Object|null} contract - 수정할 Contract 데이터 (null이면 신규 등록)
 */
function openContractModal(contract = null) {
  const modal = document.getElementById('modal-add');
  const form = document.getElementById('form-add');
  const title = document.getElementById('modal-add-title');
  const submitBtn = document.getElementById('btn-submit');
  const contractIdInput = document.getElementById('add-contract-id');

  form.reset();
  document.getElementById('add-end-partner-id').value = '';
  document.getElementById('add-end-partner').value = '';
  if (contract) {
    title.textContent = '사업정보 수정';
    submitBtn.textContent = '저장';
    contractIdInput.value = contract.id;
    document.getElementById('add-contract-name').value = contract.contract_name || '';
    document.getElementById('add-contract-type').value = contract.contract_type || 'MA';
    document.getElementById('add-end-partner').value = contract.end_partner_name || '';
    document.getElementById('add-end-partner-id').value = contract.end_partner_id || '';
  } else {
    title.textContent = '사업 등록';
    submitBtn.textContent = '등록';
    contractIdInput.value = '';
  }
  modal.showModal();
}

/** END 고객 이름 → ID 변환 (없으면 자동 생성) */
async function _resolveEndPartnerId(name) {
  if (!name) return null;
  const custRes = await fetch('/api/v1/partners');
  const custs = custRes.ok ? await custRes.json() : [];
  let cust = custs.find(c => c.name === name);
  if (!cust) {
    const createRes = await fetch('/api/v1/partners', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (createRes.ok) cust = await createRes.json();
  }
  return cust?.id ?? null;
}

/** 사업 등록 또는 수정 제출
 * @param {Function|null} loadDataFn - 등록 후 목록 새로고침 (목록 페이지용)
 * @param {Function|null} onUpdated - 수정 후 콜백 (상세 페이지용)
 */
async function submitContractModal(loadDataFn, onUpdated) {
  const form = document.getElementById('form-add');
  const fd = new FormData(form);
  const contractId = document.getElementById('add-contract-id').value;
  const contractName = (fd.get('contract_name') || '').trim();
  const contractType = fd.get('contract_type');
  const endPartnerName = document.getElementById('add-end-partner').value.trim();
  const endPartnerIdRaw = document.getElementById('add-end-partner-id').value;

  if (!contractName) { showToast('사업명을 입력하세요.', 'error'); return; }

  // 거래처는 반드시 목록에서 선택해야 함
  let endPartnerId = endPartnerIdRaw ? parseInt(endPartnerIdRaw, 10) : null;
  if (endPartnerName && !endPartnerId) {
    showToast('고객사를 목록에서 선택하세요.', 'error');
    document.getElementById('add-end-partner').focus();
    return;
  }

  if (contractId) {
    // 수정 모드
    const body = { contract_name: contractName, contract_type: contractType, end_partner_id: endPartnerId };
    const res = await fetch(`/api/v1/contracts/${contractId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      document.getElementById('modal-add').close();
      const updated = await res.json();
      showToast('사업정보가 수정되었습니다.');
      if (onUpdated) onUpdated(updated);
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || '수정에 실패했습니다.', 'error');
    }
  } else {
    // 신규 등록
    const body = { contract_name: contractName, contract_type: contractType, end_partner_id: endPartnerId };
    const res = await fetch('/api/v1/contracts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (res.ok) {
      document.getElementById('modal-add').close();
      form.reset();
      const created = await res.json();
      showToast('사업이 등록되었습니다. 기간 정보를 입력하세요.', 'info');
      // 상세 페이지로 이동 (Period 추가 모달 자동 팝업은 상세 페이지에서 처리)
      sessionStorage.setItem('contract-back', window.location.pathname === '/my-contracts' ? '/my-contracts' : '/contracts');
      sessionStorage.setItem('contract-auto-add-period', 'true');
      window.location.href = `/contracts/new/${created.id}`;
    } else {
      const err = await res.json().catch(() => ({}));
      showToast(err.detail || '등록에 실패했습니다.', 'error');
    }
  }
}

async function deleteSelectedContracts(gridApi, loadDataFn) {
  const rows = gridApi.getSelectedRows();
  if (rows.length === 0) { alert('삭제할 항목을 선택하세요.'); return; }

  const contractIds = [...new Set(rows.map(r => r.contract_id))];
  const allPeriodsByContract = new Map();
  gridApi.forEachNode(node => {
    const did = node.data.contract_id;
    if (!allPeriodsByContract.has(did)) allPeriodsByContract.set(did, 0);
    allPeriodsByContract.set(did, allPeriodsByContract.get(did) + 1);
  });
  const selectedByContract = new Map();
  rows.forEach(r => {
    selectedByContract.set(r.contract_id, (selectedByContract.get(r.contract_id) || 0) + 1);
  });

  const contractNames = rows.map(r => r.contract_name).filter((v, i, a) => a.indexOf(v) === i);
  const preview = contractNames.length <= 3 ? contractNames.join(', ') : `${contractNames.slice(0, 3).join(', ')} 외 ${contractNames.length - 3}건`;
  if (!confirm(`선택한 ${rows.length}행 (${preview})을 삭제하시겠습니까?`)) return;

  const requests = contractIds.map(contractId => {
    const selected = selectedByContract.get(contractId) || 0;
    const total = allPeriodsByContract.get(contractId) || 0;
    if (selected >= total) {
      return fetch(`/api/v1/contracts/${contractId}`, { method: 'DELETE' })
        .then(res => ({ res, type: 'contract', contractId }));
    } else {
      const periods = rows.filter(r => r.contract_id === contractId);
      return Promise.all(
        periods.map(r => fetch(`/api/v1/contract-periods/${r.id}`, { method: 'DELETE' })
          .then(res => ({ res, type: 'period', id: r.id })))
      );
    }
  });

  const results = (await Promise.all(requests)).flat();
  const denied = results.filter(r => r.res.status === 403);
  const failed = results.filter(r => !r.res.ok && r.res.status !== 403);

  await loadDataFn();
  if (denied.length > 0) showToast('권한이 없습니다. 삭제는 관리자만 가능합니다.', 'error');
  else if (failed.length > 0) showToast(`${failed.length}건 삭제에 실패했습니다.`, 'error');
  else showToast(`${results.length}건이 삭제되었습니다.`);
}

// ── 사업 목록 그리드 공통 (contracts / my_contracts 공용) ─────────────────

/** 사업 목록 컬럼 정의 생성
 * @param {Object} opts
 * @param {boolean} opts.showOwner - 담당/부서 컬럼 표시 여부
 */
function buildContractPeriodColumns(opts = {}) {
  const cols = [
    { headerName: '', width: 40, checkboxSelection: true, headerCheckboxSelection: true,
      pinned: 'left', sortable: false, resizable: false },
    { field: 'period_year', headerName: getTermLabel('period_year', '귀속연도'), width: 82, pinned: 'left' },
    { field: 'end_partner_name', headerName: getTermLabel('customer', '고객'), width: 140 },
    { field: 'contract_code', headerName: '사업코드', width: 120 },
    { field: 'contract_type', headerName: '사업유형', width: 80 },
    { field: 'contract_name', headerName: '사업명', flex: 1, minWidth: 200,
      cellClass: 'cell-link', tooltipField: 'contract_name' },
    { field: 'stage', headerName: '진행단계', width: 100 },
    { headerName: '사업기간', width: 140,
      valueGetter: p => {
        const s = p.data?.start_month, e = p.data?.end_month;
        if (!s && !e) return '-';
        const fmtM = m => m ? m.slice(0, 7) : '?';
        return `${fmtM(s)} ~ ${fmtM(e)}`;
      }},
  ];
  if (opts.showOwner) {
    cols.push({ field: 'owner_name', headerName: '담당', width: 80 });
    cols.push({ field: 'owner_department', headerName: '부서', width: 90 });
  }
  cols.push(
    { field: 'is_planned', headerName: '사업구분', width: 80,
      valueFormatter: p => p.value === true ? '계획사업' : p.value === false ? '수시사업' : '',
      cellClass: 'cell-center' },
    { field: 'expected_revenue_total', headerName: '예상 매출(원)', width: 130,
      valueFormatter: fmtNumber, cellClass: 'cell-number', type: 'numericColumn' },
    { field: 'expected_gp_total', headerName: '예상 GP(원)', width: 120,
      valueFormatter: fmtNumber, cellClass: 'cell-number', type: 'numericColumn' },
  );
  return cols;
}

/** 컬럼 상태를 localStorage에 저장 */
function saveColState(gridApi, colStateKey) {
  if (gridApi) localStorage.setItem(colStateKey, JSON.stringify(gridApi.getColumnState()));
}

function restoreColState(gridApi, colStateKey) {
  const raw = localStorage.getItem(colStateKey);
  if (!raw) return;
  try {
    gridApi.applyColumnState({ state: JSON.parse(raw), applyOrder: true });
  } catch { /* ignore */ }
}

/** 사업 목록 그리드 옵션 생성
 * @param {Object} opts
 * @param {Array} opts.columnDefs
 * @param {string} opts.backPath - 뒤로가기 경로 ('/contracts' 또는 '/my-contracts')
 * @param {string} opts.partnerInputId - 고객 텍스트 입력 ID
 * @param {string} opts.nameInputId - 사업명 텍스트 입력 ID
 * @param {Function} opts.onColChange - 컬럼 변경 콜백
 */
function buildContractGridOptions(opts) {
  const getPartnerFilter = () => (document.getElementById(opts.partnerInputId)?.value || '').trim().toLowerCase();
  const getNameFilter = () => (document.getElementById(opts.nameInputId)?.value || '').trim().toLowerCase();
  return {
    columnDefs: opts.columnDefs,
    rowData: [],
    defaultColDef: { resizable: true, sortable: true },
    rowSelection: 'multiple',
    suppressRowClickSelection: true,
    animateRows: false,
    onColumnMoved: opts.onColChange,
    onColumnResized: (e) => { if (e.finished) opts.onColChange(); },
    onCellClicked: (e) => {
      if (e.column.getColId() !== '0' && e.data?.id) {
        sessionStorage.setItem('contract-back', opts.backPath);
        window.location.href = `/contracts/${e.data.id}`;
      }
    },
    isExternalFilterPresent: () => getPartnerFilter() !== '' || getNameFilter() !== '',
    doesExternalFilterPass: (node) => {
      const d = node.data;
      const cf = getPartnerFilter();
      if (cf && !(d.end_partner_name || '').toLowerCase().includes(cf)) return false;
      const nf = getNameFilter();
      if (nf && !(d.contract_name || '').toLowerCase().includes(nf)) return false;
      return true;
    },
  };
}

/** 거래처 datalist 로드 */
function loadPartnerDatalist() {
  fetch('/api/v1/partners').then(r => r.json()).then(custs => {
    const dl = document.getElementById('partner-list');
    if (dl) dl.innerHTML = custs.map(c => `<option value="${c.name}">`).join('');
  });
}

// ── 필터 상태 저장/복원 (localStorage) ─────────────────────────────

/**
 * 현재 필터바의 체크박스 상태를 localStorage에 저장.
 * @param {string} storageKey - localStorage 키 (페이지별 구분)
 */
function saveFilterState(storageKey) {
  const state = { drops: {}, texts: {} };
  // 체크박스 드롭다운 상태
  document.querySelectorAll('.filter-bar .chk-drop').forEach(drop => {
    const id = drop.id;
    if (!id) return;
    const checked = [...drop.querySelectorAll('input:checked')].map(cb => cb.value);
    state.drops[id] = checked;
  });
  // 수행중 토글
  const chkActive = document.getElementById('chk-active-period');
  if (chkActive) state.activePeriod = chkActive.checked;
  // 내 사업만 토글
  const chkMy = document.getElementById('chk-my-contracts');
  if (chkMy) state.myOnly = chkMy.checked;
  // 텍스트 필터
  const custInput = document.getElementById('filter-partner-text');
  if (custInput) state.texts.partner = custInput.value;
  const nameInput = document.getElementById('filter-name-text');
  if (nameInput) state.texts.name = nameInput.value;
  localStorage.setItem(storageKey, JSON.stringify(state));
}

/**
 * localStorage에서 필터 상태를 복원.
 * @param {string} storageKey - localStorage 키
 * @returns {boolean} 복원 성공 여부
 */
function restoreFilterState(storageKey) {
  const raw = localStorage.getItem(storageKey);
  if (!raw) return false;
  try {
    const state = JSON.parse(raw);
    // 체크박스 드롭다운 복원
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
    // 수행중 토글 복원
    const chkActive = document.getElementById('chk-active-period');
    if (chkActive && state.activePeriod !== undefined) {
      chkActive.checked = state.activePeriod;
      toggleYearDropdowns(!chkActive.checked);
    }
    // 내 사업만 토글 복원
    const chkMy = document.getElementById('chk-my-contracts');
    if (chkMy && state.myOnly !== undefined) {
      chkMy.checked = state.myOnly;
    }
    // 텍스트 필터 복원
    if (state.texts?.partner) {
      const custInput = document.getElementById('filter-partner-text');
      if (custInput) custInput.value = state.texts.partner;
    }
    if (state.texts?.name) {
      const nameInput = document.getElementById('filter-name-text');
      if (nameInput) nameInput.value = state.texts.name;
    }
    return true;
  } catch { return false; }
}

/** 사업 목록 필터 초기화 — 모든 필터 해제 (수행중 토글 포함) */
function resetContractFilters(loadDataFn, storageKey) {
  document.querySelectorAll('.filter-bar input[type="checkbox"]').forEach(cb => { cb.checked = false; });
  // 수행중 토글도 OFF → 드롭다운 활성화
  const chkActive = document.getElementById('chk-active-period');
  if (chkActive) {
    chkActive.checked = false;
    toggleYearDropdowns(true);
  }
  document.querySelectorAll('.chk-drop').forEach(drop => updateDropLabel(drop));
  // 텍스트 필터 초기화
  const custInput = document.getElementById('filter-partner-text');
  if (custInput) custInput.value = '';
  const nameInput = document.getElementById('filter-name-text');
  if (nameInput) nameInput.value = '';
  if (storageKey) localStorage.removeItem(storageKey);
  loadDataFn();
}

// ── 컬럼 설정(Column Chooser) ────────────────────────────────────

function initColChooser(gridApi, columnDefs, colStateKey, saveColStateFn) {
  const btn = document.getElementById('btn-col-chooser');
  const menu = document.getElementById('col-chooser-menu');
  const toggleable = columnDefs.filter(c => !c.pinned && c.field);

  const saved = JSON.parse(localStorage.getItem(colStateKey) || 'null');
  if (saved) gridApi.applyColumnState({ state: saved, applyOrder: true });

  function renderMenu() {
    const stateMap = Object.fromEntries(gridApi.getColumnState().map(s => [s.colId, s]));
    menu.innerHTML = toggleable.map(col => {
      const visible = !stateMap[col.field]?.hide;
      return `<label class="col-chooser-item">
        <input type="checkbox" data-field="${col.field}" ${visible ? 'checked' : ''}> ${col.headerName}
      </label>`;
    }).join('');
  }

  btn.addEventListener('click', e => {
    e.stopPropagation();
    if (isElementHidden(menu)) {
      renderMenu();
      setElementHidden(menu, false);
    } else {
      setElementHidden(menu, true);
    }
  });

  menu.addEventListener('change', e => {
    if (e.target.type !== 'checkbox') return;
    gridApi.setColumnVisible(e.target.dataset.field, e.target.checked);
    saveColStateFn();
  });

  document.addEventListener('click', () => { setElementHidden(menu, true); });
  menu.addEventListener('click', e => e.stopPropagation());
}
