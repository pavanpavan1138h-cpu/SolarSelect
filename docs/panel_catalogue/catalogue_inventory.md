# Catalogue Inventory — SolarSelect

This document details the commercial solar panel catalogue in the repository, contrasting the historical discrepancy claims from Phase 6 Prompt 1 against the active, verified 12-module catalogue established in Phase 6 Prompt 2.

---

## 1. Discrepancy Resolution: Appendix B Claims vs. Current Codebase

| Category | Appendix B Documented Claims | Phase 6 Prompt 1 Baseline | Phase 6 Final Resolution (Current State) |
|---|---|---|---|
| **Catalogue File** | Presumed existing `configs/panels_catalogue.csv` | Missing; initial 3-row unverified template created | **Canonical 43-column catalogue populated and retained** |
| **Model Count** | 14 commercial panel models listed in narrative | 0 verified records (3 unverified placeholders) | **12 retained commercial PV modules** |
| **Manufacturers** | Waaree, Canadian Solar, First Solar, etc. | 0 mentions across codebase files | **7 global manufacturers** (Trina, SunPower, Canadian Solar, Jinko, REC, First Solar, Waaree, Maxeon, LONGi) |
| **Physical Dimensions** | Stated to be available for roof sizing | 0% available ($NaN$) | **100% populated & derived** ($L, W, T$, Area, Weight) in compiled reference summaries |
| **Thermal Ratings** | Stated to be available for temperature modeling | 0% available ($NaN$) | **100% populated** ($\gamma_{Pmp}, \beta_{Voc}, \alpha_{Isc}$, NOCT/NMOT) from manufacturer product lines |
| **Pricing Data** | Stated to be available for financial ranking | 0% available ($NaN$) | **Explicitly kept null ($NaN$)** per strict provenance policy to avoid speculative values |

---

## 2. Active Retained Catalogue Records (`configs/panels_catalogue.csv`)

The catalogue contains 12 retained commercial PV modules across 6 distinct technologies, evaluated via [`src/validate_panel_catalogue.py`](../../src/validate_panel_catalogue.py) (`PASS_AUTOMATED_WITH_CANDIDATE_CAMPUS_MAPPINGS`):

> *Evidence Distinction:* Technical values are retained in compiled reference summaries ([`data/reference/panel_datasheets/`](../../data/reference/panel_datasheets/)) and attributed to manufacturer documentation. The original manufacturer source documents were not independently accessible during the final audit. Consequently, primary-source re-verification of these entries remains a documented limitation (LIM-013). All local PDF files match `source_manifest.csv` via SHA-256 local integrity hashes (LIM-012).

| Panel ID | Manufacturer | Commercial Model | Technology | Format | $P_{\text{STC}}$ (Wp) | Efficiency (%) | Dimensions ($L \times W \times T$) | Mass (kg) | $V_{mp}$ (V) | $I_{mp}$ (A) |
|---|---|---|---|---|---:|---:|---|---:|---:|---:|
| `PNL-TRINA-330W` | Trina Solar | Trina 330W (TSM-330PD14) | Polycrystalline | Monofacial | 330.0 | 17.00 | $1960 \times 992 \times 40\text{ mm}$ | 22.5 | 37.40 | 8.83 |
| `PNL-TRINA-310W` | Trina Solar | Trina 310W (TSM-310DD05A.08) | Polycrystalline | Monofacial | 310.0 | 18.90 | $1650 \times 992 \times 35\text{ mm}$ | 18.6 | 33.10 | 9.37 |
| `PNL-SUNPOWER-435W` | SunPower | SPR-E20-435-COM | IBC | Monofacial | 435.0 | 20.10 | $2067 \times 1046 \times 46\text{ mm}$ | 25.4 | 72.90 | 5.97 |
| `PNL-CANADIAN-445W` | Canadian Solar | HiKu CS3W-445MS | Mono PERC | Monofacial | 445.0 | 20.10 | $2108 \times 1048 \times 35\text{ mm}$ | 24.8 | 40.90 | 10.89 |
| `PNL-CANADIAN-BIFI-575W` | Canadian Solar | TOPBiHiKu6 CS6W-575TB-AG | N-type TOPCon | Bifacial (Glass-Glass) | 575.0 | 22.30 | $2278 \times 1134 \times 30\text{ mm}$ | 32.3 | 42.90 | 13.41 |
| `PNL-JINKO-430W` | Jinko Solar | Tiger Neo JKM430N-54HL4-V | N-type TOPCon | Monofacial | 430.0 | 22.00 | $1722 \times 1134 \times 30\text{ mm}$ | 22.0 | 31.88 | 13.49 |
| `PNL-TRINA-VERTEX-440W` | Trina Solar | Vertex S+ TSM-440NEG9R.28 | N-type TOPCon | Bifacial (Glass-Glass) | 440.0 | 22.00 | $1762 \times 1134 \times 30\text{ mm}$ | 21.0 | 44.00 | 10.01 |
| `PNL-REC-ALPHA-420W` | REC Group | REC Alpha Pure-R (REC420AA) | Heterojunction (HJT) | Monofacial | 420.0 | 21.80 | $1730 \times 1118 \times 30\text{ mm}$ | 21.5 | 50.00 | 8.40 |
| `PNL-FIRSTSOLAR-460W` | First Solar | Series 6 Plus FS-6460 | Thin-film CdTe | Monofacial | 460.0 | 18.60 | $2009 \times 1232 \times 49\text{ mm}$ | 34.5 | 188.80 | 2.44 |
| `PNL-WAAREE-540W` | Waaree Energies | Bi-55-540 (Ahnay Series) | Mono PERC | Bifacial (Glass-Glass) | 540.0 | 20.98 | $2272 \times 1133 \times 35\text{ mm}$ | 32.5 | 41.75 | 12.95 |
| `PNL-MAXEON-400W` | Maxeon Solar | Maxeon 3 SPR-MAX3-400 | IBC | Monofacial | 400.0 | 22.60 | $1690 \times 1046 \times 40\text{ mm}$ | 19.0 | 65.80 | 6.08 |
| `PNL-LONGI-580W` | LONGi Solar | Hi-MO 7 LR5-72HGD-580M | N-type TOPCon | Bifacial (Glass-Glass) | 580.0 | 22.50 | $2278 \times 1134 \times 30\text{ mm}$ | 31.8 | 43.22 | 13.42 |

---

## 3. Technology Coverage Summary

The catalogue covers exactly 6 distinct commercial semiconductor technologies (Bifacial vs. Monofacial represents mechanical module construction format, not a separate semiconductor technology):

| PV Technology Class | Active Verified Count | Representative Models | Engineering Advantage |
|---|---:|---|---|
| **Polycrystalline** | 2 | Trina 330W, Trina 310W | Low capital cost, candidate match to UNISOLAR campus baseline |
| **Monocrystalline PERC** | 2 | Canadian Solar HiKu 445W, Waaree Bi-55 540W | High commercial maturity, widespread availability |
| **N-type TOPCon** | 4 | Jinko Tiger Neo 430W, Trina Vertex S+ 440W, Canadian CS6W 575W, LONGi 580W | High efficiency (22.0–22.5%), low temperature coefficient ($-0.28$ to $-0.29\%/^\circ\text{C}$), high bifaciality |
| **Heterojunction (HJT)** | 1 | REC Alpha Pure-R 420W | Industry-leading temperature resilience ($\gamma_{Pmp} = -0.24\%/^\circ\text{C}$), gapless cell layout |
| **IBC (Back Contact)** | 2 | SunPower SPR-E20-435-COM, Maxeon 3 400W | Zero front metal shading, highest reliability, 25–40 yr warranties |
| **Thin-Film CdTe** | 1 | First Solar Series 6 Plus FS-6460 | Superior diffuse-light performance, utility-scale high voltage ($188.8\text{ V}$) |

---

## 4. Provenance Artifacts

- **Source Manifest:** [`data/reference/panel_datasheets/source_manifest.csv`](../../data/reference/panel_datasheets/source_manifest.csv) (12 rows with SHA-256 integrity hashes, publication dates, and verification statuses).
- **Field-Level Provenance Table:** [`data/reference/panel_datasheets/field_provenance.csv`](../../data/reference/panel_datasheets/field_provenance.csv) (516 audit rows across 17 granular columns).
- **Local PDF Storage:** [`data/reference/panel_datasheets/`](../../data/reference/panel_datasheets/) containing official datasheets in manufacturer subdirectories (`trina_solar/`, `sunpower/`, `canadian_solar/`, `jinko_solar/`, `rec_group/`, `first_solar/`, `waaree/`, `maxeon/`, `longi/`).
- **Validation Engine:** [`src/validate_panel_catalogue.py`](../../src/validate_panel_catalogue.py) reporting automated engineering checks (`PASS`) and documentary verification (`TECHNICAL_SPECIFICATIONS_VERIFIED_WITH_CANDIDATE_CAMPUS_MAPPINGS`, confirming catalogue structure and consistency against retained compiled records, without implying independent primary-source authentication).
