// Interactive Client-Side AIOps Engine & Demo Simulator

document.addEventListener('DOMContentLoaded', () => {
  // Theme Toggle
  const themeToggleBtn = document.getElementById('theme-toggle-btn');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  let currentTheme = localStorage.getItem('theme') || (prefersDark ? 'dark' : 'dark');
  
  document.body.setAttribute('data-theme', currentTheme);
  updateThemeIcon();

  themeToggleBtn.addEventListener('click', () => {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', currentTheme);
    localStorage.setItem('theme', currentTheme);
    updateThemeIcon();
  });

  function updateThemeIcon() {
    themeToggleBtn.textContent = currentTheme === 'dark' ? '🌙' : '☀️';
  }

  // Simulator Inputs
  const cpuInput = document.getElementById('cpu-input');
  const memoryInput = document.getElementById('mem-input');
  const latencyInput = document.getElementById('lat-input');
  const errorInput = document.getElementById('err-input');
  const reqInput = document.getElementById('req-input');

  const cpuVal = document.getElementById('cpu-val');
  const memVal = document.getElementById('mem-val');
  const latVal = document.getElementById('lat-val');
  const errVal = document.getElementById('err-val');
  const reqVal = document.getElementById('req-val');

  // Outputs
  const riskScore = document.getElementById('sim-risk-score');
  const riskBadge = document.getElementById('sim-risk-badge');
  const rcaDiagnosis = document.getElementById('sim-rca-diagnosis');
  const k8sAction = document.getElementById('sim-k8s-action');

  // SHAP fills
  const shapCpuFill = document.getElementById('shap-cpu-fill');
  const shapMemFill = document.getElementById('shap-mem-fill');
  const shapLatFill = document.getElementById('shap-lat-fill');
  const shapErrFill = document.getElementById('shap-err-fill');
  const shapReqFill = document.getElementById('shap-req-fill');

  const shapCpuVal = document.getElementById('shap-cpu-val');
  const shapMemVal = document.getElementById('shap-mem-val');
  const shapLatVal = document.getElementById('shap-lat-val');
  const shapErrVal = document.getElementById('shap-err-val');
  const shapReqVal = document.getElementById('shap-req-val');

  // Simulation logic mimicking the trained Random Forest model & RCA rules
  function updateSimulation() {
    const cpu = parseFloat(cpuInput.value);
    const mem = parseFloat(memoryInput.value);
    const lat = parseFloat(latencyInput.value);
    const err = parseFloat(errorInput.value);
    const req = parseFloat(reqInput.value);

    // Update labels
    cpuVal.textContent = `${cpu.toFixed(1)}%`;
    memVal.textContent = `${mem.toFixed(1)}%`;
    latVal.textContent = `${lat.toFixed(0)} ms`;
    errVal.textContent = `${(err * 100).toFixed(1)}%`;
    reqVal.textContent = `${req.toFixed(0)} req/s`;

    // Logistic / Random Forest approximation calibrated on the actual dataset
    // Baseline risk = 0.05
    let z = -3.2;
    z += (cpu / 100) * 2.8;
    z += (mem / 100) * 3.4;
    z += (Math.min(lat, 2000) / 500) * 1.5;
    z += (err * 10) * 2.2;
    z += (req / 100) * 0.8;

    const risk = 1 / (1 + Math.exp(-z));
    const riskPercent = Math.min(Math.max(Math.round(risk * 100), 1), 99);

    riskScore.textContent = `${riskPercent}%`;

    if (riskPercent >= 45) {
      riskBadge.textContent = 'Elevated Risk';
      riskBadge.className = 'risk-badge elevated';
      riskScore.style.color = '#f43f5e';
    } else {
      riskBadge.textContent = 'Nominal';
      riskBadge.className = 'risk-badge nominal';
      riskScore.style.color = '#34d399';
    }

    // Dynamic SHAP Feature Attributions
    const baseCpu = 0.15 + (cpu / 100) * 0.45;
    const baseMem = 0.18 + (mem / 100) * 0.50;
    const baseLat = 0.10 + (lat / 1500) * 0.35;
    const baseErr = 0.08 + (err * 8) * 0.40;
    const baseReq = 0.05 + (req / 100) * 0.20;

    const totalWeight = baseCpu + baseMem + baseLat + baseErr + baseReq;
    const pCpu = Math.round((baseCpu / totalWeight) * 100);
    const pMem = Math.round((baseMem / totalWeight) * 100);
    const pLat = Math.round((baseLat / totalWeight) * 100);
    const pErr = Math.round((baseErr / totalWeight) * 100);
    const pReq = Math.round((baseReq / totalWeight) * 100);

    shapCpuFill.style.width = `${pCpu}%`;
    shapCpuFill.style.background = '#38bdf8';
    shapCpuVal.textContent = `+${(baseCpu * 0.6).toFixed(3)} (${pCpu}%)`;

    shapMemFill.style.width = `${pMem}%`;
    shapMemFill.style.background = '#818cf8';
    shapMemVal.textContent = `+${(baseMem * 0.6).toFixed(3)} (${pMem}%)`;

    shapLatFill.style.width = `${pLat}%`;
    shapLatFill.style.background = '#fbbf24';
    shapLatVal.textContent = `+${(baseLat * 0.6).toFixed(3)} (${pLat}%)`;

    shapErrFill.style.width = `${pErr}%`;
    shapErrFill.style.background = '#f43f5e';
    shapErrVal.textContent = `+${(baseErr * 0.6).toFixed(3)} (${pErr}%)`;

    shapReqFill.style.width = `${pReq}%`;
    shapReqFill.style.background = '#34d399';
    shapReqVal.textContent = `+${(baseReq * 0.6).toFixed(3)} (${pReq}%)`;

    // Root Cause Analysis & Guarded Kubernetes dry-run recommendation
    if (err >= 0.15 && lat >= 600) {
      rcaDiagnosis.innerHTML = '<strong>Candidate RCA:</strong> Downstream dependency degradation & cascading thread exhaustion (Confidence: 89%).';
      k8sAction.innerHTML = '<span class="code-snippet">kubectl rollout restart deployment/aiops-app -n default</span> (Dry-Run: executed: false)';
    } else if (mem >= 85) {
      rcaDiagnosis.innerHTML = '<strong>Candidate RCA:</strong> High memory pressure / runaway heap leak nearing container cgroup threshold (Confidence: 94%).';
      k8sAction.innerHTML = '<span class="code-snippet">kubectl scale deployment/aiops-app --replicas=3 -n default</span> (Dry-Run: executed: false)';
    } else if (cpu >= 85) {
      rcaDiagnosis.innerHTML = '<strong>Candidate RCA:</strong> CPU saturation due to traffic spike; queue latency backlog (Confidence: 84%).';
      k8sAction.innerHTML = '<span class="code-snippet">kubectl scale deployment/aiops-app --replicas=4 -n default</span> (Dry-Run: executed: false)';
    } else if (lat >= 800) {
      rcaDiagnosis.innerHTML = '<strong>Candidate RCA:</strong> High p95 latency spike caused by connection pool starvation (Confidence: 78%).';
      k8sAction.innerHTML = '<span class="code-snippet">kubectl rollout restart deployment/aiops-app -n default</span> (Dry-Run: executed: false)';
    } else {
      rcaDiagnosis.innerHTML = '<strong>Candidate RCA:</strong> System operating within nominal operational thresholds. No anomalies detected.';
      k8sAction.innerHTML = '<strong>Action:</strong> No remediation required. Telemetry metrics healthy.';
    }
  }

  // Event Listeners for sliders
  [cpuInput, memoryInput, latencyInput, errorInput, reqInput].forEach(slider => {
    slider.addEventListener('input', () => {
      // Clear preset active states
      document.querySelectorAll('.sim-preset-btn').forEach(btn => btn.classList.remove('active'));
      updateSimulation();
    });
  });

  // Preset Buttons
  const presets = {
    nominal: { cpu: 18, mem: 24, lat: 35, err: 0.0, req: 12 },
    memory: { cpu: 45, mem: 92, lat: 280, err: 0.02, req: 28 },
    cpu: { cpu: 94, mem: 60, lat: 480, err: 0.05, req: 75 },
    cascade: { cpu: 88, mem: 88, lat: 1250, err: 0.28, req: 60 },
  };

  document.querySelectorAll('.sim-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sim-preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const presetName = btn.getAttribute('data-preset');
      const p = presets[presetName];
      if (p) {
        cpuInput.value = p.cpu;
        memoryInput.value = p.mem;
        latencyInput.value = p.lat;
        errorInput.value = p.err;
        reqInput.value = p.req;
        updateSimulation();
      }
    });
  });

  // Live Backend & Cloudflare Tunnel Hub Logic
  const backendInput = document.getElementById('backend-url-input');
  const checkBackendBtn = document.getElementById('check-backend-btn');
  const backendStatusPill = document.getElementById('backend-status-pill');
  const backendStatusText = document.getElementById('backend-status-text');
  const backendPulseDot = document.getElementById('backend-pulse-dot');
  const linkDashboard = document.getElementById('link-dashboard');
  const linkDocs = document.getElementById('link-docs');
  const linkMetrics = document.getElementById('link-metrics');

  const savedBackendUrl = localStorage.getItem('aiops_backend_url') || 'http://localhost:8000';
  if (backendInput) {
    backendInput.value = savedBackendUrl;
    updateBackendLinks(savedBackendUrl);

    checkBackendBtn.addEventListener('click', () => {
      const url = backendInput.value.trim().replace(/\/+$/, '');
      localStorage.setItem('aiops_backend_url', url);
      updateBackendLinks(url);
      testBackendHealth(url);
    });

    backendInput.addEventListener('change', () => {
      const url = backendInput.value.trim().replace(/\/+$/, '');
      localStorage.setItem('aiops_backend_url', url);
      updateBackendLinks(url);
      testBackendHealth(url);
    });

    testBackendHealth(savedBackendUrl);
  }

  function updateBackendLinks(baseUrl) {
    if (!baseUrl) return;
    if (linkDashboard) linkDashboard.href = `${baseUrl}/dashboard`;
    if (linkDocs) linkDocs.href = `${baseUrl}/docs`;
    if (linkMetrics) linkMetrics.href = `${baseUrl}/metrics`;
  }

  async function testBackendHealth(baseUrl) {
    if (!backendStatusText) return;
    backendStatusText.textContent = 'Backend: Checking...';
    backendStatusPill.className = 'backend-status-pill offline';
    backendPulseDot.style.background = '#94a3b8';
    backendPulseDot.style.boxShadow = 'none';

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);
      const res = await fetch(`${baseUrl}/health`, { signal: controller.signal });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        backendStatusPill.className = 'backend-status-pill online';
        backendStatusText.textContent = `● Backend: Online (${data.service || 'healthy'})`;
        backendPulseDot.style.background = '#34d399';
        backendPulseDot.style.boxShadow = '0 0 10px #34d399';
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (e) {
      backendStatusPill.className = 'backend-status-pill offline';
      backendStatusText.textContent = '○ Backend: Offline (Using Simulator)';
      backendPulseDot.style.background = '#94a3b8';
      backendPulseDot.style.boxShadow = 'none';
    }
  }

  // Run initial simulation
  updateSimulation();
});

