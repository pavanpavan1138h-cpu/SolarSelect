# Phase-Wise Implementation History — SolarSelect

This document provides the authoritative, exhaustive historical record of implementation, technical decisions, empirical findings, and artifacts produced across all phases of Project **SolarSelect**.

---

## Phase 1 — Dataset Collection and Inspection

- **Objective:** Ingest, inspect, verify, and organize candidate solar energy generation and meteorological datasets.
- **Scope:** Ingested the 4 original Kaggle generation and weather files for Plants 1 & 2; evaluated candidate multi-year datasets; ingested the approved UNISOLAR multi-campus dataset.
- **Tasks Completed:**
  1. Audited raw Kaggle files (`Plant_1_Generation_Data.csv`, `Plant_1_Weather_Sensor_Data.csv`, `Plant_2_Generation_Data.csv`, `Plant_2_Weather_Sensor_Data.csv`).
  2. Identified Kaggle limitations: 34-day span (May 15 – June 17, 2020), absence of multi-year seasonality, lack of documented DC nameplate capacity ($P_{\text{STC}}$) preventing specific-yield calculation.
  3. Evaluated candidate multi-year datasets (UNISOLAR vs. Cyprus PV). Selected UNISOLAR due to complete documentation, multi-year multi-site telemetry, and campus building metadata.
  4. Ingested 4 UNISOLAR raw files into `data/raw/unisolar/` ($1.53\text{M}$ generation rows, $371\text{k}$ weather rows, 42 campus sites).
  5. Established raw data immutability policy; initialized DVC tracking (`.dvc/`).
- **Important Technical Decisions:** ADR-001 (Raw Data Immutability), ADR-002 (UNISOLAR Dataset Supplementation).
- **Notebooks & Scripts:** [`dataset_inspection_and_source_verification.ipynb`](../../notebooks/data_inspection/dataset_inspection_and_source_verification.ipynb).
- **Artifacts:** `notebooks/data_inspection/figures/raw_dataset_dimensions_and_record_counts.png`.
- **Current Status:** **COMPLETED.**

---

## Phase 2 — EDA and Data Understanding

- **Objective:** Perform deep exploratory data analysis across physical distributions, data quality, temporal dynamics, seasonal cycles, capacity scaling, and feature relationships.
- **Scope:** 6 structured tasks covering both Kaggle Plants 1 & 2 and UNISOLAR 42 sites.
- **Tasks Completed:**
  1. **Task 1 (Structure & Schema):** Verified schemas, primary composite keys, and timestamp conventions.
  2. **Task 2 (Data Quality & Completeness):** Audited missing values ($0\%$ in Kaggle, $56.23\%$ nulls in UNISOLAR concentrated at night and below $0.100–0.125\text{ kWh}$). Quantified Plant 2 inverter dropouts (904 timestamps).
  3. **Task 3 (Physical Distributions & Scaling):** Investigated Plant 1 vs Plant 2 DC/AC ratio difference (median ratio $10.22$ in P1 vs $1.02$ in P2; an approximately 10x difference whose root cause remains unconfirmed). Identified Site 27 discrete $0.125\text{ kWh}$ pulse quantization from older buffer dumps. Audited capacity scaling against theoretical STC limits.
  4. **Task 4 (Temporal, Seasonal & Site-Wise Analysis):** Formulated the A-Priori Valid Site-Day Filter ($96$ intervals, $\ge 26/28$ core 09:00–15:45 intervals). Reconciled specific yield calculation: corrected earlier inflated formula ($\text{mean} \times 96 / \text{kWp}$, $2.31\times$ inflated) to valid site-day energy sums divided by $\text{kWp}$ (peer median $Y_f = 2.94\text{ kWh}/\text{kW}_p/\text{day}$). Audited seasonal spread ($2.41\times$ summer-to-winter ratio).
  5. **Task 5 (Feature Relationships & Target Feasibility):** Evaluated weather correlations (Kaggle on-site irradiance $r=0.985$ vs UNISOLAR off-site proxy temperature $r=0.194$). Formulated 5 candidate targets and selected Daily Specific Yield ($Y_f$). Formulated 7-rule Data Leakage Register. Proved that joint tabular pooling of Kaggle and UNISOLAR is scientifically invalid.
  6. **Task 6 (Consolidated Findings & Dataset Selection):** Consolidated all findings into an evidence-based dataset selection: UNISOLAR Campus 1 designated as Primary Benchmark for Layer A; Kaggle retained as isolated secondary benchmark for 15-minute power forecasting. Formulated 14-gate Phase 3 Technical Handover Matrix.
- **Important Technical Decisions:** ADR-003 (Prohibition of Cross-Dataset Pooling), ADR-004 (Specific Yield Target Selection), ADR-005 (Valid Site-Day Filter).
- **Notebooks & Scripts:** 6 notebooks in `notebooks/eda2.0/` (Tasks 1–6) executing with 0 errors.
- **Artifacts:** 16 publication-grade figures in `notebooks/eda2.0/figures/`.
- **Current Status:** **COMPLETED.**

---

## Phase 3 — Target Definition and Data Preparation

- **Objective:** Transform approved raw datasets into reproducible, leakage-safe, ML-ready feature matrices across a dual-cohort architecture.
- **Scope:** 12-month complete annual cycle (`2021-05-01` to `2022-04-23`, 345 active observation dates across 24 documented-$\text{kW}_p$ sites).
- **Tasks Completed:**
  1. Reconciled full site-day accounting across 8,760 expected annual site-days ($7,039$ valid site-days [$80.35\%$], $1,481$ invalid site-days excluded, $240$ site-days from 10 absent dates).
  2. Engineered the authoritative **29 continuous and cyclical predictive features** (capacity, astronomical formulas, day-ahead weather lags, autoregressive yield lags, rolling stats, and lag availability indicators).
  3. Enforced strict calendar-aware day-ahead lag shifts ($\tau \ge 24\text{h}$) on a continuous daily grid without forward-fill distortion.
  4. Isolated 17 non-predictive diagnostic indicators into `diagnostic_metadata.csv` to prevent model leakage.
  5. Established dual-cohort architecture:
     * **Full Cohort (Dataset A, 24 sites):** $N = 7,039$ valid site-days (Train: 4,770; Val: 1,037; Test: 1,232).
     * **Peer Cohort (Dataset B, 22 sites):** $N = 6,456$ valid site-days (Train: 4,383; Val: 945; Test: 1,128). Excludes anomalous Sites 19 and 24.
  6. Generated chronological train/val/test splits with static training-only imputation medians.
  7. Formatted isolated Kaggle benchmark ($136,472$ intervals).
  8. Created production script [`src/prepare_phase3_data.py`](../../src/prepare_phase3_data.py).
- **Important Technical Decisions:** ADR-006 (Retention of Site 19/24 Without Clipping), ADR-007 (Dual Cohort Architecture), ADR-008 (Calendar-Aware Day-Ahead Lags), ADR-009 (Separation of Diagnostic Metadata).
- **Notebooks & Scripts:** [`target_definition_and_data_preparation.ipynb`](../../notebooks/phase3/target_definition_and_data_preparation.ipynb), `src/prepare_phase3_data.py`.
- **Artifacts:** `data/processed/unisolar/` (Full & Peer CSVs), `feature_dictionary.csv`, `preprocessing_metadata.json`, Figure 4-panel summary.
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS** (Site 19 & 24 anomalies preserved).

---

## Phase 4 — Baseline and Model Development

- **Objective:** Establish empirical baselines, benchmark 8 machine learning algorithms, tune hyperparameters via 4-fold expanding-window temporal CV, and select candidate models.
- **Scope:** Both Full Cohort (24 sites) and Peer Cohort (22 sites) across the Training partition (`2021-05-01` to `2021-12-31`).
- **Tasks Completed:**
  1. Established 3 baselines: Pre-test Mean, Persistence (Lag 1), and Historical Rolling 7-day Mean.
  2. Implemented 4-fold expanding-window temporal cross-validation grouped strictly by `Date` (zero cross-site leakage on same calendar day).
  3. Trained and tuned 8 algorithms across linear, regularized, and tree ensemble families (OLS, Ridge, Lasso, ElasticNet, Random Forest, ExtraTrees, GBR, LightGBM).
  4. Conducted permutation feature importance (astronomical insolation $H_0$, `lag1_daily_yield`, and temperature swing emerged as dominant drivers).
  5. Multi-objective profiling: evaluated RMSE, MAE, in-memory footprint, and inference latency.
  6. Candidate selection:
     * **Full Cohort:** Primary = Tuned ElasticNet ($\alpha=0.05, l_1=0.90$, $\text{CV RMSE} = 2.1299$); Fallback = Tuned ExtraTrees ($\text{CV RMSE} = 2.2048$).
     * **Peer Cohort:** Primary = Tuned ExtraTrees ($n=100, d=12, f=0.8$, $\text{CV RMSE} = 1.3190$); Fallback = Tuned ElasticNet ($\text{CV RMSE} = 1.3097$).
  7. Diagnosed summer validation negative $R^2$ in Peer Cohort as an artifact of seasonal level shift and low cross-sectional variance.
- **Important Technical Decisions:** ADR-010 (Expanding-Window Temporal CV Grouped by Date).
- **Notebooks & Scripts:** [`baseline_and_model_development.ipynb`](../../notebooks/phase4/baseline_and_model_development.ipynb).
- **Artifacts:** Serialized models in `models/phase4/`, `models/phase4/model_metadata.json`, `reports/phase4/experiment_results.csv`.
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS.**

---

## Phase 5 — Model Evaluation and Finalization

- **Objective:** Execute deep diagnostic investigations, test model improvement strategies (ensemble blending, astronomical calibration, site bias), fit final candidates on pre-test data, and conduct the single held-out test evaluation.
- **Scope:** Completed in exactly three structured prompts:
  * Prompt 1: Deep diagnostics & bias decomposition.
  * Prompt 2: Leakage-safe improvement experiments.
  * Prompt 3: Model retraining, held-out test evaluation, and final acceptance.
- **Tasks Completed:**
  1. **Prompt 1 Diagnostics:** Deconstructed negative validation $R^2$ ($\text{MSE} = 1.8122 = 0.6953 \text{ [Bias}^2\text{]} + 1.1169 \text{ [Var]}$. Bias explained $38.4\%$ of MSE). Diagnosed tree leaf averaging saturation on Site 19 ($Y_f > 30$). Verified lag imputation stability in validation (`has_valid_lag1 == 0` showed no elevated error).
  2. **Prompt 2 Improvement Experiments:** Optimized weighted ensemble blending in 4-fold temporal CV:
     * Peer Cohort: 50/50 Blend ($w=0.5$) achieved $\text{CV RMSE} = \mathbf{1.2715}$ (beating all single models). Approved as fallback.
     * Full Cohort: 70/30 Blend ($w=0.7$) achieved $\text{CV RMSE} = \mathbf{2.1122}$. Approved as fallback.
     * Evaluated and rejected astronomical calibration and site-bias adjustment due to negligible CV gain ($<0.0012$) and unnecessary operational complexity.
  3. **Prompt 3 Pre-Evaluation Reconciliation & Freezing:** Reconciled calendar days vs active telemetry dates; verified 29 features; froze candidate models; retrained models on combined pre-test data (Train + Val, Full: $N=5,807$, Peer: $N=5,328$).
  4. **Prompt 3 Single Test Evaluation (March 1 – April 23, 2022):**
     * **Peer Cohort ($N=1,128$):** Tuned ExtraTrees achieved $\text{MAE} = \mathbf{0.9050}$, $\text{RMSE} = \mathbf{1.0700}$, $\mathbf{R^2 = +0.2580}$, $\text{Bias} = -0.1036$ (16.8% MAE reduction over Persistence). Accepted as Primary. 50/50 Blend achieved $\text{MAE} = 0.8898$, $R^2 = +0.2698$. Accepted as Fallback.
     * **Full Cohort ($N=1,232$):** Tuned ElasticNet achieved $\text{MAE} = \mathbf{1.1463}$, $\text{RMSE} = \mathbf{1.9494}$, $\mathbf{R^2 = +0.7407}$, $\text{Bias} = -0.3144$. Conditionally Accepted with Documented Limitations.
- **Important Technical Decisions:** ADR-011 (Strict Test Quarantine), ADR-012 (Rejection of Astro Calibration/Site Bias), ADR-013 (Final Offline Evaluated Model Acceptance Decisions).
- **Notebooks & Scripts:** 3 notebooks in `notebooks/phase5/` executing cleanly with 0 errors.
- **Artifacts:** `models/phase5/final/` (serialized offline evaluated models), `models/phase5/final_model_metadata.json`, `reports/phase5/test_evaluation_results.csv`, `reports/phase5/test_site_evaluation.csv`, 4 test diagnostic figures.
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS.**

---

## Phase 6 — Real Solar Panel Catalogue

- **Objective:** Establish an authoritative, structured, and traceable commercial solar panel catalogue for Layer B recommendation modeling.
- **Scope:** Prompt 1 completed (Inventory, canonical schema design, automated validation engine). Prompt 2 completed (Datasheet acquisition and catalogue compiler, 12-module expansion across 6 distinct technologies, local compiled reference PDF storage with SHA-256 integrity hashes, source manifest, 516-row field provenance table, validation engine executed). Final forensic verification completed (Audit of local PDF structure, source URL accessibility, field-level provenance, and SHA-256 integrity).
- **Tasks Completed:**
  1. Audited repository: proved that `configs/panels_catalogue.csv` did not previously exist; confirmed that Appendix B's 14 commercial models existed solely as narrative claims without codebase records.
  2. Designed canonical 43-column schema across 8 domains (`configs/panels_catalogue_schema.json`) and header-only template (`configs/panels_catalogue_template.csv`).
  3. Implemented automated validation script (`src/validate_panel_catalogue.py`) checking diagnostic efficiency consistency, thermal signs/units, electrical hierarchy ($V_{mp} < V_{oc}$, $I_{mp} < I_{sc}$), and pricing standards.
  4. Executed catalogue specification compiler under stakeholder authorization (`src/acquire_phase6_datasheets.py`).
  5. Ingested and retained 12 commercial PV modules spanning 6 distinct semiconductor technologies (Polycrystalline, Monocrystalline PERC, N-type TOPCon, Heterojunction HJT, IBC, Thin-film CdTe) across Monofacial and Bifacial Glass-Glass construction formats.
  6. Reconciled UNISOLAR campus baseline installations: SunPower SPR-E20-435-COM confirmed exact match based on explicit site metadata model string (Site 27); Trina 330W (TSM-PD14) and Trina 310W (TSM-DD05A.08) documented as candidate installation mappings.
  7. Established structured local compiled reference PDF storage in `data/reference/panel_datasheets/<mfg>/`, compiled 12-row `source_manifest.csv` with SHA-256 integrity hashes, and built 516-row granular `field_provenance.csv`.
  8. Executed validation engine distinguishing automated structural checks (`PASS`) from documentary evidence checks (`TECHNICAL_SPECIFICATIONS_VERIFIED_WITH_CANDIDATE_CAMPUS_MAPPINGS`, validating catalogue consistency against retained compiled specification summaries without implying independent primary-source authentication).
  9. Conducted forensic audit of 12 local PDFs (`reports/phase6/phase6_final_datasheet_authenticity_verification.md`): confirmed they are single-page compiled technical specification summaries (~3.4 KB each); confirmed all source URLs point to official manufacturer domains but are currently inaccessible over live HTTP; confirmed 12/12 SHA-256 hashes match local manifest bit-for-bit.
- **Important Technical Decisions:** ADR-014 (Catalogue Canonical Schema & Data-Source Governance), ADR-015 (Official Datasheet Ingestion & 12-Module Catalogue Expansion).
- **Notebooks & Scripts:** [`panel_catalogue_inventory_and_validation.ipynb`](../../notebooks/phase6/panel_catalogue_inventory_and_validation.ipynb), `src/acquire_phase6_datasheets.py`, `src/validate_panel_catalogue.py`.
- **Artifacts:** `configs/panels_catalogue_schema.json`, `configs/panels_catalogue.csv`, `data/reference/panel_datasheets/source_manifest.csv`, `data/reference/panel_datasheets/field_provenance.csv`, `reports/phase6/catalogue_validation_report.json`, `reports/phase6/phase6_prompt2_datasheet_acquisition_report.md`, `reports/phase6/phase6_final_catalogue_evidence_audit.md`, `reports/phase6/phase6_final_datasheet_authenticity_verification.md`.
- **Current Status:** **`COMPLETE_WITH_DOCUMENTED_LIMITATIONS`**
  > *Closure Statement:* Phase 6 implementation and catalogue preparation are complete. Twelve panel records, the catalogue schema, validation tooling, compiled reference summaries, and provenance records are retained. However, independent primary-source re-verification of manufacturer specifications remains limited because the original manufacturer documents were inaccessible during the final audit. This limitation is documented and does not invalidate the catalogue records by itself.
- **Phase 7 Boundary:** Phase 7 (Roof-Fit and Panel Configuration Engine) has **NOT** started. No Phase 7 implementation is included in this task.

---

## Phases 7 to 10 — Future Scope

- **Phase 7 (Roof-Fit and Panel Configuration Engine):** Planned 2D physical array packing, module orientation, setbacks, and pitch/azimuth geometry. **Status: PENDING.**
- **Phase 8 (Energy, Economics and Recommendation Engine):** Planned climate-conditioned simulation, 25-year LCOE/payback, and multi-criteria panel ranking. **Status: PENDING.**
- **Phase 9 (Integration, Application and MLOps):** Planned FastAPI inference serving, Streamlit interactive dashboard, MLflow model registry, and DVC integration. **Status: PENDING.**
- **Phase 10 (Testing, Monitoring and Final Validation):** Planned Evidently AI drift monitoring, integration testing, and CI/CD automated retraining pipelines. **Status: PENDING.**
