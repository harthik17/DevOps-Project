"""Collect recent Prometheus metrics into CSV.
Run from project root: python data/collect_metrics.py
"""
import argparse
import csv
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

QUERIES = {
    "request_rate_rps": "sum(rate(aiops_http_requests_total[1m]))",
    "latency_p95_seconds": (
        "histogram_quantile(0.95, "
        "sum by (le) (rate(aiops_http_request_duration_seconds_bucket[5m])))"
    ),
    "demo_error_rate_per_second": "sum(rate(aiops_demo_errors_total[1m]))",
    "simulated_load_level": "aiops_simulated_load_level",
    "simulated_memory_pressure_percent": "aiops_simulated_memory_pressure_percent",
    "prometheus_target_up": 'up{job="aiops-app"}',
}

def fetch_range(base_url, query, start, end, step):
    params = urllib.parse.urlencode({
        "query": query, "start": str(start), "end": str(end), "step": str(step)
    })
    url = f"{base_url.rstrip('/')}/api/v1/query_range?{params}"
    request = urllib.request.Request(url, headers={"User-Agent": "AIOps-Metrics-Collector/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("status") != "success":
        raise RuntimeError(f"Prometheus query failed: {payload}")
    return payload.get("data", {}).get("result", [])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:9090")
    parser.add_argument("--minutes", type=int, default=15)
    parser.add_argument("--step", type=int, default=5)
    parser.add_argument("--output", default="data/metrics.csv")
    args = parser.parse_args()
    if args.minutes < 1 or args.step < 1:
        parser.error("--minutes and --step must be positive integers")

    end = datetime.now(timezone.utc).timestamp()
    start = end - args.minutes * 60
    rows = {}
    for column, query in QUERIES.items():
        print(f"Collecting {column} ...")
        try:
            series_list = fetch_range(args.url, query, start, end, args.step)
        except Exception as exc:
            raise SystemExit(
                f"Cannot query Prometheus at {args.url}. Check that it is running. Error: {exc}"
            ) from exc
        for series in series_list:
            for timestamp, raw_value in series.get("values", []):
                epoch = int(float(timestamp))
                value = "" if raw_value in ("NaN", "+Inf", "-Inf") else raw_value
                rows.setdefault(epoch, {})[column] = value

    if not rows:
        raise SystemExit(
            "No metric samples returned. Generate requests, wait 1–2 minutes, "
            "and check the Prometheus target status."
        )

    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ["timestamp_utc", *QUERIES.keys()]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for epoch in sorted(rows):
            writer.writerow({
                "timestamp_utc": datetime.fromtimestamp(epoch, timezone.utc).isoformat(),
                **rows[epoch],
            })
    print(f"Saved {len(rows)} rows to {path}")
    print("Synthetic demo gauges are not actual CPU or RAM measurements.")

if __name__ == "__main__":
    main()
