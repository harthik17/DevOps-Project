#!/usr/bin/env python3
"""Explainable, rule-based root-cause analysis for AIOps incident snapshots.

This is a transparent starter RCA engine, not a causal inference system.
It ranks plausible causes from metric thresholds, logs, and deployment events.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_INPUT = Path("data/incident_example.json")
DEFAULT_OUTPUT = Path("data/rca_report.json")


def _number(snapshot: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = snapshot.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def analyze_incident(incident: dict[str, Any]) -> dict[str, Any]:
    metrics = incident.get("metrics", {})
    logs = [str(x).lower() for x in incident.get("log_messages", [])]
    events = [str(x).lower() for x in incident.get("deployment_events", [])]

    cpu = _number(metrics, "cpu_usage")
    memory = _number(metrics, "memory_usage")
    latency = _number(metrics, "latency_ms")
    error_rate = _number(metrics, "error_rate")
    request_rate = _number(metrics, "request_rate")
    restart_count = _number(metrics, "restart_count")
    disk = _number(metrics, "disk_usage")
    network_errors = _number(metrics, "network_error_rate")

    causes: dict[str, dict[str, Any]] = {}

    def add(cause: str, points: int, evidence: str, recommendation: str) -> None:
        if cause not in causes:
            causes[cause] = {"score": 0, "evidence": [], "recommendations": []}
        causes[cause]["score"] += points
        causes[cause]["evidence"].append(evidence)
        if recommendation not in causes[cause]["recommendations"]:
            causes[cause]["recommendations"].append(recommendation)

    # Metric-based indicators. Thresholds are configurable starter heuristics.
    if cpu >= 85:
        add("CPU saturation", 3, f"CPU usage is high ({cpu:.1f}%).",
            "Inspect CPU-heavy processes and recent workload changes; scale replicas if demand is sustained.")
    elif cpu >= 70:
        add("CPU saturation", 1, f"CPU usage is elevated ({cpu:.1f}%).",
            "Check CPU utilization by process and compare with the normal baseline.")

    if memory >= 90:
        add("Memory pressure / possible leak", 3, f"Memory usage is critically high ({memory:.1f}%).",
            "Inspect memory trends and heap/process metrics; check for leaks and increase memory limits only after validation.")
    elif memory >= 80:
        add("Memory pressure / possible leak", 2, f"Memory usage is elevated ({memory:.1f}%).",
            "Compare memory usage over time and inspect process or container memory metrics.")

    if latency >= 1000:
        add("Application latency regression", 3, f"Latency is high ({latency:.0f} ms).",
            "Trace slow requests and inspect downstream calls, database queries, and thread/connection pools.")
    elif latency >= 500:
        add("Application latency regression", 2, f"Latency is elevated ({latency:.0f} ms).",
            "Break latency down by endpoint and dependency before changing capacity.")

    if error_rate >= 0.10:
        add("Application errors or failed dependency", 3, f"Error rate is high ({error_rate:.3f} errors/s or ratio, depending on input).",
            "Inspect error logs and dependency health; verify the error-rate unit and compare against a baseline.")
    elif error_rate >= 0.03:
        add("Application errors or failed dependency", 2, f"Error rate is elevated ({error_rate:.3f}).",
            "Group errors by type and endpoint; check downstream service availability.")

    if request_rate >= 50 and (cpu >= 70 or latency >= 500):
        add("Traffic spike / capacity pressure", 3,
            f"Request rate is high ({request_rate:.1f} requests/s) alongside elevated CPU or latency.",
            "Check traffic patterns, rate limits, autoscaling status, and replica capacity.")

    if restart_count >= 3:
        add("Repeated container or process restarts", 3, f"Restart count is high ({restart_count:.0f}).",
            "Inspect container exit codes, liveness/readiness probe failures, and out-of-memory termination events.")
    elif restart_count >= 1:
        add("Container or process restart", 1, f"At least one restart is reported ({restart_count:.0f}).",
            "Review restart timestamps and container logs around the restart.")

    if disk >= 90:
        add("Disk capacity pressure", 3, f"Disk usage is high ({disk:.1f}%).",
            "Check disk and inode usage, log growth, temporary files, and persistent-volume capacity.")

    if network_errors >= 0.05:
        add("Network or service-connectivity issue", 3, f"Network error rate is elevated ({network_errors:.3f}).",
            "Check DNS, service endpoints, network policies, timeouts, and dependency connectivity.")

    # Log indicators.
    log_rules = [
        (("out of memory", "oomkilled", "oom kill", "memoryerror"), "Memory pressure / possible leak", 4,
         "A log mentions an out-of-memory condition.",
         "Inspect memory trends and heap/process metrics; check for leaks and memory-limit events."),
        (("connection refused", "connection reset", "upstream unavailable", "connection timeout", "dns lookup failed"),
         "Network or service-connectivity issue", 3,
         "A log indicates a connection, upstream, timeout, or DNS failure.",
         "Check DNS, service endpoints, network policies, timeouts, and dependency connectivity."),
        (("traceback", "unhandled exception", "internal server error", "http 500"),
         "Application errors or failed dependency", 3,
         "A log indicates an exception or server-side error.",
         "Inspect the stack trace and correlate errors with the affected endpoint and dependency."),
        (("deadlock", "pool exhausted", "too many connections", "queue full"),
         "Resource pool or queue exhaustion", 3,
         "A log indicates a deadlock, exhausted connection pool, or full queue.",
         "Inspect pool/queue depth, connection limits, lock contention, and timeout settings."),
        (("rate limit", "too many requests", "http 429"),
         "Traffic spike / capacity pressure", 2,
         "A log indicates rate limiting or excessive request volume.",
         "Validate traffic volume and client behavior; apply suitable rate limits or scale capacity."),
    ]
    for needles, cause, points, evidence, recommendation in log_rules:
        if any(needle in line for line in logs for needle in needles):
            add(cause, points, evidence, recommendation)

    # Deployment / Kubernetes event indicators.
    event_rules = [
        (("rollout", "deployment", "new version", "image updated", "release"),
         "Recent deployment regression", 3,
         "A deployment or release event was reported near the incident.",
         "Compare error and latency metrics before/after the release; consider rollback if impact aligns."),
        (("failed liveness", "liveness probe", "readiness probe", "probe failed"),
         "Health-check or probe misconfiguration", 3,
         "A Kubernetes health-check probe failure was reported.",
         "Review probe path, timeout, initial delay, and application startup time."),
        (("oomkilled", "evicted", "insufficient memory", "insufficient cpu", "pending pod"),
         "Kubernetes resource or scheduling pressure", 3,
         "A Kubernetes event indicates resource pressure or scheduling trouble.",
         "Inspect pod events, requests/limits, node capacity, and scheduler constraints."),
        (("imagepullbackoff", "errimagepull", "image pull"),
         "Container image pull failure", 4,
         "A Kubernetes event indicates an image-pull failure.",
         "Verify image name/tag, registry access, pull secret, and node network access."),
    ]
    for needles, cause, points, evidence, recommendation in event_rules:
        if any(needle in event for event in events for needle in needles):
            add(cause, points, evidence, recommendation)

    ranked = sorted(causes.items(), key=lambda item: (-item[1]["score"], item[0]))
    max_score = max((item[1]["score"] for item in ranked), default=0)
    results = []
    for cause, details in ranked:
        # Relative ranking score, not a calibrated probability.
        relative = round(100 * details["score"] / max_score) if max_score else 0
        results.append({
            "cause": cause,
            "score": details["score"],
            "relative_score_percent": relative,
            "evidence": details["evidence"],
            "recommended_actions": details["recommendations"],
        })

    return {
        "incident_id": incident.get("incident_id", "incident-unknown"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Explainable rule-based scoring; scores are relative ranks, not probabilities or proof of causality.",
        "metrics_used": metrics,
        "ranked_root_causes": results,
        "summary": (
            f"Top candidate: {results[0]['cause']} (relative score {results[0]['relative_score_percent']}%)."
            if results else
            "No root-cause rule was triggered. Add relevant metrics/logs/events or tune thresholds to your service baseline."
        ),
        "limitations": [
            "This is a heuristic triage aid, not proof of causality.",
            "Validate findings against timestamps, traces, deployment history, and service-specific baselines.",
            "Ensure metric units are consistent before using this in an evaluation or production workflow."
        ],
    }


def demo_incident() -> dict[str, Any]:
    return {
        "incident_id": "demo-high-latency-001",
        "metrics": {
            "cpu_usage": 92,
            "memory_usage": 87,
            "latency_ms": 1350,
            "error_rate": 0.12,
            "request_rate": 64,
            "restart_count": 1,
            "disk_usage": 58,
            "network_error_rate": 0.01
        },
        "log_messages": [
            "HTTP 500 internal server error while calling checkout dependency",
            "connection timeout to payment-service"
        ],
        "deployment_events": [
            "new version deployment started 3 minutes before incident",
            "readiness probe failed for one pod"
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank likely incident root causes from metrics, logs, and deployment events.")
    parser.add_argument("--input", type=Path, help="Path to incident JSON file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output report JSON path.")
    parser.add_argument("--demo", action="store_true", help="Run with a built-in example incident.")
    args = parser.parse_args()

    if args.demo:
        incident = demo_incident()
    else:
        input_path = args.input or DEFAULT_INPUT
        if not input_path.exists():
            parser.error(f"Input file not found: {input_path}. Use --demo or create the JSON input.")
        with input_path.open("r", encoding="utf-8") as f:
            incident = json.load(f)

    report = analyze_incident(incident)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved RCA report to: {args.output}")


if __name__ == "__main__":
    main()
