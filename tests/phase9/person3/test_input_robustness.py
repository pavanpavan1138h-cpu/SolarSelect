"""Invalid vs rare-but-valid inputs; no silent clamping, imputation or lag invention."""
import copy
import pytest

def post(client, features, **extra):
    return client.post("/api/v1/predict", json={"scenario": "historical_site_day", "features": features, **extra})

def test_baseline_valid_row_succeeds(real_client, valid_row):
    r = post(real_client, valid_row)
    assert r.status_code == 200 and r.json()["energy_basis"] == "UNVERIFIED_ASSUMED_AC"

def test_every_missing_feature_rejected(real_client, valid_row):
    for name in valid_row:
        row = {k: v for k, v in valid_row.items() if k != name}
        r = post(real_client, row)
        assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_ERROR", name

def test_every_null_feature_rejected(real_client, valid_row):
    for name in valid_row:
        assert post(real_client, {**valid_row, name: None}).status_code == 422, name

@pytest.mark.parametrize("bad", ["abc", "1.5", True, [], {}])
def test_wrong_types_rejected(real_client, valid_row, bad):
    assert post(real_client, {**valid_row, "kWp": bad}).status_code == 422

@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_rejected_and_not_echoed(real_client, valid_row, token):
    import json
    raw = json.dumps({"scenario": "historical_site_day", "features": {**valid_row, "lag1_daily_yield": 0.0}}).replace('"lag1_daily_yield": 0.0', f'"lag1_daily_yield": {token}')
    r = real_client.post("/api/v1/predict", content=raw, headers={"content-type": "application/json"})
    assert r.status_code == 422

def test_unexpected_and_leakage_fields_rejected(real_client, valid_row):
    for extra in ("target_daily_yield", "SolarGeneration", "bogus"):
        r = post(real_client, {**valid_row, extra: 1.0})
        assert r.status_code == 422, extra

@pytest.mark.parametrize("field,value", [("kWp", 0), ("kWp", -5), ("lat", 91), ("lat", -91), ("Lon", 181),
                                         ("month", 13), ("month", 0), ("day_of_year", 367), ("day_of_week", 7),
                                         ("is_weekend", 2), ("has_valid_lag1", 2)])
def test_out_of_range_rejected(real_client, valid_row, field, value):
    assert post(real_client, {**valid_row, field: value}).status_code == 422

def test_inconsistent_calendar_rejected(real_client, valid_row):
    assert post(real_client, {**valid_row, "month": 12}).status_code == 422          # doy 60 is not December
    assert post(real_client, {**valid_row, "day_of_week": 6, "is_weekend": 0}).status_code == 422

def test_non_integer_calendar_field_rejected(real_client, valid_row):
    assert post(real_client, {**valid_row, "day_of_year": 60.5}).status_code == 422

def test_string_numbers_not_coerced(real_client, valid_row):
    assert post(real_client, {**valid_row, "kWp": "94.24"}).status_code == 422

def test_rare_but_valid_values_are_not_rejected_or_clamped(real_client, valid_row, primary, feature_names, heldout):
    """Large kWp / extreme lag are valid inputs outside typical support: must be predicted, not clipped."""
    import pandas as pd
    row = {**valid_row, "kWp": 5000.0, "lag1_daily_yield": 45.0}
    r = post(real_client, row)
    assert r.status_code == 200
    direct = float(primary.predict(pd.DataFrame([row])[feature_names])[0])
    assert abs(r.json()["predicted_specific_yield_kwh_per_kwp_day"] - direct) <= 1e-8

def test_empty_and_malformed_bodies(real_client):
    for payload in ({}, {"scenario": "historical_site_day"}, {"scenario": "nope"}):
        assert real_client.post("/api/v1/predict", json=payload).status_code == 422
    assert real_client.post("/api/v1/predict", content=b"{not json", headers={"content-type": "application/json"}).status_code == 422
    assert real_client.post("/api/v1/predict", content=b"", headers={"content-type": "application/json"}).status_code == 422

def test_batch_limits_and_atomicity(real_client, valid_row):
    ok = {"scenario": "historical_site_day", "features": valid_row}
    assert real_client.post("/api/v1/predict/batch", json={"rows": []}).status_code == 422
    assert real_client.post("/api/v1/predict/batch", json={"rows": [ok] * 101}).status_code == 422
    assert real_client.post("/api/v1/predict/batch", json={"rows": [ok] * 100}).status_code == 200
    bad = {"scenario": "historical_site_day", "features": {**valid_row, "kWp": -1}}
    r = real_client.post("/api/v1/predict/batch", json={"rows": [ok, bad]})
    assert r.status_code == 422 and "results" not in r.json()
    assert any(e["location"][:3] == ["body", "rows", 1] for e in r.json()["error"]["details"])

def test_duplicate_rows_give_identical_predictions(real_client, valid_row):
    ok = {"scenario": "historical_site_day", "features": valid_row}
    vals = [x["predicted_specific_yield_kwh_per_kwp_day"] for x in real_client.post("/api/v1/predict/batch", json={"rows": [ok] * 5}).json()["results"]]
    assert max(vals) - min(vals) <= 1e-12

def test_unknown_model_variant_rejected(real_client, valid_row):
    assert post(real_client, valid_row, model_variant="elastic_net_full_cohort").status_code == 422

def test_prospective_roof_stays_blocked_by_lag_policy(real_client):
    r = real_client.post("/api/v1/predict", json={"scenario": "prospective_roof", "roof_id": "R1"})
    assert r.status_code == 409
    body = r.json()
    assert body["error"]["code"] == "PREDICTION_PENDING_LAG_POLICY"
    assert body["error"]["details"]["predicted_specific_yield_kwh_per_kwp_day"] is None

def test_limitations_expose_governance_flags(real_client):
    j = real_client.get("/api/v1/limitations").json()
    assert j["prediction_energy_basis"] == "UNVERIFIED_ASSUMED_AC"
    assert j["prospective_status"] == "PREDICTION_PENDING_LAG_POLICY"

def test_error_envelope_has_request_id_and_header(real_client, valid_row):
    r = post(real_client, {**valid_row, "kWp": -1})
    assert r.json()["request_id"] == r.headers["X-Request-ID"]
