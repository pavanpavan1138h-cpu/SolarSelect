# SolarSelect — Phase 3: Target Definition and Data Preparation

**Directory:** `notebooks/phase3/`  
**Phase:** Phase 3 — Target Definition, Data Cleaning, and Feature Engineering  
**Status:** **CLOSED WITH DOCUMENTED LIMITATIONS** (Prompt 2 of 2 Final Closure Completed & Verified)

---

## 1. Phase 3 Mission & Scope

Phase 3 operationalizes the approved empirical findings from Phase 1 (Data Inspection) and Phase 2 (Exploratory Data Analysis) to produce clean, reproducible, leakage-free, ML-ready feature matrices for Phase 4 (Model Development and Comparison).

The workflow is structured across two distinct benchmark datasets:
1. **Primary Layer A Dataset (UNISOLAR Campus 1 Cohort):** Multi-seasonal, capacity-normalized specific energy yield forecasting ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$) across 24 commercial rooftop installations over a 12-month complete annual cycle (`2021-05-01` to `2022-04-30`).
2. **Dedicated Secondary Benchmark (Kaggle Plants 1 & 2):** High-frequency, short-horizon inverter power forecasting (`AC_POWER` in kW) under direct on-site pyranometer `IRRADIATION` sensors.

---

## 2. Directory Structure

```text
notebooks/phase3/
├── README.md                                                   # Phase 3 documentation and execution guide (this file)
├── target_definition_and_data_preparation.ipynb                # Master implementation notebook for Phase 3 (20 executed cells)
│
└── figures/                                                    # Dedicated directory for publication-grade preparation figures
    └── phase3_data_preparation_and_splits_summary.png          # 4-panel summary of pass rates, splits, target & correlations
```

---

## 3. Methodological Core Decisions & Prompt 2 Verification Closures

### A. Primary Target Definition & Site-Day Accounting Reconciliation
- **Formula:** $Y_{f,\text{day}} = \frac{\sum E_{15\text{m},\text{valid}}}{\text{kW}_p} \quad [\text{kWh}/\text{kW}_p/\text{day}]$.
- **Valid Site-Day Filter:** A site-day qualifies if and only if:
  1. Exactly $96$ contiguous 15-minute interval records are present.
  2. At least $26$ of $28$ core daytime intervals ($09:00$ to $15:45$) are non-null.
  3. Installed capacity $\text{kW}_p > 0$ is documented.
  4. Observation belongs to the 24 cohort sites in the approved 12-month window.
- **Complete Site-Day Accounting Reconciliation ($24\text{ sites} \times 365\text{ days}$):**
  - **Expected Annual Cohort Site-Days:** $24\text{ sites} \times 365\text{ calendar days} = \mathbf{8,760\text{ site-days}}$ ($100.00\%$).
  - **Observed Telemetry Site-Days:** Telemetry was recorded on $355$ unique dates ($24 \times 355 = \mathbf{8,520\text{ site-days}}$, $97.26\%$).
  - **Completely Absent Telemetry Dates:** Exactly $\mathbf{10\text{ calendar dates}}$ had zero recorded intervals across all 24 sites ($10 \times 24 = \mathbf{240\text{ site-days}}$, $2.74\%$):
    - `2021-07-10`, `2021-08-11`, `2021-11-27` (3 isolated single-day telemetry dropouts)
    - `2022-04-24` through `2022-04-30` (7 consecutive final days of April 2022 where telemetry logging ended)
  - **Verified Valid Site-Days:** $\mathbf{7,039\text{ site-days}}$ ($80.35\%$ of annual expected; $82.62\%$ of observed telemetry).
  - **Total Excluded / Unmodeled Site-Days:** $\mathbf{1,721\text{ site-days}}$ ($19.65\%$ of annual expected), fully logged in `excluded_site_days.csv`:
    - $1,481$ observed incomplete or low core daylight coverage site-days ($16.91\%$)
    - $240$ entirely absent telemetry site-days across the 10 unrecorded calendar dates ($2.74\%$)
  - Missing values were **never filled with zeros**, preventing severe downward distortion of true solar generating capacity.

### B. Target Physical Plausibility & Extreme Values Audit
- **Theoretical Rooftop Bounds:** Clear-sky summer insolation in Victoria, Australia peaks at $\approx 10\text{--}11\text{ kWh}/\text{m}^2/\text{day}$, yielding at most $7\text{--}8$ peak sun hours ($7\text{--}8\text{ kWh}/\text{kW}_p/\text{day}$, $\text{CF}_{24\text{h}} \le 33\%$).
- **Observed Target Maximum:** $40.7871\text{ kWh}/\text{kW}_p/\text{day}$ ($\text{CF}_{24\text{h}} = 169.95\%$) on 2021-12-30 at Site 19.
- **Root Cause Evidence:** Site 19 raw daily generation reaches $1,399.81\text{ kWh}$ on peak summer days against documented $34.32\text{ kW}_p$ nameplate rating (peak 15-minute generation reaches $42.22\text{ kWh} = 168.88\text{ kW}$ instantaneous power, or $492\%$ STC rating).
- **Localization:** Exactly $247$ observations in `features.csv` exceed $10\text{ kWh}/\text{kW}_p/\text{day}$, and **$100\%$ of these $247$ observations belong strictly to Site 19 ($n=220$) and Site 24 ($n=27$)**.
- **Peer Cohort Baseline (22 Sites, $n=6,456$ site-days):** Median $2.633$, Mean $2.880$, Max $6.917\text{ kWh}/\text{kW}_p/\text{day}$ ($\text{CF}_{24\text{h}} = 28.82\%$). Perfectly physically plausible.
- **Handling Policy:** Extreme values are genuine empirical artifacts resulting from meter/building aggregation in the UNISOLAR instrumentation, NOT a software or join bug. They are **preserved without artificial clipping or modification**. Binary indicator flags (`is_site_19`, `is_site_24`, `is_provisional_site`) are embedded in all splits to enable sensitivity analysis and ablation benchmarking in Phase 4.

### C. Operational Forecast Horizon, Feature Accounting & Leakage Audit
- **Horizon:** 24-hour day-ahead forecasting ($\tau \ge 24\text{h}$).
- **Leakage Prevention Guarantees:**
  - Same-day observed weather is **never** used as a day-ahead predictor.
  - Historical weather lags ($\tau \ge 1$ day: `lag1_temp_mean`, `lag1_temp_max`, `lag1_temp_min`, `lag1_temp_range`, `lag1_rh_mean`) reflect atmospheric state memory from day $D-1$.
  - Autoregressive generation lags (`lag1`, `lag2`, `lag7`) and rolling statistics strictly precede target day $D$.
  - Imputer statistics are fitted strictly on the training partition (`Date <= 2021-12-31`).
- **Feature Count Reconciliation (41 vs. 35 vs. 29 Columns):**
  - **Total columns in `features.csv`:** **$41$ columns**
  - **Identifiers & Split ($3$ non-predictive):** `SiteKey`, `Date`, `split`
  - **Target Ground Truth & Derivatives ($3$ evaluation):** `target_daily_yield`, `capacity_factor_24h`, `daily_energy_kwh`
  - **Primary Predictive Continuous / Cyclical Features ($29$ model inputs):**
    - Static Metadata ($3$): `kWp`, `lat`, `Lon`
    - Calendar Cycles ($8$): `day_of_year`, `month`, `day_of_week`, `is_weekend`, `sin_doy`, `cos_doy`, `sin_month`, `cos_month`
    - Deterministic Astronomical Solar Geometry ($5$): `solar_declination_deg`, `solar_noon_elevation_deg`, `solar_noon_zenith_deg`, `daylight_hours`, `extraterrestrial_radiation_h0`
    - Autoregressive Historical Generation Lags & Rolling ($8$): `has_valid_lag1`, `lag1_daily_yield`, `lag2_daily_yield`, `lag7_daily_yield`, `rolling_mean_7d_yield`, `rolling_std_7d_yield`, `rolling_mean_14d_yield`, `rolling_mean_30d_yield`
    - Historical Weather Lags ($5$): `lag1_temp_mean`, `lag1_temp_max`, `lag1_temp_min`, `lag1_temp_range`, `lag1_rh_mean`
  - **Site Diagnostic & Sensitivity Flags ($6$ binary columns):** `is_site_19`, `is_site_24`, `is_provisional_site`, `is_site_16`, `is_site_39`, `is_low_yield_site`
  - **Total Model Input Features:** $29 + 6 = \mathbf{35\text{ features}}$ (or $36$ if `SiteKey` is encoded as a categorical predictor).

### D. Chronological Train / Validation / Test Splitting
- **Training Split (8 Months: May 1, 2021 – December 31, 2021):** $4,770$ valid site-days ($67.77\%$), 24 sites. Captures Southern-Hemisphere late autumn, winter, spring, and early summer. Peer median yield: $2.202\text{ kWh}/\text{kW}_p/\text{day}$.
- **Validation Split (2 Months: January 1, 2022 – February 28, 2022):** $1,037$ valid site-days ($14.73\%$), 24 sites. Captures peak summer generation. Peer median yield: $4.245\text{ kWh}/\text{kW}_p/\text{day}$ ($1.93\times$ winter).
- **Test Split (2 Months: March 1, 2022 – April 30, 2022):** $1,232$ valid site-days ($17.50\%$), 24 sites. Captures autumn generation. Peer median yield: $2.929\text{ kWh}/\text{kW}_p/\text{day}$.

### E. Separate Kaggle Benchmark & Sensor Ratio Clarification
- **Target:** Inverter instantaneous `AC_POWER` (kW).
- **Scope:** $136,472$ intervals across 44 inverters in Plants 1 & 2 ($68,774$ Plant 1 rows, $67,698$ Plant 2 rows). Exactly 4 Plant 1 generation rows unmatched due to sensor timestamp drops.
- **Sensor Ratio Audit:** Plant 1 DC/AC $\sim 10\times$ ratio is documented as an **observed numerical discrepancy / unresolved scaling anomaly vs. documented units**, not an asserted sensor bug.
- **Exclusions:** `DAILY_YIELD`, `TOTAL_YIELD`, and `DC_POWER` permanently excluded from model inputs.
- **Splits:** Chronological partition into Train ($94,276$, 24 days), Validation ($21,120$, 5 days), and Test ($21,076$, 5 days).

---

## 4. Processed Dataset Output Inventory

All prepared data is deterministically exported to `data/processed/`:

### UNISOLAR Processed Files (`data/processed/unisolar/`):
- `target_dataset.csv`: All $\mathbf{8,760}$ evaluated site-days ($24\text{ sites} \times 365\text{ days}$) with validity flags, daily energy, and specific yield.
- `excluded_site_days.csv`: All $\mathbf{1,721}$ excluded site-days ($1,481$ observed invalid + $240$ entirely absent) with detailed exclusion reasons.
- `features.csv`: Full feature matrix for all $\mathbf{7,039}$ valid site-days across $\mathbf{41}$ columns ($0$ nulls).
- `train.csv`: Training split feature matrix ($4,770$ rows, $0$ nulls).
- `validation.csv`: Validation split feature matrix ($1,037$ rows, $0$ nulls).
- `test.csv`: Held-out test split feature matrix ($1,232$ rows, $0$ nulls).
- `feature_dictionary.csv`: Full definitions, formulas, units, prediction availability, and leakage assessments for all $41$ columns.
- `preprocessing_metadata.json`: Complete pipeline configuration, full site-day accounting reconciliation, split boundaries, and imputation values.

### Kaggle Benchmark Processed Files (`data/processed/kaggle_benchmark/`):
- `plant1_prepared.csv`: $68,774$ rows for Plant 1.
- `plant2_prepared.csv`: $67,698$ rows for Plant 2.
- `train.csv`: $94,276$ rows.
- `validation.csv`: $21,120$ rows.
- `test.csv`: $21,076$ rows.
- `preprocessing_metadata.json`: Preprocessing configuration, exclusion rationale, and inverter availability metadata.

---

## 5. Execution & Reproducibility Verification

The preparation pipeline runs deterministically end-to-end via:

```bash
# Execute the standalone preparation script
python3 src/prepare_phase3_data.py

# Or execute the complete Phase 3 Jupyter notebook
cd notebooks/phase3
jupyter nbconvert --execute --inplace target_definition_and_data_preparation.ipynb
```

Both entry points produce identical, bit-exact processed files and verified outputs with zero execution errors.
