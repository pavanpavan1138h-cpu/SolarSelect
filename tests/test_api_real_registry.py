"""Actual Person 1 champion tests; no substitute registrations or model mocks."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.backend.core.config import REPOSITORY_ROOT, Settings
from app.backend.main import create_app
from app.backend.model_loaders import MLflowRegistryProvider
from app.backend.model_loaders.verified_registry import INTEGER_FEATURES
from src.energy_economics.exceptions import FeatureValidationError
from src.energy_economics.inference import Phase5PeerCohortPredictor
from src.energy_economics.types import ModelVariant


@pytest.fixture(scope="module")
def registered_settings():
    handoff_path = REPOSITORY_ROOT / "configs/registry_peer_champion.json"
    handoff = json.loads(handoff_path.read_text())
    database = REPOSITORY_ROOT / handoff["database_relative_path"]
    if not database.exists():
        if os.getenv("SOLARSELECT_REQUIRE_REGISTRY_TESTS") == "1":
            pytest.fail("Import the approved Person 1 registry package before verification")
        pytest.skip("Approved registry assets are local-only; run prepare_person1_registry.py")
    return Settings(root=REPOSITORY_ROOT, model_source="mlflow",
                    tracking_uri="sqlite:///" + database.resolve().as_posix(),
                    model_uri="models:/SolarSelect-Yield-PeerCohort@champion",
                    registry_handoff=str(handoff_path))


@pytest.fixture(scope="module")
def registered_provider(registered_settings):
    return MLflowRegistryProvider(registered_settings)


@pytest.fixture(scope="module")
def registered_client(registered_settings, registered_provider):
    with TestClient(create_app(registered_settings, provider_factory=lambda _: registered_provider)) as client:
        yield client


def test_real_champion_identity_and_readiness(registered_client):
    assert registered_client.get("/api/v1/health/live").status_code == 200
    assert registered_client.get("/api/v1/health/ready").json()["model_source"] == "mlflow"
    result = registered_client.get("/api/v1/model/info").json()
    assert result["registered_name"] == "SolarSelect-Yield-PeerCohort"
    assert result["registered_alias"] == "champion"
    assert result["registered_version"] == "1"
    assert result["registered_run_id"] == "4b451f68e1c04de49875b095a4defd40"
    assert result["source"] == "mlflow" and result["units"] == "kWh/kWp/day"
    assert result["fitted_trees_equal_to_frozen"] == 100
    assert result["registry_provenance_basis"]["raw_run_cohort"] == "peer"
    assert result["registry_provenance_basis"]["version_tags"] == {}
    assert "artifact_relative_path" not in result


def test_independent_frozen_registered_and_http_parity(registered_client, registered_provider, historical_rows):
    direct = Phase5PeerCohortPredictor(
        primary_model_path=REPOSITORY_ROOT / Phase5PeerCohortPredictor.DEFAULT_ET_PATH,
        fallback_linear_path=REPOSITORY_ROOT / Phase5PeerCohortPredictor.DEFAULT_EN_PATH,
        metadata_path=REPOSITORY_ROOT / Phase5PeerCohortPredictor.DEFAULT_METADATA_PATH)
    expected = direct.predict(pd.DataFrame(historical_rows))
    registered = registered_provider.predict(historical_rows, ModelVariant.PRIMARY_EXTRA_TREES)
    http = []
    for row in historical_rows:
        result = registered_client.post("/api/v1/predict", json={
            "scenario": "historical_site_day", "features": dict(reversed(list(row.items())))})
        assert result.status_code == 200, result.text
        assert result.json()["energy_basis"] == "UNVERIFIED_ASSUMED_AC"
        http.append(result.json()["predicted_specific_yield_kwh_per_kwp_day"])
    assert np.allclose(expected, registered, rtol=0, atol=1e-8)
    assert np.allclose(expected, http, rtol=0, atol=1e-8)


def test_lossless_signature_types(registered_provider, historical_rows):
    typed = registered_provider.model.prepare_features(historical_rows)
    assert list(typed.columns) == registered_provider.feature_names
    for column in typed:
        assert str(typed[column].dtype) == ("int64" if column in INTEGER_FEATURES else "float64")
        assert np.array_equal(typed[column].to_numpy(), np.array([row[column] for row in historical_rows]))


@pytest.mark.parametrize("name", sorted(INTEGER_FEATURES))
def test_fractional_registered_integer_is_never_truncated(registered_provider, historical_rows, name):
    row = dict(historical_rows[0])
    row[name] += 0.25
    with pytest.raises(FeatureValidationError, match="exact integral"):
        registered_provider.model.prepare_features(row)


def test_registered_batch_order(registered_client, registered_provider, historical_rows):
    selected = list(reversed(historical_rows[:5]))
    response = registered_client.post("/api/v1/predict/batch", json={
        "rows": [{"scenario": "historical_site_day", "features": row} for row in selected]})
    assert response.status_code == 200, response.text
    results = response.json()["results"]
    expected = registered_provider.predict(selected, ModelVariant.PRIMARY_EXTRA_TREES)
    assert np.allclose([r["predicted_specific_yield_kwh_per_kwp_day"] for r in results], expected, rtol=0, atol=1e-8)
    assert all(r["model"]["source"] == "mlflow" for r in results)


@pytest.mark.parametrize("field,value", [
    ("kWp", 0), ("lag1_daily_yield", None), ("lat", 91),
    ("day_of_year", 60.5), ("month", "3"), ("SolarGeneration", 4),
])
def test_real_registry_invalid_inputs(registered_client, historical_body, field, value):
    historical_body["features"][field] = value
    result = registered_client.post("/api/v1/predict", json=historical_body)
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "VALIDATION_ERROR"


def test_real_registry_missing_and_malformed_json(registered_client, historical_body):
    del historical_body["features"]["lag7_daily_yield"]
    assert registered_client.post("/api/v1/predict", json=historical_body).status_code == 422
    result = registered_client.post("/api/v1/predict", content='{"scenario":', headers={"Content-Type": "application/json"})
    assert result.status_code == 422 and result.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_real_registry_nonfinite_input(registered_client, historical_body, value):
    historical_body["features"]["lag1_daily_yield"] = value
    assert registered_client.post("/api/v1/predict", content=json.dumps(historical_body),
                                  headers={"Content-Type": "application/json"}).status_code == 422


def test_registry_pending_prospective_and_explicit_variant_policy(registered_client, historical_body):
    pending = registered_client.post("/api/v1/predict", json={"scenario": "prospective_roof", "roof_id": "NEW"})
    assert pending.status_code == 409
    assert pending.json()["error"]["code"] == "PREDICTION_PENDING_LAG_POLICY"
    assert pending.json()["error"]["details"]["predicted_specific_yield_kwh_per_kwp_day"] is None
    historical_body["model_variant"] = "fallback_blend_50_50"
    unavailable = registered_client.post("/api/v1/predict", json=historical_body)
    assert unavailable.status_code == 409 and unavailable.json()["error"]["code"] == "MODEL_VARIANT_NOT_ENABLED"


def test_registry_openapi_unchanged(registered_client):
    expected = json.loads((REPOSITORY_ROOT / "docs/backend/openapi.json").read_text())
    assert registered_client.get("/openapi.json").json() == expected
    assert registered_client.get("/docs").status_code == 200


def test_registered_batch_bound(registered_client, historical_body):
    assert registered_client.post("/api/v1/predict/batch", json={"rows": [historical_body] * 101}).status_code == 422


@pytest.mark.parametrize("tamper", ["database_hash", "package_hash", "trusted_types", "full_cohort", "dvc_lineage"])
def test_registry_integrity_failures_are_not_ready(registered_settings, tmp_path, tamper):
    h = json.loads(Path(registered_settings.registry_handoff).read_text())
    if tamper == "database_hash":
        h["database_sha256"] = "0" * 64
    elif tamper == "package_hash":
        h["package_sha256"]["model.skops"] = "0" * 64
    elif tamper == "trusted_types":
        h["trusted_types"] = ["builtins.eval"]
    elif tamper == "full_cohort":
        h["registered_name"] = "SolarSelect-Yield-FullCohort"
    else:
        h["primary_artifact_md5"] = "0" * 32
    path = tmp_path / "invalid_handoff.json"
    path.write_text(json.dumps(h))
    with TestClient(create_app(replace(registered_settings, registry_handoff=str(path)))) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/v1/health/ready").status_code == 503
        assert client.get("/api/v1/model/info").status_code == 503


def test_imported_registry_and_package_bytes_unchanged(registered_settings):
    h = json.loads(Path(registered_settings.registry_handoff).read_text())
    assert hashlib.sha256((REPOSITORY_ROOT / h["database_relative_path"]).read_bytes()).hexdigest() == h["database_sha256"]
    directory = REPOSITORY_ROOT / h["artifact_relative_path"]
    for name, expected in h["package_sha256"].items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected
