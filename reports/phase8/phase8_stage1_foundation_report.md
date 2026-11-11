# SolarSelect MLOps EL — Phase 8, Stage 1: Foundation and Integration Layer Report

## 1. Executive Summary

Phase 8 Stage 1 establishes the integration foundation connecting the frozen Phase 6 real solar panel catalogue, the frozen Phase 7 roof-fit engine outputs, and the Phase 8 energy, economics, and recommendation workflow.

This stage strictly implements the contracts defined in the approved mathematical specification:
`reports/phase8/phase8_mathematical_specification_and_io_contract.md`.

No model inference, lag feature reconstruction, financial calculation, or ranking logic was implemented.

---

## 2. Components Implemented

The Stage 1 implementation resides in `src/energy_economics/` and consists of six core modules:

| Module | Responsibility | Key Classes / Functions |
|---|---|---|
| `src/energy_economics/types.py` | Authoritative enums, domain status codes, dataclasses, and Peer Cohort training distribution metrics. | `CapacitySupportStatus`, `CapacityEligibility`, `OverallRecommendationEligibility`, `GeometricFeasibility`, `CatalogueValidity`, `PredictionAvailability`, `ElectricalCompatibility`, `EconomicFeasibility`, `TrainingDistributionMetrics`, `CapacitySupportResult`, `FeasibilityResult` |
| `src/energy_economics/exceptions.py` | Typed domain exception hierarchy for Stage 1 operations. | `Phase8Error`, `Phase7IntegrationError`, `CatalogueIntegrationError`, `PanelNotFoundError`, `CapacityEvaluationError`, `FeasibilityEvaluationError` |
| `src/energy_economics/catalogue.py` | Read-only access to `configs/panels_catalogue.csv`, preserving missing values as `None`, with file integrity tracking and qualified provenance. | `ReadOnlyPanelCatalogue`, `PanelRecord` |
| `src/energy_economics/phase7_adapter.py` | Ingests and validates Phase 7 single or batch configurations; executes arithmetic cross-check ($|P_{\text{DC}} - \frac{N \cdot P_{\text{STC}}}{1000}| \le 10^{-6}\max(1, P_{\text{DC}})$). | `Phase7Adapter` |
| `src/energy_economics/capacity_evaluator.py` | Evaluates candidate installed DC capacity ($P_{\text{DC}}$) against the 22-site Peer Cohort distribution, returning marginal capacity support and eligibility. | `CapacitySupportEvaluator` |
| `src/energy_economics/feasibility.py` | Orchestrates multi-stage feasibility evaluation across geometric, catalogue, capacity, prediction, electrical, and economic domains. | `FeasibilityEvaluator` |
| `src/energy_economics/foundation.py` | Public orchestration engine assembling full candidate records and formatting JSON-compliant output according to §6. | `Phase8FoundationEngine` |
| `src/energy_economics/__init__.py` | Package initialization and clean public exports. | Public exports |

---

## 3. Public Interfaces Created

### 3.1 `Phase8FoundationEngine`
```python
engine = Phase8FoundationEngine(catalogue_path="configs/panels_catalogue.csv")

# Single configuration evaluation
result = engine.evaluate_configuration(phase7_result, run_id="RUN-OPTIONAL")

# Batch candidate evaluation
batch_result = engine.evaluate_batch([phase7_result_1, phase7_result_2])
```

### 3.2 `Phase7Adapter`
```python
# Validates and standardizes a Phase 7 result (dict or PanelConfigurationResult)
sanitized = Phase7Adapter.validate_and_ingest(phase7_result)

# Validates and ingests multiple candidates
batch = Phase7Adapter.ingest_batch([phase7_res_1, phase7_res_2])
```

### 3.3 `ReadOnlyPanelCatalogue`
```python
catalogue = ReadOnlyPanelCatalogue()
panel_record = catalogue.get_panel("PNL-TRINA-330W")
is_valid, errors = catalogue.validate_panel_record("PNL-TRINA-330W")
prov = catalogue.get_provenance("PNL-TRINA-330W")
integrity_ok = catalogue.verify_source_integrity()
```

### 3.4 `CapacitySupportEvaluator`
```python
evaluator = CapacitySupportEvaluator()
cap_result = evaluator.evaluate(installed_dc_capacity_kwp=38.61)
# Returns CapacitySupportResult(status, candidate_kwp, capacity_eligibility, training_distribution, warning)
```

---

## 4. Integration Approach & Clarifications

### 4.1 Phase 7 Roof-Fit Engine Integration
- **Public API Utilized:** `src.roof_fit.engine.RoofFitEngine.run_dict()` and `RoofFitEngine.fit()`.
- **Consumption Mode:** Pure consumer. The Phase 8 adapter does not rerun placement calculations, modify geometry, or alter coordinates.
- **Identity Preservation:** Preserves `configuration_id`, `roof_id`, `panel_id`, `panel_count`, `installed_dc_capacity_kwp`, `selected_orientation`, `spatial_metrics`, `placements`, and `constraint_violations`.
- **Validation:** Enforces non-blank IDs, non-negative panel counts, and mathematical capacity cross-check:
  $$|P_{\text{DC}} - \frac{\text{panel\_count} \times \text{module\_stc\_power\_wp}}{1000}| \le 10^{-6} \times \max(1, P_{\text{DC}})$$
  Rejects invalid outputs with `Phase7IntegrationError`.

### 4.2 Phase 6 Catalogue Integration & Provenance Qualification
- **Read-Only Approach:** `ReadOnlyPanelCatalogue` directly parses `configs/panels_catalogue.csv`.
- **Zero Modifications:** Source CSV is opened strictly in read mode (`"rb"` / `pd.read_csv`). File SHA-256 is tracked and verified before and after operations.
- **Preservation of Missing Data:** All 43 columns are preserved. Empty/NaN values (such as pricing columns) are stored strictly as `None`. Under no circumstances are missing values substituted with `0.0`.
- **Structural Validation:** Verifies existence of required columns (`panel_id`, `manufacturer`, `model`), absence of duplicate panel IDs, and positive physical dimensions/power.
- **Provenance Qualification:**
  - The as-recorded Phase 6 catalogue field `verification_status` is preserved exactly (`"VERIFIED_OFFICIAL_DATASHEET"`).
  - To prevent overclaiming, Phase 8 pairs this status with an explicit qualification:
    > "Technical specifications are extracted from local compiled reference PDF files under `data/reference/panel_datasheets/`, which represent compiled specification summaries, not independently authenticated original manufacturer datasheets. Original manufacturer source URLs were not independently verified during Phase 6."
  - This preserves Phase 6 documentation integrity while clarifying that extraction from a local PDF does not constitute original manufacturer publication verification.

### 4.3 Energy-Basis Clarification
- The AC/DC metering point remains unresolved under **Blocking Issue B-1**.
- The Stage 1 output explicitly records:
  ```json
  "energy_basis": "UNVERIFIED"
  ```
- No assumed AC or DC basis is adopted as an established project decision.
- Zero AC/DC conversion factors or loss adjustments are applied.
- Blocking Issue B-1 is tracked under `unresolved_inputs` and reflected in top-level recommendation caveats.

### 4.4 Model Input Placeholder Semantics
- In Stage 1, candidate energy objects include:
  ```json
  "model_input_kwp": 38.61,
  "model_input_kwp_status": "PENDING_INFERENCE_BINDING",
  "model_input_kwp_note": "Candidate DC capacity designated for Phase 5 'kWp' feature binding. Model inference is not executed in Stage 1 (PREDICTION_PENDING_LAG_POLICY)."
  ```
- This field explicitly represents the candidate capacity intended for the Phase 5 model's `kWp` feature binding, **not** a completed inference input or prediction.
- Prediction availability remains strictly `PREDICTION_PENDING_LAG_POLICY`. Zero models are loaded or executed.

---

## 5. Capacity Support Logic and Status Behavior

The marginal training-capacity support evaluation uses the authoritative 22-site Peer Cohort distribution:
- **Sample Size:** 22 unique installations ($[21.39, 539.80]\text{ kWp}$).
- **Summary Metrics:** Min: 21.39 kWp, $Q_1$: 39.99 kWp, Median: 53.96 kWp, Mean: 96.86 kWp ($s=124.59\text{ kWp}$, $\sigma \approx 121.72\text{ kWp}$), $Q_3$: 82.91 kWp, Max: 539.80 kWp.
- **Dense Core Band:** $[21.39, 100.00]\text{ kWp}$ (19 sites, 86.4%).
- **Sparse Region:** $(100.00, 539.80]\text{ kWp}$ (3 sites, 13.6%).

### Status Mapping & Impact on Overall Recommendation Eligibility
| Capacity Range ($P_{\text{DC}}$) | `capacity_support_status` | `capacity_eligibility` | Warning Tag | Impact on Overall Recommendation Eligibility |
|---|---|---|---|---|
| $21.39 \le P_{\text{DC}} \le 100.00\text{ kWp}$ | `SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION` | `CAPACITY_ELIGIBLE` | `None` | Necessary prerequisite satisfied. **Does NOT grant overall recommendation eligibility**; remaining gates evaluated separately. |
| $100.00 < P_{\text{DC}} \le 539.80\text{ kWp}$ | `SPARSE_TRAINING_SUPPORT` | `CAPACITY_FLAGGED_SPARSE` | `SPARSE_TRAINING_SUPPORT_WARNING` | Conditionally eligible with warning. When all other gates pass, sets `overall_recommendation_eligibility = "RECOMMENDATION_FLAGGED"`. |
| $P_{\text{DC}} < 21.39$ or $> 539.80\text{ kWp}$ | `OUT_OF_TRAINING_RANGE` | `CAPACITY_INELIGIBLE_OUT_OF_RANGE` | `CAPACITY_OUT_OF_DISTRIBUTION_WARNING` | Mandatory gate fails. Sets `overall_recommendation_eligibility = "RECOMMENDATION_INELIGIBLE"`. Excluded from primary rankings. |
| Distribution Metadata Missing | `CAPACITY_DISTRIBUTION_UNAVAILABLE` | `CAPACITY_INELIGIBLE_UNAVAILABLE` | `CAPACITY_DISTRIBUTION_METADATA_MISSING` | Mandatory gate fails. Sets `overall_recommendation_eligibility = "RECOMMENDATION_INELIGIBLE"`. |

---

## 6. Multi-Gate Feasibility Foundation

Stage 1 evaluates all feasibility gates without treating unevaluated checks as passes:
- **`geometric`:** `FEASIBLE` if Phase 7 `feasibility_status == "FEASIBLE"`, `panel_count >= 1`, and `constraint_violations == []`; else `INFEASIBLE`.
- **`catalogue`:** `VALID` if panel ID exists and physical dimensions/power are finite and > 0; else `INVALID`.
- **`capacity_support_status` / `capacity_eligibility`:** Evaluated from candidate $P_{\text{DC}}$.
- **`prediction_availability`:** Strictly `PREDICTION_PENDING_LAG_POLICY` (ML model inference deferred).
- **`electrical`:** Strictly `NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS` (string/inverter specifications deferred).
- **`economic`:** Strictly `NOT_EVALUATED_MISSING_COSTS` (financial calculator deferred).
- **`overall_recommendation_eligibility`:** Strictly `RECOMMENDATION_NOT_EVALUATED` (or `RECOMMENDATION_INELIGIBLE` if geometric, catalogue, or capacity gate fails).

---

## 7. Sample Phase 8 Output JSON (Stage 1 Foundation)

```json
{
  "run_id": "RUN-PHASE8-FOUNDATION-F80775BF",
  "schema_version": "phase8-io-0.1",
  "engine_status": "SUCCESS",
  "stage": "STAGE_1_FOUNDATION",
  "timestamp_utc": "2026-11-11T06:50:00.000000+00:00",
  "candidates": [
    {
      "configuration_id": "CFG-TEST-ROOF-COMMERCIAL-PNL-TRINA-330W-LANDSCAPE",
      "roof_id": "TEST-ROOF-COMMERCIAL",
      "panel_id": "PNL-TRINA-330W",
      "panel_model": "Tallmax TSM-PD14",
      "feasibility": {
        "geometric": "FEASIBLE",
        "catalogue": "VALID",
        "capacity_support_status": "SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION",
        "capacity_eligibility": "CAPACITY_ELIGIBLE",
        "prediction_availability": "PREDICTION_PENDING_LAG_POLICY",
        "electrical": "NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS",
        "electrical_checks": [],
        "economic": "NOT_EVALUATED_MISSING_COSTS",
        "first_failed_stage": null,
        "overall_recommendation_eligibility": "RECOMMENDATION_NOT_EVALUATED"
      },
      "energy": {
        "mode": "not_evaluated_stage1",
        "energy_basis": "UNVERIFIED",
        "installed_dc_capacity_kwp": 38.61,
        "model_input_kwp": 38.61,
        "model_input_kwp_status": "PENDING_INFERENCE_BINDING",
        "model_input_kwp_note": "Candidate DC capacity designated for Phase 5 'kWp' feature binding. Model inference is not executed in Stage 1 (PREDICTION_PENDING_LAG_POLICY).",
        "capacity_support": {
          "status": "SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION",
          "candidate_kwp": 38.61,
          "capacity_eligibility": "CAPACITY_ELIGIBLE",
          "training_distribution": {
            "n_sites": 22,
            "min_kwp": 21.39,
            "q1_kwp": 39.99,
            "median_kwp": 53.96,
            "mean_kwp": 96.86,
            "sample_std_kwp": 124.59,
            "pop_std_kwp": 121.72,
            "q3_kwp": 82.91,
            "max_kwp": 539.8,
            "core_band_kwp": [21.39, 100.0],
            "sparse_band_kwp": [100.0, 539.8]
          },
          "warning": null
        },
        "predicted_specific_yield_kwh_per_kwp_day": null,
        "coverage": null,
        "historical_year_status": null,
        "observed_period_energy_kwh": null,
        "e_year1_kwh": null,
        "lifetime_total_kwh": null,
        "degradation": null
      },
      "temperature_comparison": null,
      "costs": null,
      "financials": null,
      "ranking": {
        "pareto_status": "NOT_EVALUATED_STAGE1",
        "pareto_rank": null,
        "weighted_score": null,
        "weighted_status": "NOT_EVALUATED_STAGE1",
        "weighted_rank": null
      },
      "spatial_metrics": { ... },
      "catalogue_provenance": {
        "panel_id": "PNL-TRINA-330W",
        "specification_source": "data/reference/panel_datasheets/trina_solar/Datasheet_TSM_xxxPD14_TSM_EN_2017_Aus_C.pdf",
        "source_document_name": "Datasheet_TSM_xxxPD14_TSM_EN_2017_Aus_C.pdf",
        "verification_status": "VERIFIED_OFFICIAL_DATASHEET",
        "provenance_qualification": "Technical specifications are extracted from local compiled reference PDF files under data/reference/panel_datasheets/, which represent compiled specification summaries, not independently authenticated original manufacturer datasheets. Original manufacturer source URLs were not independently verified during Phase 6."
      }
    }
  ],
  "pareto_set": [],
  "weighted_ranking": {"weights": {}, "normalisation_bounds": {}, "order": []},
  "recommendation": {
    "configuration_id": null,
    "basis": "none",
    "overall_recommendation_eligibility": "RECOMMENDATION_NOT_EVALUATED",
    "explanation": "Phase 8 Stage 1 Foundation layer only. Energy prediction, financial calculator, and ranking algorithms are deferred to subsequent stages.",
    "caveats": [
      "Capacity support is strictly a marginal univariate assessment.",
      "Energy basis is UNVERIFIED; AC/DC metering point remains unconfirmed under Blocking Issue B-1. No AC/DC conversion applied.",
      "Model prediction pending approved prospective lag-yield policy (Blocking Issue B-2); no model inference executed in Stage 1.",
      "Phase 6 catalogue technical specs are compiled from local PDF summaries; original manufacturer source authenticity was not independently verified.",
      "No pricing or financial metrics evaluated."
    ]
  },
  "provenance": {
    "phase6_catalogue_path": "configs/panels_catalogue.csv",
    "phase6_catalogue_sha256": "439b1a5e1cf80ad6f595f4f5f59fa622432d667c26fa34d52bc8ee7ae3b956a9",
    "phase7_configurations_count": 1,
    "phase8_stage": "STAGE_1_FOUNDATION"
  },
  "warnings": [],
  "unresolved_inputs": [
    "B-1: AC/DC metering point confirmation (energy_basis remains UNVERIFIED; no AC/DC conversion applied)",
    "B-2: Prospective roof lag-yield policy (model prediction remains PREDICTION_PENDING_LAG_POLICY)",
    "D-2: Weather source for non-UNISOLAR sites",
    "D-3: Commercial panel prices and balance-of-system costs"
  ]
}
```

---

## 8. Automated Test Suite and Verification

The test suite in `tests/test_phase8_foundation.py` encompasses 19 unit and integration tests:

| Test ID | Test Name | Target Verified | Result |
|---|---|---|---|
| 1 | `test_valid_phase7_configuration_ingestion` | Validates Phase 7 dictionary ingestion and field standardization. | **PASS** |
| 2 | `test_multiple_configurations_batch_ingestion` | Ingests multi-candidate configuration batches simultaneously. | **PASS** |
| 3 | `test_missing_or_malformed_phase7_fields` | Rejects missing fields, negative counts, and arithmetic capacity mismatches. | **PASS** |
| 4 | `test_valid_catalogue_record` | Validates canonical catalogue access and physical dimension validation. | **PASS** |
| 5 | `test_unknown_panel_id` | Raises `PanelNotFoundError` and flags unknown panels as `INVALID`. | **PASS** |
| 6 | `test_missing_catalogue_fields_preserved_as_none` | Verifies missing pricing attributes remain `None` and are never 0.0. | **PASS** |
| 7 | `test_dense_capacity_support` | Verifies dense core [21.39, 100.00] kWp yields `SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION` & `CAPACITY_ELIGIBLE`. | **PASS** |
| 8 | `test_sparse_capacity_support` | Verifies sparse region (100.00, 539.80] kWp yields `SPARSE_TRAINING_SUPPORT` & warning. | **PASS** |
| 9 | `test_below_range_capacity` | Verifies sub-minimum (< 21.39 kWp) yields `OUT_OF_TRAINING_RANGE` & `CAPACITY_INELIGIBLE_OUT_OF_RANGE`. | **PASS** |
| 10 | `test_above_range_capacity` | Verifies super-maximum (> 539.80 kWp) yields `OUT_OF_TRAINING_RANGE`. | **PASS** |
| 11 | `test_missing_capacity_distribution_metadata` | Verifies fallback when training distribution metadata is unavailable. | **PASS** |
| 12 | `test_preservation_of_phase7_ids` | Verifies `configuration_id`, `roof_id`, and `panel_id` pass through unmodified. | **PASS** |
| 13 | `test_missing_electrical_specifications_remain_unevaluated` | Verifies electrical compatibility remains `NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS`. | **PASS** |
| 14 | `test_prediction_remains_pending` | Verifies prediction availability remains `PREDICTION_PENDING_LAG_POLICY`. | **PASS** |
| 15 | `test_overall_recommendation_eligibility_remains_not_evaluated` | Passing marginal capacity support does NOT grant overall recommendation eligibility. | **PASS** |
| 16 | `test_source_catalogue_remains_unchanged` | Verifies source CSV SHA-256 checksum is unchanged before and after all operations. | **PASS** |
| 17 | `test_catalogue_provenance_qualification_and_authenticity_limits` | Verifies provenance qualification distinguishing local PDF extraction from manufacturer authentication. | **PASS** |
| 18 | `test_energy_basis_remains_unverified_and_b1_unresolved` | Verifies energy_basis is UNVERIFIED, B-1 is unresolved, and no conversion is applied. | **PASS** |
| 19 | `test_model_input_kwp_placeholder_semantics` | Verifies model_input_kwp is a feature placeholder without model inference execution. | **PASS** |

### Test Execution Results
- `pytest -v tests/test_phase8_foundation.py`: **19 passed in 0.66s**.
- `pytest -q tests/`: **145 passed in 0.92s** (126 existing tests + 19 Phase 8 tests, zero regressions).

---

## 9. Explicitly Deferred Functionality (Remaining Phase 8 Work)

The following capabilities belong to subsequent Phase 8 stages and were **explicitly excluded** from Stage 1:
1. **Machine Learning Model Inference:** Loading Phase 5 scikit-learn ExtraTrees/ElasticNet estimators.
2. **Lag-Yield Feature Reconstruction:** Resolving Blocking Issue B-2 for prospective unbuilt roofs.
3. **Historical Replay & Weather Scenarios:** Chronological 29-feature alignment, coverage adjustment, and synthetic scenarios.
4. **Thermal Loss Adjustments:** Temperature comparison Method A and experimental Method B.
5. **Annualization & Lifetime Yield:** Year-1 annualization and 25-year lifetime compounding/linear degradation.
6. **Financial Calculator:** Gross vs. net CAPEX, OPEX schedules, NPV, LCOE, simple and discounted payback.
7. **Ranking & Optimization:** Multi-objective Pareto frontier identification and weighted scoring.
8. **Recommendation Synthesis:** Final automated recommendation selection with explanatory narrative.

---

## 10. Limitations and Dependencies for Stage 2

1. **Unresolved Lag-Feature Policy (B-2):** Phase 5 model inputs include lag solar yields (`lag1_mean`, `lag2_mean`, etc.), which do not exist for unbuilt roofs. Model inference cannot be generalized until policy B-2 is approved.
2. **Weather Data Ingestion (D-2):** There is currently no live or synthetic weather provider in the repository. Non-UNISOLAR locations require a weather data integration contract.
3. **Inverter and Balance-of-System Data (D-3 / D-9):** Electrical compatibility checks cannot proceed to `COMPATIBLE` until string layout, inverter models, and design standards are supplied.
