# Phase 8 Stage 2: Phase 5 Inference Interface & UNISOLAR Historical Replay Report

**SolarSelect MLOps Engineering Laboratory**  
**Lifecycle Stage:** Phase 8 — Stage 2: Historical Replay Implementation  
**Status:** Completed & Audited (Session 58 Reconciliation)  
**Date:** 2026-11-11  
**Author:** SolarSelect Engineering Team  

---

## 1. Executive Summary

Phase 8 Stage 2 establishes a controlled, read-only inference interface (`Phase5PeerCohortPredictor`) to the frozen Phase 5 Peer Cohort model artifacts and implements the restricted historical energy-replay pipeline (`UNISOLARHistoricalReplayEngine`). 

Stage 2 operates strictly within the boundaries defined by the authoritative mathematical specification (`reports/phase8/phase8_mathematical_specification_and_io_contract.md`). It deliberately addresses **only** historical replay for known UNISOLAR peer cohort sites where observed feature records exist.

**Critical Scope Boundaries & Governance Rules:**
- **Blocking Issue B-2 remains unresolved:** No prospective-roof energy prediction is implemented. Unbuilt prospective roofs have no operational lag-yield history; Stage 2 does **not** synthesize, interpolate, or substitute lag features for prospective configurations. Prospective roofs evaluated via Stage 1 integration continue to return `annual_energy_prediction_kwh = None`, `prediction_status = "PREDICTION_PENDING_LAG_POLICY"`, and `overall_recommendation_status = "RECOMMENDATION_NOT_EVALUATED"`.
- **Blocking Issue B-1 remains unresolved:** The energy basis across all outputs is explicitly marked `energy_basis = "UNVERIFIED"`, indicating that the unit semantics (AC active inverter yield vs DC array yield) have not been confirmed against physical site instrumentation.
- **Unresolved Decision D-4 applied:** Negative daily yield predictions ($\hat{Y} < 0$) are not silently clipped or zeroed. The raw specific yield is preserved in `predicted_specific_yield_kwh_per_kwp_day`, the raw unclipped mathematical energy is preserved in `raw_unclipped_daily_energy_kwh`, the observation is flagged with `prediction_status = "NEGATIVE_PREDICTION_WARNING"`, and negative values are excluded from positive total energy summations by setting `estimated_daily_energy_kwh = None` (admitting 0 kWh to positive totals).
- **Partial Period Preservation:** The UNISOLAR Peer Cohort dataset spans May 1, 2021 to April 23, 2022 (358 calendar days; < 12 complete calendar months). Outputs are reported strictly as observed-period totals under `historical_year_status = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"`. Annual extrapolation or multiplication by 365 is strictly forbidden.

---

## 2. Phase 5 Model Artifact Reconciliation & Provenance Audit

A rigorous inspection of the serialized Phase 5 model artifacts, Phase 5 notebooks, and evaluation metadata was conducted during Session 58:

### 2.1 Artifact Structure & Estimator Class Verification

| Artifact Role | File Path | Actual Python Class | Architecture Structure | SHA-256 Checksum |
| :--- | :--- | :--- | :--- | :--- |
| **Primary Model** | `models/phase5/final/peer_cohort/final_extra_trees.joblib` | `sklearn.ensemble._forest.ExtraTreesRegressor` | **Bare Estimator** (No Pipeline, no embedded transformers) | `39b4a11beb5423dff926e43b4594b7938957183daaa16f16bdea7e5dc54ecfe9` |
| **Component Linear Model** | `models/phase5/final/peer_cohort/final_elastic_net.joblib` | `sklearn.linear_model._coordinate_descent.ElasticNet` | **Bare Estimator** (No Pipeline, no embedded transformers) | `422bda69e708e2129c0e1407bb6cd536971003b7f64dcc635ddc82da3acae7bb` |
| **Evaluation Metadata** | `models/phase5/final_model_metadata.json` | JSON | Authoritative test metrics & hyperparameter configurations | Timestamp: `2026-11-10T08:45:00Z` |

### 2.2 Preprocessing and Imputation Architecture
- **No Embedded Preprocessing:** Neither joblib artifact is an `sklearn.pipeline.Pipeline` (`hasattr(estimator, 'steps') is False`). No scaler, one-hot encoder, or transformer is embedded in either model.
- **Absence of Embedded Imputation:** Imputation medians and missing-lag handling logic are **not embedded** in the serialized joblib files.
- **Upstream Data Preparation:** In accordance with Phase 3/5 documentation, feature engineering, lag creation, and static training-median imputation were executed upstream during dataset preparation (`src/prepare_phase3_data.py`), which emitted pre-imputed feature CSVs (`data/processed/unisolar/peer_cohort/features.csv`, `train.csv`, `validation.csv`, `test.csv`) and logged the static medians in `preprocessing_metadata.json`. The estimators were trained on pre-imputed numeric matrices.

### 2.3 Cryptographic Hash Context & Artifact Continuity Assessment
To maintain scientific integrity, the project distinguishes three tiers of verification regarding model artifact continuity:
1. **Cryptographic Identity Verification:** Cannot be claimed historically. Because `.gitignore` explicitly excluded `*.joblib` files and baseline SHA-256 checksums were not recorded in Phase 5 documents (only file paths, sample counts, and test metrics were logged in `models/phase5/final_model_metadata.json`), it is impossible to verify bit-for-bit cryptographic identity against a historical baseline hash. The SHA-256 hashes recorded in Session 57/58 serve as the initial cryptographic baseline for Phase 8 onward.
2. **Structural Equivalence:** Conclusively demonstrated. Both artifacts are bare scikit-learn estimators without pipelines or embedded imputation, matching the estimator architectures and hyperparameter configurations specified in Phase 5 code (`ExtraTreesRegressor` with 100 trees, max_depth=12, max_features=0.8; `ElasticNet` with alpha=0.05, l1_ratio=0.90).
3. **Mathematical & Behavioral Consistency:** Conclusively demonstrated across both individual estimators and ensemble blending:
   - **Primary ExtraTrees:** Executing `final_extra_trees.joblib` on the 1,128 held-out test rows (`data/processed/unisolar/peer_cohort/test.csv`) reproduces the exact Phase 5 held-out test metrics recorded in `models/phase5/final_model_metadata.json` down to the decimal:
     - MAE: **0.904968** (documented as $0.9050$)
     - RMSE: **1.070045** (documented as $1.0700$)
     - $R^2$: **+0.257957** (documented as $+0.2580$)
     - Bias (Actual $-$ Predicted): **-0.103567** (documented as $-0.1036$)
   - **Component ElasticNet:** Inspecting `final_elastic_net.joblib` confirms that its coefficients (`coef_`) and intercept (`intercept_ = 4.198852745743913`) match a deterministic refit on the Phase 5 combined pre-test partition ($N=5,328$ site-days) with a maximum absolute difference of exactly **0.0**.
   - **Read-Only Invariance Guarantees:** Calling `.fit()`, `.partial_fit()`, or `.refit()` on `Phase5PeerCohortPredictor` raises `Phase5InferenceError`.

### 2.4 Final Phase 5 Blend Metric Reconciliation (Session 59 Audit)

During Session 58 and 59, the discrepancy between the two reported sets of Peer Cohort 50/50 blend metrics was thoroughly traced and reconciled:

| Metric | Result Set A (Earlier Phase 5 Record) | Result Set B (Executed Notebook Cell 8 & Session 58) | Recomputed on Frozen Disk Artifacts |
| :--- | :--- | :--- | :--- |
| **MAE** | `0.8898` (`0.889763`) | `0.8767` | **0.876715** |
| **RMSE** | `1.0615` (`1.061457`) | `1.0444` | **1.044441** |
| **$R^2$** | `+0.2698` (`0.269821`) | `+0.2930` | **+0.293044** |
| **Bias** | `-0.1204` (`-0.120369`) | `-0.0885` | **-0.088454** |
| **Predicted Mean** | `3.0539` (`3.053883`) | `3.0220` | **3.021968** |

#### Forensic Trace & Root Cause Analysis:
1. **Origin of Result Set A:**
   - Appears in `reports/phase5/test_evaluation_results.csv` (Row 4), `models/phase5/final_model_metadata.json`, and markdown summary cells of the Phase 5 notebook.
   - Traced to an earlier evaluation run where Row 4 was computed as the blend of Row 2 (`Tuned ExtraTrees`: MAE = 0.9050, Bias = -0.1036) and Row 5 (`Tuned ElasticNet Component`: MAE = 0.8883, Bias = -0.1372).
   - In that intermediate run, the ElasticNet component evaluated had a slightly higher bias (-0.1372), resulting in a blend bias of $0.5 \times (-0.1036) + 0.5 \times (-0.1372) = -0.1204$ and blend MAE of $0.8898$.
2. **Origin of Result Set B:**
   - Preserved in the actual executed HTML output table of Cell 8 in `notebooks/phase5/final_model_evaluation_and_generalization.ipynb`.
   - Corresponds to the final end-to-end execution where `final_et_peer` and `final_enet_peer` were fitted on `df_pretest_peer` ($N=5,328$), serialized to disk, and evaluated on `df_test_peer` ($N=1,128$).
3. **Recomputation from Exact Frozen Disk Artifacts:**
   - Loading `models/phase5/final/peer_cohort/final_extra_trees.joblib` and `models/phase5/final/peer_cohort/final_elastic_net.joblib` directly and evaluating them on the exact 1,128 test rows produces **MAE = 0.876715, RMSE = 1.044441, $R^2$ = +0.293044, Bias = -0.088454**.
   - This matches **Result Set B (executed Cell 8 output)** down to floating-point rounding.
4. **Conclusion:** Result Set B represents the true, verified performance of the frozen model artifacts currently present on disk. Both result sets confirm the same empirical conclusion: the 50/50 ensemble blend successfully reduces tracking error and variance over the single tree model.

---

## 3. Inference Interface Architecture (`Phase5PeerCohortPredictor`)

The `Phase5PeerCohortPredictor` class (`src/energy_economics/inference.py`) manages feature validation and prediction execution against the frozen models.

### 3.1 Strict 29-Feature Schema Enforcement
The frozen ExtraTrees estimator was trained with exactly 29 input features (`feature_names_in_`). The inference interface guarantees:
1. **Canonical Ordering:** Input DataFrames are reordered to match the exact 29-feature sequence prior to passing to the estimator:
   ```
   1. kWp                      11. dni_mean             21. ghi_mean
   2. air_temperature_max      12. dew_point_mean       22. ghi_std
   3. lag1_dni_mean            13. lag1_dhi_mean        23. lag1_ghi_mean
   4. lag1_surface_solar_radiation 14. surface_solar_radiation 24. lag1_air_temperature_max
   5. relative_humidity_mean   15. dhi_mean             25. dhi_max
   6. lag1_dew_point_mean      16. dni_max              26. wind_speed_mean
   7. surface_pressure_mean    17. lag1_relative_humidity_mean 27. lag1_dhi_max
   8. lag1_surface_pressure_mean 18. air_temperature_min  28. lag1_dni_max
   9. lag1_wind_speed_mean     19. ghi_max              29. lag1_rh_mean
   10. lag1_ghi_max            20. lag1_air_temperature_min
   ```
2. **Missing Feature Rejection:** If any of the required 29 features is missing, execution halts immediately with `FeatureValidationError`.
3. **Non-Finite Feature Rejection:** Input features containing `NaN`, `+inf`, or `-inf` are rejected with `FeatureValidationError`.
4. **Target & Metadata Exclusion:** Columns such as `SiteKey`, `Date`, `split`, and `target_daily_yield` are excluded from the feature matrix before inference. `target_daily_yield` is stored separately as ground truth for comparison.

### 3.2 Model Selection Modes & Blend Terminology Reconciliation
To eliminate ambiguity identified in Session 57 review:
- **Primary Model (`primary_extra_trees`, Default):** Evaluates the single production `final_extra_trees.joblib` estimator.
- **Authorized Fallback Strategy (`fallback_blend_50_50`):** An ensemble blend strategy requiring explicit authorization:
  $$\hat{Y}_{blend} = 0.5 \times \hat{Y}_{ExtraTrees} + 0.5 \times \hat{Y}_{ElasticNet}$$
  - The saved artifact `final_elastic_net.joblib` is strictly the **component linear model**, not a standalone blend model.
  - The fallback prediction is computed at runtime by combining predictions from both frozen artifacts (`final_extra_trees.joblib` and `final_elastic_net.joblib`) using the exact authorized 50/50 weighting.

---

## 4. Historical Replay Engine Architecture (`UNISOLARHistoricalReplayEngine`)

The historical replay engine (`src/energy_economics/historical_replay.py`) replays actual UNISOLAR peer cohort feature records through the inference pipeline.

### 4.1 Ingestion & Date Validation
- **Dataset Source:** `data/processed/unisolar/peer_cohort/features.csv` (6,456 site-day rows across 22 sites).
- **Date Continuity & Ordering:** Ingested records are sorted chronologically by `Date`. Duplicate `(SiteKey, Date)` pairs are rejected with `HistoricalReplayError`.
- **Historical Installed Capacity Preservation:** The original `kWp` column from the feature dataset is preserved exactly. The engine does **not** recompute or modify historical capacity.

### 4.2 Sample Classification (In-Sample vs Out-of-Sample)
In accordance with Phase 5 evaluation records:
- **Out-of-Sample (`OUT_OF_SAMPLE`):** Observations from `2022-03-01` through `2022-04-23`, inclusive (exactly 1,128 records, matching Phase 5 `split == 'test'`).
- **In-Sample (`IN_SAMPLE`):** Observations prior to `2022-03-01` (from `2021-05-01` to `2022-02-28`; exactly 5,328 records, matching Phase 5 combined pre-test partition `split in ['train', 'validation']`).

### 4.3 Daily Energy Arithmetic & Negative Prediction Output Semantics
1. **Specific Yield Prediction ($\hat{Y}$):** Predicted specific yield in kWh/kWp/day, rounded to 6 decimal places. The raw unclipped value is preserved in `predicted_specific_yield_kwh_per_kwp_day`.
2. **Raw Mathematical Energy:** Computed as:
   $$E_{raw} = \text{round}(\hat{Y}_{rounded} \times kWp_{historical}, 6) \quad (\text{kWh/day})$$
   This unclipped mathematical product is preserved in `raw_unclipped_daily_energy_kwh` to maintain full arithmetic transparency.
3. **Negative Yield Handling (Decision D-4 Unresolved):**
   - If $\hat{Y} < 0.0$:
     - `prediction_status` is explicitly set to `"NEGATIVE_PREDICTION_WARNING"`.
     - `estimated_daily_energy_kwh` is set to `None`, indicating that negative yield is not admitted as valid physical generation.
     - Negative predictions contribute 0 kWh to positive energy aggregate totals (`observed_period_estimated_energy_kwh`).
   - If $\hat{Y} \ge 0.0$:
     - `prediction_status` is set to `"VALID"`.
     - `estimated_daily_energy_kwh` is set to $E_{raw}$.
   - No synthetic clipping or zeroing is applied to $\hat{Y}$ or $E_{raw}$.

### 4.4 Coverage & Partial-Period Contract
Across the full UNISOLAR dataset:
- Earliest Date: `2021-05-01`
- Latest Date: `2022-04-23`
- Total Calendar Span: 358 days
- Active Observation Days: 345 days
- Missing Calendar Days: 13 days
- Valid Day Coverage Ratio: $345 / 358 = 0.963687$

Because the calendar span is 358 days (< 12 full calendar months):
- `historical_year_status` is strictly assigned `"PARTIAL_PERIOD_NOT_A_FULL_YEAR"`.
- Annual extrapolation, scaling factors, or multiplying by 365 are strictly prevented.
- Energy outputs represent **observed-period totals only**.

### 4.5 Energy Basis Disclosure
In accordance with Blocking Issue B-1:
- `energy_basis = "UNVERIFIED"`
- `energy_basis_caveat = "Energy basis (AC inverter output vs DC array yield) is unverified in UNISOLAR ground truth per Blocking Issue B-1."`

---

## 5. Verification & Test Suite Execution

A dedicated test suite (`tests/test_phase8_stage2_inference_and_replay.py`) containing 21 comprehensive test cases was updated and executed.

### 5.1 Test Cases Executed

1. `test_loading_peer_cohort_extratrees_artifact`: Verifies loading of `final_extra_trees.joblib` and metadata.
2. `test_recording_model_sha256`: Validates exact SHA-256 checksum matching for both model artifacts.
3. `test_exact_29_feature_validation`: Validates pipeline accepts all 29 expected features.
4. `test_feature_ordering_enforced`: Verifies feature columns are canonically sorted regardless of input column order.
5. `test_missing_feature_rejection`: Confirms `FeatureValidationError` when any required feature is absent.
6. `test_non_finite_feature_rejection`: Confirms `FeatureValidationError` when NaN or Inf values are passed.
7. `test_target_column_exclusion`: Ensures `target_daily_yield` is not passed into scikit-learn estimator.
8. `test_no_model_fitting_or_retraining`: Asserts `.fit()` cannot be invoked on inference engine.
9. `test_correct_primary_model_prediction`: Asserts valid numeric specific yield output on test site rows.
10. `test_explicit_authorized_blend_selection`: Asserts 50/50 blend requires explicit variant selection.
11. `test_historical_site_capacity_preservation`: Asserts historical `kWp` is preserved and not altered.
12. `test_correct_in_sample_classification`: Confirms pre-2022-03-01 dates are classified `IN_SAMPLE`.
13. `test_correct_out_of_sample_classification`: Confirms dates from 2022-03-01 through 2022-04-23 inclusive are classified `OUT_OF_SAMPLE`.
14. `test_duplicate_site_date_rows_rejection`: Asserts `HistoricalReplayError` on duplicate `(SiteKey, Date)` rows.
15. `test_missing_feature_rows_handling`: Asserts graceful rejection when feature rows contain NaNs.
16. `test_negative_prediction_handling_without_clipping`: Asserts unclipped raw value in `predicted_specific_yield_kwh_per_kwp_day` and `raw_unclipped_daily_energy_kwh`, `NEGATIVE_PREDICTION_WARNING` flag, `estimated_daily_energy_kwh = None`, and exclusion from positive energy totals.
17. `test_daily_energy_arithmetic`: Validates $E_{daily} = \hat{Y} \times kWp$ precision.
18. `test_energy_basis_remains_unverified`: Confirms `energy_basis = "UNVERIFIED"` in replay output.
19. `test_partial_period_handling_without_annual_extrapolation`: Asserts `historical_year_status = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"`.
20. `test_b2_remains_unresolved_for_prospective_configurations`: Verifies prospective roofs return `PREDICTION_PENDING_LAG_POLICY`.
21. `test_stage1_foundation_behavior_unchanged`: Asserts Phase 8 Stage 1 integration layer behavior is preserved.

### 5.2 Test Execution Results

```
============================== test session starts ==============================
platform darwin -- Python 3.13.9, pytest-8.4.2, pluggy-1.5.0
rootdir: /Users/apple/Documents/5th sem el/MLOps_EL/SolarSelect
collected 21 items

tests/test_phase8_stage2_inference_and_replay.py .....................    [100%]

============================== 21 passed in 2.98s ==============================
```

Full repository test execution (`pytest -q tests/`):
```
166 passed in 3.12s
```
- **126 Phase 7 tests:** 100% passing (zero regressions).
- **19 Phase 8 Stage 1 tests:** 100% passing (zero regressions).
- **21 Phase 8 Stage 2 tests:** 100% passing.
- **Total:** 166 passing tests.

---

## 6. Preservation Confirmation & Frozen Phase Status

- **Phases 1–5:** Datasets, notebooks, preprocessing pipelines, model checkpoints, and evaluation metadata remain frozen and completely unmodified.
- **Phase 6:** Canonical panel catalogue (`configs/panels_catalogue.csv`), provenance records, schemas, and catalogue documentation remain unmodified and read-only.
- **Phase 7:** Public integration API, boundary models, validation suites, and closure records remain frozen.
- **Phase 8 Stage 1:** Foundations, capacity-support assessments, catalogue integration, and output serializers remain completely intact and backwards-compatible.

---

## 7. Audit Verdict & Remaining Unresolved Issues

### Final Status Determination: **`STAGE_2_ACCEPTED_WITH_DOCUMENTED_LIMITATIONS`**

All review observations and metric discrepancies from Sessions 57, 58, and 59 have been thoroughly investigated, reconciled, and documented with definitive mathematical evidence:
1. **Artifact Continuity:** Established through structural equivalence and mathematical/behavioral consistency (reproducing test metrics and refit parameters). Cryptographic identity cannot be claimed historically due to the absence of baseline hashes in Phase 5 documents; Session 57 hashes establish the cryptographic baseline for Phase 8.
2. **50/50 Blend Reconciliation:** Reconciled the earlier recorded metrics (`MAE = 0.8898, RMSE = 1.0615, R² = 0.2698`) with the recomputed metrics (`MAE = 0.8767, RMSE = 1.0444, R² = 0.2930, Bias = -0.0885`). The recomputed metrics match the executed output of Cell 8 in the Phase 5 evaluation notebook and represent the exact behavior of the frozen disk artifacts.
3. **Architecture Verification:** Estimators are confirmed to be bare scikit-learn models without embedded preprocessing or imputation.
4. **Fallback Blend Terminology:** Corrected to distinguish the component linear model artifact (`final_elastic_net.joblib`) from the runtime 50/50 ensemble blend strategy.
5. **Negative Prediction Semantics:** Audited to preserve unclipped raw yield and raw unclipped mathematical energy, flag `NEGATIVE_PREDICTION_WARNING`, and exclude negative days from physical energy estimates admitted to positive totals.
6. **Date Classification Logic:** Verified against the 1,128 test observations from `2022-03-01` through `2022-04-23`, inclusive, correcting contradictory report phrasing.

### Remaining Unresolved Issues (Non-blocking for Stage 2, Blocking for Stage 3+):
1. **Blocking Issue B-1:** Energy basis (AC inverter output vs DC array yield) remains unverified in UNISOLAR ground truth.
2. **Blocking Issue B-2:** Prospective roof energy prediction remains blocked pending definition of an authorized synthetic or climatological lag-yield policy.
3. **Decision D-2:** Authoritative weather data source for non-UNISOLAR geographic locations remains unfinalized.
4. **Decision D-4:** Formal operational policy for negative yield predictions remains unresolved; raw outputs are preserved with warnings and excluded from positive totals.
