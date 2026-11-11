# Phase 8 Stage 4: Temperature Evaluation & Methodology Audit Report

**SolarSelect MLOps Engineering Laboratory**  
**Lifecycle Stage:** Phase 8 — Stage 4: Temperature Evaluation (Method A/B)  
**Status:** Evaluation Complete — Method B Disabled (Method A Active Empirical Baseline)  
**Audit Session:** Session 63 (Initial Audit) / Session 64 (Scientific & Evidence Reconciliation)  
**Date:** 2026-11-11  
**Author:** SolarSelect Engineering Team  

---

## 1. Executive Summary

Phase 8 Stage 4 conducts an evidence-based methodology and implementation-readiness audit to determine whether an explicit module-temperature correction is scientifically justified, empirically calibratable, and technically viable for the SolarSelect energy estimation pipeline.

### Core Audit Findings:
1. **Existing Model Empirical Associations:** The frozen Phase 5 Peer Cohort model ([`final_extra_trees.joblib`](../../models/phase5/final/peer_cohort/final_extra_trees.joblib) and [`final_elastic_net.joblib`](../../models/phase5/final/peer_cohort/final_elastic_net.joblib)) was trained on operational rooftop telemetry. Its target is observed daily specific yield ($Y = E_{daily} / kWp$ in $\text{kWh/kWp/day}$), an operational measurement that inherently reflects real-world system behavior (including ambient heating, inverter performance, soiling, and weather). Furthermore, the model incorporates four historical weather features derived from lagged ambient air temperatures from day $t-1$ (`lag1_temp_mean`, `lag1_temp_max`, `lag1_temp_min`, `lag1_temp_range`). In the linear ElasticNet component, `lag1_temp_mean` carries a negative coefficient ($-0.1474$), representing a conditional predictive association between warmer prior-day ambient temperatures and lower specific yield in this dataset, rather than causal proof or an isolated physical thermal model.
2. **Material and Unquantified Double-Counting Risk:** Applying an external module-temperature correction ($P(T) = P_{ref} \times [1 + \gamma (T_{cell} - 25)]$) directly to the Phase 5 prediction $\hat{Y}$ introduces a material and unquantified risk of double-counting temperature effects. Because the model already uses lagged ambient temperatures as predictive inputs and was trained to predict observed operational yield, an uncalibrated post-hoc adjustment risks penalizing an output that already reflects operational yield depression.
3. **Severe Telemetry & Meteorological Deficits:** Auditing the UNISOLAR dataset confirms that cell temperature ($T_{cell}$), back-of-module temperature ($T_{module}$), plane-of-array irradiance ($G_{POA}$), and terrestrial global horizontal irradiance ($GHI$) are **100% absent** from the repository. Physical heat-balance models cannot be driven without surface irradiance data.
4. **Catalogue Specification & Standard Distinction:** While all 12 catalogue modules record a temperature coefficient $\gamma_{Pmax}$, NOCT is reported for 8 modules and NMOT for 4 modules. NOCT (open-circuit, IEC 61215-2) and NMOT (maximum power point, IEC 61215:2016) represent distinct measurement standards and are not interchangeable.
5. **Implementation Decision:** **Method A is retained as the active empirical baseline for supported historical replay.** **Method B (Additional Module-Temperature Correction) remains experimental and disabled.** No additional temperature correction is authorized, and zero temperature correction code has been introduced into the runtime engine.

---

## 2. Phase 5 Temperature-Feature & Model Semantic Audit

### 2.1 Target Definition and Physical Semantics
- **Target Variable:** `target_daily_yield` defined as:
  $$Y = \frac{E_{daily}}{kWp} \quad \left[\frac{\text{kWh}}{\text{kWp}\cdot\text{day}}\right]$$
  where $E_{daily}$ is the total daily generation recorded at the site AC inverter / generation meter, and $kWp$ is the installed DC nameplate capacity.
- **Physical Interpretation:** $Y$ is an **observed operational yield ratio**. It is **not** an STC-normalized reference yield ($1000\text{ W/m}^2$, $25^\circ\text{C}$ cell temperature) and not a temperature-neutral potential. While the observed generation embodies the aggregated effects of real operating systems (including thermal derating, inverter clipping, wiring losses, and weather variability), the statistical models do **not** isolate, separate, or quantify any individual physical loss mechanism. The model does not explicitly model panel-specific thermal response.

### 2.2 Inventory of Predictive Features (29 Features)
The frozen Phase 5 model strictly requires the following 29 features:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Phase 5 Feature Space (29 Features)                  │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Static Metadata (3):        kWp, lat, Lon                           │
│ 2. Calendar & Cyclical (8):     day_of_year, month, day_of_week,       │
│                                is_weekend, sin_doy, cos_doy,           │
│                                sin_month, cos_month                    │
│ 3. Solar Geometry (5):         solar_declination_deg,                  │
│                                solar_noon_elevation_deg,               │
│                                solar_noon_zenith_deg, daylight_hours,  │
│                                extraterrestrial_radiation_h0          │
│ 4. Autoregressive Lags (8):    has_valid_lag1, lag1_daily_yield,       │
│                                lag2_daily_yield, lag7_daily_yield,     │
│                                rolling_mean_7d_yield,                  │
│                                rolling_std_7d_yield,                   │
│                                rolling_mean_14d_yield,                 │
│                                rolling_mean_30d_yield                  │
│ 5. Historical Weather (5):     lag1_temp_mean, lag1_temp_max,          │
│                                lag1_temp_min, lag1_temp_range,         │
│                                lag1_rh_mean                            │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Thermal Feature Importance vs. Physical Causation
Audit of the Phase 4 feature importance analysis ([`reports/phase4/feature_importance_analysis.csv`](../../reports/phase4/feature_importance_analysis.csv)) provides insight into the empirical associations captured by the models:

| Feature Name | Family | ElasticNet Coef (Peer) | ExtraTrees MDI | ExtraTrees Permutation RMSE Drop | Interpretation & Context |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `lag1_temp_mean` | Historical Weather | **-0.147440** | 0.032452 | -0.011982 | Conditional predictive association; negative weight in linear component. |
| `lag1_temp_max` | Historical Weather | 0.000000 | 0.037412 | +0.004880 | Lagged peak daytime ambient temperature proxy. |
| `lag1_temp_min` | Historical Weather | **-0.026643** | **0.045676** | **+0.068780** | Predictive feature importance in tree ensemble; not physical causation. |
| `lag1_temp_range` | Historical Weather | 0.000000 | 0.024876 | +0.003702 | Diurnal ambient range from prior day ($T_{max} - T_{min}$). |
| `lag1_rh_mean` | Historical Weather | **-0.084707** | 0.024006 | -0.008907 | Prior-day relative humidity predictive feature. |

> [!NOTE]
> **Scientific Qualification:**
> - The negative ElasticNet coefficient for `lag1_temp_mean` indicates that, holding other model inputs constant, higher prior-day ambient temperatures are conditionally associated with lower predicted specific yield in this historical dataset. This is a statistical predictive association, **not causal proof** of a specific semiconductor bandgap loss.
> - The ExtraTrees permutation importance indicates predictive utility within the tree ensemble, **not physical causation**.
> - All four temperature features are **lagged ambient-air measurements from day $t-1$**. The model receives **zero contemporaneous ($t$) ambient measurements** and **zero contemporaneous module or cell temperature measurements**.

---

## 3. UNISOLAR Temperature & Meteorological Data Availability Audit

A forensic inspection of the raw and processed UNISOLAR dataset files ([`data/raw/unisolar/Weather_Data_reordered_all.csv`](../../data/raw/unisolar/Weather_Data_reordered_all.csv), [`data/raw/unisolar/Solar_Site_Details.csv`](../../data/raw/unisolar/Solar_Site_Details.csv), and [`data/processed/unisolar/peer_cohort/features.csv`](../../data/processed/unisolar/peer_cohort/features.csv)) was performed:

### 3.1 Meteorological Variable Availability Table

| Variable Name | Raw Source Column | Semantic Definition | Documented Units | Campus 1 Coverage (Peer Cohort) | Measurement Quality & Classification | Usable for Method B? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Air Temperature** | `AirTemperature` | Ambient dry-bulb air temperature | °C | 81.74% (14,795 missing of 81,017 15-min rows) | Weather station measurement. Contains 18.26% missing intervals. | Partial (as ambient driver only) |
| **Apparent Temperature** | `ApparentTemperature` | Perceived ambient heat index | °C | 81.74% (14,795 missing of 81,017 15-min rows) | Derived biometeorological metric. | **No** (Not a PV driver) |
| **Dew Point Temperature** | `DewPointTemperature` | Dew point temperature | °C | 81.74% (14,795 missing of 81,017 15-min rows) | Derived moisture proxy. | **No** |
| **Relative Humidity** | `RelativeHumidity` | Ambient relative humidity | % | 81.74% (14,795 missing of 81,017 15-min rows) | Weather station hygrometer. | **No** |
| **Wind Speed** | `WindSpeed` | Horizontal wind velocity | m/s | 63.35% (29,690 missing of 81,017 15-min rows) | Severe missingness (36.65% missing). | **No** (High missingness) |
| **Wind Direction** | `WindDirection` | Wind direction azimuth | degrees | 63.35% (29,690 missing of 81,017 15-min rows) | Weather station anemometer. | **No** |
| **Module Temperature** | *None* | Back-of-module temperature ($T_{mod}$) | °C | **0.0% (UNAVAILABLE)** | **Zero physical sensors deployed.** Never measured in UNISOLAR. | **NO (ABSENT)** |
| **Cell Temperature** | *None* | PV junction temperature ($T_{cell}$) | °C | **0.0% (UNAVAILABLE)** | **Zero physical sensors deployed.** Never measured in UNISOLAR. | **NO (ABSENT)** |
| **POA Irradiance** | *None* | Plane-of-array irradiance ($G_{POA}$) | $\text{W/m}^2$ | **0.0% (UNAVAILABLE)** | **Zero tilted pyranometers deployed.** | **NO (ABSENT)** |
| **Global Horizontal Irradiance** | *None* | Terrestrial GHI ($G_{GHI}$) | $\text{W/m}^2$ | **0.0% (UNAVAILABLE)** | **Zero horizontal pyranometers deployed.** | **NO (ABSENT)** |
| **Extraterrestrial Radiation** | `extraterrestrial_radiation_h0` | Top-of-atmosphere insolation ($H_0$) | $\text{kWh/m}^2/\text{day}$ | 100% (Derived) | **Deterministic astronomical formula (NOAA).** Measures radiation outside Earth's atmosphere; ignores clouds, atmosphere, and array tilt. | **NO** (Not surface irradiance) |

> [!IMPORTANT]
> **Source Clarifications:**
> - The source column `IRRADIATION` exists **exclusively** in the synthetic Kaggle benchmark dataset (`data/raw/archive/Plant_1_Weather_Sensor_Data.csv`), which originates from a utility-scale ground-mount plant in India. It is **completely absent** from the UNISOLAR rooftop dataset in Melbourne.
> - Statements confirming feature availability apply **strictly to the prepared UNISOLAR peer-cohort historical feature dataset** (`data/processed/unisolar/peer_cohort/features.csv`). They do **not** imply that all 29 features can be generated for an arbitrary prospective roof, which remains blocked under B-2 due to unmeasured operational lag features.

---

## 4. Phase 6 Catalogue Temperature Specification Audit

An audit of the frozen Phase 6 catalogue ([`configs/panels_catalogue.csv`](../../configs/panels_catalogue.csv)) was conducted across all 12 modules:

### 4.1 Catalogue Temperature Parameters

| Panel ID | Manufacturer & Model | Cell Technology | Rated $P_{mp}$ (Wp) | $\gamma_{Pmax}$ (%/°C) | NOCT (°C) | NMOT (°C) | Provenance Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `PNL-TRINA-330W` | Trina 330W (TSM-330PD14) | Polycrystalline | 330.0 | **-0.41** | **44.0** | *null* | Text-extracted specification summary |
| `PNL-TRINA-310W` | Trina 310W (TSM-310DD05A.08) | Polycrystalline | 310.0 | **-0.39** | **44.0** | *null* | Text-extracted specification summary |
| `PNL-SUNPOWER-435W` | SunPower SPR-E20-435-COM | IBC Mono | 435.0 | **-0.35** | **45.0** | *null* | Text-extracted specification summary |
| `PNL-CANADIAN-445W` | Canadian Solar HiKu CS3W-445MS | Mono PERC | 445.0 | **-0.34** | *null* | **41.0** | Text-extracted specification summary |
| `PNL-CANADIAN-BIFI-575W` | Canadian Solar TOPBiHiKu6 CS6W-575TB | N-type TOPCon | 575.0 | **-0.29** | *null* | **41.0** | Text-extracted specification summary |
| `PNL-JINKO-430W` | Jinko Tiger Neo JKM430N-54HL4-V | N-type TOPCon | 430.0 | **-0.29** | **45.0** | *null* | Text-extracted specification summary |
| `PNL-TRINA-VERTEX-440W` | Trina Vertex S+ TSM-440NEG9R.28 | N-type TOPCon | 440.0 | **-0.29** | **43.0** | *null* | Text-extracted specification summary |
| `PNL-REC-ALPHA-420W` | REC Alpha Pure-R REC420AA Pure-R | Heterojunction (HJT) | 420.0 | **-0.24** | *null* | **44.0** | Text-extracted specification summary |
| `PNL-FIRSTSOLAR-460W` | First Solar Series 6 Plus FS-6460 | Thin-film CdTe | 460.0 | **-0.32** | *null* | **45.0** | Text-extracted specification summary |
| `PNL-WAAREE-540W` | Waaree Bi-55-540 (Ahnay Series) | Mono PERC | 540.0 | **-0.34** | **43.0** | *null* | Text-extracted specification summary |
| `PNL-MAXEON-400W` | Maxeon 3 SPR-MAX3-400 | IBC Mono | 400.0 | **-0.29** | **45.0** | *null* | Text-extracted specification summary |
| `PNL-LONGI-580W` | LONGi Hi-MO 7 LR5-72HGD-580M | N-type TOPCon | 580.0 | **-0.28** | **45.0** | *null* | Text-extracted specification summary |

### 4.2 Technical Distinction: NOCT vs. NMOT
- **NOCT (Nominal Operating Cell Temperature):** Defined under standard IEC 61215-2. Measured at $800\text{ W/m}^2$ irradiance, $20^\circ\text{C}$ ambient temperature, $1\text{ m/s}$ wind speed, and open-circuit electrical conditions ($P=0$, where all absorbed solar energy is dissipated as heat).
- **NMOT (Nominal Module Operating Temperature):** Defined under modern standard IEC 61215:2016. Measured at identical environmental conditions ($800\text{ W/m}^2$, $20^\circ\text{C}$, $1\text{ m/s}$ wind), but operating at the **Maximum Power Point (MPP)** where electrical power is extracted from the module.
- **Non-Interchangeability:** NOCT and NMOT represent distinct measurement protocols and electrical loading conditions. They **cannot be treated as interchangeable values**. Comparing NOCT from one manufacturer's module directly against NMOT from another manufacturer does not establish a valid physical temperature differential.
- **Provenance Limitation:** All 12 datasheets are local 1-page PDF text compilations. Source URLs show severe link rot (9/12 HTTP 404), preventing independent web re-verification.

---

## 5. Evaluation of Method A — Existing Model Baseline

### 5.1 Formulation
Method A represents the empirical baseline delivered through the Phase 8 Stage 2 and Stage 3 interfaces:
$$\hat{Y}_{A, i} = f_{\text{Phase5}}(X_i, kWp) \quad [\text{kWh/kWp/day}]$$
$$E_{A, i} = \text{round}(\hat{Y}_{A, i} \times kWp, 6) \quad [\text{kWh/day}]$$

### 5.2 Scope & Operational Governance
1. **Active Empirical Baseline for Supported Historical Replay:** Method A serves as the active empirical baseline strictly for evaluating historical replay scenarios on the supported UNISOLAR Peer Cohort dataset.
2. **Offline Evaluated Artifacts:** The Phase 5 models are offline evaluated research artifacts, **not production-deployed models**.
3. **Generalization Scope Limits:** The reported held-out evaluation covers **March 1 to April 23, 2022** ($N = 1,128$ site-days) on Melbourne commercial rooftops. It does **not** establish predictive validity or generalization to unseen geographic regions, different climatic regimes, or different operating fleets.
4. **Preserved Governance Boundaries:** Method A does **not** resolve the unverified AC/DC energy basis under Blocking Issue B-1 (`energy_basis = "UNVERIFIED"`). Prospective roof estimation remains strictly blocked under Blocking Issue B-2 (`PREDICTION_PENDING_LAG_POLICY`).

---

## 6. Evaluation of Method B — Additional Module-Temperature Correction

### 6.1 Theoretical Physical Formulation
The standard instantaneous DC thermal power formulation is:
$$P_{DC}(T_{cell}) = P_{STC} \cdot \left(\frac{G_{POA}}{1000}\right) \cdot \left[1 + \frac{\gamma}{100} \cdot (T_{cell} - 25)\right]$$
where $T_{cell}$ is typically estimated using NOCT or heat balance:
$$T_{cell} \approx T_{ambient} + \left(\frac{\text{NOCT} - 20}{800}\right) \cdot G_{POA}$$

### 6.2 Material and Unquantified Double-Counting Risk
Applying an external factor $[1 + \frac{\gamma}{100}(T_{cell} - 25)]$ directly to $\hat{Y}_A$ is scientifically unsupportable:
1. **Timescale Mismatch:** The thermal correction is an *instantaneous power* equation ($P$ in kW). Phase 5 predicts *daily integrated energy* ($E$ in kWh). Applying daily-average temperatures to a linear power equation introduces mathematical aggregation error.
2. **Material and Unquantified Double-Counting Risk:** The Phase 5 model was trained on historical daily generation of operating arrays and already incorporates lagged ambient-temperature features. Its predictions reflect operational specific yield under prevailing weather. Applying an additional negative temperature adjustment introduces an unquantified risk of double-counting temperature effects, penalizing an output that already incorporates operational thermal suppression.
3. **Absence of Calibration Evidence:** A differential formulation ($E_B = E_A [1 + \frac{\gamma_{cand} - \gamma_{base}}{100}(\bar{T}_{cell} - 25)]$) cannot be implemented because:
   - The training fleet's baseline temperature response ($\gamma_{base}$) is uncalibrated and heterogeneous across sites.
   - The existing model's internal thermal response has not been independently isolated or quantified.
   - Operating cell temperature ($\bar{T}_{cell}$) cannot be calculated due to the complete absence of $G_{POA}$ and high wind speed missingness.

---

## 7. Method A versus Method B Comparison

| Evaluation Criterion | Method A (Existing Model Baseline) | Method B (Additional Module Temperature Correction) |
| :--- | :--- | :--- |
| **Prediction Source** | Frozen Phase 5 Ensemble Predictor via Stage 2/3 interfaces | Existing model prediction multiplied by physical temperature factor |
| **Additional Temperature Model** | **None** (statistical associations in training data) | Requires cell temperature heat-balance model ($T_{cell} = f(T_{amb}, G_{POA}, v)$) |
| **Catalogue Coefficient ($\gamma$)** | Not required | **Required** ($\gamma_{Pmax}$ from catalogue) |
| **Cell / Module Temperature Input** | Not required | **Required** (Defensible cell temperature) |
| **Calibration Status** | Offline evaluated on 1,128 held-out historical test rows | **Uncalibrated** (no fleet baseline $\gamma_{base}$ established) |
| **Double-Counting Risk** | Baseline reference | **Material and unquantified risk** of compounding thermal losses |
| **Telemetry Data Feasibility** | Supported on prepared historical UNISOLAR dataset | **Infeasible** ($G_{POA}$, $T_{mod}$, $T_{cell}$ missing) |
| **Scientific Defensibility** | Empirical interpolation on historical peer cohort | Unjustified without baseline decoupling and surface irradiance |
| **Implementation Readiness** | **ACTIVE EMPIRICAL BASELINE FOR SUPPORTED HISTORICAL REPLAY** | **DISABLED / EXPERIMENTAL ONLY** |

---

## 8. Leakage-Safe Validation Strategy for Future Research

If high-resolution plane-of-array pyranometers and back-of-module thermocouples are deployed in a future research phase, any experimental Method B investigation must adhere to the following leakage-safe validation protocol:

1. **Strict Chronological Boundary:**
   - **Calibration Window:** Pre-test observations only ($\le \text{2022-02-28}$, $N = 5,328$ site-days).
   - **Quarantined Test Window:** Strictly reserved for final evaluation ($\text{2022-03-01}$ to $\text{2022-04-23}$, $N = 1,128$ site-days). Zero parameter tuning or coefficient calibration on test data.
2. **Site-Level Grouping:**
   - GroupKFold cross-validation across the 22 peer sites to ensure models do not overfit site-specific microclimates.
3. **Stratified Thermal Regime Evaluation:**
   Model performance must be evaluated separately across ambient temperature tiers (<15°C, 15–25°C, 25–35°C, $\ge$35°C).
4. **Mandatory Acceptance Criteria:**
   Method B may only be accepted over Method A if:
   - Overall test RMSE decreases by $> 2\%$ relative to Method A.
   - Mean Bias Error (MBE) in extreme temperature regimes is demonstrably reduced without degrading mild-regime performance.
   - Double-counting decoupling is mathematically proven against ground truth.

---

## 9. Data & Calibration Gaps Summary

1. **Gap G-1: Missing In-Situ Solar Irradiance:** No pyranometer data exists in UNISOLAR. Without surface irradiance ($G_{POA}$), module operating temperature cannot be modeled.
2. **Gap G-2: Missing Module/Cell Temperature Telemetry:** No thermocouples were installed on the UNISOLAR arrays. Module operating temperature cannot be ground-truthed.
3. **Gap G-3: Unrecorded Array Tilt and Azimuth:** Roof-pitch tilt and compass azimuth were not recorded for the 22 training sites in `Solar_Site_Details.csv`.
4. **Gap G-4: Uncalibrated Fleet Baseline $\gamma_{\text{base}}$:** The training fleet consists of multiple module technologies (Trina 310W, Trina 330W, SunPower 435W). Decoupling candidate panel response from fleet response is mathematically indeterminate.
5. **Gap G-5: Wind Speed Telemetry Missingness:** 36.65% of Campus 1 wind speed observations are missing.

---

## 10. Implementation-Readiness Decision

### Final Audit Determination:
**`STAGE_4_EVALUATION_COMPLETE_METHOD_B_DISABLED`**

- **Method A:** Formally confirmed and retained as the **active empirical baseline for supported historical replay**.
- **Method B:** Formally designated as **EXPERIMENTAL and DISABLED**.
- **Authorization Status:** No additional temperature correction is authorized.
- **Implementation Status:** Zero temperature correction code has been added to [`src/energy_economics/energy_engine.py`](../../src/energy_economics/energy_engine.py). All Stage 3 daily energy arithmetic, unit types, and boundary blocks remain intact and unaltered.

---

## 11. Recommended Next Steps

1. **Preserve Stage 3 Engine Unaltered:** Retain [`Phase8EnergyEstimationEngine`](../../src/energy_economics/energy_engine.py) with Method A as the baseline.
2. **Transition to Stage 5:** Proceed to **Phase 8 Stage 5: Annualization and Lifetime Energy**, focusing on calendar coverage rules, leap-year handling, and the distinction between observed-period aggregation and representative-year scenarios.
3. **Maintain Blocking Governance:** Ensure Blocking Issues B-1 (unverified energy basis) and B-2 (prospective roofs blocked pending lag policy) remain strictly enforced.
