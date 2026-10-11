#!/usr/bin/env python3
"""Explainable recommendation engine for cloud resource optimization.

This module recommends conservative replica and CPU/memory request changes from
a JSON snapshot. It does not apply changes to Kubernetes automatically.
"""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_INPUT = Path("data/resource_snapshot.json")
DEFAULT_OUTPUT = Path("data/optimization_report.json")


def number(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        return float(data.get(key, default))
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(value, high))


def recommend(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Generate explainable recommendations; inputs are current aggregate snapshots."""
    current = snapshot.get("current", {})
    target = snapshot.get("target", {})
    metrics = snapshot.get("metrics", {})

    replicas = max(1, int(number(current, "replicas", 1)))
    min_replicas = max(1, int(number(target, "min_replicas", 1)))
    max_replicas = max(min_replicas, int(number(target, "max_replicas", 6)))
    cpu_request = max(1, number(current, "cpu_request_millicores", 500))
    memory_request = max(1, number(current, "memory_request_mib", 512))

    cpu = clamp(number(metrics, "cpu_usage_percent"), 0, 100)
    memory = clamp(number(metrics, "memory_usage_percent"), 0, 100)
    latency = max(0, number(metrics, "latency_p95_ms"))
    request_rate = max(0, number(metrics, "request_rate_rps"))
    error_ratio = clamp(number(metrics, "error_ratio"), 0, 1)
    restart_count = max(0, number(metrics, "restart_count"))
    sustained_minutes = max(0, number(metrics, "sustained_minutes", 5))

    recommendations: list[dict[str, Any]] = []
    actions: list[str] = []

    # Scale out only when load is sustained and there is no strong signal of a
    # crash loop / high error ratio that would make scaling alone inappropriate.
    if cpu >= 80 and sustained_minutes >= 5 and error_ratio < 0.10 and replicas < max_replicas:
        desired = min(max_replicas, max(replicas + 1, math.ceil(replicas * cpu / 65)))
        recommendations.append({
            "action": "scale_out",
            "priority": "high",
            "current": {"replicas": replicas},
            "recommended": {"replicas": desired},
            "reason": f"CPU is {cpu:.1f}% for {sustained_minutes:.0f} minutes and error ratio is {error_ratio:.1%}.",
            "guardrails": ["Check node capacity and pod scheduling before scaling.", "Confirm the bottleneck is not a downstream dependency."]
        })
        actions.append("Review the proposed replica increase and available cluster capacity.")
    elif cpu >= 80 and error_ratio >= 0.10:
        recommendations.append({
            "action": "investigate_before_scaling",
            "priority": "high",
            "current": {"replicas": replicas},
            "recommended": {"replicas": replicas},
            "reason": f"CPU is high ({cpu:.1f}%), but the error ratio is also high ({error_ratio:.1%}); scaling alone may hide a dependency or application fault.",
            "guardrails": ["Inspect error logs and dependency health first.", "Scale only after identifying whether capacity is the limiting factor."]
        })

    # Conservative CPU request suggestion based on sustained high usage.
    if cpu >= 85:
        suggested_cpu = int(math.ceil(cpu_request * 1.25 / 50) * 50)
        recommendations.append({
            "action": "review_cpu_request",
            "priority": "medium",
            "current": {"cpu_request_millicores": int(cpu_request)},
            "recommended": {"cpu_request_millicores": suggested_cpu},
            "reason": f"CPU usage is {cpu:.1f}%; the configured request may not reflect observed demand.",
            "guardrails": ["Validate CPU limits, throttling, and node capacity.", "Requests affect scheduling; test changes in staging."]
        })

    # Memory headroom is important: do not recommend shrinking memory.
    if memory >= 85:
        suggested_memory = int(math.ceil(memory_request * 1.25 / 64) * 64)
        recommendations.append({
            "action": "review_memory_request",
            "priority": "high",
            "current": {"memory_request_mib": int(memory_request)},
            "recommended": {"memory_request_mib": suggested_memory},
            "reason": f"Memory usage is {memory:.1f}%; increase headroom only after checking for leaks and OOM events.",
            "guardrails": ["Check memory limits and OOMKilled events.", "Investigate memory growth over time before treating this as a sizing problem."]
        })

    # Scale in only with low utilization over a sustained period and enough replicas.
    if cpu <= 25 and memory <= 60 and sustained_minutes >= 15 and replicas > min_replicas:
        desired = max(min_replicas, replicas - 1)
        recommendations.append({
            "action": "scale_in_candidate",
            "priority": "low",
            "current": {"replicas": replicas},
            "recommended": {"replicas": desired},
            "reason": f"CPU is {cpu:.1f}% and memory is {memory:.1f}% for {sustained_minutes:.0f} minutes.",
            "guardrails": ["Check peak-hour traffic and latency before scaling in.", "Use a gradual rollout and maintain availability."]
        })

    if latency >= 1000:
        recommendations.append({
            "action": "investigate_latency",
            "priority": "high",
            "current": {"latency_p95_ms": latency},
            "recommended": {"latency_p95_ms": latency},
            "reason": f"p95 latency is {latency:.0f} ms; replica scaling may not fix a slow dependency or inefficient query.",
            "guardrails": ["Inspect traces and downstream service timings.", "Check database queries, connection pools, and queue depth."]
        })

    if restart_count >= 3:
        recommendations.append({
            "action": "investigate_restarts",
            "priority": "high",
            "current": {"restart_count": int(restart_count)},
            "recommended": {"restart_count": int(restart_count)},
            "reason": f"There are {restart_count:.0f} restarts in the observation window.",
            "guardrails": ["Inspect previous container logs and exit codes.", "Check OOMKilled status and liveness/readiness probes."]
        })

    if not recommendations:
        recommendations.append({
            "action": "maintain_and_observe",
            "priority": "low",
            "current": {"replicas": replicas, "cpu_request_millicores": int(cpu_request), "memory_request_mib": int(memory_request)},
            "recommended": {"replicas": replicas, "cpu_request_millicores": int(cpu_request), "memory_request_mib": int(memory_request)},
            "reason": "No configured threshold currently justifies a resource change.",
            "guardrails": ["Continue monitoring peak and off-peak periods.", "Revisit thresholds after collecting a representative baseline."]
        })

    return {
        "incident_id": snapshot.get("incident_id", "resource-snapshot-unknown"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Conservative rule-based recommendations; not an autonomous controller.",
        "observed_metrics": metrics,
        "recommendations": recommendations,
        "next_steps": [
            "Verify the observation window and units.",
            "Compare against baseline, latency SLOs, error budget, and cluster capacity.",
            "Review recommendations with an operator and test in staging.",
            "Apply changes manually only after approval, then monitor impact."
        ],
        "safety_note": "This tool only writes a JSON report. It does not change Kubernetes, cloud resources, or billing settings."
    }


def demo_snapshot() -> dict[str, Any]:
    return {
        "incident_id": "resource-demo-001",
        "current": {
            "replicas": 2,
            "cpu_request_millicores": 500,
            "memory_request_mib": 512
        },
        "target": {
            "min_replicas": 2,
            "max_replicas": 6
        },
        "metrics": {
            "cpu_usage_percent": 91,
            "memory_usage_percent": 88,
            "latency_p95_ms": 1150,
            "request_rate_rps": 72,
            "error_ratio": 0.02,
            "restart_count": 0,
            "sustained_minutes": 8
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate explainable resource optimization recommendations.")
    parser.add_argument("--input", type=Path, help="JSON resource snapshot.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON report.")
    parser.add_argument("--demo", action="store_true", help="Use built-in demo snapshot.")
    args = parser.parse_args()

    if args.demo:
        snapshot = demo_snapshot()
    else:
        input_path = args.input or DEFAULT_INPUT
        if not input_path.exists():
            parser.error(f"Input file not found: {input_path}. Use --demo or create the JSON input.")
        with input_path.open("r", encoding="utf-8") as handle:
            snapshot = json.load(handle)

    report = recommend(snapshot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nSaved optimization report to: {args.output}")


if __name__ == "__main__":
    main()
