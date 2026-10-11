"""Automated API integration and regression tests for AIOps platform."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "aiops-app"


def test_root_api_json():
    response = client.get("/", headers={"Accept": "application/json"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "endpoints" in data
    assert data["endpoints"]["dashboard"] == "/dashboard"


def test_dashboard_endpoint():
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "AIOps" in response.text


def test_prometheus_metrics_scrape():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "aiops_http_requests_total" in response.text
    assert "aiops_simulated_load_level" in response.text


def test_demo_slow_endpoint():
    response = client.get("/demo/slow")
    assert response.status_code == 200
    data = response.json()
    assert data["demo"] == "slow response"
    assert "delay_seconds" in data


def test_demo_error_endpoint():
    response = client.get("/demo/error")
    assert response.status_code == 500
    data = response.json()
    assert "intentional error" in data["demo"]


def test_demo_load_valid_and_invalid():
    # Valid set load
    resp_valid = client.post("/demo/load/85")
    assert resp_valid.status_code == 200
    data = resp_valid.json()
    assert data["simulated_load_level"] == 85
    assert data["simulated_memory_pressure_percent"] == 68.0

    # Invalid set load (>100)
    resp_invalid = client.post("/demo/load/150")
    assert resp_invalid.status_code == 400


def test_live_metrics_endpoint():
    response = client.get("/api/metrics/live")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "metrics" in data


def test_metrics_queries_endpoint():
    response = client.get("/api/metrics/queries")
    assert response.status_code == 200
    data = response.json()
    assert "queries" in data
    assert "request_rate" in data["queries"]


def test_alerts_endpoint():
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "rules" in data
    assert len(data["rules"]) >= 4


def test_alertmanager_webhook():
    test_payload = {
        "version": "4",
        "groupKey": "test-group",
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {"alertname": "TestAlert", "severity": "warning"},
                "annotations": {"summary": "Test alert notification"},
            }
        ],
    }
    response = client.post("/api/webhook/alerts", json=test_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert data["recorded"] is True


def test_remediation_status():
    response = client.get("/api/remediation/status")
    assert response.status_code == 200
    data = response.json()
    assert data["default_mode"] == "dry_run"
    assert "restart_deployment" in data["supported_actions"]
    assert "scale_deployment" in data["supported_actions"]


def test_remediation_plan_dry_run():
    payload = {
        "action": "scale_deployment",
        "deployment": "aiops-app",
        "namespace": "default",
        "replicas": 3,
        "dry_run": True,
    }
    response = client.post("/api/remediation/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "dry_run"
    assert data["executed"] is False
    assert "kubectl" in data["command_preview"][0]
    assert "--replicas=3" in data["command_preview"]


def test_remediation_forbidden_namespace():
    payload = {
        "action": "scale_deployment",
        "deployment": "aiops-app",
        "namespace": "kube-system",
        "replicas": 3,
    }
    response = client.post("/api/remediation/plan", json=payload)
    assert response.status_code == 403


def test_orchestration_health_and_analyze():
    resp_health = client.get("/api/orchestration/health")
    assert resp_health.status_code == 200

    resp_analyze = client.post(
        "/api/orchestration/analyze",
        json={
            "cpu_usage": 92.0,
            "memory_usage": 85.0,
            "latency_ms": 650.0,
            "error_rate": 0.08,
            "request_rate": 45.0,
            "deployment": "aiops-app",
            "namespace": "default",
        },
    )
    assert resp_analyze.status_code == 200
    data = resp_analyze.json()
    assert "incident_analysis" in data
    assert data["incident_analysis"]["severity"] in ("high", "critical")
    assert data["remediation_plan"]["executed"] is False
