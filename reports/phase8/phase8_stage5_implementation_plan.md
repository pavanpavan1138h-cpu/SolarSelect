# Phase 8 Stage 5: Annualization & Lifetime Energy Implementation Plan

**SolarSelect MLOps Engineering Laboratory**  
**Lifecycle Stage:** Phase 8 — Stage 5: Annualization and Lifetime Energy  
**Status:** Implementation Plan — Ready for Review (Planning Only)  
**Session:** Session 68  
**Date:** 2026-11-11  
**Author:** SolarSelect Engineering Team  

---

## 1. Executive Summary

This document establishes the authoritative, repository-grounded implementation plan for **Phase 8 Stage 5: Annualization and Lifetime Energy**. Stage 5 builds upon the foundation layer (Stage 1), the frozen Phase 5 inference and historical replay interface (Stage 2), the daily energy estimation engine (Stage 3), and the temperature methodology audit (Stage 4).

### Core Planning Directives:
1. **Planning Only — Zero Runtime Changes:** This session delivers a technical specification and contract readiness plan. Zero runtime calculation code is introduced in this session.
2. **Observed-Period Contract Preservation:** Historical replay on the UNISOLAR dataset spans 358 calendar days (terminating on April 23, 2022). It lacks 12 complete consecutive calendar months and fails the criteria for a certified annual measurement. Stage 5 will aggregate observed-period energy only and output `historical_year_status = "NOT_A_VALIDATED_COMPLETE_YEAR"`.
3. **Rejection of Unvalidated Annualization:** Simple daily scaling ($E_{\text{obs}} \times 365 / N_{\text{obs}}$) is strictly prohibited. Coverage-adjusted monthly annualization remains unimplemented and unapproved under **Decision D-5 (`NOT APPROVED`)**.
4. **Constant-Performance Baseline for Lifetime Energy:** Stage 5 introduces the baseline calculation:
   $$E_{\text{lifetime\_baseline}} = E_{\text{annual}} \times L \quad [\text{kWh}]$$
   operating strictly as an unadjusted mathematical multiplication. It explicitly inherits the evidence status of its annual input (carrying `UNVALIDATED_REFERENCE_ONLY` or `PARTIAL_RESULT` when annual energy is partial). All physical degradation modeling is deferred to **Stage 6**, and financial discounting is deferred to **Stage 7**.
5. **Prospective Roof Boundary Maintained (Blocking Issue B-2):** Prospective unbuilt roof prediction remains strictly blocked under `BLOCKED_PENDING_LAG_POLICY`. Default annual specific yield multipliers are forbidden.

---

## 2. Current Implementation Inventory & Readiness Audit

A forensic inspection of the repository codebase ([`src/energy_economics/`](../../src/energy_economics/)), tests ([`tests/test_phase8_stage3_energy_estimation.py`](../../tests/test_phase8_stage3_energy_estimation.py)), and mathematical specifications was conducted:

| Component / Contract | Current Code Status | Current Specification Status | Stage 5 Role & Relationship |
| :--- | :--- | :--- | :--- |
| **`Phase8FoundationEngine`** | Implemented & Tested (Stage 1) | Specified in Section 2 | Ingests Phase 7 geometry, panel catalogue, evaluates marginal capacity support. Reused without changes. |
| **`Phase5PeerCohortPredictor`** | Implemented & Tested (Stage 2) | Specified in Section 3 | Frozen Phase 5 ExtraTrees and 50/50 blend inference. Reused without changes. |
| **`UNISOLARHistoricalReplayEngine`** | Implemented & Tested (Stage 2) | Specified in Section 3 | Chronological replay of 358-day UNISOLAR data. Reused without changes. |
| **`Phase8EnergyEstimationEngine`** | Implemented & Tested (Stage 3) | Specified in Section 4.1 | Computes daily energy ($E = \hat{Y} \times kWp$), handles negative predictions (D-4 open), outputs observed aggregation. Primary upstream provider for Stage 5. |
| **`HistoricalYearStatus`** | Implemented in `types.py` (`PARTIAL_PERIOD_NOT_A_FULL_YEAR`, `VALIDATED_COMPLETE_YEAR`, `NOT_APPLICABLE_SCENARIO`) | Specified in Section 4.3 (`NOT_A_VALIDATED_COMPLETE_YEAR`) | Status reconciliation required (alias/bridge in code to support both without breaking Stage 3 tests). |
| **`EnergyAggregationSummary`** | Implemented in `types.py` | Specified in Section 4.3 | Dataclass tracking cohort-wide observed energy, coverage fraction, missing days. Extended or wrapped for Stage 5. |
| **Historical Annualization** | **Not Implemented** | Specified in Section 4.3 | Core Stage 5 deliverable. Restricted to eligibility checking and observed-period pass-through for UNISOLAR. |
| **Monthly Coverage Adjustment** | **Not Implemented** | Specified in Section 4.3 (Proposal D-5) | **Blocked / Excluded.** Decision D-5 remains `NOT APPROVED`. |
| **Representative-Year Scenario** | Scenario routing stub in Stage 3 | Specified in Section 4.3 | Rejects missing/incomplete 365-day profiles (`UNSUPPORTED_SCENARIO`). |
| **Prospective Roof Annualization** | Blocked in Stage 3 (`BLOCKED_PENDING_LAG_POLICY`) | Specified in Section 1.2 & 4.1 | **Blocked under B-2.** Returns non-numeric annual energy with warning. |
| **Constant-Performance Lifetime Baseline** | **Not Implemented** | Specified in Section 4.4 | Core Stage 5 deliverable ($E_{\text{lifetime}} = E_{\text{annual}} \times L$). |
| **Degradation Modeling** | **Not Implemented** | Specified in Section 4.4 | **Deferred to Stage 6.** Zero degradation calculations in Stage 5. |
| **Financial Calculations (LCOE/NPV)** | **Not Implemented** | Specified in Section 5 | **Deferred to Stage 7.** Zero economic discounting in Stage 5. |

---

## 3. Approved Stage 5 Scope

The permitted Stage 5 implementation scope is strictly bounded to the following capabilities:

### 3.1 Observed-Period Energy Aggregation
- Ingest validated Stage 3 outputs ([`DailyEnergyEstimate`](../../src/energy_economics/types.py), [`SiteEnergySummary`](../../src/energy_economics/types.py), [`EnergyAggregationSummary`](../../src/energy_economics/types.py)).
- Preserve chronological ordering and in-sample vs. out-of-sample partition tags.
- Aggregate accepted positive daily energy only; preserve unclipped raw mathematical energy and Decision D-4 warnings.
- Report observed-period energy, valid-day count, calendar boundaries, missing-day counts, and coverage fractions.
- Never silently convert partial observation periods into annual estimates.
- Never apply simple daily scaling ($E_{\text{obs}} \times 365 / N_{\text{obs}}$).

### 3.2 Historical Annualization Eligibility Logic
- Implement explicit rule verification for `VALIDATED_COMPLETE_YEAR`:
  1. Window must span $\ge 12$ consecutive complete calendar months.
  2. No missing seasons.
- Evaluate the UNISOLAR Peer Cohort dataset against these criteria:
  * Result: Window ends on April 23, 2022 (April truncated at 23 days). Fails rule 1.
  * Status assigned: `NOT_A_VALIDATED_COMPLETE_YEAR` (aliased to `PARTIAL_PERIOD_NOT_A_FULL_YEAR`).
  * Annual numeric estimate: set to `null` (or explicitly designated as observed-period partial total).
  * Method output: `annualization_method = "none_observed_only"`, `extrapolated = false`.
- Keep Decision D-5 `NOT APPROVED`; monthly coverage-adjusted extrapolation remains disabled.

### 3.3 Lifetime Constant-Performance Reference
- Implement baseline reference arithmetic:
  $$E_{\text{lifetime\_baseline}} = E_{\text{annual\_reference}} \times L \quad [\text{kWh}]$$
- Input validation:
  * $L$ integer, $1 \le L \le 40$ (default $L = 25$ years).
  * $E_{\text{annual\_reference}}$ must be an explicitly supplied, typed annual reference with documented evidence status and provenance.
- Evidence status inheritance:
  * If the annual reference is partial or unvalidated (`NOT_A_VALIDATED_COMPLETE_YEAR`), the lifetime estimate must be marked `PARTIAL_RESULT_UNVALIDATED` or `UNVALIDATED_REFERENCE_ONLY`, with numeric output `null` unless explicitly requested in reference-only mode.
  * Mandatory warning: *"Baseline lifetime energy represents unadjusted mathematical multiplication of annual reference by lifetime years; physical module degradation, soiling, and component replacements are excluded."*

---

## 4. Explicitly Excluded Scope

The following capabilities are strictly forbidden from implementation in Stage 5:
1. **No Simple Daily Scaling:** Multiplying daily average generation by 365 is completely prohibited.
2. **No Coverage-Adjusted Monthly Annualization:** Decision D-5 remains unapproved; no intra-month scaling factors will be computed or applied.
3. **No Degradation Modeling:**
   - Linear degradation ($E_t = E_1 [1 - d(t-1)]$) is deferred to **Stage 6**.
   - Compounded degradation ($E_t = E_1 (1-d)^{t-1}$) is deferred to **Stage 6**.
   - Catalogue warranty degradation curves are deferred to **Stage 6**.
4. **No Temperature Corrections:** Stage 4 established that Method B is disabled; Stage 5 introduces zero thermal multipliers.
5. **No Financial Calculations:** CAPEX, OPEX, inverter replacement reserves, discount rates, LCOE, NPV, and payback periods belong exclusively to **Stage 7**.
6. **No Synthetic Profile Generation:** Stage 5 will not fabricate weather or yield values to bridge the 7-day April gap.
7. **No Prospective Lag Synthesis:** Prospective roofs remain strictly blocked under B-2; no default annual yield factors will be substituted.

---

## 5. Input/Output and Status Contract Reconciliation

### 5.1 Contract Status Mapping Matrix

| Capability | Mathematical Specification Contract | Existing Code Status (`types.py`) | Stage 5 Reconciled Behavior | Decision / Governance Dependency |
| :--- | :--- | :--- | :--- | :--- |
| **Historical Annual Status** | `VALIDATED_COMPLETE_YEAR`, `NOT_A_VALIDATED_COMPLETE_YEAR`, `NOT_APPLICABLE_SCENARIO` | `HistoricalYearStatus` (`VALIDATED_COMPLETE_YEAR`, `PARTIAL_PERIOD_NOT_A_FULL_YEAR`, `NOT_APPLICABLE_SCENARIO`) | Support both `NOT_A_VALIDATED_COMPLETE_YEAR` and `PARTIAL_PERIOD_NOT_A_FULL_YEAR` as equivalent aliases in `HistoricalYearStatus` to ensure 100% backwards compatibility with Stage 3 tests while adhering to the spec. | Reconciles Session 50 spec with Session 60 code. Non-breaking. |
| **Workflow Status Code** | `PARTIAL_RESULT` | `engine_status` in foundation / Stage 3 dictionaries | Returned at top level when historical replay covers an incomplete annual period; annual-dependent economics null. | Authoritative in Section 8.1 of Math Spec. |
| **Annualization Method** | `none_observed_only`, `full_observed_year`, `monthly_coverage_adjusted`, `scenario` | String field in `EnergyAggregationSummary` (`annualization_extrapolation_applied: bool`) | Introduce typed `AnnualizationMethod` enum in `types.py`: `NONE_OBSERVED_ONLY = "none_observed_only"`, `FULL_OBSERVED_YEAR = "full_observed_year"`, `MONTHLY_COVERAGE_ADJUSTED = "monthly_coverage_adjusted"`, `SCENARIO = "scenario"`. | Formalizes specification Section 4.3 contract. |
| **Annualization Status** | `PARTIAL_PERIOD_ONLY`, `COMPLETE_ANNUAL_CYCLE`, `UNSUPPORTED_INCOMPLETE_PROFILE` | Implicit in aggregation summary | Explicitly reported in `AnnualEnergyEstimate` dataclass. | Non-breaking extension. |
| **Lifetime Evidence Status** | `VALIDATED_PHYSICAL_BASELINE`, `UNVALIDATED_REFERENCE_ONLY`, `PARTIAL_RESULT_UNVALIDATED` | Not present in code | Introduced in `LifetimeEnergyBaseline` dataclass: inherits status from annual reference. Set to `PARTIAL_RESULT_UNVALIDATED` for UNISOLAR replay. | Strictly prevents presenting partial results as validated lifetime forecasts. |
| **Prospective Prediction** | `PREDICTION_PENDING_LAG_POLICY` | `prediction_status = "PREDICTION_PENDING_LAG_POLICY"` in Stage 3 | Passed through unaltered; annual energy `null`. | Governed by Blocking Issue B-2. |

### 5.2 Smallest Safe Reconciliation Strategy
To reconcile the status discrepancy without breaking existing code:
1. In `src/energy_economics/types.py`, add `NOT_A_VALIDATED_COMPLETE_YEAR = "NOT_A_VALIDATED_COMPLETE_YEAR"` to `HistoricalYearStatus`, while retaining `PARTIAL_PERIOD_NOT_A_FULL_YEAR = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"`.
2. Define a property or helper method ensuring equality checks for either string evaluate to true for partial-period results.
3. In Stage 5 outputs, report `historical_year_status = "NOT_A_VALIDATED_COMPLETE_YEAR"` (with `legacy_status_alias = "PARTIAL_PERIOD_NOT_A_FULL_YEAR"` preserved).

---

## 6. Proposed Implementation Architecture

To ensure modularity and maintainability, Stage 5 will be implemented in a dedicated component ([`src/energy_economics/annualization.py`](../../src/energy_economics/)) that cleanly consumes Stage 3 outputs.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Phase 8 Architecture                            │
├────────────────────────────────────────────────────────────────────────┤
│ Stage 1: Foundation Layer (Phase8FoundationEngine)                     │
│ Stage 2: Inference & Historical Replay (Phase5PeerCohortPredictor)     │
│ Stage 3: Energy Estimation Engine (Phase8EnergyEstimationEngine)       │
│          └── Outputs: DailyEnergyEstimate, EnergyAggregationSummary     │
├────────────────────────────────────────────────────────────────────────┤
│ Stage 5: Annualization & Lifetime Engine (Phase8AnnualizationEngine)   │
│   ├── Component A: Historical Annualization Eligibility Evaluator      │
│   │     ├── Consecutive complete calendar month checker (>= 12)       │
│   │     ├── Calendar boundary truncation detector (April 24-30)       │
│   │     └── Observed-period energy pass-through (E_obs)               │
│   ├── Component B: Scenario Annualization Router                       │
│   │     ├── Representative-year 365/366-day validator                 │
│   │     └── Prospective roof B-2 pass-through (BLOCKED)               │
│   └── Component C: Constant-Performance Lifetime Baseline Evaluator    │
│         ├── Baseline multiplication (E_annual * L)                     │
│         ├── Lifetime duration validator (1 <= L <= 40)                 │
│         └── Evidence status inheritance engine                         │
└────────────────────────────────────────────────────────────────────────┘
```

### 6.1 Component Specifications

#### Component 1: `Phase8AnnualizationEngine` (`src/energy_economics/annualization.py`)
- **Responsibilities:**
  * Ingests validated Stage 3 outputs or direct annual profile specifications.
  * Evaluates temporal completeness and consecutive calendar month count.
  * Formulates annual energy estimates according to authorized methods.
  * Computes constant-performance lifetime baselines with evidence status inheritance.
- **Input Contracts:**
  * `stage3_output: Dict[str, Any]` (output from `Phase8EnergyEstimationEngine.estimate_energy()`), OR
  * `annual_reference_kwh: Optional[float]`, `evidence_status: str`, `lifetime_years: int = 25`.
- **Output Contracts:**
  * Returns standardized Stage 5 result dictionary adhering to `phase8-io-0.1` schema.
- **Validation Rules:**
  * Reject non-integer or out-of-bounds lifetime duration ($L < 1$ or $L > 40$).
  * Reject negative or non-finite annual energy values.
  * Reject simple daily scaling requests.
  * Reject prospective prediction requests (B-2).

#### Component 2: Types & Dataclasses (`src/energy_economics/types.py`)
Add the following immutable dataclasses with `.to_dict()` methods:
1. `AnnualizationMethod(str, Enum)`: `NONE_OBSERVED_ONLY`, `FULL_OBSERVED_YEAR`, `MONTHLY_COVERAGE_ADJUSTED`, `SCENARIO`.
2. `AnnualEnergyResult(frozen=True)`: `observed_period_energy_kwh`, `annual_energy_kwh`, `annualization_method`, `historical_year_status`, `extrapolated`, `consecutive_complete_months`, `warnings`, `limitations`.
3. `LifetimeEnergyBaseline(frozen=True)`: `lifetime_years`, `baseline_lifetime_energy_kwh`, `evidence_status`, `degradation_applied = False`, `discounting_applied = False`.

---

## 7. Detailed Test Plan

A dedicated test suite ([`tests/test_phase8_stage5_annualization.py`](../../tests/test_phase8_stage5_annualization.py)) will be constructed to validate all 16 required test cases:

| Test ID | Test Name | Target Behavior | Execution Condition |
| :--- | :--- | :--- | :--- |
| **TC-01** | `test_observed_period_aggregation_preserved` | Verifies observed-period energy equals sum of Stage 3 accepted daily energy. | Immediate (Replay fixture) |
| **TC-02** | `test_chronological_ordering_and_boundaries` | Confirms start date (`2021-05-01`), end date (`2022-04-23`), and 358-day calendar span. | Immediate (Replay fixture) |
| **TC-03** | `test_insample_and_oos_preservation` | Confirms in-sample vs out-of-sample energy totals are tracked independently. | Immediate (Stage 3 output) |
| **TC-04** | `test_negative_prediction_exclusion_preserved` | Verifies negative yield days contribute 0.0 kWh to positive annual totals and retain warnings. | Immediate (Stage 3 mock) |
| **TC-05** | `test_missing_observation_dates_accounting` | Confirms 13 internal missing cohort-union dates are reported in missing-day count. | Immediate (Features fixture) |
| **TC-06** | `test_unisolar_partial_period_rejected_for_annual` | Confirms UNISOLAR replay returns `NOT_A_VALIDATED_COMPLETE_YEAR` and `annual_energy_kwh = None`. | Immediate (Replay fixture) |
| **TC-07** | `test_complete_year_eligibility_logic` | Verifies a mock 12-complete-month dataset qualifies for complete year without approving D-5. | Immediate (Synthetic 12-month) |
| **TC-08** | `test_leap_year_calendar_handling` | Confirms 366-day leap year spans are handled accurately without hardcoding 365. | Immediate (Synthetic leap year) |
| **TC-09** | `test_explicit_annual_reference_validation` | Rejects non-finite, negative, or un-typed annual references. | Immediate (Unit test) |
| **TC-10** | `test_constant_performance_lifetime_arithmetic` | Verifies $E_{\text{life}} = E_{\text{annual}} \times L$ for valid annual input ($100,000 \times 25 = 2,500,000$). | Immediate (Unit test) |
| **TC-11** | `test_lifetime_evidence_status_inheritance` | Confirms partial annual input results in `PARTIAL_RESULT_UNVALIDATED` lifetime status. | Immediate (Unit test) |
| **TC-12** | `test_invalid_lifetime_duration_rejection` | Rejects $L = 0$, $L = -5$, $L = 45$, and float $L = 25.5$. | Immediate (Unit test) |
| **TC-13** | `test_prohibition_of_degradation_and_discounting` | Asserts `degradation_applied == False`, `discounting_applied == False`, and zero degradation fields leak. | Immediate (Unit test) |
| **TC-14** | `test_b2_prospective_prediction_blocked` | Confirms prospective candidate roof returns `BLOCKED_PENDING_LAG_POLICY` with null annual energy. | Immediate (Stage 3 mock) |
| **TC-15** | `test_representative_year_incomplete_rejection` | Rejects representative profiles with $< 365$ days or missing features with `UNSUPPORTED_SCENARIO`. | Immediate (Unit test) |
| **TC-16** | `test_regression_protection_stages_1_to_3` | Runs full existing test suite confirming 180/180 tests pass with zero regressions. | Immediate (Regression check) |

---

## 8. Dependencies and Unresolved Decisions

Stage 5 operates under strict governance constraints regarding external dependencies:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Stage 5 Dependency & Decision Register               │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Decision D-5: Monthly coverage threshold (90%) and monthly          │
│    coverage-adjusted annualization.                                    │
│    STATUS: NOT APPROVED.                                               │
│    ACTION: Excluded from runtime calls. Monthly extrapolation disabled.│
│                                                                        │
│ 2. Blocking Issue B-1: AC/DC energy basis confirmation.                │
│    STATUS: UNVERIFIED.                                                 │
│    ACTION: Preserved strictly as energy_basis = "UNVERIFIED".          │
│                                                                        │
│ 3. Blocking Issue B-2: Prospective roof lag-yield policy.              │
│    STATUS: BLOCKED PENDING POLICY.                                     │
│    ACTION: Prospective annual energy remains BLOCKED (null output).    │
│                                                                        │
│ 4. Decision D-2: Authoritative weather source for non-UNISOLAR sites.  │
│    STATUS: UNRESOLVED.                                                 │
│    ACTION: External scenario generation deferred; user input required.│
│                                                                        │
│ 5. Stage 6: Module degradation modeling (linear and compounded).       │
│    STATUS: DEFERRED TO STAGE 6.                                        │
│    ACTION: Stage 5 applies zero degradation derates.                   │
│                                                                        │
│ 6. Stage 7: System cost and financial discounting (LCOE/NPV).          │
│    STATUS: DEFERRED TO STAGE 7.                                        │
│    ACTION: Stage 5 applies zero financial discounting.                 │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Implementation Sequence

Upon receiving explicit user approval to proceed with Stage 5 runtime implementation, work will execute in five sequential steps:

1. **Step 1 — Types & Contract Extension:** Update [`src/energy_economics/types.py`](../../src/energy_economics/types.py) with `AnnualizationMethod`, `AnnualEnergyResult`, `LifetimeEnergyBaseline`, and reconcile `HistoricalYearStatus`.
2. **Step 2 — Engine Implementation:** Implement [`src/energy_economics/annualization.py`](../../src/energy_economics/annualization.py) containing `Phase8AnnualizationEngine` with full input validation and eligibility logic.
3. **Step 3 — Package Export Integration:** Update [`src/energy_economics/__init__.py`](../../src/energy_economics/__init__.py) to expose new Stage 5 classes cleanly.
4. **Step 4 — Test Suite Construction:** Implement [`tests/test_phase8_stage5_annualization.py`](../../tests/test_phase8_stage5_annualization.py) covering all 16 test cases.
5. **Step 5 — Verification & Documentation:** Run full test suite ($180 + 16 = 196$ passing tests), author the Stage 5 completion report, and append to `log.txt`.

---

## 10. Acceptance Criteria

Stage 5 implementation will be considered complete only when:
1. All 16 unit and integration test cases pass without failure.
2. Zero regressions across existing Phase 7, Stage 1, Stage 2, and Stage 3 tests (180 passing tests preserved).
3. The UNISOLAR historical replay cleanly returns `NOT_A_VALIDATED_COMPLETE_YEAR` without generating an unvalidated numeric annual estimate.
4. Daily scaling ($\times 365$) is demonstrably rejected with an explicit error or warning.
5. Lifetime constant-performance energy correctly evaluates $E_{\text{annual}} \times L$ and inherits evidence status.
6. Zero degradation formulas, temperature factors, or financial discounting calculations leak into Stage 5 code.
7. Prospective roofs return `BLOCKED_PENDING_LAG_POLICY` with null annual energy.
8. `energy_basis` remains qualified as `UNVERIFIED` across all outputs.

