"""Alert validation under controlled conditions: each rule fires on its trigger and stays quiet otherwise."""
import json
import pytest
from monitoring import alerts
from monitoring.metrics import REGISTRY

def names(**kw):
    return {a["name"] for a in alerts.evaluate(**kw)}

def test_every_rule_has_severity_basis_and_runbook():
    for r in alerts.load_rules():
        assert r["severity"] in ("critical", "warning", "info") and r["basis"] and len(r["runbook"]) > 30

def test_healthy_system_is_quiet():
    REGISTRY.set_gauge("solarselect_model_loaded", 1)
    for _ in range(100):
        REGISTRY.inc("solarselect_http_requests_total", route="/api/v1/predict", method="POST", status="2xx")
        REGISTRY.observe("solarselect_http_request_duration_ms", 20, route="/api/v1/predict")
    REGISTRY.inc("solarselect_inferences_total", 100, variant="primary_extra_trees")
    assert names() == set()

def test_no_data_never_fires():
    assert names() == set()

def test_model_not_loaded():
    REGISTRY.set_gauge("solarselect_model_loaded", 0)
    assert "ModelNotLoaded" in names()

def test_5xx_rate_requires_minimum_traffic():
    REGISTRY.inc("solarselect_http_requests_total", 10, route="r", method="POST", status="5xx")
    assert "High5xxRate" not in names()
    REGISTRY.inc("solarselect_http_requests_total", 90, route="r", method="POST", status="2xx")
    assert "High5xxRate" in names()

def test_inference_failure_and_nonfinite():
    REGISTRY.inc("solarselect_inferences_total", 99); REGISTRY.inc("solarselect_inference_failures_total", 1)
    REGISTRY.inc("solarselect_nonfinite_predictions_total")
    assert {"InferenceFailures", "NonFinitePrediction"} <= names()

def test_latency_rule():
    REGISTRY.inc("solarselect_http_requests_total", 60, route="/api/v1/predict", method="POST", status="2xx")
    for _ in range(60):
        REGISTRY.observe("solarselect_http_request_duration_ms", 900, route="/api/v1/predict")
    assert "PredictLatencyP95High" in names()

def test_input_rejection_spike():
    REGISTRY.inc("solarselect_http_requests_total", 100, route="r", method="POST", status="4xx")
    REGISTRY.inc("solarselect_input_rejections_total", 40, code="VALIDATION_ERROR")
    assert "InputRejectionSpike" in names()

def test_governance_and_drift_and_performance():
    REGISTRY.inc("solarselect_governance_rejections_total", code="PREDICTION_PENDING_LAG_POLICY")
    got = names(drift={"max_psi": 0.4, "status": "ALERT"}, performance={"mae_ratio_to_reference": 1.6})
    assert {"GovernanceRejections", "FeatureDriftAlert", "PerformanceDegradation"} <= got
    assert "PerformanceDegradation" not in names(performance={"mae_ratio_to_reference": 1.0})

def test_end_to_end_alert_from_real_requests(mon_client, valid_body):
    for _ in range(60):
        mon_client.post("/api/v1/predict", json={**valid_body, "features": {**valid_body["features"], "kWp": -1}})
    assert "InputRejectionSpike" in names()

def test_no_automatic_retraining_or_promotion_code():
    from pathlib import Path
    src = "".join(p.read_text() for p in Path("monitoring").rglob("*.py")).lower()
    for forbidden in (".fit(", "set_registered_model_alias", "transition_model_version_stage", "register_model(", "joblib.dump"):
        assert forbidden not in src
