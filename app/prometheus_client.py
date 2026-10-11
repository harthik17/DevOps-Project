"""Prometheus integration helpers for the unified AIOps dashboard."""
from __future__ import annotations
import os
from typing import Any
import requests

PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090").rstrip("/")

QUERIES = {
    "cpu_usage": '100 * (1 - avg(rate(windows_cpu_time_total{mode="idle"}[5m])))',
    "memory_usage": '100 * (1 - (windows_os_physical_memory_free_bytes / windows_cs_physical_memory_bytes))',
    "latency_ms": '1000 * histogram_quantile(0.95, sum by (le) (rate(aiops_http_request_duration_seconds_bucket[5m])))',
    "error_rate": 'sum(rate(aiops_demo_errors_total[5m]))',
    "request_rate": 'sum(rate(aiops_http_requests_total[5m]))',
    "restart_count": 'sum(kube_pod_container_status_restarts_total)',
    "disk_usage": '100 * (1 - windows_logical_disk_free_bytes / windows_logical_disk_size_bytes)',
}


def query_prometheus(query: str) -> dict[str, Any]:
    response = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query",
        params={"query": query},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {payload}")
    return payload["data"]


def query_metric(query: str) -> float | None:
    data = query_prometheus(query)
    results = data.get("result", [])
    if not results:
        return None
    try:
        return float(results[0]["value"][1])
    except (KeyError, TypeError, ValueError, IndexError):
        return None


def get_live_metrics() -> dict[str, Any]:
    values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for name, query in QUERIES.items():
        try:
            values[name] = query_metric(query)
        except Exception as exc:
            values[name] = None
            errors[name] = f"{type(exc).__name__}: {exc}"

    # Only use metrics actually returned. The API/UI must disclose missing values.
    present = {key: value for key, value in values.items() if value is not None}
    return {
        "prometheus_url": PROMETHEUS_URL,
        "metrics": values,
        "available_metrics": sorted(present.keys()),
        "missing_metrics": sorted(key for key, value in values.items() if value is None),
        "query_errors": errors,
        "note": "Some queries require Windows Exporter or Kubernetes/cAdvisor metrics. App request/error/latency metrics come from the demo application."
    }
