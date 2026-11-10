# Feature Engineering — SolarSelect

This document details the feature engineering methodology, astronomical calculations, autoregressive lag formulations, and the authoritative 29 predictive inputs used in **SolarSelect Layer A**.

---

## 1. Feature Space Overview

The model training matrix contains **29 continuous and cyclical predictive features** strictly isolated from diagnostic and target metadata:

```text
The 29 Authoritative Predictive Inputs
├── A. Capacity & Geometry (1 feature)
│   └── kWp (Nameplate DC rating)
├── B. Calendar & Cyclical Transforms (7 features)
│   ├── day_of_year, month, is_weekend
│   ├── day_sin, day_cos (Cyclical day-of-year encoding)
│   └── month_sin, month_cos (Cyclical month encoding)
├── C. Analytical Astronomical Features (3 features)
│   ├── solar_noon_elevation_deg (Solar altitude angle at solar noon)
│   ├── daylight_hours (Astronomical photoperiod between sunrise/sunset)
│   └── extraterrestrial_radiation_h0 (Extraterrestrial daily insolation H0)
├── D. Day-Ahead Weather Proxies (tau >= 24h) (7 features)
│   ├── lag1_temp_mean, lag1_temp_max, lag1_temp_min, lag1_temp_range
│   ├── lag1_rh_mean (Relative humidity mean)
│   └── temp_rolling_mean_7d, rh_rolling_mean_7d (7-day backward moving averages)
├── E. Autoregressive Yield Lags & Volatility (7 features)
│   ├── lag1_daily_yield (t-1 specific yield)
│   ├── lag2_daily_yield (t-2 specific yield)
│   ├── lag7_daily_yield (t-7 same-weekday specific yield)
│   ├── rolling_mean_7d_yield, rolling_std_7d_yield (7-day backward moving stats)
│   ├── rolling_mean_14d_yield (14-day backward moving average)
│   └── rolling_mean_30d_yield (30-day baseline trend)
└── F. Telemetry & Lag Availability Flags (4 features)
    └── has_valid_lag1, has_valid_lag2, has_valid_lag7, has_valid_rolling7
```

---

## 2. Analytical Astronomical Formulas

Because on-site pyranometer irradiance is absent in UNISOLAR, three analytical astronomical features provide deterministic physical bounds derived solely from latitude ($\phi = -37.71828652^\circ\text{ S}$) and Julian day ($N = \text{day\_of\_year}$):

1. **Solar Declination Angle ($\delta$):**
   $$\delta = 23.45^\circ \cdot \sin\left(\frac{360^\circ}{365} \cdot (284 + N)\right)$$
2. **Solar Noon Elevation Angle ($\alpha_{\text{noon}}$):**
   $$\alpha_{\text{noon}} = 90^\circ - |\phi - \delta|$$
3. **Sunset Hour Angle ($\omega_s$):**
   $$\omega_s = \arccos(-\tan(\phi) \cdot \tan(\delta))$$
4. **Daylight Hours ($T_{\text{daylight}}$):**
   $$T_{\text{daylight}} = \frac{2 \cdot \omega_s}{15^\circ/\text{hour}}$$
5. **Daily Extraterrestrial Radiation ($H_0$):**
   $$H_0 = \frac{24 \times 3600}{\pi} \cdot G_{\text{sc}} \cdot \left(1 + 0.033 \cos\left(\frac{360^\circ \cdot N}{365}\right)\right) \cdot \left(\cos(\phi)\cos(\delta)\sin(\omega_s) + \frac{\pi \cdot \omega_s}{180^\circ} \sin(\phi)\sin(\delta)\right)$$
   Where $G_{\text{sc}} = 1367\text{ W}/\text{m}^2$ is the solar constant.

---

## 3. Autoregressive Lag Engineering & Imputation

1. **Day-Ahead Lead Horizon ($\tau \ge 24\text{h}$):** All autoregressive lags enforce a strict day-ahead operational horizon. To forecast day $d$, only observations from day $d-1$ or earlier are permissible.
2. **Static Imputation Medians:** Lags for missing dates are imputed using static medians fitted strictly on the Training partition:
   - `lag1_daily_yield`: $2.2799\text{ kWh}/\text{kW}_p/\text{day}$
   - `lag2_daily_yield`: $2.2569\text{ kWh}/\text{kW}_p/\text{day}$
   - `lag7_daily_yield`: $2.2679\text{ kWh}/\text{kW}_p/\text{day}$
   - `rolling_mean_7d_yield`: $2.5852\text{ kWh}/\text{kW}_p/\text{day}$
   - `rolling_std_7d_yield`: $0.7850\text{ kWh}/\text{kW}_p/\text{day}$
   - `lag1_temp_mean`: $12.167^\circ\text{C}$
   - `lag1_rh_mean`: $78.114\%$
3. **Imputation Quality Flagging:** When an imputed value is substituted, the corresponding indicator (`has_valid_lag1`) is set to `0`, allowing non-linear tree models to split on observation certainty.

