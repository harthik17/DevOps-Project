"""Transform collected Prometheus time-series metrics into ML training dataset.

Maps Prometheus telemetry into the feature schema expected by ml/train_failure_model.py:
- cpu_usage: derived from simulated_load_level (or host cpu if present)
- memory_usage: derived from simulated_memory_pressure_percent (or host mem)
- latency_ms: latency_p95_seconds * 1000
- error_rate: demo_error_rate_per_second
- request_rate: request_rate_rps
- failure_within_5m: 1 if target_up==0 or error_rate>0.05 or latency_ms>500 in next 5 mins; else 0
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["cpu_usage", "memory_usage", "latency_ms", "error_rate", "request_rate"]
TARGET_COLUMN = "failure_within_5m"
ALL_COLUMNS = FEATURE_COLUMNS + [TARGET_COLUMN]


def transform_metrics(
    input_csv: Path,
    output_csv: Path,
    lookahead_seconds: int = 300,
) -> pd.DataFrame:
    if not input_csv.exists():
        raise FileNotFoundError(f"Input file not found: {input_csv}")

    df = pd.read_csv(input_csv)
    print(f"Loaded {len(df)} rows from {input_csv}")

    # Parse timestamps for chronological sorting and forward lookahead
    if "timestamp_utc" in df.columns:
        df["dt"] = pd.to_datetime(df["timestamp_utc"], utc=True)
        df = df.sort_values("dt").reset_index(drop=True)
    else:
        df["dt"] = pd.date_range(start="2026-01-01", periods=len(df), freq="5s")

    # Map features and units
    transformed = pd.DataFrame()
    transformed["dt"] = df["dt"]
    transformed["cpu_usage"] = pd.to_numeric(df.get("simulated_load_level", 50), errors="coerce").fillna(50)
    transformed["memory_usage"] = pd.to_numeric(df.get("simulated_memory_pressure_percent", 50), errors="coerce").fillna(50)

    raw_latency = pd.to_numeric(df.get("latency_p95_seconds", 0), errors="coerce").fillna(0)
    transformed["latency_ms"] = raw_latency * 1000.0

    transformed["error_rate"] = pd.to_numeric(df.get("demo_error_rate_per_second", 0), errors="coerce").fillna(0)
    transformed["request_rate"] = pd.to_numeric(df.get("request_rate_rps", 0), errors="coerce").fillna(0)

    # Documented Labeling Rule:
    # A failure condition is active if target is down (target_up == 0),
    # error rate exceeds 5% / 0.05 errors/sec, or p95 latency exceeds 500 ms.
    target_up = pd.to_numeric(df.get("prometheus_target_up", 1), errors="coerce").fillna(1)
    is_failing = (target_up == 0) | (transformed["error_rate"] > 0.05) | (transformed["latency_ms"] > 500)

    # Calculate failure_within_5m by looking ahead within lookahead_seconds
    failure_labels = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        current_time = df.loc[i, "dt"]
        window_mask = (df["dt"] > current_time) & (df["dt"] <= current_time + pd.Timedelta(seconds=lookahead_seconds))
        if is_failing[window_mask].any():
            failure_labels[i] = 1

    transformed[TARGET_COLUMN] = failure_labels

    # Clean and order features
    final_df = transformed[ALL_COLUMNS].copy()
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_csv(output_csv, index=False)
    print(f"Wrote {len(final_df)} aligned rows to {output_csv}")
    print(f"Features: {FEATURE_COLUMNS}")
    print(f"Positive failure rate: {final_df[TARGET_COLUMN].mean():.2%}")
    return final_df


def main():
    parser = argparse.ArgumentParser(description="Transform Prometheus metrics into ML training dataset")
    parser.add_argument("--input", default="data/metrics.csv", type=Path)
    parser.add_argument("--output", default="data/training_metrics_collected.csv", type=Path)
    parser.add_argument("--lookahead", default=300, type=int, help="Lookahead window in seconds (default: 300s = 5m)")
    args = parser.parse_args()

    transform_metrics(args.input, args.output, args.lookahead)


if __name__ == "__main__":
    main()
