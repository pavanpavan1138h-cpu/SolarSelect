# Phase 9, Prompt 1: Application Architecture, Dashboard Design System & UI/UX Foundation Report

**Session:** 74  
**Date:** 2026-11-11  
**Project:** SolarSelect: An End-to-End MLOps System for AI-Based Solar Panel Selection  
**Deliverable:** Application Architecture, Reusable Component Library, Backend Service Boundary, and Interactive Streamlit Dashboard  
**Status:** COMPLETE — READY FOR BACKEND REST INTEGRATION  

---

## 1. Executive Summary

This session establishes the foundational application architecture, design system tokens, modular component library, backend service boundaries, and the multi-page interactive dashboard for **Phase 9** of Project SolarSelect.

The user mandate specifically required establishing an end-to-end software architecture and an interactive web interface adhering strictly to a **light theme + minimal professional SaaS aesthetic** (white/slate backgrounds, dark charcoal typography, restrained solar green accents, subtle borders; no dark mode, no neon green, no heavy gradients, no glassmorphism).

All prior Phase 1–8 analytical pipelines, ML model artifacts, real panel catalogues, and mathematical contracts have been preserved without modification. Real prospective candidate constraints (Decision B-1 unverified AC/DC metering, Decision B-2 prospective lag-yield policy, unpopulated commercial panel prices, unpopulated inverter specs) are strictly enforced in the UI: uncalculated metrics are never zeroed or fabricated, and synthetic layouts/curves are isolated behind explicit demonstration toggles labeled `DEMONSTRATION DATA ONLY`.

---

## 2. Existing Repository Architecture Discovered

Prior to writing application code, an exhaustive inspection of the repository structure was conducted:

1. **Layer A — Solar Yield Prediction (Phases 1–5):**
   - Trained ML model artifacts: `models/phase5/final/peer_cohort_ExtraTreesRegressor.joblib` and metadata `models/phase5/final_model_metadata.json`.
   - Feature engineering pipeline: `src/prepare_phase3_data.py` producing 29 normalized predictive features across 22 peer sites. Quarantined test performance: MAE 0.9050 kWh/kWp/day, RMSE 1.0700, $R^2 = +0.2580$.
2. **Layer B — Hardware Catalogue (Phase 6):**
   - Catalogue database: `configs/panels_catalogue.csv` containing 12 authenticated commercial PV modules spanning 6 distinct semiconductor technologies.
   - Reader interface: `src/energy_economics/catalogue.py` providing `ReadOnlyPanelCatalogue` and typed `PanelRecord` objects.
3. **Layer B — Spatial Roof-Fit Engine (Phase 7):**
   - Engine implementation: `src/roof_fit/` (`engine.py`, `placement_engine.py`, `usable_area.py`, `roof_validator.py`, `catalogue_adapter.py`, `serializer.py`).
   - Coordinate domain: Discrete integer coordinate space ($M = 10{,}000\text{ units/m}$, $0.1\text{ mm}$ resolution) utilizing deterministic row-wise strip packing with setback and obstacle avoidance.
4. **Layer B — Energy, Economics & Recommendation Engine (Phase 8):**
   - Unified engine: `src/energy_economics/engine.py` orchestrating Stages 1–10 (`EnergyEconomicsEngine`).
   - Strict governance: Preserves operational boundaries B-1, B-2, and unpopulated commercial costs/inverters by disqualifying unfeasible panels and propagating `RECOMMENDATION_NOT_EVALUATED` for prospective roofs.
5. **Pre-existing Test Baseline:**
   - 231 passing automated tests (126 Phase 7 tests + 105 Phase 8 tests).

---

## 3. Application Architecture Selected

To preserve separation of concerns and facilitate future microservice scaling, a decoupled architecture was established:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       STREAMLIT PRESENTATION TIER                           │
│  app/frontend/main.py  (Multi-page router, sidebar branding & status)      │
│  app/frontend/styles/  (Tokens: theme.py; SaaS styling: custom.css)         │
│  app/frontend/components/ui.py (Reusable badges, banners, cards, headers)   │
│  app/frontend/pages/   (Overview, Roof Config, Energy, Financial,           │
│                         Recommendations, MLOps Centre)                      │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ Direct typed Python invocations
                                       ▼ (Ready for FastAPI HTTP endpoints)
┌─────────────────────────────────────────────────────────────────────────────┐
│                          BACKEND SERVICE BOUNDARY                           │
│  app/backend/services.py (SolarSelectPlatformService)                       │
│  app/backend/schemas.py  (Pydantic V2 Request/Response validation models)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    ▼                                     ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────────┐
│     LAYER A: ML INFERENCE ENGINE     │  │   LAYER B: ROOF-FIT & RECOMMEND   │
│  models/phase5/final/                │  │  src/roof_fit/                    │
│  src/energy_economics/inference.py   │  │  src/energy_economics/            │
│  src/energy_economics/historical_*   │  │  configs/panels_catalogue.csv     │
└──────────────────────────────────────┘  └───────────────────────────────────┘
```

- **Frontend:** Streamlit 1.51.0 multi-page application configured via `.streamlit/config.toml` (`client.showSidebarNavigation = false` to preserve customized clean branding).
- **Backend Service Layer:** Decoupled `SolarSelectPlatformService` mediating between UI and Phase 6/7/8 core libraries.
- **Contract Models:** Pydantic 2.12.4 schemas ensuring strict validation of roof geometry, obstacle coordinates, and system responses.

---

## 4. Dashboard Navigation and Page Structure

The application features 6 dedicated pages accessible via the persistent branded sidebar:

| Page | File | Primary Responsibility | Governance & Integrity Enforcement |
|---|---|---|---|
| **Overview** | `app/frontend/pages/overview.py` | Platform KPI metrics, 4-stage pipeline explanation, 12-panel catalogue table, and system limitations register. | Transparently surfaces B-1, B-2, and unpopulated commercial pricing caveats upon platform entry. |
| **Roof Configuration** | `app/frontend/pages/roof_config.py` | Interactive inputs for roof dimensions, perimeter setbacks, central walkway, obstacle definitions, and panel selection. | Quantizes inputs to discrete integer units; verifies that gross area exceeds setback envelopes before triggering placement. |
| **Energy Analysis** | `app/frontend/pages/energy_analysis.py` | Year-1 specific yield, monthly generation, and 25-year degradation profiles. | Surfaces B-1/B-2 warnings; requires explicit toggle for synthetic baseline comparison (`DEMONSTRATION DATA ONLY`). |
| **Financial Analysis** | `app/frontend/pages/financial_analysis.py` | System CAPEX, OPEX, NPV, payback period, and LCOE evaluation. | Displays informational banner that commercial prices are unpopulated; provides DCF demonstration behind explicit toggle. |
| **Recommendations** | `app/frontend/pages/recommendations.py` | Multi-criteria hardware recommendations, Pareto frontier, and constraint explanations. | Enforces `RECOMMENDATION_NOT_EVALUATED` for prospective roofs; synthetic Pareto frontier isolated behind demonstration toggle. |
| **Model & MLOps Centre** | `app/frontend/pages/mlops_centre.py` | Phase 5 model benchmark metrics, chronological splits, 29-feature schema table, and MLflow/DVC tracking status. | Displays ExtraTrees test metrics (MAE 0.9050, $R^2 = +0.2580$) and outlines continuous drift monitoring hooks. |

---

## 5. Design System and Styling Decisions

To satisfy the strict design requirements, a bespoke SaaS design token system was implemented:

- **Color Palette:**
  - Base Background: Pure White (`#FFFFFF`)
  - Secondary Background: Subtle Slate (`#F8FAFC`)
  - Typography: Dark Charcoal (`#0F172A`), Slate Grey (`#334155`), Muted Slate (`#64748B`)
  - Borders: Light Slate (`#E2E8F0`), Hover Slate (`#CBD5E1`)
  - Primary Accent: Restrained Solar Green (`#15803D`)
  - Semantic Status: Success (`#166534` on `#F0FDF4`), Warning (`#92400E` on `#FFFBEB`), Error (`#991B1B` on `#FEF2F2`), Neutral (`#475569` on `#F1F5F9`)
- **Typography:** Modern clean sans-serif system stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
- **Reusable Component Library (`app/frontend/components/ui.py`):**
  - `render_page_header`: Clean breadcrumb and page title.
  - `render_metric_card`: SaaS KPI card with optional semantic badge.
  - `render_status_badge`: Pill badge with semantic dot/icon.
  - `render_banner`: Alert strip with left accent border (info, warning, error, success).
  - `render_step_card`: Workflow stage box.
  - `render_empty_state`: Dashed border container for unconfigured or unevaluated states.

---

## 6. Files Created

1. `.streamlit/config.toml` — Streamlit light theme, headless mode, and sidebar navigation configuration.
2. `app/__init__.py` — Package root.
3. `app/backend/__init__.py` — Backend package root.
4. `app/backend/schemas.py` — Pydantic schemas for roof geometry, obstacles, and system status.
5. `app/backend/services.py` — Platform service layer wrapping Phase 6 catalogue and Phase 7 roof-fit engine.
6. `app/frontend/__init__.py` — Frontend package root.
7. `app/frontend/styles/__init__.py` — Styles package root.
8. `app/frontend/styles/theme.py` — Central design tokens (palette, spacing, radius, typography).
9. `app/frontend/styles/custom.css` — SaaS CSS stylesheet classes (`.ss-card`, `.ss-banner`, etc.).
10. `app/frontend/components/__init__.py` — UI components package root.
11. `app/frontend/components/ui.py` — Reusable presentation component library.
12. `app/frontend/pages/__init__.py` — Pages package root.
13. `app/frontend/pages/overview.py` — Overview Dashboard page.
14. `app/frontend/pages/roof_config.py` — Roof Configuration page.
15. `app/frontend/pages/energy_analysis.py` — Energy Analysis page.
16. `app/frontend/pages/financial_analysis.py` — Financial Analysis page.
17. `app/frontend/pages/recommendations.py` — Hardware Recommendations page.
18. `app/frontend/pages/mlops_centre.py` — Model & MLOps Centre page.
19. `app/frontend/main.py` — Application entry point, router, and branding sidebar.
20. `tests/test_phase9_app_foundation.py` — Automated test suite covering service methods, schemas, tokens, badges, and AppTest navigation.
21. `reports/phase9/screenshots/dashboard_overview.png` — Rendered dashboard screenshot.

---

## 7. Files Modified

1. `docs/project/phase_completion_status.md` — Updated Phase 9 status to `IN PROGRESS (Prompt 1 UI Shell Complete)`.
2. `docs/project/project_roadmap.md` — Updated Phase 9 roadmap entry to reflect active UI shell.
3. `log.txt` — Appended chronological Session 74 log entry.

---

## 8. Files Deliberately Left Untouched

In strict adherence to project governance, the following directories and artifacts were preserved without any alteration:
- Phase 1–5 datasets (`data/raw/`, `data/processed/`), feature preparation scripts (`src/prepare_phase3_data.py`), and serialized ML models (`models/phase5/final/`).
- Phase 6 commercial panel catalogue (`configs/panels_catalogue.csv`), validation schema, and compiled datasheets.
- Phase 7 geometry placement engine (`src/roof_fit/`) and its 126 automated tests.
- Phase 8 energy, economics, and recommendation modules (`src/energy_economics/`) and its 105 automated tests.
- Phase 10 drift monitoring and CI/CD pipelines (uncommenced).

---

## 9. Dependencies Added

**None.**  
The current virtual environment already satisfied all technical requirements:
- `streamlit` (v1.51.0)
- `pydantic` (v2.12.4)
- `plotly` (v6.3.0)
- `pytest` (v8.4.2)

---

## 10. Commands to Run the Dashboard

To launch the interactive dashboard in a local browser:

```bash
streamlit run app/frontend/main.py
```

The server binds by default to `http://localhost:8501`.

---

## 11. Test Commands and Actual Results

The full test suite was executed to verify Phase 9 additions and ensure zero regression across Phase 7 and Phase 8:

```bash
pytest -v tests/test_phase9_app_foundation.py
pytest -q tests/
```

### Execution Results:
```text
============================== test session starts ==============================
platform darwin -- Python 3.13.9, pytest-8.4.2, pluggy-1.5.0
collected 7 items

tests/test_phase9_app_foundation.py::test_platform_service_status PASSED        [ 14%]
tests/test_phase9_app_foundation.py::test_platform_service_catalogue_summary PASSED [ 28%]
tests/test_phase9_app_foundation.py::test_platform_service_limitations PASSED  [ 42%]
tests/test_phase9_app_foundation.py::test_pydantic_schemas PASSED               [ 57%]
tests/test_phase9_app_foundation.py::test_ui_theme_tokens PASSED                [ 71%]
tests/test_phase9_app_foundation.py::test_status_badge_html_rendering PASSED   [ 85%]
tests/test_phase9_app_foundation.py::test_streamlit_app_navigation PASSED      [100%]

============================== 7 passed in 1.10s ===============================

238 passed in 4.25s
```

- Phase 7 Test Suite: 126 / 126 passed.
- Phase 8 Test Suite: 105 / 105 passed.
- Phase 9 Foundation Suite: 7 / 7 passed.
- **Total Test Suite:** 238 passed, 0 failed, 0 regressions.

---

## 12. Visual Verification

The rendered dashboard was inspected via headless Chrome CDP capture at `1440x1080` resolution.

- **Captured File:** [`reports/phase9/screenshots/dashboard_overview.png`](screenshots/dashboard_overview.png)
- **Visual Validation:**
  - Background is crisp white (`#FFFFFF`) and slate (`#F8FAFC`).
  - Typography is high-contrast charcoal (`#0F172A`) with solar green accents (`#15803D`).
  - Metric cards and workflow cards render with 1px subtle borders (`#E2E8F0`).
  - Hardware catalogue dataframe renders 12 commercial modules cleanly.
  - Sidebar exhibits clean branding with navigation radio buttons and platform status indicators.

---

## 13. Known Limitations & Operational Boundaries

1. **Demonstration Data Isolation:** Energy and financial charts utilize simulated profiles for visual demonstration and are clearly flagged as `DEMONSTRATION DATA ONLY`. Real prospective candidate calculations remain pending full backend wiring.
2. **Phase 8 Governance Boundaries:** Real unbuilt rooftops evaluate strictly to `RECOMMENDATION_NOT_EVALUATED` due to Decision B-2 (prospective lag-yield policy).
3. **Commercial Pricing Absence:** Phase 6 commercial panel AUD/W prices remain unpopulated; financial metrics require explicit user cost ledger inputs.
4. **FastAPI Serving Layer:** The REST API service boundary is currently modeled through `SolarSelectPlatformService` and will be exposed via FastAPI in subsequent Phase 9 prompts.

---

## 14. Recommended Next Implementation Task

**Phase 9, Prompt 2: FastAPI Service Layer & Interactive Layout Engine Integration**
1. Implement FastAPI REST routes (`app/backend/api.py`) exposing geometry validation, catalogue lookup, and roof-fit computation.
2. Wire the Streamlit Roof Configuration page directly to the Phase 7 `RoofFitEngine` to compute and visualize interactive 2D rooftop packing layouts in real time.
3. Integrate Plotly 2D spatial roof polygon rendering showing panel bounding boxes, setbacks, walkways, and keep-out obstacles.

