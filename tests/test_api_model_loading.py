import json
import pytest
from app.backend.model_loaders import LocalFrozenModelProvider, digest
from app.backend.core.config import Settings
from src.energy_economics.types import ModelVariant

def test_model_info_schema(real_client, real_provider):
    info = real_client.get("/api/v1/model/info").json()
    assert info["source"] == "local"
    assert info["offline_test_metrics"]["mae"] == 0.905
    assert info["units"] == "kWh/kWp/day"
    assert "artifact_path" not in json.dumps(info)
    schema = real_client.get("/api/v1/model/schema").json()
    assert schema["ordered_feature_names"] == real_provider.feature_names
    assert len(schema["fields"]) == 29
    radiation = next(f for f in schema["fields"] if f["name"] == "extraterrestrial_radiation_h0")
    assert "kWh" in radiation["units"]

def test_path_independence(api_settings, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    p = LocalFrozenModelProvider(api_settings)
    assert p.is_ready()

def test_hash_before_deserialization(api_settings, monkeypatch):
    import app.backend.model_loaders as loaders
    monkeypatch.setattr(loaders, "digest", lambda _: "bad")
    monkeypatch.setattr(loaders, "Phase5PeerCohortPredictor", lambda *a, **kw: pytest.fail("must reject before unpickling"))
    with pytest.raises(ValueError, match="fingerprint"):
        LocalFrozenModelProvider(api_settings)

def test_metadata_schema_cross_check(api_settings, monkeypatch):
    import app.backend.model_loaders as loaders
    actual = loaders.Phase5PeerCohortPredictor
    class wrong(actual):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.feature_names = list(reversed(self.feature_names))
    monkeypatch.setattr(loaders, "Phase5PeerCohortPredictor", wrong)
    with pytest.raises(ValueError, match="ordering"):
        LocalFrozenModelProvider(api_settings)

def test_no_training_interface(real_provider):
    assert not hasattr(real_provider, "fit")
    assert not hasattr(real_provider, "partial_fit")
