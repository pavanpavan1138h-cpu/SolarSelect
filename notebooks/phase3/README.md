# SolarSelect — Phase 3: Target Definition and Data Preparation

**Directory:** `notebooks/phase3/`  
**Phase:** Phase 3 — Target Definition, Data Cleaning, and Feature Engineering  
**Status:** **FINALIZED WITH DOCUMENTED LIMITATIONS** (Final Authorized Correction Pass Completed & Verified)

---

## 1. Phase 3 Mission & Scope

Phase 3 operationalizes the approved empirical findings from Phase 1 (Data Inspection) and Phase 2 (Exploratory Data Analysis) to produce clean, reproducible, leakage-free, ML-ready feature matrices for Phase 4 (Model Development and Comparison).

The workflow is structured across two distinct benchmark datasets:
1. **Primary Layer A Dataset (UNISOLAR Campus 1 Cohort):** Multi-seasonal, capacity-normalized specific energy yield forecasting ($Y_f = \text{kWh}/\text{kW}_p/\text{day}$) across commercial rooftop installations over a 12-month complete annual cycle (`2021-05-01` to `2022-04-30`).
2. **Dedicated Secondary Benchmark (Kaggle Plants 1 & 2):** High-frequency, short-horizon inverter power forecasting (`AC_POWER` in kW) under direct on-site pyranometer `IRRADIATION` sensors.

---

## 2. Directory Structure

```text
notebooks/phase3/
├── README.md                                                   # Phase 3 documentation and execution guide (this file)
├── target_definition_and_data_preparation.ipynb                # Master implementation notebook for Phase 3 (21 executed cells)
│
└── figures/                                                    # Dedicated directory for publication-grade preparation figures
    └── phase3_data_preparation_and_splits_summary.png          # 4-panel summary of pass rates, splits, target & correlations
```

---

## 3. Final Correction Pass Methodological Decisions

### A. Dual-Dataset Strategy (Full Cohort vs. Peer Cohort)
To support rigorous sensitivity benchmarking in Phase 4 without discarding empirical observations, two parallel modeling datasets are provided:
- **Dataset A — Full Cohort (`data/processed/unisolar/`):**
  - All 24 documented-capacity installations (including Sites 19 and 24).
  - Preserves original valid site-day filter: $7,039$ valid site-days ($80.35\%$ of annual expected).
  - Target statistics: Median $2.839$, Mean $3.638$, Max $40.787\text{ kWh}/\text{kW}_p/\text{day}$ ($\text{CF}_{24\text{h}} = 169.95\%$).
  - Obs $> 10\text{ kWh}/\text{kW}_p/\text{day}$: $247$ observations (strictly Sites 19 & 24).
- **Dataset B — Peer Cohort (`data/processed/unisolar/peer_cohort/`):**
  - The 22 installations excluding Sites 19 and 24.
  - Same dates, target definition, feature construction, and chronological boundaries.
  - $6,456$ valid site-days ($0$ nulls).
  - Target statistics: Median $2.633$, Mean $2.880$, Max $6.917\text{ kWh}/\text{kW}_p/\text{day}$ ($\text{CF}_{24\text{h}} = 28.82\%$).
  - Obs $> 10\text{ kWh}/\text{kW}_p/\text{day}$: **0** ($100\%$ physically bounded by commercial rooftop constraints).
- **Sites 16 and 39:** Retained in both datasets as verified low-yield operational installations ($1.68$ and $2.07\text{ kWh}/\text{kW}_p/\text{day}$).

### B. Strict Separation of Predictive Features from Diagnostic Metadata
To eliminate post-hoc leakage into model predictors:
- **Primary Feature Matrices (`features.csv`, `train.csv`, `val.csv`, `test.csv`):**
  - Exactly **$33$ columns**: $3$ identifiers (`SiteKey`, `Date`, `split`) + $1$ target (`target_daily_yield`) + **$29$ primary predictive features**.
  - Contains strictly features legitimately available at prediction time:
    * Static Metadata (3): `kWp`, `lat`, `Lon`
    * Calendar Cycles (8): `day_of_year`, `month`, `day_of_week`, `is_weekend`, `sin_doy`, `cos_doy`, `sin_month`, `cos_month`
    * Deterministic Astronomical Solar Geometry (5): `solar_declination_deg`, `solar_noon_elevation_deg`, `solar_noon_zenith_deg`, `daylight_hours`, `extraterrestrial_radiation_h0`
    * Autoregressive Historical Generation Lags & Rolling (8): `has_valid_lag1`, `lag1_daily_yield`, `lag2_daily_yield`, `lag7_daily_yield`, `rolling_mean_7d_yield`, `rolling_std_7d_yield`, `rolling_mean_14d_yield`, `rolling_mean_30d_yield`
    * Historical Weather Lags (5): `lag1_temp_mean`, `lag1_temp_max`, `lag1_temp_min`, `lag1_temp_range`, `lag1_rh_mean`
  - Zero diagnostic flags or target derivatives enter the predictive feature files.
- **Diagnostic Metadata (`diagnostic_metadata.csv`):**
  - Exactly **$17$ columns**: Target derivatives (`capacity_factor_24h`, `daily_energy_kwh`), diagnostic masks (`is_site_19`, `is_site_24`, `is_provisional_site`, `is_site_16`, `is_site_39`, `is_low_yield_site`), and quality completeness indicators.
  - Used strictly for post-hoc grouping, sensitivity ablation, and quality analysis in Phase 4.

### C. Calendar-Aware Lag and Rolling-Window Construction
- **24-Hour Day-Ahead Horizon ($\tau \ge 24\text{h}$):** Shift operations are executed on a continuous daily calendar grid (`freq='D'`).
- `shift(1)` strictly references calendar day $D-1$ without time compression or forward-fill distortion.
- Missing historical days are **not** treated as zero generation. When prior days are missing, they remain `NaN` and are imputed strictly using **training-partition medians** (`Date <= 2021-12-31`).
- `has_valid_lag1` (binary 0/1) informs the model whether the prior-day yield was genuinely observed or imputed.
- Same-day observed weather is completely excluded.

### D. Daily Energy Interval Completeness Audit
- On valid site-days, average non-null intervals are virtually identical across cohorts:
  - **Peer Cohort (22 Sites):** $43.70$ intervals/day ($45.53\%$ 24h coverage).
  - **Site 19:** $44.77$ intervals/day ($46.63\%$ 24h coverage).
  - **Site 24:** $44.34$ intervals/day ($46.18\%$ 24h coverage).
- Sub-threshold missingness outside the core window tracks astronomical day-length variation (winter non-core average: $6.93$; summer non-core average: $26.56$). Nighttime intervals produce zero energy and are recorded as `NaN`.
- Quality completeness indicators (`daily_nonnull_interval_count`, `core_nonnull_interval_count`, `daily_interval_coverage`, `missing_interval_count`) are preserved in diagnostic metadata.

### E. Sites 19 and 24 Target Quality & Physical Plausibility Findings
- **Site 19:** $34.32\text{ kW}_p$ documented capacity (104 Trina 330W, SE27.6K inverter). Peak 15-minute generation reaches $42.22\text{ kWh}$ ($168.88\text{ kW}$ instantaneous power, $492\%$ STC rating). Maximum specific yield: $40.7871\text{ kWh}/\text{kW}_p/\text{day}$ ($\text{CF}_{24\text{h}} = 169.95\%$).
- **Site 24:** $40.26\text{ kW}_p$ documented capacity (122 Trina 330W, SE82.8K inverter). Mean yield: $6.081\text{ kWh}/\text{kW}_p/\text{day}$ (max $13.568$, $\text{CF}_{24\text{h}} = 56.54\%$).
- **Unresolved Data-Quality Anomaly:** The anomaly is consistent across all 12 months ($\sim 6.3\times$ peer median for Site 19; $\sim 2.2\times$ for Site 24). Feeder/building aggregation is an **unproven hypothesis**. The anomaly is preserved in Dataset A without artificial clipping, while Dataset B provides an uncorrupted peer benchmark.

### F. Chronological Train / Validation / Test Splitting
- **Training Split (May 1, 2021 – Dec 31, 2021; 8 Months):**
  - Dataset A: $4,770$ site-days.
  - Dataset B: $4,383$ site-days.
- **Validation Split (Jan 1, 2022 – Feb 28, 2022; 2 Months, Peak Summer):**
  - Dataset A: $1,037$ site-days.
  - Dataset B: $945$ site-days.
- **Test Split (Mar 1, 2022 – Apr 23, 2022; 2 Months, Autumn):**
  - Dataset A: $1,232$ site-days.
  - Dataset B: $1,128$ site-days.
- Logging terminated on April 23, 2022 (April 24–30 are entirely absent telemetry dates).

### G. Separate Kaggle Benchmark
- Maintained under `data/processed/kaggle_benchmark/` ($136,472$ intervals across 44 inverters in Plants 1 & 2).
- Plant 1 DC/AC $\sim 10\times$ ratio documented as an **observed numerical discrepancy / unresolved scaling anomaly vs. documented units**, not an asserted sensor bug.
- `DC_POWER`, `DAILY_YIELD`, and `TOTAL_YIELD` permanently excluded.

---

## 4. Processed Dataset Output Inventory

All prepared data is deterministically exported to `data/processed/`:

### Full Cohort Dataset A (`data/processed/unisolar/`):
- `features.csv`: Primary feature matrix for all $7,039$ valid site-days ($33$ columns, $0$ nulls).
- `train.csv`: Training feature matrix ($4,770$ rows, $33$ columns).
- `validation.csv`: Validation feature matrix ($1,037$ rows, $33$ columns).
- `test.csv`: Test feature matrix ($1,232$ rows, $33$ columns).
- `diagnostic_metadata.csv`: Diagnostic flags, target derivatives, and completeness indicators ($7,039$ rows, $17$ columns).
- `target_dataset.csv`: All $8,760$ evaluated site-days ($24 \times 365$).
- `excluded_site_days.csv`: All $1,721$ excluded site-days ($1,481$ observed + $240$ absent).
- `feature_dictionary.csv`: Complete metadata catalog for all $46$ attributes.
- `preprocessing_metadata.json`: Full cohort pipeline metadata and accounting.

### Peer Cohort Dataset B (`data/processed/unisolar/peer_cohort/`):
- `features.csv`: Primary feature matrix for all $6,456$ peer valid site-days ($33$ columns, $0$ nulls).
- `train.csv`: Peer training feature matrix ($4,383$ rows, $33$ columns).
- `validation.csv`: Peer validation feature matrix ($945$ rows, $33$ columns).
- `test.csv`: Peer test feature matrix ($1,128$ rows, $33$ columns).
- `diagnostic_metadata.csv`: Peer diagnostic metadata ($6,456$ rows, $17$ columns).
- `preprocessing_metadata.json`: Peer-specific pipeline metadata and imputer medians.

### Kaggle Benchmark (`data/processed/kaggle_benchmark/`):
- `plant1_prepared.csv`: $68,774$ rows.
- `plant2_prepared.csv`: $67,698$ rows.
- `train.csv`: $94,276$ rows.
- `validation.csv`: $21,120$ rows.
- `test.csv`: $21,076$ rows.
- `preprocessing_metadata.json`: Benchmark metadata and inverter availability ratios.

---

## 5. Execution & Reproducibility Verification

```bash
# Execute the standalone preparation script
python3 src/prepare_phase3_data.py

# Or execute the complete Phase 3 Jupyter notebook
cd notebooks/phase3
jupyter nbconvert --execute --inplace target_definition_and_data_preparation.ipynb
```

Both entry points produce identical, bit-exact processed files with zero execution errors.
