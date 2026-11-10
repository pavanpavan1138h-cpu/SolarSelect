# Data Limitations — SolarSelect

This document formally details the empirical data anomalies, sensor limitations, and missingness characteristics identified in the raw and processed datasets.

---

## 1. Provisional Hardware & Capacity Anomalies (Site 19 & Site 24)

In Phase 2 and Phase 3, physical capacity scaling audits revealed substantial discrepancies between documented nameplate capacity and observed telemetry on two campus installations:

### A. Site 19 Investigation
- **Documented Metadata:** $34.32\text{ kW}_p$ ($104 \times \text{Trina 330W}$ panels) paired with $1 \times \text{SolarEdge SE27.6K}$ inverter.
- **Observed Generation Behaviour:**
  * Recorded peak 15-minute interval energy reaches $42.22\text{ kWh}$.
  * Converting this 15-minute energy to an equivalent average power over the interval:
    $$P_{\text{interval, avg}} = \frac{42.22\text{ kWh}}{0.25\text{ h}} = 168.88\text{ kW}$$
  * Comparing this equivalent average interval power to documented DC nameplate capacity:
    $$\text{Ratio} = \frac{168.88\text{ kW}}{34.32\text{ kW}_p} \approx 492.06\%$$
  * Comparing to documented inverter AC rating ($27.6\text{ kW}$):
    $$\text{Ratio} = \frac{168.88\text{ kW}}{27.6\text{ kW}} \approx 611.88\%$$
  * Observed daily specific yield averages $18.21\text{ kWh}/\text{kW}_p/\text{day}$ (peaking at $40.79\text{ kWh}/\text{kW}_p/\text{day}$).
- **Working Hypothesis:** Multiple unmetered building rooftop arrays or an entire building feeder appear aggregated into Site 19's telemetry channel.
- **Scientific Protocol:** Feeder aggregation remains an **unproven hypothesis**. The root cause has not been conclusively established. To prevent subjective data tampering, Site 19 observations are **preserved exactly as recorded without arbitrary clipping or deletion**. Instead, Site 19 is isolated from the clean Peer Cohort (Dataset B) and retained solely in the Full Cohort (Dataset A).

### B. Site 24 Investigation
- **Documented Metadata:** $40.26\text{ kW}_p$ ($122 \times \text{Trina 330W}$ panels) paired with $1 \times \text{SolarEdge SE82.8K}$ inverter. (Retaining the corrected Phase 3 capacity of $40.26\text{ kW}_p$, not the obsolete $33.15\text{ kW}_p$ figure).
- **Observed Generation Behaviour:**
  * Observed daily specific yield averages $6.08\text{ kWh}/\text{kW}_p/\text{day}$ (peaking at $13.57\text{ kWh}/\text{kW}_p/\text{day}$).
  * Observed peak 15-minute interval energy recorded in the authoritative Phase 3 dataset is $16.59\text{ kWh}$, representing an equivalent average interval power of $66.36\text{ kW}$ ($P_{\text{avg}} = \frac{E_{\text{interval}}}{0.25\text{ h}} = \frac{16.59\text{ kWh}}{0.25\text{ h}} = 66.36\text{ kW}$), which exceeds the panel nameplate equivalent ($40.26\text{ kW}_p$, $164.83\%$). (Note: A preliminary observation cited $13.63\text{ kWh}$ yielding $54.52\text{ kW}$; both confirm panel exceedance).
  * However, this observed power does **NOT exceed the documented SolarEdge SE82.8K inverter rating of $82.8\text{ kW}$** ($66.36\text{ kW} / 82.8\text{ kW} = 80.14\% \le 100\%$).
- **Working Hypothesis:** Documented panel count is likely underreported relative to the installed DC array.
- **Scientific Protocol:** Retained as a provisional data concern. Root cause remains unconfirmed. Excluded from Peer Cohort (Dataset B) to maintain physical bounds, but retained in Full Cohort (Dataset A).

---

## 2. Telemetry and Weather Sensor Limitations

1. **UNISOLAR Missing-Value Representation (Unresolved Limitation):**
   - UNISOLAR generation telemetry contains substantial `NaN` values ($56.23\%$ of 15-minute intervals in raw data).
   - Missingness is heavily concentrated during nighttime hours.
   - Telemetry readings below approximately $0.100$ to $0.125\text{ kWh}$ are also recorded as `NaN`.
   - Crucially, the available repository evidence **cannot definitively distinguish all sub-threshold production from telemetry dropout or communication missingness**.
   - Consequently, `NaN` values **must not automatically be replaced with zero**. This is recognized as an unresolved data-quality limitation.
   - The Phase 3 valid site-day filter addresses this by requiring $\ge 26/28$ core daylight intervals to be non-null before treating daytime missingness.
2. **Proxy Weather Stations:**
   - UNISOLAR weather data is collected from regional Bureau of Meteorology (BOM) automated weather stations rather than on-site pyranometers.
   - Off-site ambient temperature and humidity exhibit weaker correlation with generation ($r \approx 0.19$ to $0.35$) compared to direct solar irradiance.
3. **Absence of On-Site Pyranometer Irradiance in Primary Cohort:**
   - While the Kaggle benchmark provides on-site `IRRADIATION`, the primary UNISOLAR benchmark lacks measured solar flux. The models rely on analytical extraterrestrial radiation ($H_0$), daylight photoperiod, and temperature swing proxies.
4. **Discrete Pulse Quantization (Site 27):**
   - In Phase 2 Task 3, nighttime non-zero readings in Site 27 were identified as discrete $0.125\text{ kWh}$ pulse quantization from an older energy meter buffer dump, rather than physical nighttime PV generation.
5. **Site 16 TBD Capacity:**
   - Site 16 records documented $\text{kW}_p$ as $30.0$, but module count is fractional ($115.38$) and panel model is marked `TBD`. Retained in Full Cohort but excluded from specific module studies.
6. **Absence of Archived Day-Ahead Numerical Weather Predictions (NWP):**
   - The dataset provides realized historical BOM weather observations. Real-world day-ahead forecasting assumes access to an external weather forecast service (e.g. GFS / ECMWF / BOM day-ahead forecasts).
