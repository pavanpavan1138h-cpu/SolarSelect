# Final Model Reference — SolarSelect

This document serves as the authoritative technical reference for the final offline evaluated machine learning forecasting models in **SolarSelect Layer A**.

---

## 1. Designated Offline Evaluated Models

```text
Final Offline Evaluated Models (Phase 5 Prompt 3 Finalized)
├── Clean Physical Sites (Peer Cohort Benchmark — Primary for Layer B)
│   ├── Primary Model : Tuned ExtraTreesRegressor
│   │   └── Artifact : models/phase5/final/peer_cohort/final_extra_trees.joblib
│   └── Fallback Model: 50/50 Ensemble Blend (ExtraTrees + ElasticNet)
│       └── Artifacts: models/phase5/final/peer_cohort/final_extra_trees.joblib
│                      models/phase5/final/peer_cohort/final_elastic_net.joblib
└── Campus-Wide Aggregations (Full Cohort — Conditional Macro Use)
    ├── Primary Model : Tuned ElasticNet
    │   └── Artifact : models/phase5/final/full_cohort/final_elastic_net.joblib
    └── Fallback Model: 70/30 Ensemble Blend (ElasticNet + ExtraTrees)
        └── Artifacts: models/phase5/final/full_cohort/final_elastic_net.joblib
                       models/phase5/final/full_cohort/final_extra_trees.joblib
```

---

## 2. Model Specifications & Hyperparameters

### A. Peer Cohort Primary: Tuned ExtraTreesRegressor
- **Algorithm:** Extremely Randomized Trees Regressor (`sklearn.ensemble.ExtraTreesRegressor`).
- **Hyperparameters:**
  ```python
  ExtraTreesRegressor(
      n_estimators=100,
      max_depth=12,
      min_samples_split=2,
      min_samples_leaf=1,
      max_features=0.8,
      random_state=42,
      n_jobs=-1
  )
  ```
- **Training Data:** Combined Pre-Test Peer Cohort ($N = 5,328$ site-days, May 1, 2021 – February 28, 2022).
- **Test Set Evaluation ($N = 1,128$, March 1 – April 23, 2022):**
  * **MAE:** $\mathbf{0.9050\text{ kWh}/\text{kW}_p/\text{day}}$
  * **RMSE:** $\mathbf{1.0700\text{ kWh}/\text{kW}_p/\text{day}}$
  * **$R^2$:** $\mathbf{+0.2580}$
  * **Mean Bias:** $\mathbf{-0.1036\text{ kWh}/\text{kW}_p/\text{day}}$ (Actual $-$ Predicted)
  * **MAE % of Test Mean:** $30.85\%$ (against actual mean $2.9335\text{ kWh}/\text{kW}_p/\text{day}$)
- **In-Memory Size & Latency:** $17.7\text{ MB}$, offline inference latency $\approx 14.2\text{ ms}$ per site-day.
- **Acceptance Status:** **ACCEPTED (Offline Evaluated Model).**

### B. Full Cohort Primary: Tuned ElasticNet
- **Algorithm:** Regularized Linear Model with $L_1$ and $L_2$ penalties (`sklearn.linear_model.ElasticNet`).
- **Hyperparameters:**
  ```python
  ElasticNet(
      alpha=0.05,
      l1_ratio=0.90,
      random_state=42,
      max_iter=5000
  )
  ```
- **Training Data:** Combined Pre-Test Full Cohort ($N = 5,807$ site-days, May 1, 2021 – February 28, 2022).
- **Test Set Evaluation ($N = 1,232$, March 1 – April 23, 2022):**
  * **MAE:** $\mathbf{1.1463\text{ kWh}/\text{kW}_p/\text{day}}$
  * **RMSE:** $\mathbf{1.9494\text{ kWh}/\text{kW}_p/\text{day}}$
  * **$R^2$:** $\mathbf{+0.7407}$
  * **Mean Bias:** $\mathbf{-0.3144\text{ kWh}/\text{kW}_p/\text{day}}$
  * **MAE % of Test Mean:** $30.86\%$ (against actual mean $3.7149\text{ kWh}/\text{kW}_p/\text{day}$)
- **In-Memory Size & Latency:** $2.7\text{ KB}$, offline inference latency $\approx 350\ \mu\text{s}$ per site-day.
- **Acceptance Status:** **CONDITIONALLY ACCEPTED WITH DOCUMENTED LIMITATIONS.**

---

## 3. Strict Boundary Conditions on Evaluation Claims

> [!WARNING]
> **Scientific Caveats on Evaluation:**
> 1. **Temporal vs. Spatial Generalization:** Generalization has been verified **across time on known rooftop installations** (evaluating on unseen autumn dates for the same 22 campus sites). It has **NOT been evaluated across unseen geographic regions or continents**.
> 2. **Positive $R^2$ Context:** While $R^2 = +0.2580$ represents a major improvement over the persistence baseline ($R^2 = -0.2187$) and confirms that the model captures true out-of-sample variance, it does **not denote perfect generalization**. Late autumn variance compression (e.g. April $R^2 = -0.0401$) demonstrates that nominal $R^2$ remains highly sensitive to seasonal target variance.
> 3. **Uncertainty Calibration Protocol:** In accordance with rigorous statistical practices, **held-out test-set residuals must NEVER be used to calibrate prediction intervals or uncertainty bounds**. Uncertainty estimation in Phase 8 must be calibrated strictly using training/validation out-of-fold residuals (e.g., via conformal prediction or cross-validation quantile residuals) to prevent test-set contamination.
> 4. **Day-Ahead Weather Assumption:** Offline evaluations were conducted using historical BOM weather readings. In operational deployment, day-ahead inference requires numerical weather prediction (NWP) inputs.
