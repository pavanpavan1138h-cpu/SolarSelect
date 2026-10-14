# Initial model comparison (Phase 1, Person 3)

Full tables: `reports/model_comparison.md` / `.csv`. Figures: `reports/figures/`. All numbers are **test-set**, in W, from one run (seed 42, git `ecd47d7`, data hash `6ec4a923eeb945d2`).

## Headline results (in-plant, `forecast` features)
| Plant | Persistence MAE | Hour-of-day MAE | Ridge MAE | **Random Forest MAE** | XGBoost MAE | LightGBM MAE |
|---|---|---|---|---|---|---|
| plant1 | 1,268 | 1,586 | 1,394 | **1,107** | 1,132 | 1,157 |
| plant2 | 1,231 | 1,424 | 1,319 | **1,070** | 1,096 | 1,143 |

Plant capacity is ~25–29 kW peak, so the best MAE is roughly 4% of peak. R²: 0.93 (plant1), 0.88 (plant2).

## Which model is best?
**Random Forest has the lowest MAE on both plants**, but it is a small margin over XGBoost (~2%) and LightGBM (~4–7%). With 4–5 test days these three are not separable. What the data does support (day-block bootstrap, 95% CI for MAE gain vs persistence, W):

| Plant | RF | XGBoost | LightGBM | Ridge | Hour-of-day |
|---|---|---|---|---|---|
| plant1 | +160 [81, 242] | +136 [42, 238] | +111 [19, 214] | −126 [−179, −43] | −318 [−463, −186] |
| plant2 | +161 [64, 288] | +135 [69, 225] | +87 [−11, 205] | −88 [−127, −8] | −193 [−557, 214] |

- Tree ensembles beat persistence by ~10–13% MAE, significantly on both plants (LightGBM on plant2 is borderline).
- **Ridge and the hour-of-day mean are worse than persistence on MAE.** Persistence is a strong baseline at 15 min because cloud-driven changes are small step to step. Ridge does have lower RMSE/higher R² than persistence (it is better on large errors, worse on typical ones).
- XGBoost "remains a candidate" as planned, but this data does not show it winning; RF is the measured leader, tree models are statistically tied.

## Bias and daytime
- All models' daytime MAE (~2.0–2.1 kW plant1, ~1.9–2.0 kW plant2) is ~2× the all-day MAE: night is trivially zero and flatters all-day metrics. Report daytime numbers for decisions.
- Bias is small for plant2 (|bias| < 110 W for tree models/Ridge). Plant1 trees over-forecast by ~245–355 W; hour-of-day mean over-forecasts by 450–900 W (the test window is cloudier than the training average).

## Feature ablations (XGBoost)
| Set | plant1 MAE | plant2 MAE |
|---|---|---|
| forecast (main) | 1,132 | 1,096 |
| nowcast (no lags) | 1,188 | 1,100 |
| forecast_no_weather | 1,133 | 1,075 |
| **leaky (future observed weather)** | **274** | **684** |

- Lags help plant1 (~5%) and not plant2; weather features add nothing measurable once `AC_POWER(t)` is known (the current power already encodes irradiation).
- **Leakage is large:** supplying the *actual* irradiation at t+15 cuts MAE by 76% (plant1) and 38% (plant2). Such a model is not deployable without a real irradiance forecast, which is why the legitimate sets exclude it.

## Cross-plant generalisation
| Train → Test | Persistence | Ridge | RF | XGBoost | LightGBM |
|---|---|---|---|---|---|
| plant1 → plant2 (MAE) | 1,231 | 1,463 | 1,336 | 1,293 | 1,283 |
| plant2 → plant1 (MAE) | 1,268 | 1,414 | 1,278 | 1,525 | 1,404 |

- **No transferred model beats persistence**, and cross-plant error is 10–40% worse than in-plant. Plant-specific training is needed.
- **Data finding:** `DC_POWER/AC_POWER ≈ 10.2` at plant1 but ≈ 1.02 at plant2, i.e. plant1's DC column is on a different scale. Feeding `DC_POWER` across plants made Ridge fail catastrophically (plant2→plant1 MAE 34,682 W, R² −43). Cross-plant runs therefore use `forecast_no_dc`; the failing run is kept in MLflow as evidence. (Person 1/2: worth documenting in the data card and leakage/feature audit.)

## Caveats (state these at review)
1. Only ~34 days of data per plant (May–June 2020): test windows are 4–5 days, a single season, and no hourly/seasonal coverage. Rankings among tree models can flip with a different window.
2. Splits are the preliminary 70/15/15 from the data-prep step; no expanding-window CV yet.
3. Hyper-parameter grids are small (≤16 candidates per model); no Optuna search.
4. Metrics are on `complete_coverage` rows only; rows with missing inverters (Plant 2: ~40% of rows) are excluded by the split definition, so operational error on incomplete-coverage periods is not measured.
5. Test R² for plant2 is lower partly because its test window has fewer rows with high output; compare models within a plant, not across plants.

## Next steps
Walk-forward CV across days; tune on more than 3 days of validation; add an irradiance-forecast-based feature set to replace the leaky one; add `reports/` figures to the review deck.
