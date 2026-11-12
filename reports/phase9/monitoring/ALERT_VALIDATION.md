# Alert validation

Each rule in `monitoring/configs/alert_rules.json` is exercised in `tests/phase9/monitoring/test_alerts.py` under controlled conditions, plus a quiet-system check, a no-data check (a missing signal never fires), a traffic-floor check for rate rules, and one end-to-end test (60 invalid requests through the real app → `InputRejectionSpike`).

| Rule | Severity | Trigger validated |
|---|---|---|
| ModelNotLoaded | critical | gauge = 0 |
| High5xxRate | critical | 10 % 5xx, only after ≥ 50 requests |
| InferenceFailures | critical | 1 failure in 100 |
| NonFinitePrediction | critical | one NaN output |
| PredictLatencyP95High | warning | p95 900 ms with 60 requests |
| InputRejectionSpike | warning | 40 % rejected |
| GovernanceRejections | info | one 409 lag-policy block |
| FeatureDriftAlert | warning | max PSI 0.4 |
| PerformanceDegradation | critical | MAE ratio 1.6 (and not at 1.0) |

Runbooks are in each rule and expanded in `monitoring/RUNBOOK.md`. These tests prove the rules evaluate correctly; they do not prove an external pager/Grafana is connected — none is deployed in this repo.
