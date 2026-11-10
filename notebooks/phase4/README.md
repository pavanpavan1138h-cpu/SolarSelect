# Phase 4 — Model Development and Comparison
## Master Technical Documentation & Final Model Selection

### 1. Phase Overview & Final Status

Phase 4 of Project **SolarSelect** establishes the empirical baseline, architectural experimentation, temporal hyperparameter optimization, model interpretability, and multi-objective selection of forecasting models for daily solar specific yield:
$$Y_{f,\text{day}} = \frac{\text{kWh}}{\text{kW}_p}\quad [\text{kWh}/\text{kW}_p/\text{day}]$$

- **Final Phase Status:** **PHASE 4 — COMPLETED WITH DOCUMENTED LIMITATIONS**
- **Test Set Quarantine:** The **Test Split (March 1, 2022 – April 23, 2022)** was **STRICTLY QUARANTINED and NEVER LOADED OR EVALUATED** during Phase 4. It remains completely preserved for final evaluation in Phase 5.

---

### 2. Feature Verification & Resolution of Prompt 1 Discrepancies

#### A. Feature Name Reconciliation
During the Prompt 2 audit, a documentation discrepancy in the Prompt 1 narrative report was formally reconciled:
- The actual feature matrices in `data/processed/unisolar/` have strictly adhered to the authoritative Phase 3 Feature Dictionary.
- Features described informally in Prompt 1 narrative (such as `dc_capacity_kwp`, `day_length_hours`, `weather_cloud_cover_mean`) were strictly documentation labels; the underlying code and serialized models have always utilized the exact 29 Phase 3 feature names:
  1. *Static Metadata (3):* `kWp`, `lat`, `Lon`
  2. *Calendar & Cyclical (8):* `day_of_year`, `month`, `day_of_week`, `is_weekend`, `sin_doy`, `cos_doy`, `sin_month`, `cos_month`
  3. *Solar Geometry (5):* `solar_declination_deg`, `solar_noon_elevation_deg`, `solar_noon_zenith_deg`, `daylight_hours`, `extraterrestrial_radiation_h0`
  4. *Autoregressive Generation (8):* `has_valid_lag1`, `lag1_daily_yield`, `lag2_daily_yield`, `lag7_daily_yield`, `rolling_mean_7d_yield`, `rolling_std_7d_yield`, `rolling_mean_14d_yield`, `rolling_mean_30d_yield`
  5. *Historical Weather (5):* `lag1_temp_mean`, `lag1_temp_max`, `lag1_temp_min`, `lag1_temp_range`, `lag1_rh_mean`
- Non-existent features (e.g., same-day cloud cover or wind speed) were never present in the actual training matrices.

#### B. Chronological Partition Verification
- **Training Split:** May 1, 2021 – December 31, 2021 (245 calendar days, 234 active days; Full: 4,770 rows, Peer: 4,383 rows).
- **Validation Split:** January 1, 2022 – February 28, 2022 (59 calendar days; Full: 1,037 rows, Peer: 945 rows).
- **Test Split (Quarantined):** March 1, 2022 – April 23, 2022 (54 calendar days; Full: 1,232 rows, Peer: 1,128 rows).
  *(Note: Corrects the Prompt 1 narrative text which erroneously stated April 30; the true dataset end date is April 23, 2022).*

---

### 3. Temporal Cross-Validation Scheme

To tune hyperparameters without look-ahead bias or data leakage:
- **Expanding-Window Cross-Validation:** Constructed 4 chronological folds strictly within the 234 training calendar dates:
  - Fold 1: Train days 1–120 $\rightarrow$ Validate days 121–150 (30 days)
  - Fold 2: Train days 1–150 $\rightarrow$ Validate days 151–180 (30 days)
  - Fold 3: Train days 1–180 $\rightarrow$ Validate days 181–205 (25 days)
  - Fold 4: Train days 1–205 $\rightarrow$ Validate days 206–234 (29 days)
- **Strict Grouping by Date:** All installations for a given calendar date belong exclusively to the training fold or the validation fold. Zero cross-site leakage on the same calendar day.
- **Pipeline Isolation:** All feature transformations (`StandardScaler`) were fit strictly within each training fold.

---

### 4. Hyperparameter Optimization Results

Focused tuning on leading candidates yielded:
1. **Dataset A (Full Cohort — 24 Sites):**
   - **Tuned Elastic Net:** $\alpha = 0.05$, $l_1\text{\_ratio} = 0.9$, $\text{max\_iter} = 3000$. (Temporal CV RMSE: $2.1299$).
   - **Tuned Extra Trees:** $n\text{\_estimators} = 50$, $\text{max\_depth} = 10$, $\text{min\_samples\_split} = 5$, $\text{min\_samples\_leaf} = 2$, $\text{max\_features} = 1.0$. (Temporal CV RMSE: $2.2048$).
2. **Dataset B (Peer Cohort — 22 Sites):**
   - **Tuned Extra Trees:** $n\text{\_estimators} = 100$, $\text{max\_depth} = 12$, $\text{min\_samples\_split} = 2$, $\text{min\_samples\_leaf} = 1$, $\text{max\_features} = 0.8$. (Temporal CV RMSE: $1.3190$).
   - **Tuned Elastic Net:** $\alpha = 0.05$, $l_1\text{\_ratio} = 0.7$, $\text{max\_iter} = 3000$. (Temporal CV RMSE: $1.3097$).

---

### 5. Final Validation Performance Leaderboard

#### Dataset A: Full Cohort (24 Sites, Val $N=1,037$)
| Status / Role | Model Name | Family | MAE ($\text{kWh}/\text{kW}_p/\text{day}$) | RMSE ($\text{kWh}/\text{kW}_p/\text{day}$) | $R^2$ Score |
|---|---|---|---:|---:|---:|
| **Primary ML Candidate** | **Tuned Elastic Net** | Linear Regularized | **1.3765** | **2.0134** | **0.8484** |
| Fallback ML Candidate | Tuned Extra Trees | Tree Ensemble | 1.4924 | 2.7264 | 0.7220 |
| Reference Benchmark | Baseline: Persistence (Lag 1) | Empirical Heuristic | 1.4981 | 3.1874 | 0.6207 |
| Initial Baseline | Baseline: Train Mean | Heuristic Constant | 2.3955 | 5.5986 | -0.1724 |
| Initial Baseline | Baseline: Train Median | Heuristic Constant | 3.0660 | 5.9961 | -0.3452 |

#### Dataset B: Peer Cohort (22 Sites, Val $N=945$)
| Status / Role | Model Name | Family | MAE ($\text{kWh}/\text{kW}_p/\text{day}$) | RMSE ($\text{kWh}/\text{kW}_p/\text{day}$) | $R^2$ Score |
|---|---|---|---:|---:|---:|
| **Primary ML Candidate** | **Tuned Extra Trees** | Tree Ensemble | **1.0793** | **1.3462** | **-0.2637** |
| Fallback ML Candidate | Tuned Elastic Net | Linear Regularized | 1.3871 | 1.6366 | -0.8677 |
| Reference Benchmark | Baseline: Persistence (Lag 1) | Empirical Heuristic | 1.1319 | 1.4984 | -0.5661 |
| Initial Baseline | Baseline: Train Mean | Heuristic Constant | 1.7503 | 2.0716 | -1.9924 |
| Initial Baseline | Baseline: Train Median | Heuristic Constant | 2.0792 | 2.3812 | -2.9520 |

---

### 6. Interpretability & Feature Importance Insights

1. **Full Cohort (Elastic Net):**
   - Autoregressive generation features dominate: `rolling_mean_30d_yield` (standardized coef: $+1.782$, permutation drop: $+2.692$ RMSE), `rolling_mean_14d_yield` ($+0.693$), and `lag1_daily_yield` ($+0.311$).
   - *Physical Mechanism:* In the Full Cohort, long-term rolling mean yield is the primary differentiator between Site 19 (~18.2 kWh/kWp/day) and standard peer installations (~2.8 kWh/kWp/day).
   - Historical weather feature `lag1_rh_mean` (relative humidity) carries a negative standardized coefficient ($-0.097$), capturing overcast/moisture-induced solar attenuation.
2. **Peer Cohort (Extra Trees):**
   - Top permutation importance features: `lag1_temp_min` ($+0.069$ RMSE drop), `rolling_mean_30d_yield` ($+0.035$), `rolling_mean_14d_yield` ($+0.022$), `lag2_daily_yield` ($+0.010$), and `extraterrestrial_radiation_h0` ($+0.006$).
   - Impurity-based (MDI) importance overweights high-cardinality continuous features, whereas validation permutation importance reveals that minimum temperature (`lag1_temp_min`, a proxy for overnight radiative cooling vs overcast blanket) and solar geometry provide vital physical constraints.

---

### 7. Residual Diagnostics & Peer Cohort Negative $R^2$ Analysis

#### The Mathematics of Negative $R^2$ in Seasonal Regime Shifts
In the Peer Cohort, validation $R^2$ is negative across all algorithms (Extra Trees: $-0.2637$, Persistence: $-0.5661$, Train Mean: $-1.9924$).
- **Formal Definition:** $R^2 = 1 - \frac{\text{MSE}}{\text{Var}(y_{\text{val}})}$. A negative $R^2$ indicates that the squared error exceeds that of predicting the validation split mean ($\bar{y}_{\text{val}} = 4.260$).
- **Why Predicting the Validation Mean is Impossible at Runtime:** In an operational forecasting setting, the future summer mean cannot be known during winter/spring. The only known historical baseline is $\bar{y}_{\text{train}} = 2.569$.
- **Small Denominator Sensitivity:** Austral midsummer (Jan–Feb) exhibits very low cross-sectional variance across the 22 peer sites ($\sigma = 1.198$, $\text{Var} = 1.436$). Even an exceptionally accurate forecast with $\text{RMSE} = 1.346$ ($\text{MSE} = 1.812$) yields $1 - \frac{1.812}{1.436} = -0.2637$.
- **Operational Reality:** **Tuned Extra Trees ($\text{RMSE} = 1.3462$) reduces MSE from 4.29 (Train Mean baseline) to 1.81, an improvement of 57.8% in squared error and 35.0% in RMSE**, while also beating the strong Persistence benchmark ($\text{RMSE} = 1.4984$).

#### Site 19 and Site 24 Behavior
- In the Full Cohort, Site 19's extreme values are tracked effectively by Elastic Net via long-term rolling mean yield. However, tree models exhibit slight underprediction on peak midsummer days ($>30\text{ kWh}/\text{kW}_p/\text{day}$) due to leaf-node averaging. Observations are preserved in full without clipping.

---

### 8. Multi-Objective Comparison & Operational Feasibility

| Cohort | Candidate Model | Role | Validation MAE | Validation RMSE | Artifact Size | Latency per Site-Day |
|---|---|---|---:|---:|---:|---:|
| **Full Cohort (24)** | **Tuned Elastic Net** | **Primary ML** | **1.3765** | **2.0134** | **2.7 KB** | **$350\ \mu\text{s}$** |
| Full Cohort (24) | Tuned Extra Trees | Fallback ML | 1.4924 | 2.7264 | 1,884.5 KB | $14,367\ \mu\text{s}$ |
| Full Cohort (24) | Persistence (Lag 1) | Reference Benchmark | 1.4981 | 3.1874 | 0.0 KB | $0.0\ \mu\text{s}$ |
| **Peer Cohort (22)** | **Tuned Extra Trees** | **Primary ML** | **1.0793** | **1.3462** | **17,671.8 KB** | **$14,206\ \mu\text{s}$** |
| Peer Cohort (22) | Tuned Elastic Net | Fallback ML | 1.3871 | 1.6366 | 2.7 KB | $341\ \mu\text{s}$ |
| Peer Cohort (22) | Persistence (Lag 1) | Reference Benchmark | 1.1319 | 1.4984 | 0.0 KB | $0.0\ \mu\text{s}$ |

*Latency was measured over 500 repeated single-row predictions using `time.perf_counter_ns`.*

---

### 9. Persisted Artifacts & Documentation Map

```
SolarSelect/
├── models/
│   └── phase4/
│       ├── model_metadata.json
│       ├── full_cohort/
│       │   ├── tuned_elastic_net.joblib
│       │   ├── tuned_extra_trees.joblib
│       │   └── [8 initial baseline model artifacts]
│       └── peer_cohort/
│           ├── tuned_extra_trees.joblib
│           ├── tuned_elastic_net.joblib
│           └── [8 initial baseline model artifacts]
├── reports/
│   └── phase4/
│       ├── experiment_results.csv
│       ├── experiment_results.json
│       └── feature_importance_analysis.csv
└── notebooks/
    └── phase4/
        ├── README.md
        ├── baseline_and_model_development.ipynb
        ├── experiment_results.csv
        └── figures/
            ├── actual_vs_predicted_top_models.png
            ├── hyperparameter_tuning_cv_surface.png
            ├── multiobjective_tradeoffs.png
            ├── permutation_feature_importance.png
            ├── residual_distribution_analysis.png
            ├── seasonal_distribution_shift_and_residuals.png
            ├── site_wise_error_analysis.png
            └── validation_metrics_comparison.png
```

---

### 10. Reproducibility

To re-execute the complete Phase 4 workflow top-to-bottom:
```bash
jupyter nbconvert --to notebook --execute notebooks/phase4/baseline_and_model_development.ipynb --inplace
```
All 22 cells execute deterministically with 0 errors.
