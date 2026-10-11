"""Automated tests for AI/ML pipeline, SHAP explainability, RCA, and optimization."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ml_status():
    response = client.get("/api/ml/status")
    assert response.status_code == 200
    data = response.json()
    assert data["model_available"] is True
    assert "features" in data
    assert len(data["features"]) == 5
    assert "RandomForest" in data["model_type"]


def test_ml_predict_nominal():
    payload = {
        "cpu_usage": 15.0,
        "memory_usage": 20.0,
        "latency_ms": 25.0,
        "error_rate": 0.0,
        "request_rate": 10.0,
        "threshold": 0.5,
    }
    response = client.post("/api/ml/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "estimated_failure_risk" in data
    assert data["predicted_class"] == 0
    assert data["predicted_failure"] is False
    assert data["status"] == "nominal"


def test_ml_predict_high_risk():
    payload = {
        "cpu_usage": 95.0,
        "memory_usage": 92.0,
        "latency_ms": 1200.0,
        "error_rate": 0.25,
        "request_rate": 60.0,
        "threshold": 0.4,
    }
    response = client.post("/api/ml/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "estimated_failure_risk" in data
    assert data["estimated_failure_risk"] > 0.4
    assert data["predicted_class"] == 1
    assert data["status"] == "elevated_risk"


def test_ml_predict_validation():
    # Invalid CPU > 100
    payload = {
        "cpu_usage": 150.0,
        "memory_usage": 20.0,
        "latency_ms": 25.0,
        "error_rate": 0.0,
        "request_rate": 10.0,
    }
    response = client.post("/api/ml/predict", json=payload)
    assert response.status_code == 422


def test_ml_explain_shap():
    payload = {
        "cpu_usage": 90.0,
        "memory_usage": 85.0,
        "latency_ms": 500.0,
        "error_rate": 0.1,
        "request_rate": 30.0,
    }
    response = client.post("/api/ml/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "top_drivers" in data
    assert len(data["top_drivers"]) == 5
    assert "feature_importances" in data
    assert "cpu_usage" in data["feature_importances"]
    assert "note" in data


def test_root_cause_analysis():
    payload = {
        "metrics": {
            "cpu_usage": 92.0,
            "memory_usage": 80.0,
            "latency_ms": 450.0,
            "error_rate": 0.08,
        },
        "logs": [
            "ERROR: worker thread pool exhausted",
            "WARN: task latency exceeding threshold",
        ],
        "events": [
            "deployment/aiops-app updated to v0.1.0",
        ],
    }
    response = client.post("/api/ml/rca", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "ranked_root_causes" in data
    assert len(data["ranked_root_causes"]) >= 1
    top_cause = data["ranked_root_causes"][0]
    assert "cause" in top_cause
    assert "score" in top_cause
    assert "evidence" in top_cause


def test_resource_optimizer():
    payload = {
        "replicas": 2,
        "cpu_request_m": 500,
        "cpu_usage_percent": 90.0,
        "memory_usage_percent": 85.0,
        "sustained_duration_min": 10,
        "error_ratio_percent": 3.0,
    }
    response = client.post("/api/ml/optimize", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommended_replicas" in data
    assert "recommended_actions" in data
    assert "raw_report" in data
