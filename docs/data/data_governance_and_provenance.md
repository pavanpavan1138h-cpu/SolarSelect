# Data Governance and Provenance — SolarSelect

This document outlines the strict data governance, data lineage, leakage-prevention protocols, licensing terms, and test-partition quarantine procedures enforced across SolarSelect.

---

## 1. Raw Data Immutability Policy

All raw telemetry files stored in `data/raw/` are treated as **strictly read-only and immutable**:
- No script or notebook is permitted to modify, overwrite, truncate, or re-encode raw files in place.
- All data cleaning, filtering, interval summation, and feature engineering are executed into separate `data/interim/` and `data/processed/` directories.
- Lineage is tracked via Git and Data Version Control (DVC) (`.dvc/` configuration).

---

## 2. Licensing and Dataset Provenance

1. **Kaggle Solar Power Generation Data:**
   - **Source:** Kaggle Open Datasets ([Anikannal, 2020](https://www.kaggle.com/datasets/anikannal/solar-power-generation-data)).
   - **License:** Open Database License (ODbL) / CC BY-SA 4.0.
   - **Provenance:** Inverter-level telemetry and weather sensors from two grid-connected solar PV plants in India over a 34-day span (May 15 – June 17, 2020).
2. **UNISOLAR Multi-Campus Solar Energy Generation Dataset:**
   - **Source:** University solar microgrid telemetry dataset (Melbourne, Victoria, Australia).
   - **License:** Research / Academic Open Access.
   - **Provenance:** Rooftop PV systems monitored across five university campuses from December 2019 to April 2022. Ground truth coordinates: Latitude $-37.718^\circ$, Longitude $145.051^\circ$. Weather data sourced from regional Bureau of Meteorology (BOM) automated stations.
3. **Commercial Solar Panel Datasheets (Phase 6):**
   - **Policy:** Explicitly restricted against automated web scraping or unapproved downloads.
   - **Status:** Canonical schema defined; population from official manufacturer technical datasheets is formally **pending stakeholder approval**.

---

## 3. Strict Data Leakage Prevention Framework

To prevent artificial inflation of predictive accuracy, SolarSelect enforces an 8-rule anti-leakage register:

| Rule | Leakage Risk Addressed | Implementation Protocol in Pipeline |
|---|---|---|
| **L1: Calendar-Aware Day-Ahead Horizon** | Contemporaneous weather leakage | All weather and generation features utilize lag $\tau \ge 24\text{h}$ ($t-1$, $t-2$, $t-7$, rolling 7d). Same-day weather is strictly excluded. |
| **L2: Strict Chronological Splitting** | Temporal data snooping | Chronological splitting strictly by date. Train (`2021-05-01` to `2021-12-31`), Validation (`2022-01-01` to `2022-02-28`), Test (`2022-03-01` to `2022-04-23`). Random splitting is banned. |
| **L3: Date-Grouped Cross-Validation** | Cross-site same-day leakage | 4-fold expanding window cross-validation is grouped strictly by `Date`. All sites on a given date are evaluated together in validation folds; never split across train/val. |
| **L4: Training-Only Imputation** | Information leakage from future test data | Imputation medians and scaling parameters are fitted **exclusively on the training partition** and applied statically to validation and test sets. |
| **L5: Daily Grid Continuity (No Forward-Fill)** | Missing date distortion | Missing calendar dates (e.g. absent telemetry days) are explicitly identified on a continuous calendar grid. Lags reference actual calendar days ($t-1$ day), not row shifts. |
| **L6: Separation of Diagnostic Metadata** | Target leakage via operational flags | Diagnostic metadata (e.g. interval counts, raw energy sums, capacity factors) are isolated in `diagnostic_metadata.csv` and never included in the model matrix. |
| **L7: Cumulative Counter Exclusion** | Target leakage via cumulative yield | Monotonically increasing lifetime yield counters (`TOTAL_YIELD`, `DAILY_YIELD`) are completely excluded from predictive features. |
| **L8: Test-Set Quarantine Protocol** | Premature test-set exposure & overfitting | The test set (`2022-03-01` to `2022-04-23`) remained completely quarantined throughout Phases 1–4 and Phase 5 Prompts 1–2. It was loaded and evaluated **exactly once** in Phase 5 Prompt 3 on frozen models. |

---

## 4. Test-Partition Quarantine Audit Trail

The quarantine protocol followed a verified 3-stage lifecycle:
1. **Quarantine Enforcement (Phases 1–5 Prompt 2):** Test partition files (`data/processed/unisolar/test.csv` and `data/processed/unisolar/peer_cohort/test.csv`) were generated in Phase 3 and immediately sealed. During all exploratory diagnostics (Phase 5 Prompt 1) and ensemble blending experiments (Phase 5 Prompt 2), the test partition was never read, loaded, or inspected.
2. **Model Freezing Prior to Exposure (Phase 5 Prompt 3, Part 1):** Candidate architectures (Tuned ExtraTrees, Tuned ElasticNet, and Ensemble Blends) were frozen and retrained on combined pre-test data (Train + Validation).
3. **Single Held-Out Evaluation (Phase 5 Prompt 3, Part 2):** The test set was accessed once to evaluate generalization. Zero post-hoc hyperparameter adjustments were performed based on test outputs.

