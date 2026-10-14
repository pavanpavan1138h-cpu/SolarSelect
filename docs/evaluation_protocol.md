# Evaluation protocol (Person 3)

**Task.** Predict total plant AC power (W) 15 minutes ahead: `TARGET_AC_POWER_15MIN(t) = AC_POWER(t+15min)`.

## Data and splits
- Source: `data/processed/complete_coverage/plantN_{train,validation,test}.csv` (chronological 70/15/15, produced by `EDA/split_complete_coverage.py`). Rows require all 22 inverters at both input and target timestamps, so the target is not corrupted by missing inverters.
- Split boundaries are time-ordered with no shuffling; train/validation targets never cross a boundary.

| Plant | Train | Validation | Test |
|---|---|---|---|
| plant1 | 2,119 rows, 05-15 → 06-08 | 453, 06-08 → 06-13 | 455, 06-13 → 06-17 |
| plant2 | 1,642 rows, 05-15 → 06-10 | 351, 06-10 → 06-14 | 353, 06-14 → 06-17 |

- **Seed:** 42 for all stochastic models. Hyper-parameters are chosen on **validation MAE only**; the test split is touched once per configuration.
- **Lag features** are computed on the full per-plant 15-min grid from past values only, so a split's first rows may use history from before the boundary (legal; verified by `tests/test_modeling.py::test_lags_use_only_past`).

## Protocols
1. **In-plant chronological:** train on plant X train, test on plant X test.
2. **Cross-plant:** train on plant A train (hyper-parameters from A's validation), test on plant B test. Both directions.

## Feature sets (`src/solarselect/modeling/data.py`)
| Set | Contents | Legitimate? |
|---|---|---|
| `nowcast` | calendar (sin/cos time of day, day of year) + observations at t (AC, DC, ambient/module temp, irradiation) | yes |
| `forecast` | nowcast + AC lags (15m, 30m, 1h, 24h), irradiation lag, 1h rolling means | yes (main) |
| `forecast_no_weather` | forecast without weather columns | yes |
| `forecast_no_dc` | forecast without `DC_POWER` (needed cross-plant, see below) | yes |
| `leaky` | forecast + **observed** irradiation / module temperature at t+15 | **no** – ablation only |

## Models
Persistence (`AC(t)`), hour-of-day mean (mean target per 15-min slot), Ridge, Random Forest, XGBoost, LightGBM. Grids in `params.yaml`.

## Metrics (`metrics.py`)
MAE, RMSE, R², **safe MAPE** (only where actual ≥ 1 kW), **bias** = mean(pred − actual), and **daytime-only** MAE/RMSE/bias where daytime = input irradiation > 0.01 kW/m² (defined from the input side, not the target, so it cannot be gamed).

## Tracking
Every configuration is an MLflow run (`solarselect-phase1`, SQLite `mlflow.db`) with params, val/test metrics, and tags `git_sha`, `data_hash`, `stage`, `protocol`, `feature_set`. 34 runs per execution.

## Reproduce
```bash
python -m pip install -r requirements.txt pyyaml tabulate xgboost lightgbm mlflow
# macOS: brew install libomp   (XGBoost/LightGBM need OpenMP)
python -m src.solarselect.modeling.run_experiments
python -m pytest tests
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
Suggested DVC stage for Person 4:
```yaml
evaluate:
  cmd: python -m src.solarselect.modeling.run_experiments
  deps: [src/solarselect/modeling, data/processed/complete_coverage, data/interim, params.yaml]
  params: [modeling]
  outs: [reports/model_comparison.csv, reports/model_comparison.md, reports/figures]
  metrics: [reports/bootstrap_vs_persistence.csv]
```
