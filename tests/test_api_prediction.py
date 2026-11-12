from fastapi.testclient import TestClient
from app.backend.main import create_app
from tests.conftest import StubProvider

def test_negative_raw_prediction(api_client, historical_body):
    r = api_client.post("/api/v1/predict", json=historical_body)
    assert r.status_code == 200, r.text
    assert r.json()["predicted_specific_yield_kwh_per_kwp_day"] == -0.5
    assert r.json()["prediction_status"] == "NEGATIVE_PREDICTION_WARNING"
    assert r.json()["energy_basis"] == "UNVERIFIED_ASSUMED_AC"
    assert r.json()["request_id"] == r.headers["X-Request-ID"]

def test_pending_even_without_model(api_settings):
    def fail(_):
        raise RuntimeError()
    with TestClient(create_app(api_settings, provider_factory=fail)) as c:
        r = c.post("/api/v1/predict", json={"scenario": "prospective_roof", "roof_id": "NEW"})
        assert r.status_code == 409
        assert r.json()["error"]["code"] == "PREDICTION_PENDING_LAG_POLICY"
        assert r.json()["error"]["details"]["predicted_specific_yield_kwh_per_kwp_day"] is None

def test_default_is_primary(real_client, historical_body):
    r = real_client.post("/api/v1/predict", json=historical_body)
    assert r.status_code == 200, r.text
    assert r.json()["model"]["model_variant"] == "primary_extra_trees"
