# Model limitations and unsupported uses

Sources: `final_model_metadata.json`, this QA's measurements, `GET /api/v1/limitations`.

1. **Modest skill.** Held-out R² is 0.258 (MAE ≈ 31% of mean yield). It beats persistence but is not a precise forecaster; do not present point estimates without that context.
2. **Single-campus, single-region training data.** UNISOLAR Campus 1, Melbourne, Australia (lat ≈ −37.7). Applying to other climates (e.g. India) is outside the evidence; the supplementary datasets in the handoff are not integrated.
3. **Narrow seasonal support.** Training covers 2021-05..2021-12; the held-out period is 2022-03..04. Seasonal features of the held-out set are far outside the training distribution (PSI ≈ 5–8 on day_of_year/sin/cos/declination; see `reports/phase9/monitoring/DATA_DRIFT_REPORT.md`). Summer (Jan–Feb) and the full-year cycle were not validated on unseen data; treat predictions outside May–Dec/Mar–Apr as extrapolation.
4. **Lag-dependent.** 27 of 29 features are calendar/solar geometry or lagged yield/weather. New roofs have no yield history, hence the intentional 409 `PREDICTION_PENDING_LAG_POLICY`; rows with `has_valid_lag1=0` (58/1128 held out) are scored but with no separate accuracy gate.
4b. **No uncertainty.** The model returns a point estimate only; no interval.
5. **Energy basis unverified.** `UNVERIFIED_ASSUMED_AC`: it is not confirmed whether the target is AC or DC energy.
6. **No weather forecast inputs.** Lagged temperature/humidity only; same-day weather is not an input.
7. **Not for individual rooftops without the lag policy.** The full-cohort ElasticNet is conditional (campus tracking; Sites 19/24 treated as anomalies) and not exposed for rooftop recommendations. Do not use it as a fallback.
8. **Valid-but-extreme inputs are not clamped.** They are predicted as-is (tested); a large kWp or extreme lag can yield unreliable output without any error. Monitoring (out-of-range fraction, drift) is the safeguard.
9. **Negative predictions are possible** and flagged `NEGATIVE_PREDICTION_WARNING`.
10. **Model estimate ≠ installed-system performance.** It excludes shading, soiling, inverter limits and degradation.
