# Feature drift vs training baseline

Reference: peer-cohort training split (2021-05-01..2021-12-31, 4,383 rows). PSI on reference-quantile bins; bands 0.10 warn / 0.25 alert (convention).

| Current sample | Rows | Status | Max PSI | Features ALERT / WARN |
|---|---|---|---|---|
| Random 1,000 of training (control) | 1,000 | OK | 0.013 | 0 / 0 |
| Validation (2022-01..02, summer) | 945 | ALERT | 8.30 | 23 / 0 |
| Held-out test (2022-03..04, autumn) | 1,128 | ALERT | 8.30 | 22 / 1 |

Interpretation: the control confirms the detector is quiet on in-distribution data. Validation/test fire because the training window contains **no summer and no autumn**: calendar and solar-geometry features (day_of_year, sin/cos_doy and month, solar declination/elevation/zenith, daylight, H0) and lagged temperatures are out of range (e.g. 100 % of test day_of_year/month outside the training range). This is expected covariate shift, **not** evidence of accuracy loss — the model's held-out MAE/R² were measured directly (QA report: R² 0.258). It does show that any live data outside May–Dec will trigger `FeatureDriftAlert`; the alert is a prompt to review, never to auto-retrain. Consider rebuilding the baseline from a full-year dataset once Person 1 provides one.
