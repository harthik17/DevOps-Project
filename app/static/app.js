/**
 * AIOps Platform - Frontend Interactive Logic
 * Full integration with FastAPI backend, Prometheus telemetry, ML predictions,
 * SHAP explainability, RCA, resource optimization, and K8s dry-run previews.
 */

document.addEventListener('DOMContentLoaded', () => {
  // ================= STATE & CACHE =================
  let telemetryChart = null;
  const chartHistory = {
    labels: [],
    requestRates: [],
    latencies: [],
    cpuUsages: []
  };

  const MAX_HISTORY_POINTS = 12;

  // ================= INITIALIZATION =================
  initTheme();
  initTabs();
  initChart();
  initChaosControls();
  initForms();
  initPresets();

  // Initial data loads
  pollLiveTelemetry();
  pollAlerts();

  // Set recurring telemetry polling (every 10 seconds)
  setInterval(pollLiveTelemetry, 10000);
  setInterval(pollAlerts, 30000);

  // Global Refresh Button
  const refreshAllBtn = document.getElementById('refresh-all-btn');
  if (refreshAllBtn) {
    refreshAllBtn.addEventListener('click', () => {
      pollLiveTelemetry();
      pollAlerts();
      showToast('Telemetry and alerts refreshed', 'info');
    });
  }

  // ================= THEME TOGGLE =================
  function initTheme() {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (!toggleBtn) return;

    const savedTheme = localStorage.getItem('aiops-theme') || 'dark';
    if (savedTheme === 'light') {
      document.body.classList.remove('dark-theme');
      document.body.classList.add('light-theme');
      toggleBtn.textContent = '☀️';
    }

    toggleBtn.addEventListener('click', () => {
      const isLight = document.body.classList.contains('light-theme');
      if (isLight) {
        document.body.classList.remove('light-theme');
        document.body.classList.add('dark-theme');
        toggleBtn.textContent = '🌙';
        localStorage.setItem('aiops-theme', 'dark');
      } else {
        document.body.classList.remove('dark-theme');
        document.body.classList.add('light-theme');
        toggleBtn.textContent = '☀️';
        localStorage.setItem('aiops-theme', 'light');
      }
    });
  }

  // ================= TAB NAVIGATION =================
  function initTabs() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
      item.addEventListener('click', () => {
        const targetTab = item.getAttribute('data-tab');
        if (!targetTab) return;

        navItems.forEach(n => n.classList.remove('active'));
        item.classList.add('active');

        document.querySelectorAll('.tab-pane').forEach(pane => {
          pane.classList.remove('active');
        });

        const activePane = document.getElementById(`pane-${targetTab}`);
        if (activePane) {
          activePane.classList.add('active');
        }
      });
    });
  }

  // ================= TOAST NOTIFICATIONS =================
  function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease-out';
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // ================= LIVE TELEMETRY & METRICS =================
  async function pollLiveTelemetry() {
    try {
      const res = await fetch('/api/metrics/live');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      updateTelemetryUI(data);
    } catch (err) {
      console.warn('Telemetry polling error:', err);
      const targetCard = document.getElementById('card-target-status');
      if (targetCard) {
        targetCard.textContent = 'DEGRADED';
        targetCard.className = 'stat-value text-danger';
      }
      const sysPill = document.getElementById('system-status-pill');
      if (sysPill) {
        sysPill.className = 'status-pill degraded';
        document.getElementById('system-status-text').textContent = 'System: Telemetry Offline';
      }
    }
  }

  function updateTelemetryUI(data) {
    const metrics = data.metrics || {};
    const timestamp = new Date().toLocaleTimeString();

    // Updated Time
    const updateTimeEl = document.getElementById('metrics-updated-time');
    if (updateTimeEl) updateTimeEl.textContent = `Updated: ${timestamp}`;

    // Target Status
    const targetEl = document.getElementById('card-target-status');
    const sysPill = document.getElementById('system-status-pill');
    const sysText = document.getElementById('system-status-text');
    if (data.status === 'ok') {
      if (targetEl) {
        targetEl.textContent = 'UP';
        targetEl.className = 'stat-value text-success';
      }
      if (sysPill) {
        sysPill.className = 'status-pill';
        sysText.textContent = 'System: Healthy';
      }
    }

    // Request Rate
    const reqRate = metrics.request_rate || 0;
    const reqCard = document.getElementById('card-request-rate');
    if (reqCard) reqCard.textContent = `${reqRate.toFixed(2)} req/s`;

    // Latency
    const latency = metrics.latency_ms || 0;
    const latCard = document.getElementById('card-latency');
    if (latCard) {
      latCard.textContent = `${latency.toFixed(1)} ms`;
      latCard.className = latency > 500 ? 'stat-value text-warning' : 'stat-value';
    }

    // Error Rate
    const errorRate = metrics.error_rate || 0;
    const errCard = document.getElementById('card-error-rate');
    if (errCard) {
      errCard.textContent = `${errorRate.toFixed(3)} err/s`;
      errCard.className = errorRate > 0.05 ? 'stat-value text-danger' : 'stat-value';
    }

    // Update Telemetry Table
    const tableBody = document.getElementById('telemetry-table-body');
    if (tableBody) {
      tableBody.innerHTML = `
        <tr>
          <td><strong>Request Throughput</strong></td>
          <td><span class="mono">${reqRate.toFixed(2)} req/s</span></td>
          <td><code>rate(http_requests_total[5m])</code></td>
        </tr>
        <tr>
          <td><strong>Latency p95 (ms)</strong></td>
          <td><span class="mono">${latency.toFixed(1)} ms</span></td>
          <td><code>histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))</code></td>
        </tr>
        <tr>
          <td><strong>Error Rate (5xx)</strong></td>
          <td><span class="mono ${errorRate > 0 ? 'text-danger' : ''}">${errorRate.toFixed(3)} err/s</span></td>
          <td><code>rate(http_requests_total{status=~"5.."}[5m])</code></td>
        </tr>
        <tr>
          <td><strong>Synthetic CPU Load Gauge</strong></td>
          <td><span class="mono">${metrics.cpu_usage || 15}%</span></td>
          <td><code>aiops_simulated_load_level</code></td>
        </tr>
        <tr>
          <td><strong>Synthetic Memory Pressure</strong></td>
          <td><span class="mono">${metrics.memory_usage || 20}%</span></td>
          <td><code>aiops_simulated_memory_pressure_percent</code></td>
        </tr>
      `;
    }

    // Update Chart
    updateChart(timestamp, reqRate, latency, metrics.cpu_usage || 15);
  }

  // ================= TELEMETRY CHART =================
  function initChart() {
    const ctx = document.getElementById('telemetryChart');
    if (!ctx) return;

    telemetryChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartHistory.labels,
        datasets: [
          {
            label: 'Request Rate (req/s)',
            data: chartHistory.requestRates,
            borderColor: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            tension: 0.35,
            fill: true
          },
          {
            label: 'Latency (ms / 10)',
            data: chartHistory.latencies,
            borderColor: '#f59e0b',
            borderDash: [5, 5],
            tension: 0.35,
            fill: false
          },
          {
            label: 'Synthetic CPU (% / 10)',
            data: chartHistory.cpuUsages,
            borderColor: '#a855f7',
            tension: 0.35,
            fill: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } }
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { family: 'JetBrains Mono', size: 10 } }
          }
        },
        plugins: {
          legend: {
            labels: { color: '#cbd5e1', font: { family: 'Inter', size: 11 } }
          }
        }
      }
    });
  }

  function updateChart(time, reqRate, latency, cpuUsage) {
    if (!telemetryChart) return;

    chartHistory.labels.push(time);
    chartHistory.requestRates.push(reqRate);
    chartHistory.latencies.push(latency / 10);
    chartHistory.cpuUsages.push(cpuUsage / 10);

    if (chartHistory.labels.length > MAX_HISTORY_POINTS) {
      chartHistory.labels.shift();
      chartHistory.requestRates.shift();
      chartHistory.latencies.shift();
      chartHistory.cpuUsages.shift();
    }

    telemetryChart.update();
  }

  // ================= FORM HANDLERS & ML =================
  function initForms() {
    // Populate Live Features
    const btnPopulate = document.getElementById('btn-populate-live-features');
    if (btnPopulate) {
      btnPopulate.addEventListener('click', async () => {
        try {
          const res = await fetch('/api/metrics/live');
          if (!res.ok) throw new Error('Failed to fetch live telemetry');
          const data = await res.json();
          const m = data.metrics || {};
          document.getElementById('input-cpu').value = m.cpu_usage || 20;
          document.getElementById('input-mem').value = m.memory_usage || 25;
          document.getElementById('input-latency').value = Math.round(m.latency_ms || 50);
          document.getElementById('input-error-rate').value = (m.error_rate || 0.00).toFixed(2);
          document.getElementById('input-request-rate').value = Math.round(m.request_rate || 10);
          showToast('Form populated from live Prometheus telemetry', 'success');
        } catch (e) {
          showToast(`Error populating: ${e.message}`, 'error');
        }
      });
    }

    // Prediction Form
    const predForm = document.getElementById('prediction-form');
    if (predForm) {
      predForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await runPrediction();
      });
    }

    const btnExplain = document.getElementById('btn-run-explain');
    if (btnExplain) {
      btnExplain.addEventListener('click', async () => {
        await runExplanation();
      });
    }

    // RCA Form
    const rcaForm = document.getElementById('rca-form');
    if (rcaForm) {
      rcaForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await runRCA();
      });
    }

    // Optimizer Form
    const optForm = document.getElementById('optimizer-form');
    if (optForm) {
      optForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await runOptimizer();
      });
    }

    // Remediation Form
    const remForm = document.getElementById('remediation-form');
    if (remForm) {
      remForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        await runRemediationPlan();
      });
    }
  }

  function getFeatureInput() {
    return {
      cpu_usage: parseFloat(document.getElementById('input-cpu').value),
      memory_usage: parseFloat(document.getElementById('input-mem').value),
      latency_ms: parseFloat(document.getElementById('input-latency').value),
      error_rate: parseFloat(document.getElementById('input-error-rate').value),
      request_rate: parseFloat(document.getElementById('input-request-rate').value),
      threshold: parseFloat(document.getElementById('input-threshold').value) || 0.5
    };
  }

  async function runPrediction() {
    const payload = getFeatureInput();
    const btn = document.getElementById('btn-run-prediction');
    if (btn) btn.disabled = true;

    try {
      const res = await fetch('/api/ml/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Prediction failed');

      displayPrediction(data);
      // Auto-trigger SHAP attribution
      await runExplanation();
      showToast('Model prediction & SHAP evaluated', 'success');
    } catch (err) {
      showToast(`Prediction failed: ${err.message}`, 'error');
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  function displayPrediction(data) {
    const placeholder = document.getElementById('prediction-result-container');
    const details = document.getElementById('prediction-details');
    if (placeholder) placeholder.style.display = 'none';
    if (details) details.style.display = 'block';

    const pct = Math.round((data.failure_probability || 0) * 100);
    const riskGaugeVal = document.getElementById('res-risk-percentage');
    const riskBadge = document.getElementById('res-risk-badge');
    const interpText = document.getElementById('res-interpretation-text');

    if (riskGaugeVal) riskGaugeVal.textContent = `${pct}%`;
    if (riskBadge) {
      riskBadge.textContent = data.predicted_failure ? 'HIGH RISK' : 'NOMINAL';
      riskBadge.className = data.predicted_failure ? 'risk-label badge-danger' : 'risk-label badge-success';
    }

    if (interpText) {
      interpText.textContent = data.interpretation || `Predicted probability is ${pct}%. Decision threshold applied: ${data.threshold}.`;
    }

    // Also update overview card
    const cardRisk = document.getElementById('card-failure-risk');
    const cardMeta = document.getElementById('card-failure-meta');
    if (cardRisk) {
      cardRisk.textContent = data.predicted_failure ? 'High Risk' : 'Nominal';
      cardRisk.className = data.predicted_failure ? 'stat-value text-danger' : 'stat-value text-success';
    }
    if (cardMeta) {
      cardMeta.textContent = `Failure Prob: ${pct}% (thr: ${data.threshold})`;
    }
  }

  async function runExplanation() {
    const payload = getFeatureInput();
    try {
      const res = await fetch('/api/ml/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'SHAP failed');

      renderShapBars(data.feature_importances || data.shap_values || {});
    } catch (err) {
      console.warn('SHAP computation warning:', err);
    }
  }

  function renderShapBars(features) {
    const container = document.getElementById('shap-bars-container');
    if (!container) return;
    container.innerHTML = '';

    const entries = Object.entries(features);
    if (entries.length === 0) {
      container.innerHTML = '<p class="text-muted">No feature attributions returned.</p>';
      return;
    }

    // Sort by absolute attribution value
    entries.sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
    const maxVal = Math.max(...entries.map(e => Math.abs(e[1])), 0.01);

    entries.forEach(([name, val]) => {
      const fillWidth = Math.min(100, Math.round((Math.abs(val) / maxVal) * 100));
      const isPos = val >= 0;
      const item = document.createElement('div');
      item.className = 'shap-item';
      item.innerHTML = `
        <div class="shap-meta">
          <span><strong>${name}</strong></span>
          <span class="${isPos ? 'text-danger' : 'text-success'}">${val > 0 ? '+' : ''}${val.toFixed(4)}</span>
        </div>
        <div class="shap-bar-bg">
          <div class="shap-bar-fill ${isPos ? 'positive' : 'negative'}" style="width: ${fillWidth}%;"></div>
        </div>
      `;
      container.appendChild(item);
    });
  }

  // ================= ROOT CAUSE ANALYSIS =================
  async function runRCA() {
    const rawLogs = document.getElementById('rca-logs').value;
    const rawEvents = document.getElementById('rca-events').value;
    const logs = rawLogs.split('\n').map(l => l.trim()).filter(Boolean);
    const events = rawEvents.split('\n').map(e => e.trim()).filter(Boolean);

    // Current metrics
    const metrics = {
      cpu_usage: parseFloat(document.getElementById('input-cpu')?.value || 80),
      memory_usage: parseFloat(document.getElementById('input-mem')?.value || 75),
      latency_ms: parseFloat(document.getElementById('input-latency')?.value || 300),
      error_rate: parseFloat(document.getElementById('input-error-rate')?.value || 0.05),
      request_rate: parseFloat(document.getElementById('input-request-rate')?.value || 20)
    };

    const container = document.getElementById('rca-results-container');
    container.innerHTML = '<div class="text-center p-3 text-muted">Evaluating multi-factor RCA engine...</div>';

    try {
      const res = await fetch('/api/ml/rca', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ metrics, logs, events })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'RCA diagnostic error');

      renderRCAFindings(data);
      showToast('RCA triage diagnostics complete', 'success');
    } catch (err) {
      container.innerHTML = `<div class="notice-box text-danger">Error: ${err.message}</div>`;
      showToast(`RCA Error: ${err.message}`, 'error');
    }
  }

  function renderRCAFindings(data) {
    const container = document.getElementById('rca-results-container');
    if (!container) return;

    const causes = data.ranked_root_causes || data.ranked_causes || [];
    if (causes.length === 0) {
      container.innerHTML = '<div class="notice-box">No anomalous patterns identified. Cluster nominal.</div>';
      return;
    }

    let html = `<div class="mb-3"><strong>Primary Assessment:</strong> ${data.summary || data.primary_cause || 'Undetermined'}</div>`;
    causes.forEach((c, idx) => {
      const evidenceHtml = (c.evidence || []).map(e => `<li>${e}</li>`).join('');
      const recs = c.recommended_actions || c.recommendations || [];
      const recsHtml = recs.map(r => `<li>${r}</li>`).join('');
      const scoreDisplay = c.relative_score_percent !== undefined ? `${c.relative_score_percent}%` : `${c.score} pts`;

      html += `
        <div class="rca-card">
          <div class="rca-header">
            <span class="rca-rank">#${idx + 1}</span>
            <strong>${c.cause}</strong>
            <span class="rca-score badge ${c.score >= 2 ? 'badge-danger' : 'badge-warning'}">Rank Score: ${scoreDisplay}</span>
          </div>
          <div class="mt-2">
            <small><strong>Observed Evidence:</strong></small>
            <ul style="font-size: 0.75rem; margin-left: 1.2rem; color: #94a3b8;">${evidenceHtml}</ul>
          </div>
          <div class="mt-2">
            <small><strong>Recommended Triage:</strong></small>
            <ul style="font-size: 0.75rem; margin-left: 1.2rem; color: #38bdf8;">${recsHtml}</ul>
          </div>
        </div>
      `;
    });

    html += `<div class="notice-box mt-3"><small><strong>Engineering Note:</strong> Findings reflect rule-based symptom correlations, not physical causal proof.</small></div>`;
    container.innerHTML = html;
  }

  function initPresets() {
    document.querySelectorAll('.rca-preset-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const preset = btn.getAttribute('data-preset');
        const logsEl = document.getElementById('rca-logs');
        const eventsEl = document.getElementById('rca-events');

        if (preset === 'error') {
          logsEl.value = 'ERROR: Downstream payment service HTTP 504 Gateway Timeout\nERROR: Connection timed out to payments.internal:8443';
          eventsEl.value = 'deployment/aiops-app rollout updated image to v0.1.2';
          document.getElementById('input-error-rate').value = '0.15';
          document.getElementById('input-latency').value = '850';
        } else if (preset === 'cpu') {
          logsEl.value = 'WARNING: Worker pool thread starvation\nWARN: Task queue latency exceeding 2000ms';
          eventsEl.value = 'horizontal-pod-autoscaler scaling event triggered';
          document.getElementById('input-cpu').value = '96';
          document.getElementById('input-latency').value = '600';
        } else if (preset === 'traffic') {
          logsEl.value = 'INFO: Inbound request rate peaked at 450 req/s\nWARN: Cache hit ratio dropped to 42%';
          eventsEl.value = 'traffic ingress burst from external campaign';
          document.getElementById('input-request-rate').value = '150';
          document.getElementById('input-cpu').value = '75';
        }
        showToast(`Loaded "${preset}" scenario preset`, 'info');
      });
    });
  }

  // ================= RESOURCE OPTIMIZER =================
  async function runOptimizer() {
    const payload = {
      replicas: parseInt(document.getElementById('opt-replicas').value, 10),
      cpu_request_m: parseInt(document.getElementById('opt-cpu-req').value, 10),
      cpu_usage_percent: parseFloat(document.getElementById('opt-cpu-pct').value),
      memory_usage_percent: parseFloat(document.getElementById('opt-mem-pct').value),
      sustained_duration_min: parseInt(document.getElementById('opt-sustained').value, 10),
      error_ratio_percent: parseFloat(document.getElementById('opt-error-ratio').value)
    };

    const container = document.getElementById('optimizer-results-container');
    container.innerHTML = '<div class="text-center p-3 text-muted">Calculating rightsizing recommendations...</div>';

    try {
      const res = await fetch('/api/ml/optimize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Optimizer calculation failed');

      renderOptimizerFindings(data);
      showToast('Optimization recommendations generated', 'success');
    } catch (err) {
      container.innerHTML = `<div class="notice-box text-danger">Error: ${err.message}</div>`;
      showToast(`Optimizer Error: ${err.message}`, 'error');
    }
  }

  function renderOptimizerFindings(data) {
    const container = document.getElementById('optimizer-results-container');
    if (!container) return;

    const recActions = (data.recommended_actions || []).map(a => `<li>${a}</li>`).join('');

    container.innerHTML = `
      <div class="opt-card">
        <div class="stat-header">
          <span class="stat-title">Optimization Status</span>
          <span class="badge ${data.status === 'scale_up_recommended' ? 'badge-warning' : data.status === 'scale_down_recommended' ? 'badge-info' : 'badge-success'}">${data.status || 'NOMINAL'}</span>
        </div>
        <div class="form-grid mt-2 mb-2">
          <div>
            <div class="text-muted" style="font-size: 0.75rem;">Recommended Replicas</div>
            <div class="stat-value text-info">${data.recommended_replicas ?? '--'}</div>
          </div>
          <div>
            <div class="text-muted" style="font-size: 0.75rem;">Recommended CPU Req</div>
            <div class="stat-value text-info">${data.recommended_cpu_request_m ? data.recommended_cpu_request_m + 'm' : '--'}</div>
          </div>
        </div>
        <div class="mt-2">
          <small><strong>Action Items:</strong></small>
          <ul style="font-size: 0.8rem; margin-left: 1.2rem; color: #cbd5e1;">${recActions}</ul>
        </div>
      </div>
      <div class="notice-box mt-3">
        <small><strong>Guardrail Note:</strong> Recommendations include safety headroom and do not auto-apply. Apply through audited GitOps / PR pipeline.</small>
      </div>
    `;
  }

  // ================= PROMETHEUS ALERTS =================
  async function pollAlerts() {
    try {
      const res = await fetch('/api/alerts');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      updateAlertsUI(data);
    } catch (err) {
      console.warn('Alert polling warning:', err);
    }
  }

  function updateAlertsUI(data) {
    const tableBody = document.getElementById('alerts-table-body');
    const badgeCount = document.getElementById('alerts-count');
    if (!tableBody) return;

    const alerts = data.rules || data.alerts || [];
    let firingCount = 0;

    if (alerts.length === 0) {
      tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No alert rules loaded or Prometheus offline.</td></tr>';
      if (badgeCount) badgeCount.textContent = '0';
      return;
    }

    let rowsHtml = '';
    alerts.forEach(rule => {
      const state = rule.state || 'inactive';
      if (state === 'firing') firingCount++;

      const stateBadge = state === 'firing'
        ? '<span class="badge badge-danger">FIRING</span>'
        : state === 'pending'
        ? '<span class="badge badge-warning">PENDING</span>'
        : '<span class="badge badge-success">OK / INACTIVE</span>';

      const sev = rule.labels?.severity || rule.severity || 'warning';
      const sevBadge = sev === 'critical' ? '<span class="badge badge-danger">critical</span>' : '<span class="badge badge-warning">warning</span>';

      rowsHtml += `
        <tr>
          <td><strong>${rule.name || rule.alert}</strong></td>
          <td>${stateBadge}</td>
          <td>${sevBadge}</td>
          <td><code class="mono" style="font-size: 0.75rem;">${rule.query || rule.expr || '--'}</code></td>
          <td><span style="font-size: 0.8rem;">${rule.annotations?.description || rule.description || '--'}</span></td>
        </tr>
      `;
    });

    tableBody.innerHTML = rowsHtml;
    if (badgeCount) badgeCount.textContent = firingCount.toString();
  }

  const btnRefreshAlerts = document.getElementById('btn-refresh-alerts');
  if (btnRefreshAlerts) {
    btnRefreshAlerts.addEventListener('click', () => {
      pollAlerts();
      showToast('Polled latest alert rule states', 'info');
    });
  }

  // ================= REMEDIATION DRY-RUN PREVIEWS =================
  async function runRemediationPlan() {
    const action = document.getElementById('rem-action').value;
    const deployment = document.getElementById('rem-deployment').value;
    const namespace = document.getElementById('rem-namespace').value;
    const replicas = parseInt(document.getElementById('rem-replicas').value, 10);

    const payload = {
      action: action,
      deployment: deployment,
      namespace: namespace,
      replicas: replicas
    };

    const container = document.getElementById('remediation-results-container');
    container.innerHTML = '<div class="text-center p-3 text-muted">Validating safeguard rules and generating preview...</div>';

    try {
      const res = await fetch('/api/remediation/plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Plan generation failed');

      renderRemediationPreview(data);
      showToast('Dry-run remediation plan generated', 'success');
    } catch (err) {
      container.innerHTML = `<div class="notice-box text-danger">Error: ${err.message}</div>`;
      showToast(`Remediation Error: ${err.message}`, 'error');
    }
  }

  function renderRemediationPreview(data) {
    const container = document.getElementById('remediation-results-container');
    if (!container) return;

    container.innerHTML = `
      <div class="opt-card">
        <div class="stat-header">
          <span class="stat-title">Safeguard Evaluation</span>
          <span class="badge badge-success">DRY-RUN (executed: false)</span>
        </div>
        <div class="mt-2">
          <div><strong>Target:</strong> <code>${data.namespace || 'default'}/${data.deployment || 'aiops-app'}</code></div>
          <div class="mt-1"><strong>Action:</strong> <code>${data.action}</code></div>
          <div class="mt-2">
            <strong>Planned Kubectl Command Preview:</strong>
            <pre class="console-box mt-1" style="height: auto; padding: 0.65rem; color: #38bdf8;">${Array.isArray(data.command_preview) ? data.command_preview.join(' ') : (data.command_preview || data.planned_command || data.command || 'kubectl --dry-run=client')}</pre>
          </div>
          <div class="mt-2 text-muted" style="font-size: 0.78rem;">
            <strong>Reasoning:</strong> ${data.reason || 'Requested safe operational remediation.'}
          </div>
        </div>
      </div>
      <div class="notice-box mt-3">
        <small><strong>Safeguard Policy:</strong> Production changes are permanently disabled in this demo environment. To verify manually, run the previewed command with <code>--dry-run=client</code> in your cluster context.</small>
      </div>
    `;
  }

  // ================= CHAOS CONTROLS & LOG CONSOLE =================
  function initChaosControls() {
    const consoleBox = document.getElementById('traffic-console-log');
    const clearBtn = document.getElementById('btn-clear-traffic-log');

    function logEntry(msg, type = 'system') {
      if (!consoleBox) return;
      const entry = document.createElement('div');
      entry.className = `log-entry ${type}`;
      entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
      consoleBox.appendChild(entry);
      consoleBox.scrollTop = consoleBox.scrollHeight;
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (consoleBox) consoleBox.innerHTML = '';
        logEntry('Audit log console cleared.', 'system');
      });
    }

    // Trigger 500 errors
    const btnError = document.getElementById('btn-trigger-errors');
    if (btnError) {
      btnError.addEventListener('click', async () => {
        logEntry('Sending 5 HTTP 500 errors to /demo/error...', 'warn');
        for (let i = 1; i <= 5; i++) {
          try {
            await fetch('/demo/error');
            logEntry(`Error request #${i} sent (500 expected)`, 'error');
          } catch (e) {
            logEntry(`Error request #${i} returned error`, 'error');
          }
        }
        showToast('Sent 5 error requests to /demo/error', 'error');
        pollLiveTelemetry();
        pollAlerts();
      });
    }

    // Trigger Slow Requests
    const btnSlow = document.getElementById('btn-trigger-latency');
    if (btnSlow) {
      btnSlow.addEventListener('click', async () => {
        logEntry('Injecting 3 slow requests to /demo/slow...', 'warn');
        for (let i = 1; i <= 3; i++) {
          try {
            const start = performance.now();
            await fetch('/demo/slow');
            const dur = Math.round(performance.now() - start);
            logEntry(`Slow request #${i} completed in ${dur}ms`, 'warn');
          } catch (e) {
            logEntry(`Slow request #${i} failed: ${e.message}`, 'error');
          }
        }
        showToast('Sent 3 slow latency requests', 'warning');
        pollLiveTelemetry();
      });
    }

    // Set Synthetic Load to 85
    const btnLoadHigh = document.getElementById('btn-set-load-high');
    if (btnLoadHigh) {
      btnLoadHigh.addEventListener('click', async () => {
        logEntry('Calling /demo/load/85 to increase synthetic CPU load gauge...', 'warn');
        try {
          const res = await fetch('/demo/load/85');
          const data = await res.json();
          logEntry(`Gauge updated: ${JSON.stringify(data)}`, 'success');
          showToast('Synthetic load set to 85%', 'warning');
          pollLiveTelemetry();
        } catch (e) {
          logEntry(`Failed to set load: ${e.message}`, 'error');
        }
      });
    }

    // Reset Synthetic Load to 15
    const btnResetLoad = document.getElementById('btn-reset-load');
    if (btnResetLoad) {
      btnResetLoad.addEventListener('click', async () => {
        logEntry('Calling /demo/load/15 to reset synthetic load gauge...', 'system');
        try {
          const res = await fetch('/demo/load/15');
          const data = await res.json();
          logEntry(`Gauge reset: ${JSON.stringify(data)}`, 'success');
          showToast('Synthetic load reset to 15%', 'success');
          pollLiveTelemetry();
        } catch (e) {
          logEntry(`Failed to reset load: ${e.message}`, 'error');
        }
      });
    }
  }
});
