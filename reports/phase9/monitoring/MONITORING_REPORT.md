# Monitoring report (supplementary)

## What was built (`monitoring/`)
| File | Purpose |
|---|---|
| `metrics.py` | Thread-safe counters/gauges/histograms with Prometheus text output, no new dependencies |
| `instrumentation.py` | `MonitoredProvider` (transparent wrapper: inference count/failure/latency, non-finite and negative predictions, prediction distribution, model identity, load gauge) and HTTP middleware + hidden `GET /metrics` |
| `drift.py` | PSI, KS, training-baseline builder, rolling feature window, feature and prediction drift reports |
| `performance.py` | Outcome-based MAE/RMSE/bias vs Person 1's reference once labels exist |
| `alerts.py` + `configs/alert_rules.json` | 9 rules with severity, basis and runbook |
| `configs/feature_baseline.json` | Quantile summary (101-pt grid + range) of the 4,383-row peer training split; no raw rows |
| `dashboards/solarselect_dashboard.json` | Grafana dashboard (4 rows: API health, model health, input quality, drift/performance) |
| `scripts/` | `build_baseline.py`, `generate_reports.py`, `RUNBOOK.md` |

## Integration (the only edits to Person 2's code)
`app/backend/main.py`: the provider factory is wrapped by `monitored_factory`, and `install_http_monitoring(app)` is called after the router is included (3 lines). `/metrics` is `include_in_schema=False`, so `docs/backend/openapi.json` is unchanged. Predictions, validation, status codes and error envelopes are untouched (tested: monitored output == direct output within 1e-8).

## Evidence
- `tests/phase9/monitoring/`: 33 tests (instrumentation, privacy, drift, performance, alert firing under controlled conditions, no-retrain static check) — all pass.
- Live check: uvicorn on :8765, `/health/ready` READY, `/metrics` exposed `solarselect_model_loaded 1.0`, request counters, and a 409 prospective request raised `solarselect_governance_rejections_total{code="PREDICTION_PENDING_LAG_POLICY"} 1`.
- Sample exposition: `reports/phase9/monitoring/metrics_sample.prom`.

## Privacy and safety
Labels are bounded (route template, status class, error code, variant). No feature values, payloads, paths or tokens are stored; the feature window holds validated rows in memory only (bounded 2,000) for aggregate drift. Nothing retrains, registers or promotes a model (a test greps for it).

## Limits and open decisions
- Alert thresholds other than the binary health rules are **provisional** (basis recorded per rule); PSI 0.10/0.25 are conventional bands. The project owner should confirm them.
- Metrics are in-process and per-worker, reset on restart; for multi-worker deployment scrape each worker or use a Prometheus multiprocess setup. The batch endpoint is slow (see API_METRICS_REPORT.md) and has no latency rule.
- Concept drift cannot be measured without actual yields; `performance.py` and the `PerformanceDegradation` rule stay inert until labels are fed in.
