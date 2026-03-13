(function () {
  'use strict';
  let monthlyChart = null;
  let byTypeChart = null;
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
    const wrap = document.getElementById('dash-year-btns');
    for (let y = CURRENT_YEAR - 1; y <= CURRENT_YEAR + 1; y++) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-secondary btn-sm dash-year-btn';
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
    const users = await fetch('/api/v1/users').then(r => r.json());
    const depts = [...new Set(users.map(u => u.department).filter(Boolean))].sort();
    const deptMenu = document.querySelector('#dash-drop-dept .chk-drop-menu');
    deptMenu.innerHTML = depts.map(d => `<label><input type="checkbox" value="${d}"> ${d}</label>`).join('');

    const ownerMenu = document.querySelector('#dash-drop-owner .chk-drop-menu');
    ownerMenu.innerHTML = users.filter(u => u.is_active).sort((a, b) => a.name.localeCompare(b.name))
      .map(u => `<label><input type="checkbox" value="${u.id}"> ${u.name}</label>`).join('');
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
      const res = await fetch(`/api/v1/dashboard/summary?${params}`);
      if (!res.ok) throw new Error('데이터 조회 실패');
      const data = await res.json();
      renderKpis(data.kpis);
      renderMonthly(data.monthly_trend);
      renderByType(data.by_type);
      renderByDept(data.by_department);
      renderTopCustomers(data.top_customers);
      renderArWarnings(data.ar_warnings);
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

    const formattedForecast = fmtKoreanCurrency(k.forecast_revenue);
    const formattedActual = fmtKoreanCurrency(k.actual_revenue);
    const formattedGp = fmtKoreanCurrency(k.gp);
    const formattedReceipt = fmtKoreanCurrency(k.receipt);
    const formattedAr = fmtKoreanCurrency(k.ar);

    const achievementSub = `(달성률 ${k.achievement_rate != null ? k.achievement_rate + '%' : '-'})`;
    const gpSub = `(GP% ${k.gp_pct != null ? k.gp_pct + '%' : '-'})`;
    const arSub = `(미수율 ${k.ar_rate != null ? k.ar_rate + '%' : '-'})`;

    const cards = [
      { label: '진행 사업', value: `${k.contract_count}건`, cls: '' },
      { label: 'Forecast', value: fmt(k.forecast_revenue), sub: formattedForecast, cls: '' },
      { label: 'Actual 매출', value: fmt(k.actual_revenue), sub: [formattedActual, achievementSub].filter(v => v != null).join(' '), cls: 'highlight' },
      { label: 'GP', value: fmt(k.gp), sub: [formattedGp, gpSub].filter(v => v != null).join(' '), cls: 'highlight' },
      { label: '입금', value: fmt(k.receipt), sub: formattedReceipt, cls: '' },
      { label: '미수금', value: fmt(k.ar), sub: [formattedAr, arSub].filter(v => v != null).join(' '), cls: k.ar > 0 ? 'warn' : '' },
    ];

    el.innerHTML = cards.map(c => `
      <div class="dash-kpi ${c.cls}">
        <div class="dash-kpi-label">${c.label}</div>
        <div class="dash-kpi-value">${c.value}</div>
        ${c.sub ? `<div class="dash-kpi-sub">${c.sub}</div>` : ''}
      </div>
    `).join('');
  }

  // ── 월별 추이 (차트) ──────────────────────────────────────────

  function renderMonthly(rows) {
    const container = document.querySelector('.monthly-trend .chart-container');
    if (!container) return;

    if (monthlyChart) {
      monthlyChart.destroy();
    }

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


    const labels = rows.map(r => `${r.month}월`);
    const forecastData = rows.map(r => r.forecast_revenue / 1000000); // 백만 단위
    const actualData = rows.map(r => r.actual_revenue / 1000000);

    const textColor = getCssVar('--text-color');
    const gridColor = getCssVar('--border-color-light');

    monthlyChart = new Chart(document.getElementById('monthly-chart').getContext('2d'), {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Forecast',
            data: forecastData,
            backgroundColor: getCssVar('--chart-forecast-bg'),
            borderColor: getCssVar('--chart-forecast-border'),
            borderWidth: 1,
            borderRadius: 4,
          },
          {
            label: 'Actual',
            data: actualData,
            backgroundColor: getCssVar('--primary-color'),
            borderColor: getCssVar('--primary-color-hover'),
            borderWidth: 1,
            borderRadius: 4,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            align: 'end',
            labels: { color: textColor }
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                return `${context.dataset.label}: ${context.raw.toLocaleString()} 백만`;
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: textColor,
              callback: function(value) {
                return `${value} 백만`;
              }
            },
            grid: { color: gridColor }
          },
          x: {
            ticks: { color: textColor },
            grid: { display: false }
          }
        }
      }
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

  function renderTopCustomers(rows) {
    const tbody = document.querySelector('#tbl-top-cust tbody');
    if (!tbody) return;
    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="dash-empty">데이터 없음</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map((r, i) => `<tr>
      <td class="cell-center">${i + 1}</td>
      <td>${r.customer_name}</td>
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
      <td><a href="/contracts/${r.contract_id}" class="ar-contract-link">${r.contract_name}</a></td>
      <td>${r.owner_name || '-'}</td>
      <td class="cell-number">${fmt(r.actual_revenue)}</td>
      <td class="cell-number">${fmt(r.receipt)}</td>
      <td class="cell-number ar-positive">${fmt(r.ar)}</td>
      <td class="cell-number">${r.ar_rate != null ? r.ar_rate + '%' : '-'}</td>
    </tr>`).join('');
  }
})();
