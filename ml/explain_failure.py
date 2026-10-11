"""Explain a trained Module 3 Random Forest failure model using SHAP.

Run from the project root:
    python ml/explain_failure.py --demo

For a real prediction:
    python ml/explain_failure.py --cpu 90 --memory 88 --latency 1000 --error-rate 0.15 --request-rate 25

Requires a trained ml/failure_model.joblib created by Module 3.
"""
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt

FEATURES = ["cpu_usage", "memory_usage", "latency_ms", "error_rate", "request_rate"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="ml/failure_model.joblib")
    parser.add_argument("--cpu", type=float, default=90)
    parser.add_argument("--memory", type=float, default=88)
    parser.add_argument("--latency", type=float, default=1000)
    parser.add_argument("--error-rate", type=float, default=0.15,
                        help="Fraction from 0 to 1, e.g. 0.05 = 5 percent")
    parser.add_argument("--request-rate", type=float, default=25)
    parser.add_argument("--demo", action="store_true",
                        help="Use sample values and label the report as illustrative")
    parser.add_argument("--output", default="ml/shap_explanation.json")
    parser.add_argument("--plot", default="ml/shap_waterfall.png")
    args = parser.parse_args()

    model_path = Path(args.model)
    if not model_path.exists():
        raise SystemExit(
            f"Trained model not found: {model_path}. Complete Module 3 first."
        )

    row = pd.DataFrame([{
        "cpu_usage": args.cpu,
        "memory_usage": args.memory,
        "latency_ms": args.latency,
        "error_rate": args.error_rate,
        "request_rate": args.request_rate,
    }], columns=FEATURES)

    model = joblib.load(model_path)
    classifier = model.named_steps.get("classifier") if hasattr(model, "named_steps") else model
    if not hasattr(classifier, "feature_importances_"):
        raise SystemExit("This script expects the Random Forest model produced by Module 3.")

    # Use the fitted imputer from the training pipeline before explaining the classifier.
    imputer = model.named_steps.get("imputer") if hasattr(model, "named_steps") else None
    transformed = imputer.transform(row) if imputer is not None else row.to_numpy()
    background = transformed  # Single-row explanation; global background can be added later.
    explainer = shap.TreeExplainer(classifier)
    shap_values = explainer.shap_values(transformed)

    # SHAP return shape differs by version and binary-class output format.
    if isinstance(shap_values, list):
        values = np.asarray(shap_values[1])[0]
    else:
        values_array = np.asarray(shap_values)
        if values_array.ndim == 3:
            # Common formats: samples x features x classes OR classes x samples x features
            if values_array.shape[0] == 1:
                values = values_array[0, :, 1] if values_array.shape[-1] > 1 else values_array[0, :, 0]
            else:
                values = values_array[1, 0, :] if values_array.shape[0] == 2 else values_array[0, :, 0]
        elif values_array.ndim == 2:
            values = values_array[0]
        else:
            raise SystemExit(f"Unexpected SHAP output shape: {values_array.shape}")

    risk = float(model.predict_proba(row)[0, 1])
    base_values = explainer.expected_value
    if isinstance(base_values, (list, tuple, np.ndarray)):
        base_array = np.asarray(base_values).reshape(-1)
        base_value = float(base_array[1] if len(base_array) > 1 else base_array[0])
    else:
        base_value = float(base_values)

    contributions = [
        {"feature": name, "value": float(row.iloc[0][name]),
         "shap_value": float(value)}
        for name, value in zip(FEATURES, values)
    ]
    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    result = {
        "estimated_failure_risk": round(risk, 6),
        "input_features": {k: float(v) for k, v in row.iloc[0].items()},
        "shap_base_value": base_value,
        "feature_contributions": contributions,
        "note": (
            "Illustrative explanation for a demo input. SHAP explains this model's output; it does not prove causation."
            if args.demo else
            "SHAP explains this model's output; it does not prove causation. Use representative background data for robust explanations."
        )
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    # A clear horizontal bar plot of signed contributions.
    names = [item["feature"] for item in contributions][::-1]
    vals = [item["shap_value"] for item in contributions][::-1]
    plt.figure(figsize=(9, 5))
    plt.barh(names, vals)
    plt.axvline(0, linewidth=1)
    plt.xlabel("SHAP contribution (model output scale)")
    plt.title("Feature contributions to failure-risk prediction")
    plt.tight_layout()
    plot_path = Path(args.plot)
    plot_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(plot_path, dpi=160)
    plt.close()

    print(json.dumps({
        "estimated_failure_risk": result["estimated_failure_risk"],
        "top_contributors": contributions[:3],
        "json_report": str(output_path),
        "plot": str(plot_path),
        "note": result["note"]
    }, indent=2))


if __name__ == "__main__":
    main()
