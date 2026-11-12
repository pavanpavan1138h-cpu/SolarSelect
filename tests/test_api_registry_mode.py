import json
import sys
from types import SimpleNamespace
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.backend.core.config import Settings
from app.backend.main import create_app
from app.backend.model_loaders import MLflowRegistryProvider, load_registry, digest
from src.energy_economics.types import ModelVariant

def handoff(settings, real_provider):
    p = real_provider.predictors[ModelVariant.PRIMARY_EXTRA_TREES]
    return {"registered_name": "SolarSelectPeer", "alias": "champion", "version": "1",
            "run_id": "trusted-run", "cohort": "peer_cohort", "units": "kWh/kWp/day",
            "feature_names": real_provider.feature_names,
            "primary_artifact_sha256": p.primary_sha256,
            "reference_dataset_sha256": digest(settings.root / "data/processed/unisolar/peer_cohort/test.csv")}

def test_registry_no_handoff_readiness(api_settings):
    settings = Settings(root=api_settings.root, model_source="mlflow",
                        tracking_uri=None, model_uri=None, registry_handoff=None)
    with TestClient(create_app(settings)) as c:
        assert c.get("/api/v1/health/live").status_code == 200
        r = c.get("/api/v1/health/ready")
        assert r.status_code == 503
        assert r.json()["error"]["details"]["model"] == "BLOCKED_PENDING_PERSON1_REGISTRY_HANDOFF"
        assert c.get("/api/v1/model/info").status_code == 503

@pytest.mark.parametrize("mode", ["match", "wrong_prediction", "unavailable", "bad_features", "bad_units", "bad_hash"])
def test_registry_provider_parity_gate(api_settings, real_provider, tmp_path, monkeypatch, mode):
    import app.backend.model_loaders as loaders
    h = handoff(api_settings, real_provider)
    if mode == "bad_features":
        h["feature_names"] = list(reversed(h["feature_names"]))
    if mode == "bad_units":
        h["units"] = "W"
    if mode == "bad_hash":
        h["primary_artifact_sha256"] = "bad"
    path = tmp_path / "handoff.json"
    path.write_text(json.dumps(h))
    settings = Settings(root=api_settings.root, model_source="mlflow",
                        tracking_uri="http://127.0.0.1:5000", model_uri="models:/SolarSelectPeer@champion",
                        registry_handoff=str(path))
    monkeypatch.setattr(loaders, "LocalFrozenModelProvider", lambda _: real_provider)
    class MockRegistryModel:
        def predict(self, x):
            y = real_provider.predict(x, ModelVariant.PRIMARY_EXTRA_TREES)
            return y + (1 if mode == "wrong_prediction" else 0)
    def load(*_):
        if mode == "unavailable":
            raise ConnectionError("private registry details")
        return MockRegistryModel(), "1"
    monkeypatch.setattr(loaders, "load_registry", load)
    if mode == "match":
        provider = MLflowRegistryProvider(settings)
        assert provider.is_ready()
        assert provider.get_provenance(ModelVariant.PRIMARY_EXTRA_TREES)["source"] == "mlflow"
        with pytest.raises(Exception, match="only the primary"):
            provider.predict({}, ModelVariant.FALLBACK_BLEND_50_50)
    else:
        with TestClient(create_app(settings)) as c:
            assert c.get("/api/v1/health/ready").status_code == 503
            assert "private registry details" not in c.get("/api/v1/health/ready").text

@pytest.mark.parametrize("failure", [None, "empty", "tags", "signature", "version"])
def test_controlled_mlflow_client(api_settings, real_provider, monkeypatch, failure):
    h = handoff(api_settings, real_provider)
    tags = {"cohort": "peer_cohort", "output_units": "kWh/kWp/day",
            "model_variant": "primary_extra_trees", "primary_artifact_sha256": h["primary_artifact_sha256"]}
    if failure == "tags":
        tags["cohort"] = "full_cohort"
    version = SimpleNamespace(tags=tags, version="2" if failure == "version" else "1", run_id="trusted-run")
    class Client:
        def __init__(self, **kwargs): pass
        def get_model_version_by_alias(self, name, alias):
            assert (name, alias) == ("SolarSelectPeer", "champion")
            if failure == "empty":
                raise LookupError("No registered models")
            return version
    names = h["feature_names"] if failure != "signature" else list(reversed(h["feature_names"]))
    inputs = SimpleNamespace(input_names=lambda: names, inputs=[SimpleNamespace(type="DataType.double")] * 29)
    info = SimpleNamespace(signature=SimpleNamespace(inputs=inputs, outputs=SimpleNamespace(inputs=[SimpleNamespace(type="DataType.double")])))
    loaded = object()
    fake = SimpleNamespace(set_tracking_uri=lambda _: None, MlflowClient=Client,
                           models=SimpleNamespace(get_model_info=lambda _: info),
                           pyfunc=SimpleNamespace(load_model=lambda uri: loaded))
    monkeypatch.setitem(sys.modules, "mlflow", fake)
    settings = Settings(root=api_settings.root, tracking_uri="http://127.0.0.1:5000",
                        model_uri="models:/SolarSelectPeer@champion")
    if failure:
        with pytest.raises((ValueError, LookupError)):
            load_registry(settings, h)
    else:
        assert load_registry(settings, h) == (loaded, "1")
