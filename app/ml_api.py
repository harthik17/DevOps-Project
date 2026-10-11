"""Machine Learning & Explainable AI API Router.

Integrates failure prediction, SHAP feature attributions,
root cause analysis (RCA), and resource rightsizing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import joblib
import numpy as np
import pandas as pd

try:
    from ml.root_cause_analysis import analyze_incident as run_rca
except ImportError:
    run_rca = None

try:
    from ml.resource_optimizer import recommend as run_optimizer
except ImportError:
    run_optimizer = None

router = APIRouter(prefix="/api/ml", tags=["ai-ml"])

MODEL_PATH = Path("ml/failure_model.joblib")
REPORT_PATH = Path("ml/evaluation_report.json")
FEATURES = ["cpu_usage", "memory_usage", "latency_ms", "error_rate", "request_rate"]


class FeatureInput(BaseModel):
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU usage percent (0-100)")
    memory_usage: float = Field(..., ge=0, le=100, description="Memory usage percent (0-100)")
    latency_ms: float = Field(..., ge=0, le=30000, description="Request latency in milliseconds")
    error_rate: float = Field(..., ge=0, le=1000, description="Error rate per second or fraction")
    request_rate: float = Field(..., ge=0, le=50000, description="Request throughput (req/s)")
    threshold: Optional[float] = Field(default=0.5, ge=0.01, le=0.99, description="Decision threshold")


class IncidentInput(BaseModel):
    metrics: dict[str, Any] = Field(default={}, description="Observed telemetry dictionary")
    log_messages: list[str] = Field(default=[], description="Recent log lines")
    deployment_events: list[str] = Field(default=[], description="Recent deployment/k8s events")
    logs: list[str] = Field(default=[], description="Alias for log_messages")
    events: list[str] = Field(default=[], description="Alias for deployment_events")


class OptimizationInput(BaseModel):
    current: Optional[dict[str, Any]] = None
    target: Optional[dict[str, Any]] = None
    metrics: Optional[dict[str, Any]] = None
    replicas: Optional[int] = None
    cpu_request_m: Optional[int] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    sustained_duration_min: Optional[int] = None
    error_ratio_percent: Optional[float] = None


def load_model():
    if not MODEL_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_PATH)
    except Exception:
        return None


@router.get("/status")
def get_ml_status():
    """Returns model status, features, and evaluation metrics if available."""
    model_loaded = MODEL_PATH.exists()
    eval_report = {}
    if REPORT_PATH.exists():
        try:
            with open(REPORT_PATH, "r", encoding="utf-8") as f:
                eval_report = json.load(f)
        except Exception:
            eval_report = {}

    return {
        "model_available": model_loaded,
        "model_path": str(MODEL_PATH),
        "features": FEATURES,
        "model_type": "RandomForestClassifier Pipeline" if model_loaded else "Not Trained",
        "evaluation": eval_report,
        "disclaimer": "Trained on synthetic demonstration telemetry. Do not treat as real-world production accuracy.",
    }


@router.post("/predict")
def predict_failure(req: FeatureInput):
    """Predict failure risk using the trained Random Forest model."""
    model = load_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="ML failure model is not available. Please run 'python ml/train_failure_model.py --demo' first.",
        )

    data = {
        "cpu_usage": req.cpu_usage,
        "memory_usage": req.memory_usage,
        "latency_ms": req.latency_ms,
        "error_rate": req.error_rate,
        "request_rate": req.request_rate,
    }
    row = pd.DataFrame([data], columns=FEATURES)

    try:
        proba = float(model.predict_proba(row)[0, 1])
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Inference error: {exc}")

    thr = req.threshold if req.threshold is not None else 0.5
    is_failure = proba >= thr

    return {
        "estimated_failure_risk": round(proba, 4),
        "failure_probability": round(proba, 4),
        "predicted_failure": bool(is_failure),
        "threshold": thr,
        "predicted_class": int(is_failure),
        "status": "elevated_risk" if is_failure else "nominal",
        "interpretation": (
            "Elevated risk of service failure detected within 5 minutes. Immediate investigation recommended."
            if is_failure
            else "Nominal operating parameters; failure risk is below configured decision threshold."
        ),
        "features_evaluated": data,
        "disclaimer": "Model provides probabilistic heuristic risk estimation, not deterministic certainty.",
    }


@router.post("/explain")
def explain_prediction(req: FeatureInput):
    """Generate SHAP TreeExplainer feature importance attributions for the prediction."""
    model = load_model()
    if model is None:
        raise HTTPException(
            status_code=503,
            detail="ML failure model is not available. Train the model first.",
        )

    try:
        import shap
    except ImportError:
        raise HTTPException(status_code=501, detail="SHAP library is not installed.")

    data = {
        "cpu_usage": req.cpu_usage,
        "memory_usage": req.memory_usage,
        "latency_ms": req.latency_ms,
        "error_rate": req.error_rate,
        "request_rate": req.request_rate,
    }
    row = pd.DataFrame([data], columns=FEATURES)
    classifier = model.named_steps.get("classifier") if hasattr(model, "named_steps") else model
    imputer = model.named_steps.get("imputer") if hasattr(model, "named_steps") else None

    try:
        transformed = imputer.transform(row) if imputer is not None else row.to_numpy()
        explainer = shap.TreeExplainer(classifier)
        shap_values = explainer.shap_values(transformed)

        if isinstance(shap_values, list):
            values = np.asarray(shap_values[1])[0]
        else:
            values_array = np.asarray(shap_values)
            if values_array.ndim == 3:
                values = values_array[0, :, 1] if values_array.shape[-1] > 1 else values_array[0, :, 0]
            elif values_array.ndim == 2:
                values = values_array[0]
            else:
                values = values_array.reshape(-1)

        base_val = explainer.expected_value
        if isinstance(base_val, (list, tuple, np.ndarray)):
            base_array = np.asarray(base_val).reshape(-1)
            base_value = float(base_array[1] if len(base_array) > 1 else base_array[0])
        else:
            base_value = float(base_val)

        contributions = [
            {
                "feature": name,
                "value": float(row.iloc[0][name]),
                "shap_value": round(float(val), 4),
                "direction": "increases_risk" if val > 0 else "reduces_risk",
            }
            for name, val in zip(FEATURES, values)
        ]
        contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        feature_map = {item["feature"]: item["shap_value"] for item in contributions}
        risk = float(model.predict_proba(row)[0, 1])

        return {
            "estimated_failure_risk": round(risk, 4),
            "failure_probability": round(risk, 4),
            "shap_base_value": round(base_value, 4),
            "top_drivers": contributions,
            "feature_importances": feature_map,
            "shap_values": feature_map,
            "interpretation": (
                f"The highest contributing factor is '{contributions[0]['feature']}' "
                f"with a SHAP attribution value of {contributions[0]['shap_value']:+.4f}."
            ),
            "note": "SHAP explains mathematical model decision boundaries; it does not prove physical causation.",
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"SHAP explanation calculation failed: {exc}")


@router.post("/rca")
def root_cause_analysis(req: IncidentInput):
    """Run explainable, rule-based root cause analysis on an incident snapshot."""
    if run_rca is None:
        raise HTTPException(status_code=501, detail="RCA module not found.")

    incident_dict = {
        "metrics": req.metrics,
        "log_messages": req.log_messages or req.logs,
        "deployment_events": req.deployment_events or req.events,
    }

    try:
        report = run_rca(incident_dict)
        return report
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RCA evaluation error: {exc}")


@router.post("/optimize")
def optimize_resources(req: OptimizationInput):
    """Generate conservative cloud resource rightsizing recommendations."""
    if run_optimizer is None:
        raise HTTPException(status_code=501, detail="Resource optimizer module not found.")

    # Support flat form input from dashboard or nested JSON snapshot
    if req.current is not None or req.metrics is not None:
        snapshot = {
            "incident_id": "api-request-snapshot",
            "current": req.current or {},
            "target": req.target or {},
            "metrics": req.metrics or {},
        }
    else:
        snapshot = {
            "incident_id": "dashboard-request-snapshot",
            "current": {
                "replicas": req.replicas or 2,
                "cpu_request_millicores": req.cpu_request_m or 500,
                "memory_request_mib": 512,
            },
            "target": {
                "min_replicas": 1,
                "max_replicas": 10,
            },
            "metrics": {
                "cpu_usage_percent": req.cpu_usage_percent or 50,
                "memory_usage_percent": req.memory_usage_percent or 50,
                "sustained_minutes": req.sustained_duration_min or 10,
                "error_ratio": (req.error_ratio_percent or 0) / 100.0,
            },
        }

    try:
        raw_report = run_optimizer(snapshot)
        recommendations = raw_report.get("recommendations", [])
        
        # Determine aggregate recommended replicas and cpu
        rec_replicas = None
        rec_cpu = None
        action_strings = []
        overall_status = "nominal"

        for r in recommendations:
            res_type = r.get("resource")
            rec_val = r.get("recommended_value")
            if res_type == "replicas":
                rec_replicas = rec_val
                action_strings.append(f"Scale replicas: {r.get('current_value')} -> {rec_val} ({r.get('reason')})")
                if rec_val > (snapshot["current"].get("replicas", 2)):
                    overall_status = "scale_up_recommended"
                elif rec_val < (snapshot["current"].get("replicas", 2)):
                    overall_status = "scale_down_recommended"
            elif res_type == "cpu_request_millicores":
                rec_cpu = rec_val
                action_strings.append(f"Adjust CPU request: {r.get('current_value')}m -> {rec_val}m ({r.get('reason')})")

        if not action_strings:
            action_strings.append("Current resource allocation aligns with observed workload; maintain existing parameters.")

        return {
            "status": overall_status,
            "recommended_replicas": rec_replicas or snapshot["current"].get("replicas", 2),
            "recommended_cpu_request_m": rec_cpu or snapshot["current"].get("cpu_request_millicores", 500),
            "recommended_actions": action_strings,
            "raw_report": raw_report,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Optimization evaluation error: {exc}")
