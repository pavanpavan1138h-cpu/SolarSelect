# Model Limitations — SolarSelect

This document formally details the structural, operational, and predictive limitations of the machine learning forecasting models in **SolarSelect Layer A**.

---

## 1. Operational and Predictive Limitations

1. **Seasonal Level Shifts:**
   - Decision tree models (ExtraTrees) predict target values bounded strictly by the minimum and maximum leaves observed in the training partition.
   - When operational conditions shift significantly beyond historical training extremes (such as sudden heatwaves or unseasonal cloud cover), tree models will saturate at leaf boundary averages.
2. **Dependence on Prior Telemetry (Lag Availability):**
   - The primary models leverage autoregressive lags ($t-1$, $t-2$, $t-7$).
   - When a PV system experiences prolonged telemetry outages (>7 consecutive days), the model falls back entirely on training imputation medians. While single-day dropouts showed comparable tracking errors in offline validation diagnostics, prolonged dropouts degrade dynamic response and rely heavily on astronomical priors.

3. **Site 19 and 24 Distortion in Full Cohort:**
   - The Full Cohort model (ElasticNet) achieves an inflated nominal $R^2$ of $0.7407$ primarily because it fits the high-energy cluster of Site 19 ($Y_f \approx 18–40\text{ kWh}/\text{kW}_p/\text{day}$).
   - **Restriction:** The Full Cohort model must **NEVER be used for individual rooftop panel recommendations**, as its linear coefficients are influenced by unverified feeder aggregation on Site 19.
4. **Spatial Non-Transferability (Geographic Bound):**
   - The models were trained and evaluated exclusively on the UNISOLAR Campus 1 rooftop network in Melbourne, Australia ($-37.7^\circ\text{ S}$).
   - The model weights cannot be transferred directly to equatorial or high-latitude locations without localized re-training and re-calibration of astronomical coefficients.
5. **Absence of Numerical Weather Forecasts in Telemetry:**
   - Model development was performed using realized historical weather observations from regional BOM stations.
   - Real-world day-ahead forecasting accuracy will depend on the error distribution of the upstream meteorological forecast provider (e.g., GFS, ECMWF, BOM day-ahead forecasts). Forecast errors in temperature and humidity will propagate into yield prediction error.

