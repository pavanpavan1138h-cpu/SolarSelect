# Phase 8 Stage 3: Energy Estimation Engine & Scenario Handling Report

**SolarSelect MLOps Engineering Laboratory**  
**Lifecycle Stage:** Phase 8 — Stage 3: Energy Estimation Engine & Scenario Handling  
**Status:** Completed with Documented Limitations (Under Review)  
**Session:** Session 61 (Documentation & Roadmap Reconciliation)  
**Date:** 2026-11-11  
**Author:** SolarSelect Engineering Team  

---

## 1. Executive Summary

Phase 8 Stage 3 implements the dedicated energy estimation and scenario handling engine ([`Phase8EnergyEstimationEngine`](../../src/energy_economics/energy_engine.py)). Operating on top of the accepted Stage 1 foundation layer and Stage 2 inference/historical replay interface, Stage 3 establishes a rigorous, mathematically verified energy estimation contract.

Stage 3 preserves all unresolved scientific, physical, and modeling limitations without exception:
- **No Double Scaling:** Capacity multiplication ($E_{daily} = \hat{Y} \times kWp$) happens strictly once, with full verification against incoming Stage 2 records. Discrepancies $> 10^{-4}$ trigger an explicit arithmetic validation error.
- **Strict Unit Consistency:** All outputs explicitly preserve units: specific yield in `kWh/kWp/day`, daily energy in `kWh/day`, aggregated energy in `kWh`, and capacity in `kWp`.
- **Decision D-4 Governance (Distinction Between Implemented Behavior & Unresolved Policy):**
  * *Implemented:* Raw negative specific yields ($\hat{Y}_i < 0.0$) and raw mathematical daily energies ($E_{raw, i} = \hat{Y}_i \times kWp_i$) are preserved unclipped for numerical transparency. Negative predictions are explicitly flagged with `prediction_status = "NEGATIVE_PREDICTION_WARNING"` and excluded from accepted positive generation (`accepted_positive_daily_energy_kwh = None`), contributing 0.0 kWh to positive aggregate sums. No clipping or zero substitution is applied to raw mathematical outputs.
  * *Unresolved:* The formal operational policy for negative predictions remains open under Decision D-4. No physical correction or operational clipping policy has been authorized. Stage 3 provides an accounting and disclosure framework, not an authorized operational clipping decision.
- **Blocking Issue B-1 Governance:** All energy outputs remain qualified as `energy_basis = "UNVERIFIED"`. No AC/DC conversion losses, system derates, temperature adjustments, or tilt/orientation corrections are applied.
- **Blocking Issue B-2 Governance:** Prospective unbuilt roof scenarios remain strictly blocked with `prediction_status = "PREDICTION_PENDING_LAG_POLICY"`. Zero model inference passes with fabricated lag values or synthetic weather profiles are executed.
- **Observed-Period Contract:** Outputs represent observed-period totals only (`historical_year_status = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"`). No 365-day annual extrapolation or scaling factors are applied.

---

## 2. Approved Phase 8 Stage Roadmap

To ensure alignment across all Phase 8 documentation and components, the authoritative Phase 8 stage roadmap is defined as follows:

| Stage | Stage Name & Scope | Status | Notes |
| :--- | :--- | :--- | :--- |
| **Stage 1** | Foundation & Phase 6/7 Integration | **COMPLETE** | Ingestion adapter, read-only catalogue, marginal capacity-support evaluator. |
| **Stage 2** | Phase 5 Inference & UNISOLAR Historical Replay | **ACCEPTED** | Predictor interface, 29-feature enforcement, chronological replay, blend verification. |
| **Stage 3** | Energy Estimation & Scenario Handling | **CURRENTLY UNDER REVIEW** | Energy arithmetic, scenario router, raw vs accepted separation, observed-period aggregation. |
| **Stage 4** | Temperature Evaluation (Method A/B) | **SCHEDULED NEXT** | Cell/ambient temperature modeling (Method A: simple NOCT; Method B: cell temperature model). |
| **Stage 5** | Annualization & Lifetime Energy | **PLANNED** | Multi-year profiles, calendar coverage checks, representative annual aggregation. |
| **Stage 6** | Degradation Modelling | **PLANNED** | Compounded vs linear module degradation trajectories over asset lifecycle. |
| **Stage 7** | System Cost & Financial Evaluation | **PLANNED** | CAPEX, OPEX, DC-to-AC replacement, LCOE, NPV, simple payback period. |
| **Stage 8** | Feasibility Filtering & Electrical Evaluation | **PLANNED** | Voltage compatibility, inverter sizing ratio, roof structural checks. |
| **Stage 9** | Pareto & Weighted Ranking | **PLANNED** | Multi-objective ranking across energy yield, LCOE, NPV, and payback. |
| **Stage 10** | Recommendation & Explanation Engine | **PLANNED** | Final multi-candidate recommendation synthesis, caveats, and explainability summaries. |

> [!IMPORTANT]
> **Roadmap Corrections Reconciled in Session 61:**
> - Stage 4 is **Temperature Evaluation (Method A/B)** — it is *not* the financial engine.
> - Stage 5 is **Annualization and Lifetime Energy** — it is *not* Pareto ranking.
> - Financial calculations belong exclusively to **Stage 7 (System Cost & Financial Evaluation)**.
> - Pareto and weighted ranking belong exclusively to **Stage 9 (Pareto & Weighted Ranking)**.
> - No future stages have been initiated, reordered, or implemented.

---

## 3. Architecture & Component Reuse

Stage 3 is designed to avoid duplicate computation while enforcing strict domain contracts:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 8 Architecture                            │
├────────────────────────────────────────────────────────────────────────┤
│ Stage 1: Foundation Layer (Phase8FoundationEngine)                     │
│   ├── Phase 7 Geometry Ingestion (Phase7Adapter)                       │
│   ├── Phase 6 Catalogue Integration (ReadOnlyPanelCatalogue)           │
│   └── Training-Capacity Support Evaluator (CapacitySupportEvaluator)   │
├────────────────────────────────────────────────────────────────────────┤
│ Stage 2: Inference & Historical Replay Interface                       │
│   ├── Phase5PeerCohortPredictor (29-feature enforcement, ET + Blend)   │
│   └── UNISOLARHistoricalReplayEngine (Chronological replay, In/OOS)    │
├────────────────────────────────────────────────────────────────────────┤
│ Stage 3: Energy Estimation Engine (Phase8EnergyEstimationEngine)       │
│   ├── Scenario Input Contract & Routing Router                         │
│   ├── Daily Energy Arithmetic & Capacity Integrity Check               │
│   ├── Raw vs Accepted Positive Energy Accounting (D-4 Open Policy)     │
│   ├── Ground Truth vs Model Energy Differentiation                     │
│   └── Observed-Period Site & Cohort Aggregation Engine                 │
└────────────────────────────────────────────────────────────────────────┘
```

### Reused vs New Responsibilities:
- **Reused from Stage 2:** Model loading (`final_extra_trees.joblib`, `final_elastic_net.joblib`), 29-feature ordering/validation, SHA-256 fingerprinting, raw prediction generation, and dataset ingestion.
- **New in Stage 3:**
  1. Dedicated scenario router governing `HISTORICAL_REPLAY`, `REPRESENTATIVE_PERIOD`, and `PROSPECTIVE_ROOF`.
  2. Arithmetic validation guaranteeing capacity is multiplied exactly once.
  3. Ground-truth vs model-estimated energy distinction (`actual_daily_energy_kwh = actual_target_daily_yield * kWp`).
  4. Typed separation between raw mathematical energy (`raw_mathematical_daily_energy_kwh`) and accepted physical generation (`accepted_positive_daily_energy_kwh`).
  5. Per-site and cohort-wide observed-period aggregation tracking in-sample and out-of-sample contributions independently.

---

## 4. Mathematical Formulations & Unit Definitions

### 4.1 Daily Energy Estimation
For every site-day observation $i$:
1. **Specific Yield ($\hat{Y}_i$):**
   $$\hat{Y}_i = f(X_i, kWp_i) \quad [\text{kWh/kWp/day}]$$
   Rounded to 6 decimal places.
2. **Raw Mathematical Daily Energy ($E_{raw, i}$):**
   $$E_{raw, i} = \text{round}(\hat{Y}_i \times kWp_i, 6) \quad [\text{kWh/day}]$$
   Preserved unclipped for numerical transparency.
3. **Accepted Positive Daily Energy ($E_{accepted, i}$):**
   $$E_{accepted, i} = \begin{cases} E_{raw, i} & \text{if } \hat{Y}_i \ge 0.0 \\ \text{None} & \text{if } \hat{Y}_i < 0.0 \end{cases} \quad [\text{kWh/day}]$$
   If $\hat{Y}_i < 0.0$, the observation is flagged with `prediction_status = "NEGATIVE_PREDICTION_WARNING"`.
4. **Observed Ground-Truth Daily Energy ($E_{actual, i}$):**
   $$E_{actual, i} = \text{round}(Y_{actual, i} \times kWp_i, 6) \quad [\text{kWh/day}]$$
   Computed only when $Y_{actual, i}$ is present in telemetry.

### 4.2 Observed-Period Aggregation
For each site $s$ over observed period $T_s$:
- Accepted Positive Total:
  $$E_{accepted, s} = \sum_{i \in T_s, \hat{Y}_i \ge 0} E_{raw, i} \quad [\text{kWh}]$$
- Raw Mathematical Total:
  $$E_{raw, s} = \sum_{i \in T_s} E_{raw, i} \quad [\text{kWh}]$$
- In-Sample Accepted Energy:
  $$E_{in\_sample} = \sum_{i \in \text{IN\_SAMPLE}, \hat{Y}_i \ge 0} E_{raw, i} \quad [\text{kWh}]$$
- Out-of-Sample Accepted Energy:
  $$E_{out\_of\_sample} = \sum_{i \in \text{OUT\_OF\_SAMPLE}, \hat{Y}_i \ge 0} E_{raw, i} \quad [\text{kWh}]$$

---

## 5. Decision D-4: Detailed Status & Governance

To eliminate any ambiguity regarding negative yield predictions, Stage 3 distinguishes between the implemented numerical handling and the open operational decision:

| Dimension | Implemented Status | Open / Unresolved Scope (Decision D-4) |
| :--- | :--- | :--- |
| **Raw Specific Yield** | Preserved exactly as computed by the model ($\hat{Y}_i < 0.0$). | No post-processing clipping is applied to raw model output. |
| **Raw Daily Energy** | Computed and preserved unclipped ($E_{raw, i} = \hat{Y}_i \times kWp_i$). | Provides full mathematical auditability for bias/loss evaluation. |
| **Status Tagging** | Tagged with `prediction_status = "NEGATIVE_PREDICTION_WARNING"`. | Informs downstream consumers that generation is physically implausible. |
| **Positive Generation Sums** | Excluded from accepted generation (`accepted_positive_daily_energy_kwh = None`, contributing 0.0 kWh). | Prevents unphysical negative energy from offsetting positive generation. |
| **Operational Policy** | **NOT RESOLVED.** Stage 3 does not define or adopt an authorized clipping policy. | A formal engineering decision is required to determine whether negative predictions represent inverter cutoff, night-time tare consumption, or modeling error before downstream financial integration. |

---

## 6. Scenario Handling Contract

Stage 3 introduces an explicit scenario input contract across three mutually exclusive modes:

| Scenario Mode | Input Requirements | Execution Policy | Status Output |
| :--- | :--- | :--- | :--- |
| **`HISTORICAL_REPLAY`** | UNISOLAR feature dataset or precomputed Stage 2 replay output | Evaluates historical observations in chronological order. Preserves historical capacity. | `COMPLETED` |
| **`REPRESENTATIVE_PERIOD`** | Complete 29-feature DataFrame with verified provenance | Validates all 29 features. Rejects if inputs missing. Disallows recursive lag synthesis or future leakage. | `COMPLETED` (if profile provided) / `UNAVAILABLE_INPUT_PROFILE` (if missing) |
| **`PROSPECTIVE_ROOF`** | Candidate layout or sizing specification | Blocked under Blocking Issue B-2. Unbuilt roofs lack operational lag history; mock lag generation is prohibited. | `BLOCKED_PENDING_LAG_POLICY` |

### Disclosures & Boundary Rules:
- **Historical Replay:** In-sample records (prior to 2022-03-01) represent model reconstruction on training dates and are accompanied by an explicit warning stating they must not be reported as independent forecasts.
- **Generalization Scope:** All evaluations are restricted to known UNISOLAR Peer Cohort installations; no unseen-site or unseen-geography transfer is claimed.

---

## 7. Implementation Files

| File Path | Component Role | Description |
| :--- | :--- | :--- |
| [`src/energy_economics/energy_engine.py`](../../src/energy_economics/energy_engine.py) | `Phase8EnergyEstimationEngine` | Stage 3 energy estimation, scenario router, capacity multiplication verification, and aggregation engine. |
| [`src/energy_economics/types.py`](../../src/energy_economics/types.py) | Types, Enums & Dataclasses | `EnergyScenarioType`, `ScenarioEvaluationStatus`, `DailyEnergyEstimate`, `SiteEnergySummary`, `EnergyAggregationSummary`. |
| [`src/energy_economics/exceptions.py`](../../src/energy_economics/exceptions.py) | Typed Exceptions | `EnergyEstimationError`, `ScenarioValidationError`. |
| [`src/energy_economics/__init__.py`](../../src/energy_economics/__init__.py) | Package Exports | Exported all Stage 3 classes and types. |
| [`tests/test_phase8_stage3_energy_estimation.py`](../../tests/test_phase8_stage3_energy_estimation.py) | Test Suite | 14 comprehensive test cases verifying arithmetic, units, scenarios, governance, and compatibility. |

---

## 8. Verification & Test Suite Execution

A comprehensive test suite ([`tests/test_phase8_stage3_energy_estimation.py`](../../tests/test_phase8_stage3_energy_estimation.py)) was executed:

```
============================== test session starts ==============================
platform darwin -- Python 3.13.9, pytest-8.4.2, pluggy-1.5.0
rootdir: /Users/apple/Documents/5th sem el/MLOps_EL/SolarSelect
collected 14 items

tests/test_phase8_stage3_energy_estimation.py ..............             [100%]

============================== 14 passed in 2.05s ==============================
```

Full repository test execution (`pytest -q tests/`):
```
180 passed in 3.57s
```
- **126 Phase 7 tests:** 100% passing (zero regressions).
- **19 Phase 8 Stage 1 tests:** 100% passing (zero regressions).
- **21 Phase 8 Stage 2 tests:** 100% passing (zero regressions).
- **14 Phase 8 Stage 3 tests:** 100% passing.
- **Total:** 180 passing tests.

---

## 9. Preservation Confirmation & Governance Check

- **Observed-Period Only:** Aggregations strictly cover observed dates; no 365-day annualization or extrapolation is applied (`historical_year_status = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"`).
- **Blocking Issue B-1 Preserved:** Energy basis remains strictly `UNVERIFIED`; zero AC/DC losses, derates, temperature adjustments, or tilt/azimuth corrections are applied.
- **Blocking Issue B-2 Preserved:** Prospective roofs remain strictly blocked (`BLOCKED_PENDING_LAG_POLICY`, `prediction_status = "PREDICTION_PENDING_LAG_POLICY"`).
- **Future Stage Scope Preservation:**
  * Zero temperature modeling (Stage 4).
  * Zero annualization or lifetime energy calculation (Stage 5).
  * Zero degradation modeling (Stage 6).
  * Zero system cost or financial calculation (Stage 7).
  * Zero feasibility filtering or electrical evaluation (Stage 8).
  * Zero Pareto or weighted ranking (Stage 9).
  * Zero recommendation or explanation engine (Stage 10).
  * Zero Phase 9 or Phase 10 work.
- **Frozen Lifecycle Phases:** Phases 1–5 models/metadata, Phase 6 catalogue, and Phase 7 roof-fit engine remain frozen and untouched.

---

## 10. Audit Verdict & Remaining Unresolved Issues

### Final Status Determination: **`STAGE_3_COMPLETED_WITH_DOCUMENTED_LIMITATIONS`**

#### Documented Limitations:
1. **Blocking Issue B-1:** Energy basis remains `UNVERIFIED` in UNISOLAR ground truth; no AC/DC conversion applied.
2. **Blocking Issue B-2:** Prospective roof energy prediction remains blocked (`PREDICTION_PENDING_LAG_POLICY`) pending an authorized synthetic or climatological lag-yield policy.
3. **Decision D-2:** Authoritative weather data source for non-UNISOLAR geographic locations remains unfinalized.
4. **Decision D-4:** Negative prediction operational clipping policy remains open/unresolved; raw mathematical values are preserved with warnings, and excluded from positive accepted totals without clipping.
