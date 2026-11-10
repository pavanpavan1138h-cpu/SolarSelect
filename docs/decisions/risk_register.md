# Risk Register — SolarSelect

This register documents technical, data-quality, deployment, model, financial, and governance risks across the SolarSelect project lifecycle.

---

## Authoritative Risk Register

| Risk ID | Risk Category | Risk Event / Threat Description | Inherent Severity | Planned or Active Mitigation Strategy | Implementation Status of Control | Residual Risk Level |
|---|---|---|---|---|---|---|
| **RSK-001** | Data Governance | **Unapproved External Datasheet Acquisition** | High | Strict data-source restriction enforced. Stakeholder explicitly authorized Phase 6 Prompt 2 acquisition. Ingested 12 verified manufacturer datasheets with 516-row field provenance audit. | **Controlled Acquisition Completed & Verified** | Low |
| **RSK-002** | Modeling | **Data Leakage in Time Series ML Pipelines** | High | Implemented 8-rule anti-leakage framework: day-ahead lags ($\tau \ge 24\text{h}$), chronological splits, date-grouped temporal CV, static training imputation. Note: Mitigations significantly reduce known leakage pathways, but temporal autocorrelation remains a structural challenge. | **Active Pipeline Protocols Implemented** | Low-to-Medium |
| **RSK-003** | Modeling | **Seasonal Concept Drift / Out-of-Bounds Saturation** | High | Retrained final evaluated models on combined pre-test data (10 months). Added analytical astronomical features ($H_0$, solar elevation) to anchor seasonal cycles. | **Active Pipeline Protocols Implemented** | Medium |
| **RSK-004** | Deployment | **Numerical Weather Prediction (NWP) Forecast Error** | Medium | Upstream weather forecast errors will propagate into yield forecasts. Sensitivity analysis and conformal prediction bands planned for Phase 8. | **Planned Future Control (Phase 8)** | Medium |
| **RSK-005** | Hardware Sizing | **Physical Roof Geometry Mismatch (Array Collision)** | High | Phase 7 Roof-Fit engine will model physical module outer dimensions ($L, W, T$), orientation, setbacks, and maintenance pathways. | **Planned Future Control (Phase 7)** | Medium |
| **RSK-006** | Financial | **Currency & Price Basis Incomparability** | High | Canonical schema requires explicit `currency`, `price_region`, and `price_basis` (distinguishing wholesale MW-scale from retail distributor pricing). | **Implemented in Schema & Validator** | Low |
| **RSK-007** | Governance | **Premature Test Set Exposure (Overfitting to Test Data)** | High | Test partition was sealed and quarantined until Phase 5 Prompt 3. Evaluated once on frozen models. No post-test tuning permitted. | **Executed & Verified Closed** | Low |
| **RSK-008** | Operations | **Telemetry Inverter Dropouts & Communication Loss** | Medium | Valid site-day filter requires $\ge 26/28$ core intervals. Days failing threshold are excluded. Single-day lag dropouts are imputed via training medians with quality flags. | **Active Heuristic Implemented** | Low-to-Medium |
| **RSK-009** | Engineering | **Environment Dependency Drift & Execution Failure** | Medium | Environment pinned in `requirements.txt` under Python 3.11. Headless `nbconvert` execution tests verified across all 12 notebooks. | **Active Control Verified** | Low |
| **RSK-010** | Engineering | **Structural & Wind Load Omission in 2D Geometry Engine** | High | 2D geometric fit does not assess roof dead load ($kg/m^2$) or wind uplift. Explicit disclaimer (LIM-014) embedded in output contract requiring licensed structural engineer sign-off. | **Engine Design Disclaimer Embedded** | Medium |
| **RSK-011** | Hardware Sizing | **Inter-Row Tilt Shading & Pitch Sensitivity** | Medium | Flush mounting assumes no row shading. Tilted flat roofs require dynamic pitch calculations based on winter solstice solar elevation to prevent intra-array shading losses. | **Planned Pitch Sizing Formula in Phase 8** | Low |
| **RSK-012** | Regulatory | **Statutory Clearance & Fire Walkway Non-Compliance** | Medium | Geometric setbacks and walkway corridors are user-configurable. Default $0.50\text{ m}$ setback is an illustrative simulation default, not a certified universal fire or building code compliance standard. System documentation explicitly requires user/installer to supply statutory clearance. | **Configurable Clearances & Regulatory Disclaimer** | Low |
