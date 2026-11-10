# SolarSelect — Central Technical Documentation Portal

Welcome to the authoritative technical documentation for **SolarSelect: An End-to-End MLOps System for AI-Based Solar Panel Selection**.

This documentation suite serves as the single source of truth for the project's scientific foundation, software architecture, machine learning models, data governance, empirical results, and MLOps lifecycle. It distinguishes strictly between **what has been implemented and experimentally verified** versus **what is planned for future phases**.

---

## Documentation Roadmap & Directory Structure

```text
docs/
├── README.md                                  # Documentation portal & navigation index (this file)
│
├── project/                                   # Project Identity, Scope & Architecture
│   ├── project_overview.md                    # Vision, two-layer concept, core value proposition
│   ├── problem_statement_and_objectives.md    # Real-world problem, research gaps, project targets
│   ├── system_architecture.md                 # Implemented vs. planned architectures & Mermaid flows
│   ├── project_roadmap.md                     # 10-phase project lifecycle and milestone delivery
│   └── phase_completion_status.md             # Authoritative audit status across all 10 phases
│
├── data/                                      # Data Governance, Datasets & Preprocessing
│   ├── dataset_inventory.md                   # Full inventory of Kaggle & UNISOLAR raw/processed data
│   ├── data_dictionary.md                     # Comprehensive schemas, units, and data types
│   ├── data_governance_and_provenance.md      # Leakage boundaries, quarantine protocols, licensing
│   ├── preprocessing_methodology.md           # Filtering, valid site-day rules, imputation, splits
│   └── data_limitations.md                    # Missingness, sensor quantization, Site 19/24 anomalies
│
├── machine_learning/                          # Layer A: Specific Yield Forecasting Models
│   ├── target_definition.md                   # Daily specific yield (kWh/kWp/day) formulation
│   ├── feature_engineering.md                 # 29 predictive inputs, lag construction, astronomy
│   ├── model_development.md                   # Baselines, 8 algorithms, 4-fold expanding-window CV
│   ├── model_evaluation.md                    # Diagnostics, bias decomposition, ensemble experiments
│   ├── final_model_reference.md               # Tuned ExtraTrees, ElasticNet, test set metrics & artifacts
│   └── model_limitations.md                   # Seasonality, spatial transfer, lack of NWP forecasts
│
├── panel_catalogue/                           # Layer B: Hardware Database & Standards
│   ├── catalogue_schema.md                    # Canonical 43-column schema across 8 domains
│   ├── catalogue_inventory.md                 # Existing repository records vs. Appendix B claims
│   ├── validation_rules.md                    # Engineering, physical, electrical, and pricing rules
│   └── source_verification_policy.md          # Provenance verification, external datasheet request
│
├── engineering/                               # Reproducibility, Environment & Operations
│   ├── repository_structure.md                # Directory layout, artifact paths, and file roles
│   ├── environment_setup.md                   # Python 3.11 virtual environment, dependencies
│   ├── execution_guide.md                     # CLI data prep, validation, model training execution
│   └── reproducibility.md                     # Seed control, deterministic splits, verification logs
│
├── decisions/                                 # Living Project Governance Registers
│   ├── decision_register.md                   # Chronological ADRs (Architectural Decision Records)
│   ├── assumptions_register.md                # Scientific & operational assumptions log
│   ├── limitations_register.md                # Comprehensive technical & hardware limitations
│   └── risk_register.md                       # Technical, deployment, data-quality, and governance risks
│
└── reports/                                   # Historical Implementation Records
    └── phase_wise_implementation_history.md   # Chronological deep-dive across Phases 1 to 6
```

---

## High-Level Implementation Snapshot (Phases 1–10)

| Phase | Phase Name | Status | Primary Output / Verification |
|---|---|---|---|
| **Phase 1** | Dataset Collection and Inspection | **COMPLETED** | Verified Kaggle (2 plants) & UNISOLAR (42 sites) raw datasets |
| **Phase 2** | EDA and Data Understanding | **COMPLETED** | 6 standalone notebooks, verified valid site-day filter, capacity audit |
| **Phase 3** | Target Definition and Data Preparation | **COMPLETED WITH LIMITATIONS** | Dual cohorts (Full 24-site / Peer 22-site), 29 features, chronological splits |
| **Phase 4** | Baseline & ML Model Development | **COMPLETED WITH LIMITATIONS** | 3 baselines, 8 algorithms, 4-fold expanding-window temporal CV |
| **Phase 5** | Model Evaluation & Finalization | **COMPLETED WITH LIMITATIONS** | Quarantined test evaluation, bias resolution, ExtraTrees & ElasticNet accepted |
| **Phase 6** | Real Solar Panel Catalogue | **IN PROGRESS (P1 DONE)** | Canonical 43-column schema, validator, 3 unverified raw entries; datasheet request pending |
| **Phase 7** | Roof-Fit & Configuration Engine | **PENDING** | Future work (Layer B physical layout & packing factor) |
| **Phase 8** | Energy, Economics & Recommendation | **PENDING** | Future work (Layer B LCOE, payback, multi-criteria ranking) |
| **Phase 9** | Integration, Application & MLOps | **PENDING** | Future work (FastAPI/Streamlit serving, DVC, MLflow tracking) |
| **Phase 10** | Testing, Monitoring & Validation | **PENDING** | Future work (Evidently drift monitoring, automated CI/CD retraining) |

---

## How to Navigate This Documentation

- **To understand the scientific concept and system architecture:** Start with [`docs/project/project_overview.md`](project/project_overview.md) and [`docs/project/system_architecture.md`](project/system_architecture.md).
- **To review data handling and leakage prevention:** See [`docs/data/data_governance_and_provenance.md`](data/data_governance_and_provenance.md) and [`docs/data/preprocessing_methodology.md`](data/preprocessing_methodology.md).
- **To inspect the validated forecasting models:** Read [`docs/machine_learning/final_model_reference.md`](machine_learning/final_model_reference.md).
- **To inspect the hardware catalogue schema and validator:** Read [`docs/panel_catalogue/catalogue_schema.md`](panel_catalogue/catalogue_schema.md) and [`docs/panel_catalogue/validation_rules.md`](panel_catalogue/validation_rules.md).
- **To reproduce the pipeline from scratch:** Follow the step-by-step instructions in [`docs/engineering/execution_guide.md`](engineering/execution_guide.md).
- **To review project governance, decisions, and risks:** Consult the registers in [`docs/decisions/`](decisions/).

