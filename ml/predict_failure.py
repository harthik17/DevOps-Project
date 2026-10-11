"""Run a single prediction from the saved baseline model."""
import argparse, json
from pathlib import Path
import joblib
import pandas as pd

FEATURES = ["cpu_usage", "memory_usage", "latency_ms", "error_rate", "request_rate"]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="ml/failure_model.joblib")
    p.add_argument("--cpu", type=float, required=True)
    p.add_argument("--memory", type=float, required=True)
    p.add_argument("--latency", type=float, required=True, help="milliseconds")
    p.add_argument("--error-rate", type=float, required=True, help="fraction, e.g. 0.05 = 5%")
    p.add_argument("--request-rate", type=float, required=True, help="requests per second")
    p.add_argument("--threshold", type=float, default=0.5)
    a = p.parse_args()
    if not Path(a.model).exists():
        raise SystemExit("Model not found. Train it first with ml/train_failure_model.py.")
    x = pd.DataFrame([{"cpu_usage":a.cpu, "memory_usage":a.memory, "latency_ms":a.latency,
                       "error_rate":a.error_rate, "request_rate":a.request_rate}], columns=FEATURES)
    model = joblib.load(a.model)
    risk = float(model.predict_proba(x)[0,1])
    print(json.dumps({
        "estimated_failure_risk": round(risk,4),
        "threshold": a.threshold,
        "predicted_class": int(risk >= a.threshold),
        "interpretation": "Elevated model risk; investigate supporting evidence." if risk >= a.threshold
                          else "Below configured threshold; continue monitoring.",
        "warning": "Not a guarantee or necessarily a calibrated probability."
    }, indent=2))

if __name__ == "__main__":
    main()
