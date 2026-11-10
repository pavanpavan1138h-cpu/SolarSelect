# Problem Statement and Objectives — SolarSelect

## 1. Problem Statement

Distributed rooftop solar photovoltaics (PV) represent a massive growth frontier in clean energy transition. However, residential and commercial consumers face significant information asymmetry when investing in solar installations:

1. **Inaccurate Generation Estimates:** Installers frequently utilize simplistic "sun-hours" heuristics or static regional averages. These fail to account for how specific PV technologies (such as N-type TOPCon, Heterojunction, or Monocrystalline PERC) respond to local temperature extremes, diffuse cloud conditions, and high-ambient humidity.
2. **Thermal Performance Penalty Disregard:** In warm climates, solar modules routinely operate at cell temperatures exceeding 50°C. Depending on the cell technology, standard silicon panels lose between $0.26\%$ and $0.40\%$ of rated power for every degree above 25°C. Ignoring these temperature coefficients ($\gamma_{Pmp}$) leads to severe financial over-promising.
3. **Physical Roof-Fit Mismatches:** Consumers are often sold module types that fit poorly on their physical roof geometry. Module dimensions (length, width) vary significantly across manufacturers (e.g. 1.7m residential panels vs. 2.4m utility panels), directly impacting packing factors and balance-of-system (BOS) costs.
4. **Lack of Lifecycle Optimization:** Recommendations rarely balance upfront module cost against long-term annual degradation ($0.40\%/\text{year}$ for premium N-type vs. $0.70\%/\text{year}$ for legacy mono-PERC) and warranty coverage.
5. **Absence of Production-Grade MLOps:** Existing research prototypes in solar forecasting typically rely on offline, un-versioned Jupyter notebooks that leak temporal data, fail across seasonal transitions, and lack automated validation pipelines.

---

## 2. Project Objectives

SolarSelect was conceived to address these deficiencies through a unified MLOps framework. The project objectives are partitioned into primary functional goals and operational MLOps requirements:

### A. Machine Learning Objectives (Layer A)
- **Objective A1 (Target Formulation):** Define and validate a physically grounded, capacity-normalized target metric: Daily Specific Yield ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$).
- **Objective A2 (Leakage Prevention):** Implement a strictly chronological, day-ahead forecasting framework ($\tau \ge 24\text{h}$) ensuring zero feature leakage from future timestamps or same-day telemetry.
- **Objective A3 (Robust Multimodel Benchmarking):** Benchmark diverse algorithm families (linear, regularized, tree-based, ensemble boosting) against persistence and historical mean baselines.
- **Objective A4 (Seasonal Bias Mitigation):** Diagnose and mitigate seasonal underprediction errors across summer/winter transitions.
- **Objective A5 (Generalization Verification):** Demonstrate out-of-sample predictive generalization on a strictly quarantined held-out test partition.

### B. Hardware & Recommendation Objectives (Layer B)
- **Objective B1 (Canonical Hardware Catalogue):** Establish an auditable, 43-column commercial solar panel database capturing electrical, physical, thermal, lifetime, and economic parameters.
- **Objective B2 (Physical Roof-Fit Simulation):** Model 2D array placement, module orientation (portrait/landscape), setbacks, and packing factors on arbitrary rectangular roofs.
- **Objective B3 (Climate-Conditioned Simulation):** Modulate Layer A specific yield forecasts using panel-specific temperature coefficients, NOCT/NMOT ratings, and local temperature profiles.
- **Objective B4 (Constraint-Aware Multi-Criteria Optimization):** Rank feasible panel options based on net annual generation, Levelized Cost of Electricity (LCOE), payback period, and budget ceilings.
- **Objective B5 (Explainable Recommendations):** Provide transparent, human-readable explanations detailing why a specific panel was selected over alternatives.

### C. MLOps Lifecycle Objectives
- **Objective C1 (Data Versioning & Governance):** Maintain strict raw/interim/processed data separation with deterministic pipelines and data lineage.
- **Objective C2 (Automated Data Quality Validation):** Implement automated test suites validating physical laws (non-negative power, sub-Voc voltage, negative power temperature coefficients).
- **Objective C3 (Experiment Tracking & Model Registry):** Track model runs, hyperparameters, metrics, and serialized artifacts with audit metadata.
- **Objective C4 (Model Serving & User Interface):** Package forecasting and recommendation services into modern REST APIs (FastAPI) and interactive dashboards (Streamlit).
- **Objective C5 (Continuous Monitoring & Drift Detection):** Implement telemetry monitoring to detect data drift, concept drift, and performance degradation across operational seasons.

---

## 3. Scope Boundaries and Implementation Reality

> [!IMPORTANT]
> **Implementation Scope Distinction:**
> - **Completed & Experimentally Verified:** Objectives A1, A2, A3, A4, A5, and B1 (canonical schema and validation engine).
> - **In Progress:** Objective B1 (hardware catalogue population, currently pending external datasheet acquisition approval).
> - **Planned Future Scope:** Objectives B2–B5 (Phase 7 & 8) and C3–C5 (Phase 9 & 10).

