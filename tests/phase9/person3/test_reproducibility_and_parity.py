"""Determinism, single/batch consistency, fresh-process and API-vs-direct parity."""
import subprocess
import sys
import numpy as np
import pytest
from app.backend.core.config import REPOSITORY_ROOT
from src.energy_economics.types import ModelVariant

ATOL, RTOL = 1e-8, 0   # approved tolerance (person1_registry_handoff / Person 2 parity gate)

def test_repeated_inference_is_stable(primary, heldout, feature_names):
    """Finding F-1: n_jobs=-1 summation order makes repeats differ at ~1e-15, not bit-identical.
    Stability is therefore asserted at 1e-12, four orders below the approved 1e-8 parity gate."""
    x = heldout[feature_names].iloc[:50]
    runs = [np.asarray(primary.predict(x)) for _ in range(5)]
    for r in runs[1:]:
        np.testing.assert_allclose(r, runs[0], rtol=0, atol=1e-12)

def test_single_row_equals_batch(primary, heldout, feature_names):
    x = heldout[feature_names].iloc[:20]
    batch = np.asarray(primary.predict(x))
    single = np.concatenate([np.asarray(primary.predict(x.iloc[[i]])) for i in range(len(x))])
    np.testing.assert_allclose(single, batch, rtol=RTOL, atol=ATOL)

def test_row_order_does_not_change_predictions(primary, heldout, feature_names):
    x = heldout[feature_names].iloc[:30]
    base = np.asarray(primary.predict(x))
    rev = np.asarray(primary.predict(x.iloc[::-1]))[::-1]
    np.testing.assert_allclose(rev, base, rtol=RTOL, atol=ATOL)

def test_fresh_process_matches_loaded_model(primary, heldout, feature_names):
    code = ("import sys,json;sys.path.insert(0,'.');import pandas as pd;"
            "from src.energy_economics.inference import Phase5PeerCohortPredictor as P;"
            "n=json.load(open('models/phase5/final_model_metadata.json'))['feature_space']['predictive_feature_names'];"
            "d=pd.read_csv('data/processed/unisolar/peer_cohort/test.csv').head(25)[n];"
            "print(json.dumps([float(v) for v in P().predict(d)]))")
    out = subprocess.run([sys.executable, "-I", "-c", code], cwd=REPOSITORY_ROOT, capture_output=True, text=True, check=True).stdout
    import json
    fresh = np.array(json.loads(out.strip().splitlines()[-1]))
    np.testing.assert_allclose(fresh, np.asarray(primary.predict(heldout[feature_names].iloc[:25])), rtol=RTOL, atol=ATOL)

def test_api_single_matches_direct(real_client, primary, heldout, feature_names):
    for i in (0, 7, 300, 1127):
        row = heldout.loc[i, feature_names]
        body = {"scenario": "historical_site_day", "features": {k: (int(v) if k in ("day_of_year","month","day_of_week","is_weekend","has_valid_lag1") else float(v)) for k, v in row.items()}}
        r = real_client.post("/api/v1/predict", json=body)
        assert r.status_code == 200, r.text
        direct = float(np.asarray(primary.predict(heldout[feature_names].iloc[[i]]))[0])
        assert abs(r.json()["predicted_specific_yield_kwh_per_kwp_day"] - direct) <= ATOL

def test_api_batch_matches_direct_and_single(real_client, primary, heldout, feature_names):
    ints = ("day_of_year", "month", "day_of_week", "is_weekend", "has_valid_lag1")
    rows = [{"scenario": "historical_site_day", "features": {k: (int(v) if k in ints else float(v)) for k, v in heldout.loc[i, feature_names].items()}} for i in range(10)]
    r = real_client.post("/api/v1/predict/batch", json={"rows": rows})
    assert r.status_code == 200
    got = np.array([x["predicted_specific_yield_kwh_per_kwp_day"] for x in r.json()["results"]])
    np.testing.assert_allclose(got, np.asarray(primary.predict(heldout[feature_names].iloc[:10])), rtol=RTOL, atol=ATOL)

def test_api_fallback_variant_matches_direct(real_client, fallback, heldout, feature_names):
    ints = ("day_of_year", "month", "day_of_week", "is_weekend", "has_valid_lag1")
    feats = {k: (int(v) if k in ints else float(v)) for k, v in heldout.loc[3, feature_names].items()}
    r = real_client.post("/api/v1/predict", json={"scenario": "historical_site_day", "features": feats, "model_variant": "fallback_blend_50_50"})
    assert r.status_code == 200
    direct = float(np.asarray(fallback.predict(heldout[feature_names].iloc[[3]]))[0])
    assert abs(r.json()["predicted_specific_yield_kwh_per_kwp_day"] - direct) <= ATOL

def test_api_reports_model_identity_without_leaking_paths(real_client):
    info = real_client.get("/api/v1/model/info").json()
    assert info["units"] == "kWh/kWp/day" and info["feature_count"] == 29
    assert info["primary_artifact_fingerprint"] == "39b4a11beb5423dff"[:16]
    assert str(REPOSITORY_ROOT) not in str(info) and "\\" not in str(info)
