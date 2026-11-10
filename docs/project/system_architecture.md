# System Architecture — SolarSelect

This document details the architectural design of **SolarSelect**. In strict compliance with engineering governance standards, every architectural component is categorized into one of three statuses:
- **[IMPLEMENTED]**: Fully coded, tested, and experimentally verified in the repository.
- **[PARTIAL]**: Partially constructed (e.g. schema and validation scripts complete, but data population pending approval).
- **[PLANNED]**: Designed architecture slated for implementation in future phases.

---

## 1. Overall SolarSelect System Architecture

The overarching system integrates telemetry data pipelines, predictive machine learning models, hardware cataloguing, constraint optimization, and operational MLOps serving:

```mermaid
graph TD
    classDef implemented fill:#2ca02c,stroke:#1b611b,color:#fff;
    classDef partial fill:#ff7f0e,stroke:#c45f06,color:#fff;
    classDef planned fill:#7f7f7f,stroke:#4f4f4f,color:#fff,stroke-dasharray: 5 5;

    subgraph Ingestion["1. Data Ingestion & Storage"]
        RawKaggle["Raw Kaggle Data (2 Plants) [IMPLEMENTED]"]:::implemented
        RawUnisolar["Raw UNISOLAR Data (42 Sites) [IMPLEMENTED]"]:::implemented
        DVC["DVC Pipeline Tracking [IMPLEMENTED]"]:::implemented
    end

    subgraph MLPipeline["2. Layer A: Forecasting Engine"]
        PrepScript["Data Prep: prepare_phase3_data.py [IMPLEMENTED]"]:::implemented
        TrainValTest["Chronological Split: Train/Val/Test [IMPLEMENTED]"]:::implemented
        Models["ML Models: Tuned ExtraTrees & ElasticNet [IMPLEMENTED]"]:::implemented
        Evaluation["Held-Out Test Evaluation [IMPLEMENTED]"]:::implemented
        ModelArtifacts["Model Artifacts & JSON Metadata [IMPLEMENTED]"]:::implemented
    end

    subgraph Catalogue["3. Hardware Database"]
        Schema["Canonical 43-Column Schema [IMPLEMENTED]"]:::implemented
        Validator["Validation Script: validate_panel_catalogue.py [IMPLEMENTED]"]:::implemented
        CatCSV["Catalogue CSV (3 Unverified Entries) [PARTIAL]"]:::partial
        Datasheets["Official Manufacturer Datasheets [PLANNED]"]:::planned
    end

    subgraph Recommendation["4. Layer B: Recommendation Engine"]
        RoofFit["Roof-Fit 2D Array Packing [PLANNED]"]:::planned
        EnergySim["Climate-Conditioned Simulation [PLANNED]"]:::planned
        LCOEOpt["LCOE & Payback Optimization [PLANNED]"]:::planned
        RecOutput["Ranked Multi-Criteria Output [PLANNED]"]:::planned
    end

    subgraph MLOpsLifecycle["5. MLOps Serving & Monitoring"]
        FastAPI["FastAPI REST Inference Service [PLANNED]"]:::planned
        StreamlitUI["Streamlit Interactive UI [PLANNED]"]:::planned
        Evidently["Evidently Drift Monitoring [PLANNED]"]:::planned
        CICD["GitHub Actions CI/CD Retraining [PLANNED]"]:::planned
    end

    RawUnisolar --> PrepScript
    DVC -.-> PrepScript
    PrepScript --> TrainValTest
    TrainValTest --> Models
    Models --> Evaluation
    Evaluation --> ModelArtifacts

    ModelArtifacts --> EnergySim
    Schema --> Validator
    CatCSV --> Validator
    Datasheets -.-> CatCSV
    CatCSV --> RoofFit
    CatCSV --> EnergySim

    RoofFit --> LCOEOpt
    EnergySim --> LCOEOpt
    LCOEOpt --> RecOutput

    RecOutput -.-> FastAPI
    FastAPI -.-> StreamlitUI
    StreamlitUI -.-> Evidently
    Evidently -.-> CICD
```

---

## 2. Current Implemented ML Data Pipeline (Phases 1–3)

The data pipeline transforms raw campus telemetry into leakage-free ML training matrices:

```mermaid
flowchart TD
    classDef impl fill:#2ca02c,stroke:#1b611b,color:#fff;
    classDef excluded fill:#d62728,stroke:#941314,color:#fff;

    R1["Raw UNISOLAR Generation (1.5M rows)"]:::impl --> Filter["Valid Site-Day Filter (96 intervals, ≥26 core non-null)"]:::impl
    R2["Raw Weather Data (264k rows)"]:::impl --> Align["Timestamp Alignment & Weather Aggregation"]:::impl
    R3["Solar Site Details (42 sites)"]:::impl --> Cohort["Cohort Partitioning"]:::impl

    Filter --> Clean["7,039 Valid Site-Days"]:::impl
    Align --> Clean
    Cohort --> FullCohort["Dataset A: Full Cohort (24 Sites, N=7,039)"]:::impl
    Cohort --> PeerCohort["Dataset B: Peer Cohort (22 Sites, N=6,456)"]:::impl
    Cohort --> Excluded["Excluded: 17 sites lacking kWp + Sites 28-29"]:::excluded

    Clean --> FeatEng["Feature Engineering: 29 Predictive Features"]:::impl
    FeatEng --> ChronoSplit["Chronological Partitioning"]:::impl

    ChronoSplit --> Train["Train: 2021-05-01 to 2021-12-31 (N=4,770 Full / 4,383 Peer)"]:::impl
    ChronoSplit --> Val["Val: 2022-01-01 to 2022-02-28 (N=1,037 Full / 945 Peer)"]:::impl
    ChronoSplit --> Test["Test: 2022-03-01 to 2022-04-23 (N=1,232 Full / 1,128 Peer) [QUARANTINED]"]:::impl
```

---

## 3. Layer A Forecasting Workflow (Phases 4–5)

The production forecasting workflow fits models on pre-test data and produces day-ahead specific yield estimates:

```mermaid
flowchart LR
    classDef model fill:#1f77b4,stroke:#0f4f7a,color:#fff;
    classDef artifact fill:#ff7f0e,stroke:#c45f06,color:#fff;
    classDef metric fill:#2ca02c,stroke:#1b611b,color:#fff;

    PreTest["Combined Pre-Test Data (Train + Val, N=5,328 Peer)"] --> FitPeer["Fit Tuned ExtraTrees (n=100, d=12, f=0.8)"]:::model
    PreTestFull["Combined Pre-Test Data (Train + Val, N=5,807 Full)"] --> FitFull["Fit Tuned ElasticNet (α=0.05, l1=0.90)"]:::model

    FitPeer --> ArtPeer["models/phase5/final/peer_cohort/final_extra_trees.joblib"]:::artifact
    FitFull --> ArtFull["models/phase5/final/full_cohort/final_elastic_net.joblib"]:::artifact

    ArtPeer --> EvalPeer["Held-Out Test Evaluation (March 1 – April 23, 2022)"]
    ArtFull --> EvalFull["Held-Out Test Evaluation (March 1 – April 23, 2022)"]

    EvalPeer --> MetricsPeer["Peer: MAE=0.9050, RMSE=1.0700, R²=+0.2580 (ACCEPTED)"]:::metric
    EvalFull --> MetricsFull["Full: MAE=1.1463, RMSE=1.9494, R²=+0.7407 (CONDITIONAL)"]:::metric
```

---

## 4. Intended Layer B Recommendation Workflow (Phases 6–8)

The downstream recommendation engine couples Layer A forecasts with hardware parameters to optimize panel choices:

```mermaid
flowchart TD
    classDef implemented fill:#2ca02c,stroke:#1b611b,color:#fff;
    classDef partial fill:#ff7f0e,stroke:#c45f06,color:#fff;
    classDef planned fill:#7f7f7f,stroke:#4f4f4f,color:#fff,stroke-dasharray: 5 5;

    UserInput["Client Inputs: Roof Dimensions, Azimuth, Tilt, Budget"]:::planned --> RoofFit["Roof-Fit Engine: 2D Geometry & Orientation"]:::planned
    
    CatDB["Canonical Panel Catalogue [PARTIAL]"]:::partial --> RoofFit
    CatDB --> YieldAdj["Climate & Thermal Yield Adjustment"]:::planned
    
    LayerAYield["Layer A ML Forecast: Y_f (kWh/kWp/day) [IMPLEMENTED]"]:::implemented --> YieldAdj
    AmbientTemp["Site Ambient Temperature Profile"]:::planned --> YieldAdj

    YieldAdj --> SimGen["Simulated Annual Energy Yield (kWh)"]:::planned
    RoofFit --> PanelCount["Feasible Panel Count & Array kWp"]:::planned

    SimGen --> FinModel["Financial Engine: CAPEX, 25-yr LCOE, Payback"]:::planned
    PanelCount --> FinModel
    Degradation["Warranted Annual Degradation d_annual"]:::planned --> FinModel

    FinModel --> Ranking["Multi-Criteria Scoring Engine (AHP / TOPSIS)"]:::planned
    Ranking --> RecReport["Final Recommendation Report & Trade-Off Matrix"]:::planned
```

---

## 5. Intended End-to-End MLOps Lifecycle (Phases 9–10)

The operational deployment architecture includes automated serving, experiment tracking, and drift retraining:

```mermaid
flowchart TD
    classDef planned fill:#7f7f7f,stroke:#4f4f4f,color:#fff,stroke-dasharray: 5 5;
    classDef partial fill:#ff7f0e,stroke:#c45f06,color:#fff;
    classDef impl fill:#2ca02c,stroke:#1b611b,color:#fff;

    Dev["Model Development & Codebase"]:::impl --> Git["GitHub Repository & Actions CI"]:::planned
    Dev --> DVCStorage["DVC Remote Data Registry"]:::partial
    Dev --> MLflowRegistry["MLflow Model Registry [PLANNED]"]:::planned

    MLflowRegistry --> Container["Docker Containerized REST API (FastAPI) [PLANNED]"]:::planned
    Container --> WebApp["Streamlit Interactive Web UI [PLANNED]"]:::planned

    Client["User / Solar Installer"] --> WebApp
    WebApp --> Monitoring["Telemetry & Prediction Logging [PLANNED]"]:::planned

    Monitoring --> Evidently["Evidently AI Drift Monitoring [PLANNED]"]:::planned
    Evidently --> DriftAlert{"Drift Detected? (KS-Test p < 0.05)"}:::planned

    DriftAlert -- Yes --> TriggerRetrain["Trigger Automated Retraining Workflow"]:::planned
    DriftAlert -- No --> Stable["Continue Operational Serving"]:::planned
    TriggerRetrain --> Git
```

