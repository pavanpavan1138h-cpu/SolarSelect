# Catalogue Schema — SolarSelect

This document details the canonical 43-column schema established for the commercial solar panel catalogue in **SolarSelect Layer B**, formally defined in [`configs/panels_catalogue_schema.json`](../../configs/panels_catalogue_schema.json).

---

## 1. Schema Design Principles

1. **Physical Engineering Defensibility:** Captures all parameters required for 2D roof packing, temperature-adjusted yield calculations, and inverter string matching.
2. **Standardized Units:** All physical, electrical, and thermal parameters enforce explicit SI/engineering units.
3. **Traceable Provenance:** Every row requires explicit attribution to an authoritative source document, URL, and verification level.
4. **Explicit Nulls:** Unavailable specifications must remain null (`NaN`); guessing or assuming values is strictly prohibited.

---

## 2. Complete 43-Column Specification Table

| Group | Field Name | Data Type | Physical Unit | Required / Nullable | Constraints & Permitted Values |
|---|---|---|---|---|---|
| **A: Product ID** | `panel_id` | string | - | **Required** | Unique regex `^[A-Za-z0-9_-]+$` (e.g. `PNL-TRINA-330W`) |
| | `manufacturer` | string | - | **Required** | Official commercial name (e.g. `Trina Solar`) |
| | `model` | string | - | **Required** | Model series designation (e.g. `Tallmax TSM-PD14`) |
| | `cell_technology` | string | - | Nullable | Enum: `Monocrystalline PERC`, `N-type TOPCon`, `Heterojunction (HJT)`, `Polycrystalline`, `Thin-film CdTe`, `IBC (Interdigitated Back Contact)`, `Unknown / Pending Datasheet` |
| | `module_type` | string | - | Nullable | Enum: `Monofacial`, `Bifacial (Glass-Glass)`, `Bifacial (Transparent Backsheet)`, `Flexible / Lightweight`, `Unknown / Pending Datasheet` |
| **B: Power & Eff.** | `rated_power_wp` | float | Wp | Nullable | $P_{\text{STC}} \in [50.0, 1000.0]$ |
| | `module_efficiency_pct` | float | % | Nullable | Gross aperture efficiency $\eta \in [5.0, 30.0]$ |
| | `stc_irradiance_w_m2` | float | $\text{W}/\text{m}^2$ | Nullable | Reference standard: $1000.0$ |
| | `stc_cell_temperature_c`| float | °C | Nullable | Reference standard: $25.0$ |
| **C: Physical Specs**| `length_mm` | float | mm | Nullable | Outer frame length $\in [500.0, 3000.0]$ |
| | `width_mm` | float | mm | Nullable | Outer frame width $\in [500.0, 2000.0]$ |
| | `thickness_mm` | float | mm | Nullable | Profile depth $\in [15.0, 60.0]$ |
| | `area_m2` | float | $\text{m}^2$ | Nullable | Module gross area $\in [0.5, 4.5]$ |
| | `weight_kg` | float | kg | Nullable | Module mass with frame $\in [5.0, 50.0]$ |
| **D: Thermal Specs** | `pmax_temp_coefficient_pct_per_c` | float | $\% / ^\circ\text{C}$ | Nullable | $\gamma_{Pmp} \in [-0.60, -0.15]$ (Strictly negative) |
| | `voc_temp_coefficient_pct_per_c` | float | $\% / ^\circ\text{C}$ | Nullable | $\beta_{Voc} \in [-0.50, -0.15]$ (Strictly negative) |
| | `isc_temp_coefficient_pct_per_c` | float | $\% / ^\circ\text{C}$ | Nullable | $\alpha_{Isc} \in [0.01, 0.10]$ (Strictly positive) |
| | `noct_c` | float | °C | Nullable | NOCT rating $\in [35.0, 52.0]$ |
| | `nmot_c` | float | °C | Nullable | NMOT rating (IEC 61215) $\in [35.0, 52.0]$ |
| **E: Electrical Specs**| `voc_v` | float | V | Nullable | Open-circuit voltage $\in [20.0, 100.0]$ |
| | `isc_a` | float | A | Nullable | Short-circuit current $\in [2.0, 25.0]$ |
| | `vmp_v` | float | V | Nullable | Maximum power voltage $\in [15.0, 90.0]$ ($< V_{oc}$) |
| | `imp_a` | float | A | Nullable | Maximum power current $\in [2.0, 24.0]$ ($< I_{sc}$) |
| | `max_system_voltage_v` | float | V | Nullable | Allowed DC voltage: $600, 1000, 1500$ |
| | `max_series_fuse_rating_a`| float | A | Nullable | Protective fuse rating $\in [10.0, 40.0]$ |
| **F: Lifetime & Deg.**| `product_warranty_years` | float | years | Nullable | Materials warranty $\in [0, 40]$ |
| | `performance_warranty_years` | float | years | Nullable | Linear power warranty $\in [0, 40]$ |
| | `annual_degradation_pct` | float | $\%/\text{year}$ | Nullable | Linear degradation $d_{\text{annual}} \in [0.1, 1.5]$ |
| | `end_of_warranty_power_pct` | float | % | Nullable | Residual power output $\in [70.0, 95.0]$ |
| **G: Economics** | `price_per_module` | float | local currency | Nullable | Commercial unit purchase price ($\ge 0$) |
| | `price_per_wp` | float | local currency/Wp | Nullable | Normalized price per watt ($\ge 0$) |
| | `currency` | string | ISO 4217 | Nullable | Three-letter currency code (e.g. `USD`, `AUD`, `EUR`) |
| | `price_basis` | string | - | Nullable | Enum: `Manufacturer List Price (MSRP)`, `Wholesale / Commercial EPC Tier (MW-scale)`, `Distributor Wholesale (Pallet-scale)`, `Retail Listing`, `Historical Project Procurement`, `Unverified Estimate / Placeholder` |
| | `price_region` | string | - | Nullable | Market quotation geography (e.g. `Australia`, `Global`) |
| | `price_confidence` | string | - | Nullable | Enum: `High (Audited Invoice or Official Quote)`, `Medium (Published Distributor Catalog)`, `Low (Informal Web Listing or Index)`, `Unverified / Null` |
| | `price_observed_date` | string | `YYYY-MM-DD` | Nullable | Observation timestamp |
| **H: Provenance** | `specification_source` | string | - | Nullable | Source document or repository file path |
| | `specification_source_url` | string | URL | Nullable | Manufacturer official URL |
| | `source_document_name` | string | filename | Nullable | Official datasheet title |
| | `source_page` | string | text | Nullable | Page or section number |
| | `verification_status` | string | - | Nullable | Enum: `VERIFIED_OFFICIAL_DATASHEET`, `PROVISIONAL_PARTIAL_SPECIFICATION`, `UNVERIFIED_PENDING_EXTERNAL_DATASHEET`, `UNVERIFIED_HISTORICAL_CLAIM` |
| | `verification_date` | string | `YYYY-MM-DD` | Nullable | Verification date |
| | `notes` | string | text | Nullable | Technical commentary, mounting requirements |

