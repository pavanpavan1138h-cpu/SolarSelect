"""
SolarSelect — Phase 8, Stage 3: Energy Estimation Engine & Scenario Handling Tests
Validates the Stage 3 energy estimation layer:
- Daily energy arithmetic (E = Y_hat * kWp) and strict unit preservation.
- Capacity multiplication exactly once (no double scaling).
- Separation of raw mathematical output from accepted positive generation (Decision D-4).
- Historical replay preservation (chronology, in-sample vs out-of-sample).
- Scenario handling contracts (Historical Replay, Representative Period, Prospective Roof).
- Blocking Issue B-1 governance (energy_basis = UNVERIFIED).
- Blocking Issue B-2 prospective roof blocking (PREDICTION_PENDING_LAG_POLICY).
- Partial-period preservation without annual extrapolation.
- Backwards compatibility with Stage 1 and Stage 2.
"""

import math
import pytest
import numpy as np
import pandas as pd

from src.energy_economics.exceptions import (
    EnergyEstimationError,
    ScenarioValidationError,
    FeatureValidationError,
)
from src.energy_economics.types import (
    EnergyScenarioType,
    ScenarioEvaluationStatus,
    ReplaySampleClassification,
    HistoricalYearStatus,
    ModelVariant,
)
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.historical_replay import UNISOLARHistoricalReplayEngine
from src.energy_economics.energy_engine import Phase8EnergyEstimationEngine
from src.energy_economics.foundation import Phase8FoundationEngine


@pytest.fixture(scope="module")
def energy_engine():
    return Phase8EnergyEstimationEngine()


@pytest.fixture(scope="module")
def peer_features_df():
    return pd.read_csv("data/processed/unisolar/peer_cohort/features.csv")


@pytest.fixture(scope="module")
def sample_test_slice(peer_features_df):
    # Slice a small test set partition for fast deterministic evaluation
    return peer_features_df[
        (peer_features_df["Date"] >= "2022-03-01") & 
        (peer_features_df["Date"] <= "2022-03-03")
    ].copy()


# ==============================================================================
# 1. Energy Arithmetic & Unit Consistency
# ==============================================================================
def test_energy_arithmetic_precision_and_units(energy_engine, sample_test_slice):
    """Test 1: E_daily = predicted_specific_yield * historical_kWp with explicit units."""
    res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice,
    )
    assert res["scenario_status"] == ScenarioEvaluationStatus.COMPLETED.value
    estimates = res["daily_estimates"]
    assert len(estimates) > 0

    for est in estimates:
        y_hat = est["predicted_specific_yield_kwh_per_kwp_day"]
        kwp = est["historical_installed_capacity_kwp"]
        raw_e = est["raw_mathematical_daily_energy_kwh"]

        # Exact arithmetic check
        expected_e = round(round(y_hat, 6) * round(kwp, 4), 6)
        assert raw_e == expected_e

        # Unit verification
        assert est["specific_yield_unit"] == "kWh/kWp/day"
        assert est["daily_energy_unit"] == "kWh/day"


# ==============================================================================
# 2. Capacity Multiplication Exactly Once (No Double Scaling)
# ==============================================================================
def test_capacity_multiplied_exactly_once(energy_engine, sample_test_slice):
    """Test 2: Verifies capacity multiplication happens once; rejects double scaling."""
    # Obtain stage 2 replay output
    stage2_output = energy_engine.replay_engine.replay(dataset=sample_test_slice.iloc[:2])

    # Tamper with an existing unclipped energy to simulate double capacity multiplication
    tampered_output = dict(stage2_output)
    tampered_output["predictions"] = [dict(p) for p in stage2_output["predictions"]]
    # Artificially scale energy by capacity a second time
    tampered_output["predictions"][0]["raw_unclipped_daily_energy_kwh"] *= 2.0

    with pytest.raises(EnergyEstimationError, match="Capacity multiplication arithmetic mismatch"):
        energy_engine.estimate_energy(
            scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
            replay_output=tampered_output,
        )


# ==============================================================================
# 3. Rejection of Missing and Non-Finite Inputs
# ==============================================================================
def test_rejects_non_finite_yield_or_capacity(energy_engine, sample_test_slice):
    """Test 3: Rejects NaN or Inf in specific yield or capacity inputs."""
    stage2_output = energy_engine.replay_engine.replay(dataset=sample_test_slice.iloc[:2])

    # Case A: NaN yield
    nan_output = dict(stage2_output)
    nan_output["predictions"] = [dict(p) for p in stage2_output["predictions"]]
    nan_output["predictions"][0]["predicted_specific_yield_kwh_per_kwp_day"] = float("nan")

    with pytest.raises(EnergyEstimationError, match="Non-finite specific yield prediction"):
        energy_engine.estimate_energy(
            scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
            replay_output=nan_output,
        )

    # Case B: Inf capacity
    inf_output = dict(stage2_output)
    inf_output["predictions"] = [dict(p) for p in stage2_output["predictions"]]
    inf_output["predictions"][0]["historical_installed_capacity_kwp"] = float("inf")

    with pytest.raises(EnergyEstimationError, match="Invalid installed capacity"):
        energy_engine.estimate_energy(
            scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
            replay_output=inf_output,
        )


# ==============================================================================
# 4. Negative Prediction Handling & Separation of Raw vs Accepted Positive Energy
# ==============================================================================
def test_negative_predictions_unclipped_and_excluded_from_positive_totals(energy_engine, sample_test_slice):
    """Test 4: Raw negative yields preserved with warning and excluded from accepted positive totals."""
    # Mock a prediction row with negative yield
    mock_stage2 = {
        "stage": "STAGE_2_HISTORICAL_REPLAY",
        "replay_summary": {
            "cohort": "peer_cohort",
            "calendar_days": 1,
            "distinct_observation_dates": 1,
            "missing_calendar_dates": 0,
            "coverage_fraction": 1.0,
            "date_range": {"start": "2022-03-01", "end": "2022-03-01"},
        },
        "model_provenance": {"model_name": "Mock", "model_variant": "primary_extra_trees"},
        "predictions": [
            {
                "site_key": 15,
                "date": "2022-03-01",
                "historical_installed_capacity_kwp": 50.0,
                "sample_classification": "OUT_OF_SAMPLE",
                "predicted_specific_yield_kwh_per_kwp_day": -0.40,
                "raw_unclipped_daily_energy_kwh": -20.0,
                "estimated_daily_energy_kwh": None,
                "actual_target_daily_yield": 2.50,
                "prediction_status": "NEGATIVE_PREDICTION_WARNING",
            },
            {
                "site_key": 15,
                "date": "2022-03-02",
                "historical_installed_capacity_kwp": 50.0,
                "sample_classification": "OUT_OF_SAMPLE",
                "predicted_specific_yield_kwh_per_kwp_day": 3.0,
                "raw_unclipped_daily_energy_kwh": 150.0,
                "estimated_daily_energy_kwh": 150.0,
                "actual_target_daily_yield": 3.20,
                "prediction_status": "VALID",
            }
        ],
    }

    res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        replay_output=mock_stage2,
    )
    estimates = res["daily_estimates"]
    assert len(estimates) == 2

    # Negative day
    neg_est = estimates[0]
    assert neg_est["predicted_specific_yield_kwh_per_kwp_day"] == -0.40
    assert neg_est["raw_mathematical_daily_energy_kwh"] == -20.0
    assert neg_est["accepted_positive_daily_energy_kwh"] is None
    assert neg_est["prediction_status"] == "NEGATIVE_PREDICTION_WARNING"

    # Positive day
    pos_est = estimates[1]
    assert pos_est["predicted_specific_yield_kwh_per_kwp_day"] == 3.0
    assert pos_est["raw_mathematical_daily_energy_kwh"] == 150.0
    assert pos_est["accepted_positive_daily_energy_kwh"] == 150.0
    assert pos_est["prediction_status"] == "VALID"

    # Aggregates: raw total = 130.0 (-20 + 150); accepted positive total = 150.0
    agg = res["aggregation_summary"]
    assert agg["raw_mathematical_energy_kwh"] == 130.0
    assert agg["accepted_positive_energy_kwh"] == 150.0
    assert agg["negative_predictions_count"] == 1
    assert agg["valid_predictions_count"] == 1


# ==============================================================================
# 5. Distinction Between Ground Truth and Model Energy
# ==============================================================================
def test_distinction_between_observed_actual_and_model_energy(energy_engine, sample_test_slice):
    """Test 5: Distinguishes actual observed generation from model estimated energy."""
    res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice.iloc[:5],
    )
    for est in res["daily_estimates"]:
        assert "actual_target_daily_yield" in est
        assert "actual_daily_energy_kwh" in est
        assert "raw_mathematical_daily_energy_kwh" in est
        # Actual energy = actual_target * kWp
        if est["actual_target_daily_yield"] is not None:
            expected_actual = round(est["actual_target_daily_yield"] * est["historical_installed_capacity_kwp"], 6)
            assert est["actual_daily_energy_kwh"] == expected_actual


# ==============================================================================
# 6. In-Sample vs Out-of-Sample Separation and Disclosures
# ==============================================================================
def test_in_sample_and_out_of_sample_separation(energy_engine, peer_features_df):
    """Test 6: In-sample and OOS records are separated in aggregation with warnings."""
    # Slice spanning both pre-2022-03-01 (IN_SAMPLE) and post-2022-03-01 (OUT_OF_SAMPLE)
    mixed_slice = peer_features_df[
        (peer_features_df["Date"] >= "2022-02-27") & 
        (peer_features_df["Date"] <= "2022-03-02")
    ].copy()

    res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=mixed_slice,
    )
    agg = res["aggregation_summary"]
    assert agg["in_sample_records_count"] > 0
    assert agg["out_of_sample_records_count"] > 0
    assert agg["in_sample_accepted_positive_energy_kwh"] > 0.0
    assert agg["out_of_sample_accepted_positive_energy_kwh"] > 0.0

    # Disclosure warning check
    warnings_str = " ".join(res["warnings"])
    assert "In-sample predictions reflect historical model reconstruction" in warnings_str
    assert "does not claim unseen-site or unseen-geography generalization" in warnings_str


# ==============================================================================
# 7. Per-Site and Overall Aggregation Integrity
# ==============================================================================
def test_per_site_and_overall_aggregation_consistency(energy_engine, sample_test_slice):
    """Test 7: Site-level totals sum up exactly to overall aggregation totals."""
    res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice,
    )
    site_summaries = res["site_summaries"]
    agg = res["aggregation_summary"]

    sum_site_accepted = round(sum(s["accepted_positive_energy_kwh"] for s in site_summaries), 4)
    sum_site_raw = round(sum(s["raw_mathematical_energy_kwh"] for s in site_summaries), 4)

    assert abs(sum_site_accepted - agg["accepted_positive_energy_kwh"]) < 1e-3
    assert abs(sum_site_raw - agg["raw_mathematical_energy_kwh"]) < 1e-3


# ==============================================================================
# 8. Scenario Contract Validation: Scenario Types
# ==============================================================================
def test_scenario_type_validation_and_rejection(energy_engine):
    """Test 8: Rejects invalid scenario types."""
    with pytest.raises(ScenarioValidationError, match="Unsupported scenario_type"):
        energy_engine.estimate_energy(scenario_type="NON_EXISTENT_SCENARIO")


# ==============================================================================
# 9. Representative-Period Scenario: Complete Profile vs Unavailable Profile
# ==============================================================================
def test_representative_period_scenario_contract(energy_engine, peer_features_df):
    """Test 9: Representative-period returns UNAVAILABLE when profile missing, evaluates when present."""
    # Case A: Missing profile
    res_unavail = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD,
        representative_profile=None,
    )
    assert res_unavail["scenario_status"] == ScenarioEvaluationStatus.UNAVAILABLE_INPUT_PROFILE.value
    assert res_unavail["daily_estimates"] == []

    # Case B: Complete valid profile provided
    valid_slice = peer_features_df.iloc[:5].copy()
    res_avail = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.REPRESENTATIVE_PERIOD,
        representative_profile=valid_slice,
    )
    assert res_avail["scenario_status"] == ScenarioEvaluationStatus.COMPLETED.value
    assert len(res_avail["daily_estimates"]) == 5
    assert res_avail["aggregation_summary"]["coverage_fraction"] == 1.0


# ==============================================================================
# 10. Prospective Roof Scenario Blocked Under B-2
# ==============================================================================
def test_prospective_roof_scenario_blocked_under_b2(energy_engine):
    """Test 10: Prospective roof scenario strictly returns PREDICTION_PENDING_LAG_POLICY."""
    prospective_cfg = {
        "panel_id": "CS3W-400MS",
        "system_capacity_kwp": 50.0,
    }
    res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.PROSPECTIVE_ROOF,
        prospective_configuration=prospective_cfg,
    )
    assert res["scenario_status"] == ScenarioEvaluationStatus.BLOCKED_PENDING_LAG_POLICY.value
    assert res["daily_estimates"] == []
    cand = res["candidate_roof_evaluation"]
    assert cand["prediction_status"] == "PREDICTION_PENDING_LAG_POLICY"
    assert cand["estimated_annual_energy_kwh"] is None
    assert cand["overall_recommendation_status"] == "RECOMMENDATION_NOT_EVALUATED"

    # Warning regarding B-2
    warnings_str = " ".join(res["warnings"])
    assert "Blocking Issue B-2" in warnings_str
    assert "lag-yield features" in warnings_str


# ==============================================================================
# 11. Energy Basis Governance (B-1 Remains UNVERIFIED)
# ==============================================================================
def test_energy_basis_remains_unverified_across_all_scenarios(energy_engine, sample_test_slice):
    """Test 11: All energy outputs strictly enforce energy_basis = UNVERIFIED."""
    # Historical replay
    res_hist = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice.iloc[:2],
    )
    assert res_hist["energy_basis"] == "UNVERIFIED"
    assert res_hist["aggregation_summary"]["energy_basis"] == "UNVERIFIED"

    # Prospective
    res_prosp = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.PROSPECTIVE_ROOF,
    )
    assert res_prosp["energy_basis"] == "UNVERIFIED"


# ==============================================================================
# 12. No Annualization or Extrapolation
# ==============================================================================
def test_no_annualization_or_extrapolation_applied(energy_engine, sample_test_slice):
    """Test 12: Prevents 365-day multiplication or annual scaling on partial periods."""
    res = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice,
    )
    agg = res["aggregation_summary"]
    assert agg["historical_year_status"] == HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value
    assert agg["annualization_extrapolation_applied"] is False
    assert "annual" not in agg["energy_unit"].lower()


# ==============================================================================
# 13. Model Variant Support (Primary vs Authorized Blend)
# ==============================================================================
def test_model_variant_support_in_energy_engine(energy_engine, sample_test_slice):
    """Test 13: Engine correctly executes both primary ExtraTrees and 50/50 blend."""
    # Primary ExtraTrees
    res_et = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice.iloc[:2],
        model_variant=ModelVariant.PRIMARY_EXTRA_TREES,
    )
    assert res_et["model_provenance"]["model_variant"] == ModelVariant.PRIMARY_EXTRA_TREES.value

    # Fallback 50/50 Blend
    res_blend = energy_engine.estimate_energy(
        scenario_type=EnergyScenarioType.HISTORICAL_REPLAY,
        feature_dataset=sample_test_slice.iloc[:2],
        model_variant=ModelVariant.FALLBACK_BLEND_50_50,
    )
    assert res_blend["model_provenance"]["model_variant"] == ModelVariant.FALLBACK_BLEND_50_50.value
    assert "blend_weights" in res_blend["model_provenance"]


# ==============================================================================
# 14. Backwards Compatibility with Stage 1 Foundation
# ==============================================================================
def test_stage1_foundation_compatibility_preserved():
    """Test 14: Stage 1 foundation engine remains 100% operational and unchanged."""
    from src.roof_fit.engine import RoofFitEngine
    roof_engine = RoofFitEngine()
    spec = {
        "roof_id": "TEST-ROOF-COMMERCIAL",
        "length": 20.0,
        "width": 15.0,
        "perimeter_setback": 0.5,
        "panel_id": "PNL-TRINA-330W",
    }
    phase7_output = roof_engine.run_dict(spec)

    foundation = Phase8FoundationEngine()
    res = foundation.evaluate_configuration(phase7_output)
    assert res["engine_status"] == "SUCCESS"
    cand_feasibility = res["candidates"][0]["feasibility"]
    assert cand_feasibility["capacity_support_status"] == "SUPPORTED_WITHIN_OBSERVED_DISTRIBUTION"
    assert cand_feasibility["overall_recommendation_eligibility"] == "RECOMMENDATION_NOT_EVALUATED"
