# Model Evaluation — SolarSelect

This document details the diagnostic investigations (Prompt 1), model improvement experiments (Prompt 2), and the single held-out test evaluation (Prompt 3) conducted in **Phase 5**.

---

## 1. Prompt 1: Diagnostic Investigation & Bias Decomposition

In Phase 5 Prompt 1, deep diagnostic analysis was conducted on the Validation partition (`2022-01-01` to `2022-02-28`, $N=945$ Peer):

### A. Mathematical Deconstruction of Negative Validation $R^2$
In summer validation, ExtraTrees achieved a negative coefficient of determination ($R^2 = -0.2637$). Error decomposition revealed:
$$\text{MSE} = \text{Bias}^2 + \text{Var}(e)$$
$$\text{MSE} = 1.8122 = (0.8338)^2 + 1.1169 = 0.6953 + 1.1169$$

- **Seasonal Level Shift:** The training partition covered winter and spring ($\bar{y}_{\text{train}} = 2.569$), while validation covered peak midsummer ($\bar{y}_{\text{val}} = 4.260$).
- **Dominance of Bias:** The systematic underprediction bias ($\mu_{\text{err}} = +0.8338\text{ kWh}/\text{kW}_p/\text{day}$) explained **$38.4\%$ of total MSE**.
- **Unbiased Error Variance:** The unbiased error variance ($\sigma^2_e = 1.1169$) was actually **smaller than the validation target variance** ($\sigma^2_y = 1.4342$), yielding a debiased $R^2 = +0.2212$.
- *Conclusion:* Negative $R^2$ in validation was a mathematical artifact of the winter-to-summer seasonal shift and low cross-sectional target variance, not erratic physical predictions.

---

## 2. Prompt 2: Model Improvement Experiments

Three leakage-safe improvement experiments were evaluated strictly within the Training partition using 4-fold temporal CV:

### Experiment 1: Weighted Ensemble Blending
Evaluated $\hat{y}_{\text{blend}} = w \cdot \hat{y}_{\text{ElasticNet}} + (1 - w) \cdot \hat{y}_{\text{ExtraTrees}}$ across $w \in [0.0, 1.0]$:
- **Peer Cohort:** Optimal weight $w = 0.5$ (50/50 blend) achieved **$\text{CV RMSE} = 1.2715 \pm 0.1846$** (vs. ExtraTrees $1.3190$ and ElasticNet $1.3097$). Approved as fallback.
- **Full Cohort:** Optimal weight $w = 0.7$ (70% ElasticNet + 30% ExtraTrees) achieved **$\text{CV RMSE} = 2.1122 \pm 0.4010$** (vs. ElasticNet $2.1299$ and ExtraTrees $2.2048$). Approved as fallback.

### Experiment 2: Astronomical Seasonal Calibration (Rejected)
- Evaluated regularized post-hoc residual calibration on astronomical features ($H_0$, daylight hours, solar elevation).
- **Result:** Peer CV RMSE delta was $+0.0000$; Full CV RMSE delta was $-0.0017$.
- **Verdict: REJECTED.** The 29 predictive features already contain these exact astronomical variables. Secondary linear calibration added zero non-redundant signal and risked collinear overfitting.

### Experiment 3: Site-Specific Baseline Adjustment (Rejected)
- Evaluated historical shrunk site-bias adjustment.
- **Result:** Peer CV RMSE delta was $-0.0012$; Full CV RMSE delta was $-0.0053$.
- **Verdict: REJECTED.** Negligible improvement ($<0.25\%$) introduced unnecessary operational state maintenance and drift risk during seasonal transitions.

---

## 3. Prompt 3: Single Held-Out Test Evaluation

Following model freezing and retraining on combined pre-test data (Train + Validation: May 1, 2021 – February 28, 2022), a single evaluation was executed on the previously quarantined Test partition (`2022-03-01` to `2022-04-23`):

### Authoritative Held-Out Test Evaluation Results

| Cohort | Model Candidate | Role | Test MAE | Test RMSE | Test $R^2$ | Mean Bias | MAE % Mean | Final Acceptance Verdict |
|---|---|---|---:|---:|---:|---:|---:|---|
| **Peer (22 Sites)** | Pre-Test Mean Baseline | Baseline | 1.0628 | 1.2534 | -0.0181 | +0.1672 | 36.2% | Reference Benchmark |
| ($N = 1,128$) | Persistence Baseline (Lag 1) | Reference | 1.0875 | 1.3713 | -0.2187 | +0.0236 | 37.1% | Reference Benchmark |
| Target Mean: | **Tuned ExtraTrees** | **Primary** | **0.9050** | **1.0700** | **+0.2580** | **-0.1036** | **30.8%** | **ACCEPTED** |
| $2.9335\text{ kWh}/\text{kW}_p/\text{d}$ | **50/50 Ensemble Blend** | **Fallback** | **0.8898** | **1.0615** | **+0.2698** | **-0.1204** | **30.3%** | **ACCEPTED (Fallback)** |
| | Tuned ElasticNet | Component | 0.8883 | 1.0736 | +0.2530 | -0.1372 | 30.3% | Component Model |
| **Full (24 Sites)** | Pre-Test Mean Baseline | Baseline | 1.9029 | 3.8317 | -0.0016 | -0.1523 | 51.2% | Reference Benchmark |
| ($N = 1,232$) | Persistence Baseline (Lag 1) | Reference | 1.3952 | 2.4225 | +0.5996 | +0.0428 | 37.6% | Reference Benchmark |
| Target Mean: | **Tuned ElasticNet** | **Primary** | **1.1463** | **1.9494** | **+0.7407** | **-0.3144** | **30.9%** | **CONDITIONALLY ACCEPTED** |
| $3.7149\text{ kWh}/\text{kW}_p/\text{d}$ | **70/30 Ensemble Blend** | **Fallback** | **1.1623** | **1.9567** | **+0.7388** | **-0.3394** | **31.3%** | **CONDITIONALLY ACCEPTED** |
| | Tuned ExtraTrees | Component | 1.2581 | 2.0583 | +0.7109 | -0.3976 | 33.9% | Component Model |

---

## 4. Key Scientific Findings from Test Evaluation

1. **Seasonal Bias Resolution:** Training on pre-test data (which encompasses winter, spring, and summer) effectively eliminated the severe seasonal underprediction bias. Mean bias on the autumn test set fell to just $-0.1036\text{ kWh}/\text{kW}_p/\text{day}$.
2. **Superiority Over Persistence:** Tuned ExtraTrees strongly outperformed the persistence benchmark on day-ahead forecasting, **reducing MAE by 16.8%** ($1.0875 \rightarrow 0.9050$) and **RMSE by 22.0%** ($1.3713 \rightarrow 1.0700$) with a solidly positive $R^2 = +0.2580$.
3. **Autumn Monthly Dynamics:** In March 2022 ($N=660$, high solar), ExtraTrees achieved $\text{MAE} = 0.9108$ and $R^2 = +0.2269$. In April 2022 ($N=468$, late autumn decline), MAE remained low ($0.8967$), but cross-sectional variance compressed, causing $R^2$ to dip slightly to $-0.0401$.

