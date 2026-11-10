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
│ [Phase 6] Real Solar Panel Catalogue                ==> IN PROGRESS (P1)    │
│ [Phase 7] Roof-Fit & Panel Configuration Engine     ==> PENDING (FUTURE)    │
│ [Phase 8] Energy, Economics & Recommendation Engine ==> PENDING (FUTURE)    │
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
- **Prompt 1 Deliverables:** Repository inventory, canonical JSON schema, header-only template, baseline CSV, validation script `src/validate_panel_catalogue.py`.
- **Prompt 2 (Pending Approval):** Official manufacturer datasheet acquisition and population of commercial PV specifications.
- **Current Status:** **IN PROGRESS (PROMPT 1 COMPLETED; PROMPT 2 PENDING APPROVAL).**

### Phase 7: Roof-Fit and Panel Configuration Engine (Future Work)
- **Goal:** Model 2D rectangular array geometry, packing factor, module orientation, setbacks, and pitch/azimuth losses.
- **Current Status:** **PENDING.**

### Phase 8: Energy, Economics and Recommendation Engine (Future Work)
- **Goal:** Couple Layer A forecasts with hardware parameters to simulate annual energy, compute 25-year LCOE and payback, and rank panels via multi-criteria decision analysis (AHP / TOPSIS).
- **Current Status:** **PENDING.**

### Phase 9: Integration, Application and MLOps (Future Work)
- **Goal:** Package Layer A and Layer B into a REST API (FastAPI) and interactive consumer dashboard (Streamlit) with DVC data versioning and MLflow tracking.
- **Current Status:** **PENDING.**

### Phase 10: Testing, Monitoring and Final Validation (Future Work)
- **Goal:** Implement end-to-end integration tests, data drift monitoring via Evidently AI, and automated retraining pipelines in CI/CD.
- **Current Status:** **PENDING.**

