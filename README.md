# Explainable AI-Driven AIOps Framework for Predictive Failure Detection, Root-Cause Analysis, and Intelligent Cloud Resource Optimization

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Prometheus](https://img.shields.io/badge/Prometheus-3.0+-E6522C.svg)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Latest-F46800.svg)](https://grafana.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Minikube-326CE5.svg)](https://kubernetes.io/)
[![Tests](https://img.shields.io/badge/Tests-22%2F22%20Passing-success.svg)](file:///tests/)

An end-to-end cloud-native AIOps platform that unifies real-time application telemetry, machine learning failure risk prediction, SHAP-based model interpretability, rule-based root cause analysis (RCA), intelligent resource optimization, and guarded, dry-run Kubernetes remediation into one responsive, single-pane-of-glass dashboard.

---

## 🏗️ Architecture Overview

```mermaid
flowchart TD
    subgraph Workload ["Application Layer"]
        App["FastAPI Service (aiops-app:8000)"]
        UI["Modern Web Dashboard (/dashboard)"]
        MetricsEp["/metrics & Middleware"]
        App --> UI
        App --> MetricsEp
    end

    subgraph Observability ["Observability Stack"]
        Prom["Prometheus (9090)"]
        Graf["Grafana (3000)"]
        Alerts["Alert Rules (aiops_alerts.yml)"]
        MetricsEp -- Scrape (15s) -- Prom
        Prom -- Dashboard Queries -- Graf
        Prom -- Evaluates Rules -- Alerts
    end

    subgraph Intelligence ["AIOps & ML Engine"]
        Collector["Metrics Collector & Transformer"]
        RFModel["Random Forest Classifier (ROC-AUC 0.751)"]
        SHAP["SHAP TreeExplainer"]
        RCA["Rule-Based RCA Engine"]
        Opt["Resource Optimizer"]
        
        Prom --> Collector
        Collector --> RFModel
        RFModel --> SHAP
        RFModel --> RCA
    end

    subgraph OrchestrationLayer ["Guarded Orchestration & Remediation"]
        Orch["/api/orchestration/analyze"]
        Remed["/api/remediation/plan"]
        K8s["Kubernetes (Minikube Cluster)"]

        Prom --> Orch
        Orch --> Remed
        Remed -. Dry-Run Preview (executed: false) .-> K8s
    end

    subgraph Edge ["Public Edge Delivery"]
        Tunnel["Cloudflare Tunnel (HTTP/2 Edge TLS)"]
        App --> Tunnel
    end
```

---

## 🌟 Modules Implemented (1 to 12)

1. **Module 1 — Cloud-Native Monitoring Base**: FastAPI application instrumented with Prometheus client metrics, custom latency histograms, request counters, and synthetic error/load triggers.
2. **Module 2 — Metrics Ingestion & Collector**: Automated time-series metric collector (`data/collect_metrics.py`) and schema transformation pipeline (`data/transform_metrics.py`).
3. **Module 3 — Predictive Failure Model**: Scikit-Learn Random Forest pipeline (`ml/train_failure_model.py`) predicting failure risks with cross-validation (`ROC-AUC: 0.751`, `Precision: 0.455`).
4. **Module 4 — Model Explainability (SHAP)**: Feature importance attribution using SHAP TreeExplainer, generating JSON summaries and visual waterfall plots (`ml/shap_waterfall.png`).
5. **Module 5 — Root Cause Analysis (RCA)**: Explainable rule-based diagnostic engine scoring failure candidate causes from metrics, logs, and deployment events (`ml/root_cause_analysis.py`).
6. **Module 6 — Cloud Resource Optimizer**: Conservative scaling and CPU/memory request optimization engine recommending rightsizing actions with guardrails (`ml/resource_optimizer.py`).
7. **Module 7 — Unified Web Dashboard**: Polished SRE/DevOps dark-theme interface (`/dashboard`) featuring Chart.js telemetry timeline, interactive SHAP attribution bar charts, scenario presets, and chaos controls.
8. **Module 8 — Live Prometheus Telemetry**: Live metric extraction API querying Prometheus PromQL directly (`/api/metrics/live`).
9. **Module 9 — Multi-Rule Alerting**: 5 Prometheus alerting rules (`AIOpsTargetDown`, `AIOpsHighRequestErrorRate`, `AIOpsHighP95Latency`, `AIOpsDemoErrorCounterIncreasing`, `AIOpsSimulatedLoadHigh`) with Alertmanager routing.
10. **Module 10 — Guarded Kubernetes Remediation**: Allowlisted, guarded remediation API with dry-run protection (`/api/remediation/plan`) and namespace validation.
11. **Module 11 — End-to-End Orchestration**: Unified incident pipeline (`/api/orchestration/analyze`) synthesizing live telemetry, incident severity classification, and remediation command generation.
12. **Module 12 — Capstone Validation**: Comprehensive automated validation suite (`python -m pytest tests/`), runbooks, and acceptance criteria verification.

---

## 🚀 Quickstart Guide

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- (Optional) Minikube & kubectl

### 1. Environment Configuration
Copy the provided `.env.example` file to create your environment file:
```powershell
cp .env.example .env
```

### 2. Run with Docker Compose
```powershell
docker compose up --build -d
docker compose ps
```

### 3. Verify Local Services
- **Interactive Web Dashboard**: [http://localhost:8000/dashboard](http://localhost:8000/dashboard) (or root `/`)
- **Interactive Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Application Health Check**: [http://localhost:8000/health](http://localhost:8000/health)
- **Prometheus UI & Targets**: [http://localhost:9090/targets](http://localhost:9090/targets)
- **Prometheus Alert Rules**: [http://localhost:9090/rules](http://localhost:9090/rules)
- **Grafana Observability Portal**: [http://localhost:3000](http://localhost:3000) *(admin / change-this-password)*

### 4. Run Automated Tests
```powershell
python -m pytest tests/ -v
```
All 22 unit and integration tests validate startup, telemetry, predictions, SHAP attributions, RCA, and dry-run remediation.

### 5. Start Cloudflare Public HTTPS Tunnel
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-tunnel.ps1
```
The script initiates a zero-trust quick tunnel and displays a public HTTPS URL (e.g. `https://<unique-name>.trycloudflare.com`) pointing directly to your local application.

---

## 📡 API Endpoint Catalog

| Method | Endpoint | Description | Guardrail / Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Responsive HTML Dashboard (or API root JSON) | Public |
| `GET` | `/dashboard` | SRE/DevOps Observability Dashboard | Public |
| `GET` | `/health` | Application healthcheck | Public |
| `GET` | `/metrics` | Prometheus exposition endpoint | Public Scrape |
| `GET` | `/api/metrics/live` | Live Prometheus PromQL metric queries | Private Telemetry |
| `GET` | `/api/alerts` | Active Prometheus alerting rules & states | Private Telemetry |
| `POST` | `/api/ml/predict` | Random Forest failure prediction | Validated bounds |
| `POST` | `/api/ml/explain` | SHAP TreeExplainer feature attributions | Model bounds |
| `POST` | `/api/ml/rca` | Multi-factor root cause diagnostic triage | Heuristic Scoring |
| `POST` | `/api/ml/optimize` | Cloud rightsizing & replica recommendations | Conservative limits |
| `POST` | `/api/remediation/plan` | Kubernetes remediation preview generator | **Dry-Run Enforced** (`executed: false`) |
| `POST` | `/api/orchestration/analyze` | End-to-end incident analysis pipeline | Recommendation Only |
| `GET` | `/demo/slow` | Simulates high p95 response duration | Controlled Demo |
| `GET` | `/demo/error` | Triggers intentional 500 error burst | Controlled Demo |
| `POST` | `/demo/load/{level}` | Adjusts synthetic load gauge (0–100) | Controlled Demo |

---

## 🔬 AI/ML Experimental Results

| Metric | Measured Value | Notes |
| :--- | :---: | :--- |
| **Dataset Size** | 3,000 observations | 2,250 training / 750 test chronological split |
| **ROC-AUC** | **0.751** | Evaluated on stratified test partition |
| **Average Precision** | **0.368** | Outperforms baseline rate (0.143) by 2.5x |
| **F1 Score** | **0.265** | Tuned to reduce operational false alarms |
| **Top Features (SHAP)** | `request_rate`, `cpu_usage`, `memory_usage` | Visualized in dashboard and `ml/shap_waterfall.png` |

> *Note: Model evaluation metrics are evaluated on synthetic telemetry designed for pipeline demonstration; they must not be cited as real-world production accuracy.*

---

## 🛡️ Safety & Security Constraints
- **Dry-Run Enforcement**: Kubernetes automated actions are permanently constrained in `dry_run: true` mode (`executed: false`).
- **Telemetry Isolation**: Prometheus (9090) and Grafana (3000) administration interfaces are maintained strictly on private networks.
- **Namespace Allowlisting**: Remediation actions validate and restrict targets strictly to the allowlisted `default` namespace and `aiops-app` deployment.
- **Zero Embedded Secrets**: All configuration is handled through `.env.example` templates and environment variables.

---

## 💼 Resume-Ready Summary
> **AI-Driven AIOps Observability & Remediation Platform**
> - Architected and deployed an explainable cloud-native AIOps platform on Docker Compose and Kubernetes, instrumenting microservices with Prometheus telemetry, custom metrics, and Grafana dashboards.
> - Engineered an explainable ML failure prediction pipeline (Random Forest, ROC-AUC 0.751) integrated with SHAP TreeExplainer for real-time feature attribution and interpretability.
> - Built automated diagnostic engines for rule-based Root Cause Analysis (RCA) and conservative cloud resource rightsizing with capacity safety guardrails.
> - Designed a guarded Kubernetes remediation preview engine with strict dry-run enforcement (`executed: false`), allowlist filtering, and Cloudflare Tunnel zero-trust edge delivery.
