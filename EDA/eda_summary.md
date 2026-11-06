# EDA Summary — SolarSelect

## 1. Objective

The purpose of exploratory data analysis (EDA) is to understand the solar generation datasets, examine data quality, identify relationships between power output and weather conditions, and document findings that can guide subsequent modelling.

## 2. Dataset Overview

The project uses generation and weather data from two solar plants, covering 15 May 2020 to 17 June 2020.

| Dataset | Rows | Columns |
|---|---:|---:|
| Plant 1 generation | 68,778 | 7 |
| Plant 1 weather | 3,182 | 6 |
| Plant 2 generation | 67,698 | 7 |
| Plant 2 weather | 3,259 | 6 |

The generation data contains individual source-level measurements, while the prepared interim datasets contain plant-level aggregated power measurements aligned with weather observations.

## 3. Data Quality and Coverage

- Basic validation found no missing values or exact duplicate rows in the four original CSV files.
- Timestamp formats differed across the original datasets and were standardized during preprocessing.
- Plant 1 has 3,158 generation timestamps, of which 3,057 have complete source coverage.
- Plant 2 has 3,259 generation timestamps, of which 2,355 have complete source coverage.
- Plant 1 has one generation timestamp without a matching weather timestamp. Plant 2 has no unmatched generation timestamps.

**Modelling implication:** Coverage completeness should be considered during evaluation because missing source records may affect aggregated power measurements. Incomplete-coverage observations should not automatically be deleted without a documented policy.

## 4. Distribution Analysis

Generation histograms show right-skewed distributions, with many low or zero power observations and fewer high-power observations.

Irradiation distributions contain many observations near zero, while temperature measurements span wider ranges.

**Modelling implication:** Zero-power observations must be retained when they represent legitimate nighttime conditions. Distribution shape should be considered when evaluating model errors and residuals.

## 5. Potential Outliers

The interquartile range (IQR) method was used to identify potential outliers.

- Plant 1 generation variables had no IQR-flagged observations.
- Plant 2 AC_POWER had 2,993 potential outliers (4.42%); DC_POWER had 3,079 (4.55%).
- Weather measurements had few flagged values: two irradiation observations in Plant 1, one in Plant 2, and two module-temperature observations in Plant 2.
- No ambient-temperature observations were flagged in either plant.

These are statistical flags, not confirmed data errors.

**Modelling implication:** Flagged observations should be investigated before any removal or transformation. Valid high-power measurements and nighttime zeros should be preserved.

## 6. Correlation Analysis

Using the prepared plant-level datasets:

| Relationship | Plant 1 | Plant 2 |
|---|---:|---:|
| AC_POWER vs DC_POWER | 1.00 | 1.00 |
| AC_POWER vs IRRADIATION | 0.996 | 0.911 |
| AC_POWER vs MODULE_TEMPERATURE | 0.96 | 0.87 |
| AC_POWER vs AMBIENT_TEMPERATURE | 0.73 | 0.65 |
| MODULE_TEMPERATURE vs IRRADIATION | 0.96 | 0.95 |

The correlations indicate strong positive associations between irradiation and power output in both plants. Module temperature is also strongly associated with irradiation and power.

Plant 1's AC_POWER–IRRADIATION correlation remains approximately 0.996 when restricted to complete-coverage timestamps. For Plant 2, the correlation increases from approximately 0.911 to 0.927 on complete-coverage timestamps.

**Modelling implication:** Weather and time-related variables are candidates for predictive features. Strongly correlated features should be evaluated for redundancy rather than removed automatically.

These correlations are descriptive and do not establish predictive performance or causation.

## 7. Scatter Plot Analysis

The scatter plots show an approximately linear increase in Plant 1 power with irradiation. Plant 2 displays greater variation at higher irradiation values and a possible plateau in output.

Temperature and power are positively associated overall, but observations at similar temperatures can have substantially different power values.

**Modelling implication:** Irradiation appears particularly informative, while temperature alone is unlikely to explain all variation in power output. The observed plateau and scattered measurements warrant further investigation.

## 8. Diurnal Analysis

Average hourly power curves show a clear daily generation pattern in both plants.

- Plant 1 reaches its highest average output around 11:00–12:00.
- Plant 2 maintains a broader high-output period during the middle of the day.
- Both plants show very low average output overnight.

**Modelling implication:** Hour-of-day features may help the model capture recurring daily patterns. These plots show averages across the available dates and should not be interpreted as representing every individual day.

## 9. Daylight and Coverage Analysis

Using positive irradiation as a daylight proxy:

| Plant | Mean AC_POWER at zero irradiation | Mean AC_POWER at positive irradiation |
|---|---:|---:|
| Plant 1 | 2.07 | 12,067.93 |
| Plant 2 | 0.012 | 8,772.29 |

Mean power is substantially higher during positive-irradiation observations in both plants.

Coverage comparisons also reveal differences in mean power between complete and incomplete timestamps, particularly in Plant 1. These differences may reflect temporal composition or missing source contributions; the current analysis does not establish the cause.

## 10. Important Forecasting Considerations

The forecasting target is plant-level AC power at the next 15-minute interval.

- Features must be available at or before the prediction timestamp.
- Actual future irradiation or temperature must not be used unless supplied by a genuine forecast available at prediction time.
- Coverage status and missing source contributions should be handled consistently.
- Chronological splitting should be preserved to prevent future observations from leaking into training.
- Final feature selection should be based on the forecasting protocol and validation results, not correlation alone.

## 11. Conclusion

The EDA identifies strong relationships between irradiation and power, recurring daily generation patterns, potential outliers requiring investigation, and differences in source coverage between the plants. These findings provide a basis for feature engineering and evaluation while highlighting the importance of timestamp alignment, data completeness, and leakage prevention.