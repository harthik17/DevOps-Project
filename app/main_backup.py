import random
import time
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="AIOps Monitoring Demo", version="0.1.0")

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

@app.middleware("http")
async def metrics_middleware(request, call_next):
    path = request.url.path
    # Avoid high-cardinality labels such as arbitrary URLs and query strings.
    endpoint = path if path in {"/", "/health", "/demo/slow", "/demo/error"} else "other"
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

@app.get("/")
def root():
    return {
        "project": "Explainable AI-Driven AIOps Framework",
        "module": "Module 1 - Application and Monitoring",
        "status": "running",
        "next_steps": ["collect metrics", "train failure predictor", "add root-cause analysis"],
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

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

@app.post("/demo/load/{level}")
def set_demo_load(level: int):
    """Set a synthetic gauge to help test dashboards; this does not consume CPU or RAM."""
    if not 0 <= level <= 100:
        return JSONResponse(status_code=400, content={"error": "level must be between 0 and 100"})
    SIMULATED_LOAD.set(level)
    MEMORY_PRESSURE.set(min(100, max(0, level * 0.8)))
    return {"simulated_load_level": level, "simulated_memory_pressure_percent": min(100, level * 0.8)}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
