(function () {
  'use strict';
  let monthlyChart = null;
  let byTypeChart = null;
  let groupBy = 'month';
  let chartType = 'bar';
  let lastTrendData = null;
  const CURRENT_YEAR = new Date().getFullYear();
  const DASH_FILTER_KEY = 'dash_filter_state';

  // ── 초기화 ─────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', async () => {
    await loadTermLabels();
    applyTermLabels();
    initDateDefaults();
    initYearButtons();
    await populateContractTypeCheckboxes('#dash-drop-type .chk-drop-menu');
    await initFilters();
    restoreDashFilterState();
    initDropdownToggles();
    loadDashboard();

    document.getElementById('btn-dash-refresh').addEventListener('click', loadDashboard);
    document.getElementById('btn-dash-reset').addEventListener('click', resetFilter);
    // 차트 타입 전환 버튼
    document.querySelectorAll('.chart-type-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.chart-type-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        chartType = btn.dataset.type;
        if (lastTrendData) renderTrend(lastTrendData);
      });
    });
    // 집계 단위 버튼 (글로벌)
    document.querySelectorAll('.dash-group-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.dash-group-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        groupBy = btn.dataset.group;
        loadDashboard();
      });
    });
    // 날짜 변경 시 연도 빠른선택 동기화
    document.getElementById('dash-date-from').addEventListener('change', syncYearButtons);
    document.getElementById('dash-date-to').addEventListener('change', syncYearButtons);
    // 테마 변경시 차트 다시 그리기
    window.addEventListener('theme-changed', loadDashboard);
  });

  // CSS 변수 값을 가져오는 헬퍼 (body 기준 — dark-mode 오버라이드 반영)
  function getCssVar(varName) {
    return getComputedStyle(document.body).getPropertyValue(varName).trim();
  }

  function initDateDefaults() {
    document.getElementById('dash-date-from').value = `${CURRENT_YEAR}-01`;
    document.getElementById('dash-date-to').value = `${CURRENT_YEAR}-12`;
  }

  function initYearButtons() {
    const wrap = document.getElementById('dash-year-bar');
    // 최대 3개: 전년/올해/내년
    const startYear = CURRENT_YEAR - 1;
    const endYear = CURRENT_YEAR + 1;
    for (let y = startYear; y <= endYear; y++) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'pill-tab dash-year-btn';
      btn.textContent = `${y}년`;
      btn.dataset.year = y;
      if (y === CURRENT_YEAR) btn.classList.add('active');
      btn.addEventListener('click', () => {
        document.getElementById('dash-date-from').value = `${y}-01`;
        document.getElementById('dash-date-to').value = `${y}-12`;
        document.querySelectorAll('.dash-year-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        loadDashboard();
      });
      wrap.appendChild(btn);
    }
  }

  async function initFilters() {
    const [users, partners] = await Promise.all([
      fetch(withRootPath('/api/v1/users')).then(r => r.json()),
      fetch(withRootPath('/api/v1/partners')).then(r => r.json()),
    ]);
    const depts = [...new Set(users.map(u => u.department).filter(Boolean))].sort();
    const deptMenu = document.querySelector('#dash-drop-dept .chk-drop-menu');
    deptMenu.innerHTML = depts.map(d => `<label><input type="checkbox" value="${escapeHtml(d)}"> ${escapeHtml(d)}</label>`).join('');

    const ownerMenu = document.querySelector('#dash-drop-owner .chk-drop-menu');
    ownerMenu.innerHTML = users.filter(u => u.is_active).sort((a, b) => a.name.localeCompare(b.name))
      .map(u => `<label><input type="checkbox" value="${u.id}"> ${escapeHtml(u.name)}</label>`).join('');

    const custMenu = document.querySelector('#dash-drop-partner .chk-drop-menu');
    custMenu.innerHTML = partners.sort((a, b) => a.name.localeCompare(b.name))
      .map(c => `<label><input type="checkbox" value="${c.id}"> ${escapeHtml(c.name)}</label>`).join('');
  }

  // ── 필터 파라미터 수집 ──────────────────────────────────────────

  function getFilterParams() {
    const params = new URLSearchParams();
    params.set('date_from', document.getElementById('dash-date-from').value);
    params.set('date_to', document.getElementById('dash-date-to').value);
    document.querySelectorAll('#dash-drop-type input:checked').forEach(cb => params.append('contract_type', cb.value));
    document.querySelectorAll('#dash-drop-stage input:checked').forEach(cb => params.append('stage', cb.value));
    document.querySelectorAll('#dash-drop-dept input:checked').forEach(cb => params.append('department', cb.value));
    document.querySelectorAll('#dash-drop-owner input:checked').forEach(cb => params.append('owner_id', cb.value));
    document.querySelectorAll('#dash-drop-partner input:checked').forEach(cb => params.append('partner_id', cb.value));
    params.set('group_by', groupBy);
    return params;
  }

  // ── 필터 상태 저장/복원 (localStorage) ──────────────────────────

  function saveDashFilterState() {
    const state = { drops: {} };
    state.dateFrom = document.getElementById('dash-date-from').value;
    state.dateTo = document.getElementById('dash-date-to').value;
    document.querySelectorAll('#dash-filter-bar .chk-drop').forEach(drop => {
      if (!drop.id) return;
      state.drops[drop.id] = [...drop.querySelectorAll('input:checked')].map(cb => cb.value);
    });
    localStorage.setItem(DASH_FILTER_KEY, JSON.stringify(state));
  }

  function restoreDashFilterState() {
    const raw = localStorage.getItem(DASH_FILTER_KEY);
    if (!raw) return;
    try {
      const state = JSON.parse(raw);
      if (state.dateFrom) document.getElementById('dash-date-from').value = state.dateFrom;
      if (state.dateTo) document.getElementById('dash-date-to').value = state.dateTo;
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
      syncYearButtons();
    } catch { /* ignore corrupt state */ }
  }

  function syncYearButtons() {
    const from = document.getElementById('dash-date-from').value;
    const to = document.getElementById('dash-date-to').value;
    document.querySelectorAll('.dash-year-btn').forEach(btn => {
      const y = btn.dataset.year;
      btn.classList.toggle('active', from === `${y}-01` && to === `${y}-12`);
    });
  }

  function resetFilter() {
    initDateDefaults();
    document.querySelectorAll('#dash-filter-bar input[type="checkbox"]').forEach(cb => { cb.checked = false; });
    document.querySelectorAll('#dash-filter-bar .chk-drop').forEach(drop => updateDropLabel(drop));
    syncYearButtons();
    localStorage.removeItem(DASH_FILTER_KEY);
    loadDashboard();
  }

  // ── 데이터 로드 ────────────────────────────────────────────────

  async function loadDashboard() {
    saveDashFilterState();
    try {
      const params = getFilterParams();
      const res = await fetch(withRootPath(`/api/v1/dashboard/summary?${params}`));
      if (!res.ok) throw new Error('데이터 조회 실패');
      const data = await res.json();
      renderKpis(data.kpis);
      renderTrend(data.trend);
      renderByType(data.by_type);
      renderByDept(data.by_department);
      renderTopPartners(data.top_partners);
      renderArWarnings(data.ar_warnings);
      loadTargetVsActual();
    } catch (e) {
      console.error('Dashboard load error:', e);
      const mainContent = document.querySelector('.dashboard-grid');
      if (mainContent) mainContent.innerHTML = '<div class="dash-empty dash-full-row">데이터를 불러오는 중 오류가 발생했습니다.</div>';
    }
  }

  // ── KPI 카드 ───────────────────────────────────────────────────

  function renderKpis(k) {
    const el = document.getElementById('dash-kpis');
    if(!el) return;

    const targetRate = k.target_revenue > 0
      ? safePct(k.actual_revenue, k.target_revenue) : null;
    const gpSub = `GP% ${k.gp_pct != null ? k.gp_pct + '%' : '-'}`;
    const arSub = `미수율 ${k.ar_rate != null ? k.ar_rate + '%' : '-'}`;

    // 매출 실적 sub: 계획사업 XX + 수시사업 XX
    const plannedPart = k.planned_actual_revenue != null ? `계획사업 ${fmtKoreanCurrency(k.planned_actual_revenue)}` : '';
    const unplannedPart = k.unplanned_actual_revenue > 0 ? ` + 수시사업 ${fmtKoreanCurrency(k.unplanned_actual_revenue)}` : '';
    const actualBreakdown = plannedPart + unplannedPart;

    const cards = [
      { label: '진행 사업', value: `${k.contract_count}건`, cls: '', tip: '진행 중인 사업 건수' },
      { label: '매출 목표', value: fmt(k.target_revenue), sub: fmtKoreanCurrency(k.target_revenue), cls: '', tip: '연초 보고 사업의 Forecast 기준 예상매출' },
      { label: '매출 실적', value: fmt(k.actual_revenue), sub: `달성률 ${targetRate != null ? targetRate + '%' : '-'} · ${actualBreakdown}`, cls: 'highlight', tip: '전체 사업(계획사업+수시사업)의 확정 매출' },
      { label: 'GP', value: fmt(k.gp), sub: `${fmtKoreanCurrency(k.gp)} · ${gpSub}`, cls: 'highlight', tip: '매출 - 매입' },
      { label: '입금', value: fmt(k.receipt), sub: fmtKoreanCurrency(k.receipt), cls: '', tip: '입금 합계' },
      { label: '미수금', value: fmt(k.ar), sub: `${fmtKoreanCurrency(k.ar)} · ${arSub}`, cls: k.ar > 0 ? 'warn' : '', tip: '매출 확정 - 배분완료' },
    ];

    el.innerHTML = cards.map(c => `
      <div class="dash-kpi ${c.cls}" title="${c.tip || ''}">
        <div class="dash-kpi-label">${c.label}</div>
        <div class="dash-kpi-value">${c.value}</div>
        ${c.sub ? `<div class="dash-kpi-sub">${c.sub}</div>` : ''}
      </div>
    `).join('');
  }

  function safePct(n, d) {
    return d > 0 ? Math.round(n / d * 1000) / 10 : null;
  }

  // ── 월별 추이 (차트) ──────────────────────────────────────────

  function renderTrend(rows) {
    lastTrendData = rows;
    const container = document.querySelector('.monthly-trend .chart-container');
    if (!container) return;

    if (monthlyChart) monthlyChart.destroy();

    if (!rows || rows.length === 0) {
      container.innerHTML = '<div class="dash-empty">데이터 없음</div>';
      return;
    }
    if (container.querySelector('.dash-empty')) {
      container.innerHTML = '';
      const newCanvas = document.createElement('canvas');
      newCanvas.id = 'monthly-chart';
      container.appendChild(newCanvas);
    }

    const labels = rows.map(r => r.month.length <= 7 ? `${r.month}` : r.month);
    const plannedFc = rows.map(r => (r.planned_forecast || 0) / 1000000);
    const unplannedFc = rows.map(r => (r.unplanned_forecast || 0) / 1000000);
    const totalFc = rows.map(r => (r.forecast_revenue || 0) / 1000000);
    const actualData = rows.map(r => r.actual_revenue / 1000000);

    const textColor = getCssVar('--text-color');
    const gridColor = getCssVar('--border-color-light');

    let datasets, cType, scaleOpts;

    if (chartType === 'bar') {
      // stacked bar: 계획사업 Forecast + 수시사업 Forecast (stacked) / Actual (별도)
      cType = 'bar';
      datasets = [
        {
          label: '계획사업 Forecast', data: plannedFc,
          backgroundColor: getCssVar('--chart-forecast-bg'),
          borderColor: getCssVar('--chart-forecast-border'),
          borderWidth: 1, borderRadius: 4,
          stack: 'forecast',
        },
        {
          label: '수시사업 Forecast', data: unplannedFc,
          backgroundColor: getCssVar('--info-soft-bg'),
          borderColor: getCssVar('--info-soft-text'),
          borderWidth: 1, borderRadius: 4,
          stack: 'forecast',
        },
        {
          label: 'Actual', data: actualData,
          backgroundColor: getCssVar('--primary-color'),
          borderColor: getCssVar('--primary-color-hover'),
          borderWidth: 1, borderRadius: 4,
          stack: 'actual',
        },
      ];
      scaleOpts = { y: { stacked: true } };
    } else if (chartType === 'line') {
      // 선형: 계획사업 Forecast / 수시사업 Forecast / Actual (3개 선)
      cType = 'line';
      datasets = [
        {
          label: '계획사업 Forecast', data: plannedFc,
          borderColor: getCssVar('--chart-forecast-border'),
          backgroundColor: 'transparent',
          borderWidth: 2, tension: 0, fill: false,
          pointRadius: 4, pointHoverRadius: 6,
        },
        {
          label: '수시사업 Forecast', data: unplannedFc,
          borderColor: getCssVar('--info-soft-text'),
          backgroundColor: 'transparent',
          borderWidth: 2, tension: 0, fill: false,
          borderDash: [4, 3],
          pointRadius: 3, pointHoverRadius: 5,
        },
        {
          label: 'Actual', data: actualData,
          borderColor: getCssVar('--primary-color'),
          backgroundColor: 'transparent',
          borderWidth: 2, tension: 0, fill: false,
          pointRadius: 4, pointHoverRadius: 6,
        },
      ];
      scaleOpts = {};
    } else {
      // 영역: 계획사업+수시사업 Forecast (stacked area) / Actual (선 오버레이)
      cType = 'line';
      datasets = [
        {
          label: '계획사업 Forecast', data: plannedFc,
          borderColor: getCssVar('--chart-forecast-border'),
          backgroundColor: getCssVar('--chart-forecast-area'),
          borderWidth: 2, tension: 0, fill: true,
          pointRadius: 3, pointHoverRadius: 5,
          stack: 'forecast', order: 2,
        },
        {
          label: '수시사업 Forecast', data: unplannedFc,
          borderColor: getCssVar('--info-soft-text'),
          backgroundColor: getCssVar('--info-soft-bg'),
          borderWidth: 1.5, tension: 0, fill: true,
          pointRadius: 2, pointHoverRadius: 4,
          stack: 'forecast', order: 2,
        },
        {
          label: 'Actual', data: actualData,
          borderColor: getCssVar('--primary-color'),
          backgroundColor: getCssVar('--chart-actual-area'),
          borderWidth: 2, tension: 0, fill: true,
          pointRadius: 3, pointHoverRadius: 5,
          order: 0,
        },
      ];
      scaleOpts = { y: { stacked: true } };
    }

    monthlyChart = new Chart(document.getElementById('monthly-chart').getContext('2d'), {
      type: cType,
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'top', align: 'end', labels: { color: textColor } },
          tooltip: {
            callbacks: {
              label: ctx => `${ctx.dataset.label}: ${fmt(ctx.raw)} 백만`,
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ...scaleOpts.y,
            ticks: { color: textColor, callback: v => `${v} 백만` },
            grid: { color: gridColor },
          },
          x: {
            ...scaleOpts.x,
            ticks: { color: textColor },
            grid: { display: false },
          },
        },
      },
    });
  }

  // ── 사업유형별 매출 (차트) ────────────────────────────────────

  function renderByType(rows) {
    const container = document.querySelector('.by-type .chart-container');
    if (!container) return;
    const canvas = document.getElementById('by-type-chart');
    const emptyEl = document.getElementById('by-type-empty');

    if (byTypeChart) {
      byTypeChart.destroy();
    }

    if (!rows || rows.length === 0) {
      canvas.classList.add('is-hidden');
      emptyEl.classList.remove('is-hidden');
      return;
    }

    canvas.classList.remove('is-hidden');
    emptyEl.classList.add('is-hidden');

    const labels = rows.map(r => r.label);
    const data = rows.map(r => r.actual_revenue);
    const totalSales = data.reduce((a, b) => a + b, 0);

    const chartColors = [
      getCssVar('--chart-color-1'),
      getCssVar('--chart-color-2'),
      getCssVar('--chart-color-3'),
      getCssVar('--chart-color-4'),
      getCssVar('--chart-color-5'),
    ];
    const textColor = getCssVar('--text-color');
    const borderColor = getCssVar('--surface-color');


    byTypeChart = new Chart(canvas.getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: labels,
        datasets: [{
          data: data,
          backgroundColor: chartColors,
          borderColor: borderColor,
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: textColor,
              usePointStyle: true,
            }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                const label = context.label || '';
                const value = context.raw;
                const percentage = totalSales > 0 ? ((value / totalSales) * 100).toFixed(1) : 0;
                return `${label}: ${fmt(value)} (${percentage}%)`;
              }
            }
          }
        },
      }
    });
  }

  // ── 부서별 실적 ────────────────────────────────────────────────

  function renderByDept(rows) {
    const tbody = document.querySelector('#tbl-by-dept tbody');
    if (!tbody) return;
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="dash-empty">데이터 없음</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(r => `<tr>
      <td>${r.label}</td>
      <td class="cell-number">${r.contract_count}</td>
      <td class="cell-number">${fmt(r.forecast_revenue)}</td>
      <td class="cell-number">${fmt(r.actual_revenue)}</td>
      <td class="cell-number">${fmt(r.gp)}</td>
      <td class="cell-number">${r.gp_pct != null ? r.gp_pct + '%' : '-'}</td>
    </tr>`).join('');
  }

  // ── Top 10 거래처 ──────────────────────────────────────────────

  function renderTopPartners(rows) {
    const tbody = document.querySelector('#tbl-top-cust tbody');
    if (!tbody) return;
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="dash-empty">데이터 없음</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((r, i) => `<tr>
      <td class="cell-center">${i + 1}</td>
      <td>${r.partner_name}</td>
      <td class="cell-number">${fmt(r.actual_revenue)}</td>
      <td class="cell-number">${r.contract_count}</td>
    </tr>`).join('');
  }

  // ── 미수금 경고 ────────────────────────────────────────────────

  function renderArWarnings(rows) {
    const tbody = document.querySelector('#tbl-ar-warn tbody');
    if (!tbody) return;
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="dash-empty">미수금 없음</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(r => `<tr>
      <td><a href="${withRootPath(`/contracts/${r.contract_id}`)}" class="ar-contract-link">${r.contract_name}</a></td>
      <td>${r.owner_name || '-'}</td>
      <td class="cell-number">${fmt(r.actual_revenue)}</td>
      <td class="cell-number">${fmt(r.receipt)}</td>
      <td class="cell-number ar-positive">${fmt(r.ar)}</td>
      <td class="cell-number">${r.ar_rate != null ? r.ar_rate + '%' : '-'}</td>
    </tr>`).join('');
  }

  // ── 매출 목표 vs 실적 ───────────────────────────────────────

  async function loadTargetVsActual() {
    try {
      const params = getFilterParams();
      // stage 필터는 target-vs-actual에 적용하지 않음 (전체 기간 대상)
      params.delete('stage');
      params.set('group_by', groupBy);
      const res = await fetch(withRootPath(`/api/v1/dashboard/target-vs-actual?${params}`));
      if (!res.ok) throw new Error('목표 vs 실적 조회 실패');
      const data = await res.json();
      renderTvaTable(data.rows, data.totals);
    } catch (e) {
      console.error('Target vs Actual load error:', e);
    }
  }

  function renderTvaTable(rows, totals) {
    const tbody = document.querySelector('#tbl-tva tbody');
    if (!tbody) return;
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="dash-empty">데이터 없음</td></tr>';
      return;
    }
    const renderRow = (r, cls) => {
      const gapCls = r.gap > 0 ? ' ar-positive' : '';
      return `<tr class="${cls}">
        <td>${r.label || '합계'}</td>
        <td class="cell-number">${fmt(r.target_revenue)}</td>
        <td class="cell-number">${fmt(r.actual_revenue)}</td>
        <td class="cell-number">${fmt(r.planned_actual_revenue)}</td>
        <td class="cell-number">${fmt(r.unplanned_actual_revenue)}</td>
        <td class="cell-number${r.lost_revenue > 0 ? ' ar-positive' : ''}">${fmt(r.lost_revenue)}</td>
        <td class="cell-number${gapCls}">${fmt(r.gap)}</td>
        <td class="cell-number">${r.achievement_rate != null ? r.achievement_rate + '%' : '-'}</td>
      </tr>`;
    };
    const html = rows.map(r => renderRow(r, '')).join('')
      + renderRow({ label: '합계', ...totals }, 'row-total');
    tbody.innerHTML = html;
  }
})();
