import numpy as np
import pytest
from monitoring import drift, performance

def test_psi_zero_for_identical_and_large_for_shifted():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 5000)
    assert drift.psi(a, rng.normal(0, 1, 5000)) < 0.05
    assert drift.psi(a, rng.normal(2, 1, 5000)) > 0.25

def test_small_or_constant_samples_report_insufficient_not_guess():
    assert drift.psi(np.arange(50), np.arange(50)) is None
    assert drift.psi(np.ones(500), np.ones(500)) is None
    assert drift.ks(np.arange(10), np.arange(10)) is None

def test_baseline_covers_all_29_features_without_raw_rows(baseline):
    assert len(baseline["features"]) == 29 and baseline["rows"] == 4383
    assert all(len(v["quantiles"]) == 101 for v in baseline["features"].values())

def test_resampled_training_data_shows_no_drift(baseline, peer):
    cur = peer["train"].sample(1000, random_state=1)
    rep = drift.feature_drift_report(baseline, cur)
    assert rep["status"] in ("OK", "WARN") and rep["max_psi"] < 0.25

def test_too_few_rows_is_insufficient(baseline, peer):
    assert drift.feature_drift_report(baseline, peer["test"].head(20))["status"] == "INSUFFICIENT_DATA"

def test_synthetic_shift_triggers_alert(baseline, peer):
    cur = peer["train"].sample(1000, random_state=2).copy()
    cur["lag1_temp_mean"] += 15
    rep = drift.feature_drift_report(baseline, cur)
    assert rep["status"] == "ALERT" and rep["features"]["lag1_temp_mean"]["level"] == "ALERT"
    assert rep["features"]["lag1_temp_mean"]["out_of_training_range_fraction"] > 0

def test_heldout_season_is_flagged_as_drifted(baseline, peer):
    """Real, expected finding: training is May-Dec 2021 (Melbourne winter/spring), test is Mar-Apr 2022 (autumn);
    seasonal features (sin/cos, declination, daylight, H0) must register drift. This is covariate shift, not an accuracy verdict."""
    rep = drift.feature_drift_report(baseline, peer["test"])
    assert rep["status"] == "ALERT"
    assert rep["features"]["daylight_hours"]["level"] in ("WARN", "ALERT")

def test_prediction_drift_detects_shift():
    rng = np.random.default_rng(3)
    assert drift.prediction_drift(rng.normal(3, 1, 1000), rng.normal(3, 1, 1000))["level"] == "OK"
    assert drift.prediction_drift(rng.normal(3, 1, 1000), rng.normal(6, 1, 1000))["level"] == "ALERT"

def test_performance_needs_labels():
    assert performance.evaluate([], [], {"mae": 1, "rmse": 1})["status"] == "NO_LABELS"

def test_performance_ratio_against_person1_reference(metadata):
    ref = metadata["peer_cohort_models"]["primary_model"]["test_metrics"]
    r = performance.evaluate([3.0, 4.0], [2.0, 2.0], ref)
    assert r["mae"] == pytest.approx(1.5) and r["mae_ratio_to_reference"] == pytest.approx(1.5 / ref["mae"])
