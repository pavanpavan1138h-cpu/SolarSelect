# Target Definition — SolarSelect

This document details the mathematical formulation, physical justification, and evaluation unit of the primary forecasting target in **SolarSelect Layer A**.

---

## 1. Primary Target Formulation

The primary machine learning target is **Daily Specific Energy Yield** ($Y_{f, \text{day}}$), defined as:

$$Y_{f, \text{day}} = \frac{\sum_{i=1}^{96} E_{15\text{m}, i}}{P_{\text{STC}}} \quad \left[\frac{\text{kWh}}{\text{kW}_p/\text{day}}\right]$$

Where:
- $E_{15\text{m}, i}$ is the active energy generated during the $i$-th 15-minute interval of the day ($\text{kWh}$).
- $\sum_{i=1}^{96} E_{15\text{m}, i}$ represents total daily AC energy delivered by the inverter system ($\text{kWh}$).
- $P_{\text{STC}}$ is the documented installed DC peak power rating of the photovoltaic array under Standard Test Conditions ($\text{kW}_p$).

---

## 2. Scientific & Operational Justification

1. **Capacity Normalization:**
   - Raw kilowatt-hour generation ($E_{\text{day}}$) scales linearly with system size. A model trained on raw kWh will predict higher values simply because a system is larger ($384\text{ kW}_p$ vs $21\text{ kW}_p$), failing to capture the intrinsic meteorological efficiency of the site.
   - Specific yield ($Y_f$) normalizes out physical size, allowing a single model to learn cross-sectional solar performance across diverse arrays.
2. **Direct Compatibility with Downstream Recommendation (Layer B):**
   - Layer B recommends real commercial panels for unbuilt or proposed installations.
   - For an arbitrary candidate module with rated power $P_{\text{panel}}$ and array count $N$, expected energy generation is computed directly by scaling forecasted $Y_f$:
     $$\hat{E}_{\text{candidate}} = \hat{Y}_f \cdot (N \cdot P_{\text{panel}} \cdot 10^{-3}) \cdot \eta_{\text{thermal}} \cdot \eta_{\text{degradation}}$$
3. **Physical Interpretation:**
   - Specific yield represents the number of equivalent **peak sun hours (PSH)** the array operated at nominal capacity that day.
   - In temperate Australia (Melbourne, $-37.7^\circ\text{ S}$), clean physical systems produce between $1.0\text{ kWh}/\text{kW}_p/\text{day}$ on overcast winter days and $6.0–6.8\text{ kWh}/\text{kW}_p/\text{day}$ on clear summer days.

---

## 3. Alternative Formulations Evaluated in Phase 2

In Phase 2 Task 5, five candidate targets were comparatively audited:

| Formulation | Mathematical Expression | Evaluation Verdict | Rejection / Adoption Reason |
|---|---|---|---|
| **Option 1: 15-Minute Power (kW)** | $P_{\text{AC}}(t + 15\text{m})$ | Secondary Only (Kaggle) | High stochastic noise; irrelevant for daily panel economic sizing. |
| **Option 2: Daily Gross Energy (kWh)** | $\sum E_{15\text{m}}$ | Rejected | Highly site-size dependent; prevents cross-site generalization. |
| **Option 3: Capacity Factor (24h CF)** | $\frac{\sum E_{15\text{m}}}{P_{\text{STC}} \times 24}$ | Equivalent | Constant scalar transformation of $Y_f$ ($\text{CF} = Y_f / 24$). |
| **Option 4: Performance Ratio (PR)** | $\frac{Y_f}{H_{\text{poa}} / G_{\text{STC}}}$ | Rejected | Requires continuous on-site plane-of-array pyranometer irradiance, which is absent in UNISOLAR. |
| **Option 5: Daily Specific Yield ($Y_f$)** | $\frac{\sum E_{15\text{m}}}{P_{\text{STC}}}$ | **SELECTED PRIMARY TARGET** | Physically normalized, robust, directly drives Layer B recommendation. |

