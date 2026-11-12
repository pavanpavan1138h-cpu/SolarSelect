"""API/model metrics: counted correctly, privacy-safe, and invisible to prediction semantics."""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.backend.main import create_app
from monitoring.metrics import REGISTRY
from monitoring.instrumentation import MonitoredProvider
from src.energy_economics.types import ModelVariant
from tests.conftest import StubProvider

def test_request_counts_and_latency_recorded(mon_client, valid_body):
    for _ in range(3):
        assert mon_client.post("/api/v1/predict", json=valid_body).status_code == 200
    assert REGISTRY.counter("solarselect_http_requests_total", route="/api/v1/predict", method="POST", status="2xx") == 3
    assert REGISTRY.histogram_count("solarselect_http_request_duration_ms", route="/api/v1/predict") == 3
    assert REGISTRY.counter("solarselect_inferences_total", variant="primary_extra_trees") == 3
    assert REGISTRY.percentile("solarselect_http_request_duration_ms", 0.95, route="/api/v1/predict") > 0

def test_4xx_and_error_codes_counted(mon_client, valid_body):
    bad = {**valid_body, "features": {**valid_body["features"], "kWp": -1}}
    assert mon_client.post("/api/v1/predict", json=bad).status_code == 422
    assert REGISTRY.counter_sum("solarselect_http_requests_total", status="4xx") == 1
    assert REGISTRY.counter("solarselect_input_rejections_total", code="VALIDATION_ERROR") == 1

def test_governance_rejection_counted(mon_client):
    assert mon_client.post("/api/v1/predict", json={"scenario": "prospective_roof", "roof_id": "R"}).status_code == 409
    assert REGISTRY.counter("solarselect_governance_rejections_total", code="PREDICTION_PENDING_LAG_POLICY") == 1

def test_model_identity_and_load_status_observable(mon_client):
    text = mon_client.get("/metrics").text
    assert "solarselect_model_loaded 1.0" in text and "solarselect_model_info" in text

def test_metrics_endpoint_is_hidden_from_openapi(mon_client):
    assert "/metrics" not in mon_client.get("/openapi.json").json()["paths"]

def test_prometheus_exposition_well_formed(mon_client, valid_body):
    mon_client.post("/api/v1/predict", json=valid_body)
    for line in mon_client.get("/metrics").text.strip().splitlines():
        name, value = line.rsplit(" ", 1)
        float(value)
        assert name.startswith("solarselect_")

def test_no_payload_values_paths_or_secrets_in_metrics(real_client, historical_body):
    real_client.post("/api/v1/predict", json=historical_body)
    text = real_client.get("/metrics").text
    assert "/Users/" not in text and "C:\\" not in text and "mlflow.db" not in text
    assert str(historical_body["features"]["lag1_daily_yield"]) not in text

def test_monitoring_does_not_change_predictions(real_client, real_provider, historical_body, historical_rows):
    import pandas as pd
    r = real_client.post("/api/v1/predict", json=historical_body).json()["predicted_specific_yield_kwh_per_kwp_day"]
    direct = float(real_provider.predict(pd.DataFrame([historical_rows[0]]), ModelVariant.PRIMARY_EXTRA_TREES)[0])
    assert abs(r - direct) <= 1e-8

def test_nonfinite_and_failure_counters():
    class Bad(StubProvider):
        def predict(self, rows, variant):
            if self.value == "boom":
                raise RuntimeError("x")
            return np.array([float("nan")])
    p = MonitoredProvider(Bad(value=0.0))
    p.predict(None, ModelVariant.PRIMARY_EXTRA_TREES)
    assert REGISTRY.counter("solarselect_nonfinite_predictions_total", variant="primary_extra_trees") == 1
    with pytest.raises(RuntimeError):
        MonitoredProvider(Bad(value="boom")).predict(None, ModelVariant.PRIMARY_EXTRA_TREES)
    assert REGISTRY.counter("solarselect_inference_failures_total", variant="primary_extra_trees") == 1

def test_model_unavailable_gauge_and_health(api_settings):
    class Down(StubProvider):
        def is_ready(self):
            return False
    with TestClient(create_app(api_settings, provider_factory=lambda _: Down())) as c:
        assert c.get("/api/v1/health/ready").status_code == 503
        assert c.get("/metrics").status_code == 200       # monitoring survives model outage

def test_prediction_values_distribution_recorded(mon_client, valid_body):
    mon_client.post("/api/v1/predict", json=valid_body)
    assert REGISTRY.histogram_count("solarselect_prediction_value", variant="primary_extra_trees") == 1
    assert REGISTRY.counter("solarselect_negative_predictions_total", variant="primary_extra_trees") == 1   # stub returns -0.5

def test_thread_safe_counters():
    import threading
    ts = [threading.Thread(target=lambda: [REGISTRY.inc("c") for _ in range(1000)]) for _ in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert REGISTRY.counter("c") == 8000
