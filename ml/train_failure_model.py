"""Train a baseline failure-risk classifier. Synthetic demo data is for pipeline testing only."""
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, roc_auc_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
import joblib

FEATURES = ["cpu_usage", "memory_usage", "latency_ms", "error_rate", "request_rate"]
TARGET = "failure_within_5m"

def create_demo(path, n=3000):
    rng = np.random.default_rng(42)
    cpu = np.clip(rng.normal(48, 18, n), 1, 100)
    mem = np.clip(rng.normal(55, 17, n), 1, 100)
    rate = np.clip(rng.lognormal(2.0, .65, n), .1, 80)
    latency = np.clip(80 + cpu*3 + mem*2 + rate*2 + rng.normal(0, 100, n), 10, 3000)
    errors = np.clip((latency-350)/1000 + rng.normal(.02, .04, n), 0, 1)
    logit = -7 + .045*cpu + .035*mem + .0014*latency + 2*errors
    probability = 1/(1+np.exp(-logit))
    labels = rng.binomial(1, probability)
    df = pd.DataFrame({"cpu_usage":cpu,"memory_usage":mem,"latency_ms":latency,
                       "error_rate":errors,"request_rate":rate,TARGET:labels})
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Created {n} synthetic rows at {path}; not real operational evidence.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/training_metrics.csv")
    parser.add_argument("--model", default="ml/failure_model.joblib")
    parser.add_argument("--report", default="ml/evaluation_report.json")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args()
    input_path = Path(args.input)
    if args.demo:
        create_demo(input_path)
    if not input_path.exists():
        raise SystemExit(f"Dataset not found: {input_path}. Run with --demo to smoke-test the pipeline.")
    df = pd.read_csv(input_path)
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing columns: {missing}")
    df = df[FEATURES+[TARGET]].replace([np.inf,-np.inf], np.nan).dropna(subset=[TARGET])
    for col in FEATURES+[TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=[TARGET])
    if len(df) < 50 or set(df[TARGET].unique()) != {0,1}:
        raise SystemExit("Need at least 50 rows and both 0/1 values in failure_within_5m.")
    df[TARGET] = df[TARGET].astype(int)
    X, y = df[FEATURES], df[TARGET]
    # Quick pipeline smoke test. For real time-series evaluation, use a chronological split.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=.25, random_state=42, stratify=y)
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("classifier", RandomForestClassifier(n_estimators=250, min_samples_leaf=3,
             class_weight="balanced", random_state=42, n_jobs=-1))
    ])
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    proba = model.predict_proba(X_test)[:,1]
    report = {
        "rows": int(len(df)), "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "positive_rate": float(y.mean()), "precision": float(precision_score(y_test,pred,zero_division=0)),
        "recall": float(recall_score(y_test,pred,zero_division=0)),
        "f1": float(f1_score(y_test,pred,zero_division=0)),
        "average_precision": float(average_precision_score(y_test,proba)),
        "roc_auc": float(roc_auc_score(y_test,proba)),
        "confusion_matrix_labels_order": [0,1],
        "confusion_matrix": confusion_matrix(y_test,pred,labels=[0,1]).tolist(),
        "features": FEATURES, "synthetic_demo_data": bool(args.demo),
        "note": "Synthetic data metrics test code only; do not claim real-world predictive accuracy."
                if args.demo else "Use a chronological holdout and verified failure labels before making performance claims."
    }
    Path(args.model).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, args.model)
    Path(args.report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Saved model: {args.model}\nSaved report: {args.report}")

if __name__ == "__main__":
    main()
