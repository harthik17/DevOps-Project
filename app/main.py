import json
import os
from pathlib import Path
import random
import time
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import requests

from app.prometheus_client import (
    get_live_metrics,
    QUERIES,
    PROMETHEUS_URL,
)
from app.ml_api import router as ml_router
from app.remediation import router as remediation_router
from app.orchestration import router as orchestration_router

# ================= APP DEFINITION =================
app = FastAPI(
    title="Explainable AI-Driven AIOps Platform",
    description="Unified API & Observability Dashboard for Failure Prediction, RCA, and Guarded Remediation",
    version="1.0.0",
)

# ================= CORS MIDDLEWARE =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= ROUTER REGISTRATIONS =================
app.include_router(ml_router)
app.include_router(remediation_router)
app.include_router(orchestration_router)

# ================= STATIC ASSETS =================
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# ================= METRICS DEFINITION =================
REQUESTS = Counter(
    "aiops_http_requests_total",
    "Total HTTP requests handled",
    ["method", "endpoint", "status"],
)
LATENCY = Histogram(
    "aiops_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
ERRORS = Counter("aiops_demo_errors_total", "Errors intentionally triggered in the demo")
SIMULATED_LOAD = Gauge("aiops_simulated_load_level", "Demo load level from 0 to 100")
MEMORY_PRESSURE = Gauge("aiops_simulated_memory_pressure_percent", "Simulated memory pressure percent")

# Set initial nominal baselines
SIMULATED_LOAD.set(15)
MEMORY_PRESSURE.set(20)

# ================= TELEMETRY MIDDLEWARE =================
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    path = request.url.path
    endpoint = path if path in {"/", "/health", "/dashboard", "/demo/slow", "/demo/error"} else "api"
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        REQUESTS.labels(request.method, endpoint, "500").inc()
        raise
    finally:
        LATENCY.labels(endpoint).observe(time.perf_counter() - start)
    REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
    return response

# ================= ROOT & DASHBOARD ENDPOINTS =================
@app.get("/")
def root(request: Request):
    """
    Serves the interactive HTML dashboard when visited by a browser,
    or returns API metadata when queried programmatically.
    """
    accept = request.headers.get("accept", "")
    index_file = STATIC_DIR / "index.html"
    if "text/html" in accept and index_file.exists():
        return FileResponse(str(index_file))

    return {
        "project": "Explainable AI-Driven AIOps Framework",
        "title": "An Explainable AI-Driven AIOps Framework for Predictive Failure Detection, Root-Cause Analysis, and Intelligent Cloud Resource Optimization",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/dashboard",
            "api_docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
            "live_metrics": "/api/metrics/live",
            "ml_status": "/api/ml/status",
            "ml_predict": "/api/ml/predict",
            "ml_explain": "/api/ml/explain",
            "ml_rca": "/api/ml/rca",
            "ml_optimize": "/api/ml/optimize",
            "alerts": "/api/alerts",
            "remediation_status": "/api/remediation/status",
            "remediation_plan": "/api/remediation/plan",
            "orchestration_analyze": "/api/orchestration/analyze",
        },
    }

@app.get("/dashboard")
def dashboard():
    """Serves the SRE / DevOps interactive dashboard."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    raise HTTPException(status_code=404, detail="Dashboard UI index.html not found")

@app.get("/health")
def health():
    return {"status": "healthy", "service": "aiops-app", "timestamp": time.time()}

# ================= CONTROLLED DEMO & CHAOS ENDPOINTS =================
@app.get("/demo/slow")
def demo_slow():
    """Controlled demo endpoint: adds a short delay to demonstrate latency monitoring."""
    delay = random.uniform(0.4, 1.2)
    time.sleep(delay)
    return {"demo": "slow response", "delay_seconds": round(delay, 3)}

@app.get("/demo/error")
def demo_error():
    """Controlled demo endpoint: intentionally returns an error for monitoring tests."""
    ERRORS.inc()
    return JSONResponse(status_code=500, content={"demo": "intentional error for monitoring test"})

@app.api_route("/demo/load/{level}", methods=["GET", "POST"])
def set_demo_load(level: int):
    """Set a synthetic gauge to help test dashboards; this does not consume actual host CPU or RAM."""
    if not 0 <= level <= 100:
        return JSONResponse(status_code=400, content={"error": "level must be between 0 and 100"})
    SIMULATED_LOAD.set(level)
    MEMORY_PRESSURE.set(min(100, max(0, level * 0.8)))
    return {
        "simulated_load_level": level,
        "simulated_memory_pressure_percent": min(100, round(level * 0.8, 1)),
        "type": "synthetic_gauge",
    }

# ================= PROMETHEUS METRICS & QUERIES =================
@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/metrics/live")
def live_metrics():
    result = get_live_metrics()
    if not result.get("available_metrics"):
        # Return fallback status instead of hard 503 so dashboard doesn't break when Prometheus starts up
        return {
            "status": "starting_or_unavailable",
            "prometheus_url": PROMETHEUS_URL,
            "metrics": {
                "request_rate": 0.0,
                "latency_ms": 15.0,
                "error_rate": 0.0,
                "cpu_usage": 15.0,
                "memory_usage": 20.0,
            },
            "available_metrics": [],
            "missing_metrics": ["request_rate", "latency_ms", "error_rate"],
        }
    return result

@app.get("/api/metrics/queries")
def metrics_queries():
    return {
        "prometheus_url": PROMETHEUS_URL,
        "queries": QUERIES,
    }

# ================= PROMETHEUS ALERTS ENDPOINT =================
@app.get("/api/alerts")
def get_alerts():
    """
    Fetches active alerting rules and firing status directly from Prometheus.
    Falls back gracefully to known rules if Prometheus is unreachable.
    """
    prom_rules_url = f"{PROMETHEUS_URL}/api/v1/rules"
    try:
        resp = requests.get(prom_rules_url, timeout=3)
        if resp.ok:
            data = resp.json()
            rules = []
            for group in data.get("data", {}).get("groups", []):
                for rule in group.get("rules", []):
                    if rule.get("type") == "alerting":
                        rules.append({
                            "name": rule.get("name"),
                            "state": rule.get("state", "inactive"),
                            "severity": rule.get("labels", {}).get("severity", "warning"),
                            "query": rule.get("query"),
                            "description": rule.get("annotations", {}).get("description", ""),
                            "summary": rule.get("annotations", {}).get("summary", ""),
                            "active_alerts": rule.get("alerts", []),
                        })
            return {"status": "ok", "source": "prometheus_api", "rules": rules}
    except Exception as e:
        pass

    # Fallback to configured alert rules
    fallback_rules = [
        {
            "name": "AIOpsTargetDown",
            "state": "inactive",
            "severity": "critical",
            "query": 'up{job="aiops-app"} == 0',
            "description": "Prometheus cannot scrape target for at least 1 minute.",
        },
        {
            "name": "AIOpsHighRequestErrorRate",
            "state": "inactive",
            "severity": "warning",
            "query": '5xx error ratio > 0.05 for 2m',
            "description": "The 5xx ratio is above 5% for 2 minutes.",
        },
        {
            "name": "AIOpsHighP95Latency",
            "state": "inactive",
            "severity": "warning",
            "query": 'histogram_quantile(0.95, ...) > 0.5 for 3m',
            "description": "p95 latency is above 500 ms for 3 minutes.",
        },
        {
            "name": "AIOpsDemoErrorCounterIncreasing",
            "state": "inactive",
            "severity": "warning",
            "query": 'increase(aiops_demo_errors_total[5m]) >= 3',
            "description": "At least 3 demo errors were recorded in the last 5 minutes.",
        },
        {
            "name": "AIOpsSimulatedLoadHigh",
            "state": "inactive",
            "severity": "warning",
            "query": 'aiops_simulated_load_level >= 85 for 2m',
            "description": "Synthetic gauge indicates high simulated load.",
        },
    ]
    return {"status": "ok", "source": "configuration_fallback", "rules": fallback_rules}

# ================= ALERTMANAGER WEBHOOK RECEIVER =================
@app.post("/api/webhook/alerts")
async def alert_webhook(request: Request):
    """Webhook endpoint receiving alerts dispatched by Alertmanager."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    out_file = Path(__file__).resolve().parent.parent / "data" / "received_alerts.jsonl"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "received_at_utc": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }) + "\n")

    return {"status": "received", "recorded": True}
