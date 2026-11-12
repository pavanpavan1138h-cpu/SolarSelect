# API / inference latency baseline (reference laptop, local frozen provider, single worker)

Source: `monitoring/scripts/generate_reports.py` → `latency_results.json` (200 single predicts + 10 × batch-100).

| Metric | Value |
|---|---|
| `/predict` p50 / p95 / p99 | 27.3 / 28.1 / 29.6 ms |
| model inference p95 (per row) | 21.1 ms |
| `/predict/batch` (100 rows) p50 / p95 | 2.55 s / 3.70 s |

**Update:** `PredictionService` now makes one model call per variant; a 100-row batch measured ~0.76 s end-to-end afterwards (was ~2.5 s), parity unchanged (all QA tests pass).

**Original finding:** batch cost is ~25 ms/row, i.e. linear — `PredictionService` validates and predicts each row separately, and each ExtraTrees call pays `n_jobs=-1` thread overhead. A vectorised batch call would be far faster; it is a Person 2 optimisation, not a correctness issue, and must preserve the ≤1e-8 parity gate. The provisional `/predict` p95 alert (500 ms) is ≈18× the baseline.
