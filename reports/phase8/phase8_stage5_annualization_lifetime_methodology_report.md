# Phase 8 Stage 5: Annualization & Lifetime Energy Methodology Audit Report

**SolarSelect MLOps Engineering Laboratory**  
**Lifecycle Stage:** Phase 8 — Stage 5: Annualization and Lifetime Energy  
**Status:** Methodology Audit Complete — Final Reconciled (Under Review)  
**Audit Sessions:** Session 65 (Initial Audit) / Session 66 (Coverage & Annualization Reconciliation) / Session 67 (Coverage Semantics Verification)  
**Date:** 2026-11-11  
**Author:** SolarSelect Engineering Team  

---

## 1. Executive Summary

Phase 8 Stage 5 conducts a forensic methodology and data-readiness audit to establish a scientifically defensible foundation for annual energy estimation, representative-year scenarios, prospective roof energy projections, and constant-performance lifetime energy calculations.

### Core Audit Determinations:
1. **Truncated Historical Observation Window:** Forensic audit of the prepared UNISOLAR Peer Cohort dataset ([`data/processed/unisolar/peer_cohort/features.csv`](../../data/processed/unisolar/peer_cohort/features.csv)) confirms that observations span exactly **358 calendar days** (from `2021-05-01` to `2022-04-23`), comprising **345 active observation dates across the cohort union** and **13 calendar dates without cohort observations** (cohort-union date coverage: $345 / 358 \approx 96.37\%$).
2. **Separation of Cohort-Union Boundary Truncation from Internal Missingness:**
   - **Boundary Truncation (Cohort Union):** The observation window terminates on `2022-04-23`. Therefore, **April 24–30, 2022 (7 calendar days)** are unobserved boundary dates lying entirely outside the available telemetry window. These are boundary truncation dates, not ordinary random telemetry dropouts.
   - **Internal Missingness (Cohort Union):** Within the active 358-day observation window, there are **13 calendar dates** where no peer cohort site had valid observations, grouped into **7 discrete outage events** (July 9–11, Aug 10–12, Oct 3, Oct 30, Nov 26–28, Feb 15, Mar 23).
   - **Cohort-Union Total Missingness:** Relative to a full 365-day calendar year (May 1, 2021 – April 30, 2022), total cohort-union missingness comprises **20 days** (13 internal missing dates + 7 boundary truncation dates). **This 20-day figure refers strictly to dates with zero observations anywhere in the cohort; it must not be confused with the total missingness across individual sites.**
3. **Cohort-Union vs. Individual Site Missingness Divergence:** Across the 22 peer-cohort installations, observed valid site-days range from **279 to 324 days** (site coverage: $77.93\%$ to $90.50\%$ of the 358-day window; cohort mean: $293.45$ valid days, or $81.97\%$). Relative to an annual expected baseline of $22 \times 365 = 8,030$ site-days, the fleet experienced **1,574 invalid or unobserved site-days** ($19.60\%$ missingness across the fleet), consisting of 1,420 invalid/missing site-days within the window and 154 site-days truncated at the April boundary. In particular, individual sites suffered severe internal dropouts in December 2021 (many sites valid on only 11–16 days out of 31), which was masked by the cohort-union date filter.
4. **Verification of the Site-by-Month Matrix Definition:** Forensic verification of the Phase 3 data preparation code confirms that the 22-site by 12-month coverage matrix represents **Option B: Dates satisfying the complete original Phase 3 valid-site-day criteria** (96 intervals/day, $\ge 26/28$ core daylight intervals, $kWp > 0$). It does **not** represent raw telemetry-observation days (Option A).
5. **Non-Contiguous Seasonal Coverage:** The observation window does not capture a contiguous annual cycle. While Winter 2021 (June–August), Spring 2021 (September–November), and Summer 2021–2022 (December–February) are contiguous, Autumn is split across two non-contiguous years: May 2021 (early in window) and March–April 1–23, 2022 (10 months later), with late autumn (April 24–30) entirely unmonitored.
6. **Rejection of Daily Scaling & Conditional Status of Monthly Adjustment:** Simple daily scaling ($E_{\text{obs}} \times 365 / N_{\text{obs}}$) is **strictly rejected** as it distorts seasonal insolation patterns. Coverage-adjusted monthly annualization is an unvalidated extrapolation method and remains **conditional pending explicit policy authorization (Decision D-5)**.
7. **Prospective Roof Boundary Maintained (Blocking Issue B-2):** Prospective unbuilt roof prediction remains strictly blocked under `BLOCKED_PENDING_LAG_POLICY`. Sizing geometry and capacity-support checks operate normally, but annual energy prediction cannot proceed without an authorized prospective lag-yield policy.
8. **Constant-Performance Baseline for Lifetime Energy:** Stage 5 defines lifetime energy strictly as a constant-performance reference: $E_{\text{lifetime\_baseline}} = E_{\text{annual}} \times L$. All degradation modeling (linear and compounded) is strictly deferred to **Stage 6**, and financial discounting is deferred to **Stage 7**. Lifetime energy strictly inherits the evidence status of its underlying annual input.
9. **Implementation Decision:** **`STAGE_5_METHODOLOGY_AUDIT_COMPLETE`**. Zero annualization or lifetime energy calculation code has been introduced into the runtime engine.

---

## 2. Existing Specification Requirements & Governance Review

The Phase 8 Mathematical Specification ([`reports/phase8/phase8_mathematical_specification_and_io_contract.md`](../../reports/phase8/phase8_mathematical_specification_and_io_contract.md), Sections 4.3 and 4.4) establishes binding rules governing annualization and lifetime calculations:

### 2.1 Historical Replay Mode (`historical_replay`)
- **Observed-Period Reporting:** Observed-period energy must always be computed and reported:
  $$E_{\text{obs}} = \sum_{d \in \text{valid}} E_{\text{daily}}(d) \quad [\text{kWh}]$$
  accompanied by calendar days $N_{\text{cal}}$, observed days $N_{\text{valid}}$, missing days $N_{\text{miss}} = N_{\text{cal}} - N_{\text{valid}}$, and coverage fraction $c = N_{\text{valid}} / N_{\text{cal}}$.
- **Complete Year Threshold:** A validated complete historical year requires $\ge 12$ consecutive complete calendar months **and** every calendar month meeting a minimum monthly coverage threshold $c_{m, \text{min}}$, with no missing seasons.
- **Sub-12-Month Rule:** If the span is $< 12$ consecutive complete calendar months, or any monthly check fails, the engine must return **observed-period energy only**, set `annualization_method = "none_observed_only"`, `extrapolated = false`, and assign `historical_year_status = "NOT_A_VALIDATED_COMPLETE_YEAR"`. Annual-dependent economic metrics must be returned as null (`PARTIAL_RESULT`).
- **Prohibition of Simple 365-Day Scaling:** The specification strictly prohibits multiplying daily average energy by 365 ("Never `daily × 365`").

### 2.2 Representative-Year Mode (`representative_year`)
- Requires an explicitly identified, user-supplied profile of 365 (or 366 in leap years) complete 29-feature rows with `scenario_id`, data source, and construction provenance.
- Must be explicitly labeled `"scenario, not forecast"`. If any days are missing, the scenario must return `UNSUPPORTED_SCENARIO`.

### 2.3 Lifetime Energy Baseline vs. Degradation Boundary
- Stage 5 establishes the baseline constant-performance relationship:
  $$E_{\text{lifetime\_baseline}} = E_{\text{annual}} \times L \quad [\text{kWh}]$$
  where $L$ is the operating lifetime in integer years ($1 \le L \le 40$).
- **Strict Stage Boundary:** Stage 5 **prohibits** applying annual degradation (linear or compounded), temperature derating, or financial discount rates. Degradation trajectories belong exclusively to **Stage 6**, and financial evaluation belongs to **Stage 7**.

---

## 3. Forensic Audit of UNISOLAR Historical Data Coverage

A line-by-line audit of [`data/processed/unisolar/peer_cohort/features.csv`](../../data/processed/unisolar/peer_cohort/features.csv) and [`data/processed/unisolar/target_dataset.csv`](../../data/processed/unisolar/target_dataset.csv) was conducted:

### 3.1 Macro Temporal Boundaries (Cohort Union)
- **Earliest Timestamp:** `2021-05-01`
- **Latest Timestamp:** `2022-04-23`
- **Total Calendar Span ($N_{\text{cal}}$):** **358 days**
- **Cohort-Union Active Dates ($N_{\text{valid, cohort}}$):** **345 days** (dates with valid observations from $\ge 1$ site)
- **Internal Missing Dates (Cohort Union):** **13 days** (dates with zero valid observations across all 22 sites)
- **Boundary Truncation Dates (Cohort Union):** **7 days** (`2022-04-24` to `2022-04-30`)
- **Cohort-Union Date Coverage Ratio ($c_{\text{cohort}}$):** $345 / 358 = \mathbf{0.963687}$ ($96.37\%$)

### 3.2 Inventory of Internal Missing Dates (Cohort Union)
Within the 358-day window, the 13 dates lacking any cohort observations cluster into 7 discrete events:
1. `2021-07-09` to `2021-07-11` (3 days — Winter telemetry outage)
2. `2021-08-10` to `2021-08-12` (3 days — Winter telemetry outage)
3. `2021-10-03` (1 day — Spring single-day gap)
4. `2021-10-30` (1 day — Spring single-day gap)
5. `2021-11-26` to `2021-11-28` (3 days — Spring telemetry outage)
6. `2022-02-15` (1 day — Summer single-day gap)
7. `2022-03-23` (1 day — Autumn single-day gap)

### 3.3 Cohort-Union vs. Individual Site Coverage Divergence
While the cohort union exhibits 345 active days, individual site coverage is substantially lower:

| SiteKey | Observed Valid Days ($N_{\text{valid}, s}$) | % of 358-Day Window | % of 365-Day Calendar Year |
| :--- | :--- | :--- | :--- |
| **Site 15** | 287 | 80.17% | 78.63% |
| **Site 16** | 284 | 79.33% | 77.81% |
| **Site 17** | 289 | 80.73% | 79.18% |
| **Site 18** | 297 | 82.96% | 81.37% |
| **Site 20** | 297 | 82.96% | 81.37% |
| **Site 21** | 290 | 81.01% | 79.45% |
| **Site 22** | 287 | 80.17% | 78.63% |
| **Site 23** | 290 | 81.01% | 79.45% |
| **Site 25** (Min) | **279** | **77.93%** | **76.44%** |
| **Site 26** | 304 | 84.92% | 83.29% |
| **Site 27** | 311 | 86.87% | 85.21% |
| **Site 30** | 286 | 79.89% | 78.36% |
| **Site 31** | 299 | 83.52% | 81.92% |
| **Site 32** | 282 | 78.77% | 77.26% |
| **Site 33** | 283 | 79.05% | 77.53% |
| **Site 34** (Max) | **324** | **90.50%** | **88.77%** |
| **Site 35** | 284 | 79.33% | 77.81% |
| **Site 36** | 291 | 81.28% | 79.73% |
| **Site 37** | 295 | 82.40% | 80.82% |
| **Site 38** | 317 | 88.55% | 86.85% |
| **Site 39** | 290 | 81.01% | 79.45% |
| **Site 40** | 290 | 81.01% | 79.45% |
| **Cohort Mean** | **293.45** | **81.97%** | **80.40%** |

> [!CRITICAL]
> **Cohort-Union vs. Site Missingness Distinction:**
> The 13 internal missing dates and 7 boundary-truncation dates (totaling 20 days) are strictly **cohort-union statistics**. They describe the dates where no site in the peer cohort produced valid data. Across all 22 sites, there were **1,420 invalid or unobserved site-days within the window** and **154 site-days truncated at the April boundary**, totaling **1,574 invalid site-days** out of $22 \times 365 = 8,030$ annual site-days ($19.60\%$ missingness fleet-wide). Site-level annualization must never use cohort-union coverage as an individual site proxy.

---

## 4. Monthly & Seasonal Coverage Analysis

### 4.1 Descriptive Semantics of Calendar Months
To ensure scientific clarity, calendar months are characterized using descriptive attributes rather than mutually exclusive categories:
- `FULL_CALENDAR_MONTH_IN_WINDOW`: Calendar month whose full calendar span falls entirely within the observation window boundaries (May 2021 through March 2022).
- `PARTIAL_CALENDAR_MONTH_AT_BOUNDARY`: Calendar month truncated by an observation window boundary (April 2022, truncated on April 23).
- `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS`: Calendar month that contains missing days due to internal telemetry dropouts (e.g., July, August, October, November 2021; February, March 2022).
- *Attribute Overlap:* A month designated as `FULL_CALENDAR_MONTH_IN_WINDOW` may also be a `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` (e.g., July 2021 has all 31 days in window, but 3 internal missing dates).

### 4.2 Cohort-Union Monthly Breakdown

| Calendar Month | Month Days ($N_{\text{cal}, m}$) | Days in Window | Cohort-Union Valid Days | Missing in Window | Window Coverage (%) | Full Month Coverage (%) | Descriptive Attributes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **2021-05** | 31 | 31 | 31 | 0 | 100.00% | 100.00% | `FULL_CALENDAR_MONTH_IN_WINDOW` |
| **2021-06** | 30 | 30 | 30 | 0 | 100.00% | 100.00% | `FULL_CALENDAR_MONTH_IN_WINDOW` |
| **2021-07** | 31 | 31 | 28 | 3 | 90.32% | 90.32% | `FULL_CALENDAR_MONTH_IN_WINDOW`, `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` |
| **2021-08** | 31 | 31 | 28 | 3 | 90.32% | 90.32% | `FULL_CALENDAR_MONTH_IN_WINDOW`, `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` |
| **2021-09** | 30 | 30 | 30 | 0 | 100.00% | 100.00% | `FULL_CALENDAR_MONTH_IN_WINDOW` |
| **2021-10** | 31 | 31 | 29 | 2 | 93.55% | 93.55% | `FULL_CALENDAR_MONTH_IN_WINDOW`, `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` |
| **2021-11** | 30 | 30 | 27 | 3 | 90.00% | 90.00% | `FULL_CALENDAR_MONTH_IN_WINDOW`, `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` |
| **2021-12** | 31 | 31 | 31 | 0 | 100.00% | 100.00% | `FULL_CALENDAR_MONTH_IN_WINDOW` (Cohort union only; see site matrix) |
| **2022-01** | 31 | 31 | 31 | 0 | 100.00% | 100.00% | `FULL_CALENDAR_MONTH_IN_WINDOW` |
| **2022-02** | 28 | 28 | 27 | 1 | 96.43% | 96.43% | `FULL_CALENDAR_MONTH_IN_WINDOW`, `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` |
| **2022-03** | 31 | 31 | 30 | 1 | 96.77% | 96.77% | `FULL_CALENDAR_MONTH_IN_WINDOW`, `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` |
| **2022-04** | 30 | 23 | 23 | 7 | 100.00% | **76.67%** | `PARTIAL_CALENDAR_MONTH_AT_BOUNDARY` (Truncated at April 23) |

### 4.3 Authoritative Phase 3 Valid-Site-Day Matrix ($N_{\text{valid}, s, m}$)
Forensic inspection of [`src/prepare_phase3_data.py`](../../src/prepare_phase3_data.py) confirms that the site-by-month counts represent **Option B: Dates satisfying the complete original Phase 3 valid-site-day criteria** (96 intervals/day, $\ge 26/28$ core daylight intervals, $kWp > 0$):

```
SiteKey   2021-05 2021-06 2021-07 2021-08 2021-09 2021-10 2021-11 2021-12 2022-01 2022-02 2022-03 2022-04
15             28      29      28      28      29      23      17      11      20      23      29      22
16             26      26      24      28      27      23      19      20      23      24      26      18
17             26      29      28      27      29      23      19      13      21      21      30      23
18             28      29      28      28      29      21      20      15      21      25      30      23
20             26      29      28      28      29      24      21      16      20      23      30      23
21             26      29      28      28      29      25      20      12      19      23      28      23
22             26      29      28      28      29      23      17      11      22      22      29      23
23             29      29      28      27      30      22      19      15      18      21      29      23
25             26      25      28      28      29      24      20      13      19      16      29      22
26             26      29      28      28      29      27      22      15      22      26      29      23
27             14      30      28      28      29      24      22      31      28      26      28      23
30             28      29      28      28      28      19      19      16      20      21      28      22
31             28      29      28      28      29      23      21      18      21      21      30      23
32             26      29      28      28      29      22      19      13      16      21      29      22
33             26      29      28      28      29      22      17      13      19      23      27      22
34             28      28      27      28      30      28      26      29      26      25      29      20
35             28      29      28      28      27      24      20      13      17      18      29      23
36             26      28      28      27      29      25      20      14      19      24      28      23
37             26      28      28      28      29      25      20      17      19      22      30      23
38             28      29      28      28      29      24      22      26      25      25      30      23
39             27      29      28      28      29      24      20      15      19      19      29      23
40             27      29      28      27      29      24      21      11      17      25      29      23
```

> [!NOTE]
> **Option B Verification:**
> Cross-verification against `target_dataset.csv` proves that filtering on `is_valid_site_day == True` matches the counts in `features.csv` exactly with **0.0 difference** (6,456 valid rows). In contrast, raw telemetry days with any intervals recorded total 7,810 site-days. Thus, this matrix reflects the authoritative Phase 3 valid-site-day filter ($N_{\text{valid}, s, m}$).

### 4.4 Non-Contiguous Seasonal Coverage
Seasonal statistics must reflect temporal contiguity:
- **Winter 2021 (June 1 – August 31, 2021):** Contiguous 92-day span. Cohort union observed: 86 days ($93.48\%$).
- **Spring 2021 (September 1 – November 30, 2021):** Contiguous 91-day span. Cohort union observed: 86 days ($94.51\%$).
- **Summer 2021–2022 (December 1, 2021 – February 28, 2022):** Contiguous 90-day span. Cohort union observed: 89 days ($98.89\%$).
- **Autumn Breakdown (Non-Contiguous Observations):**
  * *May 2021:* Observed at the start of the window (31 calendar days, 31 observed).
  * *March 2022:* Observed 10 months later (31 calendar days, 30 observed, 1 missing).
  * *April 1–23, 2022:* Observed mid-autumn, truncated on April 23 (23 days observed, April 24–30 unobserved boundary).
  * Combining May 2021 and March–April 2022 into a single "Autumn" figure is misleading because the observations originate from two non-contiguous calendar years. May 2021, March 2022, and April 1–23, 2022 must be analyzed and reported as separate periods.

---

## 5. Evaluation of Historical Annualization Methods

### 5.1 Method A: Complete Historical Year
- **Eligibility Conditions:** Requires $\ge 12$ consecutive complete calendar months.
- **Audit Assessment:** **FAILED.** The observation window terminates on April 23, 2022. April 2022 contains only 23 of 30 calendar days ($76.67\%$). The dataset fails the mandatory threshold for a complete historical year.
- **Assigned Status:** `historical_year_status = "NOT_A_VALIDATED_COMPLETE_YEAR"`.
- **Output Policy:** Return observed-period energy only ($E_{\text{obs}}$). Annual-dependent financial metrics must be marked null (`PARTIAL_RESULT`).

### 5.2 Method B: Coverage-Adjusted Monthly Annualization
- **Mathematical Formulation:**
  $$E_{\text{annual, adj}} = \sum_{m=1}^{12} \left( \frac{N_{\text{cal}, m}}{N_{\text{valid}, m}} \right) \sum_{d \in \text{valid}_m} E_{\text{daily}}(d)$$
- **Prerequisites for Consideration:**
  * Must be computed strictly at the **site-month level**, where $N_{\text{valid}, m}$ is the site's own valid count.
  * Internal missingness and boundary truncation must be treated separately.
  * April 2022 ($7\text{ days unobserved}$) represents **boundary extrapolation**, not internal missingness adjustment.
- **Decision D-5 Status:** **NOT APPROVED.** Monthly coverage-adjusted annualization remains a **conditional future option**. Current evidence does not support its implementation.

### 5.3 Method C: Simple Daily Scaling ($E_{\text{obs}} \times 365 / N_{\text{obs}}$)
- **Audit Assessment:** **STRICTLY REJECTED.**
  * Simple daily scaling assumes unobserved days have the annual mean daily insolation.
  * Winter outages (July/August) would be scaled by an annual average, introducing substantial positive bias.
  * Strictly forbidden by the mathematical specification: *"Never `daily × 365`"*.

---

## 6. Evaluation of Representative-Year Scenarios

### 6.1 Definition & Scope
A representative-year scenario is an engineering construct for multi-candidate comparison, **not a forecast and not an empirical measurement**.

### 6.2 Data Constraints
1. **The 7-Day April Gap:** UNISOLAR historical telemetry cannot form an autonomous 365-day continuous profile due to the unobserved boundary dates (April 24–30).
2. **Prohibition of Data Fabrication:** Zero synthetic weather or yield values may be fabricated to bridge April 24–30.
3. **External Profile Requirement:** External profiles (e.g. TMY) require all 29 features with verified provenance. Autoregressive lag features cannot be recursively simulated without an authorized lag policy (Blocking Issue B-2).

---

## 7. Prospective Roof Annualization Constraints

### 7.1 Enforcement of Blocking Issue B-2
- **The Prospective Problem:** Unbuilt candidate roofs lack operational telemetry history. The 12 autoregressive lag features cannot be computed.
- **Stage 5 Policy:**
  * Roof layout and panel sizing operate normally.
  * Training-capacity support checks operate normally.
  * **Annual energy prediction remains strictly BLOCKED** (`prediction_status = "PREDICTION_PENDING_LAG_POLICY"`).
- **Prohibition of Default Yield Multipliers:** Substituting arbitrary annual specific yields (e.g. $1400\text{ kWh/kWp/year}$) is strictly prohibited.

---

## 8. Lifetime Energy Methodology

### 8.1 Formulation as a Constant-Performance Reference
Stage 5 defines lifetime energy strictly as a constant-performance baseline:
$$E_{\text{lifetime\_baseline}} = E_{\text{annual}} \times L \quad [\text{kWh}]$$
where $L$ is the asset operational lifetime in integer years ($1 \le L \le 40$, default $L = 25$ years).

### 8.2 Evidence Status Inheritance
- Lifetime energy **strictly inherits the evidence status** of its underlying annual energy reference.
- If $E_{\text{annual}}$ is unvalidated or partial (`PARTIAL_PERIOD_NOT_A_FULL_YEAR`), lifetime energy must be marked `PARTIAL_RESULT_UNVALIDATED` or `UNVALIDATED_REFERENCE_ONLY`. It must never be presented as a validated physical lifetime generation forecast.
- **Strict Boundary:** Zero degradation modeling (linear or compounded, Stage 6) and zero financial discounting (Stage 7) are applied.

---

## 9. Proposed Output Schema & Status Recommendations

```json
{
  "run_id": "RUN-PHASE8-ANNUAL-...",
  "stage": "STAGE_5_ANNUALIZATION_AND_LIFETIME",
  "historical_coverage": {
    "observation_start": "2021-05-01",
    "observation_end": "2022-04-23",
    "calendar_span_days": 358,
    "observed_days_cohort_union": 345,
    "internal_missing_days_cohort_union": 13,
    "boundary_truncation_days_cohort_union": 7,
    "coverage_fraction_cohort_union": 0.963687,
    "full_calendar_months_in_window": 11,
    "partial_calendar_months_at_boundary": 1,
    "historical_year_status": "NOT_A_VALIDATED_COMPLETE_YEAR"
  },
  "annual_energy_estimate": {
    "observed_period_energy_kwh": 123456.78,
    "annualization_method": "none_observed_only",
    "annual_energy_kwh": null,
    "extrapolated": false,
    "max_monthly_scaling_factor": 1.0,
    "annualization_status": "PARTIAL_PERIOD_ONLY"
  },
  "lifetime_energy_baseline": {
    "lifetime_duration_years": 25,
    "constant_performance_lifetime_energy_kwh": null,
    "lifetime_evidence_status": "PARTIAL_RESULT_UNVALIDATED",
    "degradation_applied": false,
    "degradation_stage": "DEFERRED_TO_STAGE_6"
  },
  "governance": {
    "energy_basis": "UNVERIFIED",
    "blocking_issue_b1": "UNRESOLVED",
    "blocking_issue_b2": "PROSPECTIVE_ROOF_BLOCKED_PENDING_LAG_POLICY"
  }
}
```

---

## 10. Required Methodology Comparison Matrix

| Method | Required Evidence | Current Feasibility in UNISOLAR | Main Scientific Limitation |
| :--- | :--- | :--- | :--- |
| **Complete Historical Year** | $\ge 12$ consecutive complete calendar months; $c_m \ge c_{m, \text{min}}$ for all months. | **Infeasible.** (Observation span is 358 calendar days; April truncated at day 23). | Partial observation boundary; cannot certify a complete annual cycle. |
| **Coverage-Adjusted Estimate** | Representative missingness across all months; acceptable seasonal distribution. | **Conditional / Extrapolated.** (11 full months in window; April truncated). | Assumes missing days (including 7 days in late April) match observed daily rates. |
| **Simple Daily Scaling** | Uniformly distributed missingness across the entire year. | **Infeasible / Rejected.** (Fails specification rule *"Never `daily × 365`"*). | Over-allocates energy to winter missing days; seasonal insolation distortion. |
| **Representative-Year Scenario** | Complete 365/366-day 29-feature continuous profile with verified provenance. | **Conditional on External Profile.** (UNISOLAR historical profile has 7-day April gap). | Scenario is a design comparison, not an empirical measurement or forecast. |
| **Prospective Roof Estimate** | Valid prospective feature construction without operational lag history. | **Blocked under Blocking Issue B-2.** (`BLOCKED_PENDING_LAG_POLICY`). | Unbuilt roofs lack operational yield history; lag synthesis is unverified. |
| **Constant-Performance Lifetime Energy** | Defensible annual energy reference $E_{\text{annual}}$ and lifetime duration $L$. | **Conditional.** (Inherits status of annual energy reference). | Excludes physical degradation, soiling, inverter replacement, and clipping. |

---

## 11. Scientific Limitations & Key Findings

1. **The 358-Day Horizon:** The UNISOLAR dataset spans 358 days, not 365 days. Equating 358 days with a full year without explicit disclosure constitutes unverified extrapolation.
2. **The Late April Blind Spot:** April 24–30 is completely unmonitored. In Melbourne, solar geometry and ambient temperature decline rapidly in late April, making linear extrapolation of the first 23 days speculative.
3. **Local Outage Disparities:** While cohort union coverage is $96.37\%$, site-level coverage averages $81.97\%$. Individual site annualization must handle local dropouts ranging from 21 to 66 missing days.
4. **Prospective Roof Lag Dependency:** Sizing and layout optimization can be performed for prospective roofs, but annual generation cannot be predicted using the Phase 5 model until an authorized lag policy is established.

---

## 12. Stage 5 Scientific & Methodological Reconciliation (Session 66 Audit)

This section summarizes the key reconciliations established during Session 66:
- **Cohort-Union vs. Site Coverage:** Separated cohort-union date coverage ($96.37\%$) from site-level valid counts (mean $81.97\%$).
- **Missingness Classification:** Separated internal missingness (13 cohort-union dates) from boundary truncation (7 April dates).
- **Site-Month Annualization:** Formally established that monthly coverage adjustment can only occur at the site-month level with verified intra-month representativeness.
- **Seasonal Decomposition:** Decomposed non-contiguous Autumn observations (May 2021, March 2022, April 1–23, 2022).
- **Threshold Approval Status:** Documented that the proposed $90\%$ monthly coverage threshold is a proposal requiring approval under Decision D-5.
- **Decision D-5 Status:** Formally retained Decision D-5 as **NOT APPROVED**.
- **Lifetime Energy Inheritance:** Established that constant-performance lifetime energy strictly inherits the evidence status of the annual reference.

---

## 13. Final Stage 5 Coverage Semantics Verification (Session 67 Audit)

This section documents the final forensic verifications conducted during Session 67:

### 13.1 Verification of the Site-by-Month Matrix Definition
- **Exact Generation Method:** The 22-site by 12-month matrix in Section 4.3 was generated by grouping [`data/processed/unisolar/peer_cohort/features.csv`](../../data/processed/unisolar/peer_cohort/features.csv) by `SiteKey` and `YearMonth`.
- **Classification Confirmation (Option B):** In [`src/prepare_phase3_data.py`](../../src/prepare_phase3_data.py), `features.csv` was created by filtering strictly on `is_valid_site_day == True`. This required:
  1. `total_intervals == 96` (96 15-minute intervals per 24-hour day).
  2. `core_nonnull_interval_count >= 26` (at least 26 of 28 non-null intervals in the core daylight window 09:00–15:45).
  3. `kWp > 0` (positive documented system capacity).
- **Equivalence Proof:** Cross-verification against [`data/processed/unisolar/target_dataset.csv`](../../data/processed/unisolar/target_dataset.csv) confirmed that filtering on `is_valid_site_day == True` matches the matrix cell-for-cell with **0.0 difference** (6,456 valid site-days total).
- **Telemetry-Observation Comparison:** In contrast, raw telemetry days with $>0$ intervals recorded total 7,810 site-days. Thus, 1,354 raw site-days were excluded by the Phase 3 quality filter.
- **Conclusion:** The matrix represents **Option B: Authoritative Phase 3 Valid-Site-Day Matrix ($N_{\text{valid}, s, m}$)**, and does **not** represent raw telemetry-observation days (Option A).

### 13.2 Cohort-Union vs. Site-Level Missingness Disambiguation
- **Cohort-Union Missingness:** The 13 internal missing dates and 7 boundary-truncation dates (totaling 20 days) describe the dates where **no site in the cohort had valid observations** over the 365-day calendar span.
- **Site-Level Missingness:** Across the 22 peer-cohort installations, there are **1,420 invalid or unobserved site-days within the window** and **154 site-days truncated at the April boundary**, totaling **1,574 invalid site-days** out of $22 \times 365 = 8,030$ annual site-days ($19.60\%$ missingness fleet-wide).
- The 20-day cohort-union figure must **never** be cited as the total missingness across all 22 sites.

### 13.3 Month Classification Semantics
The terms `FULL_CALENDAR_MONTH_IN_WINDOW`, `PARTIAL_CALENDAR_MONTH_AT_BOUNDARY`, and `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` are **descriptive attributes**, not mutually exclusive categories:
- A month with all calendar dates inside the window is a `FULL_CALENDAR_MONTH_IN_WINDOW`.
- If that same month contains internal telemetry dropouts, it is simultaneously a `MONTH_WITH_INTERNAL_MISSING_OBSERVATIONS` (e.g., July 2021).
- No new runtime enums or schemas are introduced.

### 13.4 Retained Methodology Decisions
- No validated complete historical annual measurement is currently available.
- Simple daily $\times 365$ scaling remains rejected.
- The proposed $90\%$ monthly coverage threshold is not approved (proposal requiring approval).
- Decision D-5 remains **NOT APPROVED**.
- Coverage-adjusted monthly annualization remains conditional and unimplemented.
- Representative-year scenarios require complete, externally supplied, provenance-verified 29-feature profiles.
- Prospective roof prediction remains blocked under B-2.
- Lifetime energy remains a constant-performance reference and inherits the evidence status of its annual input.
- No degradation or financial discounting is introduced in Stage 5.

---

## 14. Implementation-Readiness Decision & Recommended Next Steps

### Final Status Determination:
**`STAGE_5_METHODOLOGY_AUDIT_COMPLETE`**

- **Audit Completion:** The methodology and input data for Stage 5 have been forensically audited and reconciled against the Phase 8 Mathematical Specification and repository data.
- **Implementation Status:** Zero calculation code has been implemented. Implementation remains paused awaiting user review and authorization of the proposed annualization contracts.
- **Recommended Next Steps:**
  1. Review and approve the reconciled Stage 5 contracts and status mappings.
  2. Implement Stage 5 annualization and constant-performance lifetime engine under [`src/energy_economics/`](../../src/energy_economics/).
  3. Ensure that `historical_replay` returns observed-period energy with `NOT_A_VALIDATED_COMPLETE_YEAR` status, preventing unjustified extrapolation.
  4. Ensure that prospective roofs cleanly return `BLOCKED_PENDING_LAG_POLICY`.
  5. Prepare for Stage 6 (Degradation Modeling) where linear and compounded degradation curves will be introduced.
