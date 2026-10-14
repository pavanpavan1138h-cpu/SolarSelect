# SolarSelect — AI-Based Solar Panel Selection Assistant

SolarSelect is an MLOps project focused on solar power forecasting and supporting data-driven solar panel selection. The project aims to build a reproducible machine learning pipeline with data validation, preprocessing, model evaluation, and future monitoring capabilities.

## Project Objectives

- Analyze solar power generation and weather data.
- Prepare plant-level power data for 15-minute-ahead forecasting.
- Establish reproducible data preprocessing and validation.
- Support model development and evaluation.
- Extend the pipeline with experiment tracking, data drift monitoring, and retraining as the project progresses.

## Dataset

The project uses the Kaggle **Solar Power Generation Data** dataset.

Dataset source: https://www.kaggle.com/datasets/anikannal/solar-power-generation-data

### Input Files

| File | Description |
|---|---|
| `Plant_1_Generation_Data.csv` | Generation records for Plant 1 |
| `Plant_1_Weather_Sensor_Data.csv` | Weather measurements for Plant 1 |
| `Plant_2_Generation_Data.csv` | Generation records for Plant 2 |
| `Plant_2_Weather_Sensor_Data.csv` | Weather measurements for Plant 2 |

The generation data includes DC power, AC power, daily yield, total yield, timestamps, and source identifiers. The weather data includes ambient temperature, module temperature, and irradiation.

## Project Structure

```text
SolarSelect/
├── EDA/
│   ├── 01_dataset_overview.ipynb.ipynb
│   ├── validate_aggregate.py
│   ├── check_inverter_coverage.py
│   ├── inspect_source_availability.py
│   ├── prepare_plant_data.py
│   ├── align_power_weather.py
│   ├── create_forecasting_target.py
│   ├── check_forecasting_gaps.py
│   └── split_complete_coverage.py
├── data/
│   ├── raw/
│   │   └── archive/
│   │       ├── Plant_1_Generation_Data.csv
│   │       ├── Plant_1_Weather_Sensor_Data.csv
│   │       ├── Plant_2_Generation_Data.csv
│   │       └── Plant_2_Weather_Sensor_Data.csv
│   ├── interim/
│   └── processed/
│       ├── splits/
│       └── complete_coverage/
├── reports/
└── README.md
```

*Note: This structure describes the current data-preparation work. Update it if files are renamed, moved, or added.*

## Data Preparation and EDA

The current preprocessing workflow includes:

1. **Data validation:** Check required columns, timestamp formats, missing values, duplicate rows, numeric values, and basic physical constraints.
2. **Plant-level aggregation:** Sum inverter-level AC and DC power by plant and timestamp.
3. **Source coverage analysis:** Identify timestamps with fewer than the 22 distinct sources observed in each plant's dataset.
4. **Weather alignment:** Merge plant-level power readings with weather measurements using timestamps.
5. **Forecast target creation:** Construct the target as total plant AC power exactly 15 minutes after the input timestamp.
6. **Timestamp-gap analysis:** Identify irregular gaps and verify future-target alignment.
7. **Chronological splitting:** Prepare preliminary training, validation, and test datasets while preserving time order.
8. **Complete-coverage subsets:** Create separate datasets requiring complete source counts at both the input and target timestamps.

Raw CSV files are retained unchanged. Intermediate and processed datasets are generated separately.

## Initial Data Findings

- All four input CSV files passed the implemented basic validation checks.
- Plant 1 generation data contains 68,778 rows; Plant 2 contains 67,698 rows.
- Plant 1 weather data contains 3,182 rows; Plant 2 contains 3,259 rows.
- Each plant has 22 distinct source identifiers in its generation data.
- Plant 1 has 101 timestamps with fewer than 22 source records.
- Plant 2 has 904 timestamps with fewer than 22 source records.
- One Plant 1 power timestamp has no matching weather observation; Plant 2 has no unmatched weather timestamps.
- Exact 15-minute target alignment was verified for all non-missing targets in both plants.

Incomplete source coverage does not automatically mean the total power reading is incorrect. These cases are flagged for further analysis rather than silently treated as zero or removed from the raw data.

## Forecasting Task

**Prediction objective:** Forecast total plant-level AC power 15 minutes ahead.

\[
\text{Target}(t)=\text{AC Power}(t+15\text{ minutes})
\]

The intended forecasting workflow uses information available at or before the prediction time. Observed future weather must not be used as an input unless it is supplied by a legitimate forecast source.

The final feature set, model selection, evaluation protocol, and deployment workflow remain subject to the modelling team's implementation and validation.

## Environment Setup

Python 3.11 is the intended project environment.

Activate the project's existing virtual environment, or create one if needed:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install pandas numpy matplotlib seaborn jupyter
```

If the project already has a dependency or lock file, use that file as the authoritative environment specification instead of installing a separate set of versions.

## Running the Data Preparation Scripts

Run commands from the project root:

```bash
python EDA/validate_aggregate.py
python EDA/check_inverter_coverage.py
python EDA/inspect_source_availability.py
python EDA/prepare_plant_data.py
python EDA/align_power_weather.py
python EDA/create_forecasting_target.py
python EDA/check_forecasting_gaps.py
python EDA/split_complete_coverage.py
```

Run scripts in the intended order because later scripts depend on files produced by earlier ones.

## Current Scope

**Completed in the current data-preparation workflow**
- Basic validation of the four raw datasets.
- Plant-level generation aggregation.
- Source-coverage diagnostics.
- Power-weather alignment.
- Exact 15-minute target construction and verification.
- Preliminary chronological and complete-coverage dataset preparation.

**Future project work**
- Finalize the modelling dataset and split policy.
- Train and compare forecasting models.
- Track experiments and model versions.
- Implement data and model drift monitoring.
- Establish retraining and model-promotion procedures.

## Notes

- Raw data should remain unchanged.
- Missing readings should not automatically be replaced with zero.
- Random shuffling should not be used for the time-series evaluation split.
- Preliminary processed datasets must be reviewed before being treated as final model inputs.
- Keep credentials, local environment folders, and unnecessary generated files out of version control.

## Modelling & evaluation (Phase 1)

- Code: `src/solarselect/modeling/` (data/feature sets, models, metrics, `run_experiments.py`); tests in `tests/`.
- Protocol: [`docs/evaluation_protocol.md`](docs/evaluation_protocol.md) · Results: [`docs/model_comparison_report.md`](docs/model_comparison_report.md), `reports/`.
- Run: `python -m src.solarselect.modeling.run_experiments` (needs `pyyaml tabulate xgboost lightgbm mlflow`; macOS also `brew install libomp`).
