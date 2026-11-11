"""
SolarSelect — Phase 8 Stage 1: Foundation and Integration Layer Test Suite
Comprehensive unit and integration tests verifying:
  1. Valid Phase 7 configuration ingestion.
  2. Multiple configurations (batch ingestion).
  3. Missing or malformed Phase 7 fields.
  4. Valid catalogue record.
  5. Unknown panel ID.
  6. Missing catalogue fields preserved as None.
  7. Dense capacity support (21.39–100.00 kWp).
  8. Sparse capacity support (100.00–539.80 kWp).
  9. Below-range capacity (< 21.39 kWp).
  10. Above-range capacity (> 539.80 kWp).
  11. Missing capacity-distribution metadata.
  12. Preservation of Phase 7 configuration IDs and panel IDs.
  13. Missing electrical specifications remain unevaluated.
  14. Prediction remains pending.
  15. Overall recommendation eligibility remains not evaluated.
  16. Source catalogue remains unchanged after loading and evaluation.
"""

import copy
import hashlib
from pathlib import Path
import pytest

from src.roof_fit.engine import RoofFitEngine
from src.energy_economics import (
    Phase8FoundationEngine,
    Phase7Adapter,
    ReadOnlyPanelCatalogue,
    CapacitySupportEvaluator,
    FeasibilityEvaluator,
    Phase7IntegrationError,
    PanelNotFoundError,
    CapacityEvaluationError,
    CapacitySupportStatus,
    CapacityEligibility,
    OverallRecommendationEligibility,
    GeometricFeasibility,
    CatalogueValidity,
    PredictionAvailability,
    ElectricalCompatibility,
    EconomicFeasibility,
)


@pytest.fixture
def catalogue() -> ReadOnlyPanelCatalogue:
    """Fixture providing read-only access to the canonical catalogue."""
    return ReadOnlyPanelCatalogue()


@pytest.fixture
def capacity_evaluator() -> CapacitySupportEvaluator:
    """Fixture providing capacity support evaluator with standard 22-site distribution."""
    return CapacitySupportEvaluator()


@pytest.fixture
def foundation_engine() -> Phase8FoundationEngine:
    """Fixture providing an instantiated Phase8FoundationEngine."""
    return Phase8FoundationEngine()


@pytest.fixture
def valid_phase7_result() -> dict:
    """Fixture providing a verified Phase 7 layout dictionary."""
    engine = RoofFitEngine()
    spec = {
        "roof_id": "TEST-ROOF-COMMERCIAL",
        "length": 20.0,
        "width": 15.0,
        "perimeter_setback": 0.5,
        "panel_id": "PNL-TRINA-330W",
    }
    res = engine.run_dict(spec)
    assert isinstance(res, dict)
    return res


# ----------------------------------------------------------------------
# 1. Valid Phase 7 Configuration Ingestion
# ----------------------------------------------------------------------
def test_valid_phase7_configuration_ingestion(valid_phase7_result):
    """Test 1: Ingests a valid Phase 7 configuration and verifies field standardization."""
    ingested = Phase7Adapter.validate_and_ingest(valid_phase7_result)
    assert ingested["configuration_id"] == valid_phase7_result["configuration_id"]
    assert ingested["roof_id"] == "TEST-ROOF-COMMERCIAL"
    assert ingested["panel_id"] == "PNL-TRINA-330W"
    assert ingested["panel_count"] == valid_phase7_result["panel_count"]
    assert ingested["installed_dc_capacity_kwp"] == valid_phase7_result["installed_dc_capacity_kwp"]
    assert ingested["module_stc_power_wp"] == 330.0
    assert ingested["feasibility_status"] == "FEASIBLE"


# ----------------------------------------------------------------------
# 2. Multiple Configurations (Batch Ingestion)
# ----------------------------------------------------------------------
def test_multiple_configurations_batch_ingestion(valid_phase7_result):
    """Test 2: Ingests multiple candidate configurations simultaneously."""
    cand1 = copy.deepcopy(valid_phase7_result)
    cand2 = copy.deepcopy(valid_phase7_result)
    cand2["configuration_id"] = "CFG-TEST-ROOF-ALT-02"

    batch = Phase7Adapter.ingest_batch([cand1, cand2])
    assert len(batch) == 2
    assert batch[0]["configuration_id"] == cand1["configuration_id"]
    assert batch[1]["configuration_id"] == "CFG-TEST-ROOF-ALT-02"


# ----------------------------------------------------------------------
# 3. Missing or Malformed Phase 7 Fields
# ----------------------------------------------------------------------
def test_missing_or_malformed_phase7_fields(valid_phase7_result):
    """Test 3: Rejects Phase 7 results with missing fields, negative counts, or capacity mismatch."""
    # Missing required field
    bad_res1 = copy.deepcopy(valid_phase7_result)
    del bad_res1["configuration_id"]
    with pytest.raises(Phase7IntegrationError, match="missing required fields"):
        Phase7Adapter.validate_and_ingest(bad_res1)

    # Empty configuration_id
    bad_res2 = copy.deepcopy(valid_phase7_result)
    bad_res2["configuration_id"] = "   "
    with pytest.raises(Phase7IntegrationError, match="cannot be blank"):
        Phase7Adapter.validate_and_ingest(bad_res2)

    # Negative panel_count
    bad_res3 = copy.deepcopy(valid_phase7_result)
    bad_res3["panel_count"] = -5
    with pytest.raises(Phase7IntegrationError, match="non-negative integer"):
        Phase7Adapter.validate_and_ingest(bad_res3)

    # Capacity arithmetic mismatch (|P_DC - N*P_STC/1000| > tol)
    bad_res4 = copy.deepcopy(valid_phase7_result)
    bad_res4["installed_dc_capacity_kwp"] = 999.0
    with pytest.raises(Phase7IntegrationError, match="Capacity arithmetic mismatch"):
        Phase7Adapter.validate_and_ingest(bad_res4)


# ----------------------------------------------------------------------
# 4. Valid Catalogue Record
# ----------------------------------------------------------------------
def test_valid_catalogue_record(catalogue):
    """Test 4: Verifies access to canonical catalogue and physical validation of valid panel."""
    assert catalogue.has_panel("PNL-TRINA-330W")
    record = catalogue.get_panel("PNL-TRINA-330W")
    assert record.panel_id == "PNL-TRINA-330W"
    assert record.manufacturer == "Trina Solar"
    assert record.rated_power_wp == 330.0
    assert record.length_mm == 1960.0
    assert record.width_mm == 992.0

    is_valid, errors = catalogue.validate_panel_record("PNL-TRINA-330W")
    assert is_valid is True
    assert len(errors) == 0


# ----------------------------------------------------------------------
# 5. Unknown Panel ID
# ----------------------------------------------------------------------
def test_unknown_panel_id(catalogue):
    """Test 5: Raises PanelNotFoundError and marks unknown panel as invalid."""
    with pytest.raises(PanelNotFoundError, match="not found in catalogue"):
        catalogue.get_panel("PNL-NONEXISTENT-999W")

    is_valid, errors = catalogue.validate_panel_record("PNL-NONEXISTENT-999W")
    assert is_valid is False
    assert any("does not exist in catalogue" in e for e in errors)


# ----------------------------------------------------------------------
# 6. Missing Catalogue Fields Preserved as None
# ----------------------------------------------------------------------
def test_missing_catalogue_fields_preserved_as_none(catalogue):
    """Test 6: Verifies that missing catalogue values remain None and are never replaced with 0.0."""
    record = catalogue.get_panel("PNL-TRINA-330W")
    # In Phase 6 catalogue, commercial pricing fields are unpopulated (None)
    assert record.price_per_module is None
    assert record.price_per_wp is None
    assert record.currency is None
    # Crucial assertion: None is not converted to 0.0
    assert record.price_per_module != 0.0


# ----------------------------------------------------------------------
# 7. Dense Capacity Support (21.39–100.00 kWp)
# ----------------------------------------------------------------------
def test_dense_capacity_support(capacity_evaluator):
    """Test 7: Verifies dense core capacity support status and capacity eligibility."""
    # Boundary lower
    res_min = capacity_evaluator.evaluate(21.39)
    assert res_min.status == CapacitySupportStatus.SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION
    assert res_min.capacity_eligibility == CapacityEligibility.CAPACITY_ELIGIBLE
    assert res_min.warning is None

    # Median point
    res_mid = capacity_evaluator.evaluate(53.96)
    assert res_mid.status == CapacitySupportStatus.SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION
    assert res_mid.capacity_eligibility == CapacityEligibility.CAPACITY_ELIGIBLE
    assert res_mid.warning is None

    # Boundary upper
    res_max = capacity_evaluator.evaluate(100.00)
    assert res_max.status == CapacitySupportStatus.SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION
    assert res_max.capacity_eligibility == CapacityEligibility.CAPACITY_ELIGIBLE
    assert res_max.warning is None


# ----------------------------------------------------------------------
# 8. Sparse Capacity Support (100.00–539.80 kWp)
# ----------------------------------------------------------------------
def test_sparse_capacity_support(capacity_evaluator):
    """Test 8: Verifies sparse support region classification and mandatory warning."""
    # Just above dense core
    res_low = capacity_evaluator.evaluate(100.01)
    assert res_low.status == CapacitySupportStatus.SPARSE_TRAINING_SUPPORT
    assert res_low.capacity_eligibility == CapacityEligibility.CAPACITY_FLAGGED_SPARSE
    assert res_low.warning == "SPARSE_TRAINING_SUPPORT_WARNING"

    # Middle of sparse region
    res_mid = capacity_evaluator.evaluate(250.00)
    assert res_mid.status == CapacitySupportStatus.SPARSE_TRAINING_SUPPORT
    assert res_mid.capacity_eligibility == CapacityEligibility.CAPACITY_FLAGGED_SPARSE
    assert res_mid.warning == "SPARSE_TRAINING_SUPPORT_WARNING"

    # Training maximum upper boundary
    res_top = capacity_evaluator.evaluate(539.80)
    assert res_top.status == CapacitySupportStatus.SPARSE_TRAINING_SUPPORT
    assert res_top.capacity_eligibility == CapacityEligibility.CAPACITY_FLAGGED_SPARSE
    assert res_top.warning == "SPARSE_TRAINING_SUPPORT_WARNING"


# ----------------------------------------------------------------------
# 9. Below-Range Capacity (< 21.39 kWp)
# ----------------------------------------------------------------------
def test_below_range_capacity(capacity_evaluator):
    """Test 9: Verifies sub-minimum out-of-range capacity classification."""
    # Residential 5.28 kWp layout
    res_res = capacity_evaluator.evaluate(5.28)
    assert res_res.status == CapacitySupportStatus.OUT_OF_TRAINING_RANGE
    assert res_res.capacity_eligibility == CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE
    assert res_res.warning == "CAPACITY_OUT_OF_DISTRIBUTION_WARNING"

    # Just below training minimum
    res_sub = capacity_evaluator.evaluate(21.38)
    assert res_sub.status == CapacitySupportStatus.OUT_OF_TRAINING_RANGE
    assert res_sub.capacity_eligibility == CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE


# ----------------------------------------------------------------------
# 10. Above-Range Capacity (> 539.80 kWp)
# ----------------------------------------------------------------------
def test_above_range_capacity(capacity_evaluator):
    """Test 10: Verifies super-maximum out-of-range capacity classification."""
    # Just above training maximum
    res_super = capacity_evaluator.evaluate(539.81)
    assert res_super.status == CapacitySupportStatus.OUT_OF_TRAINING_RANGE
    assert res_super.capacity_eligibility == CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE
    assert res_super.warning == "CAPACITY_OUT_OF_DISTRIBUTION_WARNING"

    # Utility scale
    res_util = capacity_evaluator.evaluate(1500.00)
    assert res_util.status == CapacitySupportStatus.OUT_OF_TRAINING_RANGE
    assert res_util.capacity_eligibility == CapacityEligibility.CAPACITY_INELIGIBLE_OUT_OF_RANGE


# ----------------------------------------------------------------------
# 11. Missing Capacity-Distribution Metadata
# ----------------------------------------------------------------------
def test_missing_capacity_distribution_metadata():
    """Test 11: Verifies fallback when training distribution metadata is unavailable."""
    evaluator_no_dist = CapacitySupportEvaluator(distribution=None)
    res = evaluator_no_dist.evaluate(50.0)
    assert res.status == CapacitySupportStatus.CAPACITY_DISTRIBUTION_UNAVAILABLE
    assert res.capacity_eligibility == CapacityEligibility.CAPACITY_INELIGIBLE_UNAVAILABLE
    assert res.warning == "CAPACITY_DISTRIBUTION_METADATA_MISSING"
    assert res.training_distribution is None


# ----------------------------------------------------------------------
# 12. Preservation of Phase 7 Configuration IDs and Panel IDs
# ----------------------------------------------------------------------
def test_preservation_of_phase7_ids(foundation_engine, valid_phase7_result):
    """Test 12: Verifies that Phase 7 configuration_id, roof_id, and panel_id pass through unchanged."""
    output = foundation_engine.evaluate_configuration(valid_phase7_result)
    cand = output["candidates"][0]

    assert cand["configuration_id"] == valid_phase7_result["configuration_id"]
    assert cand["roof_id"] == valid_phase7_result["roof_id"]
    assert cand["panel_id"] == valid_phase7_result["panel_id"]


# ----------------------------------------------------------------------
# 13. Missing Electrical Specifications Remain Unevaluated
# ----------------------------------------------------------------------
def test_missing_electrical_specifications_remain_unevaluated(foundation_engine, valid_phase7_result):
    """Test 13: Verifies electrical compatibility remains NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS."""
    output = foundation_engine.evaluate_configuration(valid_phase7_result)
    feasibility = output["candidates"][0]["feasibility"]

    assert feasibility["electrical"] == ElectricalCompatibility.NOT_EVALUATED_INSUFFICIENT_SPECIFICATIONS.value
    assert feasibility["electrical_checks"] == []


# ----------------------------------------------------------------------
# 14. Prediction Remains Pending
# ----------------------------------------------------------------------
def test_prediction_remains_pending(foundation_engine, valid_phase7_result):
    """Test 14: Verifies prediction availability remains PREDICTION_PENDING_LAG_POLICY."""
    output = foundation_engine.evaluate_configuration(valid_phase7_result)
    feasibility = output["candidates"][0]["feasibility"]

    assert feasibility["prediction_availability"] == PredictionAvailability.PREDICTION_PENDING_LAG_POLICY.value


# ----------------------------------------------------------------------
# 15. Overall Recommendation Eligibility Remains Not Evaluated
# ----------------------------------------------------------------------
def test_overall_recommendation_eligibility_remains_not_evaluated(foundation_engine, valid_phase7_result):
    """Test 15: Verifies candidate is NOT recommendation-eligible merely because capacity is supported."""
    output = foundation_engine.evaluate_configuration(valid_phase7_result)
    feasibility = output["candidates"][0]["feasibility"]

    # Candidate capacity (38.61 kWp) is CAPACITY_ELIGIBLE
    assert feasibility["capacity_support_status"] == CapacitySupportStatus.SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION.value
    assert feasibility["capacity_eligibility"] == CapacityEligibility.CAPACITY_ELIGIBLE.value

    # Crucial completion criterion: passing marginal capacity support NEVER grants overall recommendation eligibility!
    assert (
        feasibility["overall_recommendation_eligibility"]
        == OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED.value
    )
    assert (
        output["recommendation"]["overall_recommendation_eligibility"]
        == OverallRecommendationEligibility.RECOMMENDATION_NOT_EVALUATED.value
    )


# ----------------------------------------------------------------------
# 16. Source Catalogue Remains Unchanged After Loading and Evaluation
# ----------------------------------------------------------------------
def test_source_catalogue_remains_unchanged(catalogue, foundation_engine, valid_phase7_result):
    """Test 16: Verifies source catalogue CSV checksum is identical before and after all operations."""
    path = catalogue.catalogue_path
    hasher_before = hashlib.sha256()
    with open(path, "rb") as f:
        hasher_before.update(f.read())
    hash_before = hasher_before.hexdigest()

    # Perform repeated catalogue accesses and engine runs
    _ = catalogue.list_panel_ids()
    _ = catalogue.get_panel("PNL-TRINA-330W")
    _ = foundation_engine.evaluate_configuration(valid_phase7_result)

    hasher_after = hashlib.sha256()
    with open(path, "rb") as f:
        hasher_after.update(f.read())
    hash_after = hasher_after.hexdigest()

    assert hash_before == hash_after
    assert catalogue.verify_source_integrity() is True


# ----------------------------------------------------------------------
# 17. Catalogue Provenance Qualification & Authenticity Limits
# ----------------------------------------------------------------------
def test_catalogue_provenance_qualification_and_authenticity_limits(catalogue, foundation_engine, valid_phase7_result):
    """Test 17: Verifies provenance preservation and explicit local-PDF qualification without overclaiming."""
    prov = catalogue.get_provenance("PNL-TRINA-330W")
    # As-recorded Phase 6 status must be preserved exactly
    assert prov["verification_status"] == "VERIFIED_OFFICIAL_DATASHEET"
    assert "Datasheet_TSM_xxxPD14" in prov["source_document_name"]

    # Qualification must be present and distinguish local PDF extraction from manufacturer authentication
    assert "provenance_qualification" in prov
    qual = prov["provenance_qualification"]
    assert "compiled specification summaries" in qual
    assert "not independently authenticated original manufacturer datasheets" in qual

    # Verify candidate output contains the qualified provenance
    output = foundation_engine.evaluate_configuration(valid_phase7_result)
    cand_prov = output["candidates"][0]["catalogue_provenance"]
    assert cand_prov["verification_status"] == "VERIFIED_OFFICIAL_DATASHEET"
    assert "provenance_qualification" in cand_prov


# ----------------------------------------------------------------------
# 18. Energy Basis Remains Explicitly UNVERIFIED and B-1 Unresolved
# ----------------------------------------------------------------------
def test_energy_basis_remains_unverified_and_b1_unresolved(foundation_engine, valid_phase7_result):
    """Test 18: Verifies energy_basis is UNVERIFIED and B-1 remains explicitly tracked."""
    output = foundation_engine.evaluate_configuration(valid_phase7_result)
    energy_block = output["candidates"][0]["energy"]

    # Must be UNVERIFIED, not UNVERIFIED_ASSUMED_AC
    assert energy_block["energy_basis"] == "UNVERIFIED"

    # Blocking Issue B-1 must be listed in unresolved_inputs
    assert any("B-1" in item for item in output["unresolved_inputs"])
    b1_item = next(item for item in output["unresolved_inputs"] if "B-1" in item)
    assert "UNVERIFIED" in b1_item

    # Caveats must mention UNVERIFIED energy basis
    assert any("UNVERIFIED" in c for c in output["recommendation"]["caveats"])


# ----------------------------------------------------------------------
# 19. Model Input kWp Placeholder Semantics & Pending Prediction
# ----------------------------------------------------------------------
def test_model_input_kwp_placeholder_semantics(foundation_engine, valid_phase7_result):
    """Test 19: Verifies model_input_kwp is a feature placeholder without model execution."""
    output = foundation_engine.evaluate_configuration(valid_phase7_result)
    energy_block = output["candidates"][0]["energy"]

    assert energy_block["model_input_kwp"] == valid_phase7_result["installed_dc_capacity_kwp"]
    assert energy_block["model_input_kwp_status"] == "PENDING_INFERENCE_BINDING"
    assert "PREDICTION_PENDING_LAG_POLICY" in energy_block["model_input_kwp_note"]

    # Model inference must not have executed
    assert energy_block["predicted_specific_yield_kwh_per_kwp_day"] is None
    assert output["candidates"][0]["feasibility"]["prediction_availability"] == "PREDICTION_PENDING_LAG_POLICY"


