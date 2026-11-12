import json
import logging
import pytest
from fastapi.testclient import TestClient
from app.backend.main import create_app
from app.backend.routes import optional_provider
from tests.conftest import StubProvider
from src.energy_economics.exceptions import FeatureValidationError, Phase5InferenceError

@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_outputs(api_settings, historical_body, value):
    with TestClient(create_app(api_settings, provider_factory=lambda _: StubProvider(value))) as c:
        r = c.post("/api/v1/predict", json=historical_body)
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "INVALID_MODEL_OUTPUT"

@pytest.mark.parametrize("exception,status,code", [
    (FeatureValidationError("secret"), 422, "INVALID_MODEL_INPUT"),
    (Phase5InferenceError("secret"), 503, "MODEL_UNAVAILABLE"),
    (RuntimeError("secret"), 500, "INTERNAL_ERROR")])
def test_mapped_errors(api_settings, historical_body, exception, status, code):
    class Broken(StubProvider):
        def predict(self, rows, variant):
            raise exception
    with TestClient(create_app(api_settings, provider_factory=lambda _: Broken()), raise_server_exceptions=False) as c:
        r = c.post("/api/v1/predict", json=historical_body)
        assert r.status_code == status
        assert r.json()["error"]["code"] == code
        assert "secret" not in r.text
        assert r.json()["request_id"] == r.headers["X-Request-ID"]

def test_dependency_override(api_settings, historical_body):
    app = create_app(api_settings, provider_factory=lambda _: StubProvider())
    app.dependency_overrides[optional_provider] = lambda: StubProvider(2.5)
    with TestClient(app) as c:
        assert c.post("/api/v1/predict", json=historical_body).json()["predicted_specific_yield_kwh_per_kwp_day"] == 2.5

def test_envelopes_and_logs(api_client, caplog, historical_body):
    caplog.set_level(logging.INFO, logger="solarselect.api")
    for path in ("/bad", "/api/v1/panels/INVALID"):
        r = api_client.get(path)
        assert set(r.json()) == {"error", "request_id"}
        assert set(r.json()["error"]) == {"code", "message", "details"}
    api_client.post("/api/v1/predict", json=historical_body)
    records = [json.loads(r.message) for r in caplog.records if r.name == "solarselect.api"]
    assert any(r.get("model_variant") == "primary_extra_trees" for r in records)
    assert all("features" not in r for r in records)
