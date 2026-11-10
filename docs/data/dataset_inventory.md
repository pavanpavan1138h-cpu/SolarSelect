# Dataset Inventory — SolarSelect

This document catalogues every raw, interim, and processed dataset in the SolarSelect repository, detailing filenames, sources, records, dimensions, date spans, schemas, and intended roles.

---

## 1. Raw Datasets (Immutable Source Data)

| Dataset Identifier | File Name | File Path | Records | Columns | Temporal Coverage | Physical Units | Intended Role |
|---|---|---|---:|---:|---|---|---|
| **Kaggle Plant 1 Generation** | `Plant_1_Generation_Data.csv` | `data/raw/archive/` | 68,778 | 7 | 2020-05-15 to 2020-06-17 | kW, kWh | Dedicated secondary benchmark for high-frequency kW forecasting |
| **Kaggle Plant 1 Weather** | `Plant_1_Weather_Sensor_Data.csv` | `data/raw/archive/` | 3,182 | 6 | 2020-05-15 to 2020-06-17 | °C, kW/m² | On-site ambient/module temp and irradiation |
| **Kaggle Plant 2 Generation** | `Plant_2_Generation_Data.csv` | `data/raw/archive/` | 67,698 | 7 | 2020-05-15 to 2020-06-17 | kW, kWh | Dedicated secondary benchmark for inverter dropout analysis |
| **Kaggle Plant 2 Weather** | `Plant_2_Weather_Sensor_Data.csv` | `data/raw/archive/` | 3,259 | 6 | 2020-05-15 to 2020-06-17 | °C, kW/m² | On-site ambient/module temp and irradiation |
| **UNISOLAR Generation** | `Solar_Energy_Generation.csv` | `data/raw/unisolar/` | 1,536,301 | 5 | 2019-12-31 to 2022-04-23 | kWh (15-min interval) | **Primary Benchmark** for Layer A specific yield forecasting |
| **UNISOLAR Weather** | `Weather_Data_reordered_all.csv` | `data/raw/unisolar/` | 371,769 | 10 | 2019-12-31 to 2022-04-23 | °C, %, km/h, hPa | Proxy BOM regional ambient weather across campuses |
| **UNISOLAR Site Details** | `Solar_Site_Details.csv` | `data/raw/unisolar/` | 42 | 10 | Static metadata | kWp, coordinates | Static installed capacity, panel/inverter strings |
| **UNISOLAR Monthly Summary** | `Monthly_Summary_Solar.csv` | `data/raw/unisolar/` | 1,176 | 6 | 2020-01 to 2022-04 (28 mos) | kWh | Coarse macro-level generation validation |

---

## 2. Processed ML Datasets (Layer A Training & Evaluation)

Processed datasets were engineered by [`src/prepare_phase3_data.py`](../../src/prepare_phase3_data.py) using the authoritative 12-month annual cycle (`2021-05-01` to `2022-04-23`, 345 active observation dates):

### A. Full Cohort (Dataset A: 24 Documented kWp Sites)
Stored under `data/processed/unisolar/`:
- **`train.csv`**: $4,770$ site-days across 234 active calendar dates (`2021-05-01` to `2021-12-31`). 33 columns (3 IDs, 1 target, 29 predictive features).
- **`validation.csv`**: $1,037$ site-days across 58 active calendar dates (`2022-01-01` to `2022-02-28`). 33 columns.
- **`test.csv`**: $1,232$ site-days across 53 active calendar dates (`2022-03-01` to `2022-04-23`). 33 columns.
- **Total Valid Site-Days:** $7,039$ site-days ($80.35\%$ of 8,760 expected annual site-days).
- **`diagnostic_metadata.csv`**: $7,039$ rows $\times$ 17 columns (isolated quality flags, intervals, and raw energy sums).
- **`excluded_site_days.csv`**: $1,481$ site-days excluded due to failing the valid site-day quality gate.

### B. Peer Cohort (Dataset B: 22 Clean Physical Sites)
Stored under `data/processed/unisolar/peer_cohort/`:
- **`train.csv`**: $4,383$ site-days across 234 active calendar dates (`2021-05-01` to `2021-12-31`). 33 columns.
- **`validation.csv`**: $945$ site-days across 58 active calendar dates (`2022-01-01` to `2022-02-28`). 33 columns.
- **`test.csv`**: $1,128$ site-days across 53 active calendar dates (`2022-03-01` to `2022-04-23`). 33 columns.
- **Total Valid Site-Days:** $6,456$ site-days. Excludes anomalous Site 19 ($Y_f = 18.21$) and Site 24 ($Y_f = 6.08$).
- **`diagnostic_metadata.csv`**: $6,456$ rows $\times$ 17 columns.

---

## 3. Hardware Catalogue Datasets (Layer B)

Stored under `configs/`:
- **`panels_catalogue_schema.json`**: Authoritative canonical schema definition containing 43 fields across 8 categories.
- **`panels_catalogue_template.csv`**: Header-only CSV template containing all 43 canonical columns.
- **`panels_catalogue.csv`**: Active catalogue file containing 3 unverified raw records extracted from `Solar_Site_Details.csv` (Trina 330W, Trina 310W, SunPower SPR-E20-435-COM) with 34 empty fields (`NaN`) pending official manufacturer datasheet ingestion.

---

## 4. Strict Non-Pooling Policy

> [!CAUTION]
> **Prohibition Against Cross-Dataset Tabular Pooling:**
> In Phase 2 Task 5, mathematical and physical audits proved that pooling Kaggle and UNISOLAR into a single joint training table is scientifically invalid:
> 1. **Semantic Target Mismatch:** Kaggle generation represents instantaneous inverter-level power (kW), while UNISOLAR represents 15-minute integrated energy intervals (kWh).
> 2. **Covariate Shift:** Kaggle provides on-site pyranometer `IRRADIATION` ($r = 0.985$ with generation), whereas UNISOLAR provides regional off-site ambient temperature and humidity proxies ($r = 0.194$).
> 3. **Geographical & Climate Divergence:** Kaggle is located in tropical India (May–June monsoon onset), whereas UNISOLAR is located in temperate southern Australia (May–April full annual cycle).

