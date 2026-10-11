# AIOps Capstone — Final Report Template

## Title
An Explainable AI-Driven AIOps Framework for Predictive Failure Detection,
Root-Cause Analysis, and Intelligent Cloud Resource Optimization

## Abstract
Describe the operational problem, the prototype architecture, the metrics collected,
the failure-prediction experiment, the explainability component, alerting, and the
guarded Kubernetes recommendation workflow. State which results were actually tested.

## Problem statement
Explain why reactive monitoring alone may detect incidents after user impact and
why teams need earlier risk indicators, interpretable signals, and safe operational
recommendations.

## Objectives
1. Collect application telemetry and expose it through Prometheus.
2. Build and evaluate a baseline failure-risk model.
3. Explain model outputs with SHAP.
4. Define alert rules for selected operational symptoms.
5. Produce incident summaries and safe Kubernetes command previews.
6. Evaluate the integration and document limitations.

## Architecture
Application → Prometheus → metrics API → prediction/explanation and incident analysis
→ alert rules → remediation plan (dry-run) → dashboard/report.

## Implementation
Document Modules 1–11, dependencies, configuration, API routes, model features,
alert thresholds, and safety defaults.

## Evaluation
Include only measured results:
- Model metrics from `ml/evaluation_report.json`
- Prometheus request-rate and latency observations with timestamps
- Alert-rule loading and test results
- API smoke-test results
- Known missing metrics and failure cases

## Limitations
Explain synthetic training data, missing real host metrics unless exporters are installed,
threshold-based incident analysis, lack of causal proof, and no automatic cluster changes
in the default configuration.

## Conclusion and future work
Discuss integration improvements: real labelled incident data, time-based validation,
feature-schema alignment, authenticated APIs, audit logging, controlled canary actions,
and production SLO-based alert tuning.
