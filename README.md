# SolarSelect — An End-to-End MLOps System for AI-Based Solar Panel Selection

[![Python 3.13.9](https://img.shields.io/badge/python-3.13.9-blue.svg)](https://www.python.org/downloads/release/python-3139/)
[![License: ODbL / Academic](https://img.shields.io/badge/license-Academic%20Open-green.svg)](#licensing)
[![Status: Phase 7 Design Active](https://img.shields.io/badge/status-Phase%207%20Design%20Active-orange.svg)](#authoritative-project-status-phases-110)
[![MLOps: DVC & Scikit-Learn](https://img.shields.io/badge/MLOps-DVC%20%7C%20Joblib-red.svg)](#repository-quickstart)

**SolarSelect** is a production-grade machine learning and operations platform designed to eliminate information asymmetry in rooftop solar adoption. It combines climate-conditioned daily specific energy yield forecasting with a constraint-aware commercial photovoltaic (PV) panel recommendation engine.

---

## Central Documentation Portal

Comprehensive project documentation is maintained in the [`docs/`](docs/) directory:

- 🏛️ [**Project Overview & Vision**](docs/project/project_overview.md) — Problem statement, two-layer architecture, and value proposition.
- 📐 [**System Architecture & Diagrams**](docs/project/system_architecture.md) — Five detailed Mermaid architecture diagrams distinguishing implemented vs. planned systems.
- 🗺️ [**10-Phase Project Roadmap**](docs/project/project_roadmap.md) — Full engineering roadmap from data ingestion to CI/CD monitoring.
- 📊 [**Dataset Inventory & Dictionaries**](docs/data/dataset_inventory.md) — Complete schemas, units, and non-pooling data governance policies.
- 🤖 [**Final Machine Learning Model Reference**](docs/machine_learning/final_model_reference.md) — Tuned ExtraTrees, ElasticNet, hyperparameters, and test evaluation metrics.
- 📦 [**Commercial Panel Catalogue & Validation**](docs/panel_catalogue/catalogue_schema.md) — 43-column canonical schema, 12 verified modules across 6 distinct technologies, local PDF datasheets with SHA-256 integrity hashes, 516-row provenance audit, and validator script.
- 📋 [**Living Governance Registers**](docs/decisions/) — [ADR Decision Register](docs/decisions/decision_register.md), [Assumptions](docs/decisions/assumptions_register.md), [Limitations](docs/decisions/limitations_register.md), and [Risks](docs/decisions/risk_register.md).
- 📜 [**Phase-Wise Implementation History**](docs/reports/phase_wise_implementation_history.md) — Exhaustive chronological record across all 10 phases.

---

## The Dual-Layer Concept

SolarSelect connects two operational layers to deliver personalized solar recommendations:

```mermaid
graph TD
    subgraph LayerA["Layer A: Climate-Conditioned Yield Forecasting (MLOps)"]
        W[BOM Regional Weather Telemetry] --> FE[Feature Engineering: 29 Predictive Features]
        A[Analytical Astronomical Angles: H0, Elevation] --> FE
        H[Autoregressive Lags: tau >= 24h] --> FE
        FE --> ET["Primary Model: Tuned ExtraTrees (Peer Cohort)"]
        FE --> EN["Primary Model: Tuned ElasticNet (Full Cohort)"]
        ET --> Yf["Forecasted Specific Yield (Y_f: kWh/kWp/day)"]
    end

    subgraph LayerB["Layer B: Constraint-Aware Panel Recommendation Engine"]
        Yf --> Sim["Climate & Thermal Energy Simulation"]
        Cat[(Canonical Commercial Panel Catalogue: 43 Columns)] --> Sim
        Cat --> RoofFit["2D Roof-Fit Array Geometry & Packing"]
        Roof[Rooftop Dimensions & Setbacks] --> RoofFit
        Budget[Client Capital Budget] --> Opt["LCOE & Payback Optimization"]
        RoofFit --> Opt
        Sim --> Opt
        Opt --> Output["Ranked, Explainable Solar Panel Recommendations"]
    end
```

---

## Authoritative Project Status (Phases 1–10)

| Phase | Title | Status | Primary Output / Verification |
|---|---|---|---|
| **Phase 1** | Dataset Collection and Inspection | **COMPLETED** | Verified Kaggle (2 plants) & UNISOLAR (42 sites) raw archives |
| **Phase 2** | EDA and Physical Understanding | **COMPLETED** | 6 standalone notebooks, verified valid site-day filter, capacity audit |
| **Phase 3** | Target Definition & Data Preparation | **COMPLETED (WITH LIMITATIONS)** | Dual cohorts (Full 24-site / Peer 22-site), 29 features, chronological splits |
| **Phase 4** | Baseline & ML Model Development | **COMPLETED (WITH LIMITATIONS)** | 3 baselines, 8 algorithms, 4-fold expanding-window temporal CV |
| **Phase 5** | Model Evaluation & Finalization | **COMPLETED (WITH LIMITATIONS)** | Single held-out test evaluation, bias resolution, ExtraTrees accepted |
| **Phase 6** | Real Solar Panel Catalogue | **COMPLETE_WITH_DOCUMENTED_LIMITATIONS** | 12 retained commercial modules across 6 technologies, compiled reference summaries with SHA-256 hashes, 516-row provenance table. Primary-source re-verification documented limitation. |
| **Phase 7** | Roof-Fit & Configuration Engine | **DESIGN / REQUIREMENTS IN PROGRESS** | Prompt 1 engineering design complete: requirements, architecture, 5-algorithm evaluation (row-wise strip packing selected), input/output contract, and 15-scenario test matrix. Implementation not started. |
| **Phase 8** | Energy, Economics & Recommendation | **PENDING** | Future work (LCOE, payback, multi-criteria ranking) |
| **Phase 9** | Integration, Application & Serving | **PENDING** | Future work (FastAPI REST service, Streamlit web UI) |
| **Phase 10** | Testing, Monitoring & CI/CD | **PENDING** | Future work (Evidently AI drift monitoring, automated retraining) |

---

## Final Machine Learning Performance (Phase 5 Held-Out Test Set)

Evaluated on the strictly quarantined Test partition (`2022-03-01` to `2022-04-23`):

### Peer Cohort (Dataset B: 22 Clean Physical Sites, $N = 1,128$)
- **Pre-Test Mean Baseline:** $\text{MAE} = 1.0628$, $\text{RMSE} = 1.2534$, $R^2 = -0.0181$
- **Persistence Baseline (Lag 1):** $\text{MAE} = 1.0875$, $\text{RMSE} = 1.3713$, $R^2 = -0.2187$
- **Primary Model: Tuned ExtraTrees:** $\mathbf{\text{MAE} = 0.9050}$, $\mathbf{\text{RMSE} = 1.0700}$, $\mathbf{R^2 = +0.2580}$, $\text{Bias} = -0.1036$
  * *Impact:* **Reduces day-ahead MAE by 16.8% and RMSE by 22.0%** relative to persistence.
- **Fallback Model: 50/50 Ensemble Blend:** $\mathbf{\text{MAE} = 0.8898}$, $\mathbf{\text{RMSE} = 1.0615}$, $\mathbf{R^2 = +0.2698}$

### Full Cohort (Dataset A: 24 Campus Sites, $N = 1,232$)
- **Pre-Test Mean Baseline:** $\text{MAE} = 1.9029$, $\text{RMSE} = 3.8317$, $R^2 = -0.0016$
- **Persistence Baseline (Lag 1):** $\text{MAE} = 1.3952$, $\text{RMSE} = 2.4225$, $R^2 = +0.5996$
- **Primary Model: Tuned ElasticNet:** $\mathbf{\text{MAE} = 1.1463}$, $\mathbf{\text{RMSE} = 1.9494}$, $\mathbf{R^2 = +0.7407}$, $\text{Bias} = -0.3144$
  * *Verdict:* **Conditioned on Macro Campus Tracking Only** (accommodates anomalous Site 19 yields without saturation; prohibited for single-site panel recommendations).

---

## Repository Quickstart

### 1. Environment Setup (Single Canonical Python 3.13.9)
```bash
# Clone repository
git clone https://github.com/your-org/SolarSelect.git
cd SolarSelect

# Use unified Python 3.13.9 runtime (pinned in .python-version)
conda activate base          # or: python3.13 -m venv .venv && source .venv/bin/activate
python --version             # Expected: Python 3.13.9

# Install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Pull Datasets and Model Artifacts (DVC)
```bash
# Optional: Configure DagsHub remote credentials if pulling fresh from remote
dvc remote modify origin --local access_key_id <YOUR_KEY>
dvc remote modify origin --local secret_access_key <YOUR_SECRET>

# Pull all versioned raw data, processed matrices, and Phase 5 models
dvc pull

# Verify local cache matches remote DagsHub S3 storage
dvc status -c
```

### 3. Run Data Preprocessing Pipeline (DVC & Python)
```bash
# Option A: Deterministic execution via DVC DAG (recomputes only when dependencies change)
dvc repro prepare_phase3_data

# Option B: Direct Python execution
python3 src/prepare_phase3_data.py
```

### 4. Run Panel Catalogue Validator
```bash
# Validates commercial panel catalogue against canonical schema & physical laws
python3 src/validate_panel_catalogue.py
```

### 5. Automated Regression Test Suite
```bash
# Run 238 automated regression tests (100% pass rate)
pytest -q tests/
```

### 6. Interactive Notebooks Execution
All 12 research and modeling notebooks in `notebooks/` are self-contained and execute cleanly end-to-end. For details on notebook order, see [`docs/engineering/execution_guide.md`](docs/engineering/execution_guide.md).

---

## MLOps Architecture & Artifact Governance

SolarSelect separates large binary artifact versioning from code and metric tracking:

- **Data Version Control (DVC):**
  - Manages immutable raw telemetry (`data/raw/archive.dvc`, `data/raw/unisolar.dvc`).
  - Tracks reproducible pipeline stages (`dvc.yaml`, `dvc.lock`) producing 18 processed CSV outputs while keeping lightweight metadata JSONs in Git.
  - Versions 8 frozen Phase 5 scikit-learn models (`models/phase5/**/*.joblib.dvc`).
  - Synchronized with DagsHub S3 remote storage (`origin`).
- **MLflow Observability (Planned for Phase 9 Serving):**
  - Reserved for experiment tracking, hyperparameter runs, metric logging, and model registry lifecycle. *(Note: MLflow experiment logging integration is pending).*

---

## Project Structure Overview

```text
SolarSelect/
├── .dvc/                # DVC remote configuration and cache pointers (credentials ignored)
├── configs/             # Canonical 43-col PV schema, template & active catalogue CSV
├── data/                # Raw (immutable DVC), interim, and processed ML matrices
├── docs/                # Central technical documentation suite
├── models/              # Serialized production models (.joblib.dvc) & metadata (.json)
├── notebooks/           # Phase 1 to Phase 6 research notebooks & figures
├── reports/             # Structured validation reports, test metrics, and CV CSVs
├── src/                 # Production pipeline scripts (prepare_phase3_data.py, etc.)
├── dvc.yaml             # DVC pipeline specification (prepare_phase3_data)
├── dvc.lock             # Immutable DVC output hash lockfile
├── log.txt              # Authoritative chronological project audit trail
└── requirements.txt     # Pinned Python package dependencies (including dvc-s3)
```

---

## Licensing & Governance

- **Software Code:** Open Academic License.
- **Kaggle Solar Generation Data:** Open Database License (ODbL) / CC BY-SA 4.0.
- **UNISOLAR Telemetry Data:** Research / Academic Open Access License.
- **Commercial PV Datasheets:** Restricted by data governance; external ingestion pending approval.
