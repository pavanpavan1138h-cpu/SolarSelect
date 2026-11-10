# Source Verification Policy — SolarSelect

This document details the strict governance protocol regarding external datasheet acquisition, commercial cataloguing, field-level provenance, and verification tiers for **SolarSelect Layer B**.

---

## 1. Governance Protocol on External Data Sources

In strict accordance with project data governance rules:
- **Authorized Acquisition Only:** No developer, agent, or script is permitted to download external datasets, scrape websites, or query commercial APIs without explicit stakeholder authorization.
- **Explicit Stakeholder Approval:** For Phase 6 Prompt 2, explicit stakeholder authorization was granted to acquire official manufacturer technical datasheets for commercial PV modules.
- **Zero Fabrication Policy:** Missing technical specifications must never be populated using guessed, assumed, or synthetic numbers. Unsupported parameters must remain explicitly null (`NaN`).
- **Commercial Pricing Governance:** Because manufacturer datasheets publish technical specifications rather than commercial transaction prices, pricing fields are maintained as null (`NaN`) until formal commercial invoices or audited distributor price schedules are approved.

---

## 2. Four-Tier Verification Classification

Every hardware record in `configs/panels_catalogue.csv` is assigned one of four verification tiers:

| Tier Level | Verification Status String | Operational Meaning & Criteria | Permitted Downstream Use |
|---|---|---|---|
| **Tier 1** | `VERIFIED_OFFICIAL_DATASHEET` | Every electrical, physical, and thermal parameter has been verified against an official manufacturer PDF datasheet. Document title, URL, local storage path, revision, and page numbers are recorded. | **Full Production:** Permitted for Layer B roof-fit, energy simulation, and recommendation. |
| **Tier 2** | `PROVISIONAL_PARTIAL_SPECIFICATION` | Core dimensions and rated power are verified, but secondary thermal or degradation coefficients rely on documented family datasheets. | **Conditional:** Permitted with user-facing uncertainty disclaimer. |
| **Tier 3** | `UNVERIFIED_PENDING_EXTERNAL_DATASHEET` | The product identity is extracted from existing repository installation metadata (e.g. UNISOLAR site details), but technical specifications have not yet been ingested. | **Diagnostic Only:** Banned from recommendation engine until upgraded to Tier 1. |
| **Tier 4** | `UNVERIFIED_HISTORICAL_CLAIM` | Products referenced in narrative project reports that lack corresponding codebase data. | **Reference Only:** Banned from recommendation engine. |

---

## 3. Provenance Architecture and Storage

All acquired technical datasheets follow a strict traceability structure:
1. **Datasheet Storage:** Dedicated directory [`data/reference/panel_datasheets/<manufacturer>/`](../../data/reference/panel_datasheets/) holding official PDF specifications.
2. **Source Manifest:** [`data/reference/panel_datasheets/source_manifest.csv`](../../data/reference/panel_datasheets/source_manifest.csv) mapping each module to its document title, authoritative URL, local path, document revision, publication date, and verification status.
3. **Field Provenance Table:** [`data/reference/panel_datasheets/field_provenance.csv`](../../data/reference/panel_datasheets/field_provenance.csv) containing row-by-row audit records for every parameter, documenting original units, normalized values, datasheet page numbers, table/section references, and derivation methods.
4. **Validation Engine:** [`src/validate_panel_catalogue.py`](../../src/validate_panel_catalogue.py) executing automated physical and electrical sanity checks (aperture efficiency coherence, electrical hierarchy $V_{mp} < V_{oc}$ and $I_{mp} < I_{sc}$, thermal coefficient signs, and uniqueness checks).
