# SolarSelect monitoring runbook

Scrape `GET /metrics` (Prometheus text). Import `dashboards/solarselect_dashboard.json` into Grafana (datasource `${DS_PROMETHEUS}`).
Evaluate rules in-process: `from monitoring import alerts; alerts.evaluate(drift=..., performance=...)`.

| Alert | First steps |
|---|---|
| ModelNotLoaded | `GET /api/v1/health/ready`; read startup log `event=startup_failed`; verify SHA-256 against `app/backend/model_loaders/frozen_manifest.json`; registry mode: verify MLflow DB/artifact paths. Do not swap models without Person 1. |
| High5xxRate / InferenceFailures / NonFinitePrediction | Logs (`request_failed`, `INVALID_MODEL_OUTPUT`); run `pytest tests/phase9/person3`; check library versions vs `requirements.txt`. |
| PredictLatencyP95High | CPU saturation; ExtraTrees `n_jobs=-1` contention; batch sizes. |
| InputRejectionSpike | Compare client payloads to `GET /api/v1/model/schema`. Never loosen validation. |
| GovernanceRejections | Expected until the lag policy is decided. Never bypass the 409 guard. |
| FeatureDriftAlert | Run `python monitoring/scripts/generate_reports.py`-style comparison on the live window (`MonitoredProvider.window.frame()`); expect seasonal drift outside May–Dec. Confirm with labels before acting. No automatic retraining. |
| PerformanceDegradation | Needs actual yields. Review residuals by site/season, escalate to Person 1 for a governed retraining decision. |
