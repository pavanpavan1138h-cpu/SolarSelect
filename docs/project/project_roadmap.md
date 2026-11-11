# Project Roadmap — SolarSelect

This roadmap outlines the complete 10-phase engineering lifecycle for **SolarSelect: An End-to-End MLOps System for AI-Based Solar Panel Selection**.

---

## 1. 10-Phase Project Lifecycle Overview

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER A: SPECIFIC YIELD FORECASTING FOUNDATION (MLOPS)                      │
│                                                                             │
│ [Phase 1] Dataset Collection & Inspection           ==> COMPLETED           │
│ [Phase 2] EDA & Physical Data Understanding         ==> COMPLETED           │
│ [Phase 3] Target Definition & Data Preparation      ==> COMPLETED (W/ LIMS) │
│ [Phase 4] Baseline & Machine Learning Development   ==> COMPLETED (W/ LIMS) │
│ [Phase 5] Model Evaluation & Finalization           ==> COMPLETED (W/ LIMS) │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER B: CONSTRAINT-AWARE REAL SOLAR PANEL RECOMMENDATION                   │
│                                                                             │
│ [Phase 6] Real Solar Panel Catalogue                ==> COMPLETED (W/ LIMS) │
│ [Phase 7] Roof-Fit & Panel Configuration Engine     ==> COMPLETED           │
│ [Phase 8] Energy, Economics & Recommendation Engine ==> COMPLETED (W/ LIMS) │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ DEPLOYMENT, MLOPS LIFECYCLE & CONTINUOUS MONITORING                         │
│                                                                             │
│ [Phase 9] Integration, Application & Serving (MLOps)==> PENDING (FUTURE)    │
│ [Phase 10] Testing, Monitoring & Final Validation   ==> PENDING (FUTURE)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase-by-Phase Roadmap Details

### Phase 1: Dataset Collection and Inspection
- **Goal:** Ingest raw multi-site solar telemetry and weather data; verify schema integrity and storage organization.
- **Key Deliverables:** Dataset audit, source verification, raw data immutability policy.
- **Current Status:** **COMPLETED.**

### Phase 2: Exploratory Data Analysis & Understanding
- **Goal:** Perform comprehensive physical, statistical, and seasonal audits across all collected data sources.
- **Key Deliverables:** 6 standalone Jupyter notebooks, valid site-day filtering criterion, investigation of Plant 1 10x DC/AC ratio difference (unconfirmed root cause), capacity normalization audit.
- **Current Status:** **COMPLETED.**

### Phase 3: Target Definition and Data Preparation
- **Goal:** Establish a leakage-safe preprocessing pipeline transforming raw telemetry into ML-ready matrices.
- **Key Deliverables:** `src/prepare_phase3_data.py`, dual-cohort split (Full 24-site / Peer 22-site), 29 predictive features, chronological partitions.
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS.**

### Phase 4: Baseline and Machine Learning Model Development
- **Goal:** Train diverse algorithm families (linear, regularized, tree ensembles) using expanding-window temporal CV.
- **Key Deliverables:** 3 empirical baselines, 8 tuned ML algorithms, multi-objective latency/footprint profiling.
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS.**

### Phase 5: Model Evaluation and Finalization
- **Goal:** Conduct deep failure-mode diagnostics, optimize ensemble blends, and execute a single held-out test evaluation.
- **Key Deliverables:** Bias decomposition, weighted blending, test set evaluation on quarantined data, final model artifacts in `models/phase5/final/`.
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS.**

### Phase 6: Real Solar Panel Catalogue
- **Goal:** Build an auditable, structured 43-column commercial solar panel database.
- **Key Deliverables:** 12 verified commercial PV modules across 6 technology families, schema validation tooling, and provenance manifests.
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS.**

### Phase 7: Roof-Fit and Panel Configuration Engine
- **Goal:** Model 2D rectangular array geometry, packing factor, module orientation, setbacks, keep-out obstacles, and walkways.
- **Key Deliverables:** Discrete integer coordinate placement engine, 12 catalogue panels fit, deterministic output contract (`src/roof_fit/`).
- **Current Status:** **COMPLETED.**

### Phase 8: Energy, Economics and Recommendation Engine
- **Goal:** Couple Layer A forecasts with hardware parameters to estimate energy, compute lifecycle economics (LCOE, NPV, payback), evaluate electrical compatibility, and generate multi-objective Pareto and weighted recommendations.
- **Key Deliverables:** 10-stage modular architecture (`src/energy_economics/`), deterministic Pareto peeling, multi-criteria scoring, trade-off explanations, and end-to-end orchestration (`EnergyEconomicsEngine`).
- **Current Status:** **COMPLETED WITH DOCUMENTED LIMITATIONS.**

### Phase 9: Integration, Application and MLOps (Active Implementation)
- **Goal:** Package Layer A and Layer B into a REST API (FastAPI) and interactive consumer dashboard (Streamlit) with DVC data/model versioning and MLflow tracking.
- **Current Status:** **IN PROGRESS (Prompt 1 UI Foundation & DVC Tracking Complete).**
  * *DVC Data & Model Lineage:* Fully completed and verified. Tracks raw datasets (`data/raw/archive.dvc`, `data/raw/unisolar.dvc`), reproducible Phase 3 pipeline (`prepare_phase3_data` with 18 CSV outputs in `dvc.lock`), and 8 frozen Phase 5 model binaries (`.joblib.dvc`). Remote synchronization active with DagsHub S3 (`dvc status -c` verified).
  * *Application UI Foundation:* Multi-page Streamlit dashboard, minimal SaaS design system, reusable component library, and service boundary established.
  * *Pending Work:* FastAPI REST endpoints, full UI recommendation orchestration wiring, and MLflow experiment logging/registry integration. 238 total repository tests passing.

### Phase 10: Testing, Monitoring and Final Validation (Future Work)
- **Goal:** Implement end-to-end integration tests, data drift monitoring via Evidently AI, and automated retraining pipelines in CI/CD.
- **Current Status:** **PENDING.**

