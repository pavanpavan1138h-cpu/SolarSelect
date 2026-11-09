# SolarSelect — Dataset Inspection and Source Verification

**Directory:** `notebooks/data_inspection/`  
**Master Notebook:** [`dataset_inspection_and_source_verification.ipynb`](dataset_inspection_and_source_verification.ipynb)  
**Status:** Completed & Validated

---

## 1. Scope & Objective

This directory contains the complete technical record of all data inspection and suitability audits performed for the SolarSelect MLOps project:
1. **Initial Kaggle Suitability Audit:** Inspecting the 4 original CSVs (`Plant_1_Generation_Data.csv`, `Plant_1_Weather_Sensor_Data.csv`, `Plant_2_Generation_Data.csv`, `Plant_2_Weather_Sensor_Data.csv`).
2. **Deep Kaggle Sensor & Inverter Audit:** Validating 22 distinct inverters per plant, source keys, plant IDs, 34-day observation horizon (May 15 to June 17, 2020), timestamp formats (`%d-%m-%Y %H:%M` vs `%Y-%m-%d %H:%M:%S`), and on-site weather parameters.
3. **Supplementary Dataset Verification:** Evaluating candidate multi-year datasets (UNISOLAR vs Cyprus PV).
4. **UNISOLAR Download Verification:** Validating the integration of 4 core UNISOLAR files into `data/raw/unisolar/`.
5. **Full Raw Inventory & Schema Audit:** Confirming schemas, dtypes, candidate primary keys, and sample records across all 8 collected datasets.

---

## 2. Directory Contents

| File | Purpose |
| :--- | :--- |
| [`dataset_inspection_and_source_verification.ipynb`](dataset_inspection_and_source_verification.ipynb) | Master executable Jupyter notebook running all inspection code, tables, and verification outputs. |
| [`figures/raw_dataset_dimensions_and_record_counts.png`](figures/raw_dataset_dimensions_and_record_counts.png) | High-contrast visualization comparing dataset row counts and dimensionality across sources. |
| [`README.md`](README.md) | Documentation and execution guide (this file). |

---

## 3. Key Findings

1. **Kaggle Solar Power Archive:**
   - 4 CSVs, 139,658 generation rows across 2 utility-scale plants in India.
   - 22 inverters per plant; 1 on-site weather monitoring station per plant.
   - Temporal span: strictly 34 days (May 15 – June 17, 2020). Single-season micro-grid coverage.
   - Plant 1 `DC_POWER` is recorded in raw sensor counts ($\approx 10\times$ AC power), whereas Plant 2 `DC_POWER` is in physical kW.
2. **UNISOLAR Dataset:**
   - 4 CSVs, 2,731,946 generation rows across 90 sites and 4 university campuses in Australia.
   - Multi-year temporal span: 2015 to 2020 (5.5 years).
   - Instantaneous power vs interval energy: Kaggle records power ($\text{kW}$), while UNISOLAR records 15-minute integrated energy ($\text{kWh}$).

---

## 4. Execution

To reproduce the data inspection analysis:
```bash
cd notebooks/data_inspection
jupyter notebook dataset_inspection_and_source_verification.ipynb
```
Or execute headless:
```bash
jupyter nbconvert --execute --inplace dataset_inspection_and_source_verification.ipynb
```
