# Phase 6 — Real Solar Panel Catalogue
## Master Technical Documentation & Catalogue Provenance Report

### 1. Phase Overview & Scope

Phase 6 of Project **SolarSelect** establishes the hardware database for **Layer B: Constraint-Aware Real Solar Panel Recommendation**.

- **Prompt 1 Objective:** Inventory existing catalogue records, establish a canonical 43-column schema across 8 engineering domains, implement automated physical and provenance validation, audit commercial technology and manufacturer coverage, and reconcile documented claims against active codebase reality.
- **Strict Data-Source Governance Compliance:**
  * No external manufacturer datasheets, commercial catalogues, or APIs were downloaded or scraped.
  * No specifications, model numbers, prices, or parameters were fabricated or populated via assumptions.
  * All unknown specifications in existing repository entries remain explicitly null (`NaN`).
  * Gaps requiring external datasheet acquisition are formally identified as pending approval.

---

### 2. Repository Catalogue Inventory & Traceability Audit

| Audit Item | Documented Claim / Appendix B Expectation | Verified Repository Reality | Traceability & Provenance Status |
|---|---|---|---|
| **Catalogue File (`configs/panels_catalogue.csv`)** | Presumed existing commercial catalogue | **ABSENT** prior to Phase 6 | File created as canonical baseline in Phase 6 |
| **Model Count** | 14 commercial models described in Appendix B | **0 records** in codebase | Documented narrative claim only; no data files existed |
| **Manufacturer Coverage** | Waaree, Canadian Solar, First Solar, Mission Solar | **0 records** in codebase | Absent in repository |
| **Raw Telemetry Metadata (`Solar_Site_Details.csv`)** | Unspecified | **3 module text references** across 25 sites: `Trina 330W` (16 sites), `Trina 310W` (7 sites), `SunpowerSPR-E20-435-COM` (1 site) | Raw installation metadata only; no engineering specifications |
| **Physical Dimensions ($L, W, T, \text{Area}, \text{Weight}$)** | Expected available | **0% available** | Absent in repository |
| **Thermal Coefficients ($\gamma_{Pmp}, \beta_{Voc}, \alpha_{Isc}, \text{NOCT}$)** | Expected available | **0% available** | Absent in repository |
| **Electrical Ratings ($V_{oc}, I_{sc}, V_{mp}, I_{mp}$)** | Expected available | **0% available** | Absent in repository |
| **Lifetime & Warranties ($d_{\text{annual}}, \text{Warranty}$)** | Expected available | **0% available** | Absent in repository |
| **Commercial Pricing ($/module, $/Wp, Currency, Basis)** | Expected available | **0% available** | Absent in repository |

---

### 3. Canonical Catalogue Schema (43 Fields)

The canonical schema is formally serialized in [`configs/panels_catalogue_schema.json`](file:///Users/apple/Documents/5th%20sem%20el/MLOps_EL/SolarSelect/configs/panels_catalogue_schema.json) and organized into 8 functional groups:

1. **A. Product Identification (5 columns):** `panel_id`, `manufacturer`, `model`, `cell_technology`, `module_type`.
2. **B. Rated Power and Efficiency (4 columns):** `rated_power_wp`, `module_efficiency_pct`, `stc_irradiance_w_m2`, `stc_cell_temperature_c`.
3. **C. Physical Specifications (5 columns):** `length_mm`, `width_mm`, `thickness_mm`, `area_m2`, `weight_kg`.
4. **D. Thermal Specifications (5 columns):** `pmax_temp_coefficient_pct_per_c`, `voc_temp_coefficient_pct_per_c`, `isc_temp_coefficient_pct_per_c`, `noct_c`, `nmot_c`.
5. **E. Electrical Specifications (6 columns):** `voc_v`, `isc_a`, `vmp_v`, `imp_a`, `max_system_voltage_v`, `max_series_fuse_rating_a`.
6. **F. Lifetime and Degradation (4 columns):** `product_warranty_years`, `performance_warranty_years`, `annual_degradation_pct`, `end_of_warranty_power_pct`.
7. **G. Economic Information (7 columns):** `price_per_module`, `price_per_wp`, `currency`, `price_basis`, `price_region`, `price_confidence`, `price_observed_date`.
8. **H. Provenance and Verification (7 columns):** `specification_source`, `specification_source_url`, `source_document_name`, `source_page`, `verification_status`, `verification_date`, `notes`.

---

### 4. Baseline Catalogue Ingestion & Missingness Profile

Ingesting the 3 module references from `data/raw/unisolar/Solar_Site_Details.csv` into [`configs/panels_catalogue.csv`](file:///Users/apple/Documents/5th%20sem%20el/MLOps_EL/SolarSelect/configs/panels_catalogue.csv) yields:

- **Total Records:** 3 (`PNL-TRINA-330W`, `PNL-TRINA-310W`, `PNL-SUNPOWER-435W`).
- **Group Completeness:**
  * Product Identification: $100.0\%$
  * Rated Power & Efficiency: $25.0\%$ (`rated_power_wp` present; efficiency/STC absent)
  * Physical Specifications: $0.0\%$
  * Thermal Specifications: $0.0\%$
  * Electrical Specifications: $0.0\%$
  * Lifetime & Degradation: $0.0\%$
  * Economic Information: $0.0\%$
  * Provenance & Verification: $42.9\%$ (`specification_source`, `verification_status`, `notes` present)
- **Overall Schema Completeness:** **$20.9\%$** across all 43 fields (34 fields are 100% null).

---

### 5. Automated Data-Quality & Engineering Validation

The validation engine [`src/validate_panel_catalogue.py`](file:///Users/apple/Documents/5th%20sem%20el/MLOps_EL/SolarSelect/src/validate_panel_catalogue.py) was executed on the active catalogue:

- **Schema Conformance:** **YES** (100% of 43 canonical columns present and correctly ordered).
- **Critical Errors:** **0** (no negative powers, no duplicate IDs, no invalid types).
- **Engineering Warnings:** **0** (no conflicting area or efficiency calculations).
- **Provenance Alerts:** **3** (all 3 records are flagged as unverified).
- **Unverified Records:** **3** (`verification_status = 'UNVERIFIED_PENDING_EXTERNAL_DATASHEET'`).
- **Overall Status:** **`PASS_WITH_UNVERIFIED_GAPS`**.
- Detailed report serialized to [`reports/phase6/catalogue_validation_report.json`](file:///Users/apple/Documents/5th%20sem%20el/MLOps_EL/SolarSelect/reports/phase6/catalogue_validation_report.json).

#### Diagnostic Consistency Checks Implemented:
1. **Diagnostic Efficiency Consistency:**
   $$\eta_{\text{calc}} = \frac{P_{\text{rated}}}{\text{Area} \times 1000} \times 100$$
   Automatically flags discrepancies $>0.5\%$ against manufacturer reported efficiency without overwriting.
2. **Thermal Sign and Unit Checks:**
   Validates $\gamma_{Pmp} < 0$, $\beta_{Voc} < 0$, $\alpha_{Isc} > 0$ with explicit units in $\% / ^\circ\text{C}$.
3. **Electrical Hierarchy Checks:**
   Validates $V_{mp} < V_{oc}$, $I_{mp} < I_{sc}$, and $P_{\text{calc}} = V_{mp} \times I_{mp} \approx P_{\text{rated}}$ within $5\%$.
4. **Economic Tier Standardization:**
   Requires explicit `currency`, `price_region`, and `price_basis` (distinguishing manufacturer list price, wholesale EPC, distributor tier, and unverified estimate).

---

### 6. Technology & Manufacturer Coverage Gap Analysis

| Photovoltaic Technology | Commercial Market Role | Appendix B Documented Claim | Verified In-Repo Records | Coverage Status |
|---|---|---:|---:|---|
| **Monocrystalline PERC** | Global rooftop/commercial standard | 4 models | 0 models | **ABSENT** |
| **N-type TOPCon** | Modern high-efficiency commercial benchmark | 4 models | 0 models | **ABSENT** |
| **Heterojunction (HJT)** | Temperature coefficient leader (hot climates) | 2 models | 0 models | **ABSENT** |
| **Polycrystalline** | Legacy low-cost utility/commercial | 1 model | 0 models | **ABSENT** |
| **Thin-film CdTe** | Utility diffuse-light standard (First Solar) | 1 model | 0 models | **ABSENT** |
| **IBC (Back Contact)** | Ultra-high aesthetics/efficiency (SunPower) | 1 model | 0 models | **ABSENT** |
| **Bifacial Glass-Glass** | Commercial albedo gain standard | 1 model | 0 models | **ABSENT** |

---

### 7. Deliverables & Artifact Inventory

```
SolarSelect/
├── configs/
│   ├── panels_catalogue_schema.json     # Canonical 43-column schema with physical constraints & enums
│   ├── panels_catalogue_template.csv   # Clean header-only template for future datasheet ingestion
│   └── panels_catalogue.csv            # Active catalogue file with 3 unverified raw records & 34 nulls
├── src/
│   └── validate_panel_catalogue.py     # Modular engineering, physical, and provenance validator
├── reports/phase6/
│   └── catalogue_validation_report.json# Structured JSON validation report
├── notebooks/phase6/
│   ├── README.md                       # This master document
│   ├── panel_catalogue_inventory_and_validation.ipynb # Master notebook (executed top-to-bottom, 0 errors)
│   └── figures/
│       ├── figure_p6_catalogue_inventory_and_missingness.png # 43-column missingness & group completeness
│       └── figure_p6_technology_and_manufacturer_gaps.png   # Technology & manufacturer gap analysis
└── log.txt                             # Appended Session 30
```

---

### 8. External Data Acquisition Request (Protocol for Prompt 2)

To enable physical roof-fitting, temperature-conditioned yield adjustment, and multi-criteria panel recommendation in subsequent phases without violating governance restrictions, we formally request authorization to acquire official manufacturer technical datasheets for:

1. **Campus Baseline Modules:**
   - **Trina Solar**: Tallmax / Honey Series datasheets for 310W and 330W modules.
   - **SunPower**: E20 / SPR series datasheet for SPR-E20-435-COM.
2. **Commercial Benchmark Cohort (10–14 models):**
   - **Monocrystalline PERC**: Canadian Solar HiKu, Waaree Bi-55 / Arka series, Longi Hi-MO 4.
   - **N-type TOPCon**: Jinko Tiger Neo, JA Solar DeepBlue 4.0 Pro, Trina Vertex S+.
   - **Heterojunction (HJT)**: REC Alpha Pure-R, Meyer Burger White / Black.
   - **Thin-Film CdTe**: First Solar Series 6 Plus / Series 7.
   - **Commercial Polycrystalline**: Canadian Solar SuperPower / MaxPower (historical reference).

