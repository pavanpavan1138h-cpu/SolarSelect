"""
SolarSelect — Phase 8 Stage 2: Phase 5 Inference Interface & Historical Replay Tests
Comprehensive unit and integration test suite covering:
  1. Loading the correct Peer Cohort ExtraTrees artifact.
  2. Recording model SHA-256.
  3. Exact 29-feature validation.
  4. Feature ordering according to feature_names_in_.
  5. Missing feature rejection.
  6. Non-finite feature rejection (NaN, Inf).
  7. Target-column exclusion.
  8. No model fitting or retraining.
  9. Correct primary model prediction.
  10. Explicit authorized blend selection (50/50 ExtraTrees + ElasticNet).
  11. Historical site-capacity preservation.
  12. Correct in-sample classification.
  13. Correct out-of-sample classification for March 1–April 23, 2022.
  14. Duplicate site-date rows rejection.
  15. Missing feature rows handling.
  16. Negative prediction handling without clipping.
  17. Daily energy arithmetic.
  18. Energy basis remains UNVERIFIED.
  19. Partial-period handling without annual extrapolation.
  20. B-2 remains unresolved for prospective configurations.
  21. Stage 1 foundation behavior remains unchanged.
"""

import copy
import hashlib
from pathlib import Path
import pytest
import numpy as np
import pandas as pd

from src.energy_economics import (
    Phase5PeerCohortPredictor,
    UNISOLARHistoricalReplayEngine,
    Phase8FoundationEngine,
    ModelVariant,
    ReplaySampleClassification,
    HistoricalYearStatus,
    Phase5InferenceError,
    FeatureValidationError,
    HistoricalReplayError,
)
from src.roof_fit.engine import RoofFitEngine


@pytest.fixture
def predictor_et() -> Phase5PeerCohortPredictor:
    """Fixture providing primary ExtraTrees predictor."""
    return Phase5PeerCohortPredictor(model_variant=ModelVariant.PRIMARY_EXTRA_TREES)


@pytest.fixture
def predictor_blend() -> Phase5PeerCohortPredictor:
    """Fixture providing authorized 50/50 ExtraTrees + ElasticNet blend predictor."""
    return Phase5PeerCohortPredictor(model_variant=ModelVariant.FALLBACK_BLEND_50_50)


@pytest.fixture
def replay_engine(predictor_et) -> UNISOLARHistoricalReplayEngine:
    """Fixture providing UNISOLAR historical replay engine."""
    return UNISOLARHistoricalReplayEngine(predictor=predictor_et)


@pytest.fixture
def sample_feature_row() -> pd.DataFrame:
    """Fixture providing one valid prepared feature row from test partition."""
    df_test = pd.read_csv("data/processed/unisolar/peer_cohort/test.csv")
    return df_test.head(1).copy()


# ----------------------------------------------------------------------
# 1. Loading the correct Peer Cohort ExtraTrees artifact
# ----------------------------------------------------------------------
def test_loading_peer_cohort_extratrees_artifact(predictor_et):
    """Test 1: Loads the primary ExtraTrees artifact from models/phase5/final/peer_cohort/."""
    expected_path = Path("models/phase5/final/peer_cohort/final_extra_trees.joblib")
    assert predictor_et.primary_path == expected_path
    assert predictor_et.model_name == "Tuned ExtraTreesRegressor"
    assert predictor_et.cohort == "peer_cohort"


# ----------------------------------------------------------------------
# 2. Recording model SHA-256
# ----------------------------------------------------------------------
def test_recording_model_sha256(predictor_et):
    """Test 2: Verifies runtime SHA-256 computation matches file on disk."""
    prov = predictor_et.get_provenance()
    assert "primary_artifact_sha256" in prov
    sha256 = prov["primary_artifact_sha256"]
    assert len(sha256) == 64

    # Direct recomputation check
    hasher = hashlib.sha256()
    with open(predictor_et.primary_path, "rb") as f:
        hasher.update(f.read())
    assert sha256 == hasher.hexdigest()


# ----------------------------------------------------------------------
# 3. Exact 29-feature validation
# ----------------------------------------------------------------------
def test_exact_29_feature_validation(predictor_et):
    """Test 3: Verifies model feature count and exact feature names list."""
    assert len(predictor_et.feature_names) == 29
    assert predictor_et.feature_names[0] == "kWp"
    assert "lat" in predictor_et.feature_names
    assert "Lon" in predictor_et.feature_names
    assert "daylight_hours" in predictor_et.feature_names
    assert "lag1_daily_yield" in predictor_et.feature_names
    assert "lag1_rh_mean" in predictor_et.feature_names


# ----------------------------------------------------------------------
# 4. Feature ordering according to feature_names_in_
# ----------------------------------------------------------------------
def test_feature_ordering_enforced(predictor_et, sample_feature_row):
    """Test 4: Shuffles input columns and verifies output ordering matches feature_names_in_ exactly."""
    # Reverse column order
    reversed_cols = list(reversed(predictor_et.feature_names))
    shuffled_df = sample_feature_row[reversed_cols].copy()

    ordered = predictor_et.validate_features(shuffled_df)
    assert list(ordered.columns) == predictor_et.feature_names


# ----------------------------------------------------------------------
# 5. Missing feature rejection
# ----------------------------------------------------------------------
def test_missing_feature_rejection(predictor_et, sample_feature_row):
    """Test 5: Explicitly rejects feature input with missing required columns."""
    incomplete_df = sample_feature_row.drop(columns=["lag1_daily_yield"]).copy()
    with pytest.raises(FeatureValidationError, match="Missing required model features"):
        predictor_et.validate_features(incomplete_df)


# ----------------------------------------------------------------------
# 6. Non-finite feature rejection (NaN, Inf)
# ----------------------------------------------------------------------
def test_non_finite_feature_rejection(predictor_et, sample_feature_row):
    """Test 6: Rejects inputs containing NaN or Infinite values."""
    # NaN check
    nan_df = sample_feature_row.copy()
    nan_df.loc[0, "kWp"] = np.nan
    with pytest.raises(FeatureValidationError, match="contains non-numeric, missing, or NaN values"):
        predictor_et.validate_features(nan_df)

    # Inf check
    inf_df = sample_feature_row.copy()
    inf_df.loc[0, "daylight_hours"] = np.inf
    with pytest.raises(FeatureValidationError, match="contains infinite values"):
        predictor_et.validate_features(inf_df)


# ----------------------------------------------------------------------
# 7. Target-column exclusion
# ----------------------------------------------------------------------
def test_target_column_exclusion(predictor_et, sample_feature_row):
    """Test 7: Ensures target columns (target_daily_yield) are never included in model features."""
    assert "target_daily_yield" in sample_feature_row.columns
    validated_X = predictor_et.validate_features(sample_feature_row)

    assert "target_daily_yield" not in validated_X.columns
    assert len(validated_X.columns) == 29
    assert "target" not in validated_X.columns
    assert "SolarGeneration" not in validated_X.columns


# ----------------------------------------------------------------------
# 8. No model fitting or retraining
# ----------------------------------------------------------------------
def test_no_model_fitting_or_retraining(predictor_et):
    """Test 8: Confirms predictor is strictly read-only and lacks fitting methods."""
    assert not hasattr(predictor_et, "fit")
    assert not hasattr(predictor_et, "refit")
    assert not hasattr(predictor_et, "retrain")


# ----------------------------------------------------------------------
# 9. Correct primary model prediction
# ----------------------------------------------------------------------
def test_correct_primary_model_prediction(predictor_et):
    """Test 9: Verifies test partition predictions match reported Phase 5 evaluation MAE."""
    df_test = pd.read_csv("data/processed/unisolar/peer_cohort/test.csv")
    preds = predictor_et.predict(df_test)
    assert len(preds) == len(df_test)

    # Calculate MAE against actual target
    mae = float(np.mean(np.abs(preds - df_test["target_daily_yield"])))
    assert abs(mae - 0.9050) < 0.001


# ----------------------------------------------------------------------
# 10. Explicit authorized blend selection (50/50 ExtraTrees + ElasticNet)
# ----------------------------------------------------------------------
def test_explicit_authorized_blend_selection(predictor_blend, sample_feature_row):
    """Test 10: Verifies 50/50 blend ensemble execution and provenance recording."""
    prov = predictor_blend.get_provenance()
    assert prov["model_variant"] == "fallback_blend_50_50"
    assert "linear_artifact_sha256" in prov
    assert prov["blend_weights"] == {"extra_trees": 0.5, "elastic_net": 0.5}

    pred = predictor_blend.predict(sample_feature_row)
    assert len(pred) == 1
    assert isinstance(float(pred[0]), float)


# ----------------------------------------------------------------------
# 11. Historical site-capacity preservation
# ----------------------------------------------------------------------
def test_historical_site_capacity_preservation(replay_engine):
    """Test 11: Verifies historical site kWp is preserved and not replaced by external values."""
    res = replay_engine.replay(site_keys=[15], date_range=("2021-05-01", "2021-05-05"))
    for rec in res["predictions"]:
        assert rec["site_key"] == 15
        # Site 15 historical capacity in prepared dataset is 94.24 kWp
        assert rec["historical_installed_capacity_kwp"] == 94.24


# ----------------------------------------------------------------------
# 12. Correct in-sample classification
# ----------------------------------------------------------------------
def test_correct_in_sample_classification(replay_engine):
    """Test 12: Dates up to 2022-02-28 are labeled IN_SAMPLE."""
    res = replay_engine.replay(date_range=("2021-06-01", "2021-06-02"))
    for rec in res["predictions"]:
        assert rec["sample_classification"] == ReplaySampleClassification.IN_SAMPLE.value


# ----------------------------------------------------------------------
# 13. Correct out-of-sample classification for March 1–April 23, 2022
# ----------------------------------------------------------------------
def test_correct_out_of_sample_classification(replay_engine):
    """Test 13: Dates between 2022-03-01 and 2022-04-23 are labeled OUT_OF_SAMPLE."""
    res = replay_engine.replay(date_range=("2022-03-15", "2022-03-16"))
    for rec in res["predictions"]:
        assert rec["sample_classification"] == ReplaySampleClassification.OUT_OF_SAMPLE.value


# ----------------------------------------------------------------------
# 14. Duplicate site-date rows rejection
# ----------------------------------------------------------------------
def test_duplicate_site_date_rows_rejection(replay_engine, sample_feature_row):
    """Test 14: Rejects datasets with duplicate (SiteKey, Date) rows."""
    dup_df = pd.concat([sample_feature_row, sample_feature_row], ignore_index=True)
    with pytest.raises(HistoricalReplayError, match="Duplicate .* combinations detected"):
        replay_engine.replay(dataset=dup_df)


# ----------------------------------------------------------------------
# 15. Missing feature rows handling
# ----------------------------------------------------------------------
def test_missing_feature_rows_handling(replay_engine, sample_feature_row):
    """Test 15: Incomplete feature rows raise FeatureValidationError during replay."""
    bad_df = sample_feature_row.drop(columns=["daylight_hours"]).copy()
    with pytest.raises(FeatureValidationError, match="Missing required model features"):
        replay_engine.replay(dataset=bad_df)


# ----------------------------------------------------------------------
# 16. Negative prediction handling without clipping
# ----------------------------------------------------------------------
def test_negative_prediction_handling_without_clipping(replay_engine, sample_feature_row):
    """Test 16: Negative predictions preserve raw value, flag warning, and exclude from energy total."""
    # Mock predictor that returns negative yield
    class MockNegativePredictor:
        model_name = "Mock Negative Predictor"
        model_variant = ModelVariant.PRIMARY_EXTRA_TREES
        feature_names = list(sample_feature_row.drop(columns=["SiteKey", "Date", "split", "target_daily_yield"]).columns)
        def validate_features(self, df):
            return df[self.feature_names].copy()
        def predict(self, df):
            return np.array([-0.50])
        def get_provenance(self):
            return {"model_name": self.model_name, "model_variant": self.model_variant.value}

    mock_engine = UNISOLARHistoricalReplayEngine(predictor=MockNegativePredictor())
    res = mock_engine.replay(dataset=sample_feature_row)

    rec = res["predictions"][0]
    # Raw negative prediction is preserved, NOT clipped to 0
    assert rec["predicted_specific_yield_kwh_per_kwp_day"] == -0.50
    assert rec["prediction_status"] == "NEGATIVE_PREDICTION_WARNING"
    assert rec["estimated_daily_energy_kwh"] is None
    # Raw unclipped mathematical energy is preserved
    expected_unclipped_energy = round(-0.50 * float(sample_feature_row["kWp"].iloc[0]), 6)
    assert rec["raw_unclipped_daily_energy_kwh"] == expected_unclipped_energy

    # Excluded from positive energy totals
    assert res["replay_summary"]["observed_period_estimated_energy_kwh"] == 0.0
    assert res["replay_summary"]["negative_predictions_count"] == 1


# ----------------------------------------------------------------------
# 17. Daily energy arithmetic (E_daily = Y_hat * kWp)
# ----------------------------------------------------------------------
def test_daily_energy_arithmetic(replay_engine):
    """Test 17: Verifies exact arithmetic: E_daily = Y_hat * kWp."""
    res = replay_engine.replay(site_keys=[15], date_range=("2021-05-01", "2021-05-01"))
    rec = res["predictions"][0]
    y_hat = rec["predicted_specific_yield_kwh_per_kwp_day"]
    kwp = rec["historical_installed_capacity_kwp"]
    expected_e = round(y_hat * kwp, 6)
    assert rec["estimated_daily_energy_kwh"] == expected_e


# ----------------------------------------------------------------------
# 18. Energy basis remains UNVERIFIED
# ----------------------------------------------------------------------
def test_energy_basis_remains_unverified(replay_engine):
    """Test 18: Verifies energy_basis is UNVERIFIED in historical replay output."""
    res = replay_engine.replay(site_keys=[15], date_range=("2021-05-01", "2021-05-02"))
    assert res["replay_summary"]["energy_basis"] == "UNVERIFIED"
    assert any("B-1" in item for item in res["unresolved_inputs"])


# ----------------------------------------------------------------------
# 19. Partial-period handling without annual extrapolation
# ----------------------------------------------------------------------
def test_partial_period_handling_without_annual_extrapolation(replay_engine):
    """Test 19: Verifies historical replay is labeled PARTIAL_PERIOD_NOT_A_FULL_YEAR and not scaled by 365."""
    res = replay_engine.replay(site_keys=[15])
    summary = res["replay_summary"]
    assert summary["historical_year_status"] == HistoricalYearStatus.PARTIAL_PERIOD_NOT_A_FULL_YEAR.value
    assert summary["annualization_extrapolation_applied"] is False
    # No annual financial metrics in output
    assert "lcoe" not in summary
    assert "payback" not in summary


# ----------------------------------------------------------------------
# 20. B-2 remains unresolved for prospective configurations
# ----------------------------------------------------------------------
def test_b2_remains_unresolved_for_prospective_configurations():
    """Test 20: Stage 1 prospective candidate continues to show PREDICTION_PENDING_LAG_POLICY."""
    roof_engine = RoofFitEngine()
    spec = {
        "roof_id": "TEST-ROOF-STAGE2-CHECK",
        "length": 20.0,
        "width": 15.0,
        "perimeter_setback": 0.5,
        "panel_id": "PNL-TRINA-330W",
    }
    p7_res = roof_engine.run_dict(spec)

    foundation_engine = Phase8FoundationEngine()
    p8_res = foundation_engine.evaluate_configuration(p7_res)
    cand = p8_res["candidates"][0]

    assert cand["feasibility"]["prediction_availability"] == "PREDICTION_PENDING_LAG_POLICY"
    assert cand["feasibility"]["overall_recommendation_eligibility"] == "RECOMMENDATION_NOT_EVALUATED"
    assert any("B-2" in item for item in p8_res["unresolved_inputs"])


# ----------------------------------------------------------------------
# 21. Stage 1 foundation behavior remains unchanged
# ----------------------------------------------------------------------
def test_stage1_foundation_behavior_unchanged():
    """Test 21: Confirms Stage 1 evaluation continues to function identically."""
    foundation_engine = Phase8FoundationEngine()
    cat = foundation_engine.catalogue
    assert cat.has_panel("PNL-TRINA-330W")
    assert cat.verify_source_integrity() is True
