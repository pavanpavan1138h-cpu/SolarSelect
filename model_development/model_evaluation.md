# SolarSelect Model Evaluation

## Goal

Predict each solar plant’s total AC power 15 minutes ahead using information available at the current time.

## Models

- **Persistence baseline:** Predicts that the next AC power reading will equal the current AC power reading.
- **XGBoost:** Uses current AC power, DC power, weather readings, and time-of-day features. The same model setup was trained separately for each plant.

XGBoost settings: 300 trees, maximum depth 4, learning rate 0.05, subsample 0.8, and column subsample 0.8.

## Evaluation approach

The data was split chronologically into training, validation, and test periods. Model choices were checked on validation data. For the final test, XGBoost was trained on the combined training and validation data.

Daytime results use rows where irradiation at the input timestamp is greater than zero. Positive bias means predictions are higher than the actual values on average.

## Final test results

| Plant | Model | MAE | RMSE | R² | Daytime MAE | Daytime RMSE | Bias |
|---|---|---:|---:|---:|---:|---:|---:|
| Plant 1 | Persistence | 1,219.44 | 2,327.45 | 0.9200 | 2,201.48 | 3,127.23 | 1.84 |
| Plant 1 | XGBoost | 1,156.56 | 2,312.65 | 0.9210 | 2,073.03 | 3,107.25 | 128.00 |
| Plant 2 | Persistence | 1,215.69 | 2,349.62 | 0.8262 | 2,173.10 | 3,141.42 | 0.00 |
| Plant 2 | XGBoost | 1,099.08 | 2,175.65 | 0.8510 | 1,955.90 | 2,908.79 | 38.12 |

## Findings

XGBoost had lower errors than persistence on both plants. For Plant 1, the improvement was modest: MAE fell by about 5%, while RMSE fell by less than 1%. For Plant 2, MAE fell by about 10% and RMSE by about 7%.

Daytime MAE was lower with XGBoost for both plants. XGBoost predictions were slightly high on average, especially for Plant 1.

## MLflow tracking

The validation and final test runs were recorded in the `SolarSelect-Forecasting` MLflow experiment. XGBoost model artifacts were logged with the final test runs.

Local MLflow files are stored in `mlflow.db` and `EDA/mlruns/`. These files are excluded from Git.

## Scope

These results describe the held-out test period in the available dataset. They do not establish how the models will perform on future seasons or other solar plants.