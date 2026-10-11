# Final Demo Runbook

## Suggested 6–8 minute demo
1. Show the architecture and explain the data flow.
2. Open `/health` and show the app is running.
3. Open Prometheus `/targets`; show `aiops-app` is UP.
4. Run `aiops_http_requests_total` and a request-rate query.
5. Show `/api/metrics/live` if Module 8 routes are installed.
6. Show Module 9 rules only if Prometheus loaded them successfully.
7. Run a Module 11 incident analysis and explain that severity rules are transparent starter rules.
8. Show Module 10 remediation plan and verify `executed: false`.
9. Finish with known limitations and planned improvements.

## If something fails
- App: `docker compose logs --tail 100 aiops-app`
- Prometheus: `docker compose logs --tail 100 prometheus`
- Services: `docker compose ps`
- Kubernetes: `kubectl get pods -A`
- Module endpoints: open `http://127.0.0.1:8000/docs`
- Prometheus target list: `http://localhost:9090/targets`
- Prometheus rules: `http://localhost:9090/rules`

## Important integration caveat
Modules were supplied incrementally and some endpoints are separate add-ons. Confirm
each router is registered in the same `app/main.py`, required dependencies are
installed, Prometheus rules file is mounted, and Prometheus config references it.
Do not assume every module is connected just because its files exist.
