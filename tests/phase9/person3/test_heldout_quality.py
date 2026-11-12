"""Held-out quality evidence. Acceptance criteria are the metrics Person 1 recorded in
final_model_metadata.json (rounded to the precision it reports) - no thresholds are invented here."""
import numpy as np
import pytest

def metrics(y, p):
    e = np.asarray(p) - y
    return {"mae": np.abs(e).mean(), "rmse": np.sqrt((e ** 2).mean()),
            "r2": 1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum(), "bias_pred_minus_actual": e.mean(),
            "mae_pct_mean": np.abs(e).mean() / y.mean() * 100}

def test_primary_metrics_reproduce_person1_report(heldout, primary_predictions, metadata):
    from tests.phase9.person3.conftest import TARGET
    m = metrics(heldout[TARGET].to_numpy(), primary_predictions)
    ref = metadata["peer_cohort_models"]["primary_model"]["test_metrics"]
    assert m["mae"] == pytest.approx(ref["mae"], abs=6e-4)
    assert m["rmse"] == pytest.approx(ref["rmse"], abs=6e-4)
    assert m["r2"] == pytest.approx(ref["r2"], abs=6e-4)
    assert m["mae_pct_mean"] == pytest.approx(ref["mae_pct_mean"], abs=6e-3)
    # Person 1 reports bias as actual - prediction (negative => over-prediction); ours is pred - actual.
    assert -m["bias_pred_minus_actual"] == pytest.approx(ref["bias"], abs=6e-4)

def test_primary_beats_persistence_baseline(heldout, primary_predictions):
    from tests.phase9.person3.conftest import TARGET
    y = heldout[TARGET].to_numpy()
    model, base = metrics(y, primary_predictions), metrics(y, heldout["lag1_daily_yield"].to_numpy())
    assert model["mae"] < base["mae"] and model["rmse"] < base["rmse"] and model["r2"] > base["r2"]

def test_persistence_baseline_matches_report_except_bias(heldout, metadata):
    """Persistence baseline incl. bias (F-2: bias was reported as 0.0528; corrected to 0.0236 in metadata)."""
    from tests.phase9.person3.conftest import TARGET
    y = heldout[TARGET].to_numpy()
    m = metrics(y, heldout["lag1_daily_yield"].to_numpy())
    ref = metadata["peer_cohort_models"]["reference_baseline"]["test_metrics"]
    assert (m["mae"], m["rmse"], m["r2"]) == pytest.approx((ref["mae"], ref["rmse"], ref["r2"]), abs=6e-4)
    assert -m["bias_pred_minus_actual"] == pytest.approx(ref["bias"], abs=6e-4)

def test_fallback_metrics_reproduce_person1_report(heldout, fallback, feature_names, metadata):
    from tests.phase9.person3.conftest import TARGET
    m = metrics(heldout[TARGET].to_numpy(), fallback.predict(heldout[feature_names]))
    ref = metadata["peer_cohort_models"]["fallback_model"]["test_metrics"]
    assert m["mae"] == pytest.approx(ref["mae"], abs=6e-4)
    assert m["rmse"] == pytest.approx(ref["rmse"], abs=6e-4)
    assert m["r2"] == pytest.approx(ref["r2"], abs=6e-4)
    assert -m["bias_pred_minus_actual"] == pytest.approx(ref["bias"], abs=6e-4)   # corrected in Phase 9 (see qa_corrections)

def test_predictions_finite_and_plausible(primary_predictions, heldout):
    from tests.phase9.person3.conftest import TARGET
    assert primary_predictions.shape == (1128,) and np.isfinite(primary_predictions).all()
    lo, hi = heldout[TARGET].min(), heldout[TARGET].max()
    assert primary_predictions.min() >= min(lo, 0) - 1.0 and primary_predictions.max() <= hi + 1.0

def test_residuals_have_no_gross_structure(heldout, primary_predictions):
    from tests.phase9.person3.conftest import TARGET
    r = heldout[TARGET].to_numpy() - primary_predictions
    assert abs(r.mean()) < 0.25 * r.std()
    assert abs(np.corrcoef(primary_predictions, r)[0, 1]) < 0.6   # descriptive sanity, not an acceptance gate

def test_lag_unavailable_rows_are_scored_and_reported(heldout, primary_predictions):
    """Rows with has_valid_lag1=0 are in-distribution inputs; quantify, do not hide, their error."""
    from tests.phase9.person3.conftest import TARGET
    mask = (heldout["has_valid_lag1"] == 0).to_numpy()
    assert mask.sum() == 58 and np.isfinite(primary_predictions[mask]).all()
