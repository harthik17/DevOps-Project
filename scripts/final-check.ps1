$ErrorActionPreference = "Continue"
Write-Host "=== AIOps Capstone Final Validation ===" -ForegroundColor Cyan

Write-Host "`n[1/6] Docker containers"
docker compose ps

Write-Host "`n[2/6] Kubernetes context"
kubectl config current-context
kubectl get deployments -A

Write-Host "`n[3/6] Application health"
try { Invoke-RestMethod "http://127.0.0.1:8000/health" | ConvertTo-Json -Depth 5 } catch { Write-Host "App health endpoint failed: $($_.Exception.Message)" -ForegroundColor Yellow }

Write-Host "`n[4/6] Prometheus target status"
try {
  Invoke-RestMethod "http://localhost:9090/api/v1/query?query=up" | ConvertTo-Json -Depth 8
} catch {
  Write-Host "Prometheus query failed: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host "`n[5/6] Orchestration health (if Module 11 is installed)"
try { Invoke-RestMethod "http://127.0.0.1:8000/api/orchestration/health" | ConvertTo-Json -Depth 5 } catch { Write-Host "Module 11 endpoint unavailable or app not running." -ForegroundColor Yellow }

Write-Host "`n[6/6] Remediation safety status (if Module 10 is installed)"
try { Invoke-RestMethod "http://127.0.0.1:8000/api/remediation/status" | ConvertTo-Json -Depth 5 } catch { Write-Host "Module 10 endpoint unavailable or app not running." -ForegroundColor Yellow }

Write-Host "`nValidation commands completed. Review warnings above; this script does not change workloads." -ForegroundColor Green
