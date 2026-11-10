# Phase 5 — Model Evaluation and Finalization
## Master Technical Documentation & Final Model Evaluation Report

### 1. Phase Overview & Final Status

Phase 5 of Project **SolarSelect** completes the rigorous diagnostic evaluation, failure-mode analysis, model improvement experimentation, candidate selection, and final held-out test evaluation of solar yield forecasting models ($Y_{f,\text{day}} = \frac{\text{kWh}}{\text{kW}_p}$).

- **Current Status:** **PHASE 5 — FORMALLY COMPLETED AND FINALIZED (PROMPTS 1, 2, & 3 COMPLETED)**
- **Test-Partition Quarantine Compliance:** The **Test Partition (March 1, 2022 – April 23, 2022; Full Cohort: 1,232 rows; Peer Cohort: 1,128 rows)** was kept **STRICTLY QUARANTINED** throughout Phases 1–4 and Phase 5 Prompts 1–2. In Prompt 3, it was loaded and evaluated **EXACTLY ONCE** on frozen candidate models trained on the combined pre-test data (Train + Validation). Zero post-test iterative modifications or tuning were performed.

---

### 2. Prompt 1 Diagnostic Recap

In Prompt 1, deep diagnostic investigations established:
1. **Peer Cohort Negative $R^2$ Deconstruction:** Validation $R^2$ (ExtraTrees: $-0.2637$) was negative due to a seasonal level shift from winter/spring training ($\bar{y}=2.569$) to summer validation ($\bar{y}=4.260$), producing an underprediction bias of $\mu_{\text{err}} = +0.8338\text{ kWh}/\text{kW}_p/\text{day}$. $\text{Bias}^2 = 0.6953$ explained **38.4% of total MSE ($1.8122$)**, while the unbiased error variance ($1.1169$) was smaller than validation target variance ($1.4342$), yielding a debiased $R^2 = +0.2212$.
2. **Full Cohort ElasticNet Breakdown:** High $R^2$ ($0.8484$) was driven almost entirely by separating Site 19 (~18.2 kWh/kWp/day) from the other 23 sites. Evaluating on the other 23 sites yielded $R^2 = -0.1207$.
3. **ExtraTrees Saturation on High Yields:** Tree leaf averaging cannot extrapolate beyond training bounds (~25-28), causing severe underprediction on Site 19 summer days (30-41 kWh/kWp/day, MAE = $9.70$).
4. **Lag Imputation Stability:** Observations with `has_valid_lag1 == 0` did not exhibit elevated errors ($\text{MAE}=0.955$ vs $1.122$).

---

### 3. Prompt 2 Model Improvement Experiments Recap

All improvement experiments were designed strictly within the **Training partition (May 1 – Dec 31, 2021)** using 4-fold expanding-window temporal cross-validation with date-level grouping.

1. **Ensemble Blending:**
   - **Peer Cohort:** 50/50 ExtraTrees + ElasticNet Blend achieved **$\text{CV RMSE} = 1.2715 \pm 0.1846$** (vs. ExtraTrees $1.3190 \pm 0.1774$ and ElasticNet $1.3097 \pm 0.2338$). Approved as fallback.
   - **Full Cohort:** 70/30 ElasticNet + ExtraTrees Blend achieved **$\text{CV RMSE} = 2.1122 \pm 0.4010$** (vs. ElasticNet $2.1299$ and ExtraTrees $2.2048$). Approved as fallback.
2. **Astronomical Calibration & Site Bias Adjustment:** Both rejected due to negligible gain ($<0.0012\text{ RMSE}$) and unnecessary stateful overhead.

---

### 4. Prompt 3 Final Held-Out Test Evaluation Results

In Prompt 3, frozen candidate models were fitted on the **combined pre-test partition (Train + Validation: May 1, 2021 – February 28, 2022; Full: $N=5,807$, Peer: $N=5,328$)** and evaluated on the quarantined held-out **Test Partition (March 1 – April 23, 2022; Full: $N=1,232$, Peer: $N=1,128$)**.

#### Consolidated Held-Out Test Evaluation Matrix

| Cohort | Model Architecture | Role | Test MAE | Test RMSE | Test $R^2$ | Mean Bias | MAE % Mean | Acceptance Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| **Peer (22 Sites)** | Pre-test Mean Baseline | Baseline | 1.0118 | 1.2534 | -0.0181 | +0.1672 | 34.5% | Reference |
| | Persistence Baseline (Lag 1) | Reference | 1.0875 | 1.3713 | -0.2187 | +0.0236 | 37.1% | Reference |
| | **Tuned ExtraTrees** | **Primary** | **0.9050** | **1.0700** | **+0.2580** | **-0.1036** | **30.8%** | **ACCEPTED** |
| | **50/50 Ensemble Blend** | **Fallback** | **0.8898** | **1.0615** | **+0.2698** | **-0.1204** | **30.3%** | **ACCEPTED (Fallback)** |
| | Tuned ElasticNet | Component | 0.9329 | 1.0736 | +0.2530 | -0.1372 | 31.8% | Component |
| **Full (24 Sites)** | Pre-test Mean Baseline | Baseline | 1.9422 | 3.8327 | -0.0016 | -0.1523 | 52.3% | Reference |
| | Persistence Baseline (Lag 1) | Reference | 1.3952 | 2.4225 | +0.5996 | +0.0428 | 37.6% | Reference |
| | **Tuned ElasticNet** | **Primary** | **1.1463** | **1.9494** | **+0.7407** | **-0.3144** | **30.9%** | **CONDITIONALLY ACCEPTED** |
| | **70/30 Ensemble Blend** | **Fallback** | **1.1623** | **1.9567** | **+0.7388** | **-0.3394** | **31.3%** | **CONDITIONALLY ACCEPTED** |
| | Tuned ExtraTrees | Component | 1.2581 | 2.0583 | +0.7109 | -0.3976 | 33.9% | Component |

---

### 5. Detailed Test Diagnostics & Findings

1. **Resolution of Seasonal Bias in Peer Cohort:**
   - Training on combined pre-test data (which encompasses winter, spring, and peak summer) successfully resolved the severe underprediction bias observed during summer validation.
   - On the autumn test set, Tuned ExtraTrees achieved **positive $R^2 = +0.2580$**, reducing MAE by **16.8%** and RMSE by **22.0%** relative to the day-ahead persistence baseline.
   - Mean bias fell to just $-0.1036\text{ kWh}/\text{kW}_p/\text{day}$.
2. **Monthly Autumn Transition:**
   - **March 2022 ($N=660$, Actual Mean $3.367$):** Tuned ExtraTrees achieved $\text{MAE} = 0.9108$, $\text{RMSE} = 1.0401$, $\mathbf{R^2 = +0.2269}$, $\text{Bias} = -0.0614$.
   - **April 2022 ($N=468$, Actual Mean $2.321$):** Tuned ExtraTrees achieved $\text{MAE} = 0.8967$, $\text{RMSE} = 1.1107$, $R^2 = -0.0401$, $\text{Bias} = -0.1631$. While absolute tracking error remained below $0.90$, cross-sectional variance compressed significantly in late autumn, suppressing nominal $R^2$.
3. **Site-Wise Performance & Anomalies:**
   - Normal peer sites (Sites 15–40 excl. 19 & 24) exhibited consistent test MAEs ranging from $0.66$ to $1.15\text{ kWh}/\text{kW}_p/\text{day}$.
   - **Site 19 ($N=52$, Actual Mean $19.00$):** Tuned ElasticNet achieved $\text{MAE} = 6.3211$ and $\text{RMSE} = 7.7196$ ($\text{Pred Mean} = 22.01$). Linear formulation gracefully handled the $492\%$ STC generation without model failure.
   - **Site 24 ($N=52$, Actual Mean $5.379$):** Tuned ElasticNet achieved $\text{MAE} = 1.8561$, $\text{RMSE} = 2.2774$, with near-zero bias of $-0.0093$ ($\text{Pred Mean} = 5.388$).
4. **Yield Level & Lag Impact:**
   - Moderate generation days ($2.0 \le Y_f < 4.0$, $N=599$) had lowest MAE of $0.5954$.
   - Missing lag observations (`has_valid_lag1 == 0`, $N=58$) showed comparable error ($\text{MAE} = 0.8992$) to full lag observations ($N=1,070, \text{MAE} = 0.9053$), verifying the robustness of the imputation pipeline.

---

### 6. Formal Model Acceptance Verdicts

1. **Peer Cohort Primary Model (Tuned ExtraTrees):** **ACCEPTED**
   - Generalizes effectively to previously unseen autumn observations.
   - Substantially outperforms persistence benchmark.
   - Ultra-fast inference latency ($<15\text{ ms}$).
   - Designated as the primary forecasting engine for Layer B panel recommendation across clean physical sites.
2. **Peer Cohort Fallback Model (50/50 Ensemble Blend):** **ACCEPTED (Authorized Fallback)**
   - Delivers marginally superior MAE ($0.8898$) and RMSE ($1.0615$) via variance reduction.
   - Authorized for deployment when dual-model execution overhead is acceptable.
3. **Full Cohort Primary Model (Tuned ElasticNet):** **CONDITIONALLY ACCEPTED WITH DOCUMENTED LIMITATIONS**
   - High nominal $R^2$ ($0.7407$) and low overall MAE ($1.1463$) across all 24 sites.
   - Accepted strictly for campus-level tracking under the explicit documented limitation that Site 19 and 24 represent unverified capacity/data anomalies.

---

### 7. Directory Structure and Serialized Artifacts

```
SolarSelect/
├── models/
│   ├── phase4/ (Preserved Phase 4 models)
│   └── phase5/
│       ├── final/ (Final models trained on Train+Val pre-test data)
│       │   ├── full_cohort/
│       │   │   ├── final_elastic_net.joblib
│       │   │   └── final_extra_trees.joblib
│       │   └── peer_cohort/
│       │       ├── final_extra_trees.joblib
│       │       └── final_elastic_net.joblib
│       └── final_model_metadata.json (Comprehensive metadata & audit trail)
├── notebooks/
│   └── phase5/
│       ├── README.md (This master document)
│       ├── model_diagnostics_and_improvement_investigation.ipynb (Prompt 1)
│       ├── model_improvement_experiments.ipynb (Prompt 2)
│       ├── final_model_evaluation_and_generalization.ipynb (Prompt 3 Master Notebook)
│       └── figures/
│           ├── figure_p5_exp1_blend_weight_curve.png
│           ├── figure_p5_exp2_3_calibration_comparison.png
│           ├── figure_p5_exp4_candidate_comparison.png
│           ├── figure_p5_test_actual_vs_predicted.png
│           ├── figure_p5_test_residuals_and_distributions.png
│           ├── figure_p5_test_site_wise_performance.png
│           ├── figure_p5_test_monthly_autumn_transition.png
│           └── [Prompt 1 diagnostic figures]
└── reports/
    └── phase5/
        ├── improvement_experiments_results.csv
        ├── improvement_experiments_summary.json
        ├── validation_comparison_secondary.csv
        ├── test_evaluation_results.csv
        └── test_site_evaluation.csv
```

---

### 8. Phase 6 Handover Notes (Recommendation Engine & Uncertainty)

With Phase 5 formally closed, the forecasting foundation (Layer A) is complete:
1. **Model Handover:** For individual site solar panel recommendation in Layer B, use the **Peer Cohort Tuned ExtraTrees model** (`models/phase5/final/peer_cohort/final_extra_trees.joblib`) or the **50/50 Ensemble Blend**.
2. **Uncertainty Bounds:** The residual standard error on held-out test data ($\sigma \approx 1.06\text{ kWh}/\text{kW}_p/\text{day}$) provides empirical calibration for conformal prediction intervals in downstream recommendation.
3. **Integration with Hardware Parameters:** Layer B will integrate predicted specific yield ($Y_f$) with specific panel temperature coefficients ($\gamma_{\text{Pmp}}$), degradation curves, and CAPEX/OPEX constraints to produce optimal multi-criteria panel rankings.
