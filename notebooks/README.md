# SolarSelect — Jupyter Notebooks Directory

This directory contains the standardized, modular Jupyter notebooks for the SolarSelect MLOps project.

> [!NOTE]
> For the complete architectural, mathematical, and data governance documentation, please consult the central [**Documentation Portal (`docs/`)**](../docs/README.md).

---

## Directory Structure

```text
notebooks/
├── README.md                                                   # Master notebook directory guide (this file)
│
├── data_inspection/
│   ├── dataset_inspection_and_source_verification.ipynb        # Master notebook for Phase 1 data inspection
│   ├── figures/
│   │   └── raw_dataset_dimensions_and_record_counts.png        # Dataset scale & dimensionality comparison
│   └── README.md                                               # Data inspection documentation & guide
│
├── eda2.0/
│   ├── README.md                                               # Comprehensive EDA 2.0 documentation & findings
│   ├── dataset_quality_and_completeness.ipynb                  # Quality audit: missingness, duplicates, and scale
│   ├── solar_generation_distributions_and_physical_analysis.ipynb # Statistical summaries, DC/AC scaling, and weather
│   ├── temporal_seasonal_and_site_analysis.ipynb               # Temporal dynamics, seasonal cycles, and site-wise yield
│   ├── feature_relationships_and_target_feasibility.ipynb      # Feature suitability, relationships, targets & leakage
│   ├── consolidated_eda_findings_and_dataset_selection.ipynb   # Phase 2 closure: consolidated findings, dataset roles & handover
│   │
│   ├── figures/                                                # Publication-grade analytical figures
│   │   ├── missing_value_percentages_across_datasets.png       # Missing value rates across datasets
│   │   ├── temporal_timeline_coverage_comparison.png           # Observation timeline spans (Kaggle vs UNISOLAR)
│   │   ├── solar_power_and_generation_distributions.png        # Generation & AC/DC power distributions
│   │   ├── plant1_vs_plant2_dc_ac_ratio_verification.png       # DC/AC ratio distributions in P1 vs P2 (10x audit)
│   │   ├── diurnal_solar_generation_hourly_profiles.png        # Hourly diurnal generation curves
│   │   ├── unisolar_nighttime_generation_investigation.png     # Nighttime generation breakdown (Site 27 quantization)
│   │   ├── ambient_and_module_weather_distributions.png        # Weather distributions across climates
│   │   ├── weather_vs_solar_generation_correlations.png        # Bivariate correlation scatter plots
│   │   ├── unisolar_capacity_vs_generation_scaling_audit.png   # Installed kWp vs observed peak generation
│   │   ├── temporal_intraday_and_weekday_invariance.png        # Ramp rates, daily yield spread & daily weekday/weekend test
│   │   ├── unisolar_monthly_and_seasonal_trends.png            # Fleet vs fixed-cohort monthly & seasonal profiles
│   │   ├── unisolar_sitewise_capacity_normalized_yield.png     # Corrected specific yield (kWh/kWp/d) & first-observation dates
│   │   ├── unisolar_temporal_reliability_and_gap_analysis.png  # Reconciled gap durations & core-coverage daily energy check
│   │   ├── feature_correlation_and_collinearity_matrices.png   # Feature correlation heatmaps & scatter dynamics
│   │   ├── generation_autocorrelation_and_time_features.png    # Autocorrelation (ACF/PACF) & cyclical hour encoding
│   │   ├── target_feasibility_and_cross_dataset_comparison.png # Target distributions & cross-dataset feasibility matrix
│   │   └── phase2_consolidated_dataset_selection_and_handover.png # Consolidated architecture, targets & handover hierarchy
│   │
│   └── archive/
│       └── eda2.0_data_quality_and_statistical_analysis.ipynb  # Preserved original 56-cell monolithic notebook
│
└── phase3/
    ├── README.md                                               # Phase 3 documentation & execution guide
    ├── target_definition_and_data_preparation.ipynb            # Target finalization, feature engineering & splits
    └── figures/
        └── phase3_data_preparation_and_splits_summary.png      # 4-panel preparation summary (pass rate, splits, features)
```

---

## Overview of Notebooks

1. [**Dataset Inspection and Source Verification (`notebooks/data_inspection/dataset_inspection_and_source_verification.ipynb`)**](data_inspection/dataset_inspection_and_source_verification.ipynb):
   - Covers all code and analysis performed during the initial data inspection and suitability audits in chronological order.
   - Evaluates the 4 original Kaggle files (`Plant_1_Generation_Data.csv`, `Plant_1_Weather_Sensor_Data.csv`, `Plant_2_Generation_Data.csv`, `Plant_2_Weather_Sensor_Data.csv`).
   - Audits inverter identifiers, weather stations, temporal ranges, and timestamp format conventions.
   - Investigates candidate multi-year datasets (UNISOLAR vs Cyprus PV).
   - Verifies UNISOLAR dataset download integrity in `data/raw/unisolar/`.
   - Performs a full raw schema, data type, and scale inspection across all 8 collected CSVs.

2. [**Dataset Quality and Completeness (`notebooks/eda2.0/dataset_quality_and_completeness.ipynb`)**](eda2.0/dataset_quality_and_completeness.ipynb):
   - Audits data quality, missing value percentages, duplicate rows, and primary composite keys across all 8 datasets.
   - Evaluates temporal continuity, 15-minute sampling intervals, and inverter dropout rates in Plant 2.
   - Contains the verified resolution of UNISOLAR Weather row counts ($371,769$ total physical rows across 5 campuses vs $264,656$ valid temperature observations).
   - Contains the verified resolution of Monthly Summary row counts ($1,176$ rows = 42 sites $\times$ 28 months).
   - Verifies UNISOLAR site capacity metadata missingness ($40.48\%$, $17$ of $42$ sites missing $kW_p$).

3. [**Solar Generation Distributions and Physical Analysis (`notebooks/eda2.0/solar_generation_distributions_and_physical_analysis.ipynb`)**](eda2.0/solar_generation_distributions_and_physical_analysis.ipynb):
   - Computes comprehensive 8-number statistical summaries for all numeric variables.
   - Analyzes generation distributions, nighttime zero inflation, and the $10\times$ DC scale discrepancy.
   - Audits Plant 1 vs Plant 2 DC/AC ratios (median $10.2202$ across 22 inverters; ratio to P2 is exactly $10.000$).
   - Resolves UNISOLAR nighttime generation mechanisms (Site 27 discrete $0.125\text{ kWh}$ pulse quantization vs Site 26 clock shifts vs Site 3 buffer dumps).
   - Examines diurnal generation profiles, weekday invariance, and weather distributions across climates.
   - Evaluates bivariate weather-generation correlations ($r = 0.989$ irradiance driving; proxy weather co-movement).
   - Audits capacity scaling across 25 UNISOLAR sites against theoretical STC limits, analyzing Site 19 ($492\%$) and Site 24 ($176\%$) anomalies.
   - Verifies physical plausibility (zero negative values, nighttime power drift, counter corruption).

4. [**Temporal, Seasonal, and Site-Wise Analysis (`notebooks/eda2.0/temporal_seasonal_and_site_analysis.ipynb`)**](eda2.0/temporal_seasonal_and_site_analysis.ipynb):
   - Establishes the UNISOLAR value-encoding diagnostic ($0$ exact zeros, $0$ values $<0.1000\text{ kWh}$, night and sub-threshold intervals stored as `NaN`) and a-priori **valid site-day** criterion ($96$ rows present and $\ge 26/28$ [$90\%$] non-null core 09:00–15:45 intervals; $20,809$ of $28,677$ site-days [$72.6\%$]).
   - Quantifies 15-minute ramp rates in Plant 1 (morning mean $+47.91\text{ kW}$, midday $-11.80\text{ kW}$ with $\text{SD} = 225.98\text{ kW}$, afternoon $-50.83\text{ kW}$) and inter-day yield spread ($1.65\times$ in P1, $1.83\times$ in P2).
   - Evaluates weekday vs. weekend generation at both the interval level and daily/weekly aggregated levels (AR(1)-adjusted Welch $p = 0.1055$, paired within-week $t$-test across 48 weeks $p = 0.0895$, Wilcoxon $p = 0.1537$): *"No statistically significant weekday–weekend difference was detected in the analysed sample. This does not establish the absence of operational or scheduling effects."*
   - Verifies all $42$ site coordinates ($-37.718^\circ$ to $-34.205^\circ\text{ S}$, $142.167^\circ$ to $146.849^\circ\text{ E}$, Victoria, Australia) and builds a fixed **37-site cohort** ($24$ with documented $\text{kW}_p$) over `2021-05` to `2022-04` ($\ge 10$ valid site-days in every month).
   - Distinguishes four seasonal metrics on `2021-05` to `2022-04`: fleet total MWh ($2.42\times$), mean per valid observation ($1.77\times$; $1.64\times$ over 28 months), cohort site-level daily energy ($2.36\times$ sum, $2.55\times$ median, $2.46\times$ within-site median), and cohort median specific yield $Y_f$ ($4.328$ vs. $1.795\text{ kWh}/\text{kW}_p/\text{day}$, **$2.41\times$**; $2.42\times$ excluding Sites 19 & 24).
   - Corrects the daily specific-yield calculation from $\text{mean}_{\text{valid}} \times 96 / \text{kW}_p$ ($2.31\times$ inflation) to valid site-day energy sums divided by $\text{kW}_p$: peer median across 23 documented-$\text{kW}_p$ sites (excl. 19 & 24) in `2021-05` to `2022-04` is **$2.94\text{ kWh}/\text{kW}_p/\text{day}$** (IQR $[2.86, 3.12]$).
   - Reports first observed generation dates (`2020-12-09 06:45` for Site 16, `2020-08-21 07:45` for Site 39) strictly as dataset entry dates, not confirmed commissioning dates; preserves feeder aggregation (Site 19, $Y_f = 18.21\text{ kWh}/\text{kW}_p/\text{d}$) and underreported DC capacity (Site 24, $Y_f = 6.08\text{ kWh}/\text{kW}_p/\text{d}$) strictly as **plausible hypotheses** and retains Sites 16, 19, 24, and 39 as **provisional data-quality concerns**.
   - Reconciles Campus 1 missing-row gap statistics ($n = 364$ gaps $>15\text{ min}$: mean $21.99\text{ h}$, median $27.25\text{ h}$, 75th pct $31.25\text{ h}$, max $47.00\text{ h} = 1.96\text{ d}$).

5. [**Feature Relationships and Target Feasibility (`notebooks/eda2.0/feature_relationships_and_target_feasibility.ipynb`)**](eda2.0/feature_relationships_and_target_feasibility.ipynb):
   - Comprehensive suitability classification of all 26 variables across Kaggle and UNISOLAR into predictive, target, metadata, and excluded categories.
   - Evaluates physical `IRRADIATION` (irradiance-related measurement) driving in Kaggle ($r = 0.9846$) vs. loose ambient temperature proxy coupling in UNISOLAR ($r = 0.1939$).
   - Diagnoses severe weather multicollinearity between `AirTemperature` and `ApparentTemperature` ($r = 0.9641$) and negative correlation with `RelativeHumidity` ($r = -0.7268$).
   - Quantifies autoregressive persistence (Lag 1 $r > 0.92$, Lag 2 $r > 0.85$, Lag 4 $r > 0.73$, PACF cutoff after lag 2), diurnal cyclicity (Lag 96 $r \approx 0.60–0.74$), and continuous cyclical hour $\sin / \cos$ transformation.
   - Audits target technical feasibility: proves Kaggle cannot support specific yield ($Y_f$) due to unrecorded nameplate capacity, while UNISOLAR Campus 1 cohort supports daily specific yield ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$) on verified valid site-days over a 12-month fixed-cohort window (`2021-05` to `2022-04`, 1 complete annual cycle; distinguished from the broader 28-month dataset). Fleet-wide absolute energy availability (`SolarGeneration` across 42 sites) is distinguished from observation quality ($56.23\%$ missing observations, $1,536,301$ nulls), requiring observation filtering and missingness treatment (sites vary in temporal suitability).
   - Proves joint tabular training across Kaggle and UNISOLAR is scientifically invalid due to semantic target mismatch (instantaneous kW vs interval kWh), severe covariate shift (measured on-site irradiance vs zero irradiance), and divergent climates/horizons.
   - Establishes a 7-item Data Leakage and Modelling Risk Register with mandatory mitigation protocols (dropping cumulative counters, enforcing chronological/purged splits, horizon-matched lags, valid-day filtering, and recommended Phase 3 sensitivity analysis for provisional data-quality sites).

6. [**Consolidated EDA Findings and Dataset Selection (`notebooks/eda2.0/consolidated_eda_findings_and_dataset_selection.ipynb`)**](eda2.0/consolidated_eda_findings_and_dataset_selection.ipynb):
   - Formally concludes and closes Phase 2 (Exploratory Data Analysis).
   - Consolidates verified empirical, physical, and temporal findings across Tasks 1–5 into an authoritative reference.
   - Formalizes dataset roles: UNISOLAR Campus 1 Consistent Cohort (24 documented-$\text{kW}_p$ sites, 12-month complete annual cycle `2021-05` to `2022-04`) as the Primary Benchmark for Layer A specific yield forecasting ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$); Kaggle Plants 1 & 2 as dedicated secondary benchmark for high-frequency physical power forecasting (kW) under on-site `IRRADIATION`.
   - Proves cross-dataset tabular pooling is scientifically invalid and strictly prohibited.
   - Classifies complete 26-variable feature taxonomy into Recommended Predictive, Conditional/Cautionary, Excluded, and Static Metadata/Identifiers.
   - Evaluates 5 candidate target formulations, selecting daily specific yield ($Y_f$) on valid site-days as the primary modeling target directly driving Layer B panel recommendation.
   - Establishes the comprehensive 14-item Limitations and Risk Register with concrete Phase 3 mitigation recommendations.
   - Delivers the 14-gate Phase 3 Technical Handover Matrix, cleanly separating closed EDA determinations from Phase 3 pipeline implementation responsibilities.

7. [**Target Definition and Data Preparation (`notebooks/phase3/target_definition_and_data_preparation.ipynb`)**](phase3/target_definition_and_data_preparation.ipynb):
   - Implements and finalizes Phase 3 (Target Definition and Data Preparation): transforms approved raw datasets into ML-ready feature matrices across a dual-dataset architecture.
   - Finalizes primary target as Daily Specific Yield ($Y_f = \frac{\sum E_{15\text{m}}}{\text{kW}_p}$ in $\text{kWh}/\text{kW}_p/\text{day}$) on verified valid site-days.
   - Establishes two parallel modeling datasets for Layer A: Dataset A (Full Cohort, 24 sites, $n = 7,039$) and Dataset B (Peer Cohort, 22 sites, $n = 6,456$, stored under `data/processed/unisolar/peer_cohort/`).
   - Reconciles full site-day accounting across the 365-day annual window ($24 \times 365 = 8,760$ expected site-days): $7,039$ valid site-days ($80.35\%$), $1,481$ observed invalid site-days ($16.91\%$), and $240$ site-days from the 10 completely absent calendar dates ($2.74\%$).
   - Strictly separates primary predictive features ($29$ continuous/cyclical features) from post-hoc diagnostic metadata and quality indicators, isolating diagnostic flags in `diagnostic_metadata.csv` to prevent model leakage.
   - Enforces calendar-aware day-ahead lag horizon $\tau \ge 24\text{h}$ on continuous daily grid without forward-fill distortion; eliminates same-day weather leakage; fits imputation medians strictly on training partition.
   - Audits daily energy interval completeness: confirms sub-threshold missingness outside the core window tracks astronomical daylight hours, with equal interval counts across cohorts ($43.7$ to $44.8$ valid intervals/day).
   - Audits target physical plausibility: documents Site 19 ($34.32\text{ kW}_p$, max $40.79\text{ kWh}/\text{kW}_p/\text{day}$) and Site 24 ($40.26\text{ kW}_p$, mean $6.08\text{ kWh}/\text{kW}_p/\text{day}$) as unresolved data-quality anomalies (feeder aggregation is an unproven hypothesis); confirms Peer Cohort is $100\%$ physically bounded ($Y_{f,\text{max}} = 6.917\text{ kWh}/\text{kW}_p/\text{day}$, $\text{CF}_{24\text{h}} \le 28.82\%$).
   - Exports chronological splits for both Dataset A (Train 4,770, Val 1,037, Test 1,232) and Dataset B (Train 4,383, Val 945, Test 1,128).
   - Prepares isolated Kaggle Benchmark (Plants 1 & 2: $136,472$ intervals); clarifies Plant 1 DC/AC $10\times$ ratio as an observed discrepancy rather than an asserted sensor bug.
   - Verifies deterministic pipeline execution via `src/prepare_phase3_data.py`.

- **Phase 4: Model Development and Comparison**
  - Directory: `notebooks/phase4/`
  - Master Notebook: `notebooks/phase4/baseline_and_model_development.ipynb`
  - Scope & Status: Complete (Prompts 1 & 2). Covers empirical baseline establishment, benchmarking of 8 machine learning algorithms, expanding-window temporal cross-validation, hyperparameter optimization, permutation feature importance, residual/site-wise diagnostics, multi-objective latency and footprint profiling, and candidate model selection.
  - Key Outcomes:
    - Reconciled feature naming and chronological partition dates: verified exact 29 Phase 3 features (`kWp`, `daylight_hours`, `extraterrestrial_radiation_h0`, `lag1_temp_mean`, `lag1_rh_mean`, etc.) and confirmed quarantined test partition (March 1 – April 23, 2022) was never touched.
    - Designed 4-fold expanding window temporal cross-validation within training partition (grouped strictly by date, zero leakage across sites on same calendar day).
    - Selected candidates for **Dataset A (Full Cohort, 24 sites)**:
      * Primary ML Candidate: **Tuned Elastic Net** ($\alpha=0.05, l_1=0.9$, $\text{MAE}=1.3765, \text{RMSE}=2.0134, R^2=0.8484$, $2.7\text{ KB}$, $350\ \mu\text{s}$ latency).
      * Fallback Candidate: **Tuned Extra Trees** ($\text{MAE}=1.4924, \text{RMSE}=2.7264, R^2=0.7220$).
      * Reference Benchmark: Persistence Baseline ($\text{MAE}=1.4981, \text{RMSE}=3.1874, R^2=0.6207$).
    - Selected candidates for **Dataset B (Peer Cohort, 22 sites)**:
      * Primary ML Candidate: **Tuned Extra Trees** ($n=100, \text{depth}=12, \text{max\_features}=0.8$, $\text{MAE}=1.0793, \text{RMSE}=1.3462, R^2=-0.2637$, $17.7\text{ MB}$, $14.2\text{ ms}$ latency). Outperforms Train Mean baseline RMSE ($2.0716$) by $35.0\%$ and beats Persistence benchmark ($\text{RMSE}=1.4984$).
      * Fallback Candidate: **Tuned Elastic Net** ($\alpha=0.05, l_1=0.7$, $\text{MAE}=1.3871, \text{RMSE}=1.6366, R^2=-0.8677$).
      * Reference Benchmark: Persistence Baseline ($\text{MAE}=1.1319, \text{RMSE}=1.4984, R^2=-0.5661$).
    - Diagnosed mathematical mechanics of negative $R^2$ in Peer Cohort midsummer validation: low summer cross-sectional variance ($\text{Var}=1.436$) coupled with winter-to-summer seasonal shift renders $R^2$ negative even for highly accurate forecasts, establishing MAE and RMSE as authoritative physical criteria.
    - Serialized tuned candidate models to `models/phase4/` and generated comprehensive metadata in `models/phase4/model_metadata.json`.

- **Phase 5: Model Evaluation and Finalization**
  - Directory: `notebooks/phase5/`
  - Master Notebooks:
    * `notebooks/phase5/model_diagnostics_and_improvement_investigation.ipynb` (Prompt 1 Diagnostics)
    * `notebooks/phase5/model_improvement_experiments.ipynb` (Prompt 2 Improvement Experiments)
    * `notebooks/phase5/final_model_evaluation_and_generalization.ipynb` (Prompt 3 Master Test Evaluation)
  - Scope & Status: Complete (Prompts 1, 2, & 3) (**STATUS: FORMALLY COMPLETED AND FINALIZED**). Covers deep model failure diagnostics, error decomposition of negative $R^2$, ensemble blending optimization, secondary validation checks, and the single, leakage-safe held-out test evaluation on the previously quarantined partition (March 1 – April 23, 2022).
  - Key Outcomes:
    - Maintained strict quarantine over test partition until Prompt 3; single evaluation execution with zero post-test iterative tuning.
    - Combined pre-test retraining (Train + Val, May 1, 2021 – Feb 28, 2022) successfully resolved seasonal underprediction bias in Peer Cohort.
    - **Peer Cohort (22 Sites, Test $N=1,128$):**
      * **Primary Candidate (Tuned ExtraTrees):** Achieved $\text{MAE} = \mathbf{0.9050}$, $\text{RMSE} = \mathbf{1.0700}$, $\mathbf{R^2 = +0.2580}$, $\text{Bias} = -0.1036$. Significantly outperformed Persistence ($\text{MAE}=1.0875, \text{RMSE}=1.3713, R^2=-0.2187$). Verdict: **ACCEPTED**.
      * **Fallback Candidate (50/50 Ensemble Blend):** Achieved $\text{MAE} = \mathbf{0.8898}$, $\text{RMSE} = \mathbf{1.0615}$, $\mathbf{R^2 = +0.2698}$. Verdict: **ACCEPTED (Authorized Fallback)**.
    - **Full Cohort (24 Sites, Test $N=1,232$):**
      * **Primary Candidate (Tuned ElasticNet):** Achieved $\text{MAE} = \mathbf{1.1463}$, $\text{RMSE} = \mathbf{1.9494}$, $\mathbf{R^2 = +0.7407}$, $\text{Bias} = -0.3144$. Outperformed Persistence ($\text{MAE}=1.3952, \text{RMSE}=2.4225, R^2=0.5996$). Verdict: **CONDITIONALLY ACCEPTED WITH DOCUMENTED LIMITATIONS**.
      * **Fallback Candidate (70/30 Ensemble Blend):** Achieved $\text{MAE} = \mathbf{1.1623}$, $\text{RMSE} = \mathbf{1.9567}$, $\mathbf{R^2 = +0.7388}$. Verdict: **CONDITIONALLY ACCEPTED WITH DOCUMENTED LIMITATIONS**.
    - Generated publication-grade test evaluation figures, complete metadata in `models/phase5/final_model_metadata.json`, and CSV reports in `reports/phase5/`.
    - Handover established for Phase 6: Layer B Constraint-Aware Solar Panel Recommendation and Uncertainty Quantification.

- **Phase 6: Real Solar Panel Catalogue**
  - Directory: `notebooks/phase6/`
  - Master Notebook: `notebooks/phase6/panel_catalogue_inventory_and_validation.ipynb` (Prompt 1)
  - Scope & Status: Prompt 1 Complete (**STATUS: IN PROGRESS — INVENTORY & CANONICAL SCHEMA ESTABLISHED**). Covers existing repository catalogue audit, reconciliation against Appendix B claims, canonical 43-column schema definition across 8 engineering domains, automated engineering validation engine, missingness analysis, and technology gap assessment.
  - Key Outcomes:
    - Proved conclusively that `configs/panels_catalogue.csv` did not previously exist; Appendix B commercial models (Waaree, Canadian Solar, First Solar, Mission Solar) exist only as documentation claims, with zero verified datasheets in codebase.
    - Extracted 3 raw module references from `data/raw/unisolar/Solar_Site_Details.csv` (Trina 330W, Trina 310W, SunpowerSPR-E20-435-COM) and populated `configs/panels_catalogue.csv` with zero assumed/fabricated values (34 fields set strictly to null, status: `UNVERIFIED_PENDING_EXTERNAL_DATASHEET`).
    - Established canonical schema in `configs/panels_catalogue_schema.json` and clean template in `configs/panels_catalogue_template.csv`.
    - Implemented modular validator `src/validate_panel_catalogue.py` with diagnostic efficiency, thermal sign/unit, electrical curve, and pricing basis checks.
    - Formulated official External Data Acquisition Request for Phase 6 Prompt 2.

---

## Project Status
- **Phase 1 (Data Inspection):** Complete and verified.
- **Phase 2 (Exploratory Data Analysis):** Complete and verified (all 6 notebooks execute with 0 errors).
- **Phase 3 (Target Definition and Data Preparation):** Complete, verified, and formally finalized with documented limitations (**STATUS: FINALIZED WITH DOCUMENTED LIMITATIONS**).
- **Phase 4 (Model Development and Comparison):** Complete and formally finalized (**STATUS: COMPLETED WITH DOCUMENTED LIMITATIONS**).
- **Phase 5 (Model Evaluation and Finalization):** Complete, verified, and formally finalized (**STATUS: FORMALLY COMPLETED AND FINALIZED**).
- **Phase 6 (Real Solar Panel Catalogue):** Prompt 1 Complete (**STATUS: IN PROGRESS — INVENTORY & CANONICAL SCHEMA ESTABLISHED**). Ready for Prompt 2 (External Datasheet Acquisition Approval & Population).
