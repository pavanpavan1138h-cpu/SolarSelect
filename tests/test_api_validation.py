import copy
import json
import pytest

@pytest.mark.parametrize("name,value", [
    ("kWp", 0), ("kWp", -1), ("kWp", "94.24"), ("kWp", True),
    ("lat", 91), ("Lon", -181), ("month", 13), ("month", 1.5),
    ("day_of_week", 7), ("day_of_year", 367), ("day_of_year", 1),
    ("has_valid_lag1", 0.5), ("is_weekend", 1), ("lag1_daily_yield", None),
    ("lag1_temp_mean", [20]), ("lag1_temp_max", {"value": 20}),
])
def test_bad_numeric_features(api_client, historical_body, name, value):
    historical_body["features"][name] = value
    r = api_client.post("/api/v1/predict", json=historical_body)
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_inputs(api_client, historical_body, value):
    historical_body["features"]["lag1_daily_yield"] = value
    r = api_client.post("/api/v1/predict", content=json.dumps(historical_body), headers={"Content-Type": "application/json"})
    assert r.status_code == 422

@pytest.mark.parametrize("name", ["target_daily_yield", "SolarGeneration", "y", "unrecognized"])
def test_leakage_extra_fields(api_client, historical_body, name):
    historical_body["features"][name] = 1
    assert api_client.post("/api/v1/predict", json=historical_body).status_code == 422

def test_missing_and_malformed(api_client, historical_body):
    historical_body["features"].pop("lag7_daily_yield")
    assert api_client.post("/api/v1/predict", json=historical_body).status_code == 422
    for body in ([], {"features": []}, None, "abc"):
        assert api_client.post("/api/v1/predict", json=body).status_code == 422

def test_unknown_variant(api_client, historical_body):
    historical_body["model_variant"] = "full_cohort_elastic_net"
    assert api_client.post("/api/v1/predict", json=historical_body).status_code == 422

def test_request_extra(api_client, historical_body):
    historical_body["artifact_path"] = "untrusted.joblib"
    assert api_client.post("/api/v1/predict", json=historical_body).status_code == 422

def test_prospective_cannot_smuggle_features(api_client, historical_body):
    historical_body.update(scenario="prospective_roof", roof_id="NEW")
    assert api_client.post("/api/v1/predict", json=historical_body).status_code == 422

@pytest.mark.parametrize("field,value", [("SiteKey", 999999), ("site_id", "UNKNOWN"),
                                        ("Date", "2022-02-30"), ("timestamp", "not-a-timestamp")])
@pytest.mark.parametrize("location", ["request", "features"])
def test_unsupported_identity_and_timestamp_fields(api_client, historical_body, field, value, location):
    # This endpoint accepts prepared feature rows, not site/date lookup parameters.
    target = historical_body if location == "request" else historical_body["features"]
    target[field] = value
    r = api_client.post("/api/v1/predict", json=historical_body)
    assert r.status_code == 422
    assert any(e["type"] == "extra_forbidden" and e["location"][-1] == field
               for e in r.json()["error"]["details"])

@pytest.mark.parametrize("body", ['{"scenario":', '{"a":1,}', '{not-json}'])
def test_malformed_json_syntax(api_client, body):
    r = api_client.post("/api/v1/predict", content=body, headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert any(e["type"] == "json_invalid" for e in r.json()["error"]["details"])
