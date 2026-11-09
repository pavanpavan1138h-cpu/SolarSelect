# SolarSelect — Phase 2: EDA 2.0 Comprehensive Documentation

**Directory:** `notebooks/eda2.0/`  
**Phase:** Phase 2 — Exploratory Data Analysis & Empirical Data Understanding  
**Status:** Phase 2 (Tasks 1–6) Formally Completed, Verified, and Closed (0 Errors Across All Notebooks)

---

## 1. Directory Overview & Organization

The `notebooks/eda2.0/` directory contains the complete exploratory data analysis suite for the SolarSelect MLOps project, organized into five modular, self-contained notebooks by analytical purpose:

```text
notebooks/eda2.0/
├── README.md                                                   # Master documentation & execution guide (this file)
│
├── dataset_quality_and_completeness.ipynb                      # Master notebook for data quality, missingness, and scale
├── solar_generation_distributions_and_physical_analysis.ipynb  # Master notebook for distributions, DC/AC scaling, and weather
├── temporal_seasonal_and_site_analysis.ipynb                   # Master notebook for temporal, seasonal, and site-wise analysis
├── feature_relationships_and_target_feasibility.ipynb          # Master notebook for features, collinearity, targets & leakage
├── consolidated_eda_findings_and_dataset_selection.ipynb       # Phase 2 closure notebook: consolidated findings & dataset strategy
│
├── figures/                                                    # Dedicated directory for publication-grade visualisations
│   ├── missing_value_percentages_across_datasets.png           # [Quality] Missing value percentages across all 8 datasets
│   ├── temporal_timeline_coverage_comparison.png               # [Quality] Timeline span comparison (Kaggle vs UNISOLAR)
│   ├── solar_power_and_generation_distributions.png            # [Distribution] AC/DC power and energy interval distributions
│   ├── plant1_vs_plant2_dc_ac_ratio_verification.png           # [Distribution] DC/AC operating ratio histograms (10x audit)
│   ├── diurnal_solar_generation_hourly_profiles.png            # [Distribution] Hourly diurnal profiles across plants
│   ├── unisolar_nighttime_generation_investigation.png         # [Distribution] Night generation breakdown (Site 27 quantization)
│   ├── ambient_and_module_weather_distributions.png            # [Weather] Temperature, irradiance, and humidity distributions
│   ├── weather_vs_solar_generation_correlations.png            # [Weather] Bivariate weather-power correlation scatter plots
│   ├── unisolar_capacity_vs_generation_scaling_audit.png       # [Capacity] Ground-truth capacity vs peak generation audit
│   ├── temporal_intraday_and_weekday_invariance.png            # [Temporal] Ramp rates, daily yield spread & daily weekday/weekend test
│   ├── unisolar_monthly_and_seasonal_trends.png                # [Seasonal] Fleet vs fixed-cohort monthly & seasonal profiles
│   ├── unisolar_sitewise_capacity_normalized_yield.png         # [Site-Wise] Corrected specific yield (kWh/kWp/d) & first-observation dates
│   ├── unisolar_temporal_reliability_and_gap_analysis.png      # [Reliability] Reconciled gap durations & core-coverage daily energy check
│   ├── feature_correlation_and_collinearity_matrices.png       # [Task 5] Daytime correlation heatmaps & scatter dynamics
│   ├── generation_autocorrelation_and_time_features.png        # [Task 5] Autocorrelation (ACF/PACF) & cyclical hour encoding
│   ├── target_feasibility_and_cross_dataset_comparison.png     # [Task 5] Target distributions & cross-dataset feasibility matrix
│   └── phase2_consolidated_dataset_selection_and_handover.png  # [Task 6] Consolidated architecture, targets & handover hierarchy
│
└── archive/                                                    # Archived original monolithic notebook
    └── eda2.0_data_quality_and_statistical_analysis.ipynb      # Preserved 56-cell monolithic notebook (for historical audit)
```

---

## 2. Notebook Summaries, Methodology & Key Findings

### 1. [Dataset Quality and Completeness (`dataset_quality_and_completeness.ipynb`)](dataset_quality_and_completeness.ipynb)
- **Focus:** Data schema verification, missing-value audits, duplicate detection, primary key validation, temporal continuity, and scale reconciliation (20 cells).
- **Key Findings:**
  * **Kaggle Datasets (P1 & P2):** $0$ missing values, $0$ duplicate records; primary composite keys `(PLANT_ID, DATE_TIME, SOURCE_KEY)` are $100\%$ unique. Plant 2 exhibits a $27.7\%$ inverter dropout rate ($904$ timestamps with $<22$ inverters).
  * **UNISOLAR Weather Scale:** Reconciled $371,769$ physical data rows across 5 campuses vs. $264,656$ valid temperature observations ($28.81\%$ null) and $208,879$ valid wind observations ($43.81\%$ null).
  * **UNISOLAR Monthly Summary Scale:** Reconciled $1,176$ physical data rows ($42\text{ sites} \times 28\text{ months}$), with $976$ valid and $200$ null entries ($17.01\%$ null).
  * **UNISOLAR Capacity Metadata:** Reconciled $40.48\%$ missingness ($17$ of $42$ sites missing $\text{kW}_p$ in `Solar_Site_Details.csv`; 25 Campus 1 sites have documented capacity, while Campuses 2–5 and Campus 1 Sites 28–29 lack $\text{kW}_p$).

### 2. [Solar Generation Distributions and Physical Analysis (`solar_generation_distributions_and_physical_analysis.ipynb`)](solar_generation_distributions_and_physical_analysis.ipynb)
- **Focus:** 8-number statistical summaries, generation and weather distributions, DC/AC operating ratio verification, nighttime generation mechanisms, capacity scaling, and physical plausibility (38 cells).
- **Key Findings:**
  * **DC/AC Scaling Discrepancy:** Plant 1 has a systemic daytime median DC/AC ratio of **$10.2202$** ($\sigma = 0.0482$) across all 22 inverters; Plant 2 daytime median is **$1.0220$** ($\sigma = 0.0053$). Ratio between plant medians is exactly **$10.000$** (plausible decimal sensor scaling discrepancy; raw values preserved).
  * **UNISOLAR Nighttime Records:** All 177 non-zero night records (23:00 to 03:00) audited: Site 27 accounts for $153$ records ($86.4\%$, plausible discrete meter pulse resolution on a $539.8\text{ kW}_p$ system); Site 26 accounts for $23$ records ($13.0\%$, plausible logger clock shift); Site 3 accounts for $1$ record ($8.72\text{ kWh}$, plausible buffer dump).
  * **Weather-Power Relationship:** `IRRADIATION` (irradiance-related measurement) directly drives generation ($r = 0.989$); ambient and module temperatures correlate positively with power because solar irradiance heats panels while driving photocurrent ($dP/dT < 0$ physically).
  * **Peak Capacity Scaling:** Verified $0$ negative values; Site 19 peak interval is $42.22\text{ kWh}$ ($492.06\%$ of documented STC) and Site 24 peak interval is $17.78\text{ kWh}$ ($176.66\%$ of documented STC).

### 3. [Temporal, Seasonal, and Site-Wise Analysis (`temporal_seasonal_and_site_analysis.ipynb`)](temporal_seasonal_and_site_analysis.ipynb)
- **Focus:** Value-encoding and valid site-day methodology, 15-minute ramp rates, daily-unit and paired-week weekday/weekend tests, coordinate-verified fixed-cohort seasonal analysis, corrected capacity-normalized specific yield ($Y_f$), qualified first-observation dates, provisional site concern audits (Sites 16, 19, 24, 39), and temporal reliability (32 cells).
- **Key Findings:**
  * **Value-Encoding & Valid Site-Day Definition:** `Solar_Energy_Generation.csv` contains $0$ exact zeros and $0$ values $<0.1000\text{ kWh}$; night/sub-threshold intervals are stored as `NaN` ($56.23\%$). Specific yield must be computed using valid site-day energy sums divided by $\text{kW}_p$, avoiding the $2.31\times$ distortion of $\text{mean}_{\text{valid}} \times 96 / \text{kW}_p$.
  * **Weekday vs. Weekend Analysis:** In UNISOLAR Campus 1, daytime mean generation is $6.866\text{ kWh}$ on weekdays vs $6.881\text{ kWh}$ on weekends (naive interval $p = 0.5937$; daily AR(1)-adjusted Welch $p = 0.1055$; paired within-week $t$-test across 48 weeks $p = 0.0895$). Calibrated conclusion: *"No statistically significant weekday–weekend difference was detected in the analysed sample. This does not establish the absence of operational or scheduling effects."*
  * **Geographic Coordinates & Fixed-Cohort Seasonality:** Coordinates confirm all $42$ sites are in Victoria, Australia ($-37.72^\circ$ to $-34.21^\circ\text{ S}$). On the consistent 37-site cohort (`2021-05` to `2022-04`), summer/winter daily energy ratio is **$2.36\times–2.55\times$**, within-site median ratio is **$2.46\times$**, and median specific yield ($24$ $\text{kW}_p$ sites) is **$2.41\times$** ($4.328$ vs. $1.795\text{ kWh}/\text{kW}_p/\text{day}$).
  * **Site-Wise Peer Baseline:** Peer median specific yield across 23 Campus 1 documented sites (excl. 19 & 24) is **$2.94\text{ kWh}/\text{kW}_p/\text{day}$** (IQR $[2.86, 3.12]$). Site 16 ($1.68$) and Site 39 ($2.07$) dates are reported strictly as first observed dates in the dataset; Site 19 ($18.21$) and Site 24 ($6.08$) explanations remain plausible hypotheses.

### 4. [Feature Relationships and Target Feasibility (`feature_relationships_and_target_feasibility.ipynb`)](feature_relationships_and_target_feasibility.ipynb)
- **Focus:** Feature suitability classification, multicollinearity diagnostics, time-based feature feasibility, target technical supportability, cross-dataset compatibility, and data leakage risk register (19 cells).
- **Key Findings:**
  * **Feature Taxonomy:** Formulated complete suitability matrix across all 26 variables. Classified predictive features (`IRRADIATION`, `AMBIENT_TEMPERATURE`, `AirTemperature`, `RelativeHumidity`, `WindSpeed`), static metadata (`kWp`, `lat`, `Lon`, `Panel`, `Inverter`), targets (`AC_POWER`, `SolarGeneration`), and strictly excluded features (`DAILY_YIELD`, `TOTAL_YIELD`, `DC_POWER`, `ApparentTemperature`).
  * **Direct vs. Proxy Weather Coupling:** Kaggle `IRRADIATION` (irradiance-related measurement) drives AC power at **$r = 0.9846$**. UNISOLAR lacks an on-site pyranometer, resulting in modest proxy weather correlations (`AirTemperature` $r = +0.1939$, `RelativeHumidity` $r = -0.2284$).
  * **Multicollinearity:** `AirTemperature` and `ApparentTemperature` correlate at **$r = 0.9641$**, and `RelativeHumidity` correlates with `AirTemperature` at **$r = -0.7268$**. `ApparentTemperature` and `DewPointTemperature` are redundant and must be excluded.
  * **Autoregressive Dynamics:** Extreme short-term persistence (Lag 1 $r > 0.92$, Lag 2 $r > 0.85$, Lag 4 $r > 0.73$) dominates up to 2 hours, cutting off sharply in PACF. Lag 96 ($24\text{h}$) captures astronomical diurnal cyclicity ($r \approx 0.60–0.74$). Cyclical encoding $\sin(2\pi h / 24)$ and $\cos(2\pi h / 24)$ eliminates midnight boundary discontinuity.
  * **Target Technical Feasibility:**
    - *Kaggle:* Fully supports short-horizon power forecasting (`AC_POWER` in kW) and derived energy ($E_{15\text{m}} = \text{AC} \times 0.25$). **Cannot support capacity-normalized specific yield ($Y_f$)** due to zero documented $\text{kW}_p$ ratings.
    - *UNISOLAR:* Target variable availability (`SolarGeneration` in kWh) is recorded across 42 sites, but observation quality is constrained by high missingness ($56.23\%$, $1,536,301$ nulls); absolute energy forecasting is feasible with observation filtering, coverage assessment, and missingness treatment (sites vary in temporal suitability). **Daily specific yield ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$)** is supported strictly for the 24 documented Campus 1 cohort sites in the verified 12-month fixed-cohort window (`2021-05` to `2022-04`, 1 complete annual cycle; distinguished from the broader 28-month dataset) on verified valid site-days.
  * **Cross-Dataset Incompatibility:** Proved that joint tabular training across Kaggle and UNISOLAR is scientifically invalid due to target mismatch (instantaneous kW vs integrated kWh), severe covariate shift (measured on-site irradiance vs zero irradiance), unrecorded capacity, and geographic/climate disparity.
  * **Data Leakage Register:** Established 7 formal modeling risks (cumulative counters, random temporal shuffling, autoregressive lookahead, silent zero-imputation, provisional site data-quality concerns, temperature multicollinearity, and inverter availability masking) with mandatory mitigation protocols, recommending separate anomaly handling or sensitivity analysis for Sites 19 and 24 in Phase 3 rather than finalized exclusion.

### 5. [Consolidated EDA Findings and Dataset Selection (`consolidated_eda_findings_and_dataset_selection.ipynb`)](consolidated_eda_findings_and_dataset_selection.ipynb)
- **Focus:** Synthesis of Tasks 1–5, formal dataset-role selection, feature taxonomy, target feasibility comparison, 14-item limitations & risk register, and 14-gate Phase 3 technical handover (17 cells).
- **Key Findings & Decisions:**
  * **Dataset Role Strategy:**
    - *Primary Benchmark (Layer A):* **UNISOLAR Campus 1 Consistent Cohort (24 documented-$\text{kW}_p$ sites, May 2021 – April 2022, 12-month complete annual cycle)** for climate-conditioned specific yield forecasting ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$).
    - *Secondary Benchmark (Layer A):* **Kaggle Plants 1 & 2** as a dedicated high-frequency physical baseline for short-horizon inverter power forecasting (kW) under direct on-site `IRRADIATION`.
    - *Cross-Dataset Prohibition:* Tabular pooling across Kaggle and UNISOLAR is strictly prohibited due to target semantic mismatch (kW vs. kWh), severe covariate shift, unrecorded capacity, and disparate climates.
  * **Feature Taxonomy:** Formally partitioned all 26 variables into Recommended Predictive (e.g. `IRRADIATION`, `AirTemperature`, `RelativeHumidity`, cyclical hour, ephemeris), Conditional/Cautionary (e.g. `WindSpeed`, `MODULE_TEMPERATURE`), Excluded (e.g. `DAILY_YIELD`, `TOTAL_YIELD`, `DC_POWER`, `ApparentTemperature`), and Static Metadata/Identifiers (`SiteKey`, `kWp`, hardware strings).
  * **Target Feasibility Hierarchy:** Daily specific yield ($Y_f$) on valid site-days selected as primary target for Layer A (directly drives Layer B panel sizing); instantaneous AC power retained as secondary benchmark target.
  * **Consolidated 14-Item Risk Register:** Comprehensive catalog spanning generation missingness ($56.23\%$), capacity metadata absence ($40.48\%$), regional weather gaps, Kaggle 34-day duration, Plant 2 dropouts ($27.7\%$) and resets, Site 19/24 anomalies ($18.21$ and $6.08\text{ kWh}/\text{kW}_p/\text{d}$), Site 16/39 low yields, absence of on-site irradiance in UNISOLAR, cross-dataset incompatibility, temporal leakage, and climatological uncertainty.
  * **Phase 3 Handover:** Formalized 14 technical decision gates cleanly separating resolved EDA determinations from Phase 3 pipeline implementation responsibilities.

---

## 3. Epistemic Calibration Table (Tasks 1–6)

| Domain | Finding / Observation | Epistemic Classification | Evidence & Operational Impact |
| :--- | :--- | :--- | :--- |
| **Kaggle Irradiance Coupling** | Daytime `IRRADIATION` (irradiance-related measurement) correlates with AC power at $r = 0.9846$ (P1) and $r = 0.9403$ (P2) | **Calculated result** | Near-perfect photoelectric driver; power forecasting models direct photo-conversion and thermal derating. |
| **UNISOLAR Proxy Weather** | Air temp correlates with generation at $r = +0.1939$; rel humidity at $r = -0.2284$ | **Calculated result** / **Supported interpretation** | Modest association reflects common diurnal solar forcing; absence of on-site irradiance requires heavy reliance on time features and NWP forecasts. |
| **Weather Multicollinearity** | AirTemperature and ApparentTemperature correlate at $r = 0.9641$ | **Calculated result** | Severe collinearity; ApparentTemperature is redundant and must be excluded. |
| **Autoregressive Persistence** | Lag 1 (15m) $r > 0.92$, Lag 2 $r > 0.85$, Lag 4 $r > 0.73$, PACF cuts off after lag 2 | **Calculated result** | Powerful for nowcasting ($h \le 2\text{h}$); requires strict horizon-lag constraints ($\tau \ge h$) for day-ahead forecasting. |
| **Kaggle Target Limitation** | 0 documented DC $\text{kW}_p$ ratings across all 44 inverters | **Verified observation** | Kaggle cannot support capacity-normalized specific yield ($Y_f$) without ungrounded synthetic assumptions. |
| **UNISOLAR Target Support** | Specific yield ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$) supportable for 24 cohort sites on valid site-days (12m cohort: `2021-05` to `2022-04`, 1 complete annual cycle); absolute energy ($E_{15\text{m}}$) availability across 42 sites qualified by $56.23\%$ missingness and site coverage | **Calculated result** | Defensible ground truth for Layer A core objective; Campuses 2–5 ($15$ sites) lack capacity metadata; absolute energy requires filtering and missingness treatment. |
| **Cross-Dataset Compatibility** | Joint tabular training of Kaggle and UNISOLAR is scientifically invalid | **Supported interpretation** | Target mismatch (kW vs kWh), covariate shift (irradiance present vs absent), disparate climates and horizons dictate separate benchmarks. |
| **Leakage Constraints** | Cumulative counters (`DAILY_YIELD`, `TOTAL_YIELD`) and random temporal splits cause fatal leakage | **Calculated result** / **Methodological rule** | Counters must be permanently dropped; chronological or purged time-series CV is mandatory. |
| **Provisional Site Handling** | Sites 19 & 24 exhibit elevated specific yields ($18.21$ and $6.08\text{ kWh}/\text{kW}_p/\text{d}$) vs peer median ($2.94$) | **Calculated result** / **Methodological recommendation** | Feeder aggregation & underreported capacity remain plausible hypotheses; recommend Phase 3 sensitivity analysis rather than finalized exclusion. |

---

## 4. Execution Instructions

All five notebooks run independently from top to bottom:

```bash
cd notebooks/eda2.0
jupyter nbconvert --execute --inplace dataset_quality_and_completeness.ipynb
jupyter nbconvert --execute --inplace solar_generation_distributions_and_physical_analysis.ipynb
jupyter nbconvert --execute --inplace temporal_seasonal_and_site_analysis.ipynb
jupyter nbconvert --execute --inplace feature_relationships_and_target_feasibility.ipynb
jupyter nbconvert --execute --inplace consolidated_eda_findings_and_dataset_selection.ipynb
```

---

## 5. Phase 2 Formal Closure & Phase 3 Handover

Phase 2 (Exploratory Data Analysis) is formally completed and closed with the execution of `consolidated_eda_findings_and_dataset_selection.ipynb`.

**Technical Readiness Gate:**
- **Primary Modeling Target:** Daily specific yield ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$) on verified valid site-days.
- **Primary Training Cohort:** 24 documented-$\text{kW}_p$ sites on UNISOLAR Campus 1 over the 12-month fixed-cohort window (`2021-05` to `2022-04`).
- **Secondary Physical Testbed:** Kaggle Plants 1 & 2 for high-frequency short-horizon inverter power forecasting under on-site `IRRADIATION`.
- **Phase 3 Scope:** Proceed to **Phase 3 (Target Definition and Data Preparation)** upon approval. Zero raw data files were modified during Phase 2.
