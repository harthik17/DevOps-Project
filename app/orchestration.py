"""End-to-end AIOps workflow orchestration.

This service composes available telemetry, prediction, RCA, and remediation
planning into one incident workflow. It does not execute Kubernetes actions.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import requests

router = APIRouter(prefix="/api/orchestration", tags=["orchestration"])
PROMETHEUS_URL = __import__("os").getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")
REQUEST_TIMEOUT = 6

QUERIES = {
    "request_rate": 'sum(rate(aiops_http_requests_total{job="aiops-app"}[5m]))',
    "p95_latency_seconds": 'histogram_quantile(0.95, sum by (le) (rate(aiops_http_request_duration_seconds_bucket{job="aiops-app"}[5m])))',
    "error_rate": 'sum(rate(aiops_http_requests_total{job="aiops-app",status=~"5.."}[5m]))',
    "target_up": 'min(up{job="aiops-app"})',
}

class IncidentRequest(BaseModel):
    cpu_usage: float | None = Field(default=None, ge=0, le=100)
    memory_usage: float | None = Field(default=None, ge=0, le=100)
    latency_ms: float | None = Field(default=None, ge=0)
    error_rate: float | None = Field(default=None, ge=0)
    request_rate: float | None = Field(default=None, ge=0)
    deployment: str = Field(default="aiops-app", pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
    namespace: str = Field(default="default", pattern=r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")

def prom_value(query: str) -> float | None:
    try:
        response = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") != "success":
            return None
        result = payload.get("data", {}).get("result", [])
        if not result:
            return None
        return float(result[0]["value"][1])
    except (requests.RequestException, ValueError, TypeError, KeyError, IndexError):
        return None

def collect_live_metrics() -> dict[str, Any]:
    values = {name: prom_value(query) for name, query in QUERIES.items()}
    return {
        "prometheus_url": PROMETHEUS_URL,
        "metrics": values,
        "available": [key for key, value in values.items() if value is not None],
        "missing": [key for key, value in values.items() if value is None],
    }

def analyze_incident(metrics: dict[str, Any]) -> dict[str, Any]:
    """Transparent baseline rules; this is not a trained ML prediction."""
    reasons: list[str] = []
    severity = "low"
    latency_ms = metrics.get("latency_ms")
    error_rate = metrics.get("error_rate")
    target_up = metrics.get("target_up")
    if target_up == 0:
        severity = "critical"
        reasons.append("Prometheus reports the application target is down.")
    if latency_ms is not None and latency_ms > 500:
        severity = "high" if severity != "critical" else severity
        reasons.append(f"p95 latency is elevated ({latency_ms:.1f} ms).")
    if error_rate is not None and error_rate > 0.05:
        severity = "high" if severity not in ("critical",) else severity
        reasons.append(f"5xx errors are elevated ({error_rate:.3f} errors/sec).")
    if not reasons:
        reasons.append("No configured baseline rule detected an incident from the available metrics.")
    return {
        "severity": severity,
        "reasons": reasons,
        "method": "transparent threshold rules; not a trained ML model or causal proof",
    }

def build_remediation_plan(severity: str, deployment: str, namespace: str) -> dict[str, Any]:
    """Produce a command preview only; never run kubectl from this module."""
    if severity == "critical":
        action = "investigate_target_and_consider_restart"
        command = ["kubectl", "rollout", "status", f"deployment/{deployment}", "-n", namespace]
    elif severity == "high":
        action = "review_capacity_and_consider_scaling"
        command = ["kubectl", "get", f"deployment/{deployment}", "-n", namespace, "-o", "wide"]
    else:
        action = "continue_monitoring"
        command = ["kubectl", "get", f"deployment/{deployment}", "-n", namespace]
    return {"recommended_action": action, "command_preview": command, "executed": False}

@router.get("/health")
def orchestration_health():
    return {"status": "ok", "module": "module11-orchestration"}

@router.get("/metrics/live")
def orchestration_live_metrics():
    return collect_live_metrics()

@router.post("/analyze")
def orchestration_analyze(req: IncidentRequest):
    live = collect_live_metrics()
    supplied = req.model_dump() if hasattr(req, "model_dump") else req.dict()
    metrics = {
        "cpu_usage": supplied["cpu_usage"],
        "memory_usage": supplied["memory_usage"],
        "latency_ms": supplied["latency_ms"],
        "error_rate": supplied["error_rate"],
        "request_rate": supplied["request_rate"],
    }
    # Only fill latency/error/request-rate from Prometheus when not supplied manually.
    live_metrics = live["metrics"]
    if metrics["latency_ms"] is None and live_metrics["p95_latency_seconds"] is not None:
        metrics["latency_ms"] = live_metrics["p95_latency_seconds"] * 1000
    if metrics["error_rate"] is None and live_metrics["error_rate"] is not None:
        metrics["error_rate"] = live_metrics["error_rate"]
    if metrics["request_rate"] is None and live_metrics["request_rate"] is not None:
        metrics["request_rate"] = live_metrics["request_rate"]

    # Translate live target status to a finding without fabricating missing values.
    metrics["target_up"] = live_metrics["target_up"]
    incident = analyze_incident(metrics)
    plan = build_remediation_plan(incident["severity"], req.deployment, req.namespace)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "metrics_used": metrics,
        "prometheus": live,
        "incident_analysis": incident,
        "remediation_plan": plan,
        "execution_policy": "recommendation_only; no commands executed",
    }
