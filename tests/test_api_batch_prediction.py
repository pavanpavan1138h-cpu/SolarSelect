import copy

def test_batch_order(real_client, historical_rows):
    rows = [{"scenario": "historical_site_day", "features": r} for r in historical_rows[:5]]
    r = real_client.post("/api/v1/predict/batch", json={"rows": rows})
    assert r.status_code == 200, r.text
    for given, result in zip(rows, r.json()["results"]):
        single = real_client.post("/api/v1/predict", json=given).json()
        assert abs(result["predicted_specific_yield_kwh_per_kwp_day"] - single["predicted_specific_yield_kwh_per_kwp_day"]) <= 1e-8
        assert result["model"] == single["model"]

def test_batch_limits(api_client, historical_body):
    for rows in ([], [historical_body] * 101):
        assert api_client.post("/api/v1/predict/batch", json={"rows": rows}).status_code == 422

def test_all_or_nothing_with_index(api_client, historical_body):
    bad = copy.deepcopy(historical_body)
    del bad["features"]["lag1_daily_yield"]
    r = api_client.post("/api/v1/predict/batch", json={"rows": [historical_body, bad]})
    assert r.status_code == 422
    assert any(e["location"][:3] == ["body", "rows", 1] for e in r.json()["error"]["details"])
    assert "results" not in r.json()
