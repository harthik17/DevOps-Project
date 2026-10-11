# Final Acceptance Checklist — AIOps Capstone

## A. Application and monitoring
- [ ] `http://127.0.0.1:8000/health` returns healthy.
- [ ] `http://localhost:9090/targets` shows `aiops-app` as UP.
- [ ] `aiops_http_requests_total` returns request series.
- [ ] `sum(rate(aiops_http_requests_total[5m]))` returns a numeric value after fresh samples.
- [ ] p95 latency query returns a numeric value after fresh samples.

## B. Modules and APIs
- [ ] Module 8: `/api/metrics/live` returns available/missing metrics clearly.
- [ ] Module 9: `/rules` shows configured alert rules (only if alert rules were mounted and loaded).
- [ ] Module 10: `/api/remediation/status` shows execution disabled by default.
- [ ] Module 10: dry-run plan returns `executed: false`.
- [ ] Module 11: `/api/orchestration/health` returns status ok.
- [ ] Module 11: `/api/orchestration/analyze` returns metrics, analysis and command preview.

## C. ML and explainability
- [ ] Module 3 model is trained and evaluation report reviewed.
- [ ] Synthetic demo data is clearly labeled as synthetic; do not report its scores as real production accuracy.
- [ ] Module 4 SHAP explanation runs successfully on the trained model.
- [ ] Module 2 collected telemetry CSV is inspected for nulls and time coverage.
- [ ] Schema mismatch between collected metrics and Module 3 training features is resolved before claiming live ML inference.

## D. Safety and documentation
- [ ] No production cluster credentials are used for the demo.
- [ ] Kubernetes execution remains disabled unless explicitly approved and tested.
- [ ] Monitoring APIs are not exposed publicly without authentication.
- [ ] Grafana/other demo credentials are changed before any shared deployment.
- [ ] README contains setup, architecture, limitations, screenshots, and reproduction steps.
- [ ] Record versions of Python, Docker, Minikube, Kubernetes, Prometheus, and model dependencies.
- [ ] Include sample alerts and a sample incident JSON response in the report.

## Project status wording
Recommended honest description:
"Prototype AIOps workflow integrating application telemetry, Prometheus monitoring,
starter alert rules, model-based failure-risk experiments, SHAP explainability,
threshold-based incident analysis, and dry-run Kubernetes remediation planning."

Do not claim fully autonomous production remediation, causal root-cause proof,
real CPU/memory monitoring, or real-world model accuracy unless those features
have been implemented and validated with representative data.
